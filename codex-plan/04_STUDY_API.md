# Phase 4 - Study API

## Goal

Expose backend endpoints for study workspaces.

## Scope

- CRUD for workspaces.
- CRUD for notes.
- CRUD for highlights.
- CRUD for saved quotes.
- CRUD for post-its.
- Workspace filters.

## Required work

1. Add authenticated API endpoints for study workspaces.
2. Validate all requests with Zod or Pydantic depending on service boundary.
3. Enforce user ownership.
4. Return source attribution for saved quotes.
5. Support filtering by workspace, document, source type, topic, and scripture reference.
6. Add structured errors and logs.

## Acceptance criteria

- API rejects unauthorized access.
- API returns real persisted study data.
- Existing public document/search endpoints are unaffected.

## Verification

```bash
pnpm test
docker compose logs api --tail=100
```

## Non-goals

- Do not build the study UI yet.
- Do not add export behavior yet.

