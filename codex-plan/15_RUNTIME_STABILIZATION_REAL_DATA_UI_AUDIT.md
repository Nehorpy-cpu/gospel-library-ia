# Phase 15 - Runtime Stabilization Real Data UI Audit

## Objective

Leave Gospel Library IA stable in real runtime with Docker running, web build passing, Study routes aligned, and frontend screens using real endpoints instead of mock data.

## Scope

- Repair local install and Next.js build issues.
- Configure non-interactive ESLint for the web app.
- Validate Docker Compose runtime with all core services healthy.
- Preserve `/api/study-workspaces` and add `/api/study/workspaces` aliases.
- Add `/api/study/workspaces/{id}/related` with semantic retrieval when vectors exist and textual fallback when Qdrant has zero vectors or OpenAI quota is unavailable.
- Add `/study/new` for real StudyWorkspace creation.
- Remove remaining frontend `mock-data` usage from home, global search, document reader, collections, favorites, history, and author pages.
- Update README and `PROGRESS.md`.

## Constraints

- Do not redesign architecture.
- Do not add large new features.
- Do not silently use mock data.
- Do not expose OpenAI keys in the frontend.
- Do not mark complete if Docker runtime cannot be validated.

## Required Validation

```bash
corepack pnpm install
corepack pnpm test
python -m unittest discover apps/api/tests
python -m unittest discover rag/tests
corepack pnpm --dir apps/web lint
corepack pnpm --dir apps/web typecheck
corepack pnpm --dir apps/web build
docker compose config --quiet
docker compose down
docker compose build --no-cache
docker compose up -d --wait
docker compose ps
```

## Runtime Smoke Tests

- `http://localhost:3000`
- `http://localhost:3000/study`
- `http://localhost:3000/study/new`
- `http://localhost:3000/admin`
- `http://localhost:8000/docs`
- `http://localhost:8080/docs`
- `http://localhost:8090/docs`
- `http://localhost:6333/collections/doctrinal_chunks_v1`
- `GET /api/documents`
- `GET /api/documents/summary`
- `GET /api/authors`
- `GET /api/topics`
- `POST /api/search`
- `POST /api/chat`
- `GET /api/ingestion/status`
- `GET /api/admin/status`
- `GET /api/study-workspaces`
- `GET /api/study/workspaces`
- `GET /api/study/workspaces/{id}/related`

## Completion Rule

If all validations pass, mark this phase completed and commit:

```txt
chore: fase 15 - runtime stabilization and real data UI audit
```

If Docker is unavailable, mark the phase blocked and instruct the user to start Docker Desktop before repeating the phase.
