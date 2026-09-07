# -*- coding: utf-8 -*-
"""
informe.presentacion — los dos PDF para mostrar el proyecto.

Thomas (07/09/2026): *"armame un PDF que explique todo lo que armamos de punta a
punta y otro PDF con las herramientas del proyecto como para presentar"*. Y
después: *"acordate de sumar desde el bot más chico hasta el más grande, desde
el clasificador hasta la automatización de las cuentas a cobrar, TODO TODO lo
que está armado"*.

Son dos documentos porque son dos lectores distintos:

    COMO_FUNCIONA   el recorrido del dato: de dónde sale y cómo se convierte en
                    una decisión. Para alguien que quiere entender el sistema.

    HERRAMIENTAS    el inventario completo, pieza por pieza, con su estado real.
                    Para mostrar el tamaño de lo construido.

EL INVENTARIO SE MIDE, NO SE ESCRIBE
------------------------------------
Las líneas de código y la cantidad de tests salen de leer el repositorio en el
momento de generar el PDF. Un inventario escrito a mano envejece en una semana
y nadie lo vuelve a chequear — y este se usa en una reunión.

Lo mismo con el estado de cada pieza: lo que está a medias dice que está a
medias. Un inventario que infla se nota en la primera pregunta.
"""

import io
import os
import re
import sys
import glob
import argparse
import datetime
import subprocess

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, PageBreak)

BASE_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)

REPO_MAGA = r"C:\MAGA"

TINTA = colors.HexColor("#14211B")
SUAVE = colors.HexColor("#55645C")
TENUE = colors.HexColor("#8A968E")
LINEA = colors.HexColor("#DDE5E0")
VERDE = colors.HexColor("#0F7A4F")
ROJO = colors.HexColor("#B3261E")
AMBAR = colors.HexColor("#96690A")
AZUL = colors.HexColor("#1B6FD6")
FONDO = colors.HexColor("#F4F7F5")


def _est():
    b = ParagraphStyle("b", fontName="Helvetica", fontSize=9.6, leading=14,
                       textColor=TINTA, alignment=TA_LEFT, spaceAfter=7)
    return {
        "h1": ParagraphStyle("h1", parent=b, fontName="Helvetica-Bold",
                             fontSize=20, leading=24, spaceAfter=3),
        "sub": ParagraphStyle("sub", parent=b, fontSize=10.3, textColor=SUAVE,
                              spaceAfter=15),
        "h2": ParagraphStyle("h2", parent=b, fontName="Helvetica-Bold",
                             fontSize=8.3, textColor=TENUE, spaceBefore=16,
                             spaceAfter=6, leading=11),
        "h3": ParagraphStyle("h3", parent=b, fontName="Helvetica-Bold",
                             fontSize=10.6, spaceBefore=10, spaceAfter=3),
        "p": b,
        "li": ParagraphStyle("li", parent=b, leftIndent=11, bulletIndent=2,
                             spaceAfter=3.5),
        "nota": ParagraphStyle("nota", parent=b, fontSize=8.5, textColor=TENUE,
                               leading=11.6, spaceBefore=3),
        "paso": ParagraphStyle("paso", parent=b, fontSize=9.4, leading=13.4,
                               leftIndent=13, spaceAfter=9),
    }


def _tabla(filas, anchos, cab=True, chico=False):
    t = Table(filas, colWidths=anchos, hAlign="LEFT")
    e = [("FONT", (0, 0), (-1, -1), "Helvetica", 8.4 if chico else 8.9),
         ("TEXTCOLOR", (0, 0), (-1, -1), TINTA),
         ("VALIGN", (0, 0), (-1, -1), "TOP"),
         ("TOPPADDING", (0, 0), (-1, -1), 4),
         ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
         ("LEFTPADDING", (0, 0), (-1, -1), 6),
         ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINEA)]
    if cab:
        e += [("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7.3),
              ("TEXTCOLOR", (0, 0), (-1, 0), TENUE),
              ("BACKGROUND", (0, 0), (-1, 0), FONDO),
              ("LINEBELOW", (0, 0), (-1, 0), 0.7, LINEA)]
    t.setStyle(TableStyle(e))
    return t


# ------------------------------------------------------------------ el censo
def _lineas(ruta):
    try:
        with io.open(ruta, encoding="utf-8", errors="replace") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def _docstring(ruta):
    """La primera línea del docstring: lo que el archivo dice de sí mismo."""
    try:
        with io.open(ruta, encoding="utf-8", errors="replace") as f:
            txt = f.read(1400)
        m = re.search(r'"""\s*\n?([^\n]*?)\n', txt)
        if not m:
            return ""
        t = m.group(1).strip()
        return re.sub(r"^[\w.]+\s+[—-]\s*", "", t)
    except Exception:
        return ""


def censar():
    """Mide el repositorio. Nada de esto se escribe a mano.

    Un inventario a mano envejece en una semana y nadie lo vuelve a chequear —
    y este se usa en una reunión, donde la primera pregunta puede ser
    exactamente sobre el número que quedó viejo.
    """
    def py(patron, base=BASE_REPO):
        out = []
        for r in sorted(glob.glob(os.path.join(base, patron))):
            n = os.path.basename(r)
            if n.startswith("__"):
                continue
            out.append({"nombre": os.path.splitext(n)[0], "ruta": r,
                        "lineas": _lineas(r), "que": _docstring(r)})
        return out

    def js(patron):
        out = []
        for r in sorted(glob.glob(os.path.join(REPO_MAGA, patron))):
            out.append({"nombre": os.path.basename(r), "ruta": r,
                        "lineas": _lineas(r)})
        return out

    def _sh(cmd):
        try:
            r = subprocess.run(cmd, cwd=BASE_REPO, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=400)
            return (r.stdout or "") + (r.stderr or "")
        except Exception:
            return ""

    tests = 0
    for t in ("tests/test_motor.py", "tests/test_lector.py",
              "tests/test_bot_generico.py"):
        tests += _sh([sys.executable, t]).count("[OK]")

    total = 0
    for base, _, files in os.walk(BASE_REPO):
        if any(x in base for x in ("__pycache__", ".git", "salidas", "datos")):
            continue
        for f in files:
            if f.endswith((".py", ".ps1")):
                total += _lineas(os.path.join(base, f))
    for r in glob.glob(os.path.join(REPO_MAGA, "apps_script", "*", "*.js")):
        if "_prueba" not in r:
            total += _lineas(r)

    return {
        "motor": py("simulador/*.py"),
        "auditoria": py("auditoria/*.py"),
        "lector": py("lector/*.py"),
        "memoria": py("memoria/*.py"),
        "dashboard": py("dashboard/*.py"),
        "informe": py("informe/*.py"),
        "ingestas": py("ingestas/*.py"),
        "nucleo": py("nucleo/*.py"),
        "orquestador": py("orquestador/*.py"),
        "bots": py("bots/*/bot.py"),
        "apps_script": [x for x in js("apps_script/*/*.js") if "_prueba" not in x["ruta"]],
        "tests": tests,
        "lineas_totales": total,
    }


# ============================================================ PDF 1: COMO FUNCIONA
def como_funciona(c, salida):
    """El recorrido del dato: de la planilla del cliente a una decisión."""
    E = _est()
    doc = SimpleDocTemplate(salida, pagesize=A4, leftMargin=21 * mm,
                            rightMargin=21 * mm, topMargin=20 * mm,
                            bottomMargin=18 * mm, title="finauto - como funciona")
    S = []
    P = S.append
    A = doc.width

    P(Paragraph("finauto", E["h1"]))
    P(Paragraph("Cómo funciona, de punta a punta · %s"
                % datetime.date.today().strftime("%d/%m/%Y"), E["sub"]))

    P(Paragraph("LA IDEA EN UNA LÍNEA", E["h2"]))
    P(Paragraph("El sistema toma los datos que la empresa ya tiene —bancos y "
                "planilla de cashflow—, los convierte en un formato estable, y "
                "responde una sola pregunta: <b>¿a quién le pago esta semana y "
                "cuánto atraso acumulo con el resto?</b>", E["p"]))

    P(Paragraph("EL RECORRIDO DEL DATO", E["h2"]))
    pasos = [
        ("1 · El banco",
         "Un bot entra al home banking, filtra por fecha y descarga los "
         "movimientos. Uno por banco. Deja el archivo en una carpeta de Drive."),
        ("2 · El clasificador",
         "Lee esos archivos, reconoce a qué farmacia y a qué concepto "
         "corresponde cada movimiento, descarta los repetidos y los carga en la "
         "planilla. Corre solo a la mañana y reintenta si Drive todavía no "
         "sincronizó."),
        ("3 · La planilla",
         "Es la que la empresa ya usa. El sistema <b>no la reemplaza</b>: la lee. "
         "Ahí viven la caja por banco, los ingresos previstos, la deuda con cada "
         "droguería, las cuentas a cobrar y la cartera de cheques."),
        ("4 · El exportador",
         "Convierte la planilla en un <b>contrato</b>: un archivo con los datos "
         "como campos —fecha, tipo, empresa, si es crédito, si es "
         "intercompañía— en vez de posiciones de celda. Es el único componente "
         "que sabe de solapas y columnas."),
        ("5 · El motor",
         "Lee solo el contrato. Calcula la posición, el reparto por proveedor "
         "ordenado por atraso, la curva de caja día por día, el día crítico y el "
         "plan mínimo de qué postergar para llegar."),
        ("6 · Los controles",
         "Antes de mostrar nada: se compara contra los números que el cliente ya "
         "calcula, se verifica que cada peso del contrato llegue a la pantalla, "
         "y se avisa si el dato está viejo. Si un control falla, no se publica."),
        ("7 · El tablero",
         "Se arma y se sube solo. El cliente abre una URL y ve la posición del "
         "día, a quién pagarle, qué cobrar, la proyección interactiva y los "
         "hallazgos."),
        ("8 · La memoria",
         "Cada corrida guarda lo que se predijo. En la visita siguiente el "
         "sistema puede decir: <i>“el mes pasado te dijimos que el 14 quedabas "
         "corto; quedaste el 16”</i>."),
    ]
    for t, d in pasos:
        P(Paragraph("<b>%s</b>" % t, E["h3"]))
        P(Paragraph(d, E["paso"]))

    P(PageBreak())

    P(Paragraph("LA DECISIÓN QUE CONTESTA, Y POR QUÉ ES OTRA", E["h2"]))
    P(Paragraph("Casi todo el software de tesorería pregunta <i>“¿me alcanza la "
                "plata?”</i> y marca en rojo el día que la caja baja de un "
                "mínimo. En una PyME que compra a plazo eso está mal planteado: "
                "quedarse corto no es una falla, es una decisión sobre a quién "
                "estirar.", E["p"]))
    P(Paragraph("Las líneas bancarias están agotadas o son caras, así que "
                "<b>el crédito operativo lo da el proveedor</b>. El límite real "
                "no es un mínimo de caja: es cuántas semanas aguanta cada "
                "proveedor antes de cortar el suministro. Por eso el reparto se "
                "ordena por <b>atraso</b> —un hecho— y no por monto ni por una "
                "tolerancia estimada.", E["p"]))

    P(Paragraph("LAS DISTINCIONES QUE HACE, Y UNA PLANILLA NO", E["h2"]))
    P(_tabla([
        ["Distinción", "Por qué cambia la decisión"],
        [Paragraph("<b>Caja</b> vs <b>menos deuda</b>", E["p"]),
         Paragraph("Un cheque endosado y una nota de crédito bajan deuda sin que "
                   "entre un peso al banco. Tratarlos como ingreso infla la caja.",
                   E["p"])],
        [Paragraph("<b>Vencido</b> vs <b>por vencer</b>", E["p"]),
         Paragraph("Lo vencido es lo que puede hacer que te corten la compra. Lo "
                   "que vence el martes todavía no aprieta.", E["p"])],
        [Paragraph("<b>Cargado</b> vs <b>estimado</b>", E["p"]),
         Paragraph("La deuda tiene fecha y monto en la planilla; el resto se "
                   "deduce del comportamiento. El tablero dice cuál es cuál.",
                   E["p"])],
        [Paragraph("<b>Dentro</b> vs <b>fuera</b> del grupo", E["p"]),
         Paragraph("Un pago entre dos empresas del mismo dueño mueve plata de "
                   "bolsillo: no puede cambiar el total del grupo.", E["p"])],
        [Paragraph("<b>Divisible</b> vs <b>todo o nada</b>", E["p"]),
         Paragraph("A una droguería le pagás una parte. Un cheque no: o lo "
                   "cubrís o rebota, y eso no es un escenario permitido.", E["p"])],
    ], [A * 0.28, A * 0.72]))

    P(Paragraph("POR QUÉ LOS NÚMEROS SE PUEDEN DEFENDER", E["h2"]))
    P(Paragraph("Es la parte que decide si alguien lo usa para mover plata. Tres "
                "controles corren solos todos los días, y si uno falla el "
                "tablero no se publica: es preferible mostrar el de ayer a uno "
                "nuevo con un número mal.", E["p"]))
    P(Paragraph("<b>Contraste.</b> Compara contra los números que el cliente ya "
                "calcula. Donde difiere, no dice “está mal”: dice de qué está "
                "hecha la diferencia, con motivos que cierran al peso.",
                E["li"], bulletText="·"))
    P(Paragraph("<b>Cobertura.</b> Verifica que cada peso del contrato llegue a "
                "la pantalla o esté declarado como excluido con motivo.",
                E["li"], bulletText="·"))
    P(Paragraph("<b>Frescura.</b> Si el dato tiene más de 30 horas, se avisa "
                "arriba de todo.", E["li"], bulletText="·"))
    P(Paragraph("Además, <b>%d pruebas automáticas</b>. Cada una corresponde a un "
                "error real que apareció mirando datos de producción: la idea no "
                "es cubrir todo el código, es que ningún error que ya costó "
                "encontrar pueda volver en silencio." % c["tests"], E["p"]))

    P(Paragraph("QUÉ HACE FALTA PARA SUMAR OTRA EMPRESA", E["h2"]))
    P(Paragraph("El motor no se toca: cero líneas. Lo que cambia son datos.",
                E["p"]))
    P(_tabla([
        ["Qué", "Dónde se configura"],
        [Paragraph("Cómo se llaman las solapas y dónde está la caja", E["p"]),
         Paragraph("Una solapa de configuración en la propia planilla", E["p"])],
        [Paragraph("Los rótulos de los bloques: deuda, cobranza, egresos", E["p"]),
         Paragraph("La misma solapa, una línea por bloque", E["p"])],
        [Paragraph("Proveedores, plazos y semanas de tolerancia", E["p"]),
         Paragraph("Un catálogo por cliente", E["p"])],
        [Paragraph("Los bancos donde opera", E["p"]),
         Paragraph("Una ficha por banco — se hace una vez y se reusa entre "
                   "clientes que usen el mismo banco", E["p"])],
    ], [A * 0.46, A * 0.54]))

    doc.build(S)
    return salida


# ============================================================ PDF 2: HERRAMIENTAS
def herramientas(c, salida):
    """El inventario completo, pieza por pieza, con su estado real."""
    E = _est()
    doc = SimpleDocTemplate(salida, pagesize=A4, leftMargin=19 * mm,
                            rightMargin=19 * mm, topMargin=19 * mm,
                            bottomMargin=17 * mm, title="finauto - herramientas")
    S = []
    P = S.append
    A = doc.width

    P(Paragraph("finauto — las herramientas", E["h1"]))
    P(Paragraph("Inventario completo de lo construido · %s · "
                "<b>%s líneas</b> de código propio y <b>%d</b> pruebas automáticas"
                % (datetime.date.today().strftime("%d/%m/%Y"),
                   format(c["lineas_totales"], ",d").replace(",", "."),
                   c["tests"]), E["sub"]))

    def bloque(titulo, intro, items, estado=None):
        P(Paragraph(titulo, E["h2"]))
        if intro:
            P(Paragraph(intro, E["p"]))
        filas = [["Pieza", "Qué hace", "Líneas"]]
        for it in items:
            filas.append([
                Paragraph("<b>%s</b>" % it["nombre"], E["p"]),
                Paragraph(it.get("que") or "—", E["p"]),
                Paragraph(str(it["lineas"]) if it["lineas"] else "—", E["p"])])
        P(_tabla(filas, [A * 0.20, A * 0.68, A * 0.12], chico=True))
        if estado:
            P(Paragraph(estado, E["nota"]))

    # --------------------------------------------------------- los bots
    P(Paragraph("1 · LOS BOTS: DE DÓNDE SALE EL DATO", E["h2"]))
    P(Paragraph("Un bot por banco. Entra al home banking con credenciales "
                "cifradas —que el cliente carga él y nadie más lee—, filtra por "
                "fecha, descarga los movimientos y deja el archivo en Drive.",
                E["p"]))
    P(_tabla([
        ["Banco", "Estado", "Líneas"],
        [Paragraph("<b>Motor genérico</b><br/><font size=7.5 color='#8A968E'>"
                   "la lógica común: login, reintentos, esperas, descargas, "
                   "recorrido de empresas</font>", E["p"]),
         Paragraph("<font color='#0F7A4F'>Funcionando</font>", E["p"]),
         Paragraph(str(next((b["lineas"] for b in c["bots"]
                             if "generico" in b["ruta"]), 0)), E["p"])],
        [Paragraph("<b>Galicia</b>", E["p"]),
         Paragraph("<font color='#0F7A4F'>Probado punta a punta</font>", E["p"]),
         Paragraph(str(next((b["lineas"] for b in c["bots"]
                             if "galicia" in b["ruta"]), 0)), E["p"])],
        [Paragraph("<b>Comafi</b>", E["p"]),
         Paragraph("Andamiaje listo, falta<br/>mapear la web real", E["p"]),
         Paragraph(str(next((b["lineas"] for b in c["bots"]
                             if "comafi" in b["ruta"]), 0)), E["p"])],
        [Paragraph("<b>Santander</b>", E["p"]),
         Paragraph("Andamiaje listo, falta<br/>mapear la web real", E["p"]),
         Paragraph(str(next((b["lineas"] for b in c["bots"]
                             if "santander" in b["ruta"]), 0)), E["p"])],
        [Paragraph("<b>Plantilla de banco nuevo</b><br/>"
                   "<font size=7.5 color='#8A968E'>una ficha de selectores; "
                   "no se programa un bot nuevo, se llena una ficha</font>", E["p"]),
         Paragraph("<font color='#0F7A4F'>Lista</font>", E["p"]),
         Paragraph("—", E["p"])],
    ], [A * 0.34, A * 0.46, A * 0.20], chico=True))
    P(Paragraph("Sumar un banco no es escribir un bot: es llenar una ficha con "
                "los selectores de esa web. Y el que se llena para un cliente "
                "sirve para todos los que usen ese banco.", E["nota"]))

    # -------------------------------------------------- lectura y carga
    P(Paragraph("2 · LECTURA Y CARGA AUTOMÁTICA (en la planilla)", E["h2"]))
    P(_tabla([
        ["Pieza", "Qué hace", "Líneas"],
        [Paragraph("<b>Clasificador</b>", E["p"]),
         Paragraph("Lee los extractos de cada banco, reconoce farmacia y "
                   "concepto, descarta repetidos por huella y carga en el "
                   "cashflow", E["p"]),
         Paragraph(str(_lineas(os.path.join(REPO_MAGA, "apps_script",
                                            "clasificador", "Clasificador V.4.js"))),
                   E["p"])],
        [Paragraph("<b>Corrida automática</b>", E["p"]),
         Paragraph("Corre a las 8, 9, 10 y 11 y controla que hayan llegado "
                   "TODOS los bancos esperados, no solo alguno", E["p"]),
         Paragraph(str(_lineas(os.path.join(REPO_MAGA, "apps_script",
                                            "clasificador", "Automatico.js"))), E["p"])],
        [Paragraph("<b>Carga en el cash</b>", E["p"]),
         Paragraph("Escribe los movimientos ya clasificados en la planilla",
                   E["p"]),
         Paragraph(str(_lineas(os.path.join(REPO_MAGA, "apps_script",
                                            "clasificador", "Carga Cash.js"))), E["p"])],
        [Paragraph("<b>Carga de saldos</b>", E["p"]),
         Paragraph("Actualiza la grilla de saldos por banco y por farmacia",
                   E["p"]),
         Paragraph(str(_lineas(os.path.join(REPO_MAGA, "apps_script",
                                            "clasificador", "Cargasaldos.js"))), E["p"])],
        [Paragraph("<b>Cobranzas</b>", E["p"]),
         Paragraph("Procesa los recibos de cobranza de la carpeta y actualiza "
                   "las cuentas a cobrar. Corre solo cada hora", E["p"]),
         Paragraph(str(_lineas(os.path.join(REPO_MAGA, "apps_script",
                                            "cashflow", "Cobranzas.js"))), E["p"])],
        [Paragraph("<b>Cheques emitidos</b>", E["p"]),
         Paragraph("Lee el listado que baja del banco y concilia qué cheques "
                   "siguen pendientes", E["p"]),
         Paragraph(str(next((x["lineas"] for x in c["ingestas"]), 0)), E["p"])],
    ], [A * 0.20, A * 0.68, A * 0.12], chico=True))

    # ---------------------------------------------------- el exportador
    P(Paragraph("3 · EL EXPORTADOR: EL LÍMITE DEL SISTEMA", E["h2"]))
    P(Paragraph("Convierte la planilla en un contrato con los datos como campos. "
                "Es el <b>único</b> componente que sabe de solapas y columnas: "
                "cambiar de cliente, o pasar de una planilla a un ERP, se "
                "resuelve acá y el resto no se entera.", E["p"]))
    P(_tabla([
        ["Qué lee", "Detalle"],
        [Paragraph("Saldos y caja", E["p"]),
         Paragraph("Por banco y por empresa, más el efectivo", E["p"])],
        [Paragraph("Movimientos", E["p"]),
         Paragraph("Busca los encabezados, no la fila: aguanta que muevan cosas",
                   E["p"])],
        [Paragraph("Ingresos previstos", E["p"]),
         Paragraph("Mostrador, tarjeta, obras sociales, PAMI, cuentas a cobrar",
                   E["p"])],
        [Paragraph("Deuda con droguerías", E["p"]),
         Paragraph("Por proveedor y por fecha de resumen, con las notas de "
                   "crédito restando", E["p"])],
        [Paragraph("Cuentas a cobrar", E["p"]),
         Paragraph("Lo que le deben a la droguería del grupo", E["p"])],
        [Paragraph("Egresos del cashflow", E["p"]),
         Paragraph("Sueldos, cargas, impuestos, alquileres, cheques a pagar",
                   E["p"])],
        [Paragraph("Cartera de cheques", E["p"]),
         Paragraph("Cada cheque con su fecha de cobro, importe y estado", E["p"])],
        [Paragraph("Los números del cliente", E["p"]),
         Paragraph("Sus propias solapas de resumen, <b>con la fórmula y a qué "
                   "celda apunta</b>, para poder contrastar", E["p"])],
    ], [A * 0.26, A * 0.74], chico=True))
    P(Paragraph("Se informa siempre qué leyó de cada hoja y hasta qué fecha. "
                "Cuando no encuentra un bloque, lista los rótulos que sí hay — "
                "porque el problema nunca fue el error, fue el silencio.",
                E["nota"]))

    P(PageBreak())

    # ------------------------------------------------------------ motor
    bloque("4 · EL MOTOR DE DECISIÓN",
           "Todo esto lee únicamente el contrato. No sabe que existe una "
           "planilla.", c["motor"])

    bloque("5 · LOS CONTROLES",
           "Corren antes de mostrar nada. Si uno falla, no se publica.",
           c["auditoria"])

    bloque("6 · LA MEMORIA",
           "Guarda lo que se predijo y lo compara contra lo que pasó. Es lo que "
           "hace que la segunda visita valga más que la primera.", c["memoria"])

    bloque("7 · EL TABLERO Y LOS INFORMES", "", c["dashboard"] + c["informe"])

    bloque("8 · ONBOARDING DE UN CLIENTE NUEVO",
           "Herramientas para no arrancar de cero con cada planilla: le hacen la "
           "radiografía y escriben un borrador del mapeo y del catálogo.",
           c["lector"])

    bloque("9 · INFRAESTRUCTURA COMÚN",
           "Credenciales cifradas, navegador, fechas, logs, estado.",
           c["nucleo"] + c["orquestador"])

    P(Paragraph("10 · LO QUE FALTA, SIN ADORNAR", E["h2"]))
    P(_tabla([
        ["Qué", "Estado"],
        [Paragraph("Bots de Comafi, Santander y Provincia", E["p"]),
         Paragraph("<font color='#B3261E'>Frenados por acceso, no por código</font>",
                   E["p"])],
        [Paragraph("Medición de acierto de la proyección", E["p"]),
         Paragraph("<font color='#96690A'>Construida; necesita una segunda foto "
                   "para mostrar un número</font>", E["p"])],
        [Paragraph("Lectura de comprobantes y contratos (OCR)", E["p"]),
         Paragraph("<font color='#B3261E'>No empezado — y postergable</font>",
                   E["p"])],
        [Paragraph("Usuarios, permisos y multiempresa real", E["p"]),
         Paragraph("<font color='#B3261E'>No empezado</font>", E["p"])],
    ], [A * 0.5, A * 0.5], chico=True))

    P(Spacer(1, 12))
    P(Paragraph("Las líneas de código y la cantidad de pruebas de este documento "
                "se miden leyendo el repositorio al generarlo. No están escritas "
                "a mano.", E["nota"]))

    doc.build(S)
    return salida


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Los PDF de presentacion")
    ap.add_argument("--dir", default="salidas")
    args = ap.parse_args()
    d = args.dir if os.path.isabs(args.dir) else os.path.join(BASE_REPO, args.dir)
    if not os.path.isdir(d):
        os.makedirs(d)

    print("Midiendo el repositorio (corre los tests, puede tardar)...")
    c = censar()
    a = como_funciona(c, os.path.join(d, "finauto_como_funciona.pdf"))
    b = herramientas(c, os.path.join(d, "finauto_herramientas.pdf"))
    for r in (a, b):
        print("Listo: %s  (%d KB)" % (r, os.path.getsize(r) // 1024))


if __name__ == "__main__":
    main()
