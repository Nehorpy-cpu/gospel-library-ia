Este directorio queda reservado para migraciones SQL, índices especializados y particionamiento.

Para producción se recomienda:

- Particionar `crawl_urls` por `source_id` o por fecha si supera decenas de millones.
- Índices GIN sobre `documents.raw_metadata`.
- Índices BTree sobre `documents.content_hash`, `documents.source_id`, `crawl_urls.status`.
- Jobs de vacuum/analyze programados durante ventanas de baja carga.
