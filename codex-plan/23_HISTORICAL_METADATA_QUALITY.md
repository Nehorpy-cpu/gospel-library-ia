# Phase 23 - Historical metadata quality

## Objective

Improve document title, author, and publication metadata using deterministic source evidence while preserving content and a reversible audit trail.

## Scope

- Parse metadata from original HTML before Readability cleanup.
- Prefer structured and page metadata over body-text title fallbacks.
- Repair malformed historical titles from canonical URL slugs.
- Recover BYU speaker names from `/talks/{speaker}/...` URLs.
- Recover missing General Conference month from `/general-conference/YYYY/MM/...`.
- Record every persisted field repair in `document_metadata_repair_audit`.
- Mark repaired documents for incremental reindexing without calling OpenAI.

## Non-goals

- Do not deduplicate documents.
- Do not invent authors for institutional, scripture, manual, or historical pages.
- Do not alter document text or source URLs.
- Do not invoke OpenAI or generate embeddings.

## Validation

- Parser and metadata-quality tests pass.
- Dry-run and applied counts are recorded.
- Audit row count matches applied repairs.
- No document has an empty or placeholder title.
- Existing source type and source URL coverage remains complete.
- Alembic, Prisma, API tests, and Docker health checks pass.
