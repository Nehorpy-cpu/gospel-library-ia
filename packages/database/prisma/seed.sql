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

INSERT INTO sources (
  id, key, name, kind, base_url, source_type, language, default_language,
  is_official, trust_level, scraping_enabled, enabled, crawl_strategy,
  rate_limit, max_pages_per_run, robots_policy_notes, config, created_at, updated_at
)
VALUES
  (gen_random_uuid(), 'byu_speeches_es', 'BYU Speeches Espanol', 'BYU_SPEECHES_ES', 'https://speeches.byu.edu/spa/talks/', 'byu_speeches_es', 'es', 'es', false, 7, true, true, 'listing_and_talk_pages', 30, 12, 'Respetar robots.txt; crawl limitado a discursos publicos en espanol.', '{"indexing":{"mode":"index_later","estimate_cost_before_embedding":true}}'::jsonb, now(), now()),
  (gen_random_uuid(), 'byu_speeches', 'BYU Speeches English', 'BYU_SPEECHES', 'https://speeches.byu.edu/talks/', 'byu_speeches_en', 'en', 'en', false, 7, true, true, 'listing_and_talk_pages', 30, 12, 'Respetar robots.txt; crawl limitado a discursos publicos.', '{"indexing":{"mode":"index_later","estimate_cost_before_embedding":true}}'::jsonb, now(), now()),
  (gen_random_uuid(), 'discursos_sud', 'Discursos SUD', 'DISCURSO_SUD', 'https://discursosud.com/', 'discursos_sud', 'es', 'es', false, 6, true, true, 'wordpress_posts', 20, 10, 'Sitio no oficial; usar crawl lento, incremental y con deduplicacion estricta.', '{"indexing":{"mode":"index_later","estimate_cost_before_embedding":true}}'::jsonb, now(), now()),
  (gen_random_uuid(), 'general_conference', 'Conferencia General', 'GENERAL_CONFERENCE', 'https://www.churchofjesuschrist.org/study/general-conference', 'general_conference', 'es', 'es', true, 10, true, true, 'official_library_pages', 20, 10, 'Fuente oficial; respetar robots.txt y no descargar masivamente.', '{"indexing":{"mode":"index_later","estimate_cost_before_embedding":true}}'::jsonb, now(), now()),
  (gen_random_uuid(), 'church_manuals', 'Manuales de la Iglesia', 'CHURCH_MANUAL', 'https://www.churchofjesuschrist.org/study/manual', 'church_manuals', 'es', 'es', true, 10, true, true, 'official_library_pages', 20, 10, 'Fuente oficial; limitar paginas por corrida.', '{"indexing":{"mode":"index_later","estimate_cost_before_embedding":true}}'::jsonb, now(), now()),
  (gen_random_uuid(), 'joseph_smith_papers', 'Joseph Smith Papers', 'JOSEPH_SMITH_PAPERS', 'https://www.josephsmithpapers.org/', 'joseph_smith_papers', 'en', 'en', true, 9, true, true, 'historical_documents', 20, 8, 'Fuente historica/documental; no es manual doctrinal oficial.', '{"indexing":{"mode":"index_later","estimate_cost_before_embedding":true}}'::jsonb, now(), now()),
  (gen_random_uuid(), 'byu_rsc', 'BYU Religious Studies Center', 'BOOK', 'https://rsc.byu.edu/', 'byu_rsc', 'en', 'en', false, 7, true, true, 'book_article_pages', 20, 8, 'Fuente academica BYU; crawl limitado por articulos/libros publicos.', '{"indexing":{"mode":"index_later","estimate_cost_before_embedding":true}}'::jsonb, now(), now()),
  (gen_random_uuid(), 'come_follow_me', 'Come, Follow Me', 'CHURCH_MANUAL', 'https://www.churchofjesuschrist.org/study/manual/come-follow-me', 'church_manuals', 'es', 'es', true, 10, true, true, 'official_library_pages', 20, 8, 'Subcoleccion oficial de manuales; limitada y auditable.', '{"indexing":{"mode":"index_later","estimate_cost_before_embedding":true}}'::jsonb, now(), now()),
  (gen_random_uuid(), 'teachings_presidents', 'Teachings of Presidents of the Church', 'CHURCH_MANUAL', 'https://www.churchofjesuschrist.org/study/manual/teachings-presidents', 'church_manuals', 'en', 'en', true, 10, true, true, 'official_library_pages', 20, 8, 'Subcoleccion oficial de manuales; limitada y auditable.', '{"indexing":{"mode":"index_later","estimate_cost_before_embedding":true}}'::jsonb, now(), now()),
  (gen_random_uuid(), 'scriptures', 'Escrituras', 'SCRIPTURE', 'https://www.churchofjesuschrist.org/study/scriptures', 'scriptures', 'es', 'es', true, 10, true, true, 'official_scripture_pages', 20, 8, 'Fuente oficial; no descargar masivamente capitulos sin aprobacion.', '{"indexing":{"mode":"index_later","estimate_cost_before_embedding":true}}'::jsonb, now(), now())
ON CONFLICT (key) DO UPDATE
SET name = EXCLUDED.name,
    base_url = EXCLUDED.base_url,
    source_type = EXCLUDED.source_type,
    language = EXCLUDED.language,
    default_language = EXCLUDED.default_language,
    enabled = EXCLUDED.enabled,
    crawl_strategy = EXCLUDED.crawl_strategy,
    rate_limit = EXCLUDED.rate_limit,
    max_pages_per_run = EXCLUDED.max_pages_per_run,
    robots_policy_notes = EXCLUDED.robots_policy_notes,
    config = sources.config || EXCLUDED.config,
    updated_at = now();
