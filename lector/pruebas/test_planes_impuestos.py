"""Tarea 91. Datos inventados: planes de ARCA y de Rentas proyectados desde sus solapas."""
import datetime as dt
import tempfile
import unittest
from pathlib import Path

import openpyxl
from lector import deuda_impositiva as di


class PlanesImpuestos(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.ruta = str(Path(tmp.name) / "impuestos.xlsx")
        self.hoy = dt.date(2026, 11, 12)

    def armar_excel(self, con_planes=True):
        wb = openpyxl.Workbook()
        v = wb.active
        v.title = "Vencimientos"
        v.append(["IMPUESTO", "CONCEPTO", "CAPITAL", "INTERES", "IMPORTE A PAGAR", "FECHA VENCIMIENTO", "ESTADO", "CANCELADO", "COLUMNA1"])
        v.append(["IVA", "DDJJ EJEMPLO", 100, 0, 100, dt.datetime(2026, 12, 20), "", "Pendiente", ""])
        v.append(["PLANES DE PAGOS ARCA", "PLANES ARCA - TODOS", 30, 0, 30, dt.datetime(2026, 11, 16), "", "Pendiente", ""])
        v.append(["PLANES DE PAGO ARCA", "CUOTA VIEJA IMPAGA", 7, 0, 7, dt.datetime(2026, 10, 16), "", "Pendiente", ""])
        v.append(["PLAN DE PAGO DGR CTES", "AGENTES EJEMPLO", 5, 0, 5, dt.datetime(2026, 12, 10), "", "Pendiente", ""])
        if con_planes:
            a = wb.create_sheet("PLANES VIGENTE ARCA A NOV")
            a.append(["PLANES DE PAGO ARCA", None, "CUOTAS", "1ER VTO", "2DO VTO", "FECHA INGRESO", "2DO VTO"])
            a.append(["PLANES DE PAGO ARCA", "PLAN UNO", "2 de 4", 10, 11, dt.datetime(2026, 11, 16), dt.datetime(2026, 11, 26)])
            a.append(["PLANES DE PAGO ARCA", "PLAN NUEVO", "3", 20, 21, dt.datetime(2026, 11, 16), dt.datetime(2026, 11, 26)])
            a.append([None, dt.datetime(2026, 11, 16), 30, "total del mes"])
            r = wb.create_sheet("PLAN DE PAGO RENTAS")
            r.append(["PLAN DGR CTES", None, None])
            r.append(["ANTICIPO", 50, "PAGADO"])
            r.append(["CUOTA 1", 5, dt.datetime(2026, 12, 10)])
            r.append(["CUOTA 2", 5, dt.datetime(2027, 1, 11)])
        wb.save(self.ruta)

    def test_proyecta_planes_y_saca_el_renglon_del_mes(self):
        self.armar_excel()
        res = di.armar(di.leer(self.ruta), self.hoy)
        filas = res["filas"]
        arca = [f for f in filas if f["Impuesto"] == "PLANES DE PAGO ARCA"]
        # PLAN UNO: cuotas 2, 3 y 4; PLAN NUEVO: 1 a 3; más la cuota vieja impaga de octubre.
        self.assertEqual(len(arca), 7)
        uno = [f for f in arca if f["Periodo"] == "PLAN UNO"]
        self.assertEqual([f["Fecha Vencimiento"] for f in uno],
                         [dt.date(2026, 11, 16), dt.date(2026, 12, 16), dt.date(2027, 1, 16)])
        self.assertEqual([f["Nro Cuota (si aplica)"] for f in uno], ["2 de 4", "3 de 4", "4 de 4"])
        self.assertTrue(all(f["Debito Automatico"] == "Si" for f in arca))
        self.assertIn("CUOTA VIEJA IMPAGA", [f["Periodo"] for f in arca])
        self.assertNotIn("PLANES ARCA - TODOS", [f["Periodo"] for f in filas])
        # Rentas: las dos cuotas del plan, sin el renglón suelto de Vencimientos ni el anticipo pagado.
        rentas = [f for f in filas if f["Impuesto"] == "PLAN DE PAGO DGR CTES"]
        self.assertEqual([(f["Fecha Vencimiento"], f["Importe"]) for f in rentas],
                         [(dt.date(2026, 12, 10), 5), (dt.date(2027, 1, 11), 5)])
        # El plan que dice solo "3" se toma como 1 de 3 y se avisa.
        self.assertTrue(any("PLAN NUEVO" in a and "confirmar" in a for a in res["avisos"]))
        nuevo = [f for f in arca if f["Periodo"] == "PLAN NUEVO"]
        self.assertEqual(nuevo[0]["Nro Cuota (si aplica)"], "1 de 3")
        self.assertIn("SUPUESTO", nuevo[0]["Observaciones"])

    def test_sin_solapas_de_planes_queda_como_antes(self):
        self.armar_excel(con_planes=False)
        filas = di.armar(di.leer(self.ruta), self.hoy)["filas"]
        self.assertEqual(sorted(f["Periodo"] for f in filas),
                         ["AGENTES EJEMPLO", "CUOTA VIEJA IMPAGA", "DDJJ EJEMPLO", "PLANES ARCA - TODOS"])

    def test_fin_de_mes(self):
        self.assertEqual(di._sumar_meses(dt.date(2026, 1, 31), 1), dt.date(2026, 2, 28))
        self.assertEqual(di._sumar_meses(dt.date(2026, 11, 16), 3), dt.date(2027, 2, 16))


if __name__ == "__main__":
    unittest.main()
