CREATE TABLE IF NOT EXISTS document_duplicate_relations (
  id uuid PRIMARY KEY,
  canonical_document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  duplicate_document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  classification varchar(40) NOT NULL,
  detection_rule varchar(80) NOT NULL,
  confidence double precision NOT NULL,
  review_status varchar(24) NOT NULL DEFAULT 'pending',
  evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  reviewed_at timestamptz,
  CONSTRAINT ck_document_duplicate_distinct CHECK (canonical_document_id <> duplicate_document_id),
  CONSTRAINT ck_document_duplicate_classification CHECK (
    classification IN (
      'exact_duplicate',
      'probable_duplicate',
      'translation',
      'revised_edition',
      'related_media',
      'not_duplicate'
    )
  ),
  CONSTRAINT ck_document_duplicate_review_status CHECK (
    review_status IN ('confirmed', 'pending', 'rejected')
  ),
  CONSTRAINT uq_document_duplicate_relation_duplicate UNIQUE (duplicate_document_id)
);

CREATE INDEX IF NOT EXISTS idx_document_duplicate_canonical
  ON document_duplicate_relations(canonical_document_id);

CREATE INDEX IF NOT EXISTS idx_document_duplicate_classification_status
  ON document_duplicate_relations(classification, review_status);
