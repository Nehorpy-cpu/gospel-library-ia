from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class AlembicIsolationTests(unittest.TestCase):
    def test_services_use_distinct_version_tables(self) -> None:
        scraper_env = (ROOT / "scraper" / "migrations" / "env.py").read_text(encoding="utf-8")
        rag_env = (ROOT / "rag" / "migrations" / "env.py").read_text(encoding="utf-8")

        self.assertIn('VERSION_TABLE = "scraper_alembic_version"', scraper_env)
        self.assertIn('VERSION_TABLE = "rag_alembic_version"', rag_env)
        self.assertNotEqual(
            self._version_table(scraper_env),
            self._version_table(rag_env),
        )

    @staticmethod
    def _version_table(source: str) -> str:
        marker = 'VERSION_TABLE = "'
        return source.split(marker, maxsplit=1)[1].split('"', maxsplit=1)[0]


if __name__ == "__main__":
    unittest.main()
