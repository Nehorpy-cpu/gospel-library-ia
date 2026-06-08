CREATE TABLE IF NOT EXISTS document_metadata_repair_audit (
  id uuid PRIMARY KEY,
  document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  field_name varchar(40) NOT NULL,
  previous_value text,
  repaired_value text NOT NULL,
  repaired_from varchar(80) NOT NULL,
  repaired_at timestamptz NOT NULL DEFAULT now(),
  reverted_at timestamptz,
  CONSTRAINT uq_document_metadata_repair_field UNIQUE (document_id, field_name)
);

CREATE INDEX IF NOT EXISTS idx_document_metadata_repair_audit_document
  ON document_metadata_repair_audit(document_id);
