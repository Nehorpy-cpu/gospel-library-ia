from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rag.calling_focus import (  # noqa: E402
    calling_application_guidance,
    calling_display_name,
    calling_focus_prompt_block,
)
from app.schemas.chat import ChatRequest  # noqa: E402


class CallingFocusPromptTest(unittest.TestCase):
    def test_custom_other_calling_is_resolved(self):
        request = ChatRequest(
            message="Analiza 1 Nefi 3:7",
            calling_focus={
                "callingCategory": "member",
                "callingName": "Otro",
                "customCallingName": "Coordinador de autosuficiencia",
                "callingFocusEnabled": True,
            },
        )

        self.assertEqual(calling_display_name(request.calling_focus), "Coordinador de autosuficiencia")

    def test_prompt_includes_selected_calling(self):
        request = ChatRequest(
            message="Analiza Mosiah 2:17",
            calling_focus={
                "callingCategory": "general-area",
                "callingName": "Setenta de Area",
                "callingFocusEnabled": True,
            },
        )
        block = calling_focus_prompt_block(request.calling_focus)

        self.assertIn("Aplicacion segun mi llamamiento: Setenta de Area", block)
        self.assertIn("La doctrina no se adapta ni se cambia", block)

    def test_general_discipleship_when_no_calling_selected(self):
        block = calling_focus_prompt_block(None)

        self.assertIn("discipulado general", block)
        self.assertIn("preparacion para servir", block)

    def test_specific_calling_replaces_fixed_area_seventy_assumption(self):
        guidance = calling_application_guidance("Obispo")

        self.assertIn("Aplicacion segun mi llamamiento: Obispo", guidance)
        self.assertIn("presidir el Sacerdocio Aaronico", guidance)
        self.assertNotIn("Aplicacion para liderazgo como Setenta de Area", guidance)


if __name__ == "__main__":
    unittest.main()
