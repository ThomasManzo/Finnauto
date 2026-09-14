# -*- coding: utf-8 -*-
"""
tablero_pdf — la "vista rapida" del tablero, para mandar por mail.

El tablero de verdad es un HTML que se abre con doble click. Por mail viaja
mal: en el celular se ve chico y un adjunto .html a veces cae en spam. Esto
es lo que se manda en su lugar: las capturas reales de cada capa, una linea
de explicacion por capa y, adelante, la aclaracion de con que datos esta
hecho y que todavia es supuesto.

Usa las capturas de privado/capturas/ (las saca finauto + playwright, ver
LEEME.md) y el mismo estilo que propuesta.py.

Uso:
    python clientes/navar/tablero_pdf.py
    (deja privado/salidas/NAVAR - Tablero vista rapida <fecha>.pdf)
"""

import os
import sys
import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from propuesta import (P, LI, caja, imagen, kpis, numeros, m, pie, E, SALIDAS, TINTA, ROJO, AMBAR,
                       FONDO, mm, A4, SimpleDocTemplate, Spacer, PageBreak, KeepTogether)


def armar():
    N = numeros()
    hoy = datetime.date.today()
    out = os.path.join(SALIDAS, "NAVAR - Tablero vista rapida %s.pdf" % hoy.isoformat())
    doc = SimpleDocTemplate(out, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=18 * mm, bottomMargin=20 * mm,
                            title="NAVAR S.A. — Tablero, vista rápida", author="Thomas Manzo")
    S = [P("NAVAR S.A. — el tablero", "titulo"),
         P("Vista rápida · datos del cash al 31/08/2026", "sub"),
         P("Esto es lo que se mira todos los lunes. El tablero real es un archivo que se abre con doble "
           "click, sin internet; acá van las pantallas tal cual salen hoy, con los datos que ya están "
           "cargados en la planilla nueva."),
         caja([P("<b>Con qué datos está hecho.</b> Con las 6 semanas reales y las 8 proyectadas del cash "
                 "viejo, y los saldos de deuda declarados al 31/08. Son totales semanales, no el detalle "
                 "factura por factura: por eso los proveedores y clientes aparecen como \"(agregado cash "
                 "viejo)\". Cuando entren los listados de Tango, cada uno aparece con su nombre."),
               P("<b>Dos cosas que todavía son supuestos.</b> (1) La vista por empresa: el cash viejo no "
                 "separaba la mayoría de los pagos entre A y AA, así que se asignaron a A hasta confirmarlo; "
                 "vale la vista \"Grupo\", no las de A o AA por separado. (2) Los $%s de cheques en cartera "
                 "no se cuentan como plata hasta que se decida si se depositan o se endosan."
                 % m(N["cheques"], True)[1:])], borde=AMBAR),
         Spacer(1, 4 * mm),
         kpis([(m(N["caja"], True), "en bancos y efectivo, sin cheques", TINTA),
               (m(N["vencido_prov"], True), "vencido con proveedores", ROJO),
               (m(N["saldo45_sin_regularizar"], True), "caja a 45 días si lo vencido sigue sin pagarse", ROJO),
               (m(N["saldo45"], True), "caja a 45 días regularizando lo vencido", ROJO)]),
         PageBreak(),
         KeepTogether([P("Posición: cuánto hay, cuánto se debe, cuándo se queda corta", "h1"),
                       imagen("tablero_posicion_arriba.png"),
                       P("Arriba: caja de hoy, deuda ya vencida, lo que vence en 7 días. Después, lo que "
                         "entra día por día y en qué se va la plata en 45 días.", "nota")]),
         PageBreak(),
         KeepTogether([P("Proyección: el día crítico y qué se puede correr", "h1"),
                       imagen("tablero_proyeccion_capa.png", alto_max=225 * mm),
                       P("La curva de caja a 7, 14, 30 o 45 días. Lo ya vencido entra el primer día; "
                         "destildándolo se ve el escenario \"si lo sigo pateando\". Abajo, qué se puede "
                         "correr y qué no (cheques, sueldos y cuotas de banco nunca).", "nota")]),
         PageBreak(),
         KeepTogether([P("A quién pagar: el reparto de la semana", "h1"),
                       imagen("tablero_a_quien_pagar_capa.png", alto_max=120 * mm),
                       P("Cada proveedor con su vencido, lo que vence pronto y el atraso. Con la lista de "
                         "Cuentas a Pagar de Tango, acá aparece cada uno con nombre y cuánto aguanta antes "
                         "de cortar.", "nota")]),
         Spacer(1, 6 * mm),
         KeepTogether([P("A cobrar: quién nos debe y qué cheques hay", "h1"),
                       imagen("tablero_a_cobrar_capa.png", alto_max=95 * mm),
                       P("Lo facturado y no cobrado, y cada cheque en cartera con su decisión pendiente.", "nota")]),
         Spacer(1, 6 * mm),
         P("Thomas Manzo · %s · confidencial" % hoy.strftime("%d/%m/%Y"), "nota")]
    doc.build(S, onFirstPage=pie, onLaterPages=pie)
    return out


if __name__ == "__main__":
    print("PDF:", armar())
