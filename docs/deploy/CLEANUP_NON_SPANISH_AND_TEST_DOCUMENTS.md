# Limpieza de documentos no españoles y de prueba

## Propósito

Este procedimiento oculta de forma segura documentos en inglés, URLs con
`lang=eng`, cargas de prueba y contenido placeholder. No modifica tablas,
credenciales ni documentos válidos.

El esquema actual contiene `documents.deleted_at`, por lo que `--apply` usa
soft delete reversible:

- asigna `deleted_at`;
- cambia `status` a `HIDDEN`;
- marca `is_indexed=false`;
- registra el motivo en metadata;
- conserva chunks y relaciones para permitir una restauración completa.

Solo un esquema heredado sin `deleted_at` usa borrado físico transaccional. En
ese caso elimina primero `document_tags` y `document_chunks`, y después el
documento detectado.

## Reglas de detección

- `language=en`.
- `lang=eng` en URL fuente, URL canónica o metadata.
- título que contiene `Documento de prueba`.
- URL que contiene `prueba-n8n`.
- `metadata.test_payload=true`.
- fuente llamada `Prueba n8n`.
- texto o resumen con:
  - `[REEMPLAZAR ANTES DE ENVIAR]`;
  - `No es una cita oficial`;
  - `no reemplaza ninguna fuente doctrinal`;
  - `contenido de prueba`;
  - `placeholder`.

El mojibake español no se elimina. Se corrige separadamente con
`normalize_existing_spanish_content.py`.

## Dry-run obligatorio

```powershell
cd F:\Proyectos\gospel-library-ia-clean\apps\api
..\.venv\Scripts\activate
$env:DATABASE_URL="TU_DATABASE_URL"
python scripts/cleanup_non_spanish_and_test_documents.py --dry-run
```

El informe muestra ID, título, idioma, URL fuente, razones y cantidad de chunks.
No realiza cambios y termina con rollback.

## Aplicar

Revisa primero todo el informe. Después:

```powershell
python scripts/cleanup_non_spanish_and_test_documents.py --apply
Remove-Item Env:DATABASE_URL
```

Una segunda ejecución es idempotente: los documentos ya ocultos no vuelven a
detectarse.

## Verificar la API

```powershell
$documents = Invoke-RestMethod "https://api.estudiopy.com/api/documents?limit=100"
$documents.items |
  Select-Object id,title,language,sourceUrl |
  Format-Table

$body = @{ query = "Jesucristo" } | ConvertTo-Json
Invoke-RestMethod `
  -Uri "https://api.estudiopy.com/api/search" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body |
  ConvertTo-Json -Depth 10
```

Comprueba también que un ID oculto devuelve 404:

```powershell
Invoke-WebRequest "https://api.estudiopy.com/api/documents/ID_OCULTO?include_chunks=true"
```

## Verificar la web

Abre `https://www.estudiopy.com/library`, recarga sin caché y confirma que:

- no aparecen documentos en inglés;
- no aparecen cargas `prueba-n8n`;
- no aparece contenido placeholder;
- búsqueda y detalle de documentos válidos siguen funcionando.

## Revertir soft delete

Usa únicamente IDs revisados del informe original:

```sql
UPDATE documents
SET deleted_at = NULL,
    status = 'READY',
    updated_at = now(),
    raw_metadata = raw_metadata - 'cleanup_mode' - 'cleanup_reason' - 'cleanup_at'
WHERE id = ANY(ARRAY[
  'UUID_REVISADO'
]::uuid[]);
```

Los chunks se conservan durante soft delete, por lo que reaparecen al restaurar
el documento. No uses esta reversión si el script informó `hard_delete`.
