-- Private, user-owned study excerpts. Never expose these through public document routes.
ALTER TABLE IF EXISTS user_private_sources
  ADD COLUMN IF NOT EXISTS reference text,
  ADD COLUMN IF NOT EXISTS topic text,
  ADD COLUMN IF NOT EXISTS scripture_reference text,
  ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS archived_at timestamptz;

CREATE INDEX IF NOT EXISTS idx_user_private_sources_active_user_updated
  ON user_private_sources(user_id, updated_at DESC) WHERE archived_at IS NULL;
