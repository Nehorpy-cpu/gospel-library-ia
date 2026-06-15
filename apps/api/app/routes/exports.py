from __future__ import annotations

from datetime import UTC, datetime
from textwrap import wrap
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.logging import logger
from app.core.config import get_settings
from app.services.auth import get_request_auth_context, normalize_user_id, require_user
from app.services.db import get_conn
from app.services.rate_limit import RateLimiter

router = APIRouter(prefix="/api/exports", tags=["exports"], dependencies=[Depends(require_user)])
log = logger(__name__)
limiter = RateLimiter()

ExportKind = Literal["notes", "quotes", "talk_drafts", "all"]
ExportFormat = Literal["markdown", "pdf"]


class StudyExportPayload(BaseModel):
    workspaceId: str
    kind: ExportKind = "all"
    format: ExportFormat = "markdown"
    noteIds: list[str] = Field(default_factory=list)
    citationIds: list[str] = Field(default_factory=list)

    @field_validator("noteIds", "citationIds")
    @classmethod
    def validate_ids(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for item in value:
            try:
                cleaned.append(str(UUID(item)))
            except (TypeError, ValueError) as exc:
                raise ValueError("Invalid resource id") from exc
        return cleaned


def current_user_id(x_user_id: str | None = Header(default=None, alias="X-User-Id")) -> str:
    if not x_user_id:
        context = get_request_auth_context()
        if context:
            return context.user_id
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return normalize_user_id(x_user_id)


@router.post("/study")
async def export_study_material(
    payload: StudyExportPayload,
    request: Request,
    user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    await limiter.check_daily(request, get_settings().max_user_exports_per_day, "exports")
    user_id = current_user_id(user_id)
    with get_conn() as conn:
        conn.row_factory = dict_row
        workspace = _require_workspace(conn, payload.workspaceId, user_id)
        notes = _load_notes(conn, payload, user_id)
        citations = _load_citations(conn, payload, user_id)
        _record_export(conn, user_id, payload, len(notes), len(citations))
        conn.commit()

    markdown = _render_markdown(workspace, notes, citations, payload.kind)
    filename = _filename(workspace["name"], payload.kind, payload.format)
    log.info(
        "study_export_created",
        workspace_id=payload.workspaceId,
        user_id=user_id,
        kind=payload.kind,
        format=payload.format,
        notes=len(notes),
        citations=len(citations),
    )
    if payload.format == "pdf":
        return Response(
            content=_markdown_to_pdf(markdown, title=workspace["name"]),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    return Response(
        content=markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _require_workspace(conn, workspace_id: str, user_id: str) -> dict:
    row = conn.execute(
        """
        SELECT id::text, name, description
        FROM study_workspaces
        WHERE id = %(workspace_id)s AND user_id = %(user_id)s AND deleted_at IS NULL
        """,
        {"workspace_id": workspace_id, "user_id": user_id},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study workspace not found")
    return row


def _record_export(conn, user_id: str, payload: StudyExportPayload, notes: int, citations: int) -> None:
    conn.execute(
        """
        INSERT INTO beta_activity_events (user_id, kind, metadata)
        VALUES (%(user_id)s, 'export', %(metadata)s)
        """,
        {
            "user_id": user_id,
            "metadata": Jsonb(
                {
                    "workspaceId": payload.workspaceId,
                    "kind": payload.kind,
                    "format": payload.format,
                    "notes": notes,
                    "citations": citations,
                }
            ),
        },
    )


def _load_notes(conn, payload: StudyExportPayload, user_id: str) -> list[dict]:
    if payload.kind == "quotes":
        return []
    where = ["sn.workspace_id = %(workspace_id)s", "sn.user_id = %(user_id)s", "sn.deleted_at IS NULL"]
    params: dict[str, Any] = {"workspace_id": payload.workspaceId, "user_id": user_id}
    if payload.kind == "talk_drafts":
        where.append("sn.position->>'type' = 'talk_builder_draft'")
    elif payload.kind == "notes":
        where.append("(sn.position->>'type' IS DISTINCT FROM 'talk_builder_draft')")
    if payload.noteIds:
        where.append("sn.id::text = ANY(%(note_ids)s)")
        params["note_ids"] = payload.noteIds
    return list(
        conn.execute(
            f"""
            SELECT
              sn.id::text,
              sn.title,
              sn.content,
              sn.selected_text,
              sn.scripture_refs,
              sn.position,
              sn.created_at,
              sn.updated_at,
              d.title AS document_title,
              d.author AS document_author,
              COALESCE(d.raw_metadata->>'source_url', d.canonical_url) AS source_url
            FROM study_notes sn
            LEFT JOIN documents d ON d.id = sn.document_id
            WHERE {" AND ".join(where)}
            ORDER BY sn.updated_at DESC
            """,
            params,
        ).fetchall()
    )


def _load_citations(conn, payload: StudyExportPayload, user_id: str) -> list[dict]:
    if payload.kind in {"notes", "talk_drafts"}:
        return []
    where = ["sc.workspace_id = %(workspace_id)s", "sc.user_id = %(user_id)s", "sc.deleted_at IS NULL"]
    params: dict[str, Any] = {"workspace_id": payload.workspaceId, "user_id": user_id}
    if payload.citationIds:
        where.append("sc.id::text = ANY(%(citation_ids)s)")
        params["citation_ids"] = payload.citationIds
    return list(
        conn.execute(
            f"""
            SELECT
              sc.id::text,
              sc.quote,
              sc.selected_text,
              sc.citation_url,
              sc.source_url,
              sc.source_title,
              sc.source_author,
              sc.location,
              sc.scripture_refs,
              sc.created_at,
              sc.updated_at
            FROM saved_citations sc
            WHERE {" AND ".join(where)}
            ORDER BY sc.updated_at DESC
            """,
            params,
        ).fetchall()
    )


def _render_markdown(workspace: dict, notes: list[dict], citations: list[dict], kind: ExportKind) -> str:
    lines = [
        f"# {workspace['name']}",
        "",
        f"Export type: {kind}",
        f"Generated at: {datetime.now(UTC).isoformat()}",
        "",
    ]
    if workspace.get("description"):
        lines.extend([workspace["description"], ""])
    if notes:
        lines.extend(["## Notes and talk drafts", ""])
        for note in notes:
            title = note["title"] or "Untitled note"
            lines.extend([f"### {title}", ""])
            if note.get("selected_text"):
                lines.extend([f"> {note['selected_text']}", ""])
            lines.extend([note["content"] or "", ""])
            lines.extend(_source_lines(note))
            lines.append("")
    if citations:
        lines.extend(["## Saved quotes", ""])
        for citation in citations:
            title = citation["source_title"] or "Saved quote"
            lines.extend([f"### {title}", "", f"> {citation['quote']}", ""])
            if citation.get("source_author"):
                lines.append(f"- Autor: {citation['source_author']}")
            url = citation.get("citation_url") or citation.get("source_url")
            if url:
                lines.append(f"- URL de fuente: {url}")
            refs = citation.get("scripture_refs") or []
            if refs:
                lines.append(f"- Scripture refs: {', '.join(refs)}")
            lines.append("")
    if not notes and not citations:
        lines.extend(["No owned study material matched this export request.", ""])
    return "\n".join(lines).strip() + "\n"


def _source_lines(row: dict) -> list[str]:
    lines: list[str] = []
    if row.get("document_title"):
        lines.append(f"- Fuente: {row['document_title']}")
    if row.get("document_author"):
        lines.append(f"- Autor: {row['document_author']}")
    if row.get("source_url"):
        lines.append(f"- URL de fuente: {row['source_url']}")
    refs = row.get("scripture_refs") or []
    if refs:
        lines.append(f"- Scripture refs: {', '.join(refs)}")
    return lines


def _filename(workspace_name: str, kind: str, format_name: str) -> str:
    stem = "".join(char.lower() if char.isalnum() else "-" for char in workspace_name).strip("-") or "study-export"
    extension = "md" if format_name == "markdown" else "pdf"
    return f"{stem}-{kind}.{extension}"


def _markdown_to_pdf(markdown: str, title: str) -> bytes:
    lines: list[str] = []
    for raw_line in markdown.splitlines():
        text = raw_line.replace("#", "").replace(">", "").strip()
        if not text:
            lines.append("")
        else:
            lines.extend(wrap(text, width=88) or [""])
    pages = [lines[index : index + 44] for index in range(0, len(lines), 44)] or [[title]]
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Count {len(pages)} /Kids [{' '.join(f'{3 + i * 2} 0 R' for i in range(len(pages)))}] >>".encode(
            "latin-1"
        ),
    ]
    for page_index, page_lines in enumerate(pages):
        page_obj = 3 + page_index * 2
        stream_obj = page_obj + 1
        content = _pdf_page_stream(page_lines)
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /Contents {stream_obj} 0 R >>".encode(
                "latin-1"
            )
        )
        objects.append(b"<< /Length " + str(len(content)).encode("latin-1") + b" >>\nstream\n" + content + b"\nendstream")
    offsets = [0]
    body = bytearray(b"%PDF-1.4\n")
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(body))
        body.extend(f"{index} 0 obj\n".encode("latin-1"))
        body.extend(obj)
        body.extend(b"\nendobj\n")
    xref_offset = len(body)
    body.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    body.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        body.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
    body.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("latin-1")
    )
    return bytes(body)


def _pdf_page_stream(lines: list[str]) -> bytes:
    commands = ["BT", "/F1 11 Tf", "50 750 Td", "14 TL"]
    for line in lines:
        commands.append(f"({_pdf_escape(line)}) Tj")
        commands.append("T*")
    commands.append("ET")
    return "\n".join(commands).encode("latin-1", errors="replace")


def _pdf_escape(value: str) -> str:
    cleaned = value.encode("latin-1", errors="replace").decode("latin-1")
    return cleaned.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
