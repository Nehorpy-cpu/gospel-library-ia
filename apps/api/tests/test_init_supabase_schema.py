import importlib.util
import os
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
        self.executed = []

    def execute(self, statement, params=None):
        text = str(statement)
        self.executed.append((text, params))
        normalized = " ".join(text.split()).lower()
        if "from information_schema.tables" in normalized:
            return FakeResult([(name,) for name in sorted(self.tables)])
        if "from information_schema.columns" in normalized:
            table_name = params[0]
            spec = next(spec for spec in schema_init.TABLE_SPECS if spec.name == table_name)
            return FakeResult([(column,) for column in spec.required_columns])
        if normalized.startswith("create table if not exists"):
            table_name = normalized.split()[5]
            self.tables.add(table_name)
        return FakeResult()


class SchemaInitTests(TestCase):
    def test_schema_ddl_is_idempotent_and_non_destructive(self):
        statements = "\n".join(
            (*schema_init.SCHEMA_STATEMENTS, *schema_init.INDEX_STATEMENTS)
        ).upper()
        self.assertNotIn("DROP TABLE", statements)
        self.assertNotIn("TRUNCATE", statements)
        self.assertNotIn("DELETE FROM", statements)
        self.assertEqual(statements.count("CREATE TABLE IF NOT EXISTS"), len(schema_init.EXPECTED_TABLES))
        self.assertTrue(all("CREATE INDEX IF NOT EXISTS" in item.upper() for item in schema_init.INDEX_STATEMENTS))

    def test_initialize_schema_can_run_twice(self):
        conn = FakeConnection()
        created, verified = schema_init.initialize_schema(conn)
        self.assertEqual(set(created), set(schema_init.EXPECTED_TABLES))
        self.assertEqual(verified, [])

        created_again, verified_again = schema_init.initialize_schema(conn)
        self.assertEqual(created_again, [])
        self.assertEqual(set(verified_again), set(schema_init.EXPECTED_TABLES))

    def test_main_fails_without_database_url_before_connecting(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(schema_init.psycopg, "connect") as connect:
            self.assertEqual(schema_init.main(), 2)
            connect.assert_not_called()
