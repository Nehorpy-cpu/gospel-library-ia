from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.utils.duplicate_detection import (
    DocumentRecord,
    DuplicateCandidate,
    canonical_score,
    choose_canonical,
    classify_pair,
    flatten_confirmed_roots,
    normalized_url_identity,
)


def record(value: int, **overrides) -> DocumentRecord:
    values = {
        "id": UUID(int=value),
        "title": "Faith in Jesus Christ",
        "author": "Jane Doe",
        "published_at": datetime(2020, 1, 1, tzinfo=timezone.utc),
        "language": "en",
        "canonical_url": f"https://example.org/talk?id={value}&lang=eng",
        "content_hash": "a" * 64,
        "text": "Faith and discipleship. " * 100,
        "raw_metadata": {"source_type": "talk"},
        "created_at": datetime(2020, 1, value, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return DocumentRecord(**values)


class DuplicateDetectionTest(unittest.TestCase):
    def test_url_identity_removes_query_and_fragment(self):
        self.assertEqual(
            normalized_url_identity("HTTPS://Example.org/talk/?id=p3&lang=eng#note"),
            "https://example.org/talk",
        )

    def test_exact_duplicate_requires_same_language_and_content(self):
        result = classify_pair(record(1), record(2), detection_rule="normalized_url")
        self.assertEqual(result.classification, "exact_duplicate")
        self.assertEqual(result.review_status, "confirmed")

    def test_translation_is_not_merged(self):
        translated = record(2, language="es", canonical_url="https://example.org/talk?lang=spa")
        result = classify_pair(record(1), translated, detection_rule="normalized_url")
        self.assertEqual(result.classification, "translation")

    def test_media_variant_is_not_merged(self):
        media = record(2, canonical_url="https://example.org/talk?imageView=photo.jpg")
        result = classify_pair(record(1), media, detection_rule="normalized_url")
        self.assertEqual(result.classification, "related_media")

    def test_false_positive_is_classified_not_duplicate(self):
        other = record(
            2,
            canonical_url="https://example.org/another",
            content_hash="b" * 64,
            text="A completely different historical document. " * 80,
        )
        result = classify_pair(record(1), other, detection_rule="title_author_date_language")
        self.assertEqual(result.classification, "not_duplicate")

    def test_official_source_wins_canonical_selection(self):
        mirror = record(1, canonical_url="https://mirror.example.org/talk", asset_count=20)
        official = record(2, canonical_url="https://speeches.byu.edu/talks/example", asset_count=0)
        self.assertGreater(canonical_score(official), canonical_score(mirror))
        self.assertEqual(choose_canonical([mirror, official]).id, official.id)

    def test_oldest_record_breaks_equal_quality_tie(self):
        older = record(1, created_at=datetime(2019, 1, 1, tzinfo=timezone.utc))
        newer = record(2, created_at=datetime(2020, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(choose_canonical([newer, older]).id, older.id)

    def test_confirmed_duplicate_chains_are_flattened(self):
        root = DuplicateCandidate(UUID(int=1), UUID(int=2), "exact_duplicate", "hash", 1, "confirmed", {})
        child = DuplicateCandidate(UUID(int=2), UUID(int=3), "exact_duplicate", "hash", 1, "confirmed", {})
        candidates = {root.duplicate_id: root, child.duplicate_id: child}

        flatten_confirmed_roots(candidates)

        self.assertEqual(child.canonical_id, UUID(int=1))


if __name__ == "__main__":
    unittest.main()
