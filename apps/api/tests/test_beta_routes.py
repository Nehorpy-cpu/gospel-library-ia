from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.routes import beta
from app.services.auth import AuthContext

USER_ID = "00000000-0000-4000-8000-000000000001"


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class FakeConnection:
    row_factory = None

    def execute(self, sql, params=None):
        query = str(sql)
        now = datetime.now(UTC)
        if "SELECT count(*)" in query:
            return FakeResult([(1,)])
        if "INSERT INTO beta_access" in query:
            return FakeResult(
                [
                    {
                        "id": "access-1",
                        "user_id": params.get("user_id"),
                        "email": params["email"],
                        "name": params.get("name"),
                        "status": params.get("status", "pending"),
                        "study_profile": params.get("study_profile"),
                        "preferred_language": params.get("preferred_language"),
                        "preferred_sources": params.get("preferred_sources") or [],
                        "onboarding_completed_at": now if "study_profile" in params else None,
                        "approved_at": now if params.get("status") == "approved" else None,
                        "created_at": now,
                        "updated_at": now,
                    }
                ]
            )
        if "SELECT status FROM beta_access" in query:
            return FakeResult([])
        if "INSERT INTO beta_feedback" in query:
            return FakeResult(
                [
                    {
                        "id": "feedback-1",
                        "user_id": params["user_id"],
                        "email": params.get("email"),
                        "page": params["page"],
                        "type": params["type"],
                        "message": params["message"],
                        "screenshot_url": params.get("screenshot_url"),
                        "status": "new",
                        "created_at": now,
                        "updated_at": now,
                    }
                ]
            )
        if "FROM beta_access" in query:
            return FakeResult(
                [
                    {
                        "id": "access-1",
                        "user_id": USER_ID,
                        "email": "beta@example.com",
                        "name": "Beta User",
                        "status": "approved",
                        "study_profile": "obispo",
                        "preferred_language": "es",
                        "preferred_sources": ["general_conference"],
                        "onboarding_completed_at": now,
                        "approved_at": now,
                        "created_at": now,
                        "updated_at": now,
                    }
                ]
            )
        if "FROM beta_feedback" in query:
            return FakeResult(
                [
                    {
                        "id": "feedback-1",
                        "user_id": USER_ID,
                        "email": "beta@example.com",
                        "page": "/study",
                        "type": "suggestion",
                        "message": "Mejorar filtros",
                        "screenshot_url": None,
                        "status": "new",
                        "created_at": now,
                        "updated_at": now,
                    }
                ]
            )
        return FakeResult([])

    def commit(self):
        return None


@contextmanager
def fake_get_conn():
    yield FakeConnection()


class BetaRoutesTest(unittest.TestCase):
    def setUp(self):
        self.original_get_conn = beta.get_conn
        beta.get_conn = fake_get_conn

    def tearDown(self):
        beta.get_conn = self.original_get_conn

    def test_request_beta_access_persists_pending_user(self):
        response = beta.request_beta_access(beta.BetaAccessRequest(email="Beta@Example.com", name="Beta"))

        self.assertEqual(response["email"], "beta@example.com")
        self.assertEqual(response["status"], "pending")

    def test_onboarding_persists_profile(self):
        response = beta.complete_onboarding(
            beta.BetaOnboardingPayload(
                callingProfile="obispo",
                language="es",
                preferredSources=["general_conference"],
            ),
            context=AuthContext(user_id=USER_ID, external_id="Beta User", role="user", email="beta@example.com"),
        )

        self.assertEqual(response["studyProfile"], "obispo")
        self.assertEqual(response["preferredLanguage"], "es")

    def test_submit_feedback_returns_feedback_row(self):
        response = beta.submit_feedback(
            beta.FeedbackPayload(page="/study", type="suggestion", message="Mejorar filtros"),
            context=AuthContext(user_id=USER_ID, external_id="Beta User", role="user", email="beta@example.com"),
            x_user_email="beta@example.com",
        )

        self.assertEqual(response["id"], "feedback-1")
        self.assertEqual(response["type"], "suggestion")

    def test_admin_beta_returns_metrics_feedback_and_users(self):
        response = beta.admin_beta()

        self.assertEqual(response["version"]["version"], "0.1.0-beta")
        self.assertEqual(response["metrics"]["feedback"], 1)
        self.assertEqual(response["users"][0]["status"], "approved")
        self.assertEqual(response["feedback"][0]["status"], "new")


if __name__ == "__main__":
    unittest.main()
