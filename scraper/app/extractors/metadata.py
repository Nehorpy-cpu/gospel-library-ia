import json
import re
from datetime import datetime
from urllib.parse import unquote, urlparse

import dateparser
from bs4 import BeautifulSoup
from langdetect import DetectorFactory, LangDetectException, detect

DetectorFactory.seed = 7

SCRIPTURE_PATTERNS = [
    r"\b(?:1|2|3)?\s?Nephi\s+\d+:\d+(?:-\d+)?\b",
    r"\bAlma\s+\d+:\d+(?:-\d+)?\b",
    r"\bMosiah\s+\d+:\d+(?:-\d+)?\b",
    r"\bMoroni\s+\d+:\d+(?:-\d+)?\b",
    r"\bDoctrine and Covenants\s+\d+:\d+(?:-\d+)?\b",
    r"\bD&C\s+\d+:\d+(?:-\d+)?\b",
    r"\bMateo\s+\d+:\d+(?:-\d+)?\b",
    r"\bMatthew\s+\d+:\d+(?:-\d+)?\b",
    r"\bJohn\s+\d+:\d+(?:-\d+)?\b",
    r"\bJuan\s+\d+:\d+(?:-\d+)?\b",
    r"\bRomans\s+\d+:\d+(?:-\d+)?\b",
    r"\bRomanos\s+\d+:\d+(?:-\d+)?\b",
]

SCRIPTURE_BOOK_ALIASES = {
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


def meta_content(soup: BeautifulSoup, *names: str) -> str | None:
    for name in names:
        tag = soup.find("meta", attrs={"name": name}) or soup.find("meta", attrs={"property": name})
        if tag and tag.get("content"):
            return tag["content"].strip()
    return None


def _clean_value(value: str | None) -> str | None:
    if not value:
        return None
    value = re.sub(r"\s+", " ", value).strip(" \t\r\n-|")
    return value or None


def _first_text(soup: BeautifulSoup, selector: str) -> str | None:
    node = soup.select_one(selector)
    return node.get_text(" ", strip=True) if node else None


def _jsonld_values(soup: BeautifulSoup, *keys: str) -> list[str]:
    values: list[str] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "")
        except Exception:
            continue
        nodes = data if isinstance(data, list) else [data]
        index = 0
        while index < len(nodes):
            node = nodes[index]
            index += 1
            if not isinstance(node, dict):
                continue
            graph = node.get("@graph")
            if isinstance(graph, list):
                nodes.extend(item for item in graph if isinstance(item, dict))
            for key in keys:
                value = node.get(key)
                if isinstance(value, str):
                    values.append(value)
                elif isinstance(value, dict) and isinstance(value.get("name"), str):
                    values.append(value["name"])
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            values.append(item)
                        elif isinstance(item, dict) and isinstance(item.get("name"), str):
                            values.append(item["name"])
    return values


def _title_from_url(url: str | None) -> str | None:
    if not url:
        return None
    path = urlparse(url).path.strip("/")
    if not path:
        return None
    parts = [unquote(part) for part in path.split("/") if part]
    if not parts:
        return None
    slug = parts[-1]
    if slug.lower().endswith(".pdf"):
        slug = slug.rsplit(".", 1)[0]
    if slug.lower() in {"spa", "eng", "por", "bofm", "talks", "study"} and len(parts) > 1:
        slug = parts[-2]
    if slug.isdigit() and len(parts) > 1:
        slug = f"{parts[-2]} {slug}"
    slug = re.sub(r"[-_]+", " ", slug)
    slug = re.sub(r"\s+", " ", slug).strip()
    return slug.title() if slug else None


def _title_from_text(text: str | None) -> str | None:
    if not text:
        return None
    blocked = {"skip to main content", "main content", "menu", "navigation"}
    for line in text.splitlines():
        value = _clean_value(line)
        if value and value.lower() not in blocked and len(value) > 2:
            return value[:300]
    return None


def extract_title(soup: BeautifulSoup, url: str | None = None, text: str | None = None) -> str:
    candidates = [
        soup.find("h1").get_text(" ", strip=True) if soup.find("h1") else None,
        _first_text(soup, "[data-testid*='title']"),
        _first_text(soup, "[class*='title']"),
        soup.title.get_text(" ", strip=True) if soup.title else None,
        meta_content(soup, "og:title", "twitter:title"),
        meta_content(soup, "title", "dc.title", "DC.title"),
        *_jsonld_values(soup, "headline", "name"),
        _title_from_text(text),
        _title_from_url(url),
    ]
    for candidate in candidates:
        value = _clean_value(candidate)
        if not value:
            continue
        value = re.sub(
            r"\s*(?:\||-|--)\s*(BYU Speeches|Church Newsroom|The Church of Jesus Christ.*)$",
            "",
            value,
            flags=re.I,
        )
        value = _clean_value(value)
        if value and value.lower() not in {"untitled document", "home", "speeches"}:
            return value[:300]
    return "Untitled document"


def extract_author(soup: BeautifulSoup) -> str | None:
    meta = meta_content(soup, "author", "article:author", "citation_author", "dc.creator", "DC.creator")
    if meta and (cleaned := _clean_author(meta)):
        return cleaned
    for value in _jsonld_values(soup, "author", "creator", "publisher"):
        if cleaned := _clean_author(value):
            return cleaned
    selectors = [
        "[rel='author']",
        ".author",
        ".speaker",
        ".byline",
        "p.byline",
        "span.byline",
        "a[href*='/speakers/']",
        "a[href*='/authors/']",
        "[class*='byline']",
        "[class*='author']",
        "[class*='speaker']",
        "[itemprop='author']",
        "[itemprop='creator']",
        "[data-speaker]",
        "[data-author]",
    ]
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            value = node.get("data-author") or node.get("data-speaker") or node.get_text(" ", strip=True)
            if cleaned := _clean_author(value):
                return cleaned
    text = soup.get_text("\n", strip=True)
    for pattern in [
        r"\b(?:By|Por)\s+([^\n|]{2,100})",
        r"\b(?:Speaker|Orador)\s*[:\-]\s*([^\n|]{2,100})",
        r"\b(?:Author|Autor)\s*[:\-]\s*([^\n|]{2,100})",
    ]:
        match = re.search(pattern, text)
        if match and (cleaned := _clean_author(match.group(1))):
            return cleaned
    return None


def _clean_author(value: str | None) -> str | None:
    value = _clean_value(value)
    if not value:
        return None
    value = re.sub(r"^(By|Por|Speaker|Orador|Author|Autor)\s*[:\-]?\s+", "", value, flags=re.I)
    value = re.sub(
        r"\s*(?:\||-|--)\s*(BYU Speeches|The Church of Jesus Christ.*)$",
        "",
        value,
        flags=re.I,
    )
    value = re.split(
        r"\s+(?:Las revistas|Ensign|Liahona|New Era|Friend|The author|La autora|El autor|Of the|De la|Del|De los|Primer|Segundo|Presidente|Apostol|Apostoles|Setenta|Obispado|Cuorum|Quorum|Consejo|Gracias|Como|Al igual|Mientras|Quizas|Dediquemos)\b",
        value,
        maxsplit=1,
        flags=re.I,
    )[0]
    value = _clean_value(value)
    if value and value.lower().startswith(("el elder ", "el presidente ", "el obispo ")):
        value = re.sub(r"^el\s+(elder|presidente|obispo)\s+", "", value, flags=re.I)
    if not value or len(value) > 90 or len(value.split()) > 8:
        return None
    blocked = {
        "church news",
        "byu speeches",
        "joseph smith papers",
        "the church of jesus christ",
        "the church of jesus christ of latter-day saints",
    }
    return None if value.lower() in blocked else value


def extract_published_at(soup: BeautifulSoup, text: str = "", url: str | None = None) -> datetime | None:
    values = [
        meta_content(
            soup,
            "article:published_time",
            "article:modified_time",
            "date",
            "pubdate",
            "citation_publication_date",
            "dc.date",
            "DC.date",
        ),
        *_jsonld_values(soup, "datePublished", "dateCreated", "dateModified", "uploadDate"),
        soup.find("time").get("datetime") if soup.find("time") else None,
        soup.find("time").get_text(" ", strip=True) if soup.find("time") else None,
    ]
    for value in values:
        if parsed := dateparser.parse(value or ""):
            return parsed
    date_match = re.search(r"\b(?:\d{1,2}\s+\w+\s+\d{4}|\w+\s+\d{1,2},\s+\d{4})\b", text)
    if date_match:
        return dateparser.parse(date_match.group(0))
    if url and (year_match := re.search(r"/((?:19|20)\d{2})(?:/|$)", url)):
        return dateparser.parse(year_match.group(1))
    return None


def detect_language(text: str, url: str | None = None) -> str | None:
    if url:
        path = urlparse(url).path.lower()
        if "/spa/" in path or "/es/" in path:
            return "es"
        if "/por/" in path or "/pt/" in path:
            return "pt"
    try:
        return detect(text[:5000]) if text.strip() else None
    except LangDetectException:
        return None


def extract_tags(soup: BeautifulSoup) -> list[str]:
    values: set[str] = set()
    keywords = meta_content(soup, "keywords", "news_keywords")
    if keywords:
        values.update(tag.strip() for tag in keywords.split(",") if tag.strip())
    for node in soup.select("a[rel='tag'], .tag, .tags a, [class*='tag'] a"):
        tag = node.get_text(" ", strip=True)
        if 2 <= len(tag) <= 80:
            values.add(tag)
    return sorted(values)


def extract_category(soup: BeautifulSoup) -> str | None:
    for selector in [".category", ".breadcrumb a:last-child", "[class*='category']"]:
        node = soup.select_one(selector)
        if node:
            value = node.get_text(" ", strip=True)
            if value and len(value) < 120:
                return value
    return meta_content(soup, "article:section")


def extract_scripture_refs(text: str) -> list[str]:
    refs: set[str] = set()
    for match in SCRIPTURE_REF_RE.finditer(text):
        refs.add(_normalize_scripture_ref(match.group(0)))
    return sorted(refs)


def _normalize_scripture_ref(value: str) -> str:
    match = SCRIPTURE_REF_RE.search(value.strip())
    if not match:
        return value.strip()
    book_key = re.sub(r"\s+", " ", match.group("book").lower().replace("dyc", "d&c")).strip()
    book = SCRIPTURE_BOOK_ALIASES.get(book_key, match.group("book").strip())
    suffix = f"-{int(match.group('end_verse'))}" if match.group("end_verse") else ""
    return f"{book} {int(match.group('chapter'))}:{int(match.group('verse'))}{suffix}"
