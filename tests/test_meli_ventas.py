"""Datos inventados, sin red ni llavero: python3 tests/test_meli_ventas.py."""
import contextlib
import copy
import datetime as dt
import io
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import urllib.error
import urllib.parse
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ingestas import meli_ventas as M, meli_oauth as O, mercado_datos as CLI


def cargo(tipo, nombre, valor, de='collector'):
    return dict(type=tipo, name=nombre, accounts={'from': de}, amounts={'original': valor})


def ejemplo(flex=False):
    orden = dict(id=2000000000000001, pack_id=None if flex else 2000000000000101, status='paid',
        date_closed='2026-09-10T11:06:30.000-04:00', date_last_updated='2026-09-10T15:00:00Z',
        order_items=[dict(item=dict(id='MLA1000000001', title='Lámpara de escritorio', seller_sku='AB 100', variation_attributes=[dict(name='Color', value_name='Negro')]), quantity=1 if flex else 2, unit_price=30000 if flex else 10000)],
        payments=[{'id': 90000000001}], shipping={'id': 70001})
    cargos = [cargo('fee', 'meli_percentage_fee', 4000), cargo('tax', 'debitos_creditos', 180)] if flex else [cargo('fee', 'meli_percentage_fee', 2600), cargo('fee', 'flat_fee', 400), cargo('tax', 'debitos_creditos', 120), cargo('tax', 'sirtac', 100), cargo('shipping', 'shp_cross_docking', 5000), cargo('coupon', 'coupon_fee', 300), cargo('coupon', 'coupon_rebate', 300, 'ml')]
    pago = dict(id=90000000001, status='approved', installments=1, transaction_amount=30000 if flex else 20000,
        transaction_amount_refunded=0, transaction_details={'net_received_amount': 25820 if flex else 11480}, charges_details=cargos)
    envio = dict(logistic_type='self_service' if flex else 'xd_drop_off', status='delivered', receiver_address={'state': {'name': 'Córdoba'}}, status_history={'date_delivered': '2026-09-12T15:20:00.000-04:00'})
    costos = dict(receiver={'cost': 0}, senders=[dict(cost=0 if flex else 5000, save=0)], gross_amount=5000)
    return orden, pago, envio, costos


class VentasTests(unittest.TestCase):
    def fila(self, datos):
        o, p, e, c = datos
        filas, descuadre = M.armar_venta([o], [p], e, c)
        self.assertFalse(descuadre)
        return filas[0]

    def test_a(self):
        f = self.fila(ejemplo())
        self.assertEqual([f[c] for c in M.IMPORTES], ['20000.00', '-3220.00', '0.00', '-5000.00', '0.00', '0.00', '-300.00', '11480.00'])
        self.assertEqual([f[c] for c in ('id_venta', 'id_pack', 'fecha_venta', 'estado', 'tiene_cuotas', 'forma_entrega', 'provincia_comprador', 'fecha_entregado', 'id_pago_mp', 'variante', 'sku')], ['2000000000000101', '', '2026-09-10 12:06', 'Entregada', 'no', 'correo', 'Córdoba', '2026-09-12 16:20', '90000000001', 'Color : Negro', 'AB 100'])

    def test_b_c_d_e_f(self):
        datos = ejemplo(True)
        f = self.fila(datos)
        self.assertEqual((f['cargo_venta_impuestos'], f['costos_envio'], f['descuentos_bonificaciones'], f['total'], f['forma_entrega']), ('-4210.00', '0.00', '5000.00', '30790.00', 'flex'))
        datos[3]['senders'] = [dict(cost=4500, save=500)]
        datos[3]['gross_amount'] = 10000
        f = self.fila(datos)
        self.assertEqual((f['descuentos_bonificaciones'], f['cargo_venta_impuestos'], f['total']), ('500.00', '-4183.00', '26317.00'))
        datos = ejemplo(True)
        datos[2]['logistic_type'] = 'drop_off'
        datos[3]['receiver']['cost'] = 3000
        f = self.fila(datos)
        self.assertEqual((f['ingresos_envio'], f['costos_envio']), ('3000.00', '-3000.00'))
        for estado, total, anulacion, etiqueta in [('cancelled', '0.00', '-30790.00', 'Cancelada'), ('delivered', '4970.00', '-25820.00', 'Devuelta')]:
            o, p, e, c = ejemplo(True)
            o['status'], p['status'], p['transaction_amount_refunded'], e['status'] = 'cancelled', 'refunded', 30000, estado
            f = self.fila((o, p, e, c))
            self.assertEqual((f['total'], f['anulaciones_reembolsos'], f['estado']), (total, anulacion, etiqueta))

    def test_g_h_multiitem_y_descuadre(self):
        o, p, e, c = ejemplo(True)
        o['pack_id'] = 2000000000000101
        otra, otro = copy.deepcopy(o), copy.deepcopy(p)
        otra['id'], otro['id'] = 2000000000000002, 90000000002
        filas, des = M.armar_venta([o, otra], [p, otro], e, c)
        self.assertFalse(des)
        self.assertEqual(len(filas), 3)
        self.assertEqual(filas[0]['estado'], 'Paquete de 2 productos')
        self.assertEqual(filas[0]['total'], '56610.00')
        for fila in filas[1:]:
            self.assertTrue(all(fila[k] == '' for k in M.IMPORTES))
            self.assertEqual(fila['forma_entrega'], 'flex')
            self.assertEqual(fila['descuadrada'], '')
        rechazado = dict(otro, status='rejected')
        self.assertEqual(M.armar_venta([o], [rechazado, p], e, c), M.armar_venta([o], [p], e, c))
        p['charges_details'].append(cargo('fee', 'financing_add_on_fee', 100))
        filas, des = M.armar_venta([o], [p], e, c)
        self.assertTrue(des)
        self.assertEqual(filas[0]['tiene_cuotas'], 'sí')
        o['order_items'] *= 2
        self.assertEqual(len(M.armar_venta([o], [p], e, c)[0]), 3)

    def test_i_j_k(self):
        for caso, total in [('I', '27000.00'), ('J', '31820.00'), ('K', '25820.00')]:
            o, p, e, c = ejemplo(True)
            c['receiver']['cost'] = 6000 if caso == 'J' else 5000
            if caso == 'I':
                o['order_items'][0]['unit_price'] = 50000
                o['shipping']['id'] = 40000000001
                p.update(transaction_amount=50000, transaction_details={'net_received_amount': 16000},
                         charges_details=[cargo('fee', 'meli_percentage_fee', 7000), cargo('tax', 'debitos_creditos', 300),
                                          cargo('tax', 'sirtac', 700), cargo('shipping', 'shp_cross_docking', 26000)])
                c.update(receiver={'cost': 11000}, senders=[dict(cost=15000, save=15000)], gross_amount=60000)
            if caso != 'J': e['logistic_type'] = 'xd_drop_off'
            aparte = dict(id=90000000009, description='marketplace_shipment', status='approved',
                          transaction_amount=c['receiver']['cost'], transaction_amount_refunded=0,
                          transaction_details={'net_received_amount': c['receiver']['cost'] - 70},
                          charges_details=[cargo('tax', 'impuesto', 70)])
            antes, des = M.armar_venta([o], [p], e, c)
            filas, des_nuevo = M.armar_venta([o], [p], e, c, [aparte])
            self.assertEqual(des, caso != 'K')
            self.assertFalse(des_nuevo)
            self.assertEqual(filas[0]['total'], total)
            self.assertEqual(filas[0]['descuadrada'], 'no')
            self.assertEqual(filas[0]['id_pago_mp'], '90000000001|90000000009')
            movimientos = CLI.mp.leer_reporte('SOURCE_ID,REAL_AMOUNT,TRANSACTION_TYPE\n90000000009,10930,SETTLEMENT_SHIPPING\n', {'separator': ','}, filas)
            self.assertEqual(movimientos[0]['id_venta_ml'], filas[0]['id_venta'])
            invalidos = [dict(aparte, id=1, status='rejected'), dict(aparte, id=2, description='otro')]
            self.assertEqual(M.armar_venta([o], [p], e, c, [aparte] + invalidos), (filas, des_nuevo))
            self.assertEqual([antes[0][k] for k in M.IMPORTES], [filas[0][k] for k in M.IMPORTES])
            self.assertTrue(M.buscar_pago_envio(o, [p], c))
            p['transaction_amount'] += c['receiver']['cost']
            self.assertFalse(M.buscar_pago_envio(o, [p], c))
        o, p, e, c = ejemplo()
        self.assertFalse(M.buscar_pago_envio(o, [p], c))

    def test_refresco_http(self):
        for caso in ('vieja', 'cambio', 'reciente', 'camino', 'reclamo', 'falta', 'aparte', 'aparte_guardado', 'devuelta', 'cancelada'):
            with self.subTest(caso=caso), tempfile.TemporaryDirectory() as tmp:
                o, p, e, c = ejemplo()
                if caso == 'reciente': o['date_closed'] = '2026-10-30T12:00:00-03:00'
                if caso == 'camino': e['status'] = 'shipped'
                if caso == 'reclamo': p['status'] = 'in_mediation'
                if caso in ('aparte', 'aparte_guardado'): c['receiver']['cost'] = 11000
                if caso == 'devuelta': e.update(status='not_delivered', substatus='returned')
                if caso == 'cancelada': e['status'] = 'cancelled'
                carpeta = Path(tmp)
                for tipo, ident, dato in [('orden', o['id'], o), ('pago', p['id'], p), ('envio', 70001, e), ('costos', 70001, c)]:
                    M.guardar_json(carpeta / f'{tipo}-{ident}.json', dato)
                if caso == 'aparte_guardado': M.guardar_json(carpeta / 'envio_pagos-70001.json', {'results': []})
                if caso == 'cambio': o['date_last_updated'] = '2026-10-31T12:00:00Z'
                if caso == 'falta': (carpeta / 'costos-70001.json').unlink()
                detalles = []
                def http(req):
                    ruta = urllib.parse.urlsplit(req.full_url).path
                    if ruta == '/orders/search': dato = dict(results=[o], paging={'total': 1})
                    else:
                        detalles.append(ruta)
                        if ruta.endswith('/payments/search'):
                            self.assertEqual(urllib.parse.parse_qs(urllib.parse.urlsplit(req.full_url).query), {'external_reference': ['70001']})
                            self.assertEqual(urllib.parse.urlsplit(req.full_url).netloc, 'api.mercadopago.com')
                        dato = {'results': [dict(id=90000000009, description='marketplace_shipment', status='approved', transaction_amount=11000)]} if ruta.endswith('/payments/search') else p if '/payments/' in ruta else c if ruta.endswith('/costs') else e
                    return 200, json.dumps(dato).encode()
                with patch.object(O, 'estado', return_value={'user_id': 123}), patch.object(O, 'access_token', return_value='inventado'), patch.object(M, '_http', side_effect=http):
                    filas, des = M.bajar(M.Sesion('ejemplo'), carpeta, dt.date(2026, 9, 1), dt.date(2026, 10, 31), '2026-10-30T12:00:00Z')
                self.assertEqual(len(detalles), 0 if caso in ('vieja', 'aparte_guardado', 'devuelta', 'cancelada') else 4 if caso == 'aparte' else 3)
                self.assertEqual(sum(f['descuadrada'] == 'sí' for f in filas), des)
                if caso == 'aparte':
                    self.assertTrue((carpeta / 'envio_pagos-70001.json').exists())
                    self.assertEqual(filas[0]['id_pago_mp'], '90000000001|90000000009')
                    self.assertEqual(des, 0)

    def test_http_reintentos_y_token(self):
        error = lambda codigo, headers={}: urllib.error.HTTPError('https://example.org', codigo, '', headers, io.BytesIO())
        with patch.object(O, 'access_token', return_value='inventado') as token, patch.object(M.time, 'sleep') as dormir:
            sesion = M.Sesion('ejemplo')
            with patch.object(M, '_http', side_effect=[error(429, {'Retry-After': '7'}), (200, b'{}'), error(401), (200, b'{}')]):
                for _ in range(2): sesion.pedir('mercadolibre', 'https://example.org', M._http)
            dormir.assert_called_once_with(7)
            self.assertEqual(token.call_count, 2)
        with patch.object(O, 'access_token', return_value='inventado'), patch.object(M.time, 'sleep') as dormir:
            with patch.object(M, '_http', side_effect=error(429)):
                with self.assertRaises(M.ErrorDatos): M.Sesion('ejemplo').pedir('mercadolibre', 'https://example.org', M._http)
            self.assertEqual([c.args[0] for c in dormir.call_args_list], [2, 4, 8, 16, 32])

    def test_cache_busqueda_y_llavero_falso(self):
        o, p, e, c = ejemplo()
        def responder(req):
            ruta = urllib.parse.urlsplit(req.full_url).path
            dato = {'results': [o], 'paging': {'total': 1}} if ruta == '/orders/search' else p if '/payments/' in ruta else c if ruta.endswith('/costs') else e
            return 200, json.dumps(dato).encode()
        class Llavero:
            def get_password(self, *args):
                return json.dumps(dict(access_token='inventado', refresh_token='inventado', scope='read', vence=time.time()+10000, user_id=123))
        with tempfile.TemporaryDirectory() as tmp, patch.object(O, '_llavero', return_value=Llavero()), patch.object(M, '_http', side_effect=responder) as http:
            filas, des = M.bajar(M.Sesion('ejemplo'), Path(tmp), dt.date(2026, 9, 1), dt.date(2026, 9, 30))
            self.assertEqual(filas[0]['total'], '11480.00')
            self.assertEqual(http.call_count, 4)
            self.assertEqual(len(list(Path(tmp).glob('*.json'))), 4)
            M.bajar(M.Sesion('ejemplo'), Path(tmp), dt.date(2026, 9, 1), dt.date(2026, 9, 30), '2026-09-29T10:00:00-03:00')
            self.assertTrue(any('date_last_updated.from' in llamada.args[0].full_url for llamada in http.call_args_list))

    def test_paginacion_y_cache_historica(self):
        o, p, e, c = ejemplo()
        consultas = []
        def http(req):
            ruta = urllib.parse.urlsplit(req.full_url)
            if ruta.path == '/orders/search':
                params = urllib.parse.parse_qs(ruta.query)
                consultas.append(params)
                if 'order.date_last_updated.from' in params:
                    dato = {'results': [], 'paging': {'total': 0}}
                elif params['order.date_created.from'][0].startswith('2026-09'):
                    # Dos páginas, la segunda vuelve a traer la misma orden.
                    dato = {'results': [o], 'paging': {'total': 2}}
                else:
                    dato = {'results': [], 'paging': {'total': 0}}
            else:
                dato = p if '/payments/' in ruta.path else c if ruta.path.endswith('/costs') else e
            return 200, json.dumps(dato).encode()
        with tempfile.TemporaryDirectory() as tmp, patch.object(O, 'access_token', return_value='inventado'), patch.object(O, 'estado', return_value={'user_id': 123}), patch.object(M, '_http', side_effect=http):
            filas, _ = M.bajar(M.Sesion('ejemplo'), Path(tmp), dt.date(2026, 9, 1), dt.date(2026, 9, 30))
            self.assertEqual(len(filas), 1)
            self.assertEqual([q['offset'] for q in consultas], [['0'], ['1']])
            consultas.clear()
            filas, _ = M.bajar(M.Sesion('ejemplo'), Path(tmp), dt.date(2026, 9, 1), dt.date(2027, 1, 10), '2027-01-09T10:00:00-03:00')
            self.assertEqual(len(filas), 1)
            self.assertEqual(consultas[0]['order.date_created.from'][0][:10], '2026-11-01')
            self.assertEqual(consultas[-1]['order.date_last_updated.from'][0][:10], '2027-01-07')

    def test_cli_error_conserva_csv_y_control(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(O, 'BASE_REPO', Path(tmp)), patch.object(O, 'estado', return_value={'user_id': 123}), patch.object(O, 'access_token', side_effect=O.ErrorAutorizacion('hay que volver a autorizar')), contextlib.redirect_stdout(io.StringIO()):
            ruta = Path(tmp)
            (ruta / 'ml_ventas.csv').write_text('anterior')
            (ruta / 'control.json').write_text(json.dumps({'fuentes': {'banco': {'ok': True}}}))
            self.assertEqual(CLI.main(['--cliente', 'ejemplo', '--salida', tmp, '--solo', 'mercadolibre']), 1)
            self.assertEqual((ruta / 'ml_ventas.csv').read_text(), 'anterior')
            control = json.loads((ruta / 'control.json').read_text())
            self.assertTrue(control['fuentes']['banco']['ok'])
            self.assertIn('autorizar', control['fuentes']['mercadolibre']['motivo'])

    def test_reemplazo_fallido_conserva_anterior(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / 'salida.csv'
            ruta.write_text('anterior')
            with patch.object(M.os, 'replace', side_effect=OSError('ocupado')):
                with self.assertRaises(OSError): M.atomico(ruta, b'nuevo')
            self.assertEqual(ruta.read_text(), 'anterior')
            self.assertEqual(list(Path(tmp).iterdir()), [ruta])

    def test_cli_exito_atomico(self):
        filas = M.armar_venta([ejemplo()[0]], [ejemplo()[1]], *ejemplo()[2:])[0]
        with tempfile.TemporaryDirectory() as tmp, patch.object(O, 'BASE_REPO', Path(tmp)), patch.object(M, 'bajar', return_value=(filas, 0)), patch.object(M.os, 'replace', wraps=M.os.replace) as reemplazo, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(CLI.main(['--cliente', 'ejemplo', '--salida', tmp, '--solo', 'mercadolibre']), 0)
            # También se guarda el estado diario, por temporal y reemplazo.
            self.assertEqual(len(reemplazo.call_args_list), 4)
            for llamada in reemplazo.call_args_list:
                self.assertEqual(Path(llamada.args[0]).parent, Path(llamada.args[1]).parent)
            control = json.loads((Path(tmp) / 'control.json').read_text())['fuentes']['mercadolibre']
            self.assertEqual((control['filas'], control['desde'], control['hasta']), (1, '2026-09-10', '2026-09-10'))





class LecturaTests(unittest.TestCase):
    def test_reintentos_lectura_y_post(self):
        from http.client import IncompleteRead
        from unittest.mock import Mock
        casos = [
            ([ConnectionResetError(), ConnectionResetError(), (200, b'{}')], [2, 4]),
            ([(200, b'{"cortado":'), (200, b'{}')], [2]),
        ]
        with patch.object(O, 'access_token', return_value='inventado'):
            for respuestas, esperas in casos:
                with self.subTest(respuestas=respuestas), patch.object(M.time, 'sleep') as dormir:
                    http = Mock(side_effect=respuestas)
                    self.assertEqual(M.Sesion('ejemplo').pedir('mercadolibre', 'https://example.org', http), {})
                    self.assertEqual([c.args[0] for c in dormir.call_args_list], esperas)
            with patch.object(M.time, 'sleep') as dormir:
                http = Mock(side_effect=IncompleteRead(b'cortado'))
                with self.assertRaisesRegex(M.ErrorDatos, 'no se pudo leer la respuesta de mercadolibre; revisar la conexión y volver a intentar'):
                    M.Sesion('ejemplo').pedir('mercadolibre', 'https://example.org', http)
                self.assertEqual(http.call_count, 6)
                self.assertEqual([c.args[0] for c in dormir.call_args_list], [2, 4, 8, 16, 32])
            for error in (ConnectionResetError(), IncompleteRead(b''), TimeoutError(), ValueError()):
                with self.subTest(error=error), patch.object(M.time, 'sleep') as dormir:
                    http = Mock(side_effect=error)
                    with self.assertRaisesRegex(M.ErrorDatos, 'no se pudo leer la respuesta'):
                        M.Sesion('ejemplo').pedir('mercadopago', 'https://example.org', http, cuerpo={})
                    self.assertEqual(http.call_count, 1)
                    dormir.assert_not_called()


if __name__ == '__main__':
    unittest.main()
