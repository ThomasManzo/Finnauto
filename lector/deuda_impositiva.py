# -*- coding: utf-8 -*-
"""
lector.deuda_impositiva — del "Control Vencimiento Impuestos" a la solapa "Deuda Impositiva".

PARA QUE
--------
El 18/09/2026 llegó `Control Vencimiento Impuestos.xlsx`: la planilla que arma Celia
(administración de NAVAR) y revisa el contador (Estudio Monti): cada impuesto, período,
capital, interés, importe a pagar, vencimiento y si está pagado. Total adeudado al
18/09: $619,6 M. Es el mapa de deuda impositiva que le faltaba al tablero.

Este módulo la lee y arma la solapa Deuda Impositiva del Cashflow: una fila por
deuda PENDIENTE (lo pagado no se carga), con su vencimiento. Lo vencido queda como
stock (bloque "Atrasado" del Cash); lo que vence adelante entra en la curva.

Las notas del contador sobre planes de pago posibles ("contado X + N cuotas de Y")
van en Observaciones, no como cuotas: son propuestas, no compromisos. Cuando se
firme un plan, se carga el plan (sus cuotas) y se da de baja la deuda original.

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

# Lo que dijo el mail del 18/09 (Celia / contador) y no está en el Excel como fecha.
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
    return {"archivo": os.path.basename(ruta), "deudas": deudas}


def armar(mapa, hoy, empresa="A", excepciones_auto=None):
    filas, avisos = [], []
    origen = "%s · %s" % (MARCA, mapa["archivo"])
    for d in mapa["deudas"]:
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
         "Fuente: `%s` (Celia, revisado por Estudio Monti el 18/09)." % mapa["archivo"], "",
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
