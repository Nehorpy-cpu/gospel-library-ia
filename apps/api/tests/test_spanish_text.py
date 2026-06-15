from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.spanish_text import normalize_tag_es, normalize_text_es


class SpanishTextNormalizationTest(unittest.TestCase):
    def test_repairs_common_author_mojibake(self):
        self.assertEqual(
            normalize_text_es("Elder D.Ã‚ Todd Christofferson"),
            "Elder D. Todd Christofferson",
        )

    def test_repairs_repeated_utf8_mojibake(self):
        self.assertEqual(normalize_text_es("Libro de MormÃƒÂ³n"), "Libro de Mormón")

    def test_translates_common_english_tags(self):
        self.assertEqual(normalize_tag_es("Book of Mormon"), "Libro de Mormón")
        self.assertEqual(normalize_tag_es("Holy Ghost"), "Espíritu Santo")


if __name__ == "__main__":
    unittest.main()
