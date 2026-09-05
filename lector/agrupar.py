# -*- coding: utf-8 -*-
"""
lector.agrupar — proponer los rubros cuando la planilla no los tiene.

EL CASO
-------
Una empresa chica suele tener tres columnas: fecha, concepto e importe. Sin una
columna de categoria, el motor se queda sin nada: el proyector cae del 93% al 4%
de cobertura, porque el mismo gasto se escribe distinto cada mes.

Pero la informacion ESTA: esta escrita en el texto que carga el administrativo.
Medido sobre 1069 movimientos reales, el 69% tiene alguna palabra en el concepto
que predice su rubro. Lo que falta no es el dato: falta agruparlo y ponerle
nombre.

QUE HACE Y QUE NO
-----------------
Agrupa los conceptos por las palabras que comparten y ordena los grupos por
plata. NO les pone nombre ni decide si se pueden postergar: eso lo hace una
persona, con el cliente. La salida es una propuesta para revisar, no una
clasificacion terminada.

Es a ciegas a proposito: no mira ninguna columna de categoria, porque el caso
para el que existe es justamente cuando esa columna no existe.

COMO SE EVALUA
--------------
Con --evaluar, sobre una planilla que SI tiene categoria: se agrupa ignorandola
y despues se compara. La medida es la PUREZA: de cada grupo propuesto, que
fraccion cae en un mismo rubro real. Un grupo puro es uno que una persona puede
mirar y nombrar de un saque.

Uso:
    python lector/agrupar.py --contrato c.json
    python lector/agrupar.py --contrato c.json --evaluar
"""

import io
import os
import re
import sys
import json
import argparse
import unicodedata
from collections import Counter, defaultdict

BASE_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)


# Palabras que aparecen en todos lados y no distinguen nada. No es una lista de
# ningun cliente: son conectores del castellano y terminos administrativos que
# se repiten en cualquier planilla.
GENERICAS = set("""
PARA POR CON SIN DEL LOS LAS UNA UNOS UNAS ESTE ESTA ESTOS ESTAS
PAGO PAGOS PAGAR ABONO COBRO COBROS TRANSFERENCIA TRANSFERENCIAS TRANSF
FACTURA FACTURAS FACT COMPROBANTE RECIBO NOTA
CUENTA CUENTAS BANCO BANCARIA MOVIMIENTO SALDO IMPORTE TOTAL
ENERO FEBRERO MARZO ABRIL MAYO JUNIO JULIO AGOSTO SEPTIEMBRE SETIEMBRE
OCTUBRE NOVIEMBRE DICIEMBRE
""".split())

MIN_LARGO = 4      # palabras mas cortas casi nunca distinguen
MIN_GRUPO = 3      # un grupo de 1 o 2 no es un rubro, es ruido


def tokens(concepto):
    s = unicodedata.normalize("NFD", str(concepto or "").upper())
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = re.sub(r"[^A-Z ]", " ", s)
    return [p for p in s.split()
            if len(p) >= MIN_LARGO and p not in GENERICAS]


def proponer(movimientos, minimo=MIN_GRUPO):
    """Agrupa los movimientos por la palabra mas distintiva que comparten.

    'Distintiva' = la que aparece en menos movimientos entre las que comparte.
    Una palabra rara une mejor que una comun: SUIZO junta los pagos a esa
    drogueria; DROGUERIA los junta con todas las demas.
    """
    movs = [m for m in movimientos if (m.get("concepto") or "").strip()]
    if not movs:
        return [], []

    freq = Counter()
    for m in movs:
        freq.update(set(tokens(m["concepto"])))

    # Se descartan las palabras que aparecen en CASI TODO: no separan nada.
    #
    # El tope estaba en 0.4 y era puro costo. En una empresa con tres rubros,
    # cada rubro es el 33% de los movimientos y quedaba peligrosamente cerca de
    # ese limite: con 11 movimientos y 2 rubros, se descartaba TODO y no armaba
    # un solo grupo. Medido sobre 1069 movimientos reales, subirlo a 0.7 no
    # cambia nada (123 grupos, 87% de pureza, mismos sueltos) y arregla del todo
    # el caso de la planilla chica, que es justo el cliente al que apuntamos.
    tope = max(minimo, len(movs) * 0.7)
    utiles = set(t for t, n in freq.items() if minimo <= n <= tope)

    grupos = defaultdict(list)
    sueltos = []
    for m in movs:
        ts = [t for t in set(tokens(m["concepto"])) if t in utiles]
        if not ts:
            sueltos.append(m)
            continue
        # la menos frecuente = la mas especifica
        grupos[min(ts, key=lambda t: freq[t])].append(m)

    out = []
    for t, ms in grupos.items():
        if len(ms) < minimo:
            sueltos.extend(ms)
            continue
        imp = sum(abs(float(x.get("importe") or 0)) for x in ms)
        ejemplos = [x["concepto"][:52] for x in
                    sorted(ms, key=lambda x: -abs(float(x.get("importe") or 0)))[:3]]
        out.append({"palabra": t, "movimientos": len(ms), "importe": imp,
                    "ejemplos": ejemplos, "_movs": ms})
    out.sort(key=lambda g: -g["importe"])
    return out, sueltos


def pureza(grupos, campo="tipo"):
    """Que fraccion de cada grupo cae en un mismo rubro real.

    Solo se puede calcular cuando la planilla YA tiene categoria, y sirve para
    saber si agrupar a ciegas da grupos que una persona pueda nombrar.
    """
    filas, total, puros = [], 0, 0
    for g in grupos:
        c = Counter((m.get(campo) or "?") for m in g["_movs"])
        may, n = c.most_common(1)[0]
        p = n / float(len(g["_movs"]))
        filas.append({"palabra": g["palabra"], "n": len(g["_movs"]),
                      "importe": g["importe"], "mayoria": may, "pureza": p,
                      "distintos": len(c)})
        total += len(g["_movs"])
        puros += n
    return filas, (puros / float(total) if total else 0.0)


def _m(v):
    return "$" + format(int(round(abs(v))), ",d").replace(",", ".")


def imprimir(grupos, sueltos, total_movs):
    L = 78
    print("=" * L)
    print("  RUBROS PROPUESTOS  (la planilla no trae categoria)")
    print("=" * L)
    tot = sum(g["importe"] for g in grupos) + sum(
        abs(float(m.get("importe") or 0)) for m in sueltos)
    print("  %d grupo(s) sobre %d movimientos. %d quedaron sueltos.\n"
          % (len(grupos), total_movs, len(sueltos)))
    print("  Esto es una PROPUESTA para revisar con el cliente, no una")
    print("  clasificacion. Lo que hay que preguntar de cada grupo es como se")
    print("  llama y cuantos dias se puede postergar.\n")
    print("  %-16s %6s %16s %6s  %s" % ("AGRUPA POR", "MOVS", "IMPORTE", "%", "EJEMPLOS"))
    print("  " + "-" * (L - 4))
    for g in grupos[:25]:
        print("  %-16s %6d %16s %5.0f%%  %s" % (
            g["palabra"][:16], g["movimientos"], _m(g["importe"]),
            100.0 * g["importe"] / tot if tot else 0, g["ejemplos"][0][:30]))
        for e in g["ejemplos"][1:]:
            print("  %-16s %6s %16s %6s  %s" % ("", "", "", "", e[:30]))
    if len(grupos) > 25:
        print("  ... y %d grupo(s) mas" % (len(grupos) - 25))
    if sueltos:
        imp = sum(abs(float(m.get("importe") or 0)) for m in sueltos)
        print("\n  SIN AGRUPAR: %d movimientos, %s (%.0f%% de la plata)"
              % (len(sueltos), _m(imp), 100.0 * imp / tot if tot else 0))
        print("  Son conceptos que no comparten palabra con ningun otro.")
        for m in sorted(sueltos, key=lambda x: -abs(float(x.get("importe") or 0)))[:5]:
            print("   . %-46s %s" % (m["concepto"][:46], _m(float(m.get("importe") or 0))))


def imprimir_evaluacion(filas, global_, grupos):
    L = 78
    print("\n" + "=" * L)
    print("  EVALUACION  (la planilla SI tenia categoria: se ignoro y se comparo)")
    print("=" * L)
    print("  Pureza global: %.0f%%" % (100 * global_))
    print("  = de cada grupo propuesto, que fraccion cae en un mismo rubro real.\n")
    buenos = [f for f in filas if f["pureza"] >= 0.9]
    print("  Grupos con pureza >= 90%%: %d de %d" % (len(buenos), len(filas)))
    print("")
    print("  %-16s %6s %10s %8s  %s" % ("AGRUPA POR", "MOVS", "PUREZA", "RUBROS", "RUBRO REAL"))
    print("  " + "-" * (L - 4))
    for f in sorted(filas, key=lambda x: -x["importe"])[:18]:
        print("  %-16s %6d %9.0f%% %8d  %s" % (
            f["palabra"][:16], f["n"], 100 * f["pureza"], f["distintos"], f["mayoria"][:24]))
    malos = [f for f in filas if f["pureza"] < 0.6]
    if malos:
        print("\n  Los que mezclan rubros (pureza < 60%%): %d" % len(malos))
        for f in sorted(malos, key=lambda x: -x["importe"])[:5]:
            print("   . %-16s %d movs, %d rubros distintos" % (
                f["palabra"][:16], f["n"], f["distintos"]))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="Proponer rubros a partir del concepto")
    ap.add_argument("--contrato", required=True)
    ap.add_argument("--evaluar", action="store_true",
                    help="comparar contra la categoria real (si la planilla la tiene)")
    ap.add_argument("--minimo", type=int, default=MIN_GRUPO)
    ap.add_argument("--salida", help="guardar la propuesta en un json")
    args = ap.parse_args()

    with io.open(args.contrato, encoding="utf-8") as f:
        movs = json.load(f).get("movimientos", [])

    grupos, sueltos = proponer(movs, args.minimo)
    imprimir(grupos, sueltos, len(movs))

    if args.evaluar:
        if not any(m.get("tipo") for m in movs):
            print("\n  No se puede evaluar: los movimientos no traen categoria.")
        else:
            filas, g = pureza(grupos)
            imprimir_evaluacion(filas, g, grupos)

    if args.salida:
        limpio = [{k: v for k, v in g.items() if k != "_movs"} for g in grupos]
        with io.open(args.salida, "w", encoding="utf-8") as f:
            f.write(json.dumps({"grupos": limpio}, ensure_ascii=False, indent=2))
        print("\n  Propuesta: %s" % args.salida)


if __name__ == "__main__":
    main()
