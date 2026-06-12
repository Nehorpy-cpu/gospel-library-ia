# Gospel Library IA Production Runbook

## Release Gates

Run these checks before any production release:

```bash
pnpm install --frozen-lockfile
pnpm --dir apps/web typecheck
pnpm --dir apps/web build
python -m compileall apps/api/app scraper/app rag/app
python -m unittest discover apps/api/tests
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

Expected local health endpoints:

```txt
web:         http://localhost:3000/api/health
api:         http://localhost:8000/ready
scraper-api: http://localhost:8080/ready
rag-api:     http://localhost:8090/ready
qdrant:      http://localhost:6333/readyz
```

## Docker Readiness

Healthchecks are expected on:

```txt
web          /api/health
api          /ready
scraper-api  /ready
rag-api      /ready
postgres     pg_isready
redis        redis-cli ping
qdrant       /readyz over port 6333
```

Workers are supervised with `restart: unless-stopped` and validated through queue depth, logs, and ingestion job status.

Useful commands:

```bash
docker compose logs web --tail=100
docker compose logs api --tail=100
docker compose logs rag-api --tail=100
docker compose logs scraper-api --tail=100
docker compose logs scraper-worker-scraping --tail=100
docker compose logs rag-worker-indexing --tail=100
```

## Vercel Frontend

Project root:

```txt
apps/web
```

Required variables:

```txt
NEXT_PUBLIC_APP_URL=https://gospellibraryia.example.com
NEXT_PUBLIC_RAG_API_URL=/api
API_INTERNAL_URL=https://api.gospellibraryia.example.com
RAG_INTERNAL_URL=https://rag.gospellibraryia.example.com
NEXT_PUBLIC_SENTRY_DSN=
```

Do not configure OpenAI secrets in Vercel frontend variables.

## Railway Services

Create these services:

```txt
api      root apps/api   command uvicorn app.main:app --host 0.0.0.0 --port $PORT
rag      root rag        command uvicorn app.main:app --host 0.0.0.0 --port $PORT
scraper  root scraper    command uvicorn app.api:app --host 0.0.0.0 --port $PORT
workers  root scraper    command celery -A app.workers.celery_app worker -Q scraping --loglevel=info
```

Use private service URLs for API-to-API traffic when possible.

## Kubernetes

Apply:

```bash
kubectl apply -k infra/k8s/overlays/production
kubectl rollout status deployment/web -n gospel-library --timeout=180s
kubectl rollout status deployment/api -n gospel-library --timeout=180s
kubectl rollout status deployment/rag-api -n gospel-library --timeout=180s
kubectl rollout status deployment/scraper-api -n gospel-library --timeout=180s
```

Required cluster components:

```txt
ingress-nginx
cert-manager
metrics-server
External Secrets Operator or sealed secrets
Prometheus Operator if using ServiceMonitor resources
```

Rollback:

```bash
kubectl rollout undo deployment/web -n gospel-library
kubectl rollout undo deployment/api -n gospel-library
kubectl rollout undo deployment/rag-api -n gospel-library
kubectl rollout undo deployment/scraper-api -n gospel-library
```

## Qdrant

Production options:

```txt
preferred: Qdrant Cloud
fallback: infra/k8s/base/platform/qdrant.yaml StatefulSet
```

Collection:

```txt
doctrinal_chunks_v1
vector size: 3072
distance: cosine
```

Validate:

```bash
curl "$QDRANT_URL/readyz"
curl "$QDRANT_URL/collections/doctrinal_chunks_v1"
```

Snapshots:

```bash
curl -X POST "$QDRANT_URL/collections/doctrinal_chunks_v1/snapshots"
```

Store snapshots in Cloudflare R2 under `qdrant-snapshots/`.

## Cloudflare

DNS:

```txt
gospellibraryia.example.com      -> Vercel or Kubernetes ingress
api.gospellibraryia.example.com  -> Railway API gateway or Kubernetes ingress
assets.gospellibraryia.example.com -> R2/custom domain
```

Enable:

```txt
SSL Full strict
Always Use HTTPS
WAF managed rules
bot protection
rate limits for /api/chat and /api/search
Zero Trust Access for /admin and scraper admin routes
cache bypass for /api/*
cache everything for /_next/static/*
```

Security headers are set by API middleware and ingress. Cloudflare Transform Rules may enforce the same headers at the edge.

## Observability

Required before production traffic:

```txt
Sentry projects: web, api, rag, scraper
Prometheus targets: api, rag-api, scraper-api, redis, qdrant
Grafana dashboards: latency, queue depth, ingestion errors, vector counts
Loki or managed log drain for JSON logs
Alerts: 5xx rate, queue backlog, failed jobs, no vectors, OpenAI quota, database errors
```

Local observability:

```bash
docker compose --profile observability up -d
```

## Backup And Restore

The tested local procedures and safety checks are documented in:

```txt
docs/BACKUP_RESTORE_RUNBOOK.md
docs/ROLLBACK_RUNBOOK.md
```

Production PostgreSQL must use managed PITR plus daily logical dumps. Keep 7
daily, 4 weekly, and 6 monthly copies, and run a monthly isolated restore drill.

Qdrant:

```txt
Create scheduled snapshots.
Store snapshots in R2.
Keep PostgreSQL chunk metadata so vectors can be rebuilt if needed.
```

R2:

```txt
Enable versioning for assets and backups.
Set lifecycle rules for exports/temp objects.
Use scoped API tokens per bucket.
```

## Smoke Tests

After deploy:

```bash
curl https://gospellibraryia.example.com/api/health
curl https://api.gospellibraryia.example.com/ready
curl https://rag.gospellibraryia.example.com/ready
curl https://scraper.gospellibraryia.example.com/ready
```

Then verify in the app:

```txt
Home loads
Library lists real documents
Search returns PostgreSQL fallback or semantic results
Chat returns grounded sources or clear no-embedding status
Admin Datos cargados shows PostgreSQL and Qdrant state
Scraping action returns task id
Reindex action returns task id or clear OpenAI quota/key status
StudyWorkspace private data is scoped by user
Exports download Markdown/PDF with source attribution
```

## Incident Shortcuts

Queue backlog:

```bash
kubectl scale deployment rag-worker-indexing --replicas=8 -n gospel-library
kubectl scale deployment scraper-worker-scraping --replicas=8 -n gospel-library
```

OpenAI quota:

```txt
Keep app in no-embedding mode.
Use PostgreSQL text fallback.
Pause indexing workers if retries are burning quota.
```

Scraper block rate:

```txt
Lower concurrency.
Rotate user agents/proxies.
Inspect latest ingestion errors in /admin.
```
