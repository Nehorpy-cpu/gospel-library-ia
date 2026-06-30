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
