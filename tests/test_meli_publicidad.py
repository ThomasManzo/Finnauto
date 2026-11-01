"""Publicidad inventada; sin red ni credenciales reales."""
import contextlib
import datetime as dt
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.parse
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ingestas import meli_publicidad as A, meli_ventas as M, meli_oauth as O, mercado_datos as CLI


class Reloj(dt.datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 11, 1, 12, tzinfo=M.HORA_BA)


class PublicidadTests(unittest.TestCase):
    def responder(self, req):
        u = urllib.parse.urlsplit(req.full_url)
        q = urllib.parse.parse_qs(u.query)
        self.pedidos.append((u.path, q))
        self.assertIn('Bearer', req.get_header('Authorization'))
        if u.path.endswith('/advertisers'):
            self.assertEqual(req.get_header('Api-version'), '1')
            dato = {'advertisers': [] if self.sin else [{'advertiser_id': 123, 'site_id': 'MLA'}]}
        else:
            self.assertEqual(req.get_header('Api-version'), '2')
            self.assertGreaterEqual(q['date_from'][0], '2026-08-04')
            if q.get('aggregation_type') == ['DAILY']:
                dato = {'results': self.dias}
                if q.get('limit') == ['1'] and self.error:
                    dato = {'results': [dict(date='2026-10-01', cost=1200)]}
            else:
                avisos = [{'item_id': 'MLA1000000001', 'metrics': {'cost': 1500}},
                          {'item_id': 'MLA1000000002', 'metrics': {'cost': 0}}]
                offset = int(q['offset'][0])
                dato = {'results': avisos[offset:offset+1], 'paging': {'total': 2}}
        return 200, json.dumps(dato).encode()

    def setUp(self):
        reloj = patch.object(CLI.dt, 'datetime', Reloj)
        reloj.start()
        self.addCleanup(reloj.stop)
        self.pedidos, self.error, self.sin = [], False, False
        self.dias = [dict(date='2026-10-01', cost=1000.25, clicks=20, direct_units_quantity=1,
                         indirect_units_quantity=0, organic_units_quantity=1, total_amount=25000),
                     dict(date='2026-10-02', cost=499.75, clicks=10, direct_units_quantity=1,
                         indirect_units_quantity=1, organic_units_quantity=0, total_amount=40000)]

    def test_l_ventana_acumulacion_y_sin_anunciante(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(O, 'access_token', return_value='inventado'), patch.object(A, '_http', side_effect=self.responder):
            carpeta = Path(tmp)
            M.guardar_json(carpeta / 'MLA1000000001.json', {'2026-01-01': {'cost': 50}})
            filas = A.bajar(M.Sesion('ejemplo'), carpeta, dt.date(2025, 10, 1), dt.date(2026, 10, 31))
            self.assertEqual([f['costo'] for f in filas], ['50.00', '1000.25', '499.75'])
            self.assertEqual(filas[1]['ventas_por_anuncio'], '25000.00')
            self.assertFalse(any(p.endswith('MLA1000000002') for p, _ in self.pedidos))
            self.dias = [dict(date='2026-10-02', cost=600)]
            filas = A.bajar(M.Sesion('ejemplo'), carpeta, dt.date(2026, 10, 2), dt.date(2026, 10, 31))
            self.assertEqual(filas[0]['costo'], '600.00')
            cache = json.loads((carpeta / 'MLA1000000001.json').read_text())
            self.assertIn('2026-01-01', cache)
            self.assertIn('2026-10-01', cache)
            self.sin = True
            self.assertEqual(A.bajar(M.Sesion('ejemplo'), carpeta, dt.date(2025, 10, 1), dt.date(2026, 10, 31)), [])

    def test_corrida_completa_aisla_error_y_respeta_orden(self):
        llamadas = []
        def ventas(*args):
            llamadas.append('ventas')
            raise M.ErrorDatos('ventas no disponibles')
        def pagos(*args):
            llamadas.append('pagos')
            return [], ''
        def publicidad(*args):
            llamadas.append('publicidad')
            return []
        with tempfile.TemporaryDirectory() as tmp, patch.object(O, 'BASE_REPO', Path(tmp)), patch.object(M, 'bajar', side_effect=ventas), patch.object(CLI.mp, 'bajar', side_effect=pagos), patch.object(A, 'bajar', side_effect=publicidad), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(CLI.main(['--cliente', 'ejemplo', '--salida', tmp]), 1)
            self.assertEqual(llamadas, ['ventas', 'pagos', 'publicidad'])
            fuentes = json.loads((Path(tmp) / 'control.json').read_text())['fuentes']
            self.assertTrue(fuentes['mercadolibre_publicidad']['ok'])
            self.assertTrue(fuentes['mercadopago']['ok'])
            self.assertFalse(fuentes['mercadolibre']['ok'])

    def test_error_conserva_csv_y_fuentes(self):
        self.error = True
        with tempfile.TemporaryDirectory() as tmp, patch.object(O, 'BASE_REPO', Path(tmp)), patch.object(O, 'access_token', return_value='inventado'), patch.object(A, '_http', side_effect=self.responder), contextlib.redirect_stdout(io.StringIO()):
            ruta = Path(tmp)
            (ruta / 'ml_publicidad.csv').write_text('anterior')
            (ruta / 'control.json').write_text(json.dumps({'fuentes': {'banco': {'ok': True}}}))
            self.assertEqual(CLI.main(['--cliente', 'ejemplo', '--salida', tmp, '--solo', 'mercadolibre_publicidad']), 1)
            self.assertEqual((ruta / 'ml_publicidad.csv').read_text(), 'anterior')
            fuentes = json.loads((ruta / 'control.json').read_text())['fuentes']
            self.assertTrue(fuentes['banco']['ok'])
            self.assertIn('no coincide', fuentes['mercadolibre_publicidad']['motivo'])
            self.sin = True
            self.assertEqual(CLI.main(['--cliente', 'ejemplo', '--salida', tmp, '--solo', 'mercadolibre_publicidad']), 0)
            self.assertEqual((ruta / 'ml_publicidad.csv').read_text().strip(), ','.join(A.COLUMNAS))


if __name__ == '__main__': unittest.main()
