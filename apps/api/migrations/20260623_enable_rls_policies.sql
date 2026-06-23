-- Supabase RLS hardening plan for Gospel Library IA.
--
-- Safe to run multiple times:
-- - Enables RLS on public tables.
-- - Recreates policies with DROP POLICY IF EXISTS + CREATE POLICY.
-- - Does not delete, truncate, or update application data.
-- - Does not enable FORCE ROW LEVEL SECURITY, so backend/service-role access
--   used by FastAPI remains compatible.
--
-- Rollback approach:
-- - Remove policies with DROP POLICY IF EXISTS.
-- - Disable RLS only after confirming the affected table is not exposed through
--   Supabase anon/authenticated clients.

begin;

grant usage on schema public to anon, authenticated;

-- Public controlled read tables.
alter table if exists public.sources enable row level security;
alter table if exists public.documents enable row level security;
alter table if exists public.document_chunks enable row level security;
alter table if exists public.authors enable row level security;
alter table if exists public.tags enable row level security;

grant select on public.sources, public.documents, public.document_chunks, public.authors, public.tags
  to anon, authenticated;

revoke insert, update, delete on public.sources, public.documents, public.document_chunks, public.authors, public.tags
  from anon, authenticated;

drop policy if exists sources_public_read_enabled on public.sources;
create policy sources_public_read_enabled
  on public.sources
  for select
  to anon, authenticated
  using (enabled = true);

drop policy if exists documents_public_read_ready on public.documents;
create policy documents_public_read_ready
  on public.documents
  for select
  to anon, authenticated
  using (status = 'READY' and deleted_at is null);

drop policy if exists document_chunks_public_read_ready_documents on public.document_chunks;
create policy document_chunks_public_read_ready_documents
  on public.document_chunks
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
  );

drop policy if exists authors_public_read on public.authors;
create policy authors_public_read
  on public.authors
  for select
  to anon, authenticated
  using (true);

drop policy if exists tags_public_read on public.tags;
create policy tags_public_read
  on public.tags
  for select
  to anon, authenticated
  using (true);

-- Private user-owned tables with a direct user_id column.
alter table if exists public.study_workspaces enable row level security;
alter table if exists public.study_workspace_sources enable row level security;
alter table if exists public.study_notes enable row level security;
alter table if exists public.study_highlights enable row level security;
alter table if exists public.saved_citations enable row level security;
alter table if exists public.post_its enable row level security;
alter table if exists public.chat_sessions enable row level security;
alter table if exists public.study_projects enable row level security;
alter table if exists public.user_private_sources enable row level security;
alter table if exists public.study_ai_suggestion_cache enable row level security;
alter table if exists public.user_preferences enable row level security;
alter table if exists public.beta_feedback enable row level security;
alter table if exists public.beta_activity_events enable row level security;

grant select, insert, update, delete on
  public.study_workspaces,
  public.study_workspace_sources,
  public.study_notes,
  public.study_highlights,
  public.saved_citations,
  public.post_its,
  public.chat_sessions,
  public.study_projects,
  public.user_private_sources,
  public.study_ai_suggestion_cache,
  public.user_preferences,
  public.beta_feedback,
  public.beta_activity_events
  to authenticated;

revoke all on
  public.study_workspaces,
  public.study_workspace_sources,
  public.study_notes,
  public.study_highlights,
  public.saved_citations,
  public.post_its,
  public.chat_sessions,
  public.study_projects,
  public.user_private_sources,
  public.study_ai_suggestion_cache,
  public.user_preferences,
  public.beta_feedback,
  public.beta_activity_events
  from anon;

drop policy if exists study_workspaces_owner_access on public.study_workspaces;
create policy study_workspaces_owner_access
  on public.study_workspaces
  for all
  to authenticated
  using ((select auth.uid()) is not null and user_id = (select auth.uid()))
  with check ((select auth.uid()) is not null and user_id = (select auth.uid()));

drop policy if exists study_workspace_sources_owner_access on public.study_workspace_sources;
create policy study_workspace_sources_owner_access
  on public.study_workspace_sources
  for all
  to authenticated
  using ((select auth.uid()) is not null and user_id = (select auth.uid()))
  with check ((select auth.uid()) is not null and user_id = (select auth.uid()));

drop policy if exists study_notes_owner_access on public.study_notes;
create policy study_notes_owner_access
  on public.study_notes
  for all
  to authenticated
  using ((select auth.uid()) is not null and user_id = (select auth.uid()))
  with check ((select auth.uid()) is not null and user_id = (select auth.uid()));

drop policy if exists study_highlights_owner_access on public.study_highlights;
create policy study_highlights_owner_access
  on public.study_highlights
  for all
  to authenticated
  using ((select auth.uid()) is not null and user_id = (select auth.uid()))
  with check ((select auth.uid()) is not null and user_id = (select auth.uid()));

drop policy if exists saved_citations_owner_access on public.saved_citations;
create policy saved_citations_owner_access
  on public.saved_citations
  for all
  to authenticated
  using ((select auth.uid()) is not null and user_id = (select auth.uid()))
  with check ((select auth.uid()) is not null and user_id = (select auth.uid()));

drop policy if exists post_its_owner_access on public.post_its;
create policy post_its_owner_access
  on public.post_its
  for all
  to authenticated
  using ((select auth.uid()) is not null and user_id = (select auth.uid()))
  with check ((select auth.uid()) is not null and user_id = (select auth.uid()));

drop policy if exists chat_sessions_owner_access on public.chat_sessions;
create policy chat_sessions_owner_access
  on public.chat_sessions
  for all
  to authenticated
  using ((select auth.uid()) is not null and user_id = (select auth.uid()))
  with check ((select auth.uid()) is not null and user_id = (select auth.uid()));

drop policy if exists study_projects_owner_access on public.study_projects;
create policy study_projects_owner_access
  on public.study_projects
  for all
  to authenticated
  using ((select auth.uid()) is not null and user_id = (select auth.uid()))
  with check ((select auth.uid()) is not null and user_id = (select auth.uid()));

drop policy if exists user_private_sources_owner_access on public.user_private_sources;
create policy user_private_sources_owner_access
  on public.user_private_sources
  for all
  to authenticated
  using ((select auth.uid()) is not null and user_id = (select auth.uid()))
  with check ((select auth.uid()) is not null and user_id = (select auth.uid()));

drop policy if exists study_ai_suggestion_cache_owner_access on public.study_ai_suggestion_cache;
create policy study_ai_suggestion_cache_owner_access
  on public.study_ai_suggestion_cache
  for all
  to authenticated
  using ((select auth.uid()) is not null and user_id = (select auth.uid()))
  with check ((select auth.uid()) is not null and user_id = (select auth.uid()));

drop policy if exists user_preferences_owner_access on public.user_preferences;
create policy user_preferences_owner_access
  on public.user_preferences
  for all
  to authenticated
  using ((select auth.uid()) is not null and user_id = (select auth.uid()))
  with check ((select auth.uid()) is not null and user_id = (select auth.uid()));

drop policy if exists beta_feedback_owner_access on public.beta_feedback;
create policy beta_feedback_owner_access
  on public.beta_feedback
  for all
  to authenticated
  using ((select auth.uid()) is not null and user_id = (select auth.uid()))
  with check ((select auth.uid()) is not null and user_id = (select auth.uid()));

drop policy if exists beta_activity_events_owner_access on public.beta_activity_events;
create policy beta_activity_events_owner_access
  on public.beta_activity_events
  for all
  to authenticated
  using ((select auth.uid()) is not null and user_id = (select auth.uid()))
  with check ((select auth.uid()) is not null and user_id = (select auth.uid()));

-- Private child tables authorized through their parent owner row.
alter table if exists public.chat_messages enable row level security;
alter table if exists public.study_blocks enable row level security;
alter table if exists public.study_sources enable row level security;

grant select, insert, update, delete on public.chat_messages, public.study_blocks, public.study_sources
  to authenticated;

revoke all on public.chat_messages, public.study_blocks, public.study_sources
  from anon;

drop policy if exists chat_messages_owner_access on public.chat_messages;
create policy chat_messages_owner_access
  on public.chat_messages
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
  );

drop policy if exists study_blocks_owner_access on public.study_blocks;
create policy study_blocks_owner_access
  on public.study_blocks
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
  );

drop policy if exists study_sources_owner_access on public.study_sources;
create policy study_sources_owner_access
  on public.study_sources
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
  );

-- Internal/admin/ingestion tables. RLS is enabled, but no anon/authenticated
-- policies are granted. FastAPI and trusted jobs should continue through the
-- backend database role/service role, not through browser Supabase clients.
alter table if exists public.crawl_urls enable row level security;
alter table if exists public.document_assets enable row level security;
alter table if exists public.ingestion_jobs enable row level security;
alter table if exists public.document_duplicate_relations enable row level security;
alter table if exists public.beta_access enable row level security;

revoke all on
  public.crawl_urls,
  public.document_assets,
  public.ingestion_jobs,
  public.document_duplicate_relations,
  public.beta_access
  from anon, authenticated;

commit;
