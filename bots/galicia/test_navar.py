"""Controles de Galicia NAVAR sin entrar al banco ni tocar el llavero."""
import datetime as dt
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpyxl import Workbook

from bots.galicia.navar import BotGaliciaNavar, URL_LOGIN


BASE = Path(__file__).resolve().parents[2]


def _configuracion():
    perfil = json.loads((BASE / "clientes/navar/perfil.json").read_text(encoding="utf-8"))
    return perfil["bancos"]["galicia"]


def _escribir_excel(ruta, fechas, encabezado_creditos="Créditos"):
    """Imita el export real de Galicia, que no incluye ni cuenta ni columna Saldo."""
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Movimientos"
    hoja.append([
        "Fecha", "Descripción", "Origen", "Débitos", encabezado_creditos,
        "Grupo de Conceptos", "Concepto", "Número de Terminal",
        "Observaciones Cliente", "Número de Comprobante",
        "Leyendas Adicionales 1", "Leyendas Adicionales 2",
        "Leyendas Adicionales 3", "Leyendas Adicionales 4",
    ])
    for fecha in fechas:
        hoja.append([
            dt.datetime.combine(fecha, dt.time()), "Movimiento inventado", "", 0, 100,
            "", "", "", "", "123", "", "", "", "",
        ])
    libro.save(ruta)


class ElementoFalso:
    def __init__(self, texto="", visible=True, al_click=None):
        self.texto = texto
        self.visible = visible
        self.al_click = al_click
        self.clics = 0
        self.valor = None

    def is_visible(self):
        return self.visible

    def click(self, timeout=None):
        self.clics += 1
        if self.al_click:
            self.al_click()

    def fill(self, valor, timeout=None):
        self.valor = valor

    def wait_for(self, state=None, timeout=None):
        if state == "hidden" and not self.visible:
            return
        if state == "visible" and self.visible:
            return
        raise RuntimeError("estado no alcanzado: %s" % state)

    def inner_text(self, timeout=None):
        return self.texto


class ListaFalsa:
    def __init__(self, elementos=None):
        self.elementos = list(elementos or [])

    def count(self):
        return len(self.elementos)

    def nth(self, indice):
        return self.elementos[indice]


class PaginaEsperaFalsa:
    def wait_for_timeout(self, milisegundos):
        pass


class PaginaConTextos(PaginaEsperaFalsa):
    def __init__(self, textos, url=""):
        self.elementos = [ElementoFalso(texto, visible) for texto, visible in textos]
        self.url = url

    def get_by_text(self, patron, exact=None):
        if isinstance(patron, str):
            elegidos = [e for e in self.elementos
                        if (e.texto == patron if exact else patron in e.texto)]
        else:
            elegidos = [e for e in self.elementos if patron.search(e.texto)]
        return ListaFalsa(elegidos)


class PaginaLoginFalsa(PaginaEsperaFalsa):
    def __init__(self):
        self.url = ""
        self.usuario = ElementoFalso("Usuario")
        self.clave = ElementoFalso("Clave")
        self.empresa = ElementoFalso("NAVAR SOCIEDAD ANONIMA", visible=False)
        self.ingresar = ElementoFalso("Ingresar", al_click=self._entrar)

    def _entrar(self):
        self.usuario.visible = False
        self.empresa.visible = True

    def goto(self, url, timeout=None):
        self.url = url

    def get_by_label(self, nombre, exact=None):
        return ListaFalsa([self.usuario if nombre == "Usuario" else self.clave])

    def get_by_role(self, rol, name=None, exact=None):
        if rol == "textbox":
            return ListaFalsa([self.usuario])
        if rol == "button" and name == "Ingresar":
            return ListaFalsa([self.ingresar])
        return ListaFalsa()

    def locator(self, selector):
        if selector == "input[type='password']":
            return ListaFalsa([self.clave])
        return ListaFalsa()

    def get_by_text(self, patron, exact=None):
        return ListaFalsa([self.empresa] if patron.search(self.empresa.texto) else [])


class PaginaSaldosFalsa(PaginaEsperaFalsa):
    def locator(self, selector):
        if "//*[normalize-space(.)='Actual']/following-sibling" in selector:
            return ListaFalsa([ElementoFalso("- $1.234,50")])
        if "//*[normalize-space(.)='Disponible']/following-sibling" in selector:
            return ListaFalsa([ElementoFalso("$765,50")])
        return ListaFalsa()


class PaginaQueNoSePuedeTocar:
    def __getattr__(self, nombre):
        raise AssertionError("Intentó usar la página: %s" % nombre)


class PruebaNavar(unittest.TestCase):
    def setUp(self):
        self.cfg = _configuracion()
        self.bot = BotGaliciaNavar(self.cfg)

    def test_unico_visible_ignora_oculto(self):
        oculto = ElementoFalso(visible=False)
        visible = ElementoFalso(visible=True)
        elegido = self.bot._esperar_unico_visible(
            PaginaEsperaFalsa(), [ListaFalsa([oculto, visible])], "ejemplo", 10)
        self.assertIs(elegido, visible)

    def test_unico_visible_frena_con_dos(self):
        with self.assertRaisesRegex(RuntimeError, "2 veces visible"):
            self.bot._esperar_unico_visible(
                PaginaEsperaFalsa(),
                [ListaFalsa([ElementoFalso(), ElementoFalso()])], "ejemplo", 10)

    def test_unico_visible_frena_al_vencer(self):
        with self.assertRaisesRegex(RuntimeError, "no apareció visible"):
            self.bot._esperar_unico_visible(
                PaginaEsperaFalsa(), [ListaFalsa([ElementoFalso(visible=False)])],
                "ejemplo", 0)

    def test_login_directo(self):
        pagina = PaginaLoginFalsa()
        self.bot.hacer_login(pagina, "usuario inventado", "clave inventada", 10)
        self.assertEqual(pagina.url, URL_LOGIN)
        self.assertEqual(pagina.usuario.valor, "usuario inventado")
        self.assertEqual(pagina.clave.valor, "clave inventada")
        self.assertEqual(pagina.ingresar.clics, 1)

    def test_cuenta_abierta_con_titulo_completo(self):
        pagina = PaginaConTextos(
            [
                ("Cuenta Corriente $ N° 0005459-5 070-1", True),
                ("N° 0005459-5 070-1", True),
            ],
            url="https://empresas.bancogalicia.com.ar/cuentas/movimientos")
        self.bot._esperar_cuenta_abierta(pagina, 10)

    def test_saldos_con_formato_argentino(self):
        saldos = self.bot.capturar_saldos(PaginaSaldosFalsa())
        self.assertEqual(saldos["actual"], -1234.50)
        self.assertEqual(saldos["disponible"], 765.50)
        self.assertEqual(saldos["actual_texto"], "- $1.234,50")

    def test_nombres_de_descarga(self):
        self.assertEqual(
            self.bot._validar_nombre_descarga("Extracto_CC545950701.xlsx"),
            "Extracto_CC545950701.xlsx")
        with self.assertRaisesRegex(RuntimeError, "cuenta pedida"):
            self.bot._validar_nombre_descarga("Extracto_CC999999999.xlsx")
        with self.assertRaisesRegex(RuntimeError, "XLSX"):
            self.bot._validar_nombre_descarga("Extracto_CC545950701.csv")

    def test_excel_realista_dentro_de_30_dias_pasa(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "inventado.xlsx"
            _escribir_excel(ruta, [dt.date.today() - dt.timedelta(days=30)])
            datos = self.bot.validar_excel(ruta)
        self.assertEqual(len(datos["movimientos"]), 1)

    def test_excel_con_fecha_futura_frena(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "inventado.xlsx"
            _escribir_excel(ruta, [dt.date.today() + dt.timedelta(days=1)])
            with self.assertRaisesRegex(RuntimeError, "fecha futura"):
                self.bot.validar_excel(ruta)

    def test_excel_con_fecha_de_hace_40_dias_frena(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "inventado.xlsx"
            _escribir_excel(ruta, [dt.date.today() - dt.timedelta(days=40)])
            with self.assertRaisesRegex(RuntimeError, "anterior a 35 días"):
                self.bot.validar_excel(ruta)

    def test_excel_sin_movimientos_frena(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "inventado.xlsx"
            _escribir_excel(ruta, [])
            with self.assertRaisesRegex(RuntimeError, "sin movimientos"):
                self.bot.validar_excel(ruta)

    def test_excel_con_encabezado_incompatible_frena(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "inventado.xlsx"
            _escribir_excel(ruta, [dt.date.today()], "No es crédito")
            with self.assertRaises(ValueError):
                self.bot.validar_excel(ruta)

    def test_filtro_no_toca_la_pagina(self):
        pagina = PaginaQueNoSePuedeTocar()
        self.assertTrue(self.bot.aplicar_filtro_fechas(
            pagina, dt.date.today(), dt.date.today(), 10))

    def test_carpeta_drive_se_resuelve_desde_variable(self):
        from orquestador.correr import correr_banco

        with tempfile.TemporaryDirectory() as carpeta:
            destino = Path(carpeta) / "Bancos" / "galicia"
            destino.mkdir(parents=True)
            recibida = {}

            def corrida_falsa(bot, ctx, usuario, clave):
                recibida["carpeta"] = ctx.carpeta_drive
                return {"fallaron": [], "ok": ["NAVAR SA"], "sin_novedades": []}

            with patch.dict(os.environ, {"FINAUTO_DRIVE": carpeta}), \
                    patch("orquestador.correr._cred.cargar", return_value=("usuario", "clave")), \
                    patch("orquestador.correr._loop.correr", side_effect=corrida_falsa):
                correr_banco("navar", "galicia")

        self.assertEqual(Path(recibida["carpeta"]), destino)

    def test_carpeta_inexistente_frena_antes_del_llavero(self):
        from orquestador.correr import correr_banco

        with tempfile.TemporaryDirectory() as carpeta:
            with patch.dict(os.environ, {"FINAUTO_DRIVE": carpeta}), \
                    patch("orquestador.correr._cred.cargar",
                          side_effect=AssertionError("Tocó el llavero")):
                with self.assertRaisesRegex(SystemExit, r"Bancos/galicia"):
                    correr_banco("navar", "galicia")

    def test_empresa_y_perfil(self):
        self.assertTrue(self.cfg["solo_empresa_activa"])
        self.assertNotIn("backfill_dias_primera_vez", self.cfg)
        pagina = PaginaConTextos([
            ("NAVAR SOCIEDAD ANONIMA", True),
            ("NAVAR SOCIEDAD ANÓNIMA - CONSUMO MASIVO", True),
        ])
        self.assertEqual(self.bot.capturar_empresa_activa(pagina), "NAVAR SA")

    def test_empresa_unica_no_hace_clics(self):
        pagina = PaginaQueNoSePuedeTocar()
        self.assertEqual(self.bot.descubrir_empresas(pagina, 10, []), [])
        with self.assertRaisesRegex(RuntimeError, "una sola empresa activa"):
            self.bot.cambiar_a_empresa(pagina, "NAVAR SA", 10)


if __name__ == "__main__":
    unittest.main()
