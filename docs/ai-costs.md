# AI cost controls

Fase 19 agrega controles para que Gospel Library IA pueda indexar con costo predecible y seguir funcionando en modo textual cuando OpenAI no este disponible.

## Variables

- `AI_COST_MODE=low|balanced|quality`: ajusta chunking, overlap y topK efectivo.
- `OPENAI_EMBEDDING_MODEL=text-embedding-3-large`
- `OPENAI_CHAT_MODEL=gpt-5.5`
- `RAG_TOP_K=12`: limite final de fuentes enviadas al chat.
- `CHUNK_SIZE=650`: alias de `CHUNK_TARGET_TOKENS`.
- `CHUNK_OVERLAP=120`: alias de `CHUNK_OVERLAP_TOKENS`.
- `EMBEDDING_BATCH_SIZE=64`
- `MAX_DAILY_EMBEDDING_TOKENS=100000`
- `MAX_USER_CHAT_MESSAGES_PER_DAY=50`
- `MAX_USER_TALK_BUILDER_PER_DAY=20`
- `EMBEDDING_TOKEN_PRICE_PER_1K=0.00013`

## Endpoints admin

- `GET /api/admin/indexing/estimate?limit=100&force=false`: estima documentos, chunks, tokens y costo antes de indexar.
- `GET /api/admin/cost`: muestra tokens, costo, cache hits, errores OpenAI y estado de indexing.
- `POST /api/admin/indexing/pause`: pausa indexing manualmente.
- `POST /api/admin/indexing/resume`: reanuda indexing.

## Cache y reindexado

Cada chunk se identifica por `text_hash` y modelo. Si el contenido no cambia, el indexer reutiliza `embedding_cache` y evita llamar OpenAI. Si el documento cambia, solo los chunks con hash nuevo generan embeddings; los chunks existentes se saltan por `EmbeddingRecord`.

Los puntos de Qdrant usan un id derivado del `chunk_id`, por lo que `upsert` reemplaza el mismo vector y evita duplicados.

## Manejo de cuota

Si OpenAI responde `insufficient_quota`, `429` o error de cuota, el indexer registra el evento en `ai_usage_events`, pausa `ai_runtime_state` con `openai_insufficient_quota` y mantiene activa la busqueda textual PostgreSQL. `/api/chat` y `/api/search` no deben devolver 500 por falta de embeddings o cuota.

## Modos

- `low`: chunks mas grandes, menos overlap, menor topK y menor contexto.
- `balanced`: valores actuales recomendados para desarrollo.
- `quality`: mas overlap, mas candidatos y topK mayor.

Para costos bajos en local:

```bash
AI_COST_MODE=low
RAG_TOP_K=6
MAX_DAILY_EMBEDDING_TOKENS=25000
```
