from __future__ import annotations

import html
import re
import unicodedata
from typing import Any


MOJIBAKE_MARKERS = ("Ã", "Â", "â€", "â€™", "â€œ", "â€�", "ðŸ")
TAG_TRANSLATIONS = {
    "atonement": "Expiación",
    "book of mormon": "Libro de Mormón",
    "covenants": "Convenios",
    "faith": "Fe",
    "gospel": "Evangelio",
    "holy ghost": "Espíritu Santo",
    "jesus christ": "Jesucristo",
    "prayer": "Oración",
    "repentance": "Arrepentimiento",
    "temple": "Templo",
}


def _repair_utf8_mojibake(value: str) -> str:
    repaired = value
    for _ in range(3):
        if not any(marker in repaired for marker in MOJIBAKE_MARKERS):
            break
        try:
            candidate = repaired.encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            break
        if candidate == repaired:
            break
        repaired = candidate
    return repaired


def normalize_text_es(value: str, *, preserve_newlines: bool = False) -> str:
    normalized = html.unescape(value)
    normalized = _repair_utf8_mojibake(normalized)
    normalized = normalized.replace("\u00a0", " ").replace("\u200b", "")
    normalized = re.sub(r"Â(?=\s|$)", "", normalized)
    normalized = unicodedata.normalize("NFC", normalized)
    if preserve_newlines:
        lines = [re.sub(r"[^\S\n]+", " ", line).strip() for line in normalized.splitlines()]
        return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    return " ".join(normalized.split())


def normalize_tag_es(value: str) -> str:
    normalized = normalize_text_es(value)
    return TAG_TRANSLATIONS.get(normalized.casefold(), normalized)


def normalize_visible_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: normalize_visible_metadata(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_visible_metadata(item) for item in value]
    if isinstance(value, str):
        return normalize_text_es(value, preserve_newlines="\n" in value)
    return value
