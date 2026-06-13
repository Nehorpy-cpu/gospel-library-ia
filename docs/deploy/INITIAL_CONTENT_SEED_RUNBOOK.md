# Initial Content Seed Runbook

## Scope

`apps/api/scripts/seed_initial_documents.py` inserts a deliberately small set
of real-source records for end-to-end testing. It does not scrape pages, call
OpenAI, create embeddings, contact Qdrant, delete data, or modify the schema.

The stored text is a short original summary marked `[SEED/TEST CONTENT]`.
Authoritative content remains at each `source_url`.

Seed documents:

1. `Faith in Jesus Christ` - official Gospel Topics page.
2. `God the Father` - official Gospel Topics page.
3. `We Talk of Christ` - Neil L. Andersen, October 2020 general conference.
4. `Be One with Christ` - Quentin L. Cook, April 2024 general conference.
5. `Faith in the Lord Jesus Christ` - Gene R. Cook, BYU Speeches.

## Run from PowerShell

Open a new PowerShell session so the temporary database variable is easy to
remove afterward:

```powershell
cd F:\Proyectos\gospel-library-ia-clean\apps\api
.\.venv\Scripts\Activate.ps1
$env:DATABASE_URL="TU_DATABASE_URL_DE_SUPABASE_CON_SSLMODE"
python scripts/seed_initial_documents.py
Remove-Item Env:DATABASE_URL
```

The URL normally ends with `?sslmode=require`. Do not paste it into Git,
screenshots, tickets, logs, or this runbook.

Expected summary:

```txt
Initial content seed completed.
Sources:   N created, N verified
Documents: N created, N verified
Chunks:    N created, N verified
Authors:   N created, N verified
Tags:      N created, N verified
```

## Idempotency

The script uses one PostgreSQL advisory transaction lock and:

- identifies sources by `sources.key`;
- identifies documents by `canonical_url` or
  `raw_metadata->>'source_url'`;
- inserts chunks with the unique key
  `(document_id, chunk_index, chunker_version)`;
- stores chunk content in `document_chunks.text`, the content column defined by
  the real schema;
- stores `source_url` and `document_id` in `document_chunks.metadata`, because
  `document_chunks` has no dedicated `source_url` column;
- inserts authors and tags by their unique slug;
- uses `ON CONFLICT DO NOTHING`;
- never updates, truncates, or deletes existing content.

Running it again verifies the same rows and does not create duplicates.

## Verify in Supabase

Use the Supabase SQL editor without exposing connection credentials:

```sql
SELECT id, key, name, source_type
FROM sources
WHERE config->>'seed_marker' = 'initial-content-seed-v1'
ORDER BY key;

SELECT id, title, canonical_url, author, status, is_indexed
FROM documents
WHERE raw_metadata->>'seed_marker' = 'initial-content-seed-v1'
ORDER BY title;

SELECT document_id, chunk_index, chunker_version, metadata->>'source_url' AS source_url
FROM document_chunks
WHERE metadata->>'seed_marker' = 'initial-content-seed-v1'
ORDER BY document_id, chunk_index;

SELECT slug, display_name
FROM authors
WHERE metadata->>'seed_marker' = 'initial-content-seed-v1'
ORDER BY display_name;
```

Tags are shared catalog rows and may already exist:

```sql
SELECT slug, name, language
FROM tags
WHERE slug IN ('faith', 'jesus-christ', 'gospel-topics', 'general-conference', 'byu-speeches')
ORDER BY name;
```

## Verify the deployed API

After running the seed against the production database:

```powershell
curl.exe "https://api.estudiopy.com/api/documents?limit=12"
curl.exe "https://api.estudiopy.com/api/authors"
curl.exe "https://api.estudiopy.com/api/topics"
curl.exe "https://api.estudiopy.com/api/ingestion/status"
```

Then open `https://www.estudiopy.com/library`. The five documents should be
visible without Qdrant or OpenAI.

## Remove only seed data

Do not run cleanup unless the seed records are no longer needed. Review the
rows first and perform the cleanup in one transaction:

```sql
BEGIN;

SELECT id, title, canonical_url
FROM documents
WHERE raw_metadata->>'seed_marker' = 'initial-content-seed-v1'
FOR UPDATE;

DELETE FROM documents
WHERE raw_metadata->>'seed_marker' = 'initial-content-seed-v1';

DELETE FROM authors a
WHERE a.metadata->>'seed_marker' = 'initial-content-seed-v1'
  AND NOT EXISTS (SELECT 1 FROM documents d WHERE d.author = a.display_name);

DELETE FROM sources s
WHERE s.config->>'seed_marker' = 'initial-content-seed-v1'
  AND NOT EXISTS (SELECT 1 FROM documents d WHERE d.source_id = s.id);

COMMIT;
```

`document_chunks` rows are removed automatically by the document foreign key.
Tags are intentionally retained because they are shared catalog data and the
schema does not record seed metadata on tag rows.
