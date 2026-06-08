Ejecuta la Fase 19: AI\_COST\_OPTIMIZATION.



Objetivo:

Reducir el costo de OpenAI y embeddings, evitar reindexaciones innecesarias y crear controles de uso.



No reducir calidad doctrinal innecesariamente.

No romper RAG.

No llamar OpenAI en tests salvo mocks.

No reindexar documentos sin cambios.



Tareas obligatorias:



1\. Cache de embeddings:

&#x20;  - crear tabla embedding\_cache o equivalente

&#x20;  - clave por contentHash + model

&#x20;  - guardar vectorId/chunkId

&#x20;  - si el chunk no cambió, no volver a llamar OpenAI



2\. Hash de chunks:

&#x20;  - cada chunk debe tener hash

&#x20;  - si hash existe, skip embedding

&#x20;  - si texto cambia, reembed solo ese chunk



3\. Batch embeddings:

&#x20;  - enviar chunks en lotes

&#x20;  - batch size configurable

&#x20;  - manejo de rate limits

&#x20;  - retry con backoff

&#x20;  - pausa si OpenAI devuelve 429



4\. Estimación de costo:

&#x20;  - antes de indexar mostrar:

&#x20;    - documentos a indexar

&#x20;    - chunks estimados

&#x20;    - tokens estimados

&#x20;    - costo estimado

&#x20;  - endpoint:

&#x20;    GET /api/admin/indexing/estimate



5\. Modo low-cost:

&#x20;  - variable:

&#x20;    AI\_COST\_MODE=low|balanced|quality

&#x20;  - low:

&#x20;    - chunks más grandes

&#x20;    - menos overlap

&#x20;    - topK menor

&#x20;  - balanced:

&#x20;    - configuración actual razonable

&#x20;  - quality:

&#x20;    - más overlap

&#x20;    - re-ranking si existe



6\. Configuración por entorno:

&#x20;  - OPENAI\_EMBEDDING\_MODEL configurable

&#x20;  - OPENAI\_CHAT\_MODEL configurable

&#x20;  - RAG\_TOP\_K configurable

&#x20;  - CHUNK\_SIZE configurable

&#x20;  - CHUNK\_OVERLAP configurable

&#x20;  - MAX\_DAILY\_EMBEDDING\_TOKENS configurable

&#x20;  - MAX\_USER\_CHAT\_MESSAGES\_PER\_DAY configurable



7\. Límites:

&#x20;  - límite diario de tokens embeddings

&#x20;  - límite por usuario para chat

&#x20;  - límite por usuario para talk builder

&#x20;  - límite por workspace si aplica

&#x20;  - admin puede ver consumo



8\. Admin Cost Dashboard:

&#x20;  - tokens usados hoy

&#x20;  - tokens usados este mes

&#x20;  - embeddings generados

&#x20;  - embeddings saltados por cache

&#x20;  - costo estimado

&#x20;  - últimos errores OpenAI

&#x20;  - botón pausar indexing

&#x20;  - botón reanudar indexing



9\. Manejo de 429:

&#x20;  - si insufficient\_quota, pausar indexing

&#x20;  - guardar estado openai\_insufficient\_quota

&#x20;  - no seguir reintentando sin límite

&#x20;  - mostrar alerta en admin

&#x20;  - fallback textual sigue funcionando



10\. Chat:

&#x20;  - limitar contexto

&#x20;  - usar fuentes topK

&#x20;  - truncar documentos largos

&#x20;  - evitar enviar texto innecesario

&#x20;  - cachear respuestas opcionalmente por query+sources si es seguro



11\. Talk Builder:

&#x20;  - si OpenAI no está disponible, generar plantilla manual

&#x20;  - si está disponible, usar solo citas/notas necesarias

&#x20;  - no enviar todo el workspace si no hace falta



12\. Tests:

&#x20;  - embedding cache skip funciona

&#x20;  - estimate endpoint funciona

&#x20;  - insufficient\_quota pausa indexing

&#x20;  - fallback textual sigue funcionando

&#x20;  - no se llama OpenAI en tests reales



13\. Documentación:

&#x20;  - docs/ai-costs.md

&#x20;  - explicar cómo cargar crédito

&#x20;  - explicar diferencia ChatGPT Plus vs API

&#x20;  - explicar cómo estimar costos

&#x20;  - explicar cómo pausar indexing



Validaciones:

\- tests pasan

\- build pasa

\- estimate endpoint funciona

\- admin muestra métricas

\- Qdrant no duplica vectores

\- embeddings no se regeneran si no hubo cambios



Resultado esperado:

La app puede crecer sin gastar IA innecesariamente.



Al terminar:

1\. Marcar 19\_AI\_COST\_OPTIMIZATION como DONE.

2\. Hacer commit:

&#x20;  feat: fase 19 - ai cost optimization

3\. Entregar resumen:

&#x20;  - ahorro implementado

&#x20;  - endpoints nuevos

&#x20;  - variables nuevas

&#x20;  - cómo usar modo low-cost

