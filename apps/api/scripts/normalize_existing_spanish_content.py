from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.n8n_ingestion import normalized_name, slugify
from app.services.spanish_text import normalize_json_text_fields, normalize_tag_es, normalize_text_es


TEXT_LIMIT = 120


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    kind: str = "text"
    preserve_newlines: bool = False


@dataclass(frozen=True)
class TableSpec:
    name: str
    columns: tuple[ColumnSpec, ...]


@dataclass
class ColumnReport:
    detected: int = 0
    modified: int = 0
    examples: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class TableReport:
    columns: dict[str, ColumnReport] = field(default_factory=dict)

    @property
    def detected(self) -> int:
        return sum(column.detected for column in self.columns.values())

    @property
    def modified(self) -> int:
        return sum(column.modified for column in self.columns.values())


TABLE_SPECS: tuple[TableSpec, ...] = (
    TableSpec(
        "documents",
        (
            ColumnSpec("title"),
            ColumnSpec("author"),
            ColumnSpec("summary", preserve_newlines=True),
            ColumnSpec("description", preserve_newlines=True),
            ColumnSpec("text", preserve_newlines=True),
            ColumnSpec("content", preserve_newlines=True),
            ColumnSpec("content_text", preserve_newlines=True),
            ColumnSpec("tags", "json"),
            ColumnSpec("scripture_refs", "json"),
            ColumnSpec("metadata", "json"),
            ColumnSpec("raw_metadata", "json"),
        ),
    ),
    TableSpec(
        "document_chunks",
        (
            ColumnSpec("title"),
            ColumnSpec("section_title"),
            ColumnSpec("text", preserve_newlines=True),
            ColumnSpec("content", preserve_newlines=True),
            ColumnSpec("metadata", "json"),
        ),
    ),
    TableSpec("sources", (ColumnSpec("name"), ColumnSpec("title"), ColumnSpec("description", preserve_newlines=True), ColumnSpec("config", "json"))),
    TableSpec("authors", (ColumnSpec("name"), ColumnSpec("display_name"), ColumnSpec("sort_name"), ColumnSpec("metadata", "json"))),
    TableSpec("tags", (ColumnSpec("name"), ColumnSpec("description", preserve_newlines=True), ColumnSpec("metadata", "json"))),
    TableSpec("study_workspaces", (ColumnSpec("name"), ColumnSpec("description", preserve_newlines=True), ColumnSpec("source_filters", "json"), ColumnSpec("settings", "json"))),
    TableSpec("study_notes", (ColumnSpec("title"), ColumnSpec("content", preserve_newlines=True), ColumnSpec("selected_text", preserve_newlines=True), ColumnSpec("selection_range", "json"), ColumnSpec("scripture_refs", "json"), ColumnSpec("position", "json"))),
    TableSpec("study_highlights", (ColumnSpec("selected_text", preserve_newlines=True), ColumnSpec("scripture_refs", "json"), ColumnSpec("metadata", "json"))),
    TableSpec("saved_citations", (ColumnSpec("quote", preserve_newlines=True), ColumnSpec("quote_text", preserve_newlines=True), ColumnSpec("selected_text", preserve_newlines=True), ColumnSpec("source_title"), ColumnSpec("source_author"), ColumnSpec("source_reference"), ColumnSpec("notes", preserve_newlines=True), ColumnSpec("location", "json"), ColumnSpec("scripture_refs", "json"), ColumnSpec("metadata", "json"))),
    TableSpec("post_its", (ColumnSpec("title"), ColumnSpec("content", preserve_newlines=True), ColumnSpec("position", "json"), ColumnSpec("source_filters", "json"))),
    TableSpec("chat_sessions", (ColumnSpec("title"), ColumnSpec("metadata", "json"))),
    TableSpec("chat_messages", (ColumnSpec("content", preserve_newlines=True), ColumnSpec("metadata", "json"))),
    TableSpec("ingestion_jobs", (ColumnSpec("payload", "json"), ColumnSpec("errors", "json"))),
    TableSpec("study_ai_suggestion_cache", (ColumnSpec("request", "json"), ColumnSpec("response", "json"), ColumnSpec("local_context", "json"), ColumnSpec("metadata", "json"))),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repara mojibake UTF-8 en contenido espanol existente.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Detecta cambios sin modificar la base.")
    mode.add_argument("--apply", action="store_true", help="Aplica cambios idempotentes sin borrar datos.")
    return parser.parse_args()


def table_columns(conn, table: str) -> dict[str, str]:
    rows = conn.execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        """,
        (table,),
    ).fetchall()
    return {row["column_name"]: row["data_type"] for row in rows}


def table_exists(conn, table: str) -> bool:
    row = conn.execute(
        """
        SELECT EXISTS (
          SELECT 1 FROM information_schema.tables
          WHERE table_schema = 'public' AND table_name = %s
        ) AS exists
        """,
        (table,),
    ).fetchone()
    return bool(row and row["exists"])


def normalize_value(value: Any, spec: ColumnSpec) -> Any:
    if value is None:
        return None
    if spec.kind == "json":
        return normalize_json_text_fields(json_value(value))
    return normalize_text_es(str(value), preserve_newlines=spec.preserve_newlines)


def json_value(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def comparable(value: Any) -> Any:
    parsed = json_value(value)
    if isinstance(parsed, (dict, list)):
        return json.dumps(parsed, ensure_ascii=False, sort_keys=True)
    return parsed


def preview(value: Any) -> str:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    else:
        text = str(value)
    text = " ".join(text.split())
    return text[:TEXT_LIMIT] + ("..." if len(text) > TEXT_LIMIT else "")


def scan_table(conn, spec: TableSpec, *, apply: bool) -> TableReport:
    report = TableReport()
    columns = table_columns(conn, spec.name)
    existing_specs = [column for column in spec.columns if column.name in columns]
    if not existing_specs or "id" not in columns:
        return report

    selected = [sql.Identifier("id"), *(sql.Identifier(column.name) for column in existing_specs)]
    query = sql.SQL("SELECT {} FROM {}").format(
        sql.SQL(", ").join(selected),
        sql.Identifier(spec.name),
    )
    rows = conn.execute(query).fetchall()
    for row in rows:
        updates: dict[str, Any] = {}
        for column in existing_specs:
            current = row[column.name]
            normalized = normalize_value(current, column)
            if comparable(current) == comparable(normalized):
                continue
            column_report = report.columns.setdefault(column.name, ColumnReport())
            column_report.detected += 1
            if len(column_report.examples) < 3:
                column_report.examples.append((preview(current), preview(normalized)))
            updates[column.name] = normalized

        if apply and updates:
            assignments = []
            params: dict[str, Any] = {"id": row["id"]}
            for name, value in updates.items():
                assignments.append(sql.SQL("{} = {}").format(sql.Identifier(name), sql.Placeholder(name)))
                params[name] = Jsonb(value) if columns[name] in {"json", "jsonb"} else value
            if "updated_at" in columns:
                assignments.append(sql.SQL("updated_at = now()"))
            update_query = sql.SQL("UPDATE {} SET {} WHERE id = %(id)s").format(
                sql.Identifier(spec.name),
                sql.SQL(", ").join(assignments),
            )
            conn.execute(update_query, params)
            for name in updates:
                report.columns[name].modified += 1
    return report


def maintain_derived_names(conn, *, apply: bool) -> None:
    if not apply:
        return
    author_columns = table_columns(conn, "authors") if table_exists(conn, "authors") else {}
    if {"id", "display_name", "sort_name", "normalized_name"} <= set(author_columns):
        rows = conn.execute("SELECT id, display_name FROM authors WHERE display_name IS NOT NULL").fetchall()
        for row in rows:
            display_name = normalize_text_es(row["display_name"])
            conn.execute(
                """
                UPDATE authors
                SET display_name = %(display_name)s,
                    sort_name = %(display_name)s,
                    normalized_name = %(normalized_name)s,
                    updated_at = now()
                WHERE id = %(id)s
                """,
                {
                    "id": row["id"],
                    "display_name": display_name,
                    "normalized_name": normalized_name(display_name),
                },
            )
    tag_columns = table_columns(conn, "tags") if table_exists(conn, "tags") else {}
    if {"id", "name", "slug", "normalized_name"} <= set(tag_columns):
        rows = conn.execute("SELECT id, name FROM tags").fetchall()
        for row in rows:
            name = normalize_tag_es(row["name"])
            conn.execute(
                """
                UPDATE tags
                SET name = %(name)s,
                    slug = %(slug)s,
                    normalized_name = %(normalized_name)s,
                    language = 'es'
                WHERE id = %(id)s
                """,
                {
                    "id": row["id"],
                    "name": name,
                    "slug": slugify(name),
                    "normalized_name": normalized_name(name),
                },
            )


def print_report(reports: dict[str, TableReport], *, apply: bool) -> None:
    mode = "apply" if apply else "dry-run"
    print(f"Modo: {mode}")
    for table, report in reports.items():
        print(f"\nTabla: {table}")
        if not report.columns:
            print("  Sin cambios detectados.")
            continue
        for column, column_report in sorted(report.columns.items()):
            print(
                f"  Columna: {column} | filas detectadas: {column_report.detected} | "
                f"filas modificadas: {column_report.modified if apply else 0}"
            )
            for before, after in column_report.examples:
                print(f"    antes: {before}")
                print(f"    despues: {after}")


def main() -> int:
    args = parse_args()
    apply = bool(args.apply)
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        print("ERROR: DATABASE_URL no esta configurada.", file=sys.stderr)
        return 1

    connection_url = database_url.replace("postgresql+psycopg://", "postgresql://")
    reports: dict[str, TableReport] = {}
    with psycopg.connect(connection_url, row_factory=dict_row) as conn:
        for spec in TABLE_SPECS:
            if not table_exists(conn, spec.name):
                continue
            reports[spec.name] = scan_table(conn, spec, apply=apply)
        maintain_derived_names(conn, apply=apply)
        if apply:
            conn.commit()
        else:
            conn.rollback()
    print_report(reports, apply=apply)
    print("\nNormalizacion finalizada. No se borraron ni truncaron tablas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
