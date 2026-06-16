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
5. Confirma que aparecen 15 nodos.
6. Deja el workflow inactivo hasta revisar el nodo HTTP.

## Configurar la clave de ingesta

El nodo **Enviar documento a Gospel Library IA** apunta a:

```text
https://api.estudiopy.com/api/ingestion/documents
```

Configura el header de ingesta en n8n usando una variable segura o una
credencial de tipo Header Auth. No pegues el valor real en notas, logs, Set
Nodes, datos fijados ni ejemplos. Si usas una credencial Header Auth, elimina el
header manual duplicado del nodo HTTP.

## URLs iniciales

El nodo **URLs curadas en español** contiene tres URLs de prueba:

1. `https://www.churchofjesuschrist.org/study/general-conference/2022/04/55soares?lang=spa`
2. `https://speeches.byu.edu/spa/talks/brad-wilcox/su-gracia-es-suficiente/`
3. `https://discursosud.com/el-amor-puro-de-cristo/`

Cada item debe incluir `source_url`, `source_name`, `content_type` y `tags`.
Usa lotes chicos para pruebas; no agregues portadas, listados ni crawlers.

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
13. Ambas ramas: **Registrar resultado**
14. **Pausa respetuosa**
15. Final del loop: **Resumen de lote**

Conexiones críticas:

- Loop de **Procesar una URL por vez** -> **Descargar página o recurso**.
- Done de **Procesar una URL por vez** -> **Resumen de lote**.
- True de **¿Documento válido?** -> **Enviar documento a Gospel Library IA**.
- False de **¿Documento válido?** -> **Registrar resultado**.
- **Enviar documento a Gospel Library IA** -> **Registrar resultado**.
- **Registrar resultado** -> **Pausa respetuosa**.
- **Pausa respetuosa** -> **Procesar una URL por vez**.

## Leer Registrar resultado

Cada URL produce un item con:

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

Al finalizar la ejecución manual, abre **Resumen de lote**. Debe devolver:

```json
{
  "resultado": "batch_summary",
  "total_procesados": 3,
  "creados": 0,
  "existentes": 3,
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
- **Registrar resultado** se ejecutó para cada URL.
- **Pausa respetuosa** vuelve a **Procesar una URL por vez**.
- La salida Done del batch llega solo a **Resumen de lote**.

## Respuestas comunes de API

- `401`: la clave de ingesta no coincide o falta.
- `400`: el JSON enviado no cumple el contrato esperado.
- `422`: la API rechazó validaciones de idioma, URL, placeholder o contenido.
- `500`: error operativo; conserva el resultado y revisa logs de Render.

El nodo HTTP tiene Never Error activado para que **Registrar resultado** pueda
registrar estos casos sin cortar el lote.

## Verificar con PowerShell

```powershell
Invoke-RestMethod "https://api.estudiopy.com/api/documents?includeSeed=false"

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

## Probar lote de 3 URLs

1. Importa el workflow.
2. Ejecuta manualmente las tres URLs iniciales.
3. Abre **Registrar resultado** y confirma tres items.
4. Abre **Resumen de lote**.
5. Si las URLs ya existían, espera `total_procesados=3` y `existentes=3`.

## Probar lote de 10 URLs

1. Agrega URLs individuales y revisadas a **URLs curadas en español**.
2. Mantén solo fuentes permitidas.
3. Ejecuta manualmente.
4. Confirma que `total_procesados` sea igual a 10.
5. Revisa `urls_rechazadas` antes de escalar.

## Regenerar y validar

```powershell
node docs/n8n/build_workflow.mjs
node --check docs/n8n/code_nodes/05_preparar_payload.js
```

Después valida JSON e importa nuevamente el archivo generado.
