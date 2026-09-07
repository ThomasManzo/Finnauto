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
from memoria import registro as MEM
from simulador import ajustes as AJ

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
         "consecuencia": "financiera", "interno": False, "tiene_tolerancia": True, "solo_tipos": []},
        {"contiene": ["SPEEDMED"], "nombre": "Interno grupo", "tolerancia": None,
         "consecuencia": "", "interno": True, "tiene_tolerancia": False, "solo_tipos": []},
        {"contiene": ["HONORARIOS DJ"], "nombre": "Honorarios DJ", "tolerancia": None,
         "consecuencia": "", "interno": False, "tiene_tolerancia": False,
         "monto_variable": True, "solo_tipos": []},
        {"contiene": ["DJ"], "nombre": "Honorarios D.Jaimovich", "tolerancia": None,
         "consecuencia": "", "interno": False, "tiene_tolerancia": False,
         "monto_variable": True, "solo_tipos": ["SUELDO"]},
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


# --------------------------------------------------- monto variable (2do eje)
def test_monto_variable():
    print("\n== Monto variable (eje aparte de la fecha) ==")

    # Honorarios DJ: la FECHA es fija (se paga pasada la mitad del mes) pero el
    # MONTO es el 10% del resultado del mes anterior. Confundir los dos ejes fue
    # un error real: yo habia asumido que "variable" queria decir "pateable".
    m = meta_de({"tipo": "SUELDO", "concepto": "HONORARIOS DJ agosto"}, CAT)
    ok(m.get("monto_variable") is True, "una excepcion puede marcar el monto como estimado")
    ok(_rigido(m), "y NO por eso se vuelve pateable: la fecha sigue siendo fija",
       "tolerancia=%s" % m["tolerancia"])

    m = meta_de({"tipo": "PAGO", "concepto": "proveedor comun"}, CAT)
    ok(not m.get("monto_variable"), "un pago comun no queda marcado como estimado")

    # ERROR REAL: una sigla corta significa cosas distintas segun el tipo.
    # 'DJ' es D.Jaimovich en un honorario y DECLARACION JURADA en un impuesto.
    m = meta_de({"tipo": "SUELDO", "concepto": "honorarios DJ julio"}, CAT)
    ok(m.get("monto_variable") is True, "la excepcion aplica dentro de su tipo")
    m = meta_de({"tipo": "PAGO", "concepto": "DJ SICORE 06-2026"}, CAT)
    ok(not m.get("monto_variable"),
       "y NO aplica fuera de su tipo (ahi DJ es declaracion jurada)",
       "nombre=%s" % m.get("nombre"))

    # El estres solo toca los variables, y con 0 no toca nada.
    egr = [_egr("v", "2026-09-20", "SUELDO", 100.0, 0, True, False),
           _egr("f", "2026-09-20", "PAGO", 100.0, 15, False, True)]
    egr[0]["monto_variable"] = True
    sin, extra0 = C.aplicar_estres([dict(e) for e in egr], 0)
    ok(extra0 == 0 and sin[0]["importe"] == 100.0, "sin --estres no se inventa ningun numero")
    con, extra = C.aplicar_estres([dict(e) for e in egr], 20)
    ok(abs(con[0]["importe"] - 120.0) < 0.01, "el estres sube el monto variable")
    ok(abs(con[1]["importe"] - 100.0) < 0.01, "y deja intacto el monto cierto")
    ok(abs(extra - 20.0) < 0.01, "informa cuanto mas serian", "extra=%s" % extra)


# --------------------------------------------------------------- memoria
def _snap(proyectados, corte="2026-09-01"):
    return {"version": 1, "cliente": "maga", "corte": corte, "hasta": "2026-10-01",
            "etiqueta": "test", "caja_hoy": 0.0, "proyectados": proyectados}


def _p(tipo, concepto, fecha, importe):
    return {"ref": "x", "huella": MEM.huella({"tipo": tipo, "concepto": concepto}),
            "fecha": fecha, "importe": importe, "tipo": tipo, "concepto": concepto,
            "monto_variable": False, "tolerancia": 0}


def test_memoria():
    print("\n== Memoria interna (que se proyecto vs que paso) ==")
    corte = datetime.date(2026, 9, 15)

    # La huella tiene que sobrevivir a que cambie la fecha o el monto: es lo que
    # permite decir "este pago se movio" en vez de "desaparecio uno y aparecio otro".
    a = MEM.huella({"tipo": "pago", "concepto": "Drogueria  Suizo S.A."})
    b = MEM.huella({"tipo": "PAGO", "concepto": "DROGUERIA SUIZO S.A."})
    ok(a == b, "la huella ignora mayusculas, acentos y espacios de mas", "%s vs %s" % (a, b))

    snap = _snap([
        _p("PAGO", "igual", "2026-09-05", 100.0),
        _p("PAGO", "corrido", "2026-09-05", 200.0),
        _p("PAGO", "mas caro", "2026-09-05", 300.0),
        _p("PAGO", "nunca paso", "2026-09-05", 400.0),
        _p("PAGO", "todavia no vence", "2026-09-28", 500.0),
    ])
    real = {"movimientos": [
        {"fecha": "2026-09-05", "tipo": "PAGO", "concepto": "igual", "importe": 100.0},
        {"fecha": "2026-09-09", "tipo": "PAGO", "concepto": "corrido", "importe": 200.0},
        {"fecha": "2026-09-05", "tipo": "PAGO", "concepto": "mas caro", "importe": 330.0},
        {"fecha": "2026-09-07", "tipo": "PAGO", "concepto": "sorpresa", "importe": 900.0},
    ]}
    c = MEM.conciliar(snap, real, corte_real=corte, cat=CAT)
    est = dict((f["concepto"], f["estado"]) for f in c["filas"])

    ok(est.get("igual") == "CUMPLIO", "detecta el que salio igual", str(est))
    ok(est.get("corrido") == "CAMBIO_FECHA", "detecta el que se corrio de fecha", str(est))
    ok(est.get("mas caro") == "CAMBIO_MONTO", "detecta el que cambio de monto", str(est))
    ok(est.get("nunca paso") == "NO_APARECIO", "detecta el que nunca ocurrio", str(est))

    # Clave: lo que TODAVIA no vencio no se juzga. Contarlo como incumplido
    # ensuciaria la estadistica con cosas que simplemente no pasaron aun.
    ok("todavia no vence" not in est, "lo que aun no vencio no se cuenta", str(est))

    f = [x for x in c["filas"] if x["concepto"] == "corrido"][0]
    ok(f["desvio_dias"] == 4, "mide cuantos dias se corrio", str(f["desvio_dias"]))
    f = [x for x in c["filas"] if x["concepto"] == "mas caro"][0]
    ok(abs(f["desvio_monto"] - 30.0) < 0.01, "mide por cuanta plata se paso")

    ok([s["concepto"] for s in c["sorpresas"]] == ["sorpresa"],
       "lo que nadie proyecto queda aparte como sorpresa",
       str([s["concepto"] for s in c["sorpresas"]]))

    # Los internos no se proyectan; tampoco tienen que aparecer como sorpresa.
    real2 = {"movimientos": real["movimientos"] + [
        {"fecha": "2026-09-06", "tipo": "TRANSF", "concepto": "entre cuentas propias",
         "importe": 1000.0}]}
    c2 = MEM.conciliar(snap, real2, corte_real=corte, cat=CAT)
    ok(len(c2["sorpresas"]) == 1, "un movimiento interno NO cuenta como sorpresa",
       str([s["concepto"] for s in c2["sorpresas"]]))

    r = dict((x["tipo"], x) for x in MEM.resumen([c]))
    ok(r["PAGO"]["n"] == 4, "el resumen agrupa por tipo", str(r["PAGO"]))
    ok(r["PAGO"]["no_aparecio"] == 1, "y cuenta los que no aparecieron")
    ok(abs(r["PAGO"]["pct_cumplio"] - 25.0) < 0.01, "1 de 4 salio exacto = 25%",
       str(r["PAGO"]["pct_cumplio"]))


# ------------------------------------------------- ajustes manuales de dias
def _e(concepto, tol, cons="comercial", imp=100.0):
    return {"id": concepto, "fecha": "2026-09-20", "tipo": "PAGO", "nombre": "Pago",
            "importe": imp, "tolerancia": tol, "rigido": (tol == 0), "divisible": True,
            "concepto": concepto, "consecuencia": cons}


def test_ajustes():
    print("\n== Ajustes manuales: cuantos dias podes mover ESE pago ==")

    # El catalogo dice lo que NORMALMENTE pasa; el ajuste, lo de esta semana.
    egr = [_e("Drogueria Suizo", 15), _e("Otro proveedor", 15)]
    out, cambios = AJ.aplicar(egr, AJ.desde_cli(["SUIZO=25"]))
    d = dict((x["concepto"], x["tolerancia"]) for x in out)
    ok(d["Drogueria Suizo"] == 25, "el ajuste pisa la tolerancia del catalogo", str(d))
    ok(d["Otro proveedor"] == 15, "y no toca a los demas", str(d))
    ok(len([c for c in cambios if c.get("concepto")]) == 1, "informa que cambio")

    # Sin ajustes no se toca nada: el default nunca deja de ser el default.
    out, cambios = AJ.aplicar([_e("X", 15)], [])
    ok(out[0]["tolerancia"] == 15 and cambios == [], "sin ajustes no cambia nada")

    # Tambien sirve al reves: acortar el plazo porque este mes aprietan.
    out, _ = AJ.aplicar([_e("Suizo", 15)], AJ.desde_cli(["SUIZO=5"]))
    ok(out[0]["tolerancia"] == 5, "tambien se puede acortar, no solo estirar")

    # Poner 0 lo vuelve rigido, y el motor tiene que dejar de proponerlo.
    out, _ = AJ.aplicar([_e("Suizo", 15)], AJ.desde_cli(["SUIZO=0"]))
    ok(out[0]["rigido"] is True, "un ajuste a 0 dias lo vuelve rigido")
    ok(C.candidatos(out, "2026-09-25", ["PAGO"]) == [], "y deja de proponerse")

    # Guardarrail: estirar un cheque/sueldo/impuesto no es "estirar un pago".
    try:
        AJ.aplicar([_e("Cheque 123", 0, cons="BCRA")], AJ.desde_cli(["CHEQUE=10"]))
        ok(False, "frena al intentar estirar algo con consecuencia grave")
    except AJ.AjusteRiesgoso as ex:
        ok("BCRA" in str(ex), "frena al intentar estirar algo con consecuencia grave", str(ex))

    # Pero la decision es del dueno, no del software: con --forzar se puede.
    out, _ = AJ.aplicar([_e("Cheque 123", 0, cons="BCRA")],
                        AJ.desde_cli(["CHEQUE=10"]), permitir_graves=True)
    ok(out[0]["tolerancia"] == 10, "con --forzar igual lo deja simular")

    # Un ajuste mal escrito haria que el escenario salga bien por la razon
    # equivocada. Tiene que avisar, no pasar en silencio.
    _, cambios = AJ.aplicar([_e("Drogueria Suizo", 15)], AJ.desde_cli(["SUISO=25"]))
    ok(any(c.get("sin_efecto") == "SUISO" for c in cambios),
       "avisa cuando un ajuste no matcheo nada", str(cambios))

    try:
        AJ.desde_cli(["SUIZO"])
        ok(False, "rechaza el formato invalido")
    except ValueError:
        ok(True, "rechaza el formato invalido")


# ------------------------------------------------------- formato de moneda
def test_formato():
    print("\n== Formato de moneda (el mismo que la planilla) ==")
    from simulador.semana import _m as fmt
    ok(fmt(1183497652.34) == "$1.183.497.652,34", "miles con punto, decimales con coma",
       fmt(1183497652.34))
    ok(fmt(-114279666) == "-$114.279.666,00", "negativos", fmt(-114279666))
    ok(fmt(0) == "$0,00", "cero")


# --------------------------------------------------- proyeccion automatica
def test_proyeccion():
    print("\n== Proyeccion deducida del historial ==")
    from simulador import proyeccion as PR

    # Agrupar por TEXTO del concepto es lo que parece obvio y es lo que falla:
    # el mismo gasto se escribe distinto cada mes. Por eso el default es 'tipo'.
    a = PR.clave({"tipo": "SUELDO", "concepto": "Sueldos Comafi"})
    b = PR.clave({"tipo": "SUELDO", "concepto": "Cs. Agosto"})
    ok(a == b, "a nivel TIPO, el mismo gasto agrupa aunque cambie el texto")
    a2 = PR.clave({"tipo": "SUELDO", "concepto": "Sueldos Comafi"}, "concepto")
    b2 = PR.clave({"tipo": "SUELDO", "concepto": "Cs. Agosto"}, "concepto")
    ok(a2 != b2, "a nivel CONCEPTO no agrupan: por eso ese nivel cubre menos")

    ok(PR.limpiar("honorarios junio Veronica") == PR.limpiar("honorarios julio Veronica"),
       "el mes dentro del concepto no separa un gasto mensual en dos")
    ok(PR.limpiar("Arciba 07-26") == PR.limpiar("Arciba 08-26"),
       "ni el periodo escrito como 07-26")

    movs = []
    for mes in ("2026-05", "2026-06", "2026-07"):
        movs.append({"fecha": mes + "-10", "tipo": "ALQUILER", "concepto": "x", "importe": 100.0})
        movs.append({"fecha": mes + "-04", "tipo": "SUELDO", "concepto": "y", "importe": 900.0})
    movs.append({"fecha": "2026-06-15", "tipo": "RARO", "concepto": "z", "importe": 50.0})

    pat, prev = PR.aprender(movs, "2026-08")
    ok(prev == ["2026-05", "2026-06", "2026-07"], "aprende solo con los meses anteriores", str(prev))
    ok(pat["ALQUILER"]["dia"] == 10, "saca el dia tipico del mes")
    ok(pat["ALQUILER"]["apariciones"] == 3, "y en cuantos meses aparecio")

    prop = PR.proyectar(pat, "2026-08", minimo_apariciones=2)
    claves = [p["clave"] for p in prop]
    ok("ALQUILER" in claves and "SUELDO" in claves, "propone los recurrentes", str(claves))
    ok("RARO" not in claves, "y descarta lo que paso una sola vez", str(claves))

    # Un mes que YA paso no se puede espiar: si el backtest mirara el mes que
    # esta prediciendo, daria 100% y no serviria para nada.
    movs.append({"fecha": "2026-08-10", "tipo": "SORPRESA", "concepto": "s", "importe": 7.0})
    pat2, _ = PR.aprender(movs, "2026-08")
    ok("SORPRESA" not in pat2, "el backtest no puede ver el mes que esta prediciendo")

    # Febrero no tiene 31: un patron del 31 tiene que caer en el ultimo dia.
    movs31 = [{"fecha": m + "-31", "tipo": "FIN", "concepto": "f", "importe": 1.0}
              for m in ("2025-12", "2026-01")]
    p31, _ = PR.aprender(movs31, "2026-02")
    pr31 = PR.proyectar(p31, "2026-02", 2)
    ok(pr31 and pr31[0]["fecha"] == "2026-02-28", "un pago del 31 cae al ultimo dia de febrero",
       pr31[0]["fecha"] if pr31 else "nada")


# --------------------------------------------- proyeccion a N dias (horizonte)
def test_horizonte():
    print("\n== Proyeccion a N dias (los dos regimenes) ==")
    from simulador import proyeccion as PR

    # Solo dias habiles: el 98% de los movimientos reales cae de lunes a viernes,
    # y proyectar fines de semana ensucia la curva.
    h = PR._habiles(datetime.date(2026, 9, 5), datetime.date(2026, 9, 13))
    ok(all(d.weekday() < 5 for d in h), "no proyecta sabados ni domingos")
    ok(len(h) == 5, "cuenta bien los habiles (5 al 13/09: solo lun-vie del medio)",
       str(len(h)))

    # DIFUSO: algo que pasa casi todos los dias -> se modela como ritmo diario.
    # EVENTO: algo que cae un dia puntual -> se modela como evento.
    movs = []
    f = datetime.date(2026, 6, 1)
    while f < datetime.date(2026, 9, 1):
        if f.weekday() < 5:
            movs.append({"fecha": f.isoformat(), "tipo": "SERVICIO",
                         "concepto": "s", "importe": 100.0})
        if f.day == 10:
            movs.append({"fecha": f.isoformat(), "tipo": "ALQUILER",
                         "concepto": "a", "importe": 9000.0})
        f += datetime.timedelta(days=1)

    perf, _ = PR.perfilar(movs, datetime.date(2026, 9, 1))
    ok(perf["SERVICIO"]["perfil"] == "difuso", "lo que pasa todos los dias es DIFUSO")
    ok(perf["ALQUILER"]["perfil"] == "evento", "lo que cae un dia fijo es EVENTO")
    ok(abs(perf["SERVICIO"]["por_dia_habil"] - 100.0) < 1.0,
       "del difuso saca cuanto drena por dia habil",
       str(perf["SERVICIO"]["por_dia_habil"]))

    proy = PR.proyectar_horizonte(perf, datetime.date(2026, 9, 1), 45)
    ok(all(datetime.date.fromisoformat(p["fecha"]).weekday() < 5 for p in proy),
       "la proyeccion cae toda en dias habiles")
    alq = [p for p in proy if p["clave"] == "ALQUILER"]
    ok("2026-09-10" in [p["fecha"] for p in alq],
       "el evento cae el dia que corresponde cuando es habil",
       str([p["fecha"] for p in alq]))
    ok(len(alq) == 2, "y una vez por mes en el tramo de 45 dias", str(len(alq)))
    # El 10/10/2026 cae sabado: el pago no se pierde, se corre al viernes 9.
    ok("2026-10-09" in [p["fecha"] for p in alq],
       "un evento que cae fin de semana se corre al habil anterior",
       str([p["fecha"] for p in alq]))

    # EL ERROR QUE YA APARECIO: los eventos de dia VARIABLE se descartaban
    # enteros y la proyeccion quedaba ~55% por debajo del real, siempre para el
    # mismo lado. Ahora el dia puede fallar, pero la plata del mes esta.
    # La ventana de historia tiene que ser realista: si los unicos movimientos
    # son los tres del pago, la historia "dura" desde el primero hasta el ultimo
    # (2,2 meses) y el ritmo mensual sale inflado. En una planilla de verdad hay
    # movimientos de otros tipos que definen el periodo observado.
    var = [{"fecha": f, "tipo": "OTRO", "concepto": "o", "importe": 1.0}
           for f in ("2026-06-01", "2026-08-31")]
    for mes, dia in (("2026-06", 5), ("2026-07", 19), ("2026-08", 11)):
        var.append({"fecha": "%s-%02d" % (mes, dia), "tipo": "DROGUERIA",
                    "concepto": "d", "importe": 300.0})
    perf2, _ = PR.perfilar(var, datetime.date(2026, 9, 1))
    proy2 = PR.proyectar_horizonte(perf2, datetime.date(2026, 9, 1), 31)
    total = sum(p["importe"] for p in proy2 if p["clave"] == "DROGUERIA")
    ok(abs(total - 300.0) < 15.0,
       "un pago mensual de dia variable NO se pierde: proyecta el total del mes",
       "proyecto %.0f de 300" % total)

    # Un grupo que aparecio una sola vez no puede inventar un ritmo mensual.
    uno = [{"fecha": "2026-06-10", "tipo": "UNICO", "concepto": "u", "importe": 50.0}]
    p3, _ = PR.perfilar(uno, datetime.date(2026, 9, 1))
    ok(p3["UNICO"]["meses"] == 1, "sabe que solo lo vio un mes")

    # El backtest no puede espiar el tramo que esta prediciendo.
    movs.append({"fecha": "2026-09-15", "tipo": "SORPRESA", "concepto": "z",
                 "importe": 5000.0})
    r = PR.backtest_horizonte(movs, datetime.date(2026, 9, 1), 45)
    ok("SORPRESA" not in r["perfiles"], "no aprende del tramo que esta midiendo")
    ok(r["total_real"] > 0, "y si compara contra lo que realmente paso")

    # El desvio se mide contra el total del tramo. Si se midiera contra el
    # acumulado del dia, el dia 1 daria cientos por ciento y no diria nada.
    ok(r["peor_desvio"] < 1000, "el peor desvio es un numero interpretable",
       "%.0f%%" % r["peor_desvio"])


# ------------------------------------------------- caja completa (dos lados)
def test_caja_completa():
    print("\n== Curva de caja: lo que entra menos lo que sale ==")
    from simulador import proyeccion as PR

    movs, cobros = [], []
    f = datetime.date(2026, 6, 1)
    while f < datetime.date(2026, 9, 1):
        if f.weekday() < 5:
            movs.append({"fecha": f.isoformat(), "tipo": "GASTO",
                         "concepto": "g", "importe": 100.0})
            cobros.append({"fecha": f.isoformat(), "concepto": "Venta",
                           "importe": 150.0})
        f += datetime.timedelta(days=1)
    contrato = {"caja_hoy": 1000.0, "movimientos": movs, "cobros_previstos": cobros}

    r = PR.proyectar_caja(contrato, datetime.date(2026, 9, 1), 10)
    ok(r["caja_inicial"] == 1000.0, "arranca del saldo que se le da")
    ok(r["total_ingresos"] > 0 and r["total_egresos"] > 0,
       "proyecta los DOS lados, no solo los egresos")
    ok(r["curva"][-1]["caja"] > 1000.0,
       "si entra mas de lo que sale, la caja sube")

    # El motor es el mismo para los dos lados: un ingreso es un movimiento con
    # otro signo. Si se invierte la relacion, la curva tiene que bajar.
    c2 = {"caja_hoy": 1000.0, "movimientos": [dict(m, importe=200.0) for m in movs],
          "cobros_previstos": [dict(c, importe=50.0) for c in cobros]}
    r2 = PR.proyectar_caja(c2, datetime.date(2026, 9, 1), 10)
    ok(r2["curva"][-1]["caja"] < 1000.0, "y si sale mas de lo que entra, baja")

    ok(len(r["curva"]) == 10, "una fila por dia del tramo", str(len(r["curva"])))


def test_coherencia():
    print("\n== Detectar que falta un lado de los movimientos ==")
    from simulador import proyeccion as PR

    # EL CASO REAL: en el contrato de MAGA entra 2,5 veces lo que sale, lo que
    # daria +$3.078M por mes con una caja de $1.183M.
    #
    # OJO con la interpretacion. La primera version de este chequeo afirmaba
    # "faltan egresos sin registrar" y estaba MAL: Thomas explico que las
    # compras a droguerias se cancelan con notas de credito, endoso de cheques o
    # compensacion con cuentas a cobrar, asi que nunca tocan la caja. No faltan.
    #
    # Pero en OTRA empresa la misma senal puede ser que no esten cargando los
    # gastos, que si es un agujero. El chequeo detecta y PREGUNTA; no diagnostica.
    movs, cobros = [], []
    f = datetime.date(2026, 6, 1)
    while f < datetime.date(2026, 9, 1):
        if f.weekday() < 5:
            movs.append({"fecha": f.isoformat(), "tipo": "GASTO",
                         "concepto": "g", "importe": 100.0})
            cobros.append({"fecha": f.isoformat(), "concepto": "Venta",
                           "importe": 500.0})
        f += datetime.timedelta(days=1)

    r = PR.revisar_coherencia({"caja_hoy": 1000.0, "movimientos": movs,
                               "cobros_previstos": cobros})
    ok(r and r["avisos"], "avisa cuando entra mucho mas de lo que sale")
    ok(any("PREGUNTAR" in a for a in r["avisos"]),
       "y en vez de diagnosticar, deja la pregunta", str(r["avisos"])[:80])
    ok(any("endoso de cheques" in a for a in r["avisos"]),
       "ofreciendo la explicacion inocente (se cancela por fuera de la caja)")
    ok(any("no se estan cargando" in a for a in r["avisos"]),
       "y tambien la preocupante (gastos sin cargar)")

    # Al reves tambien: una empresa que gasta el doble de lo que declara cobrar.
    r2 = PR.revisar_coherencia({"caja_hoy": 1000.0,
                                "movimientos": [dict(m, importe=500.0) for m in movs],
                                "cobros_previstos": [dict(c, importe=100.0) for c in cobros]})
    ok(any("Sale" in a and "veces lo que entra" in a for a in r2["avisos"]),
       "y avisa el caso contrario", str(r2["avisos"])[:80])

    # Lo normal NO tiene que dar aviso, si no el aviso deja de significar algo.
    r3 = PR.revisar_coherencia({"caja_hoy": 100000.0, "movimientos": movs,
                                "cobros_previstos": [dict(c, importe=110.0) for c in cobros]})
    ok(not r3["avisos"], "un contrato equilibrado no genera ruido", str(r3["avisos"]))

    ok(PR.revisar_coherencia({"movimientos": [], "cobros_previstos": []}) is None,
       "sin datos de un lado no inventa un aviso")


# ------------------------------------------------ completitud de los datos
def test_completitud():
    print("\n== Detectar datos que FALTAN (no errores de calculo) ==")
    from auditoria.revisar import completitud

    def tipos(c):
        return set(t for t, _ in completitud(c))

    # 1) Una unidad con caja pero sin datos: es el caso MAGA. La hoja no se
    #    leia y el contrato salia prolijo con la mitad de la deuda afuera.
    c = {"caja_por_unidad": {"SPEEDMED": 100.0, "MAGA": 200.0},
         "movimientos": [{"fecha": "2026-09-01", "unidad": "SPEEDMED",
                          "tipo": "PAGO", "importe": 10.0}],
         "cobros_previstos": []}
    ok("FALTA UNA UNIDAD" in tipos(c),
       "avisa cuando una unidad tiene caja pero ningun movimiento", str(tipos(c)))

    # Con las dos unidades presentes NO tiene que avisar: si no, el aviso
    # pierde sentido y se ignora.
    c2 = dict(c, movimientos=c["movimientos"] + [
        {"fecha": "2026-09-01", "unidad": "MAGA", "tipo": "PAGO", "importe": 10.0}])
    ok("FALTA UNA UNIDAD" not in tipos(c2), "y no avisa cuando estan todas")

    # 2) Un bloque que termina mucho antes que los demas: la deuda llegaba al
    #    25/09 y el resto al 16/10, y sumarla daba la mitad.
    c3 = {"movimientos": [{"fecha": "2026-10-31", "tipo": "PAGO", "importe": 10.0}],
          "cobros_previstos": [{"fecha": "2026-10-30", "importe": 10.0}],
          "deuda_droguerias": [{"fecha": "2026-09-25", "importe": 10.0}]}
    ok("BLOQUE CORTO" in tipos(c3), "avisa cuando un bloque queda corto",
       str(tipos(c3)))

    c4 = dict(c3, deuda_droguerias=[{"fecha": "2026-10-29", "importe": 10.0}])
    ok("BLOQUE CORTO" not in tipos(c4), "y tolera unos dias de diferencia")

    # 3) Los dos lados desparejos. No se diagnostica -- puede ser que se cancele
    #    por fuera de la caja (correcto) o que falten gastos (agujero).
    c5 = {"movimientos": [{"fecha": "2026-09-01", "tipo": "PAGO", "importe": 100.0}],
          "cobros_previstos": [{"fecha": "2026-09-01", "importe": 500.0}]}
    ok("LADOS DESPAREJOS" in tipos(c5), "avisa si entra mucho mas de lo que sale")
    c6 = {"movimientos": [{"fecha": "2026-09-01", "tipo": "PAGO", "importe": 500.0}],
          "cobros_previstos": [{"fecha": "2026-09-01", "importe": 100.0}]}
    ok("LADOS DESPAREJOS" in tipos(c6), "y tambien al reves")
    c7 = {"movimientos": [{"fecha": "2026-09-01", "tipo": "PAGO", "importe": 100.0}],
          "cobros_previstos": [{"fecha": "2026-09-01", "importe": 120.0}]}
    ok("LADOS DESPAREJOS" not in tipos(c7), "un contrato equilibrado no hace ruido")

    # 4) Movimientos sin tipo: el motor no los puede modelar.
    c8 = {"movimientos": [{"fecha": "2026-09-01", "tipo": "", "importe": 50.0},
                          {"fecha": "2026-09-01", "tipo": "PAGO", "importe": 50.0}],
          "cobros_previstos": []}
    ok("SIN CATEGORIA" in tipos(c8), "avisa por los movimientos sin categoria")

    # 5) Un bloque vacio cuando el otro tiene datos: casi siempre es que no se
    #    encontro, no que la empresa no deba nada.
    c9 = {"movimientos": [], "cobros_previstos": [],
          "cuentas_a_cobrar_droguerias": [{"fecha": "2026-09-01", "importe": 10.0}],
          "deuda_droguerias": []}
    ok("BLOQUE VACIO" in tipos(c9), "avisa si hay cuentas a cobrar y cero deuda")

    # 6) Los avisos del propio export se repiten: viajaban en el contrato y
    #    nadie los miraba.
    c10 = {"movimientos": [], "cobros_previstos": [],
           "avisos": ["OJO: la hoja X tiene columnas de fecha pero no encontre "
                      "los bloques", "Todo bien por aca"]}
    h = [t for t, _ in completitud(c10)]
    ok(h.count("AVISO DEL EXPORT") == 1,
       "repite los avisos del export que importan, y solo esos", str(h))

    ok(completitud({"movimientos": [], "cobros_previstos": []}) == [],
       "un contrato vacio no inventa hallazgos")


# ------------------------------------------------- posicion separada por unidad
def test_posicion_por_unidad():
    print("\n== La posicion va separada por negocio ==")
    from informe.visita import posicion

    # ERROR CONCEPTUAL REAL (05/09/2026). El informe consolidaba MAGA y
    # Speedmed y mostraba "te deben las droguerias" al lado de la deuda de
    # MAGA. Pero MAGA es FARMACIA: le compra a las droguerias, no les vende.
    # Esas cobranzas son de Speedmed, que es la distribuidora.
    #
    # Consolidado daba -$677M. Separado: MAGA -$2.202M y Speedmed +$1.504M.
    # Son dos situaciones opuestas, y el promedio no describe a ninguna.
    contrato = {
        "caja_hoy": 900.0,
        "caja_por_unidad": {"MAGA": 600.0, "SPEEDMED": 300.0},
        "deuda_droguerias": [
            {"unidad": "MAGA", "fecha": "2026-09-10", "importe": 2000.0,
             "estado": "PENDIENTE"},
            {"unidad": "SPEEDMED", "fecha": "2026-09-10", "importe": 1000.0,
             "estado": "PENDIENTE"},
        ],
        # Solo Speedmed tiene cuentas a cobrar: es la que vende.
        "cuentas_a_cobrar_droguerias": [
            {"unidad": "SPEEDMED", "fecha": "2026-09-15", "importe": 1500.0,
             "estado": "A_VENCER"},
            {"unidad": "SPEEDMED", "fecha": "2026-08-15", "importe": 500.0,
             "estado": "VENCIDO"},
        ],
    }
    p = posicion(contrato)
    porU = dict((u["unidad"], u) for u in p["por_unidad"])

    ok(set(porU) == {"MAGA", "SPEEDMED"}, "devuelve una posicion por unidad",
       str(set(porU)))
    ok(porU["MAGA"]["cobrar"] == 0,
       "la farmacia no tiene cuentas a cobrar con droguerias")
    ok(porU["MAGA"]["neto"] == 600.0 - 2000.0,
       "su posicion es caja menos deuda", str(porU["MAGA"]["neto"]))
    ok(porU["SPEEDMED"]["neto"] == 300.0 + 2000.0 - 1000.0,
       "la distribuidora suma lo que le deben", str(porU["SPEEDMED"]["neto"]))
    ok(porU["SPEEDMED"]["vencido"] == 500.0, "y separa lo vencido")

    # Lo importante: los signos son OPUESTOS. Consolidar los promedia y borra
    # justo el hecho que hay que mirar.
    ok(porU["MAGA"]["neto"] < 0 < porU["SPEEDMED"]["neto"],
       "los dos negocios pueden estar en situaciones opuestas")

    # La deuda intercompany no cuenta: no sale plata del grupo.
    c2 = dict(contrato, deuda_droguerias=contrato["deuda_droguerias"] + [
        {"unidad": "MAGA", "fecha": "2026-09-10", "importe": 9999.0,
         "estado": "PENDIENTE", "intercompany": True}])
    p2 = posicion(c2)
    m2 = [u for u in p2["por_unidad"] if u["unidad"] == "MAGA"][0]
    ok(m2["debe"] == 2000.0, "la deuda entre empresas del grupo no se cuenta",
       str(m2["debe"]))


# ------------------------------------------- a quien le pago esta semana
def test_proveedores():
    print("\n== Tolerancia de proveedor, no caja minima ==")
    from simulador import proveedores as PR

    prov = {
        "SUIZO": {"id": "SUIZO", "nombre": "Suizo", "vence": "jueves",
                  "tolerancia_semanas": 3},
        "DROG.DEL SUD": {"id": "DROG.DEL SUD", "nombre": "DDS", "vence": "viernes",
                         "tolerancia_semanas": 3},
    }
    hoy = datetime.date(2026, 9, 10)
    contrato = {"deuda_droguerias": [
        # vencido hace 2 semanas
        {"contraparte": "SUIZO ARGENTINA S.A. (00282)", "fecha": "2026-08-27",
         "importe": 100.0, "unidad": "SPEEDMED", "estado": "PAGADO"},
        # vence dentro de la ventana
        {"contraparte": "SUIZO ARGENTINA S.A. (00282)", "fecha": "2026-09-17",
         "importe": 200.0, "unidad": "SPEEDMED", "estado": "PENDIENTE"},
        {"contraparte": "DROG.DEL SUD S.A (0013)", "fecha": "2026-09-11",
         "importe": 300.0, "unidad": "SPEEDMED", "estado": "PENDIENTE"},
        # una nota de credito: NO es deuda con tolerancia
        {"contraparte": "NCR SUIZO", "fecha": "2026-09-15", "importe": -50.0,
         "unidad": "SPEEDMED", "es_credito": True},
        # la refinanciacion tampoco entra en el reparto semanal
        {"contraparte": "REFINANCIACION", "fecha": "2026-09-25", "importe": 900.0,
         "unidad": "SPEEDMED", "estado": "PENDIENTE"},
    ]}

    an = PR.analizar(contrato, prov, 1000.0, "SPEEDMED", hoy, 21)
    por = dict((a["proveedor"], a) for a in an)

    ok("SUIZO" in por and "DROG.DEL SUD" in por, "agrupa por proveedor", str(list(por)))
    ok(por["SUIZO"]["vencido"] == 100.0, "separa lo vencido de lo que viene")
    ok(por["SUIZO"]["por_vencer"] == 200.0, "y lo que vence en la ventana")

    # El atraso se mide desde la factura MAS VIEJA sin pagar: es el tiempo que
    # el proveedor lleva esperando.
    ok(abs(por["SUIZO"]["atraso_semanas"] - 2.0) < 0.1,
       "el atraso se mide desde la deuda mas vieja",
       str(por["SUIZO"]["atraso_semanas"]))
    ok(abs(por["SUIZO"]["margen"] - 1.0) < 0.1,
       "el margen es la tolerancia menos el atraso", str(por["SUIZO"]["margen"]))

    # Ordena por quien esta MAS CERCA de cortarte, no por quien mas debe.
    ok(an[0]["proveedor"] == "SUIZO",
       "primero el que menos margen le queda, aunque deba menos",
       str([a["proveedor"] for a in an]))

    ok(por["SUIZO"]["credito"] == 50.0, "las NCR van aparte, como credito a favor")
    ok(por["REFINANCIACION"]["tolerancia"] is None,
       "la refinanciacion no tiene tolerancia: es un acuerdo, no una factura")

    # Los escenarios: ninguno es "el correcto", todos tienen costo.
    esc = PR.escenarios(an, 500.0)
    nombres = [e["nombre"] for e in esc]
    ok(any("todo" in n.lower() for n in nombres), "ofrece pagar todo")
    ok(any("nada" in n.lower() for n in nombres), "y no pagar nada")
    todo = [e for e in esc if "todo" in e["nombre"].lower()][0]
    ok(todo["caja_queda"] < 0, "y avisa cuando pagar todo no alcanza",
       str(todo["caja_queda"]))
    nada = [e for e in esc if "nada" in e["nombre"].lower()][0]
    ok(all(sem > 0 for _, sem in nada["atrasos"]),
       "no pagar nada suma una semana de atraso a todos")


def test_rigido_y_endoso():
    print("\n== Lo rigido primero, y el cheque como palanca ==")
    from simulador import proveedores as PR

    hoy = datetime.date(2026, 9, 10)
    cat_tipos = {
        "SUELDO": {"nombre": "Sueldos", "tolerancia": 0, "interno": False},
        "PAGO": {"nombre": "Proveedores", "tolerancia": 15, "interno": False},
        "TRANSFERENCIA": {"nombre": "Interna", "tolerancia": None, "interno": True},
    }
    contrato = {"movimientos": [
        {"fecha": "2026-09-12", "tipo": "SUELDO", "importe": 500.0},
        {"fecha": "2026-09-12", "tipo": "PAGO", "importe": 900.0},          # flexible
        {"fecha": "2026-09-12", "tipo": "TRANSFERENCIA", "importe": 999.0},  # interno
        {"fecha": "2026-10-30", "tipo": "SUELDO", "importe": 700.0},         # fuera
    ]}
    rig, det = PR.obligaciones_rigidas(contrato, cat_tipos, None, hoy, 7)
    ok(rig == 500.0, "solo cuenta lo que no se puede mover", str(rig))
    ok("Sueldos" in det, "y dice de que se trata")

    # La cartera de cheques: opciones dentro de la ventana.
    # RECIBIDO = todavia sin decidir. Es el unico estado que sigue siendo
    # palanca: los otros ya se resolvieron.
    c2 = {"cartera_cheques": [
        {"fecha": "2026-09-12", "importe": 300.0, "estado": "RECIBIDO"},
        {"fecha": "2026-11-20", "importe": 800.0, "estado": "RECIBIDO"},
    ]}
    chs = PR.cheques_endosables(c2, hoy, 7)
    ok(len(chs) == 1 and chs[0]["importe"] == 300.0,
       "solo los cheques que vencen en la ventana", str(len(chs)))

    # LO QUE DECIDE ES LA FECHA, NO EL ESTADO.
    #
    # Thomas me corrigio: "recibido es que ingresan y se hacen caja; depositado
    # no es un estado en el ultimo tiempo; solo se toma recibido como depositado
    # y endosado como endosado". Y antes: "una vez que llega la fecha de cobro
    # se toma la decision de endosar o depositar".
    #
    # O sea que el estado es lo que YA PASO. Un cheque con fecha futura todavia
    # no se decidio, tenga el estado que tenga cargado.
    c3 = {"cartera_cheques": [
        {"fecha": "2026-09-12", "importe": 100.0, "estado": "RECIBIDO"},
        {"fecha": "2026-09-12", "importe": 200.0, "estado": "DEPOSITADO"},
        {"fecha": "2026-09-12", "importe": 300.0, "estado": "ENDOSADO"},
        {"fecha": "2026-09-12", "importe": 400.0, "estado": "ANULADO"},
    ]}
    ids = sorted(x["importe"] for x in PR.cheques_endosables(c3, hoy, 7))
    ok(ids == [100.0, 200.0, 300.0],
       "con fecha futura sigue siendo palanca, sea cual sea el estado", str(ids))
    ok(400.0 not in ids, "salvo los anulados, que ya no existen")

    an = [{"proveedor": "SUIZO", "vencido": 400.0, "por_vencer": 100.0,
           "tolerancia": 3, "margen": 1.0, "atraso_semanas": 2.0}]
    c = PR.consejo(an, caja=1000.0, cobros=200.0, rigido=500.0, cheques=chs)
    ok(abs(c["libre"] - 700.0) < 0.01, "lo libre es caja + cobros - rigido",
       str(c["libre"]))
    txt = " ".join(p["texto"] for p in c["pasos"])
    ok("no se pueden mover" in txt, "el consejo arranca por lo rigido")
    ok("endosas a SUIZO" in txt,
       "y propone endosar contra el proveedor mas urgente", txt[-90:])
    # 500 de deuda menos un cheque de 300 -> queda 200
    ok("200" in txt, "diciendo en cuanto queda la deuda despues", txt[-90:])
    ok(any(p["tipo"] == "alternativa" for p in c["pasos"]),
       "y muestra la otra cara: depositarlos en vez de endosarlos")

    # Los endosos son ACUMULATIVOS. La primera version calculaba cada cheque
    # contra la misma deuda base, como si hubiera que elegir uno solo.
    dos = [{"fecha": "2026-09-12", "importe": 100.0, "estado": "RECIBIDO"},
           {"fecha": "2026-09-13", "importe": 150.0, "estado": "RECIBIDO"}]
    c4 = PR.consejo(an, caja=1000.0, cobros=0.0, rigido=0.0, cheques=dos)
    paso = [p for p in c4["pasos"] if p["tipo"] == "endoso"][0]
    ok(abs(paso["total"] - 250.0) < 0.01, "suma todos los cheques, no uno solo",
       str(paso["total"]))
    ok("250" in paso["texto"], "y lo dice en el texto")

    # Si no alcanza ni para lo rigido, eso se dice primero y fuerte.
    c2 = PR.consejo(an, caja=100.0, cobros=50.0, rigido=500.0, cheques=[])
    ok(any("OJO" in p["texto"] for p in c2["pasos"]),
       "avisa cuando no alcanza ni para lo que no se puede mover")


def test_deuda_vencida():
    """UN MONTO CON FECHA PASADA ES DEUDA VENCIDA, NO UN PAGO HECHO.

    Error real (05/09/2026): el exportador marcaba PAGADO todo lo que tuviera
    fecha anterior a hoy, y el motor lo descartaba. Thomas lo corrigio:

        "si hay un monto en la parte de deuda con droguerias con fecha pasada a
         la de hoy es porque claramente esta vencido (...) son montos que
         justamente vencio y no se pagaron."

    Se perdian $2.526M de deuda vencida -- justo la que decide si una drogueria
    te corta la compra. La razon de fondo: la planilla pone la celda en CERO
    cuando se salda, asi que un importe que sobrevive a su fecha es, por
    definicion, lo que no se pago.
    """
    from simulador import semana as SEM
    from auditoria import contraste as CT

    hoy = datetime.date.today()
    ayer = (hoy - datetime.timedelta(days=9)).isoformat()
    manana = (hoy + datetime.timedelta(days=9)).isoformat()

    contrato = {"generado": hoy.isoformat() + "T00:00:00Z", "deuda_droguerias": [
        {"fecha": ayer,   "contraparte": "SUIZO",          "importe": 100.0},
        {"fecha": manana, "contraparte": "SUIZO",          "importe": 400.0},
        {"fecha": ayer,   "contraparte": "REFINANCIACION", "importe": 700.0},
        {"fecha": ayer,   "contraparte": "MAGA+", "importe": 999.0,
         "intercompany": True},
    ]}

    por_vencer, vencido, por_c = SEM.deuda_resumen(contrato)
    ok(abs(vencido - 800.0) < 0.01,
       "lo que tiene fecha pasada cuenta como vencido, no como pagado",
       str(vencido))
    ok(abs(por_vencer - 400.0) < 0.01, "y lo futuro queda como por vencer",
       str(por_vencer))
    ok("MAGA+" not in por_c, "lo intercompany no es deuda con terceros")

    # La refi vive en el mismo bloque de la planilla, pero Thomas fue claro:
    # "no tiene nada que ver con las droguerias". Sumarla al total de droguerias
    # infla la cifra y mezcla una deuda con tolerancia de proveedor con otra
    # que no la tiene.
    ok(abs(CT._deuda(contrato, True, hoy.isoformat()) - 100.0) < 0.01,
       "el contraste deja la refinanciacion afuera de la deuda con droguerias",
       str(CT._deuda(contrato, True, hoy.isoformat())))

    # El corte vencido/por-vencer se hace con la fecha DEL EXPORT. Si se usara
    # el reloj de la maquina, contrastar un archivo de ayer moveria la linea y
    # apareceria una diferencia que no existe.
    ok(CT._hoy({"generado": "2026-09-05T21:59:30.962Z"}) == "2026-09-05",
       "el corte usa la fecha del export, no la del reloj")

    viejo = {"generado": "2026-09-05T00:00:00Z", "deuda_droguerias": [
        {"fecha": "2026-09-04", "contraparte": "SUIZO", "importe": 100.0},
        {"fecha": "2026-09-06", "contraparte": "SUIZO", "importe": 400.0}]}
    ok(abs(CT._deuda(viejo, True, CT._hoy(viejo)) - 100.0) < 0.01,
       "asi el mismo archivo da siempre el mismo resultado")


def test_puentes_contraste():
    """UNA DIFERENCIA SIN EXPLICAR NO SIRVE DE NADA.

    Decir "hay 18% de diferencia contra la planilla del cliente" deja la
    discusion abierta para siempre. Lo unico que la cierra es mostrar, al peso,
    DE QUE esta hecha esa diferencia.

    Sobre datos reales del 05/09/2026 las dos diferencias resultaron ser:

      . la refinanciacion, que la Calculadora suma como deuda con droguerias
        (fila fija de la planilla) y el motor separa
      . las notas de credito, que la Calculadora NO descuenta del saldo y el
        motor si, porque una NCR baja deuda

    Sumando las dos al numero del motor da exactamente el del cliente.
    """
    from auditoria import contraste as CT

    contrato = {"generado": "2026-09-05T00:00:00Z", "deuda_droguerias": [
        {"fecha": "2026-09-01", "contraparte": "SUIZO",          "importe": 100.0},
        {"fecha": "2026-09-20", "contraparte": "SUIZO",          "importe": 400.0},
        {"fecha": "2026-09-01", "contraparte": "REFINANCIACION", "importe": 70.0},
        {"fecha": "2026-09-20", "contraparte": "REFINANCIACION", "importe": 30.0},
        {"fecha": "2026-09-20", "contraparte": "NCR SUIZO", "importe": -50.0,
         "es_credito": True},
        # Un ajuste negativo DENTRO de una fila normal: el cliente ya lo tiene
        # (suma la fila entera con signo), asi que no es un puente. Contarlo
        # hacia que la cuenta cerrara "por poco", que es peor que no cerrar:
        # parece redondeo y no lo es.
        {"fecha": "2026-09-20", "contraparte": "SUIZO", "importe": -7.0},
    ]}
    hoy = CT._hoy(contrato)

    ok(abs(CT._refi(contrato, True, hoy) - 70.0) < 0.01,
       "el puente de la refi separa lo vencido de lo que viene")
    ok(abs(CT._ncr(contrato, False, hoy) - 50.0) < 0.01,
       "el puente de las NCR cuenta solo las filas rotuladas como nota de credito",
       str(CT._ncr(contrato, False, hoy)))

    # Lo que de verdad importa: que cierre.
    for vencida, suyo in ((True, 170.0), (False, 423.0)):
        mio = CT._deuda(contrato, vencida, hoy)
        p = sum(x[1] for x in CT._puentes_deuda(contrato, vencida))
        ok(abs(mio + p - suyo) < 0.01,
           "los puentes cierran al peso (%s)" % ("vencida" if vencida else "a vencer"),
           "motor %s + puentes %s != %s" % (mio, p, suyo))

    # Y el contraste tiene que DECIR que cierra, no dejarlo como pendiente.
    contrato["referencias_del_cliente"] = {"Calculadora": [
        {"etiqueta": "Deuda droguerias VENCIDA",   "valor": 170.0},
        {"etiqueta": "Deuda droguerias a vencer",  "valor": 423.0}]}
    filas, _ = CT.contrastar(contrato)
    ok(len(filas) == 2 and all(f["cierra"] for f in filas),
       "y el contraste las marca como explicadas, no como pendientes")

    # Un numero escrito por un script, sin formula, puede estar viejo: la
    # "deuda vencida" de la Calculadora paso de $1.456M a $2.526M entre dos
    # exports del mismo dia, con los mismos datos abajo.
    ok(all(not f["formula"] for f in filas),
       "y avisa cuando el numero del cliente no sale de una formula")


def test_disponibilidad():
    """EL PUENTE: de la caja de hoy a lo que se puede sacar.

    El cliente ya tiene esta cuenta armada en su Calculadora, pero Thomas dejo
    claro el rol de cada cosa:

        "Tene en cuenta que la Calculadora en este nuevo software no va a ser el
         faro. El faro lo va a ser el simulador, el dash y demas."

    O sea que se rehace, no se copia. Estos tests fijan las cuatro cosas que el
    motor hace distinto A PROPOSITO, para que nadie las "arregle" despues
    creyendo que son bugs.
    """
    from simulador import disponibilidad as D

    hoy = "2026-09-05"
    dentro = "2026-09-20"
    fuera = "2026-11-30"          # mas alla de los 45 dias

    contrato = {
        "generado": hoy + "T00:00:00Z",
        "caja_hoy": 1000.0,
        "caja_efectivo": 50.0,
        "caja_por_unidad": {"MAGA": 600.0, "SPEEDMED": 350.0},
        "cobros_previstos": [
            {"fecha": dentro, "concepto": "Tarjeta y MP", "importe": 300.0,
             "unidad": "MAGA"},
            {"fecha": dentro, "concepto": "Cartera de CH", "importe": 200.0,
             "unidad": "SPEEDMED"},
            {"fecha": dentro, "concepto": "Transf MAGA+", "importe": 900.0,
             "unidad": "SPEEDMED", "interno": True},
            {"fecha": fuera, "concepto": "Tarjeta y MP", "importe": 700.0,
             "unidad": "MAGA"},
        ],
        "cuentas_a_cobrar_droguerias": [
            {"fecha": dentro, "contraparte": "DDS", "importe": 100.0,
             "unidad": "SPEEDMED"},
            {"fecha": "2026-08-20", "contraparte": "DDS", "importe": 40.0,
             "unidad": "SPEEDMED"},
        ],
        "deuda_droguerias": [
            {"fecha": "2026-09-01", "contraparte": "SUIZO", "importe": 80.0},
            {"fecha": dentro, "contraparte": "SUIZO", "importe": 120.0},
            {"fecha": dentro, "contraparte": "NCR SUIZO", "importe": -30.0,
             "es_credito": True},
            {"fecha": dentro, "contraparte": "REFINANCIACION", "importe": 60.0},
            {"fecha": fuera, "contraparte": "SUIZO", "importe": 5000.0},
        ],
        "egresos_cashflow": [
            {"fecha": dentro, "contraparte": "Sueldos", "importe": 90.0,
             "unidad": "MAGA"},
            {"fecha": fuera, "contraparte": "Sueldos", "importe": 4000.0,
             "unidad": "MAGA"},
        ],
    }

    p = D.puente(contrato, dias=45, minima=100.0, con_droguerias=D.TODO)

    # 1) EL HORIZONTE SE APLICA DE VERDAD.
    # En la Calculadora del cliente, HORIZONTE_DIAS: 45 aparece una sola vez en
    # todo el archivo: en el texto del subtitulo. No filtra nada -- suma todas
    # las columnas futuras de la planilla. Aca es un parametro real.
    ok(abs(p["entra_seguro"] - 400.0) < 0.01,
       "el horizonte filtra: lo que cae despues no entra", str(p["entra_seguro"]))
    ok(all(v < 1000 for _, v, _ in p["pagos"]),
       "y tampoco entra en los pagos")

    # 2) LOS CHEQUES EN CARTERA NO SON CAJA SEGURA.
    # Sobre datos reales, el 45% de la cartera se endosa y nunca pasa por el
    # banco. Contarla como caja infla justo la linea que decide un retiro.
    ok(abs(p["entra_todo"] - p["entra_seguro"] - 200.0) < 0.01,
       "los cheques en cartera van aparte, no como caja segura")
    ok(any(not seguro for _, _, seguro in p["cobros"]),
       "y quedan marcados como lo que son: una opcion")

    # 3) LO INTERNO NO ES UN INGRESO: mueve plata de lugar.
    ok(all("Transf" not in n for n, _, _ in p["cobros"]),
       "una transferencia entre empresas del grupo no suma caja")

    # 4) LAS NCR BAJAN DEUDA, NO SON UN COBRO.
    # La Calculadora hace lo contrario: las suma a los cobros y deja la deuda
    # entera. Son $915M contados dos veces al reves.
    nombres = [n for n, _, _ in p["pagos"]]
    ok(any("notas de credito" in n for n in nombres),
       "las NCR aparecen del lado de los pagos, restando")
    ok(abs(p["sale"] - (80.0 + 120.0 - 30.0 + 60.0 + 90.0)) < 0.01,
       "y netean la deuda en vez de inflar los cobros", str(p["sale"]))

    # 5) LA REFI VA EN SU PROPIA LINEA: es obligacion, pero no es una drogueria
    # y no tiene tolerancia de proveedor.
    ok(any("Refinanciacion" in n for n in nombres),
       "la refinanciacion se muestra aparte de las droguerias")

    # 6) LA COBRANZA VENCIDA NO SE CUENTA COMO SEGURA, pero se avisa.
    ok(abs(p["cobranza_vencida"] - 40.0) < 0.01,
       "lo que nos deben y ya vencio se informa aparte, sin sumarlo")

    # 7) LA CAJA POR UNIDAD ES SOLO BANCOS.
    # El efectivo de la grilla de SALDOS es un total del grupo y no dice de que
    # empresa es. Repartirlo con un criterio inventado seria peor que avisar.
    pu = D.puente(contrato, dias=45, unidad="MAGA", con_droguerias=D.TODO)
    ok(abs(pu["caja"] - 600.0) < 0.01, "por unidad, la caja es la del banco")
    ok(abs(pu["efectivo_sin_asignar"] - 50.0) < 0.01,
       "y el efectivo del grupo se avisa en vez de repartirse")


def test_posicion_por_unidad():
    """LA POSICION DE CADA EMPRESA, SEGUN A QUIEN LE PAGUES.

    Los dos escenarios que Thomas mira todos los dias, calculados a la fecha del
    export en vez de a una celda fija.

    Y un invariante que vale para cualquier grupo: UN PAGO ENTRE DOS EMPRESAS
    DEL MISMO GRUPO NO PUEDE CAMBIAR EL TOTAL. La plata se mueve de bolsillo,
    no desaparece. Ese chequeo fue el que detecto que el escenario 3 estaba mal
    calculado -- el total del grupo cambiaba -- y por eso el escenario no se
    publica: la deuda de MAGA con Speed no esta cargada del lado de MAGA.
    """
    from simulador import posicion as P

    hoy = "2026-09-05"
    dentro = "2026-09-20"
    contrato = {
        "generado": hoy + "T00:00:00Z",
        "caja_hoy": 1000.0,
        "caja_por_unidad": {"MAGA": 600.0, "SPEEDMED": 400.0},
        "cobros_previstos": [],
        "cuentas_a_cobrar_droguerias": [],
        "egresos_cashflow": [
            {"fecha": dentro, "contraparte": "Sueldos", "importe": 100.0,
             "unidad": "MAGA"},
        ],
        "deuda_droguerias": [
            {"fecha": dentro, "contraparte": "SUIZO", "importe": 300.0,
             "unidad": "MAGA"},
            {"fecha": dentro, "contraparte": "DDS", "importe": 250.0,
             "unidad": "SPEEDMED"},
        ],
    }

    us, filas = P.calcular(contrato, dias=45)
    ok(us == ["MAGA", "SPEEDMED"],
       "las empresas salen del contrato, no estan hardcodeadas", str(us))
    ok(len(filas) == 3, "son tres escenarios: los dos bordes y el del medio")
    ok("<<" in filas[1]["escenario"],
       "y el marcado es el del medio, que es el que se usa de verdad")

    # Borde de abajo: no se paga nada -> solo pesan los egresos.
    ok(abs(filas[0]["por_unidad"]["MAGA"] - 500.0) < 0.01,
       "sin pagarles nada, la deuda no resta", str(filas[0]["por_unidad"]))
    ok(abs(filas[0]["por_unidad"]["SPEEDMED"] - 400.0) < 0.01,
       "y cada empresa queda con lo suyo")

    # EL DEL MEDIO: se cubre lo vencido y se deja correr lo que no vencio.
    # Aca toda la deuda es futura, asi que tiene que dar igual que el borde de
    # abajo -- si diera distinto, estaria cobrando deuda que todavia no vencio.
    ok(abs(filas[1]["por_unidad"]["MAGA"] - 500.0) < 0.01,
       "pagando solo lo vencido, la deuda futura no pesa",
       str(filas[1]["por_unidad"]))

    # Borde de arriba: se paga todo en fecha.
    ok(abs(filas[2]["por_unidad"]["MAGA"] - 200.0) < 0.01,
       "pagando todo, la deuda resta de la empresa que la tiene")
    ok(abs(filas[2]["por_unidad"]["SPEEDMED"] - 150.0) < 0.01,
       "y de la otra tambien, cada una la suya")

    ok(abs((filas[1]["total"] - filas[2]["total"]) - 550.0) < 0.01,
       "el salto del medio al borde de arriba es lo que te financian")

    # EL INVARIANTE: lo intercompany no cambia el total del grupo.
    from simulador import disponibilidad as D
    con_inter = dict(contrato)
    con_inter["deuda_droguerias"] = contrato["deuda_droguerias"] + [
        {"fecha": dentro, "contraparte": "MAGA+", "importe": 90.0,
         "unidad": "SPEEDMED", "intercompany": True},
        {"fecha": dentro, "contraparte": "SPEEDMED", "importe": -90.0,
         "unidad": "MAGA", "intercompany": True},
    ]
    t = sum(D.puente(con_inter, dias=45, unidad=u, con_droguerias=D.TODO,
                     con_intercompany=True)["proyectada_seguro"]
            for u in us)
    ok(abs(t - filas[2]["total"]) < 0.01,
       "un pago entre empresas del grupo no cambia el total del grupo", str(t))

    # Y cuando esta cargado de un solo lado, se dice cual y cuanto.
    solo_uno = dict(contrato)
    solo_uno["deuda_droguerias"] = contrato["deuda_droguerias"] + [
        {"fecha": dentro, "contraparte": "MAGA+", "importe": 90.0,
         "unidad": "SPEEDMED", "intercompany": True}]
    f, por_u = P.diagnostico_esc3(solo_uno)
    ok(len(f) == 1 and list(por_u) == ["SPEEDMED"],
       "y el diagnostico dice de que lado quedo cargado")


def test_retiro():
    """LA REGLA DEL RETIRO, con las palabras de Thomas (06/09/2026):

        "La decision la tomaria en base a la deuda efectivamente VENCIDA. Si
         podemos pagar esa deuda y dejar un resto para retirar, estaria ok. Si
         con lo que tenemos no llegamos a cubrir esa deuda, patearia el retiro."

    Reemplaza a la regla anterior del motor -- caja proyectada menos una "caja
    minima" -- que tenia el problema de que el minimo era un numero inventado.
    La deuda vencida no: es un hecho, y es justo la que puede hacer que te
    corten la compra.
    """
    from simulador import disponibilidad as D

    hoy = "2026-09-05"
    base = {
        "generado": hoy + "T00:00:00Z",
        "caja_hoy": 1000.0,
        "cobros_previstos": [], "cuentas_a_cobrar_droguerias": [],
        "egresos_cashflow": [],
        "deuda_droguerias": [
            {"fecha": "2026-09-01", "contraparte": "SUIZO", "importe": 300.0},
            {"fecha": "2026-09-08", "contraparte": "SUIZO", "importe": 5000.0},
        ],
    }

    r = D.retiro(base, dias=7)
    ok(abs(r["vencido"] - 300.0) < 0.01, "mide lo que ya vencio", str(r["vencido"]))
    ok(abs(r["margen"] - 700.0) < 0.01,
       "el margen es lo que queda despues de cubrirlo", str(r["margen"]))
    ok(r["se_puede"] and abs(r["maximo"] - 700.0) < 0.01,
       "y ese margen es el maximo que se puede sacar")

    # LA PARED DE ATRAS.
    # Contar los cobros de la ventana contra la deuda vencida de HOY infla el
    # margen. Con 45 dias el motor llego a decir "podes retirar $5.665M" cuando
    # en esa misma ventana vencian $7.849M mas. Un margen positivo puede estar
    # tapando una pared, y eso hay que decirlo.
    ok(r["tapa_una_pared"],
       "avisa cuando el margen positivo tapa lo que vence en la misma ventana")
    ok(abs(r["por_vencer_en_ventana"] - 5000.0) < 0.01,
       "y dice cuanto es esa pared", str(r["por_vencer_en_ventana"]))

    # Cuando no alcanza ni para lo vencido, no se retira.
    flaco = dict(base, caja_hoy=100.0)
    r2 = D.retiro(flaco, dias=7, pedido=50.0)
    ok(not r2["se_puede"], "si no se cubre lo vencido, no se retira")
    ok(abs(r2["falta_para_cubrir"] - 200.0) < 0.01,
       "y dice cuanto falta para cubrirlo", str(r2["falta_para_cubrir"]))
    # Dos faltantes distintos: los tenia mezclados en uno y el titular mentia.
    ok(abs(r2["falta_para_el_retiro"] - 250.0) < 0.01,
       "aparte de cuanto falta para el retiro pedido",
       str(r2["falta_para_el_retiro"]))


def test_modos_de_pago():
    """Los tres modos, y por que el del medio es el default."""
    from simulador import disponibilidad as D

    hoy = "2026-09-05"
    c = {"generado": hoy + "T00:00:00Z", "caja_hoy": 0.0,
         "cobros_previstos": [], "cuentas_a_cobrar_droguerias": [],
         "egresos_cashflow": [],
         "deuda_droguerias": [
             {"fecha": "2026-09-01", "contraparte": "SUIZO", "importe": 100.0},
             {"fecha": "2026-09-20", "contraparte": "SUIZO", "importe": 400.0}]}

    ok(abs(D.puente(c, 45, con_droguerias=D.NADA)["sale"]) < 0.01,
       "modo nada: no se paga deuda de droguerias")
    ok(abs(D.puente(c, 45, con_droguerias=D.VENCIDO)["sale"] - 100.0) < 0.01,
       "modo vencido: solo lo que ya vencio")
    ok(abs(D.puente(c, 45, con_droguerias=D.TODO)["sale"] - 500.0) < 0.01,
       "modo todo: vencido mas lo que vence en la ventana")
    ok(abs(D.puente(c, 45)["sale"] - 100.0) < 0.01,
       "y el default es el del medio, que es lo que se hace de verdad")
    # Compatibilidad con los booleanos viejos, para no romper lo ya escrito.
    ok(D.puente(c, 45, con_droguerias=True)["con_droguerias"] == D.TODO,
       "True sigue significando 'todo'")
    ok(D.puente(c, 45, con_droguerias=False)["con_droguerias"] == D.NADA,
       "y False, 'nada'")


def test_hallazgos_del_informe():
    """LOS HALLAZGOS SE CALCULAN, Y NO PUEDEN SER FALSOS.

    El informe le dice al cliente "esto que tenes esta mal". Si uno de esos
    señalamientos es falso, no cuesta un renglon: cuesta la credibilidad de
    todos los demas, incluidos los que si son ciertos.

    FALSO POSITIVO REAL (06/09/2026): la primera version marcaba cualquier
    referencia a una celda de columna A, B o C, y saco como hallazgo que "Caja
    hoy apunta a SALDOS!C26 -- mira una fecha vieja". SALDOS no es un cashflow:
    sus columnas son bancos, no fechas, y C26 es el total correcto.

    Y se calculan sobre el contrato, nunca a mano: si el cliente arregla algo,
    el hallazgo desaparece solo. Uno hardcodeado sobrevive a su propia solucion.
    """
    from dashboard import generar as G

    base = {"generado": "2026-09-05T00:00:00Z", "caja_hoy": 0.0,
            "deuda_droguerias": [], "cuentas_a_cobrar_droguerias": [],
            "cartera_cheques": []}

    # Una referencia a la grilla de SALDOS NO es un hallazgo.
    c = dict(base, referencias_del_cliente={"Calculadora": [
        {"etiqueta": "Caja hoy", "valor": 100.0, "formula": "=SALDOS!C26",
         "apunta_a": [{"hoja": "SALDOS", "celda": "C26", "fila": 26,
                       "rotulo": "TOTAL", "valor": 100.0}]}]})
    ok(not G.hallazgos(c),
       "una referencia a SALDOS no se marca como fecha vieja",
       str([h["titulo"] for h in G.hallazgos(c)]))

    # Una referencia a la PRIMERA columna de un cashflow si lo es.
    c2 = dict(base, referencias_del_cliente={"Posicion": [
        {"etiqueta": "Speedmed", "valor": 333.0,
         "formula": "='Cash Flow Diario-Speed'!B50",
         "apunta_a": [{"hoja": "Cash Flow Diario-Speed", "celda": "B50",
                       "fila": 50, "rotulo": "Saldo cierre", "valor": 333.0}]}]})
    hs = G.hallazgos(c2)
    ok(len(hs) == 1 and "fecha vieja" in hs[0]["titulo"],
       "y una a la primera columna del cashflow si", str(hs))

    # Las NCR salen del dato: si no hay, no hay hallazgo.
    c3 = dict(base, deuda_droguerias=[
        {"fecha": "2026-09-20", "contraparte": "NCR SUIZO", "importe": -50.0,
         "es_credito": True}])
    hs3 = G.hallazgos(c3)
    ok(any(h["monto"] == 50.0 for h in hs3),
       "el hallazgo de las NCR sale del contrato, no esta escrito a mano")
    ok(not G.hallazgos(base),
       "y un contrato sin nada raro no genera ningun hallazgo")

    # Los cheques endosados: solo si son una parte relevante de la cartera.
    c4 = dict(base, cartera_cheques=[
        {"fecha": "2026-09-10", "importe": 900.0, "estado": "ENDOSADO"},
        {"fecha": "2026-09-10", "importe": 100.0, "estado": "RECIBIDO"}])
    ok(any("90%" in h["titulo"] for h in G.hallazgos(c4)),
       "y el de los cheques dice el porcentaje real de la cartera",
       str([h["titulo"] for h in G.hallazgos(c4)]))

    # Formato: seis decimales en las semanas hacen que parezca salida de script.
    ok(G.semanas(1.285714) == "1,3 sem", "las semanas van con un decimal",
       G.semanas(1.285714))
    ok(G.semanas(3.0) == "3 sem", "y sin decimal cuando es redondo")


def test_tablero():
    """LAS CAPAS DEL TABLERO, cada una con lo suyo.

    El tablero es hoy el entregable: es lo que se muestra en la reunion. Si una
    capa se rompe en silencio, el que se entera es el cliente.

    Y hay un invariante que vale la pena fijar: TODO SE CALCULA EN PYTHON. El
    JavaScript solo muestra. Por eso estos tests le pegan a datos.py y no al
    HTML: si la plata se calculara en el navegador, no habria nada que testear.
    """
    from dashboard import datos as DA

    hoy = "2026-09-05"
    contrato = {
        "generado": hoy + "T00:00:00Z",
        "cliente": "Prueba",
        "caja_hoy": 1000.0,
        "caja_por_unidad": {"MAGA": 600.0, "SPEEDMED": 400.0},
        "cobros_previstos": [
            {"fecha": "2026-09-08", "concepto": "Tarjeta y MP", "importe": 300.0,
             "unidad": "MAGA"},
            {"fecha": "2026-09-08", "concepto": "PAMI", "importe": 700.0,
             "unidad": "MAGA"},
            {"fecha": "2026-09-09", "concepto": "Tarjeta y MP", "importe": 100.0,
             "unidad": "MAGA"},
            {"fecha": "2026-09-08", "concepto": "Transf MAGA+", "importe": 999.0,
             "unidad": "SPEEDMED", "interno": True},
        ],
        "cuentas_a_cobrar_droguerias": [
            {"fecha": "2026-08-20", "contraparte": "DDS", "importe": 50.0,
             "unidad": "SPEEDMED"},
            {"fecha": "2026-09-20", "contraparte": "DDS", "importe": 200.0,
             "unidad": "SPEEDMED"},
        ],
        "cartera_cheques": [
            {"fecha": "2026-09-10", "importe": 80.0, "estado": "RECIBIDO",
             "librador": "Farmacia X"},
            {"fecha": "2026-09-10", "importe": 20.0, "estado": "ANULADO"},
        ],
        "deuda_droguerias": [
            {"fecha": "2026-09-01", "contraparte": "SUIZO", "importe": 100.0,
             "unidad": "MAGA"}],
        "egresos_cashflow": [
            {"fecha": "2026-09-07", "contraparte": "Sueldos", "importe": 90.0,
             "unidad": "MAGA"}],
        "movimientos": [],
    }

    # --- el grafico de ingresos: por dia y por fuente
    g = DA.ingresos_por_dia(contrato, "MAGA", hoy)
    ok(g["fuentes"][0] == "PAMI",
       "las fuentes se ordenan por peso, no alfabeticamente", str(g["fuentes"]))
    ok(len(g["dias"]) == 2, "un punto por dia con movimiento", str(len(g["dias"])))
    ok(all(len(d["valores"]) == len(g["fuentes"]) for d in g["dias"]),
       "y todos los dias tienen una barra por fuente (aunque sea cero)")
    # Lo interno mueve plata de lugar: no es un ingreso del grupo.
    gs = DA.ingresos_por_dia(contrato, "SPEEDMED", hoy)
    ok(not gs["dias"], "una transferencia entre empresas del grupo no entra al grafico")

    # --- a cobrar: el sentido importa
    c = DA.a_cobrar(contrato, "SPEEDMED", hoy)
    ok(abs(c["vencido"] - 50.0) < 0.01 and abs(c["por_vencer"] - 200.0) < 0.01,
       "a cobrar separa lo vencido de lo que viene")
    cg = DA.a_cobrar(contrato, "GRUPO", hoy)
    ok(abs(cg["cheques_total"] - 80.0) < 0.01,
       "y los cheques anulados no cuentan", str(cg["cheques_total"]))
    # LA CARTERA SIN UNIDAD NO SE LE ATRIBUYE A NADIE.
    # Le estaba mostrando a MAGA $208M de cheques que son de Speedmed. Si el
    # export no dice de quien son, se ven solo en el grupo y se avisa -- que es
    # mejor que repartirlos con un criterio inventado.
    ok(abs(c["cheques_total"]) < 0.01 and c["cheques_sin_unidad"],
       "y una cartera sin empresa no se le atribuye a ninguna")
    # UNA FARMACIA SI TIENE QUIEN LE DEBA: las obras sociales.
    #
    # El tablero le mostraba $0 a MAGA y Thomas salto: "como que no te deben
    # nada? Y el pago de obras sociales?". Yo solo miraba las cuentas a cobrar
    # a droguerias -- que son de Speedmed, porque MAGA les COMPRA. Que las
    # obras sociales esten cargadas en el bloque de ingresos no las hace menos
    # cuentas a cobrar.
    contrato["cobros_previstos"].append(
        {"fecha": "2026-09-15", "concepto": "Cobro O.Sociales", "importe": 400.0,
         "unidad": "MAGA"})
    cm = DA.a_cobrar(contrato, "MAGA", hoy)
    ok(any("Sociales" in f["nombre"] for f in cm["filas"]),
       "las obras sociales son cuentas a cobrar de la farmacia", str(cm["filas"]))
    ok(not any(f["que_es"] == "drogueria" for f in cm["filas"]),
       "pero no cuentas a cobrar a droguerias: a esas les compra, no les vende")
    # Del bloque de ingresos solo cuenta el futuro: ahi la planilla no limpia
    # la celda al cobrar, asi que una fecha pasada YA entro.
    contrato["cobros_previstos"].append(
        {"fecha": "2026-08-01", "concepto": "Cobro O.Sociales", "importe": 9999.0,
         "unidad": "MAGA"})
    cm2 = DA.a_cobrar(contrato, "MAGA", hoy)
    ok(abs(cm2["vencido"]) < 0.01,
       "y una fecha pasada del bloque de ingresos no es deuda vencida a favor",
       str(cm2["vencido"]))

    # --- el paquete completo, que es lo que consume el HTML
    p = DA.armar(contrato, "maga")
    ok(p["unidades"][0] == "GRUPO", "la primera vista es el grupo entero")
    for u in p["unidades"]:
        d = p["datos"][u]
        for k in ("kpis", "puente", "proveedores", "salidas", "gastos",
                  "escenarios", "retiro", "ingresos_dia", "a_cobrar", "proyeccion"):
            ok(k in d, "el paquete de %s trae %s" % (u, k))

    # Las cuatro ventanas vienen PRECALCULADAS: mover el selector en el tablero
    # no puede recalcular nada, porque entonces la cuenta viviria en el navegador.
    ok(sorted(p["datos"]["GRUPO"]["retiro"].keys()) == ["14", "30", "45", "7"],
       "las cuatro ventanas del retiro vienen resueltas de Python")


def test_atraso_y_alias():
    """EL ATRASO, Y LAS DOS FORMAS DE ESCRIBIR LA MISMA DROGUERIA.

    Los dos errores que marco Thomas el 06/09/2026 mirando el tablero, y los
    dos son de la clase que mas duele: numeros que parecen razonables y estan
    mal, en la pantalla que decide a quien se le paga.
    """
    import datetime as dt
    from simulador import proveedores as P

    hoy = dt.date(2026, 9, 5)
    fichas = {"COFALOZA": {"nombre": "Cofaloza", "tolerancia_semanas": 3},
              "DROG.DEL SUD": {"nombre": "DDS", "tolerancia_semanas": 3}}

    # UN RESTO VIEJO Y CHICO NO DEFINE EL ATRASO DE TODO EL PROVEEDOR.
    # Thomas: "cofaloza dice que estas atrasado 5.1 semanas, pero es mentira,
    # estas atrasado 1 semana nada mas". El resto de $1,3M del 31/07 -- el 0,4%
    # del total -- arrastraba el atraso de $345M.
    filas = [{"fecha": "2026-07-31", "importe": 1320670.0},
             {"fecha": "2026-08-28", "importe": 190533715.0},
             {"fecha": "2026-09-04", "importe": 153169969.0}]
    sem, desde, ign = P.semanas_de_atraso(filas, hoy)
    ok(desde == "2026-08-28", "el atraso se mide desde el resumen que importa", desde)
    ok(abs(sem - 8 / 7.0) < 0.01, "o sea 1,1 semanas y no 5,1", str(sem))
    ok(len(ign) == 1 and ign[0]["fecha"] == "2026-07-31",
       "y el resto viejo se informa aparte, no se borra de la deuda")

    # Si todos los montos son parecidos, no se ignora ninguno.
    parejo = [{"fecha": "2026-08-01", "importe": 100.0},
              {"fecha": "2026-09-01", "importe": 110.0}]
    _, desde2, ign2 = P.semanas_de_atraso(parejo, hoy)
    ok(desde2 == "2026-08-01" and not ign2,
       "con montos parejos vale el mas viejo, que es la regla de siempre")

    # LA MISMA DROGUERIA ESCRITA DE DOS FORMAS ES UNA SOLA.
    # En la vista del grupo, DDS aparecia dos veces: "Drogueria del Sud (DDS)"
    # desde la planilla de Speed y "Dds" desde la de MAGA.
    for rotulo in ("Dds", "DROG.DEL SUD S.A (0013)", "Drogueria del Sud"):
        pid, _ = P._match(rotulo, fichas)
        ok(pid == "DROG.DEL SUD", "'%s' es la misma drogueria" % rotulo, str(pid))
    ok(P._match("SUIZO ARGENTINA S.A. (00282)", fichas)[0] == "SUIZO",
       "y el nombre largo con numero de cuenta tambien matchea")

    # SE ORDENA POR ATRASO, NO POR TOLERANCIA.
    # Thomas: "no ordenemos por tolerancia, ordenemos por atraso". La
    # tolerancia es una estimacion nuestra; el atraso es un hecho.
    contrato = {"deuda_droguerias": [
        {"fecha": "2026-09-04", "contraparte": "Dds", "importe": 900.0},
        {"fecha": "2026-08-20", "contraparte": "COFALOZA", "importe": 100.0}]}
    an = P.analizar(contrato, fichas, 0, None, hoy, 21)
    ok(an[0]["nombre"] == "Cofaloza",
       "primero el mas atrasado, aunque le debas menos",
       str([(a["nombre"], a["atraso_semanas"]) for a in an]))


def test_proyeccion_por_partes():
    """LA PROYECCION VIAJA POR PARTES, para que se pueda tocar.

    Thomas: "esta solapa lo que te tiene que mostrar es que puedo hacer para
    llegar bien, que obligaciones tengo que patear". Una curva cerrada no
    contesta eso.

    Se devuelven los montos por dia Y POR GRUPO, ya resueltos; el navegador
    suma los grupos tildados. Sigue valiendo que la plata se calcula en Python:
    lo que hace el HTML es una suma, no un modelo.
    """
    from dashboard import datos as DA

    ok(DA._grupo_de("Retiro de Socios") == "socios", "los retiros son su propio grupo")
    ok(DA._grupo_de("REFINANCIACION") == "refi", "la refi tambien")
    ok(DA._grupo_de("Pago a droguerias") == "droguerias",
       "y 'Pago a droguerias' del bloque de egresos es drogueria",
       DA._grupo_de("Pago a droguerias"))
    ok(DA._grupo_de("Pago de mercaderia CHEQUES") == "mercaderia",
       "los cheques a pagar van aparte: no se pueden patear")
    ok(DA._grupo_de("Sueldos y Cs Soc Comafi") == "sueldos", "los sueldos tampoco")

    hoy = "2026-09-05"
    contrato = {"generado": hoy + "T00:00:00Z", "caja_hoy": 1000.0,
                "cobros_previstos": [], "egresos_cashflow": [],
                "deuda_droguerias": [
                    {"fecha": "2026-09-10", "contraparte": "SUIZO", "importe": 300.0},
                    {"fecha": "2026-09-12", "contraparte": "REFINANCIACION",
                     "importe": 100.0}]}
    p = DA.proyeccion(contrato, "GRUPO", hoy, dias=20)
    ok(len(p["dias"]) == 20, "un punto por dia del horizonte", str(len(p["dias"])))

    # LA DEUDA CON DROGUERIAS NO SE PROYECTA: ya tiene fecha y monto.
    # Proyectarla seria inventar un vencimiento que la planilla ya dice.
    dias = {x["fecha"]: x["sale"] for x in p["dias"]}
    ok(abs(dias["2026-09-10"].get("droguerias", 0) - 300.0) < 0.01,
       "la deuda cae el dia que dice la planilla, no uno estimado")
    ok(abs(dias["2026-09-12"].get("refi", 0) - 100.0) < 0.01,
       "y la refi va en su propio grupo, separada de las droguerias")

    # Patear un grupo es no sumarlo: la curva se arma sumando lo tildado.
    total = sum(sum(x["sale"].values()) for x in p["dias"])
    sin_drog = sum(v for x in p["dias"] for g, v in x["sale"].items()
                   if g != "droguerias")
    ok(abs(total - 400.0) < 0.01 and abs(sin_drog - 100.0) < 0.01,
       "y sacar un grupo de la suma es exactamente patearlo")


def test_detalle_para_desplegar():
    """CADA TOTAL TIENE QUE PODER ABRIRSE.

    Thomas: "me gustaria que haya un desplegable por cada concepto y poder
    tildar o destildar los conceptos desde ahi. Ejemplo deuda con drogueria y
    que salgan los resumenes que comprenden el timeline."

    Es como se decide de verdad: no se patea "las droguerias", se patea el
    resumen de Suizo del 10/09 y se paga el de Cofaloza. Un interruptor por
    grupo obliga a elegir todo o nada, que es justo lo que el negocio no hace.
    """
    from dashboard import datos as DA

    hoy = "2026-09-05"
    contrato = {"generado": hoy + "T00:00:00Z", "caja_hoy": 1000.0,
                "cobros_previstos": [],
                "egresos_cashflow": [
                    {"fecha": "2026-09-08", "contraparte": "Alquileres",
                     "importe": 50.0, "unidad": "MAGA"},
                    {"fecha": "2026-09-09", "contraparte": "Alquileres",
                     "importe": 30.0, "unidad": "MAGA"}],
                "deuda_droguerias": [
                    {"fecha": "2026-09-10", "contraparte": "SUIZO", "importe": 300.0},
                    {"fecha": "2026-09-17", "contraparte": "SUIZO", "importe": 200.0}]}

    p = DA.proyeccion(contrato, "GRUPO", hoy, dias=20)
    drog = [i for i in p["items"] if i["grupo"] == "droguerias"]
    ok(len(drog) == 2, "cada resumen es un item propio", str(len(drog)))
    ok(all("Resumen del" in i["concepto"] for i in drog),
       "y se llama por su fecha de resumen, que es como lo ve el proveedor")
    ok(all(not i["estimado"] for i in drog),
       "la deuda NO va marcada como estimada: tiene fecha y monto en la planilla")
    ok(len(set(i["id"] for i in p["items"])) == len(p["items"]),
       "cada item tiene un id unico, si no destildar uno destildaria otro")

    # Sacar un item de la suma es exactamente patearlo.
    total = sum(i["monto"] for i in drog)
    ok(abs(total - 500.0) < 0.01, "y los items suman el total del grupo", str(total))

    # Los gastos tambien se abren.
    g = DA.gastos_del_periodo(contrato, "MAGA", hoy, dias=20)
    alq = [x for x in g if x["nombre"] == "Alquileres"][0]
    ok(len(alq["detalle"]) == 2, "cada barra de gastos trae su detalle",
       str(alq["detalle"]))
    ok(abs(sum(d["monto"] for d in alq["detalle"]) - alq["monto"]) < 0.01,
       "y el detalle suma exactamente la barra: si no, una de las dos miente")


def test_plan_minimo():
    """QUE ES LO MINIMO QUE HAY QUE PATEAR — el salto de tablero a asesor.

    El tablero dice "el 14/09 quedas en rojo". Lo que se paga es la respuesta
    siguiente: "y que hago". Thomas: "esta solapa tiene que mostrar que puedo
    hacer para llegar bien, que obligaciones tengo que patear".
    """
    from simulador import plan as PL

    def proy(items, entra=0.0, caja=100.0, n=10):
        dias = []
        for k in range(n):
            f = (datetime.date(2026, 9, 5) + datetime.timedelta(days=k)).isoformat()
            dias.append({"fecha": f, "entra": entra, "sale": {}})
        return {"caja_inicial": caja, "dias": dias, "items": items}

    def it(fecha, grupo, monto, concepto="x"):
        return {"id": grupo + fecha + str(monto), "grupo": grupo, "fecha": fecha,
                "concepto": concepto, "monto": monto, "estimado": False}

    # Si la caja no se da vuelta, no hay nada que aconsejar.
    p = PL.armar(proy([it("2026-09-07", "droguerias", 50.0)]))
    ok(not p["hace_falta"], "sin rojo no propone nada")

    # UN PLAN DE 30 MOVIMIENTOS NO ES UN PLAN.
    # La primera version pateaba todos los chicos antes de tocar uno grande:
    # para llegar a 14 dias proponia 30 movimientos. Nadie hace eso.
    chicos = [it("2026-09-06", "socios", 5.0, "retiro %d" % k) for k in range(20)]
    grande = it("2026-09-06", "droguerias", 500.0, "Resumen del 06/09 · SUIZO")
    p = PL.armar(proy(chicos + [grande], caja=100.0))
    ok(p["alcanza"], "encuentra un plan que llega")
    ok(len(p["pasos"]) == 1, "y es de UN paso, no de veinte", str(len(p["pasos"])))

    # PERO SI ALCANZA CON LO BARATO, NO SE TOCA AL PROVEEDOR.
    # El orden es por consecuencia, no por monto: correr un retiro no rompe
    # nada, atrasar una drogueria puede costar el suministro.
    p2 = PL.armar(proy([it("2026-09-06", "socios", 500.0, "retiro"),
                        it("2026-09-06", "droguerias", 500.0, "Resumen · SUIZO")],
                       caja=100.0))
    ok(p2["pasos"][0]["grupo"] == "socios",
       "prefiere lo que no rompe nada, aunque el otro alcance igual",
       str(p2["pasos"][0]["grupo"]))

    # LO INTOCABLE NO SE PROPONE NUNCA.
    # "Un cheque no puede rebotar, no es un escenario que se permite."
    p3 = PL.armar(proy([it("2026-09-06", "mercaderia", 500.0),
                        it("2026-09-06", "sueldos", 500.0)], caja=100.0))
    ok(not any(x["grupo"] in ("mercaderia", "sueldos") for x in p3["pasos"]),
       "no propone patear cheques ni sueldos")
    ok(not p3["alcanza"] and not p3.get("corto_por_tope"),
       "y dice que asi no se arregla, en vez de proponer algo que no se puede")

    # EL DIA ROJO SE CORRE AL PATEAR, y los pagos de los dias nuevos tienen que
    # poder entrar. Con el filtro de fecha fijo se quedaba masticando el primer
    # tramo y decia "no alcanza" cuando si alcanzaba.
    p4 = PL.armar(proy([it("2026-09-06", "socios", 120.0),
                        it("2026-09-09", "socios", 300.0)], caja=100.0, n=10))
    ok(p4["alcanza"] and len(p4["pasos"]) == 2,
       "puede patear algo de un dia posterior al rojo original",
       str([(x["fecha"], x["monto"]) for x in p4["pasos"]]))

    # EL COSTO SE DICE SIEMPRE. Un plan que dice "llegas" sin decir a costa de
    # que no es un consejo.
    fichas = {"SUIZO": {"nombre": "Suizo Argentina", "tolerancia_semanas": 3}}
    p5 = PL.armar(proy([it("2026-09-06", "droguerias", 500.0,
                           "Resumen del 06/09 · SUIZO")], caja=100.0),
                  proveedores=fichas)
    c = p5["costo"][0]
    ok(c["quien"] == "Suizo Argentina" and c["tolerancia_semanas"] == 3,
       "el costo sale con el nombre y la tolerancia de la ficha", str(c))


def test_cobertura_detecta_los_bugs_reales():
    """EL CONTROL QUE HABRIA ATAJADO CASI TODOS LOS BUGS.

    Thomas, 06/09/2026: "vamos cortando con estos bugs porque estamos
    complicados, no puedo ofrecer algo lleno de bugs y si yo no me fijo no se
    que puede pasar".

    Lo importante es la segunda parte: SI EL NO LO MIRA, NADIE LO MIRA.

    Mirando los bugs juntos, casi todos fueron el mismo: plata que estaba en el
    contrato y no llego a la pantalla, o llego dos veces. Ninguno fue de
    aritmetica y ninguno rompio nada -- el tablero salio limpio, con un numero
    mal.

    Este test no prueba que el control ande cuando todo esta bien: prueba que
    SUENA cuando se rompe. Un control que nunca fallo no demuestra nada.
    """
    from auditoria import cobertura as COB
    from dashboard import datos as DA

    hoy = "2026-09-05"
    contrato = {
        "generado": hoy + "T00:00:00Z",
        "caja_hoy": 1000.0,
        "caja_por_unidad": {"SPEEDMED": 1000.0},
        "cobros_previstos": [
            {"fecha": "2026-09-10", "concepto": "FCIAS", "importe": 100.0,
             "unidad": "SPEEDMED"}],
        "cuentas_a_cobrar_droguerias": [
            {"fecha": "2026-09-12", "contraparte": "DDS", "importe": 500.0,
             "unidad": "SPEEDMED"}],
        "egresos_cashflow": [
            {"fecha": "2026-09-11", "contraparte": "Sueldos", "importe": 200.0,
             "unidad": "SPEEDMED"}],
        "deuda_droguerias": [
            {"fecha": "2026-09-13", "contraparte": "SUIZO", "importe": 300.0,
             "unidad": "SPEEDMED"}],
    }

    filas, _ = COB.revisar(contrato, dias=45)
    f = [x for x in filas if x["unidad"] == "SPEEDMED"][0]
    ok(abs(f["entra"]["dif"]) < 1 and abs(f["sale"]["dif"]) < 1,
       "con todo bien, el control no suena", str(f))
    ok(abs(f["entra"]["esperado"] - 600.0) < 1,
       "y cuenta las dos puntas del que compra Y vende")

    # EL BUG REAL: faltaba la cobranza a droguerias en la proyeccion.
    # Se simula sacandola y se verifica que el control lo cante.
    real = DA.proyeccion

    def sin_cobranza(c, u, h, dias=45, con_intercompany=False):
        p = real(c, u, h, dias, con_intercompany)
        cob = sum(abs(float(x.get("importe") or 0))
                  for x in c.get("cuentas_a_cobrar_droguerias", []))
        return dict(p, total_entra=p["total_entra"] - cob)

    DA.proyeccion = sin_cobranza
    try:
        filas2, _ = COB.revisar(contrato, dias=45)
        f2 = [x for x in filas2 if x["unidad"] == "SPEEDMED"][0]
        ok(abs(f2["entra"]["dif"]) > 1,
           "y SUENA cuando falta una punta -- el bug de Speed", str(f2["entra"]))
        ok(abs(f2["entra"]["dif"] + 500.0) < 1,
           "diciendo exactamente cuanta plata no llego a la pantalla",
           str(f2["entra"]["dif"]))
    finally:
        DA.proyeccion = real

    # EL OTRO BUG REAL: contar algo dos veces (los egresos estimados ADEMAS de
    # los cargados). Se simula duplicando y tiene que sonar igual.
    def duplicado(c, u, h, dias=45, con_intercompany=False):
        p = real(c, u, h, dias, con_intercompany)
        return dict(p, total_sale=p["total_sale"] * 2)

    DA.proyeccion = duplicado
    try:
        filas3, _ = COB.revisar(contrato, dias=45)
        f3 = [x for x in filas3 if x["unidad"] == "SPEEDMED"][0]
        ok(f3["sale"]["dif"] > 1,
           "y tambien cuando algo se cuenta dos veces -- el doble conteo",
           str(f3["sale"]))
    finally:
        DA.proyeccion = real


def test_memoria_del_tablero():
    """LO QUE DIJIMOS, CONTRA LO QUE PASO.

    Es el activo de una asesoria recurrente. La frase que la sostiene no es
    "acertamos el 83% de los movimientos": es *"el mes pasado te dije que el 14
    quedabas corto; quedaste el 16"*. Sin esto, cada visita arranca de cero y
    lo que se cobra es una foto, no una relacion.

    Se guarda la CURVA y el DIA CRITICO, no los movimientos: el tablero
    proyecta desde el cashflow y el modulo viejo guardaba desde la solapa
    MOVIMIENTOS. Mezclar los dos universos ya nos costo cuatro bugs.
    """
    from memoria import tablero as MT

    def paquete(fecha, caja, salidas):
        dias = []
        for k in range(20):
            f = (datetime.date(2026, 9, 5) + datetime.timedelta(days=k)).isoformat()
            dias.append({"fecha": f, "entra": 0.0,
                         "sale": {"droguerias": salidas.get(f, 0.0)}})
        return {"fecha": fecha, "unidades": ["MAGA"],
                "datos": {"MAGA": {
                    "proyeccion": {"caja_inicial": caja, "dias": dias,
                                   "hasta": dias[-1]["fecha"], "items": []},
                    "kpis": {"vencido": 0.0},
                    "planes": {"14": {"frase": "no hace falta patear nada",
                                      "pasos": []}}}}}

    # Lo que dijimos el 05: la caja se da vuelta el 09.
    dicho = paquete("2026-09-05", 100.0, {"2026-09-09": 150.0})
    _, snap = MT.guardar("_test", dicho, "prueba")
    ok(snap["unidades"]["MAGA"]["critico"]["fecha"] == "2026-09-09",
       "la foto guarda el dia critico que se le mostro al cliente")

    # Lo que paso: se dio vuelta el 11, dos dias despues.
    paso = paquete("2026-09-15", 100.0, {"2026-09-11": 150.0})
    c = MT.conciliar(snap, paso)
    u = c["unidades"][0]
    ok(u["critico_real"] == "2026-09-11" and u["dias_de_diferencia"] == 2,
       "y la conciliacion dice cuantos dias erramos", str(u))
    ok(u["acerto_critico"],
       "con dos dias de diferencia se considera acertado: mueve la misma decision")
    frase = MT.en_palabras(c)[0]
    ok("05/09" in frase and "09/09" in frase and "11/09" in frase,
       "la frase se puede leer en voz alta en una reunion", frase)

    # SOLO SE JUZGA LO QUE YA VENCIO.
    # Una proyeccion a 45 dias mirada a los 10 no se cumplio ni se incumplio.
    temprano = paquete("2026-09-04", 100.0, {})
    c2 = MT.conciliar(snap, temprano)
    ok(c2["unidades"][0].get("todavia_no"),
       "una proyeccion que todavia no vencio no se juzga")

    # Y NO SE COMPARA CONTRA SI MISMA: daria 0% de desvio siempre, que es peor
    # que no medir -- da una sensacion de precision que no existe.
    from dashboard import datos as DA
    m = DA._memoria_tablero("_test_sin_nada", {"fecha": "2026-09-05", "datos": {}})
    ok(not m["hay"] and "comparar" in m["por_que"],
       "sin una foto anterior, se dice que no hay con que comparar", str(m))

    import shutil, os as _os
    shutil.rmtree(_os.path.join(BASE_REPO, "clientes", "_test"), ignore_errors=True)


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
    test_monto_variable()
    test_memoria()
    test_ajustes()
    test_formato()
    test_proyeccion()
    test_horizonte()
    test_caja_completa()
    test_coherencia()
    test_completitud()
    test_posicion_por_unidad()
    test_retiro()
    test_modos_de_pago()
    test_hallazgos_del_informe()
    test_tablero()
    test_atraso_y_alias()
    test_proyeccion_por_partes()
    test_detalle_para_desplegar()
    test_plan_minimo()
    test_cobertura_detecta_los_bugs_reales()
    test_memoria_del_tablero()
    test_proveedores()
    test_rigido_y_endoso()
    test_deuda_vencida()
    test_puentes_contraste()
    test_disponibilidad()
    test_posicion_por_unidad()
    print("\n" + "=" * 62)
    if _fallos:
        print("  %d TEST(S) FALLARON: %s" % (len(_fallos), ", ".join(_fallos)))
        sys.exit(1)
    print("  TODOS LOS TESTS PASARON")
