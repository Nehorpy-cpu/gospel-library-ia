# Phase 8 - RAG by Scripture

## Goal

Improve retrieval and grounding around scripture references.

## Scope

- Scripture reference indexing.
- Query rewriting for scripture-aware retrieval.
- Metadata filters by book/chapter/verse.
- Citation grounding.

## Required work

1. Normalize scripture refs extracted from documents.
2. Store structured scripture refs where possible.
3. Add retrieval filters for scripture references.
4. Add query rewriting for doctrinal and scripture queries.
5. Improve source attribution in RAG responses.
6. Preserve fallback behavior when embeddings are unavailable.

## Acceptance criteria

- Searches for scripture references return relevant documents.
- Chat answers include source citations.
- No hallucinated source references.

## Verification

```bash
pnpm test
docker compose logs rag-api --tail=100
```

## Non-goals

- Do not build talk outlines in this phase.

