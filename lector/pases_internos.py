# -*- coding: utf-8 -*-
"""
lector/pases_internos — encuentra la otra pata de los pases entre cuentas propias.

POR QUÉ HACE FALTA
    Un pase entre dos cuentas de la empresa aparece dos veces: sale de un banco y entra en otro.
    Muchas veces un solo banco dice que es de la misma titularidad. El otro escribe un texto
    genérico ("transferencia", "crédito") y sus reglas lo toman como cobranza o como proveedor.
    Así se contaba una cobranza o un pago que nunca existieron.

CÓMO LA ENCUENTRA
    1. Junta entre sí las transferencias internas que ya se cancelan (importe opuesto, otra cuenta,
       hasta 3 días de diferencia). Las que quedan sueltas son las que no tienen su otra pata.
    2. Para cada suelta busca un movimiento de otra cuenta, del MISMO día y por el importe opuesto,
       clasificado como cobranza, proveedor u otros.
    3. Si hay exactamente uno, es la otra pata y pasa a transferencia interna. Si hay más de uno, no
       se adivina: queda como está y el control de cierre del Cash Mensual lo sigue mostrando.
"""

import datetime

INTERNA = "Transferencia Interna"
# Lo único que se puede reclasificar: sueldos, impuestos o préstamos tienen textos propios del banco.
CORREGIBLES = ("Cobranza Facturas", "Proveedores MP y Logist.", "Otros")
DIAS_ENTRE_INTERNAS = 3
TOLERANCIA = 1          # pesos


def _dia(valor):
    return valor.date() if isinstance(valor, datetime.datetime) else valor


def _opuestos(a, b):
    return abs(a["Importe"] + b["Importe"]) < TOLERANCIA and a["Banco / Cuenta"] != b["Banco / Cuenta"]


def sueltas(filas):
    """Las transferencias internas que no tienen otra interna que las cancele."""
    pendientes = sorted((f for f in filas if f["Categoria"] == INTERNA), key=lambda f: _dia(f["Fecha"]))
    resultado = []
    while pendientes:
        a = pendientes.pop(0)
        posibles = [b for b in pendientes if _opuestos(a, b)
                    and abs((_dia(a["Fecha"]) - _dia(b["Fecha"])).days) <= DIAS_ENTRE_INTERNAS]
        if posibles:
            b = min(posibles, key=lambda x: abs((_dia(a["Fecha"]) - _dia(x["Fecha"])).days))
            pendientes = [f for f in pendientes if f is not b]
        else:
            resultado.append(a)
    return resultado


def marcar(filas):
    """Pasa a interna la otra pata de cada pase suelto. Devuelve cuántas filas cambió."""
    cambiadas = 0
    for suelta in sueltas(filas):
        posibles = [f for f in filas if f["Categoria"] in CORREGIBLES and _opuestos(suelta, f)
                    and _dia(f["Fecha"]) == _dia(suelta["Fecha"])]
        if len(posibles) != 1:
            continue
        f = posibles[0]
        f["Categoria"] = INTERNA
        f["Medio de Pago"] = "Transferencia"
        f["Observaciones"] = "INTERNO (no es ingreso ni gasto) · %s · otra pata de un pase desde %s" % (
            f.get("Observaciones") or "", suelta["Banco / Cuenta"])
        cambiadas += 1
    return cambiadas
