# Phase 22 - Alembic version isolation

## Objective

Make scraper and RAG migration state independent in the shared PostgreSQL database and remove ambiguity from the obsolete default Alembic version table.

## Scope

- Keep scraper revisions in `public.scraper_alembic_version`.
- Keep RAG revisions in `public.rag_alembic_version`.
- Archive an existing `public.alembic_version` table as `public.legacy_alembic_version`.
- Preserve the legacy revision value for rollback and audit purposes.
- Verify that upgrading one service does not change the other service's revision.

## Non-goals

- Do not modify application data.
- Do not merge or renumber existing migration chains.
- Do not add application features.
- Do not change Prisma migrations.

## Validation

- Scraper and RAG migration environments use distinct version tables.
- `alembic upgrade head` succeeds for both services.
- Scraper reaches revision `0010`.
- RAG remains at revision `0003`.
- The obsolete shared table is archived with its original value.
- Unit tests and Docker health checks pass.
