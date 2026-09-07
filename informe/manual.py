# -*- coding: utf-8 -*-
"""Genera el manual: el PDF para operar finauto sin ayuda."""
import io
import os
import sys
import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, PageBreak)

BASE = r"C:\finauto"
TINTA = colors.HexColor("#14211B")
SUAVE = colors.HexColor("#55645C")
TENUE = colors.HexColor("#8A968E")
LINEA = colors.HexColor("#DDE5E0")
VERDE = colors.HexColor("#0F7A4F")
ROJO = colors.HexColor("#B3261E")
AMBAR = colors.HexColor("#96690A")
FONDO = colors.HexColor("#F4F7F5")
CODEBG = colors.HexColor("#EEF2F0")

b = ParagraphStyle("b", fontName="Helvetica", fontSize=9.6, leading=14,
                   textColor=TINTA, alignment=TA_LEFT, spaceAfter=7)
E = {
    "h1": ParagraphStyle("h1", parent=b, fontName="Helvetica-Bold", fontSize=20,
                         leading=24, spaceAfter=3),
    "sub": ParagraphStyle("sub", parent=b, fontSize=10.3, textColor=SUAVE,
                          spaceAfter=14),
    "h2": ParagraphStyle("h2", parent=b, fontName="Helvetica-Bold", fontSize=8.3,
                         textColor=TENUE, spaceBefore=16, spaceAfter=6, leading=11),
    "h3": ParagraphStyle("h3", parent=b, fontName="Helvetica-Bold", fontSize=11,
                         spaceBefore=11, spaceAfter=3),
    "p": b,
    "li": ParagraphStyle("li", parent=b, leftIndent=12, bulletIndent=2, spaceAfter=4),
    "nota": ParagraphStyle("nota", parent=b, fontSize=8.5, textColor=TENUE,
                           leading=11.6, spaceBefore=2),
    "cmd": ParagraphStyle("cmd", parent=b, fontName="Courier", fontSize=8.3,
                          leading=11.5, backColor=CODEBG, borderPadding=6,
                          leftIndent=2, spaceBefore=3, spaceAfter=8),
    "cita": ParagraphStyle("cita", parent=b, fontName="Helvetica-Oblique",
                           leftIndent=11, textColor=SUAVE, spaceAfter=5),
}


def tabla(filas, anchos, chico=False):
    t = Table(filas, colWidths=anchos, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 8.4 if chico else 8.9),
        ("TEXTCOLOR", (0, 0), (-1, -1), TINTA),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINEA),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7.3),
        ("TEXTCOLOR", (0, 0), (-1, 0), TENUE),
        ("BACKGROUND", (0, 0), (-1, 0), FONDO),
        ("LINEBELOW", (0, 0), (-1, 0), 0.7, LINEA)]))
    return t


salida = os.path.join(BASE, "salidas", "finauto_manual.pdf")
doc = SimpleDocTemplate(salida, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                        topMargin=19 * mm, bottomMargin=17 * mm,
                        title="finauto - manual de operacion")
S = []
P = S.append
A = doc.width

P(Paragraph("finauto — manual", E["h1"]))
P(Paragraph("Todo lo que hay que hacer, sin depender de nadie · %s"
            % datetime.date.today().strftime("%d/%m/%Y"), E["sub"]))
P(Paragraph("Este documento existe porque los créditos se restablecen el martes "
            "y las reuniones son antes. Está escrito para poder hacer todo solo, "
            "incluido lo que fallaría.", E["nota"]))

# ============================================================ PARTE 1
P(Paragraph("PARTE 1 · CONECTAR EL CASH NUEVO", E["h2"]))
P(Paragraph("Cuando los empleados actualicen el cash original y quieras un "
            "contrato nuevo. Son cinco pasos y ninguno depende de mí.", E["p"]))

P(Paragraph("1 · Sacá una copia del cash original", E["h3"]))
P(Paragraph("En Drive: botón derecho sobre el cash original → <b>Hacer una "
            "copia</b>. Ponele un nombre con la fecha, por ejemplo "
            "<i>Cash de prueba 08-09</i>.", E["p"]))
P(Paragraph("La copia trae los datos actualizados. Lo que NO trae es el código "
            "de finauto ni la solapa de configuración: eso lo reponen los pasos "
            "2 y 3, y son dos minutos.", E["nota"]))

P(Paragraph("2 · Copiá el ID del script de esa copia", E["h3"]))
P(Paragraph("En la copia: <b>Extensiones → Apps Script</b>. En el editor, el "
            "engranaje de la izquierda (<b>Configuración del proyecto</b>) → "
            "<b>ID de la secuencia de comandos</b> → Copiar.", E["p"]))
P(Paragraph("Si te queda más cómodo, copiá la URL entera del editor: el script "
            "del paso siguiente le saca el ID solo.", E["nota"]))

P(Paragraph("3 · Conectá finauto a esa copia", E["h3"]))
P(Paragraph("En la terminal, parado en <font face='Courier'>C:\\finauto</font>:",
            E["p"]))
P(Paragraph("powershell -ExecutionPolicy Bypass -File scripts\\nuevo_cash.ps1 "
            "-Id \"PEGA_ACA_EL_ID\"", E["cmd"]))
P(Paragraph("Eso apunta el proyecto a la planilla nueva y sube el código. Si el "
            "ID está mal copiado te lo dice antes de tocar nada.", E["p"]))

P(Paragraph("4 · En la planilla", E["h3"]))
P(Paragraph("<b>Recargá la página (F5)</b> — sin esto el menú no aparece.",
            E["li"], bulletText="a."))
P(Paragraph("Menú <b>finauto → Crear solapa de configuración</b>", E["li"],
            bulletText="b."))
P(Paragraph("Menú <b>finauto → Exportar contrato (JSON)</b>. Tarda unos "
            "segundos y avisa cuando terminó.", E["li"], bulletText="c."))

P(Paragraph("5 · Armá el tablero", E["h3"]))
P(Paragraph("powershell -ExecutionPolicy Bypass -File scripts\\actualizar_tablero.ps1",
            E["cmd"]))
P(Paragraph("Busca el contrato más nuevo, corre el control de cobertura, arma el "
            "tablero y lo deja en <font face='Courier'>salidas\\finauto.html</font>. "
            "Si el control falla, <b>no publica</b> — y te dice por qué.", E["p"]))

P(Paragraph("SI ALGO FALLA", E["h2"]))
P(tabla([
    ["Lo que ves", "Qué es y qué hacer"],
    [Paragraph("<b>No aparece el menú finauto</b>", E["p"]),
     Paragraph("Falta recargar la planilla (F5). Si ya recargaste, el paso 3 no "
               "llegó a subir: fijate si dijo <i>Subido</i>.", E["p"])],
    [Paragraph("<b>clasp: falló el push</b>", E["p"]),
     Paragraph("Casi siempre es la sesión vencida. Corré "
               "<font face='Courier'>clasp login</font> y repetí el paso 3.",
               E["p"])],
    [Paragraph("<b>No hay ningún contrato en H:\\Mi unidad</b>", E["p"]),
     Paragraph("Drive todavía no lo bajó. El script te lista qué .json SÍ hay en "
               "esa carpeta, así se ve si es sincronización o si el export no "
               "corrió. Podés esperar unos minutos y repetir, o pasarle otra "
               "carpeta con <font face='Courier'>-Carpeta</font>.", E["p"])],
    [Paragraph("<b>EL CONTROL DE COBERTURA FALLÓ</b>", E["p"]),
     Paragraph("Hay plata del contrato que no llega al tablero. <b>No lo "
               "publiques.</b> Es exactamente el caso en que conviene mostrar el "
               "tablero de ayer.", E["p"])],
    [Paragraph("<b>El tablero abre en blanco</b>", E["p"]),
     Paragraph("Abrilo con doble click desde el explorador, no arrastrándolo. Si "
               "sigue en blanco, es un error de JavaScript: guardá el archivo y "
               "mostrámelo el martes.", E["p"])],
], [A * 0.30, A * 0.70]))

P(Paragraph("PARA MOSTRARLO EN LA REUNIÓN", E["h2"]))
P(Paragraph("El archivo <font face='Courier'>salidas\\finauto.html</font> se abre "
            "con doble click y funciona sin internet. Para la reunión alcanza con "
            "eso: no hace falta publicar nada.", E["p"]))
P(Paragraph("Si querés pasarles un link para que lo miren después, ahí sí hay que "
            "publicar la Web App (Apps Script → Implementar → Nueva implementación "
            "→ Aplicación web). Pero para mostrar en pantalla, el archivo alcanza.",
            E["nota"]))

P(PageBreak())

# ============================================================ PARTE 2
P(Paragraph("PARTE 2 · LA REUNIÓN CON EL CFO DE MAGA+", E["h2"]))
P(Paragraph("Él conoce los datos, así que la demo se valida sola. <b>El objetivo "
            "no es mostrar el tablero: es cerrar un piloto pago.</b>", E["p"]))

P(Paragraph("Cómo abrir", E["h3"]))
P(Paragraph("No arranques por el tablero. Arrancá por los <b>hallazgos</b>: son "
            "cosas que él no sabe de su propia planilla, y es lo que separa esto "
            "de un dashboard más.", E["p"]))
P(Paragraph("“Antes de mostrarte nada, tres cosas que encontré mirando tu cash.”",
            E["cita"]))
P(Paragraph("La solapa de Posición Consolidada que usás para decidir apunta a la "
            "columna B del cashflow: el 1 de abril. Por eso los dos escenarios "
            "dan el mismo número.", E["li"], bulletText="1."))
P(Paragraph("La Calculadora muestra $915M más de deuda de la que tenés: las notas "
            "de crédito se cuentan como ingreso pero nunca se descuentan del "
            "saldo con la droguería.", E["li"], bulletText="2."))
P(Paragraph("El horizonte “a 45 días” no filtra nada — suma hasta el 31/10, que "
            "son 56.", E["li"], bulletText="3."))
P(Paragraph("Recién después el tablero. Y mostrá primero <b>“a quién le pago"
            "”</b>, que es su decisión de todos los días.", E["p"]))

P(Paragraph("Qué preguntarle", E["h3"]))
P(Paragraph("<b>¿Cuánto tiempo por semana te lleva armar el cash y decidir los "
            "pagos?</b> — es el número que después justifica el precio.",
            E["li"], bulletText="·"))
P(Paragraph("<b>¿Cuántas veces en los últimos seis meses te bloquearon una compra "
            "por atraso?</b> — cuantifica el dolor en plata, no en comodidad.",
            E["li"], bulletText="·"))
P(Paragraph("<b>¿Qué mirás vos antes de autorizar un retiro?</b> — validás si el "
            "motor contesta la pregunta correcta o una parecida.",
            E["li"], bulletText="·"))
P(Paragraph("<b>Si esto lo tuvieras andando todos los días, ¿qué dejarías de "
            "hacer?</b> — la respuesta es el argumento de venta, dicho por él.",
            E["li"], bulletText="·"))
P(Paragraph("<b>Y la incómoda: ¿esto lo pagarías? ¿cuánto te parece razonable?</b>",
            E["li"], bulletText="·"))

P(Paragraph("Qué pedirle", E["h3"]))
P(Paragraph("Que te deje seguir exportando el cash una vez por semana durante el "
            "piloto. Sin eso no hay medición de acierto, y sin medición no hay "
            "caso para el segundo cliente.", E["p"]))

P(Paragraph("Lo que NO conviene hacer", E["h3"]))
P(Paragraph("Prometer los bots. Hoy solo Galicia funciona punta a punta y no hay "
            "acceso para terminar los otros. Si se promete y no llega, se pierde "
            "la credibilidad de todo lo demás — que sí está.", E["p"]))

P(Paragraph("PARTE 3 · LA REUNIÓN CON LA CFO DE FARMA24", E["h2"]))
P(Paragraph("Es otra reunión. <b>No podés mostrar los datos de MAGA</b>, y el "
            "objetivo no es vender: es descubrir si el problema existe con esta "
            "forma en otra cadena.", E["p"]))

P(Paragraph("La pregunta que define todo", E["h3"]))
P(Paragraph("“¿Tenés línea bancaria disponible hoy?”", E["cita"]))
P(Paragraph("Si dice que sí y le sobra, <b>no vive al límite del proveedor</b> y "
            "el motor le resuelve un problema que no tiene. Es mejor saberlo en "
            "la primera reunión que en marzo.", E["p"]))

P(Paragraph("Las otras cinco", E["h3"]))
P(Paragraph("<b>¿Cómo decidís a quién le pagás cuando no alcanza?</b> — si "
            "contesta “de memoria”, el nicho es más chico de lo que parece; si "
            "describe un método, es un cliente.", E["li"], bulletText="·"))
P(Paragraph("<b>¿Tenés droguería propia o solo comprás?</b> — define si necesita "
            "las dos puntas o una sola.", E["li"], bulletText="·"))
P(Paragraph("<b>¿Cuántas razones sociales manejás?</b>", E["li"], bulletText="·"))
P(Paragraph("<b>¿Quién arma el cashflow y cuánto tarda?</b> — si hay alguien "
            "full-time haciéndolo, competís contra esa persona, no contra Excel.",
            E["li"], bulletText="·"))
P(Paragraph("<b>¿Usás algún ERP con módulo de tesorería?</b> — si sí, competís "
            "contra software instalado.", E["li"], bulletText="·"))

P(Paragraph("Qué pedirle, y es lo importante de esa reunión", E["h3"]))
P(Paragraph("<b>Una copia de su planilla de cashflow</b>, aunque sea con los "
            "números cambiados o solo la estructura. Con eso corro el lector y en "
            "un par de días le mostrás <b>sus</b> números.", E["p"]))
P(Paragraph("Es el único camino para no caer en el pitch genérico — que es "
            "exactamente lo que dice cualquiera con un dashboard.", E["nota"]))

P(Paragraph("SI PREGUNTAN POR EL PRECIO", E["h2"]))
P(Paragraph("No improvises un número a la baja. La hipótesis es <b>USD 500 de "
            "implementación más USD 100 por mes</b> para un piloto, pero todavía "
            "no está validada.", E["p"]))
P(Paragraph("Una salida honesta que no cierra la puerta:", E["p"]))
P(Paragraph("“El piloto lo estoy armando en el orden de los USD 500 de "
            "implementación y USD 100 por mes. Prefiero que primero veas si te "
            "sirve: si a los dos meses no cambió ninguna decisión tuya, no tiene "
            "sentido que lo pagues.”", E["cita"]))
P(Paragraph("Lo que sí conviene evitar es “el primer mes sin cargo” sin fecha de "
            "corte: ese mes se convierte en tres.", E["nota"]))

P(Paragraph("LO QUE TENÉS PARA MOSTRAR", E["h2"]))
P(tabla([
    ["Archivo", "Para qué"],
    [Paragraph("<font face='Courier'>finauto.html</font>", E["p"]),
     Paragraph("El tablero. Doble click, anda sin internet", E["p"])],
    [Paragraph("<font face='Courier'>finauto_como_funciona.pdf</font>", E["p"]),
     Paragraph("El recorrido del dato, si preguntan cómo funciona", E["p"])],
    [Paragraph("<font face='Courier'>finauto_herramientas.pdf</font>", E["p"]),
     Paragraph("El inventario completo, si preguntan qué tan hecho está", E["p"])],
    [Paragraph("<font face='Courier'>finauto_dossier.pdf</font>", E["p"]),
     Paragraph("Para Cowork o para vos: incluye lo que falta", E["p"])],
], [A * 0.34, A * 0.66]))
P(Paragraph("Los tres PDF y el tablero están en "
            "<font face='Courier'>C:\\finauto\\salidas\\</font>.", E["nota"]))

P(Spacer(1, 10))
P(Paragraph("Todo el código está en GitHub, en los dos repositorios, sin nada "
            "pendiente de subir. Si esta computadora desaparece, no se pierde "
            "nada del proyecto.", E["nota"]))

doc.build(S)
print("Listo: %s (%d KB)" % (salida, os.path.getsize(salida) // 1024))
