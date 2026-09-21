# Instala el vigilante en la notebook de NAVAR (Windows) como tarea programada: corre
# clientes\navar\herramientas\vigilante.py cada 15 minutos, con la sesión abierta o no.
#
#   Abrir PowerShell en la carpeta del repo (ej. C:\finauto) y correr:
#     powershell -ExecutionPolicy Bypass -File clientes\navar\herramientas\instalar_vigilante.ps1
#   Para quitarla:
#     powershell -ExecutionPolicy Bypass -File clientes\navar\herramientas\instalar_vigilante.ps1 quitar
#
# Para ver qué hizo: type clientes\navar\privado\vigilante.log

param([string]$accion = "instalar")

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$nombre = "finauto NAVAR vigilante"

if ($accion -eq "quitar") {
    Unregister-ScheduledTask -TaskName $nombre -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "vigilante desinstalado"
    exit 0
}

$python = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { Write-Host "No existe $python. Crear el entorno primero (ver instalar_notebook.md)."; exit 1 }
$script = Join-Path $repo "clientes\navar\herramientas\vigilante.py"

$accionTarea = New-ScheduledTaskAction -Execute $python -Argument "`"$script`"" -WorkingDirectory $repo
$disparador = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 15) -RepetitionDuration (New-TimeSpan -Days 3650)
$opciones = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1) -MultipleInstances IgnoreNew
Unregister-ScheduledTask -TaskName $nombre -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $nombre -Action $accionTarea -Trigger $disparador -Settings $opciones -Description "finauto: mira NAVAR - Datos en Drive y corre los lectores" | Out-Null
Write-Host "vigilante instalado: corre cada 15 min. Log: clientes\navar\privado\vigilante.log"
