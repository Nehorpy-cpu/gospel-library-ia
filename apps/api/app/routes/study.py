from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field
from psycopg.types.json import Jsonb

from app.services.db import get_conn

router = APIRouter(prefix="/api/study-workspaces")


class WorkspacePayload(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    userId: str | None = None
    sourceFilters: dict[str, Any] = Field(default_factory=dict)
    settings: dict[str, Any] = Field(default_factory=dict)


class NotePayload(BaseModel):
    documentId: str | None = None
    chunkId: str | None = None
    title: str | None = None
    content: str = Field(min_length=1)
    color: str = "yellow"
    position: dict[str, Any] = Field(default_factory=dict)


class CitationPayload(BaseModel):
    documentId: str
    chunkId: str | None = None
    quote: str = Field(min_length=1)
    citationUrl: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PostItPayload(BaseModel):
    documentId: str | None = None
    content: str = Field(min_length=1)
    color: str = "yellow"
    position: dict[str, Any] = Field(default_factory=dict)
    pinned: bool = False


@router.get("")
def list_workspaces(userId: str | None = None, limit: int = 50):
    limit = max(1, min(limit, 100))
    where = "WHERE user_id = %(user_id)s" if userId else ""
    params = {"limit": limit}
    if userId:
        params["user_id"] = userId
    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT id::text, user_id::text, name, description, source_filters, settings, created_at, updated_at
            FROM study_workspaces
            {where}
            ORDER BY updated_at DESC
            LIMIT %(limit)s
            """,
            params,
        ).fetchall()
    return {"items": [_workspace_row(row) for row in rows]}


@router.post("")
def create_workspace(payload: WorkspacePayload):
    with get_conn() as conn:
        row = conn.execute(
            """
            INSERT INTO study_workspaces (user_id, name, description, source_filters, settings)
            VALUES (%(user_id)s, %(name)s, %(description)s, %(source_filters)s, %(settings)s)
            RETURNING id::text, user_id::text, name, description, source_filters, settings, created_at, updated_at
            """,
            {
                "user_id": payload.userId,
                "name": payload.name,
                "description": payload.description,
                "source_filters": Jsonb(payload.sourceFilters),
                "settings": Jsonb(payload.settings),
            },
        ).fetchone()
        conn.commit()
    return _workspace_row(row)


@router.get("/{workspace_id}/notes")
def list_notes(workspace_id: str):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id::text, workspace_id::text, document_id::text, chunk_id::text, title, content, color, position, created_at, updated_at
            FROM study_notes
            WHERE workspace_id = %s AND deleted_at IS NULL
            ORDER BY updated_at DESC
            """,
            (workspace_id,),
        ).fetchall()
    return {"items": [_note_row(row) for row in rows]}


@router.post("/{workspace_id}/notes")
def create_note(workspace_id: str, payload: NotePayload):
    with get_conn() as conn:
        row = conn.execute(
            """
            INSERT INTO study_notes (workspace_id, document_id, chunk_id, title, content, color, position)
            VALUES (%(workspace_id)s, %(document_id)s, %(chunk_id)s, %(title)s, %(content)s, %(color)s, %(position)s)
            RETURNING id::text, workspace_id::text, document_id::text, chunk_id::text, title, content, color, position, created_at, updated_at
            """,
            {
                "workspace_id": workspace_id,
                "document_id": payload.documentId,
                "chunk_id": payload.chunkId,
                "title": payload.title,
                "content": payload.content,
                "color": payload.color,
                "position": Jsonb(payload.position),
            },
        ).fetchone()
        conn.commit()
    return _note_row(row)


@router.post("/{workspace_id}/citations")
def save_citation(workspace_id: str, payload: CitationPayload):
    with get_conn() as conn:
        row = conn.execute(
            """
            INSERT INTO saved_citations (workspace_id, document_id, chunk_id, quote, citation_url, metadata)
            VALUES (%(workspace_id)s, %(document_id)s, %(chunk_id)s, %(quote)s, %(citation_url)s, %(metadata)s)
            RETURNING id::text, workspace_id::text, document_id::text, chunk_id::text, quote, citation_url, metadata, created_at
            """,
            {
                "workspace_id": workspace_id,
                "document_id": payload.documentId,
                "chunk_id": payload.chunkId,
                "quote": payload.quote,
                "citation_url": payload.citationUrl,
                "metadata": Jsonb(payload.metadata),
            },
        ).fetchone()
        conn.commit()
    return {
        "id": row[0],
        "workspaceId": row[1],
        "documentId": row[2],
        "chunkId": row[3],
        "quote": row[4],
        "citationUrl": row[5],
        "metadata": row[6] or {},
        "createdAt": row[7].isoformat() if row[7] else None,
    }


@router.post("/{workspace_id}/post-its")
def create_post_it(workspace_id: str, payload: PostItPayload):
    with get_conn() as conn:
        row = conn.execute(
            """
            INSERT INTO post_its (workspace_id, document_id, content, color, position, pinned)
            VALUES (%(workspace_id)s, %(document_id)s, %(content)s, %(color)s, %(position)s, %(pinned)s)
            RETURNING id::text, workspace_id::text, document_id::text, content, color, position, pinned, created_at, updated_at
            """,
            {
                "workspace_id": workspace_id,
                "document_id": payload.documentId,
                "content": payload.content,
                "color": payload.color,
                "position": Jsonb(payload.position),
                "pinned": payload.pinned,
            },
        ).fetchone()
        conn.commit()
    return {
        "id": row[0],
        "workspaceId": row[1],
        "documentId": row[2],
        "content": row[3],
        "color": row[4],
        "position": row[5] or {},
        "pinned": row[6],
        "createdAt": row[7].isoformat() if row[7] else None,
        "updatedAt": row[8].isoformat() if row[8] else None,
    }


def _workspace_row(row) -> dict:
    return {
        "id": row[0],
        "userId": row[1],
        "name": row[2],
        "description": row[3],
        "sourceFilters": row[4] or {},
        "settings": row[5] or {},
        "createdAt": row[6].isoformat() if row[6] else None,
        "updatedAt": row[7].isoformat() if row[7] else None,
    }


def _note_row(row) -> dict:
    return {
        "id": row[0],
        "workspaceId": row[1],
        "documentId": row[2],
        "chunkId": row[3],
        "title": row[4],
        "content": row[5],
        "color": row[6],
        "position": row[7] or {},
        "createdAt": row[8].isoformat() if row[8] else None,
        "updatedAt": row[9].isoformat() if row[9] else None,
    }
