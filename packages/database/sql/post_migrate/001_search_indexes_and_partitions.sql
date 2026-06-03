-- Run after `prisma migrate deploy`.
-- PostgreSQL-specific search, trigram, JSONB and partial indexes.

CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS btree_gin;
CREATE EXTENSION IF NOT EXISTS btree_gist;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE documents ADD COLUMN IF NOT EXISTS search_vector tsvector;
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS search_vector tsvector;
ALTER TABLE notes ADD COLUMN IF NOT EXISTS search_vector tsvector;

CREATE OR REPLACE FUNCTION gospel_text_config(lang text)
RETURNS regconfig AS $$
BEGIN
  IF lang = 'es' THEN RETURN 'spanish'::regconfig;
  ELSIF lang = 'en' THEN RETURN 'english'::regconfig;
  ELSIF lang = 'pt' THEN RETURN 'portuguese'::regconfig;
  ELSE RETURN 'simple'::regconfig;
  END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION update_document_search_vector()
RETURNS trigger AS $$
BEGIN
  NEW.search_vector :=
    setweight(to_tsvector(gospel_text_config(NEW.language), unaccent(coalesce(NEW.title, ''))), 'A') ||
    setweight(to_tsvector(gospel_text_config(NEW.language), unaccent(coalesce(NEW.subtitle, ''))), 'B') ||
    setweight(to_tsvector(gospel_text_config(NEW.language), unaccent(coalesce(NEW.content_text, ''))), 'C');
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_chunk_search_vector()
RETURNS trigger AS $$
BEGIN
  NEW.search_vector :=
    setweight(to_tsvector(gospel_text_config(NEW.language), unaccent(coalesce(NEW.title, ''))), 'A') ||
    setweight(to_tsvector(gospel_text_config(NEW.language), unaccent(coalesce(NEW.section_title, ''))), 'B') ||
    setweight(to_tsvector(gospel_text_config(NEW.language), unaccent(coalesce(NEW.text, ''))), 'C');
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_note_search_vector()
RETURNS trigger AS $$
BEGIN
  NEW.search_vector :=
    setweight(to_tsvector('simple', unaccent(coalesce(NEW.title, ''))), 'A') ||
    setweight(to_tsvector('simple', unaccent(coalesce(NEW.plain_text, ''))), 'B');
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_documents_search_vector ON documents;
CREATE TRIGGER trg_documents_search_vector
BEFORE INSERT OR UPDATE OF title, subtitle, content_text, language ON documents
FOR EACH ROW EXECUTE FUNCTION update_document_search_vector();

DROP TRIGGER IF EXISTS trg_document_chunks_search_vector ON document_chunks;
CREATE TRIGGER trg_document_chunks_search_vector
BEFORE INSERT OR UPDATE OF title, section_title, text, language ON document_chunks
FOR EACH ROW EXECUTE FUNCTION update_chunk_search_vector();

DROP TRIGGER IF EXISTS trg_notes_search_vector ON notes;
CREATE TRIGGER trg_notes_search_vector
BEFORE INSERT OR UPDATE OF title, plain_text ON notes
FOR EACH ROW EXECUTE FUNCTION update_note_search_vector();

CREATE INDEX IF NOT EXISTS idx_documents_search_vector ON documents USING gin(search_vector);
CREATE INDEX IF NOT EXISTS idx_document_chunks_search_vector ON document_chunks USING gin(search_vector);
CREATE INDEX IF NOT EXISTS idx_notes_search_vector ON notes USING gin(search_vector);

CREATE INDEX IF NOT EXISTS idx_documents_title_trgm ON documents USING gin(title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_authors_display_name_trgm ON authors USING gin(display_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_tags_name_trgm ON tags USING gin(name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_scripture_references_display_trgm ON scripture_references USING gin(display_ref gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_documents_metadata_gin ON documents USING gin(metadata jsonb_path_ops);
CREATE INDEX IF NOT EXISTS idx_document_chunks_metadata_gin ON document_chunks USING gin(metadata jsonb_path_ops);
CREATE INDEX IF NOT EXISTS idx_embeddings_payload_gin ON embeddings USING gin(payload jsonb_path_ops);
CREATE INDEX IF NOT EXISTS idx_media_assets_metadata_gin ON media_assets USING gin(metadata jsonb_path_ops);

CREATE INDEX IF NOT EXISTS idx_documents_ready_public_lang_kind
  ON documents(language, kind, published_at DESC)
  WHERE status = 'READY' AND visibility = 'PUBLIC' AND deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_documents_source_ready_recent
  ON documents(source_id, published_at DESC)
  WHERE status = 'READY' AND deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_chunks_doc_index ON document_chunks(document_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_favorites_user_recent ON favorites(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_history_user_recent ON reading_history(user_id, last_read_at DESC);
CREATE INDEX IF NOT EXISTS idx_notes_user_active_recent ON notes(user_id, updated_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_highlights_user_active_recent ON highlights(user_id, updated_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_recent ON chat_messages(session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sync_events_user_since ON sync_events(user_id, created_at, server_rev);
