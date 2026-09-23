"""Defensas del cash con exports inventados; no necesita Drive ni toca producción."""
import datetime as dt
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import openpyxl
from lector import tango
from clientes.navar.herramientas import vigilante


class Estados(unittest.TestCase):
    def leer(self, estados, propio=False):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / 'A cheques terceros 2026-09-22.xlsx'
            wb = openpyxl.Workbook()
            ws = wb.active
            columnas = list(dict.fromkeys(k for d in estados for k in d))
            ws.append(['Fecha del cheque', 'Importe', *columnas])
            for d in estados:
                ws.append([dt.date(2026, 10, 1), 100, *(d.get(k) for k in columnas)])
            wb.save(ruta)
            wb.close()
            leer = tango.leer_cheques_propios if propio else tango.leer_cheques_terceros
            return leer(ruta, 'A', dt.date(2026, 9, 22), 'Prueba')

    def test_codigo_texto_espacios_acentos_y_conflictos(self):
        filas, desc = self.leer([
            {' Cód. ESTADO ': ' c '}, {'Estado': ' ÉN  CARTERA '},
            {'Estado': 'En Cartera', ' Cód. ESTADO ': 'C'},
            {'Estado': 'Aplicado', ' Cód. ESTADO ': 'C'},
            {'Estado': 'En Cartera', ' Cód. ESTADO ': 'R'},
            {'Estado': 'Rechazado'}, {'Estado': 'Anulado'}, {'Estado': ''},
        ])
        self.assertEqual(len(filas), 3)
        self.assertEqual(sum(n for n, _ in desc.values()), 5)
        self.assertEqual(sum(m for _, m in desc.values()), 500)

    def test_sin_columnas_no_confundir_subestado(self):
        for propio in (False, True):
            filas, desc = self.leer([{'Subestado': 'En Cartera'}], propio)
            self.assertEqual(filas, [])
            self.assertIn('lista afuera', next(iter(desc)))

    def test_propios_solo_al_cobro(self):
        filas, desc = self.leer([{'Estado': ' ÁL  COBRO '}, {'Estado': 'Debitado'},
                                 {'Estado': 'Anulado'}, {'Estado': ''}], True)
        self.assertEqual(len(filas), 1)
        self.assertEqual(sum(n for n, _ in desc.values()), 3)

    def test_resumen_informa_descartes(self):
        filas, desc = self.leer([{'Estado': 'Aplicado'}])
        res = dict(hoy=dt.date(2026, 9, 22), archivos={}, empresas=['A'],
                   listas=dict(cobrar=[], pagar=[], cheques=filas), saldos={},
                   descartes={('A', 'cheques_terceros'): desc},
                   corte_deuda_vieja=dt.date(2026, 1, 1))
        texto = tango.resumen(res, 'prueba.xlsx')
        self.assertIn('se ignoraron 1 cheques', texto)
        self.assertIn('aplicado', texto)


class Crecimiento(unittest.TestCase):
    def test_umbrales_y_achicamiento(self):
        for antes, ahora, retener in [(332, 337, False), (1694, 75611, True),
                                      (100, 300, False), (100, 301, True),
                                      (0, 100, False), (0, 101, True),
                                      (30, 10, True), (30, 15, False)]:
            with self.subTest(antes=antes, ahora=ahora), \
                 patch.object(vigilante.glob, 'glob', return_value=['anterior.xlsx']), \
                 patch.object(vigilante, '_filas_por_solapa', side_effect=[
                     {'Cartera': antes}, {'Cartera': ahora}]):
                self.assertEqual(bool(vigilante.control_contra_anterior('nuevo.xlsx')), retener)

    def test_retiene_archivo_y_resumen_sin_publicar(self):
        with tempfile.TemporaryDirectory() as carpeta:
            base = Path(carpeta)
            entrada, salida = base / 'entrada', base / 'salida'
            entrada.mkdir()
            salida.mkdir()
            def guardar(ruta, cantidad):
                wb = openpyxl.Workbook()
                wb.active.title = 'Cartera'
                wb.active.append(['Cheque'])
                for i in range(cantidad):
                    wb.active.append([i])
                wb.save(ruta)
                wb.close()
            guardar(salida / 'para_pegar_prueba_2026-09-21.xlsx', 30)
            nombre = 'para_pegar_prueba_2026-09-22.xlsx'
            guardar(entrada / nombre, 131)
            (entrada / 'resumen_prueba.md').write_text('Prueba')
            with patch.object(vigilante, 'SALIDA', str(salida)), patch.object(vigilante, 'log') as log:
                self.assertIn('crecimiento desmedido', vigilante.mover_salidas(str(entrada)))
                log.assert_called_once()
            self.assertTrue((salida / '_retenido' / nombre).exists())
            self.assertTrue((salida / '_retenido/resumen_prueba.md').exists())
            self.assertFalse((salida / nombre).exists())


if __name__ == '__main__':
    unittest.main()
