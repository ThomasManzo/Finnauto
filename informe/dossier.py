# -*- coding: utf-8 -*-
"""
informe.dossier — el PDF que arranca la conversación comercial.

PARA QUÉ ES
-----------
Thomas: *"necesito un PDF para pasarle a Cowork a ver cómo empezamos con la
parte de la venta"*.

O sea que el lector no es un cliente: es **alguien que va a ayudarlo a vender**.
Eso cambia qué tiene que decir. Un dossier para un prospecto vende; este tiene
que **informar con precisión**, incluido lo que falta — si exagera, la ayuda que
reciba va a estar mal calibrada.

Por eso lleva tres cosas que un folleto no lleva:

  · lo que está hecho, con evidencia (números verificados contra la planilla
    del cliente, cantidad de tests, hallazgos reales)
  · lo que NO está hecho, sin adornar
  · los riesgos conocidos del negocio, no solo del software

Los números no se escriben a mano: salen del contrato y del repo. Un dossier
con una cifra vieja es peor que no tenerlo, porque se usa en una reunión.
"""

import io
import os
import sys
import json
import argparse
import datetime
import subprocess

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, KeepTogether)

BASE_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)

TINTA = colors.HexColor("#14211B")
SUAVE = colors.HexColor("#55645C")
TENUE = colors.HexColor("#8A968E")
LINEA = colors.HexColor("#DDE5E0")
VERDE = colors.HexColor("#0F7A4F")
ROJO = colors.HexColor("#B3261E")
AMBAR = colors.HexColor("#96690A")
FONDO = colors.HexColor("#F4F7F5")


def _est():
    b = ParagraphStyle("b", fontName="Helvetica", fontSize=9.7, leading=14.2,
                       textColor=TINTA, alignment=TA_LEFT, spaceAfter=7)
    return {
        "h1": ParagraphStyle("h1", parent=b, fontName="Helvetica-Bold",
                             fontSize=21, leading=25, spaceAfter=3),
        "sub": ParagraphStyle("sub", parent=b, fontSize=10.5, textColor=SUAVE,
                              spaceAfter=16),
        "h2": ParagraphStyle("h2", parent=b, fontName="Helvetica-Bold",
                             fontSize=8.4, textColor=TENUE, spaceBefore=17,
                             spaceAfter=7, leading=11),
        "h3": ParagraphStyle("h3", parent=b, fontName="Helvetica-Bold",
                             fontSize=11, spaceBefore=9, spaceAfter=4),
        "p": b,
        "li": ParagraphStyle("li", parent=b, leftIndent=11, bulletIndent=2,
                             spaceAfter=4),
        "nota": ParagraphStyle("nota", parent=b, fontSize=8.6, textColor=TENUE,
                               leading=12, spaceBefore=3),
        "cita": ParagraphStyle("cita", parent=b, fontName="Helvetica-Oblique",
                               leftIndent=10, textColor=SUAVE, spaceBefore=4),
    }


def _m(v):
    signo = "-" if v < 0 else ""
    return signo + "$" + format(int(round(abs(v))), ",d").replace(",", ".")


def _corto(v):
    n = abs(v)
    s = "-" if v < 0 else ""
    if n >= 1e9:
        return s + "$" + ("%.2f" % (n / 1e9)).replace(".", ",") + " MM"
    if n >= 1e6:
        return s + "$" + ("%.0f" % (n / 1e6)) + " M"
    return _m(v)


def _tabla(filas, anchos, cab=True):
    t = Table(filas, colWidths=anchos, hAlign="LEFT")
    e = [("FONT", (0, 0), (-1, -1), "Helvetica", 9),
         ("TEXTCOLOR", (0, 0), (-1, -1), TINTA),
         ("VALIGN", (0, 0), (-1, -1), "TOP"),
         ("TOPPADDING", (0, 0), (-1, -1), 5),
         ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
         ("LEFTPADDING", (0, 0), (-1, -1), 7),
         ("LINEBELOW", (0, 0), (-1, -2), 0.5, LINEA)]
    if cab:
        e += [("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7.6),
              ("TEXTCOLOR", (0, 0), (-1, 0), TENUE),
              ("BACKGROUND", (0, 0), (-1, 0), FONDO),
              ("LINEBELOW", (0, 0), (-1, 0), 0.8, LINEA)]
    t.setStyle(TableStyle(e))
    return t


# ------------------------------------------------------------------ los datos
def reunir(contrato_path, cliente="maga"):
    """Todo lo que el dossier afirma, sacado del repo y del contrato.

    Nada escrito a mano: un dossier con una cifra vieja es peor que no tenerlo,
    porque se usa en una reunión y nadie lo vuelve a chequear.
    """
    from dashboard import datos as DA
    from auditoria import cobertura as COB

    with io.open(contrato_path, encoding="utf-8") as f:
        contrato = json.load(f)
    paq = DA.armar(contrato, cliente)

    def _sh(cmd):
        try:
            r = subprocess.run(cmd, cwd=BASE_REPO, capture_output=True,
                               text=True, encoding="utf-8", errors="replace",
                               timeout=300)
            return (r.stdout or "") + (r.stderr or "")
        except Exception:
            return ""

    salida = _sh([sys.executable, "tests/test_motor.py"])
    tests = salida.count("[OK]")
    for extra in ("tests/test_lector.py", "tests/test_bot_generico.py"):
        tests += _sh([sys.executable, extra]).count("[OK]")

    filas, _ = COB.revisar(contrato, cliente)
    cuadra = all(abs(f[l]["dif"]) <= 1 for f in filas for l in ("entra", "sale"))

    return {"contrato": contrato, "paq": paq, "tests": tests, "cuadra": cuadra,
            "cobertura": filas}


# ------------------------------------------------------------------ el PDF
def construir(d, salida):
    E = _est()
    doc = SimpleDocTemplate(salida, pagesize=A4,
                            leftMargin=21 * mm, rightMargin=21 * mm,
                            topMargin=20 * mm, bottomMargin=18 * mm,
                            title="finauto — dossier", author="Thomas Manzo")
    S = []
    P = S.append
    paq, c = d["paq"], d["contrato"]
    ancho = doc.width

    P(Paragraph("finauto", E["h1"]))
    P(Paragraph("Capa de inteligencia financiera para PyMEs que se financian "
                "con sus proveedores. Dossier para la conversación comercial · "
                "%s" % datetime.date.today().strftime("%d/%m/%Y"), E["sub"]))

    # ------------------------------------------------------- el problema
    P(Paragraph("EL PROBLEMA, EN UNA FRASE", E["h2"]))
    P(Paragraph("En una PyME argentina la caja real no está en el banco: está "
                "en <b>cuánto aguantan sus proveedores antes de cortarle la "
                "compra</b>. Las líneas bancarias están agotadas o son caras, "
                "así que el crédito operativo lo da el proveedor.", E["p"]))
    P(Paragraph("Casi todo el software de tesorería contesta <i>“¿me alcanza "
                "la plata?”</i> y marca en rojo el día que la caja baja de un "
                "mínimo. Para este negocio esa pregunta está mal formulada: "
                "quedarse corto no es una falla, es una decisión sobre a quién "
                "estirar.", E["p"]))
    P(Paragraph("finauto contesta la que se toma de verdad:", E["p"]))
    P(Paragraph("<b>“¿A quién le pago esta semana, y cuánto atraso acumulo con "
                "el resto?”</b>", E["cita"]))

    # ------------------------------------------------------- qué está hecho
    P(Paragraph("QUÉ ESTÁ CONSTRUIDO Y FUNCIONANDO", E["h2"]))
    P(_tabla([
        ["Pieza", "Estado"],
        [Paragraph("<b>Motor de decisión</b><br/>"
                   "<font size=8 color='#55645C'>reparto semanal por proveedor, "
                   "puente de caja, posición por empresa, proyección con día "
                   "crítico, plan mínimo de qué patear</font>", E["p"]),
         Paragraph("Terminado · <b>%d tests</b>" % d["tests"], E["p"])],
        [Paragraph("<b>Lectura de la planilla del cliente</b><br/>"
                   "<font size=8 color='#55645C'>exportador que convierte el "
                   "cashflow en un contrato JSON estable</font>", E["p"]),
         Paragraph("Terminado", E["p"])],
        [Paragraph("<b>Tablero web</b><br/>"
                   "<font size=8 color='#55645C'>posición, a quién pagar, a "
                   "cobrar, proyección interactiva, hallazgos</font>", E["p"]),
         Paragraph("Terminado", E["p"])],
        [Paragraph("<b>Actualización automática</b><br/>"
                   "<font size=8 color='#55645C'>el cliente abre una URL y ve "
                   "el tablero del día</font>", E["p"]),
         Paragraph("Terminado", E["p"])],
        [Paragraph("<b>Memoria</b><br/>"
                   "<font size=8 color='#55645C'>guarda lo que se predijo y lo "
                   "compara contra lo que pasó</font>", E["p"]),
         Paragraph("Terminado, sin<br/>datos aún", E["p"])],
        [Paragraph("<b>Bots bancarios</b><br/>"
                   "<font size=8 color='#55645C'>bajan los extractos solos</font>",
                   E["p"]),
         Paragraph("<font color='#B3261E'>Galicia sí.<br/>Los demás, no</font>",
                   E["p"])],
    ], [ancho * 0.62, ancho * 0.38]))

    # ------------------------------------------------------- la evidencia
    P(Paragraph("LA EVIDENCIA: QUÉ ENCONTRÓ EN DATOS REALES", E["h2"]))
    P(Paragraph("Probado sobre el cashflow real de una cadena de 14 farmacias "
                "más su droguería. Estos son hallazgos que el cliente no tenía, "
                "no funcionalidades:", E["p"]))
    for h in (paq.get("hallazgos") or [])[:4]:
        cuerpo = (h["cuerpo"].replace("<b>", "").replace("</b>", "")
                  .replace("<br>", " "))
        txt = "<b>%s.</b> %s" % (h["titulo"].replace("“", "\"").replace("”", "\""),
                                 cuerpo)
        if h.get("monto"):
            txt += " <b>%s</b>" % _m(h["monto"])
        P(Paragraph(txt, E["li"], bulletText="·"))

    P(Paragraph("A esos se suman dos que salieron de leer las fórmulas de su "
                "propia planilla: el tablero que usaba para decidir apuntaba a "
                "una columna de <b>cinco meses atrás</b>, y su horizonte "
                "“a 45 días” no filtraba nada — sumaba 56.", E["p"]))

    P(Paragraph("POR QUÉ LOS NÚMEROS SE PUEDEN DEFENDER", E["h2"]))
    P(Paragraph("Es la parte que más cuesta y la que decide si un cliente lo "
                "usa. Tres controles corren solos, todos los días:", E["p"]))
    P(Paragraph("<b>Contraste.</b> El motor se compara contra los números que "
                "el cliente ya calcula y en los que confía. Donde difiere, "
                "explica por qué con motivos nombrados que cierran al peso.",
                E["li"], bulletText="·"))
    P(Paragraph("<b>Cobertura.</b> Verifica que cada peso del contrato llegue a "
                "la pantalla o esté declarado como excluido. %s"
                % ("Hoy cuadra." if d["cuadra"] else "Hoy NO cuadra."),
                E["li"], bulletText="·"))
    P(Paragraph("<b>Frescura.</b> Si el dato tiene más de 30 horas, el tablero "
                "lo dice arriba de todo.", E["li"], bulletText="·"))
    P(Paragraph("Si un control falla, no se publica: es preferible que el "
                "cliente vea el tablero de ayer a uno nuevo con un número mal.",
                E["nota"]))

    # ------------------------------------------------------- lo que falta
    P(Paragraph("LO QUE FALTA — SIN ADORNAR", E["h2"]))
    P(_tabla([
        ["Qué falta", "Por qué importa"],
        [Paragraph("Bots de Comafi, Santander y Provincia", E["p"]),
         Paragraph("Sin ellos, alguien baja los extractos a mano. Es 1 bot por "
                   "banco; el segundo cliente con los mismos bancos solo cambia "
                   "credenciales.", E["p"])],
        [Paragraph("Config del cliente fuera del código", E["p"]),
         Paragraph("Con un cliente no molesta. Con dos hay dos copias "
                   "divergiendo. <b>Hay que resolverlo antes de vender el "
                   "segundo.</b>", E["p"])],
        [Paragraph("Un precio cobrado", E["p"]),
         Paragraph("Nunca se le cobró a nadie. Sin un precedente, se cotiza a "
                   "ciegas — y a ciegas se cotiza bajo.", E["p"])],
        [Paragraph("Contrato y política de datos", E["p"]),
         Paragraph("Un dueño no da acceso a sus bancos sin un papel que diga "
                   "qué se toca, dónde queda y quién responde.", E["p"])],
        [Paragraph("Una medición de acierto", E["p"]),
         Paragraph("La memoria está construida pero necesita una segunda foto. "
                   "Un motor de predicción que nunca mostró un acierto es una "
                   "hipótesis, no un producto.", E["p"])],
    ], [ancho * 0.32, ancho * 0.68]))

    # ------------------------------------------------------- el negocio
    P(Paragraph("EL MODELO, Y DÓNDE ESTÁ LA DUDA", E["h2"]))
    P(Paragraph("La intención es <b>asesoría recurrente</b>, no venta de "
                "software: quien opera las herramientas es Thomas y el "
                "entregable es una lectura por visita. La hipótesis de precio "
                "—sin validar— es USD 500 de implementación más USD 100 por mes "
                "en los pilotos.", E["p"]))
    P(Paragraph("<b>La pregunta comercial abierta</b> no es si el software "
                "funciona: es si el nicho existe con esta forma. El caso que "
                "lo originó tiene droguería propia, 14 razones sociales y "
                "líneas bancarias agotadas por elección. Puede ser un fenómeno "
                "de ese grupo y no de la industria.", E["p"]))
    P(Paragraph("Una sola pregunta lo despeja, y conviene hacerla antes de "
                "armar cualquier pitch:", E["p"]))
    P(Paragraph("“¿Tenés línea bancaria disponible hoy?” — si la mayoría dice "
                "que sí, no viven al límite del proveedor y el motor les "
                "resuelve un problema que no tienen.", E["cita"]))

    P(Paragraph("CONTEXTO QUE CAMBIA EL PLAN", E["h2"]))
    P(Paragraph("Thomas ya no trabaja en la empresa donde se construyó todo "
                "esto. Eso tiene dos consecuencias: el cliente #1 pasó de ser "
                "el entorno de trabajo a ser <b>un prospecto que tiene que "
                "pagar</b>, y no hay acceso a los bancos para terminar los "
                "bots. El dato disponible es una foto que no se puede "
                "refrescar sin que ese cliente lo autorice.", E["p"]))
    P(Paragraph("Alcanza para construir y demostrar. No alcanza para operar.",
                E["nota"]))

    P(Paragraph("QUÉ SE NECESITA DE LA PARTE COMERCIAL", E["h2"]))
    for t in [
        "Cómo se presenta esto a un dueño que no es técnico y decide por "
        "intuición, en una reunión de treinta minutos.",
        "Cómo se cotiza sin un precedente: qué se cobra por implementación y "
        "qué por mes, y cómo se justifica.",
        "Qué tiene que mostrar un piloto para que la empresa firme después — y "
        "cuánto debería durar.",
        "Cómo se consigue la primera reunión con una cadena ajena, sin red de "
        "contactos en el rubro fuera del ex empleador.",
        "Qué papeles hacen falta para pedir acceso a datos financieros de un "
        "tercero sin tener sociedad constituida.",
    ]:
        P(Paragraph(t, E["li"], bulletText="·"))

    P(Spacer(1, 14))
    P(Paragraph("Este documento se genera desde el repositorio: los números de "
                "arriba salen del contrato del cliente y de la corrida de tests "
                "del día, no están escritos a mano.", E["nota"]))

    doc.build(S)
    return salida


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="El dossier comercial de finauto")
    ap.add_argument("--contrato", default="datos/CONTRATO_maga_2026-09-05.json")
    ap.add_argument("--cliente", default="maga")
    ap.add_argument("--salida", default="salidas/finauto_dossier.pdf")
    args = ap.parse_args()

    contrato = args.contrato
    if not os.path.isabs(contrato):
        contrato = os.path.join(BASE_REPO, contrato)
    salida = args.salida
    if not os.path.isabs(salida):
        salida = os.path.join(BASE_REPO, salida)
    d = os.path.dirname(salida)
    if d and not os.path.isdir(d):
        os.makedirs(d)

    print("Reuniendo evidencia (corre los tests, puede tardar)...")
    datos = reunir(contrato, args.cliente)
    construir(datos, salida)
    print("Listo: %s  (%d KB)" % (salida, os.path.getsize(salida) // 1024))


if __name__ == "__main__":
    main()
