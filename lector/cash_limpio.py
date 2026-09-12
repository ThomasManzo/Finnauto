# -*- coding: utf-8 -*-
"""
lector.cash_limpio — de la planilla "Cash Flow Limpio" al contrato.

PARA QUE
--------
Es la tercera puerta de entrada al motor, al lado del Exportador (Google Sheets
de MAGA) y de lector/extraer.py (una tabla suelta de movimientos):

    Cash Flow Limpio (Excel o Google Sheets bajada como Excel)
        -> ESTE MODULO -> contrato.json -> finauto.py -> el tablero

El "Cash Flow Limpio" es el diseño que armamos para NAVAR (12/09/2026) y que
sirve para cualquier cliente nuevo: LISTAS (Movimientos, Cuentas a Cobrar,
Cuentas a Pagar, Cartera de Cheques, Saldos Bancarios, Deuda Bancaria, Deuda
Impositiva) y un consolidado que se calcula solo. Este modulo lee LAS LISTAS,
nunca el consolidado: el consolidado es una vista, y las vistas se recalculan.

CADA PESO EN UN SOLO LUGAR
--------------------------
El contrato tiene varias listas y las herramientas suman cada una en un lugar
distinto del tablero. Si un mismo pago cae en dos listas, se cuenta dos veces;
si no cae en ninguna, desaparece. Esta es la regla:

    Solapa                       -> lista del contrato
    Movimientos (Egreso)         -> movimientos            (real + proyectado)
    Movimientos (Egreso proy.)   -> egresos_cashflow       (lo futuro sin lista de detalle)
    Movimientos (Ingreso)        -> cobros_previstos
    Cuentas a Cobrar pendiente   -> cuentas_a_cobrar_droguerias
    Cuentas a Pagar pendiente    -> deuda_droguerias
    Cartera de Cheques           -> cartera_cheques        (terceros)
    Cartera de Cheques (propios) -> egresos_cashflow       (vencen y hay que cubrirlos)
    Deuda Impositiva pendiente   -> egresos_cashflow
    Deuda Bancaria (cronograma)  -> egresos_cashflow
    Saldos Bancarios (ultimo dia)-> caja_hoy / caja_por_unidad

Los nombres "droguerias" vienen del contrato v1.2, que nacio con MAGA. Para
otro cliente son "proveedores" y "clientes": el nombre del campo no cambia
porque lo leen 20 herramientas; lo que cambia es el rotulo en pantalla.

QUE TIPO ES CADA MOVIMIENTO
---------------------------
La planilla tiene su propio vocabulario ("Proveedores MP y Logist.", "Hoja
Verde"...). La traduccion a los tipos del catalogo (PROVEEDOR, HOJA_VERDE...)
vive en clientes/<cliente>/catalogo.json -> "mapa_categorias". Si aparece una
categoria que no esta en el mapa, se avisa y el movimiento entra con el tipo
"SIN_MAPEAR": nunca se descarta plata en silencio.

Uso:
    python lector/cash_limpio.py --archivo "NAVAR - Cash Flow.xlsx" --cliente navar
    python lector/cash_limpio.py --archivo cash.xlsx --cliente navar --hoy 2026-09-12
"""

import io
import os
import sys
import json
import argparse
import datetime
from collections import OrderedDict, defaultdict

BASE_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)

try:
    import openpyxl
except ImportError:
    print("Falta openpyxl. Instalalo con:  pip install openpyxl")
    sys.exit(1)

# Nombres de solapa que espera. Se comparan sin acentos ni mayusculas, para que
# "Posición de Deuda" y "Posicion de Deuda" sean lo mismo.
SOLAPAS = {
    "movimientos": "movimientos",
    "cuentas a cobrar": "cobrar",
    "cuentas a pagar": "pagar",
    "cartera de cheques": "cheques",
    "saldos bancarios": "saldos",
    "deuda bancaria": "bancaria",
    "deuda impositiva": "impositiva",
}
MARCA_AGREGADO = "AGREGADO"


# ------------------------------------------------------------------ helpers
def _norm(s):
    import unicodedata
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode()
    return " ".join(s.lower().split())


def _iso(v):
    if isinstance(v, datetime.datetime):
        return v.date().isoformat()
    if isinstance(v, datetime.date):
        return v.isoformat()
    s = str(v or "").strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return datetime.datetime.strptime(s[:10], fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _num(v):
    if v is None or isinstance(v, bool):
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    from lector.borrador import _num as n
    return n(v)


def _txt(v):
    return str(v).strip() if v is not None else ""


def _tabla(ws, fila_enc=1):
    """Lista de dicts {encabezado: valor}, saltando filas vacias.

    Las filas de la planilla tienen formulas guardadas (Saldo Pendiente,
    Estado, Dias de Atraso). Se lee con data_only=True, asi que si el archivo
    viene de Google Sheets o de Excel trae los valores calculados; si alguien
    lo guardo con openpyxl sin calcular, esas celdas vienen vacias y se
    recalculan aca lo minimo (saldo pendiente = total - pagado).
    """
    enc = [_txt(c.value) for c in ws[fila_enc]]
    out = []
    for fila in ws.iter_rows(min_row=fila_enc + 1, values_only=True):
        if not any(v not in (None, "") for v in fila):
            continue
        d = OrderedDict()
        for k, v in zip(enc, fila):
            if k:
                d[k] = v
        out.append(d)
    return out


def _col(d, *nombres):
    """Valor de la primera columna cuyo nombre contenga alguno de los textos."""
    for k, v in d.items():
        kn = _norm(k)
        for n in nombres:
            if _norm(n) in kn:
                return v
    return None


# ------------------------------------------------------------------ lectura
def leer(archivo, cliente, hoy=None):
    hoy = hoy or datetime.date.today().isoformat()
    ruta_cat = os.path.join(BASE_REPO, "clientes", cliente, "catalogo.json")
    with io.open(ruta_cat, encoding="utf-8") as f:
        cat = json.load(f)
    mapa = cat.get("mapa_categorias", {})
    mapa_egr = {k: v for k, v in mapa.get("egresos", {}).items() if not k.startswith("_")}
    mapa_ing = {k: v for k, v in mapa.get("ingresos", {}).items() if not k.startswith("_")}
    # El nombre "lindo" del cliente vive en perfil.json (el catalogo es vocabulario).
    nombre_cliente = cliente
    try:
        from nucleo import config as _config
        nombre_cliente = _config.cargar_perfil(BASE_REPO, cliente).get("cliente", cliente)
    except Exception:
        pass

    wb = openpyxl.load_workbook(archivo, data_only=True, read_only=True)
    hojas = {}
    for n in wb.sheetnames:
        k = SOLAPAS.get(_norm(n))
        if k:
            hojas[k] = wb[n]
    avisos = []
    faltan = [s for s in SOLAPAS.values() if s not in hojas]
    if faltan:
        avisos.append("Faltan solapas: %s (tiene: %s)" % (", ".join(faltan), ", ".join(wb.sheetnames)))

    def _u(v):
        return _txt(v).upper()

    # ---- Movimientos: lo real y lo proyectado, egresos e ingresos
    movimientos, cobros, egresos_cf = [], [], []
    sin_mapear = defaultdict(float)
    for d in _tabla(hojas["movimientos"]) if "movimientos" in hojas else []:
        fecha = _iso(_col(d, "fecha"))
        importe = _num(_col(d, "importe"))
        if not fecha or not importe:
            continue
        tipo_mov = _u(_col(d, "tipo"))               # Ingreso / Egreso
        categoria = _txt(_col(d, "categoria"))
        estado = _u(_col(d, "estado")) or "REAL"    # Real / Proyectado
        estado = "PROYECCION" if estado.startswith("PROY") else "REAL"
        base = {
            "fecha": fecha,
            "unidad": _u(_col(d, "empresa")),
            "banco": _u(_col(d, "banco")),
            "concepto": _txt(_col(d, "concepto")),
            "medio": _txt(_col(d, "medio")),
            "origen": _txt(_col(d, "origen")),
            "estado": estado,
            "observacion": _txt(_col(d, "observ")),
        }
        es_egreso = tipo_mov.startswith("EGR") or (not tipo_mov and importe < 0)
        if es_egreso:
            tipo = mapa_egr.get(categoria)
            if not tipo:
                tipo = "SIN_MAPEAR"
                sin_mapear[categoria] += abs(importe)
            meta = _tipo_meta(cat, tipo)
            m = dict(base, tipo=tipo, categoria_planilla=categoria,
                     categoria=meta.get("categoria", "sin_categoria"),
                     interno=bool(meta.get("interno")), importe=abs(importe), signo="egreso")
            movimientos.append(m)
            # Lo proyectado sin lista de detalle (sueldos, cosecha, estampillas...)
            # es una salida futura que el tablero tiene que ver.
            if estado == "PROYECCION" and fecha >= hoy and not m["interno"]:
                egresos_cf.append({"fecha": fecha, "contraparte": m["concepto"] or categoria,
                                   "importe": abs(importe), "unidad": m["unidad"],
                                   "tipo": tipo, "intercompany": False,
                                   "origen": "Movimientos (proyectado)"})
        else:
            fuente, nat = mapa_ing.get(categoria, ("SIN_MAPEAR", "VARIABLE"))
            if fuente == "SIN_MAPEAR":
                sin_mapear[categoria] += abs(importe)
            cobros.append(dict(base, fuente=fuente, categoria_planilla=categoria,
                               importe=abs(importe), naturaleza=nat, interno=False,
                               efecto="caja"))
    for c, v in sin_mapear.items():
        avisos.append("Categoria sin mapear en catalogo.mapa_categorias: \"%s\" (%s)"
                      % (c, _m(v)))

    # ---- Cuentas a Cobrar: lo pendiente, por vencimiento
    cobrar = []
    for d in _tabla(hojas["cobrar"]) if "cobrar" in hojas else []:
        venc = _iso(_col(d, "vencimiento"))
        total, cobrado = _num(_col(d, "importe total")), _num(_col(d, "cobrado"))
        pend = _col(d, "saldo pendiente")
        pend = _num(pend) if pend not in (None, "") else total - cobrado
        if not venc or pend <= 0:
            continue
        cobrar.append({"fecha": venc, "contraparte": _txt(_col(d, "cliente")), "importe": pend,
                       "unidad": _u(_col(d, "empresa")), "factura": _txt(_col(d, "factura")),
                       "intercompany": False,
                       "estado": "VENCIDA" if venc < hoy else "A VENCER",
                       "agregado": MARCA_AGREGADO in _txt(_col(d, "observ")).upper(),
                       "origen": "Cuentas a Cobrar"})

    # ---- Cuentas a Pagar: lo pendiente, por vencimiento
    deuda = []
    for d in _tabla(hojas["pagar"]) if "pagar" in hojas else []:
        venc = _iso(_col(d, "vencimiento"))
        total, pagado = _num(_col(d, "importe total")), _num(_col(d, "pagado"))
        pend = _col(d, "saldo pendiente")
        pend = _num(pend) if pend not in (None, "") else total - pagado
        if not venc or pend <= 0:
            continue
        categoria = _txt(_col(d, "categoria"))
        deuda.append({"fecha": venc, "contraparte": _txt(_col(d, "proveedor")), "importe": pend,
                      "unidad": _u(_col(d, "empresa")), "tipo": mapa_egr.get(categoria, "PROVEEDOR"),
                      "categoria_planilla": categoria, "factura": _txt(_col(d, "factura")),
                      "intercompany": False, "es_credito": False, "es_saldo": False,
                      "estado": "VENCIDA" if venc < hoy else "A VENCER",
                      "agregado": MARCA_AGREGADO in _txt(_col(d, "observ")).upper(),
                      "origen": "Cuentas a Pagar"})

    # ---- Cartera de Cheques
    cartera = []
    for d in _tabla(hojas["cheques"]) if "cheques" in hojas else []:
        fecha = _iso(_col(d, "fecha pago", "fecha cobro", "pago / cobro"))
        importe = _num(_col(d, "importe"))
        if not fecha or not importe:
            continue
        tipo = _txt(_col(d, "tipo"))
        est = _txt(_col(d, "estado"))
        item = {"fecha": fecha, "importe": abs(importe), "estado": est.upper(),
                "librador": _txt(_col(d, "beneficiario", "librador")),
                "numero": _txt(_col(d, "nro")), "banco": _u(_col(d, "banco")),
                "unidad": _u(_col(d, "empresa")), "propio": _norm(tipo).startswith("propio"),
                "agregado": MARCA_AGREGADO in _txt(_col(d, "observ")).upper(),
                "origen": "Cartera de Cheques"}
        if item["propio"]:
            # Un cheque propio en cartera es plata que sale el dia que se debita.
            if _norm(est) == "en cartera":
                egresos_cf.append({"fecha": fecha, "unidad": item["unidad"], "tipo": "CHEQUE",
                                   "contraparte": "Cheque propio %s a %s" % (item["numero"], item["librador"]),
                                   "importe": item["importe"], "intercompany": False,
                                   "vencido_pendiente": fecha < hoy,
                                   "origen": "Cartera de Cheques (propios)"})
        else:
            cartera.append(item)

    # ---- Deuda Impositiva: cada vencimiento pendiente es una salida rigida
    impositiva = []
    for d in _tabla(hojas["impositiva"]) if "impositiva" in hojas else []:
        venc = _iso(_col(d, "vencimiento"))
        importe = _num(_col(d, "importe"))
        est = _norm(_col(d, "estado"))
        if not venc or not importe or est == "pagado":
            continue
        x = {"fecha": venc, "unidad": _u(_col(d, "empresa")), "tipo": "IMPUESTO",
             "contraparte": "%s %s" % (_txt(_col(d, "impuesto")), _txt(_col(d, "periodo"))),
             "importe": abs(importe), "estado": est, "intercompany": False,
             # Con fecha pasada y sin pagar: es deuda vencida, entra hoy en la curva.
             "vencido_pendiente": venc < hoy,
             "agregado": MARCA_AGREGADO in _txt(_col(d, "observ")).upper(),
             "origen": "Deuda Impositiva"}
        impositiva.append(x)
        egresos_cf.append(x)

    # ---- Deuda Bancaria: dos bloques en la misma solapa (lineas y cronograma)
    lineas, cuotas = [], []
    if "bancaria" in hojas:
        ws = hojas["bancaria"]
        filas = list(ws.iter_rows(values_only=True))
        enc_idx = [i for i, f in enumerate(filas) if f and _norm(f[0]) == "banco"]
        for j, i in enumerate(enc_idx):
            enc = [_txt(c) for c in filas[i]]
            fin = enc_idx[j + 1] - 1 if j + 1 < len(enc_idx) else len(filas)
            es_cronograma = any("cuota" in _norm(e) for e in enc)
            for f in filas[i + 1:fin]:
                if not f or not any(v not in (None, "") for v in f):
                    continue
                d = OrderedDict((k, v) for k, v in zip(enc, f) if k)
                if not _txt(_col(d, "banco")):
                    continue
                if es_cronograma:
                    venc = _iso(_col(d, "vencimiento"))
                    tot = _col(d, "importe total")
                    tot = _num(tot) if tot not in (None, "") else _num(_col(d, "capital")) + _num(_col(d, "interes"))
                    if not venc or not tot or _norm(_col(d, "estado")) == "pagado":
                        continue
                    x = {"fecha": venc, "unidad": _u(_col(d, "empresa")), "tipo": "PRESTAMO",
                         "contraparte": "%s - %s cuota %s" % (_txt(_col(d, "banco")), _txt(_col(d, "linea")),
                                                              _txt(_col(d, "nro cuota"))),
                         "importe": abs(tot), "intercompany": False,
                         "vencido_pendiente": venc < hoy,
                         "agregado": MARCA_AGREGADO in _txt(_col(d, "observ")).upper(),
                         "origen": "Deuda Bancaria (cronograma)"}
                    cuotas.append(x)
                    egresos_cf.append(x)
                else:
                    lineas.append({"banco": _txt(_col(d, "banco")), "unidad": _u(_col(d, "empresa")),
                                   "linea": _txt(_col(d, "linea")),
                                   "capital_vigente": _num(_col(d, "capital vigente")),
                                   "situacion_bcra": _num(_col(d, "situacion")) or None,
                                   "vence": _iso(_col(d, "vto"))})

    # ---- Saldos Bancarios: la foto mas reciente, por banco y por empresa
    saldos, caja_por_unidad, caja_hoy, fecha_saldos = [], defaultdict(float), 0.0, None
    todos = []
    for d in _tabla(hojas["saldos"]) if "saldos" in hojas else []:
        fecha = _iso(_col(d, "fecha"))
        if not fecha:
            continue
        todos.append((fecha, d))
    if todos:
        fecha_saldos = max(f for f, _ in todos)
        for f, d in todos:
            if f != fecha_saldos:
                continue
            v = _num(_col(d, "saldo"))
            u = _u(_col(d, "empresa"))
            saldos.append({"fecha": f, "banco": _u(_col(d, "banco")), "unidad": u,
                           "cuenta": _txt(_col(d, "cuenta")), "saldo": v})
            caja_por_unidad[u] += v
            caja_hoy += v
        if fecha_saldos < hoy:
            avisos.append("El ultimo saldo bancario cargado es del %s (hoy %s): la caja de hoy "
                          "es la de ese dia." % (fecha_saldos, hoy))
    else:
        avisos.append("Saldos Bancarios esta vacio: caja_hoy = 0.")

    agregados = sum(1 for lst in (cobrar, deuda, cartera, impositiva, cuotas) for x in lst if x.get("agregado"))
    if agregados:
        avisos.append("%d filas son AGREGADOS del cash viejo (proyeccion semanal), no detalle real. "
                      "Se reemplazan con los exports de Tango." % agregados)

    contrato = OrderedDict([
        ("contrato_version", "1.2"),
        ("cliente", nombre_cliente),
        ("generado", datetime.datetime.combine(datetime.date.fromisoformat(hoy),
                                               datetime.datetime.now().time()).isoformat(timespec="seconds")),
        ("_origen", {"archivo": os.path.basename(archivo), "lector": "lector/cash_limpio.py",
                     "fecha_saldos": fecha_saldos}),
        ("caja_hoy", caja_hoy),
        ("caja_por_unidad", dict(caja_por_unidad)),
        ("caja_efectivo", 0.0),
        ("saldos", saldos),
        ("movimientos", movimientos),
        ("cobros_previstos", cobros),
        ("egresos_cashflow", sorted(egresos_cf, key=lambda x: x["fecha"])),
        ("cuentas_a_cobrar_droguerias", cobrar),
        ("deuda_droguerias", deuda),
        ("cartera_cheques", cartera),
        ("deuda_impositiva", impositiva),
        ("deuda_bancaria", {"lineas": lineas, "cuotas": cuotas}),
        ("referencias_del_cliente", {}),
        ("avisos", avisos),
    ])
    wb.close()
    return contrato


def _tipo_meta(cat, tipo):
    for t in cat.get("tipos", {}).get("valores", []):
        if t.get("id") == tipo:
            return t
    return {}


def _m(v):
    return "$" + format(int(round(abs(v))), ",d").replace(",", ".")


def imprimir(c):
    L = 74
    print("=" * L)
    print("  CASH FLOW LIMPIO -> CONTRATO   (%s, datos al %s)" % (c["cliente"], c["_origen"]["fecha_saldos"]))
    print("=" * L)
    print("  Caja hoy (sin cheques)   : %s  %s" % (_m(c["caja_hoy"]), {k: _m(v) for k, v in c["caja_por_unidad"].items()}))
    mr = [m for m in c["movimientos"] if m["estado"] == "REAL"]
    mp = [m for m in c["movimientos"] if m["estado"] != "REAL"]
    print("  Movimientos (egresos)    : %d reales, %d proyectados" % (len(mr), len(mp)))
    print("  Cobros previstos         : %d  (%s)" % (len(c["cobros_previstos"]), _m(sum(x["importe"] for x in c["cobros_previstos"]))))
    print("  A cobrar (pendiente)     : %d  (%s)" % (len(c["cuentas_a_cobrar_droguerias"]), _m(sum(x["importe"] for x in c["cuentas_a_cobrar_droguerias"]))))
    print("  A pagar a proveedores    : %d  (%s)" % (len(c["deuda_droguerias"]), _m(sum(x["importe"] for x in c["deuda_droguerias"]))))
    print("  Egresos futuros sin lista: %d  (%s)" % (len(c["egresos_cashflow"]), _m(sum(x["importe"] for x in c["egresos_cashflow"]))))
    print("  Cartera de cheques (3ros): %d  (%s)" % (len(c["cartera_cheques"]), _m(sum(x["importe"] for x in c["cartera_cheques"]))))
    print("  Deuda impositiva pend.   : %d  (%s)" % (len(c["deuda_impositiva"]), _m(sum(x["importe"] for x in c["deuda_impositiva"]))))
    print("  Cuotas bancarias pend.   : %d  (%s)" % (len(c["deuda_bancaria"]["cuotas"]), _m(sum(x["importe"] for x in c["deuda_bancaria"]["cuotas"]))))
    if c["avisos"]:
        print("\n  AVISOS")
        for a in c["avisos"]:
            print("   . " + a)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Cash Flow Limpio -> contrato.json")
    ap.add_argument("--archivo", required=True)
    ap.add_argument("--cliente", required=True)
    ap.add_argument("--hoy", help="AAAA-MM-DD (default: hoy)")
    ap.add_argument("--salida")
    args = ap.parse_args()

    c = leer(args.archivo, args.cliente, args.hoy)
    imprimir(c)
    salida = args.salida or os.path.join(BASE_REPO, "clientes", args.cliente,
                                         "contrato_%s.json" % (args.hoy or datetime.date.today().isoformat()))
    with io.open(salida, "w", encoding="utf-8") as f:
        f.write(json.dumps(c, ensure_ascii=False, indent=2))
        f.write(u"\n")
    print("\n  Contrato: %s" % salida)
    print("  Siguiente: python finauto.py --contrato %s --cliente %s" % (salida, args.cliente))


if __name__ == "__main__":
    main()
