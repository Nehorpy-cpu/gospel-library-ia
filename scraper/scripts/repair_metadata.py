import argparse
import json
import uuid
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import text

from app.db.session import SessionLocal
from app.utils.metadata_quality import (
    author_needs_repair,
    author_from_document_url,
    published_at_from_url,
    title_from_url,
    title_needs_repair,
)


SELECT_DOCUMENTS = text(
    """
    SELECT document.id, document.title, document.author, document.published_at,
           document.canonical_url,
           COALESCE(document.raw_metadata->>'source_type', source.key) AS source_type
    FROM documents AS document
    JOIN sources AS source ON source.id = document.source_id
    ORDER BY document.id
    """
)


def candidates(row) -> list[tuple[str, str | None, str, str]]:
    repairs: list[tuple[str, str | None, str, str]] = []
    if title_needs_repair(row.title):
        title = title_from_url(row.canonical_url, row.source_type)
        if title and title != row.title:
            repairs.append(("title", row.title, title, "canonical_url_slug"))
    author = author_from_document_url(row.canonical_url, row.source_type)
    if author and author_needs_repair(row.author):
        repairs.append(("author", row.author, author, "byu_talk_author_slug"))
    if row.published_at is None:
        published_at = published_at_from_url(row.canonical_url, row.source_type)
        if published_at:
            repairs.append(("published_at", None, published_at.isoformat(), "general_conference_url"))
    return repairs


def apply_repair(db, document_id, repair) -> bool:
    field_name, previous_value, repaired_value, repaired_from = repair
    audit_id = db.execute(
        text(
            """
            INSERT INTO document_metadata_repair_audit (
              id, document_id, field_name, previous_value, repaired_value, repaired_from
            )
            VALUES (:id, :document_id, :field_name, :previous_value, :repaired_value, :repaired_from)
            ON CONFLICT (document_id, field_name) DO NOTHING
            RETURNING id
            """
        ),
        {
            "id": uuid.uuid4(),
            "document_id": document_id,
            "field_name": field_name,
            "previous_value": str(previous_value) if previous_value is not None else None,
            "repaired_value": repaired_value,
            "repaired_from": repaired_from,
        },
    ).scalar_one_or_none()
    if audit_id is None:
        return False

    if field_name == "published_at":
        assignment = "published_at = CAST(:value AS timestamptz)"
    elif field_name == "author":
        assignment = "author = :value"
    else:
        assignment = "title = :value"
    db.execute(
        text(
            f"""
            UPDATE documents
            SET {assignment},
                raw_metadata = COALESCE(raw_metadata, '{{}}'::jsonb)
                  || CAST(:repair_metadata AS jsonb),
                is_indexed = false,
                updated_at = now()
            WHERE id = :document_id
            """
        ),
        {
            "value": repaired_value,
            "document_id": document_id,
            "repair_metadata": json.dumps(
                {
                    "metadata_quality_v1": {
                        "last_field": field_name,
                        "last_source": repaired_from,
                        "repaired_at": datetime.now(timezone.utc).isoformat(),
                    }
                }
            ),
        },
    )
    return True


def run(apply: bool) -> dict:
    summary: Counter = Counter()
    samples: list[dict[str, str | None]] = []
    with SessionLocal() as db:
        rows = db.execute(SELECT_DOCUMENTS).all()
        for row in rows:
            for repair in candidates(row):
                summary[f"candidate_{repair[0]}"] += 1
                if len(samples) < 12:
                    samples.append(
                        {
                            "document_id": str(row.id),
                            "field": repair[0],
                            "previous": str(repair[1])[:160] if repair[1] is not None else None,
                            "repaired": repair[2],
                            "source": repair[3],
                        }
                    )
                if apply and apply_repair(db, row.id, repair):
                    summary[f"applied_{repair[0]}"] += 1
        if apply:
            db.commit()
    return {"counts": dict(summary), "samples": samples}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit and repair deterministic document metadata.")
    parser.add_argument("--apply", action="store_true", help="Persist repairs and audit rows.")
    args = parser.parse_args()
    print(json.dumps({"mode": "apply" if args.apply else "dry-run", **run(args.apply)}, sort_keys=True))
