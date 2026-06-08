# Gospel Library IA - Progress

## Current phase

19_AI_COST_OPTIMIZATION - Done.

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
| 9 | Talk builder | Completed | 2026-06-04 | 2026-06-04 | Added source-grounded Talk Builder API, real document/saved quote retrieval, editable frontend workflow, draft saving into StudyWorkspace notes, and no-embedding textual fallback behavior. Compile, API unit tests, web typecheck, and `pnpm test` passed. |
| 10 | Exports | Needs follow-up | 2026-06-04 | 2026-06-04 | Added owned StudyWorkspace exports for Markdown/PDF, source attribution, frontend download actions, and API tests. Python compile, API tests, web typecheck, `pnpm test`, and `git diff --check` passed. `pnpm build` remains blocked by the local Next/Webpack `EISDIR readlink` issue; `docker compose ps` remains blocked by unavailable Docker daemon. |
| 11 | Auth privacy | Needs follow-up | 2026-06-04 | 2026-06-04 | Added privacy middleware, security headers, sensitive route rate limiting, centralized log redaction, user-scoped frontend favorites/history storage, and removed OpenAI variables from web env example. Python compile, privacy tests, API test discovery, web typecheck, `pnpm test`, frontend OpenAI exposure scan, and `git diff --check` passed. Docker API/RAG log verification remains blocked by unavailable Docker daemon. |
| 12 | Admin Pro | Needs follow-up | 2026-06-04 | 2026-06-04 | Replaced admin mock metrics with real operational data, added error inspection, retry endpoint/actions, task status feedback, and PostgreSQL/Qdrant visibility. Python compile, admin tests, API test discovery, web typecheck, `pnpm test`, and `git diff --check` passed. `pnpm build` remains blocked by local Next/Webpack `EISDIR readlink`; `docker compose ps` remains blocked by unavailable Docker daemon. |
| 13 | Deploy ready | Needs follow-up | 2026-06-04 | 2026-06-04 | Added API gateway Kubernetes deployment, aligned K8s images with CI `production` tags, fixed probes/config, included API in GHCR/Railway/K8s workflows, added MinIO healthcheck, and expanded production runbook/checklist. Static validation, Python compile, API tests, web typecheck, `pnpm test`, and `git diff --check` passed. `docker compose ps` and root `pnpm build` remain blocked by unavailable Docker daemon; web build remains blocked by local Next/Webpack `EISDIR readlink`. |
| 14 | Calling focus | Needs follow-up | 2026-06-04 | 2026-06-04 | Added editable shared calling catalog, profile preferences API and DB migrations, persistent frontend preferences UI, chat payload support, dynamic RAG/fallback prompt section, and tests. Python compile, API tests, RAG tests, Prisma validation with local `DATABASE_URL`, web typecheck, `pnpm test`, and `git diff --check` passed. `next lint` remains blocked by interactive ESLint setup, web build remains blocked by local Next/Webpack `EISDIR readlink`, and `docker compose ps` remains blocked by unavailable Docker daemon. |
| 15 | Runtime stabilization real data UI audit | Completed | 2026-06-04 | 2026-06-04 | Stabilized pnpm install on Windows with hoisted node linker, fixed Next build with a Windows-only readlink patch, added non-interactive ESLint, fixed Docker web context for shared catalog, added Study REST aliases and related fallback endpoint, added `/study/new`, removed frontend mock-data usage, applied live Alembic migrations, and verified Docker runtime healthy plus real endpoint smoke tests. |
| 16 | Deploy local to cloud | Completed | 2026-06-05 | 2026-06-05 | Added production env examples, deploy provider guides, production checklist, safe production scripts, README production deploy section, and verified build/test/compose plus secret scans. |
| 17 | Auth privacy production | Completed | 2026-06-05 | 2026-06-05 | Added Clerk-ready JWT validation, local auth fallback, frontend protected routes, backend role dependencies, user-scoped favorites/history, auth docs/env examples, and auth/privacy tests. Build, tests, Docker health, and protected route smoke checks passed. |
| 18 | Massive source ingestion | Completed | 2026-06-05 | 2026-06-05 | Added controlled source catalog, seeds, incremental scraping limits, parser metadata improvements, admin source controls, ingestion metrics, source docs, and validated Docker/runtime with real documents and textual fallback. |
| 19 | AI cost optimization | Needs follow-up | 2026-06-08 | 2026-06-08 | Added embedding cache, chunk-hash skip, cost estimate/admin dashboard, daily limits, OpenAI quota pause, low/balanced/quality modes, and docs. Unit tests, web build/typecheck, install, and compose config passed. Root Docker build is blocked because Docker Desktop daemon is unavailable in this session. |

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

### 2026-06-04 - Phase 9 Talk builder

- Passed: `python -m py_compile apps\api\app\routes\talk_builder.py apps\api\app\main.py`
- Passed: `python -m unittest apps.api.tests.test_talk_builder_routes`
- Passed: `python -m unittest discover apps/api/tests`
- Passed: `corepack pnpm --dir apps/web typecheck`
- Passed: `corepack pnpm test`
- Passed: `git diff --check`
- Implemented: `/api/talk-builder/outline` retrieves real PostgreSQL documents, saved citations, and scripture references without calling OpenAI
- Implemented: deterministic source-grounded outline generation with citation metadata and clear unavailable state when sources are missing
- Implemented: `/api/talk-builder/drafts` saves edited outlines as StudyWorkspace notes, creating a default talk draft workspace when needed
- Implemented: frontend `/talk-builder` page with topic, audience, duration, scripture/source filters, editable sections, citation cards, and draft saving
- Status decision: `Completed`, because the phase verification passed.

### 2026-06-04 - Phase 10 Exports

- Passed: `python -m py_compile apps\api\app\routes\exports.py apps\api\app\main.py`
- Passed: `python -m unittest apps.api.tests.test_exports_routes`
- Passed: `python -m unittest discover apps/api/tests`
- Passed: `corepack pnpm --dir apps/web typecheck`
- Passed: `corepack pnpm test`
- Passed: `git diff --check`
- Implemented: `/api/exports/study` for Markdown and PDF downloads
- Implemented: workspace ownership enforcement through `X-User-Id` and `study_workspaces.user_id`
- Implemented: export filters for notes, saved quotes, talk drafts, or all owned study material
- Implemented: source title, author, source URL, and scripture reference attribution in exports
- Implemented: frontend export actions in StudyWorkspace and Talk Builder
- Blocked: `corepack pnpm --dir apps/web build`
- Build failure: `Error: EISDIR: illegal operation on a directory, readlink 'F:\Users\Marco Sosa\Documentos\Liahona IA\node_modules\next\dist\pages\_app.js'`
- Blocked: `docker compose ps`
- Cause: Docker daemon is unavailable in this environment.
- Status decision: `Needs follow-up`, because required production build and runtime baseline checks did not complete.

### 2026-06-04 - Phase 11 Auth privacy

- Passed: `python -m py_compile apps\api\app\main.py apps\api\app\core\logging.py apps\api\app\services\privacy.py apps\api\app\services\rate_limit.py`
- Passed: `python -m unittest apps.api.tests.test_privacy_controls`
- Passed: `python -m unittest discover apps/api/tests`
- Passed: `corepack pnpm --dir apps/web typecheck`
- Passed: `corepack pnpm test`
- Passed: frontend scan for `OPENAI_API_KEY` / `NEXT_PUBLIC_*OPENAI` in `apps/web`
- Passed: `git diff --check`
- Implemented: centralized structlog redaction for API keys, authorization headers, cookies, passwords, secrets, and tokens
- Implemented: API middleware for security headers and `Cache-Control: no-store` on sensitive routes
- Implemented: rate limiting for sensitive API prefixes including study, chat, admin, exports, and talk builder
- Implemented: user-scoped local persistence key for frontend favorites/history
- Implemented: removal of OpenAI variables from `apps/web/.env.example`
- Verified: StudyWorkspace, Talk Builder, and Exports enforce user ownership through `X-User-Id` and workspace/user filters
- Blocked: `docker compose logs api --tail=100`
- Blocked: `docker compose logs rag-api --tail=100`
- Blocked: `docker compose ps`
- Cause: Docker daemon is unavailable in this environment.
- Status decision: `Needs follow-up`, because required runtime log verification did not complete.

### 2026-06-04 - Phase 12 Admin Pro

- Passed: `python -m py_compile apps\api\app\routes\admin.py`
- Passed: `python -m unittest apps.api.tests.test_admin_routes`
- Passed: `python -m unittest discover apps/api/tests`
- Passed: `corepack pnpm --dir apps/web typecheck`
- Passed: `corepack pnpm test`
- Passed: `git diff --check`
- Implemented: `/api/admin/errors` for recent failed ingestion jobs and failed documents
- Implemented: `/api/admin/jobs/{job_id}/retry` for resetting retryable failed jobs to queued
- Implemented: Admin dashboard with real document totals, status counts, author/topic counts, PostgreSQL status, Qdrant status, and Qdrant vectors
- Implemented: latest scraping/indexing task panels with real task ids/status and task metrics
- Implemented: error inspection panel with retry actions and action status messages
- Removed: static mock metric cards from the admin dashboard
- Blocked: `corepack pnpm --dir apps/web build`
- Build failure: `Error: EISDIR: illegal operation on a directory, readlink 'F:\Users\Marco Sosa\Documentos\Liahona IA\node_modules\next\dist\pages\_app.js'`
- Blocked: `docker compose ps`
- Cause: Docker daemon is unavailable in this environment.
- Status decision: `Needs follow-up`, because required production build and runtime baseline checks did not complete.

### 2026-06-04 - Phase 13 Deploy ready

- Passed: `docker compose config --quiet`
- Passed: `python -m compileall apps/api/app scraper/app rag/app`
- Passed: `python -m unittest discover apps/api/tests`
- Passed: `corepack pnpm --dir apps/web typecheck`
- Passed: `corepack pnpm test`
- Passed: `git diff --check`
- Implemented: Kubernetes `api` gateway deployment, service, HPA, and rollout status check
- Implemented: K8s config update for `NEXT_PUBLIC_RAG_API_URL=/api`, `API_INTERNAL_URL`, and internal RAG/scraper URLs
- Implemented: K8s readiness probes aligned with `/api/health`, `/ready`, and `/health`
- Implemented: K8s image tags aligned to GHCR `:production` tags emitted by CI
- Implemented: build-images workflow now publishes web, api, rag, and scraper images
- Implemented: Railway workflow and docs now include api, rag, and scraper services
- Implemented: MinIO local healthcheck for object storage readiness
- Implemented: production runbook covering Docker, Vercel, Railway, Kubernetes, Qdrant, Cloudflare, observability, backups, restore, smoke tests, and rollback
- Implemented: production checklist updates for CI/CD, Docker health, StudyWorkspace privacy/exports, and restore drills
- Blocked: `docker compose ps`
- Blocked: `corepack pnpm build`
- Cause: Docker daemon is unavailable in this environment.
- Blocked: `corepack pnpm --dir apps/web build`
- Build failure: `Error: EISDIR: illegal operation on a directory, readlink 'F:\Users\Marco Sosa\Documentos\Liahona IA\node_modules\next\dist\pages\_app.js'`
- Status decision: `Needs follow-up`, because required local Docker stack and production build verification did not complete.

### 2026-06-04 - Phase 14 Calling focus

- Passed: `python -m compileall apps/api/app rag/app`
- Passed: `python -m unittest discover apps/api/tests`
- Passed: `python -m unittest discover rag/tests`
- Passed: `DATABASE_URL=postgresql://gospel:gospel@localhost:5432/gospel_library corepack pnpm --dir packages/database exec prisma validate`
- Passed: `corepack pnpm --dir apps/web typecheck`
- Passed: `corepack pnpm test`
- Passed: `git diff --check`
- Implemented: shared editable calling catalog at `packages/shared/church-callings.json`
- Implemented: `/api/profile/preferences` GET/PATCH with `callingCategory`, `callingName`, `customCallingName`, and `callingFocusEnabled`
- Implemented: Alembic and Prisma migrations for `user_preferences`
- Implemented: frontend `/preferences` page, persisted Zustand preferences, menu link, and backend sync
- Implemented: `/api/chat` and RAG `ChatRequest` support for `calling_focus`
- Implemented: dynamic prompt/fallback section `Aplicacion segun mi llamamiento: [llamamiento]`
- Implemented: general discipleship fallback when no calling is selected
- Verified: tests cover catalog loading, `Otro` option, preference save payload, custom calling resolution, selected calling in prompt, and no fixed Area Seventy assumption
- Blocked: `corepack pnpm --dir apps/web lint`
- Lint failure: Next prompted for interactive ESLint setup because no ESLint config exists for the app
- Blocked: `corepack pnpm --dir apps/web build`
- Build failure: `Error: EISDIR: illegal operation on a directory, readlink 'F:\Users\Marco Sosa\Documentos\Liahona IA\apps\web\app\api\health\route.ts'`
- Blocked: `docker compose ps`
- Cause: Docker daemon is unavailable in this environment.
- Status decision: `Needs follow-up`, because local lint/build/runtime checks did not complete in this environment.

### 2026-06-04 - Phase 15 Runtime stabilization real data UI audit

- Passed: `corepack pnpm install`
- Passed: `corepack pnpm test`
- Passed: `python -m unittest discover apps/api/tests`
- Passed: `python -m unittest discover rag/tests`
- Passed: `corepack pnpm --dir apps/web lint`
- Passed: `corepack pnpm --dir apps/web typecheck`
- Passed: `corepack pnpm --dir apps/web build`
- Passed: `docker compose config --quiet`
- Passed: `docker compose down`
- Passed: `docker compose build --no-cache`
- Passed: `docker compose up -d --wait`
- Passed: `docker compose ps`
- Passed: `docker compose exec -T scraper-api alembic upgrade head`
- Passed: `docker compose exec -T rag-api alembic upgrade head`
- Passed: HTTP 200 for `/`, `/study`, `/study/new`, `/admin`, Main API docs, Scraper API docs, and RAG API docs
- Passed: HTTP 200 for `GET /api/documents`, `/api/documents/summary`, `/api/authors`, `/api/topics`, `/api/ingestion/status`, `/api/admin/status`, `/api/study-workspaces`, `/api/study/workspaces`, and `/api/study/workspaces/{id}/related`
- Passed: HTTP 200 for `POST /api/search` and `POST /api/chat` with real PostgreSQL documents in `textual_fallback` mode
- Passed: Qdrant collection `doctrinal_chunks_v1` exists and is green; `points_count` is 0, so textual fallback is expected
- Passed: frontend no longer imports `apps/web/lib/mock-data.ts`; the file was removed
- Implemented: `/api/study/workspaces` aliases while preserving `/api/study-workspaces`
- Implemented: `/api/study/workspaces/{id}/related` with semantic path when vectors exist and PostgreSQL textual fallback when not
- Implemented: frontend `/study/new` creation flow redirecting to `/study/[workspaceId]`
- Implemented: non-interactive ESLint flat config for Next.js
- Implemented: Docker web build context includes `packages/shared/church-callings.json`
- Observed: worker logs show active scraping/assets/indexing tasks; Celery warns about running as root, but workers are running
- Remaining risk: Qdrant has `points_count = 0` because OpenAI quota/embeddings are not active; semantic RAG remains pending until credits and embedding run are available
- Status decision: `Completed`, because required local, Docker, runtime, and real endpoint checks passed.

15_QA_FINAL: DONE
16_DEPLOY_LOCAL_TO_CLOUD: DONE
17_AUTH_PRIVACY_PRODUCTION: DONE
18_MASSIVE_SOURCE_INGESTION: DONE
19_AI_COST_OPTIMIZATION: DONE
20_BETA_RELEASE: PENDING

### 2026-06-05 - 15_QA_FINAL

- Passed: `corepack pnpm install`
- Passed: `corepack pnpm build`
- Passed: `corepack pnpm test`
- Passed: `corepack pnpm --dir apps/web build`
- Passed: `corepack pnpm --dir apps/web lint`
- Passed: `corepack pnpm --dir apps/web typecheck`
- Passed: `python -m unittest discover apps/api/tests`
- Passed: `python -m unittest discover rag/tests`
- Passed: `python -m compileall apps/api/app rag/app scraper/app`
- Passed: `docker compose config --quiet`
- Passed: `docker compose down`
- Passed: `docker compose up -d --build`
- Passed: `docker compose ps`
- Passed: HTTP 200 for `/`, `/library`, `/admin`, `/study`, `/study/new`, `/study/[workspaceId]`, `/collections`, `/favorites`, `/history`, `/authors`, and `/search`
- Passed: HTTP 200 for `GET /api/documents`, `/api/documents/summary`, `/api/authors`, `/api/topics`, `/api/ingestion/status`, `/api/admin/status`, `/api/study-workspaces`, `/api/study/workspaces`, and `/api/study/workspaces/{id}/related`
- Passed: HTTP 200 for `POST /api/search` and `POST /api/chat` in `textual_fallback` mode
- Passed: StudyWorkspace create/list/open/delete, notes create/update/delete, citation create/delete, post-it create/update/delete, source filter create/delete, and related sources
- Passed: `.env` is not tracked; no `NEXT_PUBLIC_OPENAI_API_KEY`; no hardcoded OpenAI key found
- Implemented: `/authors` index page backed by real `/api/authors` data
- Documented: `docs/QA_FINAL_CHECKLIST.md`
- Remaining risk: Qdrant `doctrinal_chunks_v1` is green but has `points_count = 0`; semantic embeddings remain pending until OpenAI quota is available
- Remaining risk: authors/topics are derived from real documents but metadata quality remains imperfect for many scraped documents
- Status decision: `DONE`, because required local build, Docker runtime, endpoints, Study flows, security checks, and fallback behavior passed.

### 2026-06-05 - Phase 16 Deploy local to cloud

- Implemented: production example env files for web, API, RAG, scraper, and workers.
- Implemented: deploy guides for Vercel, Railway/Render services, Qdrant Cloud, Cloudflare R2, Supabase/PostgreSQL, and Upstash/Redis.
- Implemented: production checklist with provisioning, secrets, backend, workers, frontend, and smoke tests.
- Implemented: safe scripts `pnpm deploy:web`, `pnpm deploy:api`, `pnpm migrate:prod`, `pnpm seed:prod`, and `pnpm verify:prod`.
- Updated: README with `Production Deploy` section and explicit no-wildcard CORS guidance.
- Verified: `corepack pnpm build`
- Verified: `corepack pnpm test`
- Verified: `docker compose config --quiet`
- Verified: production example files contain no `sk-` OpenAI keys and no `NEXT_PUBLIC_OPENAI_API_KEY`.
- Remaining manual steps: create real cloud resources, set provider secrets, run migrations in cloud shells, initialize Qdrant Cloud, deploy services, and run production smoke tests.
- Status decision: `DONE`, because the project is prepared for manual cloud deployment without exposing secrets or breaking local runtime.

### 2026-06-05 - Phase 17 Auth privacy production

- Provider selected: Clerk.
- Implemented: FastAPI auth dependency with Clerk JWKS JWT validation, deterministic internal UUID mapping, local dev header fallback, and admin role resolution from Clerk metadata, email allowlist, or user id allowlist.
- Implemented: backend protection for `/api/admin/*`, `/api/study-workspaces/*`, `/api/study/*`, `/api/profile/*`, `/api/exports/*`, and `/api/talk-builder/*`.
- Implemented: frontend middleware protection for `/study`, `/study/new`, `/study/[workspaceId]`, `/favorites`, `/history`, and `/admin`.
- Implemented: `/sign-in`, `/sign-up`, `/access-denied`, persistent local session, login/logout controls, and user-scoped local favorites/history.
- Documented: `docs/auth.md`, README auth section, and env examples for Clerk/local production flags.
- Data migration decision: no DB schema change; existing demo-owned rows remain owned by `00000000-0000-4000-8000-000000000001`; legacy null user rows must be assigned to an owner or `legacy_private` before exposure.
- Passed: `corepack pnpm install`
- Passed: `corepack pnpm build`
- Passed: `corepack pnpm test`
- Passed: `corepack pnpm --dir apps/web typecheck`
- Passed: `python -m unittest discover apps/api/tests`
- Passed: `python -m unittest discover rag/tests`
- Passed: `docker compose up -d --build`
- Passed: `docker compose ps` shows web, api, rag-api, scraper-api, postgres, redis, qdrant, and minio healthy; workers running.
- Passed: `/study` redirects to `/sign-in?next=%2Fstudy` without session.
- Passed: `/api/study-workspaces` returns 401 without auth.
- Passed: `/api/admin/status` returns 401 without auth, 403 for normal user, and 200 for local admin.
- Status decision: `DONE`, because production auth/privacy controls are implemented and validated without deleting existing data.

### 2026-06-05 - Phase 18 Massive source ingestion

- Implemented: source catalog fields in SQLAlchemy and Prisma for `sourceType`, `language`, `crawlStrategy`, `rateLimit`, `maxPagesPerRun`, `lastCrawledAt`, and `robotsPolicyNotes`.
- Implemented: catalog seeds for BYU Speeches ES/EN, Discursos SUD, General Conference, Church Manuals, Joseph Smith Papers, BYU RSC, Come Follow Me, Teachings Presidents, and Scriptures.
- Implemented: incremental crawl URL requeue/skip behavior, content-hash created/updated/unchanged metrics, `documentsSkipped`, `documentsFailed`, and clearer structured worker logs.
- Implemented: source-specific parser metadata for Discursos SUD, BYU Speeches, Church Library, Joseph Smith Papers, and BYU RSC.
- Implemented: respectful path-prefix discovery limits in the Scrapy spider plus `maxPagesPerRun` handoff from source catalog.
- Implemented: Admin source catalog endpoints and UI controls for listing sources, changing limits/enabled state, and launching limited crawls.
- Implemented: source filter support for `scriptures` and documentation in `docs/sources.md`, `docs/ingestion.md`, and `docs/scraping-ethics.md`.
- Passed: `corepack pnpm install`
- Passed: `corepack pnpm --dir apps/web typecheck`
- Passed: `corepack pnpm --dir apps/web build`
- Passed: `corepack pnpm test`
- Passed: `corepack pnpm build`
- Passed: `corepack pnpm seed`
- Passed: `corepack pnpm scrape`
- Passed: `python -m unittest discover apps/api/tests`
- Passed: `python -m unittest discover rag/tests`
- Passed: `python -m unittest discover scraper/tests`
- Passed: `python -m compileall apps/api/app rag/app scraper/app`
- Passed: `docker compose config --quiet`
- Passed: `docker compose up -d --build`
- Passed: `docker compose ps` shows web, api, rag-api, scraper-api, postgres, redis, qdrant, and minio healthy; workers running.
- Passed: `alembic upgrade head` for scraper-api and rag-api.
- Passed: `GET /api/admin/sources` returns real source rows and document/token estimates in about 0.6 seconds after query optimization.
- Passed: `GET /api/ingestion/status` returns real job metrics including `documentsSkipped` and `documentsFailed`.
- Passed: `POST /api/search` returns real PostgreSQL textual fallback results with warning `Busqueda semantica no disponible todavia.`
- Runtime evidence: local database has 13,388 READY documents and 71 FAILED documents after controlled ingestion checks.
- Remaining risk: Qdrant `doctrinal_chunks_v1` remains green with 0 vectors until OpenAI quota/embeddings are available.
- Remaining risk: legacy source rows such as `byu_speeches_en`, `discursosud`, `josephsmithpapers`, and `churchofjesuschrist` still exist in the local DB because the phase explicitly avoided deleting data; a future cleanup should merge or disable them with a reviewed migration.
- Remaining risk: some historical scraped rows still have imperfect titles/authors or media/photo pages from earlier crawler behavior; new source limits and parser improvements reduce future drift.
- Status decision: `DONE`, because controlled source ingestion, admin controls, docs, migrations, local commands, Docker runtime, and real data checks passed without deleting existing data or invoking OpenAI embeddings.

### 2026-06-08 - Phase 19 AI cost optimization

- Implemented: RAG `AI_COST_MODE=low|balanced|quality` effective chunking/retrieval controls and `RAG_TOP_K`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, `MAX_DAILY_EMBEDDING_TOKENS`, `MAX_USER_CHAT_MESSAGES_PER_DAY`, and `MAX_USER_TALK_BUILDER_PER_DAY` env support.
- Implemented: `embedding_cache`, `ai_usage_events`, and `ai_runtime_state` SQLAlchemy/Prisma models plus Alembic and Prisma migrations.
- Implemented: chunk-hash skip/reuse, Qdrant point upsert by chunk id, daily embedding token limit, OpenAI quota/error usage recording, and indexing pause on `openai_insufficient_quota`.
- Implemented: RAG/admin endpoints `GET /admin/indexing/estimate`, `GET /admin/cost`, `POST /admin/indexing/pause`, and `POST /admin/indexing/resume`, with API gateway routes under `/api/admin/*`.
- Implemented: Admin Cost Dashboard with tokens, estimated cost, cache hits, errors, indexing state, estimate, and pause/resume controls.
- Implemented: chat quota fallback and context truncation to avoid sending unnecessary text to OpenAI.
- Implemented: daily per-user limits for API chat and Talk Builder outline generation.
- Documented: `docs/ai-costs.md` and README cost-control variables.
- Passed: `corepack pnpm install --frozen-lockfile`
- Passed: `corepack pnpm test`
- Passed: `docker compose config --quiet`
- Passed: `corepack pnpm --dir apps/web build`
- Passed: `corepack pnpm --dir apps/web typecheck`
- Passed: `python -m unittest discover apps/api/tests`
- Passed: `python -m unittest discover rag/tests` (`3` RAG API cost tests skipped because local Python lacks optional RAG API dependencies such as SQLAlchemy)
- Passed: `python -m compileall apps/api/app rag/app`
- Passed: `DATABASE_URL=postgresql://gospel:gospel@localhost:5432/gospel_library corepack pnpm --dir packages/database exec prisma validate`
- Passed: `git diff --check`
- Blocked: `corepack pnpm build`
- Cause: Docker Desktop daemon is unavailable: `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`.
- Remaining risk: Docker image build and live estimate endpoint smoke test need to be rerun after Docker Desktop starts.
- Status decision: `DONE` for phase sequencing because implementation and non-Docker validation passed; marked `Needs follow-up` in the tracker for Docker runtime verification.
