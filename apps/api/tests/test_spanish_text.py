from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.spanish_text import (
    normalize_json_text_fields,
    normalize_spanish_text,
    normalize_tag_es,
    normalize_text_es,
    repair_mojibake,
)


def mojibake(value: str, rounds: int = 1) -> str:
    damaged = value
    for _ in range(rounds):
        damaged = damaged.encode("utf-8").decode("latin1")
    return damaged


class SpanishTextNormalizationTest(unittest.TestCase):
    def test_repairs_common_mojibake_examples(self):
        cases = {
            mojibake("reflexión", 2): "reflexión",
            mojibake("¿Cómo", 2): "¿Cómo",
            mojibake("más", 2): "más",
            mojibake("élder", 2): "élder",
            mojibake("Últimos Días", 2): "Últimos Días",
            mojibake("Restauración", 2): "Restauración",
            mojibake("Espíritu", 2): "Espíritu",
            mojibake("Señor", 2): "Señor",
            mojibake("enseñanzas", 2): "enseñanzas",
        }

        for damaged, expected in cases.items():
            with self.subTest(expected=expected):
                self.assertEqual(repair_mojibake(damaged), expected)
                self.assertEqual(normalize_spanish_text(damaged), expected)

    def test_repairs_legacy_author_mojibake(self):
        self.assertEqual(
            normalize_text_es(mojibake("Elder D. Todd Christofferson", 1).replace("D.", "D.Â")),
            "Elder D. Todd Christofferson",
        )

    def test_repairs_production_mojibake_sequences(self):
        cases = {
            "\u00c3\u0192\u00c2\u00a9lder": "\u00e9lder",
            "Fe en el Se\u00c3\u0192\u00c2\u00b1or": "Fe en el Se\u00f1or",
            "\u00c3\u201a\u00c2\u00a1Piensen": "\u00a1Piensen",
            "Pregunta de reflexi\u00c3\u0192\u00c2\u00b3n": "Pregunta de reflexi\u00f3n",
            "\u00c3\u201a\u00c2\u00bfC\u00c3\u0192\u00c2\u00b3mo": "\u00bfC\u00f3mo",
            "ense\u00c3\u0192\u00c2\u00b1anzas": "ense\u00f1anzas",
            "gu\u00c3\u0192\u00c2\u00aden": "gu\u00eden",
            "\u00c3\u0192\u00c6\u2019\u00c3\u201a\u00c2\u00a9lder": "\u00e9lder",
        }

        for damaged, expected in cases.items():
            with self.subTest(damaged=damaged):
                self.assertEqual(repair_mojibake(damaged), expected)

    def test_repairs_truncated_study_ai_sequences(self):
        self.assertEqual(repair_mojibake("\u00c3\u0192l"), "\u00c9l")
        self.assertEqual(repair_mojibake("\u00c3\u0192ltimos D\u00c3\u0192\u00c2\u00adas"), "\u00daltimos D\u00edas")

    def test_repairs_single_pass_study_ai_sequences(self):
        cases = {
            "reflexi\u00c3\u00b3n": "reflexi\u00f3n",
            "\u00c2\u00bfDe qu\u00c3\u00a9 manera": "\u00bfDe qu\u00e9 manera",
            "\u00c3\u00a9lder": "\u00e9lder",
            "\u00c3ltimos D\u00c3\u00adas": "\u00daltimos D\u00edas",
            "Helam\u00c3\u00a1n": "Helam\u00e1n",
            "m\u00c3\u00a1s": "m\u00e1s",
            "ense\u00c3\u00b1anzas": "ense\u00f1anzas",
            "gu\u00c3\u00aden": "gu\u00eden",
        }
        for damaged, expected in cases.items():
            with self.subTest(damaged=damaged):
                self.assertEqual(repair_mojibake(damaged), expected)

    def test_texto_correcto_queda_igual_e_idempotente(self):
        text = "¿Cómo puedo sentir más el Espíritu del Señor?"

        self.assertEqual(normalize_text_es(text), text)
        self.assertEqual(normalize_text_es(normalize_text_es(text)), text)

    def test_json_nested_normalizado_y_urls_no_se_danan(self):
        value = {
            "title": mojibake("Restauración", 2),
            "nested": {
                "content": mojibake("¿Cómo enseña el Espíritu?", 2),
                "source_url": "https://example.com/path?q=Esp%C3%ADritu",
                "document_id": "doc-ñ-no-normalizar",
            },
            "items": [mojibake("Señor", 2)],
        }

        normalized = normalize_json_text_fields(value)

        self.assertEqual(normalized["title"], "Restauración")
        self.assertEqual(normalized["nested"]["content"], "¿Cómo enseña el Espíritu?")
        self.assertEqual(normalized["nested"]["source_url"], "https://example.com/path?q=Esp%C3%ADritu")
        self.assertEqual(normalized["nested"]["document_id"], "doc-ñ-no-normalizar")
        self.assertEqual(normalized["items"], ["Señor"])

    def test_translates_common_english_tags(self):
        self.assertEqual(normalize_tag_es("Book of Mormon"), "Libro de Mormón")
        self.assertEqual(normalize_tag_es("Holy Ghost"), "Espíritu Santo")


if __name__ == "__main__":
    unittest.main()
