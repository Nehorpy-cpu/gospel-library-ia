# Curated Ingestion V1 Runbook

## Purpose

`apps/api/scripts/ingest_curated_documents.py` adds a small set of real,
verifiable pages without crawling a site or using OpenAI/Qdrant. It requests
each explicitly listed URL once, waits between requests, extracts only a known
main-content container, and skips pages that do not meet a conservative text
quality threshold.

Mass scraping is intentionally deferred until rate limits, robots policies,
monitoring, extraction quality, and duplicate review are production-ready.

Initial URLs:

1. `https://www.churchofjesuschrist.org/study/manual/gospel-topics/salvation?lang=eng`
2. `https://www.churchofjesuschrist.org/study/manual/gospel-topics/faith-in-jesus-christ?lang=eng`
3. `https://www.churchofjesuschrist.org/study/manual/gospel-topics/book-of-mormon?lang=eng`
4. `https://www.churchofjesuschrist.org/study/general-conference/2020/10/45andersen?lang=eng`
5. `https://www.churchofjesuschrist.org/study/general-conference/2021/04/28ballard?lang=eng`
6. `https://www.churchofjesuschrist.org/study/general-conference/2021/04/54christofferson?lang=eng`
7. `https://www.churchofjesuschrist.org/study/general-conference/2021/04/17eyring?lang=eng`
8. `https://speeches.byu.edu/talks/kevin-r-duncan/jesus-christ-is-the-answer/`

The Church pages are official sources. The BYU Speech remains in the list only
because its current page structure passes the same conservative live
extraction checks.

Each request uses:

```text
GospelLibraryIA/0.1 curated-ingestion contact=https://www.estudiopy.com
```

No page links are followed. Only allowlisted redirects are followed, up to the
small configured redirect limit.

## Add a URL manually

Add one `CuratedTarget` entry to `TARGETS` in the script. Requirements:

- HTTPS URL under the existing host allowlist;
- explicit source key, source type, language, category, and document type;
- a specific main-content CSS selector;
- no listing page and no automatic link discovery;
- a focused test proving the extractor returns clean content or skips it.

Do not weaken the minimum-content checks just to accept a failing page.

## Run from PowerShell

```powershell
cd F:\Proyectos\gospel-library-ia-clean\apps\api
.\.venv\Scripts\Activate.ps1
$env:DATABASE_URL="TU_DATABASE_URL_DE_SUPABASE_CON_SSLMODE"
python scripts/ingest_curated_documents.py
Remove-Item Env:DATABASE_URL
```

The connection URL normally includes `sslmode=require`. Never commit, print,
paste into tickets, or capture the real value in screenshots.

## Duplicate protection

The script acquires one PostgreSQL advisory transaction lock and checks:

- `documents.canonical_url`;
- `raw_metadata.source_url`;
- `raw_metadata.normalized_url`;
- the unique chunk key `(document_id, chunk_index, chunker_version)`;
- source, author, and tag unique keys.

Running the script twice verifies existing rows without duplicating documents
or chunks. Existing documents are not overwritten or deleted.

Document metadata includes:

- `ingestion_mode="curated_v1"`
- `is_seed=false`
- `seed_content=false` for compatibility
- `source_name`
- `source_url`
- `normalized_url`
- `canonical_url`
- `content_type="text/html"`
- `extracted_at`
- `extractor_version="curated-html-v1"`

Chunks are stored in order with the existing `document_chunks.text` column and
target approximately 800–1200 characters. Chunk metadata retains the source
URL, document ID, ingestion mode, content type, and extractor version.

## Supabase verification

```sql
SELECT id, title, author, canonical_url, published_at, language, category
FROM documents
WHERE raw_metadata->>'ingestion_mode' = 'curated_v1'
ORDER BY title;

SELECT document_id, chunk_index, length(text) AS characters,
       metadata->>'source_url' AS source_url
FROM document_chunks
WHERE metadata->>'ingestion_mode' = 'curated_v1'
ORDER BY document_id, chunk_index;
```

Seed/test documents remain identifiable with:

```sql
SELECT id, title, canonical_url
FROM documents
WHERE coalesce(
  (raw_metadata->>'is_seed')::boolean,
  (raw_metadata->>'seed_content')::boolean,
  false
) = true;
```

No seed rows are deleted. The API can hide them with:

```txt
GET /api/documents?includeSeed=false
```

Without that parameter, real documents are ordered before seed/test content.
The Library UI also exposes an `Ocultar contenido seed/test` checkbox. Text
search sends `filters.include_seed=false` while that option is active.

## API and frontend verification

```powershell
curl.exe "https://api.estudiopy.com/api/documents?includeSeed=false"
curl.exe "https://api.estudiopy.com/api/authors"
curl.exe "https://api.estudiopy.com/api/topics"
curl.exe "https://api.estudiopy.com/api/documents/summary"
curl.exe "https://api.estudiopy.com/api/sources/summary"
curl.exe -X POST "https://api.estudiopy.com/api/search" `
  -H "Content-Type: application/json" `
  -d '{"query":"Jesucristo","filters":{"include_seed":false}}'
```

Open `https://www.estudiopy.com/library` and confirm:

1. Real curated documents appear before seed/test documents.
2. Titles, authors, excerpts, source types, and source URLs are correct.
3. Opening a document shows clean paragraphs rather than menus or raw HTML.
4. Filtering the API with `includeSeed=false` returns only real content.

## Failed URLs

A failed page is printed as `SKIPPED` with a non-secret reason such as HTTP
status, unsupported content type, response size, missing title, or insufficient
clean main text.

When a URL fails:

1. Do not insert fallback HTML or fabricated text.
2. Inspect the page structure manually.
3. Add or tighten a host-specific main-content selector.
4. Add an extraction test.
5. Run the script again; successful existing URLs remain idempotent.

## Required validation

Run twice against the same Supabase database:

```powershell
python scripts/ingest_curated_documents.py
python scripts/ingest_curated_documents.py
```

The second run should report the same documents and chunks as `verified`, with
zero duplicates created. A URL that no longer meets extraction quality should
be reported as `SKIPPED`; do not weaken selectors or minimum-content checks
without manually reviewing the returned HTML.
