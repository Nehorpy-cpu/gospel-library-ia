import unittest
import httpx
from types import SimpleNamespace

from app.services import study_ai
from app.services.study_ai import (
    _extract_response_json,
    _fallback_suggestions,
    _normalize_workspace_suggestion,
    build_workspace_responses_request,
    openai_request_summary,
    prompt_hash,
)


def _contains_key(value, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False


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

        self.assertEqual(suggestion["quote_text"], "")
        self.assertEqual(suggestion["source_status"], "suggested")
        self.assertTrue(suggestion["is_ai_generated"])

    def test_workspace_responses_payload_uses_current_text_format(self):
        request_body = build_workspace_responses_request(
            model="gpt-4.1-mini",
            system_prompt="Devuelve solo JSON.",
            user_payload={"maxSuggestions": 2},
            max_output_tokens=500,
            structured=True,
        )

        text_format = request_body["text"]["format"]
        self.assertNotIn("response_format", request_body)
        self.assertNotIn("json_schema", text_format)
        self.assertEqual(text_format["type"], "json_schema")
        self.assertEqual(text_format["name"], "study_ai_suggestions")
        self.assertEqual(text_format["strict"], True)
        self.assertIn("schema", text_format)
        self.assertFalse(_contains_key(text_format["schema"], "default"))

    def test_openai_request_summary_does_not_include_prompt(self):
        request_body = build_workspace_responses_request(
            model="gpt-4.1-mini",
            system_prompt="Prompt secreto",
            user_payload={"localContext": ["texto"]},
            max_output_tokens=500,
            structured=True,
        )

        summary = openai_request_summary(request_body)

        self.assertEqual(summary["model"], "gpt-4.1-mini")
        self.assertEqual(summary["has_text_format"], True)
        self.assertEqual(summary["schema_name"], "study_ai_suggestions")
        self.assertEqual(summary["input_type"], "array")
        self.assertNotIn("Prompt secreto", str(summary))

    def test_extract_response_json_reads_output_text(self):
        parsed = _extract_response_json(
            {
                "output_text": '{"suggestions":[],"sources_used":[],"warnings":[]}',
            }
        )

        self.assertEqual(parsed["suggestions"], [])

    def test_extract_response_json_reads_output_content_text(self):
        parsed = _extract_response_json(
            {
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": '{"suggestions":[],"sources_used":[],"warnings":["ok"]}',
                            }
                        ],
                    }
                ]
            }
        )

        self.assertEqual(parsed["warnings"], ["ok"])

    def test_openai_400_raises_controlled_invalid_request(self):
        original_async_client = study_ai.httpx.AsyncClient

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def post(self, url, headers=None, json=None):
                return httpx.Response(
                    400,
                    json={
                        "error": {
                            "message": "Invalid schema shape",
                            "type": "invalid_request_error",
                            "param": "text.format",
                            "code": "invalid_json_schema",
                        }
                    },
                    request=httpx.Request("POST", url),
                )

        study_ai.httpx.AsyncClient = FakeAsyncClient
        try:
            with self.assertRaises(study_ai.StudyAiProviderInvalidRequestError) as context:
                import asyncio

                asyncio.run(study_ai._post_openai_responses("sk-test", {"model": "gpt-4.1-mini"}))
            self.assertIn("Invalid schema shape", str(context.exception))
            self.assertNotIn("sk-test", str(context.exception))
        finally:
            study_ai.httpx.AsyncClient = original_async_client

    def test_workspace_generation_falls_back_to_json_object_after_structured_400(self):
        original_async_client = study_ai.httpx.AsyncClient
        original_get_settings = study_ai.get_settings
        requests: list[dict] = []

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def post(self, url, headers=None, json=None):
                requests.append(json)
                if len(requests) == 1:
                    return httpx.Response(
                        400,
                        json={"error": {"message": "Invalid schema", "type": "invalid_request_error"}},
                        request=httpx.Request("POST", url),
                    )
                return httpx.Response(
                    200,
                    json={
                        "output_text": (
                            '{"suggestions":[{"type":"reflection_question","title":"Pregunta",'
                            '"content":"Que debo aplicar?","source_title":"","source_author":"",'
                            '"source_reference":"","source_url":"","quote_text":"","is_ai_generated":true,'
                            '"confidence":"medium","source_status":"none"}],"sources_used":[],"warnings":[]}'
                        )
                    },
                    request=httpx.Request("POST", url),
                )

        study_ai.httpx.AsyncClient = FakeAsyncClient
        study_ai.get_settings = lambda: SimpleNamespace(
            openai_api_key="sk-test",
            openai_chat_model="",
            study_ai_max_suggestions=12,
        )
        try:
            import asyncio

            suggestions, sources_used, warnings, provider = asyncio.run(
                study_ai.generate_workspace_suggestions(
                    workspace={"id": "w1", "name": "Estudio", "settings": {"title": "Estudio"}},
                    blocks=[],
                    user_id="u1",
                    payload={"mode": "rapido", "maxSuggestions": 1},
                    local_context=[],
                )
            )

            self.assertEqual(provider, "openai_responses_json_object_fallback")
            self.assertEqual(suggestions[0]["type"], "reflection_question")
            self.assertEqual(suggestions[0]["quote_text"], "")
            self.assertEqual(sources_used, [])
            self.assertEqual(requests[0]["text"]["format"]["type"], "json_schema")
            self.assertEqual(requests[1]["text"]["format"]["type"], "json_object")
            self.assertEqual(requests[0]["model"], "gpt-4.1-mini")
            self.assertIn("No se encontraron suficientes fuentes locales", warnings[0])
        finally:
            study_ai.httpx.AsyncClient = original_async_client
            study_ai.get_settings = original_get_settings


if __name__ == "__main__":
    unittest.main()
