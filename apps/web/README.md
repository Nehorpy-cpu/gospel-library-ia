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
/preferences       Preferencias de llamamiento
/admin             Dashboard admin
```

## UI/UX

- Shell responsive con sidebar desktop y header sticky.
- Dark mode con `next-themes`.
- Busqueda global modal.
- Cards compactas para discursos, manuales, PDFs, audios y escrituras.
- Chat con streaming SSE, Markdown y tarjetas de citas.
- Preferencias de llamamiento con catalogo compartido y opcion personalizada.
- Lector documental preparado para PDF, OCR, subrayados y notas.
- Biblioteca con virtualized lists para colecciones grandes.

## Configuracion

Variables:

```txt
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_ENVIRONMENT=development
```

En Vercel:

```txt
NEXT_PUBLIC_APP_URL=https://www.estudiopy.com
NEXT_PUBLIC_API_URL=https://api.estudiopy.com
NEXT_PUBLIC_ENVIRONMENT=production
```

`NEXT_PUBLIC_API_URL` contiene solo el origen. El cliente agrega `/api` a los
endpoints de FastAPI.
