# Comandos de Validacion en Windows

Este runbook separa la validacion local de backend, frontend/Vercel y Docker.
La causa raiz de los errores recientes fue ejecutar comandos pensados para la
raiz del repo desde `apps/api`. Desde `apps/api`, rutas como `apps/api/app` o
`apps/web` se convierten en rutas inexistentes bajo `apps/api/apps/...`.

Ruta raiz del repo:

```powershell
F:\Proyectos\gospel-library-ia-clean
```

## A. Validacion backend desde `apps/api`

Usar esta variante cuando la terminal ya esta trabajando dentro del backend.

```powershell
cd F:\Proyectos\gospel-library-ia-clean\apps\api
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH='.'
python -m compileall app scripts
python -m unittest discover -s tests
```

Notas:

- Desde `apps/api`, las rutas correctas son `app`, `scripts` y `tests`.
- No usar `apps/api/app` desde esta carpeta.
- No ejecutar `cd apps/api` si ya estas dentro de `apps/api`.

## B. Validacion backend desde la raiz

Usar esta variante cuando la terminal esta en la raiz del repo.

```powershell
cd F:\Proyectos\gospel-library-ia-clean
.\apps\api\.venv\Scripts\python.exe -m compileall apps\api\app apps\api\scripts
cd apps\api
$env:PYTHONPATH='.'
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Alternativa automatizada sin cambiar manualmente de carpeta:

```powershell
cd F:\Proyectos\gospel-library-ia-clean
.\scripts\validate_backend.ps1
```

## C. Validacion frontend local/Vercel

Los comandos reales estan definidos en `apps/web/package.json`:

- `lint`: `eslint . --max-warnings=0`
- `typecheck`: `tsc --noEmit`
- `build`: `node scripts/next-build.cjs`

Ejecutar desde `apps/web`:

```powershell
cd F:\Proyectos\gospel-library-ia-clean\apps\web
corepack pnpm install --frozen-lockfile
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm build
```

Alternativa automatizada:

```powershell
cd F:\Proyectos\gospel-library-ia-clean
.\scripts\validate_frontend.ps1
```

Este es el build equivalente al build de Vercel, siempre que el proyecto de
Vercel tenga root directory `apps/web`.

## D. Build Docker local opcional

En `package.json` raiz, el script `build` es:

```json
"build": "docker compose build"
```

Por eso este comando requiere Docker Desktop abierto:

```powershell
cd F:\Proyectos\gospel-library-ia-clean
corepack pnpm build
```

Validacion Docker local explicita:

```powershell
cd F:\Proyectos\gospel-library-ia-clean
docker compose config
docker compose build
```

Si Docker Desktop no esta corriendo, esta validacion puede fallar con un error
del pipe `dockerDesktopLinuxEngine`. Ese fallo no invalida backend tests ni el
build frontend/Vercel.

## E. Validacion sin Docker

Para validar lo importante sin depender de Docker Desktop:

```powershell
cd F:\Proyectos\gospel-library-ia-clean
.\scripts\validate_all_no_docker.ps1
```

Equivalente manual:

```powershell
cd F:\Proyectos\gospel-library-ia-clean\apps\api
$env:PYTHONPATH='.'
.\.venv\Scripts\python.exe -m compileall app scripts
.\.venv\Scripts\python.exe -m unittest discover -s tests

cd F:\Proyectos\gospel-library-ia-clean\apps\web
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm build

cd F:\Proyectos\gospel-library-ia-clean
git diff --check
```

## F. Checklist antes de push

```powershell
cd F:\Proyectos\gospel-library-ia-clean
git status
git diff --check
.\scripts\validate_backend.ps1
.\scripts\validate_frontend.ps1
git log --oneline -5
git push origin master
```

Docker no es obligatorio para este checklist. Usar Docker solo si tambien se
quiere validar imagenes locales.

## G. Checklist despues de deploy

API en Render:

```powershell
curl.exe https://api.estudiopy.com/health
Invoke-RestMethod "https://api.estudiopy.com/api/documents?limit=20"
Invoke-RestMethod "https://api.estudiopy.com/api/authors?limit=20"
Invoke-RestMethod "https://api.estudiopy.com/api/topics"
Invoke-RestMethod "https://api.estudiopy.com/api/ingestion/status"
```

Frontend en Vercel:

1. Abrir la app desplegada.
2. Abrir DevTools.
3. Verificar que las llamadas salgan a `https://api.estudiopy.com/api/...`.
4. Confirmar que `NEXT_PUBLIC_API_URL` no termina en `/api`.

## Resumen rapido de obligatoriedad

| Validacion | Carpeta | Requiere Docker |
| --- | --- | --- |
| Backend compileall/tests | `apps/api` | No |
| Frontend lint/typecheck/build | `apps/web` | No |
| Build raiz `corepack pnpm build` | raiz | Si |
| `docker compose config/build` | raiz | Si |
| `validate_all_no_docker.ps1` | raiz | No |
