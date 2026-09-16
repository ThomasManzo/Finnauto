# -*- coding: utf-8 -*-
"""
arreglar_cash_v2 — corrige el "Cash Flow Limpio" que devolvio Cowork y deja la v2.

QUE ARREGLA (revisado el 12/09/2026, ver ARREGLOS_ESQUELETO.md)
----------------------------------------------------------------
1. SEMANAS DEL CONSOLIDADO. Venian en bloques de 7 dias contados desde el 1 de
   cada mes (septiembre: martes a lunes; octubre: jueves a miercoles). Todo lo
   demas de la planilla es lunes a domingo. Se regeneran las 440 columnas con
   semanas LUNES-DOMINGO, cortadas en el borde de mes (una semana partida entre
   dos meses queda en dos columnas, una por mes: asi el total del mes cierra).
2. FILAS EJEMPLO. Quedaron en las listas y, con datos reales ya cargados,
   inventaban numeros (un IVA de $25M, una linea de $300M, una factura vencida).
   Se vacian.
3. LO PROYECTADO DE LAS LISTAS. Los proyectados de proveedores, cobranzas,
   impuestos, cheques, prestamos y hoja verde estaban en Movimientos con
   Estado=Proyectado, pero esas filas del consolidado solo leen Real + lo
   pendiente de las LISTAS (por diseño, y esta bien). Resultado: $539M de
   proveedores, $195M de impuestos y $312M de prestamos no aparecian en ninguna
   semana. Se mueven a las listas como filas AGREGADAS, marcadas para que las
   reemplace el detalle de Tango.
4. (La regla "factura pagada con cheque" ya estaba en Instrucciones; no se toca.)

Uso:
    python clientes/navar/herramientas/arreglar_cash_v2.py
    (lee privado/NAVAR_-_Cash_Flow_Limpio.xlsx, escribe privado/NAVAR - Cash Flow Limpio v2.xlsx)
"""

import os
import re
import sys
import copy
import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # clientes/navar/
PRIVADO = os.path.join(BASE, "privado")
ORIGEN = os.path.join(PRIVADO, "NAVAR_-_Cash_Flow_Limpio.xlsx")
DESTINO = os.path.join(PRIVADO, "NAVAR - Cash Flow Limpio v2.xlsx")

import openpyxl
from openpyxl.utils import get_column_letter as L

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
         "Septiembre", "Octubre", "Noviembre", "Diciembre"]
MES_CORTO = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

# Como se muestra la plata: positivos normales, negativos con "-" y en rojo, ceros en blanco.
FORMATO_PLATA = '$#,##0;[Red]-$#,##0;'

# Filas del consolidado (despues del bloque "Vencido a la fecha", que empieza en la 4).
F_LABEL, F_FECHA, F_VISTA = 11, 12, 13
F_SALDO_INI, F_CONTROL = 15, 16
F_SALDO_FIN, F_REGULARIZO = 47, 48
F_ULTIMA = 48
# Filas que en las columnas Semana/Mes/Año llevan "el valor del ultimo dia" en vez de una suma.
F_STOCK = (F_SALDO_INI, F_CONTROL, F_SALDO_FIN, F_REGULARIZO)


# --------------------------------------------------------------- 1. consolidado
def _formula_de_dia(plantilla, col):
    """La formula de la columna B, movida a otra columna de dia.

    Reemplaza solo las referencias RELATIVAS a la columna B (B$12, B19, B15...).
    Las absolutas ($B$2, $B$3, $B$10, Movimientos!$B$2) quedan iguales.
    """
    return re.sub(r"(?<![A-Z$!'])B(\$?\d+)", lambda m: col + m.group(1), plantilla)


def regenerar_consolidado(wb):
    ws = wb["Cash Flow Consolidado"]
    inicio = ws["B2"].value
    if isinstance(inicio, datetime.datetime):
        inicio = inicio.date()

    # Plantillas de estilo y formula: una columna de cada tipo del archivo original.
    col_tpl = {"dia": "B", "semana": "C", "mes": "D", "anio": L(ws.max_column)}
    assert ws[col_tpl["anio"] + str(F_VISTA)].value == "Año", "no encontre la columna Año"
    estilos = {t: {r: copy.copy(ws[c + str(r)]._style) for r in range(F_LABEL, F_ULTIMA + 1)}
               for t, c in col_tpl.items()}
    dims = {t: (ws.column_dimensions[c].width, ws.column_dimensions[c].outlineLevel,
                ws.column_dimensions[c].hidden) for t, c in col_tpl.items()}
    formulas_dia = {r: ws["B" + str(r)].value for r in range(F_SALDO_INI, F_ULTIMA + 1)
                    if isinstance(ws["B" + str(r)].value, str) and ws["B" + str(r)].value.startswith("=")}

    # Lo que hay en la columna B arriba de la grilla (fecha de inicio, saldo, vencidos)
    # se guarda porque delete_cols se lo lleva.
    arriba = {r: (ws["B" + str(r)].value, copy.copy(ws["B" + str(r)]._style)) for r in range(1, F_LABEL)}
    arriba_C = {r: (ws["C" + str(r)].value, copy.copy(ws["C" + str(r)]._style)) for r in range(1, F_LABEL)}

    ws.delete_cols(2, ws.max_column)
    for r, (v, st) in arriba.items():
        ws["B" + str(r)].value = v
        ws["B" + str(r)]._style = st
    for r, (v, st) in arriba_C.items():
        ws["C" + str(r)].value = v
        ws["C" + str(r)]._style = st

    # ---- armar la secuencia de columnas: dias, con Semana al cierre de cada
    # semana (domingo o fin de mes) y Mes al cierre de cada mes.
    cols = []                      # (tipo, fecha|None, etiqueta)
    dia = inicio
    fin = inicio + datetime.timedelta(days=364)
    semana_del_mes = 1
    while dia <= fin:
        cols.append(("dia", dia, None))
        ultimo_del_mes = (dia + datetime.timedelta(days=1)).month != dia.month
        if dia.weekday() == 6 or ultimo_del_mes or dia == fin:
            cols.append(("semana", None, "Sem %d %s %s" % (semana_del_mes, MES_CORTO[dia.month - 1],
                                                          str(dia.year)[2:])))
            semana_del_mes += 1
        if ultimo_del_mes or dia == fin:
            cols.append(("mes", None, "TOTAL %s %d" % (MESES[dia.month - 1].upper(), dia.year)))
            semana_del_mes = 1
        dia += datetime.timedelta(days=1)
    cols.append(("anio", None, "TOTAL AÑO"))

    # ---- escribir columna por columna
    dias_semana, semanas_mes, meses = [], [], []
    col_dia_anterior = None
    for i, (tipo, fecha, etiqueta) in enumerate(cols):
        c = L(i + 2)
        w, ol, hid = dims[tipo]
        ws.column_dimensions[c].width = w
        ws.column_dimensions[c].outlineLevel = ol
        ws.column_dimensions[c].hidden = hid
        for r in range(F_LABEL, F_ULTIMA + 1):
            ws[c + str(r)]._style = copy.copy(estilos[tipo][r])
            # Negativos con "-" y en rojo, ceros en blanco (Thomas, 14/09: los
            # parentesis no se leen). Solo en las filas de plata, no en la de fechas.
            if r >= F_SALDO_INI:
                ws[c + str(r)].number_format = FORMATO_PLATA
        ws[c + str(F_LABEL)].value = etiqueta
        ws[c + str(F_VISTA)].value = {"dia": "Día", "semana": "Semana", "mes": "Mes", "anio": "Año"}[tipo]

        if tipo == "dia":
            ws[c + str(F_FECHA)].value = "=$B$2" if col_dia_anterior is None else "=%s%d+1" % (col_dia_anterior, F_FECHA)
            for r, f in formulas_dia.items():
                ws[c + str(r)].value = _formula_de_dia(f, c)
            # El saldo inicial de cada dia es el final del dia anterior.
            ws[c + str(F_SALDO_INI)].value = "=$B$3" if col_dia_anterior is None else "=%s%d" % (col_dia_anterior, F_SALDO_FIN)
            col_dia_anterior = c
            dias_semana.append(c)
        elif tipo == "semana":
            primero, ultimo = dias_semana[0], dias_semana[-1]
            for r in formulas_dia:
                if r in F_STOCK:
                    ws[c + str(r)].value = "=%s%d" % (primero if r == F_SALDO_INI else ultimo, r)
                else:
                    ws[c + str(r)].value = "=SUM(%s%d:%s%d)" % (primero, r, ultimo, r)
            semanas_mes.append((c, primero, ultimo))
            dias_semana = []
        elif tipo == "mes":
            primero, ultimo = semanas_mes[0][1], semanas_mes[-1][2]
            for r in formulas_dia:
                if r in F_STOCK:
                    ws[c + str(r)].value = "=%s%d" % (primero if r == F_SALDO_INI else ultimo, r)
                else:
                    ws[c + str(r)].value = "=SUM(%s)" % ",".join("%s%d" % (s, r) for s, _, _ in semanas_mes)
            meses.append((c, primero, ultimo))
            semanas_mes = []
        else:   # anio
            for r in formulas_dia:
                if r in F_STOCK:
                    ws[c + str(r)].value = "=%s%d" % (meses[0][1] if r == F_SALDO_INI else meses[-1][2], r)
                else:
                    ws[c + str(r)].value = "=SUM(%s)" % ",".join("%s%d" % (m, r) for m, _, _ in meses)
    # El bloque de arriba (fecha de inicio, saldo inicial, vencidos) estaba en
    # la columna B, que es el primer DIA y queda oculta cuando la vista esta
    # colapsada a meses: el cliente no lo veia ni podia editar la fecha. Los
    # valores pasan a D (el primer "Mes", siempre visible) y B queda apuntando
    # a D, asi las formulas de toda la grilla ($B$2, $B$3, $B$10) siguen igual.
    for r in (2, 3, 5, 6, 7, 8, 9, 10):
        b, d = ws["B%d" % r], ws["D%d" % r]
        d.value, d._style = b.value, copy.copy(b._style)
        b.value = "=D%d" % r
        ws["C%d" % r].value = None
    ws["A2"].value = "Fecha Inicio del Horizonte (editar la celda D2):"
    ws.freeze_panes = "B15"
    return len(cols)


# ------------------------------------------------------------ 2. filas EJEMPLO
def vaciar_ejemplos(wb):
    """Vacia las celdas de carga de la fila EJEMPLO y deja las formulas guardadas
    (las de la fila de abajo, que devuelven "" si la fila esta vacia)."""
    hechos = []
    for nombre in ("Cuentas a Cobrar", "Cuentas a Pagar", "Deuda Impositiva", "Config Mapeo Tango",
                   "Deuda Bancaria"):
        ws = wb[nombre]
        for fila in ws.iter_rows(min_row=1, max_row=80):
            if not any(isinstance(c.value, str) and "EJEMPLO" in c.value.upper() for c in fila):
                continue
            r = fila[0].row
            for c in fila:
                abajo = ws.cell(r + 1, c.column).value
                if isinstance(abajo, str) and abajo.startswith("="):
                    # misma formula que la fila de abajo, apuntando a esta fila
                    c.value = re.sub(r"([A-Z]+)%d\b" % (r + 1), lambda m: m.group(1) + str(r), abajo)
                else:
                    c.value = None
            hechos.append("%s fila %d" % (nombre, r))
    return hechos


# ------------------------------------------- 3. proyectados: de Movimientos a listas
# Categoria de Movimientos -> a que lista va lo PROYECTADO (las filas del
# consolidado que leen estas categorias filtran Real y suman la lista).
A_LISTA = {
    "Cobranza Facturas": "Cuentas a Cobrar",
    "Proveedores MP y Logist.": "Cuentas a Pagar",
    "Proveedores AA": "Cuentas a Pagar",
    "Hoja Verde": "Cuentas a Pagar",
    "Insumos": "Cuentas a Pagar",
    "Cheques": "Cartera de Cheques",
    "Impuestos": "Deuda Impositiva",
    "Prestamo": "Deuda Bancaria",
}
MARCA = "AGREGADO del cash viejo (proyeccion semanal). Reemplazar por el detalle de Tango."


def _primera_fila_libre(ws, desde, col=1):
    r = desde
    while ws.cell(r, col).value not in (None, ""):
        r += 1
    return r


def mover_proyectados(wb):
    ws = wb["Movimientos"]
    filas = []
    for fila in ws.iter_rows(min_row=2, max_row=ws.max_row, values_only=True):
        if fila[0] in (None, ""):
            continue
        filas.append(list(fila))

    quedan, mover = [], []
    for f in filas:
        cat, estado = f[4], f[10]
        if estado == "Proyectado" and cat in A_LISTA and not (cat == "Prestamo" and f[3] == "Ingreso"):
            mover.append(f)
        else:
            quedan.append(f)

    # Reescribir Movimientos: solo lo que queda, IDs enteros, la formula de
    # Semana (col M) no se toca.
    for r in range(2, len(filas) + 2):
        for c in range(1, 15):
            if c != 13:
                ws.cell(r, c).value = None
    for i, f in enumerate(quedan):
        r = i + 2
        f[0] = i + 1
        for c, v in enumerate(f, start=1):
            if c != 13:
                ws.cell(r, c).value = v

    # A las listas.
    resumen = {}
    n_cob = _primera_fila_libre(wb["Cuentas a Cobrar"], 2)
    n_pag = _primera_fila_libre(wb["Cuentas a Pagar"], 2)
    n_chq = _primera_fila_libre(wb["Cartera de Cheques"], 2)
    n_imp = _primera_fila_libre(wb["Deuda Impositiva"], 2)
    n_ban = _primera_fila_libre(wb["Deuda Bancaria"], 64)
    for f in mover:
        _id, fecha, emp, tipo, cat, concepto, importe, medio, banco, origen, estado, ref, _sem, obs = f
        v = abs(float(importe))
        sem = fecha.strftime("%d/%m") if hasattr(fecha, "strftime") else str(fecha)
        destino = A_LISTA[cat]
        resumen[destino] = resumen.get(destino, 0) + v
        if destino == "Cuentas a Cobrar":
            w = wb[destino]
            w.cell(n_cob, 1).value = n_cob - 1
            for c, val in enumerate(["(agregado cash viejo)", emp, "AGR-%s" % sem, fecha, fecha, v, 0], start=2):
                w.cell(n_cob, c).value = val
            w.cell(n_cob, 12).value = MARCA
            n_cob += 1
        elif destino == "Cuentas a Pagar":
            w = wb[destino]
            prov = "(agregado cash viejo)"
            if cat == "Hoja Verde":
                prov = concepto.replace("Hoja verde ", "").strip() or prov
            w.cell(n_pag, 1).value = n_pag - 1
            for c, val in enumerate([prov, emp, cat, "AGR-%s" % sem, fecha, fecha, v, 0], start=2):
                w.cell(n_pag, c).value = val
            w.cell(n_pag, 14).value = MARCA
            n_pag += 1
        elif destino == "Cartera de Cheques":
            w = wb[destino]
            w.cell(n_chq, 1).value = n_chq - 1
            for c, val in enumerate(["Propio Emitido", emp, "(agregado)", "", None, fecha, "(varios proveedores)", v,
                                     "En Cartera", ""], start=2):
                w.cell(n_chq, c).value = val
            w.cell(n_chq, 12).value = MARCA
            n_chq += 1
        elif destino == "Deuda Impositiva":
            w = wb[destino]
            for c, val in enumerate(["(agregado cash viejo)", emp, "", fecha, v, "Pendiente", ""], start=1):
                w.cell(n_imp, c).value = val
            w.cell(n_imp, 8).value = MARCA
            n_imp += 1
        elif destino == "Deuda Bancaria":
            w = wb[destino]
            for c, val in enumerate(["(varios)", emp, "(agregado cash viejo)", "", fecha, v, 0], start=1):
                w.cell(n_ban, c).value = val
            w.cell(n_ban, 8).value = "=F%d+G%d" % (n_ban, n_ban)
            w.cell(n_ban, 9).value = "Pendiente"
            w.cell(n_ban, 10).value = MARCA
            n_ban += 1
    return len(quedan), len(mover), resumen


# ------------------------------------------------------- 4. regla del cheque
def regla_cheque(wb):
    ws = wb["Instrucciones"]
    # Despues de la ULTIMA fila con texto (las instrucciones tienen filas en
    # blanco en el medio; "primera fila libre" pisaba el "Que es esto").
    ultima = max(c.row for c in ws["B"] if c.value)
    r = ultima + 2
    ws.cell(r, 2).value = "Facturas pagadas o cobradas con cheque (para no contar dos veces)"
    ws.cell(r, 2)._style = copy.copy(ws["B11"]._style)
    ws.cell(r + 2, 2).value = (
        "Una factura pagada con CHEQUE PROPIO se marca Pagado (columna Pagado = importe) el dia que se "
        "EMITE el cheque. El cheque queda en Cartera de Cheques con estado En Cartera hasta que el banco "
        "lo debita; ahi pasa a Depositado/Acreditado. Si se deja la factura pendiente hasta que el cheque "
        "se cobra, el pago se cuenta dos veces (una en Cuentas a Pagar y otra en Cartera).")
    ws.cell(r + 2, 2)._style = copy.copy(ws["B13"]._style)
    ws.cell(r + 4, 2).value = (
        "Una factura cobrada con CHEQUE DE TERCEROS se marca Cobrado el dia que se RECIBE el cheque. "
        "El cheque va a Cartera de Cheques (Terceros Recibido, En Cartera) con su fecha de cobro: "
        "recien ese dia es plata.")
    ws.cell(r + 4, 2)._style = copy.copy(ws["B13"]._style)


# ------------------------------------------- 5. MAXIFS/MINIFS: prefijo para Excel
def prefijo_xlfn(wb):
    """Excel guarda las funciones nuevas (MAXIFS, MINIFS, IFS...) como _xlfn.NOMBRE
    adentro del archivo. Escritas a mano sin el prefijo, Excel muestra #NOMBRE?
    hasta que alguien reescribe la celda. Google Sheets no lo necesita, pero el
    archivo tiene que abrir bien en los dos. Lo encontro Cowork (12/09)."""
    n = 0
    for ws in wb.worksheets:
        for fila in ws.iter_rows():
            for c in fila:
                if isinstance(c.value, str) and c.value.startswith("="):
                    nuevo = re.sub(r"(?<![\w.])(MAXIFS|MINIFS|IFS|SWITCH|TEXTJOIN|CONCAT)\(",
                                   r"_xlfn.\1(", c.value, flags=re.I)
                    if nuevo != c.value:
                        c.value = nuevo
                        n += 1
    return n


# --------------------------------------------- 6. los STOCKS de deuda al 31/08
CASH_VIEJO = os.path.join(PRIVADO, "20260828 - NAVAR S.A. - CASH FLOW 31-08.xlsx")


def stocks_de_deuda(wb):
    """El cash viejo declaraba, al 31/08, tres SALDOS de deuda: proveedores
    atrasada ($205,8M), impositiva ($398,6M) y bancaria ($400,6M). La migracion
    llevo los FLUJOS semanales a las listas, pero no estos stocks: sin ellos
    "Vencido a la fecha" y Posicion de Deuda muestran menos deuda de la que el
    propio cliente reconoce.

    Van con vencimiento 30/08 (un dia antes del horizonte): asi entran en lo
    VENCIDO pero no en ninguna semana del flujo, que es exactamente lo que son.
    """
    v = openpyxl.load_workbook(CASH_VIEJO, data_only=True)["Resumen FF 31-08   (2)"]
    prov, imp, ban = abs(v["E49"].value or 0), abs(v["E44"].value or 0), abs(v["E54"].value or 0)
    venc = datetime.date(2026, 8, 30)
    marca = "AGREGADO del cash viejo: SALDO declarado al 31/08, sin detalle. Reemplazar por el detalle de Tango / ARCA / bancos."

    w = wb["Cuentas a Pagar"]
    r = _primera_fila_libre(w, 2)
    w.cell(r, 1).value = r - 1
    for c, val in enumerate(["(agregado cash viejo) deuda atrasada", "A", "Proveedores MP y Logist.",
                             "AGR-atrasada-31/08", venc, venc, prov, 0], start=2):
        w.cell(r, c).value = val
    w.cell(r, 14).value = marca

    w = wb["Deuda Impositiva"]
    r = _primera_fila_libre(w, 2)
    for c, val in enumerate(["(agregado cash viejo) deuda impositiva atrasada", "A", "", venc, imp,
                             "Pendiente", ""], start=1):
        w.cell(r, c).value = val
    w.cell(r, 8).value = marca

    w = wb["Deuda Bancaria"]
    r = _primera_fila_libre(w, 3)
    for c, val in enumerate(["(varios)", "A", "(agregado cash viejo) deuda bancaria al 31/08", ban, ban,
                             None, None, None, None], start=1):
        w.cell(r, c).value = val
    w.cell(r, 10).value = marca + " El cliente declaro ~$2.700M en total: la planilla vieja solo miraba una parte."
    return prov, imp, ban


def main():
    wb = openpyxl.load_workbook(ORIGEN)
    n_cols = regenerar_consolidado(wb)
    n_xlfn = prefijo_xlfn(wb)
    ejemplos = vaciar_ejemplos(wb)
    quedan, movidos, resumen = mover_proyectados(wb)
    prov, imp, ban = stocks_de_deuda(wb)
    # regla_cheque(wb): Cowork ya la habia agregado en Instrucciones (filas 23/25).
    wb.save(DESTINO)

    def _m(v):
        return "$" + format(int(round(v)), ",d").replace(",", ".")
    print("  Consolidado : %d columnas regeneradas, semanas lunes-domingo" % n_cols)
    print("  Excel       : %d formulas con prefijo _xlfn. (MAXIFS y cia.)" % n_xlfn)
    print("  Ejemplos    : vaciados en %s" % ", ".join(ejemplos))
    print("  Movimientos : quedan %d filas; %d proyectados movidos a las listas:" % (quedan, movidos))
    for k, v in resumen.items():
        print("      %-20s %s" % (k, _m(v)))
    print("  Stocks 31/08: proveedores atrasada %s | impositiva %s | bancaria %s" % (_m(prov), _m(imp), _m(ban)))
    print("\n  Salida: %s" % DESTINO)


if __name__ == "__main__":
    main()
