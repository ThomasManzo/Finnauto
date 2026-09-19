# -*- coding: utf-8 -*-
"""
lector.deuda_bancaria — del mapa de deuda financiera a la solapa "Deuda Bancaria".

PARA QUE
--------
El 18/09/2026 llegó `Bancos_Navar.xlsx`: una planilla "DEUDA FINANCIERA NAVAR" con
cada préstamo, descubierto, tarjeta y descuento de cheques, banco por banco, con
saldo, cuota, situación BCRA y un texto de Observaciones que dice cuántas cuotas
se pagaron, cuál viene, cuál está impaga y cuándo vence la última. Es el mapa de
deuda que faltaba. Este módulo lo lee y arma las dos partes de la solapa:

    A) Líneas de Crédito     una fila por producto: capital vigente, tasa, situación
    B) Cronograma (cuotas)   una fila por cuota pendiente: vencida (impaga) o futura

La regla que pidió Thomas (17/09): la deuda es un STOCK por concepto que no toca la
caja de hoy; lo que sí entra en la proyección son los COMPROMISOS: las cuotas con
fecha. Por eso el cronograma es lo que importa para adelante, y las líneas para
saber cuánto se debe en total.

CÓMO SE ARMA EL CRONOGRAMA
--------------------------
De la planilla se saca: valor de cuota, cantidad de cuotas, cuántas se pagaron, la
próxima (número, fecha, importe) y las impagas. Con eso:
  - las impagas van con su vencimiento original (hacia atrás, mes a mes desde la
    próxima) y Estado "Pendiente": son deuda vencida;
  - la próxima va con la fecha e importe que dice el banco;
  - las que siguen se ESTIMAN: misma cuota, mismo día de cada mes, hasta la última.
    Quedan marcadas "estimada" en Observaciones. Cuando el banco mande la tabla de
    amortización, se pisan.
Si se pasa `--bancos para_pegar_bancos_<fecha>.xlsx`, se cruza con los movimientos
reales: una cuota "impaga" que aparece pagada en el extracto después de la fecha de
la planilla se marca "Pagado" (pasó con el Nación el 14/09: pagaron la tarjeta y la
cuota de la reprogramación con un descubierto nuevo de $100 M).

LO QUE NO ES COMPROMISO
-----------------------
  - Descubiertos: el saldo usado YA está en la caja (es el saldo negativo de la
    cuenta corriente). Van en Líneas con esa aclaración y NO generan cuotas.
  - Descuento de cheques: el banco cobra el cheque al vencimiento; solo vuelve a
    NAVAR si rebota. Va en Líneas, sin cuotas.
  - Tarjetas: el resumen se paga en el vencimiento. Va en Líneas; si dice "impago"
    o "atraso", se agrega una cuota vencida por el saldo.

Uso:
    python lector/deuda_bancaria.py --archivo clientes/navar/privado/bancos/Bancos_Navar.xlsx --cliente navar --hoy 2026-09-18
    python lector/deuda_bancaria.py ... --bancos clientes/navar/privado/bancos/para_pegar_bancos_2026-09-18.xlsx
    python lector/deuda_bancaria.py ... --sheet "clientes/navar/privado/NAVAR - Cash Flow (con bancos 2026-09-18).xlsx"
"""

import os
import re
import sys
import argparse
import datetime
import unicodedata
from collections import OrderedDict, defaultdict

BASE_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)

import openpyxl

# Marca en Observaciones de todo lo que sale de acá: el importador de la Sheet
# borra lo que la tenga antes de volver a cargar.
MARCA = "Mapa deuda"

ENC_LINEAS = ["Banco", "Empresa", "Linea / Producto", "Capital Original", "Capital Vigente", "Tasa (TNA)",
              "Fecha Otorgamiento", "Fecha Vto. Final", "Situacion BCRA", "Observaciones"]
ENC_CUOTAS = ["Banco", "Empresa", "Linea / Producto", "Nro Cuota", "Fecha Vencimiento", "Importe Capital",
              "Importe Interes", "Importe Total Cuota", "Estado", "Observaciones"]
COLS_CON_FORMULA = {"Importe Total Cuota"}

# Nombre corto del banco, como está en Saldos Bancarios / Movimientos.
BANCOS = [("FRANCES", "BBVA"), ("BBVA", "BBVA"), ("NACION", "NACION"), ("GALICIA", "GALICIA"),
          ("MACRO", "MACRO"), ("CORRIENTES", "CORRIENTES")]


# ------------------------------------------------------------------ helpers
def _norm(s):
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode()
    return " ".join(s.upper().split())


def _m(v):
    return ("-" if v < 0 else "") + "$" + format(int(round(abs(v))), ",d").replace(",", ".")


def _num_ar(s):
    """'$15.388.715,94' -> 15388715.94"""
    s = re.sub(r'[^\d,.-]', '', str(s))
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif s.count(".") > 1 or re.search(r'\.\d{3}$', s):     # 17.400.000 -> sin decimales
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def _fecha(v):
    """Acepta datetime, 'dd/mm/yy', 'd/m/yyyy'."""
    if isinstance(v, datetime.datetime):
        return v.date()
    if isinstance(v, datetime.date):
        return v
    m = re.search(r'(\d{1,2})/(\d{1,2})/(\d{2,4})', str(v or ""))
    if not m:
        return None
    d, mo, a = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if a < 100:
        a += 2000
    try:
        return datetime.date(a, mo, d)
    except ValueError:
        return None


def _mas_meses(fecha, n):
    """Misma fecha n meses después (o antes, n negativo); si el mes es más corto, el último día."""
    import calendar
    mes0 = fecha.month - 1 + n
    a, mo = fecha.year + mes0 // 12, mes0 % 12 + 1
    return datetime.date(a, mo, min(fecha.day, calendar.monthrange(a, mo)[1]))


def _banco_corto(nombre):
    n = _norm(nombre)
    for clave, corto in BANCOS:
        if clave in n:
            return corto
    return nombre.strip()


def _tipo(producto):
    p = _norm(producto)
    if "DESCUBIERTO" in p or "ACUERDO EN CTA" in p:
        return "descubierto"
    if "TARJETA" in p:
        return "tarjeta"
    if "DESC." in p or "DESCUENTO" in p or "VENTA VALORES" in p:
        return "descuento"
    if "HIPOTECA" in p:
        return "hipoteca"
    return "prestamo"


# ------------------------------------------------------------------ lectura
def leer_mapa(ruta):
    """-> lista de productos (dict) tal cual la planilla, con el banco heredado hacia abajo
    y lo que se pudo sacar del texto de Observaciones."""
    wb = openpyxl.load_workbook(ruta, data_only=True)
    ws = wb.active
    filas = list(ws.iter_rows(values_only=True))
    titulo = next((str(f[0]) for f in filas if f and f[0] and "DEUDA" in _norm(f[0])), "")
    enc_i = next(i for i, f in enumerate(filas) if f and _norm(f[0]) == "BANCO")
    enc = [_norm(c) for c in filas[enc_i]]

    def col(f, nombre):
        for i, e in enumerate(enc):
            if e.startswith(nombre):
                return f[i] if i < len(f) else None
        return None

    productos, banco = [], None
    for f in filas[enc_i + 1:]:
        if not f or not any(v not in (None, "") for v in f):
            continue
        if col(f, "BANCO"):
            if _norm(col(f, "BANCO")) == "TOTAL":
                break
            banco = str(col(f, "BANCO"))
        producto = col(f, "PRODUCTO")
        if not producto:
            continue          # fila de subtotal o de nota suelta
        obs = str(col(f, "OBSERVACIONES") or "")
        saldo = col(f, "SALDO")
        p = {"banco": banco, "banco_corto": _banco_corto(banco), "producto": str(producto).strip(),
             "tipo": _tipo(producto), "valor_original": col(f, "VALOR ORIGINAL"), "alta": _fecha(col(f, "FECHA DE ALTA")),
             "cuotas": int(col(f, "CANT CUOTAS")) if isinstance(col(f, "CANT CUOTAS"), (int, float)) else None,
             "garantia": col(f, "GARANTIA"), "tna": col(f, "TNA"),
             "saldo": abs(float(saldo)) if isinstance(saldo, (int, float)) else None,
             "valor_cuota": float(col(f, "VALOR CUOTA")) if isinstance(col(f, "VALOR CUOTA"), (int, float)) else None,
             "situacion": int(col(f, "SITUACION")) if isinstance(col(f, "SITUACION"), (int, float)) else None,
             "obs": obs}
        p.update(_leer_observaciones(obs))
        productos.append(p)
    return {"titulo": titulo, "productos": productos, "archivo": os.path.basename(ruta)}


def _leer_observaciones(obs):
    """Lo que el texto libre dice sobre las cuotas."""
    o = " ".join(obs.split())
    out = {"proxima": None, "impagas": [], "pagadas": None, "vto_final": None, "atraso_dias": None,
           "solo_interes": None, "falta_importe": "FALTA IMPORTE" in o.upper() or "FALTA SALDO" in o.upper()}
    m = re.search(r'(?:Pr[oó]xima cuota|[UÚ]ltima cuota|Cuota)\s+(\d+)\s+vto\.?\s+(\d{1,2}/\d{1,2}/\d{4})\s+por\s+\$\s?([\d.,]+)', o)
    if m:
        out["proxima"] = {"nro": int(m.group(1)), "fecha": _fecha(m.group(2)), "importe": _num_ar(m.group(3))}
    m = re.search(r'impagas? cuotas?\s+([\d,\s y]+?)(?:\.|;|$)', o, re.I)
    if m:
        out["impagas"] = [int(x) for x in re.findall(r'\d+', m.group(1))]
    m = re.search(r'Cuota\s+(\d+)\s+IMPAGA\s+\$\s?([\d.,]+)\s+\(vto\.?\s+(\d{1,2}/\d{1,2}/\d{4})\)', o)
    if m:
        out["impagas"] = [int(m.group(1))]
        out["impaga_detalle"] = {"nro": int(m.group(1)), "importe": _num_ar(m.group(2)), "fecha": _fecha(m.group(3))}
    for pat in (r'(?:Pagas|Canceladas?|Cobradas)\s+(\d+)\s+de\s+(\d+)', r'(\d+)\s+de\s+(\d+)\s+cuotas pagadas'):
        m = re.search(pat, o, re.I)
        if m:
            out["pagadas"] = int(m.group(1))
            break
    m = re.search(r'(?:Vto\.?\s+final|Vencimiento final|[UÚ]ltima cuota)\s+(\d{1,2}/\d{1,2}/\d{4})', o)
    if m:
        out["vto_final"] = _fecha(m.group(1))
    m = re.search(r'Atraso\s+(\d+)\s+d[ií]as', o, re.I)
    if m:
        out["atraso_dias"] = int(m.group(1))
    m = re.search(r'(\d+)\s+cuotas de s[oó]lo inter[eé]s\s*\+\s*(\d+)\s+de capital\s*\(\$\s?([\d.,]+)\s*c/u\)', o, re.I)
    if m:
        out["solo_interes"] = {"n_interes": int(m.group(1)), "n_capital": int(m.group(2)), "capital_cuota": _num_ar(m.group(3))}
    return out


# ------------------------------------------------------------------ armado
def _fechas_del_mapa(titulo):
    """'... Frances, Galicia y Macro al 31/8/2026; Banco de Corrientes y Banco Nación al 9/9/2026'
    -> {BBVA: 31/08, GALICIA: 31/08, MACRO: 31/08, CORRIENTES: 09/09, NACION: 09/09}"""
    out = {}
    for tramo in re.split(r'[;.]', titulo):
        m = re.search(r'al (\d{1,2}/\d{1,2}/\d{4})', tramo)
        if not m:
            continue
        for clave, corto in BANCOS:
            if clave in _norm(tramo):
                out[corto] = _fecha(m.group(1))
    return out


def armar(mapa, hoy, empresa="A", pagos_reales=None):
    """-> {"lineas": [...], "cuotas": [...], "avisos": [...]}"""
    fechas = _fechas_del_mapa(mapa["titulo"])
    fecha_gral = max(fechas.values()) if fechas else None
    origen = "%s · %s%s" % (MARCA, mapa["archivo"], (" (datos al %s)" % fecha_gral.strftime("%d/%m/%Y")) if fecha_gral else "")
    lineas, cuotas, avisos = [], [], []
    for p in mapa["productos"]:
        p["fecha_mapa"] = fechas.get(p["banco_corto"], fecha_gral)
        tipo = p["tipo"]
        nota = []
        if tipo == "descubierto":
            nota.append("YA ESTA EN LA CAJA: es el saldo negativo de la cuenta corriente, no sumar como deuda aparte")
        elif tipo == "descuento":
            nota.append("cheques descontados: el banco los cobra al vencimiento, solo vuelve si rebota. No genera cuota")
        elif tipo == "tarjeta":
            nota.append("resumen de tarjeta: se paga al vencimiento")
        if p["falta_importe"]:
            nota.append("FALTA IMPORTE en el mapa")
        if tipo == "prestamo" and not p["valor_cuota"] and p["saldo"] and p["cuotas"]:
            _estimar_cuota(p, avisos)
            nota.append("cuota ESTIMADA: el mapa no trae valor de cuota, se calculó con saldo y tasa")
        if p["atraso_dias"]:
            nota.append("atraso %d días" % p["atraso_dias"])
        if (p["banco_corto"], tipo) in NOTAS_PRISCILLA:
            nota.append(NOTAS_PRISCILLA[(p["banco_corto"], tipo)])
        lineas.append(OrderedDict([
            ("Banco", p["banco_corto"]), ("Empresa", empresa), ("Linea / Producto", p["producto"]),
            ("Capital Original", p["valor_original"] if isinstance(p["valor_original"], (int, float)) else None),
            ("Capital Vigente", p["saldo"]), ("Tasa (TNA)", p["tna"]), ("Fecha Otorgamiento", p["alta"]),
            ("Fecha Vto. Final", p["vto_final"]), ("Situacion BCRA", p["situacion"]),
            ("Observaciones", origen + (" · " + " · ".join(nota) if nota else "") + " · " + p["obs"]),
        ]))

        # ---- cuotas
        if tipo == "prestamo" and p["valor_cuota"] and p["cuotas"]:
            cuotas += _cronograma(p, hoy, empresa, origen, avisos)
        elif tipo == "tarjeta" and _diferidas(p):
            # Priscilla (18/09): las "operaciones diferidas" de la AgroNación son pagos a
            # proveedores hechos con la tarjeta que van a entrar en los próximos resúmenes.
            # No se sabe en cuántos: se reparten en 3 resúmenes (vto. 28 de cada mes),
            # marcados ESTIMADO, hasta que llegue el detalle de la tarjeta.
            total = _diferidas(p)
            for k in range(3):
                venc = _mas_meses(datetime.date(2026, 9, 28), k)
                cuotas.append(OrderedDict([
                    ("Banco", p["banco_corto"]), ("Empresa", empresa), ("Linea / Producto", p["producto"]),
                    ("Nro Cuota", "resumen %d/3" % (k + 1)), ("Fecha Vencimiento", venc),
                    ("Importe Capital", round(total / 3, 2)), ("Importe Interes", 0), ("Importe Total Cuota", None),
                    ("Estado", "Pendiente"),
                    ("Observaciones", origen + " · ESTIMADO: operaciones diferidas por %s (pagos a proveedores con la tarjeta, Priscilla 18/09) repartidas en 3 resúmenes; pedir el detalle de la tarjeta" % _m(total)),
                ]))
        elif tipo == "tarjeta" and p["saldo"] and p["atraso_dias"]:
            # el resumen impago es deuda vencida hoy
            cuotas.append(OrderedDict([
                ("Banco", p["banco_corto"]), ("Empresa", empresa), ("Linea / Producto", p["producto"]),
                ("Nro Cuota", "resumen"), ("Fecha Vencimiento", hoy - datetime.timedelta(days=p["atraso_dias"])),
                ("Importe Capital", p["saldo"]), ("Importe Interes", 0), ("Importe Total Cuota", None),
                ("Estado", "Pendiente"),
                ("Observaciones", origen + " · resumen de tarjeta impago, atraso %d días" % p["atraso_dias"]),
            ]))
        elif tipo == "prestamo" and not p["falta_importe"]:
            avisos.append("%s %s: sin valor de cuota o cantidad de cuotas, no se armó cronograma" % (p["banco_corto"], p["producto"]))

    if pagos_reales:
        _cruzar_con_pagos(cuotas, pagos_reales, hoy, fechas, fecha_gral, avisos)
        _cruzar_lineas_con_pagos(lineas, mapa["productos"], pagos_reales, avisos)
    cuotas.sort(key=lambda c: (c["Fecha Vencimiento"], c["Banco"]))
    return {"lineas": lineas, "cuotas": cuotas, "avisos": avisos, "origen": origen}


def _estimar_cuota(p, avisos):
    """Sin valor de cuota en el mapa: se estima capital / cuotas que faltan + interés
    del mes sobre el saldo. Y la próxima fecha, del día de alta."""
    m = re.search(r'Faltan\s+(\d+)\s+cuotas', p["obs"], re.I)
    faltan = int(m.group(1)) if m else (p["cuotas"] - (p["pagadas"] or 0))
    if faltan <= 0:
        return
    tna = p["tna"] if isinstance(p["tna"], (int, float)) else 0.0
    p["valor_cuota"] = round(p["saldo"] / faltan + p["saldo"] * tna / 12, 2)
    p["pagadas"] = p["cuotas"] - faltan
    if not p["proxima"] and p["alta"]:
        import calendar
        hoy = datetime.date.today()
        prox = _mas_meses(p["alta"], 1)
        while prox < hoy:
            prox = _mas_meses(prox, 1)
        p["proxima"] = {"nro": p["pagadas"] + 1, "fecha": prox, "importe": p["valor_cuota"]}
    avisos.append("%s %s: el mapa no trae valor de cuota; se estimó %s (saldo %s / %d cuotas + interés al %s%%). Pedir la tabla al banco" % (
        p["banco_corto"], p["producto"], _m(p["valor_cuota"]), _m(p["saldo"]), faltan, ("%.2f" % (tna * 100)).rstrip("0").rstrip(".")))


def _diferidas(p):
    """Importe de 'operaciones diferidas por $X' en las observaciones de una tarjeta."""
    m = re.search(r'operaciones diferidas por\s+\$\s?([\d.,]+)', p["obs"], re.I)
    return _num_ar(m.group(1)) if m else None


# Lo que contestó Priscilla el 18/09 y va en las observaciones de las líneas.
NOTAS_PRISCILLA = {
    ("CORRIENTES", "prestamo"): "Priscilla 18/09: hay una refinanciación en curso",
    ("BBVA", "prestamo"): "Priscilla 18/09: la cuota impaga quedó colgada por falta de fondos; el banco la debita cuando haya (es lo 'pendiente' del home banking)",
    ("MACRO", "descuento"): "Priscilla 18/09: la venta de valores es la forma normal de meter plata en la cuenta (descuento de cheques de clientes)",
}


def _cronograma(p, hoy, empresa, origen, avisos):
    """Cuotas pendientes de un préstamo: impagas (vencidas), próxima, y las estimadas."""
    n = p["cuotas"]
    prox = p["proxima"]
    if prox and prox["fecha"]:
        dia_ref, nro_ref, imp_ref = prox["fecha"], prox["nro"], prox["importe"] or p["valor_cuota"]
    elif p["vto_final"]:
        dia_ref, nro_ref, imp_ref = p["vto_final"], n, p["valor_cuota"]
        avisos.append("%s %s: sin 'próxima cuota' en el texto; se armó desde el vencimiento final" % (p["banco_corto"], p["producto"]))
    else:
        avisos.append("%s %s: sin fecha de próxima cuota ni vencimiento final; no se armó cronograma" % (p["banco_corto"], p["producto"]))
        return []
    pagadas = p["pagadas"]
    impagas = list(p["impagas"])
    if pagadas is None:
        pagadas = (min(impagas) - 1) if impagas else (nro_ref - 1)
    primera_pendiente = min([pagadas + 1] + impagas)
    detalle = p.get("impaga_detalle")

    # el interés estimado para cuotas de capital (préstamos con cuotas de solo interés al principio)
    si = p["solo_interes"]
    tna = p["tna"] if isinstance(p["tna"], (int, float)) else None
    if tna is None and isinstance(p["tna"], str):
        m = re.search(r'(\d+(?:[.,]\d+)?)\s*%', p["tna"])
        tna = float(m.group(1).replace(",", ".")) / 100 if m else None

    out = []
    capital_restante = p["saldo"] or 0.0
    for k in range(primera_pendiente, n + 1):
        fecha = _mas_meses(dia_ref, k - nro_ref)
        if k == nro_ref:
            importe, como = imp_ref, "según el banco"
        elif detalle and k == detalle["nro"]:
            importe, como = detalle["importe"], "impaga según el banco"
        elif si and k > si["n_interes"]:
            interes = capital_restante * (tna or 0) / 12
            importe, como = si["capital_cuota"] + interes, "estimada: capital %s + interés %s" % (_m(si["capital_cuota"]), _m(interes))
            capital_restante -= si["capital_cuota"]
        else:
            importe, como = p["valor_cuota"], "estimada: misma cuota"
        vencida = fecha < hoy
        estado = "Pendiente"
        obs = "%s · cuota %d de %d · %s" % (origen, k, n, como)
        if vencida:
            obs += " · VENCIDA" + (" (impaga según el banco)" if k in impagas else "")
        out.append(OrderedDict([
            ("Banco", p["banco_corto"]), ("Empresa", empresa), ("Linea / Producto", p["producto"]),
            ("Nro Cuota", k), ("Fecha Vencimiento", fecha), ("Importe Capital", round(importe, 2)),
            ("Importe Interes", 0), ("Importe Total Cuota", None), ("Estado", estado), ("Observaciones", obs),
        ]))
    return out


def _cruzar_con_pagos(cuotas, pagos, hoy, fechas, fecha_gral, avisos):
    """Una cuota vencida (o que vence esta semana) que aparece pagada en el extracto
    (mismo banco, importe ±3%) pasa a 'Pagado'. Solo se miran pagos POSTERIORES a la
    fecha del mapa: lo anterior el banco ya lo tuvo en cuenta cuando informó."""
    usados = set()
    for c in cuotas:
        if c["Estado"] != "Pendiente" or c["Fecha Vencimiento"] > hoy + datetime.timedelta(days=7):
            continue
        desde = fechas.get(c["Banco"], fecha_gral)
        for i, pg in enumerate(pagos):
            if i in usados or pg["banco"] != c["Banco"]:
                continue
            if (desde and pg["fecha"] <= desde) or pg["fecha"] < c["Fecha Vencimiento"] - datetime.timedelta(days=5):
                continue
            imp = c["Importe Capital"] + (c["Importe Interes"] or 0)
            if abs(abs(pg["importe"]) - imp) <= 0.03 * imp:
                c["Estado"] = "Pagado"
                c["Observaciones"] += " · PAGADA el %s según extracto (%s %s)" % (pg["fecha"].strftime("%d/%m"), pg["concepto"], _m(pg["importe"]))
                usados.add(i)
                avisos.append("%s %s cuota %s: figuraba impaga/pendiente, el extracto la muestra pagada el %s" % (
                    c["Banco"], c["Linea / Producto"], c["Nro Cuota"], pg["fecha"].strftime("%d/%m")))
                break


def _cruzar_lineas_con_pagos(lineas, productos, pagos, avisos):
    """Un resumen de tarjeta que el extracto muestra pagado (mismo banco, mismo importe,
    después de la fecha del mapa) deja de ser deuda vigente."""
    for l, p in zip(lineas, productos):
        if p["tipo"] != "tarjeta" or not p["saldo"] or not p["fecha_mapa"]:
            continue
        for pg in pagos:
            if pg["banco"] == l["Banco"] and pg["fecha"] > p["fecha_mapa"] and abs(abs(pg["importe"]) - p["saldo"]) < 1:
                l["Capital Vigente"] = _diferidas(p) or 0      # lo que queda: las operaciones diferidas
                l["Observaciones"] = "%s · PAGADO el %s según extracto (%s) · saldo que informaba el mapa: %s · %s" % (
                    l["Observaciones"].split(" · ", 2)[0] + " · " + l["Observaciones"].split(" · ", 2)[1],
                    pg["fecha"].strftime("%d/%m"), _m(pg["importe"]), _m(p["saldo"]), p["obs"])
                avisos.append("%s %s: el resumen de %s se pagó el %s según el extracto; capital vigente queda en 0 (ver si hay operaciones diferidas aparte)" % (
                    l["Banco"], p["producto"], _m(p["saldo"]), pg["fecha"].strftime("%d/%m")))
                break


def leer_pagos_reales(ruta_para_pegar_bancos):
    """Los egresos 'Prestamo' y de tarjeta del para_pegar de los extractos, para cruzar."""
    wb = openpyxl.load_workbook(ruta_para_pegar_bancos, data_only=True)
    ws = wb["Movimientos"]
    enc = [str(c.value or "") for c in ws[1]]
    out = []
    for f in ws.iter_rows(min_row=2, values_only=True):
        d = dict(zip(enc, f))
        if d.get("Tipo") != "Egreso" or not d.get("Fecha"):
            continue
        con = _norm(d.get("Concepto / Detalle"))
        if d.get("Categoria") == "Prestamo" or "TARJETA" in con or "PM/TOT" in con:
            out.append({"banco": str(d.get("Banco / Cuenta", "")).split()[0], "fecha": _fecha(d["Fecha"]),
                        "importe": float(d["Importe"]), "concepto": d.get("Concepto / Detalle")})
    return out


# ------------------------------------------------------------------ salidas
def escribir_para_pegar(res, carpeta, hoy):
    ruta = os.path.join(carpeta, "para_pegar_deuda_%s.xlsx" % hoy.isoformat())
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet("Lineas")
    ws.append(ENC_LINEAS)
    for l in res["lineas"]:
        ws.append([l[c] for c in ENC_LINEAS])
    ws2 = wb.create_sheet("Cronograma")
    ws2.append(ENC_CUOTAS)
    for c in res["cuotas"]:
        ws2.append([None if k in COLS_CON_FORMULA else c[k] for k in ENC_CUOTAS])
    wb.save(ruta)
    return ruta


def escribir_sheet_con_deuda(res, sheet_original, hoy):
    """Copia del Cashflow con la solapa Deuda Bancaria cargada: bloque A (líneas) y
    bloque B (cronograma). Se pisan las filas con la MARCA y las AGREGADO; el resto
    (cargado a mano) queda."""
    wb = openpyxl.load_workbook(sheet_original)
    ws = wb["Deuda Bancaria"]
    filas = list(ws.iter_rows(values_only=True))
    enc_idx = [i for i, f in enumerate(filas) if f and _norm(f[0]) == "BANCO"]
    if len(enc_idx) != 2:
        raise RuntimeError("Deuda Bancaria: esperaba 2 encabezados 'Banco' (líneas y cronograma), hay %d" % len(enc_idx))
    bloques = [(enc_idx[0], enc_idx[1] - 2, res["lineas"], ENC_LINEAS),        # hasta 2 filas antes del título "B)"
               (enc_idx[1], len(filas) - 1, res["cuotas"], ENC_CUOTAS)]
    for i_enc, i_fin, nuevas, enc_esperado in bloques:
        enc = [str(c or "") for c in filas[i_enc]]
        col_obs = enc.index("Observaciones") + 1
        # filas que quedan: las que no tienen la marca ni son agregado
        vivas = []
        for f in filas[i_enc + 1:i_fin + 1]:
            if not f or not f[0]:
                continue
            obs = str(f[col_obs - 1] or "")
            if MARCA in obs or "AGREGADO" in obs.upper() or "(agregado" in str(f[2] or "").lower():
                continue
            vivas.append(list(f[:len(enc)]))
        finales = vivas + [[c.get(k) for k in enc] for c in nuevas]
        capacidad = i_fin - i_enc
        if len(finales) > capacidad:
            raise RuntimeError("Deuda Bancaria: el bloque que empieza en la fila %d tiene lugar para %d filas y hay %d" % (i_enc + 1, capacidad, len(finales)))
        # limpiar el bloque y escribir
        for r in range(i_enc + 2, i_fin + 2):
            for c in range(1, len(enc) + 1):
                ws.cell(row=r, column=c).value = None
        for j, fila in enumerate(finales):
            r = i_enc + 2 + j
            for c, k in enumerate(enc, 1):
                if k == "Importe Total Cuota":
                    ws.cell(row=r, column=c).value = "=F%d+G%d" % (r, r)
                elif k:
                    ws.cell(row=r, column=c).value = fila[c - 1]
    base, ext = os.path.splitext(sheet_original)
    base = re.sub(r' \(con .*?\)$', '', base)
    ruta = "%s (con deuda %s)%s" % (base, hoy.isoformat(), ext)
    wb.save(ruta)
    return ruta


def resumen(res, mapa, ruta_pegar, hoy):
    lineas, cuotas = res["lineas"], res["cuotas"]
    por_banco = defaultdict(float)
    for l in lineas:
        if l["Capital Vigente"]:
            por_banco[l["Banco"]] += l["Capital Vigente"]
    L = ["# Mapa de deuda bancaria → Cashflow · %s" % hoy.strftime("%d/%m/%Y"), "",
         "Fuente: `%s` — %s" % (mapa["archivo"], mapa["titulo"]), "",
         "## Deuda por banco (capital vigente, incluye descubiertos usados)", "",
         "| Banco | Deuda | Productos |", "|---|---:|---|"]
    for b, v in sorted(por_banco.items(), key=lambda kv: -kv[1]):
        L.append("| %s | %s | %s |" % (b, _m(v), ", ".join(l["Linea / Producto"] for l in lineas if l["Banco"] == b)))
    L += ["| **Total** | **%s** | |" % _m(sum(por_banco.values())), ""]
    desc = sum(l["Capital Vigente"] or 0 for l in lineas if "YA ESTA EN LA CAJA" in l["Observaciones"])
    L += ["De ese total, %s son descubiertos usados: ya están en la caja (saldo negativo de las cuentas), no se suman aparte." % _m(desc), ""]
    peor = max((l["Situacion BCRA"] or 0) for l in lineas)
    L += ["Peor situación BCRA informada: **%d** (%s)." % (peor, ", ".join("%s %s" % (l["Banco"], l["Linea / Producto"]) for l in lineas if l["Situacion BCRA"] == peor)), ""]
    venc = [c for c in cuotas if c["Estado"] == "Pendiente" and c["Fecha Vencimiento"] < hoy]
    L += ["## Cuotas", "", "- %d cuotas pendientes armadas (%s)" % (len([c for c in cuotas if c["Estado"] == "Pendiente"]),
                                                                   _m(sum(c["Importe Capital"] for c in cuotas if c["Estado"] == "Pendiente"))),
          "- **Vencidas (impagas): %d por %s**" % (len(venc), _m(sum(c["Importe Capital"] for c in venc)))]
    for c in venc:
        L.append("  - %s · %s · cuota %s · vto %s · %s" % (c["Banco"], c["Linea / Producto"], c["Nro Cuota"],
                                                            c["Fecha Vencimiento"].strftime("%d/%m"), _m(c["Importe Capital"])))
    for dias in (30, 90):
        prox = [c for c in cuotas if c["Estado"] == "Pendiente" and hoy <= c["Fecha Vencimiento"] < hoy + datetime.timedelta(days=dias)]
        L.append("- Vencen en %d días: %d cuotas por %s" % (dias, len(prox), _m(sum(c["Importe Capital"] for c in prox))))
    prox30 = [c for c in cuotas if c["Estado"] == "Pendiente" and hoy <= c["Fecha Vencimiento"] < hoy + datetime.timedelta(days=30)]
    for c in prox30:
        L.append("  - %s · %s · cuota %s · %s · %s" % (c["Fecha Vencimiento"].strftime("%d/%m"), c["Banco"], c["Nro Cuota"],
                                                       c["Linea / Producto"], _m(c["Importe Capital"])))
    pag = [c for c in cuotas if c["Estado"] == "Pagado"]
    if pag:
        L += ["", "Cuotas que el mapa daba impagas y el extracto muestra pagadas: %d (%s)." % (len(pag), _m(sum(c["Importe Capital"] for c in pag)))]
    if res["avisos"]:
        L += ["", "## Avisos", ""] + ["- " + a for a in res["avisos"]]
    L += ["", "## Archivo generado", "", "- `%s` → solapas Lineas y Cronograma, para la solapa Deuda Bancaria del Cashflow" % os.path.basename(ruta_pegar), ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="Mapa de deuda financiera -> solapa Deuda Bancaria")
    ap.add_argument("--archivo", required=True)
    ap.add_argument("--cliente", default="navar")
    ap.add_argument("--hoy", default=None)
    ap.add_argument("--empresa", default="A")
    ap.add_argument("--bancos", default=None, help="para_pegar_bancos_<fecha>.xlsx para cruzar cuotas pagadas")
    ap.add_argument("--sheet", default=None, help="copia del Cashflow (.xlsx) para cargar la solapa Deuda Bancaria")
    a = ap.parse_args()
    hoy = datetime.date.fromisoformat(a.hoy) if a.hoy else datetime.date.today()
    mapa = leer_mapa(a.archivo)
    pagos = leer_pagos_reales(a.bancos) if a.bancos else None
    res = armar(mapa, hoy, a.empresa, pagos)
    carpeta = os.path.dirname(os.path.abspath(a.archivo))
    ruta = escribir_para_pegar(res, carpeta, hoy)
    md = resumen(res, mapa, ruta, hoy)
    with open(os.path.join(carpeta, "resumen_deuda_%s.md" % hoy.isoformat()), "w", encoding="utf-8") as f:
        f.write(md)
    print(md)
    if a.sheet:
        print("\nCopia del Cashflow con la deuda:", escribir_sheet_con_deuda(res, a.sheet, hoy))


if __name__ == "__main__":
    main()
