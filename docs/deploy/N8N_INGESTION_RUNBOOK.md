# n8n Curated Spanish Ingestion Runbook

## Purpose

`POST /api/ingestion/documents` receives already-clean Spanish documents from
n8n and stores only metadata, clean text, chunks, and original-source
references in Supabase Postgres.

The API does not crawl source sites, call OpenAI, create Qdrant vectors, upload
files, or use Supabase Storage.

## Why web pages do not use Storage

For ordinary web pages, the useful application data is the verified source
URL, normalized metadata, clean article text, and searchable chunks. Saving
complete HTML duplicates external assets, increases storage usage, preserves
navigation/cookie noise, and complicates updates.

Storage remains reserved for explicitly approved heavy files owned or managed
by the project, such as PDFs that must be retained independently of their
original source.

## Render configuration

Create a long random secret and configure it only in:

- Render environment variable: `INGESTION_API_KEY`
- n8n credential or secret variable used by the request node

Do not expose it in Vercel, browser code, workflow output, execution logs,
screenshots, source control, or request bodies. Redeploy the Render API after
adding the variable.

The client sends:

```text
X-Ingestion-Key: <INGESTION_API_KEY>
```

Missing or incorrect credentials return `401`. If Render has no configured
key, the endpoint returns `503` and accepts no documents.

## Health check

No credential or database access is required:

```powershell
Invoke-RestMethod `
  -Uri "https://api.estudiopy.com/api/ingestion/documents/health" `
  -Method GET
```

Expected response:

```json
{
  "status": "ok",
  "required_header": "X-Ingestion-Key",
  "accepted_language": "es",
  "storage_used": false
}
```

## Payload

See `docs/examples/n8n_ingestion_payload_es.json`. Replace its marked content
before sending it; the example does not contain the source's doctrinal text.

Required fields:

- `title`
- `source_name`
- `source_url`
- `content` with at least 301 cleaned characters

Language must be `es` or `spa`. If omitted, the API performs a conservative
Spanish marker check and rejects text it cannot confirm. Optional fields are
`author`, `canonical_url`, `content_type`, `published_at`, `year`, `summary`,
`tags`, and `metadata`.

Raw structural HTML is rejected. Payload fields such as `file_url` and
`storage_path` are not part of the model and are ignored. A `storage_path`
inside metadata is also removed.

## PowerShell test

```powershell
$env:INGESTION_API_KEY="VALOR_CONFIGURADO_TAMBIEN_EN_RENDER"
$payload = Get-Content `
  "F:\Proyectos\gospel-library-ia-clean\docs\examples\n8n_ingestion_payload_es.json" `
  -Raw

# Replace the marked example content with clean source text before this call.
Invoke-RestMethod `
  -Uri "https://api.estudiopy.com/api/ingestion/documents" `
  -Method POST `
  -Headers @{ "X-Ingestion-Key" = $env:INGESTION_API_KEY } `
  -ContentType "application/json" `
  -Body $payload

Remove-Item Env:INGESTION_API_KEY
```

Created documents return HTTP `201` and `status: "created"`. Existing
documents return HTTP `200` and `status: "verified_existing"`.

## Idempotency

Before insertion, the API:

1. Normalizes source and canonical URLs.
2. Removes common tracking query parameters.
3. Normalizes clean text and calculates SHA-256 `content_hash`.
4. Acquires a transaction advisory lock for that hash.
5. Checks `canonical_url`, metadata source/normalized URL, and `content_hash`.

The unique canonical URL constraint and chunk unique key provide additional
database protection. The API never deletes or overwrites an existing document.

Stored document metadata includes:

```text
ingestion_mode=n8n_curated_v1
language=es
is_seed=false
ingested_by=n8n
storage_used=false
source_url
canonical_url
content_hash
```

## n8n workflow

Use the detailed workflow in
`docs/examples/n8n_curated_ingestion_workflow.md`:

1. Manual Trigger or low-frequency Schedule.
2. Small explicit list of Spanish URLs.
3. HTTP Request to download one page.
4. HTML Extract using a known main-content selector.
5. Code node to clean text and validate Spanish.
6. Set node to prepare JSON.
7. HTTP Request POST to the ingestion endpoint.
8. Switch or log node to record `created`, `verified_existing`, or reviewable
   failures.

Keep the API key in an n8n credential. Never place it in a Code or Set node.

## Verify in Supabase and the application

```sql
SELECT id, title, author, language, canonical_url, content_hash
FROM documents
WHERE raw_metadata->>'ingestion_mode' = 'n8n_curated_v1'
ORDER BY created_at DESC;

SELECT document_id, chunk_index, length(text) AS characters
FROM document_chunks
WHERE metadata->>'ingestion_mode' = 'n8n_curated_v1'
ORDER BY document_id, chunk_index;
```

Verify public endpoints:

```powershell
Invoke-RestMethod "https://api.estudiopy.com/api/documents?includeSeed=false"
Invoke-RestMethod "https://api.estudiopy.com/api/authors"
Invoke-RestMethod "https://api.estudiopy.com/api/topics"

$body = @{ query = "Jesucristo"; filters = @{ include_seed = $false } } |
  ConvertTo-Json -Depth 5
Invoke-RestMethod `
  -Uri "https://api.estudiopy.com/api/search" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body |
  ConvertTo-Json -Depth 10
```

In `https://www.estudiopy.com/library`, hide seed/test content and confirm the
new title, source, author, detail text, and chunks. Empty searches must return
`items: []`, `results: []`, and `total: 0`.

## Failure handling

- `401`: n8n did not send the same key configured in Render.
- `422`: inspect field validation, language, text length, or raw HTML.
- `503`: configure `INGESTION_API_KEY` in Render and redeploy.
- `verified_existing`: expected idempotent result, not an error.
- Database `5xx`: stop the batch and inspect Render logs; do not retry without
  a bounded delay.
