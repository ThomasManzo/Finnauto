# -*- coding: utf-8 -*-
"""
lector.extractos — de los extractos de los bancos a las listas del Cashflow.

PARA QUE
--------
Hasta que corran los bots, los extractos llegan a mano: el PDF del resumen
mensual y el Excel de "últimos movimientos" del home banking. Este módulo los
lee, banco por banco, y arma las dos cosas que el Cashflow espera:

    Saldos Bancarios   el saldo REAL de cada cuenta, día por día
    Movimientos        cada movimiento real, clasificado con el vocabulario de
                       la planilla (Cobranza Facturas, Proveedores, Prestamo,
                       Impuestos, Gastos Bancarios, Transferencia Interna...)

Cada banco tiene su formato; lo que sale es siempre lo mismo. Un banco nuevo =
una función `leer_pdf_<banco>` y/o `leer_planilla_<banco>` que devuelva la
misma estructura, y una entrada en BANCOS.

    privado/bancos/<banco>/*.pdf, *.xls, *.xlsx   ->   ESTE MODULO
        -> para_pegar_bancos_<fecha>.xlsx   (Saldos Bancarios + Movimientos)
        -> resumen_bancos_<fecha>.md        (qué se leyó, saldos, clasificación)
        -> copia del Cashflow con las filas  (si se pasa --sheet)

LO QUE HAY QUE SABER DE CADA BANCO (NAVAR, 17/09/2026)
------------------------------------------------------
BBVA     Dos cuentas: PRINCIPAL 489-000765/9 y RECAUDACIÓN 489-000806/5. Los
         clientes depositan en recaudación ("OPERACION DE RECAUDO") y el banco
         la barre a la principal el mismo día ("TRANSFERENCIA CUENTAS PAIS").
         La cobranza se cuenta UNA vez, en recaudación; el barrido es interno.
         El Excel trae dos saldos: el "Saldo Disponible" de cada día ES el
         contable (verificado contra el PDF al centavo); el "Saldo:" del
         encabezado es 15,5 M más bajo: operaciones pendientes que el banco ya
         descuenta. Se usa el disponible y la diferencia se informa aparte.
GALICIA  CC 0005459-5 070-1. Acuerdo de descubierto $10 M (47% TNA) y tasa
         extraordinaria 59% sobre lo excedido. En el PDF la descripción de un
         movimiento ocupa varias líneas; el importe y el saldo van al final.
         "CREDITO DESCUENTO DOCUMENTO" = plata que entra por descontar cheques.
MACRO    CC 3-033-0000083019-1, en descubierto permanente (~-$50 M) con
         intereses "INTER.ADEL.CC C/ACUERD". El PDF trae débitos y créditos en
         columnas distintas: el signo se deduce de la POSICIÓN del importe en
         la línea (débitos antes de la columna 82, créditos después). "N/D DB PAGO REMUNERACIONES" son
         los sueldos. "N/C DEUD. PUBLICA-P.PREVIO" (~$20 M dos veces por mes)
         es una acreditación que hay que preguntar: entra como financiación.
CORRIENTES  Cta Cte Empresa 130559 (suc. 10 Virasoro), un solo PDF 01/06 →
         17/09. Vive en -$42 M exactos: el banco cobra las cuotas de préstamo
         y devuelve el saldo al límite ("Pago Automatico Prestamo"). Importes
         en formato inglés (1,566,916.00) y a veces el saldo viene pegado a un
         número de referencia.
NACIÓN   No hay extracto: solo la pantalla de "Posición del cliente" (3270)
         del 17/09: cuentas corrientes -$101,7 M, préstamos $550,9 M. Se carga
         como un saldo manual con esa fecha, marcado como captura.

DEDUPLICACIÓN
-------------
PDF y Excel se pisan en el tiempo. Un movimiento es el mismo si coinciden
banco, cuenta, fecha e importe. Gana el PDF (documento oficial); el Excel
aporta lo que el PDF todavía no tiene.

Uso:
    python lector/extractos.py --carpeta clientes/navar/privado/bancos --cliente navar
    python lector/extractos.py --carpeta ... --cliente navar --sheet "<copia del Cashflow>.xlsx"
"""

import io
import os
import re
import sys
import glob
import argparse
import datetime
import unicodedata
from collections import OrderedDict, defaultdict

BASE_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)

import openpyxl

NUM_AR = r'-?\d{1,3}(?:\.\d{3})*,\d{2}'      # 1.234.567,89
NUM_US = r'-?\d{1,3}(?:,\d{3})*\.\d{2}'      # 1,234,567.89

# Encabezados de las solapas del Cashflow, tal cual.
ENC_SALDOS = ["Fecha", "Banco", "Empresa", "Cuenta / Nro", "Saldo (caja real, sin cheques)", "Origen", "Observaciones"]
ENC_MOV = ["ID", "Fecha", "Empresa", "Tipo", "Categoria", "Concepto / Detalle", "Importe", "Medio de Pago",
           "Banco / Cuenta", "Origen", "Estado", "Referencia", "Semana (lunes)", "Observaciones"]
COLS_CON_FORMULA = {"Semana (lunes)"}

# Lo que no vino en archivo pero se vio: la pantalla de posición del Nación (17/09/2026).
SALDOS_MANUALES = [
    {"banco": "NACION", "cuenta": "CTAS.CTES. (posición del cliente)", "fecha": datetime.date(2026, 9, 17),
     "saldo": -101709806.61, "origen": "Captura pantalla 3270 Nación 17/09/2026",
     "obs": "Posición del cliente: ctas. ctes. -$101.709.806,61 (pasivo) · préstamos $550.850.851,37 · posición total -$652.485.082,98. Pedir el extracto."},
]


# ------------------------------------------------------------------ helpers
def _ar(s):
    s = str(s).strip()
    neg = s.endswith("-")
    v = float(s.rstrip("-").replace(".", "").replace(",", "."))
    return -v if neg else v


def _us(s):
    return float(str(s).replace(",", ""))


def _norm(s):
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode()
    return " ".join(s.upper().split())


def _m(v):
    return ("-" if v < 0 else "") + "$" + format(int(round(abs(v))), ",d").replace(",", ".")


def _texto_pdf(ruta):
    from pypdf import PdfReader
    return "\n".join((p.extract_text() or "") for p in PdfReader(ruta).pages)


def _fecha_ddmmyy(s):
    d, m, a = int(s[:2]), int(s[3:5]), int(s[6:8])
    return datetime.date(2000 + a, m, d)


def _mov(fecha, concepto, importe, saldo, cuenta, fuente, ref=None):
    return {"fecha": fecha, "concepto": " ".join(str(concepto).split()), "importe": round(float(importe), 2),
            "saldo": saldo, "cuenta": cuenta, "fuente": fuente, "ref": ref}


# ================================================================== BBVA
def leer_pdf_bbva(ruta):
    txt = _texto_pdf(ruta)
    m = re.search(r'(\d\d)-(\d\d)\.pdf$', os.path.basename(ruta))
    anio, mes = (2000 + int(m.group(1)), int(m.group(2))) if m else (datetime.date.today().year, None)
    cuenta = re.search(r'CC \$ (\d{3}-\d{6}/\d)', txt)
    cuenta = cuenta.group(1) if cuenta else "?"
    movs = []
    for fe, con, imp, sal in re.findall(r'^(\d\d/\d\d)\s+(.*?)\s+(' + NUM_AR + r')\s+(' + NUM_AR + r')\s*$', txt, re.M):
        d, mm = int(fe[:2]), int(fe[3:5])
        a = anio - 1 if (mes == 1 and mm == 12) else anio
        try:
            movs.append(_mov(datetime.date(a, mm, d), con, _ar(imp), _ar(sal), cuenta, "pdf"))
        except ValueError:
            continue
    return {"cuenta": cuenta, "movimientos": movs, "archivo": os.path.basename(ruta)}


def leer_planilla_bbva(ruta):
    import xlrd
    sh = xlrd.open_workbook(ruta).sheets()[0]
    cab = {str(sh.cell_value(r, 0)).strip(": "): str(sh.cell_value(r, 1)).strip() for r in range(6)}
    cuit = re.search(r'\((\d{11})\)', cab.get("Empresa", ""))
    cuenta = re.search(r'(\d{3}-\d{6}/\d)', cab.get("Cuenta", ""))
    cuenta = cuenta.group(1) if cuenta else "?"
    saldo_encabezado = _ar(cab.get("Saldo", "0"))
    enc = [str(sh.cell_value(6, c)).strip() for c in range(sh.ncols)]
    ix = {e: i for i, e in enumerate(enc)}
    movs, disp = [], OrderedDict()
    for r in range(7, sh.nrows):
        f = str(sh.cell_value(r, ix["Fecha"]))
        if not re.match(r'\d\d-\d\d-\d{4}', f):
            continue
        fecha = datetime.date(int(f[6:10]), int(f[3:5]), int(f[:2]))
        cr, db = sh.cell_value(r, ix["Crédito"]), sh.cell_value(r, ix["Débito"])
        importe = float(cr or 0) if cr not in ("", None) else float(db or 0)
        if not importe:
            continue
        extra = " ".join(str(sh.cell_value(r, c)) for c in range(ix["Detalle"], sh.ncols))
        m = re.search(r'Saldo Disponible:\s*(' + NUM_AR + ')', extra)
        if m and fecha not in disp:
            disp[fecha] = _ar(m.group(1))           # primera fila del día = cierre del día
        movs.append(_mov(fecha, sh.cell_value(r, ix["Concepto"]), importe, None, cuenta, "xls",
                         ref=str(sh.cell_value(r, ix["Codigo"])).strip()))
    hoy_disp = next(iter(disp.values()), None)
    pendiente = (hoy_disp - saldo_encabezado) if hoy_disp is not None else 0.0
    return {"cuenta": cuenta, "cuit": cuit.group(1) if cuit else None, "movimientos": movs,
            "saldos_por_dia": dict(disp), "archivo": os.path.basename(ruta),
            "nota": ("el encabezado dice %s y la cadena de saldos %s: hay ~%s de operaciones pendientes que el "
                     "banco ya descuenta (confirmar en el home banking)" % (_m(saldo_encabezado), _m(hoy_disp), _m(pendiente)))
                    if abs(pendiente) > 1 else ""}


# ================================================================== GALICIA
def leer_pdf_galicia(ruta):
    txt = _texto_pdf(ruta)
    cuenta = re.search(r'N° (\d{7}-\d \d{3}-\d)', txt)
    cuenta = cuenta.group(1) if cuenta else "?"
    txt = re.sub(r'Resumen de Cuenta Corriente en Pesos \nPágina \d+ / \d+Resumen de Cuenta Corriente en Pesos \n\S+\n'
                 r'Fecha Descripción Origen Crédito\s+Débito Saldo\n', '', txt)
    movs = []
    # La descripción puede ocupar varias líneas; importe y saldo cierran el movimiento.
    for fe, con, imp, sal in re.findall(r'(\d\d/\d\d/\d\d)\s(.*?)\s(' + NUM_AR + r')\s(' + NUM_AR + r'-?)[ \t]*\n', txt, re.S):
        movs.append(_mov(_fecha_ddmmyy(fe), con, _ar(imp), _ar(sal), cuenta, "pdf"))
    acuerdo = re.search(r'Sujeto a condiciones convenidas \$(' + NUM_AR + r') %([\d,]+) (\S+) (\S+)', txt)
    return {"cuenta": cuenta, "movimientos": movs, "archivo": os.path.basename(ruta),
            "nota": ("acuerdo de descubierto %s al %s%% TNA, vence %s" % (_m(_ar(acuerdo.group(1))), acuerdo.group(2), acuerdo.group(4)))
                    if acuerdo else ""}


def leer_planilla_galicia(ruta):
    wb = openpyxl.load_workbook(ruta, data_only=True)
    ws = wb.active
    filas = [r for r in ws.iter_rows(values_only=True)]
    enc = [str(c).strip() if c else "" for c in filas[0]]
    ix = {e: i for i, e in enumerate(enc)}
    movs = []
    for r in filas[1:]:
        f = r[ix["Fecha"]]
        if not isinstance(f, datetime.datetime):
            continue
        deb, cre = float(r[ix["Débitos"]] or 0), float(r[ix["Créditos"]] or 0)
        importe = cre if cre else -deb
        if not importe:
            continue
        extras = [str(r[ix[k]]) for k in ("Leyendas Adicionales 1", "Leyendas Adicionales 2") if r[ix[k]]]
        con = " ".join([str(r[ix["Descripción"]])] + extras)
        movs.append(_mov(f.date(), con, importe, float(r[ix["Saldo"]]) if r[ix["Saldo"]] is not None else None,
                         "0005459-5 070-1", "xlsx", ref=str(r[ix["Número de Comprobante"]] or "") or None))
    return {"cuenta": "0005459-5 070-1", "movimientos": movs, "archivo": os.path.basename(ruta)}


# ================================================================== MACRO
def leer_pdf_macro(ruta):
    txt = _texto_pdf(ruta)
    cuenta = re.search(r'CUENTA CORRIENTE BANCARIA NRO\.: (\S+)', txt)
    cuenta = cuenta.group(1) if cuenta else "?"
    ini = re.search(r'SALDO ULTIMO EXTRACTO AL \d\d/\d\d/\d{4}\s+(' + NUM_AR + ')', txt)
    prev = _ar(ini.group(1)) if ini else None
    cab = re.search(r'SALDO INICIAL\s+CREDITOS\s+DEBITOS\s+I\.V\.A\.\s+SALDO FINAL\s*\n\s*(' + NUM_AR + r')\s+(' + NUM_AR +
                    r')\s+(' + NUM_AR + r')\s+(' + NUM_AR + r')\s+(' + NUM_AR + ')', txt)
    movs = []
    # Débito o crédito: el texto extraído conserva las columnas. El importe de un
    # débito arranca antes de la columna ~82; el de un crédito, después. Es más
    # confiable que el salto del saldo (que se rompe si una línea no se lee).
    for linea in txt.split("\n"):
        m = re.match(r'^\s*(\d\d/\d\d/\d\d)\s+(.*?)\s+(' + NUM_AR + r')\s+(' + NUM_AR + r')\s*$', linea)
        if not m:
            continue
        fe, con, imp, sal = m.groups()
        pos = linea.rfind(imp, 0, linea.rfind(sal))
        signo = -1 if pos < 82 else 1
        ref = None
        partes = con.split()
        if len(partes) > 1 and re.fullmatch(r'\d+', partes[-1]):
            ref = partes[-1] if partes[-1] != "0" else None
            con = " ".join(partes[:-1])
        movs.append(_mov(_fecha_ddmmyy(fe), con, signo * abs(_ar(imp)), _ar(sal), cuenta, "pdf", ref=ref))
    control = ""
    if cab and movs:
        # El control que vale: la cadena de saldos. Si saldo final - inicial == suma de
        # movimientos, se leyeron todos y con el signo correcto. (Los "CREDITOS" y
        # "DEBITOS" del encabezado no cuadran con la suma: el banco excluye algo, no
        # se sabe qué; no sirven de control.)
        ini_v, fin_v = _ar(cab.group(1)), _ar(cab.group(5))
        suma = sum(m["importe"] for m in movs)
        ok = abs((fin_v - ini_v) - suma) < 0.01
        control = "cadena de saldos %s: inicial %s, movimientos %s, final %s" % (
            "OK" if ok else "NO CIERRA", _m(ini_v), _m(suma), _m(fin_v))
    return {"cuenta": cuenta, "movimientos": movs, "archivo": os.path.basename(ruta), "nota": control}


def leer_planilla_macro(ruta):
    import xlrd
    wb = xlrd.open_workbook(ruta)
    sh = wb.sheets()[0]
    numero = None
    for r in range(min(10, sh.nrows)):
        if str(sh.cell_value(r, 0)).strip() == "Número":
            numero = str(sh.cell_value(r, 2)).strip()
    cuenta = "3-033-0000083019-1" if numero and numero.endswith("830191") else (numero or "?")
    movs = []
    for r in range(sh.nrows):
        v = sh.cell_value(r, 0)
        if not isinstance(v, float):
            continue
        fecha = datetime.date(*xlrd.xldate_as_tuple(v, wb.datemode)[:3])
        importe = sh.cell_value(r, 6)
        if importe in ("", None):
            continue
        saldo = sh.cell_value(r, 10)
        movs.append(_mov(fecha, sh.cell_value(r, 5), float(importe), float(saldo) if saldo not in ("", None) else None,
                         cuenta, "xls", ref=str(sh.cell_value(r, 3)).strip() or None))
    return {"cuenta": cuenta, "movimientos": movs, "archivo": os.path.basename(ruta)}


# ================================================================== CORRIENTES
def leer_pdf_corrientes(ruta):
    txt = _texto_pdf(ruta)
    cuenta = re.search(r'^(\d{6}) NAVAR', txt, re.M)
    cuenta = cuenta.group(1) if cuenta else "?"
    movs = []
    for fe, con, ref, dh, imp, sal, _resto in re.findall(
            r'^(\d\d/\d\d/\d\d)\s+(.*?)\s+(\S+)\s+(Db|Cr)\s+(' + NUM_US + r')\s+(' + NUM_US + r')(\S*)\s*$', txt, re.M):
        v = _us(imp) * (1 if dh == "Cr" else -1)
        movs.append(_mov(_fecha_ddmmyy(fe), con, v, _us(sal), cuenta, "pdf", ref=ref if ref != "0" else None))
    return {"cuenta": cuenta, "movimientos": movs, "archivo": os.path.basename(ruta)}


# ================================================================== registro de bancos
BANCOS = OrderedDict([
    ("bbva", {"nombre": "BBVA", "pdf": leer_pdf_bbva, "planilla": leer_planilla_bbva}),
    ("galicia", {"nombre": "GALICIA", "pdf": leer_pdf_galicia, "planilla": leer_planilla_galicia}),
    ("macro", {"nombre": "MACRO", "pdf": leer_pdf_macro, "planilla": leer_planilla_macro}),
    ("corrientes", {"nombre": "CORRIENTES", "pdf": leer_pdf_corrientes, "planilla": None}),
])


# ================================================================== clasificación
# (texto en el concepto normalizado, categoría de la planilla, medio, interno).
# Se prueban en orden; la primera que matchea gana. Las categorías tienen que
# existir en catalogo.mapa_categorias.
REGLAS_EGRESO = [
    ("CUOTA PRESTAMO", "Prestamo", "Débito automático", False),
    ("CUOTA DE PRESTAMO", "Prestamo", "Débito automático", False),
    ("DEBITO PRESTAMOS", "Prestamo", "Débito automático", False),
    ("PAGO AUTOMATICO PRESTAMO", "Prestamo", "Débito automático", False),
    ("PAGO DOCUMENTOS", "Prestamo", "Débito automático", False),
    ("DEBITO CU", "Prestamo", "Débito automático", False),
    ("REMUNERACIONES", "Sueldos y Jornales", "Transferencia", False),
    ("HABERES", "Sueldos y Jornales", "Transferencia", False),
    ("AFIP", "Impuestos", "Transferencia", False),
    ("ARCA", "Impuestos", "Transferencia", False),
    ("COMPRA/CES. CHQ", "Cheques", "Cheque Propio", False),
    ("TEF DATANET BTOB", "Proveedores MP y Logist.", "Transferencia", False),
    ("PAGO SERV", "Otros", "Débito automático", False),
    ("BURO", "Otros", "Débito automático", False),
    ("VEP", "Impuestos", "Transferencia", False),
    ("DGR", "Impuestos", "Débito automático", False),
    ("SELLOS", "Impuestos", "Débito automático", False),
    ("SIRCREB", "Impuestos", "Débito automático", False),
    ("SIRC", "Impuestos", "Débito automático", False),
    ("IIBB", "Impuestos", "Débito automático", False),
    ("ING. BRUTOS", "Impuestos", "Débito automático", False),
    ("INGR.BRUTOS", "Impuestos", "Débito automático", False),
    ("INGRESOS BRUTOS", "Impuestos", "Débito automático", False),
    ("25413", "Impuestos", "Débito automático", False),
    ("25.4", "Impuestos", "Débito automático", False),
    ("IMP.LEY", "Impuestos", "Débito automático", False),
    ("IMPUESTO LEY", "Impuestos", "Débito automático", False),
    ("LEY NRO", "Impuestos", "Débito automático", False),
    ("DEBITO FISCAL", "Impuestos", "Débito automático", False),
    ("PERCEP", "Impuestos", "Débito automático", False),
    ("RETENCION", "Impuestos", "Débito automático", False),
    ("RET.", "Impuestos", "Débito automático", False),
    ("RET ", "Impuestos", "Débito automático", False),
    ("TUCUMA", "Impuestos", "Débito automático", False),
    ("IVA", "Impuestos", "Débito automático", False),
    ("I.V.A", "Impuestos", "Débito automático", False),
    ("INTERES", "Gastos Bancarios", "Débito automático", False),
    ("INTER.", "Gastos Bancarios", "Débito automático", False),
    ("SOBREGIRO", "Gastos Bancarios", "Débito automático", False),
    ("COMISION", "Gastos Bancarios", "Débito automático", False),
    ("COM.", "Gastos Bancarios", "Débito automático", False),
    ("COMI ", "Gastos Bancarios", "Débito automático", False),
    ("COM MANT", "Gastos Bancarios", "Débito automático", False),
    ("MANTENIMIENTO", "Gastos Bancarios", "Débito automático", False),
    ("SERVICIO DE CUENTA", "Gastos Bancarios", "Débito automático", False),
    ("ADM.VALORES", "Gastos Bancarios", "Débito automático", False),
    ("GESTION DE CHEQ", "Gastos Bancarios", "Débito automático", False),
    ("TRANSFERENCIA CUENTAS PAIS", "Transferencia Interna", "Transferencia", True),
    ("TRANSFERENCIA CCP", "Transferencia Interna", "Transferencia", True),
    ("CUENTA PROPIA", "Transferencia Interna", "Transferencia", True),
    ("TRANSF INMED CP", "Transferencia Interna", "Transferencia", True),
    ("TR.NE", "Transferencia Interna", "Transferencia", True),
    ("CHEQUE", "Cheques", "Cheque Propio", False),
    ("CH.", "Cheques", "Cheque Propio", False),
    ("OSDE", "Sueldos y Jornales", "Transferencia", False),
    ("OBRA SOCIAL", "Sueldos y Jornales", "Transferencia", False),
    ("T.CREDITO", "Otros", "Débito automático", False),
    ("TARJETA", "Otros", "Débito automático", False),
    ("PAGO DE SERVICIOS", "Otros", "Débito automático", False),
    ("PAGO SERVICI", "Otros", "Débito automático", False),
    ("DEBITO DIRECTO", "Otros", "Débito automático", False),
    ("DEBITO", "Otros", "Débito automático", False),
    (" HON", "Honorarios y Dividendos", "Transferencia", False),
    ("TRANSF", "Proveedores MP y Logist.", "Transferencia", False),
    ("TRF", "Proveedores MP y Logist.", "Transferencia", False),
    ("E-SET", "Proveedores MP y Logist.", "Transferencia", False),
    ("MACRONLINE", "Proveedores MP y Logist.", "Transferencia", False),
]
REGLAS_INGRESO = [
    ("TRANSFERENCIA CUENTAS PAIS", "Transferencia Interna", "Transferencia", True),
    ("TRANSFERENCIA CCP", "Transferencia Interna", "Transferencia", True),
    ("CUENTA PROPIA", "Transferencia Interna", "Transferencia", True),
    ("TRANSF INMED CP", "Transferencia Interna", "Transferencia", True),
    ("TR.NE", "Transferencia Interna", "Transferencia", True),
    ("DESCUENTO DOCUMENTO", "Prestamo", "Transferencia", False),
    ("CHEQUES DESCONTADOS", "Prestamo", "Transferencia", False),
    ("DEUD. PUBLICA", "Prestamo", "Transferencia", False),
    ("PRESTAMO", "Prestamo", "Transferencia", False),
    ("ACRED. CH", "Cheques", "Cheque de Terceros", False),
    ("ACREDITACION CHEQUE", "Cheques", "Cheque de Terceros", False),
    ("DEPOSITO CHEQUE", "Cheques", "Cheque de Terceros", False),
    ("CH.CAMARA", "Cheques", "Cheque de Terceros", False),
    ("REMESAS", "Cheques", "Cheque de Terceros", False),
    ("CANJE", "Cheques", "Cheque de Terceros", False),
    ("TEF DATANET", "Cobranza Facturas", "Transferencia", False),
    ("CCERR", "Cheques", "Cheque de Terceros", False),
    ("G.DE ECHEQ", "Cheques", "Cheque de Terceros", False),
    ("ECHEQ", "Cheques", "Cheque de Terceros", False),
    ("NUMERO DE OPERACION", "Cobranza Facturas", "Efectivo", False),
    ("OPERACION DE R", "Cobranza Facturas", "Efectivo", False),
    ("RECAUDACION", "Cobranza Facturas", "Efectivo", False),
    ("EFECTIVO", "Cobranza Facturas", "Efectivo", False),
    ("DEPOSITO", "Cobranza Facturas", "Efectivo", False),
    ("ATM", "Cobranza Facturas", "Efectivo", False),
    ("CREDIN", "Cobranza Facturas", "Transferencia", False),
    ("DNET", "Cobranza Facturas", "Transferencia", False),
    ("BANEL", "Cobranza Facturas", "Transferencia", False),
    ("TRANSF", "Cobranza Facturas", "Transferencia", False),
    ("TRF", "Cobranza Facturas", "Transferencia", False),
    ("COBRO DE PENDIENTES", "Otros", "", False),
    ("N/C RET", "Otros", "", False),           # devolución de una retención
    ("N/C AJ", "Otros", "", False),
    ("N/C DBCR", "Otros", "", False),
]
NOTAS = {
    "NUMERO DE OPERACION": "depósito por número de operación: ¿cobranza? revisar",
    "CCERR": "cheque de cámara acreditado (circuito cerrado)",
    "DEUD. PUBLICA": "acreditación 'DEUD. PUBLICA-P.PREVIO': ¿descuento de valores? preguntar al banco",
    "EFECTIVO": "depósito en efectivo: ¿cobranza en efectivo o plata de la caja propia? revisar",
    "DEPOSITO": "depósito: ¿cobranza o plata de la caja propia? revisar",
    "ATM": "depósito en cajero: ¿cobranza o caja propia? revisar",
    "TR.NE": "viene de una cuenta de NAVAR en otro banco",
}


def clasificar(mov, cuit_propio):
    """-> (tipo, categoria, medio, interno, nota)."""
    c = _norm(mov["concepto"])
    v = mov["importe"]
    tipo = "Ingreso" if v > 0 else "Egreso"
    if cuit_propio and re.search(r'\b' + re.escape(cuit_propio) + r'\b', c.replace("-", "")):
        return (tipo, "Transferencia Interna", "Transferencia", True, "al/del CUIT propio (otra cuenta de NAVAR)")
    if re.fullmatch(r'\d{18,}', c):
        return (tipo, "Otros", "", False, "acreditación sin descripción (solo un número de operación): ¿valores al cobro, préstamo? preguntar al banco")
    for texto, cat, medio, interno in (REGLAS_INGRESO if v > 0 else REGLAS_EGRESO):
        if texto in c:
            nota = NOTAS.get(texto, "")
            if cat == "Proveedores MP y Logist.":
                cuit = re.search(r'\b(\d{11})\b', c)
                nota = ("CUIT %s-%s-%s: proveedor a identificar" % (cuit.group(1)[:2], cuit.group(1)[2:10], cuit.group(1)[10:])
                        if cuit else "proveedor a identificar")
            return (tipo, cat, medio, interno, nota)
    return (tipo, "Otros", "", False, "sin regla: revisar")


# ================================================================== armado
def procesar(carpeta, empresa="A"):
    bancos, cuit = [], None
    for clave, cfg in BANCOS.items():
        sub = os.path.join(carpeta, clave)
        if not os.path.isdir(sub):
            continue
        lecturas = []
        for ruta in sorted(glob.glob(os.path.join(sub, "*.pdf"))):
            lecturas.append(cfg["pdf"](ruta))
        if cfg["planilla"]:
            for ruta in sorted(glob.glob(os.path.join(sub, "*.xls")) + glob.glob(os.path.join(sub, "*.xlsx"))):
                if os.path.basename(ruta).startswith(("para_pegar", "~$")):
                    continue
                lecturas.append(cfg["planilla"](ruta))
        for l in lecturas:
            cuit = cuit or l.get("cuit")
        bancos.append({"clave": clave, "nombre": cfg["nombre"], "lecturas": lecturas})

    saldos, movs, resumen_bancos = [], [], []
    for b in bancos:
        vistos, propios = set(), []
        # 1. PDF manda; después las planillas agregan lo que falta.
        for l in sorted(b["lecturas"], key=lambda l: 0 if l["movimientos"] and l["movimientos"][0]["fuente"] == "pdf" else 1):
            n_nuevos = 0
            for m in l["movimientos"]:
                k = (m["cuenta"], m["fecha"], round(m["importe"], 2))
                if k in vistos:
                    continue
                vistos.add(k)
                propios.append(dict(m, banco=b["nombre"]))
                n_nuevos += 1
            l["nuevos"] = n_nuevos
        propios.sort(key=lambda m: (m["cuenta"], m["fecha"]))
        # 2. Saldo por cuenta y día: el último saldo de cada día, de lo que tenga saldo.
        por_dia = {}
        for m in propios:
            if m["saldo"] is not None:
                por_dia[(m["cuenta"], m["fecha"])] = m["saldo"]
        for l in b["lecturas"]:
            for f, s in (l.get("saldos_por_dia") or {}).items():
                por_dia[(l["cuenta"], f)] = s
        for (cta, f), s in sorted(por_dia.items()):
            saldos.append({"banco": b["nombre"], "cuenta": cta, "fecha": f, "saldo": s,
                           "origen": "Extracto %s" % b["nombre"], "obs": "saldo contable al cierre del día"})
        movs += propios
        resumen_bancos.append({"banco": b["nombre"], "lecturas": b["lecturas"], "n": len(propios),
                               "ultimos": {cta: (f, s) for (cta, f), s in sorted(por_dia.items())}})
    for s in SALDOS_MANUALES:
        saldos.append(dict(s))
    saldos.sort(key=lambda s: (s["banco"], s["cuenta"], s["fecha"]))
    movs.sort(key=lambda m: (m["fecha"], m["banco"], m["cuenta"]))

    filas, por_cat = [], defaultdict(lambda: [0, 0.0])
    for i, m in enumerate(movs, 1):
        tipo, cat, medio, interno, nota = clasificar(m, cuit)
        obs = "Extracto %s · %s%s" % (m["banco"], m["fuente"].upper(), (" · " + nota) if nota else "")
        if interno:
            obs = "INTERNO (no es ingreso ni gasto) · " + obs
        filas.append(OrderedDict([
            ("ID", i), ("Fecha", m["fecha"]), ("Empresa", empresa), ("Tipo", tipo), ("Categoria", cat),
            ("Concepto / Detalle", m["concepto"]), ("Importe", m["importe"]), ("Medio de Pago", medio),
            ("Banco / Cuenta", "%s %s" % (m["banco"], m["cuenta"])), ("Origen", "Extracto %s" % m["banco"]),
            ("Estado", "Real"), ("Referencia", m.get("ref")), ("Semana (lunes)", None), ("Observaciones", obs),
        ]))
        por_cat[(m["banco"], tipo, cat, interno)][0] += 1
        por_cat[(m["banco"], tipo, cat, interno)][1] += m["importe"]
    return {"cuit": cuit, "bancos": resumen_bancos, "saldos": saldos, "movimientos": filas, "por_cat": por_cat}


def escribir_para_pegar(res, carpeta, hoy, empresa="A"):
    ruta = os.path.join(carpeta, "para_pegar_bancos_%s.xlsx" % hoy.isoformat())
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet("Saldos Bancarios")
    ws.append(ENC_SALDOS)
    for s in res["saldos"]:
        ws.append([s["fecha"], s["banco"], empresa, s["cuenta"], round(s["saldo"], 2), s["origen"], s["obs"]])
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


def escribir_sheet_con_extractos(res, sheet_original, hoy, empresa="A"):
    """Copia del Cashflow con los extractos cargados. En Movimientos y Saldos
    Bancarios se borran las filas que ya venían de extractos (Origen dice
    Extracto / Captura) y se agregan las nuevas. Las columnas con fórmula no se tocan."""
    base, ext = os.path.splitext(sheet_original)
    destino = "%s (con bancos %s)%s" % (base.split(" (con ")[0], hoy.isoformat(), ext)
    wb = openpyxl.load_workbook(sheet_original)

    def _volcar(nombre, filas, es_nuestro, con_varios=False):
        ws = wb[nombre]
        enc = [str(c.value).strip() if c.value is not None else "" for c in ws[1]]
        idx_origen = next((i for i, e in enumerate(enc) if e.lower().startswith("origen")), None)
        idx_banco = next((i for i, e in enumerate(enc) if e.lower().startswith("banco")), None)
        idx_empresa = next((i for i, e in enumerate(enc) if e.lower().startswith("empresa")), None)
        escribibles = [(j, e) for j, e in enumerate(enc, start=1) if e and e not in COLS_CON_FORMULA]
        vivas, ultima = [], 1
        for i, f in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if f[1] in (None, ""):
                continue
            ultima = i
            if idx_origen is not None and (nuestro_o_varios(f, idx_origen, idx_banco, idx_empresa) if con_varios
                                           else es_nuestro(f[idx_origen])):
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
        if enc and enc[0] == "ID":
            for i in range(2, fila):
                ws.cell(row=i, column=1).value = i - 1
        return len(vivas), len(filas)

    nuestro = lambda o: any(t in str(o or "").upper() for t in ("EXTRACTO", "CAPTURA", "HOME BANKING"))
    # En Saldos Bancarios tambien se va la fila manual "(varios)" de la empresa que ahora
    # tiene bancos de verdad: era "bancos + efectivo del cash viejo" y pisaria el dato real.
    empresas_con_bancos = {empresa}

    def nuestro_o_varios(fila, idx_origen, idx_banco, idx_empresa):
        if nuestro(fila[idx_origen]):
            return True
        return (idx_banco is not None and "VARIOS" in str(fila[idx_banco] or "").upper()
                and str(fila[idx_empresa] or "").strip().upper() in empresas_con_bancos)
    saldos = [OrderedDict([("Fecha", s["fecha"]), ("Banco", s["banco"]), ("Empresa", empresa),
                           ("Cuenta / Nro", s["cuenta"]), ("Saldo (caja real, sin cheques)", round(s["saldo"], 2)),
                           ("Origen", s["origen"]), ("Observaciones", s["obs"])]) for s in res["saldos"]]
    r1 = _volcar("Saldos Bancarios", saldos, nuestro, con_varios=True)
    r2 = _volcar("Movimientos", res["movimientos"], nuestro)
    wb.save(destino)
    return destino, {"Saldos Bancarios": r1, "Movimientos": r2}


def resumen(res, ruta_pegar, hoy):
    L = ["# Extractos → Cashflow · %s" % hoy.strftime("%d/%m/%Y"), ""]
    L.append("CUIT de la empresa: **%s**" % (res["cuit"] or "?"))
    L.append("")
    L.append("## Por banco")
    total_hoy = 0.0
    for b in res["bancos"]:
        L.append("### %s · %d movimientos" % (b["banco"], b["n"]))
        for l in b["lecturas"]:
            L.append("- `%s` · cuenta %s · %d movimientos (%d nuevos)%s"
                     % (l["archivo"], l["cuenta"], len(l["movimientos"]), l.get("nuevos", 0),
                        (" · " + l["nota"]) if l.get("nota") else ""))
        for cta, (f, s) in b["ultimos"].items():
            L.append("- **último saldo %s: %s** (%s)" % (cta, _m(s), f.strftime("%d/%m/%Y")))
            total_hoy += s
        L.append("")
    for s in SALDOS_MANUALES:
        L.append("### %s (manual)\n- %s: **%s** (%s) · %s\n" % (s["banco"], s["cuenta"], _m(s["saldo"]), s["fecha"].strftime("%d/%m/%Y"), s["obs"]))
        total_hoy += s["saldo"]
    L.append("**Posición en cuentas corrientes, sumando el último saldo de cada cuenta: %s**" % _m(total_hoy))
    L.append("")
    L.append("## Movimientos por banco y categoría (%d en total)" % len(res["movimientos"]))
    for (banco, tipo, cat, interno), (n, tot) in sorted(res["por_cat"].items(), key=lambda kv: (kv[0][0], kv[1][1])):
        L.append("- %s · %s · %s%s: %d por %s" % (banco, tipo, cat, " (interno)" if interno else "", n, _m(tot)))
    sin_regla = [x for x in res["movimientos"] if "sin regla" in x["Observaciones"]]
    if sin_regla:
        L.append("")
        L.append("## Sin regla (quedaron en 'Otros', revisar) · %d" % len(sin_regla))
        for x in sin_regla[:25]:
            L.append("- %s %s · %s · %s" % (x["Fecha"].strftime("%d/%m"), x["Banco / Cuenta"], x["Concepto / Detalle"][:60], _m(x["Importe"])))
    L.append("")
    L.append("## Archivo generado")
    L.append("- `%s`: solapas Saldos Bancarios y Movimientos, para pegar en el Cashflow (Semana (lunes) va vacía: es fórmula)." % ruta_pegar)
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="Extractos de los bancos -> listas del Cashflow")
    ap.add_argument("--carpeta", required=True, help="carpeta con una subcarpeta por banco (bbva, galicia, macro, corrientes...)")
    ap.add_argument("--cliente", required=True)
    ap.add_argument("--empresa", default="A")
    ap.add_argument("--hoy", default=None)
    ap.add_argument("--sheet", default=None, help="copia del Cashflow (.xlsx) a la que agregarle estas filas")
    a = ap.parse_args()
    hoy = datetime.date.fromisoformat(a.hoy) if a.hoy else datetime.date.today()
    res = procesar(a.carpeta, a.empresa)
    ruta = escribir_para_pegar(res, a.carpeta, hoy, a.empresa)
    txt = resumen(res, ruta, hoy)
    if a.sheet:
        destino, cuantas = escribir_sheet_con_extractos(res, a.sheet, hoy, a.empresa)
        txt += "\n- copia del Cashflow con los bancos: `%s` (%s)" % (
            destino, "; ".join("%s: %d de otros + %d nuevas" % (k, v[0], v[1]) for k, v in cuantas.items()))
    with io.open(os.path.join(a.carpeta, "resumen_bancos_%s.md" % hoy.isoformat()), "w", encoding="utf-8") as f:
        f.write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
