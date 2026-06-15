# Ejemplos PowerShell para ingesta n8n

## Health

```powershell
Invoke-RestMethod `
  -Uri "https://api.estudiopy.com/api/ingestion/documents/health" `
  -Method GET |
  ConvertTo-Json -Depth 5
```

## Enviar un payload

Configura la clave solo durante la sesión:

```powershell
$env:INGESTION_API_KEY="VALOR_CONFIGURADO_EN_RENDER"

$payload = Get-Content `
  ".\docs\examples\n8n_ingestion_payload_es.json" `
  -Raw

Invoke-RestMethod `
  -Uri "https://api.estudiopy.com/api/ingestion/documents" `
  -Method POST `
  -Headers @{ "X-Ingestion-Key" = $env:INGESTION_API_KEY } `
  -ContentType "application/json" `
  -Body $payload |
  ConvertTo-Json -Depth 10

Remove-Item Env:INGESTION_API_KEY
```

El archivo de ejemplo contiene texto marcado como plantilla. Sustitúyelo por
texto español limpio extraído de la URL antes de llamar a producción.

La primera ejecución debe devolver `created`. Repetir el mismo payload debe
devolver `verified_existing`.

## Verificar Biblioteca

```powershell
$documents = Invoke-RestMethod `
  -Uri "https://api.estudiopy.com/api/documents?includeSeed=false&limit=30"

$documents.items |
  Select-Object id, title, author, source, sourceUrl |
  Format-Table -AutoSize
```

## Verificar búsqueda

```powershell
$body = @{
  query = "Jesucristo"
  filters = @{
    include_seed = $false
    languages = @("es")
  }
  limit = 12
} | ConvertTo-Json -Depth 5

$search = Invoke-RestMethod `
  -Uri "https://api.estudiopy.com/api/search" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body

$search | ConvertTo-Json -Depth 10
$search.items.Count
```

Cuando no existen coincidencias, `items` y `results` deben ser listas vacías y
`total` debe ser `0`.
