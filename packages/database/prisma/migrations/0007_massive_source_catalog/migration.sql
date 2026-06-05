ALTER TABLE sources
  ADD COLUMN IF NOT EXISTS source_type varchar(100),
  ADD COLUMN IF NOT EXISTS language varchar(16),
  ADD COLUMN IF NOT EXISTS enabled boolean NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS crawl_strategy varchar(80) NOT NULL DEFAULT 'html_discovery',
  ADD COLUMN IF NOT EXISTS rate_limit integer NOT NULL DEFAULT 30,
  ADD COLUMN IF NOT EXISTS max_pages_per_run integer NOT NULL DEFAULT 25,
  ADD COLUMN IF NOT EXISTS last_crawled_at timestamptz,
  ADD COLUMN IF NOT EXISTS robots_policy_notes text;

UPDATE sources
SET source_type = COALESCE(source_type, config->>'sourceType', config->>'source_type', key),
    language = COALESCE(language, default_language, config->>'language'),
    crawl_strategy = COALESCE(config->>'crawlStrategy', config->>'crawl_strategy', crawl_strategy),
    rate_limit = COALESCE(NULLIF(config->>'rateLimit', '')::int, NULLIF(config->>'rate_limit', '')::int, rate_limit),
    max_pages_per_run = COALESCE(NULLIF(config->>'maxPagesPerRun', '')::int, NULLIF(config->>'max_pages_per_run', '')::int, max_pages_per_run),
    robots_policy_notes = COALESCE(robots_policy_notes, config->>'robotsPolicyNotes', config->>'robots_policy_notes');

UPDATE sources
SET name = 'BYU Speeches English',
    source_type = 'byu_speeches_en',
    language = COALESCE(language, 'en'),
    crawl_strategy = 'listing_and_talk_pages',
    rate_limit = 30,
    max_pages_per_run = LEAST(COALESCE(max_pages_per_run, 12), 25),
    robots_policy_notes = COALESCE(robots_policy_notes, 'Respetar robots.txt; crawl limitado a discursos publicos.')
WHERE key = 'byu_speeches';

CREATE INDEX IF NOT EXISTS idx_sources_enabled_type ON sources(enabled, source_type);
CREATE INDEX IF NOT EXISTS idx_sources_last_crawled ON sources(last_crawled_at);

ALTER TABLE ingestion_jobs
  ADD COLUMN IF NOT EXISTS documents_skipped integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS documents_failed integer NOT NULL DEFAULT 0;
