# -*- coding: utf-8 -*-
"""
simulador.proyeccion — la proyección del mes, deducida del historial.

EL PROBLEMA (planteado por Thomas)
----------------------------------
    "yo por lo general cargaba las proyecciones de forma manual, replicando el
     mes anterior, en las demas empresas como lo voy a hacer? No quiero que sea
     algo que me tome dias."

Es la pregunta correcta, y es la que decide si esto es un producto o una
consultoría. Si cada cliente nuevo son tres días de cargar proyecciones a mano,
no hay negocio: hay un trabajo.

LA IDEA
-------
"Replicar el mes anterior" no es criterio, es un ALGORITMO. Lo que hace una
persona mirando la planilla es: ver qué se repite todos los meses, con qué
importe y alrededor de qué día. Eso se deduce del historial de movimientos, que
es justamente lo que el bot ya baja del banco.

Entonces el onboarding de un cliente nuevo pasa de:

    "cargá a mano las ~200 proyecciones del mes"          (días)
    a
    "revisá estas 200 que te propongo y corregí las que estén mal"   (un rato)

NO ES ADIVINAR
--------------
Este módulo NO inventa: solo repite lo que ya pasó, y dice con cuánta confianza.
Un movimiento que aparecio 4 de 4 meses el día 10 es una cosa; uno que apareció
1 de 4 es otra, y va marcado como tal para que una persona decida.

Y no sabe NADA de farmacias, droguerías ni de MAGA. Recibe movimientos con
fecha, concepto e importe: lo mismo que tiene cualquier empresa.

Uso:
    python simulador/proyeccion.py --contrato c.json --mes 2026-10
    python simulador/proyeccion.py --contrato c.json --backtest 2026-08
"""

import io
import os
import re
import sys
import json
import argparse
import datetime
import statistics
from collections import defaultdict

BASE_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)

from simulador.semana import _m


# ------------------------------------------------------------------ texto
MESES = ("ENERO FEBRERO MARZO ABRIL MAYO JUNIO JULIO AGOSTO SEPTIEMBRE "
         "SETIEMBRE OCTUBRE NOVIEMBRE DICIEMBRE").split()

# Meses y números se sacan del concepto para poder AGRUPAR. Sin esto,
# "honorarios junio Veronica" y "honorarios julio Veronica" parecen dos gastos
# distintos que pasaron una sola vez cada uno, cuando en realidad son el mismo
# gasto mensual. Es normalización de texto en castellano, no conocimiento de
# ningún cliente en particular.
def limpiar(concepto):
    s = (concepto or "").upper()
    for a, b in (("Á", "A"), ("É", "E"), ("Í", "I"), ("Ó", "O"), ("Ú", "U"), ("Ñ", "N")):
        s = s.replace(a, b)
    for mes in MESES:
        s = re.sub(r"\b%s\b" % mes, " ", s)
    s = re.sub(r"\b20\d\d\b", " ", s)          # años
    s = re.sub(r"\b\d{1,2}[-/]\d{1,2}\b", " ", s)   # 07-26, 3/9
    s = re.sub(r"\d+", " ", s)                 # cualquier otro número
    s = re.sub(r"[^A-Z ]", " ", s)
    return " ".join(s.split())


# A que NIVEL se busca la repeticion. No es un detalle: es LA decision.
#
#   'concepto' -> agrupa por el texto que escribio el administrativo.
#                 Suena mas preciso y es mucho peor: el mismo gasto se escribe
#                 distinto cada mes ("Sueldos Comafi" un mes, "Cs. Agosto" el
#                 otro) y el modelo los ve como dos gastos que pasaron una vez.
#
#   'tipo'     -> agrupa por la categoria del catalogo (SUELDO, ALQUILER...).
#                 Es como proyecta una persona: "los sueldos, alrededor del 4,
#                 unos X millones". El texto libre cambia; la categoria no.
def clave(mov, nivel="tipo"):
    tipo = (mov.get("tipo") or "").upper().strip()
    if nivel == "tipo":
        return tipo
    return "%s|%s" % (tipo, limpiar(mov.get("concepto")))


def mes_de(f):
    return f[:7] if f else None


def _sig_mes(mes):
    a, m = int(mes[:4]), int(mes[5:7])
    return "%04d-%02d" % (a + 1, 1) if m == 12 else "%04d-%02d" % (a, m + 1)


# ------------------------------------------------------------------ modelo
def aprender(movimientos, hasta_mes, meses_atras=6, nivel="tipo"):
    """Arma el patrón de cada gasto recurrente mirando los meses ANTERIORES.

    'hasta_mes' NO se incluye: es el que se quiere proyectar. Así el backtest es
    honesto (no puede espiar el resultado).
    """
    meses_previos = sorted(set(mes_de(x.get("fecha")) for x in movimientos
                               if x.get("fecha") and mes_de(x["fecha"]) < hasta_mes))
    meses_previos = meses_previos[-meses_atras:]
    if not meses_previos:
        return {}, []

    por_clave = defaultdict(lambda: defaultdict(list))
    for x in movimientos:
        f = x.get("fecha")
        if not f:
            continue
        m = mes_de(f)
        if m not in meses_previos:
            continue
        por_clave[clave(x, nivel)][m].append(x)

    patrones = {}
    for k, meses in por_clave.items():
        apariciones = len(meses)
        # Un movimiento se resume por mes: si un proveedor cobra 3 veces en el
        # mismo mes, para la proyeccion lo que importa es el total mensual.
        totales, dias, ejemplos = [], [], []
        for m, movs in meses.items():
            totales.append(sum(float(x.get("importe") or 0) for x in movs))
            dias.append(int(min(x["fecha"][8:10] for x in movs)))
            ejemplos.append(movs[0])
        patrones[k] = {
            "clave": k,
            "tipo": ejemplos[0].get("tipo") or "",
            "concepto": ejemplos[0].get("concepto") or "",
            "apariciones": apariciones,
            "de_meses": len(meses_previos),
            "dia": int(statistics.median(dias)),
            "importe": float(statistics.median(totales)),
            "ultimo": totales[-1],
            "variacion": _variacion(totales),
        }
    return patrones, meses_previos


def _variacion(vals):
    """Cuánto se mueve el importe entre meses, en %. Sirve para saber si el
    número se puede dar por bueno o hay que preguntarlo."""
    vals = [abs(v) for v in vals if v]
    if len(vals) < 2:
        return None
    med = statistics.median(vals)
    if not med:
        return None
    return 100.0 * (max(vals) - min(vals)) / med


def proyectar(patrones, mes, minimo_apariciones=2):
    """Propone los movimientos del mes, ordenados por confianza."""
    a, m = int(mes[:4]), int(mes[5:7])
    ultimo_dia = (datetime.date(a + (m == 12), (m % 12) + 1, 1) - datetime.timedelta(days=1)).day
    out = []
    for p in patrones.values():
        if p["apariciones"] < minimo_apariciones:
            continue
        dia = min(p["dia"], ultimo_dia)
        out.append(dict(p, fecha="%s-%02d" % (mes, dia),
                        confianza=p["apariciones"] / float(p["de_meses"])))
    return sorted(out, key=lambda x: (-x["confianza"], -abs(x["importe"])))


# ------------------------------------------------------------------ backtest
def backtest(movimientos, mes, minimo_apariciones=2, nivel="tipo"):
    """La única prueba que vale: proyectar un mes que YA pasó y comparar.

    Se aprende solo con los meses anteriores, así que el modelo no puede ver la
    respuesta. Devuelve cuánto del mes real habría quedado cubierto.
    """
    patrones, meses_previos = aprender(movimientos, mes, nivel=nivel)
    prop = proyectar(patrones, mes, minimo_apariciones)
    propuesto = dict((p["clave"], p) for p in prop)

    reales = defaultdict(list)
    for x in movimientos:
        if mes_de(x.get("fecha")) == mes:
            reales[clave(x, nivel)].append(x)

    aciertos, faltantes, total_real, total_acertado = [], [], 0.0, 0.0
    for k, movs in reales.items():
        imp = sum(float(x.get("importe") or 0) for x in movs)
        total_real += imp
        if k in propuesto:
            p = propuesto[k]
            dia_real = int(min(x["fecha"][8:10] for x in movs))
            aciertos.append({
                "concepto": movs[0].get("concepto", ""),
                "real": imp, "proyectado": p["importe"],
                "dia_real": dia_real, "dia_proy": p["dia"],
                "err_monto": (abs(imp - p["importe"]) / abs(imp) * 100.0) if imp else 0.0,
                "err_dias": abs(dia_real - p["dia"]),
            })
            total_acertado += imp
        else:
            faltantes.append({"concepto": movs[0].get("concepto", ""), "importe": imp,
                              "n": len(movs)})

    sobrantes = [p for k, p in propuesto.items() if k not in reales]
    return {"mes": mes, "nivel": nivel, "meses_previos": meses_previos,
            "propuestos": len(prop), "reales": len(reales),
            "aciertos": aciertos, "faltantes": faltantes, "sobrantes": sobrantes,
            "total_real": total_real, "total_acertado": total_acertado}


# ------------------------------------------------------------------ salida
def imprimir_backtest(r):
    L = 76
    print("=" * L)
    print("  BACKTEST DE LA PROYECCION  .  mes %s  .  nivel: %s" % (r["mes"], r["nivel"]))
    print("=" * L)
    print("  Aprendio SOLO con: %s" % ", ".join(r["meses_previos"]))
    print("  (el mes %s no se mira hasta el momento de comparar)\n" % r["mes"])

    n_ok = len(r["aciertos"])
    print("  COBERTURA")
    print("    Grupos distintos que pasaron en %s   : %d" % (r["mes"], r["reales"]))
    print("    De esos, el modelo habia propuesto     : %d  (%.0f%%)" % (
        n_ok, 100.0 * n_ok / r["reales"] if r["reales"] else 0))
    print("    En plata                               : %s de %s  (%.0f%%)" % (
        _m(r["total_acertado"]), _m(r["total_real"]),
        100.0 * r["total_acertado"] / r["total_real"] if r["total_real"] else 0))

    if r["aciertos"]:
        errm = statistics.median([a["err_monto"] for a in r["aciertos"]])
        errd = statistics.median([a["err_dias"] for a in r["aciertos"]])
        print("\n  PRECISION (mediana de los que acerto)")
        print("    Error de importe : %.0f%%" % errm)
        print("    Error de fecha   : %.0f dia(s)" % errd)
        exactos = sum(1 for a in r["aciertos"] if a["err_dias"] <= 2 and a["err_monto"] <= 10)
        print("    Casi clavados (+-2 dias y +-10%%): %d de %d" % (exactos, n_ok))

    if r["faltantes"]:
        tot = sum(f["importe"] for f in r["faltantes"])
        print("\n  LO QUE EL MODELO NO VIO VENIR (%d conceptos, %s)" % (len(r["faltantes"]), _m(tot)))
        print("  Esto es lo que una persona tiene que cargar igual:")
        for f in sorted(r["faltantes"], key=lambda x: -abs(x["importe"]))[:8]:
            print("     . %-42s %s" % (f["concepto"][:42], _m(f["importe"])))

    if r["sobrantes"]:
        print("\n  PROPUSO Y NO PASO (%d): se descartan de un vistazo" % len(r["sobrantes"]))
        for s in sorted(r["sobrantes"], key=lambda x: -abs(x["importe"]))[:5]:
            print("     . %-42s %s" % (s["concepto"][:42], _m(s["importe"])))


def imprimir_proyeccion(prop, mes):
    L = 76
    print("=" * L)
    print("  PROYECCION PROPUESTA PARA %s" % mes)
    print("=" * L)
    print("  %d movimientos. Revisar y corregir; no es para usar a ciegas.\n" % len(prop))
    seguros = [p for p in prop if p["confianza"] >= 0.99]
    dudosos = [p for p in prop if p["confianza"] < 0.99]

    def bloque(titulo, items):
        if not items:
            return
        print("  %s (%d)" % (titulo, len(items)))
        print("  %-10s %-40s %16s %6s" % ("FECHA", "CONCEPTO", "IMPORTE", "VAR"))
        for p in items[:40]:
            v = "" if p["variacion"] is None else "%.0f%%" % p["variacion"]
            print("  %-10s %-40s %16s %6s" % (p["fecha"], p["concepto"][:40], _m(p["importe"]), v))
        if len(items) > 40:
            print("  ... y %d mas" % (len(items) - 40))
        print("")

    bloque("PASA TODOS LOS MESES (confianza alta)", seguros)
    bloque("PASA CASI SIEMPRE (revisar)", dudosos)
    print("  Total proyectado: %s" % _m(sum(p["importe"] for p in prop)))
    print("\n  'VAR' = cuanto se movio el importe entre meses. Arriba de 30% conviene")
    print("  mirarlo: es un gasto que cambia y el numero es apenas una referencia.")


def main():
    ap = argparse.ArgumentParser(description="Proyeccion del mes deducida del historial")
    ap.add_argument("--contrato", required=True)
    ap.add_argument("--mes", help="mes a proyectar (aaaa-mm)")
    ap.add_argument("--backtest", help="mes YA pasado, para medir cuanto acierta")
    ap.add_argument("--nivel", choices=["tipo", "concepto"], default="tipo",
                    help="a que nivel buscar la repeticion (default: tipo)")
    ap.add_argument("--minimo", type=int, default=2,
                    help="en cuantos meses tiene que haber aparecido (default 2)")
    args = ap.parse_args()

    with io.open(args.contrato, encoding="utf-8") as f:
        movs = json.load(f).get("movimientos", [])

    if args.backtest:
        imprimir_backtest(backtest(movs, args.backtest, args.minimo, args.nivel))
        return
    mes = args.mes or _sig_mes(max(mes_de(x["fecha"]) for x in movs if x.get("fecha")))
    patrones, _ = aprender(movs, mes, nivel=args.nivel)
    imprimir_proyeccion(proyectar(patrones, mes, args.minimo), mes)


if __name__ == "__main__":
    main()
