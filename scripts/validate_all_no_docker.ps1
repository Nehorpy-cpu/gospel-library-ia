$ErrorActionPreference = 'Stop'

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')

Write-Host "Validacion completa sin Docker desde: $RepoRoot"

& (Join-Path $PSScriptRoot 'validate_backend.ps1')
& (Join-Path $PSScriptRoot 'validate_frontend.ps1')

Push-Location $RepoRoot
try {
  Write-Host "Verificando whitespace con git diff --check..."
  & git diff --check
}
finally {
  Pop-Location
}

Write-Host "Validacion sin Docker completada."
