# Phase 6 - Source Filters

## Goal

Make source filtering consistent across library, search, admin, and study workflows.

## Scope

- Source type filters.
- Language filters.
- Author filters.
- Topic filters.
- Date filters.

## Required work

1. Normalize frontend filter options from real API data.
2. Support canonical source types:
   - `byu_speeches_es`
   - `byu_speeches_en`
   - `discursos_sud`
   - `general_conference`
   - `church_manuals`
   - `joseph_smith_papers`
   - `byu_rsc`
3. Preserve compatibility with existing `source` records.
4. Apply filters to PostgreSQL fallback search and semantic search where available.
5. Ensure admin statistics and public library use the same filter vocabulary.

## Acceptance criteria

- Filters return real filtered documents.
- Empty filters do not hide valid results.
- Admin and library source counts align.

## Verification

```bash
pnpm test
```

## Non-goals

- Do not implement new sources in this phase.

