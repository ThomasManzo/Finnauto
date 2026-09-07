# nuevo_cash.ps1 — conectar finauto a una planilla nueva, sin depender de nadie.
#
# POR QUE EXISTE
# --------------
# El paso a paso decia "me pasas el ID del script y yo lo pongo en el
# .clasp.json". Eso funciona mientras haya alguien del otro lado. Thomas
# (07/09/2026) avisó que puede quedarse sin creditos justo antes de las
# reuniones, asi que ese paso no puede depender de una persona.
#
# Esto hace lo mismo, solo: apunta el proyecto al script de la planilla nueva,
# sube el codigo y verifica que haya quedado.
#
# COMO CONSEGUIR EL ID
#   En la planilla:  Extensiones -> Apps Script
#   En el editor:    engranaje (Configuracion del proyecto)
#                    -> "ID de la secuencia de comandos" -> Copiar
#
# USO
#   powershell -ExecutionPolicy Bypass -File scripts/nuevo_cash.ps1 -Id "1AbC..."
#
# Despues de esto, en la planilla:
#   1. Recargar la pagina (F5) para que aparezca el menu "finauto"
#   2. finauto -> Crear solapa de configuracion
#   3. finauto -> Exportar contrato (JSON)
#   4. En la PC:  powershell -ExecutionPolicy Bypass -File scripts/actualizar_tablero.ps1

param(
    [Parameter(Mandatory = $true)][string]$Id,
    [switch]$SoloVerificar
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$carpeta = Join-Path $repo "..\MAGA\apps_script\cashflow_prueba"
$carpeta = [System.IO.Path]::GetFullPath($carpeta)
$origen  = [System.IO.Path]::GetFullPath((Join-Path $repo "..\MAGA\apps_script\cashflow"))

Write-Host ""
Write-Host ("=" * 66)
Write-Host "  CONECTAR finauto A UNA PLANILLA NUEVA"
Write-Host ("=" * 66)

if (-not (Test-Path $origen)) {
    Write-Host "  No encuentro $origen" -ForegroundColor Red
    Write-Host "  Este script espera el repo MAGA al lado del de finauto."
    exit 1
}
if (-not (Get-Command clasp -ErrorAction SilentlyContinue)) {
    Write-Host "  No encuentro 'clasp'. Instalalo:  npm i -g @google/clasp" -ForegroundColor Red
    exit 1
}

# EL ID SE VALIDA ANTES DE ESCRIBIR NADA.
# Un id mal copiado -- con espacios, o con la URL entera pegada -- haria un push
# a ningun lado y el error recien aparece tres pasos despues, cuando el menu no
# esta y no se sabe por que.
$Id = $Id.Trim()
if ($Id -match "/d/([A-Za-z0-9_-]+)") { $Id = $Matches[1] }   # por si pegó la URL
if ($Id.Length -lt 30 -or $Id -notmatch "^[A-Za-z0-9_-]+$") {
    Write-Host "  Ese no parece un ID de Apps Script:" -ForegroundColor Red
    Write-Host "    '$Id'"
    Write-Host ""
    Write-Host "  Tiene que ser una cadena larga de letras y numeros, sin espacios."
    Write-Host "  Se saca en: la planilla -> Extensiones -> Apps Script ->"
    Write-Host "  engranaje (Configuracion del proyecto) -> ID de la secuencia."
    exit 1
}

if (-not (Test-Path $carpeta)) { New-Item -ItemType Directory -Path $carpeta | Out-Null }

$clasp = Join-Path $carpeta ".clasp.json"
$anterior = ""
if (Test-Path $clasp) {
    try { $anterior = (Get-Content $clasp -Raw | ConvertFrom-Json).scriptId } catch { }
}
if ($anterior -and $anterior -ne $Id) {
    Write-Host "  Antes apuntaba a: $anterior"
}
Write-Host "  Ahora apunta a  : $Id"

if ($SoloVerificar) {
    Write-Host ""
    Write-Host "  (-SoloVerificar: no se escribio ni se subio nada)" -ForegroundColor Yellow
    exit 0
}

@"
{
  "scriptId": "$Id",
  "rootDir": "",
  "scriptExtensions": [".js", ".gs"],
  "htmlExtensions": [".html"],
  "jsonExtensions": [".json"]
}
"@ | Out-File -FilePath $clasp -Encoding utf8

# El codigo vive SOLO en apps_script/cashflow. Se copia antes de cada push para
# que no haya dos versiones divergiendo: un solo lugar donde editar.
Get-ChildItem -Path $origen -Filter *.js | ForEach-Object {
    Copy-Item $_.FullName -Destination $carpeta -Force
}
Copy-Item (Join-Path $origen "appsscript.json") -Destination $carpeta -Force

Write-Host ""
Write-Host "  Subiendo el codigo..."
Push-Location $carpeta
try {
    clasp push --force
    if ($LASTEXITCODE -ne 0) { throw "clasp devolvio $LASTEXITCODE" }
} catch {
    Write-Host ""
    Write-Host "  FALLO EL PUSH: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Lo mas probable, en orden:" -ForegroundColor Yellow
    Write-Host "   1. La sesion de clasp vencio  ->  clasp login"
    Write-Host "   2. El ID es de otra cuenta de Google"
    Write-Host "   3. En la planilla nueva todavia no se abrio Apps Script"
    Write-Host "      una vez (hace falta para que el proyecto exista)"
    Pop-Location
    exit 1
}
Pop-Location

Write-Host ""
Write-Host "  LISTO. Ahora, en la planilla:" -ForegroundColor Green
Write-Host "   1. Recargar la pagina (F5) — el menu 'finauto' aparece arriba"
Write-Host "   2. finauto -> Crear solapa de configuracion"
Write-Host "   3. finauto -> Exportar contrato (JSON)"
Write-Host ""
Write-Host "   4. Y aca:  powershell -ExecutionPolicy Bypass -File scripts\actualizar_tablero.ps1"
Write-Host ""
