from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
import sys
import unittest

from fastapi import HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app
from app.routes import admin
from app.services.auth import AuthContext, normalize_user_id, require_admin

USER_ID = "00000000-0000-4000-8000-000000000001"
ADMIN_ID = "00000000-0000-4000-8000-0000000000ad"


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class FakeConnection:
    def execute(self, sql, params=None):
        query = str(sql)
        now = datetime.now(UTC)
        if "SELECT current_database(), now()" in query:
            return FakeResult([("gospel_library", now)])
        if "SELECT count(*) FROM documents" in query:
            return FakeResult([(3,)])
        if "SELECT count(*) FROM ingestion_jobs" in query:
            return FakeResult([(0,)])
        if "GROUP BY 1" in query:
            return FakeResult([("byu_speeches_en", 3)])
        return FakeResult([])


class FakeQdrantAdmin:
    def ensure_collection(self):
        return {"status": "ok", "collection": "doctrinal_chunks_v1", "points_count": 0}


@contextmanager
def fake_get_conn():
    yield FakeConnection()


class AuthProductionControlsTest(unittest.TestCase):
    def setUp(self):
        self.original_get_conn = admin.get_conn
        self.original_qdrant_admin = admin.QdrantAdmin
        admin.get_conn = fake_get_conn
        admin.QdrantAdmin = FakeQdrantAdmin
        self.client = TestClient(app)

    def tearDown(self):
        admin.get_conn = self.original_get_conn
        admin.QdrantAdmin = self.original_qdrant_admin

    def test_external_user_ids_are_mapped_to_internal_uuid(self):
        self.assertEqual(normalize_user_id(USER_ID), USER_ID)
        self.assertEqual(normalize_user_id("clerk-user-123"), normalize_user_id("clerk-user-123"))

    def test_admin_requires_authentication(self):
        response = self.client.get("/api/admin/status")
        self.assertEqual(response.status_code, 401)

    def test_normal_user_cannot_access_admin(self):
        response = self.client.get("/api/admin/status", headers={"X-User-Id": USER_ID, "X-User-Role": "user"})
        self.assertEqual(response.status_code, 403)

    def test_admin_can_access_admin_status(self):
        response = self.client.get("/api/admin/status", headers={"X-User-Id": ADMIN_ID, "X-User-Role": "admin"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["postgres"]["documents"], 3)

    def test_require_admin_rejects_user_context(self):
        with self.assertRaises(HTTPException):
            require_admin(AuthContext(user_id=USER_ID, external_id=USER_ID, role="user"))


if __name__ == "__main__":
    unittest.main()
