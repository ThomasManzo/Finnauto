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
    var = []
    for mes, dia in (("2026-06", 5), ("2026-07", 19), ("2026-08", 11)):
        var.append({"fecha": "%s-%02d" % (mes, dia), "tipo": "DROGUERIA",
                    "concepto": "d", "importe": 300.0})
    perf2, _ = PR.perfilar(var, datetime.date(2026, 9, 1))
    proy2 = PR.proyectar_horizonte(perf2, datetime.date(2026, 9, 1), 31)
    total = sum(p["importe"] for p in proy2)
    ok(abs(total - 300.0) < 1.0,
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
    print("\n" + "=" * 62)
    if _fallos:
        print("  %d TEST(S) FALLARON: %s" % (len(_fallos), ", ".join(_fallos)))
        sys.exit(1)
    print("  TODOS LOS TESTS PASARON")
