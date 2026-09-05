# -*- coding: utf-8 -*-
"""
informe.visita — el entregable de cada visita a un cliente.

POR QUE EXISTE
--------------
El modelo de Thomas no es vender un software: es asesorar. Eso cambia cual es el
producto. Hoy todas las herramientas imprimen en la terminal y no queda NADA:
uno se va de la reunion con capturas de pantalla.

El entregable de una asesoria es un documento. Es lo que justifica el honorario,
lo que el cliente guarda, y lo que le muestra al contador.

DOS LECTORES, UN ARCHIVO
------------------------
Thomas lo definio asi: lo leen los dos, "tanto yo que entiendo de finanzas como
el chabon que heredo una cadena de farmacias y entiende mas la parte operativa".

    PAGINA 1 - PARA EL DUENO
        Frases cortas, numeros grandes, cero jerga. Nada de percentiles,
        medianas ni margenes de error. La pregunta que contesta es "¿me alcanza
        la plata?" y, si no, "¿que hago?".

        NO LLEVA UN SALDO DE CIERRE, a proposito. Thomas:

            "un dueno no va a mirar al final del periodo, porque vos tenes
             deuda a 45 dias porque le pagas a las droguerias a 30/45/60. Pero
             vos tambien, como proveedor de otros, cobras a 30/45/60: o sea que
             un periodo de 45 dias todavia no esta cerrado, y ahi esta la
             importancia del timeline."

        Un saldo al dia 45 es un corte arbitrario en el medio de un ciclo
        abierto: ahi hay deuda que vence despues y cobranzas que entran despues.
        Mostrarlo como resultado es inventar un final donde no lo hay.

        Por eso la hoja muestra DOS cosas distintas:
          . el DIA A DIA, que es con lo que se decide; y
          . COMO CIERRA EL PERIODO, que es para entender, aclarando que el
            periodo NO esta cerrado.

    PAGINA 2 - PARA THOMAS
        Todo lo que la primera pagina esconde a proposito: de donde sale cada
        numero, cuanto puede errar, que no se pudo determinar y que hay que
        preguntarle al cliente en la proxima.

La separacion no es cosmetica. Meterle margenes de error a alguien que quiere
saber si el 25 le alcanza la plata no lo hace mas informado: lo hace desconfiar
de todo el informe.

QUE NO HACE
-----------
No inventa recomendaciones. Todo lo que dice sale de los modulos que ya existen
y ya estan medidos. Si algo no se puede afirmar, va en la seccion de preguntas,
no en la de conclusiones.

Uso:
    python informe/visita.py --contrato c.json --cliente maga --caja 1183497652
"""

import io
import os
import sys
import json
import html
import argparse
import datetime

BASE_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)

from simulador.proyeccion import (proyectar_caja, revisar_coherencia,
                                  backtest_horizonte, perfilar)
from simulador.semana import _m


MESES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _fecha_larga(iso):
    d = datetime.date.fromisoformat(iso)
    return "%d de %s" % (d.day, MESES[d.month])


def _e(x):
    return html.escape(str(x))


# ------------------------------------------------------------------ analisis
def analizar(contrato, caja, dias, minimo):
    hoy = datetime.date.today()
    fechas = [m["fecha"] for m in contrato.get("movimientos", []) if m.get("fecha")]
    # Si el contrato es historico, se arranca donde terminan los datos: proyectar
    # desde hoy sobre datos de hace tres meses daria una curva vacia.
    corte = hoy
    if fechas and max(fechas) < hoy.isoformat():
        corte = datetime.date.fromisoformat(max(fechas))

    caja_r = proyectar_caja(contrato, corte, dias, caja)
    coh = revisar_coherencia(contrato)

    bajo = [d for d in caja_r["curva"] if d["caja"] < minimo] if minimo else []
    critico = bajo[0] if bajo else None
    peor = min(bajo, key=lambda d: d["caja"]) if bajo else None

    # Cuanta historia hay: es lo que decide si el numero se puede mirar.
    meses_hist = 0.0
    if fechas:
        f0 = datetime.date.fromisoformat(min(fechas))
        f1 = datetime.date.fromisoformat(max(fechas))
        meses_hist = ((f1 - f0).days + 1) / 30.44

    return {"corte": corte, "caja": caja_r, "coherencia": coh,
            "posicion": posicion(contrato),
            "fin_periodo": corte + datetime.timedelta(days=dias - 1),
            "critico": critico, "peor": peor, "dias_bajo": len(bajo),
            "minimo": minimo, "dias": dias, "meses_historia": meses_hist,
            "movimientos": len(contrato.get("movimientos", [])),
            "cobros": len(contrato.get("cobros_previstos", []))}



def posicion(contrato):
    """Caja + lo que le deben - lo que debe, SEPARADO POR UNIDAD.

    ERROR CONCEPTUAL QUE HABIA (05/09/2026). Thomas:

        "estas tomando deuda y cobranzas de Speed. MAGA es farmacia, no le vende
         a las droguerias, le COMPRA. Speed es drogueria: le vende y le compra.
         Si bien el dueno es el mismo, los negocios son distintos."

    El informe sumaba todo en una sola posicion y mostraba "te deben las
    droguerias $6.264M" al lado de la deuda de MAGA. Pero a MAGA no le debe
    ninguna drogueria: MAGA es el comprador. Esas cobranzas son de Speedmed.

    Consolidar dos negocios con logicas distintas no es una simplificacion: es
    un numero que no existe. Una farmacia con deuda y una distribuidora con
    cuenta corriente se leen distinto, y el dueno lo sabe aunque la caja sea del
    mismo grupo.

    Por eso ahora se devuelve una posicion POR UNIDAD, y el total solo como
    referencia de caja.
    """
    # Solo cuenta lo PENDIENTE y lo que no es intercompany: la deuda entre
    # empresas del mismo grupo no es plata que salga del grupo.
    def suma(clave, estados, unidad=None):
        return sum(float(x.get("importe") or 0) for x in contrato.get(clave, [])
                   if not x.get("intercompany") and x.get("estado") in estados
                   and (unidad is None or (x.get("unidad") or "") == unidad))

    caja = float(contrato.get("caja_hoy") or 0)
    caja_u = contrato.get("caja_por_unidad") or {}
    debe = suma("deuda_droguerias", ("PENDIENTE",))
    cobrar = suma("cuentas_a_cobrar_droguerias", ("VENCIDO", "A_VENCER"))
    vencido = suma("cuentas_a_cobrar_droguerias", ("VENCIDO",))
    if not debe and not cobrar:
        return None

    # Una posicion por unidad. La que no tiene cuentas a cobrar simplemente no
    # las muestra -- no es que falte un dato, es que ese negocio no vende.
    unidades = sorted(set(
        [(x.get("unidad") or "").strip() for x in contrato.get("deuda_droguerias", [])] +
        [(x.get("unidad") or "").strip() for x in contrato.get("cuentas_a_cobrar_droguerias", [])] +
        [k.strip() for k in caja_u]))
    por_unidad = []
    for u in unidades:
        if not u:
            continue
        d_u = suma("deuda_droguerias", ("PENDIENTE",), u)
        c_u = suma("cuentas_a_cobrar_droguerias", ("VENCIDO", "A_VENCER"), u)
        v_u = suma("cuentas_a_cobrar_droguerias", ("VENCIDO",), u)
        k_u = float(caja_u.get(u) or 0)
        if not (d_u or c_u or k_u):
            continue
        por_unidad.append({"unidad": u, "caja": k_u, "debe": d_u, "cobrar": c_u,
                           "vencido": v_u, "neto": k_u + c_u - d_u})

    # HASTA QUE FECHA LLEGA CARGADA LA DEUDA.
    #
    # Thomas: "hoy a 45 dias tenes mucha mas deuda con droguerias de la que
    # calculaste". Tenia razon y el error era de bulto: yo sumaba las filas
    # PENDIENTE y lo llamaba "deuda". Pero esas filas son los pagos YA
    # PROGRAMADOS, y en el caso de MAGA llegaban hasta el 25/09 mientras la
    # proyeccion iba hasta el 19/10. O sea que el 53% del horizonte no tenia
    # NADA cargado, y la farmacia obviamente sigue comprando todos los dias.
    #
    # Medido: el ritmo cargado era $91.690.016 por dia. Los 24 dias sin cubrir
    # son ~$2.200M de compras nuevas que no figuraban en ningun lado. La deuda
    # real a 45 dias no era $2.690M sino ~$4.891M: casi el doble.
    #
    # No se extrapola sola. Se informa el hueco y su tamano, para que la persona
    # decida. Inventar la cifra seria repetir el error con mejor cara.
    filas = [x for x in contrato.get("deuda_droguerias", [])
             if not x.get("intercompany") and x.get("fecha")]
    cobertura = None
    if filas:
        f0 = min(x["fecha"] for x in filas)
        f1 = max(x["fecha"] for x in filas)
        d0 = datetime.date.fromisoformat(f0)
        d1 = datetime.date.fromisoformat(f1)
        dias = max(1, (d1 - d0).days + 1)
        total = sum(float(x.get("importe") or 0) for x in filas)
        cobertura = {"desde": f0, "hasta": f1, "dias": dias,
                     "por_dia": total / dias}

    return {"caja": caja, "debe": debe, "cobrar": cobrar, "vencido": vencido,
            "neto": caja + cobrar - debe, "cobertura": cobertura,
            "por_unidad": por_unidad}


# ------------------------------------------------------------------ html
CSS = """
:root{--verde:#0a8a4a;--verde-claro:#e8f5ee;--naranja:#e8781a;
      --naranja-claro:#fdf1e6;--gris:#5a6270;--linea:#e2e6ea;--texto:#1c2128}
*{box-sizing:border-box}
body{margin:0;background:#fff;color:var(--texto);
     font:17px/1.6 -apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.hoja{max-width:820px;margin:0 auto;padding:44px 36px 60px}
.hoja+.hoja{border-top:14px solid var(--verde-claro)}
h1{font-size:30px;margin:0 0 4px;letter-spacing:-.3px}
h2{font-size:21px;margin:38px 0 14px;padding-bottom:8px;
   border-bottom:2px solid var(--linea)}
h3{font-size:17px;margin:24px 0 8px;color:var(--gris)}
.sub{color:var(--gris);font-size:15px;margin:0 0 28px}
.tag{display:inline-block;background:var(--verde);color:#fff;font-size:12px;
     font-weight:700;letter-spacing:.6px;padding:4px 11px;border-radius:20px;
     text-transform:uppercase;margin-bottom:14px}
.tag.t2{background:var(--gris)}
.grande{font-size:40px;font-weight:700;letter-spacing:-1px;line-height:1.15}
.cajas{display:flex;gap:16px;flex-wrap:wrap;margin:22px 0}
.caja{flex:1;min-width:190px;border:1px solid var(--linea);border-radius:12px;
      padding:18px 20px}
.caja .rot{font-size:13px;color:var(--gris);text-transform:uppercase;
           letter-spacing:.5px;margin-bottom:6px}
.caja .val{font-size:26px;font-weight:700;letter-spacing:-.5px}
.ok{background:var(--verde-claro);border-color:#b9e0cb}
.ok .val{color:var(--verde)}
.alerta{background:var(--naranja-claro);border-color:#f5cfa8}
.alerta .val{color:var(--naranja)}
.panel{border-left:5px solid var(--verde);background:var(--verde-claro);
       padding:18px 22px;border-radius:0 10px 10px 0;margin:24px 0}
.panel.aviso{border-left-color:var(--naranja);background:var(--naranja-claro)}
.panel p{margin:8px 0}
.panel p:first-child{margin-top:0}
table{width:100%;border-collapse:collapse;margin:16px 0;font-size:15px}
th{text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:.5px;
   color:var(--gris);border-bottom:2px solid var(--linea);padding:8px 10px}
td{padding:9px 10px;border-bottom:1px solid var(--linea)}
td.num{text-align:right;font-variant-numeric:tabular-nums}
tr.rojo td{background:var(--naranja-claro)}
ul{padding-left:22px}li{margin:7px 0}
.pregunta{border:1px solid var(--linea);border-left:5px solid var(--naranja);
          border-radius:0 10px 10px 0;padding:14px 18px;margin:12px 0;
          background:#fff}
.pie{margin-top:44px;padding-top:16px;border-top:1px solid var(--linea);
     color:var(--gris);font-size:13px}
.barra{height:26px;background:var(--verde-claro);border-radius:5px;
       position:relative;overflow:hidden}
.barra i{display:block;height:100%;background:var(--verde)}
.barra.baja i{background:var(--naranja)}
@media print{.hoja{page-break-after:always;padding:0 0 20px}
             .hoja+.hoja{border-top:none}}
"""



def _bloque_periodo(a):
    """Como cierra el ciclo comercial. Va SIEMPRE, incluso cuando la caja no se
    puede proyectar: si no se puede decir cuanta plata va a haber, saber si el
    negocio cierra es justamente lo mas util que queda."""
    p = a.get("posicion")
    if not p:
        return ""
    h = []
    # COMO CIERRA EL PERIODO. Es para entender, no para decidir -- y se dice.
    h.append('<h2>Como cierra el periodo</h2>')
    h.append('<p>Esto no es la caja: es el ciclo comercial. Vos le pagas a '
             'las droguerias a 30, 45 o 60 dias, y a tus clientes les cobras '
             'con los mismos plazos. Sirve para saber si el negocio cierra, '
             'aunque no se decida con esto.</p>')
    h.append('<div class="cajas">')
    h.append('<div class="caja ok"><div class="rot">Vas a cobrar</div>'
             '<div class="val">%s</div></div>' % _m(p["cobrar"]))
    h.append('<div class="caja alerta"><div class="rot">Vas a pagar</div>'
             '<div class="val">%s</div></div>' % _m(p["debe"]))
    dif = p["cobrar"] - p["debe"]
    h.append('<div class="caja %s"><div class="rot">Diferencia</div>'
             '<div class="val">%s</div></div>'
             % ("ok" if dif >= 0 else "alerta", _m(dif)))
    h.append('</div>')
    # Si la deuda esta cargada solo hasta la mitad del periodo, la diferencia
    # NO se puede leer como conclusion: da favorable por construccion, porque
    # falta la mitad de lo que se debe. Ya nos paso una vez y el informe decia
    # que sobraba plata.
    cob = p.get("cobertura")
    incompleta = False
    if cob:
        try:
            ult = datetime.date.fromisoformat(cob["hasta"])
            incompleta = (a["fin_periodo"] - ult).days > 3
        except Exception:
            incompleta = False

    if incompleta:
        h.append('<p><strong>Esta diferencia NO se puede leer todavia.</strong> '
                 'Lo que vas a pagar esta cargado solo hasta el %s, asi que da '
                 'favorable por construccion: falta parte de lo que debes. '
                 'Completando esas fechas, el numero cambia.</p>'
                 % _fecha_larga(cob["hasta"]))
    elif dif >= 0:
        h.append('<p>Te deben mas de lo que debes. El ciclo cierra a favor, '
                 'siempre que se cobre en fecha &mdash; que es otra cosa.</p>')
    else:
        h.append('<p><strong>Debes mas de lo que te deben.</strong> El ciclo '
                 'no cierra solo: la diferencia hay que ponerla de la caja o '
                 'financiarla.</p>')
    if p["vencido"] > 0:
        h.append('<p>Y de lo que te deben, <strong>%s ya esta vencido</strong>. '
                 'Eso no es plazo comercial: es plata que tendrias que tener.</p>'
                 % _m(p["vencido"]))
    h.append('<p class="sub">Ninguno de los dos numeros se cierra dentro de '
             'los %d dias de este informe: son plazos que siguen corriendo '
             'despues. Por eso van aparte del dia a dia.</p>' % a["dias"])
    return chr(10).join(h)


def _pagina_dueno(cliente, a):
    c = a["caja"]
    fin = c["curva"][-1]["caja"] if c["curva"] else 0
    neto = c["total_ingresos"] - c["total_egresos"]

    h = ['<div class="hoja">']
    h.append('<span class="tag">Para el dueno</span>')
    h.append('<h1>%s</h1>' % _e(cliente.upper()))
    h.append('<p class="sub">Como estas parado hoy y como viene la caja en los '
             'proximos %d dias &middot; del %s al %s</p>'
             % (a["dias"], _fecha_larga(c["desde"]), _fecha_larga(c["hasta"])))

    # LA POSICION VA PRIMERO, ANTES QUE CUALQUIER PROYECCION.
    # En una farmacia el grueso del negocio esta en la cuenta corriente con las
    # droguerias. Mostrar solo la caja es mostrar la punta del iceberg.
    p = a.get("posicion")
    if p:
        h.append('<h2>Como estas parado hoy</h2>')
        # UNA POSICION POR NEGOCIO. Consolidar una farmacia (que solo le compra a
        # las droguerias) con una distribuidora (que les compra Y les vende) da
        # un numero que no le sirve a nadie.
        for u in p.get("por_unidad", []):
            h.append('<h3>%s</h3>' % _e(u["unidad"]))
            h.append('<div class="cajas">')
            if u["caja"]:
                h.append('<div class="caja"><div class="rot">En el banco</div>'
                         '<div class="val">%s</div></div>' % _m(u["caja"]))
            if u["cobrar"]:
                h.append('<div class="caja ok"><div class="rot">Le deben</div>'
                         '<div class="val">%s</div></div>' % _m(u["cobrar"]))
            if u["debe"]:
                h.append('<div class="caja alerta"><div class="rot">Le debe a droguerias</div>'
                         '<div class="val">%s</div></div>' % _m(u["debe"]))
            h.append('<div class="caja %s"><div class="rot">Posicion</div>'
                     '<div class="val">%s</div></div>'
                     % ("ok" if u["neto"] >= 0 else "alerta", _m(u["neto"])))
            h.append('</div>')
            if not u["cobrar"] and u["debe"]:
                h.append('<p class="sub">Este negocio le COMPRA a las droguerias y '
                         'no les vende, asi que no tiene cuentas a cobrar con '
                         'ellas.</p>')
            if u["vencido"]:
                h.append('<p class="sub">De lo que le deben, <strong>%s ya esta '
                         'vencido</strong>.</p>' % _m(u["vencido"]))
        h.append('<p class="sub">Lo que te deben y lo que debes NO es plata en el '
                 'banco: es cuenta corriente. Y va separado por negocio: una '
                 'farmacia y una distribuidora no se leen igual aunque el dueno '
                 'sea el mismo.</p>')

        # Si la deuda cargada no llega hasta el final del periodo, decirlo ACA,
        # al lado del numero, y no en una nota al pie que nadie lee.
        cob = p.get("cobertura")
        if cob:
            fin = datetime.date.fromisoformat(c["hasta"])
            ult = datetime.date.fromisoformat(cob["hasta"])
            faltan = (fin - ult).days
            if faltan > 3:
                estimado = cob["por_dia"] * faltan
                h.append('<div class="panel aviso">')
                h.append('<p><strong>Ojo: el "les debes" de arriba esta '
                         'incompleto.</strong></p>')
                h.append('<p>Las compras a droguerias figuran cargadas hasta el %s, '
                         'pero este informe llega hasta el %s. Faltan %d dias en los '
                         'que vas a seguir comprando.</p>'
                         % (_fecha_larga(cob["hasta"]), _fecha_larga(c["hasta"]), faltan))
                h.append('<p>Al ritmo de los ultimos %d dias, en ese hueco se '
                         'sumarian alrededor de <strong>%s</strong> mas de deuda. '
                         'Con eso, lo que deberias al final del periodo estaria mas '
                         'cerca de <strong>%s</strong> que de los %s de arriba.</p>'
                         % (cob["dias"], _m(estimado), _m(p["debe"] + estimado),
                            _m(p["debe"])))
                h.append('<p>Es una cuenta gruesa, no un dato: sirve para no mirar '
                         'el numero de arriba como si fuera todo.</p>')
                h.append('</div>')
        if p["vencido"] > 0:
            h.append('<div class="panel aviso">')
            h.append('<p><strong>Hay %s vencido que todavia no cobraste.</strong></p>'
                     % _m(p["vencido"]))
            h.append('<p>Es %.0f%% de todo lo que te deben. Cobrar eso es la palanca '
                     'mas barata que tenes: no hay que pedirle plazo a nadie ni '
                     'pagar intereses.</p>'
                     % (100.0 * p["vencido"] / p["cobrar"] if p["cobrar"] else 0))
            h.append('</div>')
        h.append('<h2>Y como viene la caja</h2>')

    # SI LOS DATOS NO CIERRAN, NO SE PROYECTA LA CAJA. Y PUNTO.
    #
    # La primera version mostraba "quedarias con $6.840M / la caja aguanta todo
    # el periodo" en la hoja del dueno, y ponia el aviso de que ese numero no era
    # confiable en la hoja tecnica. O sea: la persona que menos entiende recibia
    # el numero mas confiado, y la salvedad quedaba donde solo la lee el que ya
    # la sabe. Es la peor forma posible de estar equivocado.
    #
    # Un asterisco tampoco alcanza: el numero igual queda en la cabeza. Si no se
    # puede afirmar, NO SE MUESTRA. Lo que si se puede afirmar -- cuanto hay que
    # pagar -- se muestra igual, porque eso sirve.
    if a["coherencia"] and a["coherencia"]["avisos"]:
        h.append('<div class="panel aviso">')
        h.append('<p><strong>Todavia no puedo decirte si la caja te alcanza.</strong></p>')
        h.append('<p>Los movimientos cargados no cierran entre si: figuran %s que '
                 'entran y %s que salen en los ultimos meses, y con esa diferencia '
                 'la caja tendria que haber crecido muchisimo mas de lo que crecio.</p>'
                 % (_m(a["coherencia"]["ingresos"]), _m(a["coherencia"]["egresos"])))
        h.append('<p>Puede ser por una razon buena &mdash; que haya compras que se '
                 'cancelan sin pasar por el banco, con notas de credito, endoso de '
                 'cheques o compensando cuentas a cobrar &mdash; o porque hay gastos '
                 'que no se estan registrando. <strong>Son cosas muy distintas y '
                 'necesito confirmarlo con vos antes de darte un numero.</strong></p>')
        h.append('<p>Mientras tanto, lo que si esta firme es lo que hay que pagar.</p>')
        h.append('</div>')

        h.append('<div class="cajas">')
        h.append('<div class="caja"><div class="rot">Tenes hoy</div>'
                 '<div class="val">%s</div></div>' % _m(c["caja_inicial"]))
        h.append('<div class="caja alerta"><div class="rot">Vas a pagar en %d dias</div>'
                 '<div class="val">%s</div></div>' % (a["dias"], _m(c["total_egresos"])))
        h.append('</div>')

        h.append('<h2>Que hay que pagar, semana por semana</h2>')
        h.append('<table><tr><th>Semana del</th><th class="num">A pagar</th></tr>')
        for i in range(0, len(c["curva"]), 7):
            tramo = c["curva"][i:i + 7]
            sale = sum(-x["movimiento"] for x in tramo if x["movimiento"] < 0)
            h.append('<tr><td>%s</td><td class="num">%s</td></tr>'
                     % (_fecha_larga(tramo[0]["fecha"]), _m(sale)))
        h.append('</table>')

        h.append('<h2>Lo que necesito de vos</h2>')
        h.append('<ul><li>Confirmar si hay compras que se cancelan por fuera del '
                 'banco (notas de credito, endoso de cheques, cuentas a cobrar).</li>'
                 '<li>Si no las hay, revisar juntos que gastos no se estan '
                 'cargando en la planilla.</li>'
                 '<li>Con eso resuelto, la proyeccion de caja sale en el acto.</li></ul>')
        # El ciclo comercial SI se puede mostrar: no depende de la caja.
        h.append(_bloque_periodo(a))
        h.append('<div class="pie">Prefiero no darte un numero de caja antes de '
                 'aclarar esto. Un numero optimista es peor que ninguno.</div>')
        h.append('</div>')
        return chr(10).join(h)

    # El titular: la respuesta a "¿me alcanza?", antes que cualquier numero.
    if a["critico"]:
        h.append('<div class="panel aviso">')
        h.append('<p><strong>El %s te quedas corto de plata.</strong></p>'
                 % _fecha_larga(a["critico"]["fecha"]))
        h.append('<p>Ese dia la caja baja a %s, cuando el minimo que necesitas '
                 'para operar tranquilo es %s. Te faltarian %s.</p>'
                 % (_m(a["critico"]["caja"]), _m(a["minimo"]),
                    _m(a["minimo"] - a["critico"]["caja"])))
        if a["dias_bajo"] > 1:
            h.append('<p>No es un solo dia: son %d dias por debajo del minimo.</p>'
                     % a["dias_bajo"])
        h.append('</div>')
    else:
        h.append('<div class="panel">')
        h.append('<p><strong>La caja aguanta todo el periodo.</strong></p>')
        h.append('<p>No hay ningun dia en que baje del minimo de %s.</p>'
                 % _m(a["minimo"]))
        h.append('</div>')

    h.append('<div class="cajas">')
    h.append('<div class="caja"><div class="rot">Tenes hoy</div>'
             '<div class="val">%s</div></div>' % _m(c["caja_inicial"]))
    h.append('<div class="caja ok"><div class="rot">Va a entrar</div>'
             '<div class="val">%s</div></div>' % _m(c["total_ingresos"]))
    h.append('<div class="caja alerta"><div class="rot">Vas a pagar</div>'
             '<div class="val">%s</div></div>' % _m(c["total_egresos"]))
    # NO va un "quedarias con". Ver el docstring: el dia 45 no cierra nada.
    h.append('<div class="caja %s"><div class="rot">Dia mas ajustado</div>'
             '<div class="val">%s</div></div>'
             % ("alerta" if a["critico"] else "ok", _m(a["peor"]["caja"])
                if a["peor"] else _m(min(d["caja"] for d in c["curva"]))))
    h.append('</div>')
    h.append('<p class="sub">No ponemos "con cuanto terminas" a proposito: a los '
             '%d dias el periodo no esta cerrado. Hay deuda que vence despues y '
             'cobranzas que entran despues. Lo que importa es el camino, no el '
             'corte.</p>' % a["dias"])

    h.append('<h2>El dia a dia (esto es con lo que se decide)</h2>')
    h.append('<table><tr><th>Semana del</th><th class="num">Entra menos sale</th>'
             '<th class="num">Como queda la caja</th><th>&nbsp;</th></tr>')
    tope = max(abs(d["caja"]) for d in c["curva"]) or 1
    for i in range(0, len(c["curva"]), 7):
        tramo = c["curva"][i:i + 7]
        d = tramo[-1]
        mov = sum(x["movimiento"] for x in tramo)
        baja = d["caja"] < a["minimo"]
        pct = max(2, min(100, 100 * d["caja"] / tope))
        h.append('<tr class="%s"><td>%s</td><td class="num">%s</td>'
                 '<td class="num"><strong>%s</strong></td>'
                 '<td style="width:34%%"><div class="barra %s"><i style="width:%.0f%%"></i>'
                 '</div></td></tr>'
                 % ("rojo" if baja else "", _fecha_larga(tramo[0]["fecha"]),
                    _m(mov), _m(d["caja"]), "baja" if baja else "", pct))
    h.append('</table>')

    h.append(_bloque_periodo(a))

    h.append('<h2>Que conviene hacer</h2>')
    h.append('<ul>')
    if a["critico"]:
        h.append('<li>Adelantar la conversacion con los proveedores que se '
                 'puedan estirar, <strong>antes</strong> del %s. Llegar al dia '
                 'sin margen es lo que obliga a aceptar cualquier condicion.</li>'
                 % _fecha_larga(a["critico"]["fecha"]))
        h.append('<li>Revisar si hay cobros que se puedan apurar en esos dias.</li>')
    else:
        h.append('<li>La caja da. Es un buen momento para negociar plazos y '
                 'precios desde una posicion comoda, que es cuando se consigue.</li>')
    h.append('<li>Volver a mirar esto en dos semanas: la proyeccion se hace mejor '
             'a medida que hay mas historia cargada.</li>')
    h.append('</ul>')

    h.append('<div class="pie">Esto es una proyeccion a partir de los movimientos '
             'de los ultimos meses, no una certeza. Sirve para ver con tiempo '
             'donde puede apretar la caja.</div>')
    h.append('</div>')
    return "\n".join(h)


def _pagina_thomas(cliente, a, contrato, medicion):
    c = a["caja"]
    h = ['<div class="hoja">']
    h.append('<span class="tag t2">Detalle tecnico</span>')
    h.append('<h1>%s &mdash; respaldo</h1>' % _e(cliente.upper()))
    h.append('<p class="sub">De donde sale cada numero de la hoja anterior y '
             'cuanto puede errar.</p>')

    h.append('<h2>Con que datos se hizo</h2>')
    h.append('<table>')
    h.append('<tr><td>Historia disponible</td><td class="num">%.1f meses</td></tr>'
             % a["meses_historia"])
    h.append('<tr><td>Movimientos de egreso</td><td class="num">%d</td></tr>'
             % a["movimientos"])
    h.append('<tr><td>Movimientos de ingreso</td><td class="num">%d</td></tr>'
             % a["cobros"])
    h.append('<tr><td>Fecha de corte</td><td class="num">%s</td></tr>'
             % c["desde"])
    h.append('</table>')

    if a["meses_historia"] < 3:
        h.append('<div class="panel aviso"><p><strong>Poca historia: '
                 '%.1f meses.</strong> El motor necesita al menos 3 para '
                 'reconocer que se repite. Los numeros de la hoja anterior hay '
                 'que tomarlos como una primera aproximacion y ajustarlos a '
                 'mano con el cliente.</p></div>' % a["meses_historia"])

    if medicion:
        h.append('<h2>Cuanto erra este motor con estos datos</h2>')
        h.append('<p>Se proyectaron tramos que <strong>ya pasaron</strong>, '
                 'aprendiendo solo con lo anterior, y se comparo contra lo real.</p>')
        h.append('<table><tr><th>Corte</th><th class="num">Proyectado</th>'
                 '<th class="num">Real</th><th class="num">Error</th></tr>')
        for m in medicion:
            h.append('<tr><td>%s</td><td class="num">%s</td><td class="num">%s</td>'
                     '<td class="num">%+.0f%%</td></tr>'
                     % (m["corte"], _m(m["proy"]), _m(m["real"]), m["err"]))
        h.append('</table>')

    # Perfiles: lo que el motor cree que es cada rubro.
    pe = c.get("perfiles_egresos", {})
    # Se filtran las claves vacias: son los movimientos que quedaron sin tipo.
    # No aportan nada en la lista y quedan como una coma suelta al principio.
    dif = sorted([p["clave"] for p in pe.values()
                  if p["perfil"] == "difuso" and p["clave"].strip()])
    eve = sorted([p["clave"] for p in pe.values()
                  if p["perfil"] == "evento" and p["clave"].strip()])
    sin_tipo = [p for p in pe.values() if not p["clave"].strip()]
    p = a.get("posicion")
    if p:
        h.append('<h2>La posicion, desglosada</h2>')
        h.append('<table>')
        h.append('<tr><td>Caja (bancos + efectivo)</td><td class="num">%s</td></tr>'
                 % _m(p["caja"]))
        h.append('<tr><td>Cuentas a cobrar a droguerias</td><td class="num">%s</td></tr>'
                 % _m(p["cobrar"]))
        h.append('<tr><td style="padding-left:26px;color:#5a6270">de las cuales '
                 'VENCIDAS</td><td class="num">%s</td></tr>' % _m(p["vencido"]))
        h.append('<tr><td>Deuda con droguerias (solo PENDIENTE)</td>'
                 '<td class="num">-%s</td></tr>' % _m(p["debe"]))
        h.append('<tr><td><strong>Posicion</strong></td>'
                 '<td class="num"><strong>%s</strong></td></tr>' % _m(p["neto"]))
        h.append('</table>')
        cob = p.get("cobertura")
        if cob:
            h.append('<h3>Hasta donde llega cargada la deuda</h3>')
            h.append('<table>')
            h.append('<tr><td>Filas de deuda, desde / hasta</td>'
                     '<td class="num">%s a %s</td></tr>' % (cob["desde"], cob["hasta"]))
            h.append('<tr><td>Ritmo observado</td><td class="num">%s por dia</td></tr>'
                     % _m(cob["por_dia"]))
            fin = datetime.date.fromisoformat(c["hasta"])
            ult = datetime.date.fromisoformat(cob["hasta"])
            faltan = max(0, (fin - ult).days)
            h.append('<tr><td>Dias del horizonte sin deuda cargada</td>'
                     '<td class="num">%d de %d</td></tr>' % (faltan, a["dias"]))
            if faltan:
                h.append('<tr><td>Compras nuevas estimadas en ese hueco</td>'
                         '<td class="num">%s</td></tr>' % _m(cob["por_dia"] * faltan))
            h.append('</table>')
            h.append('<p class="sub">La extrapolacion es lineal a proposito y NO se '
                     'usa para ningun calculo: solo para dimensionar el hueco. Si el '
                     'ritmo de compra sigue otro patron (mas fuerte a fin de mes, '
                     'atado a la venta), preguntarselo al cliente.</p>')

        h.append('<p class="sub">No se cuentan los saldos intercompany ni la deuda '
                 'ya marcada como PAGADO. Estos saldos no son caja: se muestran '
                 'aparte a proposito, pero omitirlos daria una foto irreal.</p>')

    h.append('<h2>Como modela cada rubro</h2>')
    h.append('<p><strong>Difusos</strong> (pasan casi todos los dias habiles, se '
             'modelan como un ritmo diario): %s</p>'
             % (_e(", ".join(dif)) if dif else "ninguno"))
    h.append('<p><strong>Eventos</strong> (caen en dias puntuales del mes): %s</p>'
             % (_e(", ".join(eve[:18])) + (" ..." if len(eve) > 18 else "")
                if eve else "ninguno"))
    if sin_tipo:
        h.append('<p class="sub">Hay movimientos <strong>sin rubro asignado</strong>. '
                 'El motor no los puede modelar: preguntarle al cliente que son.</p>')

    if a["coherencia"] and a["coherencia"]["avisos"]:
        h.append('<h2>Revisar antes de creerle a la curva</h2>')
        h.append('<div class="panel aviso">')
        h.append('<p>En los ultimos %d meses el contrato registra <strong>%s</strong> '
                 'que entran y <strong>%s</strong> que salen.</p>'
                 % (a["coherencia"]["meses"], _m(a["coherencia"]["ingresos"]),
                    _m(a["coherencia"]["egresos"])))
        for av in a["coherencia"]["avisos"]:
            h.append('<p>%s</p>' % _e(av))
        h.append('</div>')

    h.append('<h2>Para la proxima visita</h2>')
    h.append('<ul>')
    h.append('<li>Guardar la proyeccion de hoy: <code>python memoria/registro.py '
             'guardar --contrato &lt;c&gt; --cliente %s</code></li>' % _e(cliente))
    h.append('<li>Al volver, conciliar: muestra que se cumplio, que se corrio de '
             'fecha y que aparecio sin estar previsto. <strong>Eso es lo que '
             'hace que la segunda visita valga mas que la primera.</strong></li>')
    if a["meses_historia"] < 6:
        h.append('<li>Pedir mas historia: con %.0f meses el motor todavia esta '
                 'aprendiendo.</li>' % a["meses_historia"])
    h.append('</ul>')

    h.append('<div class="pie">Generado por finauto el %s. Los numeros salen de '
             'los movimientos cargados, no de una estimacion manual.</div>'
             % datetime.date.today().strftime("%d/%m/%Y"))
    h.append('</div>')
    return "\n".join(h)


def armar_html(cliente, a, contrato, medicion):
    return ("<!doctype html><html lang=\"es\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>%s - informe de caja</title><style>%s</style></head><body>%s%s"
            "</body></html>" % (_e(cliente), CSS,
                                _pagina_dueno(cliente, a),
                                _pagina_thomas(cliente, a, contrato, medicion)))


def medir(contrato, corte, dias):
    """Backtest en tramos que ya pasaron. Si no hay historia, no se inventa."""
    out = []
    for atras in (120, 90, 60):
        d = corte - datetime.timedelta(days=atras)
        try:
            r = backtest_horizonte(contrato.get("movimientos", []), d, dias)
        except Exception:
            continue
        if r["total_real"] and r["perfiles"]:
            out.append({"corte": d.isoformat(), "proy": r["total_proy"],
                        "real": r["total_real"],
                        "err": 100.0 * (r["total_proy"] - r["total_real"]) / r["total_real"]})
    return out


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="Informe de visita a un cliente")
    ap.add_argument("--contrato", required=True)
    ap.add_argument("--cliente", required=True)
    ap.add_argument("--caja", type=float, help="saldo de hoy (si no, sale del contrato)")
    ap.add_argument("--dias", type=int, default=45)
    ap.add_argument("--minimo", type=float, default=0, help="caja minima de seguridad")
    ap.add_argument("--salida")
    args = ap.parse_args()

    with io.open(args.contrato, encoding="utf-8") as f:
        contrato = json.load(f)

    caja = args.caja if args.caja is not None else float(contrato.get("caja_hoy") or 0)
    a = analizar(contrato, caja, args.dias, args.minimo)
    med = medir(contrato, a["corte"], args.dias)

    salida = args.salida or os.path.join(
        BASE_REPO, "clientes", args.cliente,
        "informe_%s.html" % datetime.date.today().isoformat())
    d = os.path.dirname(salida)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with io.open(salida, "w", encoding="utf-8") as f:
        f.write(armar_html(args.cliente, a, contrato, med))

    print("  Informe: %s" % salida)
    print("  Pagina 1: para el dueno   .   Pagina 2: el respaldo tecnico")
    if a["critico"]:
        print("  [!] Dia critico: %s (%s)" % (a["critico"]["fecha"],
                                              _m(a["critico"]["caja"])))
    else:
        print("  [OK] La caja no baja del minimo en el periodo.")


if __name__ == "__main__":
    main()
