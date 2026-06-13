# Gospel Library IA Frontend Architecture

## Principios

- App Router con Server Components en paginas y Client Components solo para interaccion.
- Cliente API unico con origen publico validado mediante `NEXT_PUBLIC_API_URL`.
- Estado servidor en TanStack Query.
- Estado local persistente en Zustand.
- Componentes UI pequenos, accesibles y consistentes con shadcn/ui.
- Listas grandes con TanStack Virtual.
- Markdown con `react-markdown` y tipografia Tailwind.
- SEO por ruta usando `metadata`.

## Pipeline UI

```txt
Usuario
  -> AppShell
  -> Global Search / Route
  -> TanStack Query or streaming fetch
  -> Next API proxy
  -> RAG FastAPI
  -> Citation cards / Markdown / Reader
```

## Rutas

```txt
/                  Biblioteca inicial
/search            Busqueda IA hibrida
/chat              Chat doctrinal streaming
/library           Virtualized library
/documents/[id]    Lector PDF/documento
/authors/[slug]    Author page con resumen IA
/collections       Colecciones
/favorites         Favoritos persistidos
/history           Historial persistido
/preferences       Preferencias y enfoque por llamamiento
/admin             Admin dashboard
```

## Componentes

```txt
layout/
  app-shell
  app-providers
  audio-dock

search/
  global-search
  search-experience
  citation-card

chat/
  chat-experience

preferences/
  calling-preferences

document/
  pdf-reader
  document-reader
  scripture-references

library/
  speech-card
  library-grid
```

## Streaming UI

`ragApi.streamChat` lee `ReadableStream`, parsea eventos SSE y emite:

- `session`
- `citations`
- `delta`
- `grounding`
- `done`

La UI muestra Markdown parcial mientras llega el modelo y luego adjunta grounding y citation cards.

## Enfoque por llamamiento

`packages/shared/church-callings.json` contiene el catalogo editable de
llamamientos. `useUserPreferencesStore` persiste la seleccion local y
`/api/profile/preferences` sincroniza los campos del perfil. El chat envia
`calling_focus` al API para que el RAG agregue una seccion dinamica de
aplicacion sin cambiar la doctrina.

## Escalabilidad Visual

- Home usa carruseles horizontales.
- Biblioteca usa virtualizacion.
- Busqueda usa virtualizacion vertical.
- Document reader separa texto principal y panel contextual.
- Admin usa metric cards compactas para lectura rapida.

## Produccion

- Configurar `NEXT_PUBLIC_APP_URL=https://www.estudiopy.com`.
- Configurar `NEXT_PUBLIC_API_URL=https://api.estudiopy.com`.
- El cliente agrega `/api` a cada ruta y no usa rewrites de host interno.
- Ejecutar `npm run typecheck` y `npm run build` en CI.
