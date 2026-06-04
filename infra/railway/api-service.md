# Railway API Gateway Service

## Service

```txt
root: apps/api
start command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
healthcheck path: /ready
```

## Variables

```txt
DATABASE_URL
REDIS_URL
QDRANT_URL
QDRANT_API_KEY
QDRANT_COLLECTION
RAG_API_URL
SCRAPER_API_URL
OPENAI_API_KEY
OPENAI_EMBEDDING_MODEL
OPENAI_CHAT_MODEL
CORS_ORIGINS
SENTRY_DSN
```

## Notes

- Keep `RAG_API_URL` and `SCRAPER_API_URL` on private Railway service URLs when possible.
- Set `CORS_ORIGINS` to the production Vercel domain and any approved preview domains.
- Use `/health` for liveness and `/ready` before routing production traffic.
- Do not expose `OPENAI_API_KEY` to the web service or any `NEXT_PUBLIC_*` variable.
