"""Ejemplos inventados: no se abre el banco ni se usa el llavero real."""
import datetime as dt
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from openpyxl import Workbook
from bots.macro.navar import validar_excel, elegir_fila, ajustar_saldo, monto, BotMacroNavar, PATRON_DESAFIO
from lector.extractos import leer_planilla_macro
from nucleo.salidas import escribir_estado_drive
import setup_credenciales

HOY = dt.date(2026, 11, 6)
PEDIDO = dt.datetime(2026, 11, 6, 8, 50)
CUENTA = '123456789012345'


class PruebasMacro(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ruta = Path(self.tmp.name) / 'inventado.xlsx'
        self.patron = patch('bots.macro.navar.PATRON_CUIT', re.compile('30111111118'))
        self.patron.start()
        self.addCleanup(self.patron.stop)

    def archivo(self, movimientos=None, cuenta=CUENTA, cuit='30111111118', descarga='06/11/2026 08:50:00'):
        if movimientos is None:
            movimientos = [(HOY, -100, 900), (HOY - dt.timedelta(days=1), -50, 1000)]
        wb = Workbook()
        for fila in [('Últimos Movimientos',), ('CUENTA CORRIENTE BANCARIA',), ('Número', None, cuenta),
                     ('Moneda', None, 'PESOS'), ('Fecha', None, None, 'Nro. de Referencia', 'Causal', 'Concepto', 'Importe', None, None, None, 'Saldo')]:
            wb.active.append(fila)
        for fecha, importe, saldo in movimientos:
            wb.active.append([fecha, None, None, '1000001', '123', 'PRUEBA INVENTADA', importe, None, None, None, saldo])
        wb.active.append(['Fecha de descarga: ' + descarga])
        wb.active.append(['Empresa: ' + cuit + ' - EMPRESA DE PRUEBA SA'])
        wb.active.append(['Operador: Persona Inventada'])
        wb.save(self.ruta)
        wb.close()
        return self.ruta

    def validar(self, **kw):
        return validar_excel(self.archivo(**kw), CUENTA, PEDIDO, HOY)

    def test_bueno(self):
        self.assertEqual(len(self.validar()['movimientos']), 2)

    def test_rechazos(self):
        for kw in [dict(cuenta='999999999999999'), dict(cuit='30222222226'),
                   dict(movimientos=[(HOY, -100, 800), (HOY, -10, 1000)]),
                   dict(movimientos=[(HOY-dt.timedelta(days=46), -100, 900)]),
                   dict(descarga='05/11/2026 08:50:00')]:
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                self.validar(**kw)

    def test_futuros_y_lector(self):
        datos = self.validar(movimientos=[(HOY+dt.timedelta(days=2), -100, 700),
            (HOY+dt.timedelta(days=1), -100, 800), (HOY, -100, 900), (HOY-dt.timedelta(days=1), -50, 1000)])
        self.assertEqual(datos['futuros'], 2)
        self.assertIn('-200.00', datos['avisos'][0])
        limpia = Path(self.tmp.name)/'limpia.xlsx'
        wb = Workbook()
        for fila in datos['filas']:
            wb.active.append(fila)
        wb.save(limpia)
        wb.close()
        self.assertEqual(len(leer_planilla_macro(limpia)['movimientos']), 2)
        self.assertEqual(validar_excel(limpia, CUENTA, PEDIDO, HOY)['futuros'], 0)

    def test_vacios(self):
        self.assertEqual(self.validar(movimientos=[])['movimientos'], [])
        datos = self.validar(movimientos=[(HOY+dt.timedelta(days=1), 10, 100)])
        self.assertEqual(datos['movimientos'], [])
        self.assertEqual(datos['futuros'], 1)

    def test_saldos(self):
        datos = self.validar()
        for saldo, esperado in [(900, 900), (700, None), (None, None)]:
            saldos = dict(actual=saldo, actual_texto='texto de pantalla')
            avisos = []
            ajustar_saldo(saldos, datos, avisos)
            self.assertEqual(saldos['actual'], esperado)
            self.assertEqual(bool(avisos), esperado is None)
            self.assertEqual(saldos['actual_texto'], 'texto de pantalla')
        self.assertEqual(monto('$ -1.234.567,89'), -1234567.89)

    def test_bandeja(self):
        def fila(fecha, estado='Finalizado'):
            return ['Últimos Movimientos', 'Ultimos_Movimientos', 'xls', fecha, fecha, estado]
        vieja = fila('05/11/2026 08:50')
        nueva = fila('06/11/2026 08:50')
        margen = fila('06/11/2026 08:48')
        self.assertIsNone(elegir_fila([vieja], PEDIDO))
        self.assertEqual(elegir_fila([vieja, nueva], PEDIDO), 1)
        self.assertEqual(elegir_fila([margen], PEDIDO), 0)
        self.assertEqual(elegir_fila([margen, nueva], PEDIDO), 1)
        self.assertIsNone(elegir_fila([fila('06/11/2026 08:50', 'En proceso')], PEDIDO))
        self.assertIsNone(elegir_fila([], PEDIDO))
        with self.assertRaises(ValueError):
            elegir_fila([nueva, nueva], PEDIDO)

    def test_estado(self):
        resultado = dict(ok=[], fallaron=[], sin_novedades=[])
        escribir_estado_drive(self.tmp.name, 'Macro', HOY, resultado)
        ruta = Path(self.tmp.name)/'_ESTADO_Macro_06-11.txt'
        antes = ruta.read_text()
        self.assertIn('OK: no fallo ninguna empresa.', antes)
        resultado['avisos'] = ['Prueba inventada', 'Otra aclaración']
        escribir_estado_drive(self.tmp.name, 'Macro', HOY, resultado)
        self.assertEqual(ruta.read_text(), antes + '\nAVISO: Prueba inventada\nAVISO: Otra aclaración')

    def test_claves_ocultas(self):
        with patch('sys.argv', ['setup', '--cliente', 'navar', '--banco', 'macro']), patch('builtins.input', return_value='usuario inventado') as entrada, patch('getpass.getpass', side_effect=['clave inventada', 'empresa inventada']) as oculto, patch.object(setup_credenciales._cred, 'guardar', return_value='llavero simulado') as guardar:
            setup_credenciales.main()
        self.assertEqual(entrada.call_count, 1)
        self.assertEqual(oculto.call_count, 2)
        self.assertEqual(guardar.call_args.args[-1], {'clave_empresa': 'empresa inventada'})

    def test_publicacion_y_vacios(self):
        # La descarga es simulada; controlamos qué llega a Drive y qué saldo queda.
        for tipo in ('original', 'futuros', 'todos futuros', 'vacío'):
            with self.subTest(tipo=tipo), tempfile.TemporaryDirectory() as destino:
                bot = BotMacroNavar({})
                bot.cuenta = CUENTA
                bot.saldos = dict(actual=900, actual_texto='pantalla inventada')
                movs = [] if tipo == 'vacío' else [(HOY, -100, 900)]
                if tipo in ('futuros', 'todos futuros'):
                    movs = [(HOY+dt.timedelta(days=1), -100, 800)] + (movs if tipo == 'futuros' else [])
                datos = self.validar(movimientos=movs)
                page = MagicMock()
                descarga = page.expect_download.return_value.__enter__.return_value.value
                descarga.suggested_filename = 'Ultimos_Movimientos.xls'
                descarga.save_as.side_effect = lambda ruta: Path(ruta).write_bytes(b'archivo inventado')
                ctx = MagicMock(descargas_dir=self.tmp.name)
                with patch.object(bot, 'confirmar_cuenta'), patch.object(bot, 'unico'), patch.object(bot, '_bandeja'), patch('bots.macro.navar.validar_excel', return_value=datos):
                    publicado = bot.descargar_csv(page, destino, 'NAVAR SA', 10, ctx)
                if tipo in ('vacío', 'todos futuros'):
                    self.assertIsNone(publicado)
                    self.assertEqual(list(Path(destino).iterdir()), [])
                    self.assertIsNone(bot.saldos['actual'])
                elif tipo == 'futuros':
                    self.assertTrue(publicado.endswith('.xlsx'))
                    self.assertEqual(len(leer_planilla_macro(publicado)['movimientos']), 1)
                else:
                    self.assertTrue(publicado.endswith('.xls'))
                    self.assertEqual(Path(publicado).read_bytes(), b'archivo inventado')

    def test_falla_despues_de_contrasena(self):
        from bots.galicia.navar import CLAVE_ENVIADA_SIN_CONFIRMAR
        bot = BotMacroNavar({})
        bot.clave_empresa = 'empresa inventada'
        page = MagicMock()
        with patch.object(bot, 'frenar_desafio'), patch('bots.macro.navar._esperar_unico', return_value=MagicMock()), patch.object(bot, 'unico', side_effect=[MagicMock(), MagicMock(), RuntimeError('secreto inventado')]):
            with self.assertRaises(RuntimeError) as error:
                bot.hacer_login(page, 'usuario inventado', 'clave inventada', 10)
        self.assertIn(CLAVE_ENVIADA_SIN_CONFIRMAR, str(error.exception))
        self.assertNotIn('secreto inventado', str(error.exception))
        page.close.assert_called_once()

    def test_login_sin_filtrar_secretos(self):
        bot = BotMacroNavar({})
        bot.clave_empresa = 'inventada'
        page = MagicMock()
        page.goto.side_effect = RuntimeError('secreto inventado')
        with self.assertRaises(RuntimeError) as error:
            bot.hacer_login(page, 'usuario inventado', 'clave inventada', 10)
        self.assertNotIn('secreto inventado', str(error.exception))
        page.close.assert_called_once()


class CartelAntiestafas(unittest.TestCase):
    """El login de Macro muestra SIEMPRE "NO INGRESES TOKEN": no es un pedido de código (09/11/2026)."""

    def test_el_cartel_no_frena(self):
        cartel = ('ALERTA VIRUS/ESTAFAS: Si ves un mensaje de actualización de datos, tu computadora '
                  'está infectada, NO INGRESES TOKEN y comunicate urgente con nosotros.')
        self.assertIsNone(PATRON_DESAFIO.search(cartel))
        self.assertIsNone(PATRON_DESAFIO.search('Ingresá la contraseña que generaste en la Nueva App Macro'))

    def test_un_pedido_de_codigo_si_frena(self):
        for texto in ('Ingresá el código que te enviamos por SMS', 'Ingresá tu token',
                      'Te enviamos un código al celular', 'No soy un robot'):
            self.assertIsNotNone(PATRON_DESAFIO.search(texto), texto)


if __name__ == '__main__':
    unittest.main()
