import importlib.util
import os
import re
import sys
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "init_supabase_schema.py"
SPEC = importlib.util.spec_from_file_location("init_supabase_schema", SCRIPT_PATH)
assert SPEC and SPEC.loader
schema_init = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = schema_init
SPEC.loader.exec_module(schema_init)


class FakeResult:
    def __init__(self, rows=None):
        self._rows = rows or []

    def fetchall(self):
        return self._rows


class FakeConnection:
    def __init__(self):
        self.tables = set()
        self.columns = {}
        self.executed = []

    def execute(self, statement, params=None):
        text = str(statement)
        self.executed.append((text, params))
        normalized = " ".join(text.split()).lower()
        if "from information_schema.tables" in normalized:
            return FakeResult([(name,) for name in sorted(self.tables)])
        if normalized.startswith("select table_name, column_name, udt_name"):
            rows = []
            for spec in schema_init.TABLE_SPECS:
                for column in sorted(self.columns.get(spec.name, set())):
                    rows.append((spec.name, column, expected_udt(spec.name, column)))
            return FakeResult(rows)
        if normalized.startswith("select table_name, column_name"):
            return FakeResult(
                [
                    (table_name, column)
                    for table_name, columns in sorted(self.columns.items())
                    for column in sorted(columns)
                ]
            )
        if normalized.startswith("select column_name") and "from information_schema.columns" in normalized:
            table_name = params[0]
            return FakeResult([(column,) for column in sorted(self.columns.get(table_name, set()))])
        if normalized.startswith("create table if not exists"):
            table_name = normalized.split()[5]
            if table_name not in self.tables:
                self.tables.add(table_name)
                spec = next(spec for spec in schema_init.TABLE_SPECS if spec.name == table_name)
                self.columns[table_name] = set(spec.required_columns)
        if normalized.startswith("alter table if exists"):
            table_name = normalized.split()[4]
            if table_name in self.tables:
                self.columns.setdefault(table_name, set()).update(
                    re.findall(r"add column if not exists ([a-z_]+)", normalized)
                )
        return FakeResult()


def expected_udt(table_name, column_name):
    expected = schema_init.REQUIRED_COLUMN_TYPES.get((table_name, column_name))
    return sorted(expected)[0] if expected else "text"


class SchemaInitTests(TestCase):
    def test_schema_ddl_is_idempotent_and_non_destructive(self):
        statements = "\n".join(
            (
                *schema_init.SCHEMA_STATEMENTS,
                *schema_init.ALTER_TABLE_STATEMENTS,
                *schema_init.TYPE_ALIGNMENT_STATEMENTS,
                *schema_init.INDEX_STATEMENTS,
            )
        ).upper()
        self.assertNotIn("DROP TABLE", statements)
        self.assertNotIn("TRUNCATE", statements)
        self.assertNotIn("DELETE FROM", statements)
        self.assertEqual(statements.count("CREATE TABLE IF NOT EXISTS"), len(schema_init.EXPECTED_TABLES))
        self.assertTrue(all("ADD COLUMN IF NOT EXISTS" in item.upper() for item in schema_init.ALTER_TABLE_STATEMENTS))
        self.assertTrue(all("CREATE INDEX IF NOT EXISTS" in item.upper() for item in schema_init.INDEX_STATEMENTS))
        self.assertTrue(set(schema_init.PRIMARY_ENDPOINT_TABLES).issubset(schema_init.EXPECTED_TABLES))

    def test_initialize_schema_can_run_twice(self):
        conn = FakeConnection()
        created, verified, added_columns = schema_init.initialize_schema(conn)
        self.assertEqual(set(created), set(schema_init.EXPECTED_TABLES))
        self.assertEqual(verified, [])
        self.assertEqual(added_columns, {})

        created_again, verified_again, added_again = schema_init.initialize_schema(conn)
        self.assertEqual(created_again, [])
        self.assertEqual(set(verified_again), set(schema_init.EXPECTED_TABLES))
        self.assertEqual(added_again, {})

    def test_initialize_schema_repairs_existing_legacy_document_tables(self):
        conn = FakeConnection()
        conn.tables = {"documents", "ingestion_jobs"}
        conn.columns = {
            "documents": {"id", "source_id", "title", "canonical_url"},
            "ingestion_jobs": {"id", "job_type", "status"},
        }

        _, verified, added_columns = schema_init.initialize_schema(conn)

        self.assertIn("documents", verified)
        self.assertIn("raw_metadata", added_columns["documents"])
        self.assertIn("is_indexed", added_columns["documents"])
        self.assertIn("errors", added_columns["ingestion_jobs"])
        self.assertIn("documents_failed", added_columns["ingestion_jobs"])

    def test_main_fails_without_database_url_before_connecting(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(schema_init.psycopg, "connect") as connect:
            self.assertEqual(schema_init.main(), 2)
            connect.assert_not_called()
