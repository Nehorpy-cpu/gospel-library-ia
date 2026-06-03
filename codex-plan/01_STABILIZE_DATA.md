# Phase 1 - Stabilize Data

## Goal

Improve scraper data quality so `/api/documents` shows real documents with title, author, source, language, and URL.

## Scope

- Avoid `Untitled document`.
- Improve title, author, and date extraction.
- Persist correct `sourceType` and `sourceUrl`.
- Create real `ingestion_jobs`.
- Add clear scraping and ingestion logs.
- Preserve existing endpoints.

## Required work

1. Extract title from `h1`, `title`, `og:title`, `meta name="title"`, schema.org, PDF filename, visible text, and URL slug fallback.
2. Extract author from `author`, byline, meta author, schema.org, and visible site blocks.
3. Extract date from `time`, meta date, schema.org `datePublished`, visible text, and URL year.
4. Save canonical source types:
   - `byu_speeches_es`
   - `byu_speeches_en`
   - `discursos_sud`
   - `general_conference`
   - `church_manuals`
   - `joseph_smith_papers`
   - `byu_rsc`
5. Save original `sourceUrl`.
6. Create ingestion jobs with:
   - `source`
   - `status`
   - `startedAt`
   - `finishedAt`
   - `documentsFound`
   - `documentsCreated`
   - `documentsUpdated`
   - `errors`
7. Add structured logs for discovery, fetch, parsing, persistence, assets, OCR, and indexing.
8. Backfill existing documents where safe.

## Acceptance criteria

- `SELECT count(*) FROM documents WHERE title = 'Untitled document';` returns `0`.
- Every document has `raw_metadata.source_type`.
- Every document has `raw_metadata.source_url`.
- Recent `ingestion_jobs` include source and metrics.
- `/api/documents` returns document rows, not only status summaries.

## Verification

```bash
docker compose exec -T postgres psql -U gospel -d gospel_library -c "SELECT count(*) AS total, count(*) FILTER (WHERE title='Untitled document') AS untitled, count(*) FILTER (WHERE raw_metadata ? 'source_type') AS with_source_type, count(*) FILTER (WHERE raw_metadata ? 'source_url') AS with_source_url FROM documents;"
docker compose logs scraper-worker-scraping --tail=80
pnpm test
```

## Non-goals

- Do not redesign the scraper architecture.
- Do not add new product features.
- Do not use mock documents.

