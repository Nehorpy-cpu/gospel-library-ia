import asyncio
import unittest
from types import SimpleNamespace

import httpx

from app.services import study_ai
from app.services.study_ai import (
    _fallback_suggestions,
    _normalize_workspace_suggestion,
    build_workspace_responses_request,
    extract_json_object,
    normalize_ai_suggestions,
    openai_request_summary,
    prompt_hash,
)


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

    def test_workspace_responses_payload_uses_json_object_without_schema(self):
        request_body = build_workspace_responses_request(
            model="gpt-4.1-mini",
            system_prompt="Responde unicamente con JSON valido.",
            user_payload={"maxSuggestions": 2},
            max_output_tokens=500,
            json_mode=True,
        )

        self.assertNotIn("response_format", request_body)
        self.assertEqual(request_body["text"]["format"], {"type": "json_object"})
        self.assertNotIn("json_schema", str(request_body))
        self.assertNotIn("strict", str(request_body))
        self.assertNotIn("reasoning", request_body)
        self.assertNotIn("temperature", request_body)

    def test_workspace_responses_payload_can_omit_text_format_for_fallback(self):
        request_body = build_workspace_responses_request(
            model="gpt-4.1-mini",
            system_prompt="Responde unicamente con JSON valido.",
            user_payload={"maxSuggestions": 2},
            max_output_tokens=500,
            json_mode=False,
        )

        self.assertNotIn("text", request_body)
        self.assertNotIn("response_format", request_body)

    def test_openai_request_summary_does_not_include_prompt(self):
        request_body = build_workspace_responses_request(
            model="gpt-4.1-mini",
            system_prompt="Prompt secreto",
            user_payload={"localContext": ["texto"]},
            max_output_tokens=500,
            json_mode=True,
        )

        summary = openai_request_summary(request_body)

        self.assertEqual(summary["model"], "gpt-4.1-mini")
        self.assertEqual(summary["has_text_format"], True)
        self.assertEqual(summary["schema_name"], None)
        self.assertEqual(summary["input_type"], "array")
        self.assertNotIn("Prompt secreto", str(summary))

    def test_extract_json_object_reads_valid_json(self):
        parsed = extract_json_object('{"suggestions":[],"sources_used":[],"warnings":[]}')

        self.assertEqual(parsed["suggestions"], [])

    def test_extract_json_object_reads_json_with_surrounding_text(self):
        parsed = extract_json_object(
            'Texto antes {"suggestions":[{"type":"unknown","title":"T"}],"sources_used":[],"warnings":[]} texto despues'
        )

        self.assertEqual(parsed["suggestions"][0]["title"], "T")

    def test_normalize_ai_suggestions_fills_missing_fields_and_limits(self):
        suggestions, sources, warnings = normalize_ai_suggestions(
            {
                "suggestions": [
                    {"type": "unknown_type", "title": "Uno"},
                    {"type": "reflection_question", "content": "Dos"},
                ],
                "sources_used": [{"title": "Fuente"}],
                "warnings": ["revisar"],
            },
            1,
        )

        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0]["type"], "doctrinal_analysis")
        self.assertEqual(suggestions[0]["content"], "")
        self.assertEqual(suggestions[0]["source_title"], "")
        self.assertEqual(suggestions[0]["is_ai_generated"], True)
        self.assertEqual(suggestions[0]["confidence"], "medium")
        self.assertEqual(suggestions[0]["source_status"], "none")
        self.assertEqual(sources[0]["title"], "Fuente")
        self.assertEqual(warnings, ["revisar"])

    def test_normalize_ai_suggestions_warns_when_suggestions_is_not_array(self):
        suggestions, sources, warnings = normalize_ai_suggestions(
            {"suggestions": {"title": "Incorrecto"}, "sources_used": [], "warnings": []},
            3,
        )

        self.assertEqual(suggestions, [])
        self.assertEqual(sources, [])
        self.assertIn("La IA no devolvio una lista de sugerencias valida.", warnings)

    def test_workspace_response_json_empty_text_raises_controlled_error(self):
        with self.assertRaises(study_ai.StudyAiEmptyResponseError) as context:
            study_ai._extract_workspace_response_json({"output": []})

        self.assertEqual(getattr(context.exception, "stage"), "parse_response")

    def test_workspace_response_json_invalid_text_raises_unexpected_format(self):
        with self.assertRaises(study_ai.StudyAiUnexpectedFormatError) as context:
            study_ai._extract_workspace_response_json({"output_text": "no hay json"})

        self.assertEqual(getattr(context.exception, "stage"), "parse_response")

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
                            "message": "Invalid json_object",
                            "type": "invalid_request_error",
                            "param": "text.format",
                            "code": None,
                        }
                    },
                    request=httpx.Request("POST", url),
                )

        study_ai.httpx.AsyncClient = FakeAsyncClient
        try:
            with self.assertRaises(study_ai.StudyAiProviderInvalidRequestError) as context:
                asyncio.run(study_ai._post_openai_responses("sk-test", {"model": "gpt-4.1-mini"}))
            self.assertIn("Invalid json_object", str(context.exception))
            self.assertNotIn("sk-test", str(context.exception))
        finally:
            study_ai.httpx.AsyncClient = original_async_client

    def test_workspace_generation_handles_null_settings_empty_blocks_and_no_local_context(self):
        original_async_client = study_ai.httpx.AsyncClient
        original_get_settings = study_ai.get_settings

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def post(self, url, headers=None, json=None):
                return httpx.Response(
                    200,
                    json={
                        "output_text": (
                            '{"suggestions":[{"type":"doctrinal_analysis","title":"Idea","content":"Contenido"}],'
                            '"sources_used":[],"warnings":[]}'
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
            suggestions, sources_used, warnings, provider = asyncio.run(
                study_ai.generate_workspace_suggestions(
                    workspace={"id": "w1", "name": "Estudio", "settings": None},
                    blocks=[],
                    user_id="u1",
                    payload={"mode": "rapido", "maxSuggestions": 2},
                    local_context=[],
                )
            )

            self.assertEqual(provider, "openai_responses_json_object")
            self.assertEqual(suggestions[0]["type"], "doctrinal_analysis")
            self.assertEqual(suggestions[0]["source_status"], "none")
            self.assertEqual(sources_used, [])
            self.assertIn("No se encontraron suficientes fuentes locales", warnings[0])
        finally:
            study_ai.httpx.AsyncClient = original_async_client
            study_ai.get_settings = original_get_settings

    def test_workspace_generation_empty_suggestions_raises_controlled_error(self):
        original_async_client = study_ai.httpx.AsyncClient
        original_get_settings = study_ai.get_settings

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def post(self, url, headers=None, json=None):
                return httpx.Response(
                    200,
                    json={"output_text": '{"suggestions":[],"sources_used":[],"warnings":[]}'},
                    request=httpx.Request("POST", url),
                )

        study_ai.httpx.AsyncClient = FakeAsyncClient
        study_ai.get_settings = lambda: SimpleNamespace(
            openai_api_key="sk-test",
            openai_chat_model="gpt-4.1-mini",
            study_ai_max_suggestions=12,
        )
        try:
            with self.assertRaises(study_ai.StudyAiEmptyResponseError) as context:
                asyncio.run(
                    study_ai.generate_workspace_suggestions(
                        workspace={"id": "w1", "name": "Estudio", "settings": {"title": "Estudio"}},
                        blocks=[],
                        user_id="u1",
                        payload={"mode": "rapido", "maxSuggestions": 1},
                        local_context=[],
                    )
                )
            self.assertEqual(getattr(context.exception, "stage"), "normalize_response")
        finally:
            study_ai.httpx.AsyncClient = original_async_client
            study_ai.get_settings = original_get_settings

    def test_workspace_generation_suggestions_not_array_raises_controlled_error(self):
        original_async_client = study_ai.httpx.AsyncClient
        original_get_settings = study_ai.get_settings

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def post(self, url, headers=None, json=None):
                return httpx.Response(
                    200,
                    json={"output_text": '{"suggestions":{"title":"Incorrecto"},"sources_used":[],"warnings":[]}'},
                    request=httpx.Request("POST", url),
                )

        study_ai.httpx.AsyncClient = FakeAsyncClient
        study_ai.get_settings = lambda: SimpleNamespace(
            openai_api_key="sk-test",
            openai_chat_model="gpt-4.1-mini",
            study_ai_max_suggestions=12,
        )
        try:
            with self.assertRaises(study_ai.StudyAiEmptyResponseError):
                asyncio.run(
                    study_ai.generate_workspace_suggestions(
                        workspace={"id": "w1", "name": "Estudio", "settings": {"title": "Estudio"}},
                        blocks=[],
                        user_id="u1",
                        payload={"mode": "rapido", "maxSuggestions": 1},
                        local_context=[],
                    )
                )
        finally:
            study_ai.httpx.AsyncClient = original_async_client
            study_ai.get_settings = original_get_settings

    def test_workspace_generation_falls_back_to_plain_response_after_json_object_400(self):
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
                        json={"error": {"message": "json_object unsupported", "type": "invalid_request_error"}},
                        request=httpx.Request("POST", url),
                    )
                return httpx.Response(
                    200,
                    json={
                        "output_text": (
                            'Aqui va el JSON: {"suggestions":[{"type":"reflection_question","title":"Pregunta",'
                            '"content":"Que debo aplicar?"}],"sources_used":[],"warnings":[]}'
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
            suggestions, sources_used, warnings, provider = asyncio.run(
                study_ai.generate_workspace_suggestions(
                    workspace={"id": "w1", "name": "Estudio", "settings": {"title": "Estudio"}},
                    blocks=[],
                    user_id="u1",
                    payload={"mode": "rapido", "maxSuggestions": 1},
                    local_context=[],
                )
            )

            self.assertEqual(provider, "openai_responses_plain_json_fallback")
            self.assertEqual(suggestions[0]["type"], "reflection_question")
            self.assertEqual(suggestions[0]["quote_text"], "")
            self.assertEqual(sources_used, [])
            self.assertEqual(requests[0]["text"]["format"]["type"], "json_object")
            self.assertNotIn("text", requests[1])
            self.assertEqual(requests[0]["model"], "gpt-4.1-mini")
            self.assertIn("No se encontraron suficientes fuentes locales", warnings[0])
        finally:
            study_ai.httpx.AsyncClient = original_async_client
            study_ai.get_settings = original_get_settings

    def test_workspace_generation_raises_provider_invalid_after_final_400(self):
        original_async_client = study_ai.httpx.AsyncClient
        original_get_settings = study_ai.get_settings

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
                    json={"error": {"message": "bad request", "type": "invalid_request_error"}},
                    request=httpx.Request("POST", url),
                )

        study_ai.httpx.AsyncClient = FakeAsyncClient
        study_ai.get_settings = lambda: SimpleNamespace(
            openai_api_key="sk-test",
            openai_chat_model="gpt-4.1-mini",
            study_ai_max_suggestions=12,
        )
        try:
            with self.assertRaises(study_ai.StudyAiProviderInvalidRequestError) as context:
                asyncio.run(
                    study_ai.generate_workspace_suggestions(
                        workspace={"id": "w1", "name": "Estudio", "settings": {"title": "Estudio"}},
                        blocks=[],
                        user_id="u1",
                        payload={"mode": "rapido", "maxSuggestions": 1},
                        local_context=[],
                    )
                )
            self.assertEqual(getattr(context.exception, "stage"), "openai_request")
        finally:
            study_ai.httpx.AsyncClient = original_async_client
            study_ai.get_settings = original_get_settings


if __name__ == "__main__":
    unittest.main()
