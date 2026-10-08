"""Lector del Excel de BNA+ Empresas (Nación). Todos los datos son inventados."""
import datetime as dt
import os
import tempfile
import unittest

from openpyxl import Workbook

from lector.extractos import leer_planilla_nacion


def _excel(carpeta, renglones, nombre="Movimientos Nacion 12345678901234 2026-10-07.xlsx"):
    """Imita el export: dos renglones de título y la tabla, del más nuevo al más viejo."""
    libro = Workbook()
    hoja = libro.active
    hoja.append(["Banco Nación", "[BNA + Empresas]", "", "", ""])
    hoja.append([])
    hoja.append(["Últimos movimientos", "", "", "", ""])
    hoja.append([])
    hoja.append(["Fecha", "Comprobante", "Concepto", "Monto", "Saldo"])
    for r in renglones:
        hoja.append(list(r))
    ruta = os.path.join(carpeta, nombre)
    libro.save(ruta)
    return ruta


# Saldo de ANTES de cada movimiento (como lo trae el banco): arranca en -1.000,00.
#   02/10  -100,00   (antes -1.200,00 -> después -1.300,00)
#   01/10  -500,00   (antes   -700,00 -> después -1.200,00)
#   01/10  +300,00   (antes -1.000,00 -> después   -700,00)
ANTES = [
    ("02/10/2026", "111", "DEBITO INVENTADO", "$ -100,00", "$ -1.200,00"),
    ("01/10/2026", "222", "OTRO DEBITO", "$ -500,00", "$ -700,00"),
    ("01/10/2026", "333", "CREDITO INVENTADO", "$ 300,00", "$ -1.000,00"),
]


class LectorNacion(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.dir.cleanup()

    def test_saldo_de_antes_del_movimiento(self):
        r = leer_planilla_nacion(_excel(self.dir.name, ANTES))
        self.assertEqual(r["cuenta"], "12345678901234")
        self.assertIn("saldo de antes", r["nota"])
        saldos = [m["saldo"] for m in r["movimientos"]]
        self.assertEqual(saldos, [-1300.0, -1200.0, -700.0])
        self.assertEqual([m["importe"] for m in r["movimientos"]], [-100.0, -500.0, 300.0])
        self.assertEqual(r["movimientos"][0]["fecha"], dt.date(2026, 10, 2))

    def test_saldo_de_despues_tambien_se_reconoce(self):
        despues = [
            ("02/10/2026", "111", "DEBITO", "$ -100,00", "$ -1.300,00"),
            ("01/10/2026", "222", "DEBITO", "$ -500,00", "$ -1.200,00"),
            ("01/10/2026", "333", "CREDITO", "$ 300,00", "$ -700,00"),
        ]
        r = leer_planilla_nacion(_excel(self.dir.name, despues))
        self.assertIn("saldo de después", r["nota"])
        self.assertEqual([m["saldo"] for m in r["movimientos"]], [-1300.0, -1200.0, -700.0])

    def test_cadena_que_no_cierra_no_se_lee(self):
        roto = list(ANTES)
        roto[1] = ("01/10/2026", "222", "OTRO DEBITO", "$ -555,00", "$ -700,00")
        with self.assertRaisesRegex(ValueError, "no cierra"):
            leer_planilla_nacion(_excel(self.dir.name, roto))

    def test_sin_numero_de_cuenta_en_el_nombre_no_se_lee(self):
        with self.assertRaisesRegex(ValueError, "no trae la cuenta"):
            leer_planilla_nacion(_excel(self.dir.name, ANTES, nombre="Ultimos movimientos.xlsx"))

    def test_periodo_sin_movimientos(self):
        r = leer_planilla_nacion(_excel(self.dir.name, []))
        self.assertEqual(r["movimientos"], [])


if __name__ == "__main__":
    unittest.main()
