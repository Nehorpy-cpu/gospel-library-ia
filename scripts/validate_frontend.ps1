$ErrorActionPreference = 'Stop'

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$WebDir = Join-Path $RepoRoot 'apps\web'
$PackageJson = Join-Path $WebDir 'package.json'

if (-not (Test-Path $WebDir)) {
  Write-Error "No existe la carpeta frontend esperada: $WebDir"
}

if (-not (Test-Path $PackageJson)) {
  Write-Error "No existe package.json en: $WebDir"
}

Write-Host "Validando frontend desde: $WebDir"

Push-Location $WebDir
try {
  if (-not (Test-Path (Join-Path $RepoRoot 'node_modules'))) {
    Write-Host "node_modules no existe en la raiz. Instalando dependencias con lockfile..."
    & corepack pnpm install --frozen-lockfile
  }

  Write-Host "Ejecutando lint..."
  & corepack pnpm lint

  Write-Host "Ejecutando typecheck..."
  & corepack pnpm typecheck

  Write-Host "Ejecutando build frontend/Vercel..."
  & corepack pnpm build
}
finally {
  Pop-Location
}

Write-Host "Validacion frontend completada."
