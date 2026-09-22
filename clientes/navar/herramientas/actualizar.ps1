# Actualiza C:\finauto con la última versión de GitHub sin tocar lo que es de esta máquina:
# el entorno (.venv), la memoria del vigilante (clientes\navar\.run), lo privado y las claves
# (que están en el llavero, no en archivos). Baja el ZIP, lo descomprime y pisa los archivos.
#
#   Desde cualquier PowerShell:
#     powershell -ExecutionPolicy Bypass -File C:\finauto\clientes\navar\herramientas\actualizar.ps1
#
#   La primera vez (cuando este archivo todavía no está en la notebook), la misma línea pero
#   bajándolo de GitHub:
#     powershell -ExecutionPolicy Bypass -Command "iwr https://raw.githubusercontent.com/ThomasManzo/Finnauto/main/clientes/navar/herramientas/actualizar.ps1 -OutFile $env:TEMP\actualizar.ps1; & $env:TEMP\actualizar.ps1"

param([string]$repo = "C:\finauto")

$zipUrl = "https://github.com/ThomasManzo/Finnauto/archive/refs/heads/main.zip"
$tmp = Join-Path $env:TEMP "finauto_update"
$zip = Join-Path $env:TEMP "finauto_main.zip"

Write-Host "Bajando la ultima version..."
Invoke-WebRequest -Uri $zipUrl -OutFile $zip
if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
Expand-Archive -Path $zip -DestinationPath $tmp -Force
$origen = Get-ChildItem $tmp | Select-Object -First 1   # Finnauto-main

# Lo que NO se pisa: es de esta maquina.
$excluir = @(".venv", ".run", "privado", ".git", "__pycache__")

Write-Host "Copiando sobre $repo (sin tocar .venv, .run, privado)..."
if (-not (Test-Path $repo)) { New-Item -ItemType Directory -Path $repo | Out-Null }
robocopy $origen.FullName $repo /E /XD $excluir /NFL /NDL /NJH /NJS /NC /NS /NP | Out-Null

Remove-Item $zip -Force
Remove-Item $tmp -Recurse -Force

# Si hay dependencias nuevas, instalarlas (rapido si no cambio nada).
$python = Join-Path $repo ".venv\Scripts\python.exe"
if (Test-Path $python) {
    & $python -m pip install -q -r (Join-Path $repo "requirements.txt")
}
Write-Host "Listo: $repo actualizado. Version:" (Get-Date -Format "dd/MM/yyyy HH:mm")
