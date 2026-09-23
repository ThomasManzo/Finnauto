"""Prueba inventada del lector; ejecutar desde la raíz con python -m unittest discover -s lector/pruebas."""
import datetime as dt
import os
from pathlib import Path
import tempfile
import unittest

import openpyxl
from lector import tango


class Cheques(unittest.TestCase):
    def test_fechas_y_foto_mas_nueva(self):
        # La foto vieja queda última al ordenar por nombre y tiene modificación más reciente.
        # Ninguna de esas dos cosas debe ganarle a la fecha de exportación.
        with tempfile.TemporaryDirectory() as carpeta:
            def guardar(nombre, encabezados, filas):
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.append(encabezados)
                for fila in filas:
                    ws.append([fila.get(c) for c in encabezados])
                ruta = Path(carpeta) / nombre
                wb.save(ruta)
                wb.close()
                return ruta

            enc = ['Nro. de cheque', 'Banco', 'Razón social', 'Fecha de emisión',
                   'Fecha del cheque', 'Importe mon. cta.', 'Estado', 'Cód. cta. emision']
            filas = [{'Nro. de cheque': str(i), 'Banco': 'Banco prueba', 'Razón social': 'Proveedor prueba',
                      'Fecha de emisión': dt.date(2026, 7, i), 'Fecha del cheque': dt.date(2026, 9, 24+i),
                      'Importe mon. cta.': 100*i, 'Estado': 'Al Cobro'} for i in (1, 2, 3)]
            vieja = guardar('A cheques propios 2026-09-16.xlsx', enc,
                            [dict(f, **{'Fecha del cheque': dt.date(2026, 8, 25)}) for f in filas])
            nueva = guardar('A Cheques propios 2026-09-22.xlsx', list(reversed(enc[:-1])), filas)
            os.utime(vieja, (2000000000, 2000000000))
            self.assertEqual(tango.localizar(carpeta)[('A', 'cheques_propios')], str(nueva))
            terceros = [{'Nro. de cheque': str(10+i), 'Banco': 'Banco prueba', 'Cliente': 'Cliente prueba',
                         'Fecha del cheque': dt.date(2026, 11, i), 'Importe': 200*i,
                         'Estado': 'En Cartera', 'CUIT del cliente': 'inventado'} for i in (1, 2, 3)]
            enc_t = list(terceros[0])
            guardar('A cheques terceros 2026-09-16.xlsx', enc_t, terceros)
            guardar('A Cheques terceros 2026-09-22.xlsx', list(reversed(enc_t[:-1])), terceros)
            res = tango.procesar(carpeta, 'navar', '2026-09-22')
            salida = tango.escribir_para_pegar(res, carpeta)
            wb = openpyxl.load_workbook(salida, data_only=True)
            datos = list(wb['Cartera de Cheques'].values)
            self.assertEqual(list(datos[0]), tango.ENC_CHEQUES)
            resultado = {f[3]: dict(zip(datos[0], f)) for f in datos[1:]}
            self.assertEqual(len(resultado), 6)
            for f in filas + terceros:
                r = resultado[f['Nro. de cheque']]
                self.assertEqual(r['Fecha Pago / Cobro'].date(), f['Fecha del cheque'])
                emision = r['Fecha Emision']
                self.assertEqual(emision.date() if emision else None, f.get('Fecha de emisión'))
                self.assertFalse(r['Observaciones'].startswith('REVISAR:'))
            wb.close()


if __name__ == '__main__':
    unittest.main()
