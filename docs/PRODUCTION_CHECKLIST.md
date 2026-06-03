# Gospel Library IA Production Checklist

## Domains And Edge

- [ ] Cloudflare DNS configured.
- [ ] SSL mode Full strict.
- [ ] WAF enabled.
- [ ] Bot protection enabled.
- [ ] API rate limits configured.
- [ ] Admin routes protected with Cloudflare Access or equivalent.
- [ ] HSTS enabled after first successful production deploy.
- [ ] CDN cache rules for static assets.

## Secrets

- [ ] No real secrets in repo.
- [ ] GitHub Actions secrets configured.
- [ ] Vercel env vars configured.
- [ ] Railway or Kubernetes secrets configured.
- [ ] OpenAI key scoped/monitored.
- [ ] R2 access keys scoped to bucket.
- [ ] Database credentials rotated before launch.

## Data

- [ ] Managed PostgreSQL with PITR.
- [ ] PostgreSQL extensions installed.
- [ ] Prisma migration applied.
- [ ] Post-migrate SQL applied.
- [ ] Seed data applied.
- [ ] Qdrant collection created.
- [ ] Redis persistence or managed Redis configured.
- [ ] R2 bucket versioning enabled.

## Backups

- [ ] Daily PostgreSQL backups to R2.
- [ ] Monthly restore drill scheduled.
- [ ] Qdrant snapshots configured.
- [ ] Export/temp object lifecycle policies configured.
- [ ] Backup alerting configured.

## Observability

- [ ] Prometheus scraping APIs.
- [ ] Grafana dashboards installed.
- [ ] Loki/promtail or managed logging configured.
- [ ] Sentry projects configured.
- [ ] Alert rules configured.
- [ ] Slow query monitoring enabled.
- [ ] OpenAI cost/token monitoring enabled.

## CI/CD

- [ ] CI workflow green.
- [ ] Security workflow green.
- [ ] GHCR image push works.
- [ ] Vercel deploy works.
- [ ] Railway or Kubernetes deploy works.
- [ ] Rollback procedure documented.

## Kubernetes

- [ ] Ingress controller installed.
- [ ] cert-manager installed.
- [ ] metrics-server installed.
- [ ] HPA functional.
- [ ] Resource requests/limits tuned.
- [ ] Worker nodes sized for OCR.
- [ ] Network policies added if required.
- [ ] External Secrets Operator configured if used.

## Security

- [ ] Security headers verified.
- [ ] CORS allowlist configured.
- [ ] Admin RBAC tested.
- [ ] Upload limits tested.
- [ ] Prompt injection guardrails tested.
- [ ] Dependency scan reviewed.
- [ ] Container scan reviewed.

## Launch

- [ ] Smoke test home/search/chat.
- [ ] Smoke test ingestion job.
- [ ] Smoke test RAG indexing.
- [ ] Smoke test PDF/OCR asset flow.
- [ ] Smoke test backup job.
- [ ] Monitor p95 latency.
- [ ] Monitor queue depth.
- [ ] Monitor Sentry for first 24 hours.
