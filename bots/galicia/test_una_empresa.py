"""Pruebas con página falsa y archivos inventados; nunca se abre el banco."""
import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from bots.galicia.una_empresa import BotGaliciaUnaEmpresa, patron_nombre
from bots.galicia.navar import BotGaliciaNavar, PATRON_EMPRESA
from bots.galicia.test_navar import PaginaConTextos, PaginaLoginFalsa, _escribir_excel
from nucleo.config import cargar_perfil
from orquestador import correr


def configuracion(carpeta=''):
    return dict(cuenta='0001234-5 999-1', solo_estas_empresas=['EJEMPLO SA'],
                prefijo_archivo='Movimientos Galicia', variante='una_empresa',
                carpeta_drive_destino=carpeta, activo=True)


class Pruebas(unittest.TestCase):
    def test_login_usa_nombre_del_perfil_una_sola_vez(self):
        bot = BotGaliciaUnaEmpresa(configuracion())
        pagina = PaginaLoginFalsa()
        pagina.empresa.texto = "EJEMPLO SOCIEDAD ANONIMA"
        with patch("bots.galicia.navar.captura"):
            bot.hacer_login(pagina, "usuario inventado", "clave inventada", 0)
        self.assertEqual(pagina.ingresar.clics, 1)
        self.assertEqual(bot.capturar_empresa_activa(pagina), "EJEMPLO SA")
        self.assertIsNone(patron_nombre("CASA").search("CA"))
        self.assertIsNotNone(patron_nombre("CASA").search("CASA"))

    def test_nombres_y_cuenta(self):
        for nombre in ('EJEMPLO SA', 'EJEMPLO S.A.', 'EJEMPLO SOCIEDAD ANÓNIMA', 'EJEMPLO'):
            bot = BotGaliciaUnaEmpresa(dict(configuracion(), solo_estas_empresas=[nombre]))
            for texto in ('EJEMPLO SA', 'EJEMPLO S. A.', 'EJEMPLO SOCIEDAD ANONIMA', 'EJEMPLO'):
                self.assertEqual(bot.capturar_empresa_activa(PaginaConTextos([(texto, True)])), nombre)
            self.assertIsNone(bot.capturar_empresa_activa(PaginaConTextos([('OTRA SA', True)])))
        self.assertIsNone(patron_nombre('EJEMPLO SA').search('EJEMPLOSALES'))
        bot = BotGaliciaUnaEmpresa(configuracion())
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / 'mov.xlsx'
            _escribir_excel(ruta, [dt.date.today()])
            datos = bot.validar_excel(ruta)
            self.assertEqual(datos['cuenta'], bot.cuenta)
            self.assertEqual(datos['movimientos'][0]['cuenta'], bot.cuenta)
            navar = BotGaliciaNavar(configuracion())
            self.assertIs(navar.patron_empresa, PATRON_EMPRESA)
            self.assertEqual(navar.capturar_empresa_activa(PaginaConTextos([('NAVAR SA', True)])), 'NAVAR SA')
            from inspect import signature
            from lector.extractos import leer_planilla_galicia
            self.assertEqual(navar.validar_excel(ruta)['cuenta'], signature(leer_planilla_galicia).parameters['cuenta'].default)

    def test_perfil_privado_y_prioridad(self):
        with tempfile.TemporaryDirectory() as carpeta:
            raiz = Path(carpeta) / 'clientes/ejemplo'
            (raiz / 'privado').mkdir(parents=True)
            with self.assertRaises(FileNotFoundError) as error:
                cargar_perfil(carpeta, 'ejemplo')
            self.assertIn(str(raiz / 'perfil.json'), str(error.exception))
            self.assertIn(str(raiz / 'privado/perfil.json'), str(error.exception))
            (raiz / 'privado/perfil.json').write_text('{"cliente": "privado"}')
            self.assertEqual(cargar_perfil(carpeta, 'ejemplo')['cliente'], 'privado')
            (raiz / 'perfil.json').write_text('{"cliente": "raiz"}')
            self.assertEqual(cargar_perfil(carpeta, 'ejemplo')['cliente'], 'raiz')

    def test_orquestador_y_resultado_estricto(self):
        with tempfile.TemporaryDirectory() as carpeta:
            raiz = Path(carpeta) / 'clientes/ejemplo/privado'
            raiz.mkdir(parents=True)
            perfil = raiz / 'perfil.json'
            perfil.write_text(json.dumps({'bancos': {'galicia': configuracion(carpeta)}}))
            with patch.object(correr, 'BASE_REPO', carpeta), patch.object(correr._cred, 'cargar', return_value=('u', 'c')), patch.object(correr._loop, 'correr', return_value={'ok': ['EJEMPLO SA'], 'fallaron': [], 'sin_novedades': []}) as loop:
                correr.correr_banco('ejemplo', 'galicia')
                bot, ctx, _, _ = loop.call_args.args
                self.assertIsInstance(bot, BotGaliciaUnaEmpresa)
                self.assertTrue(ctx.solo_activa)
                self.assertEqual(ctx.carpeta_drive, carpeta)
                loop.return_value = {'ok': [], 'fallaron': [], 'sin_novedades': []}
                with self.assertRaisesRegex(RuntimeError, 'no terminó bien') as error:
                    correr.correr_banco('ejemplo', 'galicia')
                self.assertNotIn('NAVAR', str(error.exception))
                loop.side_effect = SystemExit('login fallido')
                with patch.object(correr, '_estado_hoy', return_value=correr.MARCA_CLAVE):
                    with self.assertRaises(SystemExit):
                        correr.correr_banco('ejemplo', 'galicia')
                contador = correr._ruta_contador(carpeta, 'ejemplo', 'galicia', dt.date.today())
                self.assertEqual(correr._leer_contador(contador), 1)

    def test_carpeta_faltante_no_toca_llavero_ni_loop(self):
        for destino in ('', 'relativa', '/carpeta-inventada-no-existe'):
            with patch.object(correr._config, 'cargar_perfil', return_value={'bancos': {'galicia': configuracion(destino)}}), patch.object(correr._cred, 'cargar') as cred, patch.object(correr._loop, 'correr') as loop:
                with self.assertRaisesRegex(SystemExit, 'antes de abrir el banco'):
                    correr.correr_banco('ejemplo', 'galicia')
                cred.assert_not_called()
                loop.assert_not_called()


if __name__ == '__main__':
    unittest.main()
