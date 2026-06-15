"""Ingest a closed list of curated doctrinal pages without crawling.

Each URL is requested once, parsed conservatively, and skipped when a clean
main-content extraction cannot be established. The script does not use OpenAI,
Qdrant, link discovery, or destructive database operations.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import httpx
import psycopg
from bs4 import BeautifulSoup, Tag


INGESTION_MODE = "curated_v1"
INGESTION_MARKER = "curated-ingestion-v1"
EXTRACTOR_VERSION = "curated-html-v1"
CHUNKER_VERSION = "curated-v1"
USER_AGENT = "GospelLibraryIA/0.1 curated-ingestion contact=https://www.estudiopy.com"
REQUEST_TIMEOUT_SECONDS = 30
REQUEST_DELAY_SECONDS = 1.0
MAX_RESPONSE_BYTES = 3_000_000
MIN_CONTENT_CHARACTERS = 800
CHUNK_MIN_CHARACTERS = 800
CHUNK_TARGET_CHARACTERS = 1_000
CHUNK_MAX_CHARACTERS = 1_200
ALLOWED_HOSTS = {
    "www.churchofjesuschrist.org",
    "churchofjesuschrist.org",
    "speeches.byu.edu",
    "www.speeches.byu.edu",
}
TRACKING_QUERY_KEYS = {
    "cid",
    "source",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}


@dataclass(frozen=True)
class CuratedTarget:
    url: str
    source_key: str
    source_name: str
    source_base_url: str
    source_type: str
    document_type: str
    category: str
    language: str
    body_selectors: tuple[str, ...]
    default_tags: tuple[str, ...]


TARGETS = (
    CuratedTarget(
        url="https://www.churchofjesuschrist.org/study/manual/gospel-topics/salvation?lang=eng",
        source_key="church_manuals",
        source_name="Manuales de la Iglesia",
        source_base_url="https://www.churchofjesuschrist.org/study/manual",
        source_type="church_manuals",
        document_type="gospel_topic",
        category="Gospel Topics",
        language="en",
        body_selectors=("article#main .body", "article#main"),
        default_tags=("Salvation", "Jesus Christ", "Gospel Topics"),
    ),
    CuratedTarget(
        url="https://www.churchofjesuschrist.org/study/manual/gospel-topics/faith-in-jesus-christ?lang=eng",
        source_key="church_manuals",
        source_name="Manuales de la Iglesia",
        source_base_url="https://www.churchofjesuschrist.org/study/manual",
        source_type="church_manuals",
        document_type="gospel_topic",
        category="Gospel Topics",
        language="en",
        body_selectors=("article#main .body", "article#main"),
        default_tags=("Faith", "Jesus Christ", "Gospel Topics"),
    ),
    CuratedTarget(
        url="https://www.churchofjesuschrist.org/study/manual/gospel-topics/book-of-mormon?lang=eng",
        source_key="church_manuals",
        source_name="Manuales de la Iglesia",
        source_base_url="https://www.churchofjesuschrist.org/study/manual",
        source_type="church_manuals",
        document_type="gospel_topic",
        category="Gospel Topics",
        language="en",
        body_selectors=("article#main .body", "article#main"),
        default_tags=("Book of Mormon", "Jesus Christ", "Scriptures"),
    ),
    CuratedTarget(
        url="https://www.churchofjesuschrist.org/study/general-conference/2020/10/45andersen?lang=eng",
        source_key="general_conference",
        source_name="Conferencia General",
        source_base_url="https://www.churchofjesuschrist.org/study/general-conference",
        source_type="general_conference",
        document_type="general_conference_talk",
        category="General Conference",
        language="en",
        body_selectors=("article#main .body", "article#main"),
        default_tags=("Jesus Christ", "Faith", "General Conference"),
    ),
    CuratedTarget(
        url="https://www.churchofjesuschrist.org/study/general-conference/2021/04/28ballard?lang=eng",
        source_key="general_conference",
        source_name="Conferencia General",
        source_base_url="https://www.churchofjesuschrist.org/study/general-conference",
        source_type="general_conference",
        document_type="general_conference_talk",
        category="General Conference",
        language="en",
        body_selectors=("article#main .body", "article#main"),
        default_tags=("Hope", "Jesus Christ", "General Conference"),
    ),
    CuratedTarget(
        url="https://www.churchofjesuschrist.org/study/general-conference/2021/04/54christofferson?lang=eng",
        source_key="general_conference",
        source_name="Conferencia General",
        source_base_url="https://www.churchofjesuschrist.org/study/general-conference",
        source_type="general_conference",
        document_type="general_conference_talk",
        category="General Conference",
        language="en",
        body_selectors=("article#main .body", "article#main"),
        default_tags=("Covenants", "Jesus Christ", "General Conference"),
    ),
    CuratedTarget(
        url="https://www.churchofjesuschrist.org/study/general-conference/2021/04/17eyring?lang=eng",
        source_key="general_conference",
        source_name="Conferencia General",
        source_base_url="https://www.churchofjesuschrist.org/study/general-conference",
        source_type="general_conference",
        document_type="general_conference_talk",
        category="General Conference",
        language="en",
        body_selectors=("article#main .body", "article#main"),
        default_tags=("Temples", "Covenants", "General Conference"),
    ),
    CuratedTarget(
        url="https://speeches.byu.edu/talks/kevin-r-duncan/jesus-christ-is-the-answer/",
        source_key="byu_speeches",
        source_name="BYU Speeches English",
        source_base_url="https://speeches.byu.edu/talks/",
        source_type="byu_speeches_en",
        document_type="byu_speech",
        category="BYU Speeches",
        language="en",
        body_selectors=(
            "main .single-speech__content",
            "main .single-speech__body",
            "main [class*='transcript']",
            "main",
        ),
        default_tags=("Jesus Christ", "Discipleship", "BYU Speeches"),
    ),
)


@dataclass(frozen=True)
class ExtractedDocument:
    target: CuratedTarget
    source_url: str
    normalized_url: str
    canonical_url: str
    title: str
    author: str | None
    published_at: datetime | None
    language: str
    text: str
    tags: tuple[str, ...]
    scripture_refs: tuple[str, ...]
    extraction_selector: str


@dataclass
class IngestionStats:
    sources_created: int = 0
    sources_verified: int = 0
    documents_created: int = 0
    documents_verified: int = 0
    chunks_created: int = 0
    chunks_verified: int = 0
    authors_created: int = 0
    authors_verified: int = 0
    tags_created: int = 0
    tags_verified: int = 0
    skipped: list[tuple[str, str]] = field(default_factory=list)


class ExtractionSkipped(ValueError):
    pass


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalized_name(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return " ".join(
        "".join(character for character in decomposed if not unicodedata.combining(character))
        .casefold()
        .split()
    )


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", normalized_name(value)).strip("-")


def normalize_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    host = (parsed.hostname or "").lower()
    if host not in ALLOWED_HOSTS or parsed.scheme != "https":
        raise ExtractionSkipped("URL outside the explicit HTTPS allowlist")
    port = f":{parsed.port}" if parsed.port and parsed.port != 443 else ""
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if path != "/":
        path = path.rstrip("/")
    query = urlencode(
        sorted(
            (key, item)
            for key, item in parse_qsl(parsed.query, keep_blank_values=False)
            if key.casefold() not in TRACKING_QUERY_KEYS
        )
    )
    return urlunsplit(("https", f"{host}{port}", path, query, ""))


def allowed_request_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    host = (parsed.hostname or "").lower()
    if host not in ALLOWED_HOSTS or parsed.scheme != "https":
        raise ExtractionSkipped("URL outside the explicit HTTPS allowlist")
    port = f":{parsed.port}" if parsed.port and parsed.port != 443 else ""
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    query = urlencode(
        sorted(
            (key, item)
            for key, item in parse_qsl(parsed.query, keep_blank_values=False)
            if key.casefold() not in TRACKING_QUERY_KEYS
        )
    )
    return urlunsplit(("https", f"{host}{port}", path, query, ""))


def _meta_content(soup: BeautifulSoup, *names: str) -> str | None:
    for name in names:
        node = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
        if node and node.get("content"):
            return " ".join(str(node["content"]).split())
    return None


def _jsonld_nodes(soup: BeautifulSoup) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "")
        except (TypeError, json.JSONDecodeError):
            continue
        pending = data if isinstance(data, list) else [data]
        for item in pending:
            if not isinstance(item, dict):
                continue
            nodes.append(item)
            graph = item.get("@graph")
            if isinstance(graph, list):
                nodes.extend(node for node in graph if isinstance(node, dict))
    return nodes


def _jsonld_value(nodes: list[dict[str, Any]], *keys: str) -> str | None:
    for node in nodes:
        for key in keys:
            value = node.get(key)
            if isinstance(value, str) and value.strip():
                return " ".join(value.split())
            if isinstance(value, dict) and isinstance(value.get("name"), str):
                return " ".join(value["name"].split())
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and isinstance(item.get("name"), str):
                        return " ".join(item["name"].split())
    return None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    cleaned = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        match = re.search(r"\b((?:19|20)\d{2})\b", cleaned)
        return datetime(int(match.group(1)), 1, 1) if match else None


def _canonical_url(soup: BeautifulSoup, source_url: str) -> str:
    node = soup.find("link", attrs={"rel": lambda value: value and "canonical" in value})
    candidate = str(node.get("href")) if node and node.get("href") else source_url
    return normalize_url(candidate)


def _title(soup: BeautifulSoup, jsonld: list[dict[str, Any]]) -> str:
    h1 = soup.find("h1")
    candidates = (
        h1.get_text(" ", strip=True) if h1 else None,
        _meta_content(soup, "og:title", "twitter:title"),
        _jsonld_value(jsonld, "headline", "name"),
    )
    for candidate in candidates:
        if candidate and 3 <= len(candidate) <= 300:
            return re.sub(r"\s*[|\-]\s*(BYU Speeches|The Church of Jesus Christ.*)$", "", candidate).strip()
    raise ExtractionSkipped("missing trustworthy title")


def _author(soup: BeautifulSoup, jsonld: list[dict[str, Any]], source_url: str) -> str | None:
    candidates = [
        _meta_content(soup, "author", "article:author", "citation_author"),
        _jsonld_value(jsonld, "author", "creator"),
    ]
    for selector in (".author-name", ".single-speech__speaker", "[rel='author']", ".byline"):
        node = soup.select_one(selector)
        if node:
            candidates.append(node.get_text(" ", strip=True))
    for candidate in candidates:
        if not candidate:
            continue
        cleaned = re.sub(r"^(By|Por)\s+", "", candidate, flags=re.I).strip()
        if 2 <= len(cleaned) <= 100 and len(cleaned.split()) <= 10:
            return cleaned
    if "speeches.byu.edu/talks/" in source_url:
        parts = [part for part in urlsplit(source_url).path.split("/") if part]
        if len(parts) >= 3:
            return " ".join(word.capitalize() if len(word) > 1 else f"{word.upper()}." for word in parts[1].split("-"))
    return None


def _published_at(soup: BeautifulSoup, jsonld: list[dict[str, Any]], canonical_url: str) -> datetime | None:
    candidates = (
        _meta_content(soup, "article:published_time", "date", "citation_publication_date"),
        _jsonld_value(jsonld, "datePublished", "dateCreated"),
        soup.find("time").get("datetime") if soup.find("time") else None,
    )
    for candidate in candidates:
        parsed = _parse_datetime(candidate)
        if parsed:
            return parsed
    match = re.search(r"/((?:19|20)\d{2})/", canonical_url)
    return datetime(int(match.group(1)), 1, 1) if match else None


def _clean_main_text(soup: BeautifulSoup, selectors: tuple[str, ...]) -> tuple[str, str]:
    for selector in selectors:
        node = soup.select_one(selector)
        if not isinstance(node, Tag):
            continue
        fragment = BeautifulSoup(str(node), "lxml")
        for unwanted in fragment.select(
            "script, style, noscript, nav, header, footer, aside, form, button, svg, "
            "[aria-hidden='true'], .notes, .footnotes, [class*='share'], [class*='related']"
        ):
            unwanted.decompose()

        blocks: list[str] = []
        seen: set[str] = set()
        for block in fragment.select("h2, h3, p, li"):
            text = " ".join(block.get_text(" ", strip=True).split())
            key = text.casefold()
            if len(text) < 20 or key in seen:
                continue
            seen.add(key)
            blocks.append(text)
        content = "\n\n".join(blocks)
        if len(content) >= MIN_CONTENT_CHARACTERS and len(blocks) >= 4:
            return content, selector
    raise ExtractionSkipped("clean main content did not meet the conservative quality threshold")


SCRIPTURE_REF_RE = re.compile(
    r"\b(?:1|2|3)?\s?(?:Nephi|Alma|Mosiah|Moroni|Matthew|John|Romans)"
    r"\s+\d{1,3}:\d{1,3}(?:-\d{1,3})?\b|"
    r"\b(?:Doctrine and Covenants|D&C)\s+\d{1,3}:\d{1,3}(?:-\d{1,3})?\b",
    flags=re.I,
)


def extract_document(target: CuratedTarget, response: httpx.Response) -> ExtractedDocument:
    content_type = response.headers.get("content-type", "").lower()
    if response.status_code != 200:
        raise ExtractionSkipped(f"HTTP {response.status_code}")
    if "text/html" not in content_type:
        raise ExtractionSkipped(f"unsupported content type: {content_type or 'missing'}")
    if len(response.content) > MAX_RESPONSE_BYTES:
        raise ExtractionSkipped("response exceeded the configured size limit")

    source_url = normalize_url(str(response.url))
    soup = BeautifulSoup(response.text, "lxml")
    jsonld = _jsonld_nodes(soup)
    canonical_url = _canonical_url(soup, source_url)
    text, selector = _clean_main_text(soup, target.body_selectors)
    title = _title(soup, jsonld)
    author = _author(soup, jsonld, source_url)
    if target.document_type == "gospel_topic":
        author = None
    published_at = _published_at(soup, jsonld, canonical_url)
    metadata_tags = _meta_content(soup, "keywords", "news_keywords")
    tags = set(target.default_tags)
    if metadata_tags:
        tags.update(value.strip() for value in metadata_tags.split(",") if 2 <= len(value.strip()) <= 80)
    scripture_refs = tuple(sorted({match.group(0) for match in SCRIPTURE_REF_RE.finditer(text)}))
    return ExtractedDocument(
        target=target,
        source_url=source_url,
        normalized_url=normalize_url(source_url),
        canonical_url=canonical_url,
        title=title,
        author=author,
        published_at=published_at,
        language=target.language,
        text=text,
        tags=tuple(sorted(tags)),
        scripture_refs=scripture_refs,
        extraction_selector=selector,
    )


def fetch_allowed(client: httpx.Client, url: str, max_redirects: int = 3) -> httpx.Response:
    current_url = allowed_request_url(url)
    for _ in range(max_redirects + 1):
        response = client.get(current_url)
        if not response.is_redirect:
            return response
        location = response.headers.get("location")
        if not location:
            raise ExtractionSkipped("redirect response did not include a location")
        current_url = allowed_request_url(urljoin(current_url, location))
    raise ExtractionSkipped("too many redirects")


def split_chunks(text: str) -> list[tuple[int, int, str]]:
    chunks: list[tuple[int, int, str]] = []
    cursor = 0
    text_length = len(text)
    separators = ("\n\n", ". ", "; ", ", ", " ")
    while cursor < text_length:
        while cursor < text_length and text[cursor].isspace():
            cursor += 1
        if cursor >= text_length:
            break
        remaining = text_length - cursor
        if remaining <= CHUNK_MAX_CHARACTERS:
            end = text_length
        else:
            minimum_end = cursor + CHUNK_MIN_CHARACTERS
            preferred_end = cursor + CHUNK_TARGET_CHARACTERS
            maximum_end = min(cursor + CHUNK_MAX_CHARACTERS, text_length)
            end = 0
            for separator in separators:
                before = text.rfind(separator, minimum_end, preferred_end + 1)
                after = text.find(separator, preferred_end, maximum_end + 1)
                candidates = [
                    position + len(separator)
                    for position in (before, after)
                    if position >= minimum_end
                ]
                if candidates:
                    end = min(candidates, key=lambda position: abs(position - preferred_end))
                    break
            if not end:
                end = maximum_end
        content = text[cursor:end].strip()
        if content:
            chunks.append((cursor, cursor + len(text[cursor:end].rstrip()), content))
        cursor = end
    return chunks


def ensure_source(conn, target: CuratedTarget, stats: IngestionStats) -> Any:
    row = conn.execute("SELECT id FROM sources WHERE key = %s", (target.source_key,)).fetchone()
    if row:
        stats.sources_verified += 1
        return row[0]
    row = conn.execute(
        """
        INSERT INTO sources (
          key, name, base_url, source_type, language, default_language,
          is_official, trust_level, scraping_enabled, enabled, crawl_strategy,
          rate_limit, max_pages_per_run, robots_policy_notes, config
        )
        VALUES (
          %(key)s, %(name)s, %(base_url)s, %(source_type)s, %(language)s,
          %(language)s, %(is_official)s, %(trust_level)s, false, true,
          'curated_url_list', 1, 1, %(notes)s, %(config)s::jsonb
        )
        ON CONFLICT (key) DO NOTHING
        RETURNING id
        """,
        {
            "key": target.source_key,
            "name": target.source_name,
            "base_url": target.source_base_url,
            "source_type": target.source_type,
            "language": target.language,
            "is_official": target.source_type != "byu_speeches_en",
            "trust_level": 10 if target.source_type != "byu_speeches_en" else 7,
            "notes": "Lista curada de URLs; una solicitud por pagina, sin crawling.",
            "config": json.dumps(
                {
                    "ingestion_mode": INGESTION_MODE,
                    "ingestion_marker": INGESTION_MARKER,
                    "indexing": {"mode": "disabled"},
                }
            ),
        },
    ).fetchone()
    if row:
        stats.sources_created += 1
        return row[0]
    stats.sources_verified += 1
    return conn.execute("SELECT id FROM sources WHERE key = %s", (target.source_key,)).fetchone()[0]


def ensure_author(conn, author: str, stats: IngestionStats) -> None:
    row = conn.execute(
        """
        INSERT INTO authors (slug, display_name, sort_name, normalized_name, metadata)
        VALUES (%s, %s, %s, %s, %s::jsonb)
        ON CONFLICT (slug) DO NOTHING
        RETURNING id
        """,
        (
            slugify(author),
            author,
            author,
            normalized_name(author),
            json.dumps({"ingestion_mode": INGESTION_MODE, "ingestion_marker": INGESTION_MARKER}),
        ),
    ).fetchone()
    if row:
        stats.authors_created += 1
    else:
        stats.authors_verified += 1


def ensure_tag(conn, tag: str, language: str, stats: IngestionStats) -> None:
    row = conn.execute(
        """
        INSERT INTO tags (slug, name, normalized_name, language, description)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (slug) DO NOTHING
        RETURNING id
        """,
        (slugify(tag), tag, normalized_name(tag), language, f"Verified by {INGESTION_MARKER}."),
    ).fetchone()
    if row:
        stats.tags_created += 1
    else:
        stats.tags_verified += 1


def find_existing_document(conn, document: ExtractedDocument) -> Any | None:
    row = conn.execute(
        """
        SELECT id
        FROM documents
        WHERE canonical_url = ANY(%s)
           OR raw_metadata->>'source_url' = ANY(%s)
           OR raw_metadata->>'normalized_url' = ANY(%s)
        LIMIT 1
        """,
        (
            [document.canonical_url, document.normalized_url, document.source_url],
            [document.canonical_url, document.normalized_url, document.source_url],
            [document.canonical_url, document.normalized_url, document.source_url],
        ),
    ).fetchone()
    return row[0] if row else None


def ensure_document(conn, source_id: Any, document: ExtractedDocument, stats: IngestionStats) -> tuple[Any, bool]:
    existing_id = find_existing_document(conn, document)
    if existing_id:
        stats.documents_verified += 1
        return existing_id, False
    row = conn.execute(
        """
        INSERT INTO documents (
          source_id, title, canonical_url, author, published_at, language,
          category, tags, scripture_refs, text, raw_metadata, content_hash,
          status, version, is_indexed
        )
        VALUES (
          %(source_id)s, %(title)s, %(canonical_url)s, %(author)s,
          %(published_at)s, %(language)s, %(category)s, %(tags)s::jsonb,
          %(scripture_refs)s::jsonb, %(text)s, %(metadata)s::jsonb,
          %(content_hash)s, 'READY', 1, false
        )
        ON CONFLICT (canonical_url) DO NOTHING
        RETURNING id
        """,
        {
            "source_id": source_id,
            "title": document.title,
            "canonical_url": document.canonical_url,
            "author": document.author,
            "published_at": document.published_at,
            "language": document.language,
            "category": document.target.category,
            "tags": json.dumps(document.tags),
            "scripture_refs": json.dumps(document.scripture_refs),
            "text": document.text,
            "metadata": json.dumps(
                {
                    "ingestion_mode": INGESTION_MODE,
                    "ingestion_marker": INGESTION_MARKER,
                    "is_seed": False,
                    "seed_content": False,
                    "content_kind": "curated_real_html",
                    "content_type": "text/html",
                    "source_name": document.target.source_name,
                    "source_type": document.target.source_type,
                    "document_type": document.target.document_type,
                    "source_url": document.source_url,
                    "normalized_url": document.normalized_url,
                    "canonical_url": document.canonical_url,
                    "extraction_selector": document.extraction_selector,
                    "extracted_at": datetime.now().astimezone().isoformat(),
                    "extractor_version": EXTRACTOR_VERSION,
                }
            ),
            "content_hash": sha256_text(document.text),
        },
    ).fetchone()
    if row:
        stats.documents_created += 1
        return row[0], True
    stats.documents_verified += 1
    existing_id = find_existing_document(conn, document)
    if not existing_id:
        raise RuntimeError("document conflict occurred but the existing row could not be verified")
    return existing_id, False


def ensure_chunks(conn, document_id: Any, document: ExtractedDocument, stats: IngestionStats) -> None:
    for chunk_index, (start_char, end_char, content) in enumerate(split_chunks(document.text)):
        row = conn.execute(
            """
            INSERT INTO document_chunks (
              document_id, chunk_index, chunker_version, language, title,
              section_title, start_char, end_char, token_count, text,
              text_hash, metadata
            )
            VALUES (
              %(document_id)s, %(chunk_index)s, %(chunker_version)s,
              %(language)s, %(title)s, 'Curated source content',
              %(start_char)s, %(end_char)s, %(token_count)s, %(text)s,
              %(text_hash)s, %(metadata)s::jsonb
            )
            ON CONFLICT (document_id, chunk_index, chunker_version) DO NOTHING
            RETURNING id
            """,
            {
                "document_id": document_id,
                "chunk_index": chunk_index,
                "chunker_version": CHUNKER_VERSION,
                "language": document.language,
                "title": document.title,
                "start_char": start_char,
                "end_char": end_char,
                "token_count": len(content.split()),
                "text": content,
                "text_hash": sha256_text(content),
                "metadata": json.dumps(
                    {
                        "ingestion_mode": INGESTION_MODE,
                        "ingestion_marker": INGESTION_MARKER,
                        "is_seed": False,
                        "seed_content": False,
                        "content_type": "text/plain",
                        "source_url": document.source_url,
                        "canonical_url": document.canonical_url,
                        "document_id": str(document_id),
                        "extractor_version": EXTRACTOR_VERSION,
                    }
                ),
            },
        ).fetchone()
        if row:
            stats.chunks_created += 1
        else:
            stats.chunks_verified += 1


def persist_document(conn, document: ExtractedDocument, stats: IngestionStats) -> None:
    source_id = ensure_source(conn, document.target, stats)
    if document.author:
        ensure_author(conn, document.author, stats)
    for tag in document.tags:
        ensure_tag(conn, tag, document.language, stats)
    document_id, _ = ensure_document(conn, source_id, document, stats)
    ensure_chunks(conn, document_id, document, stats)


def ingest_curated_documents(conn, client: httpx.Client, delay_seconds: float = REQUEST_DELAY_SECONDS) -> IngestionStats:
    stats = IngestionStats()
    conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (INGESTION_MARKER,))
    for index, target in enumerate(TARGETS):
        try:
            response = fetch_allowed(client, target.url)
            document = extract_document(target, response)
            persist_document(conn, document, stats)
        except (httpx.HTTPError, ExtractionSkipped) as exc:
            stats.skipped.append((target.url, str(exc)))
        if delay_seconds and index < len(TARGETS) - 1:
            time.sleep(delay_seconds)
    return stats


def print_summary(stats: IngestionStats) -> None:
    print("Curated real content ingestion v1 completed.")
    print(f"Sources:   {stats.sources_created} created, {stats.sources_verified} verified")
    print(f"Documents: {stats.documents_created} created, {stats.documents_verified} verified")
    print(f"Chunks:    {stats.chunks_created} created, {stats.chunks_verified} verified")
    print(f"Authors:   {stats.authors_created} created, {stats.authors_verified} verified")
    print(f"Tags:      {stats.tags_created} created, {stats.tags_verified} verified")
    print(f"Skipped:   {len(stats.skipped)}")
    for url, reason in stats.skipped:
        print(f"  SKIPPED {url} - {reason}")


def main() -> int:
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        print("ERROR: DATABASE_URL is not set. Set it and run the script again.", file=sys.stderr)
        return 2
    connect_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    try:
        with (
            psycopg.connect(connect_url) as conn,
            httpx.Client(
                headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
                timeout=REQUEST_TIMEOUT_SECONDS,
                follow_redirects=False,
            ) as client,
        ):
            stats = ingest_curated_documents(conn, client)
            conn.commit()
    except Exception as exc:
        print(
            f"ERROR: curated ingestion failed ({type(exc).__name__}). "
            "DATABASE_URL was not printed and no destructive operation was attempted.",
            file=sys.stderr,
        )
        return 1
    print_summary(stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
