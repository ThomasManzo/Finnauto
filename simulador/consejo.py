# -*- coding: utf-8 -*-
"""
simulador.consejo — el motor que ACONSEJA, no solo informa.

El timeline te dice "el 25 quedás corto". Este módulo da el paso siguiente:
te dice QUÉ MOVER y CUÁNTO GANÁS con eso.

La lógica de decisión NO está inventada: sale de cómo decide Thomas.
  1. Primero se proponen las DROGUERÍAS (es lo primero que él mueve).
  2. Dentro de eso, el que MÁS DÍAS aguanta, sin importar el monto.
  3. Regla dura: solo sirve mover un pago si su tolerancia alcanza para pasar
     el día crítico. Si vence antes igual, moverlo no resuelve nada.

Todo eso vive en clientes/<cliente>/catalogo.json (orden_de_pateo), no en el
código: otro cliente decide distinto y solo cambia su catálogo.

Uso:
    python simulador/consejo.py --contrato c.json --cheques ch.csv --minimo 200000000
"""

import os
import sys
import json
import argparse
import datetime

BASE_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)

from simulador.semana import (cargar_contrato, cheques_ventana, meta_de, _rigido,
                              _m, cargar_catalogo)


# NOTA: el catalogo se carga en UN SOLO lugar (simulador/semana.py). Antes habia
# un cargador duplicado aca y quedo desactualizado: el consejo llego a proponer
# postergar impuestos y sueldos porque no leia bien las tolerancias. Un solo
# cargador = un solo lugar donde puede estar mal.


# ----------------------------------------------------------------- datos
def egresos(contrato, cat, desde, hasta, cheques):
    """Egresos con su clasificación (los internos quedan afuera: no mueven caja)."""
    out, d, h = [], desde.isoformat(), hasta.isoformat()
    for i, m in enumerate(contrato.get("movimientos", [])):
        f = m.get("fecha")
        if not f or f < d or f > h:
            continue
        meta = meta_de(m, cat)
        if meta.get("interno"):
            continue
        out.append({"id": "m%d" % i, "fecha": f, "tipo": m.get("tipo") or "",
                    "nombre": meta["nombre"], "importe": float(m.get("importe") or 0),
                    "tolerancia": meta["tolerancia"], "rigido": _rigido(meta),
                    "divisible": bool(meta.get("divisible")),
                    "concepto": m.get("concepto", "")})
    for j, c in enumerate(cheques):
        out.append({"id": "ch%d" % j, "fecha": c["fecha"], "tipo": "CHEQUE",
                    "nombre": "Cheque a pagar", "importe": c["importe"],
                    "tolerancia": 0, "rigido": True, "divisible": False,
                    "concepto": ""})   # un cheque es todo o nada: o se cubre o rebota
    return out


def cobros(contrato, desde, hasta):
    out, d, h = [], desde.isoformat(), hasta.isoformat()
    for c in contrato.get("cobros_previstos", []):
        f = c.get("fecha")
        if not f or f < d or f > h or c.get("interno"):
            continue
        out.append({"fecha": f, "importe": float(c.get("importe") or 0),
                    "fijo": c.get("naturaleza") == "FIJO",
                    "concepto": c.get("concepto", "")})
    return out


# ----------------------------------------------------------------- simulación
def saldos(caja, egr, cob, desde, hasta, diferido=None):
    """Saldo conservador arrastrado día a día.

    'diferido' = {id: monto que se posterga}. Es un MONTO y no un sí/no porque a
    una droguería se le puede pagar una parte: si se le deben 500 y se le pagan
    250, se difieren 250 y el resto igual sale ese día. Un cheque, en cambio,
    es todo o nada.
    """
    diferido = diferido or {}
    por_dia = {}
    f = desde
    while f <= hasta:
        por_dia[f.isoformat()] = 0.0
        f += datetime.timedelta(days=1)
    for e in egr:
        if e["fecha"] in por_dia:
            por_dia[e["fecha"]] -= (e["importe"] - diferido.get(e["id"], 0.0))
    for c in cob:
        if c["fijo"] and c["fecha"] in por_dia:   # conservador: solo ingresos fijos
            por_dia[c["fecha"]] += c["importe"]
    serie, acum = [], caja
    for k in sorted(por_dia):
        acum += por_dia[k]
        serie.append((k, acum))
    return serie


def primer_rojo(serie, minimo):
    for fecha, v in serie:
        if v < minimo:
            return fecha, v
    return None, None


# ----------------------------------------------------------------- consejo
def candidatos(egr, dia_critico, prioridad, piso=0):
    """Pagos que se pueden correr MÁS ALLÁ del día crítico, en el orden de Thomas."""
    dc = datetime.date.fromisoformat(dia_critico)
    out = []
    for e in egr:
        if e["rigido"] or not e["tolerancia"]:
            continue
        if e["importe"] < piso:
            continue        # no vale la pena el llamado por ese monto
        f = datetime.date.fromisoformat(e["fecha"])
        if f > dc:
            continue                                   # ya está después: no ayuda
        if f + datetime.timedelta(days=e["tolerancia"]) <= dc:
            continue                                   # no aguanta hasta pasar el día
        out.append(e)

    def clave(e):
        try:
            p = prioridad.index(e["tipo"])
        except ValueError:
            p = len(prioridad)
        # 1) el orden que eligio Thomas (droguerias primero)
        # 2) el que mas dias aguanta
        # 3) el MAS GRANDE: mover 2 pagos grandes es mucho mejor que 26 chicos
        return (p, -(e["tolerancia"] or 0), -e["importe"])
    return sorted(out, key=clave)


def armar_plan(egr, cob, caja, desde, hasta, minimo, prioridad, piso=0):
    serie = saldos(caja, egr, cob, desde, hasta)
    dia, valor = primer_rojo(serie, minimo)
    if not dia:
        return {"ok": True, "serie": serie}

    faltante = minimo - valor
    cands = candidatos(egr, dia, prioridad, piso)
    plan, diferido, ganado = [], {}, 0.0
    for e in cands:
        if ganado >= faltante:
            break
        resta = faltante - ganado
        if e.get("divisible") and e["importe"] > resta:
            monto = resta                 # pago parcial: se difiere solo lo que falta
        else:
            monto = e["importe"]          # todo o nada (cheques, sueldos)
        diferido[e["id"]] = monto
        plan.append(dict(e, diferido=monto, paga=e["importe"] - monto))
        ganado += monto

    serie2 = saldos(caja, egr, cob, desde, hasta, diferido)
    dia2, valor2 = primer_rojo(serie2, minimo)
    return {"ok": False, "dia": dia, "valor": valor, "faltante": faltante,
            "plan": plan, "ganado": ganado, "serie": serie, "serie2": serie2,
            "resuelto": dia2 is None, "dia2": dia2, "valor2": valor2,
            "candidatos": cands}


# ----------------------------------------------------------------- salida
def imprimir(r, minimo, desde, hasta):
    L = 74
    print("=" * L)
    print("  MOTOR DE CONSEJO  .  %s al %s" % (desde.strftime("%d/%m"), hasta.strftime("%d/%m/%Y")))
    print("=" * L)
    print("  Caja minima de seguridad: %s\n" % _m(minimo))

    if r["ok"]:
        print("  [OK] TODO BIEN")
        print("     Ningun dia cae por debajo del minimo en el escenario conservador.")
        print("     No hace falta mover nada.")
        return

    d = datetime.date.fromisoformat(r["dia"])
    print("  [!] PROBLEMA DETECTADO")
    print("     El %s quedas en %s, por debajo del minimo." % (d.strftime("%d/%m/%Y"), _m(r["valor"])))
    print("     Te faltan %s.\n" % _m(r["faltante"]))

    if not r["plan"]:
        print("  [X] NO HAY NADA QUE MOVER")
        print("     Todo lo que vence antes de esa fecha es rigido (o no aguanta")
        print("     hasta pasar ese dia). Hay que resolverlo de otra forma:")
        print("       . adelantar un cobro,  . usar financiacion,  . renegociar un cheque.")
        return

    print("  >> QUE PATEAR (en tu orden: droguerias primero, y el que mas aguanta)")
    for e in r["plan"]:
        f = datetime.date.fromisoformat(e["fecha"])
        det = (" - " + e["concepto"][:24]) if e["concepto"] else ""
        if e["paga"] > 0.01:
            print("     . %s  %-24s PAGAR %s en vez de %s" % (
                f.strftime("%d/%m"), e["nombre"][:24], _m(e["paga"]), _m(e["importe"])))
            print("                                    (diferis %s, aguanta %s dias)%s" % (
                _m(e["diferido"]), e["tolerancia"], det))
        else:
            print("     . %s  %-24s POSTERGAR %s  (aguanta %s dias)%s" % (
                f.strftime("%d/%m"), e["nombre"][:24], _m(e["diferido"]), e["tolerancia"], det))
    print("     %-31s %16s" % ("TOTAL LIBERADO", _m(r["ganado"])))

    print("")
    if r["resuelto"]:
        nuevo = dict(r["serie2"])[r["dia"]]
        print("  [OK] CON ESO SE RESUELVE")
        print("     El %s pasa de %s a %s." % (d.strftime("%d/%m"), _m(r["valor"]), _m(nuevo)))
        print("     Y ningun otro dia queda por debajo del minimo.")
    else:
        d2 = datetime.date.fromisoformat(r["dia2"])
        print("  [!] AYUDA PERO NO ALCANZA")
        print("     Despues de mover eso, el %s seguis en %s." % (d2.strftime("%d/%m/%Y"), _m(r["valor2"])))
        print("     Hay que sumar otra palanca (adelantar cobros o financiacion).")


def main():
    ap = argparse.ArgumentParser(description="Motor de consejo de caja")
    ap.add_argument("--contrato", required=True)
    ap.add_argument("--cheques")
    ap.add_argument("--cliente", default="maga")
    ap.add_argument("--desde")
    ap.add_argument("--dias", type=int, default=21)
    ap.add_argument("--minimo", type=float, default=200000000)
    ap.add_argument("--piso", type=float, default=1000000,
                    help="no proponer mover montos menores a esto")
    args = ap.parse_args()

    desde = datetime.date.fromisoformat(args.desde) if args.desde else datetime.date.today()
    hasta = desde + datetime.timedelta(days=args.dias)

    cat = cargar_catalogo(args.cliente)
    contrato = cargar_contrato(args.contrato)
    ch, _ = cheques_ventana(args.cheques, desde, hasta)

    egr = egresos(contrato, cat, desde, hasta, ch)
    cob = cobros(contrato, desde, hasta)
    r = armar_plan(egr, cob, float(contrato.get("caja_hoy") or 0),
                   desde, hasta, args.minimo, cat["prioridad"], args.piso)
    imprimir(r, args.minimo, desde, hasta)


if __name__ == "__main__":
    main()
