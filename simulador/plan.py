# -*- coding: utf-8 -*-
"""
simulador.plan — qué es lo MÍNIMO que hay que patear para llegar.

EL SALTO DE TABLERO A ASESOR
----------------------------
El tablero contesta *"el 14/09 quedás en rojo"*. Eso ya es más de lo que tiene
la mayoría. Pero la pregunta que sigue —y la única que se paga— es **"¿y qué
hago?"**.

Thomas, 06/09/2026: *"esta solapa lo que te tiene que mostrar es qué puedo
hacer para llegar bien, qué obligaciones tengo que patear"*.

Este módulo lo contesta: busca el conjunto **más chico y más barato** de pagos a
correr para que la caja no se dé vuelta, y dice **cuánto cuesta** hacerlo.

POR QUÉ NO ES "EL MÁS GRANDE PRIMERO"
-------------------------------------
Patear el pago más grande siempre alcanza, y casi siempre es la peor idea. Lo
que importa no es cuánto libera sino **qué rompe**:

  · un retiro de socios se corre sin consecuencia externa
  · la refi se corre hasta el mes siguiente y no te bloquea la compra
  · una droguería te corta el suministro si te pasás de su tolerancia
  · un cheque no se puede correr: rebota, y eso no es un escenario permitido

Entonces el orden es **por consecuencia, no por monto** — y esa es exactamente
la lógica que Thomas ya tenía en la cabeza y que no está en ninguna planilla.

Y el costo se dice siempre. Un plan que dice "llegás" sin decir "a costa de
tres semanas de atraso con Cofaloza" no es un consejo: es una trampa.
"""

import os
import sys
import datetime
from collections import defaultdict

BASE_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)


# Cuánto cuesta correr cada cosa, de menos a más. Es el orden en que se
# proponen. Los que no están acá NO se proponen nunca.
#
# Sale del catálogo del cliente cuando está; esto es el default y el ejemplo
# de qué forma tiene.
COSTO = [
    ("socios", 0, "Es una decisión de los dueños, no una obligación con un tercero."),
    ("refi", 1, "Se puede correr hasta el vencimiento del mes siguiente."),
    ("impuestos", 2, "Se corre unos días, con recargo."),
    ("droguerias", 3, "Acumula atraso, y pasada la tolerancia te bloquean la compra."),
]

# Lo que NO se toca. Está separado y explícito porque es una regla dura del
# negocio, no una preferencia: "un cheque no puede rebotar, no es un escenario
# que se permite".
INTOCABLE = {"mercaderia": "Un cheque no puede rebotar.",
             "sueldos": "Los sueldos no se corren."}


def _curva(caja_inicial, dias, sale_por_dia):
    caja, out = caja_inicial, []
    for d in dias:
        caja += d["entra"] - sale_por_dia.get(d["fecha"], 0.0)
        out.append({"fecha": d["fecha"], "caja": caja})
    return out


def _primer_rojo(curva):
    for p in curva:
        if p["caja"] < 0:
            return p
    return None


def armar(proyeccion, dias=None, proveedores=None, costos=None):
    """El plan mínimo para que la caja no se dé vuelta.

    Devuelve qué patear, en qué orden, y qué cuesta. Si no hace falta patear
    nada, lo dice. Si aun pateando todo lo pateable no alcanza, también — y eso
    es una respuesta, no un error: significa que el problema no se arregla
    corriendo pagos.
    """
    todos = proyeccion.get("dias") or []
    dias = min(dias or len(todos), len(todos))
    ventana = todos[:dias]
    if not ventana:
        return {"hace_falta": False, "pasos": [], "motivo": "sin datos"}
    hasta = ventana[-1]["fecha"]
    items = [i for i in (proyeccion.get("items") or []) if i["fecha"] <= hasta]

    base = defaultdict(float)
    for i in items:
        base[i["fecha"]] += i["monto"]

    curva = _curva(proyeccion["caja_inicial"], ventana, base)
    rojo = _primer_rojo(curva)
    if not rojo:
        return {"hace_falta": False, "pasos": [], "curva": curva,
                "motivo": "la caja no se da vuelta en la ventana"}

    orden = {g: (n, txt) for n, (g, _, txt) in enumerate(costos or COSTO)}

    # SOLO SIRVE PATEAR LO QUE CAE ANTES DEL DIA EN QUE FALTA.
    #
    # Correr un pago del 30 no ayuda a llegar al 14: la plata falta antes. Es
    # la regla dura que ya estaba en el catálogo y la que hace que el plan sea
    # corto en vez de una lista de todo lo pateable.
    #
    # OJO: el filtro por fecha va DENTRO del bucle, no acá. Al patear algo, el
    # día rojo se corre hacia adelante, y con el filtro fijo los pagos de esos
    # días nuevos no entraban nunca: el plan se quedaba masticando movimientos
    # chicos del primer tramo y terminaba diciendo "no alcanza" cuando sí
    # alcanzaba.
    candidatos = [i for i in items if i["grupo"] in orden]

    # UN PLAN DE 30 MOVIMIENTOS NO ES UN PLAN.
    #
    # La primera version ordenaba de mas barato a mas caro y agregaba hasta que
    # la curva se despejara. Correcto y, en la practica, inservible: para llegar
    # a 14 dias proponia patear 30 cosas -- todos los retiros y todos los
    # impuestos, que son chicos, antes de tocar una sola drogueria.
    #
    # Nadie hace eso. Un CFO patea uno o dos pagos grandes, no treinta chicos.
    #
    # Entonces en cada vuelta se busca EL PAGO MAS BARATO QUE POR SI SOLO
    # RESUELVA el faltante; si ninguno alcanza, se toma el mas grande del nivel
    # mas barato y se vuelve a mirar. El plan sale de dos o tres pasos y sigue
    # prefiriendo lo que menos rompe.
    # EL TOPE NO ES LO MISMO QUE "NO ALCANZA", y confundirlos cambia la
    # conclusion. "No se arregla pateando pagos" manda a conseguir plata;
    # "el plan se corto en 10 pasos" manda a mirar la lista. Se distinguen.
    TOPE = 10
    pateados, pasos = [], []
    while rojo and len(pasos) < TOPE:
        falta = -rojo["caja"]
        libres = [c for c in candidatos
                  if c not in pateados and c["fecha"] <= rojo["fecha"]]
        if not libres:
            break
        solos = [c for c in libres if c["monto"] >= falta]
        if solos:
            solos.sort(key=lambda i: (orden[i["grupo"]][0], i["monto"]))
            elegido = solos[0]
        else:
            libres.sort(key=lambda i: (orden[i["grupo"]][0], -i["monto"]))
            elegido = libres[0]

        pateados.append(elegido)
        pasos.append(dict(elegido, motivo=orden[elegido["grupo"]][1]))
        nueva = defaultdict(float, base)
        for p in pateados:
            nueva[p["fecha"]] -= p["monto"]
        curva = _curva(proyeccion["caja_inicial"], ventana, nueva)
        rojo = _primer_rojo(curva)

    return {
        "hace_falta": True,
        "alcanza": rojo is None,
        "corto_por_tope": rojo is not None and len(pasos) >= TOPE,
        "pasos": pasos,
        "curva": curva,
        "libera": sum(p["monto"] for p in pasos),
        "sigue_rojo": rojo,
        "costo": costo_del_plan(pasos, proveedores or {}),
        "intocable": [{"grupo": g, "por_que": t} for g, t in INTOCABLE.items()
                      if any(i["grupo"] == g for i in items)],
    }


def costo_del_plan(pasos, proveedores):
    """Qué cuesta el plan, en el idioma de cada contraparte.

    Un plan que dice "llegás" sin decir a costa de qué no es un consejo. Para
    una droguería el costo son semanas de atraso, y contra su tolerancia se ve
    si el plan la deja al borde del corte.
    """
    por_prov = defaultdict(lambda: {"monto": 0.0, "resumenes": [], "ficha": None})
    otros = defaultdict(float)
    for p in pasos:
        if p["grupo"] == "droguerias":
            # SE USA EL MATCH DEL MOTOR, que ya sabe que "Dds" y "DROG.DEL SUD
            # S.A (0013)" son la misma drogueria. Un match propio aca daba
            # "Dds" sin ficha y "?" cuando el rotulo no traia separador: el
            # plan decia a quien patear con un nombre que no existe.
            from simulador import proveedores as _P
            crudo = p["concepto"].split("·")[-1].strip()
            pid, ficha = _P._match(crudo, proveedores or {})
            nom = (ficha or {}).get("nombre") or pid or crudo or "sin identificar"
            por_prov[nom]["monto"] += p["monto"]
            por_prov[nom]["resumenes"].append(p["fecha"])
            por_prov[nom]["ficha"] = ficha
        else:
            otros[p["grupo"]] += p["monto"]

    out = []
    for nom, d in por_prov.items():
        d["resumenes"].sort()
        tol = (d.get("ficha") or {}).get("tolerancia_semanas")
        out.append({"quien": nom, "monto": d["monto"],
                    "resumenes": d["resumenes"],
                    "tolerancia_semanas": tol,
                    "tipo": "drogueria"})
    for g, v in otros.items():
        out.append({"quien": g, "monto": v, "tipo": g})
    out.sort(key=lambda x: -x["monto"])
    return out


def en_palabras(plan):
    """El plan en una frase, que es como se cuenta en una reunión."""
    if not plan.get("hace_falta"):
        return "No hace falta patear nada: la caja no se da vuelta en la ventana."
    if not plan.get("alcanza"):
        f = (plan.get("sigue_rojo") or {}).get("fecha", "")
        if plan.get("corto_por_tope"):
            return ("Con los %d movimientos mas convenientes todavia no alcanza: la "
                    "caja se da vuelta el %s. Hay que patear mas cosas de las que "
                    "entra en un plan corto, o cobrar antes."
                    % (len(plan["pasos"]), f))
        return ("Aun corriendo TODO lo que se puede correr, la caja igual se da "
                "vuelta el %s. Esto no se arregla pateando pagos: hay que cobrar "
                "antes o poner plata." % f)
    partes = []
    for c in plan["costo"]:
        if c["tipo"] == "drogueria":
            t = "%s (%s)" % (c["quien"], ", ".join(
                f[8:10] + "/" + f[5:7] for f in c["resumenes"]))
        else:
            t = c["quien"]
        partes.append(t)
    return "Corriendo %s llegás. Son %d movimiento(s) por %s." % (
        " y ".join(partes), len(plan["pasos"]),
        format(int(round(plan["libera"])), ",d").replace(",", "."))
