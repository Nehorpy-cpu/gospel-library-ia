# Supabase PostgreSQL schema initialization

This runbook bootstraps the PostgreSQL tables required by the deployed FastAPI
API, the study workspace routes, and the delegated RAG chat flow.

The initializer is intentionally conservative:

- it reads `DATABASE_URL` only from the process environment;
- it does not print the connection string;
- it does not drop or truncate tables;
- it does not delete, update, or seed rows;
- it uses `CREATE TABLE IF NOT EXISTS`, additive
  `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, and
  `CREATE INDEX IF NOT EXISTS`;
- it runs in one transaction and uses an advisory lock;
- it verifies required tables, columns, and critical PostgreSQL types before
  committing.

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
- columns added to existing tables;
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

If the existing table is compatible, it is reported as `VERIFIED`. If it is
missing a known additive runtime column, the script adds the column and reports
the table as `ALTERED`.

The script also aligns the legacy enum forms of `documents.status`,
`ingestion_jobs.status`, and `chat_messages.role` to `varchar`. The values are
preserved. This is necessary because the current API applies PostgreSQL string
functions such as `upper()` and `lower()` to those columns.

If a required core column is still missing, or a critical column has an
incompatible type that cannot be aligned safely, the transaction aborts and
reports the exact mismatch. Do not drop the table. Back up the database and
plan an additive migration for that specific case.

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

## Troubleshooting: endpoints return 500 after schema initialization

The most common cause is an existing table created from an older schema. In
that case, `CREATE TABLE IF NOT EXISTS` sees the table and leaves it untouched,
but the API may query columns introduced later.

The current API requires these compatibility fields in particular:

- `documents`: `author`, `category`, `tags`, `scripture_refs`, `text`,
  `raw_metadata`, `status`, `is_indexed`, `created_at`, `updated_at`, and
  `deleted_at`;
- `ingestion_jobs`: `source_id`, `source`, `payload`, all five document metric
  columns, `errors`, `attempts`, and lifecycle timestamps;
- `sources`: source catalog, crawl configuration, and timestamp columns;
- `document_chunks`: section, text, metadata, and search-vector columns;
- `document_duplicate_relations`: duplicate classification and review fields.

Run the latest initializer again:

```powershell
cd apps/api
.\.venv\Scripts\activate
$env:DATABASE_URL="TU_DATABASE_URL_DE_SUPABASE_CON_SSLMODE"
python scripts/init_supabase_schema.py
```

Look for `ALTERED` lines in the output. A successful run ends with
`Primary endpoint schema verified`.

Then test the deployed routes:

```powershell
curl.exe -i "https://api.estudiopy.com/health"
curl.exe -i "https://api.estudiopy.com/api/documents"
curl.exe -i "https://api.estudiopy.com/api/documents/summary"
curl.exe -i "https://api.estudiopy.com/api/sources/summary"
curl.exe -i "https://api.estudiopy.com/api/authors"
curl.exe -i "https://api.estudiopy.com/api/topics"
curl.exe -i "https://api.estudiopy.com/api/ingestion/status"
curl.exe -i -X POST "https://api.estudiopy.com/api/search" `
  -H "Content-Type: application/json" `
  -d '{"query":"fe","limit":3}'
curl.exe -i -X POST "https://api.estudiopy.com/api/chat" `
  -H "Content-Type: application/json" `
  -d '{"message":"¿Qué enseñan las fuentes sobre la fe?","language":"es"}'
```

Expected result for an empty database is HTTP 200 with empty lists or zero
counts. Empty data is not an error.

If the script succeeds but Render still returns HTTP 500:

1. Confirm that Render is using the same Supabase project whose schema was
   initialized.
2. Confirm that the latest commit was deployed and the service restarted.
3. Inspect the Render application log for the PostgreSQL error class without
   copying credentials.
4. If the error says `undefined_column`, compare the named column with the
   `ALTERED` output and rerun the latest script.
5. If the error says `undefined_function` for `upper` or `lower`, rerun the
   latest script so legacy status enums are aligned to textual columns.
6. If the error says `relation does not exist`, verify the `public` schema and
   confirm the service connection points to the intended database.

The Qdrant health error is independent. It does not prevent these PostgreSQL
list and summary endpoints from returning HTTP 200.
