"""Controles de BBVA NAVAR sin entrar al banco ni tocar el llavero. Datos inventados."""
import datetime as dt
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from openpyxl import Workbook

from bots.bbva import navar
from bots.bbva.navar import BotBbvaNavar, nombre_publicado, patron_cuenta
from nucleo import credenciales


BASE = Path(__file__).resolve().parents[2]
HOY = dt.date(2026, 10, 3)


def _configuracion():
    perfil = json.loads((BASE / "clientes/navar/perfil.json").read_text(encoding="utf-8"))
    return perfil["bancos"]["bbva"]


def _escribir_excel(ruta, cuenta="489-000765/9", cuit="30558525025", fechas=(HOY,)):
    """Imita el export de BBVA: encabezado con empresa y cuenta, después la tabla."""
    libro = Workbook()
    hoja = libro.active
    hoja.append(["Empresa: ", "EMPRESA INVENTADA(%s)" % cuit])
    hoja.append(["Cuenta: ", "%s(CC $)" % cuenta])
    hoja.append(["Saldo: ", "-1.000,00"])
    hoja.append(["Movimientos de: ", "Ultimos 60 Días."])
    hoja.append([])
    hoja.append(["Fecha", "Fecha Valor", "Concepto", "Codigo", "Número Documento", "Oficina",
                 "Crédito", "Débito", "Detalle", "x"])
    for i, fecha in enumerate(fechas):
        texto = fecha.strftime("%d-%m-%Y")
        hoja.append([texto, texto, "MOVIMIENTO INVENTADO", "100", "", "OFICINA", "", -10.0 - i, "",
                     "Saldo Disponible: -1.0%02d,00" % i])
    libro.save(ruta)


class Pantalla(unittest.TestCase):
    def test_la_cuenta_se_reconoce_en_el_inicio_y_en_movimientos(self):
        self.assertTrue(patron_cuenta("489-000765/9", inicio=True).search("#0489-000765/9"))
        self.assertTrue(patron_cuenta("489-000765/9").search("489-000765/9 (CC $)"))
        self.assertTrue(patron_cuenta("489-000765/9").search("489-000765/9  (CC $)"))

    def test_no_se_confunde_con_la_otra_cuenta(self):
        self.assertFalse(patron_cuenta("489-000765/9", inicio=True).search("#0489-000806/5"))
        self.assertFalse(patron_cuenta("489-000806/5").search("489-000765/9 (CC $)"))
        # Un texto más largo que contenga la cuenta no es el selector.
        self.assertFalse(patron_cuenta("489-000765/9").search("TRANSFERENCIA CCP489 000765 9"))

    def test_nombre_del_archivo_publicado(self):
        self.assertEqual(nombre_publicado("Movimientos BBVA", "489-000806/5", HOY),
                         "Movimientos BBVA 489-000806-5 2026-10-03.xls")

    def test_el_perfil_trae_las_dos_cuentas_y_su_carpeta(self):
        cfg = _configuracion()
        self.assertEqual(cfg["cuentas"], ["489-000765/9", "489-000806/5"])
        self.assertEqual(cfg["carpeta_drive_relativa"], "Bancos/bbva")
        self.assertEqual(BotBbvaNavar(cfg).prefijo, "Movimientos BBVA")


class Validacion(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.ruta = os.path.join(self.dir.name, "bajado.xlsx")
        self.bot = BotBbvaNavar(_configuracion())

    def tearDown(self):
        self.dir.cleanup()

    def test_excel_correcto(self):
        _escribir_excel(self.ruta, fechas=(HOY - dt.timedelta(days=59), HOY))
        datos = self.bot.validar_excel(self.ruta, "489-000765/9", hoy=HOY)
        self.assertEqual(len(datos["movimientos"]), 2)

    def test_cuenta_distinta_de_la_pedida(self):
        _escribir_excel(self.ruta, cuenta="489-000765/9")
        with self.assertRaisesRegex(RuntimeError, "se pidió 489-000806/5"):
            self.bot.validar_excel(self.ruta, "489-000806/5", hoy=HOY)

    def test_otra_empresa(self):
        _escribir_excel(self.ruta, cuit="20111111112")
        with self.assertRaisesRegex(RuntimeError, "no es de NAVAR"):
            self.bot.validar_excel(self.ruta, "489-000765/9", hoy=HOY)

    def test_fecha_del_dia_habil_siguiente_se_acepta_pero_no_mas(self):
        _escribir_excel(self.ruta, fechas=(HOY + dt.timedelta(days=3),))
        self.bot.validar_excel(self.ruta, "489-000765/9", hoy=HOY)
        _escribir_excel(self.ruta, fechas=(HOY + dt.timedelta(days=10),))
        with self.assertRaisesRegex(RuntimeError, "fecha futura"):
            self.bot.validar_excel(self.ruta, "489-000765/9", hoy=HOY)

    def test_movimiento_demasiado_viejo(self):
        _escribir_excel(self.ruta, fechas=(HOY - dt.timedelta(days=90),))
        with self.assertRaisesRegex(RuntimeError, "más de 65 días"):
            self.bot.validar_excel(self.ruta, "489-000765/9", hoy=HOY)

    def test_cuenta_sin_movimientos_no_es_error(self):
        _escribir_excel(self.ruta, fechas=())
        with patch.object(navar, "log"):
            datos = self.bot.validar_excel(self.ruta, "489-000765/9", hoy=HOY)
        self.assertEqual(datos["movimientos"], [])

    def test_publicar_reemplaza_el_del_mismo_dia(self):
        destino = os.path.join(self.dir.name, "Movimientos BBVA 489-000765-9 2026-10-03.xls")
        Path(destino).write_text("viejo")
        Path(self.ruta).write_text("nuevo")
        BotBbvaNavar.publicar(self.ruta, self.dir.name, os.path.basename(destino))
        self.assertEqual(Path(destino).read_text(), "nuevo")
        self.assertEqual(sorted(p.name for p in Path(self.dir.name).iterdir()),
                         ["Movimientos BBVA 489-000765-9 2026-10-03.xls", "bajado.xlsx"])


class DosCuentas(unittest.TestCase):
    def setUp(self):
        self.bot = BotBbvaNavar(_configuracion())
        self.dir = tempfile.TemporaryDirectory()
        self.ctx = SimpleNamespace(descargas_dir=self.dir.name)
        for nombre in ("log", "captura"):
            p = patch.object(navar, nombre)
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        self.dir.cleanup()

    def test_baja_las_dos_y_cambia_de_cuenta_una_vez(self):
        cambios, bajadas = [], []
        with patch.object(self.bot, "_cambiar_cuenta", side_effect=lambda p, c, t: cambios.append(c)), \
                patch.object(self.bot, "capturar_saldos", return_value={"actual": 0.0, "actual_texto": "$ 0,00"}), \
                patch.object(self.bot, "_descargar_una",
                             side_effect=lambda p, c, d, t, x: bajadas.append(c) or "/x/%s" % c):
            primero = self.bot.descargar_csv(None, "/drive", "NAVAR SA", 1000, self.ctx)
        self.assertEqual(cambios, ["489-000806/5"])
        self.assertEqual(bajadas, ["489-000765/9", "489-000806/5"])
        self.assertEqual(primero, "/x/489-000765/9")

    def test_si_falla_una_la_otra_igual_se_publica_y_se_avisa(self):
        def bajar(p, cuenta, d, t, x):
            if cuenta == "489-000765/9":
                raise RuntimeError("no apareció el botón")
            return "/x/Movimientos BBVA 489-000806-5 2026-10-03.xls"
        with patch.object(self.bot, "_cambiar_cuenta"), \
                patch.object(self.bot, "capturar_saldos", return_value={}), \
                patch.object(self.bot, "_descargar_una", side_effect=bajar):
            with self.assertRaisesRegex(RuntimeError, r"1 de 2 cuentas fallaron.*489-000806-5"):
                self.bot.descargar_csv(None, "/drive", "NAVAR SA", 1000, self.ctx)

    def test_no_descarga_sin_empresa_confirmada(self):
        with self.assertRaisesRegex(RuntimeError, "confirmar la empresa"):
            self.bot.descargar_csv(None, "/drive", "EMPRESA_ACTIVA", 1000, self.ctx)

    def test_no_intenta_entrar_sin_codigo_de_empresa(self):
        class PaginaQueNoSeDebeUsar:
            def goto(self, *a, **k):
                raise AssertionError("no debía abrir el banco")
        with self.assertRaisesRegex(RuntimeError, "código de empresa"):
            self.bot.hacer_login(PaginaQueNoSeDebeUsar(), "u", "c", 1000)


class LlaveroFalso:
    def __init__(self):
        self.guardado = {}

    def set_password(self, servicio, cuenta, datos):
        self.guardado[(servicio, cuenta)] = datos

    def get_password(self, servicio, cuenta):
        return self.guardado.get((servicio, cuenta))


class Credenciales(unittest.TestCase):
    def test_el_codigo_de_empresa_viaja_con_usuario_y_clave(self):
        llavero = LlaveroFalso()
        with patch.object(credenciales, "_keyring", return_value=llavero):
            credenciales.guardar(None, "navar", "bbva", "usuario", "clave", {"codigo_empresa": "123"})
            self.assertEqual(credenciales.cargar(None, "navar", "bbva"), ("usuario", "clave"))
            self.assertEqual(credenciales.dato_extra("navar", "bbva", "codigo_empresa"), "123")

    def test_sin_codigo_de_empresa_corta_con_mensaje(self):
        llavero = LlaveroFalso()
        with patch.object(credenciales, "_keyring", return_value=llavero), \
                patch.object(credenciales, "log"):
            credenciales.guardar(None, "navar", "bbva", "usuario", "clave")
            with self.assertRaises(SystemExit):
                credenciales.dato_extra("navar", "bbva", "codigo_empresa")


if __name__ == "__main__":
    unittest.main()
