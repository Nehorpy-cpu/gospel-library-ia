const DOCUMENT_ID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function normalizeDocumentId(value: string | null | undefined): string | null {
  const documentId = value?.trim();
  return documentId && DOCUMENT_ID_PATTERN.test(documentId) ? documentId : null;
}

export function buildDocumentDetailPath(documentId: string, includeChunks = true): string {
  const normalizedDocumentId = normalizeDocumentId(documentId);
  if (!normalizedDocumentId) {
    throw new Error("No se pudo identificar el documento solicitado.");
  }
  const searchParams = new URLSearchParams();
  if (includeChunks) searchParams.set("include_chunks", "true");
  const query = searchParams.toString();
  return `/documents/${encodeURIComponent(normalizedDocumentId)}${query ? `?${query}` : ""}`;
}
