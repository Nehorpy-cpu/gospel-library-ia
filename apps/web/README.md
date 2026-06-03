# Gospel Library IA Web

Frontend Next.js 15 App Router para Gospel Library IA.

## Stack

- Next.js 15
- TypeScript
- Tailwind
- shadcn/ui-style local primitives
- Zustand
- TanStack Query
- TanStack Virtual
- next-themes
- react-markdown
- lucide-react

## Rutas

```txt
/                  Home tipo Netflix + Gospel Library
/search            Busqueda global IA
/chat              Chat doctrinal streaming
/library           Biblioteca virtualizada
/documents/[id]    Lector PDF/documento
/authors/[slug]    Pagina de autor
/collections       Colecciones
/favorites         Favoritos
/history           Historial
/admin             Dashboard admin
/api/rag/*         Proxy hacia FastAPI RAG
```

## UI/UX

- Shell responsive con sidebar desktop y header sticky.
- Dark mode con `next-themes`.
- Busqueda global modal.
- Cards compactas para discursos, manuales, PDFs, audios y escrituras.
- Chat con streaming SSE, Markdown y tarjetas de citas.
- Lector documental preparado para PDF, OCR, subrayados y notas.
- Biblioteca con virtualized lists para colecciones grandes.

## Configuracion

Variables:

```txt
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_RAG_API_URL=/api/rag
RAG_INTERNAL_URL=http://rag-api:8090
```

En desarrollo local fuera de Docker, `RAG_INTERNAL_URL` puede apuntar a:

```txt
http://localhost:8090
```
