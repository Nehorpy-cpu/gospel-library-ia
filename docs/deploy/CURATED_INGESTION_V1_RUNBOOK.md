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
2. `https://www.churchofjesuschrist.org/study/general-conference/2021/04/28ballard?lang=eng`
3. `https://speeches.byu.edu/talks/kevin-r-duncan/jesus-christ-is-the-answer/`

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

## Supabase verification

```sql
SELECT id, title, author, canonical_url, published_at, language, category
FROM documents
WHERE raw_metadata->>'ingestion_marker' = 'curated-ingestion-v1'
ORDER BY title;

SELECT document_id, chunk_index, length(text) AS characters,
       metadata->>'source_url' AS source_url
FROM document_chunks
WHERE metadata->>'ingestion_marker' = 'curated-ingestion-v1'
ORDER BY document_id, chunk_index;
```

Seed/test documents remain identifiable with:

```sql
SELECT id, title, canonical_url
FROM documents
WHERE coalesce((raw_metadata->>'seed_content')::boolean, false) = true;
```

No seed rows are deleted. The API can hide them with:

```txt
GET /api/documents?includeSeed=false
```

Without that parameter, real documents are ordered before seed/test content.

## API and frontend verification

```powershell
curl.exe "https://api.estudiopy.com/api/documents?includeSeed=false"
curl.exe "https://api.estudiopy.com/api/authors"
curl.exe "https://api.estudiopy.com/api/topics"
curl.exe "https://api.estudiopy.com/api/documents/summary"
curl.exe "https://api.estudiopy.com/api/sources/summary"
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
