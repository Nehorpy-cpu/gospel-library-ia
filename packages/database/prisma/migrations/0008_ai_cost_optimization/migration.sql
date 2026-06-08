CREATE TABLE IF NOT EXISTS embedding_cache (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content_hash varchar(64) NOT NULL,
  model varchar(128) NOT NULL,
  dimensions integer NOT NULL,
  vector jsonb,
  vector_id uuid,
  chunk_id uuid REFERENCES document_chunks(id) ON DELETE SET NULL,
  token_count integer NOT NULL DEFAULT 0,
  hit_count integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  last_used_at timestamptz,
  CONSTRAINT uq_embedding_cache_hash_model UNIQUE (content_hash, model)
);

CREATE INDEX IF NOT EXISTS idx_embedding_cache_model ON embedding_cache(model);
CREATE INDEX IF NOT EXISTS idx_embedding_cache_chunk ON embedding_cache(chunk_id);

CREATE TABLE IF NOT EXISTS ai_usage_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  kind varchar(64) NOT NULL,
  model varchar(128),
  user_id uuid,
  workspace_id uuid,
  document_id uuid,
  chunk_id uuid,
  input_tokens integer NOT NULL DEFAULT 0,
  output_tokens integer NOT NULL DEFAULT 0,
  estimated_cost_usd double precision NOT NULL DEFAULT 0,
  status varchar(64) NOT NULL DEFAULT 'ok',
  error_code varchar(128),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ai_usage_created ON ai_usage_events(created_at);
CREATE INDEX IF NOT EXISTS idx_ai_usage_kind ON ai_usage_events(kind);
CREATE INDEX IF NOT EXISTS idx_ai_usage_user_created ON ai_usage_events(user_id, created_at);

CREATE TABLE IF NOT EXISTS ai_runtime_state (
  key varchar(120) PRIMARY KEY,
  value jsonb NOT NULL DEFAULT '{}'::jsonb,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_embeddings_content_hash ON embeddings(content_hash);
CREATE INDEX IF NOT EXISTS idx_chunks_text_hash ON document_chunks(text_hash);
