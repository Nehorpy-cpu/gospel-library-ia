# Normalización de texto español y reparación de mojibake

## Qué es mojibake

Mojibake es texto UTF-8 que fue leído con una codificación incorrecta, por
ejemplo Windows-1252 o Latin-1. Un carácter correcto como `ó` puede terminar
visible como `Ã³`, y si el error se repite puede aparecer como `ÃƒÂ³`.

Ejemplos:

```txt
reflexiÃƒÂ³n -> reflexión
Ã‚Â¿CÃƒÂ³mo -> ¿Cómo
mÃƒÂ¡s -> más
ÃƒÂ©lder -> élder
RestauraciÃƒÂ³n -> Restauración
EspÃƒÂ­ritu -> Espíritu
SeÃƒÂ±or -> Señor
```

## Por qué ocurrió

El contenido de la biblioteca, n8n o respuestas de IA puede pasar por varias
capas: PDFs, HTML, JSON, PostgreSQL, FastAPI, Render y el navegador. Si una
capa decodifica bytes UTF-8 como Latin-1/Windows-1252 y luego vuelve a guardar
ese resultado, el texto queda dañado en la base.

## Cómo se previene

El backend es la fuente de verdad para reparación y normalización:

- `apps/api/app/services/spanish_text.py` contiene `repair_mojibake`,
  `normalize_spanish_text` y `normalize_json_text_fields`.
- n8n ingestion normaliza antes de insertar documentos y chunks.
- Study workspaces, notas, post-its, citas, highlights, bloques y sugerencias
  de IA normalizan texto antes de guardar o responder.
- Las respuestas públicas de biblioteca, búsqueda, autores, temas y documentos
  normalizan texto visible antes de enviarlo al frontend.

El frontend no debe intentar re-decodificar texto. Si vuelve a aparecer
mojibake, corregirlo en backend o en el origen de datos.

## Reparar datos existentes

Desde Windows PowerShell:

```powershell
cd F:\Proyectos\gospel-library-ia-clean\apps\api
.\.venv\Scripts\Activate.ps1
$env:DATABASE_URL="TU_DATABASE_URL_DE_SUPABASE_CON_SSLMODE"
python scripts/normalize_existing_spanish_content.py --dry-run
```

Si el reporte muestra cambios esperados:

```powershell
python scripts/normalize_existing_spanish_content.py --apply
```

El script es idempotente:

- no borra datos
- no trunca tablas
- solo actualiza columnas existentes
- tolera tablas faltantes
- muestra ejemplos cortos antes/después
- no imprime `DATABASE_URL`

## Tablas cubiertas

El script revisa estas tablas si existen:

```txt
documents
document_chunks
sources
authors
tags
study_workspaces
study_notes
study_highlights
saved_citations
post_its
chat_sessions
chat_messages
ingestion_jobs
study_ai_suggestion_cache
```

## Verificar en la web

1. Abrir `https://www.estudiopy.com/library`.
2. Buscar palabras con acentos: `Restauración`, `Espíritu`, `Señor`.
3. Abrir un documento y verificar título, autor, resumen, texto y chunks.
4. Abrir `/study`, crear o abrir un estudio y probar sugerencias de IA.
5. Confirmar que no aparezcan secuencias como `Ã`, `Â`, `â€` o `ï¿½`.

## Verificar por PowerShell

```powershell
Invoke-RestMethod "https://api.estudiopy.com/api/documents?limit=5" |
  ConvertTo-Json -Depth 8

Invoke-RestMethod "https://api.estudiopy.com/api/topics" |
  ConvertTo-Json -Depth 8

Invoke-RestMethod "https://api.estudiopy.com/api/authors?limit=20" |
  ConvertTo-Json -Depth 8
```

Para study:

```powershell
$workspaceId = "WORKSPACE_ID_REAL"
$headers = @{ "X-User-Id" = "00000000-0000-4000-8000-000000000001" }

Invoke-RestMethod `
  -Method Get `
  -Uri "https://api.estudiopy.com/api/study-workspaces/$workspaceId" `
  -Headers $headers |
  ConvertTo-Json -Depth 10
```

## Cómo evitar dañar texto correcto

- Ejecutar siempre `--dry-run` antes de `--apply`.
- Revisar ejemplos cortos antes/después por tabla y columna.
- No reparar URLs, IDs, slugs, hashes, tokens ni rutas de storage.
- No crear tablas vacías solo para que el script las revise.
- Si una columna no existe en Supabase, el script la salta.
