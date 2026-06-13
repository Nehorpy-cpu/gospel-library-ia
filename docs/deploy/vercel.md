# Vercel Deploy

## Scope

Deploy `apps/web` as the public Next.js frontend. Backend services stay on
Render and are called directly through `NEXT_PUBLIC_API_URL`.

## Project settings

- Framework: Next.js
- Root directory: `apps/web`
- Install command: `corepack pnpm install --frozen-lockfile`
- Build command: `corepack pnpm build`
- Output directory: leave empty (Next.js uses `.next`)
- Node: 22

## Required variables

```txt
NEXT_PUBLIC_ENVIRONMENT=production
NEXT_PUBLIC_APP_URL=https://www.estudiopy.com
NEXT_PUBLIC_API_URL=https://api.estudiopy.com
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=
NEXT_PUBLIC_SENTRY_DSN=
```

Do not add `OPENAI_API_KEY` or any backend secret to Vercel frontend variables.
Do not append `/api` to `NEXT_PUBLIC_API_URL`; the frontend client adds that
prefix to every backend route.

## Manual steps

1. Create or link the Vercel project with root `apps/web`.
2. Add the variables above from `apps/web/.env.production.example`.
3. Deploy preview.
4. Confirm `https://api.estudiopy.com/health` responds.
5. Verify `/library`, `/authors`, `/search`, `/chat`, and `/admin`.
6. Promote to production after the required backend healthchecks pass.

See [FRONTEND_API_URL_TROUBLESHOOTING.md](./FRONTEND_API_URL_TROUBLESHOOTING.md)
for DNS and environment-variable diagnostics.

See [VERCEL_FRONTEND_ROOT_AND_API_URL.md](./VERCEL_FRONTEND_ROOT_AND_API_URL.md)
for the complete root-directory audit and stale-deployment checks.
