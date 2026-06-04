from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.routes import public  # noqa: E402
from app.schemas.api import ChatRequest  # noqa: E402


class LeadershipFallbackTest(unittest.TestCase):
    def setUp(self):
        self.original_document_search = public._document_search
        public._document_search = lambda *args, **kwargs: []

    def tearDown(self):
        public._document_search = self.original_document_search

    def test_local_chat_response_warns_for_current_leadership_queries(self):
        response = public._local_chat_response(
            ChatRequest(message="Quienes integran la Primera Presidencia actual?")
        )

        self.assertIn("Regla de actualidad", response["message"])
        self.assertIn("Presidente Dallin H. Oaks", response["message"])
        self.assertIn("verificacion con fuentes oficiales", " ".join(response["warnings"]))

    def test_local_chat_response_does_not_add_leadership_note_for_general_query(self):
        response = public._local_chat_response(ChatRequest(message="Explica Alma 32 sobre la fe"))

        self.assertNotIn("Regla de actualidad", response["message"])

    def test_local_chat_response_includes_dynamic_calling_focus(self):
        response = public._local_chat_response(
            ChatRequest(
                message="Analiza Mosiah 2:17",
                calling_focus={
                    "callingCategory": "ward-branch",
                    "callingName": "Obispo",
                    "callingFocusEnabled": True,
                },
            )
        )

        self.assertIn("Aplicacion segun mi llamamiento: Obispo", response["message"])
        self.assertNotIn("Setenta de Area", response["message"])


if __name__ == "__main__":
    unittest.main()
