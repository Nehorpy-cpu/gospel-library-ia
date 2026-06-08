import re
from datetime import datetime, timezone
from urllib.parse import unquote, urlparse

from app.extractors.metadata import author_from_url


BAD_TITLE_PREFIXES = (
    "the text for this speech is unavailable",
    "pretendemos modificar a tradução",
    "tenemos la intención de modificar",
    "nous sommes toujours prêts",
)

GENERIC_SLUGS = {
    "about",
    "all",
    "archive",
    "home",
    "index",
    "search",
    "speeches",
    "study",
    "talks",
}


def title_needs_repair(title: str | None) -> bool:
    if not title or not title.strip():
        return True
    normalized = " ".join(title.split()).lower()
    return (
        normalized in {"untitled document", "sin titulo", "sin título"}
        or len(normalized) > 180
        or normalized.startswith(BAD_TITLE_PREFIXES)
        or normalized.startswith("?m=")
        or normalized == "blog"
        or (normalized.endswith(":") and len(normalized) < 30)
        or bool(re.fullmatch(r"part\s+\d+", normalized))
    )


def title_from_url(url: str | None, source_type: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    parts = [unquote(part) for part in parsed.path.strip("/").split("/") if part]
    if not parts:
        return None

    slug = None
    if "talks" in parts:
        index = parts.index("talks")
        if len(parts) > index + 2:
            slug = parts[index + 2]
    elif source_type == "general_conference" and "general-conference" in parts:
        slug = parts[-1]
    elif source_type == "joseph_smith_papers" and "paper-summary" in parts:
        slug = parts[-1]
    return _title_from_slug(slug)


def author_from_document_url(url: str | None, source_type: str | None) -> str | None:
    if source_type not in {"byu_speeches_en", "byu_speeches_es"}:
        return None
    return author_from_url(url)


def authors_match(left: str | None, right: str | None) -> bool:
    def normalized(value: str | None) -> str:
        return re.sub(r"[^a-z0-9]+", "", (value or "").lower())

    return bool(normalized(left)) and normalized(left) == normalized(right)


def author_needs_repair(author: str | None) -> bool:
    if not author or not author.strip():
        return True
    value = author.strip()
    first_letter = next((character for character in value if character.isalpha()), "")
    return (
        bool(re.search(r"\d", value))
        or len(value) > 90
        or len(value.split()) > 8
        or (bool(first_letter) and first_letter.islower())
    )


def published_at_from_url(url: str | None, source_type: str | None) -> datetime | None:
    if not url or source_type != "general_conference":
        return None
    match = re.search(r"/general-conference/((?:19|20)\d{2})/(0[1-9]|1[0-2])/", url)
    if not match:
        return None
    return datetime(int(match.group(1)), int(match.group(2)), 1, tzinfo=timezone.utc)


def _title_from_slug(slug: str | None) -> str | None:
    if not slug:
        return None
    slug = slug.rsplit(".", 1)[0] if "." in slug else slug
    normalized = re.sub(r"[-_]+", " ", slug).strip()
    if (
        not normalized
        or normalized.lower() in GENERIC_SLUGS
        or normalized.isdigit()
        or len(normalized) < 4
        or len(normalized) > 180
    ):
        return None
    return normalized.title()
