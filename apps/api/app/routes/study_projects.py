from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.config import get_settings
from app.core.logging import logger
from app.schemas.study_projects import (
    AiSuggestPayload,
    AiSuggestResponse,
    StudyBlockPayload,
    StudyBlockUpdatePayload,
    StudyProjectPayload,
    StudyProjectUpdatePayload,
    StudySourcePayload,
    UserPrivateSourcePayload,
)
from app.services.auth import get_request_auth_context, normalize_user_id, require_user
from app.services.db import get_conn
from app.services.rate_limit import RateLimiter
from app.services.study_ai import generate_suggestions, load_local_context, prompt_hash

router = APIRouter(prefix="/api/study-projects", tags=["study-projects"], dependencies=[Depends(require_user)])
limiter = RateLimiter()
log = logger(__name__)


def current_user_id(x_user_id: str | None = Header(default=None, alias="X-User-Id")) -> str:
    if x_user_id:
        return normalize_user_id(x_user_id)
    context = get_request_auth_context()
    if context:
        return context.user_id
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")


@router.get("")
def list_study_projects(
    user_id: str | None = Header(default=None, alias="X-User-Id"),
    includeArchived: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
):
    user_id = current_user_id(user_id)
    where = ["user_id = %(user_id)s"]
    if not includeArchived:
        where.append("archived_at IS NULL")
    with get_conn() as conn:
        conn.row_factory = dict_row
        rows = conn.execute(
            f"""
            SELECT id::text, user_id::text, title, scripture_reference, scripture_text,
                   personal_thought, topic, calling_context, created_at, updated_at, archived_at
            FROM study_projects
            WHERE {" AND ".join(where)}
            ORDER BY updated_at DESC
            LIMIT %(limit)s
            """,
            {"user_id": user_id, "limit": limit},
        ).fetchall()
    return {"items": [_project_row(row) for row in rows]}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_study_project(payload: StudyProjectPayload, user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = current_user_id(user_id)
    with get_conn() as conn:
        conn.row_factory = dict_row
        row = conn.execute(
            """
            INSERT INTO study_projects (
              user_id, title, scripture_reference, scripture_text, personal_thought, topic, calling_context
            )
            VALUES (
              %(user_id)s, %(title)s, %(scripture_reference)s, %(scripture_text)s,
              %(personal_thought)s, %(topic)s, %(calling_context)s
            )
            RETURNING id::text, user_id::text, title, scripture_reference, scripture_text,
                      personal_thought, topic, calling_context, created_at, updated_at, archived_at
            """,
            {
                "user_id": user_id,
                "title": payload.title,
                "scripture_reference": payload.scriptureReference,
                "scripture_text": payload.scriptureText,
                "personal_thought": payload.personalThought,
                "topic": payload.topic,
                "calling_context": payload.callingContext,
            },
        ).fetchone()
        _create_initial_project_blocks(conn, row["id"], payload)
        conn.commit()
    log.info("study_project_created", study_project_id=row["id"], user_id=user_id)
    return _project_row(row)


@router.get("/private-sources")
def list_private_sources(
    user_id: str | None = Header(default=None, alias="X-User-Id"),
    limit: int = Query(default=50, ge=1, le=100),
):
    user_id = current_user_id(user_id)
    with get_conn() as conn:
        conn.row_factory = dict_row
        rows = conn.execute(
            """
            SELECT id::text, user_id::text, title, author, source_type, citation_text, personal_note, tags,
                   created_at, updated_at
            FROM user_private_sources
            WHERE user_id = %(user_id)s
            ORDER BY updated_at DESC
            LIMIT %(limit)s
            """,
            {"user_id": user_id, "limit": limit},
        ).fetchall()
    return {"items": [_private_source_row(row) for row in rows]}


@router.post("/private-sources", status_code=status.HTTP_201_CREATED)
def create_private_source(payload: UserPrivateSourcePayload, user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = current_user_id(user_id)
    with get_conn() as conn:
        conn.row_factory = dict_row
        row = conn.execute(
            """
            INSERT INTO user_private_sources (user_id, title, author, source_type, citation_text, personal_note, tags)
            VALUES (%(user_id)s, %(title)s, %(author)s, %(source_type)s, %(citation_text)s, %(personal_note)s, %(tags)s)
            RETURNING id::text, user_id::text, title, author, source_type, citation_text, personal_note, tags,
                      created_at, updated_at
            """,
            {
                "user_id": user_id,
                "title": payload.title,
                "author": payload.author,
                "source_type": payload.sourceType,
                "citation_text": payload.citationText,
                "personal_note": payload.personalNote,
                "tags": Jsonb(payload.tags),
            },
        ).fetchone()
        conn.commit()
    return _private_source_row(row)


@router.get("/{project_id}")
def get_study_project(project_id: str, user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = current_user_id(user_id)
    with get_conn() as conn:
        conn.row_factory = dict_row
        project = _require_project(conn, project_id, user_id)
        blocks = _project_blocks(conn, project_id)
        sources = _project_sources(conn, project_id)
    return {**_project_row(project), "blocks": blocks, "sources": sources}


@router.patch("/{project_id}")
def update_study_project(
    project_id: str,
    payload: StudyProjectUpdatePayload,
    user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    user_id = current_user_id(user_id)
    updates: list[str] = []
    params: dict[str, Any] = {"project_id": project_id, "user_id": user_id}
    mapping = {
        "title": payload.title,
        "scripture_reference": payload.scriptureReference,
        "scripture_text": payload.scriptureText,
        "personal_thought": payload.personalThought,
        "topic": payload.topic,
        "calling_context": payload.callingContext,
    }
    for column, value in mapping.items():
        if value is not None:
            updates.append(f"{column} = %({column})s")
            params[column] = value
    if payload.archived is not None:
        updates.append("archived_at = CASE WHEN %(archived)s THEN now() ELSE NULL END")
        params["archived"] = payload.archived
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    updates.append("updated_at = now()")
    with get_conn() as conn:
        conn.row_factory = dict_row
        _require_project(conn, project_id, user_id)
        row = conn.execute(
            f"""
            UPDATE study_projects
            SET {", ".join(updates)}
            WHERE id = %(project_id)s AND user_id = %(user_id)s
            RETURNING id::text, user_id::text, title, scripture_reference, scripture_text,
                      personal_thought, topic, calling_context, created_at, updated_at, archived_at
            """,
            params,
        ).fetchone()
        conn.commit()
    return _project_row(row)


@router.delete("/{project_id}")
def archive_study_project(project_id: str, user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = current_user_id(user_id)
    with get_conn() as conn:
        _require_project(conn, project_id, user_id)
        conn.execute(
            """
            UPDATE study_projects
            SET archived_at = now(), updated_at = now()
            WHERE id = %(project_id)s AND user_id = %(user_id)s
            """,
            {"project_id": project_id, "user_id": user_id},
        )
        conn.commit()
    return {"deleted": True}


@router.post("/{project_id}/blocks", status_code=status.HTTP_201_CREATED)
def create_block(
    project_id: str,
    payload: StudyBlockPayload,
    user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    user_id = current_user_id(user_id)
    with get_conn() as conn:
        conn.row_factory = dict_row
        _require_project(conn, project_id, user_id)
        sort_order = payload.sortOrder
        if sort_order is None:
            sort_order = _next_sort_order(conn, project_id)
        row = conn.execute(
            """
            INSERT INTO study_blocks (
              study_project_id, type, title, content, source_title, source_author, source_url,
              source_reference, quote_text, is_ai_generated, is_saved, is_deleted, sort_order, metadata
            )
            VALUES (
              %(project_id)s, %(type)s, %(title)s, %(content)s, %(source_title)s, %(source_author)s,
              %(source_url)s, %(source_reference)s, %(quote_text)s, %(is_ai_generated)s, %(is_saved)s,
              %(is_deleted)s, %(sort_order)s, %(metadata)s
            )
            RETURNING *
            """,
            _block_params(project_id, payload, sort_order),
        ).fetchone()
        _touch_project(conn, project_id)
        conn.commit()
    return _block_row(row)


@router.patch("/{project_id}/blocks/{block_id}")
def update_block(
    project_id: str,
    block_id: str,
    payload: StudyBlockUpdatePayload,
    user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    user_id = current_user_id(user_id)
    values = {
        "type": payload.type,
        "title": payload.title,
        "content": payload.content,
        "source_title": payload.sourceTitle,
        "source_author": payload.sourceAuthor,
        "source_url": payload.sourceUrl,
        "source_reference": payload.sourceReference,
        "quote_text": payload.quoteText,
        "is_saved": payload.isSaved,
        "is_deleted": payload.isDeleted,
        "sort_order": payload.sortOrder,
        "metadata": Jsonb(payload.metadata) if payload.metadata is not None else None,
    }
    updates = [f"{column} = %({column})s" for column, value in values.items() if value is not None]
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    params = {column: value for column, value in values.items() if value is not None}
    params.update({"project_id": project_id, "block_id": block_id, "user_id": user_id})
    updates.append("updated_at = now()")
    with get_conn() as conn:
        conn.row_factory = dict_row
        _require_project(conn, project_id, user_id)
        row = conn.execute(
            f"""
            UPDATE study_blocks
            SET {", ".join(updates)}
            WHERE id = %(block_id)s AND study_project_id = %(project_id)s
            RETURNING *
            """,
            params,
        ).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found")
        _touch_project(conn, project_id)
        conn.commit()
    return _block_row(row)


@router.delete("/{project_id}/blocks/{block_id}")
def delete_block(project_id: str, block_id: str, user_id: str | None = Header(default=None, alias="X-User-Id")):
    return update_block(project_id, block_id, StudyBlockUpdatePayload(isDeleted=True, isSaved=False), user_id)


@router.post("/{project_id}/sources", status_code=status.HTTP_201_CREATED)
def create_project_source(
    project_id: str,
    payload: StudySourcePayload,
    user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    user_id = current_user_id(user_id)
    with get_conn() as conn:
        conn.row_factory = dict_row
        _require_project(conn, project_id, user_id)
        row = conn.execute(
            """
            INSERT INTO study_sources (study_project_id, source_type, title, author, url, reference, notes)
            VALUES (%(project_id)s, %(source_type)s, %(title)s, %(author)s, %(url)s, %(reference)s, %(notes)s)
            RETURNING *
            """,
            {
                "project_id": project_id,
                "source_type": payload.sourceType,
                "title": payload.title,
                "author": payload.author,
                "url": payload.url,
                "reference": payload.reference,
                "notes": payload.notes,
            },
        ).fetchone()
        _touch_project(conn, project_id)
        conn.commit()
    return _source_row(row)


@router.post("/{project_id}/ai-suggest", response_model=AiSuggestResponse)
async def ai_suggest(
    project_id: str,
    payload: AiSuggestPayload,
    request: Request,
    user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    user_id = current_user_id(user_id)
    settings = get_settings()
    await limiter.check(request, settings.chat_rate_limit_per_minute, scope="study-ai")
    await limiter.check_daily(request, settings.max_user_study_ai_per_day, "study-ai")
    with get_conn() as conn:
        conn.row_factory = dict_row
        project = _require_project(conn, project_id, user_id)
        local_context = load_local_context(conn, project, user_id)
        hash_payload = {
            "project": _project_row(project),
            "prompt": payload.prompt,
            "blockTypes": payload.blockTypes,
            "preferredSources": payload.preferredSources,
            "mode": payload.mode,
            "maxSuggestions": min(payload.maxSuggestions, settings.study_ai_max_suggestions),
            "localContextIds": [item.get("documentId") or item.get("sourceId") or item.get("studyProjectId") for item in local_context],
        }
        suggestion_hash = prompt_hash(hash_payload)
        cached = conn.execute(
            """
            SELECT suggestions, warnings
            FROM study_ai_suggestion_cache
            WHERE study_project_id = %(project_id)s AND user_id = %(user_id)s AND prompt_hash = %(prompt_hash)s
            """,
            {"project_id": project_id, "user_id": user_id, "prompt_hash": suggestion_hash},
        ).fetchone()
        if cached:
            return {
                "suggestions": cached["suggestions"] or [],
                "cached": True,
                "mode": payload.mode,
                "warnings": cached["warnings"] or [],
                "localContext": local_context,
            }
    suggestions, warnings, provider = await generate_suggestions(
        project=project,
        user_id=user_id,
        payload=payload.model_dump(mode="json"),
        local_context=local_context,
    )
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO study_ai_suggestion_cache (
              study_project_id, user_id, prompt_hash, prompt, mode, requested_block_types,
              preferred_sources, suggestions, warnings, local_context
            )
            VALUES (
              %(project_id)s, %(user_id)s, %(prompt_hash)s, %(prompt)s, %(mode)s,
              %(requested_block_types)s, %(preferred_sources)s, %(suggestions)s, %(warnings)s,
              %(local_context)s
            )
            ON CONFLICT (study_project_id, user_id, prompt_hash)
            DO UPDATE SET suggestions = EXCLUDED.suggestions, warnings = EXCLUDED.warnings,
                          local_context = EXCLUDED.local_context, created_at = now()
            """,
            {
                "project_id": project_id,
                "user_id": user_id,
                "prompt_hash": suggestion_hash,
                "prompt": payload.prompt,
                "mode": payload.mode,
                "requested_block_types": Jsonb(payload.blockTypes),
                "preferred_sources": Jsonb(payload.preferredSources),
                "suggestions": Jsonb(suggestions),
                "warnings": Jsonb(warnings),
                "local_context": Jsonb(local_context),
            },
        )
        conn.commit()
    log.info("study_ai_suggestions_generated", study_project_id=project_id, user_id=user_id, provider=provider)
    return {
        "suggestions": suggestions,
        "cached": False,
        "mode": payload.mode,
        "warnings": warnings,
        "localContext": local_context,
    }


def _require_project(conn, project_id: str, user_id: str) -> dict:
    row = conn.execute(
        """
        SELECT id::text, user_id::text, title, scripture_reference, scripture_text,
               personal_thought, topic, calling_context, created_at, updated_at, archived_at
        FROM study_projects
        WHERE id = %(project_id)s AND user_id = %(user_id)s
        """,
        {"project_id": project_id, "user_id": user_id},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study project not found")
    return row


def _create_initial_project_blocks(conn, project_id: str, payload: StudyProjectPayload) -> None:
    sort_order = 10
    if payload.personalThought:
        conn.execute(
            """
            INSERT INTO study_blocks (study_project_id, type, title, content, is_ai_generated, is_saved, sort_order)
            VALUES (%s, 'personal_note', 'Mi pensamiento', %s, false, true, %s)
            """,
            (project_id, payload.personalThought, sort_order),
        )
        sort_order += 10
    if payload.scriptureReference:
        conn.execute(
            """
            INSERT INTO study_sources (study_project_id, source_type, title, reference, notes)
            VALUES (%s, 'scripture', %s, %s, %s)
            """,
            (project_id, payload.scriptureReference, payload.scriptureReference, payload.scriptureText),
        )


def _project_blocks(conn, project_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT *
        FROM study_blocks
        WHERE study_project_id = %(project_id)s AND is_deleted IS FALSE
        ORDER BY sort_order, created_at
        """,
        {"project_id": project_id},
    ).fetchall()
    return [_block_row(row) for row in rows]


def _project_sources(conn, project_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT *
        FROM study_sources
        WHERE study_project_id = %(project_id)s
        ORDER BY created_at DESC
        """,
        {"project_id": project_id},
    ).fetchall()
    return [_source_row(row) for row in rows]


def _next_sort_order(conn, project_id: str) -> int:
    row = conn.execute(
        "SELECT coalesce(max(sort_order), 0)::int + 10 AS next_order FROM study_blocks WHERE study_project_id = %s",
        (project_id,),
    ).fetchone()
    return int(row[0] if not isinstance(row, dict) else row["next_order"])


def _touch_project(conn, project_id: str) -> None:
    conn.execute("UPDATE study_projects SET updated_at = now() WHERE id = %s", (project_id,))


def _block_params(project_id: str, payload: StudyBlockPayload, sort_order: int) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "type": payload.type,
        "title": payload.title,
        "content": payload.content,
        "source_title": payload.sourceTitle,
        "source_author": payload.sourceAuthor,
        "source_url": payload.sourceUrl,
        "source_reference": payload.sourceReference,
        "quote_text": payload.quoteText,
        "is_ai_generated": payload.isAiGenerated,
        "is_saved": payload.isSaved,
        "is_deleted": payload.isDeleted,
        "sort_order": sort_order,
        "metadata": Jsonb(payload.metadata),
    }


def _project_row(row: dict) -> dict[str, Any]:
    return {
        "id": row["id"],
        "userId": row["user_id"],
        "title": row["title"],
        "scriptureReference": row["scripture_reference"],
        "scriptureText": row["scripture_text"],
        "personalThought": row["personal_thought"],
        "topic": row["topic"],
        "callingContext": row["calling_context"],
        "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
        "updatedAt": row["updated_at"].isoformat() if row["updated_at"] else None,
        "archivedAt": row["archived_at"].isoformat() if row["archived_at"] else None,
    }


def _block_row(row: dict) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "studyProjectId": str(row["study_project_id"]),
        "type": row["type"],
        "title": row["title"],
        "content": row["content"],
        "sourceTitle": row["source_title"],
        "sourceAuthor": row["source_author"],
        "sourceUrl": row["source_url"],
        "sourceReference": row["source_reference"],
        "quoteText": row["quote_text"],
        "isAiGenerated": row["is_ai_generated"],
        "isSaved": row["is_saved"],
        "isDeleted": row["is_deleted"],
        "sortOrder": row["sort_order"],
        "metadata": row["metadata"] or {},
        "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
        "updatedAt": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


def _source_row(row: dict) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "studyProjectId": str(row["study_project_id"]),
        "sourceType": row["source_type"],
        "title": row["title"],
        "author": row["author"],
        "url": row["url"],
        "reference": row["reference"],
        "notes": row["notes"],
        "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
    }


def _private_source_row(row: dict) -> dict[str, Any]:
    return {
        "id": row["id"],
        "userId": row["user_id"],
        "title": row["title"],
        "author": row["author"],
        "sourceType": row["source_type"],
        "citationText": row["citation_text"],
        "personalNote": row["personal_note"],
        "tags": row["tags"] or [],
        "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
        "updatedAt": row["updated_at"].isoformat() if row["updated_at"] else None,
    }
