# Vercel Deploy

## Scope

Deploy `apps/web` as the public Next.js frontend. Backend services stay on
Railway or Render and are called through `NEXT_PUBLIC_API_URL` /
`NEXT_PUBLIC_RAG_API_URL`.

## Project settings

- Framework: Next.js
- Root directory: `apps/web`
- Build command: `npm run build`
- Output: Next.js default/standalone
- Node: 22

## Required variables

```txt
NEXT_PUBLIC_ENVIRONMENT=production
NEXT_PUBLIC_APP_URL=https://app.gospel-library-ia.example
NEXT_PUBLIC_API_URL=https://api.gospel-library-ia.example
NEXT_PUBLIC_RAG_API_URL=https://api.gospel-library-ia.example/api
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=
NEXT_PUBLIC_SENTRY_DSN=
API_INTERNAL_URL=https://api.gospel-library-ia.example
RAG_INTERNAL_URL=https://rag.gospel-library-ia.example
```

Do not add `OPENAI_API_KEY` or any backend secret to Vercel frontend variables.

## Manual steps

1. Create or link the Vercel project with root `apps/web`.
2. Add the variables above from `apps/web/.env.production.example`.
3. Deploy preview.
4. Confirm `/api/health` responds.
5. Promote to production after API, RAG, scraper, Qdrant, Redis, storage, and
   PostgreSQL healthchecks pass.
