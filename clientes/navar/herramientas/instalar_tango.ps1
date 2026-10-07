# Instala la bajada de Tango Live en la notebook de NAVAR: corre todos los días
# desde las 05:45 y agrega su salida a privado\tango_live.log. Las credenciales se
# leen del llavero de Windows; nunca se guardan en esta tarea ni en el log.
#
#   Instalar (desde C:\finauto):
#     powershell -ExecutionPolicy Bypass -File clientes\navar\herramientas\instalar_tango.ps1
#   Quitar:
#     powershell -ExecutionPolicy Bypass -File clientes\navar\herramientas\instalar_tango.ps1 quitar

param([string]$accion = "instalar")

# La primera hora baja; las demás sólo reintentan si todavía falta completar el día
# (--si-falta: si el parte de hoy ya está completo, no hace nada y no toca Tango).
# Tarea 51: reintenta hasta la noche, así un servidor que se prende tarde no deja el día
# sin Tango. Si cambian estos horarios, cambiar también TANGO_REINTENTA_HASTA en aviso_diario.gs.
$horas = @("05:45", "06:15", "06:45", "07:15") + @(8..20 | ForEach-Object { "{0:D2}:00" -f $_ })

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$nombre = "finauto NAVAR Tango"

if ($accion -eq "quitar") {
    Unregister-ScheduledTask -TaskName $nombre -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Tango desinstalado"
    exit 0
}

$python = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "No existe $python. Crear el entorno primero (ver instalar_notebook.md)."
    exit 1
}
$script = Join-Path $repo "ingestas\tango_live.py"
$log = Join-Path $repo "clientes\navar\privado\tango_live.log"
New-Item -ItemType Directory -Path (Split-Path $log) -Force | Out-Null

# cmd.exe deja stdout y stderr juntos, agregados al final: si falla de madrugada
# se conserva tanto el resumen de Tango como el motivo del error.
$argumentos = '/d /c ""{0}" "{1}" --cliente navar --si-falta >> "{2}" 2>&1"' -f $python, $script, $log
$accionTarea = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $argumentos -WorkingDirectory $repo
$disparadores = @($horas | ForEach-Object { New-ScheduledTaskTrigger -Daily -At $_ })
$opciones = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) -MultipleInstances IgnoreNew

Unregister-ScheduledTask -TaskName $nombre -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $nombre -Action $accionTarea -Trigger $disparadores `
    -Settings $opciones -Description "finauto: baja las fotos diarias de Tango Live (reintenta hasta las 20:00)" | Out-Null

Write-Host "Tango instalado: corre todos los días a las $($horas -join ", "). Log: clientes\navar\privado\tango_live.log"
