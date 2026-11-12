# -*- coding: utf-8 -*-
"""
lector.deuda_impositiva — del "Control Vencimiento Impuestos" a la solapa "Deuda Impositiva".

PARA QUE
--------
El 18/09/2026 llegó `Control Vencimiento Impuestos.xlsx`: la planilla que arma [persona de NAVAR]
(administración de NAVAR) y revisa el contador ([estudio contable]): cada impuesto, período,
capital, interés, importe a pagar, vencimiento y si está pagado. Total adeudado al
18/09: $X M. Es el mapa de deuda impositiva que le faltaba al tablero.

Este módulo la lee y arma la solapa Deuda Impositiva del Cashflow: una fila por
deuda PENDIENTE (lo pagado no se carga), con su vencimiento. Lo vencido queda como
stock (bloque "Atrasado" del Cash); lo que vence adelante entra en la curva.

Las notas del contador sobre planes de pago posibles ("contado X + N cuotas de Y")
van en Observaciones, no como cuotas: son propuestas, no compromisos. Cuando se
firme un plan, se carga el plan (sus cuotas) y se da de baja la deuda original.

PLANES FIRMADOS (tarea 91, planilla del 12/11/2026)
La solapa Vencimientos trae solo la cuota del mes de los planes (ARCA: un renglón con todas
juntas; Rentas: la próxima cuota). Desde noviembre la planilla trae también:
  · "PLANES VIGENTE ARCA ..." : un renglón por plan con "cuota X de N", importe al 1er vto y
    fecha de ingreso. Se proyectan las cuotas X..N, una por mes, el mismo día de la fecha de
    ingreso y con el mismo importe (estimado: ARCA ajusta un poco el interés cada mes).
    Si dice solo "N" (planes recién firmados) se toma como cuota 1 de N y se avisa.
  · "PLAN DE PAGO RENTAS": "CUOTA k · importe · fecha" (lo que dice PAGADO no se carga).
Cuando están esas solapas, los renglones de planes de Vencimientos desde la primera cuota
proyectada se reemplazan por las cuotas del plan (si no, se sumarían dos veces). Lo anterior
que haya quedado impago en Vencimientos se conserva.

Uso:
    python lector/deuda_impositiva.py --archivo "clientes/navar/privado/impuestos/Control Vencimiento Impuestos.xlsx" --cliente navar --hoy 2026-09-18
    python lector/deuda_impositiva.py ... --sheet "clientes/navar/privado/NAVAR - Cash Flow (con deuda 2026-09-18).xlsx"
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

MARCA = "Mapa impuestos"
ENC = ["Impuesto", "Empresa", "Periodo", "Fecha Vencimiento", "Importe", "Estado", "Nro Cuota (si aplica)", "Debito Automatico", "Observaciones"]

# "Debito Automatico": los planes de pago vigentes de ARCA se debitan solos de la cuenta (CBU
# adherido) → "Si". Todo lo demás (VEP, DGR, municipio) lo paga alguien por decisión → "No".
# Se corrige impuesto por impuesto en catalogo.json → "debito_automatico": {"<impuesto>": "Si"}.
def _debito_automatico(impuesto, concepto, excepciones):
    for clave, valor in (excepciones or {}).items():
        if _norm(clave) in _norm(impuesto) or _norm(clave) in _norm(concepto or ""):
            return valor
    return "Si" if "PLAN" in _norm(impuesto).upper() and "PAGO" in _norm(impuesto).upper() else "No"

# Lo que dijo el mail del 18/09 ([persona de NAVAR] / contador) y no está en el Excel como fecha.
FECHAS_DEL_MAIL = {
    "HAY QUE REHABILITAR DOS CUOTAS": (datetime.date(2026, 9, 26), "según mail del contador 18/09: rehabilitar antes del 26/09 o caduca el plan"),
    "INTERESES ABRIL 2026": (None, "intereses del IVA 04/2026 que encontró el contador en AFIP (mail 18/09)"),
}


def _norm(s):
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode()
    return " ".join(s.upper().split())


def _m(v):
    return ("-" if v < 0 else "") + "$" + format(int(round(abs(v))), ",d").replace(",", ".")


def _fecha(v):
    if isinstance(v, datetime.datetime):
        return v.date()
    if isinstance(v, datetime.date):
        return v
    m = re.search(r'(\d{1,2})/(\d{1,2})/(\d{2,4})', str(v or ""))
    if not m:
        return None
    d, mo, a = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return datetime.date(a + 2000 if a < 100 else a, mo, d)


def leer(ruta):
    wb = openpyxl.load_workbook(ruta, data_only=True)
    ws = wb["Vencimientos"] if "Vencimientos" in wb.sheetnames else wb.worksheets[0]
    filas = list(ws.iter_rows(values_only=True))
    enc_i = next(i for i, f in enumerate(filas) if f and _norm(f[0]) == "IMPUESTO")
    enc = [_norm(c) for c in filas[enc_i]]

    def col(f, nombre):
        for i, e in enumerate(enc):
            if e.startswith(nombre):
                return f[i] if i < len(f) else None
        return None

    deudas, impuesto = [], None
    for f in filas[enc_i + 1:]:
        if not f or not any(v not in (None, "") for v in f):
            continue
        if col(f, "IMPUESTO"):
            impuesto = str(col(f, "IMPUESTO")).strip()
        concepto = str(col(f, "CONCEPTO") or "").strip()
        if not concepto:
            continue
        importe = col(f, "IMPORTE A PAGAR")
        capital, interes = col(f, "CAPITAL"), col(f, "INTERES")
        deudas.append({
            "impuesto": impuesto, "concepto": concepto,
            "capital": float(capital) if isinstance(capital, (int, float)) else None,
            "interes": float(interes) if isinstance(interes, (int, float)) else None,
            "importe": float(importe) if isinstance(importe, (int, float)) else None,
            "vencimiento": _fecha(col(f, "FECHA VENCIMIENTO")),
            "estado": str(col(f, "ESTADO") or "").strip(),
            "cancelado": str(col(f, "CANCELADO") or "").strip(),
            "plan": str(col(f, "COLUMNA1") or "").strip(),      # la nota del contador ("PLAN: CONTADO ... Y N CUOTAS DE ...")
        })
    return {"archivo": os.path.basename(ruta), "deudas": deudas,
            "planes_arca": _leer_planes_arca(wb), "plan_rentas": _leer_plan_rentas(wb)}


def _sumar_meses(fecha, n):
    """Misma fecha n meses después; si ese mes no tiene el día (31/02), el último día del mes."""
    a, m = divmod(fecha.month - 1 + n, 12)
    a, m = fecha.year + a, m + 1
    for dia in (fecha.day, 30, 29, 28):
        try:
            return datetime.date(a, m, dia)
        except ValueError:
            continue


def _leer_planes_arca(wb):
    """Solapa 'PLANES VIGENTE ARCA ...': [{plan, desde, hasta, importe, fecha, supuesto}].
    Sin esa solapa, lista vacía (la planilla vieja no la tenía)."""
    nombre = next((n for n in wb.sheetnames if "PLANES VIGENTE ARCA" in _norm(n)), None)
    if not nombre:
        return []
    filas = list(wb[nombre].iter_rows(values_only=True))
    enc_i = next((i for i, f in enumerate(filas) if f and any(_norm(c) == "1ER VTO" for c in f)), None)
    if enc_i is None:
        return []
    enc = [_norm(c) for c in filas[enc_i]]
    i_cuota, i_imp, i_fecha = enc.index("CUOTAS"), enc.index("1ER VTO"), enc.index("FECHA INGRESO")
    planes = []
    for f in filas[enc_i + 1:]:
        nombre_plan = str(f[1] or "").strip() if len(f) > 1 else ""
        importe, fecha = f[i_imp], _fecha(f[i_fecha])
        if not nombre_plan or not isinstance(importe, (int, float)) or not fecha:
            continue
        texto = _norm(f[i_cuota])
        m = re.match(r"^(\d+)\s*DE\s*(\d+)$", texto)
        if m:
            desde, hasta, supuesto = int(m.group(1)), int(m.group(2)), False
        elif re.match(r"^\d+$", texto):
            desde, hasta, supuesto = 1, int(texto), True     # plan nuevo: dice solo cuántas cuotas
        else:
            desde, hasta, supuesto = 1, 1, True               # sin dato: solo la de este mes
        planes.append({"plan": nombre_plan, "desde": desde, "hasta": max(desde, hasta),
                       "importe": float(importe), "fecha": fecha, "supuesto": supuesto})
    return planes


def _leer_plan_rentas(wb):
    """Solapa 'PLAN DE PAGO RENTAS': [{cuota, importe, fecha}] de las cuotas con fecha (no las PAGADAS)."""
    nombre = next((n for n in wb.sheetnames if "PLAN DE PAGO RENTAS" in _norm(n)), None)
    if not nombre:
        return []
    cuotas = []
    for f in wb[nombre].iter_rows(values_only=True):
        m = re.match(r"^CUOTA\s*(\d+)$", _norm(f[0] if f else ""))
        if not m or len(f) < 3 or not isinstance(f[1], (int, float)) or not _fecha(f[2]):
            continue
        cuotas.append({"cuota": int(m.group(1)), "importe": float(f[1]), "fecha": _fecha(f[2])})
    return cuotas


def _es_plan_arca(impuesto):
    return bool(re.search(r"PLAN(ES)? DE PAGOS? ARCA", _norm(impuesto)))


def _es_plan_rentas(impuesto):
    return bool(re.search(r"PLAN(ES)? DE PAGOS? (DGR|RENTAS)", _norm(impuesto)))


def _cuotas_de_planes(mapa, empresa, origen, excepciones_auto, avisos):
    """Una fila por cuota proyectada de los planes firmados (ARCA y Rentas)."""
    filas = []
    for p in mapa.get("planes_arca") or []:
        if p["supuesto"]:
            avisos.append("PLAN ARCA %s: la planilla dice solo '%d' cuotas; se tomó como cuota 1 de %d desde %s (confirmar)"
                          % (p["plan"], p["hasta"], p["hasta"], p["fecha"].strftime("%d/%m/%Y")))
        for k, n in enumerate(range(p["desde"], p["hasta"] + 1)):
            obs = [origen, "plan ARCA firmado: cuota %d de %d proyectada con el importe del 1er vto (estimado)" % (n, p["hasta"])]
            if p["supuesto"]:
                obs.append("SUPUESTO: la planilla dice solo la cantidad de cuotas; se tomó la de %s como la 1" % p["fecha"].strftime("%m/%Y"))
            filas.append(OrderedDict([
                ("Impuesto", "PLANES DE PAGO ARCA"), ("Empresa", empresa), ("Periodo", p["plan"]),
                ("Fecha Vencimiento", _sumar_meses(p["fecha"], k)), ("Importe", round(p["importe"], 2)), ("Estado", "Pendiente"),
                ("Nro Cuota (si aplica)", "%d de %d" % (n, p["hasta"])),
                ("Debito Automatico", _debito_automatico("PLANES DE PAGO ARCA", p["plan"], excepciones_auto)),
                ("Observaciones", " · ".join(obs)),
            ]))
    rentas = mapa.get("plan_rentas") or []
    total = max((c["cuota"] for c in rentas), default=0)
    for c in rentas:
        filas.append(OrderedDict([
            ("Impuesto", "PLAN DE PAGO DGR CTES"), ("Empresa", empresa), ("Periodo", "Plan Rentas Corrientes"),
            ("Fecha Vencimiento", c["fecha"]), ("Importe", round(c["importe"], 2)), ("Estado", "Pendiente"),
            ("Nro Cuota (si aplica)", "%d de %d" % (c["cuota"], total)),
            ("Debito Automatico", _debito_automatico("PLAN DE PAGO DGR CTES", "", excepciones_auto)),
            ("Observaciones", origen + " · plan de Rentas firmado: cuota %d de %d (solapa PLAN DE PAGO RENTAS)" % (c["cuota"], total)),
        ]))
    return filas


def armar(mapa, hoy, empresa="A", excepciones_auto=None):
    filas, avisos = [], []
    origen = "%s · %s" % (MARCA, mapa["archivo"])
    # Con las solapas de planes, la cuota del mes que trae Vencimientos ya está en el plan:
    # se saltean los renglones de planes desde la primera cuota proyectada (lo anterior impago queda).
    desde_arca = min((p["fecha"] for p in mapa.get("planes_arca") or []), default=None)
    desde_rentas = min((c["fecha"] for c in mapa.get("plan_rentas") or []), default=None)
    for d in mapa["deudas"]:
        venc0 = d["vencimiento"] or hoy
        if (desde_arca and _es_plan_arca(d["impuesto"]) and venc0 >= desde_arca) or \
           (desde_rentas and _es_plan_rentas(d["impuesto"]) and venc0 >= desde_rentas):
            continue
        # "Cancelado" dice Pendiente pero la nota de al lado dice "pagada": se pagó después
        # de armar la planilla (16/09). Vale la nota.
        if _norm(d["plan"]) in ("PAGADA", "PAGADO"):
            d["cancelado"] = "Pagado"
        if _norm(d["cancelado"]) == "PAGADO" or (d["importe"] or 0) <= 0:
            if _norm(d["cancelado"]) != "PAGADO" and (d["importe"] or 0) <= 0 and d["concepto"]:
                avisos.append("%s · %s: sin importe en el Excel, no se cargó" % (d["impuesto"], d["concepto"]))
            continue
        venc, nota_fecha = d["vencimiento"], ""
        for clave, (fecha_mail, nota) in FECHAS_DEL_MAIL.items():
            if clave in _norm(d["concepto"]):
                venc = fecha_mail or venc
                nota_fecha = nota
        if venc is None:
            venc = hoy
            nota_fecha = (nota_fecha + " · " if nota_fecha else "") + "sin fecha en el Excel: se toma hoy (vencido)"
            avisos.append("%s · %s: sin vencimiento, se cargó como vencido hoy" % (d["impuesto"], d["concepto"]))
        obs = [origen]
        if d["capital"] is not None and d["interes"]:
            obs.append("capital %s + interés %s" % (_m(d["capital"]), _m(d["interes"])))
        if nota_fecha:
            obs.append(nota_fecha)
        if d["plan"] and "PLAN" in _norm(d["plan"]):
            obs.append("propuesta del contador (no firmada): " + d["plan"])
        filas.append(OrderedDict([
            ("Impuesto", d["impuesto"] or "(sin impuesto)"), ("Empresa", empresa), ("Periodo", d["concepto"]),
            ("Fecha Vencimiento", venc), ("Importe", round(d["importe"], 2)), ("Estado", "Pendiente"),
            ("Nro Cuota (si aplica)", None), ("Debito Automatico", _debito_automatico(d["impuesto"] or "", d["concepto"], excepciones_auto)),
            ("Observaciones", " · ".join(obs)),
        ]))
    filas += _cuotas_de_planes(mapa, empresa, origen, excepciones_auto, avisos)
    filas.sort(key=lambda x: (x["Fecha Vencimiento"], x["Impuesto"]))
    return {"filas": filas, "avisos": avisos}


def escribir_para_pegar(res, carpeta, hoy):
    ruta = os.path.join(carpeta, "para_pegar_impuestos_%s.xlsx" % hoy.isoformat())
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Deuda Impositiva"
    ws.append(ENC)
    for f in res["filas"]:
        ws.append([f[c] for c in ENC])
    wb.save(ruta)
    return ruta


def escribir_sheet(res, sheet_original, hoy):
    """Copia del Cashflow con Deuda Impositiva cargada: se pisan las filas con la MARCA
    y las "(agregado cash viejo)"; lo cargado a mano queda."""
    wb = openpyxl.load_workbook(sheet_original)
    ws = wb["Deuda Impositiva"]
    enc = [str(c.value or "") for c in ws[1]]
    col_obs = enc.index("Observaciones") + 1
    vivas, antes = [], 0
    for f in ws.iter_rows(min_row=2, values_only=True):
        if not f or not f[0]:
            continue
        antes += 1
        obs = str(f[col_obs - 1] or "")
        if MARCA in obs or "AGREGADO" in obs.upper() or "(agregado" in str(f[0]).lower():
            continue
        vivas.append(list(f[:len(enc)]))
    finales = vivas + [[x.get(k) for k in enc] for x in res["filas"]]
    for r in range(2, antes + 2):
        for c in range(1, len(enc) + 1):
            ws.cell(row=r, column=c).value = None
    for j, fila in enumerate(finales):
        for c, v in enumerate(fila, 1):
            ws.cell(row=2 + j, column=c).value = v
    base, ext = os.path.splitext(sheet_original)
    base = re.sub(r' \(con .*?\)$', '', base)
    ruta = "%s (con impuestos %s)%s" % (base, hoy.isoformat(), ext)
    wb.save(ruta)
    return ruta


def resumen(res, mapa, ruta_pegar, hoy):
    filas = res["filas"]
    por_imp = defaultdict(float)
    for f in filas:
        por_imp[f["Impuesto"]] += f["Importe"]
    venc = [f for f in filas if f["Fecha Vencimiento"] < hoy]
    L = ["# Deuda impositiva → Cashflow · %s" % hoy.strftime("%d/%m/%Y"), "",
         "Fuente: `%s` ([persona de NAVAR], revisado por [estudio contable] el 18/09)." % mapa["archivo"], "",
         "| Impuesto | Pendiente |", "|---|---:|"]
    for k, v in sorted(por_imp.items(), key=lambda kv: -kv[1]):
        L.append("| %s | %s |" % (k, _m(v)))
    L += ["| **Total** | **%s** |" % _m(sum(por_imp.values())), "",
          "- Filas cargadas: %d · **vencidas: %d por %s**" % (len(filas), len(venc), _m(sum(f["Importe"] for f in venc)))]
    for dias in (7, 30, 90):
        prox = [f for f in filas if hoy <= f["Fecha Vencimiento"] < hoy + datetime.timedelta(days=dias)]
        L.append("- Vencen en %d días: %d por %s" % (dias, len(prox), _m(sum(f["Importe"] for f in prox))))
    prox = [f for f in filas if hoy <= f["Fecha Vencimiento"] < hoy + datetime.timedelta(days=30)]
    for f in prox:
        L.append("  - %s · %s · %s · %s" % (f["Fecha Vencimiento"].strftime("%d/%m"), f["Impuesto"], f["Periodo"], _m(f["Importe"])))
    planes = [f for f in filas if "propuesta del contador" in f["Observaciones"]]
    if planes:
        L += ["", "## Planes de pago que propone el contador (no firmados)", ""]
        for f in planes:
            L.append("- %s · %s (%s): %s" % (f["Impuesto"], f["Periodo"], _m(f["Importe"]), f["Observaciones"].split("propuesta del contador (no firmada): ")[1]))
    if res["avisos"]:
        L += ["", "## Avisos", ""] + ["- " + a for a in res["avisos"]]
    L += ["", "## Archivo generado", "", "- `%s` → solapa Deuda Impositiva (botón «Importar Impuestos»)" % os.path.basename(ruta_pegar), ""]
    return "\n".join(L)


def _excepciones_auto(cliente):
    import json
    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "clientes", cliente, "catalogo.json")
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f).get("debito_automatico", {})
    except Exception:
        return {}


def main():
    ap = argparse.ArgumentParser(description="Control Vencimiento Impuestos -> solapa Deuda Impositiva")
    ap.add_argument("--archivo", required=True)
    ap.add_argument("--cliente", default="navar")
    ap.add_argument("--hoy", default=None)
    ap.add_argument("--empresa", default="A")
    ap.add_argument("--sheet", default=None)
    a = ap.parse_args()
    hoy = datetime.date.fromisoformat(a.hoy) if a.hoy else datetime.date.today()
    mapa = leer(a.archivo)
    res = armar(mapa, hoy, a.empresa, _excepciones_auto(a.cliente))
    carpeta = os.path.dirname(os.path.abspath(a.archivo))
    ruta = escribir_para_pegar(res, carpeta, hoy)
    md = resumen(res, mapa, ruta, hoy)
    with open(os.path.join(carpeta, "resumen_impuestos_%s.md" % hoy.isoformat()), "w", encoding="utf-8") as f:
        f.write(md)
    print(md)
    if a.sheet:
        print("\nCopia del Cashflow con impuestos:", escribir_sheet(res, a.sheet, hoy))


if __name__ == "__main__":
    main()
