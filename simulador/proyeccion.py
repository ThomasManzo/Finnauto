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

    # Cuantos meses de historia hay DE VERDAD. Dos correcciones en una:
    #
    #  . contar "meses distintos que aparecen" inflaba el divisor cuando la
    #    historia empieza o termina a mitad de mes (del 1/6 al 14/7 son dos
    #    meses distintos pero mes y medio de datos), y la proyeccion salia
    #    ~25% corta, siempre para el mismo lado;
    #  . medir el span de CADA GRUPO lo inflaba al reves: algo que aparecio dos
    #    veces con 3 dias de diferencia quedaba como si gastara eso cada medio
    #    mes. Un gasto que se vio una sola vez en 3 meses NO es mensual.
    #
    # El divisor correcto es el mismo para todos: los meses observados.
    span_meses = max(0.5, ((f1 - f0).days + 1) / 30.44)

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
            # Se divide por los MESES REALES de historia, no por la cantidad de
            # meses distintos que aparecen.
            #
            # BUG: si la historia va del 1/6 al 14/7, aparecen dos meses (junio y
            # julio) pero solo hay mes y medio. Dividir por 2 hacia que el ritmo
            # mensual saliera ~25% mas bajo, y la proyeccion quedaba corta SIEMPRE
            # para el mismo lado. Lo delato un cliente nuevo cuya historia
            # arrancaba a mitad de mes.
            por_mes = total / span_meses
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


# ============================================================== caja completa
# Hasta aca todo proyectaba EGRESOS. Pero la pregunta que importa no es "cuanto
# voy a gastar": es "¿me alcanza?", y eso es lo que entra menos lo que sale.
#
# Medido sobre los datos reales de MAGA, 5 tramos de 45 dias:
#     ingresos solos   5% de error mediano
#     egresos solos   27%
#     NETO             4%   (rango 1% a 46%)
#
# Los ingresos se proyectan mucho mejor porque son regulares (venta diaria,
# tarjetas), mientras que los egresos son grumosos: un pago de $362M a una
# drogueria en un dia variable mueve toda la curva.
#
# El motor es el MISMO: no sabe si lo que le dan entra o sale. Lo unico que
# cambia es el signo con que se acumula.


def _como_movimientos(cobros):
    """Los cobros del contrato, con la forma que espera el motor.

    El motor agrupa por 'tipo' y los cobros traen 'concepto': se mapea y listo.
    No hay nada especial en un ingreso -- es un movimiento con otro signo.
    """
    return [{"fecha": x["fecha"], "tipo": (x.get("concepto") or "?"),
             "concepto": x.get("concepto", ""),
             "importe": float(x.get("importe") or 0)}
            for x in (cobros or []) if x.get("fecha")]


def proyectar_caja(contrato, desde, dias=45, caja_inicial=None, nivel="tipo"):
    """Curva de caja dia por dia: lo que entra menos lo que sale."""
    egr = [x for x in contrato.get("movimientos", []) if x.get("fecha")]
    ing = _como_movimientos(contrato.get("cobros_previstos"))

    pe, _ = perfilar(egr, desde, nivel=nivel)
    pi, _ = perfilar(ing, desde, nivel=nivel)
    proy_e = proyectar_horizonte(pe, desde, dias)
    proy_i = proyectar_horizonte(pi, desde, dias)

    hasta = desde + datetime.timedelta(days=dias - 1)
    por_dia = defaultdict(float)
    for x in proy_i:
        por_dia[x["fecha"]] += abs(x["importe"])
    for x in proy_e:
        por_dia[x["fecha"]] -= abs(x["importe"])

    caja = caja_inicial
    if caja is None:
        caja = float(contrato.get("caja_hoy") or 0)

    curva, f, acum = [], desde, caja
    while f <= hasta:
        acum += por_dia.get(f.isoformat(), 0.0)
        curva.append({"fecha": f.isoformat(), "caja": acum,
                      "movimiento": por_dia.get(f.isoformat(), 0.0)})
        f += datetime.timedelta(days=1)

    return {"desde": desde.isoformat(), "hasta": hasta.isoformat(),
            "caja_inicial": caja, "curva": curva,
            "total_ingresos": sum(abs(x["importe"]) for x in proy_i),
            "total_egresos": sum(abs(x["importe"]) for x in proy_e),
            "perfiles_ingresos": pi, "perfiles_egresos": pe}


def revisar_coherencia(contrato, meses=3):
    """¿Los dos lados del contrato son comparables?

    APARECIO CON DATOS REALES. En el contrato de MAGA, agosto da:
        entra  $7.032M
        sale   $2.707M
        neto  +$4.326M por mes
    pero la caja es de $1.183M y no se mueve. O sea que la empresa NO gana
    $4.326M por mes: hay egresos que no estan registrados como movimientos.
    En este caso son las compras a droguerias, que en esa planilla viven en un
    bloque aparte.

    Sin este chequeo, la curva de caja da un dibujo precioso que sube y sube, y
    es exactamente el error mas caro posible: decirle a alguien que le sobra
    plata cuando no le sobra.

    No se puede corregir solo. Lo que si se puede es DETECTARLO y preguntar, que
    es lo mismo que hace el lector con las columnas que no entiende.
    """
    egr = [x for x in contrato.get("movimientos", []) if x.get("fecha")]
    ing = _como_movimientos(contrato.get("cobros_previstos"))
    if not egr or not ing:
        return None

    tope = max(x["fecha"] for x in egr + ing)
    piso = (datetime.date.fromisoformat(tope) -
            datetime.timedelta(days=int(meses * 30.44))).isoformat()

    def suma(xs):
        return sum(abs(float(x.get("importe") or 0)) for x in xs if x["fecha"] >= piso)

    ti, te = suma(ing), suma(egr)
    if not ti or not te:
        return None

    neto_mes = (ti - te) / float(meses)
    caja = float(contrato.get("caja_hoy") or 0)

    avisos = []
    # Si el neto mensual es una fraccion grande de la caja y la caja no crece a
    # ese ritmo, es que falta registrar movimientos de un lado.
    if caja and neto_mes > caja * 0.5:
        avisos.append(
            "El contrato dice que entran %s por mes mas de lo que sale, pero la "
            "caja es de %s. Si eso fuera cierto, la caja se multiplicaria en "
            "pocos meses. Lo mas probable es que FALTEN EGRESOS sin registrar "
            "(en una farmacia, tipicamente las compras a droguerias)."
            % (_m(neto_mes), _m(caja)))
    if te and ti / te > 2.0:
        avisos.append(
            "Entra %.1f veces lo que sale. Preguntarle al cliente que gastos no "
            "estan en esta planilla." % (ti / te))
    if ti and te / ti > 2.0:
        avisos.append(
            "Sale %.1f veces lo que entra. O falta registrar ingresos, o la "
            "empresa se esta financiando con algo que no figura aca." % (te / ti))

    return {"ingresos": ti, "egresos": te, "meses": meses,
            "neto_mes": neto_mes, "caja": caja, "avisos": avisos}


def imprimir_caja(r, minimo=0.0, coherencia=None):
    L = 76
    print("=" * L)
    print("  CAJA PROYECTADA  .  %s al %s" % (r["desde"], r["hasta"]))
    print("=" * L)
    print("  Caja inicial : %s" % _m(r["caja_inicial"]))
    print("  Entra        : %s" % _m(r["total_ingresos"]))
    print("  Sale         : %s" % _m(r["total_egresos"]))
    neto = r["total_ingresos"] - r["total_egresos"]
    print("  Neto         : %s" % _m(neto))
    print("  Caja al final: %s" % _m(r["curva"][-1]["caja"] if r["curva"] else 0))

    bajo = [d for d in r["curva"] if d["caja"] < minimo] if minimo else []
    print("")
    if minimo:
        if bajo:
            peor = min(bajo, key=lambda d: d["caja"])
            print("  [!] LA CAJA CAE POR DEBAJO DE %s" % _m(minimo))
            print("      Primer dia: %s  (%s)" % (bajo[0]["fecha"], _m(bajo[0]["caja"])))
            print("      Peor dia  : %s  (%s)" % (peor["fecha"], _m(peor["caja"])))
            print("      Dias en rojo: %d de %d" % (len(bajo), len(r["curva"])))
        else:
            print("  [OK] La caja no baja del minimo en todo el tramo.")

    print("")
    print("  %-12s %18s %18s" % ("FECHA", "MOVIMIENTO DEL DIA", "CAJA"))
    paso = max(1, len(r["curva"]) // 12)
    for i in range(0, len(r["curva"]), paso):
        d = r["curva"][i]
        marca = "  <-- bajo el minimo" if minimo and d["caja"] < minimo else ""
        print("  %-12s %18s %18s%s" % (d["fecha"], _m(d["movimiento"]),
                                       _m(d["caja"]), marca))
    if coherencia and coherencia["avisos"]:
        print("")
        print("  " + "!" * (L - 4))
        print("  ANTES DE CREERLE A ESTA CURVA")
        print("  " + "!" * (L - 4))
        print("  En los ultimos %d meses el contrato registra:" % coherencia["meses"])
        print("     entra %s" % _m(coherencia["ingresos"]))
        print("     sale  %s" % _m(coherencia["egresos"]))
        for a in coherencia["avisos"]:
            linea = "  . "
            for palabra in a.split():
                if len(linea) + len(palabra) + 1 > L - 2:
                    print(linea)
                    linea = "    "
                linea += palabra + " "
            print(linea.rstrip())
        print("")
        print("  Mientras falte ese lado, la curva de arriba esta INCOMPLETA y")
        print("  peca de optimista. Es el error mas caro posible.")

    print("")
    print("  OJO: esto sale del historial, no de una carga manual. Medido sobre")
    print("  datos reales el neto erra 4% tipico, pero llego a 46% en el tramo")
    print("  con menos historia. Sirve para ver la FORMA y el dia critico.")


def main():
    ap = argparse.ArgumentParser(description="Proyeccion del mes deducida del historial")
    ap.add_argument("--contrato", required=True)
    ap.add_argument("--mes", help="mes a proyectar (aaaa-mm)")
    ap.add_argument("--backtest", help="mes YA pasado, para medir cuanto acierta")
    ap.add_argument("--horizonte", type=int, help="proyectar N dias (ej: --horizonte 45)")
    ap.add_argument("--desde", help="fecha de corte del horizonte (aaaa-mm-dd)")
    ap.add_argument("--caja", type=float,
                    help="proyectar la CAJA (entra menos sale) desde N dias, "
                         "partiendo del saldo que se indique")
    ap.add_argument("--caja-minima", type=float, default=0, dest="caja_minima",
                    help="caja minima de seguridad, para marcar los dias en rojo")
    ap.add_argument("--nivel", choices=["tipo", "concepto"], default="tipo",
                    help="a que nivel buscar la repeticion (default: tipo)")
    ap.add_argument("--minimo", type=int, default=2,
                    help="en cuantos meses tiene que haber aparecido (default 2)")
    args = ap.parse_args()

    with io.open(args.contrato, encoding="utf-8") as f:
        movs = json.load(f).get("movimientos", [])

    if args.caja is not None:
        with io.open(args.contrato, encoding="utf-8") as f:
            c = json.load(f)
        corte = (datetime.date.fromisoformat(args.desde) if args.desde
                 else datetime.date.today())
        dias = args.horizonte or 45
        imprimir_caja(proyectar_caja(c, corte, dias, args.caja, args.nivel),
                      args.caja_minima, revisar_coherencia(c))
        return

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
