# -*- coding: utf-8 -*-
"""
ingestas.tango_live — baja las consultas de Tango Live por su API y deja los Excel en la
carpeta de Drive que corresponde, con el nombre que el vigilante y lector/tango.py esperan.
Reemplaza el "entrar a Live, exportar, renombrar, arrastrar" de todos los días.

QUÉ BAJA (perfil.json → "tango_live")
    consultas:  cobranzas · pagos · cheques_terceros · cheques_propios  (número de proceso de Live)
    empresas:   A = 13 (NAVAR SA) · AA = ? (NAVAR SA Otros)
    → "Cuentas a cobrar/A cobranzas <hoy>.xlsx", "Cuentas a pagar/AA pagos <hoy>.xlsx",
      "Cheques/A cheques terceros <hoy>.xlsx", "Cheques/A cheques propios <hoy>.xlsx" ...

CÓMO LLAMA A LIVE
    GET <url>/Api/GetApiLiveQueryData/{process}/{fromDate}/{toDate}/{pageSize}/{pageIndex}/{customQuery}
    headers: ApiAuthorization: <token>   Company: <id de empresa>
    El token es POR USUARIO: se genera una vez desde el usuario "finauto" (Live → cualquier
    consulta → Apertura → API → Obtener token) y se guarda en el llavero de la máquina:
        python setup_credenciales.py --cliente navar --banco tango_live
        (usuario: finauto · clave: el token)
    Nunca en un archivo.

    Lo que NO sabemos hasta tener el token (por eso existe --probar): el formato exacto de las
    fechas en la URL y la forma del JSON que devuelve. --probar baja 5 filas de una consulta y
    muestra la estructura cruda; con eso se ajustan FORMATO_FECHA y _filas_de() una sola vez.

USO
    python ingestas/tango_live.py --cliente navar                 # baja todo lo configurado
    python ingestas/tango_live.py --cliente navar --probar cobranzas --empresa A
    python ingestas/tango_live.py --cliente navar --simular       # dice qué haría
    python ingestas/tango_live.py --cliente navar --destino <carpeta>   # en vez del Drive
"""

import os
import sys
import json
import datetime
import argparse
import urllib.request
import urllib.error

BASE_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)

from nucleo import credenciales as _cred
from ingestas.drive_local import carpeta_datos

# Dónde va cada consulta y cómo se llama el archivo (lo mismo que espera lector/tango.py).
DESTINO = {
    "cobranzas":        ("Cuentas a cobrar", "%s cobranzas %s.xlsx"),
    "pagos":            ("Cuentas a pagar",  "%s pagos %s.xlsx"),
    "cheques_terceros": ("Cheques",          "%s cheques terceros %s.xlsx"),
    "cheques_propios":  ("Cheques",          "%s cheques propios %s.xlsx"),
    "movimientos_tesoreria": ("Tesorería AA", "%s movimientos tesoreria %s.xlsx"),   # solo AA: la operación en efectivo
}
SOLO_EMPRESA = {"movimientos_tesoreria": "AA"}      # consultas que se bajan para una sola empresa
FORMATO_FECHA = "%Y%m%d"          # a confirmar con --probar
DESDE, HASTA = "20000101", "20301231"
PAGINA = 5000


def log(msg):
    print("%s  %s" % (datetime.datetime.now().strftime("%H:%M:%S"), msg))


def perfil(cliente):
    with open(os.path.join(BASE_REPO, "clientes", cliente, "perfil.json"), encoding="utf-8") as f:
        p = json.load(f)
    cfg = p.get("tango_live")
    if not cfg:
        sys.exit("perfil.json no tiene la sección 'tango_live'")
    return cfg


def token(cliente):
    _, tok = _cred.cargar(BASE_REPO, cliente, "tango_live")
    return tok


def llamar(cfg, tok, empresa_id, proceso, pagina=0, tam=PAGINA, custom=""):
    url = "%s/Api/GetApiLiveQueryData/%s/%s/%s/%d/%d/%s" % (
        cfg["url"].rstrip("/"), proceso, DESDE, HASTA, tam, pagina, custom or cfg.get("custom_query", "-"))
    req = urllib.request.Request(url, headers={
        "ApiAuthorization": tok, "Company": str(empresa_id), "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            cuerpo = r.read().decode("utf-8", errors="replace")
            return r.status, url, cuerpo
    except urllib.error.HTTPError as e:
        return e.code, url, e.read().decode("utf-8", errors="replace")


def _filas_de(cuerpo):
    """Encuentra la lista de filas (dicts) dentro de lo que devuelve Live, sea cual sea la envoltura."""
    try:
        j = json.loads(cuerpo)
    except ValueError:
        return None
    if isinstance(j, list):
        return j
    if isinstance(j, dict):
        for k in ("data", "Data", "rows", "Rows", "items", "Items", "result", "Result", "value"):
            if isinstance(j.get(k), list):
                return j[k]
        for v in j.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
            if isinstance(v, dict):
                sub = _filas_de(json.dumps(v))
                if sub is not None:
                    return sub
    return None


def bajar(cfg, tok, empresa, proceso):
    filas, pagina = [], 0
    while True:
        st, url, cuerpo = llamar(cfg, tok, cfg["empresas"][empresa], proceso, pagina)
        if st != 200:
            raise RuntimeError("Live devolvió %s en %s: %s" % (st, url, cuerpo[:300]))
        parte = _filas_de(cuerpo)
        if parte is None:
            raise RuntimeError("no encontré filas en la respuesta de %s: %s" % (url, cuerpo[:300]))
        filas += parte
        if len(parte) < PAGINA:
            break
        pagina += 1
    return filas


def escribir_xlsx(filas, ruta):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    if not filas:
        ws.append(["(sin filas)"])
    else:
        cols = list(filas[0].keys())
        for f in filas[1:]:
            for k in f.keys():
                if k not in cols:
                    cols.append(k)
        ws.append(cols)
        for f in filas:
            fila = []
            for c in cols:
                v = f.get(c)
                if isinstance(v, str) and len(v) >= 10 and v[4:5] == "-" and v[7:8] == "-":
                    try:
                        v = datetime.datetime.fromisoformat(v[:19])
                    except ValueError:
                        pass
                fila.append(v)
            ws.append(fila)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    tmp = ruta + ".parte"
    wb.save(tmp)
    os.replace(tmp, ruta)      # aparece de golpe, entero: el vigilante nunca ve un archivo a medias


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cliente", default="navar")
    ap.add_argument("--hoy", default=datetime.date.today().isoformat())
    ap.add_argument("--destino", default=None, help="carpeta raíz (default: NAVAR - Datos en el Drive montado)")
    ap.add_argument("--probar", default=None, help="baja 5 filas de esa consulta y muestra la estructura cruda")
    ap.add_argument("--empresa", default="A")
    ap.add_argument("--simular", action="store_true")
    a = ap.parse_args()
    cfg = perfil(a.cliente)
    raiz = a.destino or carpeta_datos()
    if not raiz:
        sys.exit("no encuentro la carpeta de Drive montada; pasá --destino o fijá FINAUTO_DRIVE")

    if a.probar:
        tok = token(a.cliente)
        proceso = cfg["consultas"].get(a.probar)
        if not proceso:
            sys.exit("la consulta %s no tiene número de proceso en perfil.json" % a.probar)
        st, url, cuerpo = llamar(cfg, tok, cfg["empresas"][a.empresa], proceso, 0, 5)
        print("GET", url); print("HTTP", st); print(cuerpo[:3000])
        filas = _filas_de(cuerpo)
        print("\nfilas encontradas:", None if filas is None else len(filas))
        if filas:
            print("columnas:", list(filas[0].keys()))
        return

    pendientes = [(e, c, p) for e, eid in cfg["empresas"].items() if eid
                  for c, p in cfg["consultas"].items() if p and not (e == "AA" and c == "cheques_propios")
                  and (c not in SOLO_EMPRESA or SOLO_EMPRESA[c] == e)]
    faltan = [c for c, p in cfg["consultas"].items() if not p] + [e for e, eid in cfg["empresas"].items() if not eid]
    if faltan:
        log("sin número todavía (se saltean): %s" % ", ".join(faltan))
    if a.simular:
        for e, c, p in pendientes:
            carpeta, nombre = DESTINO[c]
            log("bajaría %s/%s (proceso %s, empresa %s)" % (carpeta, nombre % (e, a.hoy), p, cfg["empresas"][e]))
        return
    tok = token(a.cliente)
    ok = 0
    for e, c, p in pendientes:
        carpeta, nombre = DESTINO[c]
        ruta = os.path.join(raiz, carpeta, nombre % (e, a.hoy))
        try:
            filas = bajar(cfg, tok, e, p)
            escribir_xlsx(filas, ruta)
            log("%s: %d filas → %s" % (nombre % (e, a.hoy), len(filas), os.path.relpath(ruta, raiz)))
            ok += 1
        except Exception as ex:
            log("%s: FALLÓ: %s" % (nombre % (e, a.hoy), ex))
    log("listo: %d de %d" % (ok, len(pendientes)))
    return 0 if ok == len(pendientes) else 1


if __name__ == "__main__":
    sys.exit(main())
