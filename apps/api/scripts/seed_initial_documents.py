"""Insert a small, idempotent set of real-source documents for end-to-end tests.

The script does not scrape remote pages, delete rows, create embeddings, or call
OpenAI/Qdrant. Seed text is an original test summary, not a source transcript.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import psycopg


SEED_MARKER = "initial-content-seed-v1"
CHUNKER_VERSION = "seed-v1"


@dataclass(frozen=True)
class SourceSeed:
    key: str
    name: str
    base_url: str
    source_type: str
    language: str
    is_official: bool
    trust_level: int


@dataclass(frozen=True)
class DocumentSeed:
    source_key: str
    title: str
    source_url: str
    author: str | None
    published_at: datetime | None
    language: str
    category: str
    tags: tuple[str, ...]
    scripture_refs: tuple[str, ...]
    summary: str


SOURCES = (
    SourceSeed(
        key="church_manuals",
        name="Manuales de la Iglesia",
        base_url="https://www.churchofjesuschrist.org/study/manual",
        source_type="church_manuals",
        language="en",
        is_official=True,
        trust_level=10,
    ),
    SourceSeed(
        key="general_conference",
        name="Conferencia General",
        base_url="https://www.churchofjesuschrist.org/study/general-conference",
        source_type="general_conference",
        language="en",
        is_official=True,
        trust_level=10,
    ),
    SourceSeed(
        key="byu_speeches",
        name="BYU Speeches English",
        base_url="https://speeches.byu.edu/talks/",
        source_type="byu_speeches_en",
        language="en",
        is_official=False,
        trust_level=7,
    ),
)


DOCUMENTS = (
    DocumentSeed(
        source_key="church_manuals",
        title="Faith in Jesus Christ",
        source_url=(
            "https://www.churchofjesuschrist.org/study/manual/"
            "gospel-topics/faith-in-jesus-christ?lang=eng"
        ),
        author=None,
        published_at=None,
        language="en",
        category="Gospel Topics",
        tags=("Faith", "Jesus Christ", "Gospel Topics"),
        scripture_refs=(),
        summary=(
            "[SEED/TEST CONTENT] Original test summary: this official Gospel Topics "
            "page introduces faith in Jesus Christ as trust in Him and as a principle "
            "that leads to action. Read the linked source for the authoritative text."
        ),
    ),
    DocumentSeed(
        source_key="church_manuals",
        title="God the Father",
        source_url=(
            "https://www.churchofjesuschrist.org/study/manual/"
            "gospel-topics/god-the-father?lang=eng"
        ),
        author=None,
        published_at=None,
        language="en",
        category="Gospel Topics",
        tags=("God the Father", "Gospel Topics"),
        scripture_refs=(),
        summary=(
            "[SEED/TEST CONTENT] Original test summary: this official Gospel Topics "
            "page presents foundational information about God the Father and directs "
            "readers to related study. Read the linked source for the authoritative text."
        ),
    ),
    DocumentSeed(
        source_key="general_conference",
        title="We Talk of Christ",
        source_url=(
            "https://www.churchofjesuschrist.org/study/general-conference/"
            "2020/10/45andersen?lang=eng"
        ),
        author="Neil L. Andersen",
        published_at=datetime.fromisoformat("2020-10-04T00:00:00+00:00"),
        language="en",
        category="General Conference",
        tags=("Jesus Christ", "Faith", "General Conference"),
        scripture_refs=(),
        summary=(
            "[SEED/TEST CONTENT] Original test summary: Elder Neil L. Andersen invites "
            "disciples to speak more often of Jesus Christ and to center faith and "
            "teaching on Him. Read the linked conference address for the full message."
        ),
    ),
    DocumentSeed(
        source_key="general_conference",
        title="Be One with Christ",
        source_url=(
            "https://www.churchofjesuschrist.org/study/general-conference/"
            "2024/04/27cook?lang=eng"
        ),
        author="Quentin L. Cook",
        published_at=datetime.fromisoformat("2024-04-07T00:00:00+00:00"),
        language="en",
        category="General Conference",
        tags=("Jesus Christ", "Unity", "General Conference"),
        scripture_refs=(),
        summary=(
            "[SEED/TEST CONTENT] Original test summary: Elder Quentin L. Cook teaches "
            "about unity through love for Jesus Christ, covenants, and peaceful "
            "discipleship. Read the linked conference address for the full message."
        ),
    ),
    DocumentSeed(
        source_key="byu_speeches",
        title="Faith in the Lord Jesus Christ",
        source_url=(
            "https://speeches.byu.edu/talks/gene-r-cook/"
            "faith-in-the-lord-jesus-christ/"
        ),
        author="Gene R. Cook",
        published_at=None,
        language="en",
        category="BYU Speeches",
        tags=("Faith", "Jesus Christ", "BYU Speeches"),
        scripture_refs=(),
        summary=(
            "[SEED/TEST CONTENT] Original test summary: Elder Gene R. Cook discusses "
            "faith in the Lord Jesus Christ as a principle of action that can guide "
            "daily decisions and discipleship. Read the linked speech for the full text."
        ),
    ),
)


@dataclass
class SeedStats:
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
    normalized = normalized_name(value)
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")


def ensure_source(conn, source: SourceSeed, stats: SeedStats) -> Any:
    row = conn.execute("SELECT id FROM sources WHERE key = %s", (source.key,)).fetchone()
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
          'manual_seed_only', 1, 1, %(robots_policy_notes)s, %(config)s::jsonb
        )
        ON CONFLICT (key) DO NOTHING
        RETURNING id
        """,
        {
            "key": source.key,
            "name": source.name,
            "base_url": source.base_url,
            "source_type": source.source_type,
            "language": source.language,
            "is_official": source.is_official,
            "trust_level": source.trust_level,
            "robots_policy_notes": "Seed controlado sin solicitudes HTTP ni scraping.",
            "config": json.dumps(
                {
                    "seed_marker": SEED_MARKER,
                    "source_type": source.source_type,
                    "indexing": {"mode": "disabled_for_seed"},
                }
            ),
        },
    ).fetchone()
    if row:
        stats.sources_created += 1
        return row[0]

    stats.sources_verified += 1
    return conn.execute("SELECT id FROM sources WHERE key = %s", (source.key,)).fetchone()[0]


def ensure_author(conn, author: str, stats: SeedStats) -> None:
    slug = slugify(author)
    row = conn.execute(
        """
        INSERT INTO authors (slug, display_name, sort_name, normalized_name, metadata)
        VALUES (%s, %s, %s, %s, %s::jsonb)
        ON CONFLICT (slug) DO NOTHING
        RETURNING id
        """,
        (
            slug,
            author,
            author,
            normalized_name(author),
            json.dumps({"seed_marker": SEED_MARKER}),
        ),
    ).fetchone()
    if row:
        stats.authors_created += 1
    else:
        stats.authors_verified += 1


def ensure_tag(conn, tag: str, language: str, stats: SeedStats) -> None:
    row = conn.execute(
        """
        INSERT INTO tags (slug, name, normalized_name, language, description)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (slug) DO NOTHING
        RETURNING id
        """,
        (
            slugify(tag),
            tag,
            normalized_name(tag),
            language,
            f"Tag verified by {SEED_MARKER}.",
        ),
    ).fetchone()
    if row:
        stats.tags_created += 1
    else:
        stats.tags_verified += 1


def ensure_document(
    conn,
    source_id: Any,
    source_type: str,
    document: DocumentSeed,
    stats: SeedStats,
) -> Any:
    row = conn.execute(
        """
        SELECT id
        FROM documents
        WHERE canonical_url = %s OR raw_metadata->>'source_url' = %s
        ORDER BY CASE WHEN canonical_url = %s THEN 0 ELSE 1 END
        LIMIT 1
        """,
        (document.source_url, document.source_url, document.source_url),
    ).fetchone()
    if row:
        stats.documents_verified += 1
        return row[0]

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
          %(scripture_refs)s::jsonb, %(text)s, %(raw_metadata)s::jsonb,
          %(content_hash)s, 'READY', 1, false
        )
        ON CONFLICT (canonical_url) DO NOTHING
        RETURNING id
        """,
        {
            "source_id": source_id,
            "title": document.title,
            "canonical_url": document.source_url,
            "author": document.author,
            "published_at": document.published_at,
            "language": document.language,
            "category": document.category,
            "tags": json.dumps(document.tags),
            "scripture_refs": json.dumps(document.scripture_refs),
            "text": document.summary,
            "raw_metadata": json.dumps(
                {
                    "ingestion_mode": "seed_v1",
                    "is_seed": True,
                    "seed_marker": SEED_MARKER,
                    "seed_content": True,
                    "content_kind": "original_test_summary",
                    "source_type": source_type,
                    "source_url": document.source_url,
                    "authoritative_text_available_at_source": True,
                }
            ),
            "content_hash": sha256_text(document.summary),
        },
    ).fetchone()
    if row:
        stats.documents_created += 1
        return row[0]

    stats.documents_verified += 1
    return conn.execute(
        """
        SELECT id
        FROM documents
        WHERE canonical_url = %s OR raw_metadata->>'source_url' = %s
        LIMIT 1
        """,
        (document.source_url, document.source_url),
    ).fetchone()[0]


def ensure_chunk(conn, document_id: Any, document: DocumentSeed, stats: SeedStats) -> None:
    metadata = {
        "ingestion_mode": "seed_v1",
        "is_seed": True,
        "seed_marker": SEED_MARKER,
        "seed_content": True,
        "content_kind": "original_test_summary",
        "source_url": document.source_url,
        "document_id": str(document_id),
    }
    row = conn.execute(
        """
        INSERT INTO document_chunks (
          document_id, chunk_index, chunker_version, language, title,
          section_title, start_char, end_char, token_count, text, text_hash,
          metadata
        )
        VALUES (
          %(document_id)s, 0, %(chunker_version)s, %(language)s, %(title)s,
          'Seed summary', 0, %(end_char)s, %(token_count)s, %(text)s,
          %(text_hash)s, %(metadata)s::jsonb
        )
        ON CONFLICT (document_id, chunk_index, chunker_version) DO NOTHING
        RETURNING id
        """,
        {
            "document_id": document_id,
            "chunker_version": CHUNKER_VERSION,
            "language": document.language,
            "title": document.title,
            "end_char": len(document.summary),
            "token_count": len(document.summary.split()),
            "text": document.summary,
            "text_hash": sha256_text(document.summary),
            "metadata": json.dumps(metadata),
        },
    ).fetchone()
    if row:
        stats.chunks_created += 1
    else:
        stats.chunks_verified += 1


def seed_initial_documents(conn) -> SeedStats:
    stats = SeedStats()
    conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (SEED_MARKER,))

    source_ids: dict[str, Any] = {}
    source_types: dict[str, str] = {}
    for source in SOURCES:
        source_ids[source.key] = ensure_source(conn, source, stats)
        source_types[source.key] = source.source_type

    seen_authors: set[str] = set()
    seen_tags: set[tuple[str, str]] = set()
    for document in DOCUMENTS:
        if document.author and document.author not in seen_authors:
            ensure_author(conn, document.author, stats)
            seen_authors.add(document.author)
        for tag in document.tags:
            tag_key = (slugify(tag), document.language)
            if tag_key not in seen_tags:
                ensure_tag(conn, tag, document.language, stats)
                seen_tags.add(tag_key)

        document_id = ensure_document(
            conn,
            source_ids[document.source_key],
            source_types[document.source_key],
            document,
            stats,
        )
        ensure_chunk(conn, document_id, document, stats)

    return stats


def print_summary(stats: SeedStats) -> None:
    print("Initial content seed completed.")
    print(f"Sources:   {stats.sources_created} created, {stats.sources_verified} verified")
    print(f"Documents: {stats.documents_created} created, {stats.documents_verified} verified")
    print(f"Chunks:    {stats.chunks_created} created, {stats.chunks_verified} verified")
    print(f"Authors:   {stats.authors_created} created, {stats.authors_verified} verified")
    print(f"Tags:      {stats.tags_created} created, {stats.tags_verified} verified")


def main() -> int:
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        print("ERROR: DATABASE_URL is not set. Set it and run the script again.", file=sys.stderr)
        return 2

    connect_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    try:
        with psycopg.connect(connect_url) as conn:
            stats = seed_initial_documents(conn)
            conn.commit()
    except Exception as exc:
        print(
            f"ERROR: initial content seed failed ({type(exc).__name__}). "
            "DATABASE_URL was not printed and no destructive operation was attempted.",
            file=sys.stderr,
        )
        return 1

    print_summary(stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
