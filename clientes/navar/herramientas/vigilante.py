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
    Impuestos/               la planilla de vencimientos impositivos (el archivo más nuevo manda)
                             → lector/deuda_impositiva.py
    Tesorería AA/            Tango: movimientos de tesorería de AA (la operación en efectivo), el más nuevo
                             → lector/tesoreria_aa.py → Movimientos (Origen "Tango AA")
    _para la Sheet/          lo que generan los lectores (para_pegar_*.xlsx y resumen_*.md).
                             De acá los levanta el disparador de la Sheet. Nadie toca esta carpeta.

CÓMO SABE QUE HAY ALGO NUEVO
    Guarda en clientes/navar/.run/vigilante.json una firma de cada fuente (archivos + fecha de
    modificación). Si la firma cambió y el archivo más nuevo tiene más de 2 minutos (para que
    Drive termine de bajarlo), corre el lector. Si el lector falla, lo anota y lo vuelve a
    intentar en la próxima pasada. Todo queda en clientes/navar/privado/vigilante.log.

CÓMO CORRE
    Cada 15 minutos: en la Mac por launchd (instalar_vigilante.sh); en la notebook de NAVAR por
    el Programador de tareas de Windows (instalar_vigilante.ps1). Una sola máquina a la vez lo
    tiene que correr: cuando pase a la notebook, en la Mac se desinstala. A mano:
    python vigilante.py [--forzar bancos|tango|deuda|impuestos] [--simular]
"""

import os
import sys
import json
import time
import glob
import argparse
import datetime
import subprocess

# En Windows la consola es cp1252 y los lectores imprimen "→": sin esto, cada lector muere con
# UnicodeEncodeError al terminar. Se fuerza UTF-8 acá y en los procesos hijos.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

AQUI = os.path.dirname(os.path.abspath(__file__))
BASE_REPO = os.path.abspath(os.path.join(AQUI, "..", "..", ".."))
sys.path.insert(0, BASE_REPO)
from ingestas.drive_local import carpeta_datos

PYTHON = sys.executable                       # el mismo Python con el que corre esto (Mac o Windows)
DRIVE = carpeta_datos("NAVAR - Datos")        # el Drive montado en esta máquina (o FINAUTO_DRIVE)
ESTADO = os.path.join(BASE_REPO, "clientes", "navar", ".run", "vigilante.json")
LOG = os.path.join(BASE_REPO, "clientes", "navar", "privado", "vigilante.log")
ESPERA_SEG = 120          # un archivo recién bajado por Drive puede estar a medias
IGNORAR = ("para_pegar", "resumen_", "~$", ".", "desktop.ini", "Thumbs.db")     # ocultos y basura de Windows/Drive
EXTENSIONES = (".pdf", ".xls", ".xlsx", ".csv")                                     # lo único que es un dato
SALIDA = os.path.join(DRIVE or "", "_para la Sheet")
CARPETAS_TANGO = ("Cuentas a cobrar", "Cuentas a pagar", "Cheques")
STAGING_TANGO = os.path.join(BASE_REPO, "clientes", "navar", ".run", "tango_ultimo")

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
            if n.lower().startswith(tuple(x.lower() for x in IGNORAR)) or not n.lower().endswith(EXTENSIONES):
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
    try:
        return {ws.title: sum(1 for r in ws.iter_rows(min_row=2, values_only=True) if any(v is not None for v in r)) for ws in wb.worksheets}
    finally:
        wb.close()


def control_contra_anterior(nuevo):
    """Compara el para_pegar nuevo con el último publicado del mismo tipo. Si alguna solapa
    perdió más de la mitad de las filas, algo cambió en el export (un filtro, una consulta mal
    guardada) y NO se publica: el importador borraría de la Sheet lo que el archivo no trae.
    También retiene si crece a más del triple y suma más de 100 filas.
    Devuelve None si está bien, o el texto del problema."""
    prefijo = os.path.basename(nuevo).rsplit("_", 1)[0] + "_"          # para_pegar_bancos_
    previos = sorted(r for r in glob.glob(os.path.join(SALIDA, prefijo + "*.xlsx")) if r != nuevo)
    if not previos:
        return None
    antes, ahora = _filas_por_solapa(previos[-1]), _filas_por_solapa(nuevo)
    problemas = []
    for solapa in sorted(antes.keys() | ahora.keys()):
        n_antes = antes.get(solapa, 0)
        n_ahora = ahora.get(solapa, 0)
        if n_antes >= 20 and n_ahora < n_antes * 0.5:
            problemas.append("%s: %d filas antes, %d ahora" % (solapa, n_antes, n_ahora))
        # Las listas chicas pueden duplicarse normalmente. Más del triple y 100 filas
        # extra merece revisar el export antes de pisar el cash, incluso desde cero.
        if n_ahora > n_antes * 3 and n_ahora - n_antes > 100:
            problemas.append("%s: crecimiento desmedido, %d filas antes, %d ahora "
                             "(más del triple y más de 100 filas extra)" % (solapa, n_antes, n_ahora))
    return "; ".join(problemas) or None


def conservar_bancos_con_errores(nuevo):
    """Recupera del último publicado lo que hoy no se pudo releer.

    La Sheet reemplaza todos los extractos juntos. Sin este respaldo, saltear un
    banco borraría su historia o frenaría a los demás por el control de achicamiento.
    Las fechas originales se conservan: un saldo viejo no pasa a ser saldo de hoy.
    """
    import re
    from collections import Counter
    import openpyxl
    from lector.extractos import BANCOS

    if not os.path.basename(nuevo).startswith("para_pegar_bancos_"):
        return
    resumen = nuevo.replace("para_pegar_bancos_", "resumen_bancos_").rsplit(".", 1)[0] + ".md"
    if not os.path.exists(resumen):
        return
    with open(resumen, encoding="utf-8") as f:
        texto = f.read()
    claves = set(re.findall(r"^- no pude leer ([^/\\]+)[/\\]", texto, re.M))
    bancos = {BANCOS[k]["nombre"] for k in claves if k in BANCOS}
    if not bancos:
        return
    previos = sorted(glob.glob(os.path.join(SALIDA, "para_pegar_bancos_*.xlsx")))
    if not previos:
        log("bancos: sin publicación anterior para recuperar los bancos con errores: " + ", ".join(sorted(bancos)))
        return
    wb = openpyxl.load_workbook(nuevo)
    anterior = openpyxl.load_workbook(previos[-1], data_only=True)
    recuperadas = 0
    try:
        for nombre in ("Saldos Bancarios", "Movimientos"):
            ws, previa = wb[nombre], anterior[nombre]
            enc = [c.value for c in ws[1]]
            enc_previa = [c.value for c in previa[1]]
            es_saldo = nombre == "Saldos Bancarios"

            def clave(fila):
                fecha = fila.get("Fecha")
                if isinstance(fecha, datetime.datetime):
                    fecha = fecha.date()
                if es_saldo:
                    return (fecha, fila.get("Empresa"), fila.get("Banco"), fila.get("Cuenta / Nro"))
                return (fecha, fila.get("Empresa"), fila.get("Banco / Cuenta"), fila.get("Importe"))

            # Se cuenta cada repetición: dos pagos iguales pueden ser dos pagos reales.
            presentes = Counter(clave(dict(zip(enc, r))) for r in ws.iter_rows(min_row=2, values_only=True))
            vistos = Counter()
            for r in previa.iter_rows(min_row=2, values_only=True):
                fila = dict(zip(enc_previa, r))
                banco = str(fila.get("Banco") if es_saldo else fila.get("Banco / Cuenta") or "").split(" ")[0]
                if banco not in bancos:
                    continue
                k = clave(fila)
                vistos[k] += 1
                if vistos[k] <= presentes[k]:
                    continue
                ws.append([fila.get(c) for c in enc])
                recuperadas += 1
                for c in ws[ws.max_row]:
                    if isinstance(c.value, (datetime.datetime, datetime.date)):
                        c.number_format = "DD/MM/YYYY"
            if not es_saldo:
                for i in range(2, ws.max_row + 1):
                    ws.cell(i, enc.index("ID") + 1, i - 1)
        wb.save(nuevo)
    finally:
        wb.close()
        anterior.close()
    aviso = ("bancos: %d filas recuperadas del último publicado para %s; conservan su fecha original. "
             "Los archivos ilegibles siguen pendientes de revisión." % (recuperadas, ", ".join(sorted(bancos))))
    with open(resumen, "a", encoding="utf-8") as f:
        f.write("\n" + aviso + "\n")
    log(aviso)


def mover_salidas(desde):
    """Lleva lo que generó un lector (para_pegar_*, resumen_*) a _para la Sheet, salvo que el
    control contra el anterior diga que algo se achicó o creció de golpe: entonces va a _retenido."""
    import shutil
    os.makedirs(SALIDA, exist_ok=True)
    retenido = None
    for r in glob.glob(os.path.join(desde, "para_pegar_*.xlsx")):
        conservar_bancos_con_errores(r)
        problema = control_contra_anterior(r)
        if problema:
            # Un archivo sano no levanta la retención de otro que falló en la misma tanda.
            retenido = "; ".join(filter(None, (retenido, problema)))
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
    tes = archivos_de(os.path.join(DRIVE, "Tesoreria AA"), recursivo=False) or archivos_de(os.path.join(DRIVE, "Tesorería AA"), recursivo=False)
    tes_nuevo = max(tes, key=lambda x: x[1])[0] if tes else None
    F.append({"nombre": "tesoreria_aa", "archivos": tes,
              "cmd": lambda: [PYTHON, os.path.join(BASE_REPO, "lector", "tesoreria_aa.py"), "--archivo", tes_nuevo] + H,
              "salidas": lambda: os.path.dirname(tes_nuevo)})
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

    if not DRIVE or not os.path.isdir(DRIVE):
        log("no encuentro 'NAVAR - Datos' en el Drive montado (¿Google Drive para escritorio está corriendo? ¿o fijar FINAUTO_DRIVE?)")
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
        r = subprocess.run(cmd, cwd=BASE_REPO, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800, env=os.environ.copy())
        if r.returncode == 0:
            for linea in r.stdout.splitlines():
                if linea.startswith("- no pude leer ") or "REVISAR saldo:" in linea:
                    log("%s: %s" % (n, linea))
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
    # Si hubo actividad, comparte el log incluso cuando la pasada termina con un error.
    # La simulación no publica nada y una falla de Drive no tapa el error del lector.
    try:
        log_antes = os.stat(LOG).st_mtime_ns if os.path.exists(LOG) else None
    except OSError:
        log_antes = None
    try:
        sys.exit(main())
    finally:
        try:
            if "--simular" not in sys.argv and DRIVE and os.path.isdir(DRIVE) and os.path.exists(LOG):
                if os.stat(LOG).st_mtime_ns != log_antes:
                    import shutil
                    os.makedirs(SALIDA, exist_ok=True)
                    shutil.copyfile(LOG, os.path.join(SALIDA, "vigilante.log"))
        except Exception as e:
            print("No pude copiar vigilante.log a Drive: %s" % e)
