# Sugerencias con IA para Mesa de Estudio Doctrinal

## Proposito

El boton `Anadir informacion con IA` en `/study/[workspaceId]` genera bloques
doctrinales sugeridos para un estudio personal. La IA no guarda nada
automaticamente: el usuario puede editar, guardar o descartar cada sugerencia.

## Endpoint usado

Ruta canonica:

```txt
POST /api/study-workspaces/{workspaceId}/ai-suggest
```

Alias compatible:

```txt
POST /api/study/workspaces/{workspaceId}/ai-suggest
```

Payload:

```json
{
  "mode": "rapido",
  "userPrompt": "Conecta este pasaje con Jesucristo y mi llamamiento",
  "preferredSources": ["biblioteca", "manuales", "discursos"],
  "maxSuggestions": 8
}
```

Respuesta:

```json
{
  "suggestions": [
    {
      "type": "doctrinal_analysis",
      "title": "Analisis doctrinal",
      "content": "Texto editable",
      "source_title": "",
      "source_author": "",
      "source_reference": "",
      "source_url": "",
      "quote_text": "",
      "is_ai_generated": true,
      "confidence": "medium",
      "source_status": "suggested"
    }
  ],
  "sources_used": [],
  "warnings": []
}
```

## Variables necesarias

Backend Render:

```txt
OPENAI_API_KEY=...
OPENAI_CHAT_MODEL=gpt-4.1-mini
STUDY_AI_MAX_SUGGESTIONS=12
```

Si `OPENAI_CHAT_MODEL` esta vacio, el backend usa el fallback seguro
`gpt-4.1-mini`. Si Render devuelve `model_not_found`, configurar un modelo
disponible para la cuenta.

No configurar `NEXT_PUBLIC_OPENAI_API_KEY` en Vercel. La clave de OpenAI se usa
solo desde FastAPI.

## Como funciona

1. El frontend llama al backend con `POST /api/study-workspaces/{id}/ai-suggest`.
2. FastAPI verifica el usuario y carga el workspace, sus bloques existentes y
   contexto local de la biblioteca.
3. El backend llama a OpenAI Responses API en modo JSON simple.
4. El frontend muestra sugerencias editables.
5. Al guardar una sugerencia, el frontend reutiliza:

```txt
POST /api/study-workspaces/{workspaceId}/blocks
```

## Payload OpenAI estable

El backend usa Responses API con `json_object` por estabilidad:

```json
{
  "model": "OPENAI_CHAT_MODEL o gpt-4.1-mini",
  "store": false,
  "input": [
    { "role": "system", "content": "..." },
    { "role": "user", "content": "{...}" }
  ],
  "text": {
    "format": {
      "type": "json_object"
    }
  },
  "max_output_tokens": 2400
}
```

No usar `response_format` en Responses API. No usar `json_schema`, `strict`,
`text.verbosity`, `reasoning`, `temperature` ni parametros experimentales en
este flujo de produccion estable.

Si `json_object` devuelve `400 Bad Request`, el backend intenta un fallback
controlado sin `text.format`:

```json
{
  "model": "OPENAI_CHAT_MODEL o gpt-4.1-mini",
  "store": false,
  "input": [
    { "role": "system", "content": "..." },
    { "role": "user", "content": "{...}" }
  ],
  "max_output_tokens": 2400
}
```

El prompt pide: responder unicamente con JSON valido, sin Markdown, sin bloques
``` y sin explicacion fuera del JSON. El backend extrae el primer objeto JSON
valido si la respuesta trae texto alrededor, valida manualmente y normaliza
campos faltantes antes de devolverlos al frontend.

Structured Outputs estricto (`json_schema`) queda como fase futura. Para esta
app personal/familiar se prioriza estabilidad y parsing manual robusto.

## Reglas de fuentes y citas

- `quote_text` solo debe usarse cuando el texto literal esta respaldado por
  contexto local.
- `source_status=local` indica fuente encontrada en la biblioteca local.
- `source_status=user_private` queda reservado para fuentes privadas del usuario.
- `source_status=suggested` o `none` exige revision humana antes de usarlo como
  cita o referencia exacta.
- El backend no debe inventar paginas, autores, capitulos ni citas literales.
- Si una fuente no tiene titulo, autor, URL o referencia, se usa string vacio
  `""` para mantener un contrato JSON simple y facil de normalizar.

## Probar desde PowerShell

Reemplazar `WORKSPACE_ID` por un estudio real. No incluir secretos en consola.

```powershell
$body = @{
  mode = "rapido"
  userPrompt = "Dame una conexion con Jesucristo y una pregunta de reflexion"
  preferredSources = @("biblioteca", "manuales", "discursos")
  maxSuggestions = 4
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "https://api.estudiopy.com/api/study-workspaces/WORKSPACE_ID/ai-suggest" `
  -ContentType "application/json" `
  -Headers @{ "X-User-Id" = "00000000-0000-4000-8000-000000000001" } `
  -Body $body
```

## Verificar en DevTools Network

Desde `https://www.estudiopy.com/study/[workspaceId]`:

1. Abrir DevTools > Network.
2. Presionar `Anadir informacion con IA`.
3. Presionar `Generar sugerencias`.
4. Confirmar la llamada:

```txt
POST https://api.estudiopy.com/api/study-workspaces/{workspaceId}/ai-suggest
```

Estados esperados:

- `200`: sugerencias generadas.
- `401`: falta sesion o usuario valido.
- `404`: no existe el estudio solicitado o Render no tiene desplegado el endpoint.
- `422`: payload invalido.
- `502`: OpenAI no devolvio una respuesta valida o fallo la llamada externa.
- `503`: `OPENAI_API_KEY` no esta configurada en Render o el modelo no esta
  disponible para la cuenta.
- `504`: OpenAI tardo demasiado en responder.

## Solucion de errores 500 en ai-suggest

El endpoint `ai-suggest` debe devolver errores controlados para fallas esperables
y registrar el stage exacto en Render con el evento:

```txt
study_workspace_ai_suggestions_failed
```

Campos seguros esperados en el log:

```txt
workspace_id=...
user_id=...
mode=...
max_suggestions=...
error_type=...
error_message=...
stage=load_workspace|load_blocks|local_context|build_prompt|openai_request|parse_response|normalize_response|response_validation
```

No debe aparecer `OPENAI_API_KEY`, bearer tokens, prompts completos, contenido
completo del estudio ni respuestas extensas de OpenAI.

Significado de status:

- `404`: no se encontro el estudio solicitado.
- `502`: OpenAI respondio con una solicitud invalida, JSON invalido, formato
  inesperado, respuesta vacia o una respuesta que no valida contra el contrato
  del frontend.
- `503`: falta `OPENAI_API_KEY` en Render o `OPENAI_CHAT_MODEL` apunta a un
  modelo no disponible para la cuenta.
- `504`: OpenAI tardo demasiado en responder.
- `500`: error interno inesperado fuera de las fallas controladas; revisar
  `stage`, `error_type` y `error_message` en Render.

Para revisar logs en Render:

1. Abrir el servicio backend en Render.
2. Ir a `Logs`.
3. Filtrar por `study_workspace_ai_suggestions_failed`.
4. Revisar `stage` y `error_type`.

Para confirmar configuracion en Render sin imprimir secretos:

1. Ir a `Environment`.
2. Verificar que `OPENAI_API_KEY` exista y no este vacia.
3. Configurar `OPENAI_CHAT_MODEL=gpt-4.1-mini` si el modelo actual devuelve
   `model_not_found` o no esta disponible.
4. Guardar cambios y redeployar el backend.

Prueba PowerShell de produccion, sin secretos:

```powershell
$workspaceId = "WORKSPACE_ID_REAL"
$body = @{
  mode = "rapido"
  userPrompt = "Dame una conexion con Jesucristo y una pregunta de reflexion"
  maxSuggestions = 3
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "https://api.estudiopy.com/api/study-workspaces/$workspaceId/ai-suggest" `
  -ContentType "application/json" `
  -Headers @{ "X-User-Id" = "00000000-0000-4000-8000-000000000001" } `
  -Body $body
```

El endpoint no guarda sugerencias automaticamente. Para guardar una sugerencia,
el frontend llama despues a:

```txt
POST /api/study-workspaces/{workspaceId}/blocks
```

## Troubleshooting: OpenAI 400 Bad Request

Causas comunes:

- Usar `response_format` en `/v1/responses`.
- Usar `json_schema`/Structured Outputs con un modelo o cuenta que no lo acepta.
- Configurar un modelo no disponible para la cuenta.
- No pedir JSON explicitamente en el prompt cuando se usa `json_object`.
- Enviar parametros no necesarios o incompatibles como `reasoning`,
  `text.verbosity`, `temperature` o schema estricto.

Logs seguros esperados en Render:

```txt
study_workspace_ai_openai_request
model=...
has_text_format=true
schema_name=null
input_type=array
max_output_tokens=2400
```

El log no debe incluir `OPENAI_API_KEY`, prompt completo ni contenido completo
del estudio. Si OpenAI devuelve un error, el backend registra solo campos
seguros como `error.message`, `error.type`, `error.param` y `error.code`.

## Costos y limites

- `maxSuggestions` acepta de 1 a 12.
- `STUDY_AI_MAX_SUGGESTIONS` permite bajar el limite desde Render.
- El prompt envia solo contexto resumido del estudio y de fuentes locales.
- La llamada usa `store=false` para no pedir almacenamiento del request.

## Limitaciones actuales

- Las sugerencias no se cachean todavia para workspaces.
- Las fuentes privadas se leen si la tabla existe, pero la experiencia visual
  todavia no incluye un gestor dedicado de fuentes privadas para este flujo.
- Qdrant puede seguir en `error` en `/health`; este flujo usa contexto SQL local
  y no depende de Qdrant para generar sugerencias.
