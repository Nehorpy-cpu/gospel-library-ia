from pathlib import Path
import unittest


class DuplicateFilterTest(unittest.TestCase):
    def test_bm25_only_excludes_confirmed_duplicate_classes(self):
        source = (Path(__file__).resolve().parents[1] / "app" / "retrieval" / "bm25.py").read_text()
        filter_sql = source.split("CONFIRMED_DUPLICATE_FILTER =", 1)[1].split('""".strip()', 1)[0]

        self.assertIn("review_status = 'confirmed'", filter_sql)
        self.assertIn("'exact_duplicate'", filter_sql)
        self.assertIn("'probable_duplicate'", filter_sql)
        self.assertNotIn("translation", filter_sql)
        self.assertNotIn("related_media", filter_sql)


if __name__ == "__main__":
    unittest.main()
