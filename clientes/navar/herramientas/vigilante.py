# -*- coding: utf-8 -*-
"""
vigilante — mira la carpeta de Drive "NAVAR - Datos" y, cuando aparece algo nuevo, corre el
lector que corresponde. El lector deja su para_pegar_*.xlsx en la misma carpeta de Drive; el
disparador horario de la Sheet (importarLoNuevo) lo levanta solo. Nadie aprieta nada.

QUÉ MIRA (dentro de "NAVAR - Datos", en el Drive montado en la Mac): UNA CARPETA POR EXPORT.
Cada bot / persona deja su archivo en su carpeta y nada más; el vigilante sabe qué hacer con cada una.

    Bancos/<banco>/          extractos (PDF o Excel del home banking). Se ACUMULAN: cada mes
                             se agrega el nuevo; el lector relee todo y no duplica.
                             → lector/extractos.py → Saldos Bancarios + Movimientos
    Cuentas a cobrar/        Tango: composición de saldos de clientes. Un archivo por día:
                             "A cobranzas 2026-09-22.xlsx", "AA cobranzas 2026-09-22.xlsx".
    Cuentas a pagar/         Tango: composición de saldos de proveedores: "A pagos <fecha>.xlsx".
    Cheques/                 Tango: "A cheques terceros <fecha>.xlsx" (cartera) y
                             "A cheques propios <fecha>.xlsx" (emitidos pendientes).
                             Las tres carpetas de Tango → lector/tango.py → Cuentas a Cobrar,
                             Cuentas a Pagar, Cartera de Cheques. Cada archivo es la FOTO
                             completa de ese día (no un delta): se carga el más nuevo de cada
                             (empresa, lista); los viejos quedan como historia.
    Deuda bancaria/          Bancos_Navar.xlsx, el mapa de deuda
                             → lector/deuda_bancaria.py (cruza cuotas con el último extracto)
    Impuestos/               la planilla de Celia (el archivo más nuevo manda)
                             → lector/deuda_impositiva.py
    _para la Sheet/          lo que generan los lectores (para_pegar_*.xlsx y resumen_*.md).
                             De acá los levanta el disparador de la Sheet. Nadie toca esta carpeta.

CÓMO SABE QUE HAY ALGO NUEVO
    Guarda en clientes/navar/.run/vigilante.json una firma de cada fuente (archivos + fecha de
    modificación). Si la firma cambió y el archivo más nuevo tiene más de 2 minutos (para que
    Drive termine de bajarlo), corre el lector. Si el lector falla, lo anota y lo vuelve a
    intentar en la próxima pasada. Todo queda en clientes/navar/privado/vigilante.log.

CÓMO CORRE
    Cada 15 minutos por launchd (ver instalar_vigilante.sh). A mano: python vigilante.py
    [--forzar bancos|tango|deuda|impuestos] [--simular]
"""

import os
import sys
import json
import time
import glob
import argparse
import datetime
import subprocess

AQUI = os.path.dirname(os.path.abspath(__file__))
BASE_REPO = os.path.abspath(os.path.join(AQUI, "..", "..", ".."))
PYTHON = os.path.join(BASE_REPO, ".venv", "bin", "python")
DRIVE = os.path.join(os.path.expanduser("~"), "Library", "CloudStorage", "GoogleDrive-thomasezequielmanzo@gmail.com", "Mi unidad", "NAVAR - Datos")
ESTADO = os.path.join(BASE_REPO, "clientes", "navar", ".run", "vigilante.json")
LOG = os.path.join(BASE_REPO, "clientes", "navar", "privado", "vigilante.log")
ESPERA_SEG = 120          # un archivo recién bajado por Drive puede estar a medias
IGNORAR = ("para_pegar", "resumen_", "~$", ".DS_Store")
SALIDA = os.path.join(DRIVE, "_para la Sheet")
CARPETAS_TANGO = ("Cuentas a cobrar", "Cuentas a pagar", "Cheques")
STAGING_TANGO = os.path.join(BASE_REPO, "clientes", "navar", ".run", "tango_ultimo")

sys.path.insert(0, BASE_REPO)
from lector.tango import LISTAS as LISTAS_TANGO, _norm as _norm_tango      # las mismas reglas de nombre que el lector


def log(msg):
    linea = "%s  %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(linea)
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(linea + "\n")


def archivos_de(carpeta, recursivo=True):
    """[(ruta, mtime)] de los archivos de datos (sin los que generan los lectores)."""
    out = []
    if not os.path.isdir(carpeta):
        return out
    for raiz, subcarpetas, nombres in os.walk(carpeta):
        subcarpetas[:] = [s for s in subcarpetas if not s.startswith(".")]     # .ocr y similares: caché del lector
        for n in nombres:
            if n.startswith(IGNORAR) or n.endswith((".md", ".txt", ".log")):
                continue
            r = os.path.join(raiz, n)
            out.append((r, os.path.getmtime(r)))
        if not recursivo:
            break
    return sorted(out)


def firma(archivos):
    # nombre + tamaño, no la fecha: Drive vuelve a estampar la fecha al sincronizar y eso
    # haría correr el lector dos veces por el mismo archivo
    return "|".join("%s@%d" % (os.path.relpath(r, DRIVE), os.path.getsize(r)) for r, m in archivos)


def lista_tango(ruta):
    """(empresa, lista) de un export de Tango por su nombre, con las mismas reglas que lector/tango.py."""
    nombre = _norm_tango(os.path.splitext(os.path.basename(ruta))[0])
    partes = nombre.split()
    if not partes or nombre.startswith(("para pegar", "~$")):
        return None
    resto = " ".join(partes[1:])
    for clave, palabras in LISTAS_TANGO:
        if any(p in resto for p in palabras):
            return (partes[0].upper(), clave)
    return None


def tango_ultimos():
    """El archivo más nuevo de cada (empresa, lista) en las tres carpetas de Tango: [(ruta, mtime)]."""
    mejor = {}
    for c in CARPETAS_TANGO:
        for r in glob.glob(os.path.join(DRIVE, c, "*.xlsx")):
            k = lista_tango(r)
            if k and (k not in mejor or os.path.getmtime(r) > mejor[k][1]):
                mejor[k] = (r, os.path.getmtime(r))
    return sorted(mejor.values())


def preparar_staging_tango(archivos):
    """Copia el último de cada lista a una carpeta limpia y devuelve esa carpeta (tango.py lee una carpeta)."""
    import shutil
    if os.path.isdir(STAGING_TANGO):
        shutil.rmtree(STAGING_TANGO)
    os.makedirs(STAGING_TANGO)
    for r, _ in archivos:
        # No usar shutil.copy2: en la carpeta de Drive un archivo que todavía no terminó de
        # bajar da "Resource deadlock avoided". Leerlo a mano lo fuerza a bajar o falla claro.
        with open(r, "rb") as fi, open(os.path.join(STAGING_TANGO, os.path.basename(r)), "wb") as fo:
            shutil.copyfileobj(fi, fo)
    return STAGING_TANGO


def _filas_por_solapa(ruta):
    import openpyxl
    wb = openpyxl.load_workbook(ruta, read_only=False)
    return {ws.title: sum(1 for r in ws.iter_rows(min_row=2, values_only=True) if any(v is not None for v in r)) for ws in wb.worksheets}


def control_contra_anterior(nuevo):
    """Compara el para_pegar nuevo con el último publicado del mismo tipo. Si alguna solapa
    perdió más de la mitad de las filas, algo cambió en el export (un filtro, una consulta mal
    guardada) y NO se publica: el importador borraría de la Sheet lo que el archivo no trae.
    Devuelve None si está bien, o el texto del problema."""
    prefijo = os.path.basename(nuevo).rsplit("_", 1)[0] + "_"          # para_pegar_bancos_
    previos = sorted(r for r in glob.glob(os.path.join(SALIDA, prefijo + "*.xlsx")) if r != nuevo)
    if not previos:
        return None
    antes, ahora = _filas_por_solapa(previos[-1]), _filas_por_solapa(nuevo)
    problemas = []
    for solapa, n_antes in antes.items():
        n_ahora = ahora.get(solapa, 0)
        if n_antes >= 20 and n_ahora < n_antes * 0.5:
            problemas.append("%s: %d filas antes, %d ahora" % (solapa, n_antes, n_ahora))
    return "; ".join(problemas) or None


def mover_salidas(desde):
    """Lleva lo que generó un lector (para_pegar_*, resumen_*) a _para la Sheet, salvo que el
    control contra el anterior diga que algo se achicó de golpe: entonces va a _retenido."""
    import shutil
    os.makedirs(SALIDA, exist_ok=True)
    retenido = None
    for r in glob.glob(os.path.join(desde, "para_pegar_*.xlsx")):
        retenido = control_contra_anterior(r)
    destino = SALIDA
    if retenido:
        destino = os.path.join(SALIDA, "_retenido")
        os.makedirs(destino, exist_ok=True)
        log("RETENIDO (no se publica): %s. Revisar el export; el archivo quedó en _retenido" % retenido)
    for r in glob.glob(os.path.join(desde, "para_pegar_*")) + glob.glob(os.path.join(desde, "resumen_*")):
        shutil.move(r, os.path.join(destino, os.path.basename(r)))
    return retenido


def ultimo_con_prefijo(prefijo):
    c = [r for r in glob.glob(os.path.join(DRIVE, "**", prefijo + "*.xlsx"), recursive=True) if "(1)" not in r]
    return max(c, key=os.path.getmtime) if c else None


# ---- cada fuente: qué mira y qué comando corre
def fuentes(hoy):
    H = ["--hoy", hoy.isoformat(), "--cliente", "navar"]
    F = []
    bancos = os.path.join(DRIVE, "Bancos")
    F.append({"nombre": "bancos", "archivos": archivos_de(bancos),
              "cmd": lambda: [PYTHON, os.path.join(BASE_REPO, "lector", "extractos.py"), "--carpeta", bancos] + H,
              "salidas": lambda: bancos})
    tango = tango_ultimos()
    # Solo vale si hay cobranzas Y pagos: si falta una, el lector dejaría esa lista vacía
    # y el importador borraría lo que hay en la Sheet.
    listas = {lista_tango(r)[1] for r, _ in tango}
    tango_ok = {"cobranzas", "pagos"} <= listas
    F.append({"nombre": "tango", "archivos": tango if tango_ok else [],
              "cmd": lambda: [PYTHON, os.path.join(BASE_REPO, "lector", "tango.py"), "--carpeta", preparar_staging_tango(tango)] + H,
              "salidas": lambda: STAGING_TANGO})
    mapa = os.path.join(DRIVE, "Deuda bancaria", "Bancos_Navar.xlsx")
    F.append({"nombre": "deuda", "archivos": [(mapa, os.path.getmtime(mapa))] if os.path.exists(mapa) else [],
              "cmd": lambda: [PYTHON, os.path.join(BASE_REPO, "lector", "deuda_bancaria.py"), "--archivo", mapa] + H
                             + (["--bancos", ultimo_con_prefijo("para_pegar_bancos_")] if ultimo_con_prefijo("para_pegar_bancos_") else []),
              "salidas": lambda: os.path.dirname(mapa)})
    imp = archivos_de(os.path.join(DRIVE, "Impuestos"), recursivo=False)
    imp_nuevo = max(imp, key=lambda x: x[1])[0] if imp else None
    F.append({"nombre": "impuestos", "archivos": imp,
              "cmd": lambda: [PYTHON, os.path.join(BASE_REPO, "lector", "deuda_impositiva.py"), "--archivo", imp_nuevo] + H,
              "salidas": lambda: os.path.dirname(imp_nuevo)})
    return F


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--forzar", default=None, help="correr esa fuente aunque no haya nada nuevo")
    ap.add_argument("--simular", action="store_true", help="decir qué haría, sin correr nada")
    ap.add_argument("--hoy", default=None)
    a = ap.parse_args()
    hoy = datetime.date.fromisoformat(a.hoy) if a.hoy else datetime.date.today()

    if not os.path.isdir(DRIVE):
        log("no encuentro el Drive montado en %s (¿Google Drive está corriendo?)" % DRIVE)
        return 1
    estado = {}
    if os.path.exists(ESTADO):
        estado = json.load(open(ESTADO))
    ahora = time.time()
    corridos = 0
    for f in fuentes(hoy):
        n = f["nombre"]
        if not f["archivos"]:
            continue
        fa = firma(f["archivos"])
        if fa == estado.get(n) and a.forzar != n:
            continue
        mas_nuevo = max(m for _, m in f["archivos"])
        if ahora - mas_nuevo < ESPERA_SEG and a.forzar != n:
            log("%s: hay algo nuevo pero tiene menos de 2 min; espero a la próxima pasada" % n)
            continue
        try:
            cmd = f["cmd"]()
        except OSError as e:
            log("%s: Drive todavía no terminó de bajar un archivo (%s); próxima pasada" % (n, e.strerror))
            continue
        if a.simular:
            log("%s: correría  %s" % (n, " ".join(cmd)))
            continue
        log("%s: %d archivo(s) nuevos o cambiados → %s" % (n, len(f["archivos"]), os.path.basename(cmd[1])))
        r = subprocess.run(cmd, cwd=BASE_REPO, capture_output=True, text=True, timeout=1800)
        if r.returncode == 0:
            ret = mover_salidas(f["salidas"]())
            estado[n] = fa            # no se reintenta el mismo archivo; cuando suban uno nuevo, se vuelve a mirar
            log("%s: %s. %s" % (n, "RETENIDO" if ret else "OK", (r.stdout.strip().splitlines() or [""])[-1][:200]))
            corridos += 1
        else:
            log("%s: FALLÓ (código %d): %s" % (n, r.returncode, (r.stderr.strip().splitlines() or [""])[-1][:300]))
    os.makedirs(os.path.dirname(ESTADO), exist_ok=True)
    json.dump(estado, open(ESTADO, "w"), indent=1)
    if not corridos and not a.simular:
        pass    # nada nuevo: silencio en el log
    return 0


if __name__ == "__main__":
    sys.exit(main())
