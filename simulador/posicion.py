# -*- coding: utf-8 -*-
"""
simulador.posicion — la posición de cada empresa, según a quién le pagues.

QUÉ CONTESTA
------------
No "¿cuánta plata tengo?" sino **"¿cómo queda cada empresa del grupo según a
quién le pague?"**. Thomas mira tres mundos:

    1. sin pagarle a las droguerías
    2. pagándoles
    3. pagándoles Y con MAGA pagándole a Speedmed

**Acá se calculan el 1 y el 2. El 3 falta, y el módulo dice por qué**: la deuda
de MAGA con Speedmed no está cargada en la planilla de MAGA, así que el
escenario daría un número falso. Está explicado abajo, donde estaría el código.

La diferencia entre el 1 y el 2 es lo importante: **cuánto te está financiando
la droguería**. Es la línea de crédito real del negocio, porque las bancarias
están agotadas.

POR QUÉ NO ALCANZA CON LA SOLAPA QUE YA EXISTE
----------------------------------------------
La "Posición Consolidada" del cliente hace esta misma comparación, pero apunta a
celdas fijas: `'Cash Flow Diario-Speed'!B50` y `'Cash Flow Diario -MAGA'!B51`.

**La columna B de esos cashflow es el 1 de abril de 2026.** No es la de hoy: es
la primera del año. Por eso los dos escenarios dan el mismo número al peso
($333.568.133 y $308.212.367 en los dos) — a esa altura todavía no se habían
separado.

Acá la posición se calcula a la fecha del export y con un horizonte de verdad.

CÓMO SE LEE
-----------
Los niveles importan menos que los saltos. Un saldo negativo en los dos
escenarios no dice nada nuevo; lo que dice algo es cuánto cambia de uno a otro.

Uso:
    python simulador/posicion.py --contrato c.json
    python simulador/posicion.py --contrato c.json --dias 30
"""

import io
import os
import sys
import json
import argparse

BASE_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)

from simulador.semana import _m
from simulador import disponibilidad as D


# EL DEL MEDIO ES EL QUE SE USA. Los otros dos son los bordes.
#
# Cuando le mostre solo los dos extremos, Thomas corrigio (06/09/2026):
#
#     "El escenario 1 es el incorrecto, claramente no esta teniendo en cuenta
#      deuda a vencer."
#
# Tenia razon: "no pagar nada" da un numero enorme y positivo que no significa
# nada, porque la deuda no desaparecio -- se pateo. Mostrarlo al lado de "pagar
# todo" hace parecer que la eleccion es entre esos dos, y no es.
#
# La decision real es la del medio: cubrir lo VENCIDO y dejar correr lo que
# todavia no vencio. Por eso va marcada.
ESCENARIOS = [
    ("1. sin pagarles nada", dict(con_droguerias="nada"),
     "El borde de abajo. La deuda no desaparece: se patea y el atraso se "
     "acumula. Sirve para ver si al menos se cubren los cheques."),
    ("2. pagando lo VENCIDO  <<", dict(con_droguerias="vencido"),
     "LO QUE SE HACE DE VERDAD: se cubre lo que ya vencio -- que es lo que "
     "puede hacer que te corten la compra -- y lo que todavia no vencio se "
     "deja correr."),
    ("3. pagando todo en fecha", dict(con_droguerias="todo"),
     "El borde de arriba. Como quedarias sin atrasarte un dia con nadie."),
]

# EL ESCENARIO 3 NO ESTA, Y NO ES UN OLVIDO.
#
# Thomas lo describe como "con pago a droguerias Y MAGA pagandole a Speedmed:
# que pasaria si Speedmed fuera un proveedor rigido mas".
#
# Se calculo, dio un numero, y el numero era falso. Lo delato un chequeo propio:
# el TOTAL DEL GRUPO cambiaba entre el escenario 2 y el 3. Un pago entre dos
# empresas del mismo grupo no puede cambiar el total -- la plata se mueve de
# bolsillo, no desaparece. Esa sola condicion alcanzo para saber que estaba mal.
#
# La causa: la planilla de MAGA NO tiene una fila de deuda con Speedmed. Lo
# unico intercompany cargado es una fila en la planilla de SPEED. Al estar de un
# solo lado, sumarla descuadra el grupo.
#
# Y es coherente con lo que conto Thomas: "Speed le factura al costo pero SIN
# necesidad de que MAGA pague; MAGA solo transfiere cuando Speed necesita cubrir
# cheques". O sea que esa deuda no existe como obligacion en ningun lado.
#
# Mostrar igual el numero habria sido lo peor de todo: parece un escenario y es
# un error de carga. Se dice que falta, se dice que hace falta para tenerlo, y
# se sigue.


def unidades(contrato):
    """Las empresas del grupo, sacadas del propio contrato.

    No se hardcodean 'MAGA' y 'SPEEDMED': el producto tiene que servir para un
    grupo con otras empresas sin tocar código.
    """
    u = list((contrato.get("caja_por_unidad") or {}).keys())
    if u:
        return sorted(u)
    vistas = set()
    for k in ("deuda_droguerias", "cobros_previstos", "egresos_cashflow"):
        for x in contrato.get(k, []):
            if x.get("unidad"):
                vistas.add(x["unidad"])
    return sorted(vistas)


def calcular(contrato, dias=45):
    us = unidades(contrato)
    filas = []
    for nombre, flags, por_que in ESCENARIOS:
        por_unidad = {}
        for u in us:
            p = D.puente(contrato, dias=dias, unidad=u, **flags)
            por_unidad[u] = p["proyectada_seguro"]
        filas.append({"escenario": nombre, "por_que": por_que,
                      "por_unidad": por_unidad,
                      "total": sum(por_unidad.values())})
    return us, filas


def imprimir(us, filas, dias, hoy):
    L = 30 + 20 * (len(us) + 1)
    print("=" * L)
    print("  POSICION DE CADA EMPRESA, SEGUN A QUIEN LE PAGUES")
    print("  al %s, horizonte %s dias" % (hoy, dias))
    print("=" * L)

    print("  %-30s" % "" + "".join("%20s" % u[:19] for u in us) + "%20s" % "GRUPO")
    print("  " + "-" * (L - 4))
    for f in filas:
        print("  %-30s" % f["escenario"][:30]
              + "".join("%20s" % _m(f["por_unidad"][u]) for u in us)
              + "%20s" % _m(f["total"]))

    # LAS DIFERENCIAS SON LA LECTURA, NO LOS NIVELES.
    # Un saldo negativo en los tres escenarios no dice nada nuevo; lo que dice
    # algo es cuanto cambia entre uno y otro.
    print("\n  QUE SIGNIFICA CADA SALTO")
    if len(filas) >= 3:
        print("     Del 1 al 2: %s" % _m(filas[0]["total"] - filas[1]["total"]))
        print("     Es el atraso que YA tenes acumulado. Esa plata esta en tu")
        print("     caja hoy porque todavia no se la pagaste a la drogueria.")
        print("     Del 2 al 3: %s" % _m(filas[1]["total"] - filas[2]["total"]))
        print("     Es lo que te van a financiar en la ventana, si te seguis")
        print("     atrasando al mismo ritmo.")
        print("     Los dos juntos son tu linea de credito real. No hay otra:")
        print("     las bancarias estan agotadas.")

    print("\n  Esto NO es la caja de hoy: es la caja de hoy MAS lo que entra")
    print("  seguro MENOS lo que sale, en la ventana. Los cheques en cartera")
    print("  quedan afuera, porque no se sabe si se depositan o se endosan.")


def diagnostico_esc3(contrato):
    """Que hay cargado de intercompany, y de que lado."""
    filas = [x for x in contrato.get("deuda_droguerias", []) if x.get("intercompany")]
    por_unidad = {}
    for x in filas:
        por_unidad.setdefault(x.get("unidad") or "?", []).append(x)
    return filas, por_unidad


def imprimir_esc3(contrato):
    filas, por_unidad = diagnostico_esc3(contrato)
    print()
    print("  FALTA UN CUARTO ESCENARIO: \"y MAGA pagandole a Speed\"")
    print("  No se calcula porque el dato no esta, no porque no importe.")
    if not filas:
        print("     No hay ninguna fila intercompany cargada en la deuda.")
    elif len(por_unidad) == 1:
        u = list(por_unidad)[0]
        tot = sum(abs(float(x.get("importe") or 0)) for x in por_unidad[u])
        print("     Lo unico intercompany son %d fila(s), todas en la planilla"
              % len(filas))
        print("     de %s, por %s:" % (u, _m(tot)))
        for x in por_unidad[u][:5]:
            print("        %s  %-20s %s" % (x.get("fecha"),
                  str(x.get("contraparte"))[:20], _m(float(x.get("importe") or 0))))
        print("     Al estar cargado de un solo lado, contarlo hace que el total")
        print("     del grupo cambie. Y un pago entre empresas del mismo grupo")
        print("     no puede cambiar el total: por eso no se muestra.")
    else:
        print("     Hay filas intercompany en %s. Habria que verificar que cada"
              % " y ".join(sorted(por_unidad)))
        print("     una este cargada de los dos lados.")
    print("     PARA TENERLO: cargar en el cashflow de MAGA la deuda con")
    print("     Speedmed, con sus fechas, como cualquier otro proveedor.")

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Posicion por unidad, tres escenarios")
    ap.add_argument("--contrato", required=True)
    ap.add_argument("--dias", type=int, default=45)
    args = ap.parse_args()
    with io.open(args.contrato, encoding="utf-8") as f:
        contrato = json.load(f)
    us, filas = calcular(contrato, args.dias)
    imprimir(us, filas, args.dias, D.hoy_de(contrato))
    imprimir_esc3(contrato)


if __name__ == "__main__":
    main()
