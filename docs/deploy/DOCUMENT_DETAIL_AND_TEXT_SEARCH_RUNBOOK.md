# Document detail and PostgreSQL text search

## Scope

This phase implements the usable flow:

`Library -> document detail -> PostgreSQL text search -> real content/chunks`

OpenAI and Qdrant are not used by `POST /api/search`. A Qdrant health error does
not block the library, document detail, or textual search.

## Endpoints

- `GET /api/documents`
- `GET /api/documents/{document_id}`
- `GET /api/documents/{document_id}?include_chunks=true`
- `GET /api/documents/summary`
- `GET /api/sources/summary`
- `GET /api/authors`
- `GET /api/topics`
- `POST /api/search`
- `POST /api/chat` (keeps its existing local fallback behavior)

The document detail response includes bibliographic fields, source URLs,
status, tags/topics, safe metadata, the available chunk count, and optionally
up to 200 ordered chunks.

The search response exposes both `items` and `results` for compatibility:

```json
{
  "query": "Cristo",
  "mode": "postgres_text",
  "items": [],
  "results": [],
  "total": 0,
  "warnings": []
}
```

An empty result is a normal `200 OK`, not a server error.

## Test with curl

List documents and copy an `id`:

```bash
curl "https://api.estudiopy.com/api/documents?limit=12"
```

Load document metadata:

```bash
curl "https://api.estudiopy.com/api/documents/DOCUMENT_ID"
```

Load document metadata and readable chunks:

```bash
curl "https://api.estudiopy.com/api/documents/DOCUMENT_ID?include_chunks=true"
```

Run PostgreSQL textual search:

```bash
curl -X POST "https://api.estudiopy.com/api/search" \
  -H "Content-Type: application/json" \
  -d '{"query":"Cristo","limit":12}'
```

Check the empty-query contract:

```bash
curl -X POST "https://api.estudiopy.com/api/search" \
  -H "Content-Type: application/json" \
  -d '{"query":""}'
```

## Test from the frontend

1. Open `https://www.estudiopy.com/library`.
2. Confirm that the unfiltered library loads real API documents.
3. Enter at least two characters in the search field.
4. Confirm that matching cards come from `POST /api/search`.
5. Search for a phrase that does not exist and confirm
   `No se encontraron resultados.`
6. Open a card and confirm navigation to `/documents/{documentId}`.
7. Confirm the detail page shows real metadata and either real text/chunks or
   the explicit `Contenido completo no disponible` state.
8. Confirm `Abrir fuente original` only appears as an active link when the API
   returns a valid HTTP(S) source URL.

## Verify in Supabase

Run read-only checks in the Supabase SQL editor:

```sql
SELECT id, title, author, source_id, status, created_at
FROM documents
ORDER BY created_at DESC
LIMIT 20;

SELECT document_id, chunk_index, section_title, left(text, 160) AS preview
FROM document_chunks
ORDER BY document_id, chunk_index
LIMIT 50;

SELECT id, name, slug
FROM tags
ORDER BY name
LIMIT 50;

SELECT id, key, name
FROM sources
ORDER BY name;
```

To inspect the optional relational tags model when it exists:

```sql
SELECT dt.document_id, t.name
FROM document_tags dt
JOIN tags t ON t.id = dt.tag_id
ORDER BY dt.document_id, t.name
LIMIT 100;
```

Do not run destructive statements for this verification.

## How textual search works

The API normalizes the query, rejects no-content conditions safely, and uses
parameterized PostgreSQL matching over:

- `documents.title`
- `documents.author` when present
- document summary/description columns or safe metadata equivalents
- the document text column
- `document_chunks.text`
- `documents.tags`
- `tags.name` through `document_tags` when that relation exists
- `sources.name`

The ranking is intentionally simple and deterministic. Title matches receive
the highest weight, followed by author, source, summary, tags, chunks, and
document text. The snippet prefers the first matching chunk, then summary, then
document text.

## Schema initialization

The schema initializer is idempotent and does not delete data. It adds the
basic title, author, source, creation date, chunk-document, and chunk search
indexes with `CREATE INDEX IF NOT EXISTS`.

From the API service directory:

```bash
cd apps/api
python scripts/init_supabase_schema.py
```

`DATABASE_URL` must be present in the process environment. Never paste or print
the production value in logs, tickets, or chat.

## Local validation

```bash
cd apps/api
python -m compileall app scripts
python -m unittest discover -s tests

cd ../web
corepack pnpm install
corepack pnpm typecheck
corepack pnpm lint
corepack pnpm build
```

## Current limitations

- Search is substring/term matching, not semantic retrieval.
- Ranking is a simple PostgreSQL score, not BM25 or a learned reranker.
- At most 200 chunks are returned by one detail request.
- Documents with only bibliographic metadata cannot show full content.
- Seed/test summaries remain visibly identified and are not presented as
  authoritative full text.
- Future action buttons remain disabled until their complete workflows are
  connected.

## Next steps toward Qdrant and RAG

1. Finish full-text ingestion and chunk quality checks.
2. Backfill and validate `document_chunks.search_vector`.
3. Add a measured PostgreSQL full-text ranking baseline.
4. Restore Qdrant indexing behind health and readiness checks.
5. Add embeddings only after source/content quality is verified.
6. Compare PostgreSQL and semantic retrieval with a fixed evaluation set.
7. Enable grounded RAG responses only when citations resolve to stored chunks.

## Redeploy

Render:

1. Push the commit to the branch connected to the API service.
2. Run `python scripts/init_supabase_schema.py` as a one-time deploy/admin job.
3. Trigger a manual deploy of the latest commit if automatic deploy is off.
4. Verify `/health`, `/api/documents`, document detail, and `/api/search`.
5. Qdrant may remain in error for this phase; PostgreSQL and Redis should be OK.

Vercel:

1. Push the same commit to the branch connected to the web project.
2. Confirm `NEXT_PUBLIC_API_URL=https://api.estudiopy.com`.
3. Trigger a production deployment if automatic deployment is off.
4. Verify `/library`, a `/documents/{id}` route, search empty state, and API
   error state.
