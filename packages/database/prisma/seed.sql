INSERT INTO embedding_models (id, provider, name, dimensions, version, is_active, metadata, created_at)
VALUES (
  gen_random_uuid(),
  'openai',
  'text-embedding-3-large',
  3072,
  'v1',
  true,
  '{"collection":"doctrinal_chunks_v1"}'::jsonb,
  now()
)
ON CONFLICT (provider, name, version, dimensions) DO NOTHING;

INSERT INTO sources (id, key, name, kind, base_url, default_language, is_official, trust_level, scraping_enabled, config, created_at, updated_at)
VALUES
  (gen_random_uuid(), 'byu_speeches', 'BYU Speeches', 'BYU_SPEECHES', 'https://speeches.byu.edu/', 'en', false, 7, true, '{}'::jsonb, now(), now()),
  (gen_random_uuid(), 'byu_speeches_es', 'BYU Speeches Spanish', 'BYU_SPEECHES_ES', 'https://speeches.byu.edu/spa/talks/', 'es', false, 7, true, '{}'::jsonb, now(), now()),
  (gen_random_uuid(), 'discursosud', 'Discurso SUD', 'DISCURSO_SUD', 'https://discursosud.com/', 'es', false, 6, true, '{}'::jsonb, now(), now()),
  (gen_random_uuid(), 'churchofjesuschrist', 'The Church of Jesus Christ of Latter-day Saints', 'GENERAL_CONFERENCE', 'https://www.churchofjesuschrist.org/', 'es', true, 10, true, '{}'::jsonb, now(), now()),
  (gen_random_uuid(), 'josephsmithpapers', 'Joseph Smith Papers', 'JOSEPH_SMITH_PAPERS', 'https://www.josephsmithpapers.org/', 'en', true, 9, true, '{}'::jsonb, now(), now())
ON CONFLICT (key) DO NOTHING;
