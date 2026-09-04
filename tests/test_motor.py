# -*- coding: utf-8 -*-
"""
tests/test_motor.py — la red de seguridad del motor.

Cada test de acá corresponde a un error REAL que apareció mirando datos de
producción. La idea no es cubrir el 100% del código, es que **ninguno de los
errores que ya nos costó encontrar pueda volver en silencio**.

Se corre sin instalar nada:
    python tests/test_motor.py
"""

import os
import sys
import datetime

BASE_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)

from nucleo import fechas as F
from simulador.semana import meta_de, _rigido
from simulador import consejo as C
from ingestas import cheques as CH

_fallos = []


def ok(cond, nombre, detalle=""):
    if cond:
        print("  [OK]   %s" % nombre)
    else:
        print("  [FALLA] %s   %s" % (nombre, detalle))
        _fallos.append(nombre)


# Catálogo mínimo de prueba: NO usa el de ningún cliente real, así los tests
# valen para cualquier empresa (que es el punto del producto).
CAT = {
    "tipos": {
        "SUELDO":  {"nombre": "Sueldos", "tolerancia": 0, "interno": False, "divisible": False, "consecuencia": "laboral"},
        "PAGO":    {"nombre": "Proveedores", "tolerancia": 15, "interno": False, "divisible": True, "consecuencia": "comercial"},
        "RETIRO":  {"nombre": "Retiro socios", "tolerancia": 999, "interno": False, "divisible": True, "consecuencia": "ninguna"},
        "TRANSF":  {"nombre": "Interna", "tolerancia": None, "interno": True, "divisible": False, "consecuencia": "ninguna"},
    },
    "excepciones": [
        {"contiene": ["CUOTA PRESTAMO"], "nombre": "Cuota de prestamo", "tolerancia": 0,
         "consecuencia": "financiera", "interno": False, "tiene_tolerancia": True},
        {"contiene": ["SPEEDMED"], "nombre": "Interno grupo", "tolerancia": None,
         "consecuencia": "", "interno": True, "tiene_tolerancia": False},
    ],
    "prioridad": ["PAGO", "RETIRO"],
}


# ---------------------------------------------------------------- clasificación
def test_clasificacion():
    print("\n== Clasificación de movimientos ==")

    m = meta_de({"tipo": "SUELDO", "concepto": "sueldos agosto"}, CAT)
    ok(_rigido(m), "un sueldo es rígido")

    m = meta_de({"tipo": "PAGO", "concepto": "proveedor x"}, CAT)
    ok(not _rigido(m) and m["tolerancia"] == 15, "un pago a proveedor aguanta 15 días")

    # ERROR REAL: una cuota de préstamo cargada como retiro de socios llegó a
    # proponerse como "pateable 999 días".
    m = meta_de({"tipo": "RETIRO", "concepto": "PAGO PRESTAMOS - CUOTA PRESTAMO"}, CAT)
    ok(_rigido(m), "la excepción por concepto pisa la tolerancia del tipo",
       "tolerancia=%s (deberia ser 0)" % m["tolerancia"])
    ok(m["nombre"] == "Cuota de prestamo", "la excepción también cambia el nombre")

    # ERROR REAL: transferencias internas contadas como gasto -> mostraba menos plata.
    m = meta_de({"tipo": "PAGO", "concepto": "Transferencia a SPEEDMED"}, CAT)
    ok(m["interno"] is True, "una excepción puede marcar un movimiento como interno")

    # Una excepción SIN dias_tolerancia no debe pisar la del tipo.
    ok(m["tolerancia"] == 15, "excepción sin tolerancia propia no pisa la del tipo",
       "quedó %s" % m["tolerancia"])

    m = meta_de({"tipo": "DESCONOCIDO", "concepto": "algo"}, CAT)
    ok(m["tolerancia"] is None and not _rigido(m), "un tipo desconocido no se asume rígido")


# ---------------------------------------------------------------- fechas
def test_fechas():
    print("\n== Regla de fechas (qué días bajar) ==")
    hoy = datetime.date(2026, 9, 4)

    r = F.rango_a_bajar(None, hoy, True, 0)
    ok(r == (datetime.date(2026, 9, 3), hoy), "primera vez: baja ayer + hoy", str(r))

    r = F.rango_a_bajar("2026-09-01", hoy, True, 0)
    ok(r[0] == datetime.date(2026, 9, 1), "rellena desde la última corrida con éxito", str(r))

    r = F.rango_a_bajar("2026-09-04", hoy, True, 0)
    ok(r[0] == datetime.date(2026, 9, 3), "siempre re-incluye ayer (posteos tardíos)", str(r))

    # HALLAZGO: como 'desde' es siempre min(ayer, ultimo), nunca supera a 'hasta'.
    # O sea que rango_a_bajar NUNCA devuelve None y la rama "sin novedades" del
    # loop es codigo muerto. No es un bug (re-bajar ayer es lo buscado, el
    # clasificador dedup por huellas), pero conviene tenerlo escrito.
    r = F.rango_a_bajar("2026-09-04", hoy, False, 0)
    ok(r == (datetime.date(2026, 9, 3), datetime.date(2026, 9, 3)),
       "aun estando al dia, re-incluye ayer (nunca devuelve None)", str(r))


# ---------------------------------------------------------------- cheques
def test_cheques():
    print("\n== Parser de importes y fechas del banco ==")
    ok(CH._monto("$14.779.136,29") == 14779136.29, "monto argentino con puntos y coma")
    ok(CH._monto("-$1.234,50") == -1234.50, "monto negativo")
    ok(CH._monto("") == 0.0, "monto vacío no rompe")
    ok(CH._fecha("03/09/2026") == "2026-09-03", "fecha dd/mm/aaaa a ISO")
    ok(CH._fecha("no es fecha") is None, "texto que no es fecha devuelve None")
    ok(CH._norm(" Nº de cheque ") == "N DE CHEQUE", "normaliza el encabezado con Nº")


# ---------------------------------------------------------------- consejo
def _egr(id_, fecha, tipo, imp, tol, rigido, divisible):
    return {"id": id_, "fecha": fecha, "tipo": tipo, "nombre": tipo, "importe": imp,
            "tolerancia": tol, "rigido": rigido, "divisible": divisible, "concepto": ""}


def test_consejo():
    print("\n== Motor de consejo ==")
    critico = "2026-09-25"

    rigido = _egr("a", "2026-09-10", "SUELDO", 100.0, 0, True, False)
    lejos = _egr("b", "2026-09-11", "PAGO", 100.0, 3, False, True)     # vence antes del día
    sirve = _egr("c", "2026-09-20", "PAGO", 100.0, 15, False, True)
    despues = _egr("d", "2026-09-26", "PAGO", 100.0, 15, False, True)  # ya está después

    cands = C.candidatos([rigido, lejos, sirve, despues], critico, CAT["prioridad"])
    ids = [c["id"] for c in cands]
    ok(ids == ["c"], "solo propone lo que puede pasar el día crítico", str(ids))

    # A igual prioridad y tolerancia, primero el MÁS GRANDE (pocos movimientos).
    ch = _egr("chico", "2026-09-20", "PAGO", 10.0, 15, False, True)
    gr = _egr("grande", "2026-09-20", "PAGO", 900.0, 15, False, True)
    ids = [c["id"] for c in C.candidatos([ch, gr], critico, CAT["prioridad"])]
    ok(ids[0] == "grande", "a igual tolerancia propone primero el más grande", str(ids))

    # Piso: no proponer montos irrelevantes.
    ids = [c["id"] for c in C.candidatos([ch, gr], critico, CAT["prioridad"], piso=100)]
    ok("chico" not in ids, "el piso descarta los montos chicos", str(ids))

    # Prioridad del cliente: proveedores antes que retiros, aunque el retiro aguante más.
    ret = _egr("ret", "2026-09-20", "RETIRO", 500.0, 999, False, True)
    pag = _egr("pag", "2026-09-20", "PAGO", 500.0, 15, False, True)
    ids = [c["id"] for c in C.candidatos([ret, pag], critico, CAT["prioridad"])]
    ok(ids[0] == "pag", "respeta el orden de pateo del cliente", str(ids))


def test_pago_parcial():
    print("\n== Pago parcial (no es todo o nada) ==")
    desde = datetime.date(2026, 9, 20)
    hasta = datetime.date(2026, 9, 26)
    cob = []

    # Divisible: si faltan 30, se difieren 30 de los 100, no los 100.
    # Caja 150, minimo 130: el 22 sale un pago de 100 -> queda en 50, faltan 80.
    div = _egr("d1", "2026-09-22", "PAGO", 100.0, 15, False, True)
    r = C.armar_plan([div], cob, 150.0, desde, hasta, 130.0, CAT["prioridad"])
    ok(not r["ok"], "detecta que falta plata")
    ok(abs(r["plan"][0]["diferido"] - 80.0) < 0.01,
       "en un pago divisible difiere solo lo que falta",
       "difirió %s" % r["plan"][0]["diferido"])
    ok(abs(r["plan"][0]["paga"] - 20.0) < 0.01, "y paga el resto igual",
       "paga %s" % r["plan"][0]["paga"])

    # NO divisible: es todo o nada (un cheque no se puede partir).
    nod = _egr("n1", "2026-09-22", "PAGO", 100.0, 15, False, False)
    r = C.armar_plan([nod], cob, 150.0, desde, hasta, 130.0, CAT["prioridad"])
    ok(abs(r["plan"][0]["diferido"] - 100.0) < 0.01,
       "un pago NO divisible se posterga entero",
       "difirió %s" % r["plan"][0]["diferido"])


def test_internos_no_mueven_caja():
    print("\n== Los movimientos internos no mueven la caja ==")
    desde = datetime.date(2026, 9, 20)
    hasta = datetime.date(2026, 9, 26)
    interno = _egr("i1", "2026-09-22", "TRANSF", 1000.0, None, False, False)
    # egresos() ya filtra los internos; acá validamos la regla de negocio:
    m = meta_de({"tipo": "TRANSF", "concepto": ""}, CAT)
    ok(m["interno"] is True, "el tipo interno se reconoce como interno")

    serie = C.saldos(500.0, [], [], desde, hasta)
    ok(all(v == 500.0 for _, v in serie), "sin movimientos el saldo no cambia")


if __name__ == "__main__":
    print("=" * 62)
    print("  TESTS DEL MOTOR finauto")
    print("=" * 62)
    test_clasificacion()
    test_fechas()
    test_cheques()
    test_consejo()
    test_pago_parcial()
    test_internos_no_mueven_caja()
    print("\n" + "=" * 62)
    if _fallos:
        print("  %d TEST(S) FALLARON: %s" % (len(_fallos), ", ".join(_fallos)))
        sys.exit(1)
    print("  TODOS LOS TESTS PASARON")
