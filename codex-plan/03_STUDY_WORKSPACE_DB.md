# Phase 3 - Study Workspace DB

## Goal

Prepare the database foundation for personal study workspaces.

## Scope

- Study spaces.
- Personal notes.
- Saved citations.
- Post-it notes.
- Source filters.
- User ownership and synchronization fields.

## Required work

1. Add Prisma/SQL models for study workspaces.
2. Add notes linked to users, documents, optional selected text, and optional scripture refs.
3. Add highlights/subrayados linked to document ranges.
4. Add saved quotes/citations with source attribution.
5. Add post-it notes with position, color, document, and workspace.
6. Add per-workspace source filters.
7. Include timestamps and soft-delete fields where appropriate.
8. Add indexes for user, workspace, document, and updated timestamp.

## Acceptance criteria

- Migrations apply without data loss.
- Existing document, chat, favorite, history, and collection tables remain compatible.
- New tables support multi-user isolation.

## Verification

```bash
pnpm prisma:generate
pnpm prisma:migrate
pnpm test
```

## Non-goals

- Do not build frontend UI in this phase.
- Do not add RAG behavior in this phase.

