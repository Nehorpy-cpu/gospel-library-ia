# Phase 25 - Final production readiness

## Objective

Prove that Gospel Library IA can be installed, built, migrated, backed up,
restored, and operated locally without critical visible failures before a
separately authorized cloud deployment.

## Scope

- Clean frozen-lockfile installation and dependency checks.
- Complete frontend, API, RAG, and scraper validation.
- Empty and existing PostgreSQL migration paths.
- Isolated PostgreSQL and Qdrant restore drills.
- MinIO object verification.
- Data integrity, security, frontend, API, RAG, load, and log smoke tests.
- Release, backup/restore, rollback, and deployment documentation.

## Migration ownership

Scraper Alembic owns `public.scraper_alembic_version` and RAG Alembic owns
`public.rag_alembic_version`. Prisma is validated/generated as a schema and
client contract. Its incomplete initial migration history is not applied to the
current runtime database.

## Local release evidence

- Frozen pnpm install, root/web builds, typecheck, and tests pass.
- API, RAG, and scraper unit suites pass.
- Python application trees compile.
- Prisma generate and validate pass.
- A new empty database reaches scraper `0012` and RAG `0003`.
- The existing database upgrades to the same heads without losing documents.
- PostgreSQL dump and isolated restore preserve critical counts.
- Qdrant snapshot and isolated collection restore preserve collection counts.
- MinIO contains real objects and sampled reads succeed.
- Browser checks pass on public routes and protected routes redirect to sign-in.
- Mobile checks at 390x844 show no horizontal overflow on principal pages.
- StudyWorkspace ownership and create/read/delete flows pass against the live API.
- Admin authorization, CORS allowlist, security headers, and secret scans pass.
- Workers wait for healthy dependencies, and invalid/login asset responses are
  recorded once without repeated PDF parsing failures.
- Qdrant remains green with zero points; PostgreSQL fallback search/chat returns
  real grounded sources without 500 responses.

## Known production risks

- Live semantic search was not exercised because `doctrinal_chunks_v1` has zero
  vectors and no OpenAI call is permitted in local tests.
- PostgreSQL textual fallback is stable but slow under concurrent local load;
  a runtime full-text index is a post-release performance priority.
- Some historical author/topic metadata remains malformed or mojibake.
- Favorites and reading history are user-isolated browser persistence, while
  collections map to StudyWorkspace; the Prisma-only server models are not part
  of the current Alembic runtime schema.
- External cloud credentials, PITR, WAF, Sentry, managed backups, and final DNS
  require manual provider configuration.

## Completion rule

Mark this phase complete only after the mandatory local validation commands,
Docker rebuild, health checks, smoke tests, restore drills, and `git diff
--check` pass. No production deployment is performed.
