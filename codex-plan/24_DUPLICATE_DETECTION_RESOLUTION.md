# Phase 24 - Duplicate detection resolution

## Objective

Detect and classify historical duplicate documents conservatively, preserving
all physical documents and every existing relationship while excluding only
confirmed duplicate records from default discovery paths.

## Detection signals

- Normalized source and canonical URLs.
- Meaningful content hashes.
- Real media checksums.
- Normalized title, author, publication date, and language.
- Local textual similarity without OpenAI or embeddings.

## Classifications

- `exact_duplicate`
- `probable_duplicate`
- `translation`
- `revised_edition`
- `related_media`
- `not_duplicate`

Translations, revised editions, distinct sessions, PDFs, audio,
transcriptions, and complementary resources are never merged merely because
they are related.

## Persistence and reversibility

`document_duplicate_relations` records the canonical document, duplicate
document, detection rule, confidence, review status, evidence, and audit
timestamps. The migration never deletes or updates a document or its
relationships. Downgrading to revision `0011` drops only this decision table.

## Canonical selection

Canonical records are selected by official-source priority, metadata
completeness, valid content length, available media, relationship count, and
oldest creation time as the final tie-breaker. Canonical chains are flattened
so a selected canonical record is never hidden as another confirmed duplicate.

## Operation

```bash
# Dry-run by default
docker compose exec scraper-api python scripts/resolve_duplicates.py

# Persist decisions
docker compose exec scraper-api python scripts/resolve_duplicates.py --apply
```

The command is idempotent, reports counts and examples, and performs no
physical deletion. Confirmed exact/probable duplicates are excluded from the
library, PostgreSQL fallback search, BM25, semantic retrieval, and future
incremental indexing. Direct document access remains compatible.

## Applied snapshot

- Physical documents preserved: `32,140`
- Exact duplicates confirmed: `7,994`
- Probable duplicates pending review: `773`
- Translations preserved: `5,028`
- Related media preserved: `1,305`
- Not-duplicate decisions: `517`
- Revised editions preserved: `1`
- Total persisted decisions: `15,618`
- Canonical documents hidden by another confirmed relation: `0`
- Orphan references detected: `0`

## Validation

- Scraper, API, and RAG unit tests pass.
- Python compile checks pass.
- Prisma schema validates.
- Scraper Alembic reaches `0012 (head)`.
- Controlled downgrade to `0011` and re-upgrade to `0012` preserve document
  counts and restore the decision table safely.
- Repeated dry-run after apply produces zero pending decisions.
- Docker Compose configuration, image build, service health, and workers pass.
- Real document, search, and chat requests return canonical PostgreSQL data.
- No OpenAI call, embedding generation, or Qdrant collection change occurs.
