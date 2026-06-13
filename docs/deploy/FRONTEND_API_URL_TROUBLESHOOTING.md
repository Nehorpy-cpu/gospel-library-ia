# Frontend API URL Troubleshooting

## Configuracion de produccion

El frontend de Vercel llama a FastAPI directamente. Configura estas variables
en Production, Preview y Development segun corresponda:

```txt
NEXT_PUBLIC_API_URL=https://api.estudiopy.com
NEXT_PUBLIC_APP_URL=https://www.estudiopy.com
NEXT_PUBLIC_ENVIRONMENT=production
```

No agregues `/api` al final de `NEXT_PUBLIC_API_URL`. El cliente agrega ese
prefijo a rutas como `/documents`, `/authors`, `/topics`, `/search` y `/chat`.
No copies secretos del backend a variables `NEXT_PUBLIC_*`.

## Causa de DNS_HOSTNAME_NOT_FOUND

La configuracion anterior usaba `NEXT_PUBLIC_RAG_API_URL` y, cuando no estaba
definida, enviaba las solicitudes a `/api` en el dominio de Vercel. Un rewrite
intentaba resolver `http://api:8000`, un hostname interno de Docker que no
existe en la red de Vercel. El cliente actual construye URLs absolutas desde
`NEXT_PUBLIC_API_URL` y valida el origen antes de ejecutar `fetch`.

## Aplicar cambios en Vercel

1. Abre el proyecto de Vercel y entra en Settings > Environment Variables.
2. Elimina `NEXT_PUBLIC_RAG_API_URL`, `API_INTERNAL_URL` y `RAG_INTERNAL_URL`
   si solo se usaban para los rewrites anteriores.
3. Configura las tres variables de produccion mostradas arriba.
4. Inicia un redeploy. Las variables `NEXT_PUBLIC_*` se incorporan durante el
   build, por lo que cambiar su valor sin redeploy no actualiza el navegador.
5. En la consola del navegador confirma el mensaje seguro:
   `[api] Base URL: https://api.estudiopy.com`.

## Verificacion

Comprueba primero el backend:

```powershell
curl.exe https://api.estudiopy.com/health
curl.exe https://api.estudiopy.com/api/documents
curl.exe https://api.estudiopy.com/api/authors
curl.exe https://api.estudiopy.com/api/topics
curl.exe https://api.estudiopy.com/api/ingestion/status
```

Luego abre:

- `https://www.estudiopy.com/library`
- `https://www.estudiopy.com/authors`
- `https://www.estudiopy.com/search`
- `https://www.estudiopy.com/chat`
- `https://www.estudiopy.com/admin`

Una respuesta valida con `items: []` no es un error. La biblioteca debe mostrar
`No hay documentos cargados todavía.` y las otras pantallas deben conservar
sus estados vacios.

Para un build local con Docker Compose, los valores públicos se pasan como
argumentos de build desde `.env`. Los valores predeterminados apuntan a
`http://localhost:3000` y `http://localhost:8000`.

## Errores de configuracion

- `Falta NEXT_PUBLIC_API_URL`: crea la variable en Vercel y vuelve a desplegar.
- `NEXT_PUBLIC_API_URL no es una URL valida`: usa el origen completo con
  `https://`.
- `debe ser https://api.estudiopy.com en produccion`: corrige un dominio viejo,
  localhost o un hostname interno.
- Error de red con la variable correcta: verifica DNS, certificado TLS, CORS y
  el estado del servicio en Render.
