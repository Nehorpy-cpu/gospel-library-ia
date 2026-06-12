import argparse
import json
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone

from sqlalchemy import inspect, text

from app.db.session import SessionLocal
from app.utils.duplicate_detection import (
    DocumentRecord,
    choose_canonical,
    classify_pair,
    flatten_confirmed_roots,
    meaningful_content,
    normalize_author,
    normalize_title,
    normalized_url_identity,
    pending_candidates,
)

RELATION_TABLES = (
    "document_assets",
    "document_chunks",
    "favorites",
    "reading_history",
    "collection_items",
    "notes",
    "highlights",
    "chat_citations",
    "study_notes",
    "study_highlights",
    "saved_citations",
    "post_its",
)

CLASSIFICATION_PRIORITY = {
    "exact_duplicate": 60,
    "translation": 50,
    "revised_edition": 40,
    "related_media": 30,
    "probable_duplicate": 20,
    "not_duplicate": 10,
}


def _relation_counts(db) -> dict:
    counts: Counter = Counter()
    tables = set(inspect(db.bind).get_table_names())
    for table_name in RELATION_TABLES:
        if table_name not in tables:
            continue
        columns = {column["name"] for column in inspect(db.bind).get_columns(table_name)}
        if "document_id" not in columns:
            continue
        rows = db.execute(
            text(f"SELECT document_id, count(*)::int FROM {table_name} GROUP BY document_id")
        ).all()
        for document_id, count in rows:
            counts[document_id] += count
    return dict(counts)


def _load_records(db) -> list[DocumentRecord]:
    relation_counts = _relation_counts(db)
    rows = db.execute(
        text(
            """
            SELECT d.id, d.title, d.author, d.published_at, d.language,
                   d.canonical_url, d.content_hash, coalesce(d.text, ''),
                   coalesce(d.raw_metadata, '{}'::jsonb), d.created_at, s.key,
                   count(da.id)::int AS asset_count
            FROM documents d
            JOIN sources s ON s.id = d.source_id
            LEFT JOIN document_assets da ON da.document_id = d.id
            GROUP BY d.id, s.key
            ORDER BY d.id
            """
        )
    ).all()
    return [
        DocumentRecord(
            id=row.id,
            title=row.title or "",
            author=row.author,
            published_at=row.published_at,
            language=row.language,
            canonical_url=row.canonical_url,
            content_hash=row.content_hash,
            text=row[7] or "",
            raw_metadata=row[8] or {},
            created_at=row.created_at,
            source_key=row[10],
            asset_count=row.asset_count,
            relation_count=relation_counts.get(row.id, 0),
        )
        for row in rows
    ]


def _media_groups(db, records_by_id: dict) -> dict[str, list[DocumentRecord]]:
    rows = db.execute(
        text(
            """
            SELECT checksum, array_agg(DISTINCT document_id)
            FROM document_assets
            WHERE coalesce(size_bytes, 0) >= 1024
            GROUP BY checksum
            HAVING count(DISTINCT document_id) > 1
            """
        )
    ).all()
    return {
        checksum: [records_by_id[document_id] for document_id in document_ids if document_id in records_by_id]
        for checksum, document_ids in rows
    }


def _add_candidate(candidates: dict, candidate) -> None:
    existing = candidates.get(candidate.duplicate_id)
    if existing is None or CLASSIFICATION_PRIORITY[candidate.classification] > CLASSIFICATION_PRIORITY[existing.classification]:
        candidates[candidate.duplicate_id] = candidate


def _classify_group(candidates: dict, records: list[DocumentRecord], rule: str, media_checksum: str | None = None) -> None:
    if len(records) < 2:
        return
    canonical = choose_canonical(records)
    for record in records:
        if record.id == canonical.id:
            continue
        _add_candidate(
            candidates,
            classify_pair(
                canonical,
                record,
                detection_rule=rule,
                shared_media_checksum=media_checksum,
            ),
        )


def detect_candidates(db) -> dict:
    records = _load_records(db)
    records_by_id = {record.id: record for record in records}
    candidates: dict = {}

    url_groups: dict[str, list[DocumentRecord]] = defaultdict(list)
    hash_title_groups: dict[tuple, list[DocumentRecord]] = defaultdict(list)
    metadata_groups: dict[tuple, list[DocumentRecord]] = defaultdict(list)
    for record in records:
        url_groups[normalized_url_identity(record.canonical_url)].append(record)
        if meaningful_content(record):
            hash_title_groups[
                (record.content_hash, (record.language or "").lower(), normalize_title(record.title))
            ].append(record)
        title_key = normalize_title(record.title)
        if len(title_key) >= 12 and len(record.text) >= 500:
            metadata_groups[
                (
                    title_key,
                    normalize_author(record.author),
                    record.published_at.date().isoformat() if record.published_at else "",
                    (record.language or "").lower(),
                )
            ].append(record)

    for group in url_groups.values():
        _classify_group(candidates, group, "normalized_url")
    for group in hash_title_groups.values():
        _classify_group(candidates, group, "content_hash_title")
    for group in metadata_groups.values():
        _classify_group(candidates, group, "title_author_date_language")
    for checksum, group in _media_groups(db, records_by_id).items():
        _classify_group(candidates, group, "media_checksum", checksum)
    flatten_confirmed_roots(candidates)
    return candidates


def _persist_candidate(db, candidate) -> bool:
    return (
        db.execute(
            text(
                """
                INSERT INTO document_duplicate_relations (
                  id, canonical_document_id, duplicate_document_id, classification,
                  detection_rule, confidence, review_status, evidence, reviewed_at
                )
                VALUES (
                  :id, :canonical_id, :duplicate_id, :classification,
                  :detection_rule, :confidence, :review_status,
                  CAST(:evidence AS jsonb),
                  :reviewed_at
                )
                ON CONFLICT (duplicate_document_id) DO NOTHING
                RETURNING id
                """
            ),
            {
                "id": uuid.uuid4(),
                "canonical_id": candidate.canonical_id,
                "duplicate_id": candidate.duplicate_id,
                "classification": candidate.classification,
                "detection_rule": candidate.detection_rule,
                "confidence": candidate.confidence,
                "review_status": candidate.review_status,
                "evidence": json.dumps(candidate.evidence, sort_keys=True),
                "reviewed_at": datetime.now(timezone.utc) if candidate.review_status == "confirmed" else None,
            },
        ).scalar_one_or_none()
        is not None
    )


def run(apply: bool) -> dict:
    summary: Counter = Counter()
    samples: list[dict] = []
    with SessionLocal() as db:
        candidates = detect_candidates(db)
        existing = set(db.scalars(text("SELECT duplicate_document_id FROM document_duplicate_relations")).all())
        for candidate in pending_candidates(candidates, existing):
            summary[f"candidate_{candidate.classification}"] += 1
            if len(samples) < 20:
                samples.append(
                    {
                        "canonical_document_id": str(candidate.canonical_id),
                        "duplicate_document_id": str(candidate.duplicate_id),
                        "classification": candidate.classification,
                        "rule": candidate.detection_rule,
                        "confidence": candidate.confidence,
                    }
                )
            if apply and _persist_candidate(db, candidate):
                summary[f"applied_{candidate.classification}"] += 1
        if apply:
            db.commit()
    return {"counts": dict(summary), "samples": samples}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detect and resolve document duplicates without deleting data.")
    parser.add_argument("--apply", action="store_true", help="Persist classified document relationships.")
    args = parser.parse_args()
    print(json.dumps({"mode": "apply" if args.apply else "dry-run", **run(args.apply)}, sort_keys=True))
