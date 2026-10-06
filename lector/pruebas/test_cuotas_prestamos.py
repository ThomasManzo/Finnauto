"""Datos inventados: la tabla de cuotas reales, el desglose para un débito y el cronograma de la deuda."""
import datetime as dt
import tempfile
import unittest
from pathlib import Path

from lector import cuotas_prestamos as cp
from lector import deuda_bancaria as db

D = dt.date

TEXTO_GALICIA = """NAVAR SOCIEDAD ANONIMA (CUIT/DNI: 30999999995)
Préstamo Nro: 111222333
Importe: $ 300.00
Cuota Estado Vencimiento Monto total Capital Interés nominal IVA interés nominal IVA percepción Otros gastos
1 Abonada 2026-08-31 $ 125.00 $ 100.00 $ 20.00 $ 4.20 $ 0.80 $ 0.00
2 A Vencer 2026-09-30 $ 118.75 $ 100.00 $ 15.00 $ 3.15 $ 0.60 $ 0.00
3 A Vencer 2026-10-30 $ 112.50 $ 100.00 $ 10.00 $ 2.10 $ 0.40 $ 0.00
"""


def cuota(banco, linea, n, vto, total, capital=0.0, estado="A vencer", pago=None, punitorios=0.0, otros=0.0):
    return {"banco": banco, "linea": linea, "prestamo": "999", "cuota": n, "vto": vto, "estado": estado,
            "pago": pago, "capital": capital, "interes": round(total - capital - punitorios - otros, 2), "iva": 0.0,
            "percepcion": 0.0, "otros": otros, "punitorios": punitorios, "total": total, "fuente": "inventada"}


class Tabla(unittest.TestCase):
    def test_galicia_desde_el_texto_del_pdf(self):
        cs = cp.leer_texto_galicia(TEXTO_GALICIA, "Préstamo Nro. 111222333")
        self.assertEqual([c["cuota"] for c in cs], [1, 2, 3])
        self.assertEqual([c["estado"] for c in cs], ["Pagada", "A vencer", "A vencer"])
        self.assertEqual((cs[1]["capital"], cs[1]["interes"], cs[1]["iva"], cs[1]["percepcion"], cs[1]["total"]),
                         (100.0, 15.0, 3.15, 0.6, 118.75))
        self.assertEqual(cs[0]["prestamo"], "111222333")

    def test_galicia_que_no_suma_frena(self):
        with self.assertRaises(SystemExit):
            cp.leer_texto_galicia(TEXTO_GALICIA.replace("$ 118.75", "$ 999.00"), "X")

    def test_escribir_leer_y_reemplazar_un_prestamo(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = str(Path(d) / cp.ARCHIVO)
            otra = cuota("NACION", "Préstamo B", 1, D(2026, 10, 20), 50.0, 10.0)
            cs = cp.reemplazar_prestamo([otra], cp.leer_texto_galicia(TEXTO_GALICIA, "Préstamo A"))
            cp.escribir(cs, ruta)
            leidas = cp.leer(ruta)
            self.assertEqual(len(leidas), 4)
            # un PDF nuevo de Galicia reemplaza solo ese préstamo
            nuevas = cp.reemplazar_prestamo(leidas, cp.leer_texto_galicia(TEXTO_GALICIA.split("3 A Vencer")[0], "Préstamo A"))
            self.assertEqual(sorted((c["linea"], c["cuota"]) for c in nuevas),
                             [("Préstamo A", 1), ("Préstamo A", 2), ("Préstamo B", 1)])
            self.assertEqual(cp.leer(str(Path(d) / "no existe.xlsx")), [])


class Desglose(unittest.TestCase):
    def setUp(self):
        self.cs = [cuota("NACION", "Reprog", 1, D(2026, 7, 13), 2186.5, 0.0, "Pagada", D(2026, 8, 4), punitorios=48.5),
                   cuota("NACION", "Reprog", 2, D(2026, 8, 20), 1750.0),
                   cuota("GALICIA", "Prest", 6, D(2026, 9, 30), 2404.0, 1750.0)]

    def test_cuota_pagada_tarde_por_la_fecha_de_pago(self):
        c = cp.para_debito(self.cs, "NACION", D(2026, 8, 4), -2186.5)
        self.assertEqual(c["cuota"], 1)
        self.assertIn("punitorios $48,50", cp.desglose(c))

    def test_cuota_por_importe_cerca_del_vencimiento(self):
        self.assertEqual(cp.para_debito(self.cs, "GALICIA", D(2026, 9, 30), -2404.0)["cuota"], 6)
        self.assertEqual(cp.para_debito(self.cs, "NACION", D(2026, 9, 14), -1750.0)["cuota"], 2)   # pagada 25 días tarde

    def test_sin_cuota_o_de_otro_banco_o_lejos(self):
        self.assertIsNone(cp.para_debito(self.cs, "MACRO", D(2026, 9, 30), -2404.0))
        self.assertIsNone(cp.para_debito(self.cs, "GALICIA", D(2026, 9, 30), -999.0))
        self.assertIsNone(cp.para_debito(self.cs, "GALICIA", D(2027, 3, 30), -2404.0))

    def test_dos_posibles_no_muestra_ninguna(self):
        cs = self.cs + [cuota("GALICIA", "Otro", 1, D(2026, 10, 2), 2404.0)]
        self.assertIsNone(cp.para_debito(cs, "GALICIA", D(2026, 9, 30), -2404.0))


class CronogramaReal(unittest.TestCase):
    def mapa(self):
        p = {"banco": "Banco Inventado", "banco_corto": "GALICIA", "producto": "Préstamo Nro. 111222333",
             "tipo": "prestamo", "valor_original": 300.0, "alta": D(2026, 7, 30), "cuotas": 3, "garantia": None,
             "tna": 0.3, "saldo": 200.0, "valor_cuota": 125.0, "situacion": 1, "obs": "AL DÍA."}
        p.update(db._leer_observaciones(p["obs"]))
        return {"titulo": "DEUDA FINANCIERA al 6/10/2026", "productos": [p], "archivo": "mapa.xlsx"}

    def test_usa_la_tabla_en_lugar_de_estimar(self):
        reales = cp.leer_texto_galicia(TEXTO_GALICIA, "Préstamo Nro. 111222333", "PDF inventado")
        res = db.armar(self.mapa(), D(2026, 10, 6), cuotas_reales=reales)
        cuotas = res["cuotas"]
        self.assertEqual([c["Nro Cuota"] for c in cuotas], [2, 3])              # la pagada no va
        self.assertEqual((cuotas[1]["Importe Capital"], cuotas[1]["Importe Interes"]), (100.0, 12.5))
        self.assertIn("tabla del banco", cuotas[1]["Observaciones"])
        self.assertIn("VENCIDA", cuotas[0]["Observaciones"])                     # venció el 30/09
        self.assertTrue(any("cuotas de la tabla del banco" in a for a in res["avisos"]))

    def test_sin_tabla_sigue_estimando(self):
        res = db.armar(self.mapa(), D(2026, 10, 6))
        self.assertFalse(any("tabla del banco" in c["Observaciones"] for c in res["cuotas"]))


if __name__ == "__main__":
    unittest.main()
