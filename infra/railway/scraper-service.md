# Railway Scraper Service

## API Service

```txt
root: scraper
start command: uvicorn app.api:app --host 0.0.0.0 --port $PORT
```

## Worker Services

Create separate Railway services from the same root:

```txt
celery -A app.workers.celery_app worker -Q scraping --loglevel=info --concurrency=4
celery -A app.workers.celery_app worker -Q assets --loglevel=info --concurrency=4
celery -A app.workers.celery_app worker -Q ocr --loglevel=info --concurrency=2
celery -A app.workers.celery_app beat --loglevel=info
```

## Variables

```txt
DATABASE_URL
REDIS_URL
R2_ENDPOINT_URL
R2_ACCESS_KEY_ID
R2_SECRET_ACCESS_KEY
R2_BUCKET
SENTRY_DSN
```
