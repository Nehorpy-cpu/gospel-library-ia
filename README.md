# Gospel Library IA

Plataforma web doctrinal con scraping distribuido, ingesta, RAG, Qdrant, PostgreSQL, Redis, frontend Next.js y backend FastAPI.

## Servicios

```txt
web                 Next.js 15
api                 FastAPI gateway final
rag-api             RAG, embeddings, Qdrant, chat
rag-worker-indexing Embeddings/indexacion
scraper-api         Admin scraping
scraper workers     scraping/assets/ocr/indexing
postgres            PostgreSQL
redis               queues/cache
qdrant              vector database
minio               R2 local compatible
```

## Instalacion local

```bash
pnpm install
docker compose up --build
```

Inicializar DB/Qdrant/demo:

```bash
pnpm seed
```

Abrir:

```txt
Frontend: http://localhost:3000
Main API: http://localhost:8000/docs
Scraper API: http://localhost:8080/docs
RAG API: http://localhost:8090/docs
Qdrant: http://localhost:6333/dashboard
```

## Variables

Archivos:

```txt
.env.example
apps/web/.env.example
apps/api/.env.example
services/scraper/.env.example
services/embeddings/.env.example
```

Minimo real para IA:

```txt
OPENAI_API_KEY=
DATABASE_URL=
REDIS_URL=
QDRANT_URL=
QDRANT_COLLECTION=doctrinal_chunks_v1
```

## Comandos

```bash
pnpm dev
pnpm build
pnpm start
pnpm scrape
pnpm ingest
pnpm embed
pnpm seed
pnpm test
pnpm prisma:generate
pnpm prisma:migrate
pnpm prisma:seed
```

## Endpoints finales

```txt
POST /api/search
POST /api/chat
GET  /api/documents
GET  /api/documents/:id
GET  /api/authors
GET  /api/topics
GET  /api/ingestion/status
GET  /api/admin/errors
POST /api/admin/scrape
POST /api/admin/reindex
POST /api/admin/jobs/:id/retry
GET  /api/admin/status
POST /api/exports/study
```

El frontend consume esos endpoints con proxy interno de Next.

## Prisma

```bash
cd packages/database
npm install
npm run generate
npm run migrate:deploy
npm run migrate:post
npm run seed:sql
```

El SQL post-migrate agrega FTS, GIN, trigram, JSONB indexes y plantillas de particionado.

## Qdrant

Coleccion principal:

```txt
doctrinal_chunks_v1
dimensions: 3072
distance: cosine
```

Payload indexado:

```txt
author
language
source_key
category
topic
published_at
tags
document_id
```

Inicializar:

```bash
docker compose exec api python scripts/init_qdrant.py
```

## Deploy Vercel

Root:

```txt
apps/web
```

Variables:

```txt
NEXT_PUBLIC_RAG_API_URL=/api
API_INTERNAL_URL=https://api.tu-dominio.com
NEXT_PUBLIC_APP_URL=https://tu-dominio.com
```

Workflow:

```txt
.github/workflows/deploy-vercel.yml
```

## Deploy backend Railway

Servicios:

```txt
api           apps/api, uvicorn app.main:app --host 0.0.0.0 --port $PORT
rag           rag, uvicorn app.main:app --host 0.0.0.0 --port $PORT
scraper       scraper, uvicorn app.api:app --host 0.0.0.0 --port $PORT
workers       scraper/rag celery commands por cola
```

Guia:

```txt
infra/railway
```

## Deploy Qdrant

Recomendado:

```txt
Qdrant Cloud para produccion
Qdrant Docker/Kubernetes para local/staging
```

Configurar:

```txt
QDRANT_URL
QDRANT_API_KEY
QDRANT_COLLECTION
```

## Produccion

1. Configurar Cloudflare DNS/WAF/CDN/SSL.
2. Configurar PostgreSQL administrado con PITR.
3. Configurar Redis administrado.
4. Configurar Qdrant Cloud.
5. Configurar Cloudflare R2.
6. Configurar secretos en GitHub/Vercel/Railway/Kubernetes.
7. Ejecutar Prisma migrations.
8. Ejecutar SQL post-migrate.
9. Inicializar Qdrant.
10. Ejecutar scraping.
11. Ejecutar embeddings.
12. Verificar `/api/admin/status`.
13. Monitorear Sentry/Grafana/Loki.

Docs:

```txt
docs/DEVOPS_ARCHITECTURE.md
docs/PRODUCTION_CHECKLIST.md
docs/RUNBOOK.md
infra/cloudflare/waf-rules.md
infra/railway/api-service.md
```

## Codex phased development

La ejecucion por fases vive en:

```txt
codex-plan/00_ORCHESTRATOR.md
codex-plan/PROGRESS.md
```

Reglas principales:

1. Ejecutar solo una fase a la vez.
2. No implementar fases futuras hasta verificar la fase actual.
3. No usar datos mock cuando existan datos reales en PostgreSQL, Qdrant, Redis o workers.
4. No llamar OpenAI en seeds ni tests locales.
5. Mantener la app usable con busqueda textual cuando no haya embeddings.
