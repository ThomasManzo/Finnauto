"""Saldo de la pantalla del banco: una cuenta sin movimientos no parece atrasada (tarea 59). Datos inventados."""
import datetime as dt
import json
import os
import tempfile
import unittest

from lector.extractos import completar_con_pantalla, saldos_de_pantalla

CUENTA = "0001234-5 678-9"


def _json(carpeta, fecha, saldo, cuenta=CUENTA):
    ruta = os.path.join(carpeta, "_SALDOS_Banco_%s.json" % fecha[8:10])
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump({"banco": "Banco", "fecha": fecha, "empresas": [
            {"empresa": "EMPRESA INVENTADA", "cuenta": cuenta, "saldo_actual": saldo}]}, f)


class SaldoDePantalla(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.dir.cleanup()

    def test_toma_el_json_mas_nuevo(self):
        _json(self.dir.name, "2026-10-06", -100.0)
        _json(self.dir.name, "2026-10-08", -100.0)
        self.assertEqual(saldos_de_pantalla(self.dir.name), [(CUENTA, dt.date(2026, 10, 8), -100.0)])

    def test_carpeta_sin_bot(self):
        self.assertEqual(saldos_de_pantalla(self.dir.name), [])
        self.assertEqual(saldos_de_pantalla(None), [])

    def test_sin_movimientos_el_saldo_vale_hasta_el_dia_anterior_a_la_bajada(self):
        por_dia = {(CUENTA, dt.date(2026, 10, 1)): -100.0}
        obs, avisos = completar_con_pantalla(por_dia, [("000123456789", dt.date(2026, 10, 8), -100.0)])
        self.assertEqual(por_dia[(CUENTA, dt.date(2026, 10, 7))], -100.0)
        self.assertIn("sin movimientos desde el 01/10", obs[(CUENTA, dt.date(2026, 10, 7))])
        self.assertEqual(avisos, [])

    def test_si_no_coincide_no_se_inventa_un_saldo(self):
        por_dia = {(CUENTA, dt.date(2026, 10, 1)): -100.0}
        obs, avisos = completar_con_pantalla(por_dia, [(CUENTA, dt.date(2026, 10, 8), -150.0)])
        self.assertEqual(list(por_dia), [(CUENTA, dt.date(2026, 10, 1))])
        self.assertEqual(obs, {})
        self.assertIn("puede faltar algún movimiento", avisos[0])

    def test_si_el_extracto_ya_llega_a_ese_dia_no_hace_nada(self):
        por_dia = {(CUENTA, dt.date(2026, 10, 7)): -100.0}
        obs, avisos = completar_con_pantalla(por_dia, [(CUENTA, dt.date(2026, 10, 8), -999.0)])
        self.assertEqual(len(por_dia), 1)
        self.assertEqual((obs, avisos), ({}, []))

    def test_otra_cuenta_no_se_mezcla(self):
        por_dia = {(CUENTA, dt.date(2026, 10, 1)): -100.0}
        completar_con_pantalla(por_dia, [("999", dt.date(2026, 10, 8), -100.0)])
        self.assertEqual(len(por_dia), 1)


if __name__ == "__main__":
    unittest.main()
