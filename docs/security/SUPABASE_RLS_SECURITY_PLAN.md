# Plan de seguridad RLS para Supabase

Este documento describe como resolver los avisos de Supabase Security Advisor:

- `rls_disabled_in_public`
- `sensitive_columns_exposed`

La migracion propuesta no se aplica automaticamente desde el repositorio. Debe revisarse y ejecutarse manualmente en Supabase SQL Editor.

## Por que activar RLS

Supabase recomienda activar Row Level Security en tablas del schema `public` expuestas por su API. Al activar RLS, los clientes `anon` y `authenticated` solo pueden leer o escribir lo permitido por politicas explicitas. La API FastAPI sigue siendo la capa segura principal de Gospel Library IA.

No se usa `FORCE ROW LEVEL SECURITY` porque el backend en Render usa conexion directa a PostgreSQL/Supabase. Eso permite que FastAPI, jobs confiables y procesos de ingestion sigan operando como hoy, mientras se reduce la exposicion para clientes anonimos o autenticados que usen Supabase directo.

## Migracion

Archivo:

```text
apps/api/migrations/20260623_enable_rls_policies.sql
```

La migracion:

- habilita RLS con `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`
- crea politicas idempotentes con `DROP POLICY IF EXISTS` + `CREATE POLICY`
- no borra tablas
- no borra datos
- no trunca tablas
- no imprime secretos
- no cambia endpoints publicos
- no activa RLS forzado

## Clasificacion de tablas

### Lectura publica controlada

Estas tablas pueden leerse desde clientes Supabase anonimos o autenticados, pero solo bajo condiciones controladas:

- `sources`: solo fuentes `enabled = true`
- `documents`: solo documentos `status = 'READY'` y `deleted_at is null`
- `document_chunks`: solo chunks cuyo documento padre esta `READY` y no borrado
- `authors`: lectura publica
- `tags`: lectura publica

No se conceden escrituras anonimas a estas tablas.

### Privadas por usuario

Estas tablas quedan visibles/escribibles solo para `authenticated` cuando `user_id = auth.uid()`:

- `study_workspaces`
- `study_workspace_sources`
- `study_notes`
- `study_highlights`
- `saved_citations`
- `post_its`
- `chat_sessions`
- `study_projects`
- `user_private_sources`
- `study_ai_suggestion_cache`
- `user_preferences`
- `beta_feedback`
- `beta_activity_events`

### Privadas por relacion padre

Estas tablas no tienen `user_id` directo y se autorizan usando la tabla padre:

- `chat_messages`: por `chat_sessions.user_id`
- `study_blocks`: por `study_projects.user_id`
- `study_sources`: por `study_projects.user_id`

### Internas / backend only

Estas tablas tienen RLS habilitado, pero no tienen politicas para `anon` ni `authenticated`:

- `crawl_urls`
- `document_assets`
- `ingestion_jobs`
- `document_duplicate_relations`
- `beta_access`

El acceso debe mantenerse por FastAPI, jobs internos o service role. No deben consumirse desde navegador con anon key.

## Como aplicar en Supabase

1. Abrir Supabase Dashboard.
2. Ir a SQL Editor.
3. Copiar el contenido de:

```text
apps/api/migrations/20260623_enable_rls_policies.sql
```

4. Ejecutarlo una vez.
5. Volver a ejecutarlo si hace falta: es idempotente.

## Como verificar

En Supabase SQL Editor, ejecutar:

```text
scripts/check_supabase_rls.sql
```

Confirmar:

- `rls_enabled = true` para todas las tablas esperadas.
- `force_rls_enabled = false`.
- tablas publicas con politicas `SELECT`.
- tablas privadas con politicas `authenticated`.
- tablas internas sin grants para `anon` ni `authenticated`.

## Pruebas de API despues de aplicar

Desde PowerShell:

```powershell
$Api = "https://api.estudiopy.com"

Invoke-RestMethod "$Api/health"
Invoke-RestMethod "$Api/api/documents"
Invoke-RestMethod "$Api/api/documents/summary"
Invoke-RestMethod "$Api/api/sources/summary"
Invoke-RestMethod "$Api/api/authors"
Invoke-RestMethod "$Api/api/topics"
Invoke-RestMethod "$Api/api/ingestion/status"
Invoke-RestMethod "$Api/api/search?q=fe"
Invoke-RestMethod "$Api/api/study-workspaces"
```

Para AI suggestions health, usar un workspace real:

```powershell
$WorkspaceId = "REEMPLAZAR_POR_WORKSPACE_ID"
Invoke-RestMethod "$Api/api/study-workspaces/$WorkspaceId/ai-suggest/health"
```

## Validacion de n8n / ingestion

Si n8n usa endpoints FastAPI, no deberia verse afectado por RLS. Probar el flujo normal de ingestion desde n8n y revisar:

- respuesta HTTP del webhook o endpoint FastAPI
- logs de Render
- `GET /api/ingestion/status`

Si n8n usa una conexion directa a Supabase con rol `anon` o `authenticated`, debe migrarse a backend/API o service role seguro. No se deben publicar credenciales de service role en frontend.

## Si algo falla despues de aplicar

### Endpoints FastAPI devuelven 500

1. Revisar logs de Render.
2. Confirmar que Render sigue usando la cadena `DATABASE_URL` esperada.
3. Confirmar que no se activo `FORCE ROW LEVEL SECURITY`.
4. Ejecutar `scripts/check_supabase_rls.sql`.

### Clientes Supabase directos no ven datos

Eso es esperado para tablas privadas sin usuario autenticado o sin `user_id = auth.uid()`.

Para tablas publicas, confirmar que:

- `documents.status = 'READY'`
- `documents.deleted_at is null`
- `sources.enabled = true`

### Una tabla ya tenia politica previa

La migracion recrea solo las politicas con los nombres definidos en el archivo. Si existen politicas manuales adicionales, revisarlas antes de aplicar para evitar reglas contradictorias.

## Riesgos controlados

- Filas con `user_id is null` en tablas privadas no seran visibles por clientes Supabase directos. FastAPI puede seguir leyendolas si usa el rol backend.
- Las tablas internas quedan inaccesibles para `anon` y `authenticated`. Esto es intencional.
- La lectura publica de `documents` y `document_chunks` expone contenido publicado, no borrado y listo para consulta.

## Validaciones locales

Ejecutar desde la raiz del repositorio:

```powershell
.\scripts\validate_backend.ps1
.\scripts\validate_frontend.ps1
.\scripts\validate_all_no_docker.ps1
git diff --check
```
