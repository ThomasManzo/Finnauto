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
        # La refinanciacion NO es una drogueria. Thomas fue explicito: "no tiene
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


def gastos_del_periodo(contrato, unidad, hoy, dias=45, tope=8):
    """En que se va la plata, con las droguerias adentro.

    Thomas: "grafico de gastos: droguerias suizo dds y cofa, cual suma mas, un
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
        fichas = PROV.cargar_proveedores("maga")
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


# Lo que se cobra de mostrador no es "a cobrar": ya esta cobrado.
#
# ERROR REAL (06/09/2026): la solapa "A cobrar" de MAGA decia $0 y Thomas
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
# ERROR REAL (06/09/2026). Thomas: "tiene cuentas a cobrar de FCIAS vencida
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
    # de cheques que son de Speedmed. Thomas: "MAGA no tiene cheques en cartera
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
        # ERROR REAL (07/09/2026). Thomas: "cuando le das a endosar un cheque
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
# Thomas: "esta solapa lo que te tiene que mostrar es que puedo hacer para
# llegar bien, que obligaciones tengo que patear". Para eso la proyeccion no
# puede ser una curva sola: tiene que poder sacarse cosas y ver que pasa.
#
# El orden es el del catalogo: primero lo que menos duele.
PATEABLES = [
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


def _grupo_de(nombre):
    """De que grupo es un egreso, mirando como se llama la fila."""
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


def proyeccion(contrato, unidad, hoy, dias=45, con_intercompany=False):
    """La caja dia por dia, CON LO QUE ESTA CARGADO — sin estimar nada.

    ERROR REAL (06/09/2026). Thomas: *"¿cómo puede ser que Speed en el cash dé
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
    reproduce las dos filas del cash de Thomas:

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

    # --- lo que entra
    for x in contrato.get("cobros_previstos", []):
        if not _mia(x) or x.get("interno"):
            continue
        if "CARTERA" in str(x.get("concepto") or "").upper():
            continue          # no es caja hasta que se decide
        if _dentro(x.get("fecha")):
            _sumar(x["fecha"], "entra", abs(float(x.get("importe") or 0)))

    for x in contrato.get("cuentas_a_cobrar_droguerias", []):
        if not _mia(x) or x.get("intercompany"):
            continue
        if _dentro(x.get("fecha")):
            _sumar(x["fecha"], "entra", abs(float(x.get("importe") or 0)))

    # --- lo que sale, item por item para poder patearlo
    items = []
    for x in contrato.get("egresos_cashflow", []):
        if not _mia(x) or x.get("intercompany"):
            continue
        f = x.get("fecha") or ""
        if not _dentro(f):
            continue
        v = abs(float(x.get("importe") or 0))
        if not v:
            continue
        cp = (x.get("contraparte") or "?").strip()
        g = _grupo_de(cp)
        _sumar(f, g, v)
        items.append({"id": g + "|" + f + "|" + cp, "grupo": g, "fecha": f,
                      "concepto": cp, "monto": v, "estimado": False})

    # EL PAGO ENTRE EMPRESAS VA EN LA DIRECCION QUE DICE THOMAS, NO LA QUE
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
    return {"desde": hoy, "hasta": hasta, "caja_inicial": caja, "dias": out,
            "items": items,
            "grupos": [{"id": g, "nombre": n, "nota": t} for g, n, t in PATEABLES],
            "total_entra": sum(x["entra"] for x in out),
            "total_sale": sum(sum(x["sale"].values()) for x in out),
            "sin_estimar": True}


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
            # El escenario "y ademas le pago a la otra empresa del grupo".
            "proyeccion_ic": proyeccion(contrato, u, hoy, con_intercompany=True),
            # El plan minimo para cada ventana que ofrece el timeline.
            # Se precalculan porque el HTML no calcula plata: mover el slider
            # cambia de plan, no lo recalcula.
            "planes": planes_por_ventana(contrato, u, hoy, cliente),
            "refi": refinanciacion(contrato, u, hoy),
        }

    paquete_parcial = {"fecha": hoy, "unidades": unidades, "datos": datos}
    return {
        "cliente": contrato.get("cliente") or "finauto",
        "fecha": hoy,
        "generado": contrato.get("generado"),
        "unidades": unidades,
        "ventanas": VENTANAS,
        "datos": datos,
        "hallazgos": hallazgos(contrato),
        "memoria": memoria_del_cliente(cliente),
        # LO QUE DIJIMOS LA VEZ PASADA, contra lo que pasa hoy.
        # Es lo que hace que la segunda visita valga mas que la primera.
        "memoria_tablero": _memoria_tablero(cliente, paquete_parcial),
        # A quien se puede endosar un cheque: las droguerias del catalogo del
        # cliente, no una lista escrita a mano en el HTML.
        "droguerias": droguerias_del_cliente(cliente),
    }


def droguerias_del_cliente(cliente):
    try:
        from simulador import proveedores as PROV
        fichas = PROV.cargar_proveedores(cliente)
    except Exception:
        return []
    return [v.get("nombre") or k for k, v in fichas.items()
            if "REFINANC" not in str(k).upper()]
