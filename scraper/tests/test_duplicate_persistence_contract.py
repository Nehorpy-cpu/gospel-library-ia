from pathlib import Path
import sys
import unittest
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.utils.duplicate_detection import DuplicateCandidate, pending_candidates


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "migrations" / "versions" / "0012_duplicate_detection_resolution.py"
RESOLVER = ROOT / "scripts" / "resolve_duplicates.py"


class DuplicatePersistenceContractTest(unittest.TestCase):
    def test_apply_is_idempotent_for_existing_duplicate_decision(self):
        duplicate_id = UUID(int=2)
        candidate = DuplicateCandidate(
            canonical_id=UUID(int=1),
            duplicate_id=duplicate_id,
            classification="exact_duplicate",
            detection_rule="content_hash_title",
            confidence=1.0,
            review_status="confirmed",
            evidence={},
        )
        candidates = {duplicate_id: candidate}

        self.assertEqual(pending_candidates(candidates, {duplicate_id}), [])
        self.assertEqual(pending_candidates(candidates, set()), [candidate])
        self.assertIn(
            "ON CONFLICT (duplicate_document_id) DO NOTHING",
            RESOLVER.read_text(encoding="utf-8"),
        )

    def test_rollback_only_removes_duplicate_decisions(self):
        migration_source = MIGRATION.read_text(encoding="utf-8")
        downgrade_source = migration_source.split("def downgrade()", 1)[1]

        self.assertIn('op.drop_table("document_duplicate_relations")', downgrade_source)
        self.assertNotIn("documents", downgrade_source.replace("document_duplicate_relations", ""))

    def test_migration_preserves_referential_integrity(self):
        upgrade_source = MIGRATION.read_text(encoding="utf-8").split("def downgrade()", 1)[0]

        self.assertEqual(upgrade_source.count('sa.ForeignKey("documents.id", ondelete="CASCADE")'), 2)
        self.assertIn('"canonical_document_id <> duplicate_document_id"', upgrade_source)
        self.assertIn('"duplicate_document_id"', upgrade_source)


if __name__ == "__main__":
    unittest.main()
