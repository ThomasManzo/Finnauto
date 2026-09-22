# -*- coding: utf-8 -*-
"""
lector.tango — de los exports de Tango Live a las listas de la Sheet.

PARA QUE
--------
La Sheet "Cash Flow" del cliente tiene tres listas de detalle (Cuentas a Cobrar,
Cuentas a Pagar, Cartera de Cheques) que hasta ahora venían llenas de filas
"(agregado cash viejo)": totales semanales sin nombre. Este módulo toma los
exports de Tango Live (los Excel que se bajan con "Enviar a → Excel") y arma
esas mismas listas **factura por factura y cheque por cheque**, con el formato
exacto que la Sheet espera. Después, `lector/cash_limpio.py` las lee como siempre.

    exports de Tango (xlsx)  ->  ESTE MODULO  ->  filas para la Sheet
                                              ->  copia de la Sheet ya con las filas
                                                  (para correr finauto sin esperar)

QUE EXPORT ALIMENTA QUE LISTA
-----------------------------
    Ventas › Cuenta Corriente › Cobranzas a realizar   -> Cuentas a Cobrar
    Compras › Cuenta Corriente › Pagos a realizar       -> Cuentas a Pagar
    Tesorería › Cheques de terceros (En Cartera)        -> Cartera de Cheques (Terceros Recibido)
    Tesorería › Cheques propios (Al Cobro, a vencer)    -> Cartera de Cheques (Propio Emitido)
    Tesorería › Cuentas › Saldos                        -> NO se usa para la caja (ver abajo);
                                                           solo para controles.

LAS TRES REGLAS QUE NO SON OBVIAS (NAVAR, 17/09/2026)
-----------------------------------------------------
1. **Residuos**: Tango arrastra facturas con $0,01 pendiente desde 2018. Todo lo
   que debe $1 o menos se descarta y se cuenta en el resumen.
2. **Deuda vieja**: lo que venció antes del año en curso (facturas de 2007 a
   2025 que nadie dio de baja) entra a la Sheet **marcado con "REVISAR:"** en
   Observaciones. `cash_limpio.py` no lo suma al tablero: lo muestra como
   hallazgo hasta que la persona que carga diga qué es cobrable y qué no.
3. **Cheques propios**: en Tango figuran "Al Cobro" desde 1995 porque nadie los
   marca como debitados (no se concilia). Solo entran los que tienen fecha de
   pago de hoy en adelante; los de los últimos 30 días entran marcados
   "REVISAR:" (pueden estar sin debitar de verdad).

Y una que es un hallazgo, no una regla: los saldos de Tesorería de Tango NO son
la caja. En NAVAR la "CAJA CONTADO" da -$497 M. La caja de hoy sale del banco
(extractos / bots) o de la carga manual, nunca de acá.

COMO SE RECONOCEN LOS ARCHIVOS
------------------------------
Por el nombre, sin importar mayúsculas ni el orden de las palabras:
    "A cobranzas 2026-09-16.xlsx"   -> empresa A,  lista cobranzas
    "AA Cheques terceros.xlsx"      -> empresa AA, cheques de terceros
El prefijo (primera palabra) es la empresa tal como se llama en la Sheet.

Uso:
    python lector/tango.py --carpeta "clientes/navar/privado/tango/2026-09-16" --cliente navar
    python lector/tango.py --carpeta ... --cliente navar --hoy 2026-09-16 \
        --sheet "clientes/navar/privado/NAVAR - Cash Flow (export Sheets 2026-09-12).xlsx"

Deja en la carpeta de los exports:
    para_pegar_en_la_sheet_<hoy>.xlsx   una solapa por lista, listo para pegar
    resumen_tango_<hoy>.md              qué entró, qué se descartó y por qué
y, si se pasó --sheet, al lado de la Sheet original:
    <nombre de la Sheet> (con Tango <hoy>).xlsx
"""

import io
import os
import re
import sys
import glob
import json
import shutil
import argparse
import datetime
import unicodedata
from collections import OrderedDict, defaultdict

BASE_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)

import openpyxl

# La marca que cash_limpio.py entiende como "no lo sumes, mostralo como hallazgo".
MARCA_REVISAR = "REVISAR:"
# Lo que Tango deja pendiente por redondeo. Debajo de esto no es deuda, es basura.
RESIDUO = 1.0
# Cheques propios con fecha pasada hasta este límite entran marcados; más viejos, no entran.
DIAS_CHEQUE_PROPIO_DUDOSO = 30

# Qué palabras del nombre del archivo identifican cada lista. Se busca en orden:
# "cheques propios" antes que "cheques" a secas, etc.
LISTAS = [
    ("cheques_propios", ("cheques propios", "cheque propio")),
    ("cheques_terceros", ("cheques terceros", "cheque tercero", "cheques de terceros")),
    ("cobranzas", ("cobranzas", "cobranza")),
    ("pagos", ("pagos", "pago")),
    ("saldos", ("saldos", "saldo")),
    ("ventas_articulos", ("ventas articulos", "venta articulos", "articulos")),
    ("ventas_detalle", ("ventas detalle", "venta detalle", "detalle")),
    ("movimientos", ("movimientos", "movmientos", "movimiento")),
]

# Encabezados de las solapas de la Sheet, tal cual. Si en la Sheet cambian, se cambian acá.
ENC_COBRAR = ["ID", "Cliente", "Empresa", "Nro Factura", "Fecha Emision", "Fecha Vencimiento",
              "Importe Total", "Cobrado", "Saldo Pendiente", "Estado", "Dias de Atraso", "Observaciones"]
ENC_PAGAR = ["ID", "Proveedor", "Empresa", "Categoria", "Nro Factura / OC", "Fecha Emision",
             "Fecha Vencimiento", "Importe Total", "Pagado", "Saldo Pendiente", "Estado",
             "Dias de Atraso", "Prioridad", "Observaciones"]
ENC_CHEQUES = ["ID", "Tipo", "Empresa", "Nro Cheque", "Banco", "Fecha Emision", "Fecha Pago / Cobro",
               "Beneficiario / Librador", "Importe", "Estado", "Aplicado a (Ref.)", "Observaciones"]
# En la Sheet estas columnas tienen FORMULA en cada fila (saldo = total - cobrado, estado,
# dias de atraso). No se escriben: en la copia se dejan las formulas, y en el archivo
# "para pegar" van vacias para que nadie pegue un valor fijo encima de una formula.
COLS_CON_FORMULA = {"Saldo Pendiente", "Estado", "Dias de Atraso"}


# ------------------------------------------------------------------ helpers
def _norm(s):
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode()
    return " ".join(s.lower().replace("_", " ").split())


def _fecha(v):
    """datetime/date/str -> date, o None."""
    if isinstance(v, datetime.datetime):
        return v.date()
    if isinstance(v, datetime.date):
        return v
    s = str(v or "").strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.datetime.strptime(s[:10], fmt).date()
        except ValueError:
            continue
    return None


def _num(v):
    if v is None or isinstance(v, bool):
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(".", "").replace(",", ".") if "," in str(v) else str(v).strip()
    try:
        return float(s)
    except ValueError:
        return 0.0


def _txt(v):
    return str(v).strip() if v is not None else ""


def _m(v):
    return "$" + format(int(round(abs(v))), ",d").replace(",", ".")


def _tabla(ruta):
    """El export de Tango Live: primera solapa, primera fila = encabezados.
    Devuelve lista de dicts {encabezado normalizado: valor}."""
    wb = openpyxl.load_workbook(ruta, data_only=True)
    ws = wb[wb.sheetnames[0]]
    filas = [r for r in ws.iter_rows(values_only=True) if any(c is not None for c in r)]
    wb.close()
    if not filas:
        return []
    enc = [_norm(c) for c in filas[0]]
    out = []
    for f in filas[1:]:
        out.append(OrderedDict((k, v) for k, v in zip(enc, f) if k))
    return out


def _col(d, *nombres):
    """La columna que mejor coincide con alguno de los textos (sin acentos):
    primero el nombre exacto, después el que empieza así, al final el que lo contiene.
    El orden importa: "estado" tiene que agarrar "estado" y no "fecha subestado"."""
    for n in nombres:
        n = _norm(n)
        for k, v in d.items():
            if k == n:
                return v
    for n in nombres:
        n = _norm(n)
        for k, v in d.items():
            if k.startswith(n):
                return v
    for n in nombres:
        n = _norm(n)
        for k, v in d.items():
            if n in k:
                return v
    return None


# ------------------------------------------------------------------ archivos
def localizar(carpeta):
    """{ (empresa, lista): ruta } a partir de los nombres de los .xlsx."""
    out = {}
    prioridades = {}
    for ruta in sorted(glob.glob(os.path.join(carpeta, "*.xlsx"))):
        nombre = _norm(os.path.splitext(os.path.basename(ruta))[0])
        if nombre.startswith("para pegar") or nombre.startswith("~$"):
            continue
        partes = nombre.split()
        if not partes:
            continue
        empresa = partes[0].upper()
        resto = " ".join(partes[1:])
        lista = None
        for clave, palabras in LISTAS:
            if any(p in resto for p in palabras):
                lista = clave
                break
        if lista:
            # La foto más nueva manda: las mayúsculas del nombre no dicen cuándo se exportó.
            # Sin fecha en el nombre, usamos la modificación; una foto fechada tiene prioridad.
            fechas = re.findall(r"(?<!\d)(\d{4}-\d{2}-\d{2})(?!\d)", nombre)
            fecha = _fecha(fechas[-1]) if fechas else None
            prioridad = (fecha or datetime.date.min, os.path.getmtime(ruta), nombre, ruta)
            clave = (empresa, lista)
            if clave not in prioridades or prioridad > prioridades[clave]:
                prioridades[clave] = prioridad
                out[clave] = ruta
    return out


# ------------------------------------------------------------------ lecturas
def leer_cobranzas(ruta, empresa, hoy, corte_deuda_vieja, origen):
    """Cobranzas a realizar -> filas de "Cuentas a Cobrar"."""
    filas, desc = [], defaultdict(lambda: [0, 0.0])
    for d in _tabla(ruta):
        pend = _num(_col(d, "importe pendiente", "pendiente"))
        total = _num(_col(d, "importe al vencimiento", "al vencimiento", "importe total")) or pend
        venc = _fecha(_col(d, "fecha de vencimiento", "vencimiento"))
        emision = _fecha(_col(d, "fecha de emision", "emision"))
        cliente = _txt(_col(d, "razon social", "cliente"))
        if not venc or not cliente:
            desc["fila de totales de Tango (sin fecha ni cliente)"][0] += 1
            desc["fila de totales de Tango (sin fecha ni cliente)"][1] += pend
            continue
        if pend <= RESIDUO:
            desc["residuo de $1 o menos"][0] += 1
            desc["residuo de $1 o menos"][1] += pend
            continue
        nro = "%s %s" % (_txt(_col(d, "tipo comprobante", "tipo")), _txt(_col(d, "nro. comprobante", "comprobante")))
        cond = _txt(_col(d, "condicion de venta", "condicion"))
        obs = "%s · cond. venta: %s" % (origen, cond or "s/d")
        if venc < corte_deuda_vieja:
            obs = "%s deuda vieja (venció %s) · %s" % (MARCA_REVISAR, venc.strftime("%d/%m/%Y"), obs)
        atraso = (hoy - venc).days if venc < hoy else 0
        filas.append(OrderedDict([
            ("ID", None), ("Cliente", cliente), ("Empresa", empresa), ("Nro Factura", nro.strip()),
            ("Fecha Emision", emision), ("Fecha Vencimiento", venc),
            ("Importe Total", round(total, 2)), ("Cobrado", round(total - pend, 2)),
            ("Saldo Pendiente", round(pend, 2)),
            ("Estado", "Vencido" if venc < hoy else "Pendiente"),
            ("Dias de Atraso", atraso), ("Observaciones", obs),
        ]))
    return filas, desc


def leer_pagos(ruta, empresa, hoy, corte_deuda_vieja, origen, categoria_default, mapa_prov):
    """Pagos a realizar -> filas de "Cuentas a Pagar"."""
    filas, desc = [], defaultdict(lambda: [0, 0.0])
    for d in _tabla(ruta):
        pend = _num(_col(d, "total pendiente", "pendiente"))
        total = _num(_col(d, "total al vencimiento", "al vencimiento", "importe total")) or pend
        venc = _fecha(_col(d, "fecha de vencimiento", "vencimiento"))
        emision = _fecha(_col(d, "fecha de emision", "emision"))
        prov = _txt(_col(d, "razon social", "proveedor"))
        if not venc or not prov:
            desc["fila de totales de Tango (sin fecha ni proveedor)"][0] += 1
            desc["fila de totales de Tango (sin fecha ni proveedor)"][1] += pend
            continue
        if pend <= RESIDUO:
            desc["residuo de $1 o menos"][0] += 1
            desc["residuo de $1 o menos"][1] += pend
            continue
        nro = "%s %s" % (_txt(_col(d, "tipo de comprobante", "tipo")), _txt(_col(d, "nro. comprobante", "comprobante")))
        cod = _txt(_col(d, "cod. proveedor", "codigo"))
        categoria = mapa_prov.get(cod) or mapa_prov.get(prov.upper()) or categoria_default
        obs = origen
        if venc < corte_deuda_vieja:
            obs = "%s deuda vieja (venció %s) · %s" % (MARCA_REVISAR, venc.strftime("%d/%m/%Y"), obs)
        atraso = (hoy - venc).days if venc < hoy else 0
        filas.append(OrderedDict([
            ("ID", None), ("Proveedor", prov), ("Empresa", empresa), ("Categoria", categoria),
            ("Nro Factura / OC", nro.strip()), ("Fecha Emision", emision), ("Fecha Vencimiento", venc),
            ("Importe Total", round(total, 2)), ("Pagado", round(total - pend, 2)),
            ("Saldo Pendiente", round(pend, 2)),
            ("Estado", "Vencido" if venc < hoy else "Pendiente"),
            ("Dias de Atraso", atraso), ("Prioridad", "Media"), ("Observaciones", obs),
        ]))
    return filas, desc


def leer_cheques_terceros(ruta, empresa, hoy, origen):
    """Cheques de terceros -> filas "Terceros Recibido" de "Cartera de Cheques".
    Solo los que están En Cartera: los depositados, aplicados o rechazados ya no son plata por entrar."""
    filas, desc = [], defaultdict(lambda: [0, 0.0])
    for d in _tabla(ruta):
        estado = _txt(_col(d, "estado"))
        importe = _num(_col(d, "importe"))
        if _norm(estado) != "en cartera":
            desc["estado '%s' (no está en cartera)" % (estado or "s/d")][0] += 1
            desc["estado '%s' (no está en cartera)" % (estado or "s/d")][1] += importe
            continue
        cobro = _fecha(_col(d, "fecha del cheque", "fecha de cobro", "fecha cobro"))
        emision = _fecha(_col(d, "fecha de emision", "fecha de origen"))
        if not cobro or not importe:
            desc["sin fecha de cobro o sin importe"][0] += 1
            desc["sin fecha de cobro o sin importe"][1] += importe
            continue
        librador = _txt(_col(d, "razon social", "cliente"))
        obs = origen
        if cobro < hoy:
            obs = "%s fecha de cobro pasada (%s) y sigue en cartera: ¿se depositó y no se registró? · %s" % (
                MARCA_REVISAR, cobro.strftime("%d/%m/%Y"), origen)
        filas.append(OrderedDict([
            ("ID", None), ("Tipo", "Terceros Recibido"), ("Empresa", empresa),
            ("Nro Cheque", _txt(_col(d, "nro. de cheque", "nro cheque", "cheque"))),
            ("Banco", _txt(_col(d, "nombre de banco", "banco"))),
            ("Fecha Emision", emision), ("Fecha Pago / Cobro", cobro),
            ("Beneficiario / Librador", librador), ("Importe", round(abs(importe), 2)),
            ("Estado", "En Cartera"), ("Aplicado a (Ref.)", None), ("Observaciones", obs),
        ]))
    return filas, desc


def leer_cheques_propios(ruta, empresa, hoy, origen):
    """Cheques propios -> filas "Propio Emitido" de "Cartera de Cheques".
    Tango dice "Al Cobro" para todo lo que nunca se marcó debitado (desde 1995). Entra solo lo
    que vence de hoy en adelante; lo de los últimos 30 días entra con REVISAR."""
    filas, desc = [], defaultdict(lambda: [0, 0.0])
    limite = hoy - datetime.timedelta(days=DIAS_CHEQUE_PROPIO_DUDOSO)
    for d in _tabla(ruta):
        estado = _txt(_col(d, "estado"))
        importe = _num(_col(d, "importe mon", "importe"))
        pago = _fecha(_col(d, "fecha del cheque", "fecha de pago"))
        emision = _fecha(_col(d, "fecha de emision"))
        if _norm(estado) != "al cobro":
            desc["estado '%s'" % (estado or "s/d")][0] += 1
            desc["estado '%s'" % (estado or "s/d")][1] += importe
            continue
        if not pago or not importe:
            continue
        if pago < limite:
            desc["'Al Cobro' con fecha anterior a %s (sin conciliar, se descarta)" % limite.strftime("%d/%m/%Y")][0] += 1
            desc["'Al Cobro' con fecha anterior a %s (sin conciliar, se descarta)" % limite.strftime("%d/%m/%Y")][1] += importe
            continue
        obs = origen
        if pago < hoy:
            obs = "%s fecha de pago pasada (%s) y Tango lo tiene 'Al Cobro': confirmar contra el extracto · %s" % (
                MARCA_REVISAR, pago.strftime("%d/%m/%Y"), origen)
        filas.append(OrderedDict([
            ("ID", None), ("Tipo", "Propio Emitido"), ("Empresa", empresa),
            ("Nro Cheque", _txt(_col(d, "nro. de cheque", "nro cheque", "cheque"))),
            ("Banco", _txt(_col(d, "nombre de banco", "banco"))),
            ("Fecha Emision", emision), ("Fecha Pago / Cobro", pago),
            ("Beneficiario / Librador", _txt(_col(d, "razon social", "proveedor"))),
            ("Importe", round(abs(importe), 2)),
            ("Estado", "En Cartera"), ("Aplicado a (Ref.)", _txt(_col(d, "nro. comp", "comprobante")) or None),
            ("Observaciones", obs),
        ]))
    return filas, desc


def leer_saldos(ruta):
    """Saldos de Tesorería: solo para controles (la caja NO sale de acá)."""
    out = []
    for d in _tabla(ruta):
        out.append({"cuenta": _txt(_col(d, "desc", "descripcion")), "tipo": _txt(_col(d, "tipo")),
                    "saldo": _num(_col(d, "saldo"))})
    return out


# ------------------------------------------------------------------ armado
def procesar(carpeta, cliente, hoy=None):
    hoy = datetime.date.fromisoformat(hoy) if isinstance(hoy, str) else (hoy or datetime.date.today())
    corte = datetime.date(hoy.year, 1, 1)
    ruta_cat = os.path.join(BASE_REPO, "clientes", cliente, "catalogo.json")
    with io.open(ruta_cat, encoding="utf-8") as f:
        cat = json.load(f)
    tango_cfg = cat.get("tango", {})
    cat_default = {k: v for k, v in tango_cfg.get("categoria_pagos_por_empresa", {}).items() if not k.startswith("_")}
    mapa_prov = {k: v for k, v in tango_cfg.get("categoria_por_proveedor", {}).items() if not k.startswith("_")}

    archivos = localizar(carpeta)
    fecha_txt = hoy.strftime("%d/%m/%Y")
    listas = {"cobrar": [], "pagar": [], "cheques": []}
    descartes = OrderedDict()
    saldos = {}
    empresas = sorted(set(e for e, _ in archivos))

    for (empresa, lista), ruta in sorted(archivos.items()):
        origen = "Tango Live · %s · %s" % (lista.replace("_", " "), fecha_txt)
        if lista == "cobranzas":
            f, d = leer_cobranzas(ruta, empresa, hoy, corte, origen)
            listas["cobrar"] += f
        elif lista == "pagos":
            f, d = leer_pagos(ruta, empresa, hoy, corte, origen,
                              cat_default.get(empresa, "Proveedores"), mapa_prov)
            listas["pagar"] += f
        elif lista == "cheques_terceros":
            f, d = leer_cheques_terceros(ruta, empresa, hoy, origen)
            listas["cheques"] += f
        elif lista == "cheques_propios":
            f, d = leer_cheques_propios(ruta, empresa, hoy, origen)
            listas["cheques"] += f
        elif lista == "saldos":
            saldos[empresa] = leer_saldos(ruta)
            continue
        else:
            continue   # ventas y movimientos: se leen aparte, no van a estas listas
        descartes[(empresa, lista)] = d

    # Numerar los ID por lista, en orden de vencimiento: así se pegan ordenados.
    for k, filas in listas.items():
        campo = "Fecha Pago / Cobro" if k == "cheques" else "Fecha Vencimiento"
        filas.sort(key=lambda x: (x["Empresa"], x[campo] or datetime.date.max))
        for i, x in enumerate(filas, 1):
            x["ID"] = i

    return {"hoy": hoy, "empresas": empresas, "archivos": archivos, "listas": listas,
            "descartes": descartes, "saldos": saldos, "corte_deuda_vieja": corte}


def escribir_para_pegar(res, carpeta):
    ruta = os.path.join(carpeta, "para_pegar_en_la_sheet_%s.xlsx" % res["hoy"].isoformat())
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for nombre, enc, filas in (("Cuentas a Cobrar", ENC_COBRAR, res["listas"]["cobrar"]),
                               ("Cuentas a Pagar", ENC_PAGAR, res["listas"]["pagar"]),
                               ("Cartera de Cheques", ENC_CHEQUES, res["listas"]["cheques"])):
        ws = wb.create_sheet(nombre)
        ws.append(enc)
        for x in filas:
            ws.append([None if c in COLS_CON_FORMULA and nombre != "Cartera de Cheques" else x.get(c)
                       for c in enc])
        for c in ws.iter_rows(min_row=2):
            for celda in c:
                if isinstance(celda.value, datetime.date):
                    celda.number_format = "DD/MM/YYYY"
    wb.save(ruta)
    return ruta


def escribir_sheet_con_tango(res, sheet_original):
    """Copia de la Sheet exportada con las filas AGREGADO reemplazadas por las de Tango.

    Solo toca las tres solapas de listas. Los agregados de Movimientos y de Saldos
    Bancarios quedan como están: eso no sale de Tango."""
    base, ext = os.path.splitext(sheet_original)
    destino = "%s (con Tango %s)%s" % (base.split(" (export")[0], res["hoy"].isoformat(), ext)
    wb = openpyxl.load_workbook(sheet_original)
    quitadas = {}
    for nombre, enc, filas in (("Cuentas a Cobrar", ENC_COBRAR, res["listas"]["cobrar"]),
                               ("Cuentas a Pagar", ENC_PAGAR, res["listas"]["pagar"]),
                               ("Cartera de Cheques", ENC_CHEQUES, res["listas"]["cheques"])):
        hoja = next((n for n in wb.sheetnames if _norm(n) == _norm(nombre)), None)
        if not hoja:
            continue
        ws = wb[hoja]
        enc_ws = [_txt(c.value) for c in ws[1]]
        idx_obs = next((i for i, e in enumerate(enc_ws) if "observ" in _norm(e)), None)
        # Que habia: agregados o filas reales (la columna 2 es el nombre: Cliente / Proveedor / Tipo).
        n_agr = n_otras = 0
        ultima = 1
        for i, f in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if f[1] in (None, ""):
                continue
            ultima = i
            if idx_obs is not None and "AGREGADO" in _txt(f[idx_obs]).upper():
                n_agr += 1
            else:
                n_otras += 1
        quitadas[nombre] = (n_agr, n_otras)
        # Columnas que se escriben: las que NO tienen formula en la Sheet. Las de formula
        # se dejan como estan (la Sheet las calcula sola fila por fila).
        escribibles = [(j, e) for j, e in enumerate(enc_ws, start=1)
                       if e and (nombre == "Cartera de Cheques" or e not in COLS_CON_FORMULA)]
        # 1. limpiar lo que habia (solo las columnas escribibles)
        for i in range(2, max(ultima, 1) + 1):
            for j, _ in escribibles:
                ws.cell(row=i, column=j).value = None
        # 2. escribir las filas nuevas
        for i, x in enumerate(filas, start=2):
            for j, e in escribibles:
                clave = next((c for c in enc if _norm(c) == _norm(e)), None)
                v = x.get(clave) if clave else None
                celda = ws.cell(row=i, column=j)
                celda.value = v
                if isinstance(v, datetime.date):
                    celda.number_format = "DD/MM/YYYY"
    wb.save(destino)
    return destino, quitadas


def resumen(res, ruta_pegar, destino=None, quitadas=None):
    L = []
    hoy = res["hoy"]
    L.append("# Tango → Sheet · %s" % hoy.strftime("%d/%m/%Y"))
    L.append("")
    L.append("Archivos leídos: %d (empresas: %s)" % (len(res["archivos"]), ", ".join(res["empresas"])))
    for (e, l), r in sorted(res["archivos"].items()):
        L.append("- %s · %s ← `%s`" % (e, l.replace("_", " "), os.path.basename(r)))
    L.append("")

    def _bloque(nombre, filas, campo_monto, campo_fecha, quien):
        L.append("## %s: %d filas" % (nombre, len(filas)))
        por_emp = defaultdict(lambda: [0, 0.0, 0.0, 0.0])   # n, total, vencido, revisar
        for x in filas:
            p = por_emp[x["Empresa"]]
            m = x[campo_monto] or 0
            p[0] += 1
            if _txt(x.get("Observaciones")).startswith(MARCA_REVISAR):
                p[3] += m
            else:
                p[1] += m
                if x[campo_fecha] and x[campo_fecha] < hoy:
                    p[2] += m
        for e, (n, tot, venc, rev) in sorted(por_emp.items()):
            L.append("- **%s**: %d · entra al tablero %s (vencido %s) · marcado REVISAR %s"
                     % (e, n, _m(tot), _m(venc), _m(rev)))
        top = defaultdict(float)
        for x in filas:
            if not _txt(x.get("Observaciones")).startswith(MARCA_REVISAR):
                top[x[quien]] += x[campo_monto] or 0
        for k, v in sorted(top.items(), key=lambda kv: -kv[1])[:8]:
            L.append("    - %s: %s" % (k, _m(v)))
        L.append("")

    _bloque("Cuentas a Cobrar", res["listas"]["cobrar"], "Saldo Pendiente", "Fecha Vencimiento", "Cliente")
    _bloque("Cuentas a Pagar", res["listas"]["pagar"], "Saldo Pendiente", "Fecha Vencimiento", "Proveedor")
    ch = res["listas"]["cheques"]
    for tipo in ("Terceros Recibido", "Propio Emitido"):
        _bloque("Cartera de Cheques · %s" % tipo, [x for x in ch if x["Tipo"] == tipo],
                "Importe", "Fecha Pago / Cobro", "Beneficiario / Librador")

    L.append("## Descartado (no entra a la Sheet)")
    for (e, l), d in res["descartes"].items():
        for motivo, (n, monto) in d.items():
            L.append("- %s · %s: %d por %s — %s" % (e, l.replace("_", " "), n, _m(monto), motivo))
    L.append("")

    if res["saldos"]:
        L.append("## Saldos de Tesorería en Tango (control, NO es la caja)")
        for e, cuentas in sorted(res["saldos"].items()):
            caja = [c for c in cuentas if "caja" in _norm(c["cuenta"])]
            cartera = [c for c in cuentas if _norm(c["tipo"]) == "cartera"]
            bancos = [c for c in cuentas if _norm(c["tipo"]) == "banco" and abs(c["saldo"]) > 0]
            L.append("- **%s**: %s · valores a depositar %s · %d cuentas de banco con saldo (%s)"
                     % (e, "; ".join("%s %s%s" % (c["cuenta"], "-" if c["saldo"] < 0 else "", _m(c["saldo"])) for c in caja),
                        _m(sum(c["saldo"] for c in cartera)), len(bancos),
                        ", ".join("%s %s%s" % (c["cuenta"][:28], "-" if c["saldo"] < 0 else "", _m(c["saldo"])) for c in bancos)))
            en_cartera = sum(x["Importe"] for x in ch if x["Tipo"] == "Terceros Recibido" and x["Empresa"] == e
                             and not _txt(x["Observaciones"]).startswith(MARCA_REVISAR))
            L.append("  - cheques de terceros en cartera según el detalle: %s" % _m(en_cartera))
        L.append("")

    L.append("## Archivos generados")
    L.append("- para pegar en la Sheet: `%s`" % ruta_pegar)
    L.append("  - Se pega solapa por solapa desde la fila 2. Las columnas Saldo Pendiente, Estado y "
             "Dias de Atraso van VACIAS a proposito: en la Sheet son formulas; al pegar, saltearlas "
             "(pegar A:H y despues la columna de Observaciones), o pegar todo y volver a arrastrar las formulas.")
    if destino:
        L.append("- copia de la Sheet con Tango: `%s`" % destino)
        for h, (a, o) in (quitadas or {}).items():
            L.append("  - %s: se quitaron %d filas AGREGADO%s" % (h, a, " y %d filas que NO eran agregado (revisar)" % o if o else ""))
    L.append("")
    L.append("Reglas aplicadas: residuos ≤ %s descartados · vencido antes del %s → REVISAR (deuda vieja) · "
             "cheques propios: solo 'Al Cobro' con fecha ≥ %s, y con REVISAR si la fecha ya pasó."
             % (_m(RESIDUO), res["corte_deuda_vieja"].strftime("%d/%m/%Y"),
                (hoy - datetime.timedelta(days=DIAS_CHEQUE_PROPIO_DUDOSO)).strftime("%d/%m/%Y")))
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="Exports de Tango Live -> listas de la Sheet")
    ap.add_argument("--carpeta", required=True, help="carpeta con los .xlsx exportados de Tango Live")
    ap.add_argument("--cliente", required=True)
    ap.add_argument("--hoy", default=None, help="AAAA-MM-DD; por defecto hoy")
    ap.add_argument("--sheet", default=None, help="la Sheet exportada como .xlsx; si se pasa, deja una copia con las filas de Tango")
    a = ap.parse_args()

    res = procesar(a.carpeta, a.cliente, a.hoy)
    ruta_pegar = escribir_para_pegar(res, a.carpeta)
    destino = quitadas = None
    if a.sheet:
        destino, quitadas = escribir_sheet_con_tango(res, a.sheet)
    txt = resumen(res, ruta_pegar, destino, quitadas)
    ruta_md = os.path.join(a.carpeta, "resumen_tango_%s.md" % res["hoy"].isoformat())
    with io.open(ruta_md, "w", encoding="utf-8") as f:
        f.write(txt + "\n")
    print(txt)
    print("\n(resumen guardado en %s)" % ruta_md)


if __name__ == "__main__":
    main()
