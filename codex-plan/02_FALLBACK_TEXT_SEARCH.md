# Phase 2 - Fallback Text Search

## Goal

Keep search and chat usable when OpenAI returns quota errors or Qdrant has zero vectors.

## Scope

- PostgreSQL text search fallback.
- Clear warnings in `/api/search`.
- Clear no-vector response in `/api/chat`.
- No OpenAI calls in seeds or local tests.

## Required work

1. Detect `OPENAI_API_KEY` missing or unusable without crashing the app.
2. Detect Qdrant `points_count = 0` for `doctrinal_chunks_v1`.
3. In `/api/search`, use PostgreSQL textual search when semantic search is unavailable.
4. Return warning: `Busqueda semantica no disponible todavia.`
5. In `/api/chat`, return a clear message when vectors are unavailable.
6. Keep frontend messaging clear: `Falta configurar la clave de OpenAI para busqueda IA.`
7. Avoid `NEXT_PUBLIC_OPENAI_API_KEY`.
8. Do not hardcode or commit API keys.

## Acceptance criteria

- `/api/search` returns real PostgreSQL results with Qdrant at zero vectors.
- `/api/chat` does not return 500 when vectors are unavailable.
- Missing OpenAI key returns 503 with clear JSON where required.
- Seeds and tests do not call OpenAI.

## Verification

```bash
pnpm test
docker compose logs rag-api --tail=100
```

## Non-goals

- Do not implement new RAG quality improvements yet.
- Do not change the Qdrant collection name.

