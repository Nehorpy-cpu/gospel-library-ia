from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.logging import logger
from app.services.auth import get_request_auth_context, normalize_user_id, require_user
from app.services.db import get_conn
from app.services.scripture_refs import extract_scripture_refs, structured_scripture_refs
from app.services.source_filters import normalize_source_type

router = APIRouter(prefix="/api/talk-builder", tags=["talk-builder"], dependencies=[Depends(require_user)])
log = logger(__name__)


class TalkBuilderRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=240)
    audience: str = Field(default="General", min_length=2, max_length=160)
    durationMinutes: int = Field(default=10, ge=3, le=45)
    language: str | None = Field(default="es", max_length=16)
    workspaceId: str | None = None
    scriptureRefs: list[str] = Field(default_factory=list)
    sourceTypes: list[str] = Field(default_factory=list)

    @field_validator("scriptureRefs", "sourceTypes")
    @classmethod
    def clean_lists(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item and item.strip()]


class TalkDraftPayload(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    workspaceId: str | None = None
    outline: dict[str, Any] = Field(default_factory=dict)
    content: str | None = None
    scriptureRefs: list[str] = Field(default_factory=list)


def current_user_id(x_user_id: str | None = Header(default=None, alias="X-User-Id")) -> str:
    if not x_user_id:
        context = get_request_auth_context()
        if context:
            return context.user_id
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return normalize_user_id(x_user_id)


@router.post("/outline")
def generate_outline(payload: TalkBuilderRequest, user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = current_user_id(user_id)
    scripture_refs = _request_scripture_refs(payload)
    try:
        with get_conn() as conn:
            conn.row_factory = dict_row
            documents = _find_documents(conn, payload, scripture_refs, 10)
            saved_quotes = _find_saved_quotes(conn, user_id, payload, scripture_refs, 8)
    except Exception as exc:
        log.error("talk_builder_retrieval_failed", error=str(exc), topic=payload.topic)
        return {
            "status": "unavailable",
            "mode": "textual_fallback",
            "title": f"Bosquejo: {payload.topic}",
            "audience": payload.audience,
            "durationMinutes": payload.durationMinutes,
            "sections": [],
            "sources": [],
            "savedQuotes": [],
            "scriptureRefs": scripture_refs,
            "warnings": ["No fue posible leer fuentes reales desde PostgreSQL en este momento."],
        }

    sources = _source_payloads(documents)
    quotes = _quote_payloads(saved_quotes)
    if not sources and not quotes:
        return {
            "status": "unavailable",
            "mode": "textual_fallback",
            "title": f"Bosquejo: {payload.topic}",
            "audience": payload.audience,
            "durationMinutes": payload.durationMinutes,
            "sections": [],
            "sources": [],
            "savedQuotes": [],
            "scriptureRefs": scripture_refs,
            "warnings": [
                "No hay fuentes reales suficientes para generar un bosquejo con citas verificables.",
                "La busqueda semantica no es necesaria para este flujo; se uso busqueda textual basica.",
            ],
        }

    outline = _build_outline(payload, sources, quotes, scripture_refs)
    warnings = ["La busqueda semantica no esta disponible para el Talk Builder; se uso busqueda textual basica."]
    if not documents:
        warnings.append("No se encontraron documentos coincidentes; el bosquejo usa citas guardadas reales.")
    if not saved_quotes:
        warnings.append("No se encontraron citas guardadas para este tema.")
    return {**outline, "warnings": warnings}


@router.post("/drafts", status_code=status.HTTP_201_CREATED)
def save_draft(payload: TalkDraftPayload, user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = current_user_id(user_id)
    with get_conn() as conn:
        conn.row_factory = dict_row
        workspace_id = payload.workspaceId or _ensure_talk_workspace(conn, user_id)
        _require_workspace(conn, workspace_id, user_id)
        content = payload.content or _outline_to_markdown(payload.outline)
        row = conn.execute(
            """
            INSERT INTO study_notes (
              workspace_id, user_id, title, content, selected_text, selection_range,
              scripture_refs, color, position
            )
            VALUES (
              %(workspace_id)s, %(user_id)s, %(title)s, %(content)s, %(selected_text)s,
              %(selection_range)s, %(scripture_refs)s, %(color)s, %(position)s
            )
            RETURNING id::text, workspace_id::text, title, content, scripture_refs, created_at, updated_at
            """,
            {
                "workspace_id": workspace_id,
                "user_id": user_id,
                "title": payload.title,
                "content": content,
                "selected_text": None,
                "selection_range": Jsonb({}),
                "scripture_refs": Jsonb(payload.scriptureRefs),
                "color": "blue",
                "position": Jsonb({"type": "talk_builder_draft", "outline": payload.outline}),
            },
        ).fetchone()
        conn.commit()
    log.info("talk_builder_draft_saved", draft_id=row["id"], workspace_id=workspace_id, user_id=user_id)
    return {
        "status": "saved",
        "draftId": row["id"],
        "workspaceId": row["workspace_id"],
        "title": row["title"],
        "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
        "updatedAt": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


@router.get("/drafts")
def list_drafts(
    user_id: str | None = Header(default=None, alias="X-User-Id"),
    workspaceId: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
):
    user_id = current_user_id(user_id)
    where = ["user_id = %(user_id)s", "deleted_at IS NULL", "position->>'type' = 'talk_builder_draft'"]
    params: dict[str, Any] = {"user_id": user_id, "limit": limit}
    if workspaceId:
        where.append("workspace_id = %(workspace_id)s")
        params["workspace_id"] = workspaceId
    with get_conn() as conn:
        conn.row_factory = dict_row
        rows = conn.execute(
            f"""
            SELECT id::text, workspace_id::text, title, content, scripture_refs, position, created_at, updated_at
            FROM study_notes
            WHERE {" AND ".join(where)}
            ORDER BY updated_at DESC
            LIMIT %(limit)s
            """,
            params,
        ).fetchall()
    return {
        "items": [
            {
                "id": row["id"],
                "workspaceId": row["workspace_id"],
                "title": row["title"],
                "content": row["content"],
                "scriptureRefs": row["scripture_refs"] or [],
                "outline": (row["position"] or {}).get("outline"),
                "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
                "updatedAt": row["updated_at"].isoformat() if row["updated_at"] else None,
            }
            for row in rows
        ]
    }


def _request_scripture_refs(payload: TalkBuilderRequest) -> list[str]:
    refs = set(payload.scriptureRefs)
    refs.update(extract_scripture_refs(payload.topic))
    return sorted(refs)


def _find_documents(conn, payload: TalkBuilderRequest, scripture_refs: list[str], limit: int) -> list[dict]:
    terms = _search_terms(payload.topic, scripture_refs)
    source_types = [normalize_source_type(item) or item for item in payload.sourceTypes]
    params: dict[str, Any] = {"limit": limit}
    where = ["d.deleted_at IS NULL"]
    if payload.language:
        where.append("(d.language = %(language)s OR d.language IS NULL)")
        params["language"] = payload.language
    if source_types:
        where.append("(COALESCE(d.raw_metadata->>'source_type', s.key) = ANY(%(source_types)s) OR s.key = ANY(%(source_types)s))")
        params["source_types"] = source_types
    match_parts: list[str] = []
    score_parts: list[str] = []
    for index, term in enumerate(terms):
        key = f"term_{index}"
        params[key] = f"%{term}%"
        match_parts.append(
            f"(d.title ILIKE %({key})s OR coalesce(d.text, '') ILIKE %({key})s OR coalesce(d.author, '') ILIKE %({key})s "
            f"OR coalesce(d.category, '') ILIKE %({key})s OR d.tags::text ILIKE %({key})s OR d.scripture_refs::text ILIKE %({key})s)"
        )
        score_parts.append(
            f"CASE WHEN d.title ILIKE %({key})s OR d.scripture_refs::text ILIKE %({key})s THEN 3 "
            f"WHEN coalesce(d.text, '') ILIKE %({key})s THEN 1 ELSE 0 END"
        )
    if match_parts:
        where.append("(" + " OR ".join(match_parts) + ")")
    score_expr = " + ".join(score_parts) if score_parts else "0"
    rows = conn.execute(
        f"""
        SELECT
          d.id::text,
          d.title,
          d.author,
          d.language,
          d.canonical_url,
          COALESCE(d.raw_metadata->>'source_url', d.canonical_url) AS source_url,
          COALESCE(d.raw_metadata->>'source_type', s.key) AS source_type,
          s.name AS source_name,
          left(coalesce(d.text, ''), 900) AS excerpt,
          d.scripture_refs,
          ({score_expr}) AS match_score
        FROM documents d
        JOIN sources s ON s.id = d.source_id
        WHERE {" AND ".join(where)}
        ORDER BY match_score DESC, d.updated_at DESC
        LIMIT %(limit)s
        """,
        params,
    ).fetchall()
    if rows:
        return list(rows)
    fallback = conn.execute(
        """
        SELECT
          d.id::text,
          d.title,
          d.author,
          d.language,
          d.canonical_url,
          COALESCE(d.raw_metadata->>'source_url', d.canonical_url) AS source_url,
          COALESCE(d.raw_metadata->>'source_type', s.key) AS source_type,
          s.name AS source_name,
          left(coalesce(d.text, ''), 900) AS excerpt,
          d.scripture_refs,
          0 AS match_score
        FROM documents d
        JOIN sources s ON s.id = d.source_id
        WHERE d.deleted_at IS NULL
        ORDER BY d.updated_at DESC
        LIMIT %(limit)s
        """,
        {"limit": min(limit, 5)},
    ).fetchall()
    return list(fallback)


def _find_saved_quotes(conn, user_id: str, payload: TalkBuilderRequest, scripture_refs: list[str], limit: int) -> list[dict]:
    terms = _search_terms(payload.topic, scripture_refs)
    params: dict[str, Any] = {"user_id": user_id, "limit": limit}
    where = ["sc.user_id = %(user_id)s", "sc.deleted_at IS NULL"]
    if payload.workspaceId:
        where.append("sc.workspace_id = %(workspace_id)s")
        params["workspace_id"] = payload.workspaceId
    match_parts: list[str] = []
    for index, term in enumerate(terms):
        key = f"quote_term_{index}"
        params[key] = f"%{term}%"
        match_parts.append(
            f"(sc.quote ILIKE %({key})s OR coalesce(sc.selected_text, '') ILIKE %({key})s "
            f"OR coalesce(sc.source_title, '') ILIKE %({key})s OR coalesce(sc.source_author, '') ILIKE %({key})s "
            f"OR sc.scripture_refs::text ILIKE %({key})s)"
        )
    if match_parts:
        where.append("(" + " OR ".join(match_parts) + ")")
    return list(
        conn.execute(
            f"""
            SELECT
              sc.id::text,
              sc.workspace_id::text,
              sc.document_id::text,
              sc.chunk_id::text,
              sc.quote,
              sc.selected_text,
              sc.citation_url,
              sc.source_url,
              sc.source_title,
              sc.source_author,
              sc.location,
              sc.scripture_refs,
              sc.metadata,
              sc.updated_at
            FROM saved_citations sc
            WHERE {" AND ".join(where)}
            ORDER BY sc.updated_at DESC
            LIMIT %(limit)s
            """,
            params,
        ).fetchall()
    )


def _search_terms(topic: str, scripture_refs: list[str]) -> list[str]:
    words = [
        token.strip(".,;:!?()[]{}\"'").lower()
        for token in topic.split()
        if len(token.strip(".,;:!?()[]{}\"'")) > 2
    ]
    stopwords = {"para", "sobre", "con", "una", "unos", "las", "los", "del", "que", "the", "and", "about"}
    terms = [word for word in words if word not in stopwords][:8]
    terms.extend(scripture_refs)
    return terms or [topic]


def _source_payloads(rows: list[dict]) -> list[dict]:
    return [
        {
            "id": row["id"],
            "title": row["title"] or "Documento doctrinal",
            "author": row["author"],
            "language": row["language"],
            "sourceUrl": row["source_url"] or row["canonical_url"],
            "canonicalUrl": row["canonical_url"],
            "sourceType": normalize_source_type(row["source_type"]) or row["source_type"],
            "sourceName": row["source_name"],
            "excerpt": row["excerpt"],
            "scriptureRefs": row["scripture_refs"] or [],
            "scriptureRefsStructured": structured_scripture_refs(row["scripture_refs"] or []),
        }
        for row in rows
    ]


def _quote_payloads(rows: list[dict]) -> list[dict]:
    return [
        {
            "id": row["id"],
            "workspaceId": row["workspace_id"],
            "documentId": row["document_id"],
            "chunkId": row["chunk_id"],
            "quote": row["quote"],
            "selectedText": row["selected_text"],
            "citationUrl": row["citation_url"] or row["source_url"],
            "sourceUrl": row["source_url"],
            "sourceTitle": row["source_title"],
            "sourceAuthor": row["source_author"],
            "location": row["location"] or {},
            "scriptureRefs": row["scripture_refs"] or [],
            "metadata": row["metadata"] or {},
            "updatedAt": row["updated_at"].isoformat() if row["updated_at"] else None,
        }
        for row in rows
    ]


def _build_outline(payload: TalkBuilderRequest, sources: list[dict], quotes: list[dict], scripture_refs: list[str]) -> dict:
    section_count = 3 if payload.durationMinutes <= 8 else 4 if payload.durationMinutes <= 15 else 5
    section_titles = [
        f"Introduccion: {payload.topic}",
        "Principio doctrinal",
        "Aplicacion personal",
        "Testimonio y llamado a actuar",
        "Cierre con convenio",
    ][:section_count]
    citation_pool = _citation_pool(sources, quotes)
    sections = []
    for index, title in enumerate(section_titles):
        citations = [citation_pool[index % len(citation_pool)]] if citation_pool else []
        if citation_pool and len(citation_pool) > 1:
            second = citation_pool[(index + 1) % len(citation_pool)]
            if second["id"] != citations[0]["id"]:
                citations.append(second)
        source_line = citations[0]["title"] if citations else "una fuente real seleccionada"
        sections.append(
            {
                "id": f"section-{index + 1}",
                "title": title,
                "purpose": _section_purpose(index, payload.audience),
                "talkingPoints": [
                    f"Presentar el tema usando {source_line}.",
                    "Explicar la doctrina con lenguaje claro para la audiencia.",
                    "Conectar la ensenanza con una invitacion practica y verificable.",
                ],
                "suggestedQuote": citations[0].get("quote") or citations[0].get("snippet") if citations else None,
                "citations": citations,
            }
        )
    return {
        "status": "ready",
        "mode": "textual_fallback",
        "title": f"Bosquejo: {payload.topic}",
        "audience": payload.audience,
        "durationMinutes": payload.durationMinutes,
        "sections": sections,
        "sources": sources,
        "savedQuotes": quotes,
        "scriptureRefs": scripture_refs,
        "scriptureRefsStructured": structured_scripture_refs(scripture_refs),
    }


def _citation_pool(sources: list[dict], quotes: list[dict]) -> list[dict]:
    pool = [
        {
            "id": f"quote:{item['id']}",
            "type": "saved_quote",
            "documentId": item["documentId"],
            "title": item["sourceTitle"] or "Cita guardada",
            "author": item["sourceAuthor"],
            "url": item["citationUrl"] or item["sourceUrl"],
            "quote": item["quote"],
            "scriptureRefs": item["scriptureRefs"],
        }
        for item in quotes
    ]
    pool.extend(
        {
            "id": f"document:{item['id']}",
            "type": "document",
            "documentId": item["id"],
            "title": item["title"],
            "author": item["author"],
            "url": item["sourceUrl"] or item["canonicalUrl"],
            "snippet": item["excerpt"],
            "scriptureRefs": item["scriptureRefs"],
        }
        for item in sources
    )
    return pool


def _section_purpose(index: int, audience: str) -> str:
    purposes = [
        f"Abrir el tema de forma relevante para {audience}.",
        "Establecer el fundamento doctrinal con fuentes verificables.",
        "Mostrar como vivir el principio en decisiones cotidianas.",
        "Cerrar con testimonio, invitacion y esperanza.",
        "Conectar la aplicacion con convenios y discipulado continuo.",
    ]
    return purposes[index] if index < len(purposes) else purposes[-1]


def _ensure_talk_workspace(conn, user_id: str) -> str:
    row = conn.execute(
        """
        SELECT id::text
        FROM study_workspaces
        WHERE user_id = %(user_id)s AND name = %(name)s AND deleted_at IS NULL
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        {"user_id": user_id, "name": "Talk builder drafts"},
    ).fetchone()
    if row:
        return row["id"]
    created = conn.execute(
        """
        INSERT INTO study_workspaces (user_id, name, description, source_filters, settings)
        VALUES (%(user_id)s, %(name)s, %(description)s, %(source_filters)s, %(settings)s)
        RETURNING id::text
        """,
        {
            "user_id": user_id,
            "name": "Talk builder drafts",
            "description": "Borradores generados desde Talk Builder con fuentes reales.",
            "source_filters": Jsonb({"tool": "talk_builder"}),
            "settings": Jsonb({}),
        },
    ).fetchone()
    return created["id"]


def _require_workspace(conn, workspace_id: str, user_id: str) -> None:
    row = conn.execute(
        """
        SELECT id::text
        FROM study_workspaces
        WHERE id = %(workspace_id)s AND user_id = %(user_id)s AND deleted_at IS NULL
        """,
        {"workspace_id": workspace_id, "user_id": user_id},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study workspace not found")


def _outline_to_markdown(outline: dict[str, Any]) -> str:
    title = outline.get("title") or "Borrador de discurso"
    lines = [f"# {title}", ""]
    for section in outline.get("sections", []):
        lines.extend([f"## {section.get('title', 'Seccion')}", section.get("purpose", ""), ""])
        for point in section.get("talkingPoints", []):
            lines.append(f"- {point}")
        for citation in section.get("citations", []):
            label = citation.get("title") or citation.get("id")
            lines.append(f"- Fuente: {label}")
        lines.append("")
    return "\n".join(lines).strip()
