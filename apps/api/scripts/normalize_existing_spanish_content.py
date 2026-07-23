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


@dataclass(frozen=True)
class SlugConflict:
    table: str
    row_id: str
    current_slug: str
    desired_slug: str
    existing_id: str
    action: str = "skipped_slug_update"


@dataclass(frozen=True)
class DerivedNameUpdate:
    table: str
    row_id: Any
    values: dict[str, Any]
    current_slug: str | None = None
    desired_slug: str | None = None


@dataclass
class DerivedNameReport:
    detected: int = 0
    modified: int = 0
    warnings: list[SlugConflict] = field(default_factory=list)


TABLE_SPECS: tuple[TableSpec, ...] = (
    TableSpec(
        "documents",
        (
            ColumnSpec("title"),
            ColumnSpec("author"),
            ColumnSpec("source"),
            ColumnSpec("source_type"),
            ColumnSpec("summary", preserve_newlines=True),
            ColumnSpec("description", preserve_newlines=True),
            ColumnSpec("excerpt", preserve_newlines=True),
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
            ColumnSpec("snippet", preserve_newlines=True),
            ColumnSpec("text", preserve_newlines=True),
            ColumnSpec("content", preserve_newlines=True),
            ColumnSpec("metadata", "json"),
        ),
    ),
    TableSpec(
        "sources",
        (
            ColumnSpec("name"),
            ColumnSpec("title"),
            ColumnSpec("description", preserve_newlines=True),
            ColumnSpec("source_type"),
            ColumnSpec("config", "json"),
        ),
    ),
    TableSpec("authors", (ColumnSpec("name"), ColumnSpec("display_name"), ColumnSpec("sort_name"), ColumnSpec("metadata", "json"))),
    TableSpec("tags", (ColumnSpec("name"), ColumnSpec("description", preserve_newlines=True), ColumnSpec("metadata", "json"))),
    TableSpec("study_workspaces", (ColumnSpec("name"), ColumnSpec("title"), ColumnSpec("description", preserve_newlines=True), ColumnSpec("source_filters", "json"), ColumnSpec("settings", "json"))),
    TableSpec("study_notes", (ColumnSpec("title"), ColumnSpec("content", preserve_newlines=True), ColumnSpec("selected_text", preserve_newlines=True), ColumnSpec("selection_range", "json"), ColumnSpec("scripture_refs", "json"), ColumnSpec("position", "json"), ColumnSpec("metadata", "json"))),
    TableSpec("study_highlights", (ColumnSpec("selected_text", preserve_newlines=True), ColumnSpec("note", preserve_newlines=True), ColumnSpec("color"), ColumnSpec("scripture_refs", "json"), ColumnSpec("metadata", "json"))),
    TableSpec("saved_citations", (ColumnSpec("quote", preserve_newlines=True), ColumnSpec("quote_text", preserve_newlines=True), ColumnSpec("selected_text", preserve_newlines=True), ColumnSpec("source_title"), ColumnSpec("source_author"), ColumnSpec("source_reference"), ColumnSpec("notes", preserve_newlines=True), ColumnSpec("location", "json"), ColumnSpec("scripture_refs", "json"), ColumnSpec("metadata", "json"))),
    TableSpec("post_its", (ColumnSpec("title"), ColumnSpec("content", preserve_newlines=True), ColumnSpec("position", "json"), ColumnSpec("source_filters", "json"), ColumnSpec("metadata", "json"))),
    TableSpec("chat_sessions", (ColumnSpec("title"), ColumnSpec("summary", preserve_newlines=True), ColumnSpec("metadata", "json"))),
    TableSpec("chat_messages", (ColumnSpec("content", preserve_newlines=True), ColumnSpec("metadata", "json"))),
    TableSpec("ingestion_jobs", (ColumnSpec("payload", "json"), ColumnSpec("errors", "json"), ColumnSpec("metadata", "json"), ColumnSpec("error_message", preserve_newlines=True), ColumnSpec("error", preserve_newlines=True))),
    TableSpec("study_ai_suggestion_cache", (ColumnSpec("request", "json"), ColumnSpec("response", "json"), ColumnSpec("suggestions", "json"), ColumnSpec("sources_used", "json"), ColumnSpec("warnings", "json"), ColumnSpec("local_context", "json"), ColumnSpec("metadata", "json"))),
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


def fetch_rows(conn, table: str, columns: tuple[str, ...], *, where: str | None = None) -> list[dict[str, Any]]:
    query = sql.SQL("SELECT {} FROM {}").format(
        sql.SQL(", ").join(sql.Identifier(column) for column in columns),
        sql.Identifier(table),
    )
    if where:
        query += sql.SQL(" WHERE ") + sql.SQL(where)
    return list(conn.execute(query).fetchall())


def plan_author_derived_updates(rows: list[dict[str, Any]], columns: dict[str, str]) -> list[DerivedNameUpdate]:
    plans: list[DerivedNameUpdate] = []
    for row in rows:
        display_name = normalize_text_es(row["display_name"])
        desired = {
            "display_name": display_name,
            "sort_name": display_name,
            "normalized_name": normalized_name(display_name),
        }
        values = {
            column: value
            for column, value in desired.items()
            if column in columns and row.get(column) != value
        }
        if values:
            plans.append(DerivedNameUpdate("authors", row["id"], values))
    return plans


def plan_tag_derived_updates(
    rows: list[dict[str, Any]], columns: dict[str, str]
) -> tuple[list[DerivedNameUpdate], list[SlugConflict]]:
    """Plan tag repairs without merging records or changing a conflicting slug."""
    desired_rows: list[tuple[dict[str, Any], str, str]] = []
    current_slug_owners: dict[str, list[str]] = {}
    desired_slug_owners: dict[str, list[str]] = {}

    for row in rows:
        row_id = str(row["id"])
        current_slug = str(row.get("slug") or "")
        name = normalize_tag_es(row["name"])
        desired_slug = slugify(name)
        desired_rows.append((row, name, desired_slug))
        if current_slug:
            current_slug_owners.setdefault(current_slug, []).append(row_id)
        if desired_slug:
            desired_slug_owners.setdefault(desired_slug, []).append(row_id)

    plans: list[DerivedNameUpdate] = []
    conflicts: list[SlugConflict] = []
    for row, name, desired_slug in desired_rows:
        row_id = str(row["id"])
        current_slug = str(row.get("slug") or "")
        desired = {
            "name": name,
            "normalized_name": normalized_name(name),
            "language": "es",
        }
        values = {
            column: value
            for column, value in desired.items()
            if column in columns and row.get(column) != value
        }
        slug_update: str | None = None
        if "slug" in columns and desired_slug and current_slug != desired_slug:
            existing_ids = [
                owner_id
                for owner_id in current_slug_owners.get(desired_slug, [])
                if owner_id != row_id
            ]
            planned_ids = [
                owner_id
                for owner_id in desired_slug_owners.get(desired_slug, [])
                if owner_id != row_id
            ]
            conflicting_ids = existing_ids or planned_ids
            if conflicting_ids:
                conflicts.append(
                    SlugConflict(
                        table="tags",
                        row_id=row_id,
                        current_slug=current_slug,
                        desired_slug=desired_slug,
                        existing_id=conflicting_ids[0],
                    )
                )
            else:
                slug_update = desired_slug
        if values or slug_update:
            plans.append(
                DerivedNameUpdate(
                    table="tags",
                    row_id=row["id"],
                    values=values,
                    current_slug=current_slug,
                    desired_slug=slug_update,
                )
            )
    return plans, conflicts


def execute_derived_update(conn, update: DerivedNameUpdate, columns: dict[str, str]) -> None:
    assignments = [
        sql.SQL("{} = {}").format(sql.Identifier(column), sql.Placeholder(column))
        for column in update.values
    ]
    if "updated_at" in columns:
        assignments.append(sql.SQL("updated_at = now()"))
    query = sql.SQL("UPDATE {} SET {} WHERE id = %(id)s").format(
        sql.Identifier(update.table),
        sql.SQL(", ").join(assignments),
    )
    conn.execute(query, {"id": update.row_id, **update.values})


def find_slug_owner(conn, table: str, desired_slug: str, row_id: Any) -> str:
    row = conn.execute(
        sql.SQL("SELECT id FROM {} WHERE slug = %(slug)s AND id <> %(id)s LIMIT 1").format(
            sql.Identifier(table)
        ),
        {"slug": desired_slug, "id": row_id},
    ).fetchone()
    return str(row["id"]) if row else "unknown"


def execute_slug_update(conn, update: DerivedNameUpdate) -> bool:
    """Update a slug only while it remains unowned, including concurrent runs."""
    assert update.desired_slug is not None
    query = sql.SQL(
        """
        UPDATE {table} AS target
        SET slug = %(slug)s
        WHERE target.id = %(id)s
          AND NOT EXISTS (
            SELECT 1 FROM {table} AS existing
            WHERE existing.slug = %(slug)s AND existing.id <> %(id)s
          )
        """
    ).format(table=sql.Identifier(update.table))
    try:
        # A nested transaction is a savepoint when the maintenance script already
        # has an open transaction, so an unexpected unique race cannot poison it.
        with conn.transaction():
            cursor = conn.execute(query, {"id": update.row_id, "slug": update.desired_slug})
        return cursor.rowcount == 1
    except psycopg.errors.UniqueViolation:
        return False


def maintain_derived_names(conn, *, apply: bool) -> DerivedNameReport:
    report = DerivedNameReport()
    author_columns = table_columns(conn, "authors") if table_exists(conn, "authors") else {}
    if {"id", "display_name", "sort_name", "normalized_name"} <= set(author_columns):
        author_rows = fetch_rows(
            conn,
            "authors",
            ("id", "display_name", "sort_name", "normalized_name"),
            where="display_name IS NOT NULL",
        )
        author_updates = plan_author_derived_updates(author_rows, author_columns)
        report.detected += len(author_updates)
        if apply:
            for update in author_updates:
                execute_derived_update(conn, update, author_columns)
                report.modified += 1

    tag_columns = table_columns(conn, "tags") if table_exists(conn, "tags") else {}
    required_tag_columns = {"id", "name", "slug", "normalized_name"}
    if required_tag_columns <= set(tag_columns):
        tag_select_columns = tuple(
            column
            for column in ("id", "name", "slug", "normalized_name", "language")
            if column in tag_columns
        )
        tag_rows = fetch_rows(conn, "tags", tag_select_columns)
        tag_updates, conflicts = plan_tag_derived_updates(tag_rows, tag_columns)
        report.detected += len(tag_updates)
        report.warnings.extend(conflicts)
        if apply:
            for update in tag_updates:
                row_modified = False
                if update.values:
                    execute_derived_update(conn, update, tag_columns)
                    row_modified = True
                if update.desired_slug and not execute_slug_update(conn, update):
                    report.warnings.append(
                        SlugConflict(
                            table=update.table,
                            row_id=str(update.row_id),
                            current_slug=update.current_slug or "",
                            desired_slug=update.desired_slug,
                            existing_id=find_slug_owner(conn, update.table, update.desired_slug, update.row_id),
                        )
                    )
                elif update.desired_slug:
                    row_modified = True
                if row_modified:
                    report.modified += 1
    return report


def print_report(
    reports: dict[str, TableReport], derived_report: DerivedNameReport, *, apply: bool
) -> None:
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
    print(
        "\nNombres derivados | filas detectadas: "
        f"{derived_report.detected} | filas modificadas: "
        f"{derived_report.modified if apply else 0}"
    )
    if not derived_report.warnings:
        print("  Sin conflictos de slug.")
        return
    print(f"  Conflictos de slug: {len(derived_report.warnings)}")
    for warning in derived_report.warnings:
        print(
            "    slug_conflict"
            f" | table={warning.table}"
            f" | id={warning.row_id}"
            f" | current_slug={warning.current_slug}"
            f" | desired_slug={warning.desired_slug}"
            f" | existing_id={warning.existing_id}"
            f" | action={warning.action}"
        )


def main() -> int:
    args = parse_args()
    apply = bool(args.apply)
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        print("ERROR: DATABASE_URL no esta configurada.", file=sys.stderr)
        return 1

    connection_url = database_url.replace("postgresql+psycopg://", "postgresql://")
    reports: dict[str, TableReport] = {}
    derived_report = DerivedNameReport()
    with psycopg.connect(connection_url, row_factory=dict_row) as conn:
        for spec in TABLE_SPECS:
            if not table_exists(conn, spec.name):
                continue
            reports[spec.name] = scan_table(conn, spec, apply=apply)
        derived_report = maintain_derived_names(conn, apply=apply)
        if apply:
            conn.commit()
        else:
            conn.rollback()
    print_report(reports, derived_report, apply=apply)
    print("\nNormalizacion finalizada. No se borraron ni truncaron tablas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
