$ErrorActionPreference = 'Stop'

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$ApiDir = Join-Path $RepoRoot 'apps\api'
$Python = Join-Path $ApiDir '.venv\Scripts\python.exe'

if (-not (Test-Path $ApiDir)) {
  Write-Error "No existe la carpeta backend esperada: $ApiDir"
}

if (-not (Test-Path $Python)) {
  Write-Error "No existe el Python del entorno virtual: $Python. Crea el venv o ejecuta desde un entorno Python equivalente."
}

Write-Host "Validando backend desde: $ApiDir"

$PreviousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = '.'

Push-Location $ApiDir
try {
  Write-Host "Compilando app y scripts..."
  & $Python -m compileall app scripts

  Write-Host "Ejecutando tests backend..."
  & $Python -m unittest discover -s tests
}
finally {
  Pop-Location
  $env:PYTHONPATH = $PreviousPythonPath
}

Write-Host "Validacion backend completada."
