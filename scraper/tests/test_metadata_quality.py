from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.utils.metadata_quality import (
    author_needs_repair,
    author_from_document_url,
    authors_match,
    published_at_from_url,
    title_from_url,
    title_needs_repair,
)


class MetadataQualityTests(unittest.TestCase):
    def test_repairs_byu_title_and_author_from_talk_url(self) -> None:
        url = "https://speeches.byu.edu/talks/dallin-h-oaks/coming-closer-to-jesus-christ/?M=V"
        self.assertEqual(title_from_url(url, "byu_speeches_en"), "Coming Closer To Jesus Christ")
        self.assertEqual(author_from_document_url(url, "byu_speeches_en"), "Dallin H. Oaks")

    def test_repairs_general_conference_title_and_month(self) -> None:
        url = "https://www.churchofjesuschrist.org/study/general-conference/1998/04/have-you-been-saved"
        self.assertEqual(title_from_url(url, "general_conference"), "Have You Been Saved")
        self.assertEqual(
            published_at_from_url(url, "general_conference"),
            datetime(1998, 4, 1, tzinfo=timezone.utc),
        )

    def test_does_not_invent_author_outside_byu_talks(self) -> None:
        url = "https://www.churchofjesuschrist.org/study/general-conference/2025/04/example"
        self.assertIsNone(author_from_document_url(url, "general_conference"))

    def test_does_not_treat_discursos_sud_taxonomy_slug_as_title(self) -> None:
        url = "https://discursosud.com/tag/franklin-d-richards"
        self.assertIsNone(title_from_url(url, "discursos_sud"))

    def test_flags_body_paragraph_and_known_notice_titles(self) -> None:
        self.assertTrue(title_needs_repair("A" * 181))
        self.assertTrue(title_needs_repair("The text for this speech is unavailable. Please see our archive."))
        self.assertTrue(title_needs_repair("?M=A"))
        self.assertTrue(title_needs_repair("Jeff:"))
        self.assertTrue(title_needs_repair("Part 1"))
        self.assertFalse(title_needs_repair("Faith in Jesus Christ"))

    def test_compares_author_names_ignoring_punctuation(self) -> None:
        self.assertTrue(authors_match("Dallin H Oaks", "Dallin H. Oaks"))
        self.assertFalse(authors_match("the middle", "Kevin J. Worthen"))

    def test_repairs_only_clearly_invalid_existing_authors(self) -> None:
        self.assertTrue(author_needs_repair("the middle"))
        self.assertTrue(author_needs_repair("June 30 they completed the translation"))
        self.assertFalse(author_needs_repair("Dr. Dhanurjay “DJ” Patil"))


if __name__ == "__main__":
    unittest.main()
