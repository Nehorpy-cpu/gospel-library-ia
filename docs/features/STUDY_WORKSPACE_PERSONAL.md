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

Alias REST de compatibilidad:

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

Al crear, el frontend llama `POST /api/study-workspaces` y redirige a
`/study/[workspaceId]`. Si hay pensamiento personal, se crea un primer bloque
`personal_note` llamado `Mi pensamiento`.

En produccion, con `NEXT_PUBLIC_API_URL=https://api.estudiopy.com`, la URL final
del navegador debe ser:

```txt
https://api.estudiopy.com/api/study-workspaces
```

## Agregar post-its

En `/study/[workspaceId]`, usar `Anadir post-it`. El frontend llama:

```txt
POST /api/study-workspaces/{workspaceId}/blocks
```

con `type=post_it`. El backend lo guarda en `post_its`.

## Editar y eliminar bloques

Cada bloque visible permite:

- `Editar`: abre campos editables de titulo, cita y contenido.
- `Guardar`: llama `PATCH /api/study-workspaces/{workspaceId}/blocks/{blockId}`.
- `Eliminar`: llama `DELETE /api/study-workspaces/{workspaceId}/blocks/{blockId}`.

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

## Variables necesarias

Frontend Vercel:

```txt
NEXT_PUBLIC_API_URL=https://api.estudiopy.com
NEXT_PUBLIC_STUDY_USER_ID=00000000-0000-4000-8000-000000000001
```

Backend Render:

```txt
CORS_ORIGINS=http://localhost:3000,https://www.estudiopy.com,https://estudiopy.com
ALLOW_DEV_AUTH_HEADERS=false
ALLOW_STUDY_DEMO_USER=true
STUDY_DEMO_USER_ID=00000000-0000-4000-8000-000000000001
```

`ALLOW_STUDY_DEMO_USER=true` mantiene la compatibilidad de la Mesa de Estudio
personal mientras no exista una sesion real activa. Solo aplica al usuario beta
configurado y no habilita headers de desarrollo para el resto de la API.

## Probar desde PowerShell

Preflight CORS seguro, sin crear datos:

```powershell
$headers = @{
  Origin = "https://www.estudiopy.com"
  "Access-Control-Request-Method" = "POST"
  "Access-Control-Request-Headers" = "content-type,x-user-id"
}
Invoke-WebRequest `
  -Method Options `
  -Uri "https://api.estudiopy.com/api/study-workspaces" `
  -Headers $headers `
  -UseBasicParsing |
  Select-Object StatusCode, Headers
```

Listar estudios del usuario beta:

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "https://api.estudiopy.com/api/study-workspaces" `
  -Headers @{ "X-User-Id" = "00000000-0000-4000-8000-000000000001" }
```

Prueba de creacion. Este comando crea un estudio real:

```powershell
$body = @{
  name = "Prueba de conexion"
  title = "Prueba de conexion"
  scriptureReference = "Helaman 5:6"
  personalThought = "Verificar que produccion crea estudios."
  topic = "Convenios"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "https://api.estudiopy.com/api/study-workspaces" `
  -ContentType "application/json" `
  -Headers @{ "X-User-Id" = "00000000-0000-4000-8000-000000000001" } `
  -Body $body
```

## Verificar en DevTools Network

Desde `https://www.estudiopy.com/study/new`, abrir DevTools > Network y crear
un estudio. La llamada esperada es:

```txt
POST https://api.estudiopy.com/api/study-workspaces
```

Estados esperados:

- `201`: estudio creado y redireccion a `/study/[workspaceId]`.
- `401`: falta sesion o el usuario beta no coincide; la UI debe mostrar
  `Debes iniciar sesion para continuar.`
- `404`: Render no tiene desplegada la ruta; redeploy backend.
- `422`: el formulario envio un payload invalido.
- `500`: revisar logs de Render y conexion a PostgreSQL.

## Troubleshooting: endpoints return 500 after schema initialization

Si la creacion falla despues de inicializar Supabase:

- Confirmar que Render tenga desplegado el commit actual.
- Confirmar que `study_workspaces.settings` exista y sea `jsonb`.
- Confirmar que existan `study_notes` y `post_its`, porque los bloques del
  estudio reutilizan esas tablas.
- Ejecutar nuevamente el script idempotente `apps/api/scripts/init_supabase_schema.py`.
- Revisar logs de Render buscando `study_workspace_created` o el error SQL
  exacto. No imprimir `DATABASE_URL`.
