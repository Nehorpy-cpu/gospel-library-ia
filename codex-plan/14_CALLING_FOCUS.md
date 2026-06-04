# Phase 14 - Calling Focus

## Goal

Add dynamic calling-based focus for deep doctrinal analysis without changing doctrine or assuming every user is an Area Seventy.

## Scope

- Editable Church calling catalog.
- User calling preferences.
- Chat/RAG payload support for calling focus.
- Dynamic prompt section: `Aplicacion segun mi llamamiento: [calling]`.
- Frontend preferences UI.
- Tests and documentation.

## Required work

1. Create an extensible calling catalog grouped by Church level and organization.
2. Include an `Otro llamamiento` option and allow custom calling text.
3. Persist user preference fields:
   - `callingCategory`
   - `callingName`
   - `customCallingName`
   - `callingFocusEnabled`
4. Add a settings/preference UI with pastoral explanatory copy.
5. Send calling focus with chat requests when enabled.
6. Update RAG prompts so doctrine is never changed by calling. Only application, emphasis, reflection questions, and practical examples change.
7. Replace any fixed Area Seventy application assumption with a dynamic calling focus section.
8. If no calling is selected, use a general discipleship focus.
9. Add tests for catalog, custom calling, persisted preference payloads, prompt injection, and fallback behavior.
10. Update `PROGRESS.md` and project documentation.

## Acceptance criteria

- A user can choose a calling from the catalog.
- A user can write a custom calling.
- Chat/RAG requests include the selected calling focus.
- Deep doctrinal analysis prompts include the dynamic calling section.
- The app no longer assumes all users are Area Seventies.
- Marco Sosa can still choose Area Seventy in preferences.
- No previous phase is broken.

## Verification

```bash
python -m compileall apps/api/app rag/app
python -m unittest discover apps/api/tests
python -m unittest discover rag/tests
corepack pnpm --dir apps/web typecheck
corepack pnpm test
git diff --check
```
