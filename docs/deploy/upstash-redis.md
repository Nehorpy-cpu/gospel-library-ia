# Upstash or Railway Redis

## Usage

Redis backs Celery queues, lightweight cache, rate limiting, and background
worker coordination.

## Variables

```txt
REDIS_URL=rediss://default:PASSWORD@HOST:6379
```

Use separate logical databases or separate Redis instances for staging and
production. Keep queue names stable:

```txt
scraping
assets
ocr
indexing
rag-indexing
```

## Verification

1. Confirm backend services can connect at startup.
2. Confirm workers appear as running in provider logs.
3. Trigger a small scrape.
4. Confirm indexing jobs move through Redis queues.
