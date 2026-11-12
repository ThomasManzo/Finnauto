"""Saldos BBVA con archivos chicos y datos completamente inventados."""
import datetime as dt
import tempfile
import unittest
from pathlib import Path

import openpyxl
from lector import extractos as e


class SaldoParcialBBVA(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.base = Path(temporal.name)
        (self.base / 'bbva').mkdir()
        self.dia = dt.date(2026, 9, 23)
        self.filas = [
            ['23-09-2026', 'PAGO ejemplo', '', -200, 1350],
            ['23-09-2026', 'COBRO ejemplo', 400, '', 950],
            ['23-09-2026', 'PAGO ejemplo', '', -50, 1000],
        ]

    def archivo(self, nombre='diario.xlsx', saldo=1150, filas=None):
        ruta = self.base / 'bbva' / nombre
        wb = openpyxl.Workbook()
        for fila in [['Empresa:', 'Empresa ejemplo'], ['Cuenta:', '111-000111/1'],
                     ['Saldo:', saldo], ['Fecha', 'Concepto', 'Crédito', 'Débito', 'Saldo Parcial']
                     ] + (self.filas if filas is None else filas):
            wb.active.append(fila)
        wb.save(ruta)
        wb.close()
        return ruta

    def test_cadena_correcta(self):
        lectura = e.leer_planilla_bbva(self.archivo(saldo='1.150,00'))
        self.assertEqual(lectura['saldos_por_dia'], {self.dia: 1150})
        self.assertNotIn('REVISAR', lectura['nota'])

    def test_encabezado_con_saldo_anterior_no_publica(self):
        lectura = e.leer_planilla_bbva(self.archivo(saldo=1350))
        self.assertEqual(lectura['saldos_por_dia'], {})
        self.assertEqual(len(lectura['movimientos']), 3)
        for texto in ['REVISAR saldo', 'encabezado', '1150', '1350']:
            self.assertIn(texto, lectura['nota'])

    def test_cadena_rota_no_publica(self):
        self.filas[1][-1] = 900
        lectura = e.leer_planilla_bbva(self.archivo())
        self.assertEqual(lectura['saldos_por_dia'], {})
        self.assertEqual(len(lectura['movimientos']), 3)
        for texto in ['REVISAR saldo', 'cadena', '900', '400', '1300', '1350']:
            self.assertIn(texto, lectura['nota'])

    def test_dos_dias(self):
        self.filas.append(['22-09-2026', 'COBRO ejemplo', 100, '', 900])
        lectura = e.leer_planilla_bbva(self.archivo())
        self.assertEqual(lectura['saldos_por_dia'], {self.dia: 1150, dt.date(2026, 9, 22): 1000})
        self.assertNotIn('REVISAR', lectura['nota'])

    def test_archivo_mas_completo_gana_aunque_cierre_en_cero(self):
        self.archivo('a_completo.xlsx', 0, [
            ['23-09-2026', 'PAGO ejemplo', '', -300, 300],
            ['23-09-2026', 'PAGO ejemplo', '', -200, 500],
            ['23-09-2026', 'COBRO ejemplo', 500, '', 0]])
        self.archivo('z_temprano.xlsx', 500, [['23-09-2026', 'COBRO ejemplo', 500, '', 0]])
        resultado = e.procesar(self.base)
        self.assertEqual(resultado['errores'], [])
        self.assertEqual(resultado['saldos'][0]['saldo'], 0)

    def test_empate_gana_ultimo(self):
        self.archivo('a.xlsx', 500, [['23-09-2026', 'COBRO ejemplo', 500, '', 0]])
        self.archivo('z.xlsx', 600, [['23-09-2026', 'COBRO ejemplo', 600, '', 0]])
        self.assertEqual(e.procesar(self.base)['saldos'][0]['saldo'], 600)

    def test_parcial_ausente_no_publica(self):
        self.filas[1][-1] = None
        lectura = e.leer_planilla_bbva(self.archivo())
        self.assertEqual(lectura['saldos_por_dia'], {})
        self.assertIn('REVISAR saldo: cadena incompleta', lectura['nota'])

    def test_tolerancia_de_un_centavo(self):
        self.filas[1][-1] = 950.01
        lectura = e.leer_planilla_bbva(self.archivo(saldo=1150.01))
        self.assertEqual(lectura['saldos_por_dia'], {self.dia: 1150})
        self.assertNotIn('REVISAR', lectura['nota'])


if __name__ == '__main__':
    unittest.main()
