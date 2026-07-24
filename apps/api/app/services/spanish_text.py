from __future__ import annotations

import html
import re
import unicodedata
from typing import Any


MOJIBAKE_MARKERS = (
    # Single-pass UTF-8 decoded as Latin-1/Windows-1252, e.g. `reflexi\u00c3\u00b3n`.
    "\u00c3",
    "\u00c2",
    "Ã",
    "Â",
    "â€",
    "â€™",
    "â€œ",
    "â€",
    "â€“",
    "â€”",
    "ï¿½",
    "�",
)
URL_OR_IDENTIFIER_KEYS = (
    "api_key",
    "authorization",
    "canonical_url",
    "content_hash",
    "cookie",
    "database_url",
    "document_id",
    "email",
    "file_url",
    "hash",
    "id",
    "key",
    "normalized_url",
    "password",
    "secret",
    "slug",
    "source_url",
    "storage_path",
    "token",
    "url",
    "uri",
)
COMMON_SEQUENCE_REPLACEMENTS = {
    # These truncated double-encoded sequences have appeared in Study AI output.
    # Handle them before attempting a byte-level repair, because they cannot be
    # recovered reliably from a complete UTF-8 byte sequence.
    "\u00c3\u0192l": "\u00c9l",
    "\u00c3\u0192ltimos": "\u00daltimos",
    "\u00c3l": "\u00c9l",
    "\u00c3ltimos": "\u00daltimos",
    "â€œ": "“",
    "â€": "”",
    "â€˜": "‘",
    "â€™": "’",
    "â€“": "–",
    "â€”": "—",
    "â€¦": "…",
    "â€¢": "•",
    "Â¿": "¿",
    "Â¡": "¡",
    "Â«": "«",
    "Â»": "»",
    "Ãƒltimos": "Últimos",
    "ÃƒÂºltimos": "últimos",
    "DÃƒÂ­as": "Días",
    "SeÃƒÂ±or": "Señor",
    "EspÃƒÂ­ritu": "Espíritu",
    "reflexiÃƒÂ³n": "reflexión",
}
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


def _has_mojibake(value: str) -> bool:
    return any(marker in value for marker in MOJIBAKE_MARKERS)


def _apply_common_replacements(value: str) -> str:
    repaired = value
    for before, after in COMMON_SEQUENCE_REPLACEMENTS.items():
        repaired = repaired.replace(before, after)
    return repaired


def _repair_utf8_mojibake_once(value: str, encoding: str) -> str | None:
    try:
        return value.encode(encoding).decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return None


def repair_mojibake(value: str | None) -> str | None:
    if value is None:
        return None
    # Shield truncated sequences while repairing the rest of the string. A
    # direct replacement with accented text would make legacy byte decoding
    # fail for the complete value (for example, when it also starts with
    # `Ã‚Â¿`).
    shielded = {
        "\u00c3\u0192ltimos": "__STUDY_AI_ULTIMOS__",
        "\u00c3\u0192l": "__STUDY_AI_EL__",
        "\u00c3ltimos": "__STUDY_AI_ULTIMOS__",
        "\u00c3l": "__STUDY_AI_EL__",
    }
    repaired = value
    for damaged, placeholder in shielded.items():
        repaired = repaired.replace(damaged, placeholder)
    for _ in range(4):
        if not _has_mojibake(repaired):
            break
        candidates = [
            candidate
            for candidate in (
                _repair_utf8_mojibake_once(repaired, "cp1252"),
                _repair_utf8_mojibake_once(repaired, "latin1"),
            )
            if candidate and candidate != repaired
        ]
        if not candidates:
            replaced = _apply_common_replacements(repaired)
            if replaced == repaired:
                break
            repaired = replaced
            continue
        best = min(candidates, key=lambda item: sum(item.count(marker) for marker in MOJIBAKE_MARKERS))
        if best == repaired:
            break
        repaired = best
    repaired = _apply_common_replacements(repaired)
    return repaired.replace("__STUDY_AI_ULTIMOS__", "\u00daltimos").replace("__STUDY_AI_EL__", "\u00c9l")


def _looks_like_url(value: str) -> bool:
    return bool(re.match(r"^[a-z][a-z0-9+.-]*://", value.strip(), flags=re.IGNORECASE))


def _should_skip_json_key(key: str) -> bool:
    normalized = key.casefold().replace("-", "_")
    return any(term == normalized or normalized.endswith(f"_{term}") for term in URL_OR_IDENTIFIER_KEYS)


def normalize_spanish_text(value: str | None, *, preserve_newlines: bool = False) -> str | None:
    if value is None:
        return None
    if _looks_like_url(value):
        return value.strip()
    normalized = html.unescape(value)
    normalized = repair_mojibake(normalized) or ""
    normalized = normalized.replace("\u00a0", " ").replace("\u200b", "")
    normalized = re.sub(r"Â(?=\s|$)", "", normalized)
    normalized = unicodedata.normalize("NFC", normalized)
    if preserve_newlines:
        lines = [re.sub(r"[^\S\n]+", " ", line).strip() for line in normalized.splitlines()]
        return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    return " ".join(normalized.split())


def normalize_text_es(value: str, *, preserve_newlines: bool = False) -> str:
    return normalize_spanish_text(value, preserve_newlines=preserve_newlines) or ""


def normalize_tag_es(value: str) -> str:
    normalized = normalize_text_es(value)
    return TAG_TRANSLATIONS.get(normalized.casefold(), normalized)


def normalize_json_text_fields(obj: Any, *, _key: str | None = None) -> Any:
    if isinstance(obj, dict):
        return {key: normalize_json_text_fields(item, _key=str(key)) for key, item in obj.items()}
    if isinstance(obj, list):
        return [normalize_json_text_fields(item, _key=_key) for item in obj]
    if isinstance(obj, str):
        if _key and _should_skip_json_key(_key):
            return obj.strip() if _looks_like_url(obj) else obj
        return normalize_text_es(obj, preserve_newlines="\n" in obj)
    return obj


def normalize_visible_metadata(value: Any) -> Any:
    return normalize_json_text_fields(value)


def has_mojibake(value: str | None) -> bool:
    return bool(value and _has_mojibake(value))
