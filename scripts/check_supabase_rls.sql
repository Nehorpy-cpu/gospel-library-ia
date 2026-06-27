-- Supabase RLS verification queries for Gospel Library IA.
-- Run this in Supabase SQL Editor after applying the RLS migration.
-- This script only reads catalog metadata. It does not expose secrets and does
-- not modify application data. It tolerates optional tables that do not exist.

with expected_tables(table_name, classification) as (
  values
    ('sources', 'public_controlled_read'),
    ('documents', 'public_controlled_read'),
    ('document_chunks', 'public_controlled_read'),
    ('authors', 'public_controlled_read'),
    ('tags', 'public_controlled_read'),
    ('study_workspaces', 'private_user_owned'),
    ('study_workspace_sources', 'private_user_owned'),
    ('study_notes', 'private_user_owned'),
    ('study_highlights', 'private_user_owned'),
    ('saved_citations', 'private_user_owned'),
    ('post_its', 'private_user_owned'),
    ('chat_sessions', 'private_user_owned'),
    ('chat_messages', 'private_parent_owned'),
    ('study_projects', 'private_user_owned_optional'),
    ('study_blocks', 'private_parent_owned_optional'),
    ('study_sources', 'private_parent_owned_optional'),
    ('user_private_sources', 'private_user_owned_optional'),
    ('study_ai_suggestion_cache', 'private_user_owned_optional'),
    ('user_preferences', 'private_user_owned'),
    ('beta_feedback', 'private_user_owned'),
    ('beta_activity_events', 'private_user_owned'),
    ('crawl_urls', 'internal_backend_only'),
    ('document_assets', 'internal_backend_only'),
    ('ingestion_jobs', 'internal_backend_only'),
    ('document_duplicate_relations', 'internal_backend_only'),
    ('beta_access', 'internal_backend_only')
),
existing_tables as (
  select
    e.table_name,
    e.classification,
    c.oid,
    c.relrowsecurity,
    c.relforcerowsecurity
  from expected_tables e
  left join pg_namespace n
    on n.nspname = 'public'
  left join pg_class c
    on c.relnamespace = n.oid
   and c.relname = e.table_name
   and c.relkind in ('r', 'p')
),
policy_counts as (
  select
    p.tablename as table_name,
    count(*) as policy_count
  from pg_policies p
  join existing_tables e
    on e.oid is not null
   and e.table_name = p.tablename
  where p.schemaname = 'public'
  group by p.tablename
)
select
  e.classification,
  e.table_name,
  e.oid is not null as table_exists,
  coalesce(e.relrowsecurity, false) as rls_enabled,
  coalesce(e.relforcerowsecurity, false) as force_rls_enabled,
  coalesce(p.policy_count, 0) as policy_count
from existing_tables e
left join policy_counts p
  on p.table_name = e.table_name
order by e.classification, e.table_name;

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
  join pg_namespace n
    on n.nspname = 'public'
  join pg_class c
    on c.relnamespace = n.oid
   and c.relname = e.table_name
   and c.relkind in ('r', 'p')
)
select
  p.schemaname,
  p.tablename,
  p.policyname,
  p.cmd,
  p.roles,
  p.qual,
  p.with_check
from pg_policies p
join existing_tables e
  on e.table_name = p.tablename
where p.schemaname = 'public'
order by p.tablename, p.policyname;

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
order by g.table_name, g.grantee, g.privilege_type;

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
