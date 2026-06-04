# Gospel Library IA - Orchestrator

## Purpose

This folder defines the phased execution plan for Gospel Library IA. It is the source of truth for future Codex work on the project.

## Operating rules

1. Execute only one phase at a time.
2. Do not implement a later phase until the current phase is verified.
3. Do not redesign the architecture unless a phase explicitly requires it.
4. Do not add mock data when real data can be read from PostgreSQL, Qdrant, Redis, or workers.
5. Do not call OpenAI in local seeds or tests.
6. If OpenAI quota is unavailable, keep the app usable with PostgreSQL text search fallback.
7. Preserve existing endpoints unless a phase explicitly changes their contract.
8. Prefer small, reversible changes.
9. Run verification commands before closing each phase.
10. Update `PROGRESS.md` after every completed phase.

## Required phase order

| Phase | File | Status |
| --- | --- | --- |
| 1 | `01_STABILIZE_DATA.md` | Pending |
| 2 | `02_FALLBACK_TEXT_SEARCH.md` | Pending |
| 3 | `03_STUDY_WORKSPACE_DB.md` | Pending |
| 4 | `04_STUDY_API.md` | Pending |
| 5 | `05_STUDY_FRONTEND.md` | Pending |
| 6 | `06_SOURCE_FILTERS.md` | Pending |
| 7 | `07_SAVED_QUOTES_AND_POSTITS.md` | Pending |
| 8 | `08_RAG_BY_SCRIPTURE.md` | Pending |
| 9 | `09_TALK_BUILDER.md` | Pending |
| 10 | `10_EXPORTS.md` | Pending |
| 11 | `11_AUTH_PRIVACY.md` | Pending |
| 12 | `12_ADMIN_PRO.md` | Pending |
| 13 | `13_DEPLOY_READY.md` | Pending |
| 14 | `14_CALLING_FOCUS.md` | Pending |

## Global verification baseline

Run these checks at the end of any phase that touches runtime behavior:

```bash
docker compose ps
pnpm test
```

When API behavior changes, also verify:

```txt
http://localhost:3000
http://localhost:8000/docs
http://localhost:8080/docs
http://localhost:8090/docs
```

## Data quality baseline

The platform must keep:

- `GET /api/documents` returning real documents, not status-only summaries.
- `GET /api/documents/summary` returning status counts.
- `GET /api/authors` and `GET /api/topics` derived from real documents.
- `sourceType`, `sourceUrl`, title, language, source, and excerpt populated when possible.
- Qdrant collection name unchanged: `doctrinal_chunks_v1`.
