from __future__ import annotations

import hashlib
import json
from typing import Any

import httpx
from psycopg.rows import dict_row

from app.core.config import get_settings
from app.core.logging import logger
from app.services.privacy import sanitize_value

log = logger(__name__)

DEFAULT_BLOCKS = [
    "ai_doctrinal_analysis",
    "ai_reference",
    "name_meaning",
    "scripture_connection",
    "calling_application",
    "ai_quote",
    "reflection_question",
    "powerful_phrase",
    "manual_reference",
    "book_reference",
]

WORKSPACE_SUGGESTION_TYPES = [
    "doctrinal_analysis",
    "scripture_context",
    "name_meaning",
    "christ_connection",
    "scripture_connection",
    "quote",
    "manual_reference",
    "book_reference",
    "calling_application",
    "reflection_question",
    "powerful_phrase",
    "personal_application",
]

WORKSPACE_DEFAULT_TYPES = [
    "doctrinal_analysis",
    "scripture_context",
    "name_meaning",
    "christ_connection",
    "scripture_connection",
    "quote",
    "manual_reference",
    "calling_application",
    "reflection_question",
    "powerful_phrase",
]

FALLBACK_OPENAI_CHAT_MODEL = "gpt-4.1-mini"
WORKSPACE_SCHEMA_NAME = "study_ai_suggestions"
PROJECT_SCHEMA_NAME = "study_project_suggestions"

WORKSPACE_SUGGESTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["suggestions", "sources_used", "warnings"],
    "properties": {
        "suggestions": {
            "type": "array",
            "maxItems": 12,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "type",
                    "title",
                    "content",
                    "source_title",
                    "source_author",
                    "source_reference",
                    "source_url",
                    "quote_text",
                    "is_ai_generated",
                    "confidence",
                    "source_status",
                ],
                "properties": {
                    "type": {"type": "string", "enum": WORKSPACE_SUGGESTION_TYPES},
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "source_title": {"type": "string"},
                    "source_author": {"type": "string"},
                    "source_reference": {"type": "string"},
                    "source_url": {"type": "string"},
                    "quote_text": {"type": "string"},
                    "is_ai_generated": {"type": "boolean"},
                    "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
                    "source_status": {"type": "string", "enum": ["local", "suggested", "user_private", "none"]},
                },
            },
        },
        "sources_used": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title", "author", "url", "reference", "source_status"],
                "properties": {
                    "title": {"type": "string"},
                    "author": {"type": "string"},
                    "url": {"type": "string"},
                    "reference": {"type": "string"},
                    "source_status": {"type": "string", "enum": ["local", "suggested", "user_private", "none"]},
                },
            },
        },
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
}


class StudyAiConfigurationError(RuntimeError):
    pass


class StudyAiGenerationError(RuntimeError):
    pass


class StudyAiProviderInvalidRequestError(StudyAiGenerationError):
    pass


class StudyAiModelUnavailableError(StudyAiGenerationError):
    pass


class StudyAiUnexpectedFormatError(StudyAiGenerationError):
    pass


class StudyAiTimeoutError(StudyAiGenerationError):
    pass

SUGGESTION_SCHEMA: dict[str, Any] = {
    "name": "study_project_suggestions",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "suggestions": {
                "type": "array",
                "maxItems": 10,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "type": {"type": "string"},
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                        "quoteText": {"type": ["string", "null"]},
                        "sourceTitle": {"type": ["string", "null"]},
                        "sourceAuthor": {"type": ["string", "null"]},
                        "sourceUrl": {"type": ["string", "null"]},
                        "sourceReference": {"type": ["string", "null"]},
                        "sourceStatus": {
                            "type": "string",
                            "enum": ["local", "referencia_sugerida", "idea_relacionada", "usuario"],
                        },
                        "sources": {
                            "type": "array",
                            "items": {"type": "object", "additionalProperties": True},
                        },
                        "metadata": {"type": "object", "additionalProperties": True},
                    },
                    "required": [
                        "type",
                        "title",
                        "content",
                        "quoteText",
                        "sourceTitle",
                        "sourceAuthor",
                        "sourceUrl",
                        "sourceReference",
                        "sourceStatus",
                        "sources",
                        "metadata",
                    ],
                },
            },
            "warnings": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["suggestions", "warnings"],
    },
}


def prompt_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def load_local_context(conn, project: dict[str, Any], user_id: str, limit: int = 6) -> list[dict[str, Any]]:
    terms = _search_terms(
        " ".join(
            str(value or "")
            for value in (
                project.get("title"),
                project.get("scripture_reference"),
                project.get("personal_thought"),
                project.get("topic"),
            )
        )
    )
    context: list[dict[str, Any]] = []
    if terms:
        patterns = [f"%{term}%" for term in terms]
        rows = conn.execute(
            """
            SELECT d.id::text, d.title, d.author, d.canonical_url, s.name AS source_name,
                   left(coalesce(dc.text, d.text, ''), 700) AS excerpt
            FROM documents d
            JOIN sources s ON s.id = d.source_id
            LEFT JOIN LATERAL (
              SELECT text
              FROM document_chunks
              WHERE document_id = d.id AND text ILIKE ANY(%(patterns)s)
              ORDER BY chunk_index
              LIMIT 1
            ) dc ON TRUE
            WHERE d.deleted_at IS NULL
              AND (d.title ILIKE ANY(%(patterns)s)
                   OR coalesce(d.author, '') ILIKE ANY(%(patterns)s)
                   OR coalesce(d.text, '') ILIKE ANY(%(patterns)s)
                   OR dc.text IS NOT NULL)
            ORDER BY d.updated_at DESC
            LIMIT %(limit)s
            """,
            {"patterns": patterns, "limit": limit},
        ).fetchall()
        context.extend(
            {
                "kind": "library_document",
                "documentId": row["id"],
                "title": row["title"],
                "author": row["author"],
                "url": row["canonical_url"],
                "source": row["source_name"],
                "excerpt": row["excerpt"],
            }
            for row in rows
        )
    private_rows = conn.execute(
        """
        SELECT id::text, title, author, source_type, citation_text, personal_note, tags
        FROM user_private_sources
        WHERE user_id = %(user_id)s
        ORDER BY updated_at DESC
        LIMIT 4
        """,
        {"user_id": user_id},
    ).fetchall()
    context.extend(
        {
            "kind": "user_private_note",
            "sourceId": row["id"],
            "title": row["title"],
            "author": row["author"],
            "sourceType": row["source_type"],
            "citationText": row["citation_text"],
            "personalNote": row["personal_note"],
            "tags": row["tags"] or [],
        }
        for row in private_rows
    )
    previous_rows = conn.execute(
        """
        SELECT id::text, title, scripture_reference, topic
        FROM study_projects
        WHERE user_id = %(user_id)s AND archived_at IS NULL AND id <> %(project_id)s
        ORDER BY updated_at DESC
        LIMIT 4
        """,
        {"user_id": user_id, "project_id": project["id"]},
    ).fetchall()
    context.extend(
        {
            "kind": "previous_study",
            "studyProjectId": row["id"],
            "title": row["title"],
            "scriptureReference": row["scripture_reference"],
            "topic": row["topic"],
        }
        for row in previous_rows
    )
    return context


def load_workspace_local_context(
    conn,
    workspace: dict[str, Any],
    blocks: list[dict[str, Any]],
    user_id: str,
    limit: int = 8,
) -> list[dict[str, Any]]:
    settings = workspace.get("settings") or {}
    query_seed = " ".join(
        str(value or "")
        for value in (
            settings.get("title") or workspace.get("name"),
            settings.get("scriptureReference") or settings.get("mainReference") or workspace.get("description"),
            settings.get("personalThought"),
            settings.get("topic"),
            " ".join(str(block.get("title") or "") for block in blocks[:5]),
            "Jesucristo",
            "nombres" if _looks_like_name_study(settings.get("title") or workspace.get("name")) else "",
        )
    )
    terms = _search_terms(query_seed)
    context: list[dict[str, Any]] = []
    if terms:
        patterns = [f"%{term}%" for term in terms]
        rows = conn.execute(
            """
            SELECT d.id::text, d.title, d.author, d.canonical_url, s.name AS source_name,
                   left(coalesce(dc.text, d.text, ''), 900) AS excerpt
            FROM documents d
            JOIN sources s ON s.id = d.source_id
            LEFT JOIN LATERAL (
              SELECT text
              FROM document_chunks
              WHERE document_id = d.id AND text ILIKE ANY(%(patterns)s)
              ORDER BY chunk_index
              LIMIT 1
            ) dc ON TRUE
            WHERE d.deleted_at IS NULL
              AND (d.title ILIKE ANY(%(patterns)s)
                   OR coalesce(d.author, '') ILIKE ANY(%(patterns)s)
                   OR coalesce(d.text, '') ILIKE ANY(%(patterns)s)
                   OR dc.text IS NOT NULL)
            ORDER BY d.updated_at DESC
            LIMIT %(limit)s
            """,
            {"patterns": patterns, "limit": limit},
        ).fetchall()
        context.extend(
            {
                "kind": "library_document",
                "document_id": row["id"],
                "title": row["title"],
                "author": row["author"],
                "url": row["canonical_url"],
                "source": row["source_name"],
                "excerpt": row["excerpt"],
            }
            for row in rows
        )
    try:
        private_rows = conn.execute(
            """
            SELECT id::text, title, author, source_type, citation_text, personal_note, tags
            FROM user_private_sources
            WHERE user_id = %(user_id)s
            ORDER BY updated_at DESC
            LIMIT 4
            """,
            {"user_id": user_id},
        ).fetchall()
    except Exception:
        private_rows = []
    context.extend(
        {
            "kind": "user_private_note",
            "source_id": row["id"],
            "title": row["title"],
            "author": row["author"],
            "source_type": row["source_type"],
            "citation_text": row["citation_text"],
            "personal_note": row["personal_note"],
            "tags": row["tags"] or [],
        }
        for row in private_rows
    )
    return context


async def generate_workspace_suggestions(
    *,
    workspace: dict[str, Any],
    blocks: list[dict[str, Any]],
    user_id: str,
    payload: dict[str, Any],
    local_context: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str], str]:
    settings = get_settings()
    max_suggestions = min(max(int(payload.get("maxSuggestions") or 8), 1), 12)
    if settings.study_ai_max_suggestions:
        max_suggestions = min(max_suggestions, settings.study_ai_max_suggestions)
    warnings: list[str] = []
    sources_used = _sources_used(local_context)
    if not local_context:
        warnings.append("No se encontraron suficientes fuentes locales; las referencias no verificadas se marcaran como sugeridas.")
    if not settings.openai_api_key:
        raise StudyAiConfigurationError("La funcion de IA todavia no esta configurada en el servidor.")

    model = _openai_chat_model(settings.openai_chat_model)
    workspace_settings = workspace.get("settings") or {}
    title = workspace_settings.get("title") or workspace.get("name")
    scripture_reference = (
        workspace_settings.get("scriptureReference")
        or workspace_settings.get("mainReference")
        or workspace.get("description")
    )
    mode = payload.get("mode") or "rapido"
    user_prompt = _limit_text(str(payload.get("userPrompt") or payload.get("prompt") or ""), 1200)
    preferred_sources = payload.get("preferredSources") or []
    system_prompt = (
        "Eres un asistente de estudio doctrinal para uso personal de miembros de La Iglesia de Jesucristo "
        "de los Santos de los Ultimos Dias. Responde unicamente con JSON valido. No uses Markdown. No uses ```."
        " No agregues explicacion fuera del JSON. El JSON debe tener exactamente estas claves principales:"
        " suggestions, sources_used y warnings. Responde siempre en espanol. Sugiere bloques editables; no decidas por el usuario."
        " No inventes citas literales, paginas, capitulos, autores ni referencias exactas. "
        "Distingue escritura, cita literal, parafrasis, comentario doctrinal, reflexion personal y pregunta de reflexion. "
        "Usa quote_text solo cuando el texto literal este respaldado por el contexto local. Si una fuente no esta "
        "verificada localmente, usa source_status='suggested' y describe la idea como referencia sugerida. "
        "Incluye relacion con Jesucristo, preguntas de reflexion y aplicacion personal. Si hay callingContext, "
        "incluye aplicacion al llamamiento. Si el modo es nombres o el titulo trata sobre nombres, incluye significado doctrinal de nombres. "
        "Genera como maximo maxSuggestions. No guardes nada automaticamente; solo propone contenido editable. "
        "Si un dato de fuente no existe, usa string vacio. Usa source_status='none' o 'suggested' cuando corresponda."
    )
    user_payload = {
        "workspace": {
            "title": title,
            "scriptureReference": scripture_reference,
            "scriptureText": workspace_settings.get("scriptureText"),
            "personalThought": workspace_settings.get("personalThought"),
            "topic": workspace_settings.get("topic"),
            "callingContext": workspace_settings.get("callingContext"),
        },
        "existingBlocks": [
            {
                "type": block.get("type"),
                "title": block.get("title"),
                "content": _limit_text(str(block.get("content") or ""), 500),
            }
            for block in blocks[:8]
        ],
        "mode": mode,
        "preferredSources": preferred_sources,
        "userPrompt": user_prompt,
        "localContext": local_context[:10],
        "maxSuggestions": max_suggestions,
        "allowedTypes": WORKSPACE_SUGGESTION_TYPES,
        "requiredJsonShape": {
            "suggestions": [],
            "sources_used": [],
            "warnings": [],
        },
    }
    request_body = build_workspace_responses_request(
        model=model,
        system_prompt=system_prompt,
        user_payload=user_payload,
        max_output_tokens=2400,
        json_mode=True,
    )
    log.info("study_workspace_ai_openai_request", **openai_request_summary(request_body))
    try:
        data = await _post_openai_responses(settings.openai_api_key, request_body)
        parsed = _extract_response_json(data)
        provider = "openai_responses_json_object"
    except StudyAiProviderInvalidRequestError as exc:
        fallback_body = build_workspace_responses_request(
            model=model,
            system_prompt=system_prompt,
            user_payload=user_payload,
            max_output_tokens=2400,
            json_mode=False,
        )
        log.warning("study_workspace_ai_openai_json_object_request_invalid", error=str(exc), **openai_request_summary(request_body))
        log.info("study_workspace_ai_openai_request", **openai_request_summary(fallback_body))
        try:
            data = await _post_openai_responses(settings.openai_api_key, fallback_body)
            parsed = _extract_response_json(data)
            provider = "openai_responses_plain_json_fallback"
        except StudyAiProviderInvalidRequestError as fallback_exc:
            log.warning("study_workspace_ai_openai_plain_request_invalid", error=str(fallback_exc), **openai_request_summary(fallback_body))
            raise StudyAiUnexpectedFormatError("La IA respondio con un formato inesperado.") from fallback_exc
    except json.JSONDecodeError as exc:
        raise StudyAiUnexpectedFormatError("La IA respondio con un formato inesperado.") from exc

    try:
        normalized, normalized_sources, parsed_warnings = normalize_ai_suggestions(parsed, max_suggestions)
    except Exception as exc:
        raise StudyAiUnexpectedFormatError("La IA respondio con un formato inesperado.") from exc
    warnings.extend(parsed_warnings)
    if not normalized:
        warnings.append("La IA no devolvio sugerencias utiles para este estudio.")
    normalized_sources = normalized_sources or sources_used
    return normalized, normalized_sources or sources_used, warnings, provider


def build_workspace_responses_request(
    *,
    model: str,
    system_prompt: str,
    user_payload: dict[str, Any],
    max_output_tokens: int,
    json_mode: bool,
) -> dict[str, Any]:
    request_body = {
        "model": model,
        "store": False,
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
        "max_output_tokens": max_output_tokens,
    }
    if json_mode:
        request_body["text"] = {"format": {"type": "json_object"}}
    return request_body


async def generate_suggestions(
    *,
    project: dict[str, Any],
    user_id: str,
    payload: dict[str, Any],
    local_context: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str], str]:
    settings = get_settings()
    max_suggestions = min(int(payload.get("maxSuggestions") or 6), settings.study_ai_max_suggestions)
    block_types = payload.get("blockTypes") or DEFAULT_BLOCKS
    warnings: list[str] = []
    if not local_context:
        warnings.append("No se encontraron fuentes locales suficientes; las fuentes no verificadas se marcaran como referencia sugerida o idea relacionada.")
    if not settings.openai_api_key:
        warnings.append("OPENAI_API_KEY no esta configurada; se devolvieron sugerencias estructuradas de respaldo sin llamada externa.")
        return _fallback_suggestions(project, block_types, local_context, max_suggestions), warnings, "fallback_no_openai_key"

    model = _openai_chat_model(settings.openai_chat_model)
    system_prompt = (
        "Eres un asistente de estudio doctrinal para uso personal y familiar. "
        "Habla en espanol. Respeta la doctrina de La Iglesia de Jesucristo de los Santos de los Ultimos Dias. "
        "Distingue escritura, cita literal, parafrasis, comentario y reflexion. "
        "No inventes citas, paginas, capitulos ni autores. Si una cita exacta no esta en el contexto local, "
        "marca sourceStatus como referencia_sugerida o idea_relacionada y no uses quoteText literal. "
        "Incluye relacion con Jesucristo, aplicacion personal y preguntas de reflexion cuando corresponda. "
        "Devuelve bloques editables que el usuario pueda guardar, editar o descartar."
    )
    user_payload = {
        "studyProject": {
            "title": project["title"],
            "scriptureReference": project.get("scripture_reference"),
            "scriptureText": project.get("scripture_text"),
            "personalThought": project.get("personal_thought"),
            "topic": project.get("topic"),
            "callingContext": project.get("calling_context"),
        },
        "mode": payload.get("mode", "rapido"),
        "requestedBlockTypes": block_types,
        "preferredSources": payload.get("preferredSources") or [],
        "optionalPrompt": payload.get("prompt"),
        "localContext": local_context[:10],
        "maxSuggestions": max_suggestions,
    }
    request_body = {
        "model": model,
        "store": False,
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
        "text": {"format": _responses_json_schema_format(PROJECT_SCHEMA_NAME, SUGGESTION_SCHEMA["schema"])},
        "max_output_tokens": 2200,
    }
    try:
        data = await _post_openai_responses(settings.openai_api_key, request_body)
    except StudyAiGenerationError as exc:
        warnings.append(f"No se pudo generar con OpenAI; se uso respaldo local. Detalle seguro: {sanitize_value(str(exc))}")
        return _fallback_suggestions(project, block_types, local_context, max_suggestions), warnings, "fallback_openai_error"
    parsed = _extract_response_json(data)
    suggestions = parsed.get("suggestions") if isinstance(parsed, dict) else None
    if not isinstance(suggestions, list):
        warnings.append("OpenAI no devolvio sugerencias validas; se uso respaldo local.")
        return _fallback_suggestions(project, block_types, local_context, max_suggestions), warnings, "fallback_invalid_ai_response"
    warnings.extend(str(item) for item in parsed.get("warnings", []) if item)
    return suggestions[:max_suggestions], warnings, "openai_responses"


def _fallback_suggestions(
    project: dict[str, Any],
    block_types: list[str],
    local_context: list[dict[str, Any]],
    max_suggestions: int,
) -> list[dict[str, Any]]:
    context_title = local_context[0]["title"] if local_context else None
    source_status = "local" if local_context else "idea_relacionada"
    base = [
        {
            "type": "ai_doctrinal_analysis",
            "title": "Analisis doctrinal",
            "content": f"Explora como {project['title']} invita a recordar convenios, identidad espiritual y obediencia fiel.",
        },
        {
            "type": "ai_reference",
            "title": "Contexto de la escritura",
            "content": f"Usa {project.get('scripture_reference') or 'la escritura base'} como punto de partida y verifica el contexto en las escrituras canonicas.",
        },
        {
            "type": "name_meaning",
            "title": "Significado doctrinal de nombres",
            "content": "Considera los nombres como recordatorios espirituales de identidad, memoria familiar y convenios.",
        },
        {
            "type": "calling_application",
            "title": "Aplicacion para el llamamiento",
            "content": project.get("calling_context")
            or "Pregunta como este principio puede ayudarte a ministrar, ensenar o acompanar a otras personas.",
        },
        {
            "type": "ai_quote",
            "title": "Cita sugerida",
            "content": "Busca una cita corta y verificable antes de guardarla como cita literal; si no esta en tu biblioteca, tratala como referencia sugerida.",
        },
        {
            "type": "reflection_question",
            "title": "Pregunta de reflexion",
            "content": "Que nombres, convenios o experiencias debo recordar para acercarme mas a Jesucristo esta semana?",
        },
        {
            "type": "powerful_phrase",
            "title": "Frase poderosa",
            "content": "Recordar quienes nos precedieron puede ayudarnos a recordar a quien pertenecemos.",
        },
        {
            "type": "scripture_connection",
            "title": "Relacion con Jesucristo y otros pasajes",
            "content": "Busca conexiones con pasajes sobre recordar, convenios, padres fieles, identidad en Cristo y discipulado.",
        },
        {
            "type": "manual_reference",
            "title": "Manual doctrinal para revisar",
            "content": "Revisa manuales de Instituto o materiales oficiales relacionados con el pasaje antes de guardar una cita literal.",
        },
        {
            "type": "book_reference",
            "title": "Libro doctrinal para revisar",
            "content": "Considera libros doctrinales como referencia privada del estudio; guarda solo citas cortas verificadas por ti.",
        },
    ]
    wanted = set(block_types or DEFAULT_BLOCKS)
    filtered = [item for item in base if item["type"] in wanted] or base
    return [
        {
            **item,
            "quoteText": None,
            "sourceTitle": context_title,
            "sourceAuthor": local_context[0].get("author") if local_context else None,
            "sourceUrl": local_context[0].get("url") if local_context else None,
            "sourceReference": "Fuente local relacionada" if local_context else "Idea relacionada; requiere verificacion",
            "sourceStatus": source_status,
            "sources": local_context[:2],
            "metadata": {"generatedBy": "local_fallback"},
        }
        for item in filtered[:max_suggestions]
    ]


def _openai_chat_model(configured_model: str | None) -> str:
    model = (configured_model or "").strip()
    return model or FALLBACK_OPENAI_CHAT_MODEL


def _responses_json_schema_format(name: str, schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "name": name,
        "schema": schema,
        "strict": True,
    }


def openai_request_summary(request_body: dict[str, Any]) -> dict[str, Any]:
    text_format = ((request_body.get("text") or {}).get("format") or {}) if isinstance(request_body.get("text"), dict) else {}
    input_value = request_body.get("input")
    summary = {
        "model": request_body.get("model"),
        "has_text_format": bool(text_format),
        "schema_name": text_format.get("name") if isinstance(text_format, dict) else None,
        "input_type": "array" if isinstance(input_value, list) else type(input_value).__name__,
        "max_output_tokens": request_body.get("max_output_tokens"),
        "temperature": request_body.get("temperature"),
    }
    return summary


async def _post_openai_responses(api_key: str, request_body: dict[str, Any]) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                "https://api.openai.com/v1/responses",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=request_body,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        safe_error = _safe_openai_error(exc.response)
        message = safe_error.get("message") or str(exc)
        if _is_model_unavailable(safe_error):
            raise StudyAiModelUnavailableError(message) from exc
        if exc.response.status_code == 400:
            raise StudyAiProviderInvalidRequestError(json.dumps(safe_error, ensure_ascii=False)) from exc
        raise StudyAiGenerationError(json.dumps(safe_error, ensure_ascii=False)) from exc
    except httpx.TimeoutException as exc:
        raise StudyAiTimeoutError("La IA tardo demasiado en responder.") from exc
    except Exception as exc:
        raise StudyAiGenerationError(
            f"No se pudo generar informacion con IA. Detalle seguro: {sanitize_value(str(exc))}"
        ) from exc


def _safe_openai_error(response: httpx.Response) -> dict[str, Any]:
    safe: dict[str, Any] = {"status_code": response.status_code}
    try:
        body = response.json()
    except Exception:
        safe["message"] = sanitize_value(response.text[:500])
        return safe
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict):
        for key in ("message", "type", "param", "code"):
            value = error.get(key)
            safe[key] = sanitize_value(str(value)) if value is not None else None
    else:
        safe["message"] = sanitize_value(str(body)[:500])
    return safe


def _is_model_unavailable(error: dict[str, Any]) -> bool:
    values = " ".join(str(error.get(key) or "") for key in ("message", "type", "param", "code")).casefold()
    return "model_not_found" in values or "does not exist" in values or "do not have access" in values


def extract_response_text(data: dict[str, Any]) -> str:
    output_text = data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text
    content = data.get("content")
    if isinstance(content, str) and content.strip():
        return content
    for output in data.get("output", []) or []:
        if not isinstance(output, dict):
            continue
        output_content = output.get("content")
        if isinstance(output_content, str) and output_content.strip():
            return output_content
        for item in output_content or []:
            if not isinstance(item, dict):
                continue
            text = item.get("text") or item.get("content")
            if isinstance(text, str) and text.strip():
                return text
    return ""


def _extract_response_json(data: dict[str, Any]) -> dict[str, Any]:
    text = extract_response_text(data).strip()
    if not text:
        return {}
    return extract_json_object(text)


def extract_json_object(text: str) -> dict[str, Any]:
    clean = text.strip()
    if clean.startswith("```"):
        lines = clean.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        clean = "\n".join(lines).strip()
    try:
        value = json.loads(clean)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        pass
    start = clean.find("{")
    if start < 0:
        raise json.JSONDecodeError("No JSON object found", clean, 0)
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(clean)):
        char = clean[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                value = json.loads(clean[start : index + 1])
                return value if isinstance(value, dict) else {}
    raise json.JSONDecodeError("No complete JSON object found", clean, start)



def _normalize_workspace_suggestion(item: dict[str, Any]) -> dict[str, Any]:
    suggestion_type = str(item.get("type") or "doctrinal_analysis")
    if suggestion_type not in WORKSPACE_SUGGESTION_TYPES:
        suggestion_type = "doctrinal_analysis"
    source_status = str(item.get("source_status") or "none")
    if source_status not in {"local", "suggested", "user_private", "none"}:
        source_status = "suggested"
    confidence = str(item.get("confidence") or "medium")
    if confidence not in {"low", "medium", "high"}:
        confidence = "medium"
    quote_text = item.get("quote_text")
    if source_status != "local" and quote_text:
        quote_text = ""
    return {
        "type": suggestion_type,
        "title": str(item.get("title") or "Sugerencia doctrinal")[:240],
        "content": str(item.get("content") or ""),
        "source_title": str(item.get("source_title") or ""),
        "source_author": str(item.get("source_author") or ""),
        "source_reference": str(item.get("source_reference") or ""),
        "source_url": str(item.get("source_url") or ""),
        "quote_text": str(quote_text or ""),
        "is_ai_generated": True,
        "confidence": confidence,
        "source_status": source_status,
    }


def normalize_ai_suggestions(raw: Any, max_suggestions: int) -> tuple[list[dict[str, Any]], list[dict[str, str]], list[str]]:
    if not isinstance(raw, dict):
        return [], [], ["La IA devolvio una respuesta vacia o invalida."]
    raw_suggestions = raw.get("suggestions")
    raw_sources = raw.get("sources_used")
    raw_warnings = raw.get("warnings")
    suggestions = [
        _normalize_workspace_suggestion(item)
        for item in (raw_suggestions if isinstance(raw_suggestions, list) else [])
        if isinstance(item, dict)
    ][:max_suggestions]
    sources = _normalize_workspace_sources(raw_sources if isinstance(raw_sources, list) else [])
    warnings = [str(item) for item in (raw_warnings if isinstance(raw_warnings, list) else []) if item]
    return suggestions, sources, warnings


def _normalize_workspace_sources(items: list[Any]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in items[:10]:
        if not isinstance(item, dict):
            continue
        source_status = str(item.get("source_status") or item.get("sourceStatus") or "none")
        if source_status not in {"local", "suggested", "user_private", "none"}:
            source_status = "none"
        normalized.append(
            {
                "title": str(item.get("title") or ""),
                "author": str(item.get("author") or ""),
                "url": str(item.get("url") or ""),
                "reference": str(item.get("reference") or item.get("source") or item.get("kind") or ""),
                "source_status": source_status,
            }
        )
    return normalized


def _sources_used(local_context: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for item in local_context[:10]:
        sources.append(
            {
                "title": str(item.get("title") or ""),
                "author": str(item.get("author") or ""),
                "url": str(item.get("url") or ""),
                "reference": str(item.get("source") or item.get("source_type") or item.get("kind") or ""),
                "source_status": "user_private" if item.get("kind") == "user_private_note" else "local",
            }
        )
    return sources


def _limit_text(value: str, limit: int) -> str:
    clean = " ".join(value.split())
    return clean[:limit]


def _looks_like_name_study(value: str | None) -> bool:
    if not value:
        return False
    lowered = value.casefold()
    return "nombre" in lowered or "nombres" in lowered


def _search_terms(value: str) -> list[str]:
    stopwords = {"con", "para", "por", "que", "los", "las", "una", "del", "como", "este", "esta"}
    cleaned = value.replace(",", " ").replace(";", " ").replace(".", " ").replace(":", " ")
    return [token for token in cleaned.split() if len(token) > 2 and token.casefold() not in stopwords][:8]
