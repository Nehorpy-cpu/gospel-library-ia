# Phase 5 - Study Frontend

## Goal

Build the StudyWorkspace frontend experience.

## Scope

- Workspace page.
- Notes panel.
- Highlights.
- Saved citations.
- Post-it notes.
- Source filters.
- Responsive UI.

## Required work

1. Add StudyWorkspace routes in Next.js App Router.
2. Use TanStack Query for server data.
3. Use Zustand for local workspace state.
4. Integrate existing document reader and citation cards.
5. Allow creating notes and saved quotes from selected content.
6. Add source filters without breaking library browsing.
7. Support dark mode and responsive layouts.

## Acceptance criteria

- User can open a workspace.
- User can create, view, update, and delete notes.
- User can save citations from documents.
- UI uses real API data.

## Verification

```bash
pnpm build
pnpm test
```

## Non-goals

- Do not add exports.
- Do not add talk builder.

