# actualizar_tablero.ps1 — el ultimo eslabon de la cadena automatica.
#
# LA CADENA, Y POR QUE ESTA PARTIDA ASI
# -------------------------------------
#   Apps Script  ->  genera el contrato solo, todos los dias a las 7
#   Google Drive ->  lo sincroniza a la carpeta local
#   ESTE SCRIPT  ->  corre el motor y arma el tablero
#
# Thomas eligio (06/09/2026) "Apps Script hasta cerrar los primeros dos
# clientes, despues servidor". La economia es correcta -- no pagar infra antes
# de tener ingreso -- pero Apps Script no puede correr el motor: son 277 tests
# de Python. Reescribirlo en JavaScript daria dos motores, uno con tests y otro
# sin, despegandose sin que nadie se entere.
#
# Entonces se parte el problema donde YA esta partido: en el contrato. Apps
# Script hace el dato, la PC hace la cuenta. Cero infraestructura, cero pasos a
# mano, un solo motor. Cuando haya dos clientes, el ultimo paso se muda a un
# servidor y nada mas cambia.
#
# NO USA LA API DE DRIVE a proposito: Google Drive Escritorio ya sincroniza la
# carpeta, asi que el archivo aparece solo. Una credencial menos que rota, que
# vence, o que hay que renovar el dia que no estas.
#
# USO
#   powershell -ExecutionPolicy Bypass -File scripts/actualizar_tablero.ps1
#   powershell -ExecutionPolicy Bypass -File scripts/actualizar_tablero.ps1 -Instalar
#
# -Instalar deja una tarea programada de Windows que lo corre todos los dias.

param(
    [string]$Carpeta = "H:\Mi unidad",
    [string]$Cliente = "maga",
    [string]$Salida  = "",
    [int]$Hora = 8,
    [switch]$Instalar
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
if (-not $Salida) { $Salida = Join-Path $repo "salidas\finauto.html" }

# ---------------------------------------------------------------- instalar
if ($Instalar) {
    $cmd = "powershell -ExecutionPolicy Bypass -File `"$PSCommandPath`" -Carpeta `"$Carpeta`" -Cliente $Cliente"
    $accion = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$PSCommandPath`" -Carpeta `"$Carpeta`" -Cliente $Cliente"
    # Una hora despues del export: le da margen a Drive para sincronizar.
    # El export corre a las 7; si esto corriera a las 7:05 y Drive venia lento,
    # armaria el tablero con el contrato de AYER y nadie se enteraria.
    $disparador = New-ScheduledTaskTrigger -Daily -At ([datetime]::Today.AddHours($Hora))
    Register-ScheduledTask -TaskName "finauto - actualizar tablero" `
        -Action $accion -Trigger $disparador -Force | Out-Null
    Write-Host ""
    Write-Host "  Tarea instalada: corre todos los dias a las $Hora`:00." -ForegroundColor Green
    Write-Host "  Para sacarla:  Unregister-ScheduledTask -TaskName 'finauto - actualizar tablero'"
    Write-Host ""
    Write-Host "  Falta la otra mitad: en la planilla, menu finauto ->"
    Write-Host "  'Generar el contrato solo (todos los dias)'."
    exit 0
}

# ---------------------------------------------------------------- correr
Write-Host ""
Write-Host ("=" * 64)
Write-Host "  finauto - actualizar tablero"
Write-Host ("=" * 64)

if (-not (Test-Path $Carpeta)) {
    Write-Host "  No encuentro la carpeta $Carpeta." -ForegroundColor Red
    Write-Host "  Es la carpeta que sincroniza Google Drive Escritorio."
    Write-Host "  Si tu unidad es otra letra, pasala con -Carpeta 'G:\Mi unidad'."
    exit 1
}

# EL CONTRATO MAS NUEVO, y se dice cual y de cuando.
# Armar el tablero con un contrato viejo y no avisarlo es exactamente el modo
# de falla que este proyecto viene persiguiendo: salida limpia, dato de ayer.
$archivo = Get-ChildItem -Path $Carpeta -Filter "_CONTRATO_finauto_*.json" -File -ErrorAction SilentlyContinue |
           Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $archivo) {
    # SE DICE QUE SI HAY, no solo que falta lo que se buscaba.
    #
    # Es la misma regla que el exportador: cuando no encuentra un bloque, lista
    # los rotulos que SI estan. Un "no hay contrato" a secas no distingue entre
    # "la carpeta esta mal", "Drive no sincronizo" y "el trigger nunca corrio",
    # que son tres problemas con tres soluciones distintas.
    Write-Host "  No hay ningun contrato en $Carpeta." -ForegroundColor Red
    $json = @(Get-ChildItem -Path $Carpeta -Filter "*.json" -File -ErrorAction SilentlyContinue)
    $todo = @(Get-ChildItem -Path $Carpeta -File -ErrorAction SilentlyContinue)
    Write-Host ""
    Write-Host "  La carpeta existe y tiene $($todo.Count) archivo(s), $($json.Count) .json."
    if ($json.Count) {
        Write-Host "  Los .json que si hay:"
        $json | Sort-Object LastWriteTime -Descending | Select-Object -First 5 |
            ForEach-Object { Write-Host ("     " + $_.Name + "   " + $_.LastWriteTime) }
        Write-Host ""
        Write-Host "  O sea que Drive SI sincroniza .json a esta carpeta. Entonces el" -ForegroundColor Yellow
        Write-Host "  problema no es la carpeta: o el contrato se esta guardando en otra" -ForegroundColor Yellow
        Write-Host "  (revisar CARPETA_SALIDA_ID en la solapa de configuracion), o Drive" -ForegroundColor Yellow
        Write-Host "  todavia no bajo los ultimos, o el trigger nunca corrio." -ForegroundColor Yellow
    } else {
        Write-Host "  Ningun .json llego a esta carpeta: parece un problema de sincronizacion."
    }
    Write-Host ""
    Write-Host "  Para usar otra carpeta:  -Carpeta 'G:\Mi unidad\loquesea'"
    exit 1
}

$horas = [math]::Round(((Get-Date) - $archivo.LastWriteTime).TotalHours, 1)
Write-Host "  Contrato : $($archivo.Name)"
Write-Host "  Generado : $($archivo.LastWriteTime)  ($horas horas atras)"
if ($horas -gt 30) {
    Write-Host "  OJO: el contrato tiene mas de 30 horas. El tablero se va a armar" -ForegroundColor Yellow
    Write-Host "  igual, pero con datos viejos. Revisar el trigger de la planilla." -ForegroundColor Yellow
}

$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) {
    Write-Host "  No encuentro python en el PATH." -ForegroundColor Red
    exit 1
}

Push-Location $repo
try {
    & $py "dashboard\app.py" --contrato $archivo.FullName --cliente $Cliente --salida $Salida
    if ($LASTEXITCODE -ne 0) { throw "el generador devolvio $LASTEXITCODE" }
    Write-Host ""
    Write-Host "  Tablero actualizado: $Salida" -ForegroundColor Green
} finally {
    Pop-Location
}
