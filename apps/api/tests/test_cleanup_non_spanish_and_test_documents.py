import importlib.util
from pathlib import Path
import sys
from unittest import TestCase


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "cleanup_non_spanish_and_test_documents.py"
SPEC = importlib.util.spec_from_file_location("cleanup_non_spanish_and_test_documents", SCRIPT_PATH)
assert SPEC and SPEC.loader
cleanup = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cleanup
SPEC.loader.exec_module(cleanup)


class FakeResult:
    def __init__(self, row=None, rowcount=0):
        self.row = row
        self.rowcount = rowcount

    def fetchone(self):
        return self.row


class ApplyConnection:
    def __init__(self, *, soft_delete: bool):
        self.soft_delete = soft_delete
        self.executed = []

    def execute(self, sql, params=None):
        normalized = " ".join(str(sql).split()).lower()
        self.executed.append((normalized, params))
        if "information_schema.columns" in normalized:
            columns = {"id", "raw_metadata"}
            if self.soft_delete:
                columns.update({"deleted_at", "status", "is_indexed", "updated_at"})
            return type("Rows", (), {"fetchall": lambda self: [(column,) for column in columns]})()
        if "information_schema.tables" in normalized:
            return FakeResult((True,))
        if normalized.startswith("update documents"):
            return FakeResult(rowcount=1)
        if normalized.startswith("delete from"):
            return FakeResult(rowcount=1)
        raise AssertionError(normalized)


class CleanupInvalidDocumentsTest(TestCase):
    def detected_document(self):
        return cleanup.DetectedDocument(
            document_id="10000000-0000-4000-8000-000000000001",
            title="Documento de prueba",
            language="en",
            source_url="https://example.com/prueba-n8n?lang=eng",
            canonical_url="https://example.com/prueba-n8n?lang=eng",
            source_name="Prueba n8n",
            chunks=3,
            reasons=("language=en",),
        )

    def test_detects_all_required_invalid_content_signals(self):
        reasons = cleanup.detect_reasons(
            {
                "title": "Documento de prueba doctrinal",
                "language": "en",
                "source_url": "https://example.com/prueba-n8n?lang=eng",
                "canonical_url": "https://example.com/doc?lang=eng",
                "source_name": "Prueba n8n",
                "document_text": "[REEMPLAZAR ANTES DE ENVIAR] contenido de prueba placeholder",
                "summary": "No es una cita oficial y no reemplaza ninguna fuente doctrinal",
                "metadata": {
                    "test_payload": True,
                    "source_url": "https://example.com/a?lang=eng",
                    "canonical_url": "https://example.com/b?lang=eng",
                },
            }
        )

        self.assertIn("language=en", reasons)
        self.assertIn("título de documento de prueba", reasons)
        self.assertIn("URL de prueba n8n", reasons)
        self.assertIn("metadata.test_payload=true", reasons)
        self.assertIn("fuente Prueba n8n", reasons)
        self.assertTrue(any(reason.startswith("texto placeholder:") for reason in reasons))

    def test_soft_delete_is_reversible_and_keeps_chunks(self):
        conn = ApplyConnection(soft_delete=True)

        mode, affected = cleanup.apply_cleanup(conn, [self.detected_document()])

        statements = "\n".join(statement for statement, _ in conn.executed)
        self.assertEqual(mode, "soft_delete")
        self.assertEqual(affected, 1)
        self.assertIn("update documents", statements)
        self.assertIn("status = 'hidden'", statements)
        self.assertNotIn("delete from document_chunks", statements)
        self.assertNotIn("delete from documents", statements)

    def test_hard_delete_fallback_removes_relations_and_chunks_first(self):
        conn = ApplyConnection(soft_delete=False)

        mode, affected = cleanup.apply_cleanup(conn, [self.detected_document()])

        statements = [statement for statement, _ in conn.executed if statement.startswith("delete from")]
        self.assertEqual(mode, "hard_delete")
        self.assertEqual(affected, 1)
        self.assertEqual(
            statements,
            [
                "delete from document_tags where document_id::text = any(%s)",
                "delete from document_chunks where document_id::text = any(%s)",
                "delete from documents where id::text = any(%s)",
            ],
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
