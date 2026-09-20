# -*- coding: utf-8 -*-
"""
vigilante — mira la carpeta de Drive "NAVAR - Datos" y, cuando aparece algo nuevo, corre el
lector que corresponde. El lector deja su para_pegar_*.xlsx en la misma carpeta de Drive; el
disparador horario de la Sheet (importarLoNuevo) lo levanta solo. Nadie aprieta nada.

QUÉ MIRA (dentro de "NAVAR - Datos", en el Drive montado en la Mac)
    Bancos/<banco>/          extractos (PDF o Excel del home banking). Se ACUMULAN: cada mes
                             se agrega el nuevo; el lector relee todo y no duplica.
                             → lector/extractos.py → Bancos/para_pegar_bancos_<hoy>.xlsx
    Tango/<AAAA-MM-DD>/      los exports de Tango Live de ese día (la carpeta más nueva manda)
                             → lector/tango.py → Tango/<fecha>/para_pegar_en_la_sheet_<hoy>.xlsx
    Deuda/Bancos_Navar.xlsx  el mapa de deuda bancaria
                             → lector/deuda_bancaria.py (cruza con el último para_pegar_bancos)
    Impuestos/*.xlsx         la planilla de Celia (el archivo más nuevo manda)
                             → lector/deuda_impositiva.py

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


def carpeta_mas_nueva(base):
    subs = [d for d in glob.glob(os.path.join(base, "*")) if os.path.isdir(d)]
    return max(subs, key=os.path.basename) if subs else None      # AAAA-MM-DD ordena solo


def ultimo_con_prefijo(prefijo):
    c = [r for r in glob.glob(os.path.join(DRIVE, "**", prefijo + "*.xlsx"), recursive=True) if "(1)" not in r]
    return max(c, key=os.path.getmtime) if c else None


# ---- cada fuente: qué mira y qué comando corre
def fuentes(hoy):
    H = ["--hoy", hoy.isoformat(), "--cliente", "navar"]
    F = []
    bancos = os.path.join(DRIVE, "Bancos")
    F.append({"nombre": "bancos", "archivos": archivos_de(bancos),
              "cmd": lambda: [PYTHON, os.path.join(BASE_REPO, "lector", "extractos.py"), "--carpeta", bancos] + H})
    tango = carpeta_mas_nueva(os.path.join(DRIVE, "Tango"))
    # Solo vale una carpeta de Tango que tenga cobranzas Y pagos: si faltan, el lector
    # dejaría las listas vacías y el importador borraría lo que hay en la Sheet.
    tango_ok = tango and all(any(k in os.path.basename(r).lower() for r, _ in archivos_de(tango, recursivo=False)) for k in ("cobranzas", "pagos"))
    F.append({"nombre": "tango", "archivos": archivos_de(tango, recursivo=False) if tango_ok else [],
              "cmd": lambda: [PYTHON, os.path.join(BASE_REPO, "lector", "tango.py"), "--carpeta", tango] + H})
    mapa = os.path.join(DRIVE, "Deuda", "Bancos_Navar.xlsx")
    F.append({"nombre": "deuda", "archivos": [(mapa, os.path.getmtime(mapa))] if os.path.exists(mapa) else [],
              "cmd": lambda: [PYTHON, os.path.join(BASE_REPO, "lector", "deuda_bancaria.py"), "--archivo", mapa] + H
                             + (["--bancos", ultimo_con_prefijo("para_pegar_bancos_")] if ultimo_con_prefijo("para_pegar_bancos_") else [])})
    imp = archivos_de(os.path.join(DRIVE, "Impuestos"), recursivo=False)
    imp_nuevo = max(imp, key=lambda x: x[1])[0] if imp else None
    F.append({"nombre": "impuestos", "archivos": imp,
              "cmd": lambda: [PYTHON, os.path.join(BASE_REPO, "lector", "deuda_impositiva.py"), "--archivo", imp_nuevo] + H})
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
        cmd = f["cmd"]()
        if a.simular:
            log("%s: correría  %s" % (n, " ".join(cmd)))
            continue
        log("%s: %d archivo(s) nuevos o cambiados → %s" % (n, len(f["archivos"]), os.path.basename(cmd[1])))
        r = subprocess.run(cmd, cwd=BASE_REPO, capture_output=True, text=True, timeout=1800)
        if r.returncode == 0:
            estado[n] = fa
            log("%s: OK. %s" % (n, (r.stdout.strip().splitlines() or [""])[-1][:200]))
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
