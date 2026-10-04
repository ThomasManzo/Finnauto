# -*- coding: utf-8 -*-
"""
principales20_pdf — el PDF "Principales clientes y proveedores" para mandar por mail a NAVAR.

PARA QUÉ
--------
Pedido de NAVAR (28/09/2026): seguir día a día a los 20 clientes que más deben y a los 20
proveedores a los que más se les debe, para el plan de regularización de Tango. En la Sheet
eso vive en la solapa "Principales 20" (fórmulas). Este PDF es la foto de ese día, con
gráficos, para adjuntar al mail.

DE DÓNDE SALEN LOS NÚMEROS
--------------------------
De la Sheet "NAVAR - Cash Flow" exportada a Excel (solapas Cuentas a Cobrar y Cuentas a
Pagar, que se llenan solas desde Tango). No hay ningún número tipeado acá: si la Sheet
cambia, se baja de nuevo, se vuelve a correr y el PDF cambia. Las mismas reglas que la solapa:
  - saldo       = suma de "Saldo Pendiente" de esa razón social en esa empresa (A o AA);
  - vencido     = lo que tiene fecha de vencimiento anterior a --hoy;
  - a vencer    = saldo − vencido;
  - vto. impago más viejo = el vencimiento más antiguo con saldo > 0, ya vencido.
Todo es "según Tango": si Tango no tiene cargado un cobro o un pago, acá tampoco está.

Uso:
    python clientes/navar/herramientas/principales20_pdf.py [--sheet <export.xlsx>] [--hoy AAAA-MM-DD]
    (deja privado/salidas/NAVAR - Principales clientes y proveedores <fecha>.pdf y el .html)

Sin --sheet toma el export más nuevo de privado/ ("NAVAR - Cash Flow (export Sheets ...).xlsx").
El PDF lo imprime Google Chrome sin ventana (tiene que estar instalado).
"""

import os
import re
import sys
import glob
import html
import argparse
import datetime
import subprocess
from collections import defaultdict

import openpyxl

AQUI = os.path.dirname(os.path.abspath(__file__))
NAVAR = os.path.dirname(AQUI)
PRIVADO = os.path.join(NAVAR, "privado")
SALIDAS = os.path.join(PRIVADO, "salidas")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# Colores: los dos primeros de la paleta de referencia de gráficos (par validado para
# daltonismo). Naranja = vencido, azul = a vencer. El texto nunca va en color de serie.
VENCIDO = "#eb6834"
# A partir de cuánta plata con vencimiento de un año anterior se marca la fecha en negrita
# y se lista en "Para confirmar".
UMBRAL_VIEJO = 1e6
A_VENCER = "#2a78d6"

# Cada bloque: qué lista de la Sheet, qué columna tiene el nombre y de qué empresa.
BLOQUES = [
    ("clientes", "Cuentas a Cobrar", "Cliente", "A"),
    ("clientes", "Cuentas a Cobrar", "Cliente", "AA"),
    ("proveedores", "Cuentas a Pagar", "Proveedor", "A"),
    ("proveedores", "Cuentas a Pagar", "Proveedor", "AA"),
]


# ------------------------------------------------------------------ formato
def millones(v, dec=1):
    """$X M, con coma decimal como se lee en Argentina."""
    s = ("%." + str(dec) + "f") % (v / 1e6)
    return "$" + s.replace(".", ",") + " M"


def porc(v):
    return ("%.0f" % (v * 100)) + " %"


MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def fecha_corta(d):
    return "%02d/%02d/%d" % (d.day, d.month, d.year) if d else ""


def e(s):
    return html.escape(str(s))


# ------------------------------------------------------------------ datos
def ultimo_export():
    c = glob.glob(os.path.join(PRIVADO, "NAVAR - Cash Flow (export Sheets *).xlsx"))
    if not c:
        sys.exit("No hay ningún export de la Sheet en privado/. Bajala como Excel o pasá --sheet.")
    return max(c, key=os.path.getmtime)


def fecha_de_la_bajada(filas):
    """La fecha de la bajada de Tango que cargó esas filas, leída de Observaciones
    ("... Tango Live · cobranzas · 28/09/2026 ..."). Si hay varias, la más nueva."""
    fechas = set()
    for f in filas:
        for m in re.finditer(r"Tango Live · \w+ · (\d\d/\d\d/\d{4})", str(f.get("Observaciones") or "")):
            fechas.add(datetime.datetime.strptime(m.group(1), "%d/%m/%Y").date())
    return max(fechas) if fechas else None


def leer(ruta, hoy):
    wb = openpyxl.load_workbook(ruta, data_only=True, read_only=True)
    listas = {}
    for hoja in ("Cuentas a Cobrar", "Cuentas a Pagar"):
        ws = wb[hoja]
        it = ws.iter_rows(values_only=True)
        enc = [str(c).strip() if c is not None else "" for c in next(it)]
        listas[hoja] = [dict(zip(enc, r)) for r in it if any(v not in (None, "") for v in r)]
    corte_90 = hoy - datetime.timedelta(days=90)
    inicio_anio = datetime.date(hoy.year, 1, 1)

    bloques = []
    for tipo, hoja, quien, emp in BLOQUES:
        filas = [f for f in listas[hoja] if f.get("Empresa") == emp and f.get(quien)]
        por = defaultdict(lambda: {"saldo": 0.0, "vencido": 0.0, "viejo": None, "anterior": 0.0})
        for f in filas:
            s = float(f.get("Saldo Pendiente") or 0)
            v = f.get("Fecha Vencimiento")
            v = v.date() if hasattr(v, "date") else None
            x = por[str(f[quien])]
            x["saldo"] += s
            if v and v < hoy:
                x["vencido"] += s
                if s > 0:
                    x["viejo"] = min(x["viejo"] or v, v)
            if v and v < inicio_anio and s > 0:
                x["anterior"] += s
        total = sum(x["saldo"] for x in por.values())
        top = sorted(por.items(), key=lambda kv: -kv[1]["saldo"])[:20]
        top_nombres = {k for k, _ in top}
        mas_90 = sum(float(f.get("Saldo Pendiente") or 0) for f in filas
                     if str(f[quien]) in top_nombres and hasattr(f.get("Fecha Vencimiento"), "date")
                     and f["Fecha Vencimiento"].date() < corte_90 and float(f.get("Saldo Pendiente") or 0) > 0)
        suma = sum(x["saldo"] for _, x in top)
        vencido = sum(x["vencido"] for _, x in top)
        bloques.append({
            "tipo": tipo, "empresa": emp, "total": total, "suma": suma, "vencido": vencido,
            "mas_90": mas_90, "cuentas": len(por),
            "filas": [dict(nombre=k, **x) for k, x in top],
            "bajada": fecha_de_la_bajada(filas),
        })
    return bloques, inicio_anio


# ------------------------------------------------------------------ gráfico
def grafico(b, escala, inicio_anio):
    """Barras horizontales apiladas: vencido (naranja, desde la base) + a vencer (azul).
    Una fila por cliente/proveedor, con el saldo al final de la barra y el vencimiento
    impago más viejo a la derecha (en negrita si es de un año anterior)."""
    ancho_nombre, ancho_barra, ancho_valor, ancho_fecha = 196, 190, 64, 74
    alto_fila, sep = 25, 2
    W = ancho_nombre + ancho_barra + ancho_valor + ancho_fecha
    H = 22 + alto_fila * len(b["filas"])
    x0 = ancho_nombre
    partes = ['<svg viewBox="0 0 %d %d" width="%d" height="%d" xmlns="http://www.w3.org/2000/svg" '
              'font-family="Helvetica Neue, Helvetica, Arial, sans-serif">' % (W, H, W, H)]
    # encabezados de columna (texto en tinta secundaria)
    partes.append('<text x="0" y="12" font-size="8.5" fill="#6b6a66">%s</text>'
                  % ("Cliente" if b["tipo"] == "clientes" else "Proveedor"))
    partes.append('<text x="%d" y="12" font-size="8.5" fill="#6b6a66">Saldo</text>' % (x0 + ancho_barra + 6))
    partes.append('<text x="%d" y="12" font-size="8.5" fill="#6b6a66" text-anchor="end">Vto. impago más viejo</text>' % W)
    # línea base (eje recesivo)
    partes.append('<line x1="%d" y1="18" x2="%d" y2="%d" stroke="#d6d5d0" stroke-width="1"/>' % (x0, x0, H))
    for i, f in enumerate(b["filas"]):
        y = 22 + i * alto_fila
        cy = y + alto_fila / 2
        nombre = f["nombre"] if len(f["nombre"]) <= 34 else f["nombre"][:33] + "…"
        partes.append('<text x="0" y="%.1f" font-size="9" fill="#1f1f1d" dominant-baseline="middle">%s</text>'
                      % (cy, e(nombre)))
        ven = max(f["vencido"], 0)
        av = max(f["saldo"] - f["vencido"], 0)
        wv = ancho_barra * ven / escala
        wa = ancho_barra * av / escala
        hb = alto_fila - 10
        yb = y + 5
        # vencido pegado a la base; a vencer a continuación, con 2 px de separación
        if wv > 0.5:
            partes.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%d" rx="2" fill="%s"><title>Vencido %s</title></rect>'
                          % (x0, yb, wv, hb, VENCIDO, millones(ven)))
        if wa > 0.5:
            xa = x0 + wv + (sep if wv > 0.5 else 0)
            partes.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%d" rx="2" fill="%s"><title>A vencer %s</title></rect>'
                          % (xa, yb, max(wa - (sep if wv > 0.5 else 0), 0.5), hb, A_VENCER, millones(av)))
        fin = x0 + wv + wa
        partes.append('<text x="%.1f" y="%.1f" font-size="8.5" fill="#1f1f1d" dominant-baseline="middle">%s</text>'
                      % (max(fin + 4, x0 + ancho_barra + 6), cy, millones(f["saldo"])))
        if f["viejo"]:
            # Negrita solo si lo de años anteriores pesa (>= $X M): un resto de $X M de 2022
            # es cierto, pero no es donde hay que mirar primero.
            viejo = f["anterior"] >= UMBRAL_VIEJO
            partes.append('<text x="%d" y="%.1f" font-size="8.5" fill="%s" font-weight="%s" text-anchor="end" '
                          'dominant-baseline="middle">%s</text>'
                          % (W, cy, "#1f1f1d" if viejo else "#6b6a66", "700" if viejo else "400",
                             fecha_corta(f["viejo"])))
    partes.append("</svg>")
    return "".join(partes)


# ------------------------------------------------------------------ página
CSS = """
@page { size: A4 landscape; margin: 11mm 12mm 12mm 12mm; }
* { box-sizing: border-box; }
body { margin: 0; font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; color: #1f1f1d;
       background: #ffffff; font-size: 10.5px; line-height: 1.4; }
.pagina { page-break-after: always; }
.pagina:last-child { page-break-after: auto; }
h1 { font-size: 22px; margin: 0 0 2px; letter-spacing: -0.2px; }
h2 { font-size: 15px; margin: 0 0 8px; }
h3 { font-size: 12px; margin: 0 0 2px; }
.sub { color: #6b6a66; font-size: 11px; margin-bottom: 14px; }
.tiles { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 10px 0 16px; }
.tile { border: 1px solid #e4e3de; border-radius: 8px; padding: 10px 12px; }
.tile .que { font-size: 10px; color: #6b6a66; text-transform: uppercase; letter-spacing: .4px; }
.tile .num { font-size: 22px; font-weight: 700; margin: 2px 0 4px; }
.tile .det { font-size: 10px; color: #52514e; }
.meter { height: 8px; border-radius: 4px; background: #f0efec; display: flex; overflow: hidden; margin: 6px 0 4px; gap: 2px; }
.meter span { display: block; height: 100%; border-radius: 2px; }
.dos { display: grid; grid-template-columns: 1fr 1fr; gap: 22px; }
.caja { border-left: 3px solid #d6d5d0; padding: 2px 0 2px 10px; margin: 6px 0; }
.leyenda { display: flex; gap: 16px; font-size: 9.5px; color: #52514e; margin: 0 0 8px; align-items: center; }
.leyenda i { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 5px; vertical-align: -1px; }
.resumen { font-size: 10px; color: #52514e; margin: 0 0 6px; }
ul { margin: 4px 0 0 16px; padding: 0; } li { margin: 3px 0; }
li.grupo { list-style: none; margin: 8px 0 2px -16px; font-size: 9.5px; color: #6b6a66; text-transform: uppercase; letter-spacing: .4px; }
.pie { color: #8a8984; font-size: 8.5px; margin-top: 10px; }
"""


def tile(b):
    ven = b["vencido"] / b["suma"] if b["suma"] else 0
    quien = "Clientes" if b["tipo"] == "clientes" else "Proveedores"
    verbo = "deben" if b["tipo"] == "clientes" else "se les debe"
    return ('<div class="tile"><div class="que">%s · empresa %s</div>'
            '<div class="num">%s</div>'
            '<div class="det">Los 20 principales (%s del total que %s)</div>'
            '<div class="meter"><span style="width:%.1f%%;background:%s"></span>'
            '<span style="flex:1;background:%s"></span></div>'
            '<div class="det"><b>%s vencido</b> (%s) · %s con más de 90 días de vencido</div></div>'
            % (quien, b["empresa"], millones(b["suma"], 0), porc(b["suma"] / b["total"] if b["total"] else 0),
               verbo, ven * 100, VENCIDO, A_VENCER, porc(ven), millones(b["vencido"], 0), millones(b["mas_90"], 0)))


def anteriores(b, inicio_anio, cuantos=4):
    """Los que tienen más plata con vencimiento de un año anterior (lo que más hay que revisar)."""
    x = [f for f in b["filas"] if f["anterior"] >= UMBRAL_VIEJO]
    x.sort(key=lambda f: -f["anterior"])
    return x[:cuantos]


def bloque_html(b, escala, inicio_anio):
    quien = "Clientes" if b["tipo"] == "clientes" else "Proveedores"
    return ('<div><h3>%s · empresa %s</h3>'
            '<div class="resumen">Estos 20 suman %s de %s (%s). Vencido: %s.</div>%s</div>'
            % (quien, b["empresa"], millones(b["suma"]), millones(b["total"]),
               porc(b["suma"] / b["total"] if b["total"] else 0), millones(b["vencido"]),
               grafico(b, escala, inicio_anio)))


def armar(bloques, hoy, inicio_anio, fuente):
    bajada = max((b["bajada"] for b in bloques if b["bajada"]), default=None)
    fecha_datos = fecha_corta(bajada) if bajada else "(sin fecha de bajada)"
    leyenda = ('<div class="leyenda"><span><i style="background:%s"></i>Vencido (antes del %s)</span>'
               '<span><i style="background:%s"></i>A vencer</span>'
               '<span>Fecha a la derecha: el vencimiento impago más viejo; <b>en negrita</b> si hay más de $X M con vencimiento de años anteriores.</span></div>'
               % (VENCIDO, fecha_corta(hoy), A_VENCER))
    cli = [b for b in bloques if b["tipo"] == "clientes"]
    pro = [b for b in bloques if b["tipo"] == "proveedores"]
    esc_cli = max(f["saldo"] for b in cli for f in b["filas"])
    esc_pro = max(f["saldo"] for b in pro for f in b["filas"])

    def lista_anteriores(bs, titulo):
        items = ['<li class="grupo">%s</li>' % titulo]
        for b in bs:
            for f in anteriores(b, inicio_anio):
                items.append("<li><b>%s</b> (empresa %s): %s con vencimiento anterior a %d; el más viejo, %s.</li>"
                             % (e(f["nombre"]), b["empresa"], millones(f["anterior"]), inicio_anio.year,
                                fecha_corta(f["viejo"])))
        if len(items) == 1:
            items.append("<li>Ninguno por encima de $X M.</li>")
        return "".join(items)

    p1 = ('<div class="pagina"><h1>Principales clientes y proveedores</h1>'
          '<div class="sub">NAVAR · según Tango, bajada del %s · vencido calculado al %s</div>'
          '<div class="tiles">%s</div>'
          '<div class="dos"><div><h2>Qué armamos</h2>'
          '<div class="caja">En la planilla hay una solapa nueva, <b>"Principales 20"</b>: los 20 clientes que más deben '
          'y los 20 proveedores a los que más se les debe, por empresa, con lo vencido, lo que falta vencer y el '
          'vencimiento impago más viejo. <b>Se actualiza sola cada mañana</b> con la bajada de Tango.</div>'
          '<div class="caja">Próximamente suma la <b>fecha del último pago</b> de cada uno: si alguien debe mucho y '
          'Tango no registra un cobro o pago hace meses, o no está pagando o falta cargarlo.</div>'
          '<div class="caja">Todo lo que se ve es <b>lo que Tango tiene cargado</b>. Si un cobro o un pago no está '
          'imputado en Tango, acá aparece como deuda. Por eso sirve para seguir el plan de regularización.</div></div>'
          '<div><h2>Para confirmar en el plan de regularización</h2>'
          '<h3>Deudas con vencimientos de años anteriores</h3>'
          '<div class="resumen">¿Son deuda real o cobros/pagos que no se imputaron en Tango?</div>'
          '<ul>%s%s</ul>'
          '<h3 style="margin-top:10px">Pagos con cheque diferido</h3>'
          '<div class="resumen">¿Están imputados contra las facturas? Si no, Tango muestra como vencido algo que '
          'ya está pagado con cheque.</div></div></div>'
          '<div class="pie">finauto · datos de la planilla NAVAR - Cash Flow (listas Cuentas a Cobrar y Cuentas a Pagar, '
          'cargadas desde Tango) · generado el %s</div></div>'
          % (fecha_datos, fecha_corta(hoy), "".join(tile(b) for b in bloques),
             lista_anteriores(pro, "Proveedores"), lista_anteriores(cli, "Clientes"), fecha_corta(datetime.date.today())))
    p2 = ('<div class="pagina"><h2>Clientes: quién debe y cuánto está vencido</h2>%s<div class="dos">%s%s</div>'
          '<div class="pie">Misma escala en los dos gráficos, para comparar A con AA. Datos: bajada de Tango del %s.</div></div>'
          % (leyenda, bloque_html(cli[0], esc_cli, inicio_anio), bloque_html(cli[1], esc_cli, inicio_anio), fecha_datos))
    p3 = ('<div class="pagina"><h2>Proveedores: a quién se le debe y cuánto está vencido</h2>%s<div class="dos">%s%s</div>'
          '<div class="pie">Misma escala en los dos gráficos, para comparar A con AA. Datos: bajada de Tango del %s.</div></div>'
          % (leyenda, bloque_html(pro[0], esc_pro, inicio_anio), bloque_html(pro[1], esc_pro, inicio_anio), fecha_datos))
    return ('<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Principales clientes y proveedores</title>'
            '<style>%s</style></head><body>%s%s%s</body></html>' % (CSS, p1, p2, p3)), bajada


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", default=None, help="export de la Sheet en Excel (default: el más nuevo de privado/)")
    ap.add_argument("--hoy", default=datetime.date.today().isoformat())
    a = ap.parse_args()
    hoy = datetime.date.fromisoformat(a.hoy)
    fuente = a.sheet or ultimo_export()
    bloques, inicio_anio = leer(fuente, hoy)
    pagina, bajada = armar(bloques, hoy, inicio_anio, fuente)
    os.makedirs(SALIDAS, exist_ok=True)
    base = os.path.join(SALIDAS, "NAVAR - Principales clientes y proveedores %s" % (bajada or hoy).isoformat())
    with open(base + ".html", "w", encoding="utf-8") as f:
        f.write(pagina)
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    "--print-to-pdf=" + base + ".pdf", "file://" + base + ".html"],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("export usado:", os.path.basename(fuente))
    for b in bloques:
        print("%-11s %-2s  top20 %s de %s · vencido %s · +90 días %s"
              % (b["tipo"], b["empresa"], millones(b["suma"]), millones(b["total"]),
                 millones(b["vencido"]), millones(b["mas_90"])))
    print("PDF:", base + ".pdf")


if __name__ == "__main__":
    main()
