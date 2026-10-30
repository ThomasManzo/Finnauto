"""Liquidaciones inventadas; todo el HTTP se reemplaza en estas pruebas."""
import contextlib
import datetime as dt
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ingestas import mp_liquidaciones as M, meli_ventas as ML, meli_oauth as O, mercado_datos as CLI

TEXTO = 'SOURCE_ID;TRANSACTION_TYPE;REAL_AMOUNT;FEE_AMOUNT;SETTLEMENT_DATE;BUSINESS_UNIT;SUB_UNIT\n90000000001;SETTLEMENT;11480.00;-3000.00;2026-09-12T15:20:00Z;marketplace;venta\n'
VENTAS = [dict(id_venta='2000000000000101', id_pago_mp='90000000001')]


class LiquidacionesTests(unittest.TestCase):
    def test_lectura_y_faltantes(self):
        fila = M.leer_reporte(TEXTO, {'separator': ';'}, VENTAS)[0]
        self.assertEqual((fila['monto_neto'], fila['comision'], fila['fecha_liquidacion'], fila['unidad_negocio'], fila['id_venta_ml'], fila['medio_pago']), ('11480.00', '-3000.00', '2026-09-12 12:20', 'marketplace / venta', '2000000000000101', ''))
        for texto in ('SOURCE_ID\n1\n', 'REAL_AMOUNT\n2\n'):
            with self.assertRaises(M.ErrorDatos): M.leer_reporte(texto, {})

    def test_existente_pedido_espera_cache_y_no_duplicados(self):
        pedidos, listas = [], [0]
        reporte = dict(id=1, begin_date='2026-09-01T03:00:00Z', end_date='2026-10-01T02:59:59Z', status='processed', format='CSV', file_name='septiembre.csv')
        octubre = dict(reporte, id=2, begin_date='2026-10-01T03:00:00Z', end_date='2026-10-03T02:59:59Z', file_name='octubre.csv')
        def http(req):
            pedidos.append(req)
            if req.full_url.endswith('/config'): dato = {'separator': ';'}
            elif req.full_url.endswith('/list'):
                listas[0] += 1
                dato = [reporte] + ([octubre] if listas[0] > 1 else [])
            elif req.get_method() == 'POST': return 202, b''
            else: return 200, (TEXTO + TEXTO.splitlines(True)[1]).encode()
            return 200, json.dumps(dato).encode()
        with tempfile.TemporaryDirectory() as tmp, patch.object(O, 'access_token', return_value='inventado') as token, patch.object(M, '_http', side_effect=http), patch.object(M.time, 'sleep') as dormir:
            sesion = ML.Sesion('ejemplo')
            filas, motivo = M.bajar(sesion, Path(tmp), dt.date(2026, 9, 1), dt.date(2026, 10, 2), VENTAS)
            self.assertEqual((len(filas), motivo), (1, ''))
            self.assertEqual(filas[0]['id_venta_ml'], VENTAS[0]['id_venta'])
            dormir.assert_called_once_with(30)
            posts = [p for p in pedidos if p.get_method() == 'POST']
            self.assertEqual(len(posts), 1)
            self.assertEqual(json.loads(posts[0].data), dict(begin_date=octubre['begin_date'], end_date=octubre['end_date']))
            self.assertTrue(all(p.get_method() == 'GET' for p in pedidos if p.full_url.endswith('/config')))
            pedidos.clear()
            M.bajar(sesion, Path(tmp), dt.date(2026, 9, 1), dt.date(2026, 10, 2), VENTAS)
            self.assertEqual(len(pedidos), 2)
            token.assert_called_once_with('ejemplo', 'mercadopago')

    def test_pendiente_no_pisa_csv(self):
        def http(req):
            if req.full_url.endswith('/config'): return 200, b'{}'
            if req.full_url.endswith('/list'): return 200, b'[]'
            return 202, b''
        with tempfile.TemporaryDirectory() as tmp, patch.object(O, 'access_token', return_value='inventado'), patch.object(M, '_http', side_effect=http), patch.object(M.time, 'sleep') as dormir:
            filas, motivo = M.bajar(ML.Sesion('ejemplo'), Path(tmp), dt.date(2026, 9, 1), dt.date(2026, 9, 30))
            self.assertEqual(filas, [])
            self.assertIn('2026-09', motivo)
            self.assertEqual(dormir.call_count, 20)
            with patch.object(O, 'BASE_REPO', Path(tmp)), patch.object(M, 'bajar', return_value=([], motivo)), contextlib.redirect_stdout(io.StringIO()):
                (Path(tmp) / 'mp_movimientos.csv').write_text('anterior')
                self.assertEqual(CLI.main(['--cliente', 'ejemplo', '--salida', tmp, '--solo', 'mercadopago']), 1)
                self.assertEqual((Path(tmp) / 'mp_movimientos.csv').read_text(), 'anterior')

    def test_filas_completas_y_huso_configurado(self):
        texto = 'SOURCE_ID;REAL_AMOUNT;SETTLEMENT_DATE;DETALLE\n1;10;2026-09-12T15:20:00;uno\n1;10;2026-09-12T15:20:00;dos\n1;10;2026-09-12T15:20:00;uno\n'
        filas = M.leer_reporte(texto, {'separator': ';', 'display_timezone': '+00:00'})
        self.assertEqual(len(filas), 2)
        self.assertEqual(filas[0]['fecha_liquidacion'], '2026-09-12 12:20')

    def test_203_y_columna_faltante_no_se_guardan(self):
        reporte = dict(begin_date='2026-09-01T03:00:00Z', end_date='2026-10-01T02:59:59Z', status='processed', format='CSV', file_name='mes.csv')
        def http(req):
            if req.full_url.endswith('/config'): return 200, b'{}'
            if req.full_url.endswith('/list'): return 200, json.dumps([reporte]).encode()
            return 200, b'SOURCE_ID\n1\n'
        with tempfile.TemporaryDirectory() as tmp, patch.object(O, 'access_token', return_value='inventado'), patch.object(M, '_http', side_effect=http):
            with self.assertRaisesRegex(ML.ErrorDatos, 'faltan'):
                M.bajar(ML.Sesion('ejemplo'), Path(tmp), dt.date(2026, 9, 1), dt.date(2026, 9, 30))
            self.assertFalse(list(Path(tmp).glob('*.csv')))
        with patch.object(O, 'access_token', return_value='inventado'):
            with self.assertRaisesRegex(ML.ErrorDatos, 'más tarde'):
                ML.Sesion('ejemplo').pedir('mercadopago', M.BASE, lambda r: (203, b''), {})

    def test_excel(self):
        try: import openpyxl
        except ImportError: self.skipTest('openpyxl no está en este intérprete')
        libro = openpyxl.Workbook()
        libro.active.append(['SOURCE_ID', 'REAL_AMOUNT', 'SETTLEMENT_DATE'])
        libro.active.append(['90000000001', 11480, dt.datetime(2026, 9, 12, 12, 20)])
        contenido = io.BytesIO()
        libro.save(contenido)
        filas = M.leer_archivo(contenido.getvalue(), 'XLSX', {}, VENTAS)
        self.assertEqual(filas[0]['monto_neto'], '11480.00')
        self.assertEqual(filas[0]['id_venta_ml'], VENTAS[0]['id_venta'])


if __name__ == '__main__': unittest.main()
