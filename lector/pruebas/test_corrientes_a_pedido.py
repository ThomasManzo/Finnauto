# -*- coding: utf-8 -*-
"""Corrientes, formato "RESUMEN A PEDIDO" (tarea 38). Textos inventados con la forma real del PDF."""
import datetime
import unittest
from unittest import mock

from lector import extractos

CABECERA = ("RESUMEN\nPeriodo : al15/09/26 30/09/26\n"
            "130559 30/09/26Número de cuenta: Estado de Cuenta al:\n"
            "Cta Cte Empresa (PF y PJ) 130559/1 1,510.00 500.00PESOS -1,000,510.00\n"
            "FECHA CONCEPTO REFERENCIA DEBITOS CREDITOS SALDOCHEQUE\n")
PIE = "Total ret. Imp. Ley 25.413 s/débitos: 15/09/26 al 30/09/26 30.18del\n"


def leer(texto):
    with mock.patch.object(extractos, "_texto_pdf", return_value=texto):
        return extractos.leer_pdf_corrientes("Res_130559 prueba.pdf")


class PruebaCorrientesAPedido(unittest.TestCase):
    def test_lee_debitos_credito_y_concepto_partido(self):
        r = leer(CABECERA +
                 "SALDO INICIAL -1,000,000.00\n"
                 "15/09/26 10.00Imp. ley 25413 s/debitos -1,000,010.00\n"
                 "15/09/26 500.00Acred. transferencia -999,510.00\n"
                 "DENOMINACION CTA29/09/26 1,000.00Com.x servicios varios -1,000,510.00\n"
                 "SALDO FINAL -1,000,510.00\n" + PIE)
        self.assertEqual(r["cuenta"], "130559")
        movs = r["movimientos"]
        self.assertEqual([m["importe"] for m in movs], [-10.0, 500.0, -1000.0])
        self.assertEqual([m["saldo"] for m in movs], [-1000010.0, -999510.0, -1000510.0])
        self.assertEqual(movs[0]["fecha"], datetime.date(2026, 9, 15))
        self.assertEqual(movs[2]["concepto"], "Com.x servicios varios DENOMINACION CTA")
        self.assertIn("cadena de saldos OK", r["nota"])
        # Las fechas del pie (totales de impuestos) no son movimientos.
        self.assertEqual(len(movs), 3)

    def test_cadena_que_no_cierra_frena(self):
        with self.assertRaisesRegex(ValueError, "no cierra"):
            leer(CABECERA +
                 "SALDO INICIAL -1,000,000.00\n"
                 "15/09/26 10.00Imp. ley 25413 s/debitos -1,000,020.00\n"
                 "SALDO FINAL -1,000,020.00\n")

    def test_saldo_final_distinto_frena(self):
        with self.assertRaisesRegex(ValueError, "SALDO FINAL"):
            leer(CABECERA +
                 "SALDO INICIAL -1,000,000.00\n"
                 "15/09/26 10.00Imp. ley 25413 s/debitos -1,000,010.00\n"
                 "SALDO FINAL -1,000,999.00\n")

    def test_formato_viejo_sin_cambios(self):
        r = leer("130559 NAVAR SA\n"
                 "16/06/26 Acred. Ch.Camara 1532532 Cr 1,000.00 -40,000.00\n"
                 "17/06/26 Imp. ley 25413 s/debitos 0 Db 6.00 -40,006.00\n")
        self.assertEqual(r["cuenta"], "130559")
        self.assertEqual([m["importe"] for m in r["movimientos"]], [1000.0, -6.0])
        self.assertEqual(r["movimientos"][0]["ref"], "1532532")
        self.assertNotIn("nota", r)


if __name__ == "__main__":
    unittest.main()
