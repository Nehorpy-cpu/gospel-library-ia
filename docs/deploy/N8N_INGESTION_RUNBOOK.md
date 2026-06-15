# Runbook de ingesta n8n en español

## Propósito

El endpoint `POST /api/ingestion/documents` recibe documentos en español ya
limpios. Guarda metadata, texto y chunks en PostgreSQL. No usa OpenAI, Qdrant,
Supabase Storage ni crawling automático.

## Fuentes admitidas

- Discursos individuales o PDF de `https://discursosud.com/`.
- Discursos individuales bajo `https://speeches.byu.edu/spa/talks/`.
- Recursos de `churchofjesuschrist.org/study/...` con `lang=spa`.

Portadas, categorías, listados y páginas sin indicador español se rechazan.

## Configuración

En Render:

```env
INGESTION_API_KEY=<CLAVE_SECRETA_REAL>
```

En n8n:

```env
GOSPEL_LIBRARY_API_URL=https://api.estudiopy.com
INGESTION_API_KEY=<MISMA_CLAVE_SECRETA_DE_RENDER>
```

Consulta `docs/n8n/N8N_VARIABLES_AND_CREDENTIALS.md` para usar una credencial
Header Auth. Nunca guardes la clave en Git o en un nodo Set/Code.

## Importar y ejecutar

1. Importa `docs/n8n/gospel_library_curated_ingestion_v1.workflow.json`.
2. Confirma que el workflow está inactivo.
3. Conserva una sola URL durante la primera prueba.
4. Ejecuta manualmente.
5. Revisa el estado final: `created`, `verified_existing`, `skipped`,
   `rejected` o `error`.
6. Ejecuta una segunda vez; debe devolver `verified_existing`.

## Verificar el detalle

```powershell
$documents = Invoke-RestMethod "https://api.estudiopy.com/api/documents?limit=5&includeSeed=false"
$id = $documents.items[0].id
Invoke-RestMethod "https://api.estudiopy.com/api/documents/$id?include_chunks=true" |
  ConvertTo-Json -Depth 10
```

Un documento existente sin chunks devuelve `chunks: []`. Un ID inexistente
devuelve HTTP 404 con `Documento no encontrado.`.

## Normalizar datos existentes

El script no borra documentos, chunks ni URLs:

```powershell
cd apps/api
..\.venv\Scripts\activate
$env:DATABASE_URL="TU_DATABASE_URL"
python scripts/normalize_existing_spanish_content.py
Remove-Item Env:DATABASE_URL
```

Normaliza títulos, autores, fuentes, texto, chunks y metadata; traduce etiquetas
comunes y recalcula hashes de contenido. Es idempotente: una segunda ejecución
no debe reportar cambios adicionales.

## Comprobaciones

```powershell
Invoke-RestMethod "https://api.estudiopy.com/api/documents"
Invoke-RestMethod "https://api.estudiopy.com/api/authors"
Invoke-RestMethod "https://api.estudiopy.com/api/topics"

$body = @{ query = "Jesucristo" } | ConvertTo-Json
Invoke-RestMethod `
  -Uri "https://api.estudiopy.com/api/search" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
```

En la Biblioteca verifica título, autor, fuente, etiquetas, texto y enlace
original. No deben aparecer secuencias como `Ã`, `Â` o `Ãƒ`.

## Fallos

- `401`: la clave enviada por n8n no coincide con Render.
- `404` en detalle: el ID no existe.
- `422`: URL, idioma, HTML crudo o longitud inválidos.
- `503`: Render no tiene configurada `INGESTION_API_KEY`.
- `500`: detén el lote y revisa logs de Render; no hagas reintentos masivos.
