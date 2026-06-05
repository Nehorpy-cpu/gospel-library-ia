# Phase 16 - Deploy Local To Cloud

## Objective

Preparar Gospel Library IA para pasar de entorno local a entorno cloud real sin
incluir claves reales, sin subir `.env` real y sin romper el entorno local.

## Target Architecture

- Frontend: Vercel.
- Backend API: Railway o Render.
- Scraper API: Railway o Render.
- RAG API: Railway o Render.
- Workers: Railway/Render worker services.
- PostgreSQL: Railway PostgreSQL o Supabase.
- Redis: Upstash o Railway Redis.
- Vector DB: Qdrant Cloud.
- Storage: Cloudflare R2 o S3 compatible.
- Domain/DNS: Cloudflare.

## Required Work

1. Review deploy structure for `apps/web`, `apps/api`, `scraper`, `rag`,
   workers, Dockerfiles, and `docker-compose.yml`.
2. Create production example env files for web, API, RAG, scraper, and workers.
3. Document required production variables without real secrets.
4. Create deploy guides:
   - `docs/deploy/vercel.md`
   - `docs/deploy/railway.md`
   - `docs/deploy/qdrant-cloud.md`
   - `docs/deploy/cloudflare-r2.md`
   - `docs/deploy/supabase-postgres.md`
   - `docs/deploy/upstash-redis.md`
5. Create `docs/deploy/production-checklist.md`.
6. Keep production CORS explicit with local and production domains, never
   wildcard by default.
7. Confirm production healthcheck strategy for `/`, `/health`, and `/ready`.
8. Add safe production scripts:
   - `pnpm deploy:web`
   - `pnpm deploy:api`
   - `pnpm migrate:prod`
   - `pnpm seed:prod`
   - `pnpm verify:prod`
9. Separate local Docker from cloud deployment through docs and production env
   examples without breaking local Docker.
10. Document migration, storage, workers, and rollback strategy.
11. Do not trigger real cloud deploy automatically.

## Validation

```bash
corepack pnpm build
corepack pnpm test
docker compose config --quiet
```

Also verify that `.env.production.example` files contain no real secrets.

## Completion

1. Mark `16_DEPLOY_LOCAL_TO_CLOUD` as `DONE` in `PROGRESS.md`.
2. Commit with:

```txt
chore: fase 16 - deploy local to cloud
```
