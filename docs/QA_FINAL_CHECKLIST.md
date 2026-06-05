# QA Final Checklist

Fecha de ejecucion: 2026-06-05

## Automatic checks

- [x] `corepack pnpm install`
- [x] `corepack pnpm build`
- [x] `corepack pnpm test`
- [x] `corepack pnpm --dir apps/web build`
- [x] `corepack pnpm --dir apps/web lint`
- [x] `corepack pnpm --dir apps/web typecheck`
- [x] `python -m unittest discover apps/api/tests`
- [x] `python -m unittest discover rag/tests`
- [x] `python -m compileall apps/api/app rag/app scraper/app`
- [x] `docker compose config --quiet`
- [x] `docker compose down`
- [x] `docker compose up -d --build`
- [x] `docker compose ps`

## Runtime services

- [x] web healthy
- [x] api healthy
- [x] scraper-api healthy
- [x] rag-api healthy
- [x] postgres healthy
- [x] redis healthy
- [x] qdrant healthy
- [x] minio healthy
- [x] scraper/rag workers running

## Frontend routes

- [x] `/`
- [x] `/library`
- [x] `/admin`
- [x] `/study`
- [x] `/study/new`
- [x] `/study/[workspaceId]`
- [x] `/collections`
- [x] `/favorites`
- [x] `/history`
- [x] `/authors`
- [x] `/search`

## Backend endpoints

- [x] `GET /api/documents`
- [x] `GET /api/documents/summary`
- [x] `GET /api/authors`
- [x] `GET /api/topics`
- [x] `POST /api/search`
- [x] `POST /api/chat`
- [x] `GET /api/ingestion/status`
- [x] `GET /api/admin/status`
- [x] `GET /api/study-workspaces`
- [x] `GET /api/study/workspaces`
- [x] `GET /api/study/workspaces/{id}/related`

## StudyWorkspace flows

- [x] Crear workspace
- [x] Listar workspace
- [x] Abrir workspace
- [x] Agregar nota
- [x] Editar nota
- [x] Eliminar nota
- [x] Agregar cita
- [x] Eliminar cita
- [x] Crear post-it
- [x] Editar post-it
- [x] Eliminar post-it
- [x] Activar fuente
- [x] Desactivar fuente
- [x] Buscar fuentes relacionadas

## Data and RAG observations

- [x] PostgreSQL contiene documentos reales.
- [x] `GET /api/authors` y `GET /api/topics` derivan de documentos reales.
- [x] `ingestion_jobs` contiene tareas reales.
- [x] No hay documentos `Untitled document`.
- [x] Qdrant collection `doctrinal_chunks_v1` existe y esta `green`.
- [x] Qdrant tiene `points_count = 0`; fallback textual funciona.
- [x] `/api/chat` responde en modo `textual_fallback` sin 500.

## Security checks

- [x] `.env` no esta trackeado por Git.
- [x] No existe `NEXT_PUBLIC_OPENAI_API_KEY`.
- [x] `OPENAI_API_KEY` no aparece en frontend como variable publica.
- [x] No se detectaron claves OpenAI reales hardcodeadas.
- [x] StudyWorkspace usa `X-User-Id` y filtra por propietario.
- [x] Admin queda preparado para proteccion por middleware/rate limit.

## Manual browser pass

Playwright/browser automation no estuvo disponible localmente en esta sesion.
La verificacion visual queda como checklist manual antes del despliegue:

- [ ] Revisar navegacion movil en `/`, `/library`, `/study`, `/study/new`,
  `/admin`, `/search` y `/authors`.
- [ ] Confirmar que formularios muestran errores amigables al dejar campos
  requeridos vacios.
- [ ] Confirmar que search/chat muestran el aviso de fallback cuando Qdrant
  tiene cero vectores o OpenAI no tiene cuota.
- [ ] Confirmar que botones de admin muestran estado de accion al ejecutar
  scraping/reindex.
- [ ] Confirmar contraste y scroll en desktop y mobile.

## Remaining risks

- Qdrant no tiene vectores porque embeddings/OpenAI siguen pendientes.
- Muchos documentos no tienen autor confiable; los autores/temas son reales,
  pero la calidad de metadata debe limpiarse en una fase posterior.
- Celery emite advertencias por correr como root en contenedores locales; no
  bloquea QA local, pero debe endurecerse antes de produccion estricta.
