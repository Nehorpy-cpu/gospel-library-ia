# Gospel Library IA Frontend Architecture

## Principios

- App Router con Server Components en paginas y Client Components solo para interaccion.
- API proxy `/api/rag/*` para evitar CORS y ocultar URLs internas.
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

## Escalabilidad Visual

- Home usa carruseles horizontales.
- Biblioteca usa virtualizacion.
- Busqueda usa virtualizacion vertical.
- Document reader separa texto principal y panel contextual.
- Admin usa metric cards compactas para lectura rapida.

## Produccion

- Configurar `NEXT_PUBLIC_APP_URL`.
- Usar `RAG_INTERNAL_URL` para comunicacion server-to-server.
- Mantener `NEXT_PUBLIC_RAG_API_URL=/api/rag` salvo que exista gateway publico.
- Ejecutar `npm run typecheck` y `npm run build` en CI.
