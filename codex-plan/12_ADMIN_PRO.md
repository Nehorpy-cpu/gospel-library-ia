# Phase 12 - Admin Pro

## Goal

Expand the admin panel for production operations.

## Scope

- Loaded data status.
- Scraping tasks.
- Indexing tasks.
- Qdrant status.
- PostgreSQL status.
- Errors and retries.

## Required work

1. Improve admin section `Datos cargados`.
2. Show total documents, status counts, authors, topics, and Qdrant vectors.
3. Show latest scraping and indexing jobs.
4. Add buttons:
   - `Actualizar estado`
   - `Ejecutar scraping`
   - `Reindexar`
5. Add error inspection and retry actions.
6. Consume real endpoints:
   - `/api/documents`
   - `/api/documents/summary`
   - `/api/authors`
   - `/api/topics`
   - `/api/ingestion/status`
   - `/api/admin/status`

## Acceptance criteria

- Admin dashboard does not use mock data.
- Admin actions report real task ids/status.
- Qdrant and PostgreSQL status are visible.

## Verification

```bash
pnpm build
pnpm test
```

## Non-goals

- Do not change deployment infrastructure in this phase.

