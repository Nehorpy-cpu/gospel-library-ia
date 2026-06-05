# Ingestion Pipeline

The ingestion pipeline is designed for controlled, incremental source loading.

## Flow

1. Seed source catalog.
2. Discover URLs with Scrapy, robots.txt enabled, and a per-source page limit.
3. Store or update `crawl_urls` by normalized URL.
4. Skip already processed URLs unless they are failed or queued for retry.
5. Fetch HTML/PDF/MP3 with retry and anti-block detection.
6. Parse metadata and clean content.
7. Upsert `documents` by canonical URL and content hash.
8. Store assets in R2/MinIO.
9. Mark documents ready for textual search.
10. Queue indexing later without forcing OpenAI embeddings.

## Incremental Rules

- `documents.canonical_url` prevents duplicate URLs.
- `documents.content_hash` detects changed content.
- unchanged documents increment `documents_skipped`.
- updated documents reset `is_indexed=false`.
- failed jobs store `documents_failed` and error details.
- every source run creates an `ingestion_jobs` row.

## Job Metrics

`ingestion_jobs` tracks:

- `source_id`
- `source`
- `status`
- `started_at`
- `finished_at`
- `documents_found`
- `documents_created`
- `documents_updated`
- `documents_skipped`
- `documents_failed`
- `errors`

## Limited Crawl Validation

Recommended local validation:

```bash
docker compose exec scraper-api alembic upgrade head
docker compose exec scraper-api python scripts/seed_sources.py
curl -X POST http://localhost:8000/api/admin/sources/byu_speeches_en/crawl \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 00000000-0000-4000-8000-0000000000ad" \
  -H "X-User-Role: admin" \
  -d "{\"maxPagesPerRun\":3}"
```

Then verify:

```bash
curl http://localhost:8000/api/ingestion/status
curl "http://localhost:8000/api/documents?sourceType=byu_speeches_en&limit=5"
```

## Embeddings

Do not automatically generate embeddings for massive loads. Documents remain searchable by PostgreSQL textual fallback immediately. Run source-specific indexing only after estimating cost and confirming OpenAI quota.
