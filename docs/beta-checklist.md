# Beta checklist

- [ ] Deploy listo en entorno beta.
- [ ] Auth listo con Clerk o modo local controlado.
- [ ] Admin protegido por rol.
- [ ] Allowlist beta configurada si `BETA_ALLOWLIST_ENABLED=true`.
- [ ] Privacidad probada en workspaces, notas, citas, post-it, historial y exportaciones.
- [ ] Backup activo para PostgreSQL y storage.
- [ ] Costos IA controlados con `AI_COST_MODE`, limites diarios y dashboard admin.
- [ ] Feedback activo y visible en Admin.
- [ ] Terminos publicados en `/terms`.
- [ ] Privacidad publicada en `/privacy`.
- [ ] Sentry o logging equivalente configurado sin datos sensibles.
- [ ] Qdrant `doctrinal_chunks_v1` verificado.
- [ ] Fallback textual verificado cuando no hay vectores o cuota OpenAI.
- [ ] Primeros usuarios beta aprobados manualmente.
- [ ] Demo smoke test completado.

## Variables beta

```txt
BETA_ALLOWLIST_ENABLED=true
BETA_MAX_WORKSPACES_PER_USER=12
MAX_USER_CHAT_MESSAGES_PER_DAY=50
MAX_USER_TALK_BUILDER_PER_DAY=20
MAX_USER_EXPORTS_PER_DAY=10
NEXT_PUBLIC_SENTRY_DSN=
SENTRY_DSN=
```
