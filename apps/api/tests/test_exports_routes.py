from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
import asyncio
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.routes import exports

USER_ID = "00000000-0000-4000-8000-000000000001"
WORKSPACE_ID = "10000000-0000-4000-8000-000000000001"


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


class FakeConnection:
    row_factory = None

    def execute(self, sql, params=None):
        query = str(sql)
        if "FROM study_workspaces" in query:
            if params.get("user_id") != USER_ID:
                return FakeResult([])
            return FakeResult([{"id": WORKSPACE_ID, "name": "Mi estudio", "description": "Notas privadas"}])
        if "FROM study_notes sn" in query:
            return FakeResult(
                [
                    {
                        "id": "note-1",
                        "title": "Fe",
                        "content": "La fe conduce a actuar.",
                        "selected_text": "La fe conduce a actuar.",
                        "scripture_refs": ["Alma 32:21"],
                        "position": {},
                        "created_at": datetime.now(UTC),
                        "updated_at": datetime.now(UTC),
                        "document_title": "La fe en Jesucristo",
                        "document_author": "Gospel Library IA",
                        "source_url": "https://example.com/source",
                    }
                ]
            )
        if "FROM saved_citations sc" in query:
            return FakeResult(
                [
                    {
                        "id": "citation-1",
                        "quote": "La fe es un principio de accion.",
                        "selected_text": None,
                        "citation_url": "https://example.com/doc-1",
                        "source_url": "https://example.com/source",
                        "source_title": "La fe en Jesucristo",
                        "source_author": "Gospel Library IA",
                        "location": {},
                        "scripture_refs": ["Alma 32:21"],
                        "created_at": datetime.now(UTC),
                        "updated_at": datetime.now(UTC),
                    }
                ]
            )
        if "INSERT INTO beta_activity_events" in query:
            return FakeResult([])
        return FakeResult([])

    def commit(self):
        return None


@contextmanager
def fake_get_conn():
    yield FakeConnection()


class FakeClient:
    host = "127.0.0.1"


class FakeRequest:
    headers = {"X-User-Id": USER_ID}
    client = FakeClient()


class FakeLimiter:
    async def check_daily(self, request, limit, scope):
        return None


class ExportsRoutesTest(unittest.TestCase):
    def setUp(self):
        self.original_get_conn = exports.get_conn
        self.original_limiter = exports.limiter
        exports.get_conn = fake_get_conn
        exports.limiter = FakeLimiter()

    def tearDown(self):
        exports.get_conn = self.original_get_conn
        exports.limiter = self.original_limiter

    def test_markdown_export_preserves_source_attribution(self):
        response = asyncio.run(
            exports.export_study_material(
                exports.StudyExportPayload(workspaceId=WORKSPACE_ID, kind="all", format="markdown"),
                request=FakeRequest(),
                user_id=USER_ID,
            )
        )

        content = response.body.decode("utf-8")
        self.assertIn("La fe en Jesucristo", content)
        self.assertIn("Source URL: https://example.com/source", content)
        self.assertIn("Source URL: https://example.com/doc-1", content)
        self.assertIn("Alma 32:21", content)

    def test_pdf_export_returns_pdf_bytes(self):
        response = asyncio.run(
            exports.export_study_material(
                exports.StudyExportPayload(workspaceId=WORKSPACE_ID, kind="quotes", format="pdf"),
                request=FakeRequest(),
                user_id=USER_ID,
            )
        )

        self.assertEqual(response.media_type, "application/pdf")
        self.assertTrue(response.body.startswith(b"%PDF-1.4"))

    def test_export_rejects_workspace_from_other_user(self):
        with self.assertRaises(Exception):
            asyncio.run(
                exports.export_study_material(
                    exports.StudyExportPayload(workspaceId=WORKSPACE_ID, kind="all", format="markdown"),
                    request=FakeRequest(),
                    user_id="00000000-0000-4000-8000-000000000099",
                )
            )


if __name__ == "__main__":
    unittest.main()
