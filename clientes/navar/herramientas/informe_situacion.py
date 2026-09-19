# -*- coding: utf-8 -*-
"""
informe_situacion — el PDF de la reunión del martes 22/09/2026: qué vimos, la foto real,
los 6 meses sin tocar nada, cómo lo solucionamos, accionables, prioridades de pago y las
preguntas que le hacemos a Priscilla para ordenarlas.

Todo número sale de los datos leídos (extractos, Tango, mapa de deuda, planilla de
impuestos) y de la misma proyección que arma la solapa Cash Mensual
(herramientas/proyeccion_mensual.py). El escenario "con plan" es una simulación: las
decisiones se toman en la solapa Plan de la Sheet, no acá.

Uso:
    python clientes/navar/herramientas/informe_situacion.py
    (deja privado/salidas/NAVAR - Situación y plan <fecha>.pdf)
"""

import os
import sys
import datetime
import importlib.util

AQUI = os.path.dirname(os.path.abspath(__file__))
BASE_REPO = os.path.abspath(os.path.join(AQUI, "..", "..", ".."))
os.chdir(BASE_REPO)
sys.path.insert(0, BASE_REPO)
sys.path.insert(0, AQUI)

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether

import propuesta as PR          # los estilos y ayudas del PDF anterior (mismo look)

P, LI, tabla, kpis, caja, m = PR.P, PR.LI, PR.tabla, PR.kpis, PR.caja, PR.m
E, TINTA, SUAVE, TENUE, VERDE, ROJO, AMBAR, FONDO, ROJO_FONDO = PR.E, PR.TINTA, PR.SUAVE, PR.TENUE, PR.VERDE, PR.ROJO, PR.AMBAR, PR.FONDO, PR.ROJO_FONDO
HOY = datetime.date(2026, 9, 19)
HOY_TXT = HOY.strftime("%d/%m/%Y")

spec = importlib.util.spec_from_file_location("pm", os.path.join(AQUI, "proyeccion_mensual.py"))
pm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pm)
RES = pm.res
COLS = RES["cols"]
MESES = {"01": "ene", "02": "feb", "03": "mar", "06": "jun", "07": "jul", "08": "ago", "09": "sep", "10": "oct", "11": "nov", "12": "dic"}


def lab(c):
    return MESES[c[5:]] + " " + c[2:4]


def mm_(v):
    """millones con signo, sin decimales"""
    return ("-" if v < 0 else "") + format(int(round(abs(v) / 1e6)), ",d").replace(",", ".")


# ------------------------------------------------------------------ escenario "con plan"
# Supuestos (se explicitan en el PDF; las decisiones reales se toman en la solapa Plan):
#  - préstamos bancarios (sin la tarjeta): se refinancian a 60 cuotas, 3 meses de gracia,
#    3 % mensual, sobre el capital vigente ($2.220 M) -> cuota ~ $80 M desde enero;
#  - la AgroNación diferida se paga en sus 3 resúmenes (sep-nov);
#  - ARCA: los planes que propone el contador (SICORE 9 x 32,2 desde noviembre + 13,3 al
#    contado en octubre; CCSS 8 x 3,3; Bienes Personales 18 x 0,26) + los planes vigentes;
#  - lo vencido con proveedores no se regulariza en estos 6 meses (queda como stock).
def escenario_con_plan():
    cols = COLS
    fut = [c for c in cols if c >= "2026-09"]
    capital_prestamos = 2480e6 - 260e6
    cuota_refi = capital_prestamos * 0.03 / (1 - (1.03) ** -60)
    cuotas = {}
    for c in fut:
        v = 0.0
        if c in ("2026-09", "2026-10", "2026-11"):
            v += 86.8e6                      # resúmenes AgroNación
        if c == "2026-09":
            v += 17.5e6 + 15.4e6             # Nación 21/09 (recién volvieron a situación 1) y Macro 24/09
        if c >= "2027-01":
            v += cuota_refi
        cuotas[c] = v
    impuestos_plan = {}
    for c in fut:
        v = 0.0
        if c == "2026-09":
            v += 49.7e6                      # lo urgente antes del 25/09
        if c == "2026-10":
            v += 13.3e6 + 36.5e6             # contado SICORE + planes vigentes
        if c >= "2026-11":
            v += 32.2e6 + 2.8e6
        if c >= "2026-10":
            v += 3.3e6 + 0.26e6
        impuestos_plan[c] = v
    return cuotas, impuestos_plan, cuota_refi


def tabla_escenario(cuotas_plan=None, impuestos_plan=None):
    """Filas resumidas de la proyección: ingresos, egresos operativos, deuda, saldo, disponible."""
    ing = RES["tot"]["ing"]
    filas = []
    egr_lineas = {n: [v for v, _ in vals] for n, _, vals in RES["egr"]}
    cu = egr_lineas["Cuotas bancarias (cronograma)"]
    im = egr_lineas["Impuestos: deuda y planes (vencimientos)"]
    oper = [sum(v[i] for n, v in egr_lineas.items() if n not in ("Cuotas bancarias (cronograma)", "Impuestos: deuda y planes (vencimientos)")) for i in range(len(COLS))]
    cuotas = list(cu)
    imp = list(im)
    if cuotas_plan:
        cuotas = [cuotas_plan.get(c, cu[i]) if c >= "2026-09" else cu[i] for i, c in enumerate(COLS)]
        imp = [impuestos_plan.get(c, im[i]) if c >= "2026-09" else im[i] for i, c in enumerate(COLS)]
    egr = [oper[i] + cuotas[i] + imp[i] for i in range(len(COLS))]
    saldos, s = [], RES["caja_hoy"]
    real_ing = [sum(fr for _, _, vals in RES["ing"] for fr in [vals[i][0]]) for i in range(len(COLS))]
    for i, c in enumerate(COLS):
        if c < "2026-09":
            saldos.append(None)
            continue
        if c == "2026-09":
            # el mes en curso: caja de hoy + lo que falta del mes (lo real ya está en la caja)
            s = RES["saldos"][i] - (cu[i] - cuotas[i]) - (im[i] - imp[i])
        else:
            s = s + ing[i] - egr[i]
        saldos.append(s)
    return {"ing": ing, "oper": oper, "cuotas": cuotas, "imp": imp, "egr": egr, "saldos": saldos,
            "disp": [None if v is None else v + RES["acuerdos"] for v in saldos]}


def tabla_proy(esc, titulo):
    enc = ["", ] + [lab(c) for c in COLS]
    def fila(nombre, vals, neg=False):
        out = [nombre]
        for v in vals:
            if v is None:
                out.append("")
            else:
                txt = mm_(v)
                out.append(Paragraph(('<font color="#B3261E">%s</font>' % txt) if (v < 0) else txt,
                                     ParagraphStyle("n", parent=PR.b, fontSize=8.2, leading=10.5, alignment=2, spaceAfter=0)))
        return out
    filas = [[Paragraph(x, ParagraphStyle("h", parent=PR.b, fontSize=8, leading=10, alignment=2 if i else 0, spaceAfter=0, textColor=TENUE)) for i, x in enumerate(enc)],
             fila("Ingresos", esc["ing"]),
             fila("Egresos de la operación", esc["oper"]),
             fila("Cuotas bancos y tarjeta", esc["cuotas"]),
             fila("Impuestos: deuda y planes", esc["imp"]),
             fila("Total egresos", esc["egr"]),
             fila("Saldo en bancos al cierre", esc["saldos"]),
             fila("Disponible (con descubiertos)", esc["disp"])]
    t = tabla(filas, [38 * mm] + [13.2 * mm] * len(COLS), chico=True)
    t.setStyle(TableStyle([("FONTNAME", (0, 5), (-1, 5), "Helvetica-Bold"), ("LINEABOVE", (0, 5), (-1, 5), 0.8, TENUE),
                           ("BACKGROUND", (0, 6), (-1, 6), colors.HexColor("#FFF8E1")), ("BACKGROUND", (0, 7), (-1, 7), ROJO_FONDO),
                           ("BACKGROUND", (1, 0), (3, -1), colors.HexColor("#F3FAF5"))]))
    return KeepTogether([P(titulo, "h3"), t, P("en millones de $ · jun-ago real (extracto) · sep real + estimado · oct-mar estimado · lo vencido de hoy no está en ningún mes", "nota")])


def pie(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(TENUE)
    canvas.drawString(20 * mm, 12 * mm, "NAVAR S.A. · Situación de caja y plan · finauto · %s" % HOY_TXT)
    canvas.drawRightString(190 * mm, 12 * mm, "Confidencial · página %d" % doc.page)
    canvas.restoreState()


def armar(out):
    doc = SimpleDocTemplate(out, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=20 * mm,
                            title="NAVAR S.A. · Situación de caja y plan", author="finauto")
    S = []
    sin = tabla_escenario()
    cuotas_plan, imp_plan, cuota_refi = escenario_con_plan()
    con = tabla_escenario(cuotas_plan, imp_plan)

    # ---------------------------------------------------------------- portada / en una página
    S += [P("NAVAR S.A.", "h2"), P("Situación de caja y plan", "titulo"),
          P("Lo que vimos, los próximos seis meses, cómo creemos que se resuelve y qué hay que hacer esta semana. Para la reunión del martes 22/09/2026.", "sub"),
          kpis([(m(-189.5e6, True), "en cuentas corrientes hoy (5 bancos)", ROJO),
                (m(1.406e9, True), "atrasado: proveedores, cuotas, impuestos, cheques", ROJO),
                (m(2.83e9, True), "deuda con bancos (capital)", TINTA),
                (m(605e6, True), "deuda impositiva", TINTA)]),
          Spacer(1, 8),
          P("En una página", "h1"),
          P("<b>La operación, sola, da.</b> Entran unos $490 M por mes (cobranzas, cheques depositados y cheques descontados) y la operación cuesta unos $350 M (proveedores, sueldos, impuestos corrientes, banco). Sobran $100–150 M por mes, y eso pagando a los proveedores menos de lo que se les debería pagar.", "grande"),
          P("<b>La deuda no da.</b> Las cuotas de bancos y tarjeta piden $170–250 M por mes en los próximos seis meses, más los planes de ARCA. El servicio de la deuda es el doble de lo que la operación deja.", "grande"),
          P("<b>Ya no hay colchón.</b> Los descubiertos están al tope ($196 M usados sobre $160 M acordados), hay $1.406 M atrasados y Corrientes ya informa situación 3.", "grande"),
          caja([P("No es un problema de caja: es un problema de estructura de deuda que se está pagando con caja, y la caja no alcanza. La salida es refinanciar a un número que la operación pueda pagar (~$100–150 M por mes para toda la deuda), proteger lo que no puede cortarse (ARCA, sueldos, los bancos que descuentan los cheques) y decidir, con un cash que se mira todas las semanas, qué se paga y qué no.", "p")], borde=ROJO),
          ]

    # ---------------------------------------------------------------- 1 · qué hicimos
    S += [PageBreak(), P("1 · Qué leímos para llegar a esto", "h1"),
          P("Todo lo que dice este documento sale de datos, no de la planilla vieja ni de estimaciones a mano:", "p"),
          LI("<b>Extractos de los cinco bancos</b>, junio a septiembre: 2.375 movimientos reales, clasificados (cobranza, descuento de cheques, proveedores, sueldos, cuotas, impuestos, intereses). El Nación llegó escaneado y se leyó con reconocimiento de texto, controlado renglón por renglón contra el saldo."),
          LI("<b>Tango</b>: cuentas a cobrar y a pagar con vencimiento, cartera de cheques, recibos y órdenes de pago de junio a hoy (con CUIT), nómina de clientes y proveedores."),
          LI("<b>Mapa de deuda bancaria</b> (planilla de NAVAR, revisada): 26 productos en 5 bancos, cuota por cuota."),
          LI("<b>Deuda impositiva</b>: la planilla de Celia revisada por el Estudio Monti el 18/09."),
          LI("<b>Respuestas de Priscilla</b> (18/09) sobre lo que los extractos no explican solos: venta de valores, tarjeta AgroNación, cheques, sueldos, AA."),
          P("Lo que NO está y hay que tener presente", "h2"),
          LI("El costo de la <b>cosecha</b> (no está en ninguna lista; es el egreso grande de la temporada)."),
          LI("La caja de <b>AA</b> es efectivo: se carga a mano, hoy $39,3 M al 31/08."),
          LI("Corrientes: el límite del acuerdo en cuenta corriente. Nación: la hipoteca «La Gloria» y la tarjeta corporativa, sin importe. Macro: el saldo usado de la venta de valores ($270 M acordados)."),
          ]

    # ---------------------------------------------------------------- 2 · la foto
    S += [P("2 · La foto real de hoy", "h1"),
          P("Bancos (cuentas corrientes, último extracto)", "h2"),
          tabla([["Banco", "Saldo", "Acuerdo de descubierto", "Disponible", "Qué se ve"],
                 ["Nación", m(-101.7e6, True), "$100 M (14/09)", "$0 (excedido $1,7 M)", "el 14/09 pagaron la AgroNación ($82,8 M) y una cuota impaga ($17,5 M) con el descubierto nuevo"],
                 ["Corrientes", m(-45.3e6, True), "sin informar", "$0", "clavado en el límite; 4 préstamos con 3 cuotas impagas, situación 3, refinanciación en curso"],
                 ["Macro", m(-39.7e6, True), "$50 M", "$10,3 M", "por acá pagan sueldos (~$93 M/mes) y entra la venta de valores (~$260 M/mes)"],
                 ["Galicia", m(-9.1e6, True), "$10 M", "$0,9 M", "descuenta cheques: $387 M en tres meses y medio"],
                 ["BBVA", m(6.4e6, True), "sin acuerdo", "$6,4 M", "cuota de $15,4 M del 11/09 sin fondos, colgada"],
                 [Paragraph("<b>Total</b>", E["p"]), Paragraph("<b>%s</b>" % m(-189.5e6, True), E["p"]), "$160 M", Paragraph("<b>$17,5 M</b>", E["p"]), "más la caja de AA en efectivo: $39,3 M"]],
                [22 * mm, 20 * mm, 30 * mm, 28 * mm, 70 * mm], chico=True),
          P("Deuda (capital) y atrasado", "h2"),
          tabla([["Concepto", "Monto", "Detalle"],
                 ["Bancos: préstamos, tarjetas, descuento de cheques", m(2.83e9, True), "Corrientes $1.027 M (sit. 3) · Nación $850 M (incluye $260 M diferidos de la AgroNación) · Macro $327 M · BBVA $309 M · Galicia $228 M"],
                 ["Impuestos", m(605e6, True), "SICORE 2024 $315 M (la mitad son intereses) · tasa de comercio $110 M · planes ARCA $67 M · aportes $42 M · IIBB $34 M · resto $37 M"],
                 ["Proveedores vencidos (Tango, sin la deuda vieja)", m(435e6, True), "A $389 M en 175 facturas · AA $46 M"],
                 ["Cuotas bancarias impagas", m(362e6, True), "Corrientes $347 M (junio a septiembre) · BBVA $15 M"],
                 ["Impuestos vencidos", m(548e6, True), "48 vencimientos; lo urgente antes del 25/09: $49,7 M (SICORE julio, plan W255056, plan IVA W118963, Misiones, DGR)"],
                 ["Cheques propios vencidos sin debitar", m(62e6, True), "4 cheques; tres parecen pagados según el extracto (Priscilla lo confirma)"],
                 [Paragraph("<b>Atrasado total a pagar</b>", E["p"]), Paragraph("<b>%s</b>" % m(1.406e9, True), E["p"]), "no está en ningún mes de la proyección: se paga por decisión"]],
                [58 * mm, 20 * mm, 92 * mm], chico=True),
          ]

    # ---------------------------------------------------------------- 3 · seis meses
    S += [PageBreak(), P("3 · Los próximos seis meses", "h1"),
          P("La proyección usa los tres meses cerrados de extracto como base: lo que se repite (cobranza, sueldos, impuestos corrientes) se proyecta como el promedio × 1,7 % mensual de inflación; lo que tiene fecha (cuotas, planes, cheques) va por su fecha. Es la misma cuenta que hace la solapa «Cash Mensual» de la planilla, donde la inflación es una celda editable.", "p"),
          tabla_proy(sin, "Sin tocar nada: pagando todo lo que vence como está"),
          Spacer(1, 6),
          P("Cierra en <b>%s</b> en marzo con los descubiertos incluidos. Octubre es el peor mes: $247 M de cuotas (con el resumen de la AgroNación), sueldos y $50 M de planes de ARCA." % m(sin["disp"][-1], True), "p"),
          Spacer(1, 4),
          tabla_proy(con, "Con un plan: refinanciar los préstamos, planes de ARCA al máximo, proteger la operación"),
          Spacer(1, 6),
          P("Supuestos del escenario (se ajustan en la solapa «Plan» de la planilla): los préstamos bancarios ($2.220 M de capital, sin la tarjeta) se refinancian a 60 cuotas con 3 meses de gracia al 3 %% mensual → cuota de %s desde enero; la AgroNación diferida se paga en sus tres resúmenes; los planes de ARCA que propone el contador (SICORE $13,3 M al contado + 9 × $32,2 M, CCSS 8 × $3,3 M) se firman; lo vencido con proveedores no se regulariza en estos seis meses. Cierra en <b>%s</b> en marzo: de perder $60 M por mes pasa a recuperar ~$50 M por mes desde diciembre. Ese margen es el que permite negociar cuotas más largas con ARCA o empezar a regularizar proveedores." % (m(cuota_refi, True), m(con["disp"][-1], True)), "p"),
          caja([P("Lo que este escenario dice, con todas sus aproximaciones: <b>la capacidad de pago de NAVAR para toda su deuda es de $100 a $150 M por mes</b>. Cualquier acuerdo con un banco o con ARCA que sume más que eso se rompe al segundo mes.", "p")], borde=AMBAR),
          ]

    # ---------------------------------------------------------------- 4 · cómo lo solucionamos
    S += [PageBreak(), P("4 · Cómo creemos que se resuelve", "h1"),
          P("1 · Esta semana: que no se corte nada vital", "h3"),
          LI("<b>ARCA antes del 25/09: $49,7 M.</b> Un embargo de cuentas frena la operación entera. SICORE julio ($19,9 M, si no entra demanda), plan W255056 ($16 M, se debita del Macro el 26), plan IVA W118963 ($8,3 M, si no caduca), Misiones ($0,5 M), DGR Corrientes ($5 M)."),
          LI("<b>Sueldos</b> del 1 al 10 de octubre (~$93 M por Macro)."),
          LI("<b>Nación, cuota del 21/09 ($17,5 M).</b> Acaban de usar $100 M de descubierto para volver a situación 1 ahí: no tirarlo."),
          LI("<b>Galicia y Macro</b>: las cuotas del 24 y 29/09 ($39 M). Son los bancos que descuentan los cheques; si cierran esa línea, se para el motor de $260 M por mes."),
          P("2 · Pagar por consecuencia, no por antigüedad", "h3"),
          P("Orden propuesto (a confirmar con Priscilla, ver sección 6): ARCA (embarga) → sueldos → Galicia y Macro (descuentan cheques) → Nación → proveedores de hoja y de cosecha → resto de proveedores → Corrientes y tarjetas → municipal. La tasa de comercio ($110 M) y la obra social pueden esperar, dijo el contador. Corrientes está en situación 3 y en refinanciación: no se recupera pagando cuotas sueltas.", "p"),
          P("3 · Refinanciar en serio, con un número defendible", "h3"),
          P("La capacidad de pago real para toda la deuda es ~$100–150 M por mes. Hoy se piden ~$250 M. Hay que llevar los $2.830 M de bancos a cuotas que sumen eso: plazo largo (48–60 meses), 3 a 6 meses de gracia. Corrientes ya lo está haciendo; Nación tiene la reprogramación; Galicia lo tiene anotado en su propia planilla. Con ARCA, pedir el máximo de cuotas: 9 cuotas de $32 M para el SICORE son demasiado cortas para esta caja.", "p"),
          P("4 · El disponible manda", "h3"),
          P("Regla operativa desde el martes: no se compromete un peso que el «Saldo disponible» de la semana no muestre. El cash se mira todos los lunes con Priscilla; se actualiza con extractos y Tango; las decisiones (qué se paga, qué se refinancia, qué se pospone) se cargan en la solapa «Plan» y el cash recalcula.", "p"),
          ]

    # ---------------------------------------------------------------- 5 · accionables
    S += [P("5 · Accionables", "h1"),
          tabla([["Qué", "Quién", "Cuándo"],
                 ["Pagar lo urgente de ARCA ($49,7 M) y generar los VEP", "Celia / Charles", "antes del 25/09"],
                 ["Confirmar con el contador el plan de pagos más largo posible para SICORE 2024 y CCSS", "Celia + Estudio Monti", "semana del 22/09"],
                 ["Pedir a cada banco la refinanciación con el número de capacidad de pago: Nación, Galicia, BBVA, Macro (Corrientes ya en curso)", "Charles / María Rosa", "semana del 22/09"],
                 ["Confirmar la lista de prioridades de pago (sección 6) y cargarla en la solapa Plan", "Priscilla + Thomas", "martes 22/09"],
                 ["Cargar el costo de la cosecha y los proveedores críticos (hoja) en el cash", "Priscilla", "esta semana"],
                 ["Confirmar los 4 cheques propios vencidos (¿pagados?) y el límite del acuerdo de Corrientes", "Priscilla", "esta semana"],
                 ["Extractos y exports de Tango cada semana (lunes) hasta que esté automatizado; token de Tango Live para automatizar", "Priscilla / Karina / Thomas", "desde el 28/09"],
                 ["Revisión semanal del cash: disponible, qué se paga, qué se pospone", "Priscilla + Thomas", "todos los lunes"]],
                [92 * mm, 42 * mm, 36 * mm], chico=True),
          ]

    # ---------------------------------------------------------------- 6 · prioridades y preguntas
    S += [PageBreak(), P("6 · Prioridades de pago: la propuesta y lo que hay que preguntar", "h1"),
          P("La prioridad no es «a quién le debemos más» sino «qué pasa si no pagamos». Esta es la propuesta inicial; se termina de armar con Priscilla y se carga en la solapa Plan.", "p"),
          tabla([["Prioridad", "A quién", "Por qué", "Qué pasa si no"],
                 ["1", "ARCA / DGR (vencimientos urgentes y planes)", "es el único acreedor que embarga cuentas", "embargo → se frena todo"],
                 ["2", "Sueldos y cargas", "la operación no anda sin la gente; la obra social aguanta hasta 3 meses", "conflicto, paro"],
                 ["3", "Galicia y Macro (cuotas y acuerdos)", "descuentan los cheques: son el motor de la caja", "cierran la línea → sin caja"],
                 ["4", "Nación", "recién volvieron a situación 1 con $100 M de descubierto", "vuelve a situación 2, pierden el crédito"],
                 ["5", "Proveedores de hoja y de cosecha", "sin hoja no hay producto", "cortan la entrega"],
                 ["6", "Resto de proveedores (Envasando, logística, insumos)", "según tolerancia; algunos ya financian vía tarjeta", "cortan el crédito comercial"],
                 ["7", "Corrientes (préstamos y tarjetas)", "ya está en situación 3 y en refinanciación", "el daño ya está hecho; se negocia el plan"],
                 ["8", "Tasa de comercio, patentes, inmobiliario", "no embargan rápido", "intereses"]],
                [16 * mm, 48 * mm, 58 * mm, 48 * mm], chico=True),
          P("Preguntas para Priscilla (para ordenar esto bien)", "h2"),
          LI("<b>Hoja y cosecha.</b> ¿Quiénes son los proveedores de hoja? ¿Cuánto se les debe, cuánto se les paga por mes en cosecha y con qué plazo aguantan? ¿Cuándo empieza y cuánto cuesta la cosecha 2027 (jornales, transporte, secado)?"),
          LI("<b>Envasando SRL.</b> Es el proveedor más grande ($245 M financiados con la tarjeta AgroNación). ¿Qué se le compra, con qué frecuencia, y qué pasa si se atrasa el pago del resumen?"),
          LI("<b>Proveedores que cortan.</b> De la lista de 88 proveedores con saldo, ¿cuáles cortan la entrega si no cobran (los 10 que importan)? ¿Cuáles esperan?"),
          LI("<b>Sueldos.</b> ¿Cuánta gente, cuánto es el total con cargas, y qué parte se paga en AA? ¿Hay atrasos con la obra social o ART?"),
          LI("<b>Bancos.</b> ¿Con quién están negociando en Corrientes y qué proponen? ¿Galicia y Macro renovaron los acuerdos de descubierto y la línea de descuento? ¿Hasta cuándo?"),
          LI("<b>ARCA.</b> ¿Quién decide qué VEP se paga (Celia, Charles)? ¿Están los $49,7 M para el 25/09 o hay que elegir?"),
          LI("<b>Cheques.</b> ¿Cuántos cheques hay hoy en cartera y cuánto suman? ¿Cuánto más se puede descontar en Galicia y Macro (límite de las líneas)?"),
          LI("<b>Cobranza.</b> ¿Los clientes grandes (Las Marías: $600 M en recibos desde junio) pagan a término? ¿Se puede adelantar cobranza con alguno?"),
          LI("<b>Dueños.</b> ¿Hay aportes de los socios previstos o venta de algún activo (la hipoteca «La Gloria» sugiere que hay inmuebles)?"),
          Spacer(1, 6),
          caja([P("Cómo seguimos: el martes se confirma el orden de prioridades y se carga en la solapa Plan. Desde ahí, cada lunes el cash dice cuánto hay, qué vence y qué se paga. Las decisiones son de NAVAR; el cash las hace visibles antes, no después.", "p")], borde=VERDE),
          ]

    doc.build(S, onFirstPage=pie, onLaterPages=pie)
    return out


if __name__ == "__main__":
    out = os.path.join(BASE_REPO, "clientes", "navar", "privado", "salidas", "NAVAR - Situación y plan %s.pdf" % HOY.isoformat())
    armar(out)
    print(out)
