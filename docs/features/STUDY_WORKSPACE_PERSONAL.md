# Mesa de Estudio Doctrinal Personal

## Proposito

La Mesa de Estudio Doctrinal permite crear estudios personales o familiares con
una escritura base, un pensamiento personal, un tema y bloques editables. Esta
primera version se concentra en la estructura de workspace y edicion manual.
La IA queda preparada para una fase posterior, sin exponer claves ni llamar
OpenAI desde el frontend.

## Rutas frontend

- `/study`: lista de estudios guardados y acceso al primer estudio disponible.
- `/study/new`: formulario para crear un estudio.
- `/study/[workspaceId]`: detalle del estudio, bloques, post-its y acciones.

## Endpoints backend

Workspaces canonicos:

- `GET /api/study-workspaces`
- `POST /api/study-workspaces`
- `GET /api/study-workspaces/{id}`
- `PATCH /api/study-workspaces/{id}`
- `DELETE /api/study-workspaces/{id}`

Alias REST usados por el frontend:

- `GET /api/study/workspaces`
- `POST /api/study/workspaces`
- `GET /api/study/workspaces/{id}`
- `PATCH /api/study/workspaces/{id}`
- `DELETE /api/study/workspaces/{id}`

Bloques editables:

- `GET /api/study-workspaces/{id}/blocks`
- `POST /api/study-workspaces/{id}/blocks`
- `PATCH /api/study-workspaces/{id}/blocks/{block_id}`
- `DELETE /api/study-workspaces/{id}/blocks/{block_id}`
- `GET /api/study/workspaces/{id}/blocks`
- `POST /api/study/workspaces/{id}/blocks`
- `PATCH /api/study/workspaces/{id}/blocks/{block_id}`
- `DELETE /api/study/workspaces/{id}/blocks/{block_id}`

Tambien siguen disponibles los endpoints existentes de notas, citas,
highlights, post-its, filtros y documentos relacionados.

## Tablas reutilizadas

No se crean tablas nuevas para esta primera version. Se reutilizan:

- `study_workspaces`: cabecera del estudio.
- `study_notes`: notas, reflexiones, escrituras y citas manuales como bloques.
- `post_its`: post-its del estudio.
- `saved_citations`: citas guardadas desde documentos existentes.
- `study_highlights`: resaltados vinculados a documentos.
- `study_workspace_sources`: filtros/fuentes del workspace.

Los campos especificos del estudio personal se guardan en `study_workspaces.settings`:

- `title`
- `scriptureReference`
- `scriptureText`
- `personalThought`
- `topic`
- `callingContext`

Los metadatos de bloque se guardan en `study_notes.position` o `post_its.position`:

- `blockType`
- `sourceTitle`
- `sourceAuthor`
- `sourceReference`
- `sourceUrl`
- `quoteText`
- `isAiGenerated`
- `sortOrder`

## Crear un estudio

Desde `/study/new`, completar:

- Titulo del estudio
- Escritura base
- Pensamiento personal
- Tema

Al crear, el frontend llama `POST /api/study/workspaces` y redirige a
`/study/[workspaceId]`. Si hay pensamiento personal, se crea un primer bloque
`personal_note` llamado `Mi pensamiento`.

## Agregar post-its

En `/study/[workspaceId]`, usar `Anadir post-it`. El frontend llama:

```txt
POST /api/study/workspaces/{workspaceId}/blocks
```

con `type=post_it`. El backend lo guarda en `post_its`.

## Editar y eliminar bloques

Cada bloque visible permite:

- `Editar`: abre campos editables de titulo, cita y contenido.
- `Guardar`: llama `PATCH /api/study/workspaces/{workspaceId}/blocks/{blockId}`.
- `Eliminar`: llama `DELETE /api/study/workspaces/{workspaceId}/blocks/{blockId}`.

El borrado es suave: marca `deleted_at` en la tabla real reutilizada.

## Proxima fase de IA

El boton `Anadir informacion con IA` existe como preparacion visual. En esta
fase muestra el mensaje:

```txt
Esta funcion se activara en la siguiente fase.
```

La siguiente fase puede conectar este boton al backend seguro de sugerencias,
manteniendo estas reglas:

- OpenAI solo desde backend.
- Nunca exponer `OPENAI_API_KEY` en frontend.
- La IA devuelve bloques sugeridos, no guarda automaticamente.
- El usuario decide que guardar, editar o descartar.
