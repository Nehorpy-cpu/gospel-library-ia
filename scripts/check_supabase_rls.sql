-- Supabase RLS verification queries for Gospel Library IA.
-- Run this in the Supabase SQL editor after applying:
-- apps/api/migrations/20260623_enable_rls_policies.sql
--
-- This script only reads catalog metadata. It does not expose secrets and does
-- not modify application data.

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
    ('study_projects', 'private_user_owned'),
    ('study_blocks', 'private_parent_owned'),
    ('study_sources', 'private_parent_owned'),
    ('user_private_sources', 'private_user_owned'),
    ('study_ai_suggestion_cache', 'private_user_owned'),
    ('user_preferences', 'private_user_owned'),
    ('beta_feedback', 'private_user_owned'),
    ('beta_activity_events', 'private_user_owned'),
    ('crawl_urls', 'internal_backend_only'),
    ('document_assets', 'internal_backend_only'),
    ('ingestion_jobs', 'internal_backend_only'),
    ('document_duplicate_relations', 'internal_backend_only'),
    ('beta_access', 'internal_backend_only')
)
select
  e.classification,
  e.table_name,
  c.oid is not null as table_exists,
  coalesce(c.relrowsecurity, false) as rls_enabled,
  coalesce(c.relforcerowsecurity, false) as force_rls_enabled,
  count(p.policyname) as policy_count
from expected_tables e
left join pg_class c
  on c.relname = e.table_name
left join pg_namespace n
  on n.oid = c.relnamespace
  and n.nspname = 'public'
left join pg_policies p
  on p.schemaname = 'public'
  and p.tablename = e.table_name
group by e.classification, e.table_name, c.oid, c.relrowsecurity, c.relforcerowsecurity
order by e.classification, e.table_name;

select
  schemaname,
  tablename,
  policyname,
  cmd,
  roles,
  qual,
  with_check
from pg_policies
where schemaname = 'public'
  and tablename in (
    'sources',
    'documents',
    'document_chunks',
    'authors',
    'tags',
    'study_workspaces',
    'study_workspace_sources',
    'study_notes',
    'study_highlights',
    'saved_citations',
    'post_its',
    'chat_sessions',
    'chat_messages',
    'study_projects',
    'study_blocks',
    'study_sources',
    'user_private_sources',
    'study_ai_suggestion_cache',
    'user_preferences',
    'beta_feedback',
    'beta_activity_events'
  )
order by tablename, policyname;

select
  grantee,
  table_name,
  privilege_type
from information_schema.role_table_grants
where table_schema = 'public'
  and grantee in ('anon', 'authenticated')
  and table_name in (
    'sources',
    'documents',
    'document_chunks',
    'authors',
    'tags',
    'crawl_urls',
    'document_assets',
    'ingestion_jobs',
    'document_duplicate_relations',
    'beta_access'
  )
order by table_name, grantee, privilege_type;

with project_tables(table_name) as (
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
)
select
  grantee,
  table_name,
  privilege_type
from information_schema.role_table_grants
where table_schema = 'public'
  and grantee in ('anon', 'authenticated')
  and privilege_type in ('INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'REFERENCES', 'TRIGGER')
  and table_name in (select table_name from project_tables)
order by grantee, table_name, privilege_type;
