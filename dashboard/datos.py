# -*- coding: utf-8 -*-
"""
dashboard.datos — todo lo que la app necesita, calculado en Python.

LA REGLA QUE ORDENA ESTE ARCHIVO
--------------------------------
**La plata se calcula acá. El HTML solo muestra.**

Es tentador hacer la calculadora de retiro en JavaScript: son cuatro sumas. El
problema es que a la semana siguiente hay dos motores —uno en Python con 202
tests y otro en el navegador sin ninguno— y se despegan sin que nadie se
entere. El día que cambie la regla del retiro, cambia en un solo lugar.

Por eso este módulo devuelve **números ya resueltos**, para cada empresa y para
cada ventana. La app cambia de solapa y de empresa moviendo objetos, no
recalculando.

QUÉ DEVUELVE
------------
    {cliente, fecha, unidades: [...], datos: {UNIDAD: {...}}, hallazgos: [...]}

donde cada UNIDAD trae kpis, el puente, los proveedores ordenados por urgencia,
las próximas salidas, los escenarios y la tabla del retiro por ventana.
"""

import os
import sys
import datetime
import html
from collections import defaultdict

BASE_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)

from simulador import disponibilidad as D
from simulador import posicion as POS
from simulador import proveedores as PROV

# Las ventanas que ofrece la calculadora. Se precalculan todas para que mover
# el selector sea instantáneo y no haya aritmética en el navegador.
VENTANAS = [7, 14, 30, 45]

GRUPO = "GRUPO"


def esc(t):
    return html.escape(str(t if t is not None else ""))


def _unidad_real(u):
    """'GRUPO' significa 'sin filtrar', que es como lo entiende el motor."""
    return None if u == GRUPO else u


def kpis(contrato, unidad, dias=7):
    u = _unidad_real(unidad)
    r = D.retiro(contrato, dias=dias, unidad=u)
    p = r["puente"]
    return {
        "caja": p["caja"],
        "efectivo_sin_asignar": p.get("efectivo_sin_asignar") or 0,
        "vencido": r["vencido"],
        "por_vencer": r["por_vencer_en_ventana"],
        "margen": r["margen"],
        "se_puede": r["se_puede"],
        "falta": r["falta_para_cubrir"],
        "tapa_una_pared": r["tapa_una_pared"],
    }


def puente(contrato, unidad, dias):
    p = D.puente(contrato, dias=dias, unidad=_unidad_real(unidad),
                 con_droguerias=D.VENCIDO)
    return {
        "caja": p["caja"],
        "entra": [{"nombre": n, "monto": v, "seguro": s} for n, v, s in p["cobros"]],
        "sale": [{"nombre": n.strip(" -"), "monto": v} for n, v, _ in p["pagos"]],
        "entra_seguro": p["entra_seguro"],
        "total_sale": p["sale"],
        "queda": p["proyectada_seguro"],
        "cheques": p["entra_todo"] - p["entra_seguro"],
        "cobranza_vencida": p["cobranza_vencida"],
    }


def proveedores(contrato, unidad, cliente, hoy, dias=21):
    try:
        fichas = PROV.cargar_proveedores(cliente)
    except Exception:
        fichas = {}
    u = _unidad_real(unidad)
    caja = float(contrato.get("caja_hoy") or 0)
    if u:
        caja = float((contrato.get("caja_por_unidad") or {}).get(u) or 0)
    an = PROV.analizar(contrato, fichas, caja, u,
                       datetime.date.fromisoformat(hoy), dias)
    out = []
    for a in an:
        # Las notas de credito no son un proveedor.
        #
        # analizar() les da su propia clave cuando el rotulo no matchea ninguna
        # ficha, y asi "NCR DDS" aparecia como si fuera una drogueria a la que
        # se le debe. Es una fila que baja deuda, no una contraparte: si no
        # tiene nada vencido ni por vencer, no va en la tabla de a quien pagar.
        if not (a["vencido"] or a["por_vencer"]):
            continue
        out.append({
            "nombre": a["nombre"],
            "vencido": a["vencido"],
            "por_vencer": a["por_vencer"],
            "total": a["vencido"] + a["por_vencer"],
            "credito": a["credito"],
            "atraso": a["atraso_semanas"],
            "tolerancia": a["tolerancia"],
            "margen": a["margen"],
            "vence_dia": a["vence_dia"],
            "sin_ficha": a["sin_ficha"],
            "proximos": [{"fecha": x["fecha"], "monto": float(x["importe"])}
                         for x in a["proximos"]],
        })
    return out


def salidas(contrato, unidad, hoy, dias=15, tope=12):
    """Lo que sale en los próximos días, día por día.

    Es la vista que ya tenía Thomas en su dash ("próximas salidas importantes")
    y es la que se mira antes de decir que sí a algo.
    """
    u = _unidad_real(unidad)
    hasta = (datetime.date.fromisoformat(hoy)
             + datetime.timedelta(days=dias)).isoformat()
    filas = []
    for x in contrato.get("egresos_cashflow", []):
        if x.get("intercompany"):
            continue
        if u and (x.get("unidad") or "") != u:
            continue
        f = x.get("fecha") or ""
        if not (hoy <= f <= hasta):
            continue
        filas.append({"fecha": f, "detalle": (x.get("contraparte") or "?").strip(),
                      "monto": float(x.get("importe") or 0),
                      "unidad": x.get("unidad") or ""})
    filas.sort(key=lambda x: (x["fecha"], -x["monto"]))
    return filas[:tope]


def gastos_del_periodo(contrato, unidad, hoy, dias=45, tope=9):
    """Los egresos agrupados por concepto: en qué se va la plata."""
    u = _unidad_real(unidad)
    hasta = (datetime.date.fromisoformat(hoy)
             + datetime.timedelta(days=dias)).isoformat()
    agg = defaultdict(float)
    for x in contrato.get("egresos_cashflow", []):
        if x.get("intercompany"):
            continue
        if u and (x.get("unidad") or "") != u:
            continue
        f = x.get("fecha") or ""
        if not (hoy <= f <= hasta):
            continue
        agg[(x.get("contraparte") or "?").strip()] += float(x.get("importe") or 0)
    filas = sorted(agg.items(), key=lambda kv: -kv[1])
    top = [{"nombre": k, "monto": v} for k, v in filas[:tope]]
    resto = sum(v for _, v in filas[tope:])
    if resto:
        top.append({"nombre": "Otros (%d conceptos)" % (len(filas) - tope),
                    "monto": resto})
    return top


def retiro_por_ventana(contrato, unidad):
    """La tabla que hace funcionar la calculadora sin recalcular en el navegador."""
    u = _unidad_real(unidad)
    out = {}
    for d in VENTANAS:
        r = D.retiro(contrato, dias=d, unidad=u)
        out[str(d)] = {
            "caja": r["puente"]["caja"],
            "entra": r["puente"]["entra_seguro"],
            "sale": r["puente"]["sale"],
            "vencido": r["vencido"],
            "por_vencer": r["por_vencer_en_ventana"],
            "margen": r["margen"],
            "margen_pagando_todo": r["margen_pagando_todo"],
            "tapa_una_pared": r["tapa_una_pared"],
        }
    return out

# ------------------------------------------------------------------ hallazgos
def hallazgos(contrato):
    """Lo que se encontró mirando los datos del cliente.

    Se calculan sobre el contrato, no se escriben a mano: si el cliente arregla
    una de estas cosas, el hallazgo desaparece solo del informe. Un hallazgo
    hardcodeado sobrevive a su propia solución y hace quedar mal.
    """
    out = []
    hoy = D.hoy_de(contrato)

    # 1. Referencias que apuntan a una columna de FECHA vieja del cashflow.
    #
    # FALSO POSITIVO REAL (06/09/2026): la primera version marcaba cualquier
    # celda de columna A/B/C, y saco como hallazgo que "Caja hoy apunta a
    # SALDOS!C26". SALDOS no es un cashflow: sus columnas son bancos, no fechas,
    # y C26 es el total correcto. Un informe que le dice al cliente que algo
    # esta mal cuando esta bien vale menos que no decir nada -- destruye la
    # confianza en los hallazgos que SI son ciertos.
    #
    # Por eso ahora se exige que la hoja apuntada sea un cashflow: son las
    # unicas donde una columna equivale a un dia.
    def _es_cashflow(n):
        n = str(n or "").lower()
        return "cash" in n and "flow" in n

    for hoja, filas in (contrato.get("referencias_del_cliente") or {}).items():
        for f in filas:
            for a in (f.get("apunta_a") or []):
                cel = str(a.get("celda") or "")
                col = "".join(c for c in cel if c.isalpha())
                if (_es_cashflow(a.get("hoja")) and len(col) == 1
                        and col <= "C" and a.get("rotulo")):
                    out.append({
                        "titulo": "Tu “%s” mira una fecha vieja" % esc(hoja),
                        "cuerpo": ("La celda de <b>%s</b> apunta a <code>%s!%s</code>, "
                                   "que es la fila “%s” en la <b>primera columna</b> "
                                   "del cashflow. No es el saldo de hoy: es el del "
                                   "comienzo del período cargado."
                                   % (esc(f.get("etiqueta")), esc(a.get("hoja")),
                                      esc(cel), esc(a.get("rotulo")))),
                        "monto": None})
                    break
            else:
                continue
            break

    # 2. NCR que no bajan la deuda en la planilla del cliente.
    ncr = sum(abs(float(x.get("importe") or 0))
              for x in contrato.get("deuda_droguerias", [])
              if x.get("es_credito"))
    if ncr:
        out.append({
            "titulo": "Tu planilla muestra más deuda de la que tenés",
            "cuerpo": ("Las notas de crédito están cargadas como ingreso en otra "
                       "fila, pero <b>nunca se descuentan del saldo con la "
                       "droguería</b>. La deuda que ves está inflada en ese monto."),
            "monto": ncr})

    # 3. Cartera de cheques que no pasa por el banco.
    ch = contrato.get("cartera_cheques") or []
    endos = sum(abs(float(c.get("importe") or 0)) for c in ch
                if "ENDOS" in str(c.get("estado") or "").upper())
    total = sum(abs(float(c.get("importe") or 0)) for c in ch)
    if total and endos / total > 0.2:
        out.append({
            "titulo": "%d%% de tus cheques no pasan por el banco" % round(100 * endos / total),
            "cuerpo": ("De la cartera de cheques, esa parte se <b>endosa</b>: no "
                       "entra un peso a la cuenta, baja deuda con una droguería. "
                       "Contarlos como caja infla cualquier proyección."),
            "monto": endos})

    # 4. Cobranza a droguerías que venció y no entró.
    venc = sum(float(x.get("importe") or 0)
               for x in contrato.get("cuentas_a_cobrar_droguerias", [])
               if not x.get("intercompany") and (x.get("fecha") or "") < hoy)
    if venc:
        out.append({
            "titulo": "Cobranza que venció y no entró",
            "cuerpo": ("Plata que te deben con fecha ya pasada. No está contada "
                       "como segura en ningún número de este informe: si entra, "
                       "todo mejora; darla por hecha sería engañarse."),
            "monto": venc})
    return out



def ingresos_por_dia(contrato, unidad, hoy, dias=30):
    """Lo que entra, día por día y separado por fuente.

    Es el gráfico que Thomas ya tenía en su tablero de Apps Script y el único
    que muestra el RITMO del negocio: un total mensual no dice que el 07 entra
    PAMI y el resto del mes se vive de mostrador.
    """
    u = _unidad_real(unidad)
    hasta = (datetime.date.fromisoformat(hoy)
             + datetime.timedelta(days=dias)).isoformat()
    por_dia = {}
    fuentes = {}
    for x in contrato.get("cobros_previstos", []):
        if x.get("interno"):
            continue
        if u and (x.get("unidad") or "") != u:
            continue
        f = x.get("fecha") or ""
        if not (hoy <= f <= hasta):
            continue
        con = (x.get("concepto") or "?").strip()
        por_dia.setdefault(f, {})
        por_dia[f][con] = por_dia[f].get(con, 0.0) + float(x.get("importe") or 0)
        fuentes[con] = fuentes.get(con, 0.0) + float(x.get("importe") or 0)

    orden = [k for k, _ in sorted(fuentes.items(), key=lambda kv: -kv[1])]
    dias_ord = sorted(por_dia)
    return {
        "fuentes": orden,
        "dias": [{"fecha": f, "valores": [por_dia[f].get(k, 0.0) for k in orden],
                  "total": sum(por_dia[f].values())} for f in dias_ord],
    }


def a_cobrar(contrato, unidad, hoy, dias=45):
    """Lo que nos deben: vencido, por vencer, y por contraparte.

    OJO CON EL SENTIDO: MAGA le COMPRA a las droguerías. Esta vista es de
    Speedmed, que les compra Y les vende. Confundir las dos puntas fue el error
    más caro del proyecto.
    """
    u = _unidad_real(unidad)
    hasta = (datetime.date.fromisoformat(hoy)
             + datetime.timedelta(days=dias)).isoformat()
    agg = defaultdict(lambda: {"vencido": 0.0, "por_vencer": 0.0})
    venc = fut = 0.0
    for x in contrato.get("cuentas_a_cobrar_droguerias", []):
        if x.get("intercompany"):
            continue
        if u and (x.get("unidad") or "") != u:
            continue
        f = x.get("fecha") or ""
        v = float(x.get("importe") or 0)
        cp = (x.get("contraparte") or "?").strip()
        if f and f < hoy:
            agg[cp]["vencido"] += v
            venc += v
        elif hoy <= f <= hasta:
            agg[cp]["por_vencer"] += v
            fut += v
    filas = [{"nombre": k, "vencido": v["vencido"], "por_vencer": v["por_vencer"],
              "total": v["vencido"] + v["por_vencer"]}
             for k, v in agg.items()]
    filas.sort(key=lambda x: -x["total"])

    ch = []
    for c in contrato.get("cartera_cheques", []):
        f = c.get("fecha") or ""
        est = str(c.get("estado") or "").upper()
        if est == "ANULADO" or not (hoy <= f <= hasta):
            continue
        ch.append({"fecha": f, "importe": abs(float(c.get("importe") or 0)),
                   "librador": (c.get("librador") or "").strip()[:40],
                   "estado": est})
    ch.sort(key=lambda x: (x["fecha"], -x["importe"]))
    return {"filas": filas, "vencido": venc, "por_vencer": fut,
            "cheques": ch[:20],
            "cheques_total": sum(c["importe"] for c in ch)}


def proyeccion(contrato, unidad, hoy, dias=45):
    """La curva de caja día por día, y el primer día en rojo.

    Es lo único que contesta "¿qué día me quedo corto?" en vez de "¿cómo cierro
    el período?". Un dueño no mira el final del período: mira el martes.
    """
    from simulador import proyeccion as PR
    u = _unidad_real(unidad)
    caja = float(contrato.get("caja_hoy") or 0)
    if u:
        caja = float((contrato.get("caja_por_unidad") or {}).get(u) or 0)

    sub = dict(contrato)
    if u:
        sub["movimientos"] = [x for x in contrato.get("movimientos", [])
                              if (x.get("unidad") or "") == u]
        sub["cobros_previstos"] = [x for x in contrato.get("cobros_previstos", [])
                                   if (x.get("unidad") or "") == u]
    try:
        r = PR.proyectar_caja(sub, datetime.date.fromisoformat(hoy), dias,
                              caja_inicial=caja)
    except Exception as e:
        return {"error": str(e), "curva": []}

    critico = None
    for p in r["curva"]:
        if p["caja"] < 0:
            critico = p
            break
    return {"desde": r["desde"], "hasta": r["hasta"], "caja_inicial": r["caja_inicial"],
            "curva": r["curva"], "critico": critico,
            "total_ingresos": r["total_ingresos"], "total_egresos": r["total_egresos"],
            "minimo": min([p["caja"] for p in r["curva"]] or [0]),
            "final": r["curva"][-1]["caja"] if r["curva"] else caja}


def memoria_del_cliente(cliente):
    """Qué se proyectó antes y si se cumplió.

    Es el activo de una asesoría recurrente: "el mes pasado te dije que el 25
    quedabas corto". Sin esto, cada visita arranca de cero.
    """
    try:
        from memoria import registro as MEM
        rutas = MEM.snapshots(cliente)
    except Exception:
        return {"snapshots": [], "conciliadas": 0}
    out = []
    for ruta in rutas:
        try:
            d = MEM.leer(ruta)
            out.append({"corte": d.get("corte"), "hasta": d.get("hasta"),
                        "etiqueta": d.get("etiqueta") or "",
                        "movimientos": len(d.get("proyectados") or []),
                        "caja_hoy": d.get("caja_hoy")})
        except Exception:
            continue
    return {"snapshots": out, "conciliadas": 0}


def armar(contrato, cliente="maga"):
    hoy = D.hoy_de(contrato)
    us = POS.unidades(contrato)
    unidades = [GRUPO] + us if len(us) > 1 else us

    _, escen = POS.calcular(contrato, dias=45)
    esc_por_unidad = {}
    for u in unidades:
        if u == GRUPO:
            esc_por_unidad[u] = [{"nombre": f["escenario"], "monto": f["total"],
                                  "usa": "<<" in f["escenario"]} for f in escen]
        else:
            esc_por_unidad[u] = [{"nombre": f["escenario"],
                                  "monto": f["por_unidad"].get(u, 0.0),
                                  "usa": "<<" in f["escenario"]} for f in escen]

    datos = {}
    for u in unidades:
        datos[u] = {
            "kpis": kpis(contrato, u),
            "puente": puente(contrato, u, 45),
            "proveedores": proveedores(contrato, u, cliente, hoy),
            "salidas": salidas(contrato, u, hoy),
            "gastos": gastos_del_periodo(contrato, u, hoy),
            "escenarios": esc_por_unidad[u],
            "retiro": retiro_por_ventana(contrato, u),
            "ingresos_dia": ingresos_por_dia(contrato, u, hoy),
            "a_cobrar": a_cobrar(contrato, u, hoy),
            "proyeccion": proyeccion(contrato, u, hoy),
        }

    return {
        "cliente": contrato.get("cliente") or "finauto",
        "fecha": hoy,
        "generado": contrato.get("generado"),
        "unidades": unidades,
        "ventanas": VENTANAS,
        "datos": datos,
        "hallazgos": hallazgos(contrato),
        "memoria": memoria_del_cliente(cliente),
    }
