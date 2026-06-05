from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
import sys
import unittest

from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.routes import admin

JOB_ID = "20000000-0000-4000-8000-000000000001"


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


class FakeConnection:
    row_factory = None

    def __init__(self):
        self.committed = False

    def execute(self, sql, params=None):
        query = str(sql)
        now = datetime.now(UTC)
        if "FROM ingestion_jobs" in query and "UPDATE" not in query and "WITH document_stats" not in query:
            return FakeResult(
                [
                    (
                        JOB_ID,
                        "scrape",
                        "failed",
                        3,
                        "Timeout",
                        ["Timeout"],
                        {"source": "byu"},
                        "byu_speeches_en",
                        now,
                        now,
                        now,
                    )
                ]
            )
        if "FROM documents d" in query and "raw_metadata ? 'error'" in query:
            return FakeResult(
                [
                    (
                        "doc-1",
                        "Documento fallido",
                        "FAILED",
                        "https://example.com/doc",
                        now,
                        "BYU Speeches",
                        "byu_speeches_en",
                        "Parse error",
                    )
                ]
            )
        if "UPDATE ingestion_jobs" in query and params and params.get("job_id") == JOB_ID:
            return FakeResult([(JOB_ID, "scrape", "queued", {"source": "byu"}, "byu_speeches_en")])
        if "FROM sources s" in query and "WITH document_stats" in query:
            return FakeResult(
                [
                    (
                        "source-1",
                        "byu_speeches_en",
                        "BYU Speeches English",
                        "byu_speeches_en",
                        "https://speeches.byu.edu/talks/",
                        "en",
                        True,
                        "listing_and_talk_pages",
                        30,
                        12,
                        now,
                        "Respect robots.txt",
                        3,
                        12000,
                        now,
                        0,
                    )
                ]
            )
        if "UPDATE sources" in query:
            return FakeResult([("source-1", params["source_id"], params.get("enabled", True), params.get("max_pages_per_run", 12))])
        return FakeResult([])

    def commit(self):
        self.committed = True


@contextmanager
def fake_get_conn():
    yield FakeConnection()


class AdminRoutesTest(unittest.TestCase):
    def setUp(self):
        self.original_get_conn = admin.get_conn
        admin.get_conn = fake_get_conn

    def tearDown(self):
        admin.get_conn = self.original_get_conn

    def test_admin_errors_returns_jobs_and_documents(self):
        response = admin.admin_errors()

        self.assertEqual(response["jobs"][0]["id"], JOB_ID)
        self.assertEqual(response["jobs"][0]["status"], "failed")
        self.assertEqual(response["documents"][0]["status"], "FAILED")
        self.assertEqual(response["documents"][0]["sourceType"], "byu_speeches_en")

    def test_retry_ingestion_job_requeues_failed_job(self):
        response = admin.retry_ingestion_job(JOB_ID)

        self.assertEqual(response["task_id"], JOB_ID)
        self.assertEqual(response["status"], "queued")

    def test_retry_ingestion_job_rejects_missing_job(self):
        with self.assertRaises(HTTPException):
            admin.retry_ingestion_job("missing")

    def test_admin_sources_returns_catalog(self):
        response = admin.admin_sources()

        self.assertEqual(response["items"][0]["sourceId"], "byu_speeches_en")
        self.assertEqual(response["items"][0]["sourceType"], "byu_speeches_en")
        self.assertEqual(response["items"][0]["maxPagesPerRun"], 12)
        self.assertEqual(response["items"][0]["indexingMode"], "index_later")

    def test_update_admin_source_changes_limits(self):
        response = admin.update_admin_source("byu_speeches_en", admin.SourceUpdateRequest(maxPagesPerRun=5))

        self.assertEqual(response["sourceId"], "byu_speeches_en")
        self.assertEqual(response["maxPagesPerRun"], 5)


if __name__ == "__main__":
    unittest.main()
