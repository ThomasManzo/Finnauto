# -*- coding: utf-8 -*-
"""
dashboard.generar — el HTML que se muestra en la reunión.

QUÉ ES Y QUÉ NO ES
------------------
No es una pantalla de operación. Es **el material con el que se vende y se
entrega la asesoría**, y eso define tres cosas que si no, se hacen mal:

1. **Funciona solo.** Un solo archivo HTML con los datos adentro. Sin servidor,
   sin internet, sin correr Python en el medio de una reunión. Se manda por mail
   y se abre.

2. **Es la pantalla del dueño, no la del analista.** La primera pregunta es
   "¿puedo sacar plata y cuánta?", no el reparto por proveedor. El detalle está,
   pero abajo.

3. **Lleva los hallazgos.** Lo que hace que la asesoría valga no es el número
   lindo: es "tu faro apunta al 1 de abril" y "tu planilla te muestra $915M de
   deuda que no tenés". Eso no sale de un software — sale de mirar. El documento
   tiene que dejarlo por escrito.

Y una regla que atraviesa todo: **dice también lo que no sabe**. La cobranza
vencida que no se contó, los cheques que pueden no ser caja, el escenario que
falta. Un informe que solo muestra lo que le cierra es un folleto.

Uso:
    python dashboard/generar.py --contrato datos/CONTRATO_maga_2026-09-05.json
    python dashboard/generar.py --contrato c.json --salida salidas/reunion.html
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

from simulador import disponibilidad as D
from simulador import posicion as POS
from simulador import proveedores as PROV
# hallazgos() vive en dashboard/datos.py: lo usan la app y este informe.
from dashboard.datos import hallazgos                      # noqa: F401


# ------------------------------------------------------------------ formato
def money(v, decimales=False):
    """Pesos, sin centavos por defecto.

    En pantalla los centavos son ruido: nadie decide un retiro por $0,73 y
    ocupan el ancho que necesita el número que importa.
    """
    signo = "-" if v < 0 else ""
    n = abs(v)
    if decimales:
        ent, dec = divmod(round(n * 100), 100)
        return "%s$%s,%02d" % (signo, format(int(ent), ",d").replace(",", "."), dec)
    return "%s$%s" % (signo, format(int(round(n)), ",d").replace(",", "."))


def corto(v):
    """Para los números grandes de arriba: $2,5 MM en vez de 2.526.125.768."""
    n = abs(v)
    signo = "-" if v < 0 else ""
    if n >= 1e9:
        return "%s$%s MM" % (signo, ("%.2f" % (n / 1e9)).replace(".", ","))
    if n >= 1e6:
        return "%s$%s M" % (signo, ("%.1f" % (n / 1e6)).replace(".", ","))
    return money(v)


def semanas(v):
    """"1,3 sem" y no "1.28571 sem".

    Un decimal alcanza para decidir y seis hacen que el informe parezca la
    salida de un script en vez de algo que alguien miro antes de mandarlo.
    """
    if v is None:
        return "—"
    if abs(v - round(v)) < 0.05:
        return "%d sem" % round(v)
    return ("%.1f" % v).replace(".", ",") + " sem"


def esc(t):
    return html.escape(str(t if t is not None else ""))


def fecha_larga(iso):
    MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
             "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    try:
        d = datetime.date.fromisoformat(iso)
        return "%d de %s de %d" % (d.day, MESES[d.month - 1], d.year)
    except Exception:
        return iso




# ------------------------------------------------------------------ el HTML
CSS = """
:root{
  --tinta:#12211B; --suave:#5A6B63; --tenue:#93A29A;
  --papel:#FFFFFF; --fondo:#F2F6F3; --linea:#DCE7E1;
  --verde:#0F7A4F; --verde-piso:#E4F3EA;
  --rojo:#B3261E; --rojo-piso:#FBEBEA;
  --ambar:#9A6B05; --ambar-piso:#FDF3DF;
}
*{box-sizing:border-box}
body{margin:0;background:var(--fondo);color:var(--tinta);
  font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  -webkit-font-smoothing:antialiased}
.hoja{max-width:940px;margin:0 auto;padding:34px 22px 80px}
h1{font-size:26px;line-height:1.15;margin:0 0 4px;letter-spacing:-.02em}
h2{font-size:13px;text-transform:uppercase;letter-spacing:.09em;color:var(--tenue);
  margin:38px 0 12px;font-weight:700}
.sub{color:var(--suave);margin:0 0 26px;font-size:14px}
.tarjeta{background:var(--papel);border:1px solid var(--linea);border-radius:14px;
  padding:22px 24px;margin-bottom:14px}
.grande{font-size:40px;font-weight:750;letter-spacing:-.03em;line-height:1.05;margin:6px 0}
.veredicto{border-left:5px solid var(--verde);background:var(--verde-piso)}
.veredicto.no{border-left-color:var(--rojo);background:var(--rojo-piso)}
.veredicto .grande{color:var(--verde)}
.veredicto.no .grande{color:var(--rojo)}
.regla{font-size:13.5px;color:var(--suave);margin-top:10px}
table{width:100%;border-collapse:collapse;font-size:14px}
th{text-align:right;font-size:11px;text-transform:uppercase;letter-spacing:.06em;
  color:var(--tenue);font-weight:700;padding:0 0 8px}
th:first-child,td:first-child{text-align:left}
td{text-align:right;padding:9px 0;border-top:1px solid var(--linea);
  font-variant-numeric:tabular-nums}
tr.total td{font-weight:700;border-top:2px solid var(--tinta)}
.num{font-variant-numeric:tabular-nums}
.pos{color:var(--verde)} .neg{color:var(--rojo)}
.chip{display:inline-block;font-size:11px;font-weight:700;padding:2px 8px;
  border-radius:99px;letter-spacing:.03em}
.chip.ok{background:var(--verde-piso);color:var(--verde)}
.chip.mal{background:var(--rojo-piso);color:var(--rojo)}
.chip.medio{background:var(--ambar-piso);color:var(--ambar)}
.hall{border-left:5px solid var(--ambar);background:var(--papel)}
.hall b{color:var(--tinta)}
.hall .titulo{font-weight:700;font-size:16px;margin-bottom:5px}
.hall .monto{font-size:22px;font-weight:750;color:var(--ambar);margin-top:8px;
  font-variant-numeric:tabular-nums}
.nota{font-size:13px;color:var(--suave)}
.dosCol{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.marcado{background:var(--verde-piso)}
.pie{margin-top:44px;padding-top:16px;border-top:1px solid var(--linea);
  font-size:12.5px;color:var(--tenue)}
.envuelve{overflow-x:auto}
@media (max-width:720px){ .dosCol{grid-template-columns:1fr} .grande{font-size:32px} }
@media print{ body{background:#fff} .hoja{padding:0} .tarjeta{break-inside:avoid} }
"""


def render(contrato, cliente="maga", dias_retiro=7, dias_pos=45):
    hoy = D.hoy_de(contrato)
    r = D.retiro(contrato, dias=dias_retiro)
    p45 = D.puente(contrato, dias=dias_pos, con_droguerias=D.VENCIDO)
    us, escen = POS.calcular(contrato, dias=dias_pos)

    try:
        prov = PROV.cargar_proveedores(cliente)
    except Exception:
        prov = {}
    an = PROV.analizar(contrato, prov, float(contrato.get("caja_hoy") or 0),
                       None, datetime.date.fromisoformat(hoy), dias_retiro)

    H = []
    A = H.append
    A('<title>%s — al %s</title>' % (esc(contrato.get("cliente") or "finauto"),
                                     esc(hoy)))
    A('<style>%s</style>' % CSS)
    A('<div class="hoja">')
    A('<h1>%s</h1>' % esc(contrato.get("cliente") or "Informe"))
    A('<p class="sub">Situación al <b>%s</b> · ventana de decisión: %d días</p>'
      % (fecha_larga(hoy), dias_retiro))

    # ---------------------------------------------------------- el veredicto
    A('<div class="tarjeta veredicto%s">' % ("" if r["se_puede"] else " no"))
    A('<div style="font-size:13px;letter-spacing:.07em;text-transform:uppercase;'
      'font-weight:700;color:var(--suave)">¿Se puede retirar plata?</div>')
    if r["se_puede"]:
        A('<div class="grande">Sí, hasta %s</div>' % corto(r["maximo"]))
    else:
        A('<div class="grande">No</div>')
        A('<div style="font-size:17px;font-weight:600">Faltan %s para cubrir lo '
          'que ya venció</div>' % money(r["falta_para_cubrir"]))
    A('<div class="regla">La regla: primero se cubre la deuda con droguerías que '
      '<b>ya venció</b> —la que puede hacer que te corten la compra— y recién lo '
      'que sobra se puede sacar.</div>')
    # LAS DOS VENTANAS, EXPLICADAS JUNTAS.
    # Arriba dice "no se puede retirar" y mas abajo "quedan $5.665M". No se
    # contradicen -- una mira 7 dias y la otra 45 -- pero puestas en la misma
    # hoja sin aclararlo, el lector se queda con que uno de los dos numeros
    # esta mal, y deja de creerle a los dos.
    A('<table style="margin-top:16px;font-size:13.5px">')
    A('<tr><td style="border:0;padding:3px 0">Caja de hoy</td>'
      '<td class="num" style="border:0;padding:3px 0">%s</td></tr>' % money(r["puente"]["caja"]))
    A('<tr><td style="border:0;padding:3px 0">+ lo que entra seguro en %d días</td>'
      '<td class="num pos" style="border:0;padding:3px 0">%s</td></tr>'
      % (dias_retiro, money(r["puente"]["entra_seguro"])))
    A('<tr><td style="border:0;padding:3px 0">− lo que sale en %d días '
      '(incluye la deuda vencida)</td>'
      '<td class="num neg" style="border:0;padding:3px 0">%s</td></tr>'
      % (dias_retiro, money(r["puente"]["sale"])))
    A('<tr><td style="padding:6px 0"><b>Margen a %d días</b></td>'
      '<td class="num %s" style="padding:6px 0"><b>%s</b></td></tr>'
      % (dias_retiro, "pos" if r["margen"] >= 0 else "neg", money(r["margen"])))
    A('</table>')
    A('<div class="regla" style="margin-top:12px">Más abajo el mismo puente a '
      '<b>%d días</b> da otro número, y está bien que así sea: a %d días entra '
      'mes y medio de cobranza. La decisión de retirar se toma con la ventana '
      'corta.</div>' % (dias_pos, dias_pos))
    A('</div>')

    if r["tapa_una_pared"]:
        A('<div class="tarjeta" style="border-left:5px solid var(--ambar)">')
        A('<b>Ojo con lo que viene detrás.</b> En estos mismos %d días vencen '
          '%s más. Pagando todo en fecha el margen sería %s. El retiro entra hoy, '
          'pero se paga con atraso después.'
          % (dias_retiro, money(r["por_vencer_en_ventana"]),
             money(r["margen_pagando_todo"])))
        A('</div>')

    # ---------------------------------------------------------- la caja
    A('<h2>De la caja de hoy a los próximos %d días</h2>' % dias_pos)
    A('<div class="tarjeta"><div class="envuelve"><table>')
    A('<tr><th>Concepto</th><th>Monto</th></tr>')
    A('<tr><td>Caja de hoy (banco + efectivo)</td><td class="num">%s</td></tr>'
      % money(p45["caja"]))
    for nom, v, seguro in p45["cobros"]:
        if not seguro:
            continue
        A('<tr><td style="padding-left:14px;color:var(--suave)">+ %s</td>'
          '<td class="num pos">%s</td></tr>' % (esc(nom), money(v)))
    for nom, v, _ in p45["pagos"]:
        cls = "neg" if v > 0 else "pos"
        A('<tr><td style="padding-left:14px;color:var(--suave)">%s %s</td>'
          '<td class="num %s">%s</td></tr>'
          % ("−" if v > 0 else "+", esc(nom.strip(" -")), cls, money(abs(v))))
    A('<tr class="total"><td>Queda</td><td class="num %s">%s</td></tr>'
      % ("pos" if p45["proyectada_seguro"] >= 0 else "neg",
         money(p45["proyectada_seguro"])))
    A('</table></div>')
    dudoso = p45["entra_todo"] - p45["entra_seguro"]
    if dudoso:
        A('<p class="nota" style="margin-bottom:0">No están contados %s de '
          'cheques en cartera: cuando llega la fecha se decide entre depositarlos '
          '(entra plata) o endosarlos (baja deuda y no entra). Esa diferencia es '
          'la apuesta.</p>' % money(dudoso))
    A('</div>')

    # ---------------------------------------------------------- proveedores
    conTol = [a for a in an if a["tolerancia"] is not None and
              (a["vencido"] or a["por_vencer"])]
    if conTol:
        A('<h2>A quién hay que pagarle primero</h2>')
        A('<div class="tarjeta"><div class="envuelve"><table>')
        A('<tr><th>Proveedor</th><th>Ya vencido</th><th>Vence pronto</th>'
          '<th>Atraso</th><th>Le queda</th></tr>')
        for a in conTol:
            m = a["margen"]
            chip = ("mal" if m is not None and m <= 0 else
                    "medio" if m is not None and m <= 1 else "ok")
            txt = ("te puede cortar" if m is not None and m <= 0
                   else semanas(m) if m is not None else "—")
            A('<tr><td><b>%s</b></td><td class="num">%s</td><td class="num">%s</td>'
              '<td class="num">%s</td><td><span class="chip %s">%s</span></td></tr>'
              % (esc(a["nombre"]), money(a["vencido"]), money(a["por_vencer"]),
                 semanas(a["atraso_semanas"]), chip, esc(txt)))
        A('</table></div>')
        A('<p class="nota" style="margin-bottom:0">Ordenado por <b>margen</b>, no '
          'por monto: primero el que está más cerca de cortarte la compra, aunque '
          'le debas menos.</p>')
        A('</div>')

    # ---------------------------------------------------------- posición
    A('<h2>Cómo queda cada empresa, según a quién le pagues</h2>')
    A('<div class="tarjeta"><div class="envuelve"><table>')
    A('<tr><th>Escenario</th>%s<th>Grupo</th></tr>'
      % "".join("<th>%s</th>" % esc(u) for u in us))
    for i, f in enumerate(escen):
        marca = ' class="marcado"' if "<<" in f["escenario"] else ""
        nombre = f["escenario"].replace("  <<", "").split(". ", 1)[-1]
        A('<tr%s><td><b>%s</b>%s</td>%s<td class="num %s"><b>%s</b></td></tr>'
          % (marca, esc(nombre),
             ' <span class="chip ok">lo que se hace</span>' if marca else "",
             "".join('<td class="num %s">%s</td>'
                     % ("pos" if f["por_unidad"][u] >= 0 else "neg",
                        money(f["por_unidad"][u])) for u in us),
             "pos" if f["total"] >= 0 else "neg", money(f["total"])))
    A('</table></div>')
    if len(escen) >= 3:
        A('<p class="nota" style="margin-bottom:0">La distancia entre el primero y '
          'el último —<b>%s</b>— es <b>lo que te financian tus proveedores</b>. '
          'Es tu línea de crédito real.</p>'
          % money(escen[0]["total"] - escen[-1]["total"]))
    A('</div>')

    # ---------------------------------------------------------- hallazgos
    hs = hallazgos(contrato)
    if hs:
        A('<h2>Lo que encontramos mirando tus números</h2>')
        for h in hs:
            A('<div class="tarjeta hall">')
            A('<div class="titulo">%s</div>' % h["titulo"])
            A('<div class="nota" style="color:var(--suave)">%s</div>' % h["cuerpo"])
            if h["monto"]:
                A('<div class="monto">%s</div>' % money(h["monto"]))
            A('</div>')

    # ---------------------------------------------------------- honestidad
    A('<h2>Lo que este informe no sabe</h2>')
    A('<div class="tarjeta"><ul style="margin:0;padding-left:20px;color:var(--suave)">')
    A('<li><b>Cuándo paga PAMI.</b> Se esperan dos pagos por mes, a mitad y a fin, '
      'pero las fechas se corren. Es el ingreso grande e impredecible del negocio '
      'y es el riesgo que no se puede proyectar.</li>')
    if p45["cobranza_vencida"]:
        A('<li><b>Si entra la cobranza vencida</b> (%s). No está contada arriba.</li>'
          % money(p45["cobranza_vencida"]))
    if dudoso:
        A('<li><b>Qué se hace con los cheques en cartera</b> (%s): se deciden uno '
          'por uno al llegar la fecha.</li>' % money(dudoso))
    A('</ul></div>')

    A('<div class="pie">Generado por finauto a partir del cash del cliente · '
      'datos al %s · los montos no incluyen centavos.</div>' % esc(hoy))
    A('</div>')
    return "\n".join(H)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="El HTML de la reunion")
    ap.add_argument("--contrato", required=True)
    ap.add_argument("--cliente", default="maga")
    ap.add_argument("--salida", default="salidas/informe.html")
    ap.add_argument("--dias", type=int, default=7, help="ventana de decision")
    ap.add_argument("--dias-posicion", type=int, default=45)
    args = ap.parse_args()

    with io.open(args.contrato, encoding="utf-8") as f:
        contrato = json.load(f)

    salida = args.salida
    if not os.path.isabs(salida):
        salida = os.path.join(BASE_REPO, salida)
    d = os.path.dirname(salida)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with io.open(salida, "w", encoding="utf-8") as f:
        f.write("<!doctype html>\n<html lang=\"es\"><head>"
                "<meta charset=\"utf-8\">"
                "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n")
        f.write(render(contrato, args.cliente, args.dias, args.dias_posicion))
        f.write("\n</head></html>")
    print("Listo: %s" % salida)


if __name__ == "__main__":
    main()
