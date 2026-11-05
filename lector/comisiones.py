# -*- coding: utf-8 -*-
"""
lector/comisiones — separa los pagos de comisiones a vendedores del resto de los proveedores.

POR QUÉ HACE FALTA
    Los vendedores facturan su comisión como cualquier proveedor. En Tango se distinguen por la
    cuenta contable de la factura (comisiones por ventas), pero la orden de pago solo dice
    "proveedores" y varios bancos ni siquiera traen el nombre de quien cobró. Por eso se necesita
    saber quiénes son los vendedores, y para los pagos por banco, cruzar con Tango.

LA LISTA DE VENDEDORES NO ESTÁ EN EL REPO (es público; son datos personales)
    Vive en Drive: NAVAR - Datos/Comisiones/vendedores.json
        {"vendedores": [{"nombre": "Vendedor Inventado", "cuit": "20-11111111-1"}]}
    Si el archivo no está, no se marca nada y los pagos siguen como proveedores.
    Si hay un vendedor nuevo, se agrega ahí: los lectores releen todo y corrigen lo ya cargado.

CÓMO SE MARCA UN PAGO DE BANCO (siempre egresos)
    1. Si el texto del extracto trae el CUIT de un vendedor, es comisión.
    2. Si no, se busca en la tesorería de A una orden de pago a un vendedor, por ese banco, por el
       mismo importe y con hasta 7 días de diferencia. Cada orden se usa una sola vez.
"""

import glob
import json
import os
import re
import unicodedata

import openpyxl

CATEGORIA = "Comisiones"
RUTA_LISTA = os.path.join("Comisiones", "vendedores.json")
DIAS = 7
PROVEEDORES = "Proveedores MP y Logist."
# Cómo se llama cada banco en Tango y cómo en el extracto ("Frances" es el nombre viejo de BBVA).
BANCOS = {"MACRO": "MACRO", "GALICIA": "GALICIA", "NACION": "NACION", "FRANCES": "BBVA", "BBVA": "BBVA",
          "CORRIENTES": "CORRIENTES"}


def _norm(s):
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode()
    return " ".join(s.upper().split())


def solo_digitos(s):
    return re.sub(r"\D", "", str(s or ""))


def cargar_vendedores(raiz):
    """CUITs (solo dígitos) de la lista de Drive. Sin archivo: conjunto vacío."""
    ruta = os.path.join(raiz, RUTA_LISTA)
    if not os.path.isfile(ruta):
        return set()
    with open(ruta, encoding="utf-8") as f:
        lista = json.load(f).get("vendedores", [])
    cuits = {solo_digitos(v.get("cuit")) for v in lista}
    malos = [c for c in cuits if len(c) != 11]
    if malos:
        raise ValueError("%s tiene %d CUIT que no son de 11 dígitos" % (RUTA_LISTA, len(malos)))
    return cuits


def _banco(texto):
    t = _norm(texto)
    for clave, banco in BANCOS.items():
        if clave in t:
            return banco
    return None


def pagos_de_banco(raiz, vendedores):
    """Órdenes de pago a vendedores que salieron por un banco, según la tesorería de A más nueva."""
    if not vendedores:
        return []
    archivos = [x for x in glob.glob(os.path.join(raiz, "Tesoreria A detalle", "*.xlsx"))
                if not x.lower().endswith(".parte.xlsx")]
    if not archivos:
        return []
    wb = openpyxl.load_workbook(max(archivos, key=os.path.getmtime), read_only=True, data_only=True)
    try:
        filas = wb.active.iter_rows(values_only=True)
        enc = {_norm(c): i for i, c in enumerate(next(filas, ())) if c}
        faltan = [c for c in ("FECHA", "COD. COMPROBANTE", "DESC. CONTABLE", "HABER (CTE) (RENGLON)",
                              "CUIT PROVEEDOR (ENCAB.)") if c not in enc]
        if faltan:
            raise ValueError("el detalle de tesorería de A no trae: " + ", ".join(faltan))
        salida = []
        for r in filas:
            fecha = r[enc["FECHA"]]
            haber = r[enc["HABER (CTE) (RENGLON)"]] or 0
            cuenta = r[enc["DESC. CONTABLE"]]
            if str(r[enc["COD. COMPROBANTE"]] or "").strip().upper() != "O/P" or not hasattr(fecha, "date"):
                continue
            if haber > 0 and "BANCO" in _norm(cuenta) and solo_digitos(r[enc["CUIT PROVEEDOR (ENCAB.)"]]) in vendedores:
                salida.append({"fecha": fecha.date(), "importe": float(haber), "banco": _banco(cuenta)})
        return salida
    finally:
        wb.close()


def _fecha(v):
    return v.date() if hasattr(v, "date") else v


def _marcar(fila, motivo):
    fila["Categoria"] = CATEGORIA
    fila["Observaciones"] = "%s · comisión a vendedor: %s" % (fila.get("Observaciones") or "", motivo)


def marcar_banco(filas, vendedores, pagos):
    """Pasa a Comisiones los egresos de banco que son pagos a vendedores. Devuelve cuántos marcó."""
    libres = list(pagos)
    marcados = 0
    candidatas = [f for f in filas if f["Tipo"] == "Egreso" and f["Importe"] < 0 and f["Categoria"] != CATEGORIA]

    def tomar(fila):
        """La orden de pago libre que corresponde a esta fila, la más cercana en fecha, o None."""
        banco = _banco(fila["Banco / Cuenta"])
        posibles = [p for p in libres if abs(p["importe"] + fila["Importe"]) < 1 and p["banco"] in (None, banco)
                    and abs((p["fecha"] - _fecha(fila["Fecha"])).days) <= DIAS]
        if not posibles:
            return None
        p = min(posibles, key=lambda x: abs((x["fecha"] - _fecha(fila["Fecha"])).days))
        libres.remove(p)
        return p

    # Primero las que traen el CUIT: es el dato más seguro y consume su orden de pago.
    for fila in candidatas:
        if fila["Categoria"] in (PROVEEDORES, "Otros") and \
                set(re.findall(r"\d{11}", solo_guiones(fila["Concepto / Detalle"]))) & vendedores:
            tomar(fila)
            _marcar(fila, "el extracto trae su CUIT")
            marcados += 1
    for fila in candidatas:
        if fila["Categoria"] == PROVEEDORES and tomar(fila):
            _marcar(fila, "coincide con una orden de pago de Tango")
            marcados += 1
    return marcados


def solo_guiones(s):
    """Saca los guiones para que un CUIT 20-11111111-1 se lea como 11 dígitos seguidos."""
    return str(s or "").replace("-", "")
