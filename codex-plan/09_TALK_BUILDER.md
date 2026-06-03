# Phase 9 - Talk Builder

## Goal

Create a doctrinal talk builder based on real library sources.

## Scope

- Topic input.
- Audience and duration.
- Outline generation.
- Scripture and quote suggestions.
- Source-grounded sections.

## Required work

1. Add talk builder API flow.
2. Retrieve sources from documents, saved quotes, and scripture references.
3. Generate outline with citation grounding.
4. Allow user edits before final draft.
5. Support no-embedding fallback with text search.

## Acceptance criteria

- Generated outline cites real sources.
- User can save a draft.
- No OpenAI failure produces a 500; return clear unavailable state.

## Verification

```bash
pnpm test
```

## Non-goals

- Do not export generated talks yet.

