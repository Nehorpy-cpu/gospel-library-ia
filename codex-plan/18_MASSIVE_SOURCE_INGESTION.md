Ejecuta la Fase 18: MASSIVE\_SOURCE\_INGESTION.



Objetivo:

Preparar y ejecutar una carga masiva controlada de fuentes doctrinales reales para Gospel Library IA.



No hacer scraping agresivo.

Respetar robots.txt y límites razonables.

No duplicar documentos.

No consumir OpenAI innecesariamente.

No romper datos existentes.



Fuentes objetivo:



1\. BYU Speeches Español:

&#x20;  - https://speeches.byu.edu/spa/talks/



2\. BYU Speeches Inglés:

&#x20;  - https://speeches.byu.edu/talks/



3\. Discursos SUD:

&#x20;  - https://discursosud.com/



4\. Conferencia General:

&#x20;  - churchofjesuschrist.org/study/general-conference



5\. Manuales de la Iglesia:

&#x20;  - churchofjesuschrist.org/study/manual



6\. Joseph Smith Papers:

&#x20;  - josephsmithpapers.org



7\. BYU Religious Studies Center:

&#x20;  - rsc.byu.edu



8\. Come, Follow Me:

&#x20;  - churchofjesuschrist.org/study/manual/come-follow-me



9\. Teachings of Presidents of the Church:

&#x20;  - churchofjesuschrist.org/study/manual/teachings-presidents



10\. Escrituras:

&#x20;  - churchofjesuschrist.org/study/scriptures



Tareas obligatorias:



1\. Crear catálogo de fuentes:

&#x20;  - sourceId

&#x20;  - name

&#x20;  - sourceType

&#x20;  - baseUrl

&#x20;  - language

&#x20;  - enabled

&#x20;  - crawlStrategy

&#x20;  - rateLimit

&#x20;  - maxPagesPerRun

&#x20;  - lastCrawledAt

&#x20;  - robotsPolicyNotes



2\. Crear seeds de fuentes.

&#x20;  No crear documentos duplicados.

&#x20;  No usar mock data.



3\. Mejorar scraping incremental:

&#x20;  - detectar URL ya procesada

&#x20;  - hash de contenido

&#x20;  - updatedAt si cambió

&#x20;  - skip si no cambió

&#x20;  - retry de fallidos

&#x20;  - límite por corrida

&#x20;  - logs por fuente



4\. Mejorar metadata:

&#x20;  - title

&#x20;  - author

&#x20;  - date

&#x20;  - language

&#x20;  - sourceType

&#x20;  - sourceUrl

&#x20;  - canonicalUrl

&#x20;  - tags

&#x20;  - topics

&#x20;  - scriptureReferences

&#x20;  - media links

&#x20;  - pdf links

&#x20;  - audio links



5\. Mejorar extracción por fuente:

&#x20;  - crear parsers específicos por sourceType

&#x20;  - fallback genérico

&#x20;  - tests de parsers



6\. Discursos SUD:

&#x20;  - extraer posts

&#x20;  - detectar PDFs

&#x20;  - guardar URL original

&#x20;  - extraer título desde h1/og:title/slug

&#x20;  - extraer autor si existe



7\. BYU Speeches Español/Inglés:

&#x20;  - extraer title

&#x20;  - speaker

&#x20;  - date

&#x20;  - transcript

&#x20;  - audio

&#x20;  - video si existe

&#x20;  - topics



8\. Church sources:

&#x20;  - usar crawling respetuoso

&#x20;  - extraer título

&#x20;  - autor si existe

&#x20;  - manual/category

&#x20;  - scripture references



9\. Joseph Smith Papers:

&#x20;  - extraer título

&#x20;  - fecha

&#x20;  - tipo de documento

&#x20;  - URL original

&#x20;  - texto disponible

&#x20;  - advertir si fuente es histórica/documental, no manual doctrinal oficial



10\. BYU RSC:

&#x20;  - extraer libro/artículo

&#x20;  - autor

&#x20;  - fecha

&#x20;  - título

&#x20;  - URL

&#x20;  - contenido



11\. Crear panel Admin de fuentes:

&#x20;  - listar fuentes

&#x20;  - activar/desactivar fuente

&#x20;  - ejecutar crawl por fuente

&#x20;  - ver últimos errores

&#x20;  - ver documentos por fuente

&#x20;  - ver último crawl

&#x20;  - limitar páginas por corrida



12\. Ingestion jobs:

&#x20;  - registrar cada corrida

&#x20;  - sourceId

&#x20;  - status

&#x20;  - startedAt

&#x20;  - finishedAt

&#x20;  - documentsFound

&#x20;  - documentsCreated

&#x20;  - documentsUpdated

&#x20;  - documentsSkipped

&#x20;  - documentsFailed

&#x20;  - errors



13\. Deduplicación:

&#x20;  - por canonicalUrl

&#x20;  - por contentHash

&#x20;  - por title+author+date

&#x20;  - evitar guardar lo mismo dos veces



14\. Indexing:

&#x20;  - no generar embeddings automáticamente para todo si OpenAI no tiene cuota

&#x20;  - permitir “index later”

&#x20;  - permitir indexar por fuente

&#x20;  - permitir estimar costo antes de indexar



15\. Fallback textual:

&#x20;  - todo documento cargado debe ser buscable textualmente aunque no tenga embedding



16\. Validaciones:

&#x20;  - ejecutar crawl limitado por fuente

&#x20;  - verificar documentos creados

&#x20;  - verificar metadata

&#x20;  - verificar ingestion\_jobs

&#x20;  - verificar búsqueda textual

&#x20;  - verificar admin



17\. Documentación:

&#x20;  - docs/sources.md

&#x20;  - docs/ingestion.md

&#x20;  - docs/scraping-ethics.md

&#x20;  - actualizar README



Reglas importantes:

\- No descargar masivamente sin límites.

\- No violar rate limits.

\- No bloquear por OpenAI.

\- No borrar documentos existentes.

\- No indexar millones de chunks sin confirmación.

\- No poner claves en código.



Resultado esperado:

El sistema puede cargar fuentes reales de forma controlada, incremental y auditable.



Al terminar:

1\. Marcar 18\_MASSIVE\_SOURCE\_INGESTION como DONE si pasa validación limitada.

2\. Hacer commit:

&#x20;  feat: fase 18 - massive source ingestion

3\. Entregar resumen:

&#x20;  - fuentes configuradas

&#x20;  - documentos cargados en prueba limitada

&#x20;  - errores por fuente

&#x20;  - próximos pasos para carga completa

