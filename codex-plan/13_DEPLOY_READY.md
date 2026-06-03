# Phase 13 - Deploy Ready

## Goal

Prepare Gospel Library IA for production deployment.

## Scope

- Docker.
- Kubernetes readiness.
- CI/CD.
- Vercel.
- Railway.
- Cloudflare.
- Monitoring and logging.
- Backups and secrets.

## Required work

1. Verify `docker-compose.yml` healthchecks.
2. Verify Dockerfiles for web, api, rag, scraper, and workers.
3. Verify GitHub Actions.
4. Prepare Vercel frontend deployment.
5. Prepare Railway backend and worker deployment.
6. Prepare Qdrant deployment.
7. Configure Cloudflare DNS, CDN, SSL, WAF, and security headers.
8. Configure Redis queues and rate limiting.
9. Configure Sentry and observability.
10. Document backup and restore strategy.
11. Create final production checklist.

## Acceptance criteria

- Local Docker stack is healthy.
- CI/CD workflows are documented and runnable.
- Required secrets are documented but not committed.
- Production runbook exists.

## Verification

```bash
docker compose ps
pnpm build
pnpm test
```

## Non-goals

- Do not add product features in this phase.

