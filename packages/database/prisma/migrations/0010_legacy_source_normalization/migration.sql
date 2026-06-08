CREATE TABLE IF NOT EXISTS source_legacy_cleanup_audit (
  source_id uuid PRIMARY KEY,
  source_key varchar(100) NOT NULL,
  previous_enabled boolean NOT NULL,
  previous_source_type varchar(100),
  previous_config jsonb NOT NULL DEFAULT '{}'::jsonb,
  replacement_key varchar(100),
  migrated_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO source_legacy_cleanup_audit (
  source_id, source_key, previous_enabled, previous_source_type,
  previous_config, replacement_key
)
SELECT
  id,
  key,
  enabled,
  source_type,
  config,
  CASE key
    WHEN 'byu_speeches_en' THEN 'byu_speeches'
    WHEN 'discursosud' THEN 'discursos_sud'
    WHEN 'josephsmithpapers' THEN 'joseph_smith_papers'
    ELSE NULL
  END
FROM sources
WHERE key IN ('byu_speeches_en', 'discursosud', 'josephsmithpapers', 'churchofjesuschrist')
ON CONFLICT (source_id) DO NOTHING;

UPDATE sources
SET enabled = false,
    source_type = CASE key
      WHEN 'discursosud' THEN 'discursos_sud'
      WHEN 'josephsmithpapers' THEN 'joseph_smith_papers'
      ELSE source_type
    END,
    config = config || jsonb_build_object(
      'legacy', true,
      'legacyDisabledReason', 'duplicate_or_unbounded_source_catalog',
      'replacementSourceKey', CASE key
        WHEN 'byu_speeches_en' THEN 'byu_speeches'
        WHEN 'discursosud' THEN 'discursos_sud'
        WHEN 'josephsmithpapers' THEN 'joseph_smith_papers'
        ELSE NULL
      END
    ),
    updated_at = now()
WHERE key IN ('byu_speeches_en', 'discursosud', 'josephsmithpapers', 'churchofjesuschrist');
