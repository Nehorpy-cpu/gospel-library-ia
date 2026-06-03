-- Common production query patterns.

-- Library cursor pagination.
SELECT id, title, kind, language, published_at
FROM documents
WHERE status = 'READY'
  AND visibility = 'PUBLIC'
  AND deleted_at IS NULL
  AND (published_at, id) < ($1::date, $2::uuid)
ORDER BY published_at DESC, id DESC
LIMIT 50;

-- Reader chunks.
SELECT id, chunk_index, section_title, page_number, text
FROM document_chunks
WHERE document_id = $1
ORDER BY chunk_index ASC
LIMIT 200;

-- User annotations for reader.
SELECT *
FROM highlights
WHERE user_id = $1
  AND document_id = $2
  AND deleted_at IS NULL
ORDER BY start_char ASC;

-- FTS chunk search.
SELECT
  dc.id,
  dc.document_id,
  d.title,
  ts_rank_cd(dc.search_vector, plainto_tsquery('simple', $1)) AS rank
FROM document_chunks dc
JOIN documents d ON d.id = dc.document_id
WHERE dc.search_vector @@ plainto_tsquery('simple', $1)
  AND d.status = 'READY'
  AND d.deleted_at IS NULL
ORDER BY rank DESC
LIMIT 100;

-- Fuzzy author suggestions.
SELECT id, display_name, similarity(display_name, $1) AS score
FROM authors
WHERE display_name % $1
ORDER BY score DESC
LIMIT 10;

-- Incremental sync.
SELECT *
FROM sync_events
WHERE user_id = $1
  AND created_at > $2
ORDER BY created_at ASC, server_rev ASC
LIMIT 1000;
