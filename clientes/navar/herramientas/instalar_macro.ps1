# Instala o quita la bajada de Macro. Los tres secretos quedan solo en el llavero.
param([string]$accion = "instalar")

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$nombre = "finauto NAVAR Macro"

if ($accion -eq "quitar") {
    Unregister-ScheduledTask -TaskName $nombre -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Macro desinstalado"
    exit 0
}

$python = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "No existe $python. Crear el entorno primero (ver instalar_notebook.md)."
    exit 1
}
$script = Join-Path $repo "orquestador\correr.py"
$log = Join-Path $repo "clientes\navar\privado\macro.log"
New-Item -ItemType Directory -Path (Split-Path $log) -Force | Out-Null

# cmd.exe deja stdout y stderr juntos, agregados al final: si falla de madrugada
# se conserva tanto el resumen de Macro como el motivo del error.
$argumentos = '/d /c ""{0}" "{1}" --cliente navar --banco macro --si-falta >> "{2}" 2>&1"' -f $python, $script, $log
$accionTarea = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $argumentos -WorkingDirectory $repo
# Reintenta solo si falta; el orquestador frena tras dos claves sin confirmar. Las horas quedan
# separadas 15 minutos o más: Macro no deja volver a entrar hasta pasados unos 10 minutos (Thomas,
# 10/11/2026), y un reintento antes de eso fallaría y gastaría uno de los dos intentos del día.
$horas = @("06:25", "06:45", "07:30", "09:05", "12:05", "16:05")
$disparadores = @($horas | ForEach-Object { New-ScheduledTaskTrigger -Daily -At $_ })
$opciones = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) -MultipleInstances IgnoreNew

Unregister-ScheduledTask -TaskName $nombre -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $nombre -Action $accionTarea -Trigger $disparadores `
    -Settings $opciones -Description "finauto: baja los movimientos diarios de la cuenta de Macro" | Out-Null

Write-Host "Macro instalado: corre todos los días a las $($horas -join ", ") (reintenta solo si falta). Log: clientes\navar\privado\macro.log"
