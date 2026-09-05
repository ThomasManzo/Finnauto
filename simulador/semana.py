# -*- coding: utf-8 -*-
"""
simulador.semana — el escenario de caja a N días, con datos REALES.

Punta final de la cadena:

    Cash (planilla)  --Exportador.gs-->  contrato.json  --+
                                                          +--> ESTE MODULO --> el escenario
    Banco (listado)  --ingestas/cheques.py--> cheques  ---+

Reglas (salen del catálogo del cliente, no están hardcodeadas):
  · INTERNOS (transferencias entre cuentas propias, depósitos de efectivo) NO
    cuentan: la plata no entra ni sale, solo cambia de lugar.
  · Egresos: RÍGIDOS (dias_tolerancia = 0: sueldos, cheques, impuestos...) vs
    FLEXIBLES (se pueden patear N días).
  · Ingresos: FIJOS (entran sí o sí) vs VARIABLES (pueden no entrar ese día).
  · Los CHEQUES son el rígido más duro: si no se cubren, la empresa va al BCRA.
  · MONTO VARIABLE: eje aparte de la tolerancia. Hay pagos con fecha FIJA cuyo
    importe es una estimación (ej. Honorarios DJ = 10% del resultado del mes
    anterior). No se pueden patear, pero su número puede moverse: por eso el
    escenario los marca y --estres permite ver si el plan aguanta si suben.

Dos escenarios:
  · CONSERVADOR  = solo con los ingresos FIJOS. Es el que manda para decidir.
  · OPTIMISTA    = contando también los VARIABLES.

Uso:
    python simulador/semana.py --contrato ruta.json --cheques listado.csv --dias 7
"""

import os
import sys
import json
import argparse
import re
import datetime
from collections import defaultdict

BASE_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)


# ------------------------------------------------------------------ catálogo
def cargar_catalogo(cliente):
    """Devuelve {'tipos': {...}, 'excepciones': [...]}.

    Las EXCEPCIONES miran el concepto y pisan la tolerancia del tipo: bajo un
    mismo TIPO puede haber cosas muy distintas (ej. 'RETIRO_SOCIO' incluye tanto
    el retiro discrecional de los socios como la CUOTA DE UN PRÉSTAMO, que no se
    puede patear). Sin esto, el consejo sale mal.
    """
    ruta = os.path.join(BASE_REPO, "clientes", cliente, "catalogo.json")
    with open(ruta, "r", encoding="utf-8") as f:
        cat = json.load(f)
    tipos = {}
    for t in cat.get("tipos", {}).get("valores", []):
        tipos[t["id"]] = {
            "nombre": t.get("nombre", t["id"]),
            "tolerancia": t.get("dias_tolerancia"),
            "interno": bool(t.get("interno")),
            "divisible": bool(t.get("divisible")),
            "consecuencia": t.get("consecuencia", ""),
            "monto_variable": bool(t.get("monto_variable")),
        }
    exc = []
    for r in cat.get("excepciones_por_concepto", {}).get("reglas", []):
        exc.append({
            "contiene": [c.upper() for c in r.get("contiene", [])],
            "nombre": r.get("nombre"),
            "tolerancia": r.get("dias_tolerancia"),
            "consecuencia": r.get("consecuencia", ""),
            "interno": bool(r.get("interno")),
            "tiene_tolerancia": ("dias_tolerancia" in r),
            "monto_variable": bool(r.get("monto_variable")),
            "palabra_completa": bool(r.get("palabra_completa")),
        })
    # Orden con el que el cliente decide que patear cuando falta plata.
    prioridad = cat.get("orden_de_pateo", {}).get("prioridad_por_tipo", [])
    return {"tipos": tipos, "excepciones": exc, "prioridad": prioridad}


def _matchea(concepto, regla):
    """Por defecto la excepcion matchea por SUBCADENA, que alcanza casi siempre.

    Con "palabra_completa": true matchea solo palabras enteras. Hace falta cuando
    la clave es corta y se mete adentro de otra: "DJ" aparece dentro de
    "D.Jaimovich", y ya nos paso lo mismo con "PERSONAL" dentro de "PERSONALES".
    """
    if regla.get("palabra_completa"):
        return any(re.search(r"(?<![A-Z0-9])%s(?![A-Z0-9])" % re.escape(p), concepto)
                   for p in regla["contiene"])
    return any(p in concepto for p in regla["contiene"])


def meta_de(mov, cat):
    """Clasifica un movimiento: primero por TIPO, y si alguna excepción matchea
    el CONCEPTO, esa pisa la tolerancia y el nombre."""
    tipo = mov.get("tipo") or ""
    base = cat["tipos"].get(tipo, {"nombre": tipo or "(sin tipo)", "tolerancia": None,
                                   "interno": False, "consecuencia": "?",
                                   "monto_variable": False})
    meta = dict(base)
    concepto = (mov.get("concepto") or "").upper()
    if concepto:
        for r in cat["excepciones"]:
            if _matchea(concepto, r):
                meta["nombre"] = r["nombre"] or meta["nombre"]
                if r.get("tiene_tolerancia"):
                    meta["tolerancia"] = r["tolerancia"]
                meta["consecuencia"] = r["consecuencia"] or meta["consecuencia"]
                if r.get("monto_variable"):
                    # OJO: monto_variable NO afecta la tolerancia. Son dos ejes
                    # distintos: la fecha sigue siendo fija, lo que no es cierto
                    # es el IMPORTE (ej. Honorarios DJ = 10% del resultado).
                    meta["monto_variable"] = True
                if r.get("interno"):
                    meta["interno"] = True      # no es gasto: no sale del grupo
                    meta["divisible"] = False
                meta["excepcion"] = True
                break
    return meta


def _rigido(meta):
    return meta.get("tolerancia") == 0


# ------------------------------------------------------------------ lectura
def cargar_contrato(ruta):
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def egresos_ventana(contrato, cat, desde, hasta):
    d, h = desde.isoformat(), hasta.isoformat()
    rigidos, flexibles, internos = [], [], []
    for m in contrato.get("movimientos", []):
        f = m.get("fecha")
        if not f or f < d or f > h:
            continue
        tipo = m.get("tipo") or ""
        meta = meta_de(m, cat)
        item = {"fecha": f, "tipo": tipo, "nombre": meta["nombre"],
                "importe": float(m.get("importe") or 0),
                "tolerancia": meta["tolerancia"], "consecuencia": meta["consecuencia"]}
        if meta["interno"]:
            internos.append(item)
        elif _rigido(meta):
            rigidos.append(item)
        else:
            flexibles.append(item)
    return rigidos, flexibles, internos


def cobros_ventana(contrato, desde, hasta):
    """Ingresos previstos, separados en FIJOS / VARIABLES (los internos se descartan)."""
    d, h = desde.isoformat(), hasta.isoformat()
    fijos, variables, internos = [], [], []
    for c in contrato.get("cobros_previstos", []):
        f = c.get("fecha")
        if not f or f < d or f > h:
            continue
        item = {"fecha": f, "concepto": c.get("concepto", ""), "unidad": c.get("unidad", ""),
                "importe": float(c.get("importe") or 0), "naturaleza": c.get("naturaleza")}
        if c.get("interno"):
            internos.append(item)
        elif c.get("naturaleza") == "FIJO":
            fijos.append(item)
        else:
            variables.append(item)
    return fijos, variables, internos


def cheques_ventana(ruta_csv, desde, hasta):
    if not ruta_csv:
        return [], None
    from ingestas.cheques import parse_galicia, proximos
    obl, resumen = parse_galicia(ruta_csv)
    prox = proximos(obl, desde.isoformat(), hasta.isoformat())
    items = [{"fecha": o["fecha_vencimiento"], "tipo": "CHEQUE", "nombre": "Cheque a pagar",
              "importe": o["importe"], "tolerancia": 0, "consecuencia": "BCRA"} for o in prox]
    return items, resumen


def deuda_resumen(contrato):
    """Deuda VIVA con droguerías (terceros).

    OJO: en el bloque de deuda, una fecha PASADA significa que ese pago YA SE HIZO.
    Así que la deuda que todavía hay que pagar es solo la que está PENDIENTE.
    Las NCR vienen con signo invertido (restan), así que la suma ya las contempla.
    """
    pendiente, pagado, por_c = 0.0, 0.0, defaultdict(float)
    for d in contrato.get("deuda_droguerias", []):
        if d.get("intercompany"):
            continue
        imp = float(d.get("importe") or 0)
        est = d.get("estado")
        if est in ("PAGADO",):
            pagado += imp
            continue
        pendiente += imp
        por_c[d.get("contraparte", "?")] += imp
    return pendiente, pagado, dict(por_c)


# ------------------------------------------------------------------ cálculo
def calcular(caja, rigidos, flexibles, fijos, variables):
    t_rig = sum(i["importe"] for i in rigidos)
    t_flex = sum(i["importe"] for i in flexibles)
    t_fijo = sum(i["importe"] for i in fijos)
    t_var = sum(i["importe"] for i in variables)
    return {
        "caja": caja, "rigido": t_rig, "flexible": t_flex,
        "fijo": t_fijo, "variable": t_var,
        # Escenarios (después de pagar TODO lo de la semana)
        "conservador": caja + t_fijo - t_rig - t_flex,
        "optimista": caja + t_fijo + t_var - t_rig - t_flex,
        # Margen para una jugada nueva, cubriendo lo de la semana
        "margen_seguro": caja + t_fijo - t_rig - t_flex,
        "margen_optimista": caja + t_fijo + t_var - t_rig - t_flex,
        # Si solo cubrimos lo intocable y pateamos todo lo flexible
        "margen_max": caja + t_fijo - t_rig,
    }


def sugerir_pateo(flexibles, faltante):
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
    """Formato argentino: $1.183.497.652,34 (miles con punto, decimales con coma).

    Es el mismo formato de la planilla: si el tablero muestra otro, el dueno
    tiene que traducir mentalmente cada numero antes de creerselo.
    """
    signo = "-" if x < 0 else ""
    ent = format(abs(round(x, 2)), ",.2f")          # 1,234.56
    ent = ent.replace(",", "@").replace(".", ",").replace("@", ".")
    return signo + "$" + ent


def _agrupar(items, campo="nombre"):
    agg = defaultdict(lambda: [0.0, 0])
    for i in items:
        agg[i.get(campo, "?")][0] += i["importe"]
        agg[i.get(campo, "?")][1] += 1
    return sorted([(k, v[0], v[1]) for k, v in agg.items()], key=lambda t: -t[1])


def imprimir(res, rigidos, flexibles, fijos, variables, internos, desde, hasta, deuda):
    L = 70
    print("=" * L)
    print("  ESCENARIO DE CAJA  ·  %s al %s" % (desde.strftime("%d/%m"), hasta.strftime("%d/%m/%Y")))
    print("=" * L)
    print("\n  Caja hoy (bancos + efectivo)              %20s" % _m(res["caja"]))

    print("\n  ── INGRESOS FIJOS (entran sí o sí) ─────────────────────────")
    for n, t, c in _agrupar(fijos, "concepto"):
        print("     %-32s %3d %20s" % (n, c, _m(t)))
    print("     %-32s %3s %20s" % ("TOTAL FIJOS", "", _m(res["fijo"])))

    print("\n  ── INGRESOS VARIABLES (pueden no entrar) ───────────────────")
    for n, t, c in _agrupar(variables, "concepto"):
        print("     %-32s %3d %20s" % (n, c, _m(t)))
    print("     %-32s %3s %20s" % ("TOTAL VARIABLES", "", _m(res["variable"])))

    print("\n  ── EGRESOS RÍGIDOS (no se pueden mover) ────────────────────")
    for n, t, c in _agrupar(rigidos):
        print("     %-32s %3d %20s" % (n, c, _m(t)))
    print("     %-32s %3s %20s" % ("TOTAL RÍGIDO", "", _m(res["rigido"])))

    print("\n  ── EGRESOS FLEXIBLES (se pueden patear) ────────────────────")
    for n, t, c in _agrupar(flexibles):
        tol = next((i["tolerancia"] for i in flexibles if i["nombre"] == n), "?")
        print("     %-32s %3d %20s  (%s días)" % (n, c, _m(t), tol))
    print("     %-32s %3s %20s" % ("TOTAL FLEXIBLE", "", _m(res["flexible"])))

    if internos:
        print("\n  ── INTERNOS (no entran ni salen) ───────────────────────────")
        print("     %-32s %3d %20s  ← excluidos" % ("Movimientos internos", len(internos),
                                                    _m(sum(i["importe"] for i in internos))))

    print("\n" + "=" * L)
    print("  ESCENARIO CONSERVADOR  (solo ingresos seguros)  %18s" % _m(res["conservador"]))
    print("  ESCENARIO OPTIMISTA    (si entra todo)          %18s" % _m(res["optimista"]))
    print("=" * L)

    # Veredicto
    print("")
    if res["conservador"] >= 0:
        print("  🟢 PODÉS PAGAR TRANQUILO")
        print("     Cubrís todo lo de la semana aunque no entre ningún ingreso variable.")
    elif res["optimista"] >= 0:
        print("  🟡 RIESGOSO")
        print("     Solo cierra si entran los ingresos variables (%s)." % _m(res["variable"]))
        print("     Si no entran, te faltan %s." % _m(-res["conservador"]))
        plan = sugerir_pateo(flexibles, -res["conservador"])
        if plan:
            print("\n     ¿Qué patear? (lo de mayor tolerancia primero):")
            for i in plan:
                print("       · %-28s %16s  (hasta %s días)" % (i["nombre"], _m(i["importe"]), i["tolerancia"]))
    else:
        print("  🔴 NO ALCANZA")
        print("     Ni con los ingresos variables cubrís la semana. Faltan %s." % _m(-res["optimista"]))

    print("\n  >> MÁXIMO PARA UNA JUGADA NUEVA (pagar a una droguería)")
    print("     sin depender de ingresos variables:       %20s" % _m(max(0, res["margen_seguro"])))
    print("     si además pateás todo lo flexible:        %20s" % _m(max(0, res["margen_max"])))

    pendiente, pagado, por_c = deuda
    if por_c:
        print("\n  ── DEUDA VIVA CON DROGUERÍAS (lo que falta pagar) ──────────")
        for c, v in sorted(por_c.items(), key=lambda kv: -kv[1]):
            etiqueta = c + ("  (nota de crédito, resta)" if v < 0 else "")
            print("     %-42s %20s" % (etiqueta[:42], _m(v)))
        print("     %-42s %20s" % ("TOTAL PENDIENTE", _m(pendiente)))
        print("     (ya pagado en el período: %s)" % _m(pagado))


def main():
    ap = argparse.ArgumentParser(description="Escenario de caja a N días con datos reales")
    ap.add_argument("--contrato", required=True)
    ap.add_argument("--cheques")
    ap.add_argument("--cliente", default="maga")
    ap.add_argument("--dias", type=int, default=7)
    ap.add_argument("--desde")
    args = ap.parse_args()

    desde = datetime.date.fromisoformat(args.desde) if args.desde else datetime.date.today()
    hasta = desde + datetime.timedelta(days=args.dias)

    cat = cargar_catalogo(args.cliente)
    contrato = cargar_contrato(args.contrato)

    rigidos, flexibles, int_eg = egresos_ventana(contrato, cat, desde, hasta)
    fijos, variables, int_in = cobros_ventana(contrato, desde, hasta)
    ch, _ = cheques_ventana(args.cheques, desde, hasta)
    rigidos += ch

    res = calcular(float(contrato.get("caja_hoy") or 0), rigidos, flexibles, fijos, variables)
    imprimir(res, rigidos, flexibles, fijos, variables, int_eg + int_in,
             desde, hasta, deuda_resumen(contrato))


if __name__ == "__main__":
    main()
