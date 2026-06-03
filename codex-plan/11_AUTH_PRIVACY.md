# Phase 11 - Auth Privacy

## Goal

Harden authentication, authorization, and privacy boundaries.

## Scope

- User isolation.
- Private study data.
- Secure session behavior.
- Rate limiting.
- Privacy-safe logs.

## Required work

1. Audit endpoints for user ownership checks.
2. Ensure notes, highlights, quotes, post-its, chats, favorites, and history are private.
3. Add or verify rate limiting on sensitive endpoints.
4. Remove sensitive values from logs.
5. Validate CORS and security headers.
6. Confirm no OpenAI keys are exposed to the frontend.

## Acceptance criteria

- Users cannot access other users' study data.
- Logs do not leak secrets.
- Frontend never uses `NEXT_PUBLIC_OPENAI_API_KEY`.

## Verification

```bash
pnpm test
docker compose logs api --tail=100
docker compose logs rag-api --tail=100
```

## Non-goals

- Do not add admin analytics in this phase.

