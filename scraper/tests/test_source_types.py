from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.utils.source_types import source_type_for_url


class SourceTypesTest(unittest.TestCase):
    def test_canonical_church_source_is_preserved_for_unclassified_child_url(self):
        self.assertEqual(
            source_type_for_url(
                "church_manuals",
                "https://www.churchofjesuschrist.org/study/come-follow-me?lang=eng",
            ),
            "church_manuals",
        )

    def test_legacy_generic_church_source_remains_explicit(self):
        self.assertEqual(
            source_type_for_url(
                "churchofjesuschrist",
                "https://www.churchofjesuschrist.org/learn/example?lang=eng",
            ),
            "churchofjesuschrist",
        )


if __name__ == "__main__":
    unittest.main()
