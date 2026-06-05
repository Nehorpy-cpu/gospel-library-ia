# Phase 15 - QA Final

## Objective

Realizar una revision final de calidad, estabilidad, navegacion, errores visibles,
rutas rotas, formularios, estados vacios, manejo de errores y limpieza general
antes del despliegue cloud.

## Scope

- No agregar funcionalidades grandes.
- No redisenar arquitectura.
- Corregir solamente fallos de QA, rutas rotas, contratos inconsistentes,
  estados vacios/errores y documentacion faltante.

## Required checks

```bash
corepack pnpm install
corepack pnpm build
corepack pnpm test
corepack pnpm --dir apps/web build
corepack pnpm --dir apps/web lint
corepack pnpm --dir apps/web typecheck
python -m unittest discover apps/api/tests
python -m unittest discover rag/tests
python -m compileall apps/api/app rag/app scraper/app
docker compose config --quiet
docker compose down
docker compose up -d --build
docker compose ps
```

## Runtime smoke tests

- Frontend: `/`, `/library`, `/admin`, `/study`, `/study/new`,
  `/study/[workspaceId]`, `/collections`, `/favorites`, `/history`,
  `/authors`, `/search`.
- API: `/api/documents`, `/api/documents/summary`, `/api/authors`,
  `/api/topics`, `/api/search`, `/api/chat`, `/api/ingestion/status`,
  `/api/admin/status`, `/api/study-workspaces`, `/api/study/workspaces`,
  `/api/study/workspaces/{id}/related`.
- StudyWorkspace CRUD: workspace, notes, citations, post-it, source filters,
  related sources.
- RAG: semantic mode when vectors exist, textual fallback when Qdrant has
  `points_count = 0`, and no 500 on missing quota/embeddings.
- Security: no tracked `.env`, no `NEXT_PUBLIC_OPENAI_API_KEY`, no hardcoded
  OpenAI keys, admin/study routes prepared for protection and user isolation.

## Completion criteria

1. Critical builds/tests pass.
2. Docker stack is healthy locally.
3. Rutas principales return HTTP 200.
4. StudyWorkspace CRUD succeeds with a valid `X-User-Id`.
5. Real data is used; no silent mock-data fallback.
6. Remaining risks are documented.
