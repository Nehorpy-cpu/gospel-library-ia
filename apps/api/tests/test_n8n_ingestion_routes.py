from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app
from app.routes import ingestion


SPANISH_CONTENT = (
    "Jesucristo es el centro del evangelio restaurado y nos invita a ejercer fe en Él. "
    "Por medio de Su gracia podemos arrepentirnos, guardar los convenios y servir con amor. "
    "El Padre Celestial desea que cada persona aprenda de Cristo, siga Su ejemplo y reciba "
    "las bendiciones del Espíritu Santo. La oración, el estudio de las Escrituras y la "
    "participación digna en las ordenanzas fortalecen la fe y ayudan a perseverar. "
) * 3


class FakeResult:
    def __init__(self, row=None):
        self.row = row

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self):
        self.source_id = None
        self.documents = {}
        self.chunks = set()
        self.authors = set()
        self.tags = set()
        self.commits = 0
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
        if normalized.startswith("select id::text, source_id::text, canonical_url from documents"):
            urls = params[0]
            content_hash = params[3]
            for document in self.documents.values():
                if (
                    document["canonical_url"] in urls
                    or document["source_url"] in urls
                    or document["content_hash"] == content_hash
                ):
                    return FakeResult(
                        (document["id"], document["source_id"], document["canonical_url"])
                    )
            return FakeResult()
        if normalized.startswith("select count(*)::int from document_chunks"):
            count = sum(document_id == params[0] for document_id, _ in self.chunks)
            return FakeResult((count,))
        if normalized.startswith("select id from sources where key"):
            return FakeResult((self.source_id,) if self.source_id else None)
        if normalized.startswith("insert into sources"):
            self.source_id = self.new_id()
            return FakeResult((self.source_id,))
        if normalized.startswith("insert into authors"):
            self.authors.add(params[0])
            return FakeResult()
        if normalized.startswith("insert into tags"):
            self.tags.add(params[0])
            return FakeResult()
        if normalized.startswith("insert into documents"):
            canonical_url = params["canonical_url"]
            if canonical_url in self.documents:
                return FakeResult()
            document_id = self.new_id()
            metadata = json.loads(params["metadata"])
            self.documents[canonical_url] = {
                "id": document_id,
                "source_id": str(params["source_id"]),
                "canonical_url": canonical_url,
                "source_url": metadata["source_url"],
                "content_hash": params["content_hash"],
            }
            return FakeResult((document_id,))
        if normalized.startswith("insert into document_chunks"):
            self.chunks.add((params["document_id"], params["chunk_index"]))
            return FakeResult()
        raise AssertionError(f"Unexpected SQL: {normalized}")

    def commit(self):
        self.commits += 1


class N8nIngestionRoutesTest(unittest.TestCase):
    def setUp(self):
        self.connection = FakeConnection()
        self.original_get_conn = ingestion.get_conn
        self.original_get_settings = ingestion.get_settings

        @contextmanager
        def fake_get_conn():
            yield self.connection

        ingestion.get_conn = fake_get_conn
        ingestion.get_settings = lambda: SimpleNamespace(ingestion_api_key="test-ingestion-key")
        self.client = TestClient(app)

    def tearDown(self):
        ingestion.get_conn = self.original_get_conn
        ingestion.get_settings = self.original_get_settings

    def payload(self):
        return {
            "title": "La fe en Jesucristo",
            "author": "Autor de prueba",
            "source_name": "Sitio oficial de la Iglesia",
            "source_url": (
                "https://www.churchofjesuschrist.org/study/general-conference/"
                "2020/10/45andersen?lang=spa&utm_source=n8n"
            ),
            "canonical_url": (
                "https://www.churchofjesuschrist.org/study/general-conference/"
                "2020/10/45andersen?lang=spa"
            ),
            "language": "es",
            "content_type": "discurso",
            "year": 2024,
            "content": SPANISH_CONTENT,
            "summary": "Resumen breve del documento.",
            "tags": ["Jesucristo", "Fe"],
            "metadata": {
                "workflow": "curated-es-v1",
                "storage_path": "ignored",
                "nested": {"token": "must-not-be-stored", "reviewed": True},
            },
        }

    def test_rejects_request_without_api_key(self):
        response = self.client.post("/api/ingestion/documents", json=self.payload())

        self.assertEqual(response.status_code, 401)
        self.assertEqual(len(self.connection.documents), 0)

    def test_rejects_incorrect_api_key(self):
        response = self.client.post(
            "/api/ingestion/documents",
            headers={"X-Ingestion-Key": "wrong-key"},
            json=self.payload(),
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(len(self.connection.documents), 0)

    def test_rejects_non_spanish_content(self):
        payload = self.payload()
        payload["language"] = "en"

        response = self.client.post(
            "/api/ingestion/documents",
            headers={"X-Ingestion-Key": "test-ingestion-key"},
            json=payload,
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(len(self.connection.documents), 0)

    def test_rejects_predominantly_english_content_even_when_declared_spanish(self):
        payload = self.payload()
        payload["content"] = (
            "Jesus Christ is the center of the gospel and this document is written in English. "
            "The Lord invites you to come unto me, and the disciples are called to faith and service. "
            "This is a complete English paragraph for testing language detection and quality controls. "
        ) * 4

        response = self.client.post(
            "/api/ingestion/documents",
            headers={"X-Ingestion-Key": "test-ingestion-key"},
            json=payload,
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(len(self.connection.documents), 0)

    def test_rejects_non_spanish_language_urls_in_payload_and_metadata(self):
        for field, value in (
            ("source_url", "https://discursosud.com/discurso/ejemplo?lang=eng"),
            ("canonical_url", "https://discursosud.com/discurso/ejemplo?lang=fra"),
        ):
            payload = self.payload()
            payload["source_name"] = "Discursos SUD"
            payload["source_url"] = "https://discursosud.com/discurso/ejemplo"
            payload["canonical_url"] = payload["source_url"]
            payload[field] = value
            response = self.client.post(
                "/api/ingestion/documents",
                headers={"X-Ingestion-Key": "test-ingestion-key"},
                json=payload,
            )
            self.assertEqual(response.status_code, 422, field)

        payload = self.payload()
        payload["metadata"]["source_url"] = "https://discursosud.com/discurso/ejemplo?lang=eng"
        response = self.client.post(
            "/api/ingestion/documents",
            headers={"X-Ingestion-Key": "test-ingestion-key"},
            json=payload,
        )
        self.assertEqual(response.status_code, 422)

        payload = self.payload()
        payload["metadata"]["canonical_url"] = "https://discursosud.com/discurso/ejemplo?lang=por"
        response = self.client.post(
            "/api/ingestion/documents",
            headers={"X-Ingestion-Key": "test-ingestion-key"},
            json=payload,
        )
        self.assertEqual(response.status_code, 422)

    def test_rejects_placeholder_and_test_documents(self):
        variants = [
            ("title", "Documento de prueba para ingesta"),
            ("content", "[REEMPLAZAR ANTES DE ENVIAR] " + SPANISH_CONTENT),
            ("summary", "No es una cita oficial"),
            ("source_name", "Prueba n8n"),
        ]
        for field, value in variants:
            payload = self.payload()
            payload[field] = value
            response = self.client.post(
                "/api/ingestion/documents",
                headers={"X-Ingestion-Key": "test-ingestion-key"},
                json=payload,
            )
            self.assertEqual(response.status_code, 422, field)

        payload = self.payload()
        payload["metadata"]["test_payload"] = True
        response = self.client.post(
            "/api/ingestion/documents",
            headers={"X-Ingestion-Key": "test-ingestion-key"},
            json=payload,
        )
        self.assertEqual(response.status_code, 422)

    def test_rejects_payload_without_source_url(self):
        payload = self.payload()
        payload.pop("source_url")

        response = self.client.post(
            "/api/ingestion/documents",
            headers={"X-Ingestion-Key": "test-ingestion-key"},
            json=payload,
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(len(self.connection.documents), 0)

    def test_rejects_raw_html_content(self):
        payload = self.payload()
        payload["content"] = f"<html><body><nav>Menú</nav><p>{SPANISH_CONTENT}</p></body></html>"

        response = self.client.post(
            "/api/ingestion/documents",
            headers={"X-Ingestion-Key": "test-ingestion-key"},
            json=payload,
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(len(self.connection.documents), 0)

    def test_requires_exact_spanish_language_code(self):
        for language in (None, "spa"):
            payload = self.payload()
            if language is None:
                payload.pop("language")
            else:
                payload["language"] = language

            response = self.client.post(
                "/api/ingestion/documents",
                headers={"X-Ingestion-Key": "test-ingestion-key"},
                json=payload,
            )

            self.assertEqual(response.status_code, 422)
            self.assertIn("language must be es", response.text)

    def test_creates_valid_document_and_chunks(self):
        response = self.client.post(
            "/api/ingestion/documents",
            headers={"X-Ingestion-Key": "test-ingestion-key"},
            json=self.payload(),
        )

        payload = response.json()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(payload["status"], "created")
        self.assertGreater(payload["chunks"], 0)
        self.assertEqual(len(self.connection.documents), 1)
        self.assertEqual(self.connection.authors, {"autor-de-prueba"})
        self.assertEqual(self.connection.tags, {"jesucristo", "fe"})
        self.assertEqual(self.connection.commits, 1)
        document_insert = next(
            params
            for statement, params in self.connection.executed
            if statement.startswith("insert into documents")
        )
        metadata = json.loads(document_insert["metadata"])
        self.assertNotIn("storage_path", metadata)
        self.assertNotIn("token", metadata["nested"])
        self.assertTrue(metadata["nested"]["reviewed"])
        self.assertEqual(metadata["ingestion_mode"], "n8n_curated_v1")
        self.assertFalse(metadata["storage_used"])
        self.assertEqual(metadata["source_name"], "La Iglesia de Jesucristo de los Santos de los Últimos Días")
        self.assertEqual(metadata["source_type"], "church_official_es")
        self.assertEqual(metadata["submitted_source_name"], "Sitio oficial de la Iglesia")

    def test_normalizes_mojibake_and_translates_tags_before_insert(self):
        payload = self.payload()
        payload["title"] = "Libro de MormÃƒÂ³n"
        payload["author"] = "Elder D.Ã‚ Todd Christofferson"
        payload["tags"] = ["Book of Mormon", "Holy Ghost"]

        response = self.client.post(
            "/api/ingestion/documents",
            headers={"X-Ingestion-Key": "test-ingestion-key"},
            json=payload,
        )

        self.assertEqual(response.status_code, 201)
        document_insert = next(
            params
            for statement, params in self.connection.executed
            if statement.startswith("insert into documents")
        )
        self.assertEqual(document_insert["title"], "Libro de Mormón")
        self.assertEqual(document_insert["author"], "Elder D. Todd Christofferson")
        self.assertEqual(json.loads(document_insert["tags"]), ["Libro de Mormón", "Espíritu Santo"])
        self.assertEqual(self.connection.tags, {"libro-de-mormon", "espiritu-santo"})

    def test_duplicate_document_is_verified_without_new_rows(self):
        headers = {"X-Ingestion-Key": "test-ingestion-key"}

        first = self.client.post("/api/ingestion/documents", headers=headers, json=self.payload())
        second = self.client.post("/api/ingestion/documents", headers=headers, json=self.payload())

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["status"], "verified_existing")
        self.assertEqual(second.json()["document_id"], first.json()["document_id"])
        self.assertEqual(len(self.connection.documents), 1)

    def test_rejects_source_outside_allowlist(self):
        payload = self.payload()
        payload["source_url"] = "https://example.com/documento"
        payload["canonical_url"] = "https://example.com/documento"

        response = self.client.post(
            "/api/ingestion/documents",
            headers={"X-Ingestion-Key": "test-ingestion-key"},
            json=payload,
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(len(self.connection.documents), 0)

    def test_rejects_insecure_authorized_source_url(self):
        payload = self.payload()
        payload["source_url"] = "http://discursosud.com/discurso/ejemplo/"
        payload["canonical_url"] = payload["source_url"]

        response = self.client.post(
            "/api/ingestion/documents",
            headers={"X-Ingestion-Key": "test-ingestion-key"},
            json=payload,
        )

        self.assertEqual(response.status_code, 422)

    def test_accepts_discursos_sud_document_url(self):
        payload = self.payload()
        payload["source_name"] = "Discursos SUD"
        payload["source_url"] = "https://discursosud.com/discurso/ejemplo-doctrinal/"
        payload["canonical_url"] = payload["source_url"]

        response = self.client.post(
            "/api/ingestion/documents",
            headers={"X-Ingestion-Key": "test-ingestion-key"},
            json=payload,
        )

        self.assertEqual(response.status_code, 201)
        document_insert = next(
            params
            for statement, params in self.connection.executed
            if statement.startswith("insert into documents")
        )
        metadata = json.loads(document_insert["metadata"])
        self.assertEqual(metadata["source_type"], "discursos_sud_es")

    def test_accepts_byu_spanish_individual_talk(self):
        payload = self.payload()
        payload["source_name"] = "BYU Speeches Español"
        payload["source_url"] = "https://speeches.byu.edu/spa/talks/autor/discurso-ejemplo/"
        payload["canonical_url"] = payload["source_url"]

        response = self.client.post(
            "/api/ingestion/documents",
            headers={"X-Ingestion-Key": "test-ingestion-key"},
            json=payload,
        )

        self.assertEqual(response.status_code, 201)

    def test_rejects_byu_navigation_listing(self):
        payload = self.payload()
        payload["source_url"] = "https://speeches.byu.edu/spa/talks/"
        payload["canonical_url"] = payload["source_url"]

        response = self.client.post(
            "/api/ingestion/documents",
            headers={"X-Ingestion-Key": "test-ingestion-key"},
            json=payload,
        )

        self.assertEqual(response.status_code, 422)

    def test_rejects_discursos_sud_navigation_archive(self):
        payload = self.payload()
        payload["source_url"] = "https://discursosud.com/category/discursos/"
        payload["canonical_url"] = payload["source_url"]

        response = self.client.post(
            "/api/ingestion/documents",
            headers={"X-Ingestion-Key": "test-ingestion-key"},
            json=payload,
        )

        self.assertEqual(response.status_code, 422)

    def test_pdf_keeps_url_and_text_without_storage(self):
        payload = self.payload()
        payload["source_name"] = "Discursos SUD"
        payload["source_url"] = "https://discursosud.com/wp-content/uploads/discurso.pdf"
        payload["canonical_url"] = payload["source_url"]
        payload["content_type"] = "application/pdf"

        response = self.client.post(
            "/api/ingestion/documents",
            headers={"X-Ingestion-Key": "test-ingestion-key"},
            json=payload,
        )

        self.assertEqual(response.status_code, 201)
        document_insert = next(
            params
            for statement, params in self.connection.executed
            if statement.startswith("insert into documents")
        )
        metadata = json.loads(document_insert["metadata"])
        self.assertEqual(metadata["source_format"], "pdf")
        self.assertEqual(metadata["pdf_url"], payload["source_url"])
        self.assertFalse(metadata["storage_used"])

    def test_health_documents_contract(self):
        response = self.client.get("/api/ingestion/documents/health")

        self.assertEqual(
            response.json(),
            {
                "status": "ok",
                "required_header": "X-Ingestion-Key",
                "accepted_language": "es",
                "storage_used": False,
            },
        )


if __name__ == "__main__":
    unittest.main()
