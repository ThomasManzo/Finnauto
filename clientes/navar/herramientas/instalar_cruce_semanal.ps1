# Instala el cruce banco <-> Tango semanal en la notebook de NAVAR: los miércoles a las 08:30 corre
# lector\cruce_semanal.py, que deja en Drive (NAVAR - Datos\Cruce) el Excel para la administración y
# los datos del mail. El mail lo manda la Sheet a las 09:30 (cruce_semanal.gs). Si a las 08:30 la
# notebook estaba apagada, corre apenas se prenda (StartWhenAvailable); a las 09:00 hay un reintento.
#
#   Instalar (desde C:\finauto):
#     powershell -ExecutionPolicy Bypass -File clientes\navar\herramientas\instalar_cruce_semanal.ps1
#   Quitar:
#     powershell -ExecutionPolicy Bypass -File clientes\navar\herramientas\instalar_cruce_semanal.ps1 quitar

param([string]$accion = "instalar")

$horas = @("08:30", "09:00")

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$nombre = "finauto NAVAR cruce semanal"

if ($accion -eq "quitar") {
    Unregister-ScheduledTask -TaskName $nombre -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Cruce semanal desinstalado"
    exit 0
}

$python = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "No existe $python. Crear el entorno primero (ver instalar_notebook.md)."
    exit 1
}
$script = Join-Path $repo "lector\cruce_semanal.py"
$log = Join-Path $repo "clientes\navar\privado\cruce_semanal.log"
New-Item -ItemType Directory -Path (Split-Path $log) -Force | Out-Null

# Correr dos veces el mismo día no hace daño: se pisa el archivo del día con datos más nuevos.
$argumentos = '/d /c ""{0}" "{1}" --cliente navar >> "{2}" 2>&1"' -f $python, $script, $log
$accionTarea = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $argumentos -WorkingDirectory $repo
$disparadores = @($horas | ForEach-Object { New-ScheduledTaskTrigger -Weekly -DaysOfWeek Wednesday -At $_ })
$opciones = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -MultipleInstances IgnoreNew

Unregister-ScheduledTask -TaskName $nombre -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $nombre -Action $accionTarea -Trigger $disparadores `
    -Settings $opciones -Description "finauto: cruce banco-Tango semanal para la administración" | Out-Null

Write-Host "Cruce semanal instalado: miércoles a las $($horas -join " y "). Log: clientes\navar\privado\cruce_semanal.log"
