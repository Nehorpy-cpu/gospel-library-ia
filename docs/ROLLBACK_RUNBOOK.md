# Release rollback runbook

## Decision gate

Rollback when health checks fail persistently, migrations corrupt behavior,
5xx rates rise materially, or data integrity checks fail. Pause ingestion and
indexing before database intervention.

## Application rollback

1. Keep the current database backup and service logs.
2. Redeploy the previously verified immutable image tag.
3. Roll back web, API, RAG, scraper, then workers.
4. Verify `/ready`, `/api/documents`, `/api/search`, and `/api/chat`.
5. Resume workers only after the read path is stable.

Kubernetes:

```bash
kubectl rollout undo deployment/web -n gospel-library
kubectl rollout undo deployment/api -n gospel-library
kubectl rollout undo deployment/rag-api -n gospel-library
kubectl rollout undo deployment/scraper-api -n gospel-library
```

## Database rollback

Alembic owns the current runtime schema:

```bash
cd scraper && alembic current && alembic downgrade <verified_revision>
cd rag && alembic current && alembic downgrade <verified_revision>
```

Use a migration downgrade only when that downgrade was tested and data loss is
not possible. Otherwise restore PostgreSQL to a new database from PITR or the
pre-release dump, verify counts, and switch the connection string.

Prisma is a schema/client contract in the current deployment. Do not run
`prisma migrate deploy` unless Prisma has explicitly been selected as the sole
production migration owner and the migration history has been repaired.

## Qdrant rollback

Restore a verified snapshot into a new collection first. Compare collection
status, point count, vector count, and sample searches. Switch
`QDRANT_COLLECTION` only after validation. Keep `doctrinal_chunks_v1` unchanged
until the replacement is proven.

## Object storage rollback

Restore a previous R2 object version or copy a verified backup into a temporary
prefix. Validate content length and checksum before changing application
references.

## Completion

Record the trigger, image versions, migration revisions, backup identifiers,
checksums, counts, smoke results, and follow-up owner.
