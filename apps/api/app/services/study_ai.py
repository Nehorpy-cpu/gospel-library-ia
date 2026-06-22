from __future__ import annotations

import hashlib
import json
from typing import Any

import httpx
from psycopg.rows import dict_row

from app.core.config import get_settings
from app.services.privacy import sanitize_value

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

WORKSPACE_SUGGESTION_SCHEMA: dict[str, Any] = {
    "name": "study_workspace_suggestions",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "suggestions": {
                "type": "array",
                "maxItems": 12,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "type": {"type": "string", "enum": WORKSPACE_SUGGESTION_TYPES},
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                        "source_title": {"type": ["string", "null"]},
                        "source_author": {"type": ["string", "null"]},
                        "source_reference": {"type": ["string", "null"]},
                        "source_url": {"type": ["string", "null"]},
                        "quote_text": {"type": ["string", "null"]},
                        "is_ai_generated": {"type": "boolean"},
                        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
                        "source_status": {"type": "string", "enum": ["local", "suggested", "user_private", "none"]},
                    },
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
                },
            },
            "warnings": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["suggestions", "warnings"],
    },
}


class StudyAiConfigurationError(RuntimeError):
    pass


class StudyAiGenerationError(RuntimeError):
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
        "de los Santos de los Ultimos Dias. Responde siempre en espanol. Sugiere bloques editables; no decidas "
        "por el usuario. No inventes citas literales, paginas, capitulos, autores ni referencias exactas. "
        "Distingue escritura, cita literal, parafrasis, comentario doctrinal, reflexion personal y pregunta de reflexion. "
        "Usa quote_text solo cuando el texto literal este respaldado por el contexto local. Si una fuente no esta "
        "verificada localmente, usa source_status='suggested' y describe la idea como referencia sugerida. "
        "Incluye relacion con Jesucristo, preguntas de reflexion y aplicacion personal. Si hay callingContext, "
        "incluye aplicacion al llamamiento. Si el modo es nombres o el titulo trata sobre nombres, incluye significado doctrinal de nombres."
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
    }
    request_body = {
        "model": settings.openai_chat_model,
        "store": False,
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
        "text": {
            "verbosity": "low",
            "format": {
                "type": "json_schema",
                "json_schema": WORKSPACE_SUGGESTION_SCHEMA,
            },
        },
        "reasoning": {"effort": "low"},
    }
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                "https://api.openai.com/v1/responses",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json=request_body,
            )
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        raise StudyAiGenerationError(
            f"No se pudo generar informacion con IA. Detalle seguro: {sanitize_value(str(exc))}"
        ) from exc

    parsed = _extract_response_json(data)
    suggestions = parsed.get("suggestions") if isinstance(parsed, dict) else None
    if not isinstance(suggestions, list):
        raise StudyAiGenerationError("OpenAI no devolvio sugerencias validas.")
    warnings.extend(str(item) for item in parsed.get("warnings", []) if item)
    normalized = [_normalize_workspace_suggestion(item) for item in suggestions[:max_suggestions] if isinstance(item, dict)]
    return normalized, sources_used, warnings, "openai_responses"


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
        "model": settings.openai_chat_model,
        "store": False,
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
        "text": {
            "verbosity": "low",
            "format": {
                "type": "json_schema",
                "json_schema": SUGGESTION_SCHEMA,
            },
        },
        "reasoning": {"effort": "low"},
    }
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                "https://api.openai.com/v1/responses",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json=request_body,
            )
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
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


def _extract_response_json(data: dict[str, Any]) -> dict[str, Any]:
    if isinstance(data.get("output_text"), str):
        return json.loads(data["output_text"])
    for output in data.get("output", []) or []:
        for content in output.get("content", []) or []:
            if content.get("type") in {"output_text", "text"} and isinstance(content.get("text"), str):
                return json.loads(content["text"])
    return {}


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
        quote_text = None
    return {
        "type": suggestion_type,
        "title": str(item.get("title") or "Sugerencia doctrinal")[:240],
        "content": str(item.get("content") or ""),
        "source_title": item.get("source_title"),
        "source_author": item.get("source_author"),
        "source_reference": item.get("source_reference"),
        "source_url": item.get("source_url"),
        "quote_text": quote_text,
        "is_ai_generated": True,
        "confidence": confidence,
        "source_status": source_status,
    }


def _sources_used(local_context: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for item in local_context[:10]:
        sources.append(
            {
                "kind": item.get("kind"),
                "title": item.get("title"),
                "author": item.get("author"),
                "url": item.get("url"),
                "source": item.get("source") or item.get("source_type"),
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
