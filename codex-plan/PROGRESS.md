# Gospel Library IA - Progress

## Current phase

Phase 2 - Fallback text search needs runtime log verification follow-up.

## Phase tracker

| Phase | Name | Status | Started | Finished | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | Stabilize data | Needs follow-up | 2026-06-03 | 2026-06-03 | Code and data-quality plan are present; `corepack pnpm test` passed. Docker runtime checks could not run because Docker daemon/service is unavailable in this environment. |
| 2 | Fallback text search | Needs follow-up | 2026-06-03 | 2026-06-03 | Implemented PostgreSQL text fallback for unavailable OpenAI/Qdrant, warning propagation, and frontend messaging. `corepack pnpm test` and Python AST validation passed. Docker `rag-api` logs could not run because Docker daemon is unavailable. |
| 3 | Study workspace DB | Pending | - | - | - |
| 4 | Study API | Pending | - | - | - |
| 5 | Study frontend | Pending | - | - | - |
| 6 | Source filters | Pending | - | - | - |
| 7 | Saved quotes and post-its | Pending | - | - | - |
| 8 | RAG by scripture | Pending | - | - | - |
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
