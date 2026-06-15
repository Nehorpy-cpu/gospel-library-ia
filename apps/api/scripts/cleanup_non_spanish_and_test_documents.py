from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


PLACEHOLDER_MARKERS = (
    "[reemplazar antes de enviar]",
    "no es una cita oficial",
    "no reemplaza ninguna fuente doctrinal",
    "contenido de prueba",
    "placeholder",
)


@dataclass(frozen=True)
class DetectedDocument:
    document_id: str
    title: str
    language: str | None
    source_url: str | None
    canonical_url: str | None
    source_name: str | None
    chunks: int
    reasons: tuple[str, ...]


def table_columns(conn, table_name: str) -> set[str]:
    return {
        row[0]
        for row in conn.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            """,
            (table_name,),
        ).fetchall()
    }


def table_exists(conn, table_name: str) -> bool:
    row = conn.execute(
        """
        SELECT EXISTS (
          SELECT 1 FROM information_schema.tables
          WHERE table_schema = 'public' AND table_name = %s
        )
        """,
        (table_name,),
    ).fetchone()
    return bool(row and row[0])


def json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def detect_reasons(row: dict[str, Any]) -> tuple[str, ...]:
    metadata = json_object(row.get("metadata"))
    language = str(row.get("language") or "").casefold()
    title = str(row.get("title") or "")
    source_url = str(row.get("source_url") or "")
    canonical_url = str(row.get("canonical_url") or "")
    source_name = str(row.get("source_name") or "")
    searchable_text = "\n".join(
        str(value or "")
        for value in (
            row.get("document_text"),
            row.get("summary"),
            metadata.get("summary"),
            metadata.get("description"),
        )
    ).casefold()
    metadata_source_url = str(metadata.get("source_url") or "")
    metadata_canonical_url = str(metadata.get("canonical_url") or "")
    reasons: list[str] = []

    if language == "en":
        reasons.append("language=en")
    for label, value in (
        ("source_url", source_url),
        ("canonical_url", canonical_url),
        ("metadata.source_url", metadata_source_url),
        ("metadata.canonical_url", metadata_canonical_url),
    ):
        if "lang=eng" in value.casefold():
            reasons.append(f"{label} contiene lang=eng")
    if "documento de prueba" in title.casefold():
        reasons.append("título de documento de prueba")
    if "prueba-n8n" in source_url.casefold() or "prueba-n8n" in canonical_url.casefold():
        reasons.append("URL de prueba n8n")
    if str(metadata.get("test_payload", "")).casefold() == "true":
        reasons.append("metadata.test_payload=true")
    if source_name.casefold() == "prueba n8n":
        reasons.append("fuente Prueba n8n")
    for marker in PLACEHOLDER_MARKERS:
        if marker in searchable_text:
            reasons.append(f"texto placeholder: {marker}")
    return tuple(dict.fromkeys(reasons))


def load_detected_documents(conn) -> list[DetectedDocument]:
    document_columns = table_columns(conn, "documents")
    metadata_column = "raw_metadata" if "raw_metadata" in document_columns else "metadata"
    text_column = "text" if "text" in document_columns else "content_text"
    summary_expression = (
        "d.summary"
        if "summary" in document_columns
        else f"COALESCE(d.{metadata_column}->>'summary', d.{metadata_column}->>'description')"
    )
    source_url_expression = f"COALESCE(d.{metadata_column}->>'source_url', d.canonical_url)"
    active_filter = "WHERE d.deleted_at IS NULL" if "deleted_at" in document_columns else ""
    has_chunks = table_exists(conn, "document_chunks")
    chunk_count = (
        "(SELECT count(*)::int FROM document_chunks dc WHERE dc.document_id = d.id)"
        if has_chunks
        else "0"
    )
    rows = conn.execute(
        f"""
        SELECT
          d.id::text AS document_id,
          d.title,
          d.language,
          {source_url_expression} AS source_url,
          d.canonical_url,
          s.name AS source_name,
          d.{text_column} AS document_text,
          {summary_expression} AS summary,
          d.{metadata_column} AS metadata,
          {chunk_count} AS chunk_count
        FROM documents d
        JOIN sources s ON s.id = d.source_id
        {active_filter}
        ORDER BY d.created_at, d.id
        """
    ).fetchall()
    detected: list[DetectedDocument] = []
    keys = (
        "document_id",
        "title",
        "language",
        "source_url",
        "canonical_url",
        "source_name",
        "document_text",
        "summary",
        "metadata",
        "chunk_count",
    )
    for values in rows:
        row = dict(zip(keys, values))
        reasons = detect_reasons(row)
        if reasons:
            detected.append(
                DetectedDocument(
                    document_id=row["document_id"],
                    title=row["title"],
                    language=row["language"],
                    source_url=row["source_url"],
                    canonical_url=row["canonical_url"],
                    source_name=row["source_name"],
                    chunks=row["chunk_count"],
                    reasons=reasons,
                )
            )
    return detected


def apply_cleanup(conn, documents: list[DetectedDocument]) -> tuple[str, int]:
    if not documents:
        return "sin_cambios", 0
    ids = [document.document_id for document in documents]
    columns = table_columns(conn, "documents")
    metadata_column = "raw_metadata" if "raw_metadata" in columns else "metadata"
    if "deleted_at" in columns:
        status_assignment = ", status = 'HIDDEN'" if "status" in columns else ""
        indexed_assignment = ", is_indexed = false" if "is_indexed" in columns else ""
        updated_assignment = ", updated_at = now()" if "updated_at" in columns else ""
        result = conn.execute(
            f"""
            UPDATE documents
            SET deleted_at = now()
                {status_assignment}
                {indexed_assignment}
                {updated_assignment},
                {metadata_column} = COALESCE({metadata_column}, '{{}}'::jsonb)
                  || jsonb_build_object(
                    'cleanup_mode', 'soft_delete',
                    'cleanup_reason', 'non_spanish_or_test_content',
                    'cleanup_at', now()::text
                  )
            WHERE id::text = ANY(%s)
              AND deleted_at IS NULL
            """,
            (ids,),
        )
        return "soft_delete", result.rowcount

    if table_exists(conn, "document_tags"):
        conn.execute("DELETE FROM document_tags WHERE document_id::text = ANY(%s)", (ids,))
    if table_exists(conn, "document_chunks"):
        conn.execute("DELETE FROM document_chunks WHERE document_id::text = ANY(%s)", (ids,))
    result = conn.execute("DELETE FROM documents WHERE id::text = ANY(%s)", (ids,))
    return "hard_delete", result.rowcount


def print_report(documents: list[DetectedDocument], mode: str) -> None:
    print(f"Modo: {mode}")
    print(f"Documentos detectados: {len(documents)}")
    for document in documents:
        print("-" * 72)
        print(f"ID: {document.document_id}")
        print(f"Título: {document.title}")
        print(f"Idioma: {document.language or '(sin idioma)'}")
        print(f"Source URL: {document.source_url or '(sin URL)'}")
        print(f"Chunks relacionados: {document.chunks}")
        print(f"Razones: {'; '.join(document.reasons)}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Limpia documentos no españoles o de prueba.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Solo informa; no modifica datos.")
    mode.add_argument("--apply", action="store_true", help="Aplica la limpieza detectada.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        print("ERROR: DATABASE_URL no está configurada.", file=sys.stderr)
        return 2
    connection_url = database_url.replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(connection_url) as conn:
        documents = load_detected_documents(conn)
        print_report(documents, "dry-run" if args.dry_run else "apply")
        if args.dry_run:
            conn.rollback()
            print("No se realizaron cambios.")
            return 0
        cleanup_mode, affected = apply_cleanup(conn, documents)
        conn.commit()
        print(f"Modo de limpieza aplicado: {cleanup_mode}")
        print(f"Documentos afectados: {affected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
