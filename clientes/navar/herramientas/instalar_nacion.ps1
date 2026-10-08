# Instala la bajada de Nación en la notebook de NAVAR: corre todos los días
# a las 05:52 y 05:57 y agrega su salida a privado\nacion.log. Las claves (DNI,
# usuario y contraseña) se leen del llavero de Windows; nunca se guardan en esta
# tarea ni en el log.
#
# Va DESPUÉS de Galicia (05:45 y 05:48) para no tener dos navegadores a la vez, y
# antes de que el vigilante procese a las 06:08.
#
#   Instalar (desde C:\finauto), recién cuando la prueba a mano salió bien:
#     powershell -ExecutionPolicy Bypass -File clientes\navar\herramientas\instalar_nacion.ps1
#   Quitar:
#     powershell -ExecutionPolicy Bypass -File clientes\navar\herramientas\instalar_nacion.ps1 quitar

param([string]$accion = "instalar")

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$nombre = "finauto NAVAR Nacion"

if ($accion -eq "quitar") {
    Unregister-ScheduledTask -TaskName $nombre -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Nación desinstalado"
    exit 0
}

$python = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "No existe $python. Crear el entorno primero (ver instalar_notebook.md)."
    exit 1
}
$script = Join-Path $repo "orquestador\correr.py"
$log = Join-Path $repo "clientes\navar\privado\nacion.log"
New-Item -ItemType Directory -Path (Split-Path $log) -Force | Out-Null

# cmd.exe deja stdout y stderr juntos, agregados al final: si falla de madrugada
# se conserva tanto el resumen de Nación como el motivo del error.
$argumentos = '/d /c ""{0}" "{1}" --cliente navar --banco nacion >> "{2}" 2>&1"' -f $python, $script, $log
$accionTarea = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $argumentos -WorkingDirectory $repo
# El segundo horario es el seguro, como en Galicia: si la primera corrida salió bien,
# la segunda ve que ya está al día y no vuelve a entrar al banco.
$disparador = New-ScheduledTaskTrigger -Daily -At "05:52"
$disparadorSeguro = New-ScheduledTaskTrigger -Daily -At "05:57"
$opciones = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) -MultipleInstances IgnoreNew

Unregister-ScheduledTask -TaskName $nombre -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $nombre -Action $accionTarea -Trigger @($disparador, $disparadorSeguro) `
    -Settings $opciones -Description "finauto: baja los movimientos diarios de la cuenta de Nación" | Out-Null

Write-Host "Nación instalado: corre todos los días a las 05:52 y 05:57. Log: clientes\navar\privado\nacion.log"
