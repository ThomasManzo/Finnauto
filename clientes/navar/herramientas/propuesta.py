# -*- coding: utf-8 -*-
"""
propuesta — el PDF para la dueña de NAVAR: qué encontramos, qué armamos, qué sigue.

PARA QUIÉN
----------
Thomas (12/09/2026): "armemos bien un pdf que sea limpio y claro con los errores
que encontramos, cómo va a funcionar la planilla que armamos, hasta dónde
podemos automatizar y un ejemplo visual de cómo se vería el dashboard [...] y
cómo seguimos, qué datos faltan, qué tienen que sumar desde su lado y qué no
comprendemos desde nuestro lado".

Lo lee la dueña de la empresa. Entonces: nada de software, repos ni tests.
Frases cortas, números con nombre, y en cada sección un "qué significa para
vos". Los montos salen del contrato y del diagnóstico, no se tipean.

Uso:
    python clientes/navar/herramientas/propuesta.py
    (deja privado/salidas/NAVAR - Propuesta finauto <fecha>.pdf)
"""

import io
import os
import sys
import json
import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # clientes/navar/
REPO = os.path.dirname(os.path.dirname(BASE))
PRIVADO = os.path.join(BASE, "privado")
CAPTURAS = os.path.join(PRIVADO, "capturas")
SALIDAS = os.path.join(PRIVADO, "salidas")

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                PageBreak, Image, KeepTogether)

TINTA = colors.HexColor("#14211B")
SUAVE = colors.HexColor("#55645C")
TENUE = colors.HexColor("#8A968E")
LINEA = colors.HexColor("#DDE5E0")
VERDE = colors.HexColor("#0F7A4F")
ROJO = colors.HexColor("#B3261E")
AMBAR = colors.HexColor("#96690A")
FONDO = colors.HexColor("#F4F7F5")
ROJO_FONDO = colors.HexColor("#FBEDEB")

b = ParagraphStyle("b", fontName="Helvetica", fontSize=10, leading=14.5, textColor=TINTA,
                   alignment=TA_LEFT, spaceAfter=7)
E = {
    "titulo": ParagraphStyle("titulo", parent=b, fontName="Helvetica-Bold", fontSize=26, leading=31, spaceAfter=6),
    "sub": ParagraphStyle("sub", parent=b, fontSize=12, leading=17, textColor=SUAVE, spaceAfter=18),
    "h1": ParagraphStyle("h1", parent=b, fontName="Helvetica-Bold", fontSize=17, leading=21, spaceBefore=4, spaceAfter=8),
    "h2": ParagraphStyle("h2", parent=b, fontName="Helvetica-Bold", fontSize=8.5, textColor=TENUE, spaceBefore=14, spaceAfter=5, leading=11),
    "h3": ParagraphStyle("h3", parent=b, fontName="Helvetica-Bold", fontSize=11.5, spaceBefore=8, spaceAfter=3),
    "p": b,
    "grande": ParagraphStyle("grande", parent=b, fontSize=12.5, leading=18),
    "li": ParagraphStyle("li", parent=b, leftIndent=12, bulletIndent=2, spaceAfter=3),
    "nota": ParagraphStyle("nota", parent=b, fontSize=8.6, textColor=TENUE, leading=11.5, spaceBefore=2),
    "cita": ParagraphStyle("cita", parent=b, fontName="Helvetica-Oblique", leftIndent=11, textColor=SUAVE, spaceAfter=5),
    "kpi_n": ParagraphStyle("kpi_n", parent=b, fontName="Helvetica-Bold", fontSize=18, leading=22, spaceAfter=0),
    "kpi_t": ParagraphStyle("kpi_t", parent=b, fontSize=8.5, textColor=SUAVE, leading=11, spaceAfter=0),
}


def P(txt, st="p"):
    return Paragraph(txt, E[st])


def LI(txt):
    return Paragraph(txt, E["li"], bulletText="·")


def tabla(filas, anchos, cabecera=True, chico=False, zebra=True):
    filas = [[Paragraph(str(c), ParagraphStyle("c", parent=b, fontSize=8.4 if chico else 9, leading=11.5 if chico else 12.5, spaceAfter=0))
              if not isinstance(c, Paragraph) else c for c in f] for f in filas]
    t = Table(filas, colWidths=anchos, hAlign="LEFT", repeatRows=1 if cabecera else 0)
    st = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINEA),
    ]
    if cabecera:
        st += [("BACKGROUND", (0, 0), (-1, 0), FONDO), ("LINEBELOW", (0, 0), (-1, 0), 0.8, TENUE)]
    t.setStyle(TableStyle(st))
    return t


def kpis(items, ancho=170 * mm):
    """Tres o cuatro numeros grandes en una fila."""
    fila1 = [Paragraph(v, ParagraphStyle("k", parent=E["kpi_n"], textColor=col)) for v, _, col in items]
    fila2 = [Paragraph(t, E["kpi_t"]) for _, t, _ in items]
    t = Table([fila1, fila2], colWidths=[ancho / len(items)] * len(items), hAlign="LEFT")
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), FONDO), ("TOPPADDING", (0, 0), (-1, 0), 10),
                           ("BOTTOMPADDING", (0, 1), (-1, 1), 10), ("LEFTPADDING", (0, 0), (-1, -1), 10),
                           ("LINEAFTER", (0, 0), (-2, -1), 0.6, colors.white)]))
    return t


def imagen(nombre, ancho=170 * mm, alto_max=None):
    ruta = os.path.join(CAPTURAS, nombre)
    if not os.path.exists(ruta):
        return P("(falta la captura %s)" % nombre, "nota")
    from reportlab.lib.utils import ImageReader
    iw, ih = ImageReader(ruta).getSize()
    alto = ancho * ih / float(iw)
    if alto_max and alto > alto_max:
        alto = alto_max
        ancho = alto * iw / float(ih)
    img = Image(ruta, width=ancho, height=alto)
    img.hAlign = "LEFT"
    return img


def caja(flowables, color=FONDO, borde=None):
    t = Table([[flowables]], colWidths=[170 * mm], hAlign="LEFT")
    st = [("BACKGROUND", (0, 0), (-1, -1), color), ("LEFTPADDING", (0, 0), (-1, -1), 12),
          ("RIGHTPADDING", (0, 0), (-1, -1), 12), ("TOPPADDING", (0, 0), (-1, -1), 9),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 9)]
    if borde:
        st.append(("LINEBEFORE", (0, 0), (0, -1), 3, borde))
    t.setStyle(TableStyle(st))
    return t


def m(v, corto=False):
    v = float(v or 0)
    if corto:
        return ("-" if v < 0 else "") + "$" + ("%.0f M" % (abs(v) / 1e6)).replace(".", ",")
    return ("-" if v < 0 else "") + "$" + format(int(round(abs(v))), ",d").replace(",", ".")


def pie(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(TENUE)
    canvas.drawString(20 * mm, 12 * mm, "NAVAR S.A. · Propuesta de trabajo · Thomas Manzo · %s" % HOY_TXT)
    canvas.drawRightString(190 * mm, 12 * mm, "Confidencial · página %d" % doc.page)
    canvas.restoreState()


HOY = datetime.date.today()
HOY_TXT = HOY.strftime("%d/%m/%Y")


def numeros():
    """Lo que el PDF dice con numero sale del contrato, no se tipea."""
    ruta = os.path.join(BASE, "contrato_2026-08-31.json")
    with io.open(ruta, encoding="utf-8") as f:
        c = json.load(f)
    sys.path.insert(0, REPO)
    from dashboard import datos as DA
    p = DA.armar(c, "navar")
    g = p["datos"]["GRUPO"]
    pr = g["proyeccion"]
    saldo, minimo = pr["caja_inicial"], (None, 1e18)
    for d in pr["dias"]:
        saldo += d["entra"] - sum(d["sale"].values())
        if saldo < minimo[1]:
            minimo = (d["fecha"], saldo)
    # El mismo saldo si lo ya vencido se sigue sin pagar (el escenario "pateando").
    vencido_curva = sum(i["monto"] for i in pr["items"] if i["grupo"] == "vencido")
    saldo_sin_regularizar = saldo + vencido_curva
    imp = sum(x["importe"] for x in c["deuda_impositiva"] if x["fecha"] < "2026-08-31")
    imp_flujo = sum(x["importe"] for x in c["deuda_impositiva"] if x["fecha"] >= "2026-08-31")
    cuotas = sum(x["importe"] for x in c["deuda_bancaria"]["cuotas"])
    cap = sum(x["capital_vigente"] for x in c["deuda_bancaria"]["lineas"])
    cheques = sum(x["importe"] for x in c["cartera_cheques"])
    proy = sum(x["importe"] for x in c["cobros_previstos"] if x["fuente"] == "COBRANZA_PROYECTADA" and x["fecha"] >= "2026-08-31")
    ing = sum(x["importe"] for x in c["cobros_previstos"] if x["fecha"] >= "2026-08-31") + \
        sum(x["importe"] for x in c["cuentas_a_cobrar_droguerias"])
    return {
        "caja": c["caja_hoy"], "caja_A": c["caja_por_unidad"].get("A", 0), "caja_AA": c["caja_por_unidad"].get("AA", 0),
        "cheques": cheques, "vencido_prov": g["kpis"]["vencido"], "prov_8sem": sum(x["importe"] for x in c["deuda_droguerias"] if x["fecha"] >= "2026-08-31"),
        "imp_atrasada": imp, "imp_flujo": imp_flujo, "cuotas": cuotas, "capital": cap,
        "entra45": pr["total_entra"], "sale45": pr["total_sale"] - vencido_curva, "saldo45": saldo,
        "saldo45_sin_regularizar": saldo_sin_regularizar, "vencido_curva": vencido_curva,
        "min_fecha": minimo[0], "min_saldo": minimo[1],
        "proy_kg": proy, "ing_8sem": ing, "pct_kg": 100.0 * proy / ing if ing else 0,
    }


def armar():
    N = numeros()
    out = os.path.join(SALIDAS, "NAVAR - Propuesta finauto %s.pdf" % HOY.isoformat())
    doc = SimpleDocTemplate(out, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=18 * mm, bottomMargin=20 * mm,
                            title="NAVAR S.A. — Propuesta de trabajo", author="Thomas Manzo")
    S = []

    # ------------------------------------------------------------ portada
    S += [Spacer(1, 40 * mm),
          P("NAVAR S.A.", "titulo"),
          P("Ordenar la caja, proyectarla y automatizarla", "sub"),
          P("Qué encontramos en el cash actual, cómo funciona la planilla nueva, qué muestra el "
            "tablero, hasta dónde se puede automatizar y qué hace falta para seguir.", "grande"),
          Spacer(1, 14 * mm),
          P("Preparado por <b>Thomas Manzo</b> · %s" % HOY_TXT),
          P("Datos: cash flow de NAVAR al 31/08/2026 (semanas del 20/07 al 24/08 cerradas, "
            "proyección del 31/08 al 19/10).", "nota"),
          P("Este documento contiene información financiera de NAVAR S.A. No se comparte con terceros.", "nota"),
          PageBreak()]

    # ------------------------------------------------------------ resumen
    S += [P("En una página", "h1"),
          P("<b>Lo que encontramos.</b> El cash flow semanal con el que hoy se decide tiene <b>10 errores "
            "de fórmula</b> y su proyección de ingresos a una semana le erra, en promedio, un <b>49%</b>. "
            "No es un problema de la persona que lo carga: es la herramienta, que se copia y se pisa cada "
            "lunes. El número que más se mira —la deuda total— está midiendo otra cosa."),
          P("<b>Lo que armamos.</b> Una planilla nueva en Google Sheets, compartida, donde cada movimiento, "
            "factura, cheque y vencimiento es <b>una fila</b>, y el cash flow (por día, semana y mes) se "
            "calcula solo. Ya tiene cargadas las 6 semanas reales y las 8 proyectadas del cash viejo. "
            "Y un tablero que la lee y contesta las tres preguntas de todas las semanas: cuánto hay, a "
            "quién pagar primero, y qué día se queda corta la caja."),
          P("<b>Lo que muestra hoy, con sus números.</b>")]
    S += [kpis([(m(N["caja"], True), "en bancos y efectivo al 31/08 (sin contar cheques)", TINTA),
                (m(N["cheques"], True), "en cheques de terceros en cartera", AMBAR),
                (m(N["vencido_prov"], True), "vencido con proveedores", ROJO),
                (m(N["imp_atrasada"] + N["capital"], True), "deuda impositiva + bancaria declarada", ROJO)]),
          Spacer(1, 4 * mm),
          P("A 45 días, con lo cargado hoy, <b>entran %s y salen %s</b> de lo que vence en ese período: la caja "
            "llega a <b>%s</b> el 12/10 <i>si lo ya vencido se sigue sin pagar</i>. Si además se regulariza lo "
            "vencido (%s entre proveedores y ARCA), llega a <b>%s</b>. Ninguno de los dos números se arregla "
            "corriendo pagos. El dato más importante de esa cuenta: <b>el %d%% de lo que entra es la \"cobranza "
            "proyectada por kilo\"</b>, una estimación, no una factura. Ordenar eso es lo primero."
            % (m(N["entra45"]), m(N["sale45"]), m(N["saldo45_sin_regularizar"]), m(N["vencido_curva"]),
               m(N["saldo45"]), round(N["pct_kg"]))),
          P("Los números son del grupo. La vista por empresa (A / AA) todavía no es confiable: el cash viejo no "
            "separaba la mayoría de los pagos por empresa y se asignaron a \"A\" hasta confirmarlo.", "nota"),
          P("<b>Lo que sigue.</b> Tres cosas de su lado (los listados de Tango, el detalle de préstamos y "
            "de deuda con ARCA, y una hora con quien carga los números) y el tablero pasa de \"con los "
            "números del cash viejo\" a \"con los números reales\". Después, en etapas, se automatiza la "
            "carga hasta que el lunes a la mañana el cash esté hecho antes de que llegue nadie."),
          PageBreak()]

    # ------------------------------------------------------------ errores
    S += [P("1 · Lo que encontramos en el cash actual", "h1"),
          P("Revisamos la planilla \"CASH FLOW 31-08\" celda por celda, con las seis pestañas semanales "
            "que trae. Todo lo de abajo está verificado en la fórmula."),
          P("Errores de fórmula", "h2")]
    filas = [["#", "Qué pasa", "Efecto"],
             ["1", "El saldo inicial del 21/09 arranca del cierre del 07/09, salteando la semana del 14/09.", "Las últimas 5 semanas de la proyección están $35,9 M más bajas de lo que la propia planilla calcula."],
             ["2", "El saldo final del 31/08 usa el saldo <i>antes</i> del \"ajuste vs. semana anterior\" (-$49,9 M).", "Dice -$16,1 M; el correcto es -$66,0 M. Todas las semanas siguientes arrastran $49,9 M de más."],
             ["3", "Los cheques en cartera se suman al saldo inicial como si fueran plata.", "Del \"saldo inicial\" de $165 M, $124 M (75%) son cheques que todavía no se cobraron."],
             ["4", "En las semanas proyectadas, el pago previsto de impuestos, proveedores y préstamos se carga como deuda <i>nueva</i>. En la columna Real, el mismo pago la <i>baja</i>.", "La \"Deuda total final\" de -$2.157 M al 19/10 no es una proyección: es la deuda de hoy más todos los pagos previstos sumados encima."],
             ["5", "El total de \"Cheques emitidos\" suma las columnas Proyectado + Real + Variación.", "Muestra $85,6 M; el correcto es $46,9 M."],
             ["6", "El \"Proyectado\" de egresos está tipeado, no calculado, y quedó pegado tres semanas seguidas (-$248,2 M).", "La columna \"Variación\" de esas semanas comparó contra un número que no era."],
             ["7", "\"Saldo Acumulado\" acumula saldos que ya vienen acumulados.", "El -$1.052 M de esa fila no significa nada."],
             ["8", "\"Prom mens\" divide por 3 un total de 8 semanas.", "Promedio mensual subestimado ~35%."],
             ["9", "En julio, \"Cobranzas en cheques\" ($193 M y $140 M) contadas como ingreso y \"Venta de valores\" ($60 M y $206 M) como egreso.", "Son movimientos de cartera, no de caja. En agosto esas filas desaparecen sin explicación."],
             ["10", "La deuda bancaria final del 14/09 ignora el movimiento de la semana; dos pestañas rotuladas con la misma fecha.", "Sin efecto hoy; explota cuando carguen algo."]]
    S += [tabla(filas, [8 * mm, 86 * mm, 76 * mm], chico=True)]
    S += [PageBreak(), P("Cuánto le erra la proyección (medido con sus propias pestañas)", "h2"),
          P("Cada pestaña guarda lo que se proyectó para la semana y lo que pasó. Con eso se puede medir "
            "sin opinar:")]
    filas = [["Semana", "Ingresos proy.", "Ingresos real", "Error", "Egresos proy.", "Egresos real", "Error"],
             ["20/07", "148 M", "277 M", "+88%", "-362 M", "-166 M", "+54%"],
             ["27/07", "177 M", "207 M", "+17%", "-97 M", "-304 M", "-213%"],
             ["03/08", "198 M", "130 M", "-34%", "-248 M", "-141 M", "+43%"],
             ["10/08", "166 M", "121 M", "-27%", "-248 M", "-92 M", "+63%"],
             ["17/08", "410 M", "140 M", "-66%", "-248 M", "-110 M", "+56%"],
             ["24/08", "210 M", "335 M", "+59%", "-327 M", "-211 M", "+35%"]]
    S += [tabla(filas, [18 * mm, 27 * mm, 27 * mm, 18 * mm, 27 * mm, 27 * mm, 18 * mm], chico=True),
          Spacer(1, 3 * mm),
          LI("<b>Ingresos:</b> error promedio del <b>49%</b>, para arriba y para abajo."),
          LI("<b>Egresos:</b> el real quedó <b>por debajo</b> de lo proyectado 5 semanas de 6. Se proyecta lo que "
             "<i>vence</i>, no lo que se va a <i>pagar</i>."),
          LI("<b>La \"cobranza proyectada por kg\" es el 67% de los ingresos de las próximas 8 semanas</b> ($746 M de "
             "$1.114 M) y en las seis pestañas su \"real\" es siempre cero: cuando entra, se anota como cobranza "
             "de facturas. <b>Nunca se pudo medir si acierta.</b>"),
          Spacer(1, 3 * mm),
          KeepTogether(caja([P("<b>Qué significa para vos.</b> La pregunta semanal —\"qué pago priorizo\"— es la correcta. "
                  "Pero la herramienta con la que hoy se contesta tiene la deuda mal calculada (error 4), la caja "
                  "inflada con cheques (error 3) y una proyección de ingresos que no se puede controlar. No es "
                  "que la persona que carga se equivoque: es que cada lunes se copia una pestaña y se pisa la "
                  "anterior, y nadie puede revisar nada.")], borde=ROJO, color=ROJO_FONDO)),
          PageBreak()]

    # ------------------------------------------------------------ planilla nueva
    S += [P("2 · Cómo funciona la planilla nueva", "h1"),
          P("Está en Google Drive como <b>\"NAVAR - Cash Flow\"</b>, para que la usen todos los que "
            "cargan y todos los que miran. La idea de fondo cambia: <b>no se carga el cash flow, se cargan "
            "los hechos</b> (un pago, una factura, un cheque, un vencimiento) y el cash flow se arma solo."),
          P("Las solapas", "h2")]
    filas = [["Solapa", "Qué se carga ahí", "Quién / cuándo"],
             ["Movimientos", "Todo lo que entró y salió de plata, día por día. Es la fuente de lo REAL. También lo proyectado que no tiene detalle (sueldos, cosecha, estampillas).", "Oficina, los lunes (después: solo de Tango)"],
             ["Cuentas a Cobrar", "Factura por factura lo que deben los clientes, con vencimiento. Se marca cobrado cuando entra.", "De Tango"],
             ["Cuentas a Pagar", "Factura por factura lo que se le debe a cada proveedor, con vencimiento. <b>Hoy no existe una lista así</b>: sin ella no hay forma real de decidir a quién pagar primero.", "De Tango"],
             ["Cartera de Cheques", "Cheques propios emitidos y de terceros recibidos, con su fecha real de pago o cobro. Separa la plata (banco) del papel (cheques).", "De Tango"],
             ["Saldos Bancarios", "El saldo real de cada banco y cada empresa, sin cheques adentro.", "Extractos, los lunes"],
             ["Deuda Bancaria", "Cada línea de crédito con su capital, tasa y situación BCRA, y el cronograma cuota por cuota.", "Una vez; después se marcan las cuotas pagadas"],
             ["Deuda Impositiva", "Cada vencimiento de ARCA / provincia, con estado (pendiente, pagado, plan de pago).", "Con el contador"],
             ["Cash Flow Consolidado", "<b>No se carga nada.</b> Por día, semana y mes, calculado solo desde las listas. Arriba, un bloque con lo vencido a la fecha.", "Se mira"],
             ["Posición de Deuda", "<b>No se carga nada.</b> Pendiente / vencido / vence en 7, 30 y 90 días, por proveedores, impuestos, bancos y cheques.", "Se mira"],
             ["Vista Semanal", "La bitácora: qué se proyectó cada semana y qué pasó. La llena el sistema.", "Automático"]]
    S += [tabla(filas, [32 * mm, 98 * mm, 40 * mm], chico=True),
          P("Tres reglas que hacen que funcione", "h2"),
          LI("<b>Un hecho, una fila.</b> Nada se suma a mano. Si un número está mal, se busca la fila y se corrige ahí."),
          LI("<b>Lo vencido no desaparece.</b> Una factura vencida e impaga sigue apareciendo en \"vencido a la fecha\" "
             "hasta que se paga. En el cash viejo se perdía."),
          LI("<b>Los cheques no son plata hasta que se cobran.</b> Un cheque de terceros entra a la cartera con su fecha; "
             "es caja recién ese día, y solo si se deposita."),
          P("Lo que ya está cargado", "h2"),
          P("Las 6 semanas reales (20/07 al 24/08) y las 8 proyectadas (31/08 al 19/10) del cash viejo, más los "
            "saldos de deuda declarados al 31/08. Están marcadas como <b>\"agregado del cash viejo\"</b> porque son "
            "totales semanales, no el detalle factura por factura: se reemplazan cuando lleguen los listados de "
            "Tango."),
          PageBreak()]

    # ------------------------------------------------------------ tablero
    S += [P("3 · El tablero", "h1"),
          P("Lee la planilla y contesta, empresa por empresa (A, AA y el grupo), lo que se pregunta todos "
            "los lunes. Las capturas son con los datos reales cargados hoy."),
          KeepTogether([
              P("Posición: cuánto hay, cuánto se debe, cuándo se queda corta", "h2"),
              imagen("tablero_posicion_arriba.png", alto_max=95 * mm),
              P("Caja de hoy sin cheques, deuda ya vencida con proveedores, lo que vence en la semana. Abajo, lo que "
                "entra día por día y en qué se va la plata en 45 días.", "nota")]),
          Spacer(1, 4 * mm),
          KeepTogether([
              P("Proyección: el día crítico, y qué se puede correr para llegar", "h2"),
              imagen("tablero_proyeccion_capa.png", alto_max=118 * mm),
              P("La curva de caja a 7, 14, 30 o 45 días. Lo ya vencido entra el primer día (se puede destildar "
                "para ver el escenario \"si lo sigo pateando\"). Marca el día en que la caja se da vuelta y propone "
                "qué pagos correr —en orden de consecuencia, no de monto— y cuánto cuesta. Con los datos de hoy la "
                "respuesta es dura: <i>no se arregla pateando pagos</i>. Ese es justamente el dato.", "nota")]),
          Spacer(1, 4 * mm),
          KeepTogether([
              P("A quién pagar: el reparto de la semana", "h2"),
              imagen("tablero_a_quien_pagar_capa.png", alto_max=80 * mm),
              P("Cada proveedor con su vencido, lo que vence pronto y el atraso acumulado. Cuando esté la lista de "
                "Cuentas a Pagar de Tango, acá aparece cada proveedor con nombre y cuánto aguanta antes de cortar.", "nota")]),
          Spacer(1, 4 * mm),
          KeepTogether([
              P("A cobrar: quién nos debe y qué cheques tenemos", "h2"),
              imagen("tablero_a_cobrar_capa.png", alto_max=105 * mm),
              P("Lo facturado y no cobrado por cliente, y cada cheque en cartera con su decisión pendiente "
                "(depositar o endosar).", "nota")]),
          Spacer(1, 3 * mm),
          caja([P("<b>Qué significa para vos.</b> El tablero no reemplaza a nadie: la persona de oficina sigue "
                  "cargando, el contador sigue con los impuestos. Lo que cambia es que <b>la decisión del lunes "
                  "deja de depender de una pestaña copiada</b>, y que cada semana queda registrado qué se dijo "
                  "que iba a pasar. A los dos meses se puede medir cuánto le erra la proyección, y bajarlo.")]),
          PageBreak()]

    # ------------------------------------------------------------ automatizacion
    S += [P("4 · Hasta dónde se puede automatizar", "h1"),
          P("En etapas, y cada etapa se justifica sola. Nada de la etapa siguiente arranca sin que la anterior "
            "esté andando."),
          ]
    filas = [["Etapa", "Qué", "Qué cambia el lunes a la mañana", "Qué hace falta"],
             ["1 · Ahora", "La planilla nueva + el tablero semanal. Carga manual desde Tango y extractos.", "La carga sigue a mano pero sobre listas, no sobre un cash copiado. El tablero sale en minutos.", "Listados de Tango, préstamos, deuda ARCA, una hora con quien carga."],
             ["2 · Tango", "Los listados de Tango (cobrar, pagar, cheques, movimientos) entran solos a la planilla.", "Desaparece el 80% de la carga manual. Los lunes se revisa, no se tipea.", "Acceso de lectura a Tango (una PC de la oficina o el servidor donde está)."],
             ["3 · Bancos", "Los extractos y saldos de los 5 bancos se bajan solos, todos los días, en una computadora de NAVAR.", "Saldos y movimientos reales sin abrir ningún home banking.", "Un usuario de consulta por banco. Corre en su equipo: nadie de afuera ve las claves."],
             ["4 · Proyección", "La cobranza proyectada se estima del historial real por cliente, no por kilo. Alertas: \"el jueves vencen $X y hay $Y\".", "El número menos firme del cash (67% de los ingresos) pasa a tener una medición de acierto mes a mes.", "Dos o tres meses de historial cargado (se acumula solo desde la etapa 1)."]]
    S += [tabla(filas, [22 * mm, 52 * mm, 52 * mm, 44 * mm], chico=True),
          P("Qué NO se automatiza", "h2"),
          LI("<b>Las decisiones.</b> El tablero dice \"con esto cubrís lo vencido y te sobra X\". Pagar o no pagar lo decide NAVAR."),
          LI("<b>Los impuestos.</b> El calendario de vencimientos se puede generar; los montos los pone el contador. Un número de impuestos estimado desde la caja es un número parecido y equivocado."),
          LI("<b>Mover plata.</b> Nada de lo que se construye transfiere, paga ni firma. Todo es de lectura."),
          Spacer(1, 3 * mm),
          P("Sobre Tango", "h2"),
          P("Tango es un programa de escritorio con una base de datos en una computadora o servidor de la "
            "empresa. Hay dos formas de conectarse: exportar los listados a Excel desde Tango Live (semi "
            "automático, alcanza para la etapa 1 y 2) o leer la base directamente con un usuario de solo "
            "lectura (automático total). Cuál conviene depende de dónde está instalado, que es una de las "
            "preguntas de la sección siguiente."),
          PageBreak()]

    # ------------------------------------------------------------ que falta
    S += [P("5 · Qué falta para que quede bien", "h1"),
          P("Hoy el tablero corre con los totales del cash viejo. Para que corra con los números reales hacen "
            "falta tres cosas de su lado, y hay cosas que no entendemos todavía y preferimos preguntar antes "
            "que suponer."),
          P("Lo que tienen que sumar desde NAVAR", "h2")]
    filas = [["Qué", "Para qué", "Quién lo tiene"],
             ["Los 4 listados de Tango, de A y de AA: cuentas a cobrar, cuentas a pagar, cartera de cheques (propios y de terceros) y movimientos de caja/bancos de los últimos 3 meses.", "Reemplazan los totales semanales por el detalle real. Sin esto no hay \"a quién pagar\" con nombre.", "Administración"],
             ["El cronograma de cada préstamo: banco, cuota, vencimiento, capital e interés. Y la situación BCRA por banco.", "Hoy la planilla mira ~$401 M de deuda bancaria y ustedes declaran ~$2.700 M. Hay que saber qué mira cada uno.", "Administración / bancos"],
             ["La deuda con ARCA: qué es plan de pagos (cuota fija, fecha exacta) y qué es mora.", "Es el objetivo declarado (\"adelantarse a los vencimientos\") y hoy es un solo número de $399 M.", "Contador"],
             ["Los saldos por banco y por empresa al lunes (los 5 bancos).", "Con situación 2 en dos bancos, importa en cuál está la plata.", "Oficina"],
             ["Los plazos y la tolerancia de cada proveedor: cuántos días aguanta antes de cortar.", "Es la línea de crédito real del negocio y \"no se carga en ningún lado\".", "Compras / dueña"],
             ["Dónde está instalado Tango y quién tiene Tango Live.", "Define cómo se automatiza la etapa 2.", "Sistemas / quien lo administra"]]
    S += [tabla(filas, [78 * mm, 62 * mm, 30 * mm], chico=True),
          P("Lo que no entendemos todavía (para la reunión con quien carga)", "h2")]
    qs = ["¿Qué es la empresa \"A\" y qué es \"AA\"? ¿Se pasan plata entre ellas?",
          "¿Cómo se calcula la \"cobranza proyectada por kg\"? ¿Kilos a despachar × precio × un porcentaje?",
          "¿Los clientes pagan con cheque o con transferencia? Define si el 75% del saldo es plata o papel.",
          "¿Qué proveedores hay detrás de los $539 M de \"MP y logística\" en 8 semanas?",
          "\"Pago cosecha\": ¿es mano de obra (tareferos) o compra de hoja? ¿Se puede correr una semana? ¿Cuándo termina la zafra?",
          "\"Honorarios + dividendos\": ¿honorarios fijos de directorio o retiros de socios? Son cosas opuestas para la caja.",
          "\"Otros gastos\": se proyectan $0 y salen $39 M reales. ¿Qué hay adentro?",
          "\"Estampillas\": ¿es la estampilla del INYM para despachar? ¿Se paga por semana según lo que sale?",
          "Catalina-Dolores y Carolina: ¿son establecimientos que venden hoja? ¿Con qué plazo? ¿Contrato de zafra?",
          "En el cash viejo, la fila \"Ingreso\" de deuda: ¿es lo que vence o lo que se paga? (es el error 4)"]
    S += [LI("%d. %s" % (i + 1, q)) for i, q in enumerate(qs)]
    S += [P("Decisiones que hay que tomar", "h2"),
          LI("<b>Quién es dueño de la planilla en Google.</b> Recomendación: una cuenta de NAVAR, no de una persona. Los datos son de la empresa."),
          LI("<b>Quién carga y quién mira.</b> Oficina edita las listas; la dueña ve; las solapas calculadas quedan protegidas."),
          LI("<b>La regla del cheque.</b> Una factura pagada con cheque propio se marca pagada el día que se emite el cheque (ya está escrito en la planilla; hay que acordarlo)."),
          PageBreak()]

    # ------------------------------------------------------------ como seguimos
    S += [P("6 · Cómo seguimos", "h1")]
    filas = [["Cuándo", "Qué", "Termina con"],
             ["Semana 1", "Reunión con quien carga (1 hora): las 10 preguntas, la planilla nueva abierta, cómo se carga cada solapa. Pedido de los listados de Tango.", "La planilla en la cuenta de NAVAR, con permisos. Las categorías confirmadas."],
             ["Semana 2", "Carga de los listados de Tango, préstamos y ARCA. Primera corrida del tablero con datos reales.", "El tablero con nombres de proveedores y clientes. La primera lectura semanal."],
             ["Semanas 3 a 6", "Rutina: los lunes se carga, se corre el tablero, se lee. Cada semana queda guardado qué se proyectó.", "Cuatro lecturas. Un cash flow que ya no se copia."],
             ["Semana 6", "Primera conciliación: qué se proyectó vs. qué pasó, por cuánto le erró y en qué. Propuesta de etapa 2 (Tango automático).", "Un número de acierto. La decisión de seguir automatizando, con datos."]]
    S += [tabla(filas, [24 * mm, 90 * mm, 56 * mm], chico=True),
          Spacer(1, 4 * mm),
          P("Qué se entrega cada semana", "h2"),
          LI("El tablero actualizado (un archivo que se abre con doble click, sin internet)."),
          LI("Una hoja con la lectura: caja, vencido, día crítico, qué se propone correr y qué se recomienda."),
          LI("La bitácora: qué se dijo la semana pasada y qué pasó."),
          Spacer(1, 4 * mm),
          P("Cómo trabajo con los datos", "h2"),
          P("Solo lectura, siempre: no muevo un peso, no cargo un pago, no firmo nada. Los datos quedan en la "
            "cuenta de NAVAR; yo tengo una copia mientras dura el trabajo y la borro al terminar. Nada de lo "
            "que vea se comparte ni se usa como ejemplo sin autorización escrita. Si en algún momento quieren "
            "cortar, cambian las claves y se terminó."),
          Spacer(1, 6 * mm),
          caja([P("<b>Honorarios.</b> Se conversan en la reunión de presentación: una implementación por la "
                  "etapa 1 y un abono mensual por la lectura semanal, que se ajusta cuando haya un número de "
                  "acierto medido (semana 6).")]),
          Spacer(1, 8 * mm),
          P("Thomas Manzo · %s" % HOY_TXT, "nota")]

    doc.build(S, onFirstPage=pie, onLaterPages=pie)
    return out


if __name__ == "__main__":
    print("PDF:", armar())
