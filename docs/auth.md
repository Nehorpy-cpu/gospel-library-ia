# Auth and Privacy

Gospel Library IA uses Clerk as the production auth provider.

## Local development

Local development keeps a simple session fallback so the app can run without Clerk secrets:

- Visit `/sign-in`.
- Choose `Entrar como usuario` for a normal user.
- Choose `Entrar como admin local` for admin-only screens.
- The browser stores local session cookies named `gospel_user_*`.
- The API accepts `X-User-Id`, `X-User-Role`, and `X-User-Email` only while `ALLOW_DEV_AUTH_HEADERS=true`.

The default local user id is `00000000-0000-4000-8000-000000000001` so existing local StudyWorkspace data remains accessible.

## Production

Set these backend variables:

```env
AUTH_PROVIDER=clerk
ALLOW_DEV_AUTH_HEADERS=false
CLERK_SECRET_KEY=
CLERK_JWKS_URL=
CLERK_JWT_ISSUER=
CLERK_WEBHOOK_SECRET=
CLERK_ADMIN_EMAILS=
ADMIN_USER_IDS=
```

Set this frontend variable:

```env
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=
```

Production clients should send `Authorization: Bearer <Clerk JWT>` to protected API endpoints. The API validates the JWT with Clerk JWKS, extracts the Clerk subject, and maps it to the internal UUID used by PostgreSQL.

## Roles

Supported roles:

- `user`
- `admin`

Admin is assigned in one of these ways:

- Clerk public metadata contains `role=admin`.
- The normalized user id appears in `ADMIN_USER_IDS`.
- The user email appears in `CLERK_ADMIN_EMAILS`.

Use Clerk metadata for long-term role management. Use allowlists only for initial production bootstrap.

## Protected routes

Frontend middleware protects:

- `/study`
- `/study/new`
- `/study/[workspaceId]`
- `/favorites`
- `/history`
- `/admin`

Backend protects:

- `/api/study-workspaces/*`
- `/api/study/*`
- `/api/profile/*`
- `/api/exports/*`
- `/api/talk-builder/*`
- `/api/admin/*`

Public document browsing and search stay public by design.

## Data isolation

Study workspaces, notes, saved citations, highlights, post-its, exports, profile preferences, local favorites, and local history are scoped by user id.

Existing local data is not deleted. Data already assigned to the demo UUID remains owned by the local demo user. If legacy rows with `user_id` null are discovered later, migrate them either to a known owner or a `legacy_private` owner before exposing them.

## Security notes

- Do not log `Authorization`, cookies, secrets, or tokens.
- Do not expose `OPENAI_API_KEY` or Clerk secret keys in frontend env variables.
- Do not set `NEXT_PUBLIC_OPENAI_API_KEY`.
- Set `ALLOW_DEV_AUTH_HEADERS=false` in production.
- Keep CORS restricted to the production app origin.
