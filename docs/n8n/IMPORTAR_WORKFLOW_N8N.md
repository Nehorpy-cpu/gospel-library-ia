# Importar el workflow de ingesta curada en n8n

## Archivos

- Workflow importable: `docs/n8n/gospel_library_curated_ingestion_v1.workflow.json`
- Code Nodes fuente: `docs/n8n/code_nodes/`
- Constructor reproducible: `docs/n8n/build_workflow.mjs`

El workflow procesa una URL por vez, no descubre enlaces y espera tres segundos
antes de continuar con el siguiente documento.

## Importar

1. Abre n8n.
2. Ve a **Workflows**.
3. Selecciona **Import from File**.
4. Elige `gospel_library_curated_ingestion_v1.workflow.json`.
5. Confirma que aparecen 16 nodos.
6. Deja el workflow inactivo hasta revisar el nodo HTTP.

## Configurar la clave de ingesta

El nodo **Enviar documento a Gospel Library IA** apunta a:

```text
https://api.estudiopy.com/api/ingestion/documents
```

Configura el header de ingesta en n8n usando un valor manual seguro en el nodo
HTTP o una credencial de tipo Header Auth. No pegues el valor real en notas,
logs, Set Nodes, datos fijados ni ejemplos. Si usas una credencial Header Auth,
elimina el header manual duplicado del nodo HTTP.

## URLs iniciales

El nodo **URLs curadas en español** contiene un lote controlado de 25 URLs
reales en español:

- 10 del sitio oficial de la Iglesia, todas con `lang=spa`.
- 7 de BYU Speeches Español bajo `/spa/talks/`.
- 8 de Discursos SUD.

Cada item incluye `source_url`, `source_name`, `content_type: "text/html"` y
`tags`. No agregues portadas, listados, crawlers, documentos de prueba ni URLs
en inglés. Si agregas URLs oficiales de la Iglesia, deben declarar `lang=spa`.

## Flujo confirmado

1. **Inicio manual - Ingesta curada**
2. **URLs curadas en español**
3. **Inicializar reporte de lote**
4. **Separar lista de URLs**
5. **Procesar una URL por vez**
6. **Descargar página o recurso**
7. **Detectar tipo de recurso**
8. **Limpiar HTML y extraer contenido**
9. **Validar español y calidad mínima**
10. **Preparar payload para Gospel Library IA**
11. **¿Documento válido?**
12. Rama true: **Enviar documento a Gospel Library IA**
13. Rama true: **Registrar resultado enviado**
14. Rama false: **Registrar resultado omitido**
15. **Pausa respetuosa**
16. Final del loop: **Resumen de lote**

Conexiones críticas:

- Loop de **Procesar una URL por vez** -> **Descargar página o recurso**.
- Done de **Procesar una URL por vez** -> **Resumen de lote**.
- True de **¿Documento válido?** -> **Enviar documento a Gospel Library IA**.
- **Enviar documento a Gospel Library IA** -> **Registrar resultado enviado**.
- False de **¿Documento válido?** -> **Registrar resultado omitido**.
- **Registrar resultado enviado** -> **Pausa respetuosa**.
- **Registrar resultado omitido** -> **Pausa respetuosa**.
- **Pausa respetuosa** -> **Procesar una URL por vez**.

## Leer los registros de resultado

**Registrar resultado enviado** recibe exclusivamente la respuesta del nodo HTTP
y usa el payload original desde **Preparar payload para Gospel Library IA**. Si
la API responde HTTP 200 sin `body.status` reconocible, registra `resultado:
error` y un `api_body_preview` seguro para depurar.

**Registrar resultado omitido** recibe exclusivamente la rama false de
**¿Documento válido?** y registra `resultado: skipped` con la razón del nodo que
lo omitió.

Cada URL produce un item normalizado con:

- `resultado`: `created`, `verified_existing`, `skipped`, `rejected` o `error`.
- `title`
- `source_url`
- `source_name`
- `language`
- `chunks_count`
- `document_id`
- `mensaje`
- `http_status`

Si `resultado=skipped`, revisa `mensaje`. Normalmente indica URL no permitida,
texto corto, idioma no español, PDF pendiente o placeholder.

## Leer Resumen de lote

Al finalizar la ejecución manual, abre **Resumen de lote**. Para el lote actual
de 25 URLs, `total_procesados` debe ser 25. Si algunas URLs ya existían, se
contarán como `existentes`.

```json
{
  "resultado": "batch_summary",
  "total_procesados": 25,
  "creados": 0,
  "existentes": 25,
  "omitidos": 0,
  "rechazados": 0,
  "errores": 0,
  "titulos_creados": [],
  "urls_rechazadas": [],
  "resultados": []
}
```

Si `total_procesados=0`, revisa:

- **Inicializar reporte de lote** se ejecutó antes de separar URLs.
- **Registrar resultado enviado** o **Registrar resultado omitido** se ejecutó
  para cada URL.
- **Pausa respetuosa** vuelve a **Procesar una URL por vez**.
- La salida Done del batch llega solo a **Resumen de lote**.

## Respuestas comunes de API

- `401`: la clave de ingesta no coincide o falta.
- `400`: el JSON enviado no cumple el contrato esperado.
- `422`: la API rechazó validaciones de idioma, URL, placeholder o contenido.
- `500`: error operativo; conserva el resultado y revisa logs de Render.

El nodo HTTP tiene Never Error activado para que **Registrar resultado enviado**
pueda registrar estos casos sin cortar el lote.

## Verificar con PowerShell

```powershell
Invoke-RestMethod "https://api.estudiopy.com/api/documents?includeSeed=false"

$documents = Invoke-RestMethod "https://api.estudiopy.com/api/documents?limit=25&includeSeed=false"
$documents.items |
  Select-Object id,title,source_name,language,source_url |
  Format-Table -AutoSize

$id = $documents.items[0].id
Invoke-RestMethod "https://api.estudiopy.com/api/documents/$id`?include_chunks=true" |
  ConvertTo-Json -Depth 10

$body = @{
  query = "Jesucristo"
  filters = @{ include_seed = $false }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Uri "https://api.estudiopy.com/api/search" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body |
  ConvertTo-Json -Depth 10
```

## Probar lote de 25 URLs

1. Importa el workflow.
2. Revisa el nodo **URLs curadas en español** y confirma que contiene 25 items.
3. Ejecuta manualmente.
4. Abre **Registrar resultado enviado** y **Registrar resultado omitido** para
   confirmar que entre ambos hay 25 items.
5. Abre **Resumen de lote**.
6. Si las URLs ya existían, espera `total_procesados=25` y `existentes=25`.
7. Si alguna URL sale `skipped`, revisa `mensaje`; suele ser texto insuficiente,
   PDF pendiente o contenido que no pudo limpiarse con seguridad.
8. Si alguna URL sale `rejected`, revisa las reglas de la API y corrige la URL o
   el contenido antes de reintentar.
9. Si alguna URL sale `error`, revisa `http_status`, `api_body_preview` y logs de
   Render sin exponer credenciales.

## Regenerar y validar

```powershell
node docs/n8n/build_workflow.mjs
node --check docs/n8n/code_nodes/05_preparar_payload.js
```

Después valida JSON e importa nuevamente el archivo generado.
