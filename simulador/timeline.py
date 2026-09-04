# -*- coding: utf-8 -*-
"""
simulador.timeline — el escenario DÍA POR DÍA entre dos fechas.

Lo que el total de la semana no te muestra: que un martes puntual quedás corto
aunque la semana cierre bien. Arranca del saldo de hoy y va arrastrando el saldo
día a día, sumando lo que entra y restando lo que sale.

Dos líneas de saldo:
  · CONSERVADOR: solo cuenta los ingresos FIJOS (lo que entra sí o sí).
  · OPTIMISTA  : cuenta también los VARIABLES (que pueden no entrar ese día).

El conservador es el que manda: si ahí quedás en rojo un día, es un riesgo real.

Uso:
    python simulador/timeline.py --contrato c.json --cheques ch.csv --desde 2026-09-04 --dias 21
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

from simulador.semana import (cargar_catalogo, cargar_contrato, _rigido,
                              cheques_ventana, _m, meta_de)

DIAS_ES = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]


def armar_dias(contrato, cat, cheques, desde, hasta):
    """Arma un diccionario fecha -> {fijo, variable, rigido, flexible, detalle}."""
    dias = defaultdict(lambda: {"fijo": 0.0, "variable": 0.0, "rigido": 0.0,
                                "flexible": 0.0, "detalle": []})
    d, h = desde.isoformat(), hasta.isoformat()

    # Egresos (solapa MOVIMIENTOS)
    for m in contrato.get("movimientos", []):
        f = m.get("fecha")
        if not f or f < d or f > h:
            continue
        meta = meta_de(m, cat)
        if meta.get("interno"):
            continue                      # no entra ni sale: no mueve la caja
        imp = float(m.get("importe") or 0)
        clave = "rigido" if _rigido(meta) else "flexible"
        dias[f][clave] += imp
        dias[f]["detalle"].append(("-", meta.get("nombre", ""), imp, clave))

    # Cheques del banco (siempre rígidos)
    for c in cheques:
        f = c["fecha"]
        if not f or f < d or f > h:
            continue
        dias[f]["rigido"] += c["importe"]
        dias[f]["detalle"].append(("-", "Cheque a pagar", c["importe"], "rigido"))

    # Ingresos previstos
    for c in contrato.get("cobros_previstos", []):
        f = c.get("fecha")
        if not f or f < d or f > h or c.get("interno"):
            continue
        imp = float(c.get("importe") or 0)
        clave = "fijo" if c.get("naturaleza") == "FIJO" else "variable"
        dias[f][clave] += imp
        dias[f]["detalle"].append(("+", c.get("concepto", ""), imp, clave))

    return dias


def imprimir(dias, caja, desde, hasta, minimo, detalle=False):
    L = 92
    print("=" * L)
    print("  TIMELINE DE CAJA  ·  %s al %s" % (desde.strftime("%d/%m/%Y"), hasta.strftime("%d/%m/%Y")))
    print("=" * L)
    print("  Saldo de partida: %s" % _m(caja))
    if minimo:
        print("  Caja mínima de seguridad: %s" % _m(minimo))
    print("")
    print("  %-11s %16s %16s %18s %18s" % ("DÍA", "ENTRA", "SALE", "SALDO CONSERV.", "SALDO OPTIM."))
    print("  " + "-" * (L - 4))

    cons = opt = caja
    peor_cons, peor_dia = None, None
    dias_rojos = []

    f = desde
    while f <= hasta:
        k = f.isoformat()
        d = dias.get(k)
        entra_f = d["fijo"] if d else 0.0
        entra_v = d["variable"] if d else 0.0
        sale = (d["rigido"] + d["flexible"]) if d else 0.0

        cons += entra_f - sale
        opt += entra_f + entra_v - sale

        if peor_cons is None or cons < peor_cons:
            peor_cons, peor_dia = cons, f
        bajo = cons < (minimo or 0)
        if bajo:
            dias_rojos.append((f, cons))

        marca = "  <-- BAJO MINIMO" if bajo else ("  <-- ajustado" if minimo and cons < (minimo or 0) * 1.5 else "")
        etiqueta = "%s %s" % (DIAS_ES[f.weekday()], f.strftime("%d/%m"))
        movido = (entra_f or entra_v or sale)
        print("  %-11s %16s %16s %18s %18s%s" % (
            etiqueta,
            _m(entra_f + entra_v) if movido else "-",
            _m(-sale) if sale else "-",
            _m(cons), _m(opt), marca))

        if detalle and d and d["detalle"]:
            for signo, nombre, imp, clave in sorted(d["detalle"], key=lambda x: -x[2]):
                print("       %s %-38s %16s   (%s)" % (signo, nombre[:38], _m(imp), clave))
        f += datetime.timedelta(days=1)

    print("  " + "-" * (L - 4))
    print("\n  Peor día (escenario conservador): %s  ->  %s" % (
        peor_dia.strftime("%d/%m/%Y"), _m(peor_cons)))

    if dias_rojos:
        print("\n  [!] ATENCION: %d día(s) por debajo de la caja mínima:" % len(dias_rojos))
        for f2, v in dias_rojos[:10]:
            print("       %s  ->  %s" % (f2.strftime("%d/%m/%Y"), _m(v)))
    else:
        print("\n  [OK] Ningun dia queda por debajo de la caja mínima en el período.")


def main():
    ap = argparse.ArgumentParser(description="Timeline de caja día por día")
    ap.add_argument("--contrato", required=True)
    ap.add_argument("--cheques")
    ap.add_argument("--cliente", default="maga")
    ap.add_argument("--desde")
    ap.add_argument("--hasta")
    ap.add_argument("--dias", type=int, default=21)
    ap.add_argument("--minimo", type=float, default=0, help="caja mínima de seguridad")
    ap.add_argument("--detalle", action="store_true", help="mostrar qué compone cada día")
    args = ap.parse_args()

    desde = datetime.date.fromisoformat(args.desde) if args.desde else datetime.date.today()
    hasta = (datetime.date.fromisoformat(args.hasta) if args.hasta
             else desde + datetime.timedelta(days=args.dias))

    cat = cargar_catalogo(args.cliente)
    contrato = cargar_contrato(args.contrato)
    cheques, _ = cheques_ventana(args.cheques, desde, hasta)

    dias = armar_dias(contrato, cat, cheques, desde, hasta)
    imprimir(dias, float(contrato.get("caja_hoy") or 0), desde, hasta,
             args.minimo, args.detalle)


if __name__ == "__main__":
    main()
