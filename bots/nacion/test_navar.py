"""Controles de Nación NAVAR sin entrar al banco ni tocar el llavero. Datos inventados."""
import datetime as dt
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from openpyxl import Workbook

from bots.nacion.navar import (BotNacionNavar, elegir_notificacion, hora_de_notificacion,
                               nombre_publicado)


BASE = Path(__file__).resolve().parents[2]
CUENTA = "12345678901234"


def _bot(**cambios):
    cfg = dict(json.loads((BASE / "clientes/navar/perfil.json").read_text(encoding="utf-8"))["bancos"]["nacion"])
    cfg["cuenta"] = CUENTA
    cfg.update(cambios)
    return BotNacionNavar(cfg)


def _excel(ruta, renglones):
    libro = Workbook()
    hoja = libro.active
    hoja.append(["Banco Nación", "[BNA + Empresas]"])
    hoja.append(["Fecha", "Comprobante", "Concepto", "Monto", "Saldo"])
    for r in renglones:
        hoja.append(list(r))
    libro.save(ruta)


class Notificaciones(unittest.TestCase):
    PEDIDO = dt.datetime(2026, 10, 7, 21, 14, 40)

    def test_lee_fecha_y_hora(self):
        self.assertEqual(hora_de_notificacion("Atención al cliente Descarga de listado 07/10/2026 21:15"),
                         dt.datetime(2026, 10, 7, 21, 15))
        self.assertIsNone(hora_de_notificacion("Descarga de listado"))

    def test_elige_la_mas_nueva_de_este_pedido(self):
        textos = ["Descarga de listado 06/10/2026 09:00",     # de ayer: no
                  "Descarga de listado 07/10/2026 21:15",
                  "Descarga de listado 07/10/2026 21:16"]
        self.assertEqual(elegir_notificacion(textos, self.PEDIDO), 2)

    def test_una_vieja_no_sirve(self):
        self.assertIsNone(elegir_notificacion(["Descarga de listado 07/10/2026 20:00"], self.PEDIDO))

    def test_margen_por_reloj_corrido(self):
        # El reloj del banco va un minuto atrás: igual es de este pedido.
        self.assertEqual(elegir_notificacion(["Descarga de listado 07/10/2026 21:13"], self.PEDIDO), 0)


class Datos(unittest.TestCase):
    def test_ventana_de_dias(self):
        self.assertEqual(_bot().ventana(dt.date(2026, 10, 7)), (dt.date(2026, 10, 3), dt.date(2026, 10, 7)))
        self.assertEqual(_bot(dias_a_bajar=1).ventana(dt.date(2026, 10, 7)),
                         (dt.date(2026, 10, 7), dt.date(2026, 10, 7)))

    def test_la_cuenta_recortada_del_inicio(self):
        bot = _bot()
        self.assertTrue(bot._es_la_cuenta("N° 5678901234"))
        self.assertFalse(bot._es_la_cuenta("N° 5678901299"))
        self.assertFalse(bot._es_la_cuenta("N°"))

    def test_nombre_publicado_lleva_la_cuenta(self):
        self.assertEqual(nombre_publicado("Movimientos Nacion", CUENTA, dt.date(2026, 10, 7)),
                         "Movimientos Nacion 12345678901234 2026-10-07.xls")

    def test_perfil(self):
        bot = BotNacionNavar(json.loads((BASE / "clientes/navar/perfil.json").read_text(encoding="utf-8"))
                             ["bancos"]["nacion"])
        self.assertEqual(len(bot.cuenta), 14)
        self.assertEqual(bot.dias, 5)


class Validacion(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.ruta = os.path.join(self.dir.name, "nacion_por_validar_%s_x.xlsx" % CUENTA)
        self.bot = _bot()

    def tearDown(self):
        self.dir.cleanup()

    def test_dentro_del_filtro(self):
        _excel(self.ruta, [("07/10/2026", "1", "DEBITO", "$ -10,00", "$ 100,00"),
                           ("06/10/2026", "2", "CREDITO", "$ 50,00", "$ 50,00")])
        datos = self.bot.validar_excel(self.ruta, dt.date(2026, 10, 3), dt.date(2026, 10, 7))
        self.assertEqual(datos["movimientos"][0]["saldo"], 90.0)

    def test_fuera_del_filtro_es_un_listado_viejo(self):
        _excel(self.ruta, [("01/09/2026", "1", "DEBITO", "$ -10,00", "$ 100,00")])
        with self.assertRaisesRegex(RuntimeError, "fuera del filtro"):
            self.bot.validar_excel(self.ruta, dt.date(2026, 10, 3), dt.date(2026, 10, 7))

    def test_cadena_rota_no_se_publica(self):
        _excel(self.ruta, [("07/10/2026", "1", "DEBITO", "$ -10,00", "$ 999,00"),
                           ("06/10/2026", "2", "CREDITO", "$ 50,00", "$ 50,00")])
        with self.assertRaisesRegex(ValueError, "no cierra"):
            self.bot.validar_excel(self.ruta, dt.date(2026, 10, 3), dt.date(2026, 10, 7))


class Frenos(unittest.TestCase):
    def test_sin_dni_no_abre_el_banco(self):
        class NoUsar:
            def goto(self, *a, **k):
                raise AssertionError("no debía abrir el banco")
        with self.assertRaisesRegex(RuntimeError, "Falta el DNI"):
            _bot().hacer_login(NoUsar(), "u", "c", 1000)

    def test_no_descarga_sin_filtro(self):
        with self.assertRaisesRegex(RuntimeError, "filtro"):
            _bot().descargar_csv(None, "/drive", "NAVAR SA", 1000, SimpleNamespace(descargas_dir="/tmp"))

    def test_captcha_visible_frena_y_el_invisible_no(self):
        class Marco:
            def __init__(self, src, alto):
                self.src, self.alto = src, alto
            def get_attribute(self, _):
                return self.src
            def is_visible(self):
                return True
            def bounding_box(self):
                return {"height": self.alto}

        class Pagina:
            def __init__(self, marcos):
                self.marcos = marcos
            def locator(self, _):
                return SimpleNamespace(all=lambda: self.marcos)

        visible = Pagina([Marco("https://www.google.com/recaptcha/api2/anchor?k=x&size=normal", 78)])
        invisible = Pagina([Marco("https://www.google.com/recaptcha/api2/anchor?k=x&size=invisible", 60)])
        self.assertTrue(BotNacionNavar.hay_captcha(visible))
        self.assertFalse(BotNacionNavar.hay_captcha(invisible))


if __name__ == "__main__":
    unittest.main()
