from pathlib import Path
import sys
import unittest

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app
from app.services.privacy import sanitize_value


class PrivacyControlsTest(unittest.TestCase):
    def test_log_sanitizer_redacts_secret_fields(self):
        payload = {
            "OPENAI_API_KEY": "sk-test-secret",
            "authorization": "Bearer abc",
            "nested": {"refresh_token": "token-value", "safe": "value"},
        }

        self.assertEqual(
            sanitize_value(payload),
            {
                "OPENAI_API_KEY": "[REDACTED]",
                "authorization": "[REDACTED]",
                "nested": {"refresh_token": "[REDACTED]", "safe": "value"},
            },
        )

    def test_sensitive_routes_return_security_headers(self):
        client = TestClient(app)
        response = client.get("/api/study-workspaces")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertEqual(response.headers["x-frame-options"], "DENY")
        self.assertEqual(response.headers["referrer-policy"], "no-referrer")
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_frontend_env_does_not_expose_openai_keys(self):
        env_file = Path(__file__).resolve().parents[2] / "web" / ".env.example"
        content = env_file.read_text(encoding="utf-8")

        self.assertNotIn("NEXT_PUBLIC_OPENAI_API_KEY", content)
        self.assertNotIn("OPENAI_API_KEY", content)


if __name__ == "__main__":
    unittest.main()
