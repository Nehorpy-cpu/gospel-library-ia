# Phase 7 - Saved Quotes and Post-its

## Goal

Add user-facing saved quote and post-it workflows.

## Scope

- Save selected text as quote.
- Attach quote to document and source.
- Create post-it note on documents or study workspace.
- Color and position metadata.

## Required work

1. Implement quote save action from reader and chat citations.
2. Persist exact quote text, document id, source url, and optional location.
3. Implement post-it creation, update, delete, and positioning.
4. Add quote and post-it lists inside StudyWorkspace.
5. Add optimistic UI where safe.

## Acceptance criteria

- Saved quotes persist across reloads.
- Post-its persist with position/color.
- Quotes include source attribution.

## Verification

```bash
pnpm build
pnpm test
```

## Non-goals

- Do not implement PDF export yet.

