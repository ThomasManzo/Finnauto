# -*- coding: utf-8 -*-
"""
memoria.registro — la memoria interna del modelo.

La idea (de Thomas): el modelo tiene que ACORDARSE de lo que proyectó, para
después poder decir si se cumplió, por qué monto y en qué fecha.

    "lo unico que puede servir es que el modelo cuente con una memoria interna"

Es a propósito un módulo TONTO: acá NO se calibra ni se predice nada. Solo se
registra y se compara. Es la diferencia entre un dato y una opinión:

    guardar()    -> foto de lo que el modelo creía que iba a pasar
    conciliar()  -> esa foto contra lo que efectivamente pasó
    resumen()    -> cuánto le pega cada TIPO de movimiento

Recién cuando haya varios meses de esto se puede pensar en usar el historial
para ajustar proyecciones. Antes de eso, cualquier "calibración" sería inventar
un número con una muestra de uno.

Por qué NO es una base de datos: son archivos JSON, uno por corrida, dentro de
clientes/<cliente>/memoria/. Se pueden abrir, mirar, versionar y borrar a mano.
Cuando haya muchos clientes se cambia el backend; el contrato de este módulo no.

Uso:
    python memoria/registro.py guardar   --contrato c.json
    python memoria/registro.py conciliar --contrato c_nuevo.json
    python memoria/registro.py resumen
"""

import os
import io
import sys
import json
import glob
import argparse
import datetime

BASE_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)

from nucleo.utilidades import _norm
from simulador.semana import cargar_catalogo, meta_de


# --------------------------------------------------------------- huellas
# Un movimiento no tiene ID estable entre dos exportaciones de la planilla: si
# el administrativo cambia la fecha o el monto, sigue siendo "el mismo pago".
# Por eso la huella es TIPO + CONCEPTO (lo que no cambia cuando se reprograma),
# y la fecha y el importe son justamente lo que después se compara.
def huella(mov):
    return "%s|%s" % ((mov.get("tipo") or "").upper().strip(),
                      _norm(mov.get("concepto")))


def _mov(m, i):
    return {
        "ref": "m%d" % i,
        "huella": huella(m),
        "fecha": m.get("fecha"),
        "importe": float(m.get("importe") or 0),
        "tipo": (m.get("tipo") or "").upper().strip(),
        "concepto": m.get("concepto") or "",
    }


def _dir_memoria(cliente):
    d = os.path.join(BASE_REPO, "clientes", cliente, "memoria")
    if not os.path.isdir(d):
        os.makedirs(d)
    return d


# --------------------------------------------------------------- guardar
def guardar(cliente, contrato, corte=None, dias=30, etiqueta=""):
    """Congela lo que el modelo cree HOY que va a pasar en los próximos N días.

    Solo se guarda el FUTURO: lo pasado ya no es una proyección, es un hecho.
    """
    corte = corte or datetime.date.today()
    hasta = corte + datetime.timedelta(days=dias)
    c, h = corte.isoformat(), hasta.isoformat()

    cat = cargar_catalogo(cliente)
    movs = []
    for i, m in enumerate(contrato.get("movimientos", [])):
        f = m.get("fecha")
        if not f or f < c or f > h:
            continue
        meta = meta_de(m, cat)
        if meta.get("interno"):
            continue                      # los internos no mueven caja: no interesa seguirlos
        d = _mov(m, i)
        d["monto_variable"] = bool(meta.get("monto_variable"))
        d["tolerancia"] = meta.get("tolerancia")
        movs.append(d)

    snap = {
        "version": 1,
        "cliente": cliente,
        "corte": c,               # el día en que el modelo hizo esta proyección
        "hasta": h,
        "etiqueta": etiqueta,
        "caja_hoy": float(contrato.get("caja_hoy") or 0),
        "proyectados": movs,
    }
    ruta = os.path.join(_dir_memoria(cliente), "proyeccion_%s.json" % c)
    with io.open(ruta, "w", encoding="utf-8") as f:
        f.write(json.dumps(snap, ensure_ascii=False, indent=2))
    return ruta, snap


def snapshots(cliente):
    d = os.path.join(BASE_REPO, "clientes", cliente, "memoria")
    return sorted(glob.glob(os.path.join(d, "proyeccion_*.json")))


def leer(ruta):
    with io.open(ruta, encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------- conciliar
def conciliar(snap, contrato, corte_real=None, cat=None):
    """Compara una proyección vieja contra la realidad de hoy.

    Solo se juzga lo que ya VENCIÓ: un pago proyectado para dentro de una semana
    todavía no se cumplió ni se incumplió, no se cuenta ni a favor ni en contra.
    """
    corte_real = corte_real or datetime.date.today()
    cr = corte_real.isoformat()
    # BUG QUE YA APARECIO: guardar() filtra los INTERNOS pero conciliar() no lo
    # hacia, asi que cada transferencia entre cuentas propias figuraba como
    # "movimiento que nadie proyecto". Los dos lados tienen que mirar lo mismo.
    cat = cat or cargar_catalogo(snap["cliente"])

    # Lo proyectado que ya deberia haber pasado.
    pend = {}
    for m in snap["proyectados"]:
        if m["fecha"] and m["fecha"] <= cr:
            pend.setdefault(m["huella"], []).append(dict(m))

    # La realidad, agrupada por la misma huella.
    reales = {}
    for i, m in enumerate(contrato.get("movimientos", [])):
        f = m.get("fecha")
        if not f or f > cr or f < snap["corte"]:
            continue
        if meta_de(m, cat).get("interno"):
            continue                      # no mueve caja: no se proyecta ni se juzga
        d = _mov(m, i)
        reales.setdefault(d["huella"], []).append(d)

    filas = []
    for hu, proys in pend.items():
        cands = sorted(reales.get(hu, []), key=lambda x: (x["fecha"], x["importe"]))
        for p in sorted(proys, key=lambda x: (x["fecha"], x["importe"])):
            if not cands:
                filas.append(_fila(p, None))
                continue
            # Se empareja con el real MÁS PARECIDO (primero monto, después fecha):
            # si el mismo proveedor tiene varios pagos, el que se le parece más
            # es casi siempre el que era.
            r = min(cands, key=lambda x: (abs(x["importe"] - p["importe"]),
                                          abs(_dias(x["fecha"], p["fecha"]))))
            cands.remove(r)
            filas.append(_fila(p, r))
        reales[hu] = cands

    # Lo que apareció y nadie había proyectado: son las sorpresas, y suelen ser
    # la razón real por la que un mes no cierra como se esperaba.
    sorpresas = []
    for hu, resto in reales.items():
        for r in resto:
            sorpresas.append(r)

    return {"corte_proyeccion": snap["corte"], "corte_real": cr,
            "filas": filas, "sorpresas": sorpresas}


def _dias(a, b):
    return (datetime.date.fromisoformat(a) - datetime.date.fromisoformat(b)).days


def _fila(p, r):
    if r is None:
        return {"estado": "NO_APARECIO", "tipo": p["tipo"], "concepto": p["concepto"],
                "fecha_proy": p["fecha"], "fecha_real": None,
                "monto_proy": p["importe"], "monto_real": 0.0,
                "desvio_dias": None, "desvio_monto": -p["importe"],
                "monto_variable": p.get("monto_variable", False)}
    dd = _dias(r["fecha"], p["fecha"])
    dm = r["importe"] - p["importe"]
    # Tolerancia de centavos: la planilla redondea y no queremos ruido.
    if dd == 0 and abs(dm) < 1:
        est = "CUMPLIO"
    elif dd == 0:
        est = "CAMBIO_MONTO"
    elif abs(dm) < 1:
        est = "CAMBIO_FECHA"
    else:
        est = "CAMBIO_AMBOS"
    return {"estado": est, "tipo": p["tipo"], "concepto": p["concepto"],
            "fecha_proy": p["fecha"], "fecha_real": r["fecha"],
            "monto_proy": p["importe"], "monto_real": r["importe"],
            "desvio_dias": dd, "desvio_monto": dm,
            "monto_variable": p.get("monto_variable", False)}


# --------------------------------------------------------------- resumen
def resumen(concs):
    """Agrega varias conciliaciones por TIPO.

    Esto es lo único que a futuro puede alimentar una calibración: si el TIPO
    'PAGO' históricamente sale 4 días tarde y un 8% más caro, el modelo lo puede
    usar. Con UNA sola conciliación no alcanza, y el resumen lo dice explícito.
    """
    por = {}
    for c in concs:
        for f in c["filas"]:
            d = por.setdefault(f["tipo"], {"n": 0, "cumplio": 0, "no_aparecio": 0,
                                           "dias": [], "desvio_pct": []})
            d["n"] += 1
            if f["estado"] == "CUMPLIO":
                d["cumplio"] += 1
            if f["estado"] == "NO_APARECIO":
                d["no_aparecio"] += 1
                continue
            if f["desvio_dias"] is not None:
                d["dias"].append(f["desvio_dias"])
            if f["monto_proy"]:
                d["desvio_pct"].append(100.0 * f["desvio_monto"] / f["monto_proy"])
    out = []
    for t, d in sorted(por.items()):
        out.append({
            "tipo": t, "n": d["n"],
            "pct_cumplio": (100.0 * d["cumplio"] / d["n"]) if d["n"] else 0.0,
            "no_aparecio": d["no_aparecio"],
            "dias_prom": (sum(d["dias"]) / len(d["dias"])) if d["dias"] else 0.0,
            "desvio_pct_prom": (sum(d["desvio_pct"]) / len(d["desvio_pct"])) if d["desvio_pct"] else 0.0,
        })
    return sorted(out, key=lambda x: -x["n"])


# --------------------------------------------------------------- salida
def _m(v):
    return "$" + format(int(round(v)), ",d").replace(",", ".")


def imprimir_conciliacion(c):
    L = 78
    print("=" * L)
    print("  MEMORIA . proyectado el %s  vs  realidad al %s" % (c["corte_proyeccion"], c["corte_real"]))
    print("=" * L)
    filas = c["filas"]
    if not filas:
        print("  Todavia no vencio nada de esa proyeccion: no hay nada que juzgar.")
        return
    orden = {"NO_APARECIO": 0, "CAMBIO_AMBOS": 1, "CAMBIO_MONTO": 2, "CAMBIO_FECHA": 3, "CUMPLIO": 4}
    n_ok = sum(1 for f in filas if f["estado"] == "CUMPLIO")
    print("  %d de %d movimientos salieron exactamente como se proyectaron (%.0f%%)" % (
        n_ok, len(filas), 100.0 * n_ok / len(filas)))
    print("")
    print("  %-14s %-24s %10s %10s %6s" % ("ESTADO", "CONCEPTO", "PROY", "REAL", "DIAS"))
    print("  " + "-" * (L - 4))
    for f in sorted(filas, key=lambda x: orden.get(x["estado"], 9)):
        dias = "" if f["desvio_dias"] is None else "%+d" % f["desvio_dias"]
        marca = " *" if f["monto_variable"] else ""
        print("  %-14s %-24s %10s %10s %6s%s" % (
            f["estado"], (f["concepto"] or f["tipo"])[:24],
            _m(f["monto_proy"]), _m(f["monto_real"]), dias, marca))
    if any(f["monto_variable"] for f in filas):
        print("\n  (*) monto estimado por definicion: el desvio ahi es esperable.")
    if c["sorpresas"]:
        tot = sum(s["importe"] for s in c["sorpresas"])
        print("\n  [!] %d movimiento(s) que NADIE habia proyectado, por %s:" % (len(c["sorpresas"]), _m(tot)))
        for s in sorted(c["sorpresas"], key=lambda x: -x["importe"])[:8]:
            print("      . %s  %-28s %s" % (s["fecha"], (s["concepto"] or s["tipo"])[:28], _m(s["importe"])))


def imprimir_resumen(rs, n_snaps):
    L = 78
    print("=" * L)
    print("  MEMORIA . comportamiento historico por tipo")
    print("=" * L)
    if not rs:
        print("  Todavia no hay nada conciliado.")
        return
    print("  %-20s %5s %9s %11s %12s" % ("TIPO", "N", "CUMPLIO", "DIAS PROM", "DESVIO $"))
    print("  " + "-" * (L - 4))
    for r in rs:
        print("  %-20s %5d %8.0f%% %+10.1f %+11.1f%%" % (
            r["tipo"][:20], r["n"], r["pct_cumplio"], r["dias_prom"], r["desvio_pct_prom"]))
    print("")
    if n_snaps < 3:
        print("  [i] Solo hay %d proyeccion(es) conciliada(s). Estos numeros TODAVIA NO" % n_snaps)
        print("      sirven para ajustar nada: son una muestra muy chica. Se vuelven")
        print("      utiles con varios meses de historia.")


# --------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser(description="Memoria interna del modelo")
    ap.add_argument("accion", choices=["guardar", "conciliar", "resumen", "listar"])
    ap.add_argument("--contrato")
    ap.add_argument("--cliente", default="maga")
    ap.add_argument("--dias", type=int, default=30)
    ap.add_argument("--corte", help="fecha de la proyeccion a conciliar (aaaa-mm-dd)")
    ap.add_argument("--etiqueta", default="")
    args = ap.parse_args()

    if args.accion == "listar":
        for s in snapshots(args.cliente):
            d = leer(s)
            print("  %s  %3d movimientos  hasta %s  %s" % (
                d["corte"], len(d["proyectados"]), d["hasta"], d.get("etiqueta", "")))
        return

    if args.accion == "guardar":
        with io.open(args.contrato, encoding="utf-8") as f:
            contrato = json.load(f)
        ruta, snap = guardar(args.cliente, contrato, dias=args.dias, etiqueta=args.etiqueta)
        print("  Guardado: %s" % ruta)
        print("  %d movimientos proyectados hasta %s" % (len(snap["proyectados"]), snap["hasta"]))
        return

    snaps = snapshots(args.cliente)
    if not snaps:
        print("  No hay ninguna proyeccion guardada todavia. Corre 'guardar' primero.")
        return

    with io.open(args.contrato, encoding="utf-8") as f:
        contrato = json.load(f)

    if args.accion == "conciliar":
        ruta = snaps[-1]
        if args.corte:
            m = [s for s in snaps if args.corte in s]
            if not m:
                print("  No hay proyeccion del %s" % args.corte)
                return
            ruta = m[0]
        imprimir_conciliacion(conciliar(leer(ruta), contrato))
        return

    if args.accion == "resumen":
        concs = [conciliar(leer(s), contrato) for s in snaps]
        imprimir_resumen(resumen(concs), len(snaps))


if __name__ == "__main__":
    main()
