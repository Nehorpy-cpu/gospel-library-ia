import re
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[3]
MIGRATION_PATH = ROOT / "apps" / "api" / "migrations" / "20260623_enable_rls_policies.sql"
CHECK_SCRIPT_PATH = ROOT / "scripts" / "check_supabase_rls.sql"


PUBLIC_READ_TABLES = {
    "sources",
    "documents",
    "document_chunks",
    "authors",
    "tags",
}

PRIVATE_USER_TABLES = {
    "study_workspaces",
    "study_workspace_sources",
    "study_notes",
    "study_highlights",
    "saved_citations",
    "post_its",
    "chat_sessions",
    "study_projects",
    "user_private_sources",
    "study_ai_suggestion_cache",
    "user_preferences",
    "beta_feedback",
    "beta_activity_events",
}

PRIVATE_CHILD_TABLES = {
    "chat_messages",
    "study_blocks",
    "study_sources",
}

INTERNAL_TABLES = {
    "crawl_urls",
    "document_assets",
    "ingestion_jobs",
    "document_duplicate_relations",
    "beta_access",
}


def migration_sql() -> str:
    return MIGRATION_PATH.read_text(encoding="utf-8")


def executable_sql(sql: str) -> str:
    return "\n".join(line for line in sql.splitlines() if not line.lstrip().startswith("--"))


class SupabaseRlsMigrationTests(TestCase):
    def test_migration_is_non_destructive(self):
        sql = executable_sql(migration_sql()).upper()

        self.assertNotIn("DROP TABLE", sql)
        self.assertNotIn("TRUNCATE", sql)
        self.assertNotIn("DELETE FROM", sql)
        self.assertNotIn("FORCE ROW LEVEL SECURITY", sql)

    def test_expected_tables_have_rls_enabled(self):
        sql = migration_sql().lower()
        expected_tables = PUBLIC_READ_TABLES | PRIVATE_USER_TABLES | PRIVATE_CHILD_TABLES | INTERNAL_TABLES

        for table in sorted(expected_tables):
            self.assertIn(f"alter table if exists public.{table} enable row level security", sql)

    def test_public_read_policies_are_read_only_and_scoped(self):
        sql = migration_sql().lower()

        for table in sorted(PUBLIC_READ_TABLES):
            self.assertRegex(sql, rf"create policy [a-z0-9_]+[\s\S]*?on public\.{table}[\s\S]*?for select")

        self.assertIn("using (status = 'ready' and deleted_at is null)", sql)
        self.assertIn("where d.id = document_chunks.document_id", sql)
        self.assertIn("and d.status = 'ready'", sql)
        self.assertIn("and d.deleted_at is null", sql)
        self.assertIn("revoke insert, update, delete on public.sources", sql)

    def test_private_policies_use_authenticated_uid_checks(self):
        sql = migration_sql().lower()

        for table in sorted(PRIVATE_USER_TABLES):
            self.assertRegex(sql, rf"create policy {table}_owner_access[\s\S]*?on public\.{table}[\s\S]*?to authenticated")

        self.assertGreaterEqual(sql.count("(select auth.uid()) is not null"), 1)
        self.assertGreaterEqual(sql.count("user_id = (select auth.uid())"), len(PRIVATE_USER_TABLES))

    def test_child_policies_authorize_through_parent_ownership(self):
        sql = migration_sql().lower()

        self.assertIn("from public.chat_sessions s", sql)
        self.assertIn("where s.id = chat_messages.session_id", sql)
        self.assertIn("from public.study_projects p", sql)
        self.assertIn("where p.id = study_blocks.project_id", sql)
        self.assertIn("where p.id = study_sources.project_id", sql)

    def test_internal_tables_have_no_anon_or_authenticated_policy(self):
        sql = migration_sql().lower()

        for table in sorted(INTERNAL_TABLES):
            self.assertIn(f"public.{table}", sql)
            self.assertNotRegex(sql, rf"create policy [\s\S]*?on public\.{table}[\s\S]*?to (anon|authenticated)")

        self.assertIn("revoke all on", sql)
        self.assertIn("from anon, authenticated", sql)

    def test_verification_script_checks_catalog_metadata(self):
        sql = CHECK_SCRIPT_PATH.read_text(encoding="utf-8").lower()

        self.assertIn("pg_policies", sql)
        self.assertIn("relrowsecurity", sql)
        self.assertIn("relforcerowsecurity", sql)
        self.assertIn("information_schema.role_table_grants", sql)
        self.assertNotRegex(sql, re.compile(r"\b(update|insert|delete|truncate|drop)\b"))
