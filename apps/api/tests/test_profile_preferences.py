from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
import json
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.routes import profile  # noqa: E402

USER_ID = "00000000-0000-4000-8000-000000000001"


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


class FakeConnection:
    row_factory = None

    def __init__(self):
        self.saved = None

    def execute(self, sql, params=None):
        query = str(sql)
        if "SELECT user_id::text" in query:
            return FakeResult([])
        if "INSERT INTO user_preferences" in query:
            self.saved = params
            return FakeResult(
                [
                    {
                        "user_id": params["user_id"],
                        "calling_category": params["calling_category"],
                        "calling_name": params["calling_name"],
                        "custom_calling_name": params["custom_calling_name"],
                        "calling_focus_enabled": params["calling_focus_enabled"],
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


class ProfilePreferencesTest(unittest.TestCase):
    def setUp(self):
        self.original_get_conn = profile.get_conn
        profile.get_conn = fake_get_conn

    def tearDown(self):
        profile.get_conn = self.original_get_conn

    def test_catalog_loads_and_includes_other_calling(self):
        catalog_path = Path(__file__).resolve().parents[3] / "packages" / "shared" / "church-callings.json"
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        callings = [calling for category in catalog for calling in category["callings"]]

        self.assertGreaterEqual(len(catalog), 8)
        self.assertIn("Setenta de Area", callings)
        self.assertTrue(any("Otro" in calling for calling in callings))

    def test_get_preferences_returns_default_for_new_user(self):
        response = profile.get_preferences(user_id=USER_ID)

        self.assertEqual(response["userId"], USER_ID)
        self.assertFalse(response["callingFocusEnabled"])
        self.assertIsNone(response["callingName"])

    def test_update_preferences_saves_calling(self):
        response = profile.update_preferences(
            profile.CallingPreferencePayload(
                callingCategory="ward-branch",
                callingName="Obispo",
                customCallingName=None,
                callingFocusEnabled=True,
            ),
            user_id=USER_ID,
        )

        self.assertEqual(response["callingCategory"], "ward-branch")
        self.assertEqual(response["callingName"], "Obispo")
        self.assertTrue(response["callingFocusEnabled"])


if __name__ == "__main__":
    unittest.main()
