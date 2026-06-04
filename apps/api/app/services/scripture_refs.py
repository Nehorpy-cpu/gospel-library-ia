import re


BOOK_ALIASES = {
    "1 nephi": "1 Nephi",
    "2 nephi": "2 Nephi",
    "3 nephi": "3 Nephi",
    "alma": "Alma",
    "mosiah": "Mosiah",
    "moroni": "Moroni",
    "doctrine and covenants": "Doctrine and Covenants",
    "d&c": "Doctrine and Covenants",
    "dyc": "Doctrine and Covenants",
    "mateo": "Matthew",
    "matthew": "Matthew",
    "john": "John",
    "juan": "John",
    "romans": "Romans",
    "romanos": "Romans",
}

SCRIPTURE_REF_RE = re.compile(
    r"\b(?P<book>1\s*Nephi|2\s*Nephi|3\s*Nephi|Alma|Mosiah|Moroni|Doctrine and Covenants|D&C|DyC|Mateo|Matthew|John|Juan|Romans|Romanos)"
    r"\s+(?P<chapter>\d{1,3}):(?P<verse>\d{1,3})(?:\s*[-–]\s*(?P<end_verse>\d{1,3}))?\b",
    flags=re.I,
)


def normalize_scripture_ref(value: str | None) -> str | None:
    if not value:
        return None
    match = SCRIPTURE_REF_RE.search(value.strip())
    if not match:
        return None
    book_key = re.sub(r"\s+", " ", match.group("book").lower().replace("dyc", "d&c")).strip()
    book = BOOK_ALIASES.get(book_key)
    if not book:
        return None
    chapter = int(match.group("chapter"))
    verse = int(match.group("verse"))
    end_verse = match.group("end_verse")
    suffix = f"-{int(end_verse)}" if end_verse else ""
    return f"{book} {chapter}:{verse}{suffix}"


def extract_scripture_refs(value: str | None) -> list[str]:
    refs: set[str] = set()
    if not value:
        return []
    for match in SCRIPTURE_REF_RE.finditer(value):
        refs.add(normalize_scripture_ref(match.group(0)) or match.group(0).strip())
    return sorted(refs)


def structured_scripture_ref(value: str) -> dict | None:
    normalized = normalize_scripture_ref(value)
    if not normalized:
        return None
    match = SCRIPTURE_REF_RE.search(normalized)
    if not match:
        return None
    return {
        "display": normalized,
        "book": BOOK_ALIASES[match.group("book").lower()],
        "chapter": int(match.group("chapter")),
        "verseStart": int(match.group("verse")),
        "verseEnd": int(match.group("end_verse") or match.group("verse")),
    }


def structured_scripture_refs(values: list[str] | None) -> list[dict]:
    seen: set[str] = set()
    structured: list[dict] = []
    for value in values or []:
        item = structured_scripture_ref(value)
        if item and item["display"] not in seen:
            seen.add(item["display"])
            structured.append(item)
    return structured
