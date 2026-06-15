from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.schemas.ingestion import N8nDocumentIngestionRequest
from app.services.curated_sources import curated_source_for_url


INGESTION_MODE = "n8n_curated_v1"
CHUNKER_VERSION = "n8n-curated-v1"
CHUNK_MIN_CHARACTERS = 800
CHUNK_TARGET_CHARACTERS = 1_000
CHUNK_MAX_CHARACTERS = 1_200
TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}
SENSITIVE_METADATA_KEYS = {
    "api_key",
    "authorization",
    "cookie",
    "database_url",
    "ingestion_api_key",
    "password",
    "secret",
    "token",
}


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
    port = f":{parsed.port}" if parsed.port and parsed.port not in {80, 443} else ""
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
    return urlunsplit((parsed.scheme.lower(), f"{host}{port}", path, query, ""))


def normalize_content(value: str) -> str:
    lines = [" ".join(line.split()) for line in value.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def safe_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: safe_metadata(item)
            for key, item in value.items()
            if key.casefold().replace("-", "_") not in SENSITIVE_METADATA_KEYS
            and key.casefold() not in {"file_url", "storage_path"}
        }
    if isinstance(value, list):
        return [safe_metadata(item) for item in value]
    return value


def split_chunks(text: str) -> list[tuple[int, int, str]]:
    chunks: list[tuple[int, int, str]] = []
    cursor = 0
    while cursor < len(text):
        while cursor < len(text) and text[cursor].isspace():
            cursor += 1
        if cursor >= len(text):
            break
        if len(text) - cursor <= CHUNK_MAX_CHARACTERS:
            end = len(text)
        else:
            minimum_end = cursor + CHUNK_MIN_CHARACTERS
            preferred_end = cursor + CHUNK_TARGET_CHARACTERS
            maximum_end = min(cursor + CHUNK_MAX_CHARACTERS, len(text))
            candidates: list[int] = []
            for separator in ("\n\n", ". ", "; ", ", ", " "):
                before = text.rfind(separator, minimum_end, preferred_end + 1)
                after = text.find(separator, preferred_end, maximum_end + 1)
                candidates.extend(
                    position + len(separator)
                    for position in (before, after)
                    if position >= minimum_end
                )
                if candidates:
                    break
            end = min(candidates, key=lambda position: abs(position - preferred_end)) if candidates else maximum_end
        content = text[cursor:end].strip()
        if content:
            chunks.append((cursor, cursor + len(text[cursor:end].rstrip()), content))
        cursor = end
    return chunks


def _ensure_source(conn, payload: N8nDocumentIngestionRequest) -> Any:
    source_url = normalize_url(payload.source_url)
    source = curated_source_for_url(source_url)
    if not source:
        raise ValueError("source URL is outside the curated allowlist")
    row = conn.execute(
        "SELECT id FROM sources WHERE key = %s",
        (source.key,),
    ).fetchone()
    if row:
        return row[0]
    row = conn.execute(
        """
        INSERT INTO sources (
          key, name, base_url, source_type, language, default_language,
          is_official, trust_level, scraping_enabled, enabled, crawl_strategy,
          rate_limit, max_pages_per_run, robots_policy_notes, config
        )
        VALUES (
          %(key)s, %(name)s, %(base_url)s, %(source_type)s, 'es', 'es',
          %(is_official)s, %(trust_level)s, false, true,
          'n8n_curated_payload', 1, 1,
          'Contenido limpio enviado por n8n; sin crawling desde la API.',
          %(config)s::jsonb
        )
        ON CONFLICT (key) DO NOTHING
        RETURNING id
        """,
        {
            "key": source.key,
            "name": source.name,
            "base_url": source.base_url,
            "source_type": source.source_type,
            "is_official": source.is_official,
            "trust_level": source.trust_level,
            "config": json.dumps(
                {
                    "ingestion_mode": INGESTION_MODE,
                    "storage_used": False,
                    "authorized_curated_source": True,
                }
            ),
        },
    ).fetchone()
    if row:
        return row[0]
    return conn.execute("SELECT id FROM sources WHERE key = %s", (source.key,)).fetchone()[0]


def _ensure_author(conn, author: str) -> None:
    conn.execute(
        """
        INSERT INTO authors (slug, display_name, sort_name, normalized_name, metadata)
        VALUES (%s, %s, %s, %s, %s::jsonb)
        ON CONFLICT (slug) DO NOTHING
        """,
        (
            slugify(author),
            author,
            author,
            normalized_name(author),
            json.dumps({"ingestion_mode": INGESTION_MODE}),
        ),
    )


def _ensure_tags(conn, tags: list[str]) -> None:
    for tag in tags:
        conn.execute(
            """
            INSERT INTO tags (slug, name, normalized_name, language, description)
            VALUES (%s, %s, %s, 'es', %s)
            ON CONFLICT (slug) DO NOTHING
            """,
            (slugify(tag), tag, normalized_name(tag), "Etiqueta verificada por ingesta n8n."),
        )


def _find_existing(conn, urls: list[str], content_hash: str):
    return conn.execute(
        """
        SELECT id::text, source_id::text, canonical_url
        FROM documents
        WHERE canonical_url = ANY(%s)
           OR raw_metadata->>'source_url' = ANY(%s)
           OR raw_metadata->>'normalized_url' = ANY(%s)
           OR content_hash = %s
        ORDER BY created_at
        LIMIT 1
        """,
        (urls, urls, urls, content_hash),
    ).fetchone()


def ingest_document(conn, payload: N8nDocumentIngestionRequest) -> dict[str, Any]:
    content = normalize_content(payload.content)
    content_hash = sha256_text(content)
    source_url = normalize_url(payload.source_url)
    canonical_url = normalize_url(payload.canonical_url or payload.source_url)
    source = curated_source_for_url(source_url)
    if not source:
        raise ValueError("source URL is outside the curated allowlist")
    urls = list(dict.fromkeys([canonical_url, source_url]))
    conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (content_hash,))

    existing = _find_existing(conn, urls, content_hash)
    if existing:
        chunks = conn.execute(
            "SELECT count(*)::int FROM document_chunks WHERE document_id = %s",
            (existing[0],),
        ).fetchone()[0]
        return {
            "status": "verified_existing",
            "document_id": existing[0],
            "source_id": existing[1],
            "canonical_url": existing[2],
            "content_hash": content_hash,
            "chunks": chunks,
        }

    source_id = _ensure_source(conn, payload)
    if payload.author:
        _ensure_author(conn, payload.author)
    _ensure_tags(conn, payload.tags)
    metadata = {
        **safe_metadata(payload.metadata),
        "ingestion_mode": INGESTION_MODE,
        "language": "es",
        "is_seed": False,
        "seed_content": False,
        "ingested_by": "n8n",
        "storage_used": False,
        "source_name": source.name,
        "submitted_source_name": payload.source_name,
        "source_type": source.source_type,
        "source_url": source_url,
        "normalized_url": source_url,
        "canonical_url": canonical_url,
        "content_hash": content_hash,
        "content_type": payload.content_type,
        "source_format": "pdf" if payload.content_type.casefold() in {"application/pdf", "pdf"} else "web",
        "pdf_url": source_url if payload.content_type.casefold() in {"application/pdf", "pdf"} else None,
        "summary": payload.summary,
        "ingested_at": datetime.now().astimezone().isoformat(),
    }
    row = conn.execute(
        """
        INSERT INTO documents (
          source_id, title, canonical_url, author, published_at, language,
          category, tags, scripture_refs, text, raw_metadata, content_hash,
          status, version, is_indexed
        )
        VALUES (
          %(source_id)s, %(title)s, %(canonical_url)s, %(author)s,
          %(published_at)s, 'es', %(category)s, %(tags)s::jsonb, '[]'::jsonb,
          %(text)s, %(metadata)s::jsonb, %(content_hash)s, 'READY', 1, false
        )
        ON CONFLICT (canonical_url) DO NOTHING
        RETURNING id::text
        """,
        {
            "source_id": source_id,
            "title": payload.title,
            "canonical_url": canonical_url,
            "author": payload.author,
            "published_at": payload.published_at,
            "category": payload.content_type,
            "tags": json.dumps(payload.tags),
            "text": content,
            "metadata": json.dumps(metadata),
            "content_hash": content_hash,
        },
    ).fetchone()
    if not row:
        existing = _find_existing(conn, urls, content_hash)
        if not existing:
            raise RuntimeError("document conflict occurred but the existing row could not be verified")
        return {
            "status": "verified_existing",
            "document_id": existing[0],
            "source_id": existing[1],
            "canonical_url": existing[2],
            "content_hash": content_hash,
            "chunks": 0,
        }

    document_id = row[0]
    chunks = split_chunks(content)
    for chunk_index, (start_char, end_char, chunk) in enumerate(chunks):
        conn.execute(
            """
            INSERT INTO document_chunks (
              document_id, chunk_index, chunker_version, language, title,
              section_title, start_char, end_char, token_count, text,
              text_hash, metadata
            )
            VALUES (
              %(document_id)s, %(chunk_index)s, %(chunker_version)s, 'es',
              %(title)s, 'Contenido curado', %(start_char)s, %(end_char)s,
              %(token_count)s, %(text)s, %(text_hash)s, %(metadata)s::jsonb
            )
            ON CONFLICT (document_id, chunk_index, chunker_version) DO NOTHING
            """,
            {
                "document_id": document_id,
                "chunk_index": chunk_index,
                "chunker_version": CHUNKER_VERSION,
                "title": payload.title,
                "start_char": start_char,
                "end_char": end_char,
                "token_count": len(chunk.split()),
                "text": chunk,
                "text_hash": sha256_text(chunk),
                "metadata": json.dumps(
                    {
                        "ingestion_mode": INGESTION_MODE,
                        "language": "es",
                        "is_seed": False,
                        "ingested_by": "n8n",
                        "storage_used": False,
                        "source_url": source_url,
                        "canonical_url": canonical_url,
                        "content_hash": content_hash,
                        "document_id": document_id,
                    }
                ),
            },
        )
    return {
        "status": "created",
        "document_id": document_id,
        "source_id": str(source_id),
        "canonical_url": canonical_url,
        "content_hash": content_hash,
        "chunks": len(chunks),
    }
