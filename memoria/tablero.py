# -*- coding: utf-8 -*-
"""
memoria.tablero — lo que dijimos que iba a pasar, contra lo que pasó.

POR QUÉ ESTE MÓDULO Y NO EL QUE YA HABÍA
----------------------------------------
`memoria/registro.py` guarda movimiento por movimiento desde la solapa
MOVIMIENTOS. Sirve para medir si cada pago cayó donde se esperaba.

Pero el tablero no proyecta movimientos: proyecta **una curva de caja y un día
crítico**, desde el cashflow. Guardar una cosa y mostrar la otra sería
exactamente la mezcla de universos que ya nos costó cuatro bugs.

Y además la frase que sostiene una asesoría recurrente no es *"acertamos el
83% de los movimientos"*. Es:

    "El mes pasado te dije que el 14 quedabas corto. Quedaste el 16."

Eso es la curva y el día crítico. Por eso se guarda eso.

QUÉ SE GUARDA Y QUÉ NO
----------------------
Se guarda **lo que se le dijo al cliente**: la curva por unidad, el día
crítico, la deuda vencida del momento y el plan que se propuso. Es la promesa,
no el dato crudo — el dato crudo ya vive en el contrato.

No se guarda el contrato entero. Un snapshot por día del contrato completo son
900 KB cada uno y no agregan nada: lo que hay que poder defender después es lo
que se dijo.

CÓMO SE JUZGA
-------------
Solo lo que YA VENCIÓ. Una proyección a 45 días mirada a los 10 no se cumplió
ni se incumplió. Y el error se mide contra la **caja inicial**, no contra el
valor del día: dividir por un acumulado que arranca cerca de cero da 300% por
una diferencia de centavos y la métrica deja de decir nada.
"""

import os
import io
import sys
import json
import glob
import datetime

BASE_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)


def _dir(cliente):
    d = os.path.join(BASE_REPO, "clientes", cliente, "memoria")
    if not os.path.isdir(d):
        os.makedirs(d)
    return d


def _curva_de(proy, dias=None):
    """La curva que arma el tablero, sumando todo lo que sale."""
    caja, out = proy["caja_inicial"], []
    for d in (proy.get("dias") or [])[:dias or len(proy.get("dias") or [])]:
        caja += d["entra"] - sum(d["sale"].values())
        out.append({"fecha": d["fecha"], "caja": caja})
    return out


def guardar(cliente, paquete, etiqueta=""):
    """Congela lo que el tablero le está diciendo hoy al cliente.

    Un archivo por día. Si ya hay uno de hoy se pisa: lo que vale es lo último
    que se mostró, no cada vez que se apretó actualizar.
    """
    corte = paquete["fecha"]
    unidades = {}
    for u in paquete["unidades"]:
        d = paquete["datos"][u]
        proy = d.get("proyeccion") or {}
        curva = _curva_de(proy)
        critico = next((p for p in curva if p["caja"] < 0), None)
        plan = (d.get("planes") or {}).get("14") or {}
        unidades[u] = {
            "caja_inicial": proy.get("caja_inicial"),
            "curva": curva,
            "critico": critico,
            "minimo": min([p["caja"] for p in curva], default=None),
            "vencido": (d.get("kpis") or {}).get("vencido"),
            "plan_14": {"frase": plan.get("frase"),
                        "pasos": len(plan.get("pasos") or [])},
        }

    snap = {"version": 1, "cliente": cliente, "corte": corte,
            "hasta": (paquete["datos"][paquete["unidades"][0]]
                      .get("proyeccion") or {}).get("hasta"),
            "etiqueta": etiqueta, "unidades": unidades}

    ruta = os.path.join(_dir(cliente), "tablero_%s.json" % corte)
    with io.open(ruta, "w", encoding="utf-8") as f:
        f.write(json.dumps(snap, ensure_ascii=False, indent=2))
    return ruta, snap


def snapshots(cliente):
    return sorted(glob.glob(os.path.join(_dir(cliente), "tablero_*.json")))


def leer(ruta):
    with io.open(ruta, encoding="utf-8") as f:
        return json.load(f)


def conciliar(snap, paquete_hoy):
    """La proyección vieja contra lo que el tablero dice hoy.

    Devuelve, por unidad, qué se había dicho y qué pasó — con el desvío medido
    contra la caja inicial, que es la única base estable.
    """
    hoy = paquete_hoy["fecha"]
    out = []
    for u, viejo in (snap.get("unidades") or {}).items():
        d = (paquete_hoy.get("datos") or {}).get(u)
        if not d:
            continue
        real = _curva_de(d.get("proyeccion") or {})
        por_fecha = {p["fecha"]: p["caja"] for p in real}

        # SOLO LO QUE YA VENCIO.
        juzgables = [p for p in viejo["curva"] if p["fecha"] <= hoy]
        if not juzgables:
            out.append({"unidad": u, "dias_juzgables": 0,
                        "dijimos": viejo, "todavia_no": True})
            continue

        base = abs(viejo.get("caja_inicial") or 0) or 1.0
        desvios = []
        for p in juzgables:
            r = por_fecha.get(p["fecha"])
            if r is None:
                continue
            desvios.append(abs(r - p["caja"]) / base)
        prom = (sum(desvios) / len(desvios) * 100) if desvios else None

        crit_dicho = (viejo.get("critico") or {}).get("fecha")
        crit_real = next((p["fecha"] for p in real if p["caja"] < 0), None)

        out.append({
            "unidad": u,
            "dias_juzgables": len(juzgables),
            "desvio_promedio_pct": prom,
            "critico_dicho": crit_dicho,
            "critico_real": crit_real,
            "acerto_critico": (crit_dicho is not None and crit_real is not None
                               and abs(_dias(crit_dicho, crit_real)) <= 2),
            "dias_de_diferencia": (_dias(crit_dicho, crit_real)
                                   if crit_dicho and crit_real else None),
            "vencido_dicho": viejo.get("vencido"),
            "plan_14": (viejo.get("plan_14") or {}).get("frase"),
        })
    return {"corte": snap["corte"], "hoy": hoy, "unidades": out}


def _dias(a, b):
    try:
        return (datetime.date.fromisoformat(b) - datetime.date.fromisoformat(a)).days
    except Exception:
        return None


def en_palabras(c):
    """La frase que se dice en la visita siguiente.

    Es el activo de una asesoría recurrente: sin esto, cada visita arranca de
    cero y lo que se cobra es una foto, no una relación.
    """
    out = []
    for u in c.get("unidades") or []:
        if u.get("todavia_no"):
            out.append("%s: la proyección del %s todavía no se puede juzgar."
                       % (u["unidad"], c["corte"]))
            continue
        cd, cr = u.get("critico_dicho"), u.get("critico_real")
        if cd and cr:
            dd = u.get("dias_de_diferencia")
            if dd == 0:
                t = "el %s ibas a quedar corto, y quedaste ese mismo día" % _dm(cd)
            else:
                t = ("el %s ibas a quedar corto, y quedaste el %s (%d día%s %s)"
                     % (_dm(cd), _dm(cr), abs(dd), "" if abs(dd) == 1 else "s",
                        "después" if dd > 0 else "antes"))
        elif cd and not cr:
            t = "el %s ibas a quedar corto, y no pasó" % _dm(cd)
        elif cr and not cd:
            t = "no habíamos marcado ningún día crítico, y quedaste corto el %s" % _dm(cr)
        else:
            t = "no marcamos día crítico y no lo hubo"
        des = u.get("desvio_promedio_pct")
        if des is not None:
            t += ". La curva se desvió %.0f%% en promedio sobre %d días" % (
                des, u["dias_juzgables"])
        out.append("%s: el %s te dijimos que %s." % (u["unidad"], _dm(c["corte"]), t))
    return out


def _dm(iso):
    return iso[8:10] + "/" + iso[5:7] if iso and len(iso) >= 10 else str(iso)
