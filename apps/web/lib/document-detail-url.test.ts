import assert from "node:assert/strict";
import test from "node:test";

import { buildDocumentDetailPath, normalizeDocumentId } from "./document-detail-url.ts";

const DOCUMENT_ID = "10000000-0000-4000-8000-000000000001";

test("construye la ruta exacta del detalle con chunks", () => {
  assert.equal(
    buildDocumentDetailPath(DOCUMENT_ID, true),
    `/documents/${DOCUMENT_ID}?include_chunks=true`
  );
});

test("rechaza IDs ausentes o confundidos con parámetros", () => {
  assert.equal(normalizeDocumentId(undefined), null);
  assert.equal(normalizeDocumentId(""), null);
  assert.equal(normalizeDocumentId("=true"), null);
  assert.throws(
    () => buildDocumentDetailPath("=true", true),
    /No se pudo identificar el documento solicitado/
  );
});
