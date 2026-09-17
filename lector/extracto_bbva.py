# -*- coding: utf-8 -*-
"""
lector.extracto_bbva — de los extractos del BBVA a las listas del Cashflow.

PARA QUE
--------
Hasta que corran los bots, los extractos llegan a mano: el PDF del resumen
mensual y el Excel de "últimos movimientos" del home banking. Este módulo los
lee y arma dos cosas que el Cashflow espera:

    Saldos Bancarios   el saldo REAL de cada cuenta en cada fecha (fin de mes
                       de cada PDF + día por día del Excel)
    Movimientos        cada movimiento real, clasificado con el vocabulario de
                       la planilla (Cobranza Facturas, Proveedores, Prestamo,
                       Impuestos, Transferencia Interna...)

Es el molde para los otros bancos: cada uno tiene su formato de PDF y de
Excel, pero el resultado es el mismo. Cuando lleguen Nación, Corrientes, Macro
y Galicia se copia la estructura y se cambian los parsers.

LO QUE HAY QUE SABER DE BBVA (NAVAR, 17/09/2026)
------------------------------------------------
- Dos cuentas: la PRINCIPAL (489-000765/9) y la de RECAUDACIÓN (489-000806/5).
  Los clientes depositan en la de recaudación ("OPERACION DE RECAUDO") y el
  banco la barre a la principal el mismo día ("TRANSFERENCIA CUENTAS PAIS").
  Por eso la cobranza se cuenta UNA vez, en recaudación; el barrido es interno.
- El Excel trae dos saldos que NO coinciden: el "Saldo Disponible" de cada día
  y el "Saldo:" del encabezado. Se verificó contra el PDF (17/09/2026): la
  cadena de "Saldo Disponible" reproduce al centavo el saldo del resumen
  (407.033,87 al 11/08 + todos los movimientos = 6.405.116,16 al 16/09). El
  encabezado (-9.134.993,63) es 15,5 M más bajo: operaciones pendientes que
  el banco ya descuenta (cheques a debitar, débitos programados) pero que
  todavía no son movimientos. Se usa el disponible como saldo contable y la
  diferencia se informa como "pendiente", a confirmar en el home banking.
- Transferencias al CUIT propio (30-55852502-5) son plata que se mueve a
  otro banco de NAVAR: internas, no gasto.
- "DEBITO CUOTA 243-96-00432582" es la cuota del préstamo BBVA (~$15,8 M por
  mes, el 30). Sale como Prestamo.

DEDUPLICACIÓN
-------------
El PDF de agosto y el Excel de "últimos 60 días" se pisan (29/07 → 11/08). Un
movimiento se considera el mismo si coinciden fecha, importe y cuenta. Gana el
PDF (es el documento oficial); el Excel aporta lo que el PDF todavía no tiene.

Uso:
    python lector/extracto_bbva.py --carpeta clientes/navar/privado/bancos/bbva --cliente navar

Deja en la carpeta:
    para_pegar_bancos_bbva_<fecha>.xlsx   solapas "Saldos Bancarios" y "Movimientos"
    resumen_bbva_<fecha>.md               qué se leyó, saldos, y cómo se clasificó
"""

import io
import os
import re
import sys
import glob
import json
import argparse
import datetime
import unicodedata
from collections import OrderedDict, defaultdict

BASE_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)

import openpyxl

BANCO = "BBVA"
NUM = r'-?\d{1,3}(?:\.\d{3})*,\d{2}'

# Encabezados de las solapas del Cashflow, tal cual.
ENC_SALDOS = ["Fecha", "Banco", "Empresa", "Cuenta / Nro", "Saldo (caja real, sin cheques)", "Origen", "Observaciones"]
ENC_MOV = ["ID", "Fecha", "Empresa", "Tipo", "Categoria", "Concepto / Detalle", "Importe", "Medio de Pago",
           "Banco / Cuenta", "Origen", "Estado", "Referencia", "Semana (lunes)", "Observaciones"]
COLS_CON_FORMULA = {"Semana (lunes)"}


# ------------------------------------------------------------------ helpers
def _num(s):
    return float(str(s).replace(".", "").replace(",", "."))


def _norm(s):
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode()
    return " ".join(s.upper().split())


def _m(v):
    return "$" + format(int(round(abs(v))), ",d").replace(",", ".")


# ------------------------------------------------------------------ PDF (resumen mensual)
def leer_pdf(ruta):
    """El resumen mensual. Devuelve {cuenta, anio, mes, saldo_cierre, fecha_cierre, movimientos}."""
    from pypdf import PdfReader
    txt = "\n".join((p.extract_text() or "") for p in PdfReader(ruta).pages)
    m = re.search(r'(\d\d)-(\d\d)\.pdf$', os.path.basename(ruta))
    anio, mes = (2000 + int(m.group(1)), int(m.group(2))) if m else (None, None)
    cuenta = re.search(r'CC \$ (\d{3}-\d{6}/\d)', txt)
    cuenta = cuenta.group(1) if cuenta else "?"
    cierre = re.search(r'SALDO AL (\d+) DE (\w+) (' + NUM + ')', txt)
    MESES = {"ENERO": 1, "FEBRERO": 2, "MARZO": 3, "ABRIL": 4, "MAYO": 5, "JUNIO": 6, "JULIO": 7,
             "AGOSTO": 8, "SEPTIEMBRE": 9, "OCTUBRE": 10, "NOVIEMBRE": 11, "DICIEMBRE": 12}
    fecha_cierre = saldo_cierre = None
    if cierre:
        mes_c = MESES.get(cierre.group(2).upper(), mes)
        fecha_cierre = datetime.date(anio or datetime.date.today().year, mes_c, int(cierre.group(1)))
        saldo_cierre = _num(cierre.group(3))
    movs = []
    for fe, con, imp, sal in re.findall(r'^(\d\d/\d\d)\s+(.*?)\s+(' + NUM + r')\s+(' + NUM + r')\s*$', txt, re.M):
        d, mm = int(fe[:2]), int(fe[3:5])
        # El resumen de un mes puede arrancar con movimientos del último día del mes anterior.
        a = anio or datetime.date.today().year
        if mes and mm > mes and mes == 1:
            a -= 1
        try:
            fecha = datetime.date(a, mm, d)
        except ValueError:
            continue
        movs.append({"fecha": fecha, "concepto": " ".join(con.split()), "importe": _num(imp),
                     "saldo": _num(sal), "cuenta": cuenta, "fuente": "pdf"})
    return {"cuenta": cuenta, "anio": anio, "mes": mes, "fecha_cierre": fecha_cierre,
            "saldo_cierre": saldo_cierre, "movimientos": movs, "archivo": os.path.basename(ruta)}


# ------------------------------------------------------------------ XLS (home banking, últimos 60 días)
def leer_xls(ruta):
    """El export del home banking. Devuelve {cuenta, cuit, saldo_actual, acuerdo, movimientos, saldos_por_dia}."""
    import xlrd
    sh = xlrd.open_workbook(ruta).sheets()[0]
    cab = {str(sh.cell_value(r, 0)).strip(": "): str(sh.cell_value(r, 1)).strip() for r in range(6)}
    cuit = re.search(r'\((\d{11})\)', cab.get("Empresa", ""))
    cuit = cuit.group(1) if cuit else None
    cuenta = re.search(r'(\d{3}-\d{6}/\d)', cab.get("Cuenta", ""))
    cuenta = cuenta.group(1) if cuenta else "?"
    saldo_actual = _num(cab.get("Saldo", "0"))
    enc = [str(sh.cell_value(6, c)).strip() for c in range(sh.ncols)]
    ix = {e: i for i, e in enumerate(enc)}
    movs, disponible_por_dia = [], OrderedDict()
    for r in range(7, sh.nrows):
        f = str(sh.cell_value(r, ix["Fecha"]))
        if not re.match(r'\d\d-\d\d-\d{4}', f):
            continue
        fecha = datetime.date(int(f[6:10]), int(f[3:5]), int(f[:2]))
        cr, db = sh.cell_value(r, ix["Crédito"]), sh.cell_value(r, ix["Débito"])
        importe = float(cr or 0) if cr not in ("", None) else float(db or 0)
        if not importe:
            continue
        # El "Saldo Disponible" viene en la última columna, que no tiene encabezado.
        extra = " ".join(str(sh.cell_value(r, c)) for c in range(ix["Detalle"], sh.ncols))
        m = re.search(r'Saldo Disponible:\s*(' + NUM + ')', extra)
        if m and fecha not in disponible_por_dia:
            disponible_por_dia[fecha] = _num(m.group(1))     # primera fila del día = cierre del día
        movs.append({"fecha": fecha, "concepto": " ".join(str(sh.cell_value(r, ix["Concepto"])).split()),
                     "importe": importe, "detalle": str(sh.cell_value(r, ix["Detalle"])).strip(),
                     "codigo": str(sh.cell_value(r, ix["Codigo"])).strip(), "cuenta": cuenta, "fuente": "xls"})
    # El "Saldo Disponible" del día es el contable (verificado contra el PDF). Lo que
    # el encabezado descuenta de más son operaciones pendientes: se informa aparte.
    hoy_disp = next(iter(disponible_por_dia.values()), None)
    pendiente = (hoy_disp - saldo_actual) if hoy_disp is not None else 0.0
    saldos = OrderedDict(disponible_por_dia)
    return {"cuenta": cuenta, "cuit": cuit, "saldo_actual": saldo_actual, "pendiente": pendiente,
            "saldo_contable_hoy": hoy_disp,
            "fecha_saldo": max(disponible_por_dia) if disponible_por_dia else None,
            "movimientos": movs, "saldos_por_dia": saldos, "archivo": os.path.basename(ruta)}


# ------------------------------------------------------------------ clasificación
# Cada regla: (texto que tiene que estar en el concepto normalizado, categoría de la
# planilla, medio de pago, interno). Se prueban en orden; la primera que matchea gana.
# Las categorías tienen que existir en catalogo.mapa_categorias (egresos / ingresos).
REGLAS_EGRESO = [
    ("DEBITO CU", "Prestamo", "Débito automático", False),
    ("PAGOS AFIP", "Impuestos", "Transferencia", False),
    ("INTERES SALDO DEUDOR", "Impuestos", "Débito automático", False),   # interés del descubierto: costo financiero
    ("TRANSFERENCIA CUENTAS PAIS", "Transferencia Interna", "Transferencia", True),
    ("TRANSFERENCIA CCP", "Transferencia Interna", "Transferencia", True),
    ("IMP.LEY", "Impuestos", "Débito automático", False),
    ("IMPUESTO LEY", "Impuestos", "Débito automático", False),
    ("LEY NRO", "Impuestos", "Débito automático", False),
    ("SIRCREB", "Impuestos", "Débito automático", False),
    ("SIRC", "Impuestos", "Débito automático", False),
    ("PERCEP", "Impuestos", "Débito automático", False),
    ("IVA", "Impuestos", "Débito automático", False),
    ("INGR.BRUTOS", "Impuestos", "Débito automático", False),
    ("INGRESOS BRUTOS", "Impuestos", "Débito automático", False),
    ("TUCUMA", "Impuestos", "Débito automático", False),
    ("SELLOS", "Impuestos", "Débito automático", False),
    ("COMISION", "Otros", "Débito automático", False),
    ("COM MANT", "Otros", "Débito automático", False),
    ("COMI TRANSF", "Otros", "Débito automático", False),
    ("PAGO DE SERVICIOS TARJETA", "Otros", "Débito automático", False),
    ("PAGO SERVICI", "Otros", "Débito automático", False),
    ("DEBITO DIRECTO", "Otros", "Débito automático", False),
    ("DEBITO", "Otros", "Débito automático", False),
    ("CHEQUE", "Cheques", "Cheque Propio", False),
    ("TRANSFERENCI", "Proveedores MP y Logist.", "Transferencia", False),   # a un CUIT: proveedor, salvo que sea el propio
    ("TRF", "Proveedores MP y Logist.", "Transferencia", False),
]
REGLAS_INGRESO = [
    ("OPERACION DE R", "Cobranza Facturas", "Efectivo", False),             # recaudación: cliente deposita
    ("TRANSFERENCIA CUENTAS PAIS", "Transferencia Interna", "Transferencia", True),
    ("TRANSFERENCIA CCP", "Transferencia Interna", "Transferencia", True),
    ("TR.NE", "Transferencia Interna", "Transferencia", True),              # viene de otra cuenta de NAVAR
    ("DEPOSITO CHEQUE", "Cheques", "Cheque de Terceros", False),
    ("DEPOSITO", "Transferencia Interna", "Efectivo", True),                # depósito en efectivo: caja propia al banco (revisar)
    ("DNET", "Cobranza Facturas", "Transferencia", False),
    ("BANEL", "Cobranza Facturas", "Transferencia", False),
    ("TRANSFERENCI", "Cobranza Facturas", "Transferencia", False),
]


def clasificar(mov, cuit_propio):
    """-> (tipo, categoria, medio, interno, nota)."""
    c = _norm(mov["concepto"])
    v = mov["importe"]
    reglas = REGLAS_INGRESO if v > 0 else REGLAS_EGRESO
    # Transferencia al CUIT propio: interna, aunque la regla genérica diga proveedor.
    cuit = re.search(r'\b(\d{11})\b', c)
    if cuit and cuit_propio and cuit.group(1) == cuit_propio:
        return ("Ingreso" if v > 0 else "Egreso", "Transferencia Interna", "Transferencia", True,
                "al/del CUIT propio (otra cuenta de NAVAR)")
    for texto, cat, medio, interno in reglas:
        if texto in c:
            nota = ""
            if cat == "Proveedores MP y Logist." and cuit:
                nota = "CUIT %s-%s-%s: proveedor a identificar" % (cuit.group(1)[:2], cuit.group(1)[2:10], cuit.group(1)[10:])
            if texto == "DEPOSITO":
                nota = "depósito en efectivo: ¿caja propia o cliente? revisar"
            if texto == "TR.NE":
                nota = "transferencia desde una cuenta de NAVAR en otro banco"
            return ("Ingreso" if v > 0 else "Egreso", cat, medio, interno, nota)
    return ("Ingreso" if v > 0 else "Egreso", "Otros", "", False, "sin regla: revisar")


# ------------------------------------------------------------------ armado
def procesar(carpeta, cliente, empresa="A"):
    pdfs = [leer_pdf(r) for r in sorted(glob.glob(os.path.join(carpeta, "*.pdf")))]
    xlss = [leer_xls(r) for r in sorted(glob.glob(os.path.join(carpeta, "*.xls*")))
            if not os.path.basename(r).startswith("para_pegar")]
    cuit_propio = next((x["cuit"] for x in xlss if x.get("cuit")), None)

    # ---- saldos: fin de mes de cada PDF + día por día del Excel
    saldos = []
    for p in pdfs:
        if p["fecha_cierre"] is not None:
            saldos.append({"fecha": p["fecha_cierre"], "cuenta": p["cuenta"], "saldo": p["saldo_cierre"],
                           "origen": "Extracto %s (PDF %s)" % (BANCO, p["archivo"]), "obs": "saldo de cierre del resumen"})
    for x in xlss:
        for f, s in x["saldos_por_dia"].items():
            saldos.append({"fecha": f, "cuenta": x["cuenta"], "saldo": s,
                           "origen": "Home banking %s (%s)" % (BANCO, x["archivo"]),
                           "obs": "saldo contable del día (cadena verificada contra el PDF)"})
    saldos.sort(key=lambda s: (s["cuenta"], s["fecha"]))

    # ---- movimientos: PDF manda; el Excel agrega lo que el PDF no tiene
    vistos, movs = set(), []
    for p in pdfs:
        for m in p["movimientos"]:
            vistos.add((m["cuenta"], m["fecha"], round(m["importe"], 2)))
            movs.append(m)
    dup = 0
    for x in xlss:
        for m in x["movimientos"]:
            k = (m["cuenta"], m["fecha"], round(m["importe"], 2))
            if k in vistos:
                dup += 1
                continue
            vistos.add(k)
            movs.append(m)
    movs.sort(key=lambda m: (m["fecha"], m["cuenta"]))

    filas, por_cat = [], defaultdict(lambda: [0, 0.0])
    for i, m in enumerate(movs, 1):
        tipo, cat, medio, interno, nota = clasificar(m, cuit_propio)
        obs = "Extracto %s · %s%s" % (BANCO, m["fuente"].upper(), (" · " + nota) if nota else "")
        if interno:
            obs = "INTERNO (no es ingreso ni gasto) · " + obs
        filas.append(OrderedDict([
            ("ID", i), ("Fecha", m["fecha"]), ("Empresa", empresa), ("Tipo", tipo), ("Categoria", cat),
            ("Concepto / Detalle", m["concepto"] + ((" · " + m.get("detalle")) if m.get("detalle") else "")),
            ("Importe", round(m["importe"], 2)), ("Medio de Pago", medio),
            ("Banco / Cuenta", "%s %s" % (BANCO, m["cuenta"])), ("Origen", "Extracto %s" % BANCO),
            ("Estado", "Real"), ("Referencia", m.get("codigo") or None), ("Semana (lunes)", None),
            ("Observaciones", obs),
        ]))
        por_cat[(tipo, cat, "interno" if interno else "")][0] += 1
        por_cat[(tipo, cat, "interno" if interno else "")][1] += m["importe"]

    return {"pdfs": pdfs, "xlss": xlss, "cuit": cuit_propio, "saldos": saldos, "movimientos": filas,
            "por_cat": por_cat, "duplicados": dup}


def escribir_para_pegar(res, carpeta, hoy):
    ruta = os.path.join(carpeta, "para_pegar_bancos_%s_%s.xlsx" % (BANCO.lower(), hoy.isoformat()))
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet("Saldos Bancarios")
    ws.append(ENC_SALDOS)
    for s in res["saldos"]:
        ws.append([s["fecha"], BANCO, "A", s["cuenta"], round(s["saldo"], 2), s["origen"], s["obs"]])
    ws2 = wb.create_sheet("Movimientos")
    ws2.append(ENC_MOV)
    for x in res["movimientos"]:
        ws2.append([None if c in COLS_CON_FORMULA else x.get(c) for c in ENC_MOV])
    for w in (ws, ws2):
        for fila in w.iter_rows(min_row=2):
            for c in fila:
                if isinstance(c.value, datetime.date):
                    c.number_format = "DD/MM/YYYY"
    wb.save(ruta)
    return ruta


def escribir_sheet_con_extracto(res, sheet_original, hoy, empresa="A"):
    """Copia del Cashflow con las filas de este banco cargadas (para correr finauto sin esperar).

    En Movimientos y Saldos Bancarios: se borran las filas que ya eran de este banco
    (Origen dice BBVA) y se agregan las nuevas debajo de lo que haya. Las columnas
    con fórmula (Semana) no se tocan."""
    base, ext = os.path.splitext(sheet_original)
    destino = "%s (con %s %s)%s" % (base, BANCO, hoy.isoformat(), ext)
    wb = openpyxl.load_workbook(sheet_original)

    def _volcar(nombre, enc_nuestro, filas, es_de_este_banco):
        ws = wb[nombre]
        enc = [str(c.value).strip() if c.value is not None else "" for c in ws[1]]
        idx_origen = next((i for i, e in enumerate(enc) if e.lower().startswith("origen")), None)
        idx_nombre = 1
        escribibles = [(j, e) for j, e in enumerate(enc, start=1) if e and e not in COLS_CON_FORMULA]
        vivas, ultima = [], 1
        for i, f in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if f[idx_nombre] in (None, ""):
                continue
            ultima = i
            if idx_origen is not None and es_de_este_banco(f[idx_origen]):
                continue
            vivas.append(f)
        for i in range(2, ultima + 1):
            for j, _ in escribibles:
                ws.cell(row=i, column=j).value = None
        fila = 2
        for f in vivas:
            for j, _ in escribibles:
                ws.cell(row=fila, column=j).value = f[j - 1]
            fila += 1
        for x in filas:
            for j, e in escribibles:
                v = x.get(e)
                c = ws.cell(row=fila, column=j)
                c.value = v
                if isinstance(v, datetime.date):
                    c.number_format = "DD/MM/YYYY"
            fila += 1
        # renumerar ID si la solapa lo tiene
        if enc and enc[0] == "ID":
            for i in range(2, fila):
                ws.cell(row=i, column=1).value = i - 1
        return len(vivas), len(filas)

    de_bbva = lambda o: BANCO.upper() in str(o or "").upper()
    saldos = [OrderedDict([("Fecha", s["fecha"]), ("Banco", BANCO), ("Empresa", empresa),
                           ("Cuenta / Nro", s["cuenta"]), ("Saldo (caja real, sin cheques)", round(s["saldo"], 2)),
                           ("Origen", s["origen"]), ("Observaciones", s["obs"])]) for s in res["saldos"]]
    r1 = _volcar("Saldos Bancarios", ENC_SALDOS, saldos, de_bbva)
    r2 = _volcar("Movimientos", ENC_MOV, res["movimientos"], de_bbva)
    wb.save(destino)
    return destino, {"Saldos Bancarios": r1, "Movimientos": r2}


def resumen(res, ruta_pegar, hoy):
    L = ["# Extractos %s → Cashflow · %s" % (BANCO, hoy.strftime("%d/%m/%Y")), ""]
    L.append("CUIT de la empresa (del home banking): **%s**" % (res["cuit"] or "no encontrado"))
    L.append("")
    L.append("## Archivos")
    for p in res["pdfs"]:
        L.append("- PDF `%s` · cuenta %s · %d movimientos · saldo al %s: **%s%s**"
                 % (p["archivo"], p["cuenta"], len(p["movimientos"]),
                    p["fecha_cierre"].strftime("%d/%m/%Y") if p["fecha_cierre"] else "?",
                    "-" if (p["saldo_cierre"] or 0) < 0 else "", _m(p["saldo_cierre"] or 0)))
    for x in res["xlss"]:
        sc = x["saldo_contable_hoy"] if x["saldo_contable_hoy"] is not None else x["saldo_actual"]
        L.append("- Excel `%s` · cuenta %s · %d movimientos · saldo contable al %s: **%s%s**%s"
                 % (x["archivo"], x["cuenta"], len(x["movimientos"]),
                    x["fecha_saldo"].strftime("%d/%m/%Y") if x["fecha_saldo"] else "?",
                    "-" if sc < 0 else "", _m(sc),
                    (" · el encabezado dice %s%s: hay ~%s de operaciones pendientes que el banco ya descuenta (confirmar en el home banking)"
                     % ("-" if x["saldo_actual"] < 0 else "", _m(x["saldo_actual"]), _m(x["pendiente"])))
                    if abs(x["pendiente"]) > 1 else ""))
    L.append("- movimientos que estaban en el PDF y en el Excel (se tomaron una vez): %d" % res["duplicados"])
    L.append("")
    L.append("## Saldos por cuenta (los que van a Saldos Bancarios)")
    ult = {}
    for s in res["saldos"]:
        ult[s["cuenta"]] = s
    for cta, s in sorted(ult.items()):
        L.append("- %s: **%s%s** al %s" % (cta, "-" if s["saldo"] < 0 else "", _m(s["saldo"]), s["fecha"].strftime("%d/%m/%Y")))
    L.append("")
    L.append("## Movimientos por categoría (%d en total)" % len(res["movimientos"]))
    for (tipo, cat, interno), (n, tot) in sorted(res["por_cat"].items(), key=lambda kv: kv[1][1]):
        L.append("- %s · %s%s: %d por %s%s" % (tipo, cat, (" (interno)" if interno else ""), n,
                                              "-" if tot < 0 else "", _m(tot)))
    sin_regla = [x for x in res["movimientos"] if "sin regla" in x["Observaciones"]]
    if sin_regla:
        L.append("")
        L.append("## Sin regla (quedaron en 'Otros', revisar)")
        for x in sin_regla[:20]:
            L.append("- %s %s %s" % (x["Fecha"].strftime("%d/%m"), x["Concepto / Detalle"][:60], _m(x["Importe"])))
    L.append("")
    L.append("## Archivo generado")
    L.append("- `%s`: solapas Saldos Bancarios y Movimientos, para pegar en el Cashflow (Semana (lunes) va vacía: es fórmula)." % ruta_pegar)
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="Extractos BBVA (PDF + Excel del home banking) -> listas del Cashflow")
    ap.add_argument("--carpeta", required=True)
    ap.add_argument("--cliente", required=True)
    ap.add_argument("--empresa", default="A", help="A o AA: de qué empresa de la planilla son estas cuentas")
    ap.add_argument("--hoy", default=None)
    ap.add_argument("--sheet", default=None, help="copia del Cashflow (.xlsx) a la que agregarle estas filas")
    a = ap.parse_args()
    hoy = datetime.date.fromisoformat(a.hoy) if a.hoy else datetime.date.today()
    res = procesar(a.carpeta, a.cliente, a.empresa)
    ruta = escribir_para_pegar(res, a.carpeta, hoy)
    txt = resumen(res, ruta, hoy)
    if a.sheet:
        destino, cuantas = escribir_sheet_con_extracto(res, a.sheet, hoy, a.empresa)
        txt += "\n- copia del Cashflow con %s: `%s` (%s)" % (
            BANCO, destino, "; ".join("%s: quedaron %d filas de otros + %d nuevas" % (k, v[0], v[1]) for k, v in cuantas.items()))
    with io.open(os.path.join(a.carpeta, "resumen_%s_%s.md" % (BANCO.lower(), hoy.isoformat())), "w", encoding="utf-8") as f:
        f.write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
