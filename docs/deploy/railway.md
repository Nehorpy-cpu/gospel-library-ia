# Railway or Render Deploy

## Services

Deploy each backend as an independent service. Use the repository root, but set
the service root/build context per service.

```txt
apps/api  -> uvicorn app.main:app --host 0.0.0.0 --port $PORT
rag       -> uvicorn app.main:app --host 0.0.0.0 --port $PORT
scraper   -> uvicorn app.api:app --host 0.0.0.0 --port $PORT
```

Workers:

```txt
scraper-scheduler       celery -A app.workers.celery_app beat --loglevel=info
scraper-worker-scraping celery -A app.workers.celery_app worker -Q scraping --loglevel=info --concurrency=4
scraper-worker-assets   celery -A app.workers.celery_app worker -Q assets --loglevel=info --concurrency=4
scraper-worker-ocr      celery -A app.workers.celery_app worker -Q ocr --loglevel=info --concurrency=2
scraper-worker-indexing celery -A app.workers.celery_app worker -Q indexing --loglevel=info --concurrency=2
rag-worker-indexing     celery -A app.workers.celery_app worker -Q rag-indexing --loglevel=info --concurrency=2
```

## Variables

Use:

```txt
apps/api/.env.production.example
rag/.env.production.example
scraper/.env.production.example
workers/.env.production.example
```

Production `CORS_ORIGINS` must include local development and the real frontend
domain only. Do not use `*`.

## Healthchecks

Configure provider healthchecks:

```txt
GET /
GET /health
GET /ready
```

## Render API build

Para el servicio API de Render, usar `apps/api` como root/build context.

Comando de build:

```txt
pip install --upgrade pip && pip install .
```

Comando de start:

```txt
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

`apps/api/pyproject.toml` configura setuptools para empaquetar solo `app`.
Esto evita que carpetas top-level como `migrations`, `scripts` o `tests` sean
detectadas como paquetes Python durante `pip install .`. La carpeta
`migrations` debe permanecer como migraciones SQL/seguridad, no como paquete
instalable.

## Release order

1. Provision PostgreSQL, Redis, Qdrant Cloud, and R2.
2. Deploy `rag-api`, `scraper-api`, and `api`.
3. Run migrations from backend shells.
4. Initialize Qdrant collection.
5. Deploy workers.
6. Deploy web.
7. Run smoke tests for `/api/documents`, `/api/search`, `/api/chat`, study,
   admin, scraping, and indexing.
