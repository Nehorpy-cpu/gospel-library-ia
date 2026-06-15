from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.n8n_ingestion import normalized_name, slugify
from app.services.spanish_text import normalize_tag_es, normalize_text_es, normalize_visible_metadata


@dataclass
class Summary:
    documents: int = 0
    chunks: int = 0
    authors: int = 0
    tags: int = 0
    sources: int = 0


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def table_columns(conn, table: str) -> set[str]:
    return {
        row[0]
        for row in conn.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            """,
            (table,),
        ).fetchall()
    }


def json_value(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def normalize_tags(value: Any) -> list[str]:
    parsed = json_value(value)
    if not isinstance(parsed, list):
        return []
    return list(dict.fromkeys(normalize_tag_es(str(item)) for item in parsed if normalize_tag_es(str(item))))


def normalize_documents(conn, summary: Summary) -> None:
    columns = table_columns(conn, "documents")
    if not columns:
        return
    metadata_column = "raw_metadata" if "raw_metadata" in columns else "metadata"
    text_column = "text" if "text" in columns else "content_text"
    selected = ["id", "title"]
    for column in ("author", text_column, "tags", metadata_column, "content_hash"):
        if column in columns and column not in selected:
            selected.append(column)
    rows = conn.execute(f"SELECT {', '.join(selected)} FROM documents").fetchall()
    for row in rows:
        current = dict(zip(selected, row))
        updates: dict[str, Any] = {"title": normalize_text_es(current["title"])}
        if "author" in current:
            updates["author"] = normalize_text_es(current["author"]) if current["author"] else None
        if text_column in current:
            updates[text_column] = (
                normalize_text_es(current[text_column], preserve_newlines=True) if current[text_column] else None
            )
        if "tags" in current:
            updates["tags"] = json.dumps(normalize_tags(current["tags"]), ensure_ascii=False)
        if metadata_column in current:
            updates[metadata_column] = json.dumps(
                normalize_visible_metadata(json_value(current[metadata_column]) or {}),
                ensure_ascii=False,
            )
        if "content_hash" in current and updates.get(text_column):
            updates["content_hash"] = sha256_text(updates[text_column])
        changed = {
            key: value
            for key, value in updates.items()
            if json_value(current.get(key)) != json_value(value)
        }
        if not changed:
            continue
        assignments = ", ".join(f"{key} = %({key})s" + ("::jsonb" if key in {"tags", metadata_column} else "") for key in changed)
        conn.execute(
            f"UPDATE documents SET {assignments}, updated_at = now() WHERE id = %(id)s",
            {**changed, "id": current["id"]},
        )
        summary.documents += 1


def normalize_chunks(conn, summary: Summary) -> None:
    columns = table_columns(conn, "document_chunks")
    if not columns:
        return
    text_column = "text" if "text" in columns else "content"
    selected = ["id", text_column]
    for column in ("title", "section_title", "metadata", "text_hash"):
        if column in columns:
            selected.append(column)
    for row in conn.execute(f"SELECT {', '.join(selected)} FROM document_chunks").fetchall():
        current = dict(zip(selected, row))
        text = normalize_text_es(current[text_column], preserve_newlines=True)
        updates: dict[str, Any] = {text_column: text}
        if "title" in current:
            updates["title"] = normalize_text_es(current["title"]) if current["title"] else None
        if "section_title" in current:
            updates["section_title"] = normalize_text_es(current["section_title"]) if current["section_title"] else None
        if "metadata" in current:
            updates["metadata"] = json.dumps(
                normalize_visible_metadata(json_value(current["metadata"]) or {}),
                ensure_ascii=False,
            )
        if "text_hash" in current:
            updates["text_hash"] = sha256_text(text)
        changed = {
            key: value
            for key, value in updates.items()
            if json_value(current.get(key)) != json_value(value)
        }
        if not changed:
            continue
        assignments = ", ".join(f"{key} = %({key})s" + ("::jsonb" if key == "metadata" else "") for key in changed)
        updated_at = ", updated_at = now()" if "updated_at" in columns else ""
        conn.execute(
            f"UPDATE document_chunks SET {assignments}{updated_at} WHERE id = %(id)s",
            {**changed, "id": current["id"]},
        )
        summary.chunks += 1


def normalize_named_tables(conn, summary: Summary) -> None:
    author_columns = table_columns(conn, "authors")
    if {"id", "display_name"} <= author_columns:
        for row in conn.execute("SELECT id, display_name FROM authors").fetchall():
            display_name = normalize_text_es(row[1])
            values = {
                "id": row[0],
                "display_name": display_name,
                "sort_name": display_name,
                "normalized_name": normalized_name(display_name),
            }
            result = conn.execute(
                """
                UPDATE authors
                SET display_name = %(display_name)s,
                    sort_name = %(sort_name)s,
                    normalized_name = %(normalized_name)s,
                    updated_at = now()
                WHERE id = %(id)s
                  AND (display_name, coalesce(sort_name, ''), normalized_name)
                      IS DISTINCT FROM (%(display_name)s, %(sort_name)s, %(normalized_name)s)
                """,
                values,
            )
            summary.authors += result.rowcount

    tag_columns = table_columns(conn, "tags")
    if {"id", "name", "slug", "normalized_name"} <= tag_columns:
        for row in conn.execute("SELECT id, name, slug, normalized_name FROM tags").fetchall():
            name = normalize_tag_es(row[1])
            slug = slugify(name)
            slug_in_use = conn.execute("SELECT 1 FROM tags WHERE slug = %s AND id <> %s", (slug, row[0])).fetchone()
            new_slug = row[2] if slug_in_use else slug
            result = conn.execute(
                """
                UPDATE tags
                SET name = %s, slug = %s, normalized_name = %s, language = 'es'
                WHERE id = %s
                  AND (name, slug, normalized_name, language)
                      IS DISTINCT FROM (%s, %s, %s, 'es')
                """,
                (name, new_slug, normalized_name(name), row[0], name, new_slug, normalized_name(name)),
            )
            summary.tags += result.rowcount

    source_columns = table_columns(conn, "sources")
    if {"id", "name"} <= source_columns:
        for row in conn.execute("SELECT id, name FROM sources").fetchall():
            name = normalize_text_es(row[1])
            result = conn.execute(
                "UPDATE sources SET name = %s, updated_at = now() WHERE id = %s AND name IS DISTINCT FROM %s",
                (name, row[0], name),
            )
            summary.sources += result.rowcount


def main() -> int:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        print("ERROR: DATABASE_URL no está configurada.", file=sys.stderr)
        return 1
    summary = Summary()
    connection_url = database_url.replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(connection_url) as conn:
        normalize_documents(conn, summary)
        normalize_chunks(conn, summary)
        normalize_named_tables(conn, summary)
        conn.commit()
    print("Normalización completada sin borrar documentos ni chunks.")
    print(f"Documentos actualizados: {summary.documents}")
    print(f"Chunks actualizados: {summary.chunks}")
    print(f"Autores actualizados: {summary.authors}")
    print(f"Etiquetas actualizadas: {summary.tags}")
    print(f"Fuentes actualizadas: {summary.sources}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
