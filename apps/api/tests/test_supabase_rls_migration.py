import re
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[3]
MIGRATION_PATH = ROOT / "apps" / "api" / "migrations" / "20260623_enable_rls_policies.sql"
CHECK_SCRIPT_PATH = ROOT / "scripts" / "check_supabase_rls.sql"
PUBLIC_GRANTS_CHECK_PATH = ROOT / "scripts" / "check_public_grants.sql"


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

SQL_STARTERS = (
    "alter ",
    "and ",
    "begin",
    "commit",
    "create ",
    "drop ",
    "exists ",
    "for ",
    "from ",
    "grant ",
    "on ",
    "public.",
    "(select ",
    "('",
    "revoke ",
    "select",
    "to ",
    "using ",
    "values",
    "where ",
    "with ",
)


def migration_sql() -> str:
    return MIGRATION_PATH.read_text(encoding="utf-8")


def executable_sql(sql: str) -> str:
    return "\n".join(line for line in sql.splitlines() if not line.lstrip().startswith("--"))


class SupabaseRlsMigrationTests(TestCase):
    def assert_sql_file_has_no_markdown_or_free_text(self, path: Path):
        text = path.read_text(encoding="utf-8")
        self.assertNotIn("```", text)

        first_non_empty = next(line.strip() for line in text.splitlines() if line.strip())
        self.assertTrue(
            first_non_empty.startswith("--")
            or first_non_empty.startswith("/*")
            or first_non_empty.lower().startswith(SQL_STARTERS),
            f"{path} starts with non-SQL text: {first_non_empty}",
        )

        for line_number, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith(("--", "/*", "*", "*/")):
                continue
            self.assertFalse(
                stripped.startswith(("Supabase RLS hardening plan", "apps/api/", "scripts/")),
                f"{path}:{line_number} contains un-commented prose or a pasted path: {stripped}",
            )

    def test_sql_files_are_pure_sql_or_comments(self):
        self.assert_sql_file_has_no_markdown_or_free_text(MIGRATION_PATH)
        self.assert_sql_file_has_no_markdown_or_free_text(CHECK_SCRIPT_PATH)
        self.assert_sql_file_has_no_markdown_or_free_text(PUBLIC_GRANTS_CHECK_PATH)

    def test_migration_is_non_destructive(self):
        sql = executable_sql(migration_sql()).upper()

        self.assertNotIn("DROP TABLE", sql)
        self.assertNotRegex(sql, r"(^|\n)\s*TRUNCATE\s+")
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
        self.assertIn("grant select on public.sources, public.documents, public.document_chunks, public.authors, public.tags", sql)

    def test_migration_revokes_dangerous_anon_authenticated_grants(self):
        sql = migration_sql().lower()

        self.assertIn("revoke all privileges on all tables in schema public from anon, authenticated", sql)
        self.assertIn(
            "revoke insert, update, delete, truncate, references, trigger on all tables in schema public from anon, authenticated",
            sql,
        )
        self.assertIn("revoke all privileges on all sequences in schema public from anon, authenticated", sql)
        self.assertIn("alter default privileges in schema public revoke all privileges on tables from anon, authenticated", sql)

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

    def test_private_tables_keep_no_direct_authenticated_grants(self):
        sql = migration_sql().lower()
        grant_statements = [
            statement.strip()
            for statement in executable_sql(sql).lower().split(";")
            if statement.strip().startswith("grant ")
        ]

        self.assertNotIn("grant select, insert, update, delete on", sql)
        for table in sorted(PRIVATE_USER_TABLES | PRIVATE_CHILD_TABLES | INTERNAL_TABLES):
            self.assertFalse(
                any(f"public.{table}" in statement and "to authenticated" in statement for statement in grant_statements),
                f"Unexpected authenticated grant for private/internal table: {table}",
            )

    def test_verification_script_checks_catalog_metadata(self):
        sql = CHECK_SCRIPT_PATH.read_text(encoding="utf-8").lower()

        self.assertIn("pg_policies", sql)
        self.assertIn("relrowsecurity", sql)
        self.assertIn("relforcerowsecurity", sql)
        self.assertIn("information_schema.role_table_grants", sql)
        self.assertIn("'insert', 'update', 'delete', 'truncate', 'references', 'trigger'", sql)
        self.assertNotRegex(executable_sql(sql), re.compile(r"(^|\n)\s*(update|insert|delete|truncate|drop)\b"))

    def test_public_grants_check_lists_expected_columns(self):
        sql = PUBLIC_GRANTS_CHECK_PATH.read_text(encoding="utf-8").lower()

        self.assertIn("grantee", sql)
        self.assertIn("table_name", sql)
        self.assertIn("privilege_type", sql)
        self.assertIn("information_schema.role_table_grants", sql)
