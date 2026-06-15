from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

from fastapi.testclient import TestClient
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app
from app.routes import public
from app.schemas.api import SearchRequest


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


class FakeConnection:
    def __init__(self):
        self.last_query = ""
        self.last_params = None

    def execute(self, sql, params=None):
        query = str(sql)
        self.last_query = query
        self.last_params = params
        if "information_schema.columns" in query:
            return FakeResult(
                [
                    ("id",),
                    ("source_id",),
                    ("title",),
                    ("canonical_url",),
                    ("author",),
                    ("language",),
                    ("text",),
                    ("raw_metadata",),
                    ("status",),
                    ("is_indexed",),
                    ("created_at",),
                    ("updated_at",),
                ]
            )
        if "GROUP BY 1" in query:
            if "source_type" in query:
                return FakeResult([("byu_speeches", "byu_speeches", "BYU Speeches", 3)])
            return FakeResult([("READY", 2), ("INDEXED", 1)])
        return FakeResult(
            [
                (
                    "doc-1",
                    "La fe en Jesucristo",
                    "Gospel Library IA",
                    "BYU Speeches",
                    "byu_speeches_en",
                    "es",
                    "READY",
                    None,
                    None,
                    "https://example.com/doc-1",
                    "https://example.com/original",
                    "La fe en Jesucristo es un principio de accion.",
                    None,
                    {"source_type": "byu_speeches_en", "source_url": "https://example.com/original"},
                    1,
                )
            ]
        )


@contextmanager
def fake_get_conn():
    yield FakeConnection()


class DocumentRoutesTest(unittest.TestCase):
    def setUp(self):
        self.original_get_conn = public.get_conn
        public.get_conn = fake_get_conn

    def tearDown(self):
        public.get_conn = self.original_get_conn

    def test_documents_summary_returns_status_counts(self):
        response = public.documents_summary()

        self.assertEqual(
            response["documents"],
            [
                {"status": "READY", "count": 2},
                {"status": "PENDING", "count": 0},
                {"status": "FAILED", "count": 0},
                {"status": "INDEXED", "count": 1},
            ],
        )

    def test_documents_returns_navigable_list(self):
        response = public.documents(
            limit=10,
            offset=0,
            status="READY",
            sourceType="byu_speeches_en",
            search="fe",
        )

        self.assertEqual(response["total"], 1)
        self.assertEqual(response["limit"], 10)
        self.assertEqual(response["offset"], 0)
        self.assertEqual(
            response["items"][0],
            {
                "id": "doc-1",
                "title": "La fe en Jesucristo",
                "author": "Gospel Library IA",
                "source": "BYU Speeches",
                "sourceType": "byu_speeches_en",
                "language": "es",
                "status": "READY",
                "createdAt": None,
                "updatedAt": None,
                "url": "https://example.com/doc-1",
                "sourceUrl": "https://example.com/original",
                "excerpt": "La fe en Jesucristo es un principio de accion.",
                "publishedAt": None,
                "metadata": {"source_type": "byu_speeches_en", "source_url": "https://example.com/original"},
            },
        )
        self.assertEqual(response["documents"], response["items"])

    def test_search_request_extracts_scripture_refs(self):
        request = SearchRequest(query="Que ensena Alma 32:21 sobre la fe?")

        self.assertEqual(request.filters.scripture_refs, ["Alma 32:21"])

    def test_search_request_accepts_and_normalizes_empty_query(self):
        request = SearchRequest(query="   ")

        self.assertEqual(request.query, "")

    def test_textual_search_empty_query_returns_empty_contract(self):
        response = public._textual_search_response(SearchRequest(query=""))

        self.assertEqual(response["items"], [])
        self.assertEqual(response["results"], [])
        self.assertEqual(response["total"], 0)
        self.assertEqual(response["mode"], "postgres_text")

    def test_textual_search_exposes_compatible_items_and_results(self):
        original_document_search = public._document_search
        public._document_search = lambda *_args, **_kwargs: [
            {
                "id": "doc-1",
                "chunk_id": "chunk-1",
                "title": "La fe en Jesucristo",
                "author": None,
                "source": "Biblioteca oficial",
                "source_key": "church",
                "source_url": "https://example.com/source",
                "canonical_url": "https://example.com/doc",
                "language": "es",
                "section_title": "Introduccion",
                "snippet": "La fe en Jesucristo.",
                "score": 7.0,
                "tags": ["fe"],
                "scripture_refs": [],
            }
        ]
        try:
            response = public._textual_search_response(SearchRequest(query="Cristo"))
        finally:
            public._document_search = original_document_search

        self.assertEqual(response["total"], 1)
        self.assertEqual(response["items"], response["results"])
        self.assertEqual(response["items"][0]["document_id"], "doc-1")
        self.assertEqual(response["items"][0]["source"], "Biblioteca oficial")
        self.assertEqual(response["items"][0]["tags"], ["fe"])

    def test_search_endpoint_serializes_empty_results_as_arrays(self):
        original_document_search = public._document_search
        public._document_search = lambda *_args, **_kwargs: []
        try:
            response = TestClient(app).post("/api/search", json={"query": "Jesucristo"})
        finally:
            public._document_search = original_document_search

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "query": "Jesucristo",
                "rewritten_query": None,
                "mode": "postgres_text",
                "warnings": [],
                "items": [],
                "results": [],
                "total": 0,
            },
        )
        self.assertIn('"items":[]', response.text)
        self.assertIn('"results":[]', response.text)

    def test_search_endpoint_serializes_results_as_arrays(self):
        row = {
            "id": "doc-1",
            "chunk_id": "chunk-1",
            "title": "La fe en Jesucristo",
            "author": None,
            "source": "Biblioteca oficial",
            "source_key": "church",
            "source_url": "https://example.com/source",
            "canonical_url": "https://example.com/doc",
            "language": "es",
            "section_title": "Introduccion",
            "snippet": "La fe en Jesucristo.",
            "score": 0.75,
            "tags": ["fe"],
            "scripture_refs": [],
        }
        original_document_search = public._document_search
        public._document_search = lambda *_args, **_kwargs: [row]
        try:
            response = TestClient(app).post("/api/search", json={"query": "Jesucristo"})
        finally:
            public._document_search = original_document_search

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(payload["items"], list)
        self.assertIsInstance(payload["results"], list)
        self.assertEqual(payload["items"], payload["results"])
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["items"][0]["document_id"], "doc-1")

    def test_sources_summary_returns_canonical_counts(self):
        response = public.sources_summary()

        by_key = {item["key"]: item for item in response["items"]}
        self.assertEqual(by_key["byu_speeches_en"]["documentCount"], 3)
        self.assertTrue(by_key["byu_speeches_en"]["canonical"])

    def test_default_document_filter_only_hides_confirmed_duplicates(self):
        sql = public.confirmed_duplicate_filter("d")

        self.assertIn("duplicate_document_id = d.id", sql)
        self.assertIn("review_status = 'confirmed'", sql)
        self.assertIn("'exact_duplicate'", sql)
        self.assertIn("'probable_duplicate'", sql)
        self.assertNotIn("translation", sql)
        self.assertNotIn("related_media", sql)

    def test_documents_can_exclude_seed_content(self):
        connection = FakeConnection()

        @contextmanager
        def tracked_get_conn():
            yield connection

        public.get_conn = tracked_get_conn
        public.documents(includeSeed=False)

        self.assertIn("seed_content", connection.last_query)
        self.assertIn("is_seed", connection.last_query)
        self.assertIn("<> 'true'", connection.last_query)

    def test_search_filter_can_exclude_seed_content(self):
        request = SearchRequest(query="Cristo", filters={"include_seed": False})

        where, _ = public._metadata_filter_sql(
            request.filters,
            None,
            "s.key",
            {"raw_metadata"},
        )

        self.assertTrue(any("is_seed" in clause and "seed_content" in clause for clause in where))

    def test_safe_metadata_removes_nested_secrets(self):
        safe = public._safe_metadata(
            {
                "source_type": "manual",
                "api_key": "do-not-return",
                "nested": {"token": "do-not-return", "language": "es"},
            }
        )

        self.assertEqual(safe, {"source_type": "manual", "nested": {"language": "es"}})

    def test_document_detail_returns_real_metadata_and_optional_chunks(self):
        published_at = datetime(2024, 4, 6, tzinfo=timezone.utc)

        class DetailConnection:
            def execute(self, sql, params=None):
                query = str(sql)
                if "FROM documents d" in query:
                    return FakeResult(
                        [
                            (
                                "doc-1",
                                "La fe en Jesucristo",
                                None,
                                "Biblioteca oficial",
                                "manual",
                                "https://example.com/source",
                                "https://example.com/canonical",
                                "es",
                                "manual",
                                published_at,
                                "Resumen real.",
                                None,
                                ["fe", "Cristo"],
                                "READY",
                                published_at,
                                published_at,
                                {
                                    "seed_content": True,
                                    "api_key": "do-not-return",
                                    "source_url": "https://example.com/source",
                                },
                                1,
                            )
                        ]
                    )
                if "FROM document_chunks" in query:
                    return FakeResult(
                        [
                            (
                                "chunk-1",
                                0,
                                "Introduccion",
                                "Contenido real del chunk.",
                                {"token": "do-not-return", "page": 1},
                            )
                        ]
                    )
                raise AssertionError(query)

        @contextmanager
        def detail_get_conn():
            yield DetailConnection()

        original_table_exists = public._table_exists
        original_table_columns = public._table_columns
        public.get_conn = detail_get_conn
        public._table_exists = lambda _conn, table: table == "document_chunks"
        public._table_columns = lambda _conn, table: {"text", "metadata"} if table == "document_chunks" else set()
        try:
            response = public.document_detail("doc-1", include_chunks=True)
        finally:
            public._table_exists = original_table_exists
            public._table_columns = original_table_columns

        self.assertEqual(response["source"], "Biblioteca oficial")
        self.assertEqual(response["source_url"], "https://example.com/source")
        self.assertEqual(response["summary"], "Resumen real.")
        self.assertEqual(response["tags"], ["fe", "Cristo"])
        self.assertEqual(response["chunks_available"], 1)
        self.assertEqual(response["chunks"][0]["text"], "Contenido real del chunk.")
        self.assertNotIn("api_key", response["metadata"])
        self.assertNotIn("token", response["chunks"][0]["metadata"])

    def test_document_detail_without_chunks_returns_empty_array(self):
        published_at = datetime(2024, 4, 6, tzinfo=timezone.utc)

        class DetailConnection:
            def execute(self, sql, params=None):
                query = str(sql)
                if "information_schema" in query:
                    return FakeResult([])
                if "FROM documents d" in query:
                    return FakeResult(
                        [
                            (
                                "doc-empty",
                                "Documento sin chunks",
                                None,
                                "Biblioteca oficial",
                                "manual",
                                "https://example.com/source",
                                "https://example.com/canonical",
                                "es",
                                "manual",
                                published_at,
                                None,
                                None,
                                [],
                                "READY",
                                published_at,
                                published_at,
                                {},
                                0,
                            )
                        ]
                    )
                raise AssertionError(query)

        @contextmanager
        def detail_get_conn():
            yield DetailConnection()

        original_get_conn = public.get_conn
        original_table_exists = public._table_exists
        original_table_columns = public._table_columns
        public.get_conn = detail_get_conn
        public._table_exists = lambda _conn, _table: False
        public._table_columns = lambda _conn, _table: set()
        try:
            response = public.document_detail("doc-empty", include_chunks=True)
        finally:
            public.get_conn = original_get_conn
            public._table_exists = original_table_exists
            public._table_columns = original_table_columns

        self.assertEqual(response["chunks"], [])
        self.assertEqual(response["chunks_available"], 0)

    def test_document_detail_missing_id_returns_404(self):
        class MissingConnection:
            def execute(self, sql, params=None):
                if "FROM documents d" in str(sql):
                    return FakeResult([])
                return FakeResult([])

        @contextmanager
        def missing_get_conn():
            yield MissingConnection()

        original_get_conn = public.get_conn
        original_table_exists = public._table_exists
        original_table_columns = public._table_columns
        public.get_conn = missing_get_conn
        public._table_exists = lambda _conn, _table: False
        public._table_columns = lambda _conn, table: {
            "id", "source_id", "title", "canonical_url", "text", "raw_metadata", "is_indexed"
        } if table == "documents" else set()
        try:
            with self.assertRaises(HTTPException) as raised:
                public.document_detail("missing", include_chunks=True)
        finally:
            public.get_conn = original_get_conn
            public._table_exists = original_table_exists
            public._table_columns = original_table_columns

        self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual(raised.exception.detail, "Documento no encontrado.")

    def test_document_detail_ignores_incompatible_legacy_document_tags(self):
        published_at = datetime(2024, 4, 6, tzinfo=timezone.utc)

        class LegacyConnection:
            def execute(self, sql, params=None):
                query = str(sql)
                if "FROM documents d" in query:
                    return FakeResult(
                        [
                            (
                                "doc-legacy",
                                "Documento heredado",
                                None,
                                "Fuente",
                                "manual",
                                "https://example.com/source",
                                "https://example.com/canonical",
                                "es",
                                "manual",
                                published_at,
                                None,
                                None,
                                [],
                                "READY",
                                published_at,
                                published_at,
                                {},
                                0,
                            )
                        ]
                    )
                if "JOIN tags" in query:
                    raise AssertionError("No debe consultar columnas heredadas incompatibles")
                return FakeResult([])

        @contextmanager
        def legacy_get_conn():
            yield LegacyConnection()

        original_get_conn = public.get_conn
        original_table_exists = public._table_exists
        original_table_columns = public._table_columns
        public.get_conn = legacy_get_conn
        public._table_exists = lambda _conn, table: table in {"document_tags", "tags"}
        public._table_columns = lambda _conn, table: {
            "document_tags": {"document_id", "tag_name"},
            "tags": {"id", "name"},
            "documents": {"id", "source_id", "title", "canonical_url", "text", "raw_metadata", "is_indexed"},
        }.get(table, set())
        try:
            response = public.document_detail("doc-legacy")
        finally:
            public.get_conn = original_get_conn
            public._table_exists = original_table_exists
            public._table_columns = original_table_columns

        self.assertEqual(response["id"], "doc-legacy")

    def test_search_builds_legacy_compatible_chunk_query(self):
        class SearchConnection:
            def __init__(self):
                self.search_query = ""

            def execute(self, sql, params=None):
                query = str(sql)
                if "information_schema.columns" in query:
                    table = params[0]
                    columns = {
                        "documents": [
                            "id", "source_id", "title", "canonical_url", "author", "language",
                            "text", "raw_metadata", "tags", "scripture_refs", "updated_at",
                        ],
                        "document_chunks": ["id", "document_id", "chunk_index", "content"],
                        "document_tags": ["document_id", "tag_name"],
                        "tags": ["id", "name"],
                    }.get(table, [])
                    return FakeResult([(column,) for column in columns])
                if "information_schema.tables" in query:
                    return FakeResult([(params[0] in {"document_chunks", "document_tags", "tags"},)])
                if "FROM documents d" in query:
                    self.search_query = query
                    return FakeResult([])
                raise AssertionError(query)

        connection = SearchConnection()

        @contextmanager
        def search_get_conn():
            yield connection

        original_get_conn = public.get_conn
        public.get_conn = search_get_conn
        try:
            response = public._document_search("Jesucristo", 5)
        finally:
            public.get_conn = original_get_conn

        self.assertEqual(response, [])
        self.assertIn("dc.content", connection.search_query)
        self.assertIn("NULL::text AS section_title", connection.search_query)
        self.assertNotIn("{chunk_", connection.search_query)
        self.assertNotIn("JOIN tags t ON t.id = dt.tag_id", connection.search_query)


if __name__ == "__main__":
    unittest.main()
