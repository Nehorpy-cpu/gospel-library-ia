# Phase 21 - Legacy source normalization

## Objective

Stop duplicate or unbounded legacy source catalogs from creating new crawl jobs while preserving all existing documents and source relationships.

## Scope

- Disable legacy source keys:
  - `byu_speeches_en`
  - `discursosud`
  - `josephsmithpapers`
  - `churchofjesuschrist`
- Keep canonical replacements enabled.
- Normalize safe legacy source types.
- Preserve previous values in a reversible audit table.
- Keep all existing documents queryable.
- Preserve canonical source context for unclassified child URLs discovered by a canonical Church source.

## Non-goals

- Do not delete or move documents.
- Do not merge source foreign keys.
- Do not reclassify ambiguous historical Church pages.
- Do not improve titles, authors, or deduplicate content in this phase.
- Do not invoke OpenAI or generate embeddings.

## Validation

- Python compile and scraper tests pass.
- Prisma schema validates.
- Alembic upgrades to head.
- Legacy sources are disabled and annotated.
- Canonical replacements remain enabled.
- The migration does not mutate documents, document count does not decrease, and no orphaned document source references are introduced.
- Docker services used for validation are healthy.
