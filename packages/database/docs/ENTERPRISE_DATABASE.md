# Gospel Library IA Enterprise Database

## Stack

- PostgreSQL 16+
- Prisma ORM
- Qdrant for vector storage
- PostgreSQL for embedding metadata, FTS, relational data and user state

## Core Design

```txt
organizations
  -> memberships
  -> users

sources
  -> documents
  -> document_chunks
  -> embeddings metadata
  -> media_assets
  -> transcript_segments

authors/categories/tags/scriptures
  -> document join tables
  -> chunk join tables

users
  -> favorites
  -> reading_history
  -> notes
  -> highlights
  -> collections
  -> chat_sessions
  -> sync_events
```

## Document Scale

The database is designed for:

- millions of `documents`
- tens or hundreds of millions of `document_chunks`
- embeddings metadata in PostgreSQL
- vectors in Qdrant
- user-generated data with offline sync

Document text is stored in `documents.content_text` for canonical access. Search and
RAG operate mostly on `document_chunks`.

## Embeddings Strategy

PostgreSQL does not store vector arrays. It stores:

- chunk id
- model id
- Qdrant point id
- Qdrant collection
- content hash
- payload metadata

Qdrant stores:

- vector
- chunk/document/source payload
- semantic filter fields

This keeps PostgreSQL relational and Qdrant specialized.

## Full Text Search

Migration `0001_enterprise_schema` adds:

- `documents.search_vector`
- `document_chunks.search_vector`
- `notes.search_vector`
- language-aware `gospel_text_config`
- GIN indexes on all search vectors
- trigram indexes for fuzzy title/author/tag/scripture lookup

Recommended query pattern:

```sql
SELECT dc.id, ts_rank_cd(dc.search_vector, plainto_tsquery('spanish', $1)) AS rank
FROM document_chunks dc
JOIN documents d ON d.id = dc.document_id
WHERE dc.search_vector @@ plainto_tsquery('spanish', $1)
  AND d.status = 'READY'
  AND d.visibility = 'PUBLIC'
ORDER BY rank DESC
LIMIT 100;
```

## Hybrid Search

Use PostgreSQL for:

- BM25-like FTS
- exact metadata filters
- user/private data filters
- scripture references
- tag/category/author joins

Use Qdrant for:

- semantic nearest neighbors
- vector payload filtering
- multilingual semantic retrieval

Merge in application:

```txt
0.52 semantic_score
0.36 bm25_score
0.08 source trust / official boost
0.04 metadata freshness / language match
```

Then rerank top 40-100 candidates.

## Partitioning

### Partition Immediately

For very high-volume SaaS deployments, partition before backfills:

- `sync_events`: monthly range partition by `created_at`
- `audit_logs`: monthly range partition by `created_at`
- `chat_messages`: range by `created_at` or hash by `session_id`

### Partition Later Or From Day One

`document_chunks` can reach tens of millions quickly.

Options:

- Hash partition by `document_id`
- Range partition by source/date for historical corpora
- Separate physical tables by collection/model version only if operations require it

Recommended for millions of documents:

```txt
document_chunks PARTITION BY HASH(document_id)
32 partitions initially
64 or 128 for very large clusters
```

### Prisma Caveat

Prisma does not model PostgreSQL partitions well. Use raw SQL migrations for
partitioned tables and keep Prisma models pointing at the parent table.

## Index Strategy

### Documents

- `(source_id, status)`
- `(kind, language)`
- `(visibility, status)`
- `(published_at)`
- `content_hash`
- partial index for public ready documents
- GIN JSONB metadata
- GIN FTS vector
- trigram title

### Chunks

- `(document_id, chunk_index)`
- `text_hash`
- `(language)`
- `(document_id, page_number)`
- GIN FTS vector
- GIN JSONB metadata

### User Data

- favorites: `(user_id, created_at DESC)`
- history: `(user_id, last_read_at DESC)`
- notes: partial active index `(user_id, updated_at DESC) WHERE deleted_at IS NULL`
- highlights: partial active index `(user_id, updated_at DESC) WHERE deleted_at IS NULL`

### Sync

- `(user_id, created_at, server_rev)`
- `(organization_id, created_at)`
- `(entity, entity_id)`

## Multi-Tenant Strategy

Public canonical content can have `organization_id = null`.
Private tenant content uses `organization_id`.

For enterprise isolation:

- Add PostgreSQL Row Level Security.
- Use `organization_id` predicates in every tenant query.
- Put private documents and user data behind organization membership checks.

Potential RLS policy:

```sql
CREATE POLICY tenant_documents ON documents
USING (
  organization_id IS NULL OR
  organization_id = current_setting('app.organization_id')::uuid
);
```

## Offline Sync

User-mutated entities include:

- notes
- highlights
- favorites
- collections
- collection_items
- reading_history
- chat sessions/messages

Each mutable personal entity has:

- `client_rev`
- `server_rev`
- `updated_at`
- `deleted_at`

`sync_events` gives incremental sync:

```sql
SELECT *
FROM sync_events
WHERE user_id = $1
  AND created_at > $2
ORDER BY created_at ASC, server_rev ASC
LIMIT 1000;
```

Conflict strategy:

- notes/highlights: field-level merge if possible
- favorites/history: last write wins
- collections: server rev wins, client retries with patch

## Migration Strategy

Development:

```bash
cd packages/database
npm install
npm run validate
npm run migrate:dev
```

Production:

```bash
cd packages/database
npm run generate
npm run migrate:deploy
npm run migrate:post
npm run seed:sql
```

Rules:

- Never run huge backfills in the same deploy migration.
- Create indexes concurrently in production when possible.
- Backfill search vectors in batches.
- Backfill embeddings asynchronously.
- Use Qdrant collection versioning: `doctrinal_chunks_v1`, `v2`, etc.

## Performance Strategy

### Write Path

```txt
scraper -> documents/assets
RAG worker -> chunks
embedding worker -> embeddings metadata + Qdrant
app users -> notes/highlights/history/sync
```

Keep ingestion and user traffic separated:

- ingestion workers use batch inserts
- user app uses short transactions
- embeddings are idempotent by `(chunk_id, model_id, content_hash)`

### Read Path

Home/library:

- read from `documents`
- filter by `status=READY`
- use cursor pagination by `(published_at, id)`

Reader:

- document metadata
- chunks by `(document_id, chunk_index)`
- notes/highlights by `(user_id, document_id)`

Search:

- PostgreSQL FTS top 100
- Qdrant semantic top 100
- merge/rerank in service

Chat:

- recent chat messages by `(session_id, created_at)`
- citations stored normalized in `chat_citations`

### Autovacuum

Tune for high-write tables:

- `sync_events`
- `audit_logs`
- `chat_messages`
- `reading_history`
- `crawl_urls`
- `ingestion_jobs`

Suggested:

```sql
ALTER TABLE reading_history SET (
  autovacuum_vacuum_scale_factor = 0.02,
  autovacuum_analyze_scale_factor = 0.01
);
```

## Retention

Suggested defaults:

- audit logs: 1-7 years depending on plan
- sync events: 30-180 days after all clients acknowledge
- failed ingestion jobs: 90 days
- chat sessions: user-controlled deletion
- public documents: permanent unless takedown

## Backup And Recovery

- PITR enabled for PostgreSQL
- daily logical dumps for critical lookup tables
- Qdrant snapshots by collection
- R2/S3 versioning for assets
- embedding metadata can rebuild vectors if source text is retained

## Operational Checks

Track:

- slow FTS queries
- Qdrant latency
- chunk count per document
- embedding backlog
- failed jobs
- sync lag per user
- table bloat
- index hit ratio
- autovacuum health
