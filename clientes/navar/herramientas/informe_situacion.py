# -*- coding: utf-8 -*-
"""
informe_situacion — el PDF "Situación de caja y plan" de NAVAR.

Versión 2 (20/09/2026): TODOS los números salen de la Sheet "NAVAR - Cash Flow" exportada a
Excel (solapas Cash Mensual, Plan, Deuda Bancaria, Deuda Impositiva). No hay ningún número
tipeado acá: si la Sheet cambia, se vuelve a correr y el PDF cambia. Lo real es real hasta
el último extracto; lo demás está marcado como estimado.

Tres escenarios, todos con la misma operación (lo que la Sheet proyecta):
  A · sin tocar nada: cuotas y vencimientos como están en el cronograma;
  B · el plan cargado en la solapa Plan (la propuesta);
  C · lo que haría falta para volver a cero (supuestos explícitos, ver escenario_c).
El escenario B es una PROPUESTA: que un banco la apruebe es otra cosa, y el PDF lo dice.

Uso:
    python clientes/navar/herramientas/informe_situacion.py [--sheet <export.xlsx>] [--hoy AAAA-MM-DD]
    (deja privado/salidas/NAVAR - Situación y plan <fecha>.pdf)
"""

import os
import sys
import glob
import datetime
import argparse
from collections import defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
BASE_REPO = os.path.abspath(os.path.join(AQUI, "..", "..", ".."))
os.chdir(BASE_REPO)
sys.path.insert(0, BASE_REPO)
sys.path.insert(0, AQUI)

import openpyxl
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.graphics.shapes import Drawing, Line, String, Rect, PolyLine

import propuesta as PR          # los estilos y ayudas del PDF anterior (mismo look)

P, LI, tabla, kpis, caja = PR.P, PR.LI, PR.tabla, PR.kpis, PR.caja
E, TINTA, SUAVE, TENUE, VERDE, ROJO, AMBAR, FONDO, ROJO_FONDO, LINEA = (
    PR.E, PR.TINTA, PR.SUAVE, PR.TENUE, PR.VERDE, PR.ROJO, PR.AMBAR, PR.FONDO, PR.ROJO_FONDO, PR.LINEA)
AZUL = colors.HexColor("#3A5FA8")
NOMBRE = {"NACION": "Nación", "CORRIENTES": "Corrientes", "MACRO": "Macro", "GALICIA": "Galicia", "BBVA": "BBVA"}
CONCEPTO = {"SICORE": "SICORE", "PLANES DE PAGO ARCA": "Planes de pago ARCA", "AGENTES INGRESOS BRUTOS": "Agentes de Ingresos Brutos",
            "EMPLEADOR-APORTES SEG. SOCIAL": "Aportes seguridad social", "BIENES ACC Y PARTICIPACIONES": "Bienes personales (acciones)",
            "GANANCIAS SOCIEDADES": "Ganancias sociedades", "IVA": "IVA"}


def m(v, corto=False):
    """$ con punto de miles; corto = en millones"""
    if corto:
        return ("-" if v < 0 else "") + "$" + format(int(round(abs(float(v or 0)) / 1e6)), ",d").replace(",", ".") + " M"
    return PR.m(v)


def nom(b):
    return NOMBRE.get(str(b), str(b).title())


def conc(c):
    return CONCEPTO.get(str(c), str(c))

MESES = {1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun", 7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic"}


def lab(d):
    return "%s %s" % (MESES[d.month], str(d.year)[2:])


def mm_(v):
    """millones con signo, sin decimales"""
    return ("-" if v < 0 else "") + format(int(round(abs(v) / 1e6)), ",d").replace(",", ".")


def pmt(capital, tasa, n):
    return capital * tasa / (1 - (1 + tasa) ** -n) if tasa else capital / n


# ------------------------------------------------------------------ leer la Sheet
def ultimo_export():
    c = sorted(glob.glob(os.path.join("clientes", "navar", "privado", "NAVAR - Cash Flow (export Sheets *.xlsx")))
    if not c:
        sys.exit("No hay export de la Sheet en privado/. Bajarla como Excel primero.")
    return c[-1]


def leer(sheet, hoy):
    wb = openpyxl.load_workbook(sheet, data_only=True)
    D = {"hoy": hoy}

    # ---- Cash Mensual: renglón → lista de valores por mes
    ws = wb["Cash Mensual"]
    filas = list(ws.iter_rows(values_only=True))
    fechas = next(r for r in filas if r[0] == "Fecha")
    cols = [c for c in fechas[1:] if isinstance(c, datetime.datetime)]
    D["cols"] = [c.date() for c in cols]
    n = len(cols)
    D["ultimo_extracto"] = next(r[1] for r in filas if r[0] and str(r[0]).startswith("Último día")).date()
    D["inflacion"] = next(r[1] for r in filas if r[0] and str(r[0]).startswith("Inflación"))
    M = {}
    for r in filas:
        if r[0] and isinstance(r[0], str):
            M[r[0].strip()] = [float(v) if isinstance(v, (int, float)) else 0.0 for v in r[1:1 + n]]
    # nombres de la pantalla v5 → nombres que usa este informe (cuotas = todo lo bancario, impuestos = deuda impositiva)
    z = [0.0] * n
    suma = lambda *ks: [sum(M.get(k, z)[i] for k in ks) for i in range(n)]
    M["Cuotas bancarias y tarjeta"] = suma("Cuotas y tarjetas con débito automático", "Cuotas que se pagan por decisión")
    M["Impuestos: deuda y planes"] = suma("Planes de ARCA con débito automático", "Impuestos por VEP y planes nuevos")
    M.setdefault("Regularización de atrasado", z)
    M["Saldo de bancos al cierre del mes"] = M.get("SALDO AL CIERRE del mes pagando toda la deuda", M.get("Saldo de bancos al cierre del mes", z))
    M["Descubiertos acordados con los bancos"] = M.get("Descubierto acordado con los bancos", M.get("Descubiertos acordados con los bancos", z))
    M["Saldo disponible (cierre + descubiertos)"] = M.get("Saldo disponible pagando toda la deuda (positivos + descubierto disponible)", M.get("Saldo disponible (cierre + descubiertos)", z))
    D["M"] = M
    # bancos: la última columna con saldo real
    bancos = {}
    en_bancos = False
    for r in filas:
        if r[0] == "1 · Bancos (saldo real al cierre)":
            en_bancos = True
            continue
        if en_bancos:
            if r[0] is None or str(r[0]).startswith("Total"):
                if str(r[0] or "").startswith("Total"):
                    break
                continue
            vals = [v for v in r[1:1 + n] if isinstance(v, (int, float))]
            bancos[r[0]] = vals[-1] if vals else 0.0
    D["bancos"] = bancos

    # ---- Plan
    ws = wb["Plan"]
    filas = list(ws.iter_rows(values_only=True))
    enc = next(r for r in filas if r[0] == "Tipo")
    meses_plan = [c.date() for c in enc if isinstance(c, datetime.datetime)]
    plan = []
    for r in filas[filas.index(enc) + 1:]:
        if r[0] in ("Banco", "Impuesto", "Atrasado"):
            d = dict(zip(enc, r))
            d["meses"] = {mp: float(v or 0) for mp, v in zip(meses_plan, [r[enc.index(c)] for c in enc if isinstance(c, datetime.datetime)])}
            plan.append(d)
    D["plan"] = plan

    # ---- Deuda Bancaria: líneas y cronograma pendiente por mes y banco (escenario "sin tocar nada")
    ws = wb["Deuda Bancaria"]
    filas = list(ws.iter_rows(values_only=True))
    enc_l = filas[1]
    lineas = []
    for r in filas[2:]:
        if r[0] == "Banco" or r[0] is None or str(r[0]).startswith("B)"):
            if r[0] == "Banco":
                break
            continue
        lineas.append(dict(zip(enc_l, r)))
    D["lineas"] = lineas
    D["descubiertos"] = {l["Banco"]: float(l["Capital Original"] or 0) for l in lineas if "escubierto" in str(l["Linea / Producto"])}
    i_cron = next(i for i, r in enumerate(filas) if r[0] == "Banco" and "Nro Cuota" in r)
    enc_c = filas[i_cron]
    cron = defaultdict(float)
    cron_banco = defaultdict(float)
    for r in filas[i_cron + 1:]:
        d = dict(zip(enc_c, r))
        f = d.get("Fecha Vencimiento")
        if not f or d.get("Estado") != "Pendiente":
            continue
        imp = d.get("Importe Total Cuota") or ((d.get("Importe Capital") or 0) + (d.get("Importe Interes") or 0))
        if f.date() < hoy:
            cron["vencido"] += imp
        else:
            k = f.date().replace(day=1)
            cron[k] += imp
            cron_banco[(k, d["Banco"], d["Linea / Producto"])] += imp
    D["cron"], D["cron_banco"] = cron, cron_banco

    # ---- Deuda Impositiva pendiente por mes
    ws = wb["Deuda Impositiva"]
    filas = list(ws.iter_rows(values_only=True))
    enc_i = filas[0]
    imp_mes = defaultdict(float)
    for r in filas[1:]:
        d = dict(zip(enc_i, r))
        f = d.get("Fecha Vencimiento")
        if not f or str(d.get("Estado") or "").lower().startswith("pag"):
            continue
        v = float(d.get("Importe") or 0)
        if f.date() < hoy:
            imp_mes["vencido"] += v
        else:
            imp_mes[f.date().replace(day=1)] += v
    D["imp_mes"] = imp_mes
    return D


# ------------------------------------------------------------------ escenarios
def escenarios(D):
    """Devuelve {A,B,C}: por mes futuro, cuotas, impuestos, saldo y disponible. La operación es la misma."""
    cols = D["cols"]
    M = D["M"]
    hoy_mes = D["hoy"].replace(day=1)
    i_hoy = cols.index(hoy_mes)
    fut = cols[i_hoy:]                       # mes en curso + 6
    res_op = M["Resultado de la operación (antes de la deuda)"]
    acuerdos = M["Descubiertos acordados con los bancos"][i_hoy]
    saldo_sep_B = M["Saldo de bancos al cierre del mes"][i_hoy]
    cuotas_B = M["Cuotas bancarias y tarjeta"]
    imp_B = M["Impuestos: deuda y planes"]
    reg_B = M["Regularización de atrasado"]

    # lo que en el mes en curso ya está pagado (real) = lo que la Sheet muestra menos lo que el Plan pone para el mes
    plan_mes = lambda tipo, mes: sum(p["meses"].get(mes, 0) for p in D["plan"] if p["Tipo"] == tipo)
    real_cuotas_mes = cuotas_B[i_hoy] - plan_mes("Banco", hoy_mes)
    real_imp_mes = imp_B[i_hoy] - plan_mes("Impuesto", hoy_mes)

    def correr(cuotas, imp, reg):
        saldos, disp = [], []
        s = None
        for i, c in enumerate(cols):
            if i < i_hoy:
                saldos.append(M["Saldo de bancos al cierre del mes"][i]); disp.append(M["Saldo disponible (cierre + descubiertos)"][i]); continue
            if i == i_hoy:
                # el mes en curso: la Sheet ya tiene la caja real + lo que falta según el Plan; se ajusta la diferencia
                s = saldo_sep_B - (cuotas[i] - cuotas_B[i]) - (imp[i] - imp_B[i]) - (reg[i] - reg_B[i])
            else:
                s = s + res_op[i] - cuotas[i] - imp[i] - reg[i]
            saldos.append(s); disp.append(s + acuerdos)
        return {"cuotas": cuotas, "imp": imp, "reg": reg, "saldos": saldos, "disp": disp,
                "egr": [M["Total egresos de la operación"][i] + cuotas[i] + imp[i] + reg[i] for i in range(len(cols))]}

    # A · sin tocar nada: cronograma + vencimientos impositivos
    cuotas_A = [real_cuotas_mes + D["cron"].get(c, 0) if i == i_hoy else (D["cron"].get(c, 0) if i > i_hoy else cuotas_B[i]) for i, c in enumerate(cols)]
    imp_A = [real_imp_mes + D["imp_mes"].get(c, 0) if i == i_hoy else (D["imp_mes"].get(c, 0) if i > i_hoy else imp_B[i]) for i, c in enumerate(cols)]
    A = correr(cuotas_A, imp_A, [0.0] * len(cols))
    B = correr(cuotas_B, imp_B, reg_B)
    C, sup_c = escenario_c(D, correr, cols, i_hoy, real_cuotas_mes, real_imp_mes, cuotas_B, imp_B, reg_B)
    return {"A": A, "B": B, "C": C, "sup_c": sup_c, "fut": fut, "i_hoy": i_hoy, "acuerdos": acuerdos, "res_op": res_op}


def escenario_c(D, correr, cols, i_hoy, real_cuotas_mes, real_imp_mes, cuotas_B, imp_B, reg_B):
    """C · lo que haría falta: parte del Plan (B) y además
       - Nación (reprogramación) y Macro (préstamos) también a 60 cuotas, 3 meses de gracia, 3 % mensual;
       - la tarjeta AgroNación diferida en 6 resúmenes en lugar de 3;
       - SICORE en 24 cuotas en lugar de 12.
       Es lo que hay que pedir para que en marzo el disponible vuelva a ser positivo."""
    hoy_mes = cols[i_hoy]
    def mas_meses(d, k):
        y, mth = d.year, d.month + k
        while mth > 12:
            y += 1; mth -= 12
        return d.replace(year=y, month=mth)
    tasa, n_c, gracia = 0.03, 60, 3
    primer = mas_meses(hoy_mes, gracia + 1)
    cuotas = defaultdict(float)
    imp = defaultdict(float)
    sup = []
    refi = {}
    for p in D["plan"]:
        cap = float(p["Deuda total hoy"] or 0)
        conc = str(p["Concepto"])
        if p["Tipo"] == "Banco":
            if p["Acreedor"] == "NACION" and "AgroNación" in conc:
                for k in range(6):
                    cuotas[mas_meses(hoy_mes, k)] += cap / 6
                sup.append("AgroNación ($%s M) en 6 resúmenes en vez de 3" % mm_(cap))
            elif p["Acreedor"] in ("NACION", "MACRO") and ("Reprog" in conc or "Préstamo" in conc) and cap > 0:
                # la cuota de este mes se paga; después, gracia y cuota nueva
                cuotas[hoy_mes] += p["meses"].get(hoy_mes, 0)
                c = pmt(cap, tasa, n_c)
                for k in range(gracia + 1, 7):
                    cuotas[mas_meses(hoy_mes, k)] += c
                refi[p["Acreedor"]] = (refi.get(p["Acreedor"], (0, 0))[0] + cap, refi.get(p["Acreedor"], (0, 0))[1] + c)
            else:
                for mes, v in p["meses"].items():
                    cuotas[mes] += v
        elif p["Tipo"] == "Impuesto":
            if conc == "SICORE":
                c = pmt(cap, 0.03, 24)
                for k in range(2, 7):
                    imp[mas_meses(hoy_mes, k)] += c
                sup.append("SICORE ($%s M) en 24 cuotas → $%s M/mes" % (mm_(cap), mm_(c)))
            else:
                for mes, v in p["meses"].items():
                    imp[mes] += v
    for bco, (cap, c) in refi.items():
        sup.append("préstamos de %s ($%s M) a %d cuotas con %d meses de gracia al %d %% → $%s M/mes" % (nom(bco), mm_(cap), n_c, gracia, int(tasa * 100), mm_(c)))
    cu = [real_cuotas_mes + cuotas.get(c, 0) if i == i_hoy else (cuotas.get(c, 0) if i > i_hoy else cuotas_B[i]) for i, c in enumerate(cols)]
    im = [real_imp_mes + imp.get(c, 0) if i == i_hoy else (imp.get(c, 0) if i > i_hoy else imp_B[i]) for i, c in enumerate(cols)]
    return correr(cu, im, [0.0] * len(cols)), sup


# ------------------------------------------------------------------ piezas del PDF
def celda_num(v, bold=False):
    if v is None:
        return ""
    txt = mm_(v)
    st = ParagraphStyle("n", parent=PR.b, fontName="Helvetica-Bold" if bold else "Helvetica", fontSize=8.2, leading=10.5, alignment=2, spaceAfter=0)
    return Paragraph(('<font color="#B3261E">%s</font>' % txt) if v < 0 else txt, st)


def tabla_meses(D, esc, titulo, nota, resumida=False):
    cols = D["cols"]
    M = D["M"]
    i_hoy = D["hoy"].replace(day=1)
    enc = [""] + [lab(c) for c in cols]
    def fila(nombre, vals, bold=False):
        return [Paragraph(("<b>%s</b>" if bold else "%s") % nombre, ParagraphStyle("l", parent=PR.b, fontSize=8.2, leading=10.5, spaceAfter=0))] + [celda_num(v, bold) for v in vals]
    filas = [[Paragraph(x, ParagraphStyle("h", parent=PR.b, fontSize=8, leading=10, alignment=2 if i else 0, spaceAfter=0, textColor=TENUE)) for i, x in enumerate(enc)],
             ["", ] + [Paragraph("real" if c < i_hoy else ("real + est." if c == i_hoy else "est."), ParagraphStyle("h", parent=PR.b, fontSize=6.8, leading=8, alignment=2, spaceAfter=0, textColor=TENUE)) for c in cols],
             fila("Resultado de la operación", M["Resultado de la operación (antes de la deuda)"], True),
             fila("Cuotas bancos y tarjeta", esc["cuotas"]),
             fila("Impuestos: deuda y planes", esc["imp"]),
             fila("Resultado después de la deuda", [M["Resultado de la operación (antes de la deuda)"][i] - esc["cuotas"][i] - esc["imp"][i] - esc["reg"][i] for i in range(len(cols))], True),
             fila("Saldo en bancos al cierre", esc["saldos"]),
             fila("Disponible (con descubiertos)", esc["disp"], True)]
    if not resumida:
        filas[2:2] = [fila("Ingresos", M["Total ingresos"]), fila("Egresos de la operación", M["Total egresos de la operación"])]
    k = 0 if resumida else 2
    t = tabla(filas, [38 * mm] + [13.2 * mm] * len(cols), chico=True)
    t.setStyle(TableStyle([("LINEABOVE", (0, 2 + k), (-1, 2 + k), 0.8, TENUE), ("LINEABOVE", (0, 5 + k), (-1, 5 + k), 0.8, TENUE),
                           ("BACKGROUND", (0, 7 + k), (-1, 7 + k), colors.HexColor("#FFF8E1")),
                           ("BACKGROUND", (1, 0), (3, -1), colors.HexColor("#F3FAF5")),
                           ("BOTTOMPADDING", (0, 1), (-1, 1), 1), ("TOPPADDING", (0, 1), (-1, 1), 0)]))
    return KeepTogether([P(titulo, "h3"), t, P(nota, "nota")])


def grafico(D, ESC):
    """Disponible mes a mes en los tres escenarios."""
    cols = D["cols"]
    i0 = ESC["i_hoy"]
    xs = cols[i0:]
    W, H = 170 * mm, 54 * mm
    d = Drawing(W, H)
    izq, der, arr, aba = 14 * mm, 4 * mm, 6 * mm, 10 * mm
    series = [("A · sin tocar nada", ESC["A"]["disp"][i0:], ROJO), ("B · plan propuesto", ESC["B"]["disp"][i0:], AZUL), ("C · lo que haría falta", ESC["C"]["disp"][i0:], VERDE)]
    vals = [v for _, s, _ in series for v in s] + [0]
    lo, hi = min(vals), max(vals)
    lo, hi = min(lo, 0) * 1.08 - (hi - lo) * 0.22, max(hi, 0) * 1.08 + 1      # aire abajo para la leyenda
    def X(i):
        return izq + (W - izq - der) * i / (len(xs) - 1)
    def Y(v):
        return aba + (H - arr - aba) * (v - lo) / (hi - lo)
    # grilla
    paso = 100e6
    v = (int(lo / paso)) * paso
    while v <= hi:
        d.add(Line(izq, Y(v), W - der, Y(v), strokeColor=LINEA if v else TENUE, strokeWidth=0.8 if v == 0 else 0.4))
        d.add(String(izq - 2 * mm, Y(v) - 2.5, mm_(v), fontName="Helvetica", fontSize=6.5, fillColor=TENUE, textAnchor="end"))
        v += paso
    for i, c in enumerate(xs):
        d.add(String(X(i), 2 * mm, lab(c), fontName="Helvetica", fontSize=7, fillColor=SUAVE, textAnchor="middle"))
    x_leg = izq + 2 * mm
    for k, (nombre, s, col) in enumerate(series):
        d.add(PolyLine([(X(i), Y(v)) for i, v in enumerate(s)], strokeColor=col, strokeWidth=1.6))
        y_leg = aba + 3 * mm + (len(series) - 1 - k) * 4 * mm      # abajo a la izquierda: ahí no pasa ninguna línea
        d.add(Line(x_leg, y_leg + 1, x_leg + 5 * mm, y_leg + 1, strokeColor=col, strokeWidth=1.6))
        d.add(String(x_leg + 6.5 * mm, y_leg - 1, "%s · marzo: %s" % (nombre, mm_(s[-1])), fontName="Helvetica-Bold", fontSize=6.8, fillColor=col))
    return d


def pie(canvas, doc, hoy_txt):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(TENUE)
    canvas.drawString(20 * mm, 12 * mm, "NAVAR S.A. · Situación de caja y plan · finauto · %s" % hoy_txt)
    canvas.drawRightString(190 * mm, 12 * mm, "Confidencial · página %d" % doc.page)
    canvas.restoreState()


# ------------------------------------------------------------------ el documento
def armar(D, out):
    hoy = D["hoy"]
    hoy_txt = hoy.strftime("%d/%m/%Y")
    ult = D["ultimo_extracto"].strftime("%d/%m")
    M = D["M"]
    ESC = escenarios(D)
    A, B, C = ESC["A"], ESC["B"], ESC["C"]
    cols = D["cols"]
    i0 = ESC["i_hoy"]
    fut = cols[i0 + 1:]

    # números de cabecera
    bancos = {k: v for k, v in D["bancos"].items() if k != "Varios"}
    saldo_bancos = sum(bancos.values())
    caja_aa = D["bancos"].get("Varios", 0)
    desc_usado = -sum(v for v in bancos.values() if v < 0)
    acuerdos = ESC["acuerdos"]
    deuda_bancos = sum(float(l["Capital Vigente"] or 0) for l in D["lineas"] if "escubierto" not in str(l["Linea / Producto"]))
    deuda_bancos_plan = sum(float(p["Deuda total hoy"] or 0) for p in D["plan"] if p["Tipo"] == "Banco")
    deuda_imp = sum(float(p["Deuda total hoy"] or 0) for p in D["plan"] if p["Tipo"] == "Impuesto")
    atrasado = M["Total atrasado a pagar"][0]
    at = {k: M[k][0] for k in ("Proveedores A vencidos", "Proveedores AA vencidos", "Cuotas bancarias impagas", "Impuestos vencidos", "Cheques propios vencidos sin debitar")}
    res_op_fut = [ESC["res_op"][i] for i in range(i0 + 1, len(cols))]
    cap_min, cap_max = min(res_op_fut), max(res_op_fut)
    cuotas_A_fut = [A["cuotas"][i] + A["imp"][i] for i in range(i0 + 1, len(cols))]
    cuotas_B_fut = [B["cuotas"][i] + B["imp"][i] for i in range(i0 + 1, len(cols))]
    ing_base = sum(M["Total ingresos"][:3]) / 3          # los préstamos ya no están en ingresos (van en Deuda)
    PREST = M.get("Préstamos tomados (entra plata: resta)", [0.0] * len(cols))
    NOPAG = M.get("Venció en el período y no se pagó (proveedores + impuestos)", [0.0] * len(cols))
    HONESTO = M.get("Resultado de la operación pagando lo que vencía", [0.0] * len(cols))
    egr_base = sum(M["Total egresos de la operación"][:3]) / 3

    doc = SimpleDocTemplate(out, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=20 * mm,
                            title="NAVAR S.A. · Situación de caja y plan", author="finauto")
    S = []

    # ---------------------------------------------------------------- portada
    S += [P("NAVAR S.A.", "h2"), P("Situación de caja y plan", "titulo"),
          P("Dónde está la caja hoy, qué pasa en los próximos seis meses si no se toca nada, qué proponemos y qué hace falta pedir. Datos reales hasta el %s (último extracto); lo demás es estimación y está marcado. %s." % (ult, hoy_txt), "sub"),
          kpis([(m(saldo_bancos, True), "en cuentas corrientes al %s (5 bancos)" % ult, ROJO),
                (m(atrasado, True), "atrasado: proveedores, cuotas, impuestos, cheques", ROJO),
                (m(deuda_bancos_plan, True), "deuda con bancos (capital, sin descubiertos)", TINTA),
                (m(deuda_imp, True), "deuda impositiva", TINTA)]),
          Spacer(1, 8),
          P("En una página", "h1"),
          P("<b>La operación, por banco, da; pagando todo lo que vence, no.</b> En los tres meses cerrados entraron en promedio %s por mes (cobranzas, cheques depositados y descontados; sin préstamos) y salieron %s (proveedores, sueldos, impuestos corrientes, banco): quedaron entre %s y %s por mes. Pero en esos mismos meses vencieron y no se pagaron %s, %s y %s de facturas e impuestos. <b>Pagando lo que vencía, la operación queda alrededor de cero.</b> Proyectado a seis meses, con lo que vence según Tango, deja entre %s y %s por mes: esa es la <b>capacidad de pago</b> para toda la deuda, y solo existe si el atrasado deja de crecer." % (m(ing_base, True), m(egr_base, True), m(min(M["Resultado de la operación (antes de la deuda)"][:3]), True), m(max(M["Resultado de la operación (antes de la deuda)"][:3]), True), m(NOPAG[0], True), m(NOPAG[1], True), m(NOPAG[2], True), m(cap_min, True), m(cap_max, True)), "grande"),
          P("<b>La deuda pide el doble.</b> Sin tocar nada, entre octubre y marzo las cuotas de bancos, tarjeta e impuestos piden entre %s y %s por mes. Con el plan propuesto bajan a %s–%s, y todavía quedan por encima de lo que la operación deja en la mitad de los meses." % (m(min(cuotas_A_fut), True), m(max(cuotas_A_fut), True), m(min(cuotas_B_fut), True), m(max(cuotas_B_fut), True)), "grande"),
          P("<b>Ya no hay colchón.</b> Los descubiertos están usados (%s sobre %s acordados), hay %s atrasados y Corrientes informa situación 3. Septiembre cierra en %s en bancos porque en lo que queda del mes vencen, según Tango, más pagos de los que entran." % (m(desc_usado, True), m(acuerdos, True), m(atrasado, True), m(B["saldos"][i0], True)), "grande"),
          caja([P("No es un problema de caja: es una estructura de deuda que se está pagando con caja, y la caja no alcanza. La salida tiene tres partes que van juntas: (1) refinanciar a un número que la operación pueda pagar, (2) proteger lo que no puede cortarse (ARCA, sueldos, los bancos que descuentan los cheques) y (3) decidir cada semana, con el cash a la vista, qué se paga y qué no. <b>El plan de este documento es una propuesta: que cada banco la acepte es otra negociación, y por eso se muestra también qué pasa si dicen que no.</b>", "p")], borde=ROJO),
          ]

    # ---------------------------------------------------------------- 1 · de dónde sale
    S += [PageBreak(), P("1 · De dónde salen los números", "h1"),
          P("Todo lo que dice este documento sale de la planilla «NAVAR - Cash Flow», y la planilla sale de datos, no de estimaciones a mano:", "p"),
          LI("<b>Extractos de los cinco bancos</b>, junio a septiembre: cada movimiento real, clasificado (cobranza, descuento de cheques, proveedores, sueldos, cuotas, impuestos, intereses). Saldo real por cuenta y por día hasta el %s." % ult),
          LI("<b>Tango</b>: cuentas a cobrar y a pagar con vencimiento, cartera de cheques, recibos y órdenes de pago."),
          LI("<b>Mapa de deuda bancaria</b> (planilla de NAVAR al 09/09, revisada): %d productos en 5 bancos, cuota por cuota." % len(D["lineas"])),
          LI("<b>Deuda impositiva</b>: la planilla de Celia revisada por el estudio contable el 18/09."),
          LI("<b>Respuestas de Priscilla</b> (18/09) sobre lo que los extractos no explican solos: venta de valores, tarjeta AgroNación, cheques, sueldos, la caja de AA."),
          P("Cómo se proyecta", "h2"),
          P("Lo que se repite (cobranza, cheques, sueldos, impuestos corrientes, intereses) se proyecta como el promedio de los tres meses cerrados × %.1f %% mensual de inflación. Lo que tiene fecha (cuotas, planes, cheques, facturas de Tango) va por su fecha. Para el mes en curso se suma lo real hasta el %s más lo que falta. Es exactamente la cuenta que hace la solapa «Cash Mensual» de la planilla, donde la inflación es una celda editable." % (D["inflacion"] * 100, ult), "p"),
          P("Lo que NO está y hay que tener presente", "h2"),
          LI("La <b>cosecha</b> (abril a septiembre) ya pasó este año y no vuelve como tal: para 2027 NAVAR planea comprar canchada y vender molida, sin cosecha ni secanza propias (Priscilla, 21/09). Ese costo entra como compra a proveedores; la proyección no tiene un renglón de cosecha."),
          LI("La caja de <b>AA</b> es efectivo (%s al 21/09, arqueo semanal los lunes): se carga a mano y no se mueve en la proyección." % m(caja_aa, True)),
          LI("Corrientes: el límite del acuerdo en cuenta corriente. Nación: la hipoteca «La Gloria» y la tarjeta corporativa, sin importe. Macro: el límite usado de la venta de valores."),
          ]

    # ---------------------------------------------------------------- 2 · la foto
    orden = ["NACION", "CORRIENTES", "MACRO", "GALICIA", "BBVA"]
    que = {"NACION": "el 14/09 pagaron la AgroNación y una cuota impaga con el descubierto nuevo; vuelven a situación 1",
           "CORRIENTES": "en el límite; 4 préstamos con cuotas impagas, situación 3, refinanciación en curso",
           "MACRO": "por acá pagan sueldos y entra la venta de valores (descuento de cheques)",
           "GALICIA": "descuenta cheques: es el motor de la caja",
           "BBVA": "cuota de septiembre sin fondos, colgada"}
    fb = [["Banco", "Saldo al %s" % ult, "Descubierto acordado", "Disponible", "Qué se ve"]]
    for bco in orden:
        s = bancos.get(bco, 0)
        ac = D["descubiertos"].get(bco, 0)
        disp = max(0.0, s + ac)
        fb.append([nom(bco), m(s, True), m(ac, True) if ac else "sin acuerdo", m(disp, True) + ("" if s + ac >= 0 else " (excedido %s)" % m(-(s + ac), True)), que[bco]])
    fb.append([Paragraph("<b>Total</b>", E["p"]), Paragraph("<b>%s</b>" % m(saldo_bancos, True), E["p"]), m(acuerdos, True), Paragraph("<b>%s</b>" % m(sum(max(0.0, bancos.get(b, 0) + D["descubiertos"].get(b, 0)) for b in orden), True), E["p"]), "más la caja de AA en efectivo: %s" % m(caja_aa, True)])
    por_banco = defaultdict(float)
    for p in D["plan"]:
        if p["Tipo"] == "Banco":
            por_banco[p["Acreedor"]] += float(p["Deuda total hoy"] or 0)
    det_bancos = " · ".join("%s %s" % (nom(b), m(v, True)) for b, v in sorted(por_banco.items(), key=lambda x: -x[1]))
    imp_det = " · ".join("%s %s" % (conc(p["Concepto"]), m(float(p["Deuda total hoy"]), True)) for p in sorted([p for p in D["plan"] if p["Tipo"] == "Impuesto"], key=lambda p: -float(p["Deuda total hoy"] or 0))[:5])
    S += [PageBreak(), P("2 · La foto real de hoy", "h1"),
          P("Bancos (cuentas corrientes, último extracto)", "h2"),
          tabla(fb, [22 * mm, 22 * mm, 26 * mm, 30 * mm, 70 * mm], chico=True),
          P("Deuda (capital) y atrasado", "h2"),
          tabla([["Concepto", "Monto", "Detalle"],
                 ["Bancos: préstamos, tarjetas, descuento de cheques", m(deuda_bancos_plan, True), det_bancos + " · más %s de descubiertos usados, que ya están en el saldo" % m(desc_usado, True)],
                 ["Impuestos", m(deuda_imp, True), imp_det],
                 ["Proveedores vencidos (Tango, sin la deuda vieja)", m(at["Proveedores A vencidos"] + at["Proveedores AA vencidos"], True), "A %s · AA %s" % (m(at["Proveedores A vencidos"], True), m(at["Proveedores AA vencidos"], True))],
                 ["Cuotas bancarias impagas", m(at["Cuotas bancarias impagas"], True), "Corrientes (junio a septiembre) y BBVA (septiembre)"],
                 ["Impuestos vencidos", m(at["Impuestos vencidos"], True), "lo urgente antes del 25/09 según el estudio: SICORE julio, planes ARCA, Misiones, DGR"],
                 ["Cheques propios vencidos sin debitar", m(at["Cheques propios vencidos sin debitar"], True), "a confirmar: varios parecen pagados según el extracto"],
                 [Paragraph("<b>Atrasado total a pagar</b>", E["p"]), Paragraph("<b>%s</b>" % m(atrasado, True), E["p"]), "no está en ningún mes de la proyección: se paga por decisión, y esa decisión se carga en la solapa Plan"]],
                [58 * mm, 20 * mm, 92 * mm], chico=True),
          ]

    # ---------------------------------------------------------------- 3 · tres meses reales
    S += [PageBreak(), P("3 · Los tres meses reales: qué entra y qué sale", "h1"),
          P("Junio, julio y agosto según el extracto (no según Tango ni la planilla vieja). Es la base de toda la proyección.", "p")]
    ren_ing = ["Cobranza acreditada", "Cheques de clientes (depositados y descontados)"]
    ren_egr = ["Proveedores A", "Sueldos y cargas", "Impuestos corrientes", "Cheques propios", "Intereses y gastos bancarios", "Otros (tarjeta, honorarios)"]
    fr = [["", lab(cols[0]), lab(cols[1]), lab(cols[2]), "promedio"]]
    def f3(nombre, vals, bold=False):
        return [Paragraph(("<b>%s</b>" if bold else "%s") % nombre, ParagraphStyle("l", parent=PR.b, fontSize=8.4, leading=11, spaceAfter=0))] + [celda_num(v, bold) for v in vals[:3]] + [celda_num(sum(vals[:3]) / 3, bold)]
    for r in ren_ing:
        fr.append(f3(r, M[r]))
    fr.append(f3("Total ingresos", M["Total ingresos"], True))
    for r in ren_egr:
        fr.append(f3(r, M[r]))
    fr.append(f3("Total egresos de la operación", M["Total egresos de la operación"], True))
    fr.append(f3("Resultado de la operación por banco (sin préstamos)", M["Resultado de la operación (antes de la deuda)"], True))
    fr.append(f3("Venció en el mes y no se pagó (proveedores + impuestos)", NOPAG))
    fr.append(f3("Resultado de la operación pagando lo que vencía", HONESTO, True))
    fr.append(f3("Cuotas bancarias y tarjeta pagadas", M["Cuotas bancarias y tarjeta"]))
    fr.append(f3("Préstamos tomados", [-v for v in PREST]))
    fr.append(f3("Resultado después de la deuda (por banco)", M["Resultado después de la deuda"], True))
    t = tabla(fr, [70 * mm, 25 * mm, 25 * mm, 25 * mm, 25 * mm], chico=True)
    t.setStyle(TableStyle([("LINEABOVE", (0, 3), (-1, 3), 0.8, TENUE), ("LINEABOVE", (0, 10), (-1, 10), 0.8, TENUE),
                           ("BACKGROUND", (0, 11), (-1, 11), colors.HexColor("#FFF8E1")), ("BACKGROUND", (0, 13), (-1, 13), ROJO_FONDO),
                           ("TEXTCOLOR", (0, 12), (0, 12), ROJO)]))
    S += [t, P("en millones de $ · «Proveedores A» es lo que salió del banco a proveedores · «Venció y no se pagó» son las facturas de proveedores e impuestos con vencimiento en ese mes que siguen impagos hoy (Tango y planilla de impuestos) · los préstamos entran en el bloque de deuda, no en la operación", "nota"),
          caja([P("<b>Por banco, la operación da positiva: entre %s y %s por mes.</b> Pero da positiva porque no se pagó todo lo que venció: en julio quedaron sin pagar %s de facturas e impuestos, en agosto %s. <b>Pagando lo que vencía, la operación queda entre %s y %s por mes: alrededor de cero.</b> Ese es el número real de la operación, y es el que explica por qué el atrasado crece cada mes. Lo que no está acá, porque no pasa por el banco: la operación de AA en efectivo (a cobrar %s, a pagar %s pendientes) y los cheques de clientes que se endosan directamente a proveedores (unos %s por mes según Tango: entran y salen sin tocar la cuenta)." % (
              m(min(M["Resultado de la operación (antes de la deuda)"][:3]), True), m(max(M["Resultado de la operación (antes de la deuda)"][:3]), True),
              m(NOPAG[1], True), m(NOPAG[2], True), m(min(HONESTO[:3]), True), m(max(HONESTO[:3]), True),
              m(96e6, True), m(170e6, True), m(150e6, True)), "p")], borde=ROJO)]

    # ---------------------------------------------------------------- 4 · seis meses
    S += [PageBreak(), P("4 · Los próximos seis meses, en tres escenarios", "h1"),
          P("La operación es la misma en los tres (lo que proyecta la planilla). Lo que cambia es la deuda: cómo están las cuotas hoy, cómo quedan con la propuesta, y qué haría falta pedir para volver a cero.", "p"),
          grafico(D, ESC),
          P("Saldo disponible al cierre de cada mes (saldo en bancos + descubiertos acordados), en millones de $. Por debajo de cero: no se cubre lo comprometido ni usando todo el descubierto.", "nota"),
          Spacer(1, 4),
          tabla_meses(D, A, "A · Sin tocar nada: pagando todo lo que vence como está", "en millones de $ · cuotas según el cronograma de cada banco y vencimientos impositivos con fecha · lo vencido de hoy no está en ningún mes"),
          Spacer(1, 6),
          P("Cierra en <b>%s</b> de disponible en marzo. Octubre y noviembre son los peores meses: las cuotas del cronograma piden %s y %s con una operación que deja %s y %s." % (m(A["disp"][-1], True), m(A["cuotas"][i0 + 1], True), m(A["cuotas"][i0 + 2], True), m(ESC["res_op"][i0 + 1], True), m(ESC["res_op"][i0 + 2], True)), "p"),
          caja([P("Lo que los tres escenarios dicen, con todas sus aproximaciones: <b>la capacidad de pago de NAVAR para toda su deuda es de %s a %s por mes</b>. Cualquier acuerdo con un banco o con ARCA que sume más que eso se rompe al segundo mes. Y el agujero de septiembre (%s) hay que taparlo con algo que no sea caja de la operación." % (m(cap_min, True), m(cap_max, True), m(B["saldos"][i0], True)), "p")], borde=AMBAR),
          PageBreak(),
          tabla_meses(D, B, "B · El plan propuesto (lo que está cargado en la solapa Plan)", "en millones de $ · misma operación que en A · Corrientes, Galicia y BBVA refinanciados a 48–60 cuotas con 3 meses de gracia al 3 % mensual · Nación y Macro se pagan como están · SICORE en 12 cuotas · tasa de comercio e inmobiliario pospuestos · lo vencido con proveedores no se regulariza en estos seis meses", resumida=True),
          Spacer(1, 6),
          P("Cierra en <b>%s</b> de disponible en marzo: <b>frena la caída pero no recupera el pozo de septiembre</b>. De diciembre en adelante la operación y la deuda quedan parejas (resultado después de la deuda cerca de cero). Es lo que se puede pedir hoy sin tocar a los dos bancos que están al día." % m(B["disp"][-1], True), "p"),
          Spacer(1, 4),
          tabla_meses(D, C, "C · Lo que haría falta para volver a cero", "en millones de $ · todo lo de B, y además: " + "; ".join(ESC["sup_c"]), resumida=True),
          Spacer(1, 6),
          P("Cierra en <b>%s</b> de disponible en marzo, con el saldo en bancos en %s. Es decir: <b>para que las cuentas vuelvan a cero hace falta refinanciar toda la deuda bancaria, incluidos los dos bancos que hoy están al día, y estirar ARCA</b>. Y aun así quedan meses en rojo: %s. Ese bache no sale de la operación: sale de un aporte, de la venta de un activo, de adelantar cobranza o de stock." % (m(C["disp"][-1], True), m(C["saldos"][-1], True), ", ".join("%s (%s)" % (lab(cols[i]), m(C["disp"][i], True)) for i in range(i0, len(cols)) if C["disp"][i] < 0) or "ninguno"), "p"),
          ]

    # ---------------------------------------------------------------- 5 · el plan, banco por banco
    fut6 = cols[i0 + 1:]
    fp = [["Acreedor", "Deuda hoy", "Cronograma oct–mar", "Propuesta", "Queda oct–mar", "Si dicen que no"]]
    por_acreedor = defaultdict(lambda: {"deuda": 0.0, "cron": 0.0, "plan": 0.0, "dec": set(), "conc": []})
    for p in D["plan"]:
        if p["Tipo"] != "Banco":
            continue
        a = por_acreedor[p["Acreedor"]]
        a["deuda"] += float(p["Deuda total hoy"] or 0)
        a["plan"] += sum(p["meses"].get(mth, 0) for mth in fut6)
        a["dec"].add(p["Decisión"])
        if p["Decisión"] == "Refinanciar":
            a["conc"].append((float(p["Deuda total hoy"] or 0), int(p["Cuotas nuevas"] or 0), int(p["Meses de gracia"] or 0), float(p["Cuota nueva"] or 0), lab(p["Primer vencimiento"].date()) if p["Primer vencimiento"] else "—"))
    for (mth, bco, _), v in D["cron_banco"].items():
        if mth in fut6:
            por_acreedor[bco]["cron"] += v
    for bco in orden:
        a = por_acreedor[bco]
        if "Refinanciar" in a["dec"]:
            cs = a["conc"]
            prop = "Refinanciar %s (%s): %s cuotas con %s meses de gracia → %s por mes desde %s" % (
                "%d préstamos" % len(cs) if len(cs) > 1 else "el préstamo", m(sum(c[0] for c in cs), True),
                "/".join(sorted({str(c[1]) for c in cs})), "/".join(sorted({str(c[2]) for c in cs})), m(sum(c[3] for c in cs), True), cs[0][4])
            sino = "marzo: %s menos de disponible" % m(a["cron"] - a["plan"], True)
        else:
            prop = "Pagar como está: " + ("está al día y descuenta cheques; no tocar" if bco == "MACRO" else "recién reprogramado; no perder la situación 1")
            sino = "—"
        fp.append([nom(bco), m(a["deuda"], True), m(a["cron"], True), prop, m(a["plan"], True), sino])
    S += [PageBreak(), P("5 · El plan, acreedor por acreedor: qué se pide y qué pasa si dicen que no", "h1"),
          P("Lo que está cargado en la solapa Plan. Cada fila es una negociación distinta, con su propio tiempo; lo que ya está en curso (Corrientes) es lo más probable.", "p"),
          tabla(fp, [20 * mm, 18 * mm, 20 * mm, 66 * mm, 18 * mm, 28 * mm], chico=True),
          P("«Pide el cronograma» y «Queda» son la suma de cuotas de octubre a marzo. La diferencia es lo que se le pide al banco que postergue en estos seis meses.", "nota"),
          P("ARCA y provincia", "h2"),
          tabla([["Concepto", "Deuda hoy", "Propuesta", "Por qué"]] +
                [[conc(p["Concepto"]), m(float(p["Deuda total hoy"] or 0), True),
                  (p["Decisión"] + (": %d cuotas de %s desde %s" % (int(p["Cuotas nuevas"] or 0), m(float(p["Cuota nueva"] or 0), True), lab(p["Primer vencimiento"].date())) if p["Decisión"] == "Refinanciar" and p["Primer vencimiento"] else "")),
                  p["Por qué"]] for p in sorted([p for p in D["plan"] if p["Tipo"] == "Impuesto" and float(p["Deuda total hoy"] or 0) >= 10e6], key=lambda p: -float(p["Deuda total hoy"] or 0))],
                [40 * mm, 20 * mm, 50 * mm, 60 * mm], chico=True),
          P("Impuestos menores a $10 M (patentes, bienes personales, IVA) no se listan; están en la solapa Plan.", "nota"),
          caja([P("<b>Antes de ir a un banco.</b> Un plan armado en una planilla y un plan aprobado por un comité de crédito son dos cosas distintas. Corrientes ya está en refinanciación; Galicia y BBVA hay que pedirlos; Nación y Macro conviene no tocarlos hasta que los otros tres estén cerrados. Cada «no» tiene su número en la última columna.", "p")], borde=AZUL),
          ]

    # ---------------------------------------------------------------- 6 · prioridades
    S += [PageBreak(), P("6 · Prioridades de pago: por consecuencia, no por antigüedad", "h1"),
          P("La prioridad no es «a quién le debemos más» sino «qué pasa si no pagamos». Es la que está cargada en la columna Prioridad de la solapa Plan y se ajusta con Priscilla.", "p"),
          tabla([["Prioridad", "A quién", "Por qué", "Qué pasa si no"],
                 ["1", "ARCA / DGR (vencimientos urgentes y planes)", "es el único acreedor que embarga cuentas", "embargo → se frena todo"],
                 ["2", "Sueldos y cargas", "la operación no anda sin la gente", "conflicto, paro"],
                 ["2", "Galicia y Macro (cuotas y acuerdos)", "descuentan los cheques: son el motor de la caja", "cierran la línea → sin caja"],
                 ["3", "Nación y BBVA", "recién reprogramado / al día: no perder la situación 1", "vuelve a situación 2, pierden el crédito"],
                 ["4", "Tarjetas (AgroNación, Visa)", "financian proveedores; se paga el resumen o se corta la tarjeta", "se corta la financiación de proveedores"],
                 ["5", "Corrientes (préstamos)", "ya está en situación 3 y en refinanciación", "el daño ya está hecho; se negocia el plan"],
                 ["6", "Proveedores de hoja y cosecha, después el resto", "sin hoja no hay producto; los demás según tolerancia", "cortan la entrega / el crédito comercial"],
                 ["8", "Tasa de comercio, patentes, inmobiliario", "no embargan rápido", "intereses"]],
                [16 * mm, 48 * mm, 58 * mm, 48 * mm], chico=True),
          ]

    # ---------------------------------------------------------------- 7 · esta semana y cómo sigue
    urg = D["imp_mes"].get(hoy.replace(day=1), 0)
    S += [P("Esta semana: que no se corte nada vital", "h3"),
          LI("<b>ARCA</b>: los vencimientos de septiembre que quedan (%s según la planilla de impuestos) y lo urgente que marcó el estudio antes del 25/09. Un embargo de cuentas frena la operación entera." % m(urg, True)),
          LI("<b>Sueldos</b> del 1 al 10 de octubre por Macro."),
          LI("<b>Nación</b>: la cuota de septiembre. Acaban de usar el descubierto para volver a situación 1: no tirarlo."),
          LI("<b>Galicia y Macro</b>: las cuotas de fin de mes. Son los bancos que descuentan los cheques."),
          PageBreak(), P("7 · Accionables y cómo sigue", "h1"),
          tabla([["Qué", "Quién", "Cuándo"],
                 ["Confirmar el orden de prioridades y las decisiones de la solapa Plan", "Priscilla + Thomas", "esta semana"],
                 ["Pagar lo urgente de ARCA y generar los VEP", "Celia / Charles", "antes del 25/09"],
                 ["Pedir al estudio el plan más largo posible para SICORE y cargas sociales", "Celia + estudio", "semana del 22/09"],
                 ["Corrientes: cerrar la refinanciación en curso con 60 cuotas y gracia", "Charles / María Rosa", "en curso"],
                 ["Galicia y BBVA: pedir la refinanciación con el número de capacidad de pago", "Charles / María Rosa", "semana del 28/09"],
                 ["Cargar la caja de AA cada día y el plan de compra de canchada 2027 en la planilla", "Priscilla", "esta semana"],
                 ["Definir con qué se tapa el agujero de septiembre (aporte, activo, adelanto de cobranza, stock)", "Dueños", "antes de octubre"],
                 ["Revisión semanal del cash: disponible, qué se paga, qué se pospone", "Priscilla + Thomas", "todos los lunes"]],
                [92 * mm, 42 * mm, 36 * mm], chico=True),
          P("Cómo se va a manejar el cash de acá en adelante", "h3"),
          P("La planilla tiene tres pantallas (día por día, semana por semana, mes por mes) que son fórmula sobre listas: movimientos y saldos de banco, facturas de Tango, cheques, deuda bancaria e impositiva. Nadie tipea un número en una pantalla: cuando un banco debita una cuota, la deuda baja sola; cuando entra un préstamo, suben las cuotas futuras. Las decisiones (qué se paga, qué se refinancia, qué se pospone) se cargan en la solapa Plan y el mes por mes se recalcula. Cada lunes se cargan los extractos y Tango, se mira el disponible de la semana y se decide. La regla operativa: <b>no se compromete un peso que el disponible de la semana no muestre.</b>", "p"),
          P("Preguntas abiertas (las que cambian los números)", "h3"),
          LI("<b>Compra de canchada 2027</b>: a quién, cuánto por mes y con qué plazo de pago; es lo que reemplaza a la cosecha en la proyección."),
          LI("<b>Proveedores de hoja</b>: quiénes, cuánto se les debe, cuánto aguantan."),
          LI("<b>Corrientes</b>: qué proponen en la refinanciación (plazo, gracia, tasa)."),
          LI("<b>Galicia</b>: la cuota real del préstamo y si renovaron la línea de descuento."),
          LI("<b>Dueños</b>: si hay aporte, activo para vender o cobranza que se pueda adelantar."),
          caja([P("Cómo seguimos: esta semana se confirma el plan en la planilla; desde ahí, cada lunes el cash dice cuánto hay, qué vence y qué se paga. Las decisiones son de NAVAR; el cash las hace visibles antes, no después.", "p")], borde=VERDE),
          ]

    doc.build(S, onFirstPage=lambda c, d: pie(c, d, hoy_txt), onLaterPages=lambda c, d: pie(c, d, hoy_txt))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", default=None, help="export de la Sheet a Excel (default: el último en privado/)")
    ap.add_argument("--hoy", default=datetime.date.today().isoformat())
    a = ap.parse_args()
    hoy = datetime.date.fromisoformat(a.hoy)
    D = leer(a.sheet or ultimo_export(), hoy)
    out = os.path.join(BASE_REPO, "clientes", "navar", "privado", "salidas", "NAVAR - Situación y plan %s.pdf" % hoy.isoformat())
    armar(D, out)
    print(out)
