import importlib.util
import os
import sys
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "seed_initial_documents.py"
SPEC = importlib.util.spec_from_file_location("seed_initial_documents", SCRIPT_PATH)
assert SPEC and SPEC.loader
seed = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = seed
SPEC.loader.exec_module(seed)


class FakeResult:
    def __init__(self, row=None):
        self.row = row

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self):
        self.sources = {}
        self.documents = {}
        self.authors = set()
        self.tags = set()
        self.chunks = set()
        self.next_id = 1
        self.executed = []

    def new_id(self):
        value = f"00000000-0000-4000-8000-{self.next_id:012d}"
        self.next_id += 1
        return value

    def execute(self, statement, params=None):
        normalized = " ".join(str(statement).split()).lower()
        self.executed.append((normalized, params))
        if normalized.startswith("select pg_advisory_xact_lock"):
            return FakeResult((None,))
        if normalized.startswith("select id from sources"):
            return FakeResult((self.sources[params[0]],) if params[0] in self.sources else None)
        if normalized.startswith("insert into sources"):
            source_id = self.new_id()
            self.sources[params["key"]] = source_id
            return FakeResult((source_id,))
        if normalized.startswith("insert into authors"):
            slug = params[0]
            if slug in self.authors:
                return FakeResult()
            self.authors.add(slug)
            return FakeResult((self.new_id(),))
        if normalized.startswith("insert into tags"):
            slug = params[0]
            if slug in self.tags:
                return FakeResult()
            self.tags.add(slug)
            return FakeResult((self.new_id(),))
        if normalized.startswith("select id from documents"):
            url = params[0]
            return FakeResult((self.documents[url],) if url in self.documents else None)
        if normalized.startswith("insert into documents"):
            url = params["canonical_url"]
            if url in self.documents:
                return FakeResult()
            document_id = self.new_id()
            self.documents[url] = document_id
            return FakeResult((document_id,))
        if normalized.startswith("insert into document_chunks"):
            key = (params["document_id"], params["chunker_version"])
            if key in self.chunks:
                return FakeResult()
            self.chunks.add(key)
            return FakeResult((self.new_id(),))
        raise AssertionError(f"Unexpected SQL: {normalized}")


class InitialContentSeedTests(TestCase):
    def test_seed_is_idempotent_and_non_destructive(self):
        conn = FakeConnection()

        first = seed.seed_initial_documents(conn)
        second = seed.seed_initial_documents(conn)

        self.assertEqual(first.sources_created, len(seed.SOURCES))
        self.assertEqual(first.documents_created, len(seed.DOCUMENTS))
        self.assertEqual(first.chunks_created, len(seed.DOCUMENTS))
        self.assertEqual(second.sources_verified, len(seed.SOURCES))
        self.assertEqual(second.documents_verified, len(seed.DOCUMENTS))
        self.assertEqual(second.chunks_verified, len(seed.DOCUMENTS))
        statements = "\n".join(statement for statement, _ in conn.executed)
        self.assertIn("raw_metadata->>'source_url'", statements)
        self.assertFalse(
            any(
                destructive in statement.upper()
                for statement, _ in conn.executed
                for destructive in ("DELETE FROM", "TRUNCATE", "DROP TABLE")
            )
        )

    def test_seed_content_is_marked_and_uses_https_sources(self):
        categories = [document.category for document in seed.DOCUMENTS]
        self.assertGreaterEqual(categories.count("Gospel Topics"), 2)
        self.assertGreaterEqual(categories.count("General Conference"), 2)
        self.assertGreaterEqual(categories.count("BYU Speeches"), 1)
        for document in seed.DOCUMENTS:
            self.assertTrue(document.source_url.startswith("https://"))
            self.assertIn("[SEED/TEST CONTENT]", document.summary)
            self.assertLess(len(document.summary), 600)

    def test_main_requires_database_url(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(seed.psycopg, "connect") as connect:
            self.assertEqual(seed.main(), 2)
            connect.assert_not_called()
