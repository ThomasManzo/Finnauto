# -*- coding: utf-8 -*-
"""
simulador.disponibilidad — el puente de la caja de hoy a lo que se puede sacar.

QUÉ ES EL PUENTE
----------------
Una sola cuenta, la que todos entienden:

    caja de hoy  +  lo que entra  -  lo que sale  =  con cuánto quedás

El cliente ya la tiene armada en su "Calculadora de disponibilidad". Este módulo
la hace de nuevo — **no la copia**.

POR QUÉ NO LA COPIA
-------------------
Thomas fue explícito sobre el rol de cada cosa:

    "Tené en cuenta que la Calculadora en este nuevo software no va a ser el
     faro. El faro lo va a ser el simulador, el dash y demás."

O sea que la Calculadora es el **punto de control**, no el modelo a reproducir.
Sirve para saber que no nos fuimos a cualquier lado; no para heredar sus
limitaciones. Y tiene cuatro que se arreglan acá:

1. **El horizonte de 45 días no existe.** `HORIZONTE_DIAS: 45` aparece una sola
   vez en toda la Calculadora: en el texto del subtítulo. No filtra nada. Suma
   todas las columnas futuras de la planilla, que hoy llegan al 31/10 — 56 días.
   Acá el horizonte es un parámetro y se aplica de verdad.

2. **Las notas de crédito se cuentan como cobro y no bajan la deuda.** Thomas:
   "las notas de crédito, compensaciones y demás bajan deuda, no tocan caja".
   La Calculadora hace lo contrario: las suma a los cobros y deja la deuda
   entera. Son $915M contados dos veces al revés.

3. **Los cheques en cartera se cuentan como caja.** Pero sobre los datos reales
   el 45% de esa plata se endosa y nunca pasa por el banco. Acá van aparte,
   marcados como lo que son: una opción, no un ingreso.

4. **Lo vencido se mezcla con lo que viene.** Un cobro que venció y no entró no
   vale lo mismo que uno que vence el martes. Acá se separan.

CÓMO SE LEE
-----------
Cada línea dice si es CAJA SEGURA o no. La cuenta se cierra dos veces: una
contando solo lo seguro y otra contando todo. La diferencia entre las dos es el
tamaño de la apuesta que estás haciendo.

Uso:
    python simulador/disponibilidad.py --contrato c.json
    python simulador/disponibilidad.py --contrato c.json --dias 30 --minima 200000000
"""

import io
import os
import sys
import json
import argparse
import datetime
from collections import defaultdict

BASE_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)

from simulador.semana import _m


def hoy_de(contrato):
    """La fecha DEL EXPORT, no la del reloj.

    Un contrato exportado ayer, mirado hoy, correría la línea entre vencido y
    por vencer y haría aparecer diferencias que no existen. Y deja el resultado
    reproducible: el mismo archivo da siempre lo mismo.
    """
    g = str(contrato.get("generado") or "")
    return g[:10] if len(g) >= 10 else datetime.date.today().isoformat()


def _en_ventana(fecha, hoy, hasta):
    return bool(fecha) and hoy <= fecha <= hasta


def _es_refi(x):
    return "REFINANC" in str(x.get("contraparte") or "").upper()


# ------------------------------------------------------------------ entradas
def cobros(contrato, hoy, hasta, unidad=None):
    """Lo que entra, separado por si es caja segura o no.

    Devuelve (lineas, vencido_sin_cobrar), donde cada línea es
    (nombre, monto, es_caja_segura).
    """
    seguro, cartera = defaultdict(float), 0.0

    for x in contrato.get("cobros_previstos", []):
        if x.get("interno"):
            continue                       # mueve plata de lugar, no la crea
        if unidad and (x.get("unidad") or "") != unidad:
            continue
        if not _en_ventana(x.get("fecha"), hoy, hasta):
            continue
        imp = float(x.get("importe") or 0)
        con = (x.get("concepto") or "?").strip()

        # LA CARTERA DE CHEQUES NO ES UN INGRESO: ES UNA OPCIÓN.
        #
        # Thomas: "una vez que llega la fecha de cobro se toma la decisión de
        # endosar o depositar". Sobre sus datos, el 45% de la cartera se endosa
        # y nunca pasa por el banco. Contarla como caja infla el puente justo en
        # la línea que se usa para decidir un retiro.
        if "CARTERA" in con.upper():
            cartera += imp
            continue
        seguro[con] += imp

    # Cobranza a droguerías: lo que nos deben ellas a nosotros.
    #
    # OJO CON EL SENTIDO: MAGA le COMPRA a las droguerías; Speedmed les compra y
    # les vende. Esta línea es solo de Speed, y confundirla con la deuda fue uno
    # de los errores más caros del proyecto.
    drog_futuro, drog_vencido = 0.0, 0.0
    for x in contrato.get("cuentas_a_cobrar_droguerias", []):
        if x.get("intercompany"):
            continue
        if unidad and (x.get("unidad") or "") != unidad:
            continue
        f = x.get("fecha") or ""
        imp = float(x.get("importe") or 0)
        if _en_ventana(f, hoy, hasta):
            drog_futuro += imp
        elif f and f < hoy:
            drog_vencido += imp

    lineas = [(k, v, True) for k, v in sorted(seguro.items(), key=lambda kv: -kv[1])]
    if drog_futuro:
        lineas.append(("Cobranza a droguerias", drog_futuro, True))
    if cartera:
        lineas.append(("Cheques en cartera", cartera, False))
    return lineas, drog_vencido


# ------------------------------------------------------------------ salidas
def pagos(contrato, hoy, hasta, unidad=None,
          con_droguerias=True, con_intercompany=False):
    """Lo que sale, separado por si se puede mover o no.

    Cada línea es (nombre, monto, se_puede_patear).

    LOS DOS INTERRUPTORES SON LOS ESCENARIOS DE THOMAS.

    Su Posición Consolidada compara tres mundos (ver docs/NEGOCIO.md §8):

      1. sin pagarle a las droguerías   -> con_droguerias=False
      2. pagándoles                      -> con_droguerias=True
      3. y además MAGA pagándole a Speed -> con_intercompany=True

    El tercero no es una curiosidad contable: es el que muestra **qué tan
    rentable es una empresa del grupo sin la otra**, que es la pregunta de
    fondo cuando MAGA sola no cierra.
    """
    deuda_venc, deuda_fut, ncr = 0.0, 0.0, 0.0
    refi_venc, refi_fut = 0.0, 0.0

    inter = 0.0
    for x in contrato.get("deuda_droguerias", []):
        if unidad and (x.get("unidad") or "") != unidad:
            continue
        f = x.get("fecha") or ""
        if not f:
            continue
        imp = float(x.get("importe") or 0)

        if x.get("intercompany"):
            # Plata que se mueve DENTRO del grupo: no sale para afuera. Solo
            # cuenta en el escenario 3, y ahí lo que hace es correr posición de
            # una empresa a la otra sin cambiar el total del grupo.
            if con_intercompany and f <= hasta:
                inter += imp
            continue

        if _es_refi(x):
            # Se puede patear, pero es una obligación, y no es una droguería:
            # no tiene tolerancia de proveedor. Va en su propia línea.
            if f < hoy:
                refi_venc += imp
            elif f <= hasta:
                refi_fut += imp
            continue

        # LAS NCR BAJAN DEUDA. No son un cobro.
        #
        # Vienen con importe negativo, así que sumarlas ya netea. Se llevan
        # aparte solo para poder mostrar cuánto es.
        if x.get("es_credito"):
            if f <= hasta:
                ncr += abs(imp)
            continue

        if f < hoy:
            deuda_venc += imp
        elif f <= hasta:
            deuda_fut += imp

    egresos = defaultdict(float)
    for x in contrato.get("egresos_cashflow", []):
        if x.get("intercompany"):
            continue
        if unidad and (x.get("unidad") or "") != unidad:
            continue
        if not _en_ventana(x.get("fecha"), hoy, hasta):
            continue
        egresos[(x.get("contraparte") or "?").strip()] += float(x.get("importe") or 0)

    # Lo vencido primero: es lo que aprieta.
    if not con_droguerias:
        # Escenario 1: "si no les pago". Thomas lo usaba cuando el negocio
        # estaba peor, para ver si al menos se cubrían los cheques de la
        # semana. La deuda no desaparece -- se patea, y eso se dice.
        deuda_venc = deuda_fut = ncr = 0.0

    lineas = []
    if inter:
        lineas.append(("Pago a la otra empresa del grupo", inter, True))
    if deuda_venc:
        lineas.append(("Deuda droguerias YA VENCIDA", deuda_venc, True))
    if deuda_fut:
        lineas.append(("Deuda droguerias por vencer", deuda_fut, True))
    if ncr:
        lineas.append(("  - notas de credito (bajan deuda)", -ncr, False))
    if refi_venc or refi_fut:
        lineas.append(("Refinanciacion", refi_venc + refi_fut, True))
    for k, v in sorted(egresos.items(), key=lambda kv: -kv[1]):
        lineas.append((k, v, False))
    return lineas


# ------------------------------------------------------------------ el puente
def puente(contrato, dias=45, unidad=None, minima=0.0, hoy=None,
           con_droguerias=True, con_intercompany=False):
    hoy = hoy or hoy_de(contrato)
    hasta = (datetime.date(*map(int, hoy.split("-")))
             + datetime.timedelta(days=dias)).isoformat()

    caja = float(contrato.get("caja_hoy") or 0)
    sin_efectivo = 0.0
    if unidad:
        # La caja por unidad es SOLO BANCOS: el efectivo de la grilla de SALDOS
        # es un total del grupo y no dice de que empresa es. Se avisa en vez de
        # repartirlo con un criterio inventado.
        caja = float((contrato.get("caja_por_unidad") or {}).get(unidad) or 0)
        sin_efectivo = float(contrato.get("caja_efectivo") or 0)

    lin_c, drog_vencido = cobros(contrato, hoy, hasta, unidad)
    lin_p = pagos(contrato, hoy, hasta, unidad,
                  con_droguerias, con_intercompany)

    entra_seguro = sum(v for _, v, ok in lin_c if ok)
    entra_todo = sum(v for _, v, _ in lin_c)
    sale = sum(v for _, v, _ in lin_p)

    return {
        "hoy": hoy, "hasta": hasta, "dias": dias, "unidad": unidad,
        "caja": caja, "cobros": lin_c, "pagos": lin_p,
        "efectivo_sin_asignar": sin_efectivo,
        "entra_seguro": entra_seguro, "entra_todo": entra_todo, "sale": sale,
        "cobranza_vencida": drog_vencido,
        "con_droguerias": con_droguerias, "con_intercompany": con_intercompany,
        "proyectada_seguro": caja + entra_seguro - sale,
        "proyectada_todo": caja + entra_todo - sale,
        "minima": minima,
        "distribuible": max(0.0, caja + entra_seguro - sale - minima),
    }


# ------------------------------------------------------------------ salida
def imprimir(p):
    L = 74
    print("=" * L)
    print("  DE LA CAJA DE HOY A LO QUE PODES SACAR")
    print("  %s dias: %s -> %s%s" % (p["dias"], p["hoy"], p["hasta"],
                                     ("  ·  " + p["unidad"]) if p["unidad"] else ""))
    print("=" * L)
    print("  %-46s %22s" % (
        "Caja de hoy (banco)" if p["unidad"] else "Caja de hoy (banco + efectivo)",
        _m(p["caja"])))
    if p.get("efectivo_sin_asignar"):
        print("     (aparte hay %s de efectivo del grupo, sin unidad asignada)"
              % _m(p["efectivo_sin_asignar"]))

    print("\n  ENTRA")
    for nom, v, seguro in p["cobros"]:
        print("     %-40s %22s%s" % (nom[:40], _m(v), "" if seguro else "   (*)"))
    print("     %-40s %22s" % ("suma de lo seguro", _m(p["entra_seguro"])))

    print("\n  SALE")
    for nom, v, pateable in p["pagos"]:
        print("     %-40s %22s%s" % (nom[:40], _m(v), "   (se puede patear)" if pateable else ""))
    print("     %-40s %22s" % ("total", _m(p["sale"])))

    print("\n  " + "-" * (L - 4))
    print("  %-46s %22s" % ("Caja proyectada (solo con lo seguro)",
                            _m(p["proyectada_seguro"])))
    print("  %-46s %22s" % ("Caja proyectada (contando los cheques)",
                            _m(p["proyectada_todo"])))
    if p["minima"]:
        print("  %-46s %22s" % ("- caja minima", _m(-p["minima"])))
        print("  %-46s %22s" % ("DISTRIBUIBLE", _m(p["distribuible"])))

    # (*) LO QUE NO ES CAJA SEGURA.
    # Se explica siempre, no solo cuando molesta: la diferencia entre las dos
    # proyecciones es el tamaño de la apuesta.
    dudoso = p["entra_todo"] - p["entra_seguro"]
    if dudoso:
        print("\n  (*) %s de cheques en cartera. No son caja hasta que se" % _m(dudoso))
        print("      decida depositarlos: al llegar la fecha se elige entre")
        print("      depositar (entra plata) o endosar (baja deuda, no entra).")
        print("      Esa diferencia es la apuesta que estas haciendo.")
    if p["cobranza_vencida"]:
        print("\n  OJO: hay %s de cobranza a droguerias que YA VENCIO y no" % _m(p["cobranza_vencida"]))
        print("      entro. No esta contada arriba. Si una parte entra, el")
        print("      panorama mejora; contarla como segura seria mentirse.")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="El puente de la caja")
    ap.add_argument("--contrato", required=True)
    ap.add_argument("--dias", type=int, default=45)
    ap.add_argument("--unidad")
    ap.add_argument("--minima", type=float, default=0.0)
    args = ap.parse_args()
    with io.open(args.contrato, encoding="utf-8") as f:
        contrato = json.load(f)
    imprimir(puente(contrato, args.dias, args.unidad, args.minima))


if __name__ == "__main__":
    main()
