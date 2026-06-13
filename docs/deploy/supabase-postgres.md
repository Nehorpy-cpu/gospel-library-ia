# Supabase or Railway PostgreSQL

## Requirements

- PostgreSQL 16 recommended.
- SSL required in production connection strings.
- Daily backups and point-in-time recovery enabled.

## Variables

```txt
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/gospel_library?sslmode=require
```

Services that use psycopg may use:

```txt
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/gospel_library?sslmode=require
```

## Migration strategy

1. Take a backup before every migration batch.
2. Run scraper Alembic migrations: `cd scraper && alembic upgrade head`.
3. Run RAG Alembic migrations: `cd rag && alembic upgrade head`.
4. Run Prisma migrations only if `packages/database` is the chosen production
   owner for schema changes.
5. Verify `/health`, `/ready`, `/api/documents`, and `/api/admin/status`.

Rollback is backup-first: restore from PITR or snapshot, then redeploy the
previous service image.

## Bootstrap for the deployed main API

When the Supabase database is empty and only `apps/api` is available in the
deployment environment, use the conservative schema initializer documented in
[SUPABASE_SCHEMA_INIT_RUNBOOK.md](SUPABASE_SCHEMA_INIT_RUNBOOK.md).

It creates only the tables required by the current API, study workspace, beta,
and delegated chat contracts. It is idempotent, does not seed rows, and does
not replace the longer-term migration ownership strategy above.
