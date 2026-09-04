# -*- coding: utf-8 -*-
"""
simulador.semana — el escenario de caja a N días, con datos REALES.

Esta es la punta final de la cadena:

    Cash (planilla)  --Exportador.gs-->  contrato.json  --+
                                                          +--> ESTE MODULO --> el escenario
    Banco (listado)  --ingestas/cheques.py--> cheques  ---+

Reglas que aplica (salen del catálogo del cliente, no están hardcodeadas):
  · Los movimientos INTERNOS (transferencias entre cuentas propias, depósitos de
    efectivo) NO son egresos: la plata no sale, solo cambia de lugar.
  · Los egresos se parten en RÍGIDOS (dias_tolerancia = 0: sueldos, cheques,
    impuestos, alquileres...) y FLEXIBLES (se pueden patear N días).
  · Los CHEQUES son el rígido más duro: si no se cubren, la empresa va al BCRA.

Uso:
    python simulador/semana.py --contrato ruta.json --cheques listado.csv --dias 7
"""

import os
import sys
import json
import argparse
import datetime
from collections import defaultdict

BASE_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)


# ------------------------------------------------------------------ catálogo
def cargar_catalogo(cliente):
    ruta = os.path.join(BASE_REPO, "clientes", cliente, "catalogo.json")
    with open(ruta, "r", encoding="utf-8") as f:
        cat = json.load(f)
    tipos = {}
    for t in cat.get("tipos", {}).get("valores", []):
        tipos[t["id"]] = {
            "nombre": t.get("nombre", t["id"]),
            "tolerancia": t.get("dias_tolerancia"),
            "interno": bool(t.get("interno")),
            "consecuencia": t.get("consecuencia", ""),
            "categoria": t.get("categoria", ""),
        }
    return tipos


def _es_rigido(meta):
    """Rígido = no se puede mover ni un día."""
    return (meta.get("tolerancia") == 0)


# ------------------------------------------------------------------ datos
def cargar_contrato(ruta):
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def egresos_ventana(contrato, tipos, desde, hasta):
    """Movimientos de egreso en la ventana, ya clasificados y sin los internos."""
    d, h = desde.isoformat(), hasta.isoformat()
    rigidos, flexibles, internos = [], [], []
    for m in contrato.get("movimientos", []):
        f = m.get("fecha")
        if not f or f < d or f > h:
            continue
        tipo = m.get("tipo") or ""
        meta = tipos.get(tipo, {"nombre": tipo or "(sin tipo)", "tolerancia": None,
                                "interno": False, "consecuencia": "?", "categoria": "?"})
        item = {
            "fecha": f, "tipo": tipo, "nombre": meta["nombre"],
            "importe": float(m.get("importe") or 0),
            "unidad": m.get("unidad", ""), "banco": m.get("banco", ""),
            "estado": m.get("estado", ""), "tolerancia": meta["tolerancia"],
            "consecuencia": meta["consecuencia"],
        }
        if meta["interno"]:
            internos.append(item)
        elif _es_rigido(meta):
            rigidos.append(item)
        else:
            flexibles.append(item)
    return rigidos, flexibles, internos


def cheques_ventana(ruta_csv, desde, hasta):
    """Cheques del listado del banco que vencen en la ventana (siempre rígidos)."""
    if not ruta_csv:
        return [], None
    from ingestas.cheques import parse_galicia, proximos
    obl, resumen = parse_galicia(ruta_csv)
    prox = proximos(obl, desde.isoformat(), hasta.isoformat())
    items = [{
        "fecha": o["fecha_vencimiento"], "tipo": "CHEQUE", "nombre": "Cheque a pagar",
        "importe": o["importe"], "unidad": o.get("unidad", ""), "banco": o.get("banco", ""),
        "estado": o.get("estado_banco", ""), "tolerancia": 0, "consecuencia": "BCRA",
    } for o in prox]
    return items, resumen


# ------------------------------------------------------------------ cálculo
def calcular(caja, rigidos, flexibles):
    tot_rig = sum(i["importe"] for i in rigidos)
    tot_flex = sum(i["importe"] for i in flexibles)
    return {
        "caja": caja,
        "rigido": tot_rig,
        "flexible": tot_flex,
        "tras_rigidos": caja - tot_rig,          # lo que queda después de lo intocable
        "tras_todo": caja - tot_rig - tot_flex,  # si además pagás todo lo flexible
        "margen": caja - tot_rig,                # máximo disponible para maniobrar
    }


def sugerir_pateo(flexibles, faltante):
    """Si falta plata, propone qué patear: primero lo de mayor tolerancia."""
    if faltante <= 0:
        return []
    orden = sorted(flexibles, key=lambda i: (-(i["tolerancia"] or 0), -i["importe"]))
    plan, acum = [], 0.0
    for i in orden:
        if acum >= faltante:
            break
        plan.append(i)
        acum += i["importe"]
    return plan


# ------------------------------------------------------------------ salida
def _m(x):
    return "$" + format(round(x, 2), ",.2f")


def imprimir(res, rigidos, flexibles, internos, desde, hasta, resumen_ch):
    print("=" * 68)
    print("  ESCENARIO DE CAJA  ·  %s a %s" % (desde.strftime("%d/%m"), hasta.strftime("%d/%m/%Y")))
    print("=" * 68)
    print("\n  Caja hoy (bancos + efectivo)            %18s" % _m(res["caja"]))

    print("\n  ── LO RÍGIDO (no se puede mover) ──────────────────────────")
    for nombre, tot, n in _agrupar(rigidos):
        print("     %-30s %3d  %18s" % (nombre, n, _m(tot)))
    print("     %-30s %3s  %18s" % ("TOTAL RÍGIDO", "", _m(res["rigido"])))

    print("\n  ── LO FLEXIBLE (se puede patear) ──────────────────────────")
    for nombre, tot, n in _agrupar(flexibles):
        tol = next((i["tolerancia"] for i in flexibles if i["nombre"] == nombre), None)
        print("     %-30s %3d  %18s   (hasta %s días)" % (nombre, n, _m(tot), tol))
    print("     %-30s %3s  %18s" % ("TOTAL FLEXIBLE", "", _m(res["flexible"])))

    if internos:
        tot_int = sum(i["importe"] for i in internos)
        print("\n  ── INTERNOS (NO son gasto: la plata no sale) ──────────────")
        print("     %-30s %3d  %18s   ← excluidos" % ("Movimientos internos", len(internos), _m(tot_int)))

    print("\n" + "-" * 68)
    print("  Después de pagar LO RÍGIDO              %18s" % _m(res["tras_rigidos"]))
    print("  Después de pagar TODO                   %18s" % _m(res["tras_todo"]))
    print("-" * 68)

    print("\n  >> MÁXIMO QUE PODÉS PAGAR A UNA DROGUERÍA")
    print("     sin comprometer lo rígido:           %18s" % _m(max(0, res["margen"])))
    print("\n  (OJO: todavía NO se cuentan los INGRESOS de la semana —")
    print("   venta diaria, obras sociales, cartera de cheques —, así que")
    print("   este es el piso: el peor escenario posible.)")

    if resumen_ch:
        print("\n  Listado de cheques: %s pendientes de %s leídos." % (
            resumen_ch.get("pendientes"), resumen_ch.get("cheques")))


def _agrupar(items):
    agg = defaultdict(lambda: [0.0, 0])
    for i in items:
        agg[i["nombre"]][0] += i["importe"]
        agg[i["nombre"]][1] += 1
    return sorted([(k, v[0], v[1]) for k, v in agg.items()], key=lambda t: -t[1])


def main():
    ap = argparse.ArgumentParser(description="Escenario de caja a N días con datos reales")
    ap.add_argument("--contrato", required=True, help="JSON exportado del Cash")
    ap.add_argument("--cheques", help="CSV del listado de cheques emitidos del banco")
    ap.add_argument("--cliente", default="maga")
    ap.add_argument("--dias", type=int, default=7)
    ap.add_argument("--desde", help="AAAA-MM-DD (default: hoy)")
    args = ap.parse_args()

    desde = datetime.date.fromisoformat(args.desde) if args.desde else datetime.date.today()
    hasta = desde + datetime.timedelta(days=args.dias)

    tipos = cargar_catalogo(args.cliente)
    contrato = cargar_contrato(args.contrato)

    rigidos, flexibles, internos = egresos_ventana(contrato, tipos, desde, hasta)
    ch, resumen_ch = cheques_ventana(args.cheques, desde, hasta)
    rigidos += ch   # los cheques son siempre rígidos

    res = calcular(float(contrato.get("caja_hoy") or 0), rigidos, flexibles)
    imprimir(res, rigidos, flexibles, internos, desde, hasta, resumen_ch)


if __name__ == "__main__":
    main()
