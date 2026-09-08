# traspaso.ps1 -- lo que TIENE que sobrevivir a esta computadora.
#
# POR QUE EXISTE
# --------------
# Thomas (08/09/2026): "Manana entrego esta PC". El codigo esta en GitHub, asi
# que el codigo no corre riesgo. Lo que corre riesgo es lo que esta gitignoreado
# a proposito -- porque son datos de un cliente real -- y por lo tanto existe en
# UNA sola maquina, que se va.
#
# LA REGLA PARA DECIDIR QUE VIAJA
# -------------------------------
# No viaja "todo lo importante": viaja lo que NO SE PUEDE VOLVER A GENERAR.
#
#   codigo            -> GitHub (Finnauto + MAGA). No viaja: ya esta.
#   credenciales      -> DPAPI, atadas a este usuario+maquina. NO PUEDEN viajar,
#                        no se desencriptan en otra PC. Se vuelven a cargar.
#   contratos         -> se regeneran desde la planilla... la de HOY. Los de
#                        fechas pasadas no vuelven. VIAJAN.
#   memoria           -> es historia: que dijimos el 05/09 y que paso despues.
#                        No se regenera de ninguna forma. VIAJA. Es lo mas
#                        irrecuperable de todo el proyecto.
#   PDFs y tablero    -> se regeneran, pero manana hay reunion. VIAJAN igual.
#   tareas programadas-> se regeneran con -Instalar, pero el XML es gratis.
#
# USO
#   powershell -ExecutionPolicy Bypass -File scripts/traspaso.ps1

param(
    [string]$Carpeta = "H:\Mi unidad",
    [string]$Destino = "finauto_traspaso"
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host ("=" * 66)
Write-Host "  finauto - TRASPASO DE MAQUINA"
Write-Host ("=" * 66)

if (-not (Test-Path $Carpeta)) {
    Write-Host "  No encuentro $Carpeta (la carpeta de Google Drive)." -ForegroundColor Red
    Write-Host "  Si tu unidad es otra letra:  -Carpeta 'G:\Mi unidad'"
    exit 1
}

$dest = Join-Path $Carpeta $Destino
if (-not (Test-Path $dest)) { New-Item -ItemType Directory -Path $dest | Out-Null }

function Copiar($origen, $sub, $filtro, $rotulo) {
    if (-not (Test-Path $origen)) {
        Write-Host ("  {0,-22} no existe en esta PC" -f $rotulo) -ForegroundColor Yellow
        return 0
    }
    $d = Join-Path $dest $sub
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d | Out-Null }
    $n = 0
    Get-ChildItem -Path $origen -Filter $filtro -File -ErrorAction SilentlyContinue | ForEach-Object {
        Copy-Item $_.FullName $d -Force
        $n++
    }
    $color = if ($n) { "Green" } else { "Yellow" }
    Write-Host ("  {0,-22} {1} archivo(s)" -f $rotulo, $n) -ForegroundColor $color
    return $n
}

Write-Host ""
Write-Host "  LO QUE NO SE PUEDE REGENERAR"
Write-Host ("  " + ("-" * 62))
$m = Copiar (Join-Path $repo "clientes\maga\memoria") "memoria_maga" "*.json" "Memoria (historia)"
$c = Copiar (Join-Path $repo "datos") "contratos" "CONTRATO_*.json" "Contratos"

Write-Host ""
Write-Host "  LO QUE SE REGENERA, PERO MANANA HAY REUNION"
Write-Host ("  " + ("-" * 62))
Copiar (Join-Path $repo "salidas") "informes" "*.pdf" "PDFs" | Out-Null
Copiar (Join-Path $repo "salidas") "informes" "finauto.html" "Tablero" | Out-Null

# LAS TAREAS PROGRAMADAS: el XML es la definicion exacta, con hora y argumentos.
# Se regeneran a mano, pero acordarse de la hora exacta a las tres semanas no.
Write-Host ""
Write-Host "  CONFIGURACION DE LA MAQUINA"
Write-Host ("  " + ("-" * 62))
$dt = Join-Path $dest "tareas_programadas"
if (-not (Test-Path $dt)) { New-Item -ItemType Directory -Path $dt | Out-Null }
$nt = 0
Get-ScheduledTask -ErrorAction SilentlyContinue |
    Where-Object { $_.TaskName -match "finauto|[Gg]alicia|[Cc]omafi" } | ForEach-Object {
        $xml = Export-ScheduledTask -TaskName $_.TaskName -TaskPath $_.TaskPath
        $safe = $_.TaskName -replace "[^A-Za-z0-9_ -]", "_"
        [System.IO.File]::WriteAllText((Join-Path $dt ($safe + ".xml")), $xml, [System.Text.Encoding]::UTF8)
        $nt++
    }
Write-Host ("  {0,-22} {1} tarea(s)" -f "Tareas programadas", $nt) -ForegroundColor Green

# LA MEMORIA DEL PROYECTO (la de Claude): el contexto acumulado de meses de
# decisiones. No es codigo y no esta en ningun repo.
$mem = Join-Path $env:USERPROFILE ".claude\projects\C--Users-thoma--claude-sessions\memory"
Copiar $mem "contexto_proyecto" "*.md" "Contexto del proyecto" | Out-Null

# ------------------------------------------------------------------ el LEEME
$hoy = (Get-Date).ToString("dd/MM/yyyy HH:mm")
$leeme = @"
TRASPASO DE MAQUINA - finauto
Generado el $hoy por scripts/traspaso.ps1

QUE HAY EN ESTA CARPETA
-----------------------
  memoria_maga/        La historia: que proyectamos cada dia y que paso.
                       ESTO NO SE REGENERA. Es lo unico verdaderamente
                       irrecuperable del proyecto.
  contratos/           Los contratos JSON ya exportados (fotos de la planilla).
  informes/            PDFs y el tablero, tal como quedaron hoy.
  tareas_programadas/  XML de las tareas de Windows (hora y argumentos exactos).
  contexto_proyecto/   Las notas de contexto del proyecto.

QUE **NO** ESTA ACA, Y POR QUE
------------------------------
  EL CODIGO ya esta en GitHub, no hace falta copiarlo:
      https://github.com/ThomasManzo/Finnauto   (motor, tablero, informes, bots)
      https://github.com/ThomasManzo/MAGA       (bots productivos + Apps Script)
  Los dos repos estan limpios y pusheados al 08/09/2026.

  LAS CLAVES DE LOS BANCOS no pueden copiarse. Estan encriptadas con DPAPI,
  que ata el archivo a ESTE usuario y ESTA maquina: el archivo copiado no se
  desencripta en otra PC. Es a proposito -- si se pudiera copiar, cualquiera
  que agarre la carpeta tendria las claves. En la maquina nueva se vuelven a
  cargar con:  python setup_credenciales.py

  LA SESION DE clasp (.clasprc.json) tampoco viaja: es un token de acceso a tu
  cuenta de Google. En la maquina nueva:  clasp login

  LAS PLANILLAS viven en tu Drive personal y son tuyas. No hay nada que mover.

PARA DEJAR LA MAQUINA NUEVA ANDANDO
-----------------------------------
  1. Instalar Python 3.14, Node y Git.
  2. npm i -g @google/clasp   y luego   clasp login
  3. git clone https://github.com/ThomasManzo/Finnauto.git C:inauto
     git clone https://github.com/ThomasManzo/MAGA.git      C:\MAGA
  4. cd C:inauto  &  pip install -r requirements.txt
  5. Copiar de vuelta desde esta carpeta:
       memoria_maga\*.json   ->  C:inauto\clientes\maga\memoria       contratos\*.json      ->  C:inauto\datos  6. Instalar Google Drive Escritorio y esperar a que sincronice.
  7. Cargar las claves de los bancos:  python setup_credenciales.py
  8. Reinstalar la tarea diaria:
       powershell -ExecutionPolicy Bypass -File scriptsctualizar_tablero.ps1 -Instalar
  9. Probar de punta a punta:
       python tests	est_motor.py
       powershell -ExecutionPolicy Bypass -File scriptsctualizar_tablero.ps1

  Si el paso 9 termina en verde, la maquina nueva quedo igual que la vieja.
"@
[System.IO.File]::WriteAllText((Join-Path $dest "LEEME_TRASPASO.txt"), $leeme, (New-Object System.Text.UTF8Encoding $true))

Write-Host ""
Write-Host ("=" * 66)
Write-Host "  Todo en: $dest" -ForegroundColor Green
Write-Host "  Drive lo sube solo. Verificalo en drive.google.com antes de"
Write-Host "  entregar la maquina -- que este en la carpeta local no alcanza."
Write-Host ("=" * 66)
if ($m -eq 0) {
    Write-Host "  OJO: no se copio ninguna memoria. Es lo unico irrecuperable." -ForegroundColor Red
}
Write-Host ""
