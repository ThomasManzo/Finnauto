# -*- coding: utf-8 -*-
"""
simulador.proveedores — la decisión que se toma todas las semanas.

EL CAMBIO DE PREGUNTA
---------------------
Todo el motor anterior contestaba "¿me alcanza la plata?" y marcaba un día
crítico cuando la caja caía debajo de un mínimo. Thomas explicó que esa no es la
decisión que se toma:

    "La decisión que más se repite: ¿cuánto le pago a las droguerías que le debo?"

    "Si no le pagás, nada. Después de x tiempo te bloquean la compra, pero solés
     tener entre 1 y 2 o 3 semanas de tolerancia."

    "Se puede hacer, siempre y cuando nos atrasemos con las droguerías y
     corramos el riesgo de que nos bloqueen."

O sea que quedarse corto NO es un fallo: es una decisión de a quién estirar. El
límite real no es la caja mínima, es **cuánto atraso aguanta cada proveedor
antes de cortarte la compra**.

Y esto no es de farmacias. Es el patrón de cualquier PyME que se financia con
sus proveedores porque las líneas bancarias están agotadas — que es exactamente
el caso acá:

    "A los dueños les gusta más apalancarse con proveedores que con el banco."

QUÉ MODELA
----------
  · lo que vence por proveedor y por semana
  · cuánto atraso YA hay acumulado con cada uno
  · cuánta tolerancia le queda antes del bloqueo
  · qué pasa con la caja y con el atraso según a quién se le pague

QUÉ NO MODELA TODAVÍA
---------------------
La plata que baja deuda sin tocar la caja: cheques endosados, notas de crédito
de obras sociales y compensaciones. Está declarado en el catálogo pero el
exportador todavía marca todos los cobros como efecto 'caja'. Cuando ese dato
exista, entra acá sin cambiar la estructura: es un pago más, con otro origen.

Uso:
    python simulador/proveedores.py --contrato c.json --cliente maga
    python simulador/proveedores.py --contrato c.json --cliente maga --unidad SPEEDMED
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

DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]


def cargar_proveedores(cliente):
    """Tolerancia y relación comercial de cada proveedor. Sale del catálogo."""
    ruta = os.path.join(BASE_REPO, "clientes", cliente, "catalogo.json")
    with io.open(ruta, encoding="utf-8") as f:
        cat = json.load(f)
    out = {}
    for p in cat.get("proveedores", {}).get("valores", []):
        out[p["id"].upper()] = p
    return out


def _match(contraparte, proveedores):
    """De 'SUIZO ARGENTINA S.A. (00282)' a la ficha de SUIZO.

    Se busca por contención en los dos sentidos: la planilla escribe el nombre
    completo con el número de cuenta, y el catálogo lo tiene corto.
    """
    c = (contraparte or "").upper()
    for pid, p in proveedores.items():
        if pid in c or c.startswith(pid.split()[0]):
            return pid, p
    return None, None


def deuda_por_proveedor(contrato, proveedores, unidad=None, hoy=None):
    """Agrupa la deuda por proveedor, separando lo vencido de lo que viene."""
    hoy = (hoy or datetime.date.today()).isoformat()
    agg = defaultdict(lambda: {"vencido": [], "futuro": [], "credito": 0.0,
                               "sin_ficha": False})

    for x in contrato.get("deuda_droguerias", []):
        if x.get("intercompany"):
            continue
        if unidad and (x.get("unidad") or "") != unidad:
            continue
        imp = float(x.get("importe") or 0)
        cp = x.get("contraparte") or "?"

        # Las NCR y la refinanciación no son una factura con tolerancia: van
        # aparte. Meterlas en el reparto semanal daría un consejo equivocado.
        if x.get("es_credito") or imp < 0:
            pid, _ = _match(cp, proveedores)
            agg[pid or cp]["credito"] += abs(imp)
            continue
        if "REFINANC" in cp.upper():
            agg["REFINANCIACION"]["futuro" if x["fecha"] >= hoy else "vencido"].append(x)
            agg["REFINANCIACION"]["sin_ficha"] = True
            continue

        pid, p = _match(cp, proveedores)
        clave = pid or cp
        if p is None:
            agg[clave]["sin_ficha"] = True
        agg[clave]["vencido" if x["fecha"] < hoy else "futuro"].append(x)

    return agg


def semanas_de_atraso(filas_vencidas, hoy):
    """Cuántas semanas hace que hay deuda vencida sin pagar.

    Se mide desde la MÁS VIEJA: si algo vence hace tres semanas, el proveedor
    lleva tres semanas esperando, aunque después se le haya pagado algo.
    """
    if not filas_vencidas:
        return 0.0
    mas_vieja = min(x["fecha"] for x in filas_vencidas)
    dias = (hoy - datetime.date.fromisoformat(mas_vieja)).days
    return max(0.0, dias / 7.0)


def analizar(contrato, proveedores, caja, unidad=None, hoy=None, dias=21):
    hoy = hoy or datetime.date.today()
    agg = deuda_por_proveedor(contrato, proveedores, unidad, hoy)
    hasta = hoy + datetime.timedelta(days=dias)

    out = []
    for clave, d in agg.items():
        p = proveedores.get(clave, {})
        tol = p.get("tolerancia_semanas")
        atraso = semanas_de_atraso(d["vencido"], hoy)
        vence_pronto = [x for x in d["futuro"] if x["fecha"] <= hasta.isoformat()]
        out.append({
            "proveedor": clave,
            "nombre": p.get("nombre", clave),
            "vencido": sum(float(x["importe"]) for x in d["vencido"]),
            "por_vencer": sum(float(x["importe"]) for x in vence_pronto),
            "credito": d["credito"],
            "atraso_semanas": atraso,
            "tolerancia": tol,
            "margen": (tol - atraso) if tol is not None else None,
            "vence_dia": p.get("vence"),
            "compensa": p.get("compensa"),
            "sin_ficha": d["sin_ficha"],
            "proximos": sorted(vence_pronto, key=lambda x: x["fecha"])[:6],
        })
    # Primero el que menos margen le queda: es el que puede cortar la compra.
    return sorted(out, key=lambda x: (x["margen"] if x["margen"] is not None else 99,
                                      -x["vencido"]))


def cobros_de_la_semana(contrato, unidad, hoy, dias):
    """Lo que se espera cobrar en la ventana, y que se puede usar para pagar.

    Thomas: "podes tener un cobro al dia siguiente y con ese cobro decidir no
    pagarle a las droguerias y te financias con eso". Sin esto, el motor diria
    "no alcanza" con la caja de hoy y estaria mintiendo: la plata llega dentro
    de la misma semana.

    Solo cuenta lo que tiene efecto CAJA. Un cheque endosado o una nota de
    credito bajan deuda pero no sirven para pagarle a otro.
    """
    hasta = (hoy + datetime.timedelta(days=dias)).isoformat()
    h = hoy.isoformat()
    total, detalle = 0.0, defaultdict(float)
    for x in contrato.get("cobros_previstos", []):
        f = x.get("fecha")
        if not f or f < h or f > hasta:
            continue
        if x.get("interno"):
            continue
        if (x.get("efecto") or "caja") != "caja":
            continue
        if unidad and (x.get("unidad") or "") != unidad:
            continue
        v = float(x.get("importe") or 0)
        total += v
        detalle[x.get("concepto") or "?"] += v
    return total, dict(detalle)


def escenarios(analisis, caja):
    """Qué pasa con la caja según a quién se le pague.

    No propone UNA respuesta: muestra las opciones con su costo. Quién decide es
    el que se come el bloqueo, no el programa.
    """
    conTol = [a for a in analisis if a["tolerancia"] is not None]
    total = sum(a["vencido"] + a["por_vencer"] for a in conTol)
    out = [{"nombre": "Pagar todo lo que vence",
            "paga": total, "caja_queda": caja - total,
            "atrasos": [(a["proveedor"], 0.0) for a in conTol]}]

    # Pagar solo a los que están al límite es la jugada real: se cubre a quien
    # está por cortar y se estira al que todavía aguanta.
    urgentes = [a for a in conTol if a["margen"] is not None and a["margen"] <= 1]
    if urgentes and len(urgentes) < len(conTol):
        monto = sum(a["vencido"] + a["por_vencer"] for a in urgentes)
        atrasos = []
        for a in conTol:
            atrasos.append((a["proveedor"],
                            0.0 if a in urgentes else a["atraso_semanas"] + 1))
        out.append({"nombre": "Pagar solo a los que están al límite",
                    "paga": monto, "caja_queda": caja - monto, "atrasos": atrasos})

    out.append({"nombre": "No pagar nada esta semana",
                "paga": 0.0, "caja_queda": caja,
                "atrasos": [(a["proveedor"], a["atraso_semanas"] + 1) for a in conTol]})
    return out


# ------------------------------------------------------------------ salida
def imprimir(analisis, esc, caja, unidad, hoy, cobros=0.0, detalle=None, dias=7):
    detalle = detalle or {}
    L = 78
    print("=" * L)
    print("  A QUIEN LE PAGO ESTA SEMANA%s" % ("  ·  " + unidad if unidad else ""))
    print("  %s %s" % (DIAS[hoy.weekday()], hoy.strftime("%d/%m/%Y")))
    print("=" * L)
    print("  Caja hoy          : %s" % _m(caja))
    if cobros:
        print("  Cobras en %2d dias : %s" % (dias, _m(cobros)))
        print("  " + "-" * 44)
        print("  DISPONIBLE        : %s" % _m(caja + cobros))
        top = sorted(detalle.items(), key=lambda kv: -kv[1])[:4]
        print("  (%s)" % ", ".join("%s %s" % (k[:20], _m(v)) for k, v in top))
    print("")

    print("  %-16s %14s %14s %8s %9s" % ("PROVEEDOR", "VENCIDO", "POR VENCER",
                                         "ATRASO", "MARGEN"))
    print("  " + "-" * (L - 4))
    for a in analisis:
        if a["tolerancia"] is None:
            continue
        marca = ""
        if a["margen"] is not None and a["margen"] <= 0:
            marca = "  <-- YA PUEDE CORTARTE"
        elif a["margen"] is not None and a["margen"] <= 1:
            marca = "  <-- al limite"
        print("  %-16s %14s %14s %6.1f sem %5.1f sem%s" % (
            a["proveedor"][:16], _m(a["vencido"]), _m(a["por_vencer"]),
            a["atraso_semanas"], a["margen"], marca))
        if a["vence_dia"]:
            det = "vence los %s" % a["vence_dia"]
            if a["compensa"]:
                det += "  ·  compensa: %s" % a["compensa"]
            print("  %-16s %s" % ("", det))
        if a["credito"]:
            print("  %-16s tiene %s en notas de credito a favor"
                  % ("", _m(a["credito"])))

    # Los que solo aparecen por una nota de credito no son deuda: no van en la
    # lista de "fuera del reparto", que es para obligaciones reales.
    aparte = [a for a in analisis if a["tolerancia"] is None
              and (a["vencido"] or a["por_vencer"])]
    if aparte:
        print("\n  FUERA DEL REPARTO SEMANAL")
        for a in aparte:
            print("   . %-16s %14s   (no es una factura con tolerancia)"
                  % (a["proveedor"][:16], _m(a["vencido"] + a["por_vencer"])))

    print("\n" + "=" * L)
    print("  LAS OPCIONES")
    print("=" * L)
    for e in esc:
        falta = e["caja_queda"] < 0
        print("\n  %s" % e["nombre"].upper())
        print("     pagas %s   ->   te queda %s%s" % (
            _m(e["paga"]), _m(e["caja_queda"]),
            "   (NO ALCANZA)" if falta else ""))
        peor = [(p, s) for p, s in e["atrasos"] if s > 0]
        if not peor:
            print("     nadie queda atrasado")
        else:
            for p, s in sorted(peor, key=lambda x: -x[1]):
                a = [x for x in analisis if x["proveedor"] == p][0]
                riesgo = ""
                if a["tolerancia"] is not None and s >= a["tolerancia"]:
                    riesgo = "  <-- pasa la tolerancia"
                print("     %-16s queda en %.1f semanas de atraso%s" % (p, s, riesgo))

    print("\n  Ninguna de estas opciones es 'la correcta': tienen costos distintos.")
    print("  El que decide es el que se come el bloqueo.")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="A quien pagarle esta semana")
    ap.add_argument("--contrato", required=True)
    ap.add_argument("--cliente", default="maga")
    ap.add_argument("--unidad", help="MAGA o SPEEDMED (si no, las dos juntas)")
    ap.add_argument("--caja", type=float)
    ap.add_argument("--hoy", help="aaaa-mm-dd, para simular otro dia")
    ap.add_argument("--dias", type=int, default=21)
    args = ap.parse_args()

    with io.open(args.contrato, encoding="utf-8") as f:
        contrato = json.load(f)

    caja = args.caja
    if caja is None:
        por_u = contrato.get("caja_por_unidad") or {}
        caja = float(por_u.get(args.unidad) if args.unidad and por_u.get(args.unidad)
                     else contrato.get("caja_hoy") or 0)

    hoy = datetime.date.fromisoformat(args.hoy) if args.hoy else datetime.date.today()
    prov = cargar_proveedores(args.cliente)
    an = analizar(contrato, prov, caja, args.unidad, hoy, args.dias)
    cobros, detalle = cobros_de_la_semana(contrato, args.unidad, hoy, args.dias)
    disponible = caja + cobros
    imprimir(an, escenarios(an, disponible), caja, args.unidad, hoy,
             cobros, detalle, args.dias)


if __name__ == "__main__":
    main()
