# -*- coding: utf-8 -*-
"""Tarea 52: el tablero de siempre se rearma solo. Pruebas sin datos reales ni Drive."""
import os
import sys
import datetime
import tempfile
import unittest
from unittest import mock

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERR = os.path.join(BASE, "clientes", "navar", "herramientas")
sys.path.insert(0, BASE)
sys.path.insert(0, HERR)
import armar_tablero  # noqa: E402
import vigilante      # noqa: E402

HOY = datetime.date(2026, 10, 7)


class ArmarTablero(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.tablero = os.path.join(self.dir, "Tablero")
        os.makedirs(os.path.join(self.tablero, "fuente"))
        self.xlsx = os.path.join(self.tablero, "fuente", "NAVAR - Cash Flow 2026-10-07 0730.xlsx")
        open(self.xlsx, "wb").close()
        self.final = os.path.join(self.tablero, "finauto.html")
        with open(self.final, "w", encoding="utf-8") as f:
            f.write("TABLERO ANTERIOR")
        self.trabajo = os.path.join(self.dir, "trabajo")

    def tearDown(self):
        self.tmp.cleanup()

    def correr_falso(self, html):
        """Reemplaza los dos programas de siempre: el segundo deja `html` como tablero."""
        def falso(cmd):
            if cmd[1].endswith("finauto.py"):
                salidas = cmd[cmd.index("--salidas") + 1]
                os.makedirs(salidas, exist_ok=True)
                with open(os.path.join(salidas, "finauto.html"), "w", encoding="utf-8") as f:
                    f.write(html)
            return ""
        return mock.patch.object(armar_tablero, "_correr", side_effect=falso)

    def leer_final(self):
        with open(self.final, encoding="utf-8") as f:
            return f.read()

    def test_arma_y_reemplaza_cuando_el_tablero_esta_bien(self):
        bueno = "<html>NAVAR S.A. " + "x" * (armar_tablero.TAMANO_MINIMO + 10) + "</html>"
        with self.correr_falso(bueno) as m:
            armar_tablero.armar(self.xlsx, self.tablero, HOY, self.trabajo)
        self.assertEqual(bueno, self.leer_final())
        pasos = [os.path.basename(c.args[0][1]) for c in m.call_args_list]
        self.assertEqual(["cash_limpio.py", "finauto.py"], pasos)
        self.assertIn("--sin-memoria", m.call_args_list[1].args[0])          # la foto de visita no se toca
        self.assertIn(HOY.isoformat(), m.call_args_list[0].args[0])          # cuenta lo vencido con la fecha de hoy
        self.assertFalse(os.path.exists(self.final + ".parte"))

    def test_un_tablero_vacio_no_pisa_al_anterior(self):
        with self.correr_falso("<html>NAVAR</html>"):
            with self.assertRaisesRegex(RuntimeError, "queda el anterior"):
                armar_tablero.armar(self.xlsx, self.tablero, HOY, self.trabajo)
        self.assertEqual("TABLERO ANTERIOR", self.leer_final())

    def test_si_falla_un_paso_no_pisa_al_anterior(self):
        with mock.patch.object(armar_tablero, "_correr", side_effect=RuntimeError("cash_limpio.py falló: algo")):
            with self.assertRaises(RuntimeError):
                armar_tablero.armar(self.xlsx, self.tablero, HOY, self.trabajo)
        self.assertEqual("TABLERO ANTERIOR", self.leer_final())

    def test_sin_copia_de_la_sheet_avisa(self):
        with self.assertRaisesRegex(RuntimeError, "no encuentro la copia"):
            armar_tablero.armar(os.path.join(self.dir, "no-existe.xlsx"), self.tablero, HOY, self.trabajo)

    def test_el_vigilante_arma_con_la_copia_mas_nueva_y_una_vez_por_dia(self):
        viejo = os.path.join(self.tablero, "fuente", "NAVAR - Cash Flow 2026-10-06 0730.xlsx")
        open(viejo, "wb").close()
        os.utime(viejo, (1, 1))
        with mock.patch.object(vigilante, "DRIVE", self.dir):
            f = {x["nombre"]: x for x in vigilante.fuentes(HOY)}["tablero"]
            cmd = f["cmd"]()
        self.assertTrue(f.get("mirar_dia"))
        self.assertEqual("armar_tablero.py", os.path.basename(cmd[1]))
        self.assertEqual(self.xlsx, cmd[cmd.index("--archivo") + 1])
        self.assertEqual(HOY.isoformat(), cmd[cmd.index("--hoy") + 1])

    def test_sin_copia_el_vigilante_no_corre_el_tablero(self):
        os.remove(self.xlsx)
        with mock.patch.object(vigilante, "DRIVE", self.dir):
            f = {x["nombre"]: x for x in vigilante.fuentes(HOY)}["tablero"]
        self.assertEqual([], f["archivos"])


if __name__ == "__main__":
    unittest.main()
