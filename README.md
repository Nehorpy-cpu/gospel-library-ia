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

Control de costos IA:

```txt
AI_COST_MODE=balanced
RAG_TOP_K=12
CHUNK_SIZE=650
CHUNK_OVERLAP=120
MAX_DAILY_EMBEDDING_TOKENS=100000
MAX_USER_CHAT_MESSAGES_PER_DAY=50
MAX_USER_TALK_BUILDER_PER_DAY=20
EMBEDDING_TOKEN_PRICE_PER_1K=0.00013
```

Ver tambien [docs/ai-costs.md](docs/ai-costs.md) para estimacion previa, cache de embeddings, limites y manejo de `insufficient_quota`.

Auth local/produccion:

```txt
AUTH_PROVIDER=clerk
ALLOW_DEV_AUTH_HEADERS=true
CLERK_SECRET_KEY=
CLERK_JWKS_URL=
CLERK_JWT_ISSUER=
CLERK_WEBHOOK_SECRET=
CLERK_ADMIN_EMAILS=
ADMIN_USER_IDS=
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=
```

No usar `NEXT_PUBLIC_OPENAI_API_KEY`. Las claves OpenAI y Clerk secretas solo pertenecen a backend/workers.

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
GET  /api/profile/preferences
PATCH /api/profile/preferences
POST /api/admin/scrape
POST /api/admin/reindex
POST /api/admin/jobs/:id/retry
GET  /api/admin/status
GET  /api/admin/sources
PATCH /api/admin/sources/:sourceId
POST /api/admin/sources/:sourceId/crawl
POST /api/exports/study
```

El frontend consume esos endpoints con proxy interno de Next.

## Fuentes e ingesta masiva controlada

El catalogo de fuentes vive en PostgreSQL `sources` y se siembra con:

```bash
docker compose exec scraper-api python scripts/seed_sources.py
```

Fuentes configuradas:

```txt
byu_speeches_es
byu_speeches_en
discursos_sud
general_conference
church_manuals
joseph_smith_papers
byu_rsc
come_follow_me
teachings_presidents
scriptures
```

La ingesta masiva siempre debe ser limitada. Desde Admin se puede listar fuentes,
activar/desactivar, ajustar `maxPagesPerRun` y ejecutar crawl por fuente. Los
documentos quedan disponibles para busqueda textual aunque no se generen
embeddings.

Docs:

```txt
docs/sources.md
docs/ingestion.md
docs/scraping-ethics.md
```

## Auth y privacidad

Proveedor elegido: Clerk.

Modo local:

```txt
/sign-in
/sign-up
/access-denied
```

En local se puede entrar como usuario demo o admin local. Produccion debe usar `Authorization: Bearer <Clerk JWT>` y `ALLOW_DEV_AUTH_HEADERS=false`.

Rutas frontend protegidas:

```txt
/study
/study/new
/study/:workspaceId
/favorites
/history
/admin
```

Backend protegido:

```txt
/api/study-workspaces/*
/api/study/*
/api/profile/*
/api/exports/*
/api/talk-builder/*
/api/admin/*
```

Admin se asigna por `public_metadata.role=admin` en Clerk, `CLERK_ADMIN_EMAILS` o `ADMIN_USER_IDS`.

Guia completa:

```txt
docs/auth.md
```

## StudyWorkspace runtime

Ruta canonica actual:

```txt
GET    /api/study-workspaces
POST   /api/study-workspaces
GET    /api/study-workspaces/:id
PATCH  /api/study-workspaces/:id
DELETE /api/study-workspaces/:id
```

Aliases REST disponibles para auditorias y clientes nuevos:

```txt
GET    /api/study/workspaces
POST   /api/study/workspaces
GET    /api/study/workspaces/:id
PATCH  /api/study/workspaces/:id
DELETE /api/study/workspaces/:id
GET    /api/study/workspaces/:id/related
GET    /api/study/workspaces/:id/source-filters
POST   /api/study/workspaces/:id/source-filters
GET    /api/study/workspaces/:id/notes
POST   /api/study/workspaces/:id/notes
GET    /api/study/workspaces/:id/citations
POST   /api/study/workspaces/:id/citations
GET    /api/study/workspaces/:id/highlights
POST   /api/study/workspaces/:id/highlights
GET    /api/study/workspaces/:id/sticky-notes
POST   /api/study/workspaces/:id/sticky-notes
```

El frontend expone `/study/new` para crear un StudyWorkspace real y redirigir a
`/study/[workspaceId]`.

## Fallback textual

Cuando Qdrant `doctrinal_chunks_v1` tiene `points_count = 0`, o OpenAI responde
`missing_api_key` / `insufficient_quota`, la app sigue operando en modo basico:

```txt
POST /api/search -> mode: textual_fallback
POST /api/chat   -> respuesta clara con fuentes reales si hay coincidencias
GET  /api/study/workspaces/:id/related -> mode: textual_fallback
```

En este modo no se llama OpenAI desde seeds ni tests locales. Para volver al
modo semantico, configurar `OPENAI_API_KEY`, ejecutar `pnpm embed` y confirmar
que Qdrant tenga `points_count > 0`.

## Validacion runtime

```bash
corepack pnpm install
corepack pnpm build
corepack pnpm test
python -m unittest discover apps/api/tests
python -m unittest discover rag/tests
corepack pnpm --dir apps/web lint
corepack pnpm --dir apps/web typecheck
corepack pnpm --dir apps/web build
docker compose config --quiet
docker compose down
docker compose build --no-cache
docker compose up -d --wait
docker compose ps
```

Si `docker compose` no puede conectarse al daemon, iniciar Docker Desktop y
repetir la validacion. Si la base persistida viene de una fase anterior, ejecutar:

```bash
docker compose exec scraper-api alembic upgrade head
docker compose exec rag-api alembic upgrade head
```

Alembic mantiene cadenas independientes dentro de PostgreSQL:

- scraper: `public.scraper_alembic_version`
- RAG: `public.rag_alembic_version`

La tabla histórica compartida, si existe, se conserva como
`public.legacy_alembic_version` y no controla ninguna migración activa.

Para auditar y reparar metadatos históricos deterministas:

```bash
# Simulación sin escritura
docker compose exec scraper-api python scripts/repair_metadata.py

# Aplicación auditada e idempotente
docker compose exec scraper-api python scripts/repair_metadata.py --apply
```

Las reparaciones quedan registradas en `document_metadata_repair_audit`.
No se invoca OpenAI y los documentos afectados quedan pendientes de
reindexación incremental.

## QA final local

Checklist manual y evidencia de la ultima auditoria:

```txt
docs/QA_FINAL_CHECKLIST.md
```

Rutas frontend verificadas por HTTP:

```txt
/
/library
/admin
/study
/study/new
/study/[workspaceId]
/collections
/favorites
/history
/authors
/search
```

Flujos StudyWorkspace verificados con datos reales:

```txt
workspace create/list/open/delete
notes create/update/delete
citations create/delete
sticky-notes create/update/delete
source-filters create/delete
related documents textual fallback
```

Observaciones actuales:

```txt
Qdrant doctrinal_chunks_v1: green, points_count=0
Search/chat: textual_fallback activo sin 500
Metadata: autores/temas derivados de documentos reales, calidad pendiente de limpieza
```

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

## Regla de liderazgo vigente

El analisis doctrinal trata la Primera Presidencia y el Cuorum de los Doce
Apostoles como informacion sensible al tiempo. Cuando existan fuentes oficiales
recientes en el contexto RAG, la respuesta debe verificar la conformacion actual
antes de generar contenido que dependa de lideres vigentes.

Referencia local para 2026:

```txt
Primera Presidencia:
- Presidente Dallin H. Oaks
- Presidente Henry B. Eyring, Primer Consejero
- Presidente D. Todd Christofferson, Segundo Consejero

Cuorum de los Doce Apostoles:
- David A. Bednar
- Dieter F. Uchtdorf
- Quentin L. Cook
- Neil L. Andersen
- Ronald A. Rasband
- Gary E. Stevenson
- Dale G. Renlund
- Gerrit W. Gong
- Ulisses Soares
- Patrick Kearon
- Gérald Caussé
- Clark G. Gilbert
```

Modo historico/devocional: puede usar citas del Presidente Russell M. Nelson
como profeta anterior y lider doctrinal relevante. Modo liderazgo vigente:
prioriza fuentes/citas del Presidente Dallin H. Oaks como Presidente actual de la
Iglesia cuando el contexto lo respalde.

## Enfoque por llamamiento

La app permite que cada usuario configure su llamamiento en `/preferences`.
El catalogo inicial vive en:

```txt
packages/shared/church-callings.json
```

Campos de preferencia:

```txt
callingCategory
callingName
customCallingName
callingFocusEnabled
```

Cuando el enfoque esta activo, `/api/chat` envia `calling_focus` al RAG. La
doctrina no se adapta ni se cambia por llamamiento; solo cambian la aplicacion,
el enfasis, las preguntas de reflexion y los ejemplos practicos. Si no hay
llamamiento seleccionado, el analisis usa un enfoque general de discipulado.

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

## Production Deploy

La fase cloud esta preparada para un despliegue manual en Vercel, Railway/Render,
Qdrant Cloud, Cloudflare R2, Supabase/Railway PostgreSQL y Upstash/Railway Redis.
No hay claves reales en el repositorio y los archivos `.env.production` reales
deben vivir solo en el proveedor cloud.

Ejemplos de variables:

```txt
apps/web/.env.production.example
apps/api/.env.production.example
rag/.env.production.example
scraper/.env.production.example
workers/.env.production.example
```

Guia por proveedor:

```txt
docs/deploy/vercel.md
docs/deploy/railway.md
docs/deploy/qdrant-cloud.md
docs/deploy/cloudflare-r2.md
docs/deploy/supabase-postgres.md
docs/deploy/upstash-redis.md
docs/deploy/production-checklist.md
```

Scripts seguros de preparacion/verificacion:

```bash
pnpm deploy:web
pnpm deploy:api
pnpm migrate:prod
pnpm seed:prod
pnpm verify:prod
```

`deploy:web` no incluye secretos y solo prepara el build antes del deploy manual.
`deploy:api`, `migrate:prod` y `seed:prod` imprimen instrucciones seguras o
validan variables; no ejecutan un despliegue cloud automatico. `verify:prod`
requiere:

```txt
PROD_APP_URL
PROD_API_URL
PROD_RAG_URL
PROD_SCRAPER_URL
```

CORS en produccion debe usar dominios explicitos:

```txt
CORS_ORIGINS=http://localhost:3000,https://app.gospel-library-ia.example
```

No usar `*` en produccion salvo una excepcion temporal y documentada.

## Beta privada

Gospel Library IA Beta usa version `0.1.0-beta` y entorno `beta`. La landing local esta en:

```txt
http://localhost:3000/beta
```

Controles beta principales:

```txt
BETA_ALLOWLIST_ENABLED=false
BETA_MAX_WORKSPACES_PER_USER=12
MAX_USER_CHAT_MESSAGES_PER_DAY=50
MAX_USER_TALK_BUILDER_PER_DAY=20
MAX_USER_EXPORTS_PER_DAY=10
```

Docs:

```txt
CHANGELOG.md
docs/beta-checklist.md
docs/demo-script.md
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

Fase 19 documenta controles de costo, cache y limites diarios en `docs/ai-costs.md`.
