# -*- coding: utf-8 -*-
"""
auditoria.cobertura — que ningún peso del contrato se pierda en el camino.

POR QUÉ EXISTE
--------------
Thomas, 06/09/2026: *"vamos cortando con estos bugs porque estamos complicados,
no puedo ofrecer algo lleno de bugs y si yo no me fijo no sé qué puede pasar"*.

Tiene razón, y la parte importante es la segunda: **si él no lo mira, nadie lo
mira**. Un tablero que se muestra a un dueño no puede depender de que alguien
reconozca de memoria que un número está mal.

MIRANDO LOS BUGS JUNTOS, CASI TODOS SON EL MISMO
------------------------------------------------
    · la cobranza a droguerías no entraba a la proyección (faltaba una punta)
    · las NCR sumaban en vez de restar (signo)
    · la deuda de MAGA no se leía y el export decía OK (bloque no encontrado)
    · la cartera se atribuía a la empresa equivocada
    · los egresos se estimaban ADEMÁS de estar cargados (doble conteo)
    · las FCIAS vencidas quedaban afuera

Ninguno fue un error de aritmética. **Todos fueron plata que estaba en el
contrato y no llegó a la pantalla, o llegó dos veces.** Y ninguno rompió nada:
el tablero salió limpio, con un número mal.

QUÉ HACE ESTE MÓDULO
--------------------
Toma el contrato y el paquete que consume la app, y verifica lo único que tiene
que ser cierto siempre:

    cada peso del contrato, en la ventana, está en EXACTAMENTE UN lugar
    del tablero — o está declarado como excluido, con motivo.

Lo que no cae en ninguno de los dos casos se lista. No adivina si está bien o
mal: dice "esto no lo estás mostrando" y deja que una persona decida.

Es el mismo criterio que el resto del proyecto: el enemigo no es el error, es
el silencio.

Uso:
    python auditoria/cobertura.py --contrato datos/CONTRATO_maga_2026-09-05.json
"""

import io
import os
import sys
import json
import argparse
from collections import defaultdict

BASE_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)

from dashboard import datos as DA


TOLERANCIA = 1.0     # pesos


def _m(v):
    signo = "-" if v < 0 else ""
    return signo + "$" + format(int(round(abs(v))), ",d").replace(",", ".")


# Lo que el tablero deja afuera A PROPÓSITO, con el motivo escrito.
#
# Que esté declarado es la mitad del control: si mañana alguien saca algo del
# tablero sin agregarlo acá, aparece como "no mostrado" y se ve.
EXCLUIDO_A_PROPOSITO = {
    "interno": "movimiento entre empresas del grupo: mueve plata, no la crea",
    "intercompany": "lo mismo, del lado de la deuda",
    "cartera": "un cheque no es caja hasta que se decide depositarlo o endosarlo",
    "fuera_de_ventana": "cae después del horizonte que se está mirando",
    "pasado_ingresos": "fecha pasada en el bloque de ingresos: ya entró",
}


def revisar(contrato, cliente="maga", dias=45):
    hoy = DA.D.hoy_de(contrato)
    unidades = DA.POS.unidades(contrato)
    out = []

    for u in unidades:
        p = DA.proyeccion(contrato, u, hoy, dias)
        hasta = p["hasta"]

        def _mia(x):
            return (x.get("unidad") or "") == u

        # ---------------------------------------------------- lo que ENTRA
        esperado_entra, excluido_entra = 0.0, defaultdict(float)
        for x in contrato.get("cobros_previstos", []):
            if not _mia(x):
                continue
            v = abs(float(x.get("importe") or 0))
            f = x.get("fecha") or ""
            con = str(x.get("concepto") or "").upper()
            if x.get("interno"):
                excluido_entra["interno"] += v
            elif "CARTERA" in con:
                excluido_entra["cartera"] += v
            elif f < hoy:
                excluido_entra["pasado_ingresos"] += v
            elif f > hasta:
                excluido_entra["fuera_de_ventana"] += v
            else:
                esperado_entra += v

        for x in contrato.get("cuentas_a_cobrar_droguerias", []):
            if not _mia(x):
                continue
            v = abs(float(x.get("importe") or 0))
            f = x.get("fecha") or ""
            if x.get("intercompany"):
                excluido_entra["intercompany"] += v
            elif f < hoy:
                # Vencido y sin cobrar: no se da por hecho, pero se informa en
                # la solapa "A cobrar". Se cuenta como declarado, no como
                # perdido.
                excluido_entra["cobranza vencida (se informa aparte)"] += v
            elif f > hasta:
                excluido_entra["fuera_de_ventana"] += v
            else:
                esperado_entra += v

        # ----------------------------------------------------- lo que SALE
        esperado_sale, excluido_sale = 0.0, defaultdict(float)
        for x in contrato.get("egresos_cashflow", []):
            if not _mia(x):
                continue
            v = abs(float(x.get("importe") or 0))
            f = x.get("fecha") or ""
            if x.get("intercompany"):
                excluido_sale["intercompany"] += v
            elif f < hoy or f > hasta:
                excluido_sale["fuera_de_ventana"] += v
            else:
                esperado_sale += v

        for x in contrato.get("deuda_droguerias", []):
            if not _mia(x):
                continue
            v = float(x.get("importe") or 0)
            f = x.get("fecha") or ""
            if x.get("intercompany"):
                excluido_sale["intercompany"] += abs(v)
            elif v <= 0:
                # NCR: baja deuda. No es un egreso.
                excluido_sale["notas de credito (restan deuda)"] += abs(v)
            elif f < hoy or f > hasta:
                excluido_sale["fuera_de_ventana"] += v
            else:
                esperado_sale += v

        out.append({
            "unidad": u,
            "entra": {"esperado": esperado_entra, "mostrado": p["total_entra"],
                      "dif": p["total_entra"] - esperado_entra,
                      "excluido": dict(excluido_entra)},
            "sale": {"esperado": esperado_sale, "mostrado": p["total_sale"],
                     "dif": p["total_sale"] - esperado_sale,
                     "excluido": dict(excluido_sale)},
        })
    return out, hoy


def imprimir(filas, hoy):
    L = 80
    print("=" * L)
    print("  CADA PESO DEL CONTRATO, ¿LLEGA A LA PANTALLA?")
    print("  al %s" % hoy)
    print("=" * L)
    print("  Lo unico que tiene que ser cierto siempre: lo que hay en el contrato")
    print("  dentro de la ventana, o se muestra, o esta declarado como excluido.")

    problemas = 0
    for f in filas:
        print("\n  " + f["unidad"])
        print("  " + "-" * (L - 4))
        for lado in ("entra", "sale"):
            d = f[lado]
            ok = abs(d["dif"]) <= TOLERANCIA
            if not ok:
                problemas += 1
            print("   %-8s contrato %18s   tablero %18s   %s"
                  % (lado.upper(), _m(d["esperado"]), _m(d["mostrado"]),
                     "ok" if ok else "<-- DIFERENCIA " + _m(d["dif"])))
            for k, v in sorted(d["excluido"].items(), key=lambda kv: -kv[1]):
                por = EXCLUIDO_A_PROPOSITO.get(k, k)
                print("        afuera: %-34s %16s" % (por[:34], _m(v)))

    print("\n" + "=" * L)
    if problemas:
        print("  %d DIFERENCIA(S). Algo del contrato no llega a la pantalla, o" % problemas)
        print("  llega dos veces. Los dos casos ya pasaron y los dos salieron")
        print("  limpios: el tablero se dibujo igual, con un numero mal.")
    else:
        print("  TODO CUADRA. Cada peso del contrato esta mostrado o declarado.")
    return problemas


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Cobertura del contrato en el tablero")
    ap.add_argument("--contrato", required=True)
    ap.add_argument("--cliente", default="maga")
    ap.add_argument("--dias", type=int, default=45)
    args = ap.parse_args()
    with io.open(args.contrato, encoding="utf-8") as f:
        contrato = json.load(f)
    filas, hoy = revisar(contrato, args.cliente, args.dias)
    sys.exit(1 if imprimir(filas, hoy) else 0)


if __name__ == "__main__":
    main()
