# Qdrant Cloud

## Collection

```txt
name: doctrinal_chunks_v1
vector size: 3072
distance: Cosine
```

## Payload fields

```txt
document_id
chunk_id
title
author
language
source_key
category
topic
published_at
tags
scripture_refs
```

## Manual steps

1. Create a Qdrant Cloud cluster.
2. Create an API key with read/write access.
3. Set `QDRANT_URL`, `QDRANT_API_KEY`, and `QDRANT_COLLECTION`.
4. Run the existing collection initializer from the API service shell.
5. Verify:

```txt
GET /collections/doctrinal_chunks_v1
```

Semantic search requires `points_count > 0`. Until embeddings are available,
the app must continue using textual fallback.
