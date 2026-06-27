-- List dangerous grants for Supabase browser-facing roles.
-- Run in Supabase SQL Editor. This script is read-only and tolerates missing
-- optional tables. If everything is hardened, this query returns zero rows.

with expected_tables(table_name) as (
  values
    ('sources'),
    ('documents'),
    ('document_chunks'),
    ('authors'),
    ('tags'),
    ('study_workspaces'),
    ('study_workspace_sources'),
    ('study_notes'),
    ('study_highlights'),
    ('saved_citations'),
    ('post_its'),
    ('chat_sessions'),
    ('chat_messages'),
    ('study_projects'),
    ('study_blocks'),
    ('study_sources'),
    ('user_private_sources'),
    ('study_ai_suggestion_cache'),
    ('user_preferences'),
    ('beta_feedback'),
    ('beta_activity_events'),
    ('crawl_urls'),
    ('document_assets'),
    ('ingestion_jobs'),
    ('document_duplicate_relations'),
    ('beta_access')
),
existing_tables as (
  select e.table_name
  from expected_tables e
  join information_schema.tables t
    on t.table_schema = 'public'
   and t.table_name = e.table_name
)
select
  g.grantee,
  g.table_name,
  g.privilege_type
from information_schema.role_table_grants g
join existing_tables e
  on e.table_name = g.table_name
where g.table_schema = 'public'
  and g.grantee in ('anon', 'authenticated')
  and g.privilege_type in ('INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'REFERENCES', 'TRIGGER')
order by g.grantee, g.table_name, g.privilege_type;
