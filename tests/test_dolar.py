"""Cotizaciones inventadas, sin red, perfiles ni permisos."""
import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.error

from ingestas import dolar as D, mercado_datos as C


class DolarTests(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.salida = Path(temporal.name)
        self.desde, self.hasta = dt.date(2026, 1, 2), dt.date(2026, 1, 3)
        self.espera = patch.object(D.time, 'sleep').start()
        self.addCleanup(patch.stopall)

    def bajar(self, datos):
        return D.bajar(self.salida, self.desde, self.hasta,
                       http=Mock(return_value=(200, json.dumps(datos).encode())))

    def fila(self, fecha, compra=4, venta=5):
        return dict(fecha=fecha, compra=compra, venta=venta, casa='oficial')

    def test_filtra_hoy_y_ordena_con_decimales(self):
        filas = self.bajar([self.fila('2026-01-04'), self.fila('2026-01-03', 4.125),
                            self.fila('2026-01-01'), self.fila('2026-01-02')])
        self.assertEqual([f['fecha'] for f in filas], ['2026-01-02', '2026-01-03'])
        self.assertEqual(filas[1], dict(fecha='2026-01-03', compra='4.13', venta='5.00', fuente='argentinadatos'))

    def test_suma_sin_pisar_ni_borrar_fuera_del_periodo(self):
        anteriores = [dict(fecha=f, compra='2.00', venta='3.00', fuente='argentinadatos')
                      for f in ['2026-01-01', '2026-01-02']]
        C.escribir_csv(self.salida / 'dolar.csv', D.COLUMNAS, anteriores)
        filas = self.bajar([self.fila('2026-01-02'), self.fila('2026-01-03')])
        self.assertEqual(filas[:2], anteriores)
        self.assertEqual(len(filas), 3)

    def test_datos_invalidos_no_tocan_archivo(self):
        ruta = self.salida / 'dolar.csv'
        ruta.write_bytes(b'historial anterior\r\n')
        invalidos = [{}, [None], [dict(compra=4, venta=5)], [self.fila('2026-02-30')]]
        for campo in ('compra', 'venta'):
            for valor in (None, '4', True, 0, -1, float('nan'), float('inf')):
                fila = self.fila('2026-01-01')  # También se valida fuera del período.
                fila[campo] = valor
                invalidos.append([fila])
        for datos in invalidos:
            with self.subTest(datos=datos), self.assertRaises(C.ml.ErrorDatos):
                self.bajar(datos)
            self.assertEqual(ruta.read_bytes(), b'historial anterior\r\n')

    def test_reintenta_corte_y_errores_transitorios(self):
        for error in (urllib.error.URLError('corte'), TimeoutError(),
                      urllib.error.HTTPError(D.URL, 429, '', None, None),
                      urllib.error.HTTPError(D.URL, 503, '', None, None)):
            http = Mock(side_effect=[error, (200, b'[]')])
            self.assertEqual(D.bajar(self.salida, self.desde, self.hasta, http=http), [])
            self.assertEqual(http.call_count, 2)
            self.assertEqual(http.call_args.args[0].get_header('User-agent'), 'finauto')

    def test_error_final_y_error_permanente(self):
        for codigo, intentos in ((500, 3), (404, 1)):
            http = Mock(side_effect=urllib.error.HTTPError(D.URL, codigo, '', None, None))
            with self.assertRaisesRegex(C.ml.ErrorDatos, D.ERROR_CONEXION):
                D.bajar(self.salida, self.desde, self.hasta, http=http)
            self.assertEqual(http.call_count, intentos)

    def test_http_timeout(self):
        with patch.object(D.urllib.request, 'urlopen') as abrir:
            respuesta = abrir.return_value.__enter__.return_value
            respuesta.status, respuesta.read.return_value = 200, b'[]'
            self.assertEqual(D._http('pedido'), (200, b'[]'))
            abrir.assert_called_once_with('pedido', timeout=60)


if __name__ == '__main__':
    unittest.main()
