# Supabase PostgreSQL schema initialization

This runbook bootstraps the PostgreSQL tables required by the deployed FastAPI
API, the study workspace routes, and the delegated RAG chat flow.

The initializer is intentionally conservative:

- it reads `DATABASE_URL` only from the process environment;
- it does not print the connection string;
- it does not drop or truncate tables;
- it does not delete, update, or seed rows;
- it uses `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS`;
- it runs in one transaction and uses an advisory lock;
- it verifies required columns before committing.

## Why Alembic is not used here yet

`apps/api` is the deployed API package, but it does not currently contain an
Alembic dependency, `alembic.ini`, or a migration directory. The repository
does have historical schema ownership in the scraper and RAG services, plus a
Prisma contract under `packages/database`, but running those migration chains
from the Render API service would change the current deployment architecture.

For the present recovery, `apps/api/scripts/init_supabase_schema.py` provides a
bounded bootstrap for an empty Supabase database. It follows the existing
scraper, RAG, and Prisma table contracts without making Alembic a new runtime
dependency. Future schema evolution should select one migration owner before
adding non-bootstrap changes.

## Get the Supabase connection string

1. Open the Supabase project dashboard.
2. Select the project and click **Connect** at the top.
3. Copy a PostgreSQL connection string. For a workstation that requires IPv4,
   use the **Session pooler** connection string.
4. Replace the password placeholder with the database password.
5. Ensure the URL uses SSL, for example by including `sslmode=require`.

Supabase documents the current connection options at:

- https://supabase.com/docs/guides/database/connecting-to-postgres
- https://supabase.com/docs/guides/database/psql

Do not paste the real URL into source files, commits, tickets, or chat.

## Run from Windows PowerShell

From the repository root:

```powershell
cd apps/api
.\.venv\Scripts\activate
$env:DATABASE_URL="TU_DATABASE_URL_DE_SUPABASE_CON_SSLMODE"
python scripts/init_supabase_schema.py
```

The script accepts both `postgresql://` and `postgresql+psycopg://` URLs.
If the supplied URL already includes `sslmode=require`, psycopg preserves and
uses it.

After the run, remove the variable from the current terminal if it is no longer
needed:

```powershell
Remove-Item Env:DATABASE_URL
```

## Expected result

The command prints:

- tables created during this run;
- tables that already existed and passed validation;
- the total number of required tables verified.

It never prints `DATABASE_URL`.

## Verify tables in Supabase

In **SQL Editor**, run this read-only query:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'sources',
    'crawl_urls',
    'documents',
    'document_assets',
    'document_chunks',
    'ingestion_jobs',
    'authors',
    'tags',
    'document_duplicate_relations',
    'chat_sessions',
    'chat_messages',
    'study_workspaces',
    'study_workspace_sources',
    'study_notes',
    'study_highlights',
    'saved_citations',
    'post_its',
    'user_preferences',
    'beta_access',
    'beta_feedback',
    'beta_activity_events'
  )
ORDER BY table_name;
```

You can also inspect **Table Editor** in the Supabase dashboard. Empty tables
are expected immediately after initialization because this script does not
seed or ingest content.

## Test the deployed API

Run these public checks after the schema is initialized:

```powershell
Invoke-RestMethod "https://api.estudiopy.com/health"
Invoke-RestMethod "https://api.estudiopy.com/api/documents"
Invoke-RestMethod "https://api.estudiopy.com/api/documents/summary"
Invoke-RestMethod "https://api.estudiopy.com/api/sources/summary"
Invoke-RestMethod "https://api.estudiopy.com/api/authors"
Invoke-RestMethod "https://api.estudiopy.com/api/topics"
Invoke-RestMethod "https://api.estudiopy.com/api/ingestion/status"
```

The list endpoints should return HTTP 200 with empty lists or zero counts until
documents and ingestion jobs are loaded. Protected admin and study endpoints
must be tested with the existing production authentication flow; do not place
tokens in this runbook.

`qdrant: error` is separate from PostgreSQL schema initialization. Search and
chat can use the existing PostgreSQL textual fallback, but semantic search
requires Qdrant to be healthy and populated.

## If a table already exists

Run the initializer normally. `CREATE TABLE IF NOT EXISTS` leaves the existing
table and its rows untouched. The script then verifies the columns required by
the API.

If the existing table is compatible, it is reported as `VERIFIED`.

If required columns are missing, the transaction aborts and the script reports
the table and missing columns. Do not drop the table. Back up the database,
compare the existing schema with the repository migration contracts, and plan
an additive migration for that specific case.

## If `DATABASE_URL` fails

- If the variable is absent, the script exits before opening a connection.
- Re-copy the connection string from the Supabase **Connect** panel.
- Confirm that the password placeholder was replaced.
- Confirm that SSL is enabled in the URL.
- If direct connection fails from an IPv4-only network, use the Session pooler.
- Confirm that the Supabase project is active and not paused.
- Check network restrictions and the database password in Supabase.

The script intentionally does not echo psycopg connection details, which avoids
leaking credentials through terminal logs.
