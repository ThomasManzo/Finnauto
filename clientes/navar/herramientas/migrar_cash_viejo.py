# -*- coding: utf-8 -*-
"""
migrar_cash_viejo — del cash semanal viejo de NAVAR a filas del cash nuevo.

PARA QUE
--------
El esqueleto nuevo arranca vacio. El cash viejo tiene 6 semanas de numeros
REALES (20/07 al 24/08) y 8 semanas PROYECTADAS (31/08 al 19/10). Tirar eso a la
basura es arrancar el tablero sin historia; cargarlo a mano son 200 celdas.

Este script lee el cash viejo y deja un Excel con las filas ya armadas para
PEGAR en las solapas del esqueleto nuevo: Movimientos, Saldos Bancarios,
Cartera de Cheques y Vista Semanal.

QUE HACE Y QUE NO
-----------------
  · Cada celda "Real" del cash viejo -> UNA fila en Movimientos, con fecha el
    LUNES de esa semana. Es un agregado semanal, no el detalle diario: por eso
    todas llevan Origen="Manual" y la observacion "migrado del cash viejo".
    Cuando lleguen los exports de Tango, estas filas se reemplazan.
  · Las 8 semanas proyectadas de la ultima pestaña -> filas con Estado="Proyectado".
  · Bancos+efectivo, Caja AA y Cheques en cartera del 31/08 -> Saldos / Cartera.
    El cash viejo NO abre por banco ni por cheque: van como un solo renglon
    "(varios)" con la nota de que falta el detalle.
  · Proyectado vs Real de cada pestaña -> Vista Semanal (la bitacora), asi
    arranca con 6 semanas de "que dijimos / que paso".

No inventa nada: si una celda esta vacia o en cero, no genera fila.

Uso:
    python clientes/navar/herramientas/migrar_cash_viejo.py
    (lee y escribe en clientes/navar/privado/, que no sube a git)
"""

import io
import os
import sys
import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # clientes/navar/
PRIVADO = os.path.join(BASE, "privado")
ORIGEN = os.path.join(PRIVADO, "20260828 - NAVAR S.A. - CASH FLOW 31-08.xlsx")
DESTINO = os.path.join(PRIVADO, "datos_migrados_del_cash_viejo.xlsx")

try:
    import openpyxl
    from openpyxl.styles import Font
except ImportError:
    print("Falta openpyxl. Instalalo con:  pip install openpyxl")
    sys.exit(1)

# Rotulo de la fila del cash viejo -> (Tipo, Empresa, Categoria del esqueleto
# nuevo, Concepto, Medio de pago). Se mapea POR ROTULO y no por numero de fila:
# las pestañas de julio tienen filas de mas (cobranzas en cheques, venta de
# cheques, pago a proveedores con cheques) y todo corre dos lugares. Con el
# numero de fila, "Sueldos" de julio caia en "Egresos" y nadie se enteraba.
#
# Las categorias son EXACTAMENTE las de la validacion de Movimientos!E.
FILAS = {
    "cobranza a de facturas":                     ("Ingreso", "A",  "Cobranza Facturas",        "Cobranza A de facturas", ""),
    "cobranza aa de facturas":                    ("Ingreso", "AA", "Cobranza Facturas",        "Cobranza AA de facturas", ""),
    "cobranza canchada":                          ("Ingreso", "A",  "Cobranza Canchada",        "Cobranza canchada", ""),
    "cobranza a proyectada":                      ("Ingreso", "A",  "Cobranza Proyectada",      "Cobranza A proyectada (estimacion por kg)", ""),
    "cobranza aa proyectada":                     ("Ingreso", "AA", "Cobranza Proyectada",      "Cobranza AA proyectada (estimacion por kg)", ""),
    "cobranzas en cheques":                       ("Ingreso", "A",  "Cobranza Facturas",        "Cobranzas en cheques de terceros", "Cheque de Terceros"),
    "ingreso por venta de cheques de terceros":   ("Ingreso", "A",  "Otros",                    "Venta (descuento) de cheques de terceros", ""),
    "cheques emitidos":                           ("Egreso",  "A",  "Cheques",                  "Cheques emitidos", "Cheque Propio"),
    "sueldos y jornales":                         ("Egreso",  "A",  "Sueldos y Jornales",       "Sueldos y jornales", ""),
    "pago de impuestos":                          ("Egreso",  "A",  "Impuestos",                "Pago de impuestos", ""),
    "pago cosecha":                               ("Egreso",  "A",  "Cosecha",                  "Pago cosecha", ""),
    "pago a proveedores (mp y logist.)":          ("Egreso",  "A",  "Proveedores MP y Logist.", "Pago a proveedores (MP y logistica)", ""),
    "pago a proveedores con cheques de terceros": ("Egreso",  "A",  "Proveedores MP y Logist.", "Pago a proveedores con cheques de terceros", "Cheque de Terceros"),
    "pago a proveedores con cheque de terceros":  ("Egreso",  "A",  "Proveedores MP y Logist.", "Pago a proveedores con cheques de terceros", "Cheque de Terceros"),
    "pago a proveedores aa":                      ("Egreso",  "AA", "Proveedores AA",           "Pago a proveedores AA", ""),
    "pago insumos (proyectada)":                  ("Egreso",  "A",  "Insumos",                  "Pago insumos", ""),
    "pago hoja verde catalina - dolores":         ("Egreso",  "A",  "Hoja Verde",               "Hoja verde Catalina - Dolores", ""),
    "pago hoja verde carolina":                   ("Egreso",  "A",  "Hoja Verde",               "Hoja verde Carolina", ""),
    "pago hoja verde otros":                      ("Egreso",  "A",  "Hoja Verde",               "Hoja verde otros", ""),
    "honorarios + dividendos":                    ("Egreso",  "A",  "Honorarios y Dividendos",  "Honorarios + dividendos", ""),
    "gastos estampillas":                         ("Egreso",  "A",  "Estampillas",              "Estampillas", ""),
    "otros gastos":                               ("Egreso",  "A",  "Otros",                    "Otros gastos (CCG + Rodolfo + T. Agronac)", ""),
    # En julio iba con signo NEGATIVO dentro de egresos: cheques de terceros que
    # salen de la cartera (descontados o endosados). Se respeta como egreso y se
    # marca REVISAR: en el cash nuevo esto es un movimiento de Cartera, no de caja.
    "venta de valores":                           ("Egreso",  "A",  "Otros",                    "Venta de valores (cheques de terceros descontados/endosados) - REVISAR", "Cheque de Terceros"),
    "ingreso de prestamos":                       ("Ingreso", "A",  "Prestamo",                 "Ingreso de prestamos", ""),
    "pago de prestamos":                          ("Egreso",  "A",  "Prestamo",                 "Pago de prestamos", ""),
}
# Filas del cash viejo que son totales/saldos: se ignoran a proposito.
IGNORAR = ("saldo", "ajuste", "bancos + efectivo", "caja aa", "cheques en cartera",
           "ingresos", "egresos", "flujo de caja", "semana", "cash flow semanal",
           "deuda", "ingreso", "pago")
# OJO: la empresa "A" es un SUPUESTO en todo lo que el cash viejo no separa por
# empresa (solo separa cobranzas y proveedores AA). Se marca en Observaciones.
SIN_EMPRESA_CIERTA = {k for k, v in FILAS.items() if v[1] == "A" and "aa" not in k}
# Rotulos de las filas de totales, para la bitacora.
BITACORA = {"ingresos": "Ingresos", "egresos": "Egresos", "flujo de caja operativo": "Flujo Operativo",
            "flujo de caja bancario": "Flujo Bancario", "saldo final": "Saldo Final"}


def _clave(rotulo):
    """'Pago a Proveedores (MP y logíst.)' -> 'pago a proveedores (mp y logist.)'."""
    import unicodedata
    s = unicodedata.normalize("NFD", str(rotulo or "")).encode("ascii", "ignore").decode()
    return " ".join(s.lower().split())


def _mapa(ws):
    """{clave del rotulo: numero de fila} de una pestaña. Avisa lo que no reconoce."""
    filas, raros = {}, []
    for r in range(4, 42):
        k = _clave(ws.cell(r, 1).value)
        if not k:
            continue
        # Coincidencia exacta, y si no, por prefijo: "otros gastos (ccg, rodolfo)"
        # y "otros gastos (ccg + rodolfo + t. agronac)" son la misma fila.
        if k in FILAS or k in BITACORA:
            filas[k] = r
            continue
        pref = [c for c in FILAS if k.startswith(c)]
        if pref:
            filas[max(pref, key=len)] = r
        elif not k.startswith(IGNORAR):
            raros.append((r, ws.cell(r, 1).value))
    return filas, raros


ENC_MOV = ["ID", "Fecha", "Empresa", "Tipo", "Categoria", "Concepto / Detalle", "Importe",
           "Medio de Pago", "Banco / Cuenta", "Origen", "Estado", "Referencia",
           "Semana (lunes)", "Observaciones"]
ENC_SALDOS = ["Fecha", "Banco", "Empresa", "Cuenta / Nro", "Saldo (caja real, sin cheques)",
              "Origen", "Observaciones"]
ENC_CARTERA = ["ID", "Tipo", "Empresa", "Nro Cheque", "Banco", "Fecha Emision", "Fecha Pago / Cobro",
               "Beneficiario / Librador", "Importe", "Estado", "Aplicado a (Ref.)", "Observaciones"]
ENC_VISTA = ["Fecha de Carga", "Semana (lunes)", "Categoria", "Proyectado", "Real", "Variacion",
             "Observaciones"]


def _f(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _fecha(v):
    if isinstance(v, datetime.datetime):
        return v.date()
    return v


def leer(wb):
    """Devuelve (reales, proyectados, saldos, bitacora) leyendo cada pestaña."""
    reales, bitacora = [], []
    proyectados, saldos = [], {}
    ultima = None

    for nombre in wb.sheetnames:
        ws = wb[nombre]
        primera_futura = _fecha(ws["E3"].value)
        if not primera_futura:
            continue
        mapa, raros = _mapa(ws)
        for r, rot in raros:
            print("  AVISO %s fila %d sin mapear: %r" % (nombre.strip(), r, rot))
        # La columna "Real" (C) es la semana ANTERIOR a la primera futura.
        # (No se usa B2: en la pestaña 24-08 quedo con la fecha equivocada.)
        semana_real = primera_futura - datetime.timedelta(days=7)
        for k, (tipo, emp, cat, concepto, medio) in FILAS.items():
            if k not in mapa:
                continue
            fila = mapa[k]
            v = _f(ws.cell(fila, 3).value)
            if v:
                reales.append((semana_real, tipo, emp, cat, concepto, medio, v, k, fila, nombre))
        # Bitacora: lo que se proyecto para esa semana vs lo que paso.
        for k, etiqueta in BITACORA.items():
            if k not in mapa:
                continue
            p, r = _f(ws.cell(mapa[k], 2).value), _f(ws.cell(mapa[k], 3).value)
            if p or r:
                bitacora.append((primera_futura, semana_real, etiqueta, p, r, nombre))
        ultima = (nombre, ws, primera_futura, mapa)

    # Proyectados y saldos: solo de la ultima pestaña (la mas reciente).
    nombre, ws, primera_futura, mapa = ultima
    for col in range(5, 13):                      # E..L = 8 semanas
        semana = _fecha(ws.cell(3, col).value)
        if not semana:
            continue
        for k, (tipo, emp, cat, concepto, medio) in FILAS.items():
            if k not in mapa:
                continue
            v = _f(ws.cell(mapa[k], col).value)
            if v:
                proyectados.append((semana, tipo, emp, cat, concepto, medio, v, k, mapa[k], nombre))
    saldos = {
        "fecha": primera_futura,
        "bancos_efvo": _f(ws["E7"].value),
        "caja_aa": _f(ws["E8"].value),
        "cheques_cartera": _f(ws["E9"].value),
        "pestaña": nombre,
    }
    return reales, proyectados, saldos, bitacora


def escribir(reales, proyectados, saldos, bitacora):
    out = openpyxl.Workbook()
    gris = Font(italic=True, color="666666")

    # ---- Movimientos
    ws = out.active
    ws.title = "Movimientos"
    ws.append(ENC_MOV)
    n = 0
    for estado, origen, lista in (("Real", "Manual", reales), ("Proyectado", "Proyeccion", proyectados)):
        for semana, tipo, emp, cat, concepto, medio, v, k, fila, pest in lista:
            n += 1
            obs = "migrado del cash viejo (%s, fila %d): agregado SEMANAL, no diario" % (pest.strip(), fila)
            if k in SIN_EMPRESA_CIERTA:
                obs += " | empresa A es SUPUESTO, confirmar"
            importe = abs(v) if tipo == "Ingreso" else -abs(v)
            ws.append([n, semana, emp, tipo, cat, concepto, importe, medio, "", origen, estado, "",
                       semana, obs])
    ws.freeze_panes = "A2"

    # ---- Saldos Bancarios (con la columna Empresa del arreglo #3)
    ws = out.create_sheet("Saldos Bancarios")
    ws.append(ENC_SALDOS)
    f = saldos["fecha"]
    ws.append([f, "(varios)", "A", "", saldos["bancos_efvo"], "Manual",
               "Bancos + efectivo del cash viejo (%s). SIN detalle por banco: reemplazar por un renglon por banco" % saldos["pestaña"].strip()])
    ws.append([f, "(varios)", "AA", "", saldos["caja_aa"], "Manual",
               "Caja AA del cash viejo. SIN detalle por banco"])
    ws.freeze_panes = "A2"

    # ---- Cartera de Cheques (un solo agregado)
    ws = out.create_sheet("Cartera de Cheques")
    ws.append(ENC_CARTERA)
    ws.append([1, "Terceros Recibido", "A", "(agregado)", "", "", f, "(varios clientes)",
               saldos["cheques_cartera"], "En Cartera", "",
               "AGREGADO del cash viejo: 'Cheques en cartera' al %s. NO tiene fecha de cobro real. "
               "Reemplazar por el detalle cheque por cheque de Tango." % f.strftime("%d/%m")])
    ws.freeze_panes = "A2"

    # ---- Vista Semanal (la bitacora)
    ws = out.create_sheet("Vista Semanal")
    ws.append(ENC_VISTA)
    for carga, semana, etiqueta, p, r, pest in bitacora:
        ws.append([carga, semana, etiqueta, p, r, r - p,
                   "del cash viejo (%s). OJO: en las pestañas 10-08/17-08/24-08 el Proyectado de "
                   "Egresos estaba tipeado y pegado (-248.229.455)" % pest.strip()
                   if etiqueta == "Egresos" else "del cash viejo (%s)" % pest.strip()])
    ws.freeze_panes = "A2"

    # Formato de fecha en todas las columnas de fecha
    for hoja in out.worksheets:
        for fila in hoja.iter_rows(min_row=2):
            for c in fila:
                if isinstance(c.value, (datetime.date, datetime.datetime)):
                    c.number_format = "DD/MM/YYYY"
                elif isinstance(c.value, float):
                    c.number_format = "#,##0"
    out.save(DESTINO)


def main():
    if not os.path.exists(ORIGEN):
        print("No encuentro el cash viejo: %s" % ORIGEN)
        sys.exit(1)
    wb = openpyxl.load_workbook(ORIGEN, data_only=True)
    reales, proyectados, saldos, bitacora = leer(wb)
    escribir(reales, proyectados, saldos, bitacora)

    def _m(v):
        return "$" + format(int(round(abs(v))), ",d").replace(",", ".")
    semanas = sorted(set(r[0] for r in reales))
    print("  Cash viejo   : %s" % os.path.basename(ORIGEN))
    print("  Reales       : %d movimientos en %d semanas (%s al %s)" % (
        len(reales), len(semanas), semanas[0].strftime("%d/%m"), semanas[-1].strftime("%d/%m")))
    print("  Proyectados  : %d movimientos en 8 semanas desde %s" % (
        len(proyectados), min(p[0] for p in proyectados).strftime("%d/%m")))
    print("  Saldos al %s: bancos+efvo %s | caja AA %s | cheques en cartera %s" % (
        saldos["fecha"].strftime("%d/%m"), _m(saldos["bancos_efvo"]), _m(saldos["caja_aa"]),
        _m(saldos["cheques_cartera"])))
    print("  Bitacora     : %d filas proyectado-vs-real" % len(bitacora))
    print("\n  Salida: %s" % DESTINO)
    print("  Cada solapa se pega en la solapa del mismo nombre del esqueleto nuevo.")


if __name__ == "__main__":
    main()
