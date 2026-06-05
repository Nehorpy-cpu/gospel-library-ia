# Production Deploy Checklist

## Provisioning

- [ ] Create production PostgreSQL with backups/PITR.
- [ ] Create production Redis.
- [ ] Create Qdrant Cloud cluster.
- [ ] Create `doctrinal_chunks_v1` with 3072 dimensions and cosine distance.
- [ ] Create Cloudflare R2 bucket.
- [ ] Create Cloudflare DNS records and SSL.

## Secrets

- [ ] Fill `apps/web/.env.production.example` in Vercel.
- [ ] Fill `apps/api/.env.production.example` in Railway/Render.
- [ ] Fill `rag/.env.production.example` in Railway/Render.
- [ ] Fill `scraper/.env.production.example` in Railway/Render.
- [ ] Fill `workers/.env.production.example` in worker services.
- [ ] Confirm no `.env.production` file is committed.
- [ ] Confirm no `NEXT_PUBLIC_OPENAI_API_KEY` exists.

## Backend release

- [ ] Deploy `rag-api`.
- [ ] Deploy `scraper-api`.
- [ ] Deploy `api`.
- [ ] Run scraper Alembic migrations.
- [ ] Run RAG Alembic migrations.
- [ ] Initialize Qdrant collection.
- [ ] Verify `GET /`, `/health`, and `/ready` for every API.

## Workers

- [ ] Deploy scraper scheduler.
- [ ] Deploy scraper scraping worker.
- [ ] Deploy scraper assets worker.
- [ ] Deploy scraper OCR worker.
- [ ] Deploy scraper indexing worker.
- [ ] Deploy RAG indexing worker.
- [ ] Confirm logs show Redis connection and registered queues.

## Frontend

- [ ] Deploy Vercel preview.
- [ ] Verify `/api/health`.
- [ ] Verify `/`, `/library`, `/search`, `/study`, `/study/new`, `/admin`.
- [ ] Promote to production.

## Smoke tests

- [ ] `GET /api/documents`
- [ ] `GET /api/documents/summary`
- [ ] `POST /api/search`
- [ ] `POST /api/chat`
- [ ] Create StudyWorkspace.
- [ ] Create note/citation/post-it.
- [ ] Trigger small scraping job.
- [ ] Trigger small indexing job.
- [ ] Confirm Qdrant `points_count`.
- [ ] Confirm textual fallback still works when vectors are zero.
