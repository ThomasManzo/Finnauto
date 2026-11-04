"""Datos inventados, HTTP y llavero falsos: python3 tests/test_tiendanube.py."""
import contextlib
import datetime as dt
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
import urllib.parse
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ingestas import tiendanube as T, mercado_datos as CLI, meli_oauth as O, meli_ventas as M


def ejemplo(**cambios):
    return dict(dict(id=9000001, number=1001, created_at='2026-09-10T11:06:30-0300',
        updated_at='2026-09-10T11:06:30-0300', status='open', payment_status='paid',
        subtotal='25000.00', shipping_cost_customer='3000.00', total='26000.00',
        payment_details={'installments': 3}, products=[
            dict(sku='AB 100', name='Lámpara', quantity=2, price='10000.00'),
            dict(sku='AB-200', name='Pantalla', quantity=1, price='5000.00')]), **cambios)


def error(codigo, headers=None, cuerpo=None):
    return urllib.error.HTTPError('https://example.org', codigo, 'inventado', headers or {},
        io.BytesIO(json.dumps(cuerpo or {'message': 'clave-inventada codigo-inventado token-inventado'}).encode()))


class Llavero:
    def __init__(self):
        self.datos = {
            ('finauto:ejemplo:tiendanube', 'credenciales'): json.dumps(dict(usuario='12345', clave='clave-inventada')),
            ('finauto:ejemplo:tiendanube-token', 'token'): json.dumps(dict(access_token='token-inventado', store_id='67890', scope='read_orders'))}

    def get_password(self, servicio, cuenta):
        return self.datos.get((servicio, cuenta))

    def set_password(self, servicio, cuenta, dato):
        self.datos[servicio, cuenta] = dato


class Reloj(dt.datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 11, 1, 12, tzinfo=M.HORA_BA)


class TiendanubeTests(unittest.TestCase):
    def setUp(self):
        self.llavero = Llavero()
        for parche in (patch.object(T, '_llavero', return_value=self.llavero),
                       patch.object(T.credenciales, '_keyring', return_value=self.llavero),
                       patch.object(T.time, 'sleep'),
                       patch.object(T.time, 'monotonic', side_effect=range(100000)),
                       patch.object(CLI.dt, 'datetime', Reloj)):
            parche.start()
            self.addCleanup(parche.stop)
        # Ninguna prueba puede salir a internet por descuido.
        parche = patch.object(T, '_http', side_effect=AssertionError('HTTP sin respuesta falsa'))
        parche.start()
        self.addCleanup(parche.stop)

    def test_link_y_canje_p(self):
        url = urllib.parse.urlsplit(T.link_autorizacion('ejemplo'))
        self.assertEqual(url.path, '/apps/12345/authorize')
        self.assertRegex(urllib.parse.parse_qs(url.query)['state'][0], r'^tn-[a-f0-9]{8}$')
        for campo in ('user_id', 'store_id'):
            with patch.object(T, '_http', return_value=({'access_token': 'token-nuevo', campo: 67890, 'scope': 'read_orders,read_products'}, {})) as http:
                resumen = T.canjear_codigo('ejemplo', ' TN: abc123\n')
                pedido = http.call_args.args[0]
                self.assertEqual(pedido.full_url, T.TOKEN_URL)
                self.assertEqual(pedido.get_method(), 'POST')
                self.assertEqual(pedido.get_header('Content-type'), 'application/json')
                self.assertEqual(json.loads(pedido.data), dict(client_id='12345', client_secret='clave-inventada', grant_type='authorization_code', code='abc123'))
                self.assertEqual(resumen['store_id'], '67890')
                self.assertNotIn('access_token', resumen)
                guardado = json.loads(self.llavero.datos[('finauto:ejemplo:tiendanube-token', 'token')])
                self.assertEqual(set(guardado), {'access_token', 'store_id', 'scope'})
                self.assertEqual(guardado['access_token'], 'token-nuevo')

    def test_consola_sin_secretos(self):
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida), contextlib.redirect_stderr(salida), patch('sys.stdin', io.StringIO('TN: codigo-inventado\n')), patch.object(T, '_http', return_value=(dict(access_token='token-inventado', user_id=67890, scope='read_orders'), {})):
            self.assertEqual(T.main(['--cliente', 'ejemplo', 'canjear']), 0)
            self.assertEqual(T.main(['--cliente', 'ejemplo', 'estado']), 0)
            self.assertEqual(T.main(['--cliente', 'ejemplo', 'probar']), 0)
        for secreto in ('token-inventado', 'codigo-inventado', 'clave-inventada'):
            self.assertNotIn(secreto, salida.getvalue())
        self.assertIn('OK', salida.getvalue())

    def test_errores_canje_sin_cuerpo_y_sin_reintento(self):
        for codigo, tipo, esperado in [(400, 'invalid_grant', 'venció'), (400, 'invalid_client', 'inválidas'), (401, '', 'inválidas'), (500, '', 'no se pudo')]:
            salida = io.StringIO()
            with patch.object(T, '_http', side_effect=error(codigo, cuerpo=dict(error=tipo, message='clave-inventada codigo-inventado'))) as http, contextlib.redirect_stdout(salida), contextlib.redirect_stderr(salida), patch('sys.stdin', io.StringIO('codigo-inventado')):
                self.assertEqual(T.main(['--cliente', 'ejemplo', 'canjear']), 1)
            self.assertIn(esperado, salida.getvalue())
            self.assertNotIn('clave-inventada', salida.getvalue())
            self.assertNotIn('codigo-inventado', salida.getvalue())
            self.assertEqual(http.call_count, 1)
        with patch.object(self.llavero, 'set_password', side_effect=RuntimeError('token-inventado')), patch.object(T, '_http', return_value=(dict(access_token='token-inventado', store_id=67890, scope='read_orders'), {})):
            with self.assertRaisesRegex(T.ErrorTiendanube, 'no se pudo guardar'):
                T.canjear_codigo('ejemplo', 'abc123')

    def test_m_n_o_y_estados(self):
        filas, rara = T.armar_orden(ejemplo())
        self.assertFalse(rara)
        self.assertEqual([filas[0][k] for k in T.COLUMNAS], ['1001', '2026-09-10 11:06', 'pagada', 'AB 100', 'Lámpara', 2, '10000.00', '25000.00', '-2000.00', '3000.00', '26000.00', 3, '', ''])
        self.assertEqual(filas[1]['sku'], 'AB-200')
        self.assertTrue(all(filas[1][k] == '' for k in T.COLUMNAS[7:]))
        self.assertEqual(T.armar_orden(ejemplo(status='cancelled', payment_status='refunded'))[0][0]['estado_pago'], 'cancelada')
        filas, rara = T.armar_orden(ejemplo(subtotal='10000.00', shipping_cost_customer='', total='10500.00', payment_details=None))
        self.assertTrue(rara)
        self.assertEqual((filas[0]['descuento'], filas[0]['cuotas']), ('500.00', ''))
        self.assertFalse(T.armar_orden(ejemplo(subtotal='10000', shipping_cost_customer=None, total='10001'))[1])
        for original, traducido in dict(T.ESTADOS, desconocido='desconocido').items():
            self.assertEqual(T.armar_orden(ejemplo(payment_status=original))[0][0]['estado_pago'], traducido)
        self.assertEqual(T.armar_orden(ejemplo(created_at='2026-09-10T02:00:00+0000'))[0][0]['fecha'], '2026-09-09 23:00')

    def test_paginacion_headers_y_enlaces_seguros(self):
        sesion = T.Sesion('ejemplo')
        siguiente = sesion.base + '/orders?cursor=abc'
        with patch.object(T, '_http', side_effect=[([ejemplo()], {'Link': f'<{sesion.base}/orders?page=1>; rel="prev", <{siguiente}>; rel="next"', 'X-Total-Count': '2'}), ([ejemplo(id=9000002)], {})]) as http:
            self.assertEqual(len(list(T.ordenes(sesion, {}))), 2)
            self.assertEqual(http.call_args.args[0].full_url, siguiente)
            self.assertEqual(http.call_args.args[0].get_header('User-agent'), T.USER_AGENT)
            self.assertEqual(http.call_args.args[0].get_header('Authorization'), 'Bearer token-inventado')
        for url in ('https://example.org/orders', T.API + '/111/orders', 'http://api.tiendanube.com/2025-03/67890/orders'):
            with patch.object(T, '_http', return_value=([], {'Link': f'<{url}>; rel="next"'})) as http:
                with self.assertRaisesRegex(T.ErrorTiendanube, 'enlace'):
                    list(T.ordenes(sesion, {}))
                self.assertEqual(http.call_count, 1)
        with patch.object(T, '_http', return_value=([], {'Link': f'<{siguiente}>; rel="next"'})):
            with self.assertRaisesRegex(T.ErrorTiendanube, 'repitió'):
                list(T.ordenes(sesion, {}))

    def test_reintentos_429_red_5xx_401_402(self):
        for falla, demoras in [(error(429, {'X-Rate-Limit-Reset': '1500'}), [1.5]*5), (error(429), [2,4,8,16,32]), (error(503), [2,4,8,16,32]), (urllib.error.URLError('token-inventado'), [2,4,8,16,32]), (ConnectionResetError(), [2,4,8,16,32])]:
            with patch.object(T, '_http', side_effect=falla) as http, patch.object(T.time, 'sleep') as dormir:
                sesion = T.Sesion('ejemplo')
                with self.assertRaises(T.ErrorTiendanube):
                    sesion.pedir(sesion.base + '/store')
                self.assertEqual(http.call_count, 6)
                self.assertEqual([c.args[0] for c in dormir.call_args_list], demoras)
        for codigo, mensaje in [(401, 'volver a autorizar'), (402, 'pago pendiente')]:
            with patch.object(T, '_http', side_effect=error(codigo)) as http:
                sesion = T.Sesion('ejemplo')
                with self.assertRaisesRegex(T.ErrorTiendanube, mensaje):
                    sesion.pedir(sesion.base + '/store')
                self.assertEqual(http.call_count, 1)
        with patch.object(T, '_http', side_effect=[error(503), ({}, {})]):
            sesion = T.Sesion('ejemplo')
            self.assertEqual(sesion.pedir(sesion.base + '/store'), ({}, {}))

    def test_limite_dos_pedidos_por_segundo(self):
        with patch.object(T.time, 'monotonic', return_value=100), patch.object(T.time, 'sleep') as dormir, patch.object(T, '_http', return_value=({}, {})):
            sesion = T.Sesion('ejemplo')
            sesion.pedir(sesion.base + '/store')
            sesion.pedir(sesion.base + '/store')
            dormir.assert_called_once_with(.5)

    def test_cache_incremental_y_orden_historica_cambiada(self):
        with tempfile.TemporaryDirectory() as tmp:
            carpeta = Path(tmp)
            sesion = T.Sesion('ejemplo')
            with patch.object(T, '_http', return_value=([ejemplo()], {})) as http:
                filas, _ = T.bajar(sesion, carpeta, dt.date(2026,9,5), dt.date(2026,10,31))
                self.assertEqual(len(filas), 2)
                consultas = [urllib.parse.parse_qs(urllib.parse.urlsplit(c.args[0].full_url).query) for c in http.call_args_list]
                self.assertEqual([q['created_at_min'][0][:10] for q in consultas], ['2026-09-05', '2026-10-01'])
            self.assertEqual(len(list(carpeta.glob('orden-*.json'))), 1)
            consultas = []
            def responder(req):
                params = urllib.parse.parse_qs(urllib.parse.urlsplit(req.full_url).query)
                consultas.append(params)
                return ([ejemplo(status='cancelled')] if 'updated_at_min' in params else []), {}
            with patch.object(T, '_http', side_effect=responder):
                filas, _ = T.bajar(sesion, carpeta, dt.date(2026,9,1), dt.date(2027,1,10), '2027-01-09T12:00:00-03:00')
            self.assertEqual(consultas[0]['created_at_min'][0][:10], '2026-11-01')
            self.assertEqual(consultas[-1]['updated_at_min'][0], '2027-01-07T12:00:00-03:00')
            self.assertEqual(len(filas), 2)
            self.assertEqual(filas[0]['estado_pago'], 'cancelada')
            with patch.object(T, '_http', return_value=([], {})):
                self.assertEqual(T.bajar(sesion, carpeta, dt.date(2026,10,1), dt.date(2026,10,31))[0], [])

    def correr(self, tmp, solo=True, desde='2026-09-01'):
        args = ['--cliente', 'ejemplo', '--salida', tmp, '--desde', desde]
        with patch.object(O, 'BASE_REPO', Path(tmp)), contextlib.redirect_stdout(io.StringIO()):
            return CLI.main(args + (['--solo', 'tiendanube'] if solo else []))

    def test_cli_sin_aplicacion_sin_permiso_y_llavero_roto(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.llavero.datos.pop(('finauto:ejemplo:tiendanube', 'credenciales'))
            self.assertEqual(self.correr(tmp), 0)
            self.assertNotIn('tiendanube', json.loads((Path(tmp)/'control.json').read_text())['fuentes'])
            self.assertFalse((Path(tmp)/'tn_ordenes.csv').exists())
            self.llavero = Llavero()
            with patch.object(T, '_llavero', return_value=self.llavero), patch.object(T.credenciales, '_keyring', return_value=self.llavero):
                self.llavero.datos.pop(('finauto:ejemplo:tiendanube-token', 'token'))
                self.assertEqual(self.correr(tmp), 0)
                self.assertNotIn('tiendanube', json.loads((Path(tmp)/'control.json').read_text())['fuentes'])
            with patch.object(T, '_llavero', side_effect=RuntimeError('clave-inventada')):
                self.assertEqual(self.correr(tmp), 1)
                self.assertNotIn('clave-inventada', (Path(tmp)/'control.json').read_text())

    def test_cli_exito_error_y_marca_solo_despues_del_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp)
            (ruta/'control.json').write_text(json.dumps({'fuentes': {'banco': {'ok': True}}}))
            with patch.object(T, '_http', return_value=([ejemplo(subtotal='10000', total='10500', shipping_cost_customer='0')], {})):
                self.assertEqual(self.correr(tmp), 0)
            csv = (ruta/'tn_ordenes.csv').read_bytes()
            self.assertEqual(csv.decode().splitlines()[0], ','.join(T.COLUMNAS))
            resumen = json.loads((ruta/'control.json').read_text())['fuentes']['tiendanube']
            self.assertEqual(resumen, dict(ok=True, filas=2, desde='2026-09-10', hasta='2026-09-10', motivo='', raras=1))
            marca = ruta/'clientes/ejemplo/.run/tiendanube/cache/ultima.json'
            anterior = marca.read_bytes()
            for falla in (error(401), error(402), ValueError('token-inventado')):
                with patch.object(T, '_http', side_effect=falla):
                    self.assertEqual(self.correr(tmp), 1)
                self.assertEqual((ruta/'tn_ordenes.csv').read_bytes(), csv)
                self.assertEqual(marca.read_bytes(), anterior)
            with patch.object(T, '_http', return_value=([], {})), patch.object(CLI, 'escribir_csv', side_effect=OSError('ocupado')):
                self.assertEqual(self.correr(tmp), 1)
                self.assertEqual(marca.read_bytes(), anterior)
            control = json.loads((ruta/'control.json').read_text())
            self.assertTrue(control['fuentes']['banco']['ok'])

    def test_csv_anterior_si_falla_segunda_pagina_o_reemplazo(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp)
            (ruta/'tn_ordenes.csv').write_text('anterior')
            enlace = T.API + '/67890/orders?cursor=segunda'
            with patch.object(T, '_http', side_effect=[([ejemplo()], {'Link': f'<{enlace}>; rel="next"'}), error(401)]):
                self.assertEqual(self.correr(tmp), 1)
            self.assertEqual((ruta/'tn_ordenes.csv').read_text(), 'anterior')
            self.assertFalse((ruta/'clientes/ejemplo/.run/tiendanube/cache/ultima.json').exists())
            reemplazar = M.os.replace
            def reemplazo(origen, destino):
                if Path(destino).name == 'tn_ordenes.csv':
                    raise OSError('ocupado')
                return reemplazar(origen, destino)
            with patch.object(T, '_http', return_value=([ejemplo()], {})), patch.object(M.os, 'replace', side_effect=reemplazo):
                self.assertEqual(self.correr(tmp), 1)
            self.assertEqual((ruta/'tn_ordenes.csv').read_text(), 'anterior')
            self.assertFalse((ruta/'clientes/ejemplo/.run/tiendanube/cache/ultima.json').exists())
            self.assertEqual({p.name for p in ruta.iterdir()}, {'clientes', 'tn_ordenes.csv', 'control.json'})

    def test_cache_no_mezcla_tiendas_y_ordena_numeros(self):
        with tempfile.TemporaryDirectory() as tmp:
            sesion = T.Sesion('ejemplo')
            ordenes = [ejemplo(id=9000002, number='10'), ejemplo(number='9')]
            with patch.object(T, '_http', return_value=(ordenes, {})):
                filas, _ = T.bajar(sesion, Path(tmp), dt.date(2026,9,1), dt.date(2026,9,30))
            self.assertEqual([f['numero_orden'] for f in filas], ['9', '9', '10', '10'])
            sesion.permiso['store_id'] = '11111'
            with patch.object(T, '_http', return_value=([], {})):
                self.assertEqual(T.bajar(sesion, Path(tmp), dt.date(2026,9,1), dt.date(2026,9,30)), ([], 0))

    def test_corrida_completa_y_ampliar_periodo(self):
        llamadas = []
        def bajar(nombre, resultado):
            def ejecutar(*args):
                llamadas.append(nombre)
                return resultado
            return ejecutar
        with tempfile.TemporaryDirectory() as tmp, patch.object(M, 'bajar', side_effect=bajar('ml', ([],0))), patch.object(CLI.mp, 'bajar', side_effect=bajar('mp', ([],''))), patch.object(CLI.ads, 'bajar', side_effect=bajar('ads', [])), patch.object(T, 'bajar', side_effect=bajar('tn', ([],0))) as tn:
            self.assertEqual(self.correr(tmp, solo=False), 0)
            self.assertEqual(llamadas, ['ml','mp','ads','tn'])
            self.assertIsNone(tn.call_args.args[-1])
            self.assertEqual(self.correr(tmp), 0)
            self.assertIsNotNone(tn.call_args.args[-1])
            self.assertEqual(self.correr(tmp, desde='2026-08-01'), 0)
            self.assertIsNone(tn.call_args.args[-1])
            control = json.loads((Path(tmp)/'control.json').read_text())['fuentes']
            self.assertEqual(len(control), 4)
            self.assertTrue(all(f['ok'] for f in control.values()))





class LecturaTests(unittest.TestCase):
    def test_periodo_sin_ordenes_no_es_error(self):
        import urllib.error
        permiso = dict(access_token='inventado', store_id='123', scope='read_orders')
        def error_404(cuerpo):
            return urllib.error.HTTPError('https://ejemplo', 404, 'Not Found', {}, io.BytesIO(cuerpo))
        with patch.object(T, '_leer', return_value=permiso), patch.object(T.time, 'sleep'):
            sesion = T.Sesion('ejemplo')
            with patch.object(T, '_http', side_effect=error_404(b'{"description": "Last page is 0"}')):
                self.assertEqual(sesion.pedir(sesion.base + '/orders'), ([], {}))
            # Otro 404 (por ejemplo, una tienda que no existe) sigue siendo un error.
            with patch.object(T, '_http', side_effect=error_404(b'{"description": "Store not found"}')):
                with self.assertRaisesRegex(T.ErrorTiendanube, 'HTTP 404'):
                    sesion.pedir(sesion.base + '/orders')

    def test_reintentos_lectura(self):
        from http.client import IncompleteRead
        permiso = dict(access_token='inventado', store_id='123', scope='read_orders')
        for error in (ValueError(), IncompleteRead(b''), ConnectionResetError()):
            for agotar in (False, True):
                with self.subTest(error=error, agotar=agotar), patch.object(T, '_leer', return_value=permiso), patch.object(T.time, 'sleep') as dormir, patch.object(T.time, 'monotonic', side_effect=range(100)), patch.object(T, '_http', side_effect=error if agotar else [error, ([], {})]) as http:
                    sesion = T.Sesion('ejemplo')
                    if agotar:
                        with self.assertRaisesRegex(T.ErrorTiendanube, 'no se pudo leer la respuesta de Tiendanube; revisar la conexión y volver a intentar'):
                            sesion.pedir(sesion.base + '/orders')
                    else:
                        self.assertEqual(sesion.pedir(sesion.base + '/orders'), ([], {}))
                    self.assertEqual(http.call_count, 6 if agotar else 2)
                    self.assertEqual([c.args[0] for c in dormir.call_args_list], [2, 4, 8, 16, 32] if agotar else [2])


if __name__ == '__main__':
    unittest.main()
