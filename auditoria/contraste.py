# -*- coding: utf-8 -*-
"""
auditoria.contraste — el motor contra los números del propio cliente.

POR QUÉ
-------
Thomas: *"tu faro moral para decir da o no da es la solapa de Posición
Consolidada."*

Hasta que existió esto, cada discusión de números terminaba en *"decime vos si
está bien"*. El cliente ya tiene sus propios números, los mira todos los días y
confía en ellos. Contrastarse contra eso es la única validación que no depende
de que yo tenga razón.

Y sirve para siempre, no una vez: si el motor empieza a diferir después de un
cambio, aparece acá y no tres semanas después en una reunión.

CÓMO SE LEE
-----------
Una diferencia NO es necesariamente un error del motor. Puede ser:

  · un error del motor  → hay que arreglarlo
  · una definición distinta → hay que aclararla y anotarla
  · un error de la planilla → también pasa, y encontrarlo tiene valor

Por eso el módulo NO dice "está mal": muestra las dos cifras, la diferencia, y
deja que una persona decida cuál de las tres cosas es.

Uso:
    python auditoria/contraste.py --contrato c.json
"""

import io
import os
import sys
import json
import argparse

BASE_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)


def _m(v):
    signo = "-" if v < 0 else ""
    return signo + "$" + format(int(round(abs(v))), ",d").replace(",", ".")


def referencias(contrato):
    """Aplana las solapas de referencia en {etiqueta_normalizada: valor}."""
    out = {}
    for hoja, filas in (contrato.get("referencias_del_cliente") or {}).items():
        for f in filas:
            et = " ".join(str(f.get("etiqueta") or "").upper().split())
            out.setdefault(et, {"hoja": hoja, "valor": float(f.get("valor") or 0)})
    return out


def _suma(contrato, clave, estados, unidad=None):
    return sum(float(x.get("importe") or 0) for x in contrato.get(clave, [])
               if not x.get("intercompany")
               and (not estados or x.get("estado") in estados)
               and (unidad is None or (x.get("unidad") or "") == unidad))


# Qué del motor se compara contra qué etiqueta del cliente.
#
# La lista es corta a propósito: solo lo que se puede comparar SIN interpretar.
# Meter comparaciones forzadas convierte el contraste en ruido y deja de mirarse.
COMPARACIONES = [
    ("Caja de hoy", "CAJA HOY (BANCO + EFECTIVO)",
     lambda c: float(c.get("caja_hoy") or 0),
     "Sale de la misma grilla de SALDOS: si no coincide, algo se lee mal."),
    ("Deuda con droguerias por vencer", "DEUDA DROGUERIAS A VENCER",
     lambda c: _suma(c, "deuda_droguerias", ("PENDIENTE",)),
     "Lo que todavia hay que pagar."),
    ("Deuda con droguerias ya vencida", "DEUDA DROGUERIAS VENCIDA",
     lambda c: _suma(c, "deuda_droguerias", ("PAGADO",)),
     "OJO: el motor marca PAGADO lo que tiene fecha pasada, siguiendo la regla "
     "de Thomas ('fecha pasada en deuda = ya se pago'). La Calculadora tiene "
     "'vencida' como categoria propia. Puede que no sean lo mismo."),
    ("Cuentas a cobrar a droguerias", "COBRANZA DROGUERIAS (SPEED)",
     lambda c: _suma(c, "cuentas_a_cobrar_droguerias", ("VENCIDO", "A_VENCER")),
     None),
]

TOLERANCIA = 2.0        # % por debajo del cual se considera que coincide


def contrastar(contrato):
    ref = referencias(contrato)
    out = []
    for nombre, etiqueta, calc, nota in COMPARACIONES:
        r = ref.get(etiqueta)
        if r is None:
            continue
        mio = calc(contrato)
        suyo = r["valor"]
        dif = mio - suyo
        pct = (100.0 * dif / suyo) if suyo else 0.0
        out.append({"nombre": nombre, "etiqueta": etiqueta, "hoja": r["hoja"],
                    "mio": mio, "suyo": suyo, "dif": dif, "pct": pct,
                    "coincide": abs(pct) <= TOLERANCIA, "nota": nota})
    return out, ref


def imprimir(filas, ref):
    L = 82
    print("=" * L)
    print("  EL MOTOR CONTRA LOS NUMEROS DEL CLIENTE")
    print("=" * L)
    if not filas:
        print("  El contrato no trae solapas de referencia.")
        print("  Correr el exportador actualizado para capturarlas.\n")
        return

    print("  %-32s %16s %16s %8s" % ("", "EL CLIENTE", "EL MOTOR", "DIF"))
    print("  " + "-" * (L - 4))
    for f in filas:
        marca = "  ok" if f["coincide"] else "  <--"
        print("  %-32s %16s %16s %7.0f%%%s" % (
            f["nombre"][:32], _m(f["suyo"]), _m(f["mio"]), f["pct"], marca))

    difs = [f for f in filas if not f["coincide"]]
    if difs:
        print("\n  LAS DIFERENCIAS")
        print("  Una diferencia no es necesariamente un error del motor. Puede ser")
        print("  una definicion distinta, o un error de la planilla.\n")
        for f in difs:
            print("   . %s: %s de diferencia" % (f["nombre"], _m(abs(f["dif"]))))
            if f["nota"]:
                linea = "     "
                for p in f["nota"].split():
                    if len(linea) + len(p) + 1 > L - 2:
                        print(linea)
                        linea = "     "
                    linea += p + " "
                print(linea.rstrip())
    else:
        print("\n  Todo coincide dentro del %.0f%%." % TOLERANCIA)

    # Lo que el cliente calcula y el motor todavia no. Es la lista de lo que
    # falta construir, escrita por el propio cliente.
    comparadas = set(f["etiqueta"] for f in filas)
    resto = [(k, v) for k, v in ref.items() if k not in comparadas]
    if resto:
        print("\n" + "=" * L)
        print("  LO QUE EL CLIENTE YA CALCULA Y EL MOTOR TODAVIA NO")
        print("=" * L)
        for k, v in sorted(resto, key=lambda kv: -abs(kv[1]["valor"]))[:14]:
            print("   %-46s %16s" % (k[:46], _m(v["valor"])))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Contraste contra los numeros del cliente")
    ap.add_argument("--contrato", required=True)
    args = ap.parse_args()
    with io.open(args.contrato, encoding="utf-8") as f:
        contrato = json.load(f)
    filas, ref = contrastar(contrato)
    imprimir(filas, ref)


if __name__ == "__main__":
    main()
