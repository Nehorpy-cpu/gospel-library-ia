from pathlib import Path
import unittest


class CorsProductionConfigTest(unittest.TestCase):
    def test_production_example_allows_estudiopy_frontend_origin(self):
        env_example = Path(__file__).resolve().parents[1] / ".env.production.example"
        values = {}
        for line in env_example.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key] = value

        origins = {origin.strip() for origin in values["CORS_ORIGINS"].split(",")}
        self.assertIn("https://www.estudiopy.com", origins)


if __name__ == "__main__":
    unittest.main()
