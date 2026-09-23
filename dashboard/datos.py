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
import io
import json
import sys
import datetime
import html
from decimal import Decimal
from collections import defaultdict, OrderedDict

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


# ---------------------------------------------------------------- el modo del vencido
# DOS FORMAS DE TRATAR LO QUE YA VENCIO.
#
# "dia_1" (MAGA): lo vencido entra a la curva HOY. Las droguerias cortan la
# compra manana si no cobran, asi que la deuda vencida es una salida inmediata.
#
# "stock" (NAVAR, la dirección 17/09/2026): "esta gente tiene deuda hace mucho
# tiempo, no tiene sentido que la paguen toda de una. Lo mas facil seria
# calcular las salidas proyectadas y cuanto te queda de caja libre vs la deuda,
# para ver cuanto y que podes pagar sin comprometer las obligaciones futuras".
# La curva lleva solo lo comprometido con fecha; lo vencido es un STOCK que se
# muestra aparte, y de la caja libre sale "cuanto podes pagar y a quien".
#
# Se elige en clientes/<cliente>/perfil.json -> "vencido": {"modo": "stock"}.
DIA_1, STOCK = "dia_1", "stock"


def modo_vencido(cliente):
    try:
        from nucleo import config as _config
        perfil = _config.cargar_perfil(BASE_REPO, cliente)
        return (perfil.get("vencido") or {}).get("modo") or DIA_1
    except Exception:
        return DIA_1


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


def puente(contrato, unidad, dias, modo=DIA_1):
    p = D.puente(contrato, dias=dias, unidad=_unidad_real(unidad),
                 con_droguerias=D.NADA if modo == STOCK else D.VENCIDO)
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
        # La refinanciacion NO es una drogueria. la dirección fue explicito: "no tiene
        # nada que ver con las droguerias". Va en su propia linea del tablero,
        # no mezclada en la tabla de a quien pagarle.
        if "REFINANC" in str(a["proveedor"]).upper():
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
            "atraso_desde": a.get("atraso_desde"),
            "resumenes": a.get("resumenes") or [],
            "restos_ignorados": a.get("restos_ignorados") or [],
            "proximos": [{"fecha": x["fecha"], "monto": float(x["importe"])}
                         for x in a["proximos"]],
        })
    return out


def refinanciacion(contrato, unidad, hoy, dias=45):
    """La refi, aparte: es obligacion pero no tiene tolerancia de proveedor."""
    u = _unidad_real(unidad)
    hasta = (datetime.date.fromisoformat(hoy)
             + datetime.timedelta(days=dias)).isoformat()
    venc = fut = 0.0
    cuotas = []
    for x in contrato.get("deuda_droguerias", []):
        if "REFINANC" not in str(x.get("contraparte") or "").upper():
            continue
        if u and (x.get("unidad") or "") != u:
            continue
        f = x.get("fecha") or ""
        v = float(x.get("importe") or 0)
        if f and f < hoy:
            venc += v
        elif hoy <= f <= hasta:
            fut += v
        else:
            continue
        cuotas.append({"fecha": f, "monto": v, "vencida": f < hoy})
    cuotas.sort(key=lambda c: c["fecha"])
    return {"vencido": venc, "por_vencer": fut, "cuotas": cuotas}


def salidas(contrato, unidad, hoy, dias=15, tope=12):
    """Lo que sale en los próximos días, día por día.

    Es la vista que ya tenía la dirección en su dash ("próximas salidas importantes")
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


def gastos_del_periodo(contrato, unidad, hoy, dias=45, tope=8, cliente="maga"):
    """En que se va la plata, con las droguerias adentro.

    la dirección: "grafico de gastos: droguerias suizo dds y cofa, cual suma mas, un
    grafico de barras; pago de mercaderia, otros gastos".

    Lo importante es que las DROGUERIAS ENTREN. Antes este grafico salia solo
    del bloque de egresos del cashflow, donde la deuda con droguerias no esta:
    mostraba "en que se te va la plata" sin el gasto mas grande que hay.
    """
    from simulador import disponibilidad as D
    u = _unidad_real(unidad)
    hasta = (datetime.date.fromisoformat(hoy)
             + datetime.timedelta(days=dias)).isoformat()
    # Se guarda el detalle ademas del total: sin eso la barra dice "cuanto" pero
    # no "de que", y la primera pregunta frente a una barra grande es de que
    # esta hecha.
    agg = defaultdict(float)
    det = defaultdict(list)

    for x in contrato.get("egresos_cashflow", []):
        if x.get("intercompany"):
            continue
        if u and (x.get("unidad") or "") != u:
            continue
        f = x.get("fecha") or ""
        if not (hoy <= f <= hasta):
            continue
        k = (x.get("contraparte") or "?").strip()
        agg[k] += float(x.get("importe") or 0)
        det[k].append({"fecha": f, "concepto": k,
                       "monto": float(x.get("importe") or 0)})

    # Las droguerias, una barra por cada una y con su nombre.
    from simulador import proveedores as PROV
    try:
        # Los proveedores son del cliente que se esta mirando, no de MAGA.
        # (Estaba fijo en "maga" y con el segundo cliente cargaba las
        # droguerias de MAGA para clasificar una yerbatera.)
        fichas = PROV.cargar_proveedores(cliente)
    except Exception:
        fichas = {}
    for x in contrato.get("deuda_droguerias", []):
        if x.get("intercompany") or x.get("es_credito"):
            continue
        if u and (x.get("unidad") or "") != u:
            continue
        f = x.get("fecha") or ""
        if not f or f > hasta:
            continue
        v = float(x.get("importe") or 0)
        if v <= 0:
            continue
        cp = (x.get("contraparte") or "?").strip()
        if "REFINANC" in cp.upper():
            agg["Refinanciacion"] += v
            det["Refinanciacion"].append(
                {"fecha": f, "concepto": "Cuota del " + f[8:10] + "/" + f[5:7],
                 "monto": v})
            continue
        pid, ficha = PROV._match(cp, fichas)
        k = (ficha or {}).get("nombre") or pid or cp
        agg[k] += v
        det[k].append({"fecha": f, "concepto": "Resumen del " + f[8:10] + "/" + f[5:7],
                       "monto": v})

    filas = sorted(agg.items(), key=lambda kv: -kv[1])
    top = [{"nombre": k, "monto": v,
            "detalle": sorted(det[k], key=lambda d: d["fecha"])} for k, v in filas[:tope]]
    resto = sum(v for _, v in filas[tope:])
    if resto:
        sueltos = []
        for k, _ in filas[tope:]:
            sueltos.append({"fecha": "", "concepto": k, "monto": agg[k]})
        top.append({"nombre": "Otros gastos (%d conceptos)" % (len(filas) - tope),
                    "monto": resto,
                    "detalle": sorted(sueltos, key=lambda d: -d["monto"])})
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

    # 5. Lo que el lector dejó afuera a propósito (filas "REVISAR:" de la planilla:
    #    deuda vieja, cheques que Tango sigue mostrando pendientes, etc.). Viene
    #    armado desde el lector porque solo él sabe el motivo; acá solo se muestra.
    for h in contrato.get("hallazgos_del_lector") or []:
        if h.get("titulo"):
            out.append({"titulo": esc(h["titulo"]), "cuerpo": esc(h.get("cuerpo") or ""),
                        "monto": h.get("monto")})
    return out



def ingresos_por_dia(contrato, unidad, hoy, dias=30):
    """Misma cobranza que la curva; los días sin dato quedan visibles en cero.

    Las facturas estaban fuera del gráfico porque solo se leían movimientos.
    Los cheques se muestran aparte: depositar o endosar sigue siendo una decisión.
    """
    u = _unidad_real(unidad)
    desde = datetime.date.fromisoformat(hoy)
    fechas = [(desde + datetime.timedelta(days=i)).isoformat() for i in range(dias)]
    por_dia = {f: defaultdict(float) for f in fechas}
    for lista in ("cobros_previstos", "cuentas_a_cobrar_droguerias"):
        for x in contrato.get(lista, []):
            if x.get("interno") or x.get("intercompany") or (u and x.get("unidad") != u):
                continue
            f = x.get("fecha")
            if f not in por_dia:
                continue
            con = (x.get("concepto") or "Otros ingresos").strip()
            if "CARTERA" in con.upper():
                continue
            if lista == "cuentas_a_cobrar_droguerias":
                con = "Facturas " + str(x.get("unidad") or "sin empresa")
            elif str(x.get("estado") or "").upper() == "REAL":
                con = str(x.get("categoria_planilla") or con) + " (real)"
            por_dia[f][con] += float(x.get("importe") or 0)
    fuentes = sorted({k for d in por_dia.values() for k in d})
    filas = [{"fecha": f, "valores": [por_dia[f].get(k, 0.0) for k in fuentes],
              "total": sum(por_dia[f].values())} for f in fechas]
    cheques = defaultdict(float)
    dueno = _dueno_de_la_cartera(contrato)
    for x in contrato.get("cartera_cheques", []):
        if (x.get("propio") or str(x.get("estado") or "").upper() == "ANULADO"
                or (u and (x.get("unidad") or dueno) != u)):
            continue
        if x.get("fecha") in por_dia:
            cheques[x["fecha"]] += abs(float(x.get("importe") or 0))
    return {"fuentes": fuentes, "dias": filas, "desde": hoy,
            "hasta": fechas[-1] if fechas else hoy,
            "total": sum(x["total"] for x in filas),
            "cheques": [{"fecha": f, "importe": v} for f, v in sorted(cheques.items())],
            "cheques_total": sum(cheques.values())}


# Lo que se cobra de mostrador no es "a cobrar": ya esta cobrado.
#
# ERROR REAL (06/09/2026): la solapa "A cobrar" de MAGA decia $0 y la dirección
# salto: "como que no te deben nada? Y el pago de obras sociales?".
#
# Tenia razon. Yo solo miraba las cuentas a cobrar a droguerias -- que son de
# Speedmed, porque MAGA le COMPRA a las droguerias, no le vende. Pero MAGA si
# tiene quien le deba: las OBRAS SOCIALES y PAMI, que es plata ya vendida y
# todavia no cobrada. Que estuvieran cargadas en el bloque de ingresos del
# cashflow no las hace menos cuentas a cobrar.
COBRO_INMEDIATO = ('EFECTIVO', 'TARJETA')

# Conceptos que SI mantienen el saldo hasta cobrarse.
#
# ERROR REAL (06/09/2026). la dirección: "tiene cuentas a cobrar de FCIAS vencida
# Speed, mira esos 102M del 31".
#
# Yo habia puesto una regla por BLOQUE: del bloque de ingresos, solo el futuro,
# porque ahi la celda no se limpia al cobrar. Vale para el mostrador -- tarjeta
# y efectivo son el registro de lo que entro -- pero NO para "Cuentas a cobrar
# FCIAS", que es exactamente lo que dice: plata facturada y no cobrada. Un monto
# con fecha del 31/08 que sigue ahi el 05/09 son $102M sin cobrar.
#
# O sea que la regla no es del bloque: es del CONCEPTO.
MANTIENEN_SALDO = ('CUENTAS A COBRAR', 'A COBRAR', 'CTAS A COBRAR')


def _mantiene_saldo(concepto):
    c = " ".join(str(concepto or "").upper().split())
    return any(k in c for k in MANTIENEN_SALDO)


def _es_a_cobrar(concepto):
    c = " ".join(str(concepto or "").upper().split())
    for k in COBRO_INMEDIATO:
        if k in c:
            return False
    return True



def _dueno_de_la_cartera(contrato):
    """Que empresa tiene la cartera de cheques, segun el propio contrato.

    La fila "Cartera de CH" del bloque de ingresos del cashflow viene con su
    unidad. Si esta, la cartera es de esa empresa.
    """
    for x in contrato.get("cobros_previstos", []):
        if "CARTERA" in str(x.get("concepto") or "").upper() and x.get("unidad"):
            return x["unidad"]
    return None


def a_cobrar(contrato, unidad, hoy, dias=45):
    """Lo que nos deben: por quien, vencido y por vencer.

    Junta las dos puntas que estaban separadas en la planilla:
      . cuentas a cobrar a droguerias  (Speedmed: les compra Y les vende)
      . obras sociales, PAMI y farmacias (lo vendido y no cobrado)

    OJO CON EL SENTIDO: MAGA le COMPRA a las droguerias. Confundir las dos
    puntas fue el error mas caro del proyecto.
    """
    u = _unidad_real(unidad)
    hasta = (datetime.date.fromisoformat(hoy)
             + datetime.timedelta(days=dias)).isoformat()
    agg = defaultdict(lambda: {"vencido": 0.0, "por_vencer": 0.0, "que_es": ""})
    venc = fut = 0.0

    for x in contrato.get("cuentas_a_cobrar_droguerias", []):
        if x.get("intercompany"):
            continue
        if u and (x.get("unidad") or "") != u:
            continue
        f = x.get("fecha") or ""
        v = float(x.get("importe") or 0)
        cp = (x.get("contraparte") or "?").strip()
        agg[cp]["que_es"] = "drogueria"
        if f and f < hoy:
            agg[cp]["vencido"] += v
            venc += v
        elif hoy <= f <= hasta:
            agg[cp]["por_vencer"] += v
            fut += v

    for x in contrato.get("cobros_previstos", []):
        if x.get("interno"):
            continue
        if u and (x.get("unidad") or "") != u:
            continue
        con = (x.get("concepto") or "?").strip()
        if not _es_a_cobrar(con) or "CARTERA" in con.upper():
            continue
        # LOS DOS BLOQUES NO USAN LA MISMA CONVENCION, Y CONFUNDIRLOS INFLA
        # LA CIFRA MAS IMPORTANTE DE ESTA PANTALLA.
        #
        # En el bloque de DEUDA y en el de COBRANZA A DROGUERIAS la celda se
        # pone en cero cuando se salda, asi que un monto que sobrevive a su
        # fecha es algo sin cobrar.
        #
        # En el bloque de INGRESOS del cashflow NO: la celda queda como
        # historial de lo que entro. Contar una fecha pasada como "vencido y
        # no cobrado" daba $4.314M de cuentas a cobrar de MAGA que en realidad
        # ya se cobraron -- el numero mas grande de la pantalla, y falso.
        #
        # Por eso de esta fuente solo cuenta el futuro.
        f = x.get("fecha") or ""
        v = float(x.get("importe") or 0)
        if _mantiene_saldo(con) and f and f < hoy:
            # Vencida y sin cobrar: la celda sigue con monto porque no entro.
            agg[con]["que_es"] = "facturado y no cobrado"
            agg[con]["vencido"] += v
            venc += v
            continue
        if not (hoy <= f <= hasta):
            continue
        agg[con]["que_es"] = ("facturado y no cobrado" if _mantiene_saldo(con)
                              else "vendido y no cobrado")
        agg[con]["por_vencer"] += v
        fut += v

    filas = [{"nombre": k, "vencido": v["vencido"], "por_vencer": v["por_vencer"],
              "total": v["vencido"] + v["por_vencer"], "que_es": v["que_es"]}
             for k, v in agg.items() if (v["vencido"] or v["por_vencer"])]
    filas.sort(key=lambda x: -x["total"])

    # LA CARTERA DE CHEQUES ES DE UNA EMPRESA SOLA.
    #
    # Estaba saliendo sin unidad, asi que el tablero le mostraba a MAGA $208M
    # de cheques que son de Speedmed. la dirección: "MAGA no tiene cheques en cartera
    # actualmente". El exportador nuevo los marca; los contratos viejos no, y
    # en ese caso se dice que no estan atribuidos en vez de repartirlos.
    # DE QUE EMPRESA ES LA CARTERA, DEDUCIDO DEL PROPIO CONTRATO.
    #
    # Los exports viejos traen los cheques sin unidad. En vez de no mostrarlos
    # -- que dejaba a Speedmed en $0 cuando la cartera es suya -- se deduce:
    # la fila "Cartera de CH" del bloque de ingresos SI dice de que empresa es.
    # Es una deduccion del dato, no un supuesto: si esa fila no existe, no se
    # atribuye nada y se avisa.
    dueno = _dueno_de_la_cartera(contrato)
    ch, sin_unidad = [], False
    for idx, c in enumerate(contrato.get("cartera_cheques", [])):
        f = c.get("fecha") or ""
        est = str(c.get("estado") or "").upper()
        # TODOS los que todavia no vencieron, no solo los de la ventana: cada
        # uno es una decision pendiente y el que vence en 60 dias tambien
        # cuenta como palanca.
        if est == "ANULADO" or not f or f < hoy:
            continue
        cu = c.get("unidad") or dueno
        if not cu:
            sin_unidad = True
            if u:
                continue
        elif u and cu != u:
            continue
        # UN ID POR CHEQUE, NO POR DIA.
        #
        # ERROR REAL (07/09/2026). la dirección: "cuando le das a endosar un cheque
        # automaticamente le da endosar al que se encuentre en el mismo dia, lo
        # cual esta mal: podes endosar uno y el otro no".
        #
        # El id era numero + fecha, y en esta cartera NINGUN cheque trae numero
        # -- los 365 vienen vacios. Asi que dos cheques del mismo dia
        # terminaban con el mismo id y el endoso de uno movia al otro.
        #
        # Se agrega la posicion en la lista: es lo unico que garantiza unicidad
        # cuando la planilla no trae un identificador propio.
        ch.append({"fecha": f, "importe": abs(float(c.get("importe") or 0)),
                   "librador": (c.get("librador") or "").strip()[:40],
                   "estado": est,
                   "id": "%s|%s|%s|%d" % ((c.get("numero") or "").strip(), f,
                                          int(abs(float(c.get("importe") or 0))),
                                          idx)})
    ch.sort(key=lambda x: (x["fecha"], -x["importe"]))
    return {"filas": filas, "vencido": venc, "por_vencer": fut,
            "cheques": ch[:40],
            "cheques_total": sum(c["importe"] for c in ch),
            "cheques_sin_unidad": sin_unidad}


# Los grupos que se pueden patear, y en que orden se pateam.
#
# la dirección: "esta solapa lo que te tiene que mostrar es que puedo hacer para
# llegar bien, que obligaciones tengo que patear". Para eso la proyeccion no
# puede ser una curva sola: tiene que poder sacarse cosas y ver que pasa.
#
# El orden es el del catalogo: primero lo que menos duele.
PATEABLES = [
    # LO YA VENCIDO ENTRA EL PRIMER DIA. la dirección (12/09/2026): "esta mal que el
    # flujo de tan bien con una empresa con TANTA deuda". Tenia razon: la curva
    # solo sumaba lo que vence DENTRO de la ventana, asi que la deuda atrasada
    # (fecha anterior a hoy) no restaba nunca y la caja parecia mejor de lo que
    # es. Ahora lo vencido se carga el dia 1 como su propio grupo: la curva dice
    # la verdad por defecto, y destildando el grupo se ve "si lo sigo pateando".
    ("vencido", "Deuda ya vencida (a regularizar)",
     "Ya vencio. Se cuenta el primer dia: si no se paga, la caja parece mejor de lo que es."),
    ("droguerias", "Pago a droguerias",
     "Se puede correr, pero el atraso se acumula y a las 2-3 semanas te bloquean la compra."),
    ("refi", "Refinanciacion",
     "Se puede patear hasta el vencimiento del mes siguiente: 2 semanas."),
    ("socios", "Retiros de socios",
     "Es una decision, no una obligacion: se corre sin consecuencia externa."),
    ("mercaderia", "Pago de mercaderia con cheques",
     "NO se puede patear: un cheque no puede rebotar."),
    ("sueldos", "Sueldos y cargas",
     "NO se puede patear."),
    ("bancos", "Cuotas de prestamos",
     "NO se puede patear: un atraso mas con el banco cambia la situacion BCRA y cierra las lineas."),
    ("impuestos", "Impuestos y servicios",
     "Se puede correr unos dias, con recargo."),
    ("intercompany", "Pago a la otra empresa del grupo",
     "Speedmed le factura a MAGA al costo y sin necesidad de que pague: hoy MAGA "
     "solo transfiere cuando Speed necesita cubrir cheques."),
    ("otros", "Otros egresos", ""),
]



def _mismo(a, b):
    """Si dos rotulos nombran a la misma empresa ('MAGA' y 'MAGA+')."""
    x = "".join(ch for ch in str(a or "").upper() if ch.isalnum())
    y = "".join(ch for ch in str(b or "").upper() if ch.isalnum())
    return bool(x) and bool(y) and (x in y or y in x)


# Cuando el egreso viene con TIPO del catalogo (lector/cash_limpio.py), el grupo
# sale de ahi y no de adivinar por el nombre de la fila.
GRUPO_POR_TIPO = {
    "CHEQUE": "mercaderia", "SUELDO": "sueldos", "IMPUESTO": "impuestos", "ESTAMPILLAS": "impuestos",
    "PRESTAMO": "bancos", "PROVEEDOR": "droguerias", "HOJA_VERDE": "droguerias", "INSUMOS": "droguerias",
    "COSECHA": "droguerias", "HONORARIO_DIVIDENDO": "socios", "RETIRO_SOCIO": "socios",
}


def _grupo_de(nombre, tipo=None):
    """De que grupo es un egreso: por su tipo si lo trae, si no por como se llama la fila."""
    if tipo and str(tipo).upper() in GRUPO_POR_TIPO:
        return GRUPO_POR_TIPO[str(tipo).upper()]
    n = " ".join(str(nombre or "").upper().split())
    if "RETIRO" in n or "SOCIO" in n:
        return "socios"
    if "REFINANC" in n:
        return "refi"
    if "DROGUERIA" in n or "DROG" in n:
        return "droguerias"
    if "MERCADERIA" in n:
        return "mercaderia"
    if "SUELDO" in n or "CS SOC" in n or "COMISION" in n:
        return "sueldos"
    if "IMPUESTO" in n or "SERVICIO" in n or "AFIP" in n or "VEP" in n or "ALQUILER" in n:
        return "impuestos"
    return "otros"


def proyeccion(contrato, unidad, hoy, dias=45, con_intercompany=False, modo=DIA_1):
    """La caja dia por dia, CON LO QUE ESTA CARGADO — sin estimar nada.

    ERROR REAL (06/09/2026). la dirección: *"¿cómo puede ser que Speed en el cash dé
    tan bien y en la aplicación dé tan mal?"*.

    Dos causas, las dos mias, y las dos de la misma familia:

    1. **Faltaba una punta.** Se le restaban los $4.677M que Speed le DEBE a
       las droguerias y no se le sumaban los $6.8MM que las droguerias le DEBEN
       a Speed. Speedmed les compra Y les vende: contar un solo lado lo dejaba
       en rojo por construccion.

    2. **Se estimaba lo que ya estaba cargado.** El cashflow trae los egresos
       futuros con fecha y monto — para eso existe — y aca se los ignoraba para
       proyectarlos a partir del historico. O sea que a lo cargado se le sumaba
       una estimacion de lo mismo.

    Ahora no se estima nada: se usa lo que dice la planilla. Y el resultado
    reproduce las dos filas del cash de la dirección:

        Speed sin pagar droguerias   +$3.791M   ("Saldo cierre")
        Speed pagandolas             -$885M     ("Con pago a droguerias")

    La maquinaria de estimacion sigue viva en simulador/proyeccion.py, que es
    donde sirve: para el backtest y la memoria, donde la pregunta es "¿lo que
    proyectamos se parecio a lo que paso?". Para el tablero, la respuesta
    honesta es mostrar lo que el cliente cargo.
    """
    u = _unidad_real(unidad)
    caja = float(contrato.get("caja_hoy") or 0)
    if u:
        caja = float((contrato.get("caja_por_unidad") or {}).get(u) or 0)

    desde = datetime.date.fromisoformat(hoy)
    hasta = (desde + datetime.timedelta(days=dias - 1)).isoformat()

    def _mia(x):
        return (not u) or (x.get("unidad") or "") == u

    def _dentro(f):
        return bool(f) and hoy <= f <= hasta

    por_dia = {}

    def _sumar(f, grupo, monto):
        d = por_dia.setdefault(f, {"entra": 0.0})
        if grupo == "entra":
            d["entra"] += monto
        else:
            d[grupo] = d.get(grupo, 0.0) + monto

    # Una sola cuenta para el gráfico y la curva: una factura no puede faltar en uno.
    for x in ingresos_por_dia(contrato, unidad, hoy, dias)["dias"]:
        _sumar(x["fecha"], "entra", x["total"])

    # --- lo que sale, item por item para poder patearlo
    items = []
    # En modo "stock" lo vencido no entra a la curva: se junta aca y se muestra aparte.
    stock = []

    def _vencido(f, cp, v, tipo):
        if modo == STOCK:
            stock.append({"fecha": f, "contraparte": cp, "monto": v, "tipo": tipo})
            return
        _sumar(hoy, "vencido", v)
        items.append({"id": "vencido|" + f + "|" + cp, "grupo": "vencido", "fecha": hoy,
                      "concepto": "Vencido el " + f[8:10] + "/" + f[5:7] + " · " + cp,
                      "monto": v, "estimado": False})

    for x in contrato.get("egresos_cashflow", []):
        if not _mia(x) or x.get("intercompany"):
            continue
        f = x.get("fecha") or ""
        v = abs(float(x.get("importe") or 0))
        if not v:
            continue
        cp = (x.get("contraparte") or "?").strip()
        # Un egreso con fecha pasada que el lector marco como PENDIENTE (deuda
        # impositiva en mora, cuota bancaria no pagada) es vencido: entra hoy.
        # Los demas con fecha pasada ya se pagaron y no se tocan.
        if f and f < hoy and x.get("vencido_pendiente"):
            _vencido(f, cp, v, x.get("tipo") or "")
            continue
        if not _dentro(f):
            continue
        g = _grupo_de(cp, x.get("tipo"))
        _sumar(f, g, v)
        items.append({"id": g + "|" + f + "|" + cp, "grupo": g, "fecha": f,
                      "concepto": cp, "monto": v, "estimado": False})

    # EL PAGO ENTRE EMPRESAS VA EN LA DIRECCION QUE DICE la dirección, NO LA QUE
    # SUGIERE EL BLOQUE DONDE ESTA CARGADO.
    #
    # ERROR REAL (07/09/2026): "en el selector de Speed sale como si Speed le
    # tendria que pagar a MAGA, cuando en realidad MAGA le debe a Speed".
    #
    # La fila "MAGA+" esta escrita dentro del bloque de deuda de la planilla de
    # Speed, asi que yo la tomaba como algo que Speed paga. Pero la linea
    # siguiente del cash dice "Con pago DE MAGA+": es plata que Speed RECIBE.
    # La ubicacion en la planilla es una decision de layout, no de signo.
    #
    # La regla: la CONTRAPARTE le paga a la unidad donde esta cargada la fila.
    # Y como el dato existe de un solo lado, para la otra empresa se deriva con
    # el signo opuesto -- que ademas es lo unico que mantiene el invariante:
    # un pago dentro del grupo no puede cambiar el total del grupo.
    inter_entra, inter_sale = [], []
    for x in contrato.get("deuda_droguerias", []):
        if x.get("intercompany"):
            f = x.get("fecha") or ""
            v = abs(float(x.get("importe") or 0))
            duena = x.get("unidad") or ""
            otra = str(x.get("contraparte") or "").strip()
            if not (_dentro(f) and v):
                continue
            # EN LA VISTA DEL GRUPO NO CUENTA NI DE UN LADO NI DEL OTRO.
            #
            # Un pago entre dos empresas del mismo grupo no puede cambiar el
            # total del grupo: entra por una puerta y sale por la otra. Es el
            # mismo invariante que ya tenia test, y al arreglar la direccion
            # casi lo rompo -- en GRUPO sumaba la entrada sin la salida.
            if not u:
                continue
            if u == duena:
                inter_entra.append({"fecha": f, "monto": v, "de": otra})
            elif _mismo(u, otra):
                inter_sale.append({"fecha": f, "monto": v, "a": duena})

    for x in contrato.get("deuda_droguerias", []):
        if not _mia(x):
            continue
        cp = str(x.get("contraparte") or "")
        # Lo intercompany solo cuenta en el escenario "con pago a la otra
        # empresa": es plata que se mueve dentro del grupo.
        if x.get("intercompany"):
            continue          # se maneja aparte, con su direccion correcta
        f = x.get("fecha") or ""
        v = float(x.get("importe") or 0)
        if f and f < hoy and v > 0 and not x.get("es_credito"):
            # Vencido e impago: entra HOY en su propio grupo (dia_1) o al stock (stock).
            _vencido(f, cp, v, "PROVEEDOR")
            continue
        if not _dentro(f) or v <= 0:
            continue
        if x.get("intercompany"):
            g = "intercompany"
        elif "REFINANC" in cp.upper():
            g = "refi"
        else:
            g = "droguerias"
        _sumar(f, g, v)
        items.append({"id": g + "|" + f + "|" + cp, "grupo": g, "fecha": f,
                      "concepto": ("Resumen del " + f[8:10] + "/" + f[5:7] +
                                   " · " + cp) if g == "droguerias" else cp,
                      "monto": v, "estimado": False})

    if con_intercompany:
        for x in inter_entra:
            _sumar(x["fecha"], "entra", x["monto"])
        for x in inter_sale:
            _sumar(x["fecha"], "intercompany", x["monto"])
            items.append({"id": "intercompany|" + x["fecha"] + "|" + x["a"],
                          "grupo": "intercompany", "fecha": x["fecha"],
                          "concepto": "Pago a " + x["a"], "monto": x["monto"],
                          "estimado": False})

    f, out = desde, []
    while f.isoformat() <= hasta:
        d = por_dia.get(f.isoformat(), {"entra": 0.0})
        out.append({"fecha": f.isoformat(), "entra": d.get("entra", 0.0),
                    "sale": {g: d.get(g, 0.0) for g, _, _ in PATEABLES if d.get(g)}})
        f += datetime.timedelta(days=1)

    items.sort(key=lambda i: (i["grupo"], i["fecha"], -i["monto"]))
    por_tipo = defaultdict(float)
    for x in stock:
        por_tipo["proveedores" if x["tipo"] == "PROVEEDOR" else
                 "impuestos" if x["tipo"] == "IMPUESTO" else
                 "bancos" if x["tipo"] == "PRESTAMO" else "otros"] += x["monto"]
    return {"desde": hoy, "hasta": hasta, "caja_inicial": caja, "dias": out,
            "modo": modo,
            "vencido_stock": {"total": sum(x["monto"] for x in stock),
                              "por_tipo": dict(por_tipo), "items": stock},
            "items": items,
            "grupos": [{"id": g, "nombre": n, "nota": t} for g, n, t in PATEABLES],
            # (el nombre del grupo "droguerias" lo traduce el HTML con D.vocab)
            "total_entra": sum(x["entra"] for x in out),
            "total_sale": sum(sum(x["sale"].values()) for x in out),
            "sin_estimar": True}


def capacidad_de_pago(contrato, unidad, hoy, cliente, ventanas=VENTANAS):
    """Modo "stock": cuanto del vencido se puede pagar sin comprometer lo que viene.

    Para cada ventana: la curva de caja con SOLO lo comprometido (sin vencido);
    el punto mas bajo de esa curva es la caja libre -- lo que se puede sacar hoy
    sin que ningun dia de la ventana quede en rojo. Con eso se paga vencido en
    orden de atraso (el que hace mas que espera, primero), hasta que se acaba.

    Es la pregunta de la dirección (17/09/2026): "cuanto y que podes pagar sin
    comprometer las obligaciones futuras". No es un consejo de a quien
    postergar: es cuanto hay, y hasta donde llega.
    """
    p = proyeccion(contrato, unidad, hoy, dias=max(ventanas), modo=STOCK)
    provs = proveedores(contrato, unidad, cliente, hoy)
    # Vencido por proveedor, ordenado por atraso (mas viejo primero).
    cola = sorted([x for x in provs if x["vencido"] > 0],
                  key=lambda x: -(x["atraso"] or 0))
    vencido_prov = sum(x["vencido"] for x in cola)
    out = {}
    for v in ventanas:
        caja, minimo, dia_min = p["caja_inicial"], p["caja_inicial"], hoy
        sale_total = entra_total = 0.0
        for x in p["dias"][:v]:
            sale = sum(x["sale"].values())
            caja += x["entra"] - sale
            entra_total += x["entra"]
            sale_total += sale
            if caja < minimo:
                minimo, dia_min = caja, x["fecha"]
        libre = max(0.0, minimo)
        resto, paga = libre, []
        for x in cola:
            if resto <= 0:
                break
            m = min(resto, x["vencido"])
            paga.append({"nombre": x["nombre"], "monto": m, "completo": m >= x["vencido"] - 0.5,
                         "atraso": x["atraso"], "vencido": x["vencido"]})
            resto -= m
        out[str(v)] = {
            "libre": libre, "minimo": minimo, "dia_minimo": dia_min,
            "entra": entra_total, "sale": sale_total,
            "paga": paga, "pagado": libre - resto,
            "queda_vencido": vencido_prov - (libre - resto),
            "vencido_proveedores": vencido_prov,
            "vencido_total": p["vencido_stock"]["total"],
            "vencido_por_tipo": p["vencido_stock"]["por_tipo"],
        }
    return out


def _grupo_debito(fila):
    """Solo vale lo cargado: un vacío o un valor raro queda sin definir."""
    valor = fila.get("debito_automatico", fila.get("Debito Automatico"))
    if valor is True or str(valor).strip().casefold() in ("sí", "si"):
        return "automatico"
    if valor is False or str(valor).strip().casefold() == "no":
        return "decision"
    return "sin_definir"


def obligaciones_por_debito(lineas, cuotas, hoy, impuestos=False):
    """Reparte el stock y el cronograma por separado: jamás se suman entre sí.

    En bancos, el capital sale de las líneas y las fechas de las cuotas.
    En impuestos, cada fila ya es una deuda con su vencimiento. Si falta el
    banco del CBU, lo mostramos; no inventamos dónde se va a debitar.
    """
    hoy = hoy.isoformat() if hasattr(hoy, "isoformat") else str(hoy)
    hasta = (datetime.date.fromisoformat(hoy) + datetime.timedelta(days=30)).isoformat()
    grupos = [{"id": k, "nombre": n, "por_banco": {}} for k, n in (
        ("automatico", "Sale sí o sí"), ("decision", "Se paga por decisión"),
        ("sin_definir", "Sin definir"))]
    indice = {g["id"]: g for g in grupos}

    def agregar(fila, es_stock):
        banco = fila.get("banco") or ("Banco/CBU sin informar" if impuestos else
                                      (fila.get("contraparte") or "Banco sin informar").split(" - ")[0])
        g = indice[_grupo_debito(fila)]
        b = g["por_banco"].setdefault(banco, {"banco": banco, "total": Decimal(0),
                "vencido": Decimal(0), "en_30": Decimal(0), "items": []})
        monto = Decimal(str(fila.get("capital_vigente" if es_stock and not impuestos else "importe") or 0))
        fecha = str(fila.get("fecha") or "")
        if es_stock:
            b["total"] += monto
        if not es_stock or impuestos:
            if fecha and fecha < hoy:
                b["vencido"] += monto
            elif hoy <= fecha < hasta:
                b["en_30"] += monto
        # Dejamos todo el cronograma disponible, también lo posterior a 30 días.
        b["items"].append({"concepto": fila.get("linea") or fila.get("contraparte") or "Obligación",
            "fecha": fecha or str(fila.get("vence") or ""), "importe": float(monto),
            "clase": "Capital (no sumar a cuotas)" if es_stock and not impuestos else "Vencimiento",
            "estimado": bool(fila.get("estimado")), "falta_importe": bool(fila.get("falta_importe"))})

    for fila in lineas:
        if not fila.get("en_caja"):
            agregar(fila, True)
    for fila in cuotas:
        agregar(fila, False)
    for g in grupos:
        bancos = sorted(g["por_banco"].values(), key=lambda b: b["banco"])
        for campo in ("total", "vencido", "en_30"):
            g[campo] = float(sum((b[campo] for b in bancos), Decimal(0)))
            for b in bancos:
                b[campo] = float(b[campo])
        for b in bancos:
            b["items"].sort(key=lambda x: (x["clase"], x["fecha"], x["concepto"]))
        g["por_banco"] = bancos
    return grupos


def deuda_impositiva_por_debito(contrato, unidad, hoy):
    filas = [x for x in contrato.get("deuda_impositiva") or []
             if unidad == GRUPO or _unidad_real(x.get("unidad")) == unidad]
    return obligaciones_por_debito(filas, [], hoy, impuestos=True) if filas else []


def deuda_bancaria(contrato, unidad, hoy):
    """La deuda con los bancos como STOCK, por banco: lo que se debe, lo que ya
    vencio (cuotas impagas), lo que vence en 30 dias y la peor situacion BCRA.

    Los descubiertos van aparte: lo usado YA esta en la caja (es el saldo negativo
    de la cuenta), asi que sumarlo seria contarlo dos veces. Lo que importa de un
    descubierto es cuanto margen queda: acordado menos usado. Ese margen es, en la
    practica, la unica "caja libre" que tiene NAVAR (18/09/2026).
    """
    db = contrato.get("deuda_bancaria") or {}
    lineas = [l for l in db.get("lineas") or [] if unidad == GRUPO or _unidad_real(l.get("unidad")) == unidad]
    cuotas = [c for c in db.get("cuotas") or [] if unidad == GRUPO or _unidad_real(c.get("unidad")) == unidad]
    if not lineas and not cuotas:
        return None
    hoy_s = hoy.isoformat() if hasattr(hoy, "isoformat") else str(hoy)
    d30 = (datetime.date.fromisoformat(hoy_s) + datetime.timedelta(days=30)).isoformat()
    d90 = (datetime.date.fromisoformat(hoy_s) + datetime.timedelta(days=90)).isoformat()
    por_banco = OrderedDict()
    for l in lineas:
        b = por_banco.setdefault(l["banco"], {"banco": l["banco"], "deuda": 0.0, "productos": 0, "situacion": None,
                                               "vencido": 0.0, "en_30": 0.0, "en_90": 0.0, "descubierto_acordado": 0.0,
                                               "descubierto_usado": 0.0, "faltan": [], "estimados": []})
        if l.get("en_caja"):
            b["descubierto_acordado"] += l.get("capital_original") or 0.0
            b["descubierto_usado"] += l.get("capital_vigente") or 0.0
        else:
            b["deuda"] += l.get("capital_vigente") or 0.0
            b["productos"] += 1
        if l.get("situacion_bcra"):
            b["situacion"] = max(b["situacion"] or 0, int(l["situacion_bcra"]))
        if l.get("falta_importe"):
            b["faltan"].append(l["linea"])
        if l.get("estimado"):
            b["estimados"].append(l["linea"])
    for c in cuotas:
        banco = (c.get("contraparte") or "").split(" - ")[0]
        b = por_banco.setdefault(banco, {"banco": banco, "deuda": 0.0, "productos": 0, "situacion": None,
                                          "vencido": 0.0, "en_30": 0.0, "en_90": 0.0, "descubierto_acordado": 0.0,
                                          "descubierto_usado": 0.0, "faltan": [], "estimados": []})
        f = c["fecha"]
        if f < hoy_s:
            b["vencido"] += c["importe"]
        elif f < d30:
            b["en_30"] += c["importe"]
        if hoy_s <= f < d90:
            b["en_90"] += c["importe"]
    # Lo usado del descubierto es el saldo negativo REAL de la cuenta (extracto), no lo
    # que decia el mapa el dia que se armo. Si el banco no informo acuerdo, el margen es 0.
    usado_real = defaultdict(float)
    for sal in contrato.get("saldos") or []:
        if unidad == GRUPO or _unidad_real(sal.get("unidad")) == unidad:
            usado_real[sal.get("banco")] += max(0.0, -(sal.get("saldo") or 0.0))
    for b in por_banco.values():
        if b["banco"] in usado_real:
            b["descubierto_usado"] = usado_real[b["banco"]]
        b["margen"] = max(0.0, b["descubierto_acordado"] - b["descubierto_usado"]) if b["descubierto_acordado"] else 0.0
    filas = sorted(por_banco.values(), key=lambda b: -(b["deuda"] + b["vencido"]))
    margen = sum(b["margen"] for b in filas)
    return {
        "por_banco": filas,
        "por_debito": obligaciones_por_debito(lineas, cuotas, hoy),
        "total": sum(b["deuda"] for b in filas),
        "vencido": sum(b["vencido"] for b in filas),
        "en_30": sum(b["en_30"] for b in filas),
        "en_90": sum(b["en_90"] for b in filas),
        "descubierto_acordado": sum(b["descubierto_acordado"] for b in filas),
        "descubierto_usado": sum(b["descubierto_usado"] for b in filas),
        "margen_descubierto": margen,
        "situacion_peor": max([b["situacion"] or 0 for b in filas] or [0]),
        "faltan": [x for b in filas for x in b["faltan"]],
        "estimados": [x for b in filas for x in b["estimados"]],
    }


def faltantes(contrato):
    """Lo que el tablero no tiene cargado y tendria que tener. Se dice, no se disimula."""
    out = []
    if not contrato.get("deuda_impositiva"):
        out.append("<b>La deuda con ARCA e Ingresos Brutos.</b> No está cargada: ni los vencimientos "
                   "del mes ni los planes de pago. Es el pedido al contador.")
    db = contrato.get("deuda_bancaria") or {}
    if not db.get("cuotas"):
        out.append("<b>Las cuotas de los préstamos bancarios.</b> No están cargadas: cuánto, cuándo "
                   "y en qué banco. Sale de los contratos o de cada home banking.")
    else:
        faltan = [l["linea"] for l in db.get("lineas") or [] if l.get("falta_importe")]
        if faltan:
            out.append("<b>Deuda bancaria sin importe:</b> %s. Están en el mapa de deuda pero sin saldo; "
                       "pedir el detalle al banco." % ", ".join(faltan))
        est = [l["linea"] for l in db.get("lineas") or [] if l.get("estimado")]
        if est:
            out.append("<b>Cuotas estimadas, no informadas por el banco:</b> %s. Se calcularon con el saldo y la "
                       "tasa; pedir la tabla de amortización." % ", ".join(est))
    # La caja: que cuentas estan al dia y cuales siguen con la carga manual.
    hoy = D.hoy_de(contrato)
    viejos = OrderedDict()
    for s in contrato.get("saldos") or []:
        f = s.get("fecha")
        if f and f < hoy:
            u = s.get("unidad") or "?"
            viejos[u] = max(viejos.get(u, ""), f)
    fs = (contrato.get("_origen") or {}).get("fecha_saldos")
    if not viejos and fs and fs < hoy:
        viejos["?"] = fs
    for u, f in viejos.items():
        dd = f[8:10] + "/" + f[5:7]
        if u == "?":
            out.append("<b>La caja de hoy es la del %s.</b> Los saldos de banco se cargaron ese día." % dd)
        elif f < (datetime.date.fromisoformat(hoy) - datetime.timedelta(days=5)).isoformat():
            out.append("<b>La caja de %s es la del %s.</b> Sigue con la carga manual de la planilla vieja, "
                       "sin extracto de banco." % (_unidad_real(u), dd))
    return out


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




def planes_por_ventana(contrato, unidad, hoy, cliente, ventanas=(7, 14, 21, 30, 45)):
    """El plan minimo para cada ventana del timeline.

    Se precalculan todas: mover el slider tiene que cambiar de plan al toque, y
    la regla del proyecto es que la plata se calcula en Python. Son cinco
    calculos baratos sobre datos que ya estan en memoria.
    """
    from simulador import plan as PL
    try:
        fichas = PROV.cargar_proveedores(cliente)
    except Exception:
        fichas = {}
    p = proyeccion(contrato, unidad, hoy)
    out = {}
    for v in ventanas:
        try:
            pl = PL.armar(p, dias=v, proveedores=fichas)
        except Exception as e:
            out[str(v)] = {"error": str(e)}
            continue
        pl.pop("curva", None)          # la curva la arma el navegador
        pl["frase"] = PL.en_palabras(pl)
        out[str(v)] = pl
    return out



def _memoria_tablero(cliente, paquete):
    """Concilia el tablero de hoy contra el ultimo snapshot ANTERIOR.

    Se busca el mas reciente que NO sea de hoy: comparar contra si mismo daria
    0% de desvio siempre, que es peor que no medir -- da una sensacion de
    precision que no existe.
    """
    try:
        from memoria import tablero as MT
        rutas = [r for r in MT.snapshots(cliente)
                 if paquete["fecha"] not in os.path.basename(r)]
        if not rutas:
            return {"hay": False,
                    "por_que": "todavia no hay ninguna proyeccion guardada de "
                               "otro dia contra la cual comparar"}
        snap = MT.leer(rutas[-1])
        c = MT.conciliar(snap, paquete)
        return {"hay": True, "desde": snap["corte"],
                "frases": MT.en_palabras(c), "unidades": c["unidades"]}
    except Exception as e:
        return {"hay": False, "por_que": "no se pudo leer la memoria: %s" % e}


# Con que palabras le habla el tablero al cliente. Vive en el catalogo
# ("vocabulario"); esto es solo el default para un catalogo que no lo tenga.
VOCAB_DEFAULT = {
    "proveedor": "proveedor", "proveedores": "proveedores", "Proveedor": "Proveedor",
    "nota_vencido": "con proveedores", "tiene_refi": False,
    "nota_ritmo": "Un cobro grande un dia y treinta dias parejos no es lo mismo, aunque sumen igual.",
    "nota_a_cobrar": "Lo facturado y no cobrado es cuenta a cobrar: es caja recien cuando entra.",
    "no_sabe_cobranza": "",
    "no_sabe_extra": "",
    "comprobante": "resumen",
}


def vocabulario(cliente):
    v = dict(VOCAB_DEFAULT)
    try:
        ruta = os.path.join(BASE_REPO, "clientes", cliente, "catalogo.json")
        with io.open(ruta, encoding="utf-8") as f:
            cat = json.load(f)
        v.update({k: x for k, x in (cat.get("vocabulario") or {}).items() if not k.startswith("_")})
    except Exception:
        pass
    return v


def armar(contrato, cliente="maga"):
    # La estimación por kg fue dada de baja en NAVAR. Filtramos una copia
    # antes de TODOS los cálculos del tablero; el contrato original no se toca.
    if cliente == "navar":
        contrato = dict(contrato)
        contrato["cobros_previstos"] = [x for x in contrato.get("cobros_previstos", [])
            if x.get("fuente") != "COBRANZA_PROYECTADA"]
    hoy = D.hoy_de(contrato)
    vocab = vocabulario(cliente)
    modo = modo_vencido(cliente)
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
            "puente": puente(contrato, u, 45, modo),
            "proveedores": proveedores(contrato, u, cliente, hoy),
            "salidas": salidas(contrato, u, hoy),
            "gastos": gastos_del_periodo(contrato, u, hoy, cliente=cliente),
            "escenarios": esc_por_unidad[u],
            "retiro": retiro_por_ventana(contrato, u),
            "ingresos_dia": ingresos_por_dia(contrato, u, hoy),
            "a_cobrar": a_cobrar(contrato, u, hoy),
            "proyeccion": proyeccion(contrato, u, hoy, modo=modo),
            # El escenario "y ademas le pago a la otra empresa del grupo".
            "proyeccion_ic": proyeccion(contrato, u, hoy, con_intercompany=True, modo=modo),
            # Modo stock: cuanto del vencido se puede pagar en cada ventana.
            "capacidad": capacidad_de_pago(contrato, u, hoy, cliente) if modo == STOCK else None,
            # La deuda con los bancos como stock: por banco, vencido, proximos 30 dias, margen.
            "deuda_bancaria": deuda_bancaria(contrato, u, hoy),
            "deuda_impositiva_debito": deuda_impositiva_por_debito(contrato, u, hoy),
            # El plan minimo para cada ventana que ofrece el timeline.
            # Se precalculan porque el HTML no calcula plata: mover el slider
            # cambia de plan, no lo recalcula.
            "planes": planes_por_ventana(contrato, u, hoy, cliente),
            "refi": refinanciacion(contrato, u, hoy),
        }

    for d in datos.values():
        stock = d["proyeccion"]["vencido_stock"]
        filas = []
        for tipo, nombre, riesgo in (
            ("IMPUESTO", "ARCA / impuestos", "Riesgo de embargo de cuentas."),
            ("PRESTAMO", "Bancos", "Riesgo de corte de las líneas que financian la caja."),
            ("PROVEEDOR", "Proveedores", "Riesgo de corte de entregas.")):
            items = [x for x in stock["items"] if x["tipo"] == tipo]
            filas.append({"nombre": nombre, "monto": sum(x["monto"] for x in items),
                          "desde": min((x["fecha"] for x in items), default=None),
                          "riesgo": riesgo})
        # Reusamos el stock de la curva: no sumamos de nuevo el mapa bancario.
        d["vencidos_resumen"] = {"filas": filas, "total": stock["total"],
            "otros": stock["por_tipo"].get("otros", 0)} if modo == STOCK else None

    paquete_parcial = {"fecha": hoy, "unidades": unidades, "datos": datos}
    return {
        "cliente": contrato.get("cliente") or "finauto",
        "fecha": hoy,
        "generado": contrato.get("generado"),
        "unidades": unidades,
        "ventanas": VENTANAS,
        "datos": datos,
        "hallazgos": hallazgos(contrato),
        "faltantes": faltantes(contrato),
        "modo_vencido": modo,
        "memoria": memoria_del_cliente(cliente),
        # LO QUE DIJIMOS LA VEZ PASADA, contra lo que pasa hoy.
        # Es lo que hace que la segunda visita valga mas que la primera.
        "memoria_tablero": _memoria_tablero(cliente, paquete_parcial),
        # A quien se puede endosar un cheque: las droguerias del catalogo del
        # cliente, no una lista escrita a mano en el HTML.
        "droguerias": droguerias_del_cliente(cliente),
        # Las palabras con las que el HTML le habla a este cliente.
        "vocab": vocab,
    }


def droguerias_del_cliente(cliente):
    try:
        from simulador import proveedores as PROV
        fichas = PROV.cargar_proveedores(cliente)
    except Exception:
        return []
    return [v.get("nombre") or k for k, v in fichas.items()
            if "REFINANC" not in str(k).upper()]
