# Plan de seguridad RLS para Supabase

Este documento describe como resolver los avisos de Supabase Security Advisor:

- `rls_disabled_in_public`
- `sensitive_columns_exposed`

La migracion propuesta no se aplica automaticamente desde el repositorio. Debe revisarse y ejecutarse manualmente en Supabase SQL Editor.

Importante: en Supabase SQL Editor se pega SQL, no rutas de archivo. No pegar textos como `apps/api/migrations/20260623_enable_rls_policies.sql`, bloques markdown ni explicaciones sin `--`.

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
- revoca permisos amplios heredados en tablas y secuencias para `anon` y `authenticated`
- revoca explicitamente `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `REFERENCES` y `TRIGGER`
- vuelve a conceder solo `SELECT` en tablas de lectura publica controlada
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

Si la app decide usar exclusivamente FastAPI tambien para lectura de biblioteca, se puede endurecer aun mas revocando `SELECT` de estas tablas para `anon` y `authenticated`. La migracion actual conserva `SELECT` minimo porque es una lectura publica controlada por RLS y mantiene compatibilidad con una posible lectura directa futura.

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

Nota operativa: la migracion define politicas por `auth.uid()`, pero no concede grants directos a `authenticated` para estas tablas privadas. Hoy el acceso debe pasar por FastAPI. Si mas adelante se habilita un cliente Supabase directo autenticado, se debe crear una migracion separada con grants minimos y pruebas de producto.

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
3. En el editor local, abrir:

```text
apps/api/migrations/20260623_enable_rls_policies.sql
```

4. Copiar el contenido completo del archivo, desde la primera linea `-- Supabase RLS...` hasta `commit;`.
5. Pegar ese contenido en Supabase SQL Editor.
6. No pegar la ruta del archivo.
7. No pegar markdown fences como ```sql.
8. No pegar explicaciones sueltas sin comentario SQL.
9. Ejecutarlo una vez.
10. Volver a ejecutarlo si hace falta: es idempotente.

## Como verificar

En Supabase SQL Editor, ejecutar:

```text
scripts/check_supabase_rls.sql
```

Igual que con la migracion: abrir el archivo local, copiar su contenido completo y pegarlo en SQL Editor. No pegar solo la ruta.

Confirmar:

- `rls_enabled = true` para todas las tablas esperadas.
- `force_rls_enabled = false`.
- tablas publicas con politicas `SELECT`.
- tablas privadas con politicas `authenticated`, pero sin grants directos.
- tablas internas sin grants para `anon` ni `authenticated`.
- la ultima consulta no devuelve filas con `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `REFERENCES` o `TRIGGER`.

Para ver exactamente todos los grants visibles de `anon` y `authenticated`, ejecutar tambien:

```text
scripts/check_public_grants.sql
```

El resultado esperado despues de la migracion es que `anon` y `authenticated` conserven como maximo `SELECT` sobre:

- `sources`
- `documents`
- `document_chunks`
- `authors`
- `tags`

No debe quedar `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `REFERENCES` ni `TRIGGER`.

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

### Si aparece ERROR 42P01 relation does not exist

`ERROR 42P01` significa que PostgreSQL intento ejecutar una sentencia contra una relacion que no existe, por ejemplo una tabla opcional o futura como `study_projects`, `study_blocks`, `study_sources`, `user_private_sources` o `study_ai_suggestion_cache`.

No significa perdida de datos. Normalmente indica que se ejecuto una version anterior del check o de la migracion que referenciaba tablas opcionales de forma directa.

Que hacer:

1. No crear tablas vacias solo para que pase el check.
2. Abrir la version corregida de `scripts/check_supabase_rls.sql`.
3. Copiar el contenido completo del archivo, no la ruta.
4. Ejecutarlo nuevamente en Supabase SQL Editor.
5. Si la migracion principal tambien fallo por una tabla opcional, volver a ejecutar la version corregida de `apps/api/migrations/20260623_enable_rls_policies.sql`.

La version corregida usa catalogos (`pg_class`, `pg_namespace`, `information_schema.tables`) y `to_regclass(...)` para detectar tablas existentes antes de revisar o aplicar RLS.

## Como revertir si algo falla

La forma preferida de revertir es volver a pasar el acceso por FastAPI y ajustar grants/politicas puntuales, no desactivar seguridad globalmente. Si se necesita rollback inmediato:

1. Guardar el error exacto y los logs.
2. Confirmar si el problema viene de grants directos a Supabase o de FastAPI.
3. Si el problema es solo lectura publica directa, conceder temporalmente `SELECT` a las tablas publicas necesarias.
4. No conceder `INSERT`, `UPDATE` ni `DELETE` a `anon`.
5. No usar `FORCE ROW LEVEL SECURITY`.
6. Evitar `DISABLE ROW LEVEL SECURITY` salvo emergencia y solo tabla por tabla.

Ejemplo de concesion temporal de lectura publica:

```sql
grant select on public.sources, public.documents, public.document_chunks, public.authors, public.tags
  to anon, authenticated;
```

Luego volver a ejecutar `scripts/check_supabase_rls.sql`.

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
