# -*- coding: utf-8 -*-
"""Pruebas sin red ni llavero real: python tests/test_meli_oauth.py."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import urllib.error
import urllib.parse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ingestas import meli_oauth as M


class Llavero:
    def __init__(self):
        self.datos = {}

    def get_password(self, servicio, cuenta):
        return self.datos.get((servicio, cuenta))

    def set_password(self, servicio, cuenta, valor):
        self.datos[servicio, cuenta] = valor


class OAuthTests(unittest.TestCase):
    def setUp(self):
        self.pila = contextlib.ExitStack()
        self.addCleanup(self.pila.close)
        self.carpeta = self.pila.enter_context(tempfile.TemporaryDirectory())
        self.pila.enter_context(patch.object(M, 'BASE_REPO', Path(self.carpeta)))
        self.kr = Llavero()
        self.pila.enter_context(patch.object(M, '_llavero', return_value=self.kr))
        self.pila.enter_context(patch.object(M.credenciales, '_keyring', return_value=self.kr))
        for fuente in M.FUENTES:
            self.kr.set_password('finauto:ejemplo:' + fuente, 'credenciales',
                                 json.dumps(dict(usuario='123456', clave='secreto-inventado')))
        self.pedidos = []
        self.http = self.pila.enter_context(patch.object(M, '_http', side_effect=self.responder))

    def responder(self, pedido):
        self.pedidos.append(pedido)
        if pedido.get_method() == 'GET':
            return dict(id=789, nickname='ejemplo', access_token='no-mostrar')
        return dict(access_token='acceso-inventado', refresh_token='refresh-nuevo',
                    expires_in=21600, user_id=789, scope='read offline_access')

    def guardar(self, segundos=10000, fuente='mercadolibre'):
        dato = dict(access_token='acceso-anterior', refresh_token='refresh-anterior',
                    vence=time.time() + segundos, obtenido=time.time(), user_id=789, scope='read')
        self.kr.set_password('finauto:ejemplo:' + fuente + '-token', 'token', json.dumps(dato))

    def test_links(self):
        for fuente, config in M.FUENTES.items():
            redirect = 'https://example.org/vuelta/?a=uno dos&b=2'
            link = M.link_autorizacion('ejemplo', fuente, redirect)
            self.assertTrue(link.startswith(config['autorizacion']))
            self.assertIn('redirect_uri=' + urllib.parse.quote(redirect, safe=''), link)
            params = urllib.parse.parse_qs(urllib.parse.urlsplit(link).query)
            self.assertEqual(params['client_id'], ['123456'])
            self.assertEqual(params['response_type'], ['code'])
            self.assertRegex(params['state'][0], '^' + config['prefijo'] + '-[a-f0-9]{8}$')
            self.assertEqual(params.get('platform_id'), ['mp'] if fuente == 'mercadopago' else None)

    def test_codigos(self):
        for texto in ('ML: TG-abc', 'ml:TG-abc', '  TG-abc \n', ' ML : TG-\nabc '):
            self.assertEqual(M.limpiar_codigo(texto), 'TG-abc')
            self.assertEqual(M.limpiar_codigo(texto, 'mercadolibre'), 'TG-abc')
        with self.assertRaisesRegex(M.ErrorAutorizacion, 'prefijo'):
            M.canjear_codigo('ejemplo', 'mercadolibre', 'MP: TG-abc')
        self.http.assert_not_called()

    def test_canje_y_formatos(self):
        for fuente, config in M.FUENTES.items():
            antes = time.time()
            resumen = M.canjear_codigo('ejemplo', fuente, config['prefijo'] + ': TG-abc')
            pedido = self.pedidos[-1]
            self.assertEqual(pedido.full_url, config['token'])
            self.assertEqual(pedido.get_method(), 'POST')
            if config['formato'] == 'json':
                cuerpo = json.loads(pedido.data)
                self.assertEqual(pedido.get_header('Content-type'), 'application/json')
            else:
                cuerpo = dict(urllib.parse.parse_qsl(pedido.data.decode()))
                self.assertEqual(pedido.get_header('Content-type'), 'application/x-www-form-urlencoded')
            self.assertEqual(cuerpo, dict(client_id='123456', client_secret='secreto-inventado',
                                         grant_type='authorization_code', code='TG-abc',
                                         redirect_uri=M.REDIRECT_POR_DEFECTO))
            dato = M._leer('ejemplo', fuente)
            self.assertGreaterEqual(dato['vence'], antes + 21600 - 60)
            self.assertEqual(dato['refresh_token'], 'refresh-nuevo')
            self.assertTrue(resumen['offline_access'])
            self.assertTrue(resumen['vence'].endswith('-03:00'))
            self.assertNotIn('access_token', resumen)

    def test_renovacion(self):
        for fuente in M.FUENTES:
            self.guardar(fuente=fuente)
            self.assertEqual(M.access_token('ejemplo', fuente), 'acceso-anterior')
            self.guardar(599, fuente)
            self.assertEqual(M.access_token('ejemplo', fuente), 'acceso-inventado')
            self.assertEqual(M._leer('ejemplo', fuente)['refresh_token'], 'refresh-nuevo')
            pedido = self.pedidos[-1]
            cuerpo = (json.loads(pedido.data) if fuente == 'mercadopago'
                      else dict(urllib.parse.parse_qsl(pedido.data.decode())))
            self.assertEqual(cuerpo['grant_type'], 'refresh_token')
            self.assertEqual(cuerpo['refresh_token'], 'refresh-anterior')
        self.assertEqual(len(self.pedidos), 2)
        self.guardar(-1)
        M.access_token('ejemplo', 'mercadolibre')
        self.assertEqual(len(self.pedidos), 3)

    def test_errores_y_secretos(self):
        for error, motivo in M.MOTIVOS.items():
            self.http.side_effect = urllib.error.HTTPError('https://example.org', 400, '', {},
                io.BytesIO(json.dumps(dict(error=error)).encode()))
            with self.assertRaises(M.ErrorAutorizacion) as capturado:
                M.canjear_codigo('ejemplo', 'mercadolibre', 'TG-abc')
            self.assertEqual(capturado.exception.motivo, motivo)
        self.http.side_effect = urllib.error.HTTPError('https://example.org', 403, '', {},
            io.BytesIO(json.dumps(dict(error='denegado', message='secreto-inventado TG-abc')).encode()))
        salida = io.StringIO()
        with contextlib.redirect_stderr(salida), contextlib.redirect_stdout(salida), patch('builtins.input', return_value='TG-abc'):
            self.assertEqual(M.main(['--cliente', 'ejemplo', '--fuente', 'mercadolibre', 'canjear']), 1)
        self.assertIn('HTTP 403: denegado', salida.getvalue())
        self.assertNotIn('secreto-inventado', salida.getvalue())
        self.assertNotIn('TG-abc', salida.getvalue())

    def test_cli_sin_secretos(self):
        for fuente in M.FUENTES:
            salida = io.StringIO()
            with contextlib.redirect_stdout(salida), contextlib.redirect_stderr(salida), patch('builtins.input', return_value='TG-abc'):
                for comando in ('link', 'canjear', 'estado', 'probar'):
                    self.assertEqual(M.main(['--cliente', 'ejemplo', '--fuente', fuente, comando]), 0)
            for secreto in ('TG-abc', 'secreto-inventado', 'acceso-inventado', 'refresh-nuevo', 'no-mostrar'):
                self.assertNotIn(secreto, salida.getvalue())
            self.assertIn('Listo: autorizado el usuario 789', salida.getvalue())
            self.assertIn('"nickname": "ejemplo"', salida.getvalue())
            self.assertEqual(self.pedidos[-1].get_header('Authorization'), 'Bearer acceso-inventado')

    def test_faltantes_y_fallo_guardado(self):
        self.assertFalse(M.estado('ejemplo', 'mercadolibre')['hay_token'])
        with self.assertRaisesRegex(M.ErrorAutorizacion, M.SIN_TOKEN):
            M.access_token('ejemplo', 'mercadolibre')
        with patch.object(self.kr, 'set_password', side_effect=RuntimeError('secreto-inventado')):
            with self.assertRaisesRegex(M.ErrorAutorizacion, 'no se pudo guardar'):
                M.canjear_codigo('ejemplo', 'mercadolibre', 'TG-abc')
        self.kr.datos.clear()
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida), contextlib.redirect_stderr(salida):
            with self.assertRaisesRegex(M.ErrorAutorizacion, M.FALTAN_CREDENCIALES):
                M.link_autorizacion('ejemplo', 'mercadolibre')
        self.assertEqual(salida.getvalue(), '')

    def test_candado_viejo_y_espera(self):
        self.guardar(10)
        ruta = Path(self.carpeta) / 'clientes/ejemplo/.run/mercadolibre/token.lock'
        ruta.parent.mkdir(parents=True)
        ruta.touch()
        os.utime(ruta, (time.time() - 121, time.time() - 121))
        M.access_token('ejemplo', 'mercadolibre')
        self.assertFalse(ruta.exists())
        self.guardar(10)
        ruta.touch()
        # Simulamos que el dueño del candado termina la renovación mientras esperamos.
        def termina(_):
            self.guardar(10000)
            ruta.unlink()
        with patch.object(M.time, 'sleep', side_effect=termina):
            self.assertEqual(M.access_token('ejemplo', 'mercadolibre'), 'acceso-anterior')
        self.assertEqual(len(self.pedidos), 1)
        ruta.touch()
        with patch.object(M.time, 'monotonic', side_effect=[0, 31]):
            with self.assertRaisesRegex(M.ErrorAutorizacion, 'otro programa'):
                with M._candado('ejemplo', 'mercadolibre'):
                    self.fail('no debía tomar el candado')
        self.assertTrue(ruta.exists())

    def test_dos_bajadas_renuevan_una_vez(self):
        self.guardar(10)
        entro = threading.Event()
        seguir = threading.Event()
        resultados = []
        errores = []
        def responder(pedido):
            entro.set()
            if not seguir.wait(3):
                raise AssertionError('no se liberó el HTTP falso')
            return self.responder(pedido)
        self.http.side_effect = responder
        def bajar():
            try:
                resultados.append(M.access_token('ejemplo', 'mercadolibre'))
            except Exception as exc:
                errores.append(exc)
        uno = threading.Thread(target=bajar)
        dos = threading.Thread(target=bajar)
        uno.start()
        try:
            self.assertTrue(entro.wait(3))
            dos.start()
        finally:
            seguir.set()
            uno.join(3)
            if dos.ident:
                dos.join(3)
        self.assertFalse(errores)
        self.assertEqual(resultados, ['acceso-inventado'] * 2)
        self.assertEqual(len(self.pedidos), 1)


if __name__ == '__main__':
    unittest.main()
