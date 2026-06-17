# Study Projects Personal Workspace

## Proposito

La Mesa de Estudio Doctrinal agrega una capa personal sobre la biblioteca ya existente. Un usuario crea estudios con titulo, escritura base, pensamiento personal y bloques editables. La IA puede sugerir informacion organizada, pero no guarda automaticamente nada: el usuario decide que guardar, editar, descartar o exportar.

Esta funcion no reemplaza la biblioteca, n8n, `/api/documents`, `/api/search` ni los workspaces historicos. Los endpoints antiguos siguen disponibles.

## Flujo de Usuario

1. Abrir `/study/new`.
2. Completar titulo, escritura base, pensamiento personal, tema y contexto de llamamiento.
3. Crear el estudio.
4. En `/study/[id]`, pulsar `Anadir informacion con IA`.
5. Revisar sugerencias por bloque.
6. Guardar, editar, descartar o guardar todo.
7. Agregar citas manuales o post-its.
8. Exportar el estudio a Markdown cuando sea necesario.

## Tablas

Tablas nuevas:

- `study_projects`: cabecera del estudio personal.
- `study_blocks`: bloques editables, manuales o generados por IA.
- `study_sources`: fuentes asociadas al estudio.
- `user_private_sources`: citas cortas o notas privadas del usuario.
- `study_ai_suggestion_cache`: cache por `study_project_id`, usuario y hash del prompt para no repetir llamadas.

Tablas reutilizadas:

- `documents`
- `document_chunks`
- `study_workspaces`
- `study_notes`
- `saved_citations`
- `post_its`

El inicializador seguro sigue siendo:

```powershell
cd apps/api
.\.venv\Scripts\activate
$env:DATABASE_URL="TU_DATABASE_URL_DE_SUPABASE_CON_SSLMODE"
python scripts/init_supabase_schema.py
```

## Endpoints

- `GET /api/study-projects`
- `POST /api/study-projects`
- `GET /api/study-projects/{id}`
- `PATCH /api/study-projects/{id}`
- `DELETE /api/study-projects/{id}`
- `POST /api/study-projects/{id}/blocks`
- `PATCH /api/study-projects/{id}/blocks/{block_id}`
- `DELETE /api/study-projects/{id}/blocks/{block_id}`
- `POST /api/study-projects/{id}/sources`
- `GET /api/study-projects/private-sources`
- `POST /api/study-projects/private-sources`
- `POST /api/study-projects/{id}/ai-suggest`

`POST /api/study-projects/{id}/ai-suggest` devuelve `suggestions`, no texto plano unico. Las sugerencias no se guardan hasta que el usuario las acepte.

## OpenAI API

Configurar solamente en backend:

```txt
OPENAI_API_KEY=
OPENAI_CHAT_MODEL=gpt-5.5
MAX_USER_STUDY_AI_PER_DAY=20
STUDY_AI_MAX_SUGGESTIONS=10
```

No crear `NEXT_PUBLIC_OPENAI_API_KEY`. El frontend nunca llama a OpenAI.

El servicio usa la Responses API con Structured Outputs para pedir JSON con bloques. Si falta `OPENAI_API_KEY` o la llamada falla, devuelve sugerencias de respaldo estructuradas y marcadas como `idea_relacionada`.

## Fuentes Privadas

El usuario puede guardar fuentes privadas cortas en `user_private_sources`.
Usos permitidos:

- Citas breves.
- Notas personales.
- Referencias privadas para estudio familiar.

No se debe copiar un libro completo ni publicar una base de libros protegidos.

## Evitar Citas Inventadas

Reglas aplicadas en el prompt y en la UI:

- Toda cita literal debe estar en `quoteText`.
- Si no hay fuente local, `sourceStatus` debe ser `referencia_sugerida` o `idea_relacionada`.
- No inventar pagina, capitulo o autor.
- Preferir resumen, parafrasis y referencias.
- El usuario puede editar o eliminar cualquier bloque.

## Prueba Local

Backend:

```powershell
cd apps/api
python -m compileall app
$env:PYTHONPATH="."
python -m unittest discover -s tests
```

Frontend:

```powershell
cd apps/web
$env:NEXT_PUBLIC_API_URL="https://api.estudiopy.com"
$env:NEXT_PUBLIC_APP_URL="https://www.estudiopy.com"
$env:NEXT_PUBLIC_ENVIRONMENT="production"
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm build
```

Prueba manual:

1. Ejecutar el inicializador de schema.
2. Abrir `/study/new`.
3. Crear un estudio con `Helaman 5:6`.
4. Abrir `/study/{id}`.
5. Pulsar `Anadir informacion con IA`.
6. Guardar un bloque sugerido y editarlo.

## Despliegue

1. Ejecutar `apps/api/scripts/init_supabase_schema.py` en Supabase.
2. Confirmar variables backend en Render.
3. Desplegar API.
4. Desplegar frontend en Vercel.
5. Verificar `/api/study-projects` con usuario autenticado o headers de desarrollo habilitados.

## Limitaciones

- La primera version usa busqueda textual local sobre `documents` y `document_chunks`; no depende de Qdrant.
- El export inicial es Markdown desde el cliente.
- RLS no se activa todavia.
- El cache se invalida por hash de prompt y contexto local basico, no por cada edicion futura de documento.
