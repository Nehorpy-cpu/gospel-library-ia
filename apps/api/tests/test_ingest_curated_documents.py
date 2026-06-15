import importlib.util
import os
import sys
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import httpx


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "ingest_curated_documents.py"
SPEC = importlib.util.spec_from_file_location("ingest_curated_documents", SCRIPT_PATH)
assert SPEC and SPEC.loader
ingest = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ingest
SPEC.loader.exec_module(ingest)


class FakeResult:
    def __init__(self, row=None):
        self.row = row

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self):
        self.sources = {}
        self.documents = {}
        self.authors = set()
        self.tags = set()
        self.chunks = set()
        self.next_id = 1
        self.executed = []

    def new_id(self):
        value = f"00000000-0000-4000-8000-{self.next_id:012d}"
        self.next_id += 1
        return value

    def execute(self, statement, params=None):
        normalized = " ".join(str(statement).split()).lower()
        self.executed.append((normalized, params))
        if normalized.startswith("select pg_advisory_xact_lock"):
            return FakeResult((None,))
        if normalized.startswith("select id from sources"):
            return FakeResult((self.sources[params[0]],) if params[0] in self.sources else None)
        if normalized.startswith("insert into sources"):
            source_id = self.new_id()
            self.sources[params["key"]] = source_id
            return FakeResult((source_id,))
        if normalized.startswith("insert into authors"):
            slug = params[0]
            if slug in self.authors:
                return FakeResult()
            self.authors.add(slug)
            return FakeResult((self.new_id(),))
        if normalized.startswith("insert into tags"):
            slug = params[0]
            if slug in self.tags:
                return FakeResult()
            self.tags.add(slug)
            return FakeResult((self.new_id(),))
        if normalized.startswith("select id from documents"):
            urls = params[0]
            for url in urls:
                if url in self.documents:
                    return FakeResult((self.documents[url],))
            return FakeResult()
        if normalized.startswith("insert into documents"):
            url = params["canonical_url"]
            if url in self.documents:
                return FakeResult()
            document_id = self.new_id()
            self.documents[url] = document_id
            return FakeResult((document_id,))
        if normalized.startswith("insert into document_chunks"):
            key = (params["document_id"], params["chunk_index"], params["chunker_version"])
            if key in self.chunks:
                return FakeResult()
            self.chunks.add(key)
            return FakeResult((self.new_id(),))
        raise AssertionError(f"Unexpected SQL: {normalized}")


class FakeClient:
    def __init__(self, responses):
        self.responses = responses

    def get(self, url):
        return self.responses[url]


def html_response(target, title: str, author: str = "Test Author") -> httpx.Response:
    paragraphs = "".join(f"<p>{title} paragraph {index} " + ("faith and discipleship " * 20) + "</p>" for index in range(8))
    body_class = "single-speech__content" if target.document_type == "byu_speech" else "body"
    html = f"""
    <html lang="en">
      <head>
        <title>{title}</title>
        <link rel="canonical" href="{target.url}">
        <meta name="author" content="{author}">
      </head>
      <body><main><article id="main"><div class="{body_class}"><h1>{title}</h1>{paragraphs}</div></article></main></body>
    </html>
    """
    return httpx.Response(
        200,
        headers={"content-type": "text/html"},
        content=html.encode(),
        request=httpx.Request("GET", target.url),
    )


class CuratedIngestionTests(TestCase):
    def test_curated_targets_are_small_explicit_and_allowed(self):
        self.assertEqual(len(ingest.TARGETS), 8)
        self.assertEqual(
            ingest.USER_AGENT,
            "GospelLibraryIA/0.1 curated-ingestion contact=https://www.estudiopy.com",
        )
        self.assertTrue(all(target.url.startswith("https://") for target in ingest.TARGETS))
        self.assertTrue(all(ingest.normalize_url(target.url) for target in ingest.TARGETS))

    def test_ingestion_is_idempotent(self):
        conn = FakeConnection()
        responses = {
            ingest.allowed_request_url(target.url): html_response(target, f"Title {index}")
            for index, target in enumerate(ingest.TARGETS)
        }
        client = FakeClient(responses)

        first = ingest.ingest_curated_documents(conn, client, delay_seconds=0)
        second = ingest.ingest_curated_documents(conn, client, delay_seconds=0)

        self.assertEqual(first.documents_created, len(ingest.TARGETS))
        self.assertEqual(second.documents_verified, len(ingest.TARGETS))
        self.assertEqual(len(conn.documents), len(ingest.TARGETS))
        self.assertEqual(first.skipped, [])
        statements = "\n".join(statement for statement, _ in conn.executed)
        self.assertNotIn("delete from", statements)
        self.assertNotIn("truncate", statements)
        document_inserts = [
            params
            for statement, params in conn.executed
            if statement.startswith("insert into documents")
        ]
        metadata = ingest.json.loads(document_inserts[0]["metadata"])
        self.assertEqual(metadata["ingestion_mode"], "curated_v1")
        self.assertFalse(metadata["is_seed"])
        self.assertEqual(metadata["extractor_version"], "curated-html-v1")
        self.assertEqual(metadata["content_type"], "text/html")
        self.assertTrue(metadata["source_url"].startswith("https://"))

    def test_chunks_stay_near_requested_size_and_preserve_text(self):
        text = " ".join(f"paragraph-{index} " + ("faith " * 45) for index in range(20))

        chunks = ingest.split_chunks(text)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk[2]) <= ingest.CHUNK_MAX_CHARACTERS for chunk in chunks))
        self.assertTrue(
            all(len(chunk[2]) >= ingest.CHUNK_MIN_CHARACTERS for chunk in chunks[:-1])
        )
        self.assertEqual(
            "".join(chunk[2] for chunk in chunks).replace(" ", ""),
            text.replace(" ", ""),
        )

    def test_dirty_or_short_page_is_skipped(self):
        target = ingest.TARGETS[0]
        response = httpx.Response(
            200,
            headers={"content-type": "text/html"},
            content=b"<html><body><nav>Menu</nav><main><p>Too short</p></main></body></html>",
            request=httpx.Request("GET", target.url),
        )

        with self.assertRaises(ingest.ExtractionSkipped):
            ingest.extract_document(target, response)

    def test_redirect_outside_allowlist_is_rejected(self):
        target = ingest.TARGETS[0]
        response = httpx.Response(
            302,
            headers={"location": "https://example.com/untrusted"},
            request=httpx.Request("GET", target.url),
        )

        with self.assertRaises(ingest.ExtractionSkipped):
            ingest.fetch_allowed(FakeClient({target.url: response}), target.url)

    def test_main_requires_database_url(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(ingest.psycopg, "connect") as connect:
            self.assertEqual(ingest.main(), 2)
            connect.assert_not_called()
