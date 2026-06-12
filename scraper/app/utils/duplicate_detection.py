import re
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from urllib.parse import parse_qs, unquote, urlsplit, urlunsplit
from uuid import UUID

EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
MEDIA_QUERY_KEYS = {"imageview", "download", "asset", "media"}
REVISION_TERMS = {"edition", "revised", "revision", "updated", "version"}
OFFICIAL_HOST_SUFFIXES = (
    "churchofjesuschrist.org",
    "byu.edu",
    "josephsmithpapers.org",
)


@dataclass(slots=True)
class DocumentRecord:
    id: UUID
    title: str
    author: str | None
    published_at: datetime | None
    language: str | None
    canonical_url: str
    content_hash: str | None
    text: str
    raw_metadata: dict = field(default_factory=dict)
    created_at: datetime | None = None
    source_key: str | None = None
    asset_count: int = 0
    relation_count: int = 0


@dataclass(slots=True)
class DuplicateCandidate:
    canonical_id: UUID
    duplicate_id: UUID
    classification: str
    detection_rule: str
    confidence: float
    review_status: str
    evidence: dict


def flatten_confirmed_roots(candidates: dict[UUID, DuplicateCandidate]) -> None:
    hidden_classes = {"exact_duplicate", "probable_duplicate"}
    for candidate in candidates.values():
        original_canonical = candidate.canonical_id
        root = original_canonical
        visited = {candidate.duplicate_id}
        while root in candidates:
            parent = candidates[root]
            if parent.review_status != "confirmed" or parent.classification not in hidden_classes:
                break
            if root in visited:
                break
            visited.add(root)
            root = parent.canonical_id
        if root != original_canonical and root != candidate.duplicate_id:
            candidate.canonical_id = root
            candidate.evidence["canonical_chain_flattened"] = [
                str(original_canonical),
                str(root),
            ]


def pending_candidates(
    candidates: dict[UUID, DuplicateCandidate],
    existing_duplicate_ids: set[UUID],
) -> list[DuplicateCandidate]:
    return sorted(
        (
            candidate
            for candidate in candidates.values()
            if candidate.duplicate_id not in existing_duplicate_ids
        ),
        key=lambda item: str(item.duplicate_id),
    )


def normalized_url_identity(url: str) -> str:
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").lower()
    if parts.port and parts.port not in (80, 443):
        host = f"{host}:{parts.port}"
    path = re.sub(r"/+", "/", unquote(parts.path or "/")).rstrip("/") or "/"
    return urlunsplit(((parts.scheme or "https").lower(), host, path, "", ""))


def url_language(url: str, fallback: str | None = None) -> str:
    values = parse_qs(urlsplit(url).query)
    value = (values.get("lang") or values.get("language") or [fallback or ""])[0].lower()
    aliases = {"eng": "en", "spa": "es", "por": "pt", "fra": "fr", "deu": "de"}
    return aliases.get(value, value or (fallback or "").lower())


def is_media_variant(url: str, title: str = "") -> bool:
    query_keys = {key.lower() for key in parse_qs(urlsplit(url).query)}
    if query_keys & MEDIA_QUERY_KEYS:
        return True
    return bool(re.search(r"\.(?:jpe?g|png|gif|webp|mp3|mp4|pdf)$", title.strip(), re.IGNORECASE))


def normalize_title(value: str | None) -> str:
    normalized = re.sub(r"[^\w]+", " ", (value or "").casefold(), flags=re.UNICODE)
    return " ".join(normalized.split())


def normalize_author(value: str | None) -> str:
    return normalize_title(value)


def text_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    left_sample = " ".join(left[:6000].split())
    right_sample = " ".join(right[:6000].split())
    if left_sample == right_sample:
        return 1.0
    matcher = SequenceMatcher(None, left_sample, right_sample, autojunk=True)
    quick = matcher.quick_ratio()
    if quick < 0.9:
        return quick
    return matcher.ratio()


def meaningful_content(record: DocumentRecord) -> bool:
    return (
        len(record.text.strip()) >= 500
        and bool(record.content_hash)
        and record.content_hash != EMPTY_SHA256
    )


def canonical_score(record: DocumentRecord) -> tuple:
    host = (urlsplit(record.canonical_url).hostname or "").lower()
    official = int(any(host == suffix or host.endswith(f".{suffix}") for suffix in OFFICIAL_HOST_SUFFIXES))
    metadata_complete = sum(
        bool(value)
        for value in (
            record.title,
            record.author,
            record.published_at,
            record.language,
            record.raw_metadata,
        )
    )
    created = record.created_at.timestamp() if record.created_at else float("inf")
    return (
        official,
        metadata_complete,
        len(record.text),
        record.asset_count,
        record.relation_count,
        -created,
        str(record.id),
    )


def choose_canonical(records: list[DocumentRecord]) -> DocumentRecord:
    return max(records, key=canonical_score)


def classify_pair(
    canonical: DocumentRecord,
    candidate: DocumentRecord,
    *,
    detection_rule: str,
    shared_media_checksum: str | None = None,
) -> DuplicateCandidate:
    same_url = normalized_url_identity(canonical.canonical_url) == normalized_url_identity(candidate.canonical_url)
    canonical_language = url_language(canonical.canonical_url, canonical.language)
    candidate_language = url_language(candidate.canonical_url, candidate.language)
    same_language = canonical_language == candidate_language
    same_hash = bool(canonical.content_hash) and canonical.content_hash == candidate.content_hash
    same_title = normalize_title(canonical.title) == normalize_title(candidate.title)
    evidence = {
        "same_normalized_url": same_url,
        "same_content_hash": same_hash,
        "same_title": same_title,
        "same_language": same_language,
        "canonical_url_identity": normalized_url_identity(canonical.canonical_url),
    }
    if shared_media_checksum:
        evidence["shared_media_checksum"] = shared_media_checksum

    if same_url and not same_language:
        result = ("translation", 0.99, "confirmed")
    elif is_media_variant(canonical.canonical_url, canonical.title) or is_media_variant(
        candidate.canonical_url, candidate.title
    ):
        result = ("related_media", 0.98, "confirmed")
    elif same_hash and same_language and meaningful_content(canonical) and meaningful_content(candidate):
        result = ("exact_duplicate", 1.0, "confirmed")
    elif shared_media_checksum:
        result = ("related_media", 0.9, "confirmed")
    else:
        similarity = text_similarity(canonical.text, candidate.text)
        evidence["text_similarity"] = round(similarity, 6)
        if same_url and same_language and similarity >= 0.93:
            result = ("probable_duplicate", similarity, "pending")
        elif same_title and same_language and similarity >= 0.93:
            result = ("probable_duplicate", similarity, "pending")
        elif same_title and any(
            term in f"{canonical.canonical_url} {candidate.canonical_url}".casefold()
            for term in REVISION_TERMS
        ):
            result = ("revised_edition", 0.85, "confirmed")
        else:
            result = ("not_duplicate", max(similarity, 0.25), "confirmed")

    return DuplicateCandidate(
        canonical_id=canonical.id,
        duplicate_id=candidate.id,
        classification=result[0],
        detection_rule=detection_rule,
        confidence=round(result[1], 6),
        review_status=result[2],
        evidence=evidence,
    )
