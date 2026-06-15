# Importar el workflow de ingesta curada en n8n

## Archivos

- Workflow importable:
  `docs/n8n/gospel_library_curated_ingestion_v1.workflow.json`
- Código fuente de los Code Nodes:
  `docs/n8n/code_nodes/`
- Constructor reproducible:
  `docs/n8n/build_workflow.mjs`

El workflow procesa una URL por vez, no descubre enlaces y espera tres segundos
antes de continuar con el siguiente documento.

## Importar el JSON

1. Abre n8n.
2. Ve a **Workflows**.
3. Selecciona **Import from File**.
4. Elige `gospel_library_curated_ingestion_v1.workflow.json`.
5. Confirma que aparecen trece nodos y que el workflow permanece inactivo.
6. Abre los nodos HTTP y revisa sus expresiones antes de ejecutar.

n8n también permite pegar un workflow copiado directamente en el lienzo, pero
para esta versión se recomienda importar el archivo completo.

## Variables necesarias

En una instalación autohospedada de n8n configura:

```env
GOSPEL_LIBRARY_API_URL=https://api.estudiopy.com
INGESTION_API_KEY=VALOR_SECRETO_COMPARTIDO_CON_RENDER
```

Reinicia n8n después de agregar variables. El workflow usa:

```text
$env.GOSPEL_LIBRARY_API_URL
$env.INGESTION_API_KEY
```

La variable `INGESTION_API_KEY` debe coincidir con la configurada en Render.
No la agregues a Git, al payload, a un Set Node ni a los datos fijados de n8n.
No uses textos literales de ejemplo como clave. Genera un valor aleatorio largo
y guárdalo únicamente como variable secreta o credencial.

## Alternativa con credencial Header Auth

Si la instancia no permite acceso a `$env`:

1. Crea una credencial **Header Auth** en n8n.
2. Usa el nombre `X-Ingestion-Key`.
3. Guarda la clave como valor secreto.
4. Abre **Enviar documento a Gospel Library IA**.
5. Cambia Authentication a la credencial Header Auth creada.
6. Elimina el header manual `X-Ingestion-Key` del nodo para no duplicarlo.

La credencial no se exporta dentro del workflow. Cada instancia debe asociarla
después de importar.

## URLs iniciales

El nodo **URLs curadas en español** contiene únicamente:

1. `https://discursosud.com/el-amor-puro-de-cristo/`
2. `https://speeches.byu.edu/spa/talks/brad-wilcox/su-gracia-es-suficiente/`
3. `https://www.churchofjesuschrist.org/study/general-conference/2022/04/55soares?lang=spa`

Son páginas individuales, no portadas ni listados. Antes de una ejecución real,
abre cada URL y confirma que continúa disponible y en español.

## Cambiar la lista

Edita únicamente el array del nodo **URLs curadas en español**. Cada elemento
debe incluir:

```json
{
  "source_url": "https://URL-INDIVIDUAL",
  "source_name": "Nombre de fuente",
  "content_type": "text/html",
  "tags": ["Tema"]
}
```

Usa como máximo cinco URLs durante pruebas. Solo se aceptan documentos
individuales HTTPS de las tres fuentes autorizadas por la API.

## Probar una sola URL

1. Conserva un solo objeto en el array.
2. Pulsa **Execute workflow**.
3. Inspecciona cada nodo sin fijar datos que contengan contenido completo.
4. Confirma que **Registrar resultado** produce uno de estos estados:
   - `created`
   - `verified_existing`
   - `skipped`
   - `rejected`
   - `error`
5. Ejecuta una segunda vez. El resultado esperado es `verified_existing`.

## Flujo de datos

1. **Descargar página o recurso** obtiene texto con timeout de 30 segundos.
2. **Detectar tipo de recurso** clasifica HTML, PDF o recurso desconocido.
3. Los PDF quedan como `skipped_pdf_pending`; no se guarda el binario.
4. **Limpiar HTML y extraer contenido** elimina estructura y devuelve texto.
   También repara entidades HTML, espacios no separables y mojibake UTF-8 común.
5. **Validar español y calidad mínima** exige título, más de 300 caracteres y
   marcadores suficientes de español. También rechaza idiomas declarados
   `eng`, `por`, `fra`, `ita`, `deu`, `language=en`, URLs no españolas y
   cualquier texto de prueba o placeholder.
6. **Preparar payload para Gospel Library IA** construye el contrato de API.
   Normaliza título, autor, fuente, resumen, contenido y traduce etiquetas
   doctrinales comunes al español.
7. **¿Documento válido?** evita enviar documentos omitidos.
8. **Enviar documento a Gospel Library IA** llama a Render.
9. **Registrar resultado** normaliza el resumen en español.
10. **Pausa respetuosa** espera tres segundos.

## Verificar en la aplicación

```powershell
Invoke-RestMethod `
  -Uri "https://api.estudiopy.com/api/documents?includeSeed=false"

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

Después abre `https://www.estudiopy.com/library`, oculta el contenido seed/test
y verifica título, autor, fuente, texto y enlace original.

## Evitar scraping masivo

- Mantén lotes de una URL.
- No agregues nodos que recorran enlaces.
- No importes portadas, categorías, buscadores o archivos de paginación.
- Usa listas explícitas de hasta cinco URLs durante pruebas.
- Mantén la pausa de tres segundos.
- No configures reintentos ilimitados.
- Revisa manualmente cualquier cambio de selector o extractor.
- BYU solo acepta URLs individuales bajo `/spa/talks/`.
- El sitio oficial requiere `lang=spa`; cualquier otra variante queda omitida.
- Nunca uses `lang=eng`, `lang=por`, `lang=fra`, `lang=ita` o `lang=deu`.
- No envíes títulos `Documento de prueba`, `test_payload=true` ni frases como
  `[REEMPLAZAR ANTES DE ENVIAR]`, `No es una cita oficial`,
  `contenido de prueba` o `placeholder`.

## PDFs

Esta versión detecta PDF y devuelve `skipped_pdf_pending`. Conserva la URL pero
no descarga, extrae ni guarda el archivo. Para habilitar PDFs más adelante:

1. Usa un nodo de extracción acotada.
2. Descarta el binario después de obtener texto.
3. Valida idioma y calidad.
4. Envía `content_type: application/pdf`, texto limpio y URL original.
5. No uses Supabase Storage salvo decisión arquitectónica explícita.

## Regenerar el workflow

Cuando cambie un archivo de `code_nodes`, ejecuta:

```powershell
node docs/n8n/build_workflow.mjs
```

Después valida e importa nuevamente el JSON generado.
