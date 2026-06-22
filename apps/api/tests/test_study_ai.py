import unittest

from app.services.study_ai import _fallback_suggestions, _normalize_workspace_suggestion, prompt_hash


class StudyAiServiceTests(unittest.TestCase):
    def test_prompt_hash_is_stable_for_sorted_payloads(self):
        left = {"mode": "rapido", "blockTypes": ["ai_reference"], "prompt": "Helaman 5:6"}
        right = {"prompt": "Helaman 5:6", "blockTypes": ["ai_reference"], "mode": "rapido"}

        self.assertEqual(prompt_hash(left), prompt_hash(right))

    def test_fallback_suggestions_are_structured_and_source_marked(self):
        suggestions = _fallback_suggestions(
            {
                "title": "Los nombres en Helaman 5:6",
                "scripture_reference": "Helaman 5:6",
                "calling_context": "Clase familiar",
            },
            ["ai_doctrinal_analysis", "reflection_question"],
            [],
            2,
        )

        self.assertEqual(len(suggestions), 2)
        self.assertEqual(suggestions[0]["sourceStatus"], "idea_relacionada")
        self.assertIn("type", suggestions[0])
        self.assertIn("title", suggestions[0])
        self.assertIn("content", suggestions[0])

    def test_workspace_suggestion_clears_unverified_quote_text(self):
        suggestion = _normalize_workspace_suggestion(
            {
                "type": "quote",
                "title": "Cita sugerida",
                "content": "Buscar y verificar antes de guardar.",
                "quote_text": "Texto literal no verificado",
                "source_status": "suggested",
                "confidence": "medium",
            }
        )

        self.assertIsNone(suggestion["quote_text"])
        self.assertEqual(suggestion["source_status"], "suggested")
        self.assertTrue(suggestion["is_ai_generated"])


if __name__ == "__main__":
    unittest.main()
