# Vercel Frontend Root and API URL

## Proyecto correcto

El frontend de produccion es la aplicacion Next.js ubicada en `apps/web`.
`apps/api` es el backend FastAPI desplegado por separado en Render.

La carpeta local `F:\Proyectos\liahonaai` es un proyecto historico Vite/Firebase.
No debe usarse para desplegar `www.estudiopy.com`, aunque tenga configurado el
mismo remoto de Git.

## Configuracion exacta de Vercel

Configura el proyecto de `www.estudiopy.com` con estos valores:

```txt
Framework Preset: Next.js
Root Directory: apps/web
Install Command: corepack pnpm install --frozen-lockfile
Build Command: corepack pnpm build
Output Directory: dejar vacio (Next.js usa .next)
Node.js Version: 22.x
```

El archivo `apps/web/vercel.json` fija los comandos cuando `apps/web` es la
raiz del proyecto. El lockfile y `pnpm-workspace.yaml` permanecen en la raiz
del repositorio.

Variables para Production, Preview y Development:

```txt
NEXT_PUBLIC_API_URL=https://api.estudiopy.com
NEXT_PUBLIC_APP_URL=https://www.estudiopy.com
NEXT_PUBLIC_ENVIRONMENT=production
```

No agregues `/api` a `NEXT_PUBLIC_API_URL`. El cliente agrega ese prefijo al
construir rutas como `/api/documents`. No agregues secretos del backend a
variables `NEXT_PUBLIC_*`.

## Detectar un despliegue viejo o una raiz incorrecta

1. En el deployment de Vercel compara el commit SHA con `origin/master`.
2. En Build Logs confirma que el directorio de trabajo sea `apps/web`.
3. Confirma que Vercel detecte Next.js, no Vite.
4. Revisa que el build ejecute `corepack pnpm build`.
5. En DevTools > Network abre una llamada de Biblioteca y confirma que Request
   URL comience con `https://api.estudiopy.com/api/`.
6. En la consola confirma `[api] Base URL: https://api.estudiopy.com`.

Si el bundle contiene `NEXT_PUBLIC_RAG_API_URL`, `http://api:8000`, Firebase o
archivos `vite`, Vercel esta sirviendo un commit anterior o el proyecto
equivocado. Un cambio de variable `NEXT_PUBLIC_*` requiere un nuevo build.

## Verificacion de produccion

Backend:

```powershell
curl.exe https://api.estudiopy.com/health
curl.exe https://api.estudiopy.com/api/documents
curl.exe https://api.estudiopy.com/api/authors
curl.exe https://api.estudiopy.com/api/topics
curl.exe https://api.estudiopy.com/api/ingestion/status
```

Frontend:

1. Abre `https://www.estudiopy.com/library`.
2. Abre DevTools > Network y filtra por `documents`.
3. Confirma una solicitud a
   `https://api.estudiopy.com/api/documents?limit=100&offset=0`.
4. Una respuesta `200` con listas vacias debe mostrar
   `No hay documentos cargados todavía.` y no un error de carga.

## DNS_HOSTNAME_NOT_FOUND

Este error indica que el navegador o una funcion de Vercel intento resolver un
hostname inexistente. En este proyecto ocurria cuando un bundle viejo usaba una
ruta relativa y un rewrite apuntaba al hostname Docker `api:8000`.

1. Confirma que `https://api.estudiopy.com/health` responda por HTTPS.
2. Corrige `NEXT_PUBLIC_API_URL` en Vercel.
3. Elimina variables obsoletas como `NEXT_PUBLIC_RAG_API_URL`,
   `API_INTERNAL_URL` o `RAG_INTERNAL_URL` si pertenecian al proxy anterior.
4. Redeploya sin reutilizar el deployment viejo.
5. Verifica de nuevo la Request URL en DevTools.

No se debe resolver el error agregando datos falsos ni ocultando respuestas
fallidas. Los estados vacios solo son validos cuando la API responde `200`.
