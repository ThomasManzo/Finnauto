"""Lista privada de proveedores: pruebas inventadas, sin Drive ni datos del cliente."""
import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import openpyxl
from lector import tango
from clientes.navar.herramientas import principales20_pdf

HOY = dt.date(2030, 2, 10)


class ListaAdministracion(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.carpeta = Path(self.tmp.name)
        self.ruta_lista = self.carpeta / "lista.json"
        self.datos = {"empresa": "A", "fecha": "2030-01-31",
                      "real": [{"codigo": "R", "nombre": "Real Inventado", "ajuste": -150}],
                      "no_real": [{"codigo": "N", "nombre": "No Real Inventado", "saldo": 700},
                                  {"codigo": "S", "nombre": "Sin Facturas Inventado", "saldo": 300}]}
        self.guardar_lista()

    def guardar_lista(self):
        self.ruta_lista.write_text(json.dumps(self.datos))

    def export(self, empresa="A"):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Cód. proveedor", "Razón social", "Fecha de emisión", "Fecha de vencimiento",
                   "Total al vencimiento", "Total pendiente", "Nro. comprobante"])
        for cod, nro, emision, venc, total, pendiente in [
            ("R", "1", "2028-01-01", "2028-02-01", 120, 100),
            ("R", "2", "2030-01-31", "2030-02-05", 200, 200),
            ("N", "3", "2030-01-30", "2030-02-05", 500, 500),
            ("X", "4", "2030-01-31", "2030-02-05", 400, 400),
            ("N", "5", "2030-02-01", "2030-02-15", 50, 50),
            ("X", "6", "2030-02-01", "2030-02-15", 60, 60),
            ("R", "7", "2030-01-31", "2030-02-05", 1, 1),
            ("R", "8", "2030-02-01", "2030-02-20", 80, 80),
        ]:
            ws.append([cod, cod + " Inventado", dt.date.fromisoformat(emision),
                       dt.date.fromisoformat(venc), total, pendiente, nro])
        wb.save(self.carpeta / (empresa + " pagos.xlsx"))
        wb.close()

    def procesar(self, ruta=True):
        return tango.procesar(str(self.carpeta), "navar", HOY,
                              str(self.ruta_lista) if ruta is True else ruta)

    def test_reglas_y_ajuste_repartido(self):
        self.export()
        self.export("AA")
        res = self.procesar()
        filas = res["listas"]["pagar"]
        a = {f["Nro Factura / OC"]: f for f in filas if f["Empresa"] == "A"
             and f["Nro Factura / OC"] != "LISTA ADMINISTRACION"}
        self.assertEqual(set(a), {"1", "2", "4", "5", "6", "8"})
        self.assertEqual([a[n]["Pagado"] for n in ("1", "2")], [120, 50])
        self.assertEqual([a[n]["Saldo Pendiente"] for n in ("1", "2")], [0, 150])
        for n in ("1", "2", "5", "6", "8"):
            self.assertTrue(a[n]["Observaciones"].startswith("Tango Live"))
        self.assertTrue(a["4"]["Observaciones"].startswith("REVISAR: fuera de la lista"))
        sinteticas = [f for f in filas if f["Nro Factura / OC"] == "LISTA ADMINISTRACION"]
        self.assertEqual(len(sinteticas), 2)
        self.assertEqual(sum(f["Saldo Pendiente"] for f in sinteticas), 1000)
        for f in sinteticas:
            self.assertEqual(f["Fecha Emision"], dt.date(2030, 1, 31))
            self.assertEqual(f["Fecha Vencimiento"], f["Fecha Emision"])
            self.assertEqual(f["Pagado"], 0)
            self.assertIn("REVISAR: deuda no real · Tango Live", f["Observaciones"])
        aa = [f for f in filas if f["Empresa"] == "AA"]
        sin_lista = self.procesar(None)["listas"]["pagar"]
        # Los ID se renumeran para toda la lista; los datos de AA quedan iguales.
        sin_id = lambda f: {k: v for k, v in f.items() if k != "ID"}
        self.assertEqual([sin_id(f) for f in aa],
                         [sin_id(f) for f in sin_lista if f["Empresa"] == "AA"])
        self.assertTrue(aa[0]["Observaciones"].startswith("REVISAR: deuda vieja"))
        self.assertEqual(res["descartes"][("A", "pagos")]["residuo de $1 o menos"], [1, 1])
        texto = tango.resumen(res, "inventado.xlsx")
        for regla in res["estadisticas_lista"]:
            self.assertIn(regla, texto)
        self.assertIn("Ajuste negativo aplicado: 2", texto)

    def test_ajustes_excesivo_y_positivo(self):
        self.export()
        for ajuste, esperados in [(-1000, [0, 0]), (45.25, [100, 245.25])]:
            self.datos["real"][0]["ajuste"] = ajuste
            self.guardar_lista()
            res = self.procesar()
            a = {f["Nro Factura / OC"]: f for f in res["listas"]["pagar"]}
            self.assertEqual([a[n]["Saldo Pendiente"] for n in ("1", "2")], esperados)
            self.assertEqual(a["8"]["Saldo Pendiente"], 80)
            self.assertEqual(a["4"]["Saldo Pendiente"], 400)
            if ajuste < 0:
                self.assertEqual(res["estadisticas_lista"]["Ajuste negativo sobrante descartado"], [1, 700])
            else:
                self.assertEqual(a["2"]["Importe Total"], 245.25)
                self.assertEqual(a["2"]["Pagado"], 0)

    def test_sin_export_igual_hay_no_reales(self):
        res = self.procesar()
        self.assertEqual(len(res["listas"]["pagar"]), 2)

    def test_ausente_rota_e_invalida_no_cortan(self):
        self.export()
        base = self.procesar(None)
        for contenido in ("{", '{"empresa": "A"}', json.dumps({**self.datos, "empresa": "AA"}),
                          json.dumps({**self.datos, "fecha": "no es fecha"}),
                          json.dumps({**self.datos, "real": [{"codigo": "R", "nombre": "Inventado", "ajuste": float("nan")}]})):
            self.ruta_lista.write_text(contenido)
            res = self.procesar()
            self.assertEqual(res["listas"], base["listas"])
            self.assertIn("AVISO:", tango.resumen(res, "inventado.xlsx"))
        self.ruta_lista.unlink()
        self.assertEqual(self.procesar()["listas"], base["listas"])
        self.assertIn("AVISO:", tango.resumen(base, "inventado.xlsx"))

    def test_pdf_excluye_solo_las_dos_marcas(self):
        wb = openpyxl.Workbook()
        wb.remove(wb.active)
        for nombre, quien in (("Cuentas a Pagar", "Proveedor"), ("Cuentas a Cobrar", "Cliente")):
            ws = wb.create_sheet(nombre)
            ws.append([quien, "Empresa", "Saldo Pendiente", "Fecha Vencimiento", "Observaciones"])
            for obs in ("REVISAR: deuda no real · Tango Live", "REVISAR: fuera de la lista de la administración",
                        "REVISAR: deuda vieja", "Tango Live"):
                ws.append(["Inventado", "A", 100, HOY - dt.timedelta(days=100), obs])
        ruta = self.carpeta / "sheet.xlsx"
        wb.save(ruta)
        wb.close()
        bloques, _ = principales20_pdf.leer(ruta, HOY)
        self.assertEqual(bloques[0]["total"], 400)
        self.assertEqual(bloques[2]["total"], 200)
        self.assertEqual(bloques[2]["mas_90"], 200)


if __name__ == "__main__":
    unittest.main()
