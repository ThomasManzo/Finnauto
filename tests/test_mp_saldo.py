"""Saldos inventados, HTTP falso y esperas anuladas: nunca usa cuentas reales."""
import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ingestas import mp_saldo as S, mercado_datos as C
from ingestas.meli_ventas import Sesion, ErrorDatos

EJEMPLO = b'''DATE;SOURCE_ID;DESCRIPTION;NET_CREDIT_AMOUNT;NET_DEBIT_AMOUNT;BALANCE_AMOUNT
2026-01-10T00:00:00.000-03:00;;;1000.00;0.00;1000.00
2026-01-10T09:00:00.000-03:00;111;payment;50.00;0.00;1050.00
2026-01-10T10:00:00.000-03:00;;asset_management;2.50;0.00;1052.50
2026-01-12T08:00:00.000-03:00;222;payout;0.00;52.50;1000.00
;;;1000.00;0.00;0.00
'''


class SaldoTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.carpeta, self.csv = self.base / 'reportes', self.base / 'mp_saldo.csv'
        self.desde, self.hasta = dt.date(2026, 1, 10), dt.date(2026, 1, 12)
        self.reporte = dict(id=1, begin_date='2026-01-01T03:00:00Z', end_date='2026-01-13T02:59:59Z',
                            status='enabled', format='CSV', file_name='inventado.csv')
        self.listado, self.contenido = [self.reporte], EJEMPLO
        self.sesion = Sesion('ejemplo')
        self.sesion.tokens['mercadopago'] = 'token-inventado'
        for parche in (patch.object(S, '_http', side_effect=self.http),
                       patch.object(S.time, 'sleep'),
                       patch.object(S.meli_oauth, 'access_token', side_effect=AssertionError('No pedir token'))):
            valor = parche.start()
            self.addCleanup(parche.stop)
            if parche.attribute == '_http': self.red = valor
            if parche.attribute == 'sleep': self.dormir = valor

    def http(self, pedido):
        url, metodo = pedido.full_url, pedido.get_method()
        if url.endswith('/config'):
            self.assertEqual(metodo, 'GET')
            return 200, b'{"separator": ";", "display_timezone": "-03:00"}'
        if url.endswith('/list'):
            self.assertEqual(metodo, 'GET')
            return 200, json.dumps(self.listado).encode()
        if url == S.BASE:
            self.assertEqual(metodo, 'POST')
            cuerpo = json.loads(pedido.data)
            self.assertEqual(cuerpo['begin_date'], self.reporte['begin_date'])
            self.assertEqual(cuerpo['end_date'], self.reporte['end_date'])
            return 202, b''
        self.assertEqual(metodo, 'GET')
        return 200, self.contenido

    def bajar(self):
        return S.bajar(self.sesion, self.carpeta, self.csv, self.desde, self.hasta)

    def posts(self):
        return [c for c in self.red.call_args_list if c.args[0].get_method() == 'POST']

    def test_ejemplo_cache_y_dias_sin_movimientos(self):
        filas, motivo = self.bajar()
        self.assertEqual(motivo, '')
        self.assertEqual([f['disponible'] for f in filas], ['1052.50', '1052.50', '1000.00'])
        self.assertEqual([f['intereses_del_dia'] for f in filas], ['2.50', '0.00', '0.00'])
        self.assertTrue(all(f['a_liberar'] == '' for f in filas))
        self.red.reset_mock()
        self.assertEqual(self.bajar(), (filas, ''))
        self.red.assert_not_called()

    def test_conserva_historial_y_no_duplica_ni_pide_token(self):
        vieja = dict(fecha='2026-01-10', disponible='777.123', a_liberar='8', intereses_del_dia='9')
        C.escribir_csv(self.csv, S.COLUMNAS, [vieja])
        filas, motivo = self.bajar()
        self.assertEqual(filas[0], vieja)
        self.assertEqual(len(filas), 3)
        C.escribir_csv(self.csv, S.COLUMNAS, filas)
        anterior = self.csv.read_bytes()
        self.red.reset_mock()
        self.sesion.tokens.clear()
        self.assertEqual(self.bajar(), (filas, ''))
        self.red.assert_not_called()
        self.assertEqual(self.csv.read_bytes(), anterior)

    def test_reporte_roto_no_guarda_cache_ni_toca_csv(self):
        C.escribir_csv(self.csv, S.COLUMNAS, [dict(fecha='2026-01-09', disponible='5', a_liberar='', intereses_del_dia='')])
        anterior = self.csv.read_bytes()
        for contenido in (EJEMPLO.replace(b'1052.50', b'1059.50'),
                          EJEMPLO.replace(b'BALANCE_AMOUNT', b'OTRA'),
                          b'\n'.join(EJEMPLO.split(b'\n')[:1] + EJEMPLO.split(b'\n')[2:])):
            with self.subTest(contenido=contenido):
                self.contenido = contenido
                with self.assertRaises(ErrorDatos): self.bajar()
                self.assertFalse(list(self.carpeta.glob('*.csv')))
                self.assertEqual(self.csv.read_bytes(), anterior)

    def test_no_llega_no_repite_pedido_y_no_salta_meses(self):
        self.listado = []
        filas, motivo = self.bajar()
        self.assertEqual(filas, [])
        self.assertIn('2026-01-01_2026-01-12', motivo)
        self.assertEqual(len(self.posts()), 1)
        self.assertEqual(sum(c.args[0] for c in self.dormir.call_args_list), 300)
        self.assertEqual(self.bajar(), (filas, motivo))
        self.assertEqual(len(self.posts()), 1)
        self.assertFalse(self.csv.exists())
        self.hasta = dt.date(2026, 2, 2)
        self.reporte['end_date'] = '2026-02-01T02:59:59Z'
        filas, motivo = self.bajar()
        self.assertEqual(filas, [])
        self.assertIn('2026-02-01_2026-02-02', motivo)
        self.assertFalse((self.carpeta / '2026-02-01_2026-02-02.pedido.json').exists())

    def test_pending_no_pide_y_processed_se_acepta(self):
        self.reporte['status'] = 'pending'
        self.assertTrue(self.bajar()[1])
        self.assertEqual(self.posts(), [])
        self.reporte['status'] = 'processed'
        self.assertEqual(len(self.bajar()[0]), 3)

    def test_listado_se_actualiza_durante_espera(self):
        self.listado = []
        self.dormir.side_effect = lambda _: self.listado.append(self.reporte)
        self.assertEqual(len(self.bajar()[0]), 3)
        self.assertEqual(len(self.posts()), 1)

    def test_varios_meses_cache_y_apertura_distinta_del_historial(self):
        self.carpeta.mkdir()
        (self.carpeta / '2026-01-01_2026-01-31.csv').write_bytes(EJEMPLO)
        febrero = b'DATE;DESCRIPTION;NET_CREDIT_AMOUNT;NET_DEBIT_AMOUNT;BALANCE_AMOUNT\n2026-02-01T00:00:00-03:00;;40;0;40\n2026-02-02T10:00:00-03:00;asset_management;1;0;41\n'
        (self.carpeta / '2026-02-01_2026-02-02.csv').write_bytes(febrero)
        self.hasta = dt.date(2026, 2, 2)
        filas, motivo = self.bajar()
        self.assertEqual(motivo, '')
        self.assertEqual(len(filas), 24)
        self.assertEqual(filas[-3]['disponible'], '1000.00')
        self.assertEqual(filas[-2]['disponible'], '40.00')
        self.assertEqual(filas[-1]['intereses_del_dia'], '1.00')
        self.red.assert_not_called()

    def test_fecha_local_e_intereses_netos(self):
        contenido = EJEMPLO.replace(b'2026-01-10T10:00:00.000-03:00', b'2026-01-10T23:30:00.000-05:00')
        contenido = contenido.replace(b'2.50;0.00;1052.50', b'3.50;1.00;1052.50')
        filas = S.leer_reporte(contenido, {'separator': ';'}, self.desde, self.hasta)
        self.assertEqual(filas[0]['intereses_del_dia'], '2.50')
        self.assertEqual(filas[1]['intereses_del_dia'], '0.00')


if __name__ == '__main__':
    unittest.main()
