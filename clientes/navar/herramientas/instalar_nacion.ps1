# Instala la bajada de Nación en la notebook de NAVAR: corre todos los días
# desde las 06:10 (reintenta solo si falta) y agrega su salida a privado\nacion.log. Las claves (DNI,
# usuario y contraseña) se leen del llavero de Windows; nunca se guardan en esta
# tarea ni en el log.
#
# BNA+ deja entrar recién desde las 06:00 (dato de Thomas, 07/10/2026): por eso 06:10, ya
# terminado Galicia (05:45 y 05:48). El vigilante lo procesa a las 06:23.
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
$argumentos = '/d /c ""{0}" "{1}" --cliente navar --banco nacion --si-falta >> "{2}" 2>&1"' -f $python, $script, $log
$accionTarea = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $argumentos -WorkingDirectory $repo
# Mismo esquema que Galicia (tarea 51): 06:15 es el seguro y el resto, reintentos del día. Con
# --si-falta, si hoy ya bajó bien no vuelve a entrar; si el banco recibió la contraseña y no confirmó
# la entrada 2 veces, no insiste (para no bloquear el usuario). BNA+ deja entrar de 06:00 a 22:00.
$horas = @("06:10", "06:15", "07:00", "09:00", "12:00", "16:00")
$disparadores = @($horas | ForEach-Object { New-ScheduledTaskTrigger -Daily -At $_ })
$opciones = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) -MultipleInstances IgnoreNew

Unregister-ScheduledTask -TaskName $nombre -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $nombre -Action $accionTarea -Trigger $disparadores `
    -Settings $opciones -Description "finauto: baja los movimientos diarios de la cuenta de Nación" | Out-Null

Write-Host "Nación instalado: corre todos los días a las $($horas -join ", ") (reintenta solo si falta). Log: clientes\navar\privado\nacion.log"
