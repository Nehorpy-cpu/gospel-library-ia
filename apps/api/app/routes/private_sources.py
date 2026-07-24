from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.routes.study import current_user_id
from app.services.auth import require_study_user
from app.services.db import get_conn
from app.services.spanish_text import normalize_json_text_fields, normalize_tag_es, normalize_text_es

router = APIRouter(prefix="/api/user-private-sources", tags=["private-sources"], dependencies=[Depends(require_study_user)])
alias_router = APIRouter(prefix="/api/study/private-sources", tags=["private-sources"], dependencies=[Depends(require_study_user)])
SourceType = Literal["book", "manual", "scripture_note", "discourse", "personal_note", "quote", "institute_manual", "byu_speech", "church_manual", "other"]


class PrivateSourcePayload(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    author: str | None = Field(default=None, max_length=240)
    source_type: SourceType = Field(validation_alias="sourceType")
    reference: str | None = Field(default=None, max_length=500)
    citation_text: str | None = Field(default=None, max_length=3000, validation_alias="citationText")
    personal_note: str | None = Field(default=None, max_length=5000, validation_alias="personalNote")
    tags: list[str] = Field(default_factory=list, max_length=20)
    topic: str | None = Field(default=None, max_length=200)
    scripture_reference: str | None = Field(default=None, max_length=240, validation_alias="scriptureReference")

    @field_validator("tags")
    @classmethod
    def normalized_tags(cls, tags: list[str]) -> list[str]:
        return [normalize_tag_es(tag) for tag in tags if normalize_tag_es(tag)][:20]


def _row(row: dict) -> dict:
    return normalize_json_text_fields({
        "id": row["id"], "user_id": row["user_id"], "title": row["title"], "author": row["author"],
        "source_type": row["source_type"], "reference": row["reference"], "citation_text": row["citation_text"],
        "personal_note": row["personal_note"], "tags": row["tags"] or [], "topic": row["topic"],
        "scripture_reference": row["scripture_reference"], "archived_at": row["archived_at"],
        "created_at": row["created_at"], "updated_at": row["updated_at"],
    })


def _require(conn, source_id: str, user_id: str) -> dict:
    row = conn.execute("SELECT id::text AS id, user_id::text AS user_id, title, author, source_type, reference, citation_text, personal_note, tags, topic, scripture_reference, archived_at, created_at, updated_at FROM user_private_sources WHERE id=%(id)s AND user_id=%(user_id)s", {"id": source_id, "user_id": user_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Fuente privada no encontrada")
    return row


@router.get("")
@alias_router.get("")
def list_sources(user_id: str | None = Header(default=None, alias="X-User-Id"), q: str | None = None, source_type: SourceType | None = Query(default=None), include_archived: bool = False):
    user_id = current_user_id(user_id)
    where, params = ["user_id=%(user_id)s"], {"user_id": user_id}
    if not include_archived: where.append("archived_at IS NULL")
    if source_type: where.append("source_type=%(source_type)s"); params["source_type"] = source_type
    if q: where.append("concat_ws(' ', title, author, reference, citation_text, personal_note, topic, tags::text) ILIKE %(q)s"); params["q"] = f"%{normalize_text_es(q)}%"
    with get_conn() as conn:
        conn.row_factory = dict_row
        rows = conn.execute(f"SELECT id::text AS id, user_id::text AS user_id, title, author, source_type, reference, citation_text, personal_note, tags, topic, scripture_reference, archived_at, created_at, updated_at FROM user_private_sources WHERE {' AND '.join(where)} ORDER BY updated_at DESC LIMIT 100", params).fetchall()
    return {"items": [_row(row) for row in rows]}


@router.post("", status_code=status.HTTP_201_CREATED)
@alias_router.post("", status_code=status.HTTP_201_CREATED)
def create_source(payload: PrivateSourcePayload, user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = current_user_id(user_id); data = normalize_json_text_fields(payload.model_dump())
    with get_conn() as conn:
        conn.row_factory = dict_row
        row = conn.execute("INSERT INTO user_private_sources (user_id,title,author,source_type,reference,citation_text,personal_note,tags,topic,scripture_reference) VALUES (%(user_id)s,%(title)s,%(author)s,%(source_type)s,%(reference)s,%(citation_text)s,%(personal_note)s,%(tags)s,%(topic)s,%(scripture_reference)s) RETURNING id::text AS id,user_id::text AS user_id,title,author,source_type,reference,citation_text,personal_note,tags,topic,scripture_reference,archived_at,created_at,updated_at", {**data,"user_id":user_id,"tags":Jsonb(data["tags"])}).fetchone(); conn.commit()
    return _row(row)


@router.get("/{source_id}")
def get_source(source_id: str, user_id: str | None = Header(default=None, alias="X-User-Id")):
    with get_conn() as conn: conn.row_factory = dict_row; return _row(_require(conn, source_id, current_user_id(user_id)))


@router.patch("/{source_id}")
def update_source(source_id: str, payload: PrivateSourcePayload, user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = current_user_id(user_id); data = normalize_json_text_fields(payload.model_dump())
    with get_conn() as conn:
        conn.row_factory = dict_row; _require(conn, source_id, user_id)
        row = conn.execute("UPDATE user_private_sources SET title=%(title)s,author=%(author)s,source_type=%(source_type)s,reference=%(reference)s,citation_text=%(citation_text)s,personal_note=%(personal_note)s,tags=%(tags)s,topic=%(topic)s,scripture_reference=%(scripture_reference)s,updated_at=now() WHERE id=%(id)s AND user_id=%(user_id)s RETURNING id::text AS id,user_id::text AS user_id,title,author,source_type,reference,citation_text,personal_note,tags,topic,scripture_reference,archived_at,created_at,updated_at", {**data,"id":source_id,"user_id":user_id,"tags":Jsonb(data["tags"])}).fetchone(); conn.commit()
    return _row(row)


@router.delete("/{source_id}")
def archive_source(source_id: str, user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = current_user_id(user_id)
    with get_conn() as conn: _require(conn, source_id, user_id); conn.execute("UPDATE user_private_sources SET archived_at=now(),updated_at=now() WHERE id=%s AND user_id=%s", (source_id,user_id)); conn.commit()
    return {"deleted": True}
