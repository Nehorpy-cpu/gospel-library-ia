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
OPENAI_CHAT_MODEL=gpt-5.5
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
3. El backend llama a OpenAI Responses API con salida estructurada JSON.
4. El frontend muestra sugerencias editables.
5. Al guardar una sugerencia, el frontend reutiliza:

```txt
POST /api/study-workspaces/{workspaceId}/blocks
```

## Payload OpenAI seguro

El backend usa Responses API con `text.format` directo:

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
      "type": "json_schema",
      "name": "study_ai_suggestions",
      "schema": { "type": "object" },
      "strict": true
    }
  },
  "max_output_tokens": 2400
}
```

No usar `response_format` en Responses API. Tampoco envolver el schema dentro
de `text.format.json_schema`; el formato correcto es `text.format.name`,
`text.format.schema` y `text.format.strict`.

Si Structured Outputs devuelve `400 Bad Request`, el backend intenta un fallback
controlado con:

```json
{
  "text": {
    "format": { "type": "json_object" }
  }
}
```

El prompt sigue pidiendo JSON compatible con el schema y el backend valida y
normaliza la respuesta antes de devolverla al frontend.

## Reglas de fuentes y citas

- `quote_text` solo debe usarse cuando el texto literal esta respaldado por
  contexto local.
- `source_status=local` indica fuente encontrada en la biblioteca local.
- `source_status=user_private` queda reservado para fuentes privadas del usuario.
- `source_status=suggested` o `none` exige revision humana antes de usarlo como
  cita o referencia exacta.
- El backend no debe inventar paginas, autores, capitulos ni citas literales.
- Si una fuente no tiene titulo, autor, URL o referencia, se usa string vacio
  `""` para mantener el JSON Schema simple y estricto.

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
- `404`: Render no tiene desplegado el endpoint.
- `422`: payload invalido.
- `502`: OpenAI no devolvio una respuesta valida o fallo la llamada externa.
- `503`: `OPENAI_API_KEY` no esta configurada en Render o el modelo no esta
  disponible para la cuenta.

## Troubleshooting: OpenAI 400 Bad Request

Causas comunes:

- Usar `response_format` en `/v1/responses` en lugar de `text.format`.
- Envolver el schema como `text.format.json_schema` en vez de enviar
  `type`, `name`, `schema` y `strict` directamente.
- Configurar un modelo que no soporta Structured Outputs.
- Usar features de JSON Schema no compatibles con modo estricto.
- No pedir JSON explicitamente cuando se usa el fallback `json_object`.

Logs seguros esperados en Render:

```txt
study_workspace_ai_openai_request
model=...
has_text_format=true
schema_name=study_ai_suggestions
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
