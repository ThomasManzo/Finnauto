# -*- coding: utf-8 -*-
"""
armar_tablero — rearma el tablero de NAVAR (el de siempre) a partir de la copia en Excel de la Sheet.

POR QUÉ (tarea 52, 07/10/2026)
    El tablero que ve la dirección (`finauto.html`, el de la barra lateral y las solapas Posición,
    A quién pagar, A cobrar, Proyección y Hallazgos) se armaba a mano: bajar la Sheet como Excel,
    correr dos comandos y copiar el resultado a Drive. Por eso quedaba viejo. Ahora:

      1. La Sheet deja sola una copia en Excel en `NAVAR - Datos/Tablero/fuente/` cada vez que importa
         algo nuevo (exportarParaTablero, en el Apps Script del tablero).
      2. El vigilante de la notebook ve la copia nueva (o que cambió el día) y corre ESTE script.
      3. Este script corre los mismos dos pasos de siempre y deja `finauto.html` en
         `NAVAR - Datos/Tablero/`. El link del tablero muestra siempre el último.

    No cambia nada del diseño ni de las cuentas: son los mismos programas (lector/cash_limpio.py y
    finauto.py) que se corrían a mano.

QUÉ NO PUEDE PASAR
    Que una corrida fallida deje el tablero roto o vacío. El nuevo se arma aparte, se controla que
    sea un tablero de verdad (tamaño y contenido), y recién ahí reemplaza al anterior de un saque.
    Si algo falla, queda el de antes (con la banda roja de "viejo" que pone la página a las 48 horas).

USO
    python clientes/navar/herramientas/armar_tablero.py --archivo "<Drive>/Tablero/fuente/NAVAR - Cash Flow ....xlsx"
"""

import os
import sys
import shutil
import argparse
import datetime
import subprocess

AQUI = os.path.dirname(os.path.abspath(__file__))
BASE_REPO = os.path.abspath(os.path.join(AQUI, "..", "..", ".."))
TRABAJO = os.path.join(BASE_REPO, "clientes", "navar", ".run", "tablero")
TAMANO_MINIMO = 100 * 1024        # un tablero de verdad pesa cientos de KB; uno roto, casi nada


def _correr(cmd):
    r = subprocess.run(cmd, cwd=BASE_REPO, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        ultima = (r.stderr.strip().splitlines() or r.stdout.strip().splitlines() or ["sin detalle"])[-1]
        raise RuntimeError("%s falló: %s" % (os.path.basename(cmd[1]), ultima[:300]))
    return r.stdout


def armar(archivo, destino, hoy, trabajo=TRABAJO):
    """Arma el tablero en `trabajo` y, si está bien, lo deja en `destino` (la carpeta Tablero)."""
    if not os.path.isfile(archivo):
        raise RuntimeError("no encuentro la copia de la Sheet: %s" % archivo)
    os.makedirs(trabajo, exist_ok=True)
    contrato = os.path.join(trabajo, "contrato.json")
    salidas = os.path.join(trabajo, "salidas")
    if os.path.isdir(salidas):
        shutil.rmtree(salidas)
    _correr([sys.executable, os.path.join(BASE_REPO, "lector", "cash_limpio.py"), "--archivo", archivo,
             "--cliente", "navar", "--hoy", hoy.isoformat(), "--salida", contrato])
    _correr([sys.executable, os.path.join(BASE_REPO, "finauto.py"), "--contrato", contrato,
             "--cliente", "navar", "--salidas", salidas, "--sin-memoria"])
    nuevo = os.path.join(salidas, "finauto.html")
    if not os.path.isfile(nuevo) or os.path.getsize(nuevo) < TAMANO_MINIMO:
        raise RuntimeError("el tablero nuevo salió vacío o incompleto; queda el anterior")
    with open(nuevo, encoding="utf-8") as f:
        html = f.read()
    if "NAVAR" not in html or "</html>" not in html:
        raise RuntimeError("el tablero nuevo no parece un tablero de NAVAR; queda el anterior")
    # Se copia al lado con otro nombre y se reemplaza de un saque: nadie ve un archivo a medias.
    os.makedirs(destino, exist_ok=True)
    final = os.path.join(destino, "finauto.html")
    temporal = final + ".parte"
    shutil.copyfile(nuevo, temporal)
    os.replace(temporal, final)
    return final


def main(argv=None):
    ap = argparse.ArgumentParser(description="Rearma el tablero de NAVAR con la copia en Excel de la Sheet")
    ap.add_argument("--archivo", required=True, help="la copia en Excel de la Sheet")
    ap.add_argument("--destino", default=None, help="carpeta Tablero (default: la que contiene a fuente/)")
    ap.add_argument("--hoy", default=datetime.date.today().isoformat())
    a = ap.parse_args(argv)
    destino = a.destino or os.path.dirname(os.path.dirname(os.path.abspath(a.archivo)))
    final = armar(a.archivo, destino, datetime.date.fromisoformat(a.hoy))
    print("tablero rearmado: %s (%d KB)" % (final, os.path.getsize(final) // 1024))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError) as e:
        sys.exit("No se rearmó el tablero: %s" % e)
