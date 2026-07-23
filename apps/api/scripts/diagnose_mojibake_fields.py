from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.normalize_existing_spanish_content import (
    TABLE_SPECS,
    ColumnSpec,
    comparable,
    json_value,
    normalize_value,
    preview,
    table_columns,
    table_exists,
)


@dataclass
class FieldFinding:
    suspicious_rows: int = 0
    examples: list[tuple[str, str]] = field(default_factory=list)
    json_keys: set[str] = field(default_factory=set)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnostica mojibake UTF-8 sin modificar datos.")
    parser.add_argument("--sample", type=int, default=20, help="Maximo de ejemplos por columna (1-100).")
    return parser.parse_args()


def changed_json_keys(before: Any, after: Any, path: str = "") -> set[str]:
    if isinstance(before, dict) and isinstance(after, dict):
        keys: set[str] = set()
        for key in before.keys() | after.keys():
            child_path = f"{path}.{key}" if path else str(key)
            keys.update(changed_json_keys(before.get(key), after.get(key), child_path))
        return keys
    if isinstance(before, list) and isinstance(after, list):
        keys: set[str] = set()
        for index, (before_item, after_item) in enumerate(zip(before, after)):
            keys.update(changed_json_keys(before_item, after_item, f"{path}[{index}]"))
        return keys
    return {path or "valor"} if comparable(before) != comparable(after) else set()


def diagnose_column(conn, table: str, column: ColumnSpec, *, sample_limit: int) -> FieldFinding:
    finding = FieldFinding()
    query = sql.SQL("SELECT id, {} FROM {}").format(
        sql.Identifier(column.name),
        sql.Identifier(table),
    )
    for row in conn.execute(query).fetchall():
        current = row[column.name]
        normalized = normalize_value(current, column)
        if comparable(current) == comparable(normalized):
            continue
        finding.suspicious_rows += 1
        if len(finding.examples) < sample_limit:
            finding.examples.append((preview(current), preview(normalized)))
        if column.kind == "json":
            finding.json_keys.update(changed_json_keys(json_value(current), json_value(normalized)))
    return finding


def main() -> int:
    args = parse_args()
    sample_limit = max(1, min(args.sample, 100))
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        print("ERROR: DATABASE_URL no esta configurada.", file=sys.stderr)
        return 1

    connection_url = database_url.replace("postgresql+psycopg://", "postgresql://")
    findings = 0
    with psycopg.connect(connection_url, row_factory=dict_row) as conn:
        for table_spec in TABLE_SPECS:
            if not table_exists(conn, table_spec.name):
                continue
            columns = table_columns(conn, table_spec.name)
            existing_specs = [spec for spec in table_spec.columns if spec.name in columns]
            if not existing_specs or "id" not in columns:
                continue
            print(f"\nTabla: {table_spec.name}")
            for column in existing_specs:
                finding = diagnose_column(conn, table_spec.name, column, sample_limit=sample_limit)
                if not finding.suspicious_rows:
                    continue
                findings += 1
                print(f"  Columna: {column.name} | filas sospechosas: {finding.suspicious_rows}")
                if finding.json_keys:
                    print(f"    claves JSON afectadas: {', '.join(sorted(finding.json_keys)[:sample_limit])}")
                for before, after in finding.examples:
                    print(f"    antes: {before}")
                    print(f"    despues: {after}")
        conn.rollback()
    if not findings:
        print("No se detectaron campos sospechosos en las tablas y columnas disponibles.")
    print("\nDiagnostico finalizado sin modificar datos ni imprimir DATABASE_URL.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
