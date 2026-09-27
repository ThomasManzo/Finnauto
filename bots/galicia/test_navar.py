"""Controles de Galicia NAVAR sin entrar al banco ni tocar el llavero."""
import datetime as dt
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpyxl import Workbook

from bots.galicia.bot import BotGalicia
from bots.galicia.navar import BotGaliciaNavar


BASE = Path(__file__).resolve().parents[2]


def _configuracion():
    perfil = json.loads((BASE / "clientes/navar/perfil.json").read_text(encoding="utf-8"))
    return perfil["bancos"]["galicia"]


def _escribir_excel(ruta, fecha, encabezado_creditos="Créditos"):
    """Imita los encabezados reales: Galicia no incluye la cuenta en el export."""
    libro = Workbook()
    hoja = libro.active
    hoja.append([
        "Fecha", "Descripción", "Origen", "Débitos", encabezado_creditos,
        "Grupo de Conceptos", "Concepto", "Número de Terminal", "Saldo",
    ])
    hoja.append([fecha, "Movimiento inventado", "", 0, 100, "", "", "", 100])
    libro.save(ruta)


class ElementoFalso:
    def __init__(self, texto="", visible=True):
        self.texto = texto
        self.visible = visible
        self.clics = 0

    def is_visible(self):
        return self.visible

    def click(self, timeout=None):
        self.clics += 1


class ListaFalsa:
    def __init__(self, elementos):
        self.elementos = elementos

    def count(self):
        return len(self.elementos)

    def nth(self, indice):
        return self.elementos[indice]


class PaginaConTextos:
    def __init__(self, textos):
        self.elementos = [ElementoFalso(texto, visible) for texto, visible in textos]

    def get_by_text(self, patron):
        return ListaFalsa([e for e in self.elementos if patron.search(e.texto)])


class PaginaOfficeBanking:
    def __init__(self):
        self.oculto = ElementoFalso("Office Banking", visible=False)
        self.visible = ElementoFalso("Office Banking", visible=True)

    def get_by_role(self, rol, name=None):
        if rol == "link":
            return ListaFalsa([self.oculto, self.visible])
        if rol == "button":
            return ListaFalsa([])
        raise AssertionError("Rol inesperado: %s" % rol)


class PaginaQueNoSePuedeTocar:
    def __getattr__(self, nombre):
        raise AssertionError("Intentó usar la página: %s" % nombre)


class PruebaNavar(unittest.TestCase):
    def setUp(self):
        self.cfg = _configuracion()
        self.bot = BotGaliciaNavar(self.cfg)
        self.bot.rango = (dt.date(2026, 9, 22), dt.date(2026, 9, 23))

    def test_excel_realista_sin_cuenta_pasa(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "inventado.xlsx"
            _escribir_excel(ruta, dt.datetime(2026, 9, 23))
            datos = self.bot.validar_excel(ruta)

        self.assertEqual(len(datos["movimientos"]), 1)
        self.assertEqual(datos["movimientos"][0]["importe"], 100)

    def test_excel_fuera_de_rango_frena(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "inventado.xlsx"
            _escribir_excel(ruta, dt.datetime(2026, 9, 24))
            with self.assertRaisesRegex(RuntimeError, "fuera del rango"):
                self.bot.validar_excel(ruta)

    def test_excel_con_encabezado_incompatible_frena(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "inventado.xlsx"
            _escribir_excel(ruta, dt.datetime(2026, 9, 23), "No es crédito")
            with self.assertRaises(ValueError):
                self.bot.validar_excel(ruta)

    def test_filtro_no_confirmado_frena(self):
        with patch.object(BotGalicia, "aplicar_filtro_fechas", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "No pude confirmar las fechas"):
                self.bot.aplicar_filtro_fechas(None, dt.date.today(), dt.date.today(), 10)
        self.assertIsNone(self.bot.rango)

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

    def test_nombres_de_empresa(self):
        self.assertTrue(self.cfg["solo_empresa_activa"])
        self.assertEqual(self.cfg["backfill_dias_primera_vez"], 7)
        for nombre in ("NAVAR SA", "NAVAR SOCIEDAD ANÓNIMA"):
            pagina = PaginaConTextos([(nombre, True)])
            self.assertEqual(self.bot.capturar_empresa_activa(pagina), "NAVAR SA")
        otra = PaginaConTextos([("OTRA EMPRESA SOCIEDAD ANONIMA", True)])
        self.assertIsNone(self.bot.capturar_empresa_activa(otra))

    def test_empresa_repetida_visible_se_reconoce(self):
        pagina = PaginaConTextos([
            ("NAVAR SOCIEDAD ANONIMA", True),
            ("NAVAR SOCIEDAD ANONIMA - CONSUMO MASIVO", True),
        ])
        self.bot._esperar_empresa_visible(pagina, 10)
        self.assertEqual(self.bot.capturar_empresa_activa(pagina), "NAVAR SA")

    def test_office_banking_elige_el_unico_visible(self):
        pagina = PaginaOfficeBanking()
        self.bot._abrir_office_banking(pagina, 10)
        self.assertEqual(pagina.oculto.clics, 0)
        self.assertEqual(pagina.visible.clics, 1)

    def test_empresa_unica_no_hace_clics(self):
        pagina = PaginaQueNoSePuedeTocar()
        self.assertEqual(self.bot.descubrir_empresas(pagina, 10, []), [])
        with self.assertRaisesRegex(RuntimeError, "una sola empresa activa"):
            self.bot.cambiar_a_empresa(pagina, "NAVAR SA", 10)


if __name__ == "__main__":
    unittest.main()
