from contextlib import contextmanager
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.routes import public
from app.schemas.api import SearchRequest


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows


class FakeConnection:
    def execute(self, sql, params=None):
        query = str(sql)
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

    def test_sources_summary_returns_canonical_counts(self):
        response = public.sources_summary()

        by_key = {item["key"]: item for item in response["items"]}
        self.assertEqual(by_key["byu_speeches_en"]["documentCount"], 3)
        self.assertTrue(by_key["byu_speeches_en"]["canonical"])


if __name__ == "__main__":
    unittest.main()
