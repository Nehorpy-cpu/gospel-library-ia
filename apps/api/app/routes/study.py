from typing import Any, Literal

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.config import get_settings
from app.core.logging import logger
from app.services.auth import get_request_auth_context, normalize_user_id, require_study_user
from app.services.db import get_conn
from app.services.qdrant_admin import QdrantAdmin
from app.services.rate_limit import RateLimiter
from app.services.source_filters import normalize_source_type, source_type_aliases
from app.services.study_ai import (
    StudyAiConfigurationError,
    StudyAiGenerationError,
    generate_workspace_suggestions,
    load_workspace_local_context,
)

router = APIRouter(prefix="/api/study-workspaces", tags=["study"], dependencies=[Depends(require_study_user)])
alias_router = APIRouter(prefix="/api/study", tags=["study"], dependencies=[Depends(require_study_user)])
log = logger(__name__)
limiter = RateLimiter()


class WorkspacePayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def fill_name_from_title(cls, data):
        if isinstance(data, dict) and not data.get("name"):
            title = data.get("title")
            if isinstance(title, str) and title.strip():
                return {**data, "name": title.strip()}
        return data

    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    userId: str | None = Field(default=None, validation_alias=AliasChoices("userId", "user_id"))
    sourceFilters: dict[str, Any] = Field(default_factory=dict, validation_alias=AliasChoices("sourceFilters", "source_filters"))
    settings: dict[str, Any] = Field(default_factory=dict)
    title: str | None = Field(default=None, max_length=200)
    scriptureReference: str | None = Field(default=None, max_length=240, validation_alias=AliasChoices("scriptureReference", "scripture_reference"))
    scriptureText: str | None = Field(default=None, validation_alias=AliasChoices("scriptureText", "scripture_text"))
    personalThought: str | None = Field(default=None, validation_alias=AliasChoices("personalThought", "personal_thought"))
    topic: str | None = Field(default=None, max_length=160)
    callingContext: str | None = Field(default=None, max_length=240, validation_alias=AliasChoices("callingContext", "calling_context"))


class WorkspaceUpdatePayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    sourceFilters: dict[str, Any] | None = Field(default=None, validation_alias=AliasChoices("sourceFilters", "source_filters"))
    settings: dict[str, Any] | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    scriptureReference: str | None = Field(default=None, max_length=240, validation_alias=AliasChoices("scriptureReference", "scripture_reference"))
    scriptureText: str | None = Field(default=None, validation_alias=AliasChoices("scriptureText", "scripture_text"))
    personalThought: str | None = Field(default=None, validation_alias=AliasChoices("personalThought", "personal_thought"))
    topic: str | None = Field(default=None, max_length=160)
    callingContext: str | None = Field(default=None, max_length=240, validation_alias=AliasChoices("callingContext", "calling_context"))


class SourceFilterPayload(BaseModel):
    sourceKey: str | None = Field(default=None, max_length=100)
    language: str | None = Field(default=None, max_length=16)
    author: str | None = None
    category: str | None = None
    tags: list[str] = Field(default_factory=list)


class NotePayload(BaseModel):
    documentId: str | None = None
    chunkId: str | None = None
    title: str | None = Field(default=None, max_length=240)
    content: str = Field(min_length=1)
    selectedText: str | None = None
    selectionRange: dict[str, Any] = Field(default_factory=dict)
    scriptureRefs: list[str] = Field(default_factory=list)
    color: str = Field(default="yellow", max_length=32)
    position: dict[str, Any] = Field(default_factory=dict)


class NoteUpdatePayload(BaseModel):
    documentId: str | None = None
    chunkId: str | None = None
    title: str | None = Field(default=None, max_length=240)
    content: str | None = Field(default=None, min_length=1)
    selectedText: str | None = None
    selectionRange: dict[str, Any] | None = None
    scriptureRefs: list[str] | None = None
    color: str | None = Field(default=None, max_length=32)
    position: dict[str, Any] | None = None


class HighlightPayload(BaseModel):
    documentId: str
    chunkId: str | None = None
    noteId: str | None = None
    startChar: int = Field(ge=0)
    endChar: int = Field(gt=0)
    selectedText: str = Field(min_length=1)
    scriptureRefs: list[str] = Field(default_factory=list)
    color: str = Field(default="yellow", max_length=32)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("endChar")
    @classmethod
    def end_after_start(cls, value: int, info):
        start = info.data.get("startChar", 0)
        if value <= start:
            raise ValueError("endChar must be greater than startChar")
        return value


class HighlightUpdatePayload(BaseModel):
    chunkId: str | None = None
    noteId: str | None = None
    startChar: int | None = Field(default=None, ge=0)
    endChar: int | None = Field(default=None, gt=0)
    selectedText: str | None = Field(default=None, min_length=1)
    scriptureRefs: list[str] | None = None
    color: str | None = Field(default=None, max_length=32)
    metadata: dict[str, Any] | None = None


class CitationPayload(BaseModel):
    documentId: str
    chunkId: str | None = None
    quote: str = Field(min_length=1)
    selectedText: str | None = None
    citationUrl: str | None = None
    location: dict[str, Any] = Field(default_factory=dict)
    scriptureRefs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CitationUpdatePayload(BaseModel):
    quote: str | None = Field(default=None, min_length=1)
    selectedText: str | None = None
    citationUrl: str | None = None
    location: dict[str, Any] | None = None
    scriptureRefs: list[str] | None = None
    metadata: dict[str, Any] | None = None


class PostItPayload(BaseModel):
    documentId: str | None = None
    content: str = Field(min_length=1)
    color: str = Field(default="yellow", max_length=32)
    position: dict[str, Any] = Field(default_factory=dict)
    sourceFilters: dict[str, Any] = Field(default_factory=dict)
    pinned: bool = False


class PostItUpdatePayload(BaseModel):
    documentId: str | None = None
    content: str | None = Field(default=None, min_length=1)
    color: str | None = Field(default=None, max_length=32)
    position: dict[str, Any] | None = None
    sourceFilters: dict[str, Any] | None = None
    pinned: bool | None = None


StudyBlockType = str


class BlockPayload(BaseModel):
    type: StudyBlockType = Field(default="personal_note", max_length=80)
    title: str = Field(default="Nota", max_length=240)
    content: str = ""
    quoteText: str | None = None
    sourceTitle: str | None = Field(default=None, max_length=300)
    sourceAuthor: str | None = Field(default=None, max_length=240)
    sourceReference: str | None = Field(default=None, max_length=300)
    sourceUrl: str | None = None
    isAiGenerated: bool = False
    sortOrder: int | None = None


class BlockUpdatePayload(BaseModel):
    type: StudyBlockType | None = Field(default=None, max_length=80)
    title: str | None = Field(default=None, max_length=240)
    content: str | None = None
    quoteText: str | None = None
    sourceTitle: str | None = Field(default=None, max_length=300)
    sourceAuthor: str | None = Field(default=None, max_length=240)
    sourceReference: str | None = Field(default=None, max_length=300)
    sourceUrl: str | None = None
    isAiGenerated: bool | None = None
    sortOrder: int | None = None


WorkspaceAiMode = Literal["rapido", "profundo", "citas", "manuales", "nombres", "llamamiento"]
WorkspaceAiSuggestionType = Literal[
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
WorkspaceAiSourceStatus = Literal["local", "suggested", "user_private", "none"]
WorkspaceAiConfidence = Literal["low", "medium", "high"]


class WorkspaceAiSuggestPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    mode: WorkspaceAiMode = "rapido"
    userPrompt: str | None = Field(default=None, max_length=1200, validation_alias=AliasChoices("userPrompt", "user_prompt"))
    preferredSources: list[str] = Field(default_factory=list, validation_alias=AliasChoices("preferredSources", "preferred_sources"))
    maxSuggestions: int = Field(default=8, ge=1, le=12, validation_alias=AliasChoices("maxSuggestions", "max_suggestions"))


class WorkspaceAiSuggestion(BaseModel):
    type: WorkspaceAiSuggestionType
    title: str
    content: str
    source_title: str | None = None
    source_author: str | None = None
    source_reference: str | None = None
    source_url: str | None = None
    quote_text: str | None = None
    is_ai_generated: bool = True
    confidence: WorkspaceAiConfidence = "medium"
    source_status: WorkspaceAiSourceStatus = "none"


class WorkspaceAiSuggestResponse(BaseModel):
    suggestions: list[WorkspaceAiSuggestion]
    sources_used: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def current_user_id(x_user_id: str | None = Header(default=None, alias="X-User-Id")) -> str:
    if not x_user_id:
        context = get_request_auth_context()
        if context:
            return context.user_id
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return normalize_user_id(x_user_id)


def _ensure_payload_user(payload_user_id: str | None, user_id: str) -> None:
    if payload_user_id and payload_user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Payload userId does not match authenticated user")


def _require_workspace(conn, workspace_id: str, user_id: str) -> dict:
    row = conn.execute(
        """
        SELECT id::text, user_id::text, name, description, source_filters, settings, created_at, updated_at
        FROM study_workspaces
        WHERE id = %(workspace_id)s AND user_id = %(user_id)s AND deleted_at IS NULL
        """,
        {"workspace_id": workspace_id, "user_id": user_id},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study workspace not found")
    return row


def _resource_belongs_to_user(conn, table: str, resource_id: str, workspace_id: str, user_id: str) -> dict:
    allowed = {
        "study_notes",
        "study_highlights",
        "saved_citations",
        "post_its",
        "study_workspace_sources",
    }
    if table not in allowed:
        raise ValueError(f"Unsupported table {table}")
    row = conn.execute(
        f"""
        SELECT *
        FROM {table}
        WHERE id = %(resource_id)s
          AND workspace_id = %(workspace_id)s
          AND user_id = %(user_id)s
          AND deleted_at IS NULL
        """,
        {"resource_id": resource_id, "workspace_id": workspace_id, "user_id": user_id},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    return row


def _filter_sql(
    *,
    document_id: str | None = None,
    source_type: str | None = None,
    topic: str | None = None,
    scripture_ref: str | None = None,
    artifact_alias: str = "item",
) -> tuple[list[str], dict[str, Any], bool]:
    where: list[str] = []
    params: dict[str, Any] = {}
    needs_document_join = bool(source_type or topic or scripture_ref)
    if document_id:
        where.append(f"{artifact_alias}.document_id = %(document_id)s")
        params["document_id"] = document_id
    if source_type:
        where.append("(COALESCE(d.raw_metadata->>'source_type', s.key) = ANY(%(source_types)s) OR s.key = ANY(%(source_types)s))")
        params["source_types"] = source_type_aliases(source_type)
    if topic:
        where.append(
            "(d.category ILIKE %(topic)s OR d.tags::text ILIKE %(topic)s OR d.raw_metadata::text ILIKE %(topic)s)"
        )
        params["topic"] = f"%{topic}%"
    if scripture_ref:
        where.append(f"({artifact_alias}.scripture_refs::text ILIKE %(scripture_ref)s OR d.scripture_refs::text ILIKE %(scripture_ref)s)")
        params["scripture_ref"] = f"%{scripture_ref}%"
    return where, params, needs_document_join


def _document_attribution(conn, document_id: str) -> dict:
    row = conn.execute(
        """
        SELECT
          d.title,
          d.author,
          d.canonical_url,
          COALESCE(d.raw_metadata->>'source_url', d.canonical_url) AS source_url,
          COALESCE(d.raw_metadata->>'source_type', s.key) AS source_type,
          s.name AS source_name
        FROM documents d
        JOIN sources s ON s.id = d.source_id
        WHERE d.id = %(document_id)s
        """,
        {"document_id": document_id},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return row


def _qdrant_points_count() -> int:
    try:
        return int(QdrantAdmin().ensure_collection().get("vectors") or 0)
    except Exception:
        return 0


def _document_columns(conn) -> set[str]:
    return {
        row["column_name"] if isinstance(row, dict) else row[0]
        for row in conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'documents'"
        ).fetchall()
    }


def _workspace_related_query(workspace: dict) -> tuple[str, list[str], list[str]]:
    source_filters = workspace.get("source_filters") or {}
    settings = workspace.get("settings") or {}
    query_parts = [
        workspace.get("name"),
        workspace.get("description"),
        settings.get("title"),
        settings.get("mainReference"),
        settings.get("referenceType"),
    ]
    query = " ".join(str(part).strip() for part in query_parts if part).strip() or workspace["name"]

    source_values: list[str] = []
    raw_source = source_filters.get("sourceType") or source_filters.get("source_key") or source_filters.get("sourceKey")
    if isinstance(raw_source, str) and raw_source:
        source_values.extend(source_type_aliases(raw_source))

    languages: list[str] = []
    raw_language = settings.get("language") or source_filters.get("language")
    if isinstance(raw_language, str) and raw_language:
        languages.append(raw_language)

    return query, sorted(set(source_values)), sorted(set(languages))


def _workspace_settings_from_payload(payload: WorkspacePayload) -> dict[str, Any]:
    settings = dict(payload.settings or {})
    if payload.title is not None:
        settings["title"] = payload.title
    if payload.scriptureReference is not None:
        settings["scriptureReference"] = payload.scriptureReference
        settings["mainReference"] = payload.scriptureReference
        settings["referenceType"] = "scripture"
    if payload.scriptureText is not None:
        settings["scriptureText"] = payload.scriptureText
    if payload.personalThought is not None:
        settings["personalThought"] = payload.personalThought
    if payload.topic is not None:
        settings["topic"] = payload.topic
    if payload.callingContext is not None:
        settings["callingContext"] = payload.callingContext
    return settings


def _workspace_update_settings(payload: WorkspaceUpdatePayload) -> dict[str, Any] | None:
    if payload.settings is None and all(
        value is None
        for value in (
            payload.title,
            payload.scriptureReference,
            payload.scriptureText,
            payload.personalThought,
            payload.topic,
            payload.callingContext,
        )
    ):
        return None
    settings = dict(payload.settings or {})
    if payload.title is not None:
        settings["title"] = payload.title
    if payload.scriptureReference is not None:
        settings["scriptureReference"] = payload.scriptureReference
        settings["mainReference"] = payload.scriptureReference
        settings["referenceType"] = "scripture"
    if payload.scriptureText is not None:
        settings["scriptureText"] = payload.scriptureText
    if payload.personalThought is not None:
        settings["personalThought"] = payload.personalThought
    if payload.topic is not None:
        settings["topic"] = payload.topic
    if payload.callingContext is not None:
        settings["callingContext"] = payload.callingContext
    return settings


def _semantic_related(workspace: dict, limit: int) -> dict | None:
    if _qdrant_points_count() <= 0:
        return None

    query, source_values, languages = _workspace_related_query(workspace)
    payload: dict[str, Any] = {
        "query": query,
        "limit": limit,
        "filters": {
            "source_keys": source_values,
            "languages": languages,
        },
    }
    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(f"{get_settings().rag_api_url}/search", json=payload)
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        log.warning("study_related_semantic_failed", workspace_id=workspace["id"], error=str(exc))
        return None

    results = [
        {
            "id": item.get("document_id") or item.get("chunk_id"),
            "chunkId": item.get("chunk_id"),
            "title": item.get("title"),
            "author": item.get("author"),
            "sourceType": item.get("source_key"),
            "sourceUrl": item.get("canonical_url"),
            "language": item.get("language"),
            "excerpt": item.get("snippet"),
            "relevanceScore": item.get("score"),
        }
        for item in data.get("results", [])
    ]
    return {
        "workspaceId": workspace["id"],
        "mode": data.get("mode") or "semantic",
        "warning": None,
        "query": query,
        "results": results,
    }


def _textual_related(workspace: dict, limit: int) -> dict:
    query, source_values, languages = _workspace_related_query(workspace)
    terms = [
        token
        for token in query.replace(",", " ").replace(";", " ").split()
        if len(token) > 2
    ][:8]
    with get_conn() as conn:
        conn.row_factory = dict_row
        columns = _document_columns(conn)
        metadata_column = "raw_metadata" if "raw_metadata" in columns else "metadata"
        text_column = "text" if "text" in columns else "content_text"
        author_expr = "d.author" if "author" in columns else "NULL"
        deleted_filter = "d.deleted_at IS NULL" if "deleted_at" in columns else "1=1"
        source_type_expr = f"COALESCE(d.{metadata_column}->>'source_type', s.key)"
        source_url_expr = f"COALESCE(d.{metadata_column}->>'source_url', d.canonical_url)"
        where = [deleted_filter]
        params: dict[str, Any] = {"limit": limit}
        if source_values:
            where.append(f"({source_type_expr} = ANY(%(source_values)s) OR s.key = ANY(%(source_values)s))")
            params["source_values"] = source_values
        if languages:
            where.append("d.language = ANY(%(languages)s)")
            params["languages"] = languages
        if terms:
            for index, term in enumerate(terms):
                params[f"term_{index}"] = f"%{term}%"
            match_terms = " OR ".join(
                f"(d.title ILIKE %(term_{index})s OR coalesce(d.{text_column}, '') ILIKE %(term_{index})s OR coalesce({author_expr}, '') ILIKE %(term_{index})s)"
                for index in range(len(terms))
            )
            score_expr = " + ".join(
                f"CASE WHEN d.title ILIKE %(term_{index})s OR coalesce(d.{text_column}, '') ILIKE %(term_{index})s THEN 1 ELSE 0 END"
                for index in range(len(terms))
            )
            where.append(f"({match_terms})")
        else:
            score_expr = "0"
        rows = conn.execute(
            f"""
            SELECT
              d.id::text,
              d.title,
              {author_expr} AS author,
              s.name AS source,
              {source_type_expr} AS source_type,
              d.language,
              d.canonical_url,
              {source_url_expr} AS source_url,
              left(coalesce(d.{text_column}, ''), 360) AS excerpt,
              ({score_expr})::float AS relevance_score
            FROM documents d
            JOIN sources s ON s.id = d.source_id
            WHERE {" AND ".join(where)}
            ORDER BY relevance_score DESC, d.updated_at DESC, d.id
            LIMIT %(limit)s
            """,
            params,
        ).fetchall()
    return {
        "workspaceId": workspace["id"],
        "mode": "textual_fallback",
        "warning": "Busqueda semantica no disponible todavia.",
        "query": query,
        "results": [
            {
                "id": row["id"],
                "title": row["title"],
                "author": row["author"],
                "source": row["source"],
                "sourceType": normalize_source_type(row["source_type"]) or row["source_type"],
                "language": row["language"],
                "url": row["canonical_url"],
                "sourceUrl": row["source_url"],
                "excerpt": row["excerpt"],
                "relevanceScore": row["relevance_score"],
            }
            for row in rows
        ],
    }


@router.get("")
def list_workspaces(
    user_id: str | None = Header(default=None, alias="X-User-Id"),
    limit: int = Query(default=50, ge=1, le=100),
    sourceType: str | None = None,
    topic: str | None = None,
):
    user_id = current_user_id(user_id)
    where = ["sw.user_id = %(user_id)s", "sw.deleted_at IS NULL"]
    params: dict[str, Any] = {"user_id": user_id, "limit": limit}
    if sourceType:
        where.append("(sws.source_key = ANY(%(source_types)s) OR sw.source_filters::text ILIKE %(source_type_like)s)")
        params["source_types"] = source_type_aliases(sourceType)
        params["source_type_like"] = f"%{sourceType}%"
    if topic:
        where.append("(sw.name ILIKE %(topic)s OR sw.description ILIKE %(topic)s OR sw.source_filters::text ILIKE %(topic)s)")
        params["topic"] = f"%{topic}%"
    join_sources = "LEFT JOIN study_workspace_sources sws ON sws.workspace_id = sw.id AND sws.deleted_at IS NULL" if sourceType else ""
    with get_conn() as conn:
        conn.row_factory = dict_row
        rows = conn.execute(
            f"""
            SELECT DISTINCT sw.id::text, sw.user_id::text, sw.name, sw.description, sw.source_filters, sw.settings,
                   sw.created_at, sw.updated_at
            FROM study_workspaces sw
            {join_sources}
            WHERE {" AND ".join(where)}
            ORDER BY sw.updated_at DESC
            LIMIT %(limit)s
            """,
            params,
        ).fetchall()
    return {"items": [_workspace_row(row) for row in rows]}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_workspace(payload: WorkspacePayload, user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = current_user_id(user_id)
    _ensure_payload_user(payload.userId, user_id)
    settings = _workspace_settings_from_payload(payload)
    name = payload.title or settings.get("title") or payload.name
    description = payload.description or payload.scriptureReference or settings.get("scriptureReference") or settings.get("mainReference")
    with get_conn() as conn:
        conn.row_factory = dict_row
        workspace_count_row = conn.execute(
            """
            SELECT count(*)::int AS workspace_count
            FROM study_workspaces
            WHERE user_id = %(user_id)s AND deleted_at IS NULL
            """,
            {"user_id": user_id},
        ).fetchone()
        workspace_count = workspace_count_row["workspace_count"]
        if workspace_count >= get_settings().beta_max_workspaces_per_user:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Beta workspace limit reached")
        row = conn.execute(
            """
            INSERT INTO study_workspaces (user_id, name, description, source_filters, settings)
            VALUES (%(user_id)s, %(name)s, %(description)s, %(source_filters)s, %(settings)s)
            RETURNING id::text, user_id::text, name, description, source_filters, settings, created_at, updated_at
            """,
            {
                "user_id": user_id,
                "name": name,
                "description": description,
                "source_filters": Jsonb(payload.sourceFilters),
                "settings": Jsonb(settings),
            },
        ).fetchone()
        if payload.personalThought:
            conn.execute(
                """
                INSERT INTO study_notes (workspace_id, user_id, title, content, position)
                VALUES (%s, %s, 'Mi pensamiento', %s, %s)
                """,
                (
                    row["id"],
                    user_id,
                    payload.personalThought,
                    Jsonb({"blockType": "personal_note", "sortOrder": 10, "isAiGenerated": False}),
                ),
            )
        conn.commit()
    log.info("study_workspace_created", workspace_id=row["id"], user_id=user_id)
    return _workspace_row(row)


@router.get("/{workspace_id}")
def get_workspace(workspace_id: str, user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = current_user_id(user_id)
    with get_conn() as conn:
        conn.row_factory = dict_row
        row = _require_workspace(conn, workspace_id, user_id)
        blocks = _workspace_blocks(conn, workspace_id, user_id)
    return {**_workspace_row(row), "blocks": blocks}


@router.patch("/{workspace_id}")
def update_workspace(workspace_id: str, payload: WorkspaceUpdatePayload, user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = current_user_id(user_id)
    updates: list[str] = []
    params: dict[str, Any] = {"workspace_id": workspace_id, "user_id": user_id}
    if payload.name is not None:
        updates.append("name = %(name)s")
        params["name"] = payload.name
    if payload.description is not None:
        updates.append("description = %(description)s")
        params["description"] = payload.description
    if payload.sourceFilters is not None:
        updates.append("source_filters = %(source_filters)s")
        params["source_filters"] = Jsonb(payload.sourceFilters)
    settings_update = _workspace_update_settings(payload)
    if settings_update is not None:
        updates.append("settings = %(settings)s")
        if payload.settings is None:
            with get_conn() as conn:
                conn.row_factory = dict_row
                current = _require_workspace(conn, workspace_id, user_id)
                settings_update = {**(current.get("settings") or {}), **settings_update}
        params["settings"] = Jsonb(settings_update)
    if payload.title is not None and payload.name is None:
        updates.append("name = %(name)s")
        params["name"] = payload.title
    if payload.scriptureReference is not None and payload.description is None:
        updates.append("description = %(description)s")
        params["description"] = payload.scriptureReference
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    updates.extend(["updated_at = now()", "server_rev = server_rev + 1"])
    with get_conn() as conn:
        conn.row_factory = dict_row
        _require_workspace(conn, workspace_id, user_id)
        row = conn.execute(
            f"""
            UPDATE study_workspaces
            SET {", ".join(updates)}
            WHERE id = %(workspace_id)s AND user_id = %(user_id)s AND deleted_at IS NULL
            RETURNING id::text, user_id::text, name, description, source_filters, settings, created_at, updated_at
            """,
            params,
        ).fetchone()
        conn.commit()
    log.info("study_workspace_updated", workspace_id=workspace_id, user_id=user_id)
    return _workspace_row(row)


@router.delete("/{workspace_id}")
def delete_workspace(workspace_id: str, user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = current_user_id(user_id)
    with get_conn() as conn:
        conn.row_factory = dict_row
        _require_workspace(conn, workspace_id, user_id)
        conn.execute(
            """
            UPDATE study_workspaces
            SET deleted_at = now(), updated_at = now(), server_rev = server_rev + 1
            WHERE id = %(workspace_id)s AND user_id = %(user_id)s
            """,
            {"workspace_id": workspace_id, "user_id": user_id},
        )
        conn.commit()
    log.info("study_workspace_deleted", workspace_id=workspace_id, user_id=user_id)
    return {"deleted": True}


@router.get("/{workspace_id}/sources")
def list_source_filters(workspace_id: str, user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = current_user_id(user_id)
    with get_conn() as conn:
        conn.row_factory = dict_row
        _require_workspace(conn, workspace_id, user_id)
        rows = conn.execute(
            """
            SELECT id::text, workspace_id::text, user_id::text, source_key, language, author, category, tags, created_at, updated_at
            FROM study_workspace_sources
            WHERE workspace_id = %(workspace_id)s AND user_id = %(user_id)s AND deleted_at IS NULL
            ORDER BY updated_at DESC
            """,
            {"workspace_id": workspace_id, "user_id": user_id},
        ).fetchall()
    return {"items": [_source_filter_row(row) for row in rows]}


@router.post("/{workspace_id}/sources", status_code=status.HTTP_201_CREATED)
def create_source_filter(workspace_id: str, payload: SourceFilterPayload, user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = current_user_id(user_id)
    with get_conn() as conn:
        conn.row_factory = dict_row
        _require_workspace(conn, workspace_id, user_id)
        row = conn.execute(
            """
            INSERT INTO study_workspace_sources (workspace_id, user_id, source_key, language, author, category, tags)
            VALUES (%(workspace_id)s, %(user_id)s, %(source_key)s, %(language)s, %(author)s, %(category)s, %(tags)s)
            RETURNING id::text, workspace_id::text, user_id::text, source_key, language, author, category, tags, created_at, updated_at
            """,
            {
                "workspace_id": workspace_id,
                "user_id": user_id,
                "source_key": normalize_source_type(payload.sourceKey),
                "language": payload.language,
                "author": payload.author,
                "category": payload.category,
                "tags": Jsonb(payload.tags),
            },
        ).fetchone()
        conn.commit()
    log.info("study_source_filter_created", workspace_id=workspace_id, user_id=user_id, source_key=payload.sourceKey)
    return _source_filter_row(row)


@router.delete("/{workspace_id}/sources/{source_filter_id}")
def delete_source_filter(workspace_id: str, source_filter_id: str, user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = current_user_id(user_id)
    with get_conn() as conn:
        conn.row_factory = dict_row
        _require_workspace(conn, workspace_id, user_id)
        _resource_belongs_to_user(conn, "study_workspace_sources", source_filter_id, workspace_id, user_id)
        conn.execute(
            """
            UPDATE study_workspace_sources SET deleted_at = now(), updated_at = now()
            WHERE id = %(source_filter_id)s AND workspace_id = %(workspace_id)s AND user_id = %(user_id)s
            """,
            {"source_filter_id": source_filter_id, "workspace_id": workspace_id, "user_id": user_id},
        )
        conn.commit()
    return {"deleted": True}


@router.get("/{workspace_id}/notes")
def list_notes(
    workspace_id: str,
    user_id: str | None = Header(default=None, alias="X-User-Id"),
    documentId: str | None = None,
    sourceType: str | None = None,
    topic: str | None = None,
    scriptureRef: str | None = None,
    limit: int = Query(default=100, ge=1, le=200),
):
    user_id = current_user_id(user_id)
    filters, params, needs_document_join = _filter_sql(
        document_id=documentId,
        source_type=sourceType,
        topic=topic,
        scripture_ref=scriptureRef,
        artifact_alias="sn",
    )
    params.update({"workspace_id": workspace_id, "user_id": user_id, "limit": limit})
    joins = "LEFT JOIN documents d ON d.id = sn.document_id LEFT JOIN sources s ON s.id = d.source_id" if needs_document_join else ""
    with get_conn() as conn:
        conn.row_factory = dict_row
        _require_workspace(conn, workspace_id, user_id)
        rows = conn.execute(
            f"""
            SELECT sn.id::text, sn.workspace_id::text, sn.user_id::text, sn.document_id::text, sn.chunk_id::text,
                   sn.title, sn.content, sn.selected_text, sn.selection_range, sn.scripture_refs, sn.color, sn.position,
                   sn.created_at, sn.updated_at
            FROM study_notes sn
            {joins}
            WHERE sn.workspace_id = %(workspace_id)s AND sn.user_id = %(user_id)s AND sn.deleted_at IS NULL
              {"AND " + " AND ".join(filters) if filters else ""}
            ORDER BY sn.updated_at DESC
            LIMIT %(limit)s
            """,
            params,
        ).fetchall()
    return {"items": [_note_row(row) for row in rows]}


@router.post("/{workspace_id}/notes", status_code=status.HTTP_201_CREATED)
def create_note(workspace_id: str, payload: NotePayload, user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = current_user_id(user_id)
    with get_conn() as conn:
        conn.row_factory = dict_row
        _require_workspace(conn, workspace_id, user_id)
        row = conn.execute(
            """
            INSERT INTO study_notes (
              workspace_id, user_id, document_id, chunk_id, title, content, selected_text,
              selection_range, scripture_refs, color, position
            )
            VALUES (
              %(workspace_id)s, %(user_id)s, %(document_id)s, %(chunk_id)s, %(title)s, %(content)s, %(selected_text)s,
              %(selection_range)s, %(scripture_refs)s, %(color)s, %(position)s
            )
            RETURNING id::text, workspace_id::text, user_id::text, document_id::text, chunk_id::text,
                      title, content, selected_text, selection_range, scripture_refs, color, position, created_at, updated_at
            """,
            {
                "workspace_id": workspace_id,
                "user_id": user_id,
                "document_id": payload.documentId,
                "chunk_id": payload.chunkId,
                "title": payload.title,
                "content": payload.content,
                "selected_text": payload.selectedText,
                "selection_range": Jsonb(payload.selectionRange),
                "scripture_refs": Jsonb(payload.scriptureRefs),
                "color": payload.color,
                "position": Jsonb(payload.position),
            },
        ).fetchone()
        conn.commit()
    log.info("study_note_created", workspace_id=workspace_id, user_id=user_id, note_id=row["id"])
    return _note_row(row)


@router.patch("/{workspace_id}/notes/{note_id}")
def update_note(workspace_id: str, note_id: str, payload: NoteUpdatePayload, user_id: str | None = Header(default=None, alias="X-User-Id")):
    return _update_json_resource(
        table="study_notes",
        row_mapper=_note_row,
        workspace_id=workspace_id,
        resource_id=note_id,
        user_id=current_user_id(user_id),
        payload={
            "document_id": payload.documentId,
            "chunk_id": payload.chunkId,
            "title": payload.title,
            "content": payload.content,
            "selected_text": payload.selectedText,
            "selection_range": Jsonb(payload.selectionRange) if payload.selectionRange is not None else None,
            "scripture_refs": Jsonb(payload.scriptureRefs) if payload.scriptureRefs is not None else None,
            "color": payload.color,
            "position": Jsonb(payload.position) if payload.position is not None else None,
        },
        returning="""
          id::text, workspace_id::text, user_id::text, document_id::text, chunk_id::text, title, content,
          selected_text, selection_range, scripture_refs, color, position, created_at, updated_at
        """,
    )


@router.delete("/{workspace_id}/notes/{note_id}")
def delete_note(workspace_id: str, note_id: str, user_id: str | None = Header(default=None, alias="X-User-Id")):
    return _soft_delete_resource("study_notes", note_id, workspace_id, current_user_id(user_id), "study_note_deleted")


@router.get("/{workspace_id}/highlights")
def list_highlights(
    workspace_id: str,
    user_id: str | None = Header(default=None, alias="X-User-Id"),
    documentId: str | None = None,
    sourceType: str | None = None,
    topic: str | None = None,
    scriptureRef: str | None = None,
    limit: int = Query(default=100, ge=1, le=200),
):
    user_id = current_user_id(user_id)
    filters, params, needs_document_join = _filter_sql(
        document_id=documentId,
        source_type=sourceType,
        topic=topic,
        scripture_ref=scriptureRef,
        artifact_alias="sh",
    )
    params.update({"workspace_id": workspace_id, "user_id": user_id, "limit": limit})
    joins = "LEFT JOIN documents d ON d.id = sh.document_id LEFT JOIN sources s ON s.id = d.source_id" if needs_document_join else ""
    with get_conn() as conn:
        conn.row_factory = dict_row
        _require_workspace(conn, workspace_id, user_id)
        rows = conn.execute(
            f"""
            SELECT sh.id::text, sh.workspace_id::text, sh.user_id::text, sh.document_id::text, sh.chunk_id::text,
                   sh.note_id::text, sh.start_char, sh.end_char, sh.selected_text, sh.scripture_refs, sh.color,
                   sh.metadata, sh.created_at, sh.updated_at
            FROM study_highlights sh
            {joins}
            WHERE sh.workspace_id = %(workspace_id)s AND sh.user_id = %(user_id)s AND sh.deleted_at IS NULL
              {"AND " + " AND ".join(filters) if filters else ""}
            ORDER BY sh.updated_at DESC
            LIMIT %(limit)s
            """,
            params,
        ).fetchall()
    return {"items": [_highlight_row(row) for row in rows]}


@router.post("/{workspace_id}/highlights", status_code=status.HTTP_201_CREATED)
def create_highlight(workspace_id: str, payload: HighlightPayload, user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = current_user_id(user_id)
    with get_conn() as conn:
        conn.row_factory = dict_row
        _require_workspace(conn, workspace_id, user_id)
        row = conn.execute(
            """
            INSERT INTO study_highlights (
              workspace_id, user_id, document_id, chunk_id, note_id, start_char, end_char,
              selected_text, scripture_refs, color, metadata
            )
            VALUES (
              %(workspace_id)s, %(user_id)s, %(document_id)s, %(chunk_id)s, %(note_id)s, %(start_char)s, %(end_char)s,
              %(selected_text)s, %(scripture_refs)s, %(color)s, %(metadata)s
            )
            RETURNING id::text, workspace_id::text, user_id::text, document_id::text, chunk_id::text,
                      note_id::text, start_char, end_char, selected_text, scripture_refs, color, metadata, created_at, updated_at
            """,
            {
                "workspace_id": workspace_id,
                "user_id": user_id,
                "document_id": payload.documentId,
                "chunk_id": payload.chunkId,
                "note_id": payload.noteId,
                "start_char": payload.startChar,
                "end_char": payload.endChar,
                "selected_text": payload.selectedText,
                "scripture_refs": Jsonb(payload.scriptureRefs),
                "color": payload.color,
                "metadata": Jsonb(payload.metadata),
            },
        ).fetchone()
        conn.commit()
    log.info("study_highlight_created", workspace_id=workspace_id, user_id=user_id, highlight_id=row["id"])
    return _highlight_row(row)


@router.patch("/{workspace_id}/highlights/{highlight_id}")
def update_highlight(
    workspace_id: str,
    highlight_id: str,
    payload: HighlightUpdatePayload,
    user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    return _update_json_resource(
        table="study_highlights",
        row_mapper=_highlight_row,
        workspace_id=workspace_id,
        resource_id=highlight_id,
        user_id=current_user_id(user_id),
        payload={
            "chunk_id": payload.chunkId,
            "note_id": payload.noteId,
            "start_char": payload.startChar,
            "end_char": payload.endChar,
            "selected_text": payload.selectedText,
            "scripture_refs": Jsonb(payload.scriptureRefs) if payload.scriptureRefs is not None else None,
            "color": payload.color,
            "metadata": Jsonb(payload.metadata) if payload.metadata is not None else None,
        },
        returning="""
          id::text, workspace_id::text, user_id::text, document_id::text, chunk_id::text,
          note_id::text, start_char, end_char, selected_text, scripture_refs, color, metadata, created_at, updated_at
        """,
    )


@router.delete("/{workspace_id}/highlights/{highlight_id}")
def delete_highlight(workspace_id: str, highlight_id: str, user_id: str | None = Header(default=None, alias="X-User-Id")):
    return _soft_delete_resource("study_highlights", highlight_id, workspace_id, current_user_id(user_id), "study_highlight_deleted")


@router.get("/{workspace_id}/citations")
def list_citations(
    workspace_id: str,
    user_id: str | None = Header(default=None, alias="X-User-Id"),
    documentId: str | None = None,
    sourceType: str | None = None,
    topic: str | None = None,
    scriptureRef: str | None = None,
    limit: int = Query(default=100, ge=1, le=200),
):
    user_id = current_user_id(user_id)
    filters, params, _ = _filter_sql(
        document_id=documentId,
        source_type=sourceType,
        topic=topic,
        scripture_ref=scriptureRef,
        artifact_alias="sc",
    )
    params.update({"workspace_id": workspace_id, "user_id": user_id, "limit": limit})
    with get_conn() as conn:
        conn.row_factory = dict_row
        _require_workspace(conn, workspace_id, user_id)
        rows = conn.execute(
            f"""
            SELECT sc.id::text, sc.workspace_id::text, sc.user_id::text, sc.document_id::text, sc.chunk_id::text,
                   sc.quote, sc.selected_text, sc.citation_url, sc.source_url, sc.source_title, sc.source_author,
                   sc.location, sc.scripture_refs, sc.metadata, sc.created_at, sc.updated_at,
                   COALESCE(d.raw_metadata->>'source_type', s.key) AS source_type, s.name AS source_name
            FROM saved_citations sc
            JOIN documents d ON d.id = sc.document_id
            JOIN sources s ON s.id = d.source_id
            WHERE sc.workspace_id = %(workspace_id)s AND sc.user_id = %(user_id)s AND sc.deleted_at IS NULL
              {"AND " + " AND ".join(filters) if filters else ""}
            ORDER BY sc.updated_at DESC
            LIMIT %(limit)s
            """,
            params,
        ).fetchall()
    return {"items": [_citation_row(row) for row in rows]}


@router.post("/{workspace_id}/citations", status_code=status.HTTP_201_CREATED)
def save_citation(workspace_id: str, payload: CitationPayload, user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = current_user_id(user_id)
    with get_conn() as conn:
        conn.row_factory = dict_row
        _require_workspace(conn, workspace_id, user_id)
        attribution = _document_attribution(conn, payload.documentId)
        row = conn.execute(
            """
            INSERT INTO saved_citations (
              workspace_id, user_id, document_id, chunk_id, quote, selected_text, citation_url,
              source_url, source_title, source_author, location, scripture_refs, metadata
            )
            VALUES (
              %(workspace_id)s, %(user_id)s, %(document_id)s, %(chunk_id)s, %(quote)s, %(selected_text)s, %(citation_url)s,
              %(source_url)s, %(source_title)s, %(source_author)s, %(location)s, %(scripture_refs)s, %(metadata)s
            )
            RETURNING id::text, workspace_id::text, user_id::text, document_id::text, chunk_id::text,
                      quote, selected_text, citation_url, source_url, source_title, source_author, location,
                      scripture_refs, metadata, created_at, updated_at
            """,
            {
                "workspace_id": workspace_id,
                "user_id": user_id,
                "document_id": payload.documentId,
                "chunk_id": payload.chunkId,
                "quote": payload.quote,
                "selected_text": payload.selectedText,
                "citation_url": payload.citationUrl or attribution["canonical_url"],
                "source_url": attribution["source_url"],
                "source_title": attribution["title"],
                "source_author": attribution["author"],
                "location": Jsonb(payload.location),
                "scripture_refs": Jsonb(payload.scriptureRefs),
                "metadata": Jsonb({**payload.metadata, "sourceType": attribution["source_type"], "sourceName": attribution["source_name"]}),
            },
        ).fetchone()
        conn.commit()
    log.info("saved_citation_created", workspace_id=workspace_id, user_id=user_id, citation_id=row["id"])
    return _citation_row({**row, "source_type": attribution["source_type"], "source_name": attribution["source_name"]})


@router.patch("/{workspace_id}/citations/{citation_id}")
def update_citation(
    workspace_id: str,
    citation_id: str,
    payload: CitationUpdatePayload,
    user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    return _update_json_resource(
        table="saved_citations",
        row_mapper=_citation_row,
        workspace_id=workspace_id,
        resource_id=citation_id,
        user_id=current_user_id(user_id),
        payload={
            "quote": payload.quote,
            "selected_text": payload.selectedText,
            "citation_url": payload.citationUrl,
            "location": Jsonb(payload.location) if payload.location is not None else None,
            "scripture_refs": Jsonb(payload.scriptureRefs) if payload.scriptureRefs is not None else None,
            "metadata": Jsonb(payload.metadata) if payload.metadata is not None else None,
        },
        returning="""
          id::text, workspace_id::text, user_id::text, document_id::text, chunk_id::text, quote, selected_text,
          citation_url, source_url, source_title, source_author, location, scripture_refs, metadata, created_at, updated_at
        """,
    )


@router.delete("/{workspace_id}/citations/{citation_id}")
def delete_citation(workspace_id: str, citation_id: str, user_id: str | None = Header(default=None, alias="X-User-Id")):
    return _soft_delete_resource("saved_citations", citation_id, workspace_id, current_user_id(user_id), "saved_citation_deleted")


@router.get("/{workspace_id}/post-its")
def list_post_its(
    workspace_id: str,
    user_id: str | None = Header(default=None, alias="X-User-Id"),
    documentId: str | None = None,
    sourceType: str | None = None,
    topic: str | None = None,
    limit: int = Query(default=100, ge=1, le=200),
):
    user_id = current_user_id(user_id)
    filters, params, needs_document_join = _filter_sql(
        document_id=documentId,
        source_type=sourceType,
        topic=topic,
        artifact_alias="pi",
    )
    params.update({"workspace_id": workspace_id, "user_id": user_id, "limit": limit})
    joins = "LEFT JOIN documents d ON d.id = pi.document_id LEFT JOIN sources s ON s.id = d.source_id" if needs_document_join else ""
    with get_conn() as conn:
        conn.row_factory = dict_row
        _require_workspace(conn, workspace_id, user_id)
        rows = conn.execute(
            f"""
            SELECT pi.id::text, pi.workspace_id::text, pi.user_id::text, pi.document_id::text, pi.content,
                   pi.color, pi.position, pi.source_filters, pi.pinned, pi.created_at, pi.updated_at
            FROM post_its pi
            {joins}
            WHERE pi.workspace_id = %(workspace_id)s AND pi.user_id = %(user_id)s AND pi.deleted_at IS NULL
              {"AND " + " AND ".join(filters) if filters else ""}
            ORDER BY pi.pinned DESC, pi.updated_at DESC
            LIMIT %(limit)s
            """,
            params,
        ).fetchall()
    return {"items": [_post_it_row(row) for row in rows]}


@router.post("/{workspace_id}/post-its", status_code=status.HTTP_201_CREATED)
def create_post_it(workspace_id: str, payload: PostItPayload, user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = current_user_id(user_id)
    with get_conn() as conn:
        conn.row_factory = dict_row
        _require_workspace(conn, workspace_id, user_id)
        row = conn.execute(
            """
            INSERT INTO post_its (workspace_id, user_id, document_id, content, color, position, source_filters, pinned)
            VALUES (%(workspace_id)s, %(user_id)s, %(document_id)s, %(content)s, %(color)s, %(position)s, %(source_filters)s, %(pinned)s)
            RETURNING id::text, workspace_id::text, user_id::text, document_id::text, content, color,
                      position, source_filters, pinned, created_at, updated_at
            """,
            {
                "workspace_id": workspace_id,
                "user_id": user_id,
                "document_id": payload.documentId,
                "content": payload.content,
                "color": payload.color,
                "position": Jsonb(payload.position),
                "source_filters": Jsonb(payload.sourceFilters),
                "pinned": payload.pinned,
            },
        ).fetchone()
        conn.commit()
    log.info("post_it_created", workspace_id=workspace_id, user_id=user_id, post_it_id=row["id"])
    return _post_it_row(row)


@router.patch("/{workspace_id}/post-its/{post_it_id}")
def update_post_it(workspace_id: str, post_it_id: str, payload: PostItUpdatePayload, user_id: str | None = Header(default=None, alias="X-User-Id")):
    return _update_json_resource(
        table="post_its",
        row_mapper=_post_it_row,
        workspace_id=workspace_id,
        resource_id=post_it_id,
        user_id=current_user_id(user_id),
        payload={
            "document_id": payload.documentId,
            "content": payload.content,
            "color": payload.color,
            "position": Jsonb(payload.position) if payload.position is not None else None,
            "source_filters": Jsonb(payload.sourceFilters) if payload.sourceFilters is not None else None,
            "pinned": payload.pinned,
        },
        returning="""
          id::text, workspace_id::text, user_id::text, document_id::text, content, color,
          position, source_filters, pinned, created_at, updated_at
        """,
    )


@router.delete("/{workspace_id}/post-its/{post_it_id}")
def delete_post_it(workspace_id: str, post_it_id: str, user_id: str | None = Header(default=None, alias="X-User-Id")):
    return _soft_delete_resource("post_its", post_it_id, workspace_id, current_user_id(user_id), "post_it_deleted")


@router.get("/{workspace_id}/blocks")
def list_blocks(workspace_id: str, user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = current_user_id(user_id)
    with get_conn() as conn:
        conn.row_factory = dict_row
        _require_workspace(conn, workspace_id, user_id)
        return {"items": _workspace_blocks(conn, workspace_id, user_id)}


@router.post("/{workspace_id}/blocks", status_code=status.HTTP_201_CREATED)
def create_block(workspace_id: str, payload: BlockPayload, user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = current_user_id(user_id)
    block_type = _normalize_block_type(payload.type)
    sort_order = payload.sortOrder
    with get_conn() as conn:
        conn.row_factory = dict_row
        _require_workspace(conn, workspace_id, user_id)
        if sort_order is None:
            sort_order = _next_block_sort_order(conn, workspace_id, user_id)
        metadata = _block_metadata(payload, block_type, sort_order)
        if block_type == "post_it":
            row = conn.execute(
                """
                INSERT INTO post_its (workspace_id, user_id, content, color, position, source_filters, pinned)
                VALUES (%(workspace_id)s, %(user_id)s, %(content)s, 'yellow', %(position)s, '{}'::jsonb, false)
                RETURNING id::text, workspace_id::text, user_id::text, document_id::text, content, color,
                          position, source_filters, pinned, created_at, updated_at
                """,
                {
                    "workspace_id": workspace_id,
                    "user_id": user_id,
                    "content": payload.content or payload.quoteText or payload.title,
                    "position": Jsonb(metadata),
                },
            ).fetchone()
            conn.commit()
            return _post_it_block_row(row)
        row = conn.execute(
            """
            INSERT INTO study_notes (
              workspace_id, user_id, title, content, selected_text, selection_range,
              scripture_refs, color, position
            )
            VALUES (
              %(workspace_id)s, %(user_id)s, %(title)s, %(content)s, %(selected_text)s,
              '{}'::jsonb, '[]'::jsonb, 'yellow', %(position)s
            )
            RETURNING id::text, workspace_id::text, user_id::text, document_id::text, chunk_id::text,
                      title, content, selected_text, selection_range, scripture_refs, color, position,
                      created_at, updated_at
            """,
            {
                "workspace_id": workspace_id,
                "user_id": user_id,
                "title": payload.title,
                "content": payload.content or "",
                "selected_text": payload.quoteText,
                "position": Jsonb(metadata),
            },
        ).fetchone()
        conn.commit()
    return _note_block_row(row)


@router.patch("/{workspace_id}/blocks/{block_id}")
def update_block(workspace_id: str, block_id: str, payload: BlockUpdatePayload, user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = current_user_id(user_id)
    with get_conn() as conn:
        conn.row_factory = dict_row
        _require_workspace(conn, workspace_id, user_id)
        note = _find_block_note(conn, workspace_id, block_id, user_id)
        post_it = None if note else _find_block_post_it(conn, workspace_id, block_id, user_id)
        if not note and not post_it:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found")
        current = _note_block_row(note) if note else _post_it_block_row(post_it)
        next_type = _normalize_block_type(payload.type or current["type"])
        metadata = {
            **(current.get("metadata") or {}),
            "blockType": next_type,
            "title": payload.title if payload.title is not None else current["title"],
            "sourceTitle": payload.sourceTitle if payload.sourceTitle is not None else current.get("sourceTitle"),
            "sourceAuthor": payload.sourceAuthor if payload.sourceAuthor is not None else current.get("sourceAuthor"),
            "sourceReference": payload.sourceReference if payload.sourceReference is not None else current.get("sourceReference"),
            "sourceUrl": payload.sourceUrl if payload.sourceUrl is not None else current.get("sourceUrl"),
            "isAiGenerated": payload.isAiGenerated if payload.isAiGenerated is not None else current.get("isAiGenerated", False),
            "sortOrder": payload.sortOrder if payload.sortOrder is not None else current.get("sortOrder", 0),
        }
        if note:
            row = conn.execute(
                """
                UPDATE study_notes
                SET title = %(title)s, content = %(content)s, selected_text = %(selected_text)s,
                    position = %(position)s, updated_at = now(), server_rev = server_rev + 1
                WHERE id = %(block_id)s AND workspace_id = %(workspace_id)s AND user_id = %(user_id)s AND deleted_at IS NULL
                RETURNING id::text, workspace_id::text, user_id::text, document_id::text, chunk_id::text,
                          title, content, selected_text, selection_range, scripture_refs, color, position,
                          created_at, updated_at
                """,
                {
                    "block_id": block_id,
                    "workspace_id": workspace_id,
                    "user_id": user_id,
                    "title": payload.title if payload.title is not None else current["title"],
                    "content": payload.content if payload.content is not None else current["content"],
                    "selected_text": payload.quoteText if payload.quoteText is not None else current.get("quoteText"),
                    "position": Jsonb(metadata),
                },
            ).fetchone()
            conn.commit()
            return _note_block_row(row)
        row = conn.execute(
            """
            UPDATE post_its
            SET content = %(content)s, position = %(position)s, updated_at = now(), server_rev = server_rev + 1
            WHERE id = %(block_id)s AND workspace_id = %(workspace_id)s AND user_id = %(user_id)s AND deleted_at IS NULL
            RETURNING id::text, workspace_id::text, user_id::text, document_id::text, content, color,
                      position, source_filters, pinned, created_at, updated_at
            """,
            {
                "block_id": block_id,
                "workspace_id": workspace_id,
                "user_id": user_id,
                "content": payload.content if payload.content is not None else current["content"],
                "position": Jsonb(metadata),
            },
        ).fetchone()
        conn.commit()
    return _post_it_block_row(row)


@router.delete("/{workspace_id}/blocks/{block_id}")
def delete_block(workspace_id: str, block_id: str, user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = current_user_id(user_id)
    with get_conn() as conn:
        conn.row_factory = dict_row
        _require_workspace(conn, workspace_id, user_id)
        if _find_block_note(conn, workspace_id, block_id, user_id):
            conn.execute(
                """
                UPDATE study_notes
                SET deleted_at = now(), updated_at = now(), server_rev = server_rev + 1
                WHERE id = %(block_id)s AND workspace_id = %(workspace_id)s AND user_id = %(user_id)s
                """,
                {"block_id": block_id, "workspace_id": workspace_id, "user_id": user_id},
            )
            conn.commit()
            return {"deleted": True}
        if _find_block_post_it(conn, workspace_id, block_id, user_id):
            conn.execute(
                """
                UPDATE post_its
                SET deleted_at = now(), updated_at = now(), server_rev = server_rev + 1
                WHERE id = %(block_id)s AND workspace_id = %(workspace_id)s AND user_id = %(user_id)s
                """,
                {"block_id": block_id, "workspace_id": workspace_id, "user_id": user_id},
            )
            conn.commit()
            return {"deleted": True}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found")


@router.post("/{workspace_id}/ai-suggest", response_model=WorkspaceAiSuggestResponse)
async def ai_suggest_workspace(
    workspace_id: str,
    payload: WorkspaceAiSuggestPayload,
    request: Request,
    user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    user_id = current_user_id(user_id)
    settings = get_settings()
    await limiter.check(request, settings.chat_rate_limit_per_minute, scope="study-ai")
    await limiter.check_daily(request, settings.max_user_study_ai_per_day, "study-ai")
    with get_conn() as conn:
        conn.row_factory = dict_row
        workspace = _require_workspace(conn, workspace_id, user_id)
        blocks = _workspace_blocks(conn, workspace_id, user_id)
        local_context = load_workspace_local_context(conn, workspace, blocks, user_id)
    try:
        suggestions, sources_used, warnings, provider = await generate_workspace_suggestions(
            workspace=workspace,
            blocks=blocks,
            user_id=user_id,
            payload=payload.model_dump(mode="json"),
            local_context=local_context,
        )
    except StudyAiConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La funcion de IA todavia no esta configurada en el servidor.",
        ) from exc
    except StudyAiGenerationError as exc:
        log.warning("study_workspace_ai_suggestions_failed", workspace_id=workspace_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No se pudo generar informacion con IA. Intenta nuevamente mas tarde.",
        ) from exc
    log.info("study_workspace_ai_suggestions_generated", workspace_id=workspace_id, user_id=user_id, provider=provider)
    return {"suggestions": suggestions, "sources_used": sources_used, "warnings": warnings}


@alias_router.get("/workspaces")
def alias_list_workspaces(
    user_id: str | None = Header(default=None, alias="X-User-Id"),
    limit: int = Query(default=50, ge=1, le=100),
    sourceType: str | None = None,
    topic: str | None = None,
):
    return list_workspaces(user_id=user_id, limit=limit, sourceType=sourceType, topic=topic)


@alias_router.post("/workspaces", status_code=status.HTTP_201_CREATED)
def alias_create_workspace(payload: WorkspacePayload, user_id: str | None = Header(default=None, alias="X-User-Id")):
    return create_workspace(payload=payload, user_id=user_id)


@alias_router.get("/workspaces/{workspace_id}")
def alias_get_workspace(workspace_id: str, user_id: str | None = Header(default=None, alias="X-User-Id")):
    return get_workspace(workspace_id=workspace_id, user_id=user_id)


@alias_router.patch("/workspaces/{workspace_id}")
def alias_update_workspace(workspace_id: str, payload: WorkspaceUpdatePayload, user_id: str | None = Header(default=None, alias="X-User-Id")):
    return update_workspace(workspace_id=workspace_id, payload=payload, user_id=user_id)


@alias_router.delete("/workspaces/{workspace_id}")
def alias_delete_workspace(workspace_id: str, user_id: str | None = Header(default=None, alias="X-User-Id")):
    return delete_workspace(workspace_id=workspace_id, user_id=user_id)


@alias_router.get("/workspaces/{workspace_id}/related")
def related_documents(
    workspace_id: str,
    user_id: str | None = Header(default=None, alias="X-User-Id"),
    limit: int = Query(default=12, ge=1, le=50),
):
    user_id = current_user_id(user_id)
    with get_conn() as conn:
        conn.row_factory = dict_row
        workspace = _require_workspace(conn, workspace_id, user_id)
    semantic = _semantic_related(workspace, limit)
    if semantic is not None:
        return semantic
    return _textual_related(workspace, limit)


@alias_router.get("/workspaces/{workspace_id}/source-filters")
def alias_list_source_filters(workspace_id: str, user_id: str | None = Header(default=None, alias="X-User-Id")):
    return list_source_filters(workspace_id=workspace_id, user_id=user_id)


@alias_router.post("/workspaces/{workspace_id}/source-filters", status_code=status.HTTP_201_CREATED)
def alias_create_source_filter(workspace_id: str, payload: SourceFilterPayload, user_id: str | None = Header(default=None, alias="X-User-Id")):
    return create_source_filter(workspace_id=workspace_id, payload=payload, user_id=user_id)


@alias_router.delete("/workspaces/{workspace_id}/source-filters/{source_filter_id}")
def alias_delete_source_filter(workspace_id: str, source_filter_id: str, user_id: str | None = Header(default=None, alias="X-User-Id")):
    return delete_source_filter(workspace_id=workspace_id, source_filter_id=source_filter_id, user_id=user_id)


@alias_router.get("/workspaces/{workspace_id}/notes")
def alias_list_notes(
    workspace_id: str,
    user_id: str | None = Header(default=None, alias="X-User-Id"),
    documentId: str | None = None,
    sourceType: str | None = None,
    topic: str | None = None,
    scriptureRef: str | None = None,
    limit: int = Query(default=100, ge=1, le=200),
):
    return list_notes(workspace_id, user_id, documentId, sourceType, topic, scriptureRef, limit)


@alias_router.post("/workspaces/{workspace_id}/notes", status_code=status.HTTP_201_CREATED)
def alias_create_note(workspace_id: str, payload: NotePayload, user_id: str | None = Header(default=None, alias="X-User-Id")):
    return create_note(workspace_id=workspace_id, payload=payload, user_id=user_id)


@alias_router.patch("/workspaces/{workspace_id}/notes/{note_id}")
def alias_update_note(workspace_id: str, note_id: str, payload: NoteUpdatePayload, user_id: str | None = Header(default=None, alias="X-User-Id")):
    return update_note(workspace_id=workspace_id, note_id=note_id, payload=payload, user_id=user_id)


@alias_router.delete("/workspaces/{workspace_id}/notes/{note_id}")
def alias_delete_note(workspace_id: str, note_id: str, user_id: str | None = Header(default=None, alias="X-User-Id")):
    return delete_note(workspace_id=workspace_id, note_id=note_id, user_id=user_id)


@alias_router.get("/workspaces/{workspace_id}/citations")
def alias_list_citations(
    workspace_id: str,
    user_id: str | None = Header(default=None, alias="X-User-Id"),
    documentId: str | None = None,
    sourceType: str | None = None,
    topic: str | None = None,
    scriptureRef: str | None = None,
    limit: int = Query(default=100, ge=1, le=200),
):
    return list_citations(workspace_id, user_id, documentId, sourceType, topic, scriptureRef, limit)


@alias_router.post("/workspaces/{workspace_id}/citations", status_code=status.HTTP_201_CREATED)
def alias_save_citation(workspace_id: str, payload: CitationPayload, user_id: str | None = Header(default=None, alias="X-User-Id")):
    return save_citation(workspace_id=workspace_id, payload=payload, user_id=user_id)


@alias_router.delete("/workspaces/{workspace_id}/citations/{citation_id}")
def alias_delete_citation(workspace_id: str, citation_id: str, user_id: str | None = Header(default=None, alias="X-User-Id")):
    return delete_citation(workspace_id=workspace_id, citation_id=citation_id, user_id=user_id)


@alias_router.patch("/workspaces/{workspace_id}/citations/{citation_id}")
def alias_update_citation(
    workspace_id: str,
    citation_id: str,
    payload: CitationUpdatePayload,
    user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    return update_citation(workspace_id=workspace_id, citation_id=citation_id, payload=payload, user_id=user_id)


@alias_router.get("/workspaces/{workspace_id}/highlights")
def alias_list_highlights(
    workspace_id: str,
    user_id: str | None = Header(default=None, alias="X-User-Id"),
    documentId: str | None = None,
    sourceType: str | None = None,
    topic: str | None = None,
    scriptureRef: str | None = None,
    limit: int = Query(default=100, ge=1, le=200),
):
    return list_highlights(workspace_id, user_id, documentId, sourceType, topic, scriptureRef, limit)


@alias_router.post("/workspaces/{workspace_id}/highlights", status_code=status.HTTP_201_CREATED)
def alias_create_highlight(workspace_id: str, payload: HighlightPayload, user_id: str | None = Header(default=None, alias="X-User-Id")):
    return create_highlight(workspace_id=workspace_id, payload=payload, user_id=user_id)


@alias_router.patch("/workspaces/{workspace_id}/highlights/{highlight_id}")
def alias_update_highlight(
    workspace_id: str,
    highlight_id: str,
    payload: HighlightUpdatePayload,
    user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    return update_highlight(workspace_id=workspace_id, highlight_id=highlight_id, payload=payload, user_id=user_id)


@alias_router.delete("/workspaces/{workspace_id}/highlights/{highlight_id}")
def alias_delete_highlight(workspace_id: str, highlight_id: str, user_id: str | None = Header(default=None, alias="X-User-Id")):
    return delete_highlight(workspace_id=workspace_id, highlight_id=highlight_id, user_id=user_id)


@alias_router.get("/workspaces/{workspace_id}/sticky-notes")
def alias_list_sticky_notes(
    workspace_id: str,
    user_id: str | None = Header(default=None, alias="X-User-Id"),
    documentId: str | None = None,
    sourceType: str | None = None,
    topic: str | None = None,
    limit: int = Query(default=100, ge=1, le=200),
):
    return list_post_its(workspace_id, user_id, documentId, sourceType, topic, limit)


@alias_router.post("/workspaces/{workspace_id}/sticky-notes", status_code=status.HTTP_201_CREATED)
def alias_create_sticky_note(workspace_id: str, payload: PostItPayload, user_id: str | None = Header(default=None, alias="X-User-Id")):
    return create_post_it(workspace_id=workspace_id, payload=payload, user_id=user_id)


@alias_router.patch("/workspaces/{workspace_id}/sticky-notes/{post_it_id}")
def alias_update_sticky_note(workspace_id: str, post_it_id: str, payload: PostItUpdatePayload, user_id: str | None = Header(default=None, alias="X-User-Id")):
    return update_post_it(workspace_id=workspace_id, post_it_id=post_it_id, payload=payload, user_id=user_id)


@alias_router.delete("/workspaces/{workspace_id}/sticky-notes/{post_it_id}")
def alias_delete_sticky_note(workspace_id: str, post_it_id: str, user_id: str | None = Header(default=None, alias="X-User-Id")):
    return delete_post_it(workspace_id=workspace_id, post_it_id=post_it_id, user_id=user_id)


@alias_router.get("/workspaces/{workspace_id}/blocks")
def alias_list_blocks(workspace_id: str, user_id: str | None = Header(default=None, alias="X-User-Id")):
    return list_blocks(workspace_id=workspace_id, user_id=user_id)


@alias_router.post("/workspaces/{workspace_id}/blocks", status_code=status.HTTP_201_CREATED)
def alias_create_block(workspace_id: str, payload: BlockPayload, user_id: str | None = Header(default=None, alias="X-User-Id")):
    return create_block(workspace_id=workspace_id, payload=payload, user_id=user_id)


@alias_router.patch("/workspaces/{workspace_id}/blocks/{block_id}")
def alias_update_block(workspace_id: str, block_id: str, payload: BlockUpdatePayload, user_id: str | None = Header(default=None, alias="X-User-Id")):
    return update_block(workspace_id=workspace_id, block_id=block_id, payload=payload, user_id=user_id)


@alias_router.delete("/workspaces/{workspace_id}/blocks/{block_id}")
def alias_delete_block(workspace_id: str, block_id: str, user_id: str | None = Header(default=None, alias="X-User-Id")):
    return delete_block(workspace_id=workspace_id, block_id=block_id, user_id=user_id)


@alias_router.post("/workspaces/{workspace_id}/ai-suggest", response_model=WorkspaceAiSuggestResponse)
async def alias_ai_suggest_workspace(
    workspace_id: str,
    payload: WorkspaceAiSuggestPayload,
    request: Request,
    user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    return await ai_suggest_workspace(workspace_id=workspace_id, payload=payload, request=request, user_id=user_id)


def _update_json_resource(
    *,
    table: str,
    row_mapper,
    workspace_id: str,
    resource_id: str,
    user_id: str,
    payload: dict[str, Any],
    returning: str,
):
    assignments: list[str] = []
    params: dict[str, Any] = {"resource_id": resource_id, "workspace_id": workspace_id, "user_id": user_id}
    for column, value in payload.items():
        if value is not None:
            assignments.append(f"{column} = %({column})s")
            params[column] = value
    if not assignments:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    assignments.extend(["updated_at = now()", "server_rev = server_rev + 1"])
    with get_conn() as conn:
        conn.row_factory = dict_row
        _require_workspace(conn, workspace_id, user_id)
        _resource_belongs_to_user(conn, table, resource_id, workspace_id, user_id)
        row = conn.execute(
            f"""
            UPDATE {table}
            SET {", ".join(assignments)}
            WHERE id = %(resource_id)s AND workspace_id = %(workspace_id)s AND user_id = %(user_id)s AND deleted_at IS NULL
            RETURNING {returning}
            """,
            params,
        ).fetchone()
        conn.commit()
    log.info("study_resource_updated", table=table, resource_id=resource_id, workspace_id=workspace_id, user_id=user_id)
    return row_mapper(row)


def _soft_delete_resource(table: str, resource_id: str, workspace_id: str, user_id: str, event_name: str):
    with get_conn() as conn:
        conn.row_factory = dict_row
        _require_workspace(conn, workspace_id, user_id)
        _resource_belongs_to_user(conn, table, resource_id, workspace_id, user_id)
        conn.execute(
            f"""
            UPDATE {table}
            SET deleted_at = now(), updated_at = now(), server_rev = server_rev + 1
            WHERE id = %(resource_id)s AND workspace_id = %(workspace_id)s AND user_id = %(user_id)s
            """,
            {"resource_id": resource_id, "workspace_id": workspace_id, "user_id": user_id},
        )
        conn.commit()
    log.info(event_name, resource_id=resource_id, workspace_id=workspace_id, user_id=user_id)
    return {"deleted": True}


def _normalize_block_type(value: str) -> str:
    allowed = {"personal_note", "post_it", "scripture", "quote", "reflection", "doctrinal_analysis"}
    aliases = {
        "ai_quote": "quote",
        "manual_reference": "quote",
        "ai_doctrinal_analysis": "doctrinal_analysis",
        "reflection_question": "reflection",
    }
    normalized = aliases.get(value, value)
    return normalized if normalized in allowed else "personal_note"


def _block_metadata(payload: BlockPayload, block_type: str, sort_order: int) -> dict[str, Any]:
    return {
        "blockType": block_type,
        "title": payload.title,
        "sourceTitle": payload.sourceTitle,
        "sourceAuthor": payload.sourceAuthor,
        "sourceReference": payload.sourceReference,
        "sourceUrl": payload.sourceUrl,
        "quoteText": payload.quoteText,
        "isAiGenerated": payload.isAiGenerated,
        "sortOrder": sort_order,
    }


def _find_block_note(conn, workspace_id: str, block_id: str, user_id: str) -> dict | None:
    return conn.execute(
        """
        SELECT id::text, workspace_id::text, user_id::text, document_id::text, chunk_id::text,
               title, content, selected_text, selection_range, scripture_refs, color, position,
               created_at, updated_at
        FROM study_notes
        WHERE id = %(block_id)s AND workspace_id = %(workspace_id)s AND user_id = %(user_id)s AND deleted_at IS NULL
        """,
        {"block_id": block_id, "workspace_id": workspace_id, "user_id": user_id},
    ).fetchone()


def _find_block_post_it(conn, workspace_id: str, block_id: str, user_id: str) -> dict | None:
    return conn.execute(
        """
        SELECT id::text, workspace_id::text, user_id::text, document_id::text, content, color,
               position, source_filters, pinned, created_at, updated_at
        FROM post_its
        WHERE id = %(block_id)s AND workspace_id = %(workspace_id)s AND user_id = %(user_id)s AND deleted_at IS NULL
        """,
        {"block_id": block_id, "workspace_id": workspace_id, "user_id": user_id},
    ).fetchone()


def _workspace_blocks(conn, workspace_id: str, user_id: str) -> list[dict[str, Any]]:
    notes = conn.execute(
        """
        SELECT id::text, workspace_id::text, user_id::text, document_id::text, chunk_id::text,
               title, content, selected_text, selection_range, scripture_refs, color, position,
               created_at, updated_at
        FROM study_notes
        WHERE workspace_id = %(workspace_id)s AND user_id = %(user_id)s AND deleted_at IS NULL
        """,
        {"workspace_id": workspace_id, "user_id": user_id},
    ).fetchall()
    post_its = conn.execute(
        """
        SELECT id::text, workspace_id::text, user_id::text, document_id::text, content, color,
               position, source_filters, pinned, created_at, updated_at
        FROM post_its
        WHERE workspace_id = %(workspace_id)s AND user_id = %(user_id)s AND deleted_at IS NULL
        """,
        {"workspace_id": workspace_id, "user_id": user_id},
    ).fetchall()
    blocks = [_note_block_row(row) for row in notes] + [_post_it_block_row(row) for row in post_its]
    return sorted(blocks, key=lambda item: (item["sortOrder"], item.get("createdAt") or ""))


def _next_block_sort_order(conn, workspace_id: str, user_id: str) -> int:
    blocks = _workspace_blocks(conn, workspace_id, user_id)
    if not blocks:
        return 10
    return max(int(block.get("sortOrder") or 0) for block in blocks) + 10


def _workspace_row(row: dict) -> dict:
    settings = row["settings"] or {}
    return {
        "id": row["id"],
        "userId": row["user_id"],
        "name": row["name"],
        "title": settings.get("title") or row["name"],
        "scriptureReference": settings.get("scriptureReference") or settings.get("mainReference") or row["description"],
        "scriptureText": settings.get("scriptureText"),
        "personalThought": settings.get("personalThought"),
        "topic": settings.get("topic"),
        "callingContext": settings.get("callingContext"),
        "description": row["description"],
        "sourceFilters": row["source_filters"] or {},
        "settings": settings,
        "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
        "updatedAt": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


def _source_filter_row(row: dict) -> dict:
    return {
        "id": row["id"],
        "workspaceId": row["workspace_id"],
        "userId": row["user_id"],
        "sourceKey": row["source_key"],
        "language": row["language"],
        "author": row["author"],
        "category": row["category"],
        "tags": row["tags"] or [],
        "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
        "updatedAt": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


def _note_row(row: dict) -> dict:
    return {
        "id": row["id"],
        "workspaceId": row["workspace_id"],
        "userId": row["user_id"],
        "documentId": row["document_id"],
        "chunkId": row["chunk_id"],
        "title": row["title"],
        "content": row["content"],
        "selectedText": row["selected_text"],
        "selectionRange": row["selection_range"] or {},
        "scriptureRefs": row["scripture_refs"] or [],
        "color": row["color"],
        "position": row["position"] or {},
        "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
        "updatedAt": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


def _highlight_row(row: dict) -> dict:
    return {
        "id": row["id"],
        "workspaceId": row["workspace_id"],
        "userId": row["user_id"],
        "documentId": row["document_id"],
        "chunkId": row["chunk_id"],
        "noteId": row["note_id"],
        "startChar": row["start_char"],
        "endChar": row["end_char"],
        "selectedText": row["selected_text"],
        "scriptureRefs": row["scripture_refs"] or [],
        "color": row["color"],
        "metadata": row["metadata"] or {},
        "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
        "updatedAt": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


def _citation_row(row: dict) -> dict:
    return {
        "id": row["id"],
        "workspaceId": row["workspace_id"],
        "userId": row["user_id"],
        "documentId": row["document_id"],
        "chunkId": row["chunk_id"],
        "quote": row["quote"],
        "selectedText": row.get("selected_text"),
        "citationUrl": row.get("citation_url"),
        "sourceUrl": row.get("source_url"),
        "sourceTitle": row.get("source_title"),
        "sourceAuthor": row.get("source_author"),
        "sourceType": row.get("source_type") or (row.get("metadata") or {}).get("sourceType"),
        "sourceName": row.get("source_name") or (row.get("metadata") or {}).get("sourceName"),
        "location": row.get("location") or {},
        "scriptureRefs": row.get("scripture_refs") or [],
        "metadata": row.get("metadata") or {},
        "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
        "updatedAt": row["updated_at"].isoformat() if row.get("updated_at") else None,
    }


def _post_it_row(row: dict) -> dict:
    return {
        "id": row["id"],
        "workspaceId": row["workspace_id"],
        "userId": row["user_id"],
        "documentId": row["document_id"],
        "content": row["content"],
        "color": row["color"],
        "position": row["position"] or {},
        "sourceFilters": row["source_filters"] or {},
        "pinned": row["pinned"],
        "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
        "updatedAt": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


def _note_block_row(row: dict) -> dict[str, Any]:
    position = row["position"] or {}
    block_type = _normalize_block_type(position.get("blockType") or ("quote" if row["selected_text"] else "personal_note"))
    title = position.get("title") or row["title"] or ("Cita manual" if block_type == "quote" else "Nota")
    return {
        "id": row["id"],
        "workspaceId": row["workspace_id"],
        "type": block_type,
        "title": title,
        "content": row["content"] or "",
        "quoteText": row["selected_text"] or position.get("quoteText"),
        "sourceTitle": position.get("sourceTitle"),
        "sourceAuthor": position.get("sourceAuthor"),
        "sourceReference": position.get("sourceReference"),
        "sourceUrl": position.get("sourceUrl"),
        "isAiGenerated": bool(position.get("isAiGenerated", False)),
        "sortOrder": int(position.get("sortOrder") or 0),
        "metadata": position,
        "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
        "updatedAt": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


def _post_it_block_row(row: dict) -> dict[str, Any]:
    position = row["position"] or {}
    return {
        "id": row["id"],
        "workspaceId": row["workspace_id"],
        "type": "post_it",
        "title": position.get("title") or "Post-it",
        "content": row["content"] or "",
        "quoteText": position.get("quoteText"),
        "sourceTitle": position.get("sourceTitle"),
        "sourceAuthor": position.get("sourceAuthor"),
        "sourceReference": position.get("sourceReference"),
        "sourceUrl": position.get("sourceUrl"),
        "isAiGenerated": bool(position.get("isAiGenerated", False)),
        "sortOrder": int(position.get("sortOrder") or 0),
        "metadata": {**position, "display": "post_it", "color": row["color"]},
        "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
        "updatedAt": row["updated_at"].isoformat() if row["updated_at"] else None,
    }
