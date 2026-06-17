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


def _search_terms(value: str) -> list[str]:
    stopwords = {"con", "para", "por", "que", "los", "las", "una", "del", "como", "este", "esta"}
    cleaned = value.replace(",", " ").replace(";", " ").replace(".", " ").replace(":", " ")
    return [token for token in cleaned.split() if len(token) > 2 and token.casefold() not in stopwords][:8]
