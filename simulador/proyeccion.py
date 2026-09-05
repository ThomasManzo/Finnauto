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


# ================================================================ horizonte
# Proyectar 45 dias no es "proyectar un mes y medio". Mirando 4 meses de datos
# reales aparecen dos comportamientos muy distintos, y tratarlos igual es lo que
# hacia que el error de importe fuera del 50%:
#
#   DIFUSO  - pasa casi todos los dias habiles (sueldos, impuestos, servicios,
#             efectivo). Preguntarse "que dia cae" no tiene sentido: lo que
#             importa es cuanto drena por dia.
#   EVENTO  - cae en dias puntuales del mes (alquiler, VEP AFIP, cuota de
#             prestamo). Ahi si importa el dia, y el importe suele repetirse.
#
# Ademas, el 98% de los movimientos cae en dia habil: proyectar sabados y
# domingos ensucia la curva justo donde se toman las decisiones.
UMBRAL_DIFUSO = 0.35     # fraccion de dias habiles con movimiento


def _habiles(desde, hasta):
    out, f = [], desde
    while f <= hasta:
        if f.weekday() < 5:
            out.append(f)
        f += datetime.timedelta(days=1)
    return out


def perfilar(movimientos, hasta_fecha, meses_atras=6, nivel="tipo"):
    """Perfil de cada grupo: difuso o evento, con su ritmo.

    'hasta_fecha' no se incluye: todo lo que se aprende es anterior a esa fecha.
    """
    corte = hasta_fecha.isoformat()
    desde = (hasta_fecha - datetime.timedelta(days=meses_atras * 31)).isoformat()
    hist = [x for x in movimientos if x.get("fecha") and desde <= x["fecha"] < corte]
    if not hist:
        return {}, 0

    f0 = datetime.date.fromisoformat(min(x["fecha"] for x in hist))
    f1 = datetime.date.fromisoformat(max(x["fecha"] for x in hist))
    n_habiles = max(1, len(_habiles(f0, f1)))

    por = defaultdict(list)
    for x in hist:
        por[clave(x, nivel)].append(x)

    perfiles = {}
    for k, movs in por.items():
        dias_con = set(x["fecha"] for x in movs)
        cobertura = len(dias_con) / float(n_habiles)
        total = sum(float(x.get("importe") or 0) for x in movs)
        meses = set(x["fecha"][:7] for x in movs)

        if cobertura >= UMBRAL_DIFUSO:
            perfiles[k] = {
                "clave": k, "perfil": "difuso",
                "concepto": movs[0].get("concepto", ""),
                "por_dia_habil": total / n_habiles,
                "cobertura": cobertura, "n": len(movs), "meses": len(meses),
            }
        else:
            # Un evento se proyecta SIEMPRE por su total mensual, repartido entre
            # los dias en que suele caer.
            #
            # La version anterior se quedaba solo con los dias que se repetian en
            # dos o mas meses, y descartaba el resto. Resultado: los pagos grandes
            # de dia variable (droguerias, retiros) desaparecian de la proyeccion
            # y el total quedaba ~55% por debajo del real, SIEMPRE para el mismo
            # lado. Subestimar lo que vas a gastar es el peor error posible: te
            # deja tranquilo justo cuando no tenes que estarlo.
            #
            # Ahora el dia puede estar mal, pero la PLATA DEL MES esta.
            por_dia = defaultdict(float)
            for x in movs:
                por_dia[int(x["fecha"][8:10])] += abs(float(x.get("importe") or 0))
            suma = sum(por_dia.values())
            if suma > 0:
                peso = dict((d, v / suma) for d, v in por_dia.items())
            else:
                peso = {15: 1.0}
            por_mes = total / max(1, len(meses))
            perfiles[k] = {
                "clave": k, "perfil": "evento",
                "concepto": movs[0].get("concepto", ""),
                "peso": peso,                       # que fraccion del mes cae cada dia
                "dias": dict((d, por_mes * w) for d, w in peso.items()),
                "cobertura": cobertura, "n": len(movs),
                "meses": len(meses), "por_mes": por_mes,
            }
    return perfiles, n_habiles


def proyectar_horizonte(perfiles, desde, dias=45):
    """Lista de {fecha, clave, importe, perfil} para los proximos N dias."""
    hasta = desde + datetime.timedelta(days=dias - 1)
    habiles = _habiles(desde, hasta)
    out = []
    for p in perfiles.values():
        if p["perfil"] == "difuso":
            for f in habiles:
                out.append({"fecha": f.isoformat(), "clave": p["clave"],
                            "importe": p["por_dia_habil"], "perfil": "difuso"})
        else:
            # Los eventos se recorren por dia CALENDARIO, no por habil: si el 10
            # cae sabado, el pago no desaparece, se corre.
            #
            # BUG QUE ENCONTRARON LOS TESTS: antes se iteraba sobre los habiles y
            # se preguntaba por f.day, asi que un evento que caia fin de semana
            # se perdia entero. Con un alquiler es una fecha; con un pago a
            # drogueria son millones que faltan en la curva -- y siempre para el
            # lado de proyectar de menos.
            f = desde
            while f <= hasta:
                imp = p["dias"].get(f.day)
                if imp:
                    # Se corre al habil ANTERIOR: suponer que la plata sale antes
                    # es el lado seguro del error.
                    g = f
                    while g.weekday() >= 5:
                        g -= datetime.timedelta(days=1)
                    if g < desde:
                        g = habiles[0] if habiles else f
                    out.append({"fecha": g.isoformat(), "clave": p["clave"],
                                "importe": imp, "perfil": "evento"})
                f += datetime.timedelta(days=1)
    return sorted(out, key=lambda x: x["fecha"])


def backtest_horizonte(movimientos, corte, dias=45, nivel="tipo"):
    """Proyecta N dias desde 'corte' y compara con lo que realmente paso.

    La medida que importa NO es acertar cada movimiento, es que la CURVA
    ACUMULADA se parezca: un pago que se corre un dia no cambia una decision,
    una curva desviada 40% si.
    """
    perfiles, _ = perfilar(movimientos, corte, nivel=nivel)
    proy = proyectar_horizonte(perfiles, corte, dias)
    hasta = corte + datetime.timedelta(days=dias - 1)
    reales = [x for x in movimientos if x.get("fecha")
              and corte.isoformat() <= x["fecha"] <= hasta.isoformat()]

    def acumular(items):
        por_dia = defaultdict(float)
        for x in items:
            por_dia[x["fecha"]] += abs(float(x.get("importe") or 0))
        acum, curva, f = 0.0, [], corte
        while f <= hasta:
            acum += por_dia.get(f.isoformat(), 0.0)
            curva.append((f.isoformat(), acum))
            f += datetime.timedelta(days=1)
        return curva

    cp, cr = acumular(proy), acumular(reales)
    tp = cp[-1][1] if cp else 0.0
    tr = cr[-1][1] if cr else 0.0

    # El desvio se mide contra el TOTAL del tramo, no contra el acumulado de ese
    # dia. Si se midiera contra el acumulado, el dia 1 (que arranca casi en cero)
    # daria 300% por una diferencia de centavos y la metrica no diria nada.
    peor, peor_dia = 0.0, None
    base = tr if tr else 1.0
    for (f, vp), (_, vr) in zip(cp, cr):
        e = abs(vp - vr) / base * 100.0
        if e > peor:
            peor, peor_dia = e, f

    return {"corte": corte.isoformat(), "dias": dias, "hasta": hasta.isoformat(),
            "perfiles": perfiles, "n_proy": len(proy), "n_real": len(reales),
            "total_proy": tp, "total_real": tr,
            "err_total": (abs(tp - tr) / tr * 100.0) if tr else 0.0,
            "peor_desvio": peor, "peor_dia": peor_dia,
            "curva_proy": cp, "curva_real": cr}


def imprimir_horizonte(r):
    L = 76
    print("=" * L)
    print("  PROYECCION A %d DIAS  .  %s al %s" % (r["dias"], r["corte"], r["hasta"]))
    print("=" * L)
    dif = [p for p in r["perfiles"].values() if p["perfil"] == "difuso"]
    eve = [p for p in r["perfiles"].values() if p["perfil"] == "evento"]
    print("  Aprendio: %d grupos DIFUSOS (pasan casi todos los dias) + %d EVENTOS"
          % (len(dif), len(eve)))
    if dif:
        print("    difusos: %s" % ", ".join(sorted(p["clave"] for p in dif)))
    print("")
    print("  TOTAL DE EGRESOS DEL TRAMO")
    print("    Proyectado : %s" % _m(r["total_proy"]))
    print("    Real       : %s" % _m(r["total_real"]))
    print("    Error      : %.0f%%" % r["err_total"])
    print("")
    print("  CURVA ACUMULADA (es lo que se usa para decidir)")
    print("    Peor desvio (sobre el total del tramo): %.0f%%%s" % (
        r["peor_desvio"], ("  el %s" % r["peor_dia"]) if r["peor_dia"] else ""))
    print("")
    print("  %-12s %18s %18s %8s" % ("FECHA", "PROYECTADO", "REAL", "DESVIO"))
    paso = max(1, len(r["curva_proy"]) // 9)
    for i in range(0, len(r["curva_proy"]), paso):
        f, vp = r["curva_proy"][i]
        vr = r["curva_real"][i][1]
        e = ("%+.0f%%" % ((vp - vr) / vr * 100.0)) if vr else "-"
        print("  %-12s %18s %18s %8s" % (f, _m(vp), _m(vr), e))


def main():
    ap = argparse.ArgumentParser(description="Proyeccion del mes deducida del historial")
    ap.add_argument("--contrato", required=True)
    ap.add_argument("--mes", help="mes a proyectar (aaaa-mm)")
    ap.add_argument("--backtest", help="mes YA pasado, para medir cuanto acierta")
    ap.add_argument("--horizonte", type=int, help="proyectar N dias (ej: --horizonte 45)")
    ap.add_argument("--desde", help="fecha de corte del horizonte (aaaa-mm-dd)")
    ap.add_argument("--nivel", choices=["tipo", "concepto"], default="tipo",
                    help="a que nivel buscar la repeticion (default: tipo)")
    ap.add_argument("--minimo", type=int, default=2,
                    help="en cuantos meses tiene que haber aparecido (default 2)")
    args = ap.parse_args()

    with io.open(args.contrato, encoding="utf-8") as f:
        movs = json.load(f).get("movimientos", [])

    if args.horizonte:
        corte = (datetime.date.fromisoformat(args.desde) if args.desde
                 else datetime.date.today())
        imprimir_horizonte(backtest_horizonte(movs, corte, args.horizonte, args.nivel))
        return

    if args.backtest:
        imprimir_backtest(backtest(movs, args.backtest, args.minimo, args.nivel))
        return
    mes = args.mes or _sig_mes(max(mes_de(x["fecha"]) for x in movs if x.get("fecha")))
    patrones, _ = aprender(movs, mes, nivel=args.nivel)
    imprimir_proyeccion(proyectar(patrones, mes, args.minimo), mes)


if __name__ == "__main__":
    main()
