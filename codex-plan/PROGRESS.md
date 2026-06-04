# Gospel Library IA - Progress

## Current phase

Phase 8 - RAG by scripture needs runtime log verification follow-up.

## Phase tracker

| Phase | Name | Status | Started | Finished | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | Stabilize data | Needs follow-up | 2026-06-03 | 2026-06-03 | Code and data-quality plan are present; `corepack pnpm test` passed. Docker runtime checks could not run because Docker daemon/service is unavailable in this environment. |
| 2 | Fallback text search | Needs follow-up | 2026-06-03 | 2026-06-03 | Implemented PostgreSQL text fallback for unavailable OpenAI/Qdrant, warning propagation, and frontend messaging. `corepack pnpm test` and Python AST validation passed. Docker `rag-api` logs could not run because Docker daemon is unavailable. |
| 3 | Study workspace DB | Needs follow-up | 2026-06-03 | 2026-06-03 | Added enterprise study workspace DB fields, study highlights, Prisma schema relations, Alembic migration, and Prisma SQL migration. `prisma:generate`, `prisma validate`, and `pnpm test` passed. `prisma:migrate` could not connect because Postgres/Docker are unavailable. |
| 4 | Study API | Needs follow-up | 2026-06-03 | 2026-06-03 | Implemented authenticated StudyWorkspace API endpoints with Pydantic validation, ownership enforcement, CRUD for workspaces/source filters/notes/highlights/citations/post-its, source attribution, filters, and structured logs. `pnpm test` and Python compile checks passed. Docker API logs could not run because Docker daemon is unavailable. |
| 5 | Study frontend | Needs follow-up | 2026-06-03 | 2026-06-03 | Added StudyWorkspace frontend routes, real API client methods, Zustand study state, responsive workspace UI, note/citation/highlight/post-it/source filter flows, and Next rewrites for API proxying. Typecheck and `pnpm test` passed. `pnpm build` is blocked by a local Next/Webpack `EISDIR readlink` issue in hoisted Windows node_modules. |
| 6 | Source filters | Completed | 2026-06-03 | 2026-06-03 | Normalized canonical source filter vocabulary across API, PostgreSQL fallback search, RAG BM25/semantic payloads, admin statistics, library, search, and study UI. Added real `/api/sources/summary` options and tests. `pnpm test`, API route unit tests, Python compile checks, and web typecheck passed. |
| 7 | Saved quotes and post-its | Needs follow-up | 2026-06-04 | 2026-06-04 | Added user-facing save quote actions from reader and chat citations, default StudyWorkspace creation for saves, persisted citation location metadata, post-it color/position/create/update/delete controls, and optimistic post-it updates. Web typecheck and `pnpm test` passed. `pnpm build` is blocked by a local Next/Webpack `EISDIR readlink` issue. |
| 8 | RAG by scripture | Needs follow-up | 2026-06-04 | 2026-06-04 | Added scripture reference normalization, query/message scripture extraction, API/RAG metadata filters, PostgreSQL fallback filtering, Qdrant payload filters, scripture-aware indexing metadata, and frontend scripture filter input. Local compile, web typecheck, API unit tests, and `pnpm test` passed. Docker `rag-api` logs could not run because Docker daemon is unavailable. |
| 9 | Talk builder | Pending | - | - | - |
| 10 | Exports | Pending | - | - | - |
| 11 | Auth privacy | Pending | - | - | - |
| 12 | Admin Pro | Pending | - | - | - |
| 13 | Deploy ready | Pending | - | - | - |

## Update rules

After each phase:

1. Mark the phase as `Completed`, `Blocked`, or `Needs follow-up`.
2. Add verification evidence.
3. Add any remaining risks.
4. Do not mark a phase complete if tests or required runtime checks failed.

## Verification log

### 2026-06-03 - Phase 1 Stabilize data

- Passed: `corepack pnpm test`
- Blocked: `docker compose ps`
- Blocked: `docker compose exec -T postgres psql -U gospel -d gospel_library -c "...data quality counts..."`
- Blocked: `docker compose logs scraper-worker-scraping --tail=80`
- Cause: Docker contexts `desktop-linux` and `default` could not connect to a Docker daemon. `com.docker.service` is stopped and could not be started from this session.
- Status decision: `Needs follow-up`, because required runtime checks did not complete.

### 2026-06-03 - Phase 2 Fallback text search

- Passed: `corepack pnpm test`
- Passed: Python AST validation for changed RAG/API files
- Passed: no committed `NEXT_PUBLIC_OPENAI_API_KEY` or hardcoded `OPENAI_API_KEY=sk-...` found
- Implemented: `/search` returns PostgreSQL text fallback when OpenAI is missing/unusable or Qdrant has zero vectors
- Implemented: `/chat` returns a clear no-vector fallback message instead of 500 when vectors are unavailable
- Implemented: frontend renders all fallback warnings, including `Falta configurar la clave de OpenAI para busqueda IA.`
- Blocked: `docker compose logs rag-api --tail=100`
- Cause: Docker daemon is unavailable in this environment.
- Status decision: `Needs follow-up`, because required runtime log verification did not complete.

### 2026-06-03 - Phase 3 Study workspace DB

- Passed: `corepack pnpm prisma:generate`
- Passed: `corepack pnpm --dir packages/database exec prisma validate`
- Passed: Python AST validation for `scraper/migrations/versions/0005_study_workspace_enterprise_fields.py`
- Passed: `corepack pnpm test`
- Implemented: Prisma models/relations for study workspaces, workspace source filters, study notes, saved citations, post-its, and study highlights
- Implemented: user ownership fields, selected text, scripture refs, soft-delete fields, sync revision fields, and user/workspace/document/chunk indexes
- Implemented: Alembic migration `0005_study_workspace_enterprise_fields.py`
- Implemented: Prisma migration `0003_study_workspace_enterprise_fields/migration.sql`
- Blocked: `corepack pnpm prisma:migrate`
- Cause: PostgreSQL is not reachable at `localhost:5432`; Docker daemon is unavailable in this environment.
- Status decision: `Needs follow-up`, because the migration could not be applied to a live database.

### 2026-06-03 - Phase 4 Study API

- Passed: Python AST validation for `apps/api/app/routes/study.py` and `apps/api/app/main.py`
- Passed: `python -m py_compile apps\api\app\routes\study.py apps\api\app\main.py`
- Passed: `corepack pnpm test`
- Implemented: authenticated `/api/study-workspaces` endpoints requiring `X-User-Id`
- Implemented: CRUD for study workspaces, workspace source filters, notes, highlights, saved citations, and post-its
- Implemented: Pydantic request validation, user ownership checks, soft deletes, structured logs, and source attribution for saved citations
- Implemented: filters by workspace, document, source type, topic, and scripture reference where applicable
- Updated: API CORS allows `PATCH` and `DELETE` for the new CRUD endpoints
- Blocked: `docker compose logs api --tail=100`
- Cause: Docker daemon is unavailable in this environment.
- Status decision: `Needs follow-up`, because required runtime log verification did not complete.

### 2026-06-03 - Phase 5 Study frontend

- Passed: `corepack pnpm --dir apps/web typecheck`
- Passed: `corepack pnpm test`
- Passed: `git diff --check`
- Implemented: Next App Router pages `/study` and `/study/[workspaceId]`
- Implemented: StudyWorkspace UI with real TanStack Query calls for workspaces, documents, source filters, notes, highlights, saved citations, and post-its
- Implemented: Zustand local study state for active workspace, active document, selected text, and filters
- Implemented: create/view/update/delete flow for notes
- Implemented: save citations and highlights from selected document text
- Implemented: responsive source filters without changing library browsing
- Implemented: Study navigation item and configurable `NEXT_PUBLIC_STUDY_USER_ID`
- Updated: Next API proxying moved from catch-all route files to `next.config.ts` rewrites to avoid Windows/Webpack `readlink` failures on `[...path]` route directories
- Blocked: `corepack pnpm --dir apps/web build`
- Build failure: `Error: EISDIR: illegal operation on a directory, readlink 'F:\Users\Marco Sosa\Documentos\Liahona IA\node_modules\next\dist\pages\_app.js'`
- Blocked: local HTTP visual check for `http://localhost:3000/study`
- Cause: no local web server is running, and Docker daemon remains unavailable in this environment.
- Status decision: `Needs follow-up`, because required production build and visual/runtime checks did not complete.

### 2026-06-03 - Phase 6 Source filters

- Passed: `python -m py_compile apps\api\app\routes\public.py apps\api\app\routes\admin.py apps\api\app\routes\study.py apps\api\app\schemas\api.py apps\api\app\services\source_filters.py rag\app\schemas\search.py rag\app\retrieval\bm25.py rag\app\retrieval\source_filters.py rag\app\services\indexer.py`
- Passed: `corepack pnpm --dir apps/web typecheck`
- Passed: `python -m unittest apps.api.tests.test_documents_routes`
- Passed: `corepack pnpm test`
- Implemented: canonical source types `byu_speeches_es`, `byu_speeches_en`, `discursos_sud`, `general_conference`, `church_manuals`, `joseph_smith_papers`, and `byu_rsc`
- Implemented: `/api/sources/summary` with real document counts and backward-compatible aliases
- Implemented: source type normalization for `/api/documents`, PostgreSQL fallback search/chat, Study API filters, admin source counts, RAG BM25, and Qdrant payload indexing
- Implemented: frontend source filter options from real API data in library, search, admin, and study workflows
- Status decision: `Completed`, because the phase verification passed.

### 2026-06-04 - Phase 7 Saved quotes and post-its

- Passed: `corepack pnpm --dir apps/web typecheck`
- Passed: `corepack pnpm test`
- Implemented: reusable save-to-study action that saves exact quote text, document id, source url, and location metadata
- Implemented: quote save actions from document reader selections
- Implemented: quote save actions from chat citations in desktop citation panel and compact mobile message actions
- Implemented: default `Mi estudio` workspace creation when saving before a workspace exists
- Implemented: post-it creation with color and position metadata
- Implemented: post-it content, color, pinned state, and position updates through the real Study API
- Implemented: optimistic post-it update UI with rollback on error
- Blocked: `corepack pnpm --dir apps/web build`
- Build failure: `Error: EISDIR: illegal operation on a directory, readlink 'F:\Users\Marco Sosa\Documentos\Liahona IA\apps\web\app\api\health\route.ts'`
- Status decision: `Needs follow-up`, because required production build did not complete in this local Next/Webpack environment.

### 2026-06-04 - Phase 8 RAG by scripture

- Passed: Python compile validation for changed API, RAG, and scraper files
- Passed: `corepack pnpm --dir apps/web typecheck`
- Passed: `python -m unittest apps.api.tests.test_documents_routes`
- Passed: `corepack pnpm test`
- Implemented: scripture reference normalization for scraper, API, and RAG paths
- Implemented: automatic scripture reference extraction from `/api/search`, `/api/chat`, RAG `/search`, and RAG `/chat` requests
- Implemented: `scripture_refs` metadata filters for PostgreSQL fallback search and RAG BM25 retrieval
- Implemented: scripture ref payload indexing and Qdrant filter support for semantic retrieval
- Implemented: structured scripture reference metadata in indexed chunks and fallback search results
- Implemented: scripture-aware local query rewriting when OpenAI is unavailable
- Implemented: scripture references in RAG citation context for better grounding
- Implemented: frontend scripture reference filter in global search
- Blocked: `docker compose logs rag-api --tail=100`
- Cause: Docker daemon is unavailable in this environment.
- Status decision: `Needs follow-up`, because required runtime log verification did not complete.
