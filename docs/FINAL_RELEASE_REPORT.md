# Gospel Library IA final local release report

Date: 2026-06-12

## Decision

Local release candidate is ready for a controlled cloud deployment process.
No cloud resources were created and no production deployment was performed.

## Verified data

| Check | Result |
| --- | ---: |
| Physical documents | 33,638 |
| Distinct document authors | 1,479 |
| Distinct categories | 12 |
| Distinct tag values | 1,941 |
| Ingestion jobs | 525,786 |
| Study workspaces | 8 total / 4 active |
| Study notes | 5 total / 2 active |
| Saved citations | 4 total / 1 active |
| Post-its | 4 total / 1 active |
| Duplicate decisions | 15,618 |
| Qdrant points/vectors | 0 / 0 |
| MinIO objects | 11,547 |
| Runtime foreign-key orphans | 0 |

This runtime snapshot was taken while ingestion workers were active, so
document and job counts can continue increasing. All runtime foreign keys are
validated. The PostgreSQL dump/restore comparison matched documents, citations,
duplicate decisions, ingestion jobs, notes, sources, and workspaces exactly at
the backup snapshot (`32,978` documents).

## Migration and restore evidence

- Empty PostgreSQL database: scraper Alembic `0012`, RAG Alembic `0003`.
- Existing database: upgraded to the same heads with document count unchanged.
- PostgreSQL custom dump: 144,216,178 bytes, SHA-256
  `0CB3AC6D1E63D0548D0C0C3FFADBE26C5706228500EC08D4BF2C76170E6097FE`.
- Qdrant snapshot: 753,152 bytes, SHA-256
  `D93FF02512BEBFB66587020E1E52CB9EF7ABBF0BE3321B5FE401685192B2ED96`.
- Restore drills used temporary database/collection targets and did not replace
  the primary data.

## Runtime and UX

- Public browser routes render real data.
- Admin, Study, Favorites, and History redirect anonymous users to sign-in.
- Principal mobile pages have no horizontal overflow at 390x844.
- No browser console errors were observed in the smoke pass.
- StudyWorkspace live CRUD and cross-user isolation passed.
- Admin anonymous/user/admin access returns 401/403/200 respectively.
- CORS accepts the configured frontend origin and rejects an unlisted origin.

## RAG behavior

`doctrinal_chunks_v1` is green but empty. Search and chat use PostgreSQL
`textual_fallback`, return real document citations, and do not return 500 when
OpenAI credentials or vectors are unavailable. The `insufficient_quota` path
is covered by containerized unit tests. Live semantic search remains conditional
on a valid backend OpenAI key, available quota, and indexed vectors.

## Basic local load test

| Endpoint | Requests / concurrency | Errors | p50 | p95 |
| --- | --- | ---: | ---: | ---: |
| `/health` | 100 / 10 | 0 | 321 ms | 457 ms |
| `/api/documents?limit=20` | 100 / 10 | 0 | 541 ms | 597 ms |
| `/api/search` | 40 / 5 | 0 | 13,847 ms | 14,320 ms |
| `/api/chat` | 10 / 2 | 0 | 8,319 ms | 8,333 ms |

The local Docker/Windows environment is not a production benchmark. Textual
fallback is the slow path because the runtime schema has no full-text index.

## Corrections included

- Fixed StudyWorkspace creation with psycopg `dict_row`.
- Avoided sending an empty Qdrant API key over local HTTP.
- Workers now wait for healthy Redis/PostgreSQL/MinIO/Qdrant dependencies.
- Asset downloads reject empty, login HTML, and invalid PDF responses once
  instead of persisting them or entering pointless retries.
- Added a regression test for dict-row workspace counts.
- Corrected migration ownership documentation.
- Added tested backup/restore and rollback runbooks.

## Manual cloud gates

- Provision managed PostgreSQL with PITR, Redis, Qdrant, and R2.
- Configure scoped secrets, Clerk, Sentry, WAF, DNS, SSL, and log drains.
- Apply scraper and RAG Alembic migrations after a provider backup.
- Populate and validate vectors only after OpenAI quota is available.
- Run production smoke/load/restore drills before inviting users.
