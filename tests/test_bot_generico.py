# -*- coding: utf-8 -*-
"""
tests/test_bot_generico.py — el bot genérico, probado de punta a punta.

Corre el recorrido completo contra `scripts/banco_de_prueba/index.html`, un
home banking falso que reproduce el camino que describió Thomas:

    login -> empresas -> cuenta -> apretar en saldo -> filtro de fecha ->
    aplicar -> descargar

Por qué existe: cuando MAGA cambió las claves de todos los bancos nos quedamos
sin poder probar nada contra un banco real. Sin esto, el motor quedaría escrito
pero no verificado, y el día que haya acceso no sabríamos si lo que falla es la
ficha de selectores o el motor. Con esto, el motor ya está probado: lo único
nuevo va a ser la ficha.

Se separa de test_motor.py porque necesita Playwright y tarda unos segundos.

    python tests/test_bot_generico.py
"""

import os
import sys
import shutil
import datetime
import tempfile

BASE_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)

from bots.generico.bot import BotGenerico, cargar_ficha
from bots.generico import validar as V
from nucleo.navegador import abrir_navegador

_fallos = []


def ok(cond, nombre, detalle=""):
    if cond:
        print("  [OK]   %s" % nombre)
    else:
        print("  [FALLA] %s   %s" % (nombre, detalle))
        _fallos.append(nombre)


def url_banco_falso():
    ruta = os.path.join(BASE_REPO, "scripts", "banco_de_prueba", "index.html")
    return "file:///" + os.path.abspath(ruta).replace(os.sep, "/")


# ------------------------------------------------------- sin navegador
def test_ficha():
    print("\n== Lectura de la ficha de selectores ==")
    bot = BotGenerico("prueba")

    ok(bot._sels("login", "usuario") == ["#usuario", "[name='usuario']"],
       "lee la lista de candidatos de un paso")
    ok(bot._sels("no", "existe") == [], "un paso inexistente devuelve lista vacia")

    # Una ficha a medio llenar no puede hacerse pasar por completa: los
    # '>>> COMPLETAR' se descartan como si el paso no estuviera.
    b2 = BotGenerico("prueba", {"login": {"usuario": [">>> COMPLETAR: el campo",
                                                     "#real"]}})
    ok(b2._sels("login", "usuario") == ["#real"],
       "descarta los '>>> COMPLETAR' y deja solo los selectores de verdad",
       str(b2._sels("login", "usuario")))

    plantilla = os.path.join(BASE_REPO, "bots", "_plantilla", "selectores.json")
    ok(os.path.exists(plantilla), "existe la plantilla para bancos nuevos")


def test_validador():
    print("\n== Validador de fichas (sin tocar el banco) ==")
    r = V.revisar("prueba")
    ok(not r["faltan"], "la ficha del banco de prueba esta completa", str(r["faltan"]))
    ok(not r["avisos"], "y sin avisos", str(r["avisos"]))

    r = V.revisar("comafi")
    ok(len(r["faltan"]) > 0, "la de comafi figura como incompleta")
    ok(any("descarga.boton" == c for c, _ in r["faltan"]),
       "y dice exactamente que paso falta")

    # Incoherencia que un ojo humano pasa por alto.
    ficha = dict(cargar_ficha("prueba"))
    ficha["empresas"] = {"tiene": True}
    import bots.generico.validar as VV
    orig = VV.cargar_ficha
    VV.cargar_ficha = lambda b: ficha
    try:
        r = VV.revisar("prueba")
        ok(any("tiene = true" in a for a in r["avisos"]),
           "detecta 'tiene empresas' sin los selectores para manejarlas",
           str(r["avisos"]))
    finally:
        VV.cargar_ficha = orig


# ------------------------------------------------------- con navegador
def test_recorrido_completo():
    print("\n== Recorrido completo contra el banco de prueba ==")
    bot = BotGenerico("prueba")
    bot.url = url_banco_falso()
    destino = tempfile.mkdtemp()
    perfil = os.path.join(BASE_REPO, "salidas", "perfiles", "_test_generico")

    try:
        with abrir_navegador(perfil, destino, headless=True) as page:
            bot.hacer_login(page, "thomas", "clave-de-mentira", 30000)
            ok(bot.capturar_empresa_activa(page) == "MAGA MAS SA",
               "login y lectura de la empresa activa")

            emps = bot.descubrir_empresas(page, 30000, excluir=["FARMACIA DOMINICO SRL"])
            ok(emps == ["MAGA MAS SA", "SPEEDMED SA"],
               "descubre las empresas y respeta la lista de excluidas", str(emps))

            solo = bot.descubrir_empresas(page, 30000, excluir=[], solo=["SPEEDMED SA"])
            ok(solo == ["SPEEDMED SA"], "y el filtro 'solo'", str(solo))

            bot.cambiar_a_empresa(page, "SPEEDMED SA", 30000)
            ok(bot.capturar_empresa_activa(page) == "SPEEDMED SA", "cambia de empresa")

            bot.ir_a_cuenta(page, 30000)
            s = bot.capturar_saldos(page)
            ok(s["actual"] == 1234567.89, "lee el saldo actual como numero", str(s["actual"]))
            ok(s["disponible"] == 1200000.0, "y el disponible", str(s["disponible"]))

            aplico = bot.aplicar_filtro_fechas(
                page, datetime.date(2026, 9, 3), datetime.date(2026, 9, 15), 30000)
            ok(aplico is True, "confirma que el filtro se aplico de verdad")

            filas = page.locator("#tbodyMov tr").count()
            ok(filas == 4, "el filtro recorta los movimientos (4 de 7)", "filas=%d" % filas)

            arch = bot.descargar_csv(page, destino, "SPEEDMED SA", 30000, None)
            ok(os.path.exists(arch), "descarga el archivo")

            with open(arch, encoding="utf-8") as f:
                csv = f.read()
            ok(csv.count("\n") == 4, "el CSV trae solo el rango filtrado",
               "lineas=%d" % csv.count("\n"))
            ok("Pago sueldos" in csv and "Cheque 0001234" not in csv,
               "con los movimientos correctos adentro")

            # El nombre original del banco se conserva porque ahi viene el numero
            # de cuenta. Ya se rompio una vez: el archivo se renombraba entero.
            ok(bot.extraer_cuenta_id(arch) == "CC0123456",
               "saca el numero de cuenta del nombre original del archivo",
               str(bot.extraer_cuenta_id(arch)))
    finally:
        shutil.rmtree(destino, ignore_errors=True)
        shutil.rmtree(perfil, ignore_errors=True)


def test_errores_claros():
    print("\n== Los errores dicen que arreglar ==")
    bot = BotGenerico("prueba", {"login": {}, "empresas": {"tiene": False}})
    bot.url = url_banco_falso()
    perfil = os.path.join(BASE_REPO, "salidas", "perfiles", "_test_err")
    destino = tempfile.mkdtemp()
    try:
        with abrir_navegador(perfil, destino, headless=True) as page:
            try:
                bot.hacer_login(page, "x", "y", 30000)
                ok(False, "avisa cuando la ficha no define el campo de usuario")
            except Exception as ex:
                ok("login.usuario" in str(ex),
                   "avisa cuando la ficha no define el campo de usuario", str(ex)[:70])
    finally:
        shutil.rmtree(destino, ignore_errors=True)
        shutil.rmtree(perfil, ignore_errors=True)


if __name__ == "__main__":
    print("=" * 62)
    print("  BOT GENERICO  ·  contra el banco de prueba")
    print("=" * 62)
    test_ficha()
    test_validador()
    test_recorrido_completo()
    test_errores_claros()
    print("\n" + "=" * 62)
    if _fallos:
        print("  %d TEST(S) FALLARON: %s" % (len(_fallos), ", ".join(_fallos)))
        sys.exit(1)
    print("  TODOS LOS TESTS PASARON")
