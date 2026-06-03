-- Optional production partition templates.
-- These do not alter existing tables. Use them as reference for a deliberate
-- partition migration before large historical backfills.

CREATE SCHEMA IF NOT EXISTS partition_templates;

CREATE TABLE IF NOT EXISTS partition_templates.sync_events_template (
  LIKE sync_events INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES
);

CREATE TABLE IF NOT EXISTS partition_templates.audit_logs_template (
  LIKE audit_logs INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES
);

CREATE TABLE IF NOT EXISTS partition_templates.chat_messages_template (
  LIKE chat_messages INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES
);

COMMENT ON SCHEMA partition_templates IS
  'Reference structures for future production partition migrations.';

-- Recommended future production patterns:
--
-- sync_events: RANGE(created_at), monthly partitions.
-- audit_logs: RANGE(created_at), monthly partitions.
-- chat_messages: HASH(session_id) or RANGE(created_at), depending on retention.
-- document_chunks: HASH(document_id), 32+ partitions for tens of millions of chunks.
