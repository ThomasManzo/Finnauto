# Instala la bajada de Galicia en la notebook de NAVAR: corre todos los días a las 05:45 y
# reintenta sola durante el día si no bajó (tarea 51), y agrega su salida a privado\galicia.log. Las claves se leen
# del llavero de Windows; nunca se guardan en esta tarea ni en el log.
#
#   Instalar (desde C:\finauto):
#     powershell -ExecutionPolicy Bypass -File clientes\navar\herramientas\instalar_galicia.ps1
#   Quitar:
#     powershell -ExecutionPolicy Bypass -File clientes\navar\herramientas\instalar_galicia.ps1 quitar

param([string]$accion = "instalar")

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$nombre = "finauto NAVAR Galicia"

if ($accion -eq "quitar") {
    Unregister-ScheduledTask -TaskName $nombre -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Galicia desinstalado"
    exit 0
}

$python = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "No existe $python. Crear el entorno primero (ver instalar_notebook.md)."
    exit 1
}
$script = Join-Path $repo "orquestador\correr.py"
$log = Join-Path $repo "clientes\navar\privado\galicia.log"
New-Item -ItemType Directory -Path (Split-Path $log) -Force | Out-Null

# cmd.exe deja stdout y stderr juntos, agregados al final: si falla de madrugada
# se conserva tanto el resumen de Galicia como el motivo del error.
# --si-falta: si hoy ya bajó bien no abre el banco; si el banco recibió la clave y no confirmó la
# entrada 2 veces en el día, no insiste (para no bloquear el usuario) y lo deja escrito para el mail.
$argumentos = '/d /c ""{0}" "{1}" --cliente navar --banco galicia --si-falta >> "{2}" 2>&1"' -f $python, $script, $log
$accionTarea = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $argumentos -WorkingDirectory $repo
# 05:48 es el seguro de siempre (la primera corrida a veces falla en frío, tareas 27 a 29); los
# demás son los reintentos del día. Volver a bajar reemplaza el archivo del día, no duplica.
# Si cambian estos horarios, cambiar también GALICIA_REINTENTA_HASTA en aviso_diario.gs.
$horas = @("05:45", "05:48", "06:30", "07:15", "09:00", "12:00", "16:00")
$disparadores = @($horas | ForEach-Object { New-ScheduledTaskTrigger -Daily -At $_ })
$opciones = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) -MultipleInstances IgnoreNew

Unregister-ScheduledTask -TaskName $nombre -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $nombre -Action $accionTarea -Trigger $disparadores `
    -Settings $opciones -Description "finauto: baja el extracto diario de Galicia" | Out-Null

Write-Host "Galicia instalado: corre todos los días a las $($horas -join ", ") (reintenta solo si falta). Log: clientes\navar\privado\galicia.log"
