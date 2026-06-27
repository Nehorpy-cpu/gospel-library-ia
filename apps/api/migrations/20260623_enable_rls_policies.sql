-- Supabase RLS hardening plan for Gospel Library IA.
--
-- Safe to run multiple times:
-- - Enables RLS on existing public tables only.
-- - Recreates policies only when the target table exists.
-- - Skips optional/future tables that are not present in the database.
-- - Revokes broad Supabase Data API grants from anon/authenticated roles.
-- - Does not delete, truncate, or update application data.
-- - Does not create missing tables.
-- - Does not enable FORCE ROW LEVEL SECURITY, so backend/service-role access
--   used by FastAPI remains compatible.
--
-- Supabase SQL Editor usage:
-- - Open this .sql file and copy its complete contents.
-- - Do not paste the file path.
-- - Do not paste markdown fences or prose that is not commented with --.

begin;

grant usage on schema public to anon, authenticated;

-- Close broad table access inherited by Supabase anon/authenticated roles.
-- These schema-wide statements only affect relations that already exist.
revoke all privileges on all tables in schema public from anon, authenticated;
revoke insert, update, delete, truncate, references, trigger on all tables in schema public from anon, authenticated;
revoke all privileges on all sequences in schema public from anon, authenticated;

alter default privileges in schema public revoke all privileges on tables from anon, authenticated;
alter default privileges in schema public revoke all privileges on sequences from anon, authenticated;

-- Helper functions live only for this session through pg_temp. They make the
-- migration safe when optional tables are not present in the current database.
create or replace function pg_temp.relation_exists(relation_name text)
returns boolean
language plpgsql
as $$
begin
  return to_regclass(format('public.%I', relation_name)) is not null;
end;
$$;

create or replace function pg_temp.all_relations_exist(relation_names text[])
returns boolean
language plpgsql
as $$
declare
  relation_name text;
begin
  foreach relation_name in array relation_names loop
    if not pg_temp.relation_exists(relation_name) then
      return false;
    end if;
  end loop;

  return true;
end;
$$;

create or replace function pg_temp.enable_rls_if_exists(relation_name text)
returns void
language plpgsql
as $$
begin
  if pg_temp.relation_exists(relation_name) then
    execute format('alter table public.%I enable row level security', relation_name);
  end if;
end;
$$;

create or replace function pg_temp.revoke_all_if_exists(relation_names text[])
returns void
language plpgsql
as $$
declare
  relation_name text;
begin
  foreach relation_name in array relation_names loop
    if pg_temp.relation_exists(relation_name) then
      execute format('revoke all on table public.%I from anon, authenticated', relation_name);
    end if;
  end loop;
end;
$$;

create or replace function pg_temp.grant_public_select_if_exists(relation_name text)
returns void
language plpgsql
as $$
begin
  if pg_temp.relation_exists(relation_name) then
    execute format('grant select on table public.%I to anon, authenticated', relation_name);
  end if;
end;
$$;

create or replace function pg_temp.replace_policy_if_exists(
  relation_name text,
  policy_name text,
  policy_sql text,
  required_relations text[] default array[]::text[]
)
returns void
language plpgsql
as $$
begin
  if pg_temp.relation_exists(relation_name)
     and pg_temp.all_relations_exist(required_relations) then
    execute format('drop policy if exists %I on public.%I', policy_name, relation_name);
    execute format('create policy %I on public.%I %s', policy_name, relation_name, policy_sql);
  end if;
end;
$$;

-- Public controlled read tables. These are optional-safe: if any table is not
-- present yet, its RLS/grants/policy statements are skipped.
select pg_temp.enable_rls_if_exists(table_name)
from unnest(array[
  'sources',
  'documents',
  'document_chunks',
  'authors',
  'tags'
]) as t(table_name);

select pg_temp.grant_public_select_if_exists(table_name)
from unnest(array[
  'sources',
  'documents',
  'document_chunks',
  'authors',
  'tags'
]) as t(table_name);

select pg_temp.replace_policy_if_exists(
  'sources',
  'sources_public_read_enabled',
  $policy$
    for select
    to anon, authenticated
    using (enabled = true)
  $policy$
);

select pg_temp.replace_policy_if_exists(
  'documents',
  'documents_public_read_ready',
  $policy$
    for select
    to anon, authenticated
    using (status = 'READY' and deleted_at is null)
  $policy$
);

select pg_temp.replace_policy_if_exists(
  'document_chunks',
  'document_chunks_public_read_ready_documents',
  $policy$
    for select
    to anon, authenticated
    using (
      exists (
        select 1
        from public.documents d
        where d.id = document_chunks.document_id
          and d.status = 'READY'
          and d.deleted_at is null
      )
    )
  $policy$,
  array['documents']
);

select pg_temp.replace_policy_if_exists(
  'authors',
  'authors_public_read',
  $policy$
    for select
    to anon, authenticated
    using (true)
  $policy$
);

select pg_temp.replace_policy_if_exists(
  'tags',
  'tags_public_read',
  $policy$
    for select
    to anon, authenticated
    using (true)
  $policy$
);

-- Private user-owned tables with a direct user_id column. RLS policies are
-- defined for future direct Supabase authenticated access, but grants remain
-- closed so FastAPI stays the active access layer.
select pg_temp.enable_rls_if_exists(table_name)
from unnest(array[
  'study_workspaces',
  'study_workspace_sources',
  'study_notes',
  'study_highlights',
  'saved_citations',
  'post_its',
  'chat_sessions',
  'study_projects',
  'user_private_sources',
  'study_ai_suggestion_cache',
  'user_preferences',
  'beta_feedback',
  'beta_activity_events'
]) as t(table_name);

select pg_temp.revoke_all_if_exists(array[
  'study_workspaces',
  'study_workspace_sources',
  'study_notes',
  'study_highlights',
  'saved_citations',
  'post_its',
  'chat_sessions',
  'study_projects',
  'user_private_sources',
  'study_ai_suggestion_cache',
  'user_preferences',
  'beta_feedback',
  'beta_activity_events'
]);

select pg_temp.replace_policy_if_exists(table_name, table_name || '_owner_access', $policy$
    for all
    to authenticated
    using ((select auth.uid()) is not null and user_id = (select auth.uid()))
    with check ((select auth.uid()) is not null and user_id = (select auth.uid()))
  $policy$)
from unnest(array[
  'study_workspaces',
  'study_workspace_sources',
  'study_notes',
  'study_highlights',
  'saved_citations',
  'post_its',
  'chat_sessions',
  'study_projects',
  'user_private_sources',
  'study_ai_suggestion_cache',
  'user_preferences',
  'beta_feedback',
  'beta_activity_events'
]) as t(table_name);

-- Private child tables authorized through their parent owner row.
select pg_temp.enable_rls_if_exists(table_name)
from unnest(array[
  'chat_messages',
  'study_blocks',
  'study_sources'
]) as t(table_name);

select pg_temp.revoke_all_if_exists(array[
  'chat_messages',
  'study_blocks',
  'study_sources'
]);

select pg_temp.replace_policy_if_exists(
  'chat_messages',
  'chat_messages_owner_access',
  $policy$
    for all
    to authenticated
    using (
      (select auth.uid()) is not null
      and exists (
        select 1
        from public.chat_sessions s
        where s.id = chat_messages.session_id
          and s.user_id = (select auth.uid())
      )
    )
    with check (
      (select auth.uid()) is not null
      and exists (
        select 1
        from public.chat_sessions s
        where s.id = chat_messages.session_id
          and s.user_id = (select auth.uid())
      )
    )
  $policy$,
  array['chat_sessions']
);

select pg_temp.replace_policy_if_exists(
  'study_blocks',
  'study_blocks_owner_access',
  $policy$
    for all
    to authenticated
    using (
      (select auth.uid()) is not null
      and exists (
        select 1
        from public.study_projects p
        where p.id = study_blocks.project_id
          and p.user_id = (select auth.uid())
      )
    )
    with check (
      (select auth.uid()) is not null
      and exists (
        select 1
        from public.study_projects p
        where p.id = study_blocks.project_id
          and p.user_id = (select auth.uid())
      )
    )
  $policy$,
  array['study_projects']
);

select pg_temp.replace_policy_if_exists(
  'study_sources',
  'study_sources_owner_access',
  $policy$
    for all
    to authenticated
    using (
      (select auth.uid()) is not null
      and exists (
        select 1
        from public.study_projects p
        where p.id = study_sources.project_id
          and p.user_id = (select auth.uid())
      )
    )
    with check (
      (select auth.uid()) is not null
      and exists (
        select 1
        from public.study_projects p
        where p.id = study_sources.project_id
          and p.user_id = (select auth.uid())
      )
    )
  $policy$,
  array['study_projects']
);

-- Internal/admin/ingestion tables. RLS is enabled, but no anon/authenticated
-- policies are granted. FastAPI and trusted jobs should continue through the
-- backend database role/service role, not through browser Supabase clients.
select pg_temp.enable_rls_if_exists(table_name)
from unnest(array[
  'crawl_urls',
  'document_assets',
  'ingestion_jobs',
  'document_duplicate_relations',
  'beta_access'
]) as t(table_name);

select pg_temp.revoke_all_if_exists(array[
  'crawl_urls',
  'document_assets',
  'ingestion_jobs',
  'document_duplicate_relations',
  'beta_access'
]);

commit;
