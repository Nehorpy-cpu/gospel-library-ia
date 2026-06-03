# Phase 10 - Exports

## Goal

Add export workflows for study material and talk drafts.

## Scope

- PDF export.
- Markdown export.
- Study notes export.
- Saved quotes export.
- Talk draft export.

## Required work

1. Add export API endpoints.
2. Generate PDF from selected notes, quotes, or talk drafts.
3. Preserve citations and source URLs.
4. Add frontend export actions.
5. Add safeguards for private user data.

## Acceptance criteria

- Exports include source attribution.
- User can export only owned data.
- Export does not expose secrets or private data from other users.

## Verification

```bash
pnpm build
pnpm test
```

## Non-goals

- Do not add deployment changes in this phase.

