# Railway RAG Service

## Service

```txt
root: rag
start command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Variables

```txt
DATABASE_URL
REDIS_URL
OPENAI_API_KEY
QDRANT_URL
QDRANT_API_KEY
QDRANT_COLLECTION
SENTRY_DSN
```

## Notes

- Use Railway Postgres only for small staging. Production should use managed Postgres with PITR.
- Use managed Redis for queues.
- Prefer Qdrant Cloud for vector database.
- Add a private networking route between services when available.
