from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.asset_validation import asset_response_error


class AssetDownloadValidationTest(unittest.TestCase):
    def test_accepts_real_pdf_signature(self):
        error = asset_response_error(
            asset_type="pdf",
            final_url="https://example.com/talk.pdf",
            status_code=200,
            content=b"%PDF-1.7\ncontent",
            content_type="application/pdf",
        )

        self.assertIsNone(error)

    def test_rejects_login_html_for_pdf_without_retryable_exception(self):
        error = asset_response_error(
            asset_type="pdf",
            final_url="https://www.churchofjesuschrist.org/study/login?state=silent",
            status_code=200,
            content=b"<html>login required</html>",
            content_type="text/html; charset=utf-8",
        )

        self.assertIn("HTML/login", error)

    def test_rejects_empty_asset_response(self):
        error = asset_response_error(
            asset_type="mp3",
            final_url="https://example.com/audio.mp3",
            status_code=200,
            content=b"",
            content_type="audio/mpeg",
        )

        self.assertEqual(error, "Asset response was empty")


if __name__ == "__main__":
    unittest.main()
