from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.parsers.sources import parser_for_url


HTML = """
<html>
  <head>
    <title>Faith in Jesus Christ | BYU Speeches</title>
    <meta name="author" content="Jane Doe" />
    <meta property="article:published_time" content="2024-01-14" />
    <meta property="og:title" content="Faith in Jesus Christ" />
  </head>
  <body>
    <h1>Faith in Jesus Christ</h1>
    <p class="byline">Jane Doe</p>
    <time datetime="2024-01-14">January 14, 2024</time>
    <article>
      <p>Alma 32 teaches us to exercise faith in Jesus Christ.</p>
      <a href="/sample.pdf">PDF</a>
      <audio src="/sample.mp3"></audio>
    </article>
  </body>
</html>
"""


class SourceParsersTest(unittest.TestCase):
    def test_byu_english_parser_metadata(self):
        document = parser_for_url("https://speeches.byu.edu/talks/jane-doe/faith/").parse(
            "https://speeches.byu.edu/talks/jane-doe/faith/",
            HTML,
        )

        self.assertEqual(document.source_key, "byu_speeches_en")
        self.assertEqual(document.title, "Faith in Jesus Christ")
        self.assertEqual(document.author, "Jane Doe")
        self.assertEqual(document.metadata["source_type"], "byu_speeches_en")
        self.assertTrue(any(asset.asset_type == "pdf" for asset in document.assets))
        self.assertTrue(any(asset.asset_type == "mp3" for asset in document.assets))

    def test_byu_spanish_parser_sets_language(self):
        document = parser_for_url("https://speeches.byu.edu/spa/talks/jane-doe/fe/").parse(
            "https://speeches.byu.edu/spa/talks/jane-doe/fe/",
            HTML,
        )

        self.assertEqual(document.source_key, "byu_speeches_es")
        self.assertEqual(document.language, "es")

    def test_church_scriptures_source_type(self):
        document = parser_for_url("https://www.churchofjesuschrist.org/study/scriptures/bofm/alma/32").parse(
            "https://www.churchofjesuschrist.org/study/scriptures/bofm/alma/32",
            HTML,
        )

        self.assertEqual(document.metadata["source_type"], "scriptures")
        self.assertEqual(document.category, "Escrituras")

    def test_joseph_smith_papers_adds_historical_note(self):
        document = parser_for_url("https://www.josephsmithpapers.org/paper-summary/sample").parse(
            "https://www.josephsmithpapers.org/paper-summary/sample",
            HTML,
        )

        self.assertEqual(document.source_key, "joseph_smith_papers")
        self.assertIn("historica/documental", document.metadata["source_note"])


if __name__ == "__main__":
    unittest.main()
