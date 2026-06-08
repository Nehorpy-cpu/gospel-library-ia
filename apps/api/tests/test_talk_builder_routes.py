from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
import asyncio
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.routes import talk_builder

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
        if "FROM documents d" in query:
            return FakeResult(
                [
                    {
                        "id": "doc-1",
                        "title": "La fe en Jesucristo",
                        "author": "Gospel Library IA",
                        "language": "es",
                        "canonical_url": "https://example.com/doc-1",
                        "source_url": "https://example.com/source",
                        "source_type": "byu_speeches_es",
                        "source_name": "BYU Speeches ES",
                        "excerpt": "La fe en Jesucristo produce accion y esperanza.",
                        "scripture_refs": ["Alma 32:21"],
                        "match_score": 3,
                    }
                ]
            )
        if "FROM saved_citations sc" in query:
            return FakeResult(
                [
                    {
                        "id": "quote-1",
                        "workspace_id": WORKSPACE_ID,
                        "document_id": "doc-1",
                        "chunk_id": None,
                        "quote": "La fe es un principio de accion.",
                        "selected_text": None,
                        "citation_url": "https://example.com/doc-1",
                        "source_url": "https://example.com/source",
                        "source_title": "La fe en Jesucristo",
                        "source_author": "Gospel Library IA",
                        "location": {},
                        "scripture_refs": ["Alma 32:21"],
                        "metadata": {},
                        "updated_at": datetime.now(UTC),
                    }
                ]
            )
        if "FROM study_workspaces" in query and "name = %(name)s" in query:
            return FakeResult([])
        if "INSERT INTO study_workspaces" in query:
            return FakeResult([{"id": WORKSPACE_ID}])
        if "FROM study_workspaces" in query:
            return FakeResult([{"id": WORKSPACE_ID}])
        if "INSERT INTO study_notes" in query:
            return FakeResult(
                [
                    {
                        "id": "draft-1",
                        "workspace_id": WORKSPACE_ID,
                        "title": "Bosquejo: Fe",
                        "content": "# Bosquejo: Fe",
                        "scripture_refs": ["Alma 32:21"],
                        "created_at": datetime.now(UTC),
                        "updated_at": datetime.now(UTC),
                    }
                ]
            )
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


class TalkBuilderRoutesTest(unittest.TestCase):
    def setUp(self):
        self.original_get_conn = talk_builder.get_conn
        self.original_limiter = talk_builder.limiter
        talk_builder.get_conn = fake_get_conn
        talk_builder.limiter = FakeLimiter()

    def tearDown(self):
        talk_builder.get_conn = self.original_get_conn
        talk_builder.limiter = self.original_limiter

    def test_outline_uses_real_documents_and_saved_quotes(self):
        response = asyncio.run(
            talk_builder.generate_outline(
                talk_builder.TalkBuilderRequest(topic="Fe en Jesucristo", scriptureRefs=["Alma 32:21"]),
                request=FakeRequest(),
                user_id=USER_ID,
            )
        )

        self.assertEqual(response["status"], "ready")
        self.assertEqual(response["sources"][0]["id"], "doc-1")
        self.assertEqual(response["savedQuotes"][0]["id"], "quote-1")
        self.assertEqual(response["sections"][0]["citations"][0]["type"], "saved_quote")
        self.assertIn("Alma 32:21", response["scriptureRefs"])

    def test_save_draft_creates_workspace_and_note(self):
        response = talk_builder.save_draft(
            talk_builder.TalkDraftPayload(
                title="Bosquejo: Fe",
                outline={"title": "Bosquejo: Fe", "sections": []},
                scriptureRefs=["Alma 32:21"],
            ),
            user_id=USER_ID,
        )

        self.assertEqual(response["status"], "saved")
        self.assertEqual(response["draftId"], "draft-1")
        self.assertEqual(response["workspaceId"], WORKSPACE_ID)


if __name__ == "__main__":
    unittest.main()
