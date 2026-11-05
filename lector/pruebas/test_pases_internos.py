# -*- coding: utf-8 -*-
"""Tarea 81: la otra pata de los pases entre cuentas propias. Datos inventados."""
import datetime
import unittest

from lector import pases_internos as p

D = datetime.datetime(2026, 8, 10)
INTERNA = p.INTERNA


def fila(importe, cat, banco, fecha=D):
    return {"Tipo": "Egreso" if importe < 0 else "Ingreso", "Categoria": cat, "Importe": importe,
            "Banco / Cuenta": banco, "Fecha": fecha, "Medio de Pago": "x", "Observaciones": "obs"}


class Pases(unittest.TestCase):
    def test_credito_cargado_como_cobranza_pasa_a_interna(self):
        sale = fila(-1000.0, INTERNA, "BANCO UNO")
        entra = fila(1000.0, "Cobranza Facturas", "BANCO DOS")
        self.assertEqual(1, p.marcar([sale, entra]))
        self.assertEqual(INTERNA, entra["Categoria"])
        self.assertEqual("Ingreso", entra["Tipo"])
        self.assertIn("INTERNO", entra["Observaciones"])

    def test_debito_cargado_como_proveedor_pasa_a_interna(self):
        entra = fila(700.0, INTERNA, "BANCO UNO")
        sale = fila(-700.0, "Proveedores MP y Logist.", "BANCO DOS")
        self.assertEqual(1, p.marcar([entra, sale]))
        self.assertEqual(INTERNA, sale["Categoria"])

    def test_pase_que_ya_cancela_no_busca_nada(self):
        a, b = fila(-500.0, INTERNA, "BANCO UNO"), fila(500.0, INTERNA, "BANCO DOS", D + datetime.timedelta(days=2))
        cobro = fila(500.0, "Cobranza Facturas", "BANCO TRES")
        self.assertEqual(0, p.marcar([a, b, cobro]))
        self.assertEqual("Cobranza Facturas", cobro["Categoria"])

    def test_con_dos_candidatas_no_adivina(self):
        sale = fila(-300.0, INTERNA, "BANCO UNO")
        uno, dos = fila(300.0, "Cobranza Facturas", "BANCO DOS"), fila(300.0, "Cobranza Facturas", "BANCO TRES")
        self.assertEqual(0, p.marcar([sale, uno, dos]))
        self.assertEqual("Cobranza Facturas", uno["Categoria"])

    def test_otro_dia_misma_cuenta_u_otra_categoria_no_cuentan(self):
        sale = fila(-300.0, INTERNA, "BANCO UNO")
        otro_dia = fila(300.0, "Cobranza Facturas", "BANCO DOS", D + datetime.timedelta(days=1))
        misma = fila(300.0, "Cobranza Facturas", "BANCO UNO")
        prestamo = fila(300.0, "Prestamo", "BANCO TRES")
        self.assertEqual(0, p.marcar([sale, otro_dia, misma, prestamo]))

    def test_cada_pata_se_usa_una_sola_vez(self):
        a, b = fila(-300.0, INTERNA, "BANCO UNO"), fila(-300.0, INTERNA, "BANCO TRES")
        entra = fila(300.0, "Cobranza Facturas", "BANCO DOS")
        self.assertEqual(1, p.marcar([a, b, entra]))


if __name__ == "__main__":
    unittest.main()
