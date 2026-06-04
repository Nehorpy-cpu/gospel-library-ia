# Gospel Library IA RAG Architecture

## Objetivo

Servicio RAG doctrinal multiidioma para millones de documentos, PDFs, discursos,
escrituras y audios transcritos.

## Componentes

```txt
RAG API
  /search
  /chat
  /chat/stream
  /admin/index

PostgreSQL
  documents
  document_chunks
  embeddings
  chat_sessions
  chat_messages

Qdrant
  doctrinal_chunks_v1

Redis
  Celery broker
  query rewrite cache
  retrieval cache hook

OpenAI
  text-embedding-3-large
  gpt-4.1-mini for answer, rewriting, reranking, grounding
```

## Ingestion Pipeline

```txt
Scraper/OCR/transcription
  -> documents.text
  -> documents.metadata
  -> documents.is_indexed=false
  -> RAG /admin/index or Celery indexing job
  -> smart chunking
  -> PostgreSQL document_chunks + FTS tsvector
  -> OpenAI embedding batches
  -> Qdrant upsert
  -> embeddings record
  -> documents.is_indexed=true
```

## Embeddings Pipeline

```txt
select pending documents
  -> chunk text by structure
  -> batch chunks by EMBEDDING_BATCH_SIZE
  -> OpenAI embeddings
  -> Qdrant PointStruct
  -> payload metadata:
       chunk_id
       document_id
       source_key
       title
       author
       language
       category
       tags
       scripture_refs
       canonical_url
       published_at
       section_title
       text_hash
  -> embeddings table tracks model/version/hash
```

## Chunking Strategy

- Normalize whitespace.
- Preserve paragraphs.
- Detect headings.
- Split very large paragraphs by sentence.
- Target: 650 tokens.
- Max: 950 tokens.
- Overlap: 120 tokens.
- Store offsets, section title, language and text hash.

## Semantic Indexing

Qdrant collection:

```txt
doctrinal_chunks_v1
  vector size: OPENAI_EMBEDDING_DIMENSIONS
  distance: cosine
  payload indexes:
    document_id
    source_key
    language
    author
    category
```

## Hybrid Retrieval

```txt
query
  -> language detection
  -> query rewriting
  -> metadata filters
  -> semantic retrieval from Qdrant
  -> BM25/FTS retrieval from PostgreSQL
  -> score normalization
  -> source trust boost
  -> language boost
  -> document diversification
  -> LLM reranking
  -> context packing
```

## Ranking Formula

```txt
final_score =
  0.52 * normalized_semantic_score +
  0.36 * normalized_bm25_score +
  source_trust_boost +
  language_boost
```

Reranking then computes:

```txt
final_score =
  0.70 * llm_rerank_score +
  0.30 * previous_final_score
```

## Metadata Filtering

Supported filters:

- source_keys
- languages
- authors
- categories
- tags hook
- published_after
- published_before
- document_ids

Qdrant filters run for semantic search. SQL filters run for FTS/BM25.

## Long Context Optimization

- Candidate budget before rerank: `RETRIEVAL_CANDIDATE_TOKEN_BUDGET`.
- Final context budget: `RETRIEVAL_CONTEXT_TOKEN_BUDGET`.
- Diversification limits same-document repetition.
- Chunks are packed by ranking score while respecting token limits.

## Conversational Memory

`chat_sessions` stores the session.
`chat_messages` stores user/assistant turns and citations.
Only the latest `MEMORY_MAX_MESSAGES` are included to control context length.

## Streaming

`/chat/stream` emits SSE events:

- `session`
- `citations`
- `delta`
- `grounding`
- `done`

## Hallucination Reduction

- System prompt requires use of provided sources only.
- Answer prompt includes numbered source blocks.
- Citation markers `[1]`, `[2]` are required.
- Grounding validator checks final answer against quotes.
- Empty retrieval produces `grounded=false`.
- Source attribution includes title, author, source, URL and quote.

## Current Leadership Policy

References to the First Presidency and the Quorum of the Twelve Apostles are
time-sensitive. The RAG system prompt includes a local 2026 reference, but
answers that depend on current leadership must use recent official Church
sources from the retrieved context when available. If the context is not enough
to verify the current composition, the assistant must say so clearly.

Local 2026 reference:

- First Presidency: President Dallin H. Oaks; President Henry B. Eyring, First
  Counselor; President D. Todd Christofferson, Second Counselor.
- Quorum of the Twelve Apostles: David A. Bednar; Dieter F. Uchtdorf; Quentin L.
  Cook; Neil L. Andersen; Ronald A. Rasband; Gary E. Stevenson; Dale G.
  Renlund; Gerrit W. Gong; Ulisses Soares; Patrick Kearon; Gérald Caussé; Clark
  G. Gilbert.
- Historical/devotional mode may include President Russell M. Nelson as a
  previous prophet and doctrinally significant leader when supported by sources.
- Current-leadership mode prioritizes President Dallin H. Oaks as current
  President of the Church when supported by sources.

## Calling Focus Policy

Users can send an optional `calling_focus` object with chat requests:

```json
{
  "callingCategory": "ward-branch",
  "callingName": "Obispo",
  "customCallingName": null,
  "callingFocusEnabled": true
}
```

The prompt adds a dynamic section named `Aplicacion segun mi llamamiento:
[calling]`. Doctrine, citations, and source grounding do not change by calling.
Only application, emphasis, reflection questions, and practical examples are
adapted to the user's current responsibility. When no calling is selected, the
system uses a general discipleship focus.

## Production Scaling

Recommended scaling:

```txt
rag-api: horizontal replicas
rag-worker-indexing: horizontal replicas
qdrant: cluster or Qdrant Cloud
postgres: managed primary + read replicas
redis: managed Redis
```

For millions of documents:

- Index in batches.
- Use dedicated embedding workers.
- Keep Qdrant collection versioned.
- Reindex into `doctrinal_chunks_v2` before switching traffic.
- Partition `document_chunks` by source or document date if needed.
- Add read replica for `/search`.
- Cache query rewrites and frequent retrievals.
