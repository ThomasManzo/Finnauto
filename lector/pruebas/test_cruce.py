"""Ejemplos inventados: cada regla del cruce banco ↔ Tango y la cuenta de control."""
import datetime as dt
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import openpyxl
from lector import cruce as cz

D = dt.datetime
CFG = {
    "empresa": "A", "cuit_propio": "30-99999999-5",
    "cuentas": {"GALICIA 111": 5, "MACRO 222": 25, "BBVA 333/1": 89, "BBVA 333/2": 89},
    "dias_antes": 3, "dias_despues": 5, "tolerancia": 1,
    "categorias_gastos": ["Impuestos", "Gastos Bancarios"],
    "categorias_deposito": ["Cheques", "Descuento de Cheques"],
    "comprobantes_deposito": ["BDM", "BDG"],
    "intereses_descuento": {"todas": ["INTERES"], "alguna": ["VTA", "VALORES"]},
    "cuentas_efectivo": ["CAJA"], "cuenta_cheques_terceros": "VALORES A DEPOSITAR",
    "comprobantes_cobro": ["REC"], "comprobantes_pago": ["O/P", "OPF"],
}
ENC_MOV = ["ID", "Fecha", "Empresa", "Tipo", "Categoria", "Concepto / Detalle", "Importe", "Medio de Pago",
           "Banco / Cuenta", "Origen", "Estado", "Referencia", "Semana (lunes)", "Observaciones"]
ENC_TANGO = ["Banco", "Cód. comprobante", "Comprobante", "Nro. interno", "Cód. cuenta", "Desc. contable",
             "Debe (cte) (renglón)", "Haber (cte) (renglón)", "Total comp. (cte)", "CUIT cliente (encab.)",
             "CUIT proveedor (encab.)", "Razón social (encab.)", "Proveedor (encab.)", "Leyenda", "Fecha de emisión"]
CUIT_A = "20-11111111-2"      # CUITs inventados con dígito verificador válido
CUIT_B = "27-22222222-8"


class _Base(unittest.TestCase):
    """Arma los dos Excel inventados y corre el cruce. No tiene pruebas propias."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.mov, self.tg, self.n = [], [], 0

    # ---- armado de los dos Excel inventados
    def banco(self, fecha, cuenta, importe, concepto="MOV", categoria="Otros", origen="Extracto X", obs=""):
        self.mov.append([len(self.mov) + 1, fecha, "A", "", categoria, concepto, importe, "", cuenta, origen,
                         "Real", None, None, obs])

    def tango(self, fecha, tipo, cod, importe, cuenta="BANCO", cuit="", nombre="", leyenda="", interno=None,
              banco="X"):
        self.n += 1
        debe, haber = (importe, 0) if importe >= 0 else (0, -importe)
        self.tg.append([banco if cod in (5, 25, 89, 106) else None, tipo, " %010d/0" % self.n, interno or self.n,
                        cod, cuenta, debe, haber, abs(importe), cuit if tipo == "REC" else None,
                        cuit if tipo != "REC" else None, nombre if tipo == "REC" else None,
                        nombre if tipo != "REC" else None, leyenda, fecha])

    def correr(self, mes="2026-08", parchar=True):
        sheet, tango = self.base / "sheet.xlsx", self.base / "tango.xlsx"
        wb = openpyxl.Workbook()
        wb.active.title = "Cash"
        ws = wb.create_sheet("Movimientos")
        ws.append(ENC_MOV)
        for f in self.mov:
            ws.append(f)
        wb.save(sheet)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Detalle de comprobantes"
        ws.append(ENC_TANGO)
        for f in self.tg:
            ws.append(f)
        ws.append([None] * len(ENC_TANGO))           # la fila casi vacía del final del export
        wb.save(tango)
        def correr():
            return cz.correr("prueba", mes, str(sheet), str(tango), str(self.base / "salidas"),
                             hoy=dt.date(2026, 9, 28))
        if parchar:
            with patch.object(cz, "cargar_config", return_value=cz_config()):
                inf, md = correr()
        else:
            inf, md = correr()
        self.assertTrue(inf["control_ok"], md)
        return inf

    @staticmethod
    def regla_de(inf, importe):
        for p in inf["pares"]:
            if any(abs(b["c"] - round(importe * 100)) <= 1 for b in p["banco"]):
                return p["regla"]
        return None


class Cruce(_Base):
    def test_exacto_banco_despues_y_antes(self):
        self.banco(D(2026, 8, 5), "GALICIA 111", 1000.0)          # 2 días después de Tango
        self.tango(D(2026, 8, 3), "REC", 5, 1000.0)
        self.banco(D(2026, 8, 9), "GALICIA 111", -2500.5)         # 1 día antes que Tango
        self.tango(D(2026, 8, 10), "O/P", 5, -2500.5)
        inf = self.correr()
        self.assertEqual(self.regla_de(inf, 1000), "exacto")
        self.assertEqual(self.regla_de(inf, -2500.5), "exacto")
        self.assertEqual(inf["solo_banco"], [])
        self.assertEqual(inf["solo_tango"], [])

    def test_fecha_corrida(self):
        self.banco(D(2026, 8, 24), "MACRO 222", -2983.0, "DEBITO PRESTAMOS", "Prestamo")
        self.tango(D(2026, 9, 1), "FPR", 25, -2983.0)               # 8 días después: fuera de la ventana
        inf = self.correr()
        self.assertEqual(self.regla_de(inf, -2983), "fecha corrida")

    def test_fecha_corrida_con_competencia_no_empareja(self):
        self.banco(D(2026, 8, 24), "MACRO 222", -500.0, "DEBITO", "Prestamo")
        self.banco(D(2026, 8, 20), "MACRO 222", -500.0, "DEBITO", "Prestamo")
        self.tango(D(2026, 9, 2), "FPR", 25, -500.0)
        inf = self.correr()
        self.assertEqual(inf["pares"], [])

    def test_muy_lejos_no_empareja_y_deja_pista(self):
        self.banco(D(2026, 8, 30), "GALICIA 111", -700.0, categoria="Proveedores")
        self.tango(D(2026, 8, 10), "O/P", 5, -700.0)                # 20 días antes: ni corrida
        inf = self.correr()
        self.assertEqual(len(inf["solo_banco"]), 1)
        self.assertIn("mismo importe", inf["solo_banco"][0]["pista"])
        self.assertEqual(inf["solo_tango"][0]["estado"], "no aparece en el banco: revisar")

    def test_desempate_por_cuit(self):
        self.banco(D(2026, 8, 12), "MACRO 222", -500.0, "TRANSF 27222222228 VAR")
        self.banco(D(2026, 8, 12), "MACRO 222", -500.0, "TRANSF 20111111112 VAR")
        self.tango(D(2026, 8, 12), "O/P", 25, -500.0, cuit=CUIT_A, nombre="PROVEEDOR A")
        self.tango(D(2026, 8, 12), "O/P", 25, -500.0, cuit=CUIT_B, nombre="PROVEEDOR B")
        inf = self.correr()
        for p in inf["pares"]:
            self.assertEqual(p["banco"][0]["cuit"], p["tango"][0]["cuit"])

    def test_mismo_cuit_una_op_contra_dos_transferencias(self):
        self.banco(D(2026, 8, 14), "MACRO 222", -300.0, "TRANSF 20111111112 VAR")
        self.banco(D(2026, 8, 15), "MACRO 222", -200.0, "TRANSF 20111111112 VAR")
        self.tango(D(2026, 8, 14), "O/P", 25, -500.0, cuit=CUIT_A)
        inf = self.correr()
        self.assertEqual(self.regla_de(inf, -300), "mismo CUIT")
        self.assertEqual(len(inf["pares"][0]["banco"]), 2)

    def test_descuento_neto_de_intereses(self):
        self.banco(D(2026, 8, 6), "MACRO 222", 9600.0, "033000111", "Descuento de Cheques")
        self.banco(D(2026, 8, 6), "MACRO 222", 1900.0, "033000222", "Descuento de Cheques")
        self.tango(D(2026, 8, 6), "BDM", 25, 10000.0)
        self.tango(D(2026, 8, 6), "BDM", 25, 2000.0)
        self.tango(D(2026, 8, 6), "FPR", 25, -400.0, leyenda="INTERESES VTA.CH.")
        self.tango(D(2026, 8, 6), "FPR", 25, -100.0, leyenda="INTERESES VTA VALORES MACRO")
        inf = self.correr()
        self.assertEqual(self.regla_de(inf, 9600), "descuento neto")
        self.assertEqual(self.regla_de(inf, 1900), "descuento neto")
        self.assertEqual(inf["solo_tango"], [])

    def test_bloque_del_dia(self):
        for v in (100.0, 250.0, 650.0):
            self.banco(D(2026, 8, 26), "GALICIA 111", v, "CREDITO DESCUENTO DOCUMENTO", "Descuento de Cheques")
        self.tango(D(2026, 8, 26), "BDG", 5, 1000.0)
        inf = self.correr()
        self.assertEqual(self.regla_de(inf, 100), "bloque del día")
        self.assertEqual(len(inf["pares"][0]["banco"]), 3)

    def test_boleta_acreditada_al_dia_siguiente_en_dos_renglones(self):
        self.banco(D(2026, 8, 12), "MACRO 222", 300.0, "ACREDITACION CHEQUE", "Cheques")
        self.banco(D(2026, 8, 12), "MACRO 222", 700.0, "ACREDITACION CHEQUE", "Cheques")
        self.banco(D(2026, 8, 12), "MACRO 222", 55.0, "ACREDITACION CHEQUE", "Cheques")   # de otra boleta
        self.banco(D(2026, 8, 12), "MACRO 222", 80.0, "ACREDITACION CHEQUE", "Cheques")   # sin boleta: el bloque no da
        self.tango(D(2026, 8, 11), "BDM", 25, 1000.0)
        self.tango(D(2026, 8, 13), "BDM", 25, 55.0)
        inf = self.correr()
        self.assertEqual(self.regla_de(inf, 300), "agrupado")
        self.assertEqual(self.regla_de(inf, 55), "exacto")
        self.assertEqual([b["c"] for b in inf["solo_banco"]], [8000])

    def test_ambiguo_va_a_revisar(self):
        # 100+200 y 150+150 dan 300: dos combinaciones posibles → no se empareja
        for v in (100.0, 200.0, 150.0, 150.0):
            self.banco(D(2026, 8, 18), "MACRO 222", -v, "PAGO", "Proveedores")
        self.tango(D(2026, 8, 18), "OPF", 25, -300.0)
        inf = self.correr()
        self.assertEqual(inf["pares"], [])
        self.assertTrue(any(r["lado"] == "Tango" and "más de una combinación" in r["motivo"] for r in inf["revisar"]))
        self.assertEqual(len(inf["solo_tango"]), 0)

    def test_transferencia_entre_bancos_propios(self):
        self.banco(D(2026, 8, 10), "MACRO 222", -25000.0, "TRANSF 30999999995 VAR", "Transferencia Interna")
        self.banco(D(2026, 8, 10), "GALICIA 111", 25000.0, "TRANSFERENCIA DE CUENTA PROPIA", "Transferencia Interna")
        self.tango(D(2026, 8, 10), "EXT", 25, -25000.0, interno=900)
        self.tango(D(2026, 8, 10), "EXT", 5, 25000.0, interno=900)
        inf = self.correr()
        self.assertEqual(len(inf["pares"]), 2)
        self.assertEqual({p["regla"] for p in inf["pares"]}, {"exacto"})

    def test_internas_entre_las_dos_bbva(self):
        self.banco(D(2026, 8, 6), "BBVA 333/2", 4000.0, "OPERACION DE RECAUDO", "Cobranza Facturas")
        self.banco(D(2026, 8, 6), "BBVA 333/2", -4000.0, "TRANSFERENCIA CUENTAS PAIS", "Transferencia Interna")
        self.banco(D(2026, 8, 6), "BBVA 333/1", 4000.0, "TRANSFERENCIA CUENTAS PAIS", "Transferencia Interna")
        self.tango(D(2026, 8, 6), "REC", 89, 4000.0, cuit=CUIT_A)
        inf = self.correr()
        self.assertEqual(len(inf["internas"]), 1)
        self.assertEqual(len(inf["pares"]), 1)
        self.assertEqual(inf["pares"][0]["banco"][0]["cuenta"], "BBVA 333/2")
        self.assertEqual(inf["solo_banco"], [])

    def test_solo_tango_de_cuenta_compartida_se_cuenta_una_vez(self):
        self.banco(D(2026, 8, 6), "BBVA 333/1", -1.0, "COMISION", "Gastos Bancarios")
        self.banco(D(2026, 8, 6), "BBVA 333/2", -1.0, "COMISION", "Gastos Bancarios")
        self.tango(D(2026, 8, 6), "O/P", 89, -777.0)
        inf = self.correr()
        self.assertEqual(sorted(r["n_solo_tango"] for r in inf["resumen"]), [0, 1])

    def test_gastos_van_a_su_bloque(self):
        self.banco(D(2026, 8, 3), "GALICIA 111", -12.34, "IMP DEBITOS Y CREDITOS", "Impuestos")
        self.banco(D(2026, 8, 3), "GALICIA 111", -50.0, "COMISION", "Gastos Bancarios")
        inf = self.correr()
        self.assertEqual(len(inf["gastos"]), 2)
        self.assertEqual(inf["solo_banco"], [])

    def test_no_pasa_por_banco(self):
        self.tango(D(2026, 8, 7), "REC", 1, 800.0, cuenta="CAJA", cuit=CUIT_A, nombre="CLIENTE", interno=50)
        self.tango(D(2026, 8, 7), "REC", 3, 1200.0, cuenta="VALORES A DEPOSITAR", cuit=CUIT_A, interno=50)
        self.tango(D(2026, 8, 7), "REC", 10, -2000.0, cuenta="DEUDORES POR VENTAS", cuit=CUIT_A, interno=50)
        self.tango(D(2026, 8, 9), "O/P", 3, -900.0, cuenta="VALORES A DEPOSITAR", cuit=CUIT_B, interno=60)
        self.tango(D(2026, 8, 9), "O/P", 17, 900.0, cuenta="PROVEEDORES", cuit=CUIT_B, interno=60)
        self.banco(D(2026, 8, 9), "GALICIA 111", -1.0, "COMISION", "Gastos Bancarios")
        inf = self.correr()
        clases = sorted(g["clase"] for g in inf["no_banco"])
        self.assertEqual(clases, ["Cheque de tercero endosado", "Efectivo (cobro)"])
        self.assertEqual(inf["cheques_recibidos"], [1, 120000])

    def test_fecha_imposible(self):
        self.banco(D(2026, 8, 13), "MACRO 222", 8980.0, "ACREDITACION CHEQUE", "Cheques")
        self.tango(D(2036, 8, 12), "BDM", 25, 8980.0)
        inf = self.correr()
        self.assertEqual(inf["pares"], [])
        self.assertTrue(any("fecha imposible" in r["motivo"] and "12/08/2026" in r["motivo"] for r in inf["revisar"]))
        self.assertIn("fecha imposible", inf["solo_banco"][0]["pista"])

    def test_par_cruzado_de_mes(self):
        self.banco(D(2026, 9, 2), "GALICIA 111", 5000.0, "TRANSF 20111111112", "Cobranza Facturas")
        self.tango(D(2026, 8, 31), "REC", 5, 5000.0, cuit=CUIT_A)
        inf = self.correr()
        self.assertEqual(len(inf["pares"]), 1)
        self.assertEqual(inf["solo_tango"], [])

    def test_ignora_manual_y_caja_aa(self):
        self.banco(D(2026, 8, 5), "GALICIA 111", 999.0, origen="Manual")
        self.banco(D(2026, 8, 5), "Caja AA", 999.0, origen="Tango AA · movimientos")
        self.banco(D(2026, 8, 5), "GALICIA 111", 10.0, "COMISION", "Gastos Bancarios")
        inf = self.correr()
        self.assertEqual(inf["resumen"][0]["n"], 1)
        self.assertEqual(inf["sin_par_banco"], {})

    def test_anulado_con_reversion(self):
        self.tango(D(2026, 8, 18), "OPF", 25, -609.0, leyenda="PAGO GREMIO")
        self.tango(D(2026, 8, 18), "REV", 25, 609.0, leyenda="PAGO GREMIO")
        self.banco(D(2026, 8, 18), "MACRO 222", -1.0, "COMISION", "Gastos Bancarios")
        inf = self.correr()
        self.assertTrue(all(t.get("anulado") for t in inf["solo_tango"]))
        self.assertEqual(inf["resumen"][0]["n_solo_tango"], 0)

    def test_excel_y_resumen_se_escriben(self):
        self.banco(D(2026, 8, 5), "GALICIA 111", 1000.0)
        self.tango(D(2026, 8, 5), "REC", 5, 1000.0)
        self.correr()
        wb = openpyxl.load_workbook(self.base / "salidas" / "cruce_2026-08.xlsx")
        self.assertEqual(wb.sheetnames, ["Resumen", "Conciliado", "Solo en banco", "Gastos bancarios",
                                         "Solo en Tango", "No pasa por banco", "Revisar"])
        self.assertTrue((self.base / "salidas" / "resumen_cruce_2026-08.md").exists())


class ReglasDeSeptiembre(_Base):
    """Casos que aparecieron con los datos de septiembre (tarea 45). Datos inventados."""

    def par_de(self, inf, importe):
        for p in inf["pares"]:
            if any(abs(b["c"] - round(importe * 100)) <= 1 for b in p["banco"]):
                return p
        return None

    def test_impuestos_agrupados_en_dias_distintos(self):
        self.banco(D(2026, 9, 16), "MACRO 222", -2210.0 * 1000, "IMP. AFIP", "Impuestos")
        self.tango(D(2026, 9, 15), "OPF", 25, -2000.0 * 1000, leyenda="PAGO APORTES")
        self.tango(D(2026, 9, 15), "OPF", 25, -200.0 * 1000, leyenda="INTERES APORTES")
        self.tango(D(2026, 9, 16), "OPF", 25, -10.0 * 1000, leyenda="PAGO INTERES APORTE")
        par = self.par_de(self.correr("2026-09"), -2210000)
        self.assertEqual(("impuestos", "Sugerido", 3), (par["regla"], par["nivel"], len(par["tango"])))
        self.assertIn("órdenes de pago de impuestos", par["criterio"])

    def test_impuestos_no_toma_pagos_a_proveedores_ni_montos_chicos(self):
        self.banco(D(2026, 9, 16), "MACRO 222", -300.0 * 1000, "IMP. AFIP", "Impuestos")
        self.tango(D(2026, 9, 16), "OPF", 25, -100.0 * 1000, cuit=CUIT_A)   # tiene CUIT: es un tercero
        self.tango(D(2026, 9, 16), "OPF", 25, -200.0 * 1000)
        self.banco(D(2026, 9, 17), "MACRO 222", -500.0, "IMP. AFIP", "Impuestos")   # menos del mínimo
        self.tango(D(2026, 9, 17), "OPF", 25, -300.0)
        self.tango(D(2026, 9, 17), "OPF", 25, -200.0)
        inf = self.correr("2026-09")
        self.assertEqual(inf["pares"], [])
        self.assertEqual(len(inf["gastos"]), 2)

    def test_impuestos_ambiguo_va_a_revisar(self):
        self.banco(D(2026, 9, 16), "MACRO 222", -300.0 * 1000, "IMP. AFIP", "Impuestos")
        for v in (100.0, 200.0, 150.0, 150.0):
            self.tango(D(2026, 9, 16), "OPF", 25, -v * 1000)
        inf = self.correr("2026-09")
        self.assertEqual(inf["pares"], [])
        self.assertTrue(any("impuestos agrupados" in r["motivo"] for r in inf["revisar"]))
        self.assertEqual(inf["gastos"], [])

    def test_descuento_neto_corrido(self):
        # el interés se carga el día del banco y la boleta dos días después
        self.banco(D(2026, 9, 14), "MACRO 222", 9600.0, "033000111", "Descuento de Cheques")
        self.tango(D(2026, 9, 16), "BDM", 25, 10000.0)
        self.tango(D(2026, 9, 14), "FPR", 25, -400.0, leyenda="INTERESES VTA VALORES MACRO")
        par = self.par_de(self.correr("2026-09"), 9600)
        self.assertEqual(("descuento neto", "Sugerido"), (par["regla"], par["nivel"]))
        self.assertIn("cargados en días distintos", par["criterio"])

    def test_descuento_del_mismo_dia_sigue_siendo_seguro(self):
        self.banco(D(2026, 9, 14), "MACRO 222", 9600.0, "033000111", "Descuento de Cheques")
        self.tango(D(2026, 9, 14), "BDM", 25, 10000.0)
        self.tango(D(2026, 9, 14), "FPR", 25, -400.0, leyenda="INTERESES VTA VALORES MACRO")
        self.assertEqual("Seguro", self.par_de(self.correr("2026-09"), 9600)["nivel"])

    def test_deposito_acreditado_en_dos_dias(self):
        self.banco(D(2026, 8, 5), "MACRO 222", 1600.0, "DEPOSITO CANJE", "Cheques")
        self.banco(D(2026, 8, 6), "MACRO 222", 1200.0, "ACREDITACION CHEQUE", "Cheques")
        self.banco(D(2026, 8, 6), "MACRO 222", 77.0, "ACREDITACION CHEQUE", "Cheques")    # de otra cosa
        self.tango(D(2026, 8, 5), "BDM", 25, 2800.0)
        inf = self.correr()
        par = self.par_de(inf, 1600)
        self.assertEqual(("agrupado", "Posible", 2), (par["regla"], par["nivel"], len(par["banco"])))
        self.assertIn("acreditados el 05/08 y el 06/08", par["criterio"])
        self.assertEqual([b["c"] for b in inf["solo_banco"]], [7700])

    def test_pista_de_error_de_tipeo(self):
        self.banco(D(2026, 9, 14), "MACRO 222", -12345678.0, "TARJETA DE CREDITO", "Otros")
        self.tango(D(2026, 8, 31), "EXT", 25, -12354678.0)
        inf = self.correr("2026-09")
        self.assertIn("error de tipeo", inf["solo_banco"][0]["pista"])


class Niveles(_Base):
    """Cada par sale con nivel (Seguro / Sugerido / Posible) y un criterio en castellano."""

    def par_de(self, inf, importe):
        for p in inf["pares"] + inf["pares_internas"]:
            if any(abs(b["c"] - round(importe * 100)) <= 1 for b in p["banco"]):
                return p
        self.fail("no hay par para %s" % importe)

    def test_seguro_exacto_unico(self):
        self.banco(D(2026, 8, 5), "GALICIA 111", 1000.0, "TRANSF 20111111112")
        self.tango(D(2026, 8, 3), "REC", 5, 1000.0, cuit=CUIT_A)
        par = self.par_de(self.correr(), 1000)
        self.assertEqual(par["nivel"], "Seguro")
        self.assertIn("importe exacto", par["criterio"])
        self.assertIn("CUIT coincide", par["criterio"])
        self.assertIn("banco 2 días después", par["criterio"])

    def test_seguro_exacto_con_cuit_entre_varios(self):
        self.banco(D(2026, 8, 12), "MACRO 222", -500.0, "TRANSF 27222222228 VAR")
        self.banco(D(2026, 8, 12), "MACRO 222", -500.0, "TRANSF 20111111112 VAR")
        self.tango(D(2026, 8, 12), "O/P", 25, -500.0, cuit=CUIT_A)
        self.tango(D(2026, 8, 12), "O/P", 25, -500.0, cuit=CUIT_B)
        inf = self.correr()
        self.assertEqual({p["nivel"] for p in inf["pares"]}, {"Seguro"})
        self.assertTrue(all("ganó el del mismo CUIT" in p["criterio"] for p in inf["pares"]))

    def test_sugerido_exacto_desempatado_por_fecha(self):
        self.banco(D(2026, 8, 12), "MACRO 222", -500.0, "DEBITO")
        self.banco(D(2026, 8, 14), "MACRO 222", -500.0, "DEBITO")
        self.tango(D(2026, 8, 12), "OPF", 25, -500.0)
        self.tango(D(2026, 8, 13), "OPF", 25, -500.0)
        inf = self.correr()
        self.assertEqual({p["nivel"] for p in inf["pares"]}, {"Sugerido"})
        criterios = sorted(p["criterio"] for p in inf["pares"])
        self.assertTrue(any("ganó la fecha más cercana" in c for c in criterios))
        self.assertTrue(any("después de otro desempate" in c for c in criterios))

    def test_sugerido_bloque_y_seguro_descuento_neto(self):
        for v in (100.0, 900.0):
            self.banco(D(2026, 8, 26), "GALICIA 111", v, "CREDITO DESCUENTO DOCUMENTO", "Descuento de Cheques")
        self.tango(D(2026, 8, 26), "BDG", 5, 1000.0)
        self.banco(D(2026, 8, 6), "MACRO 222", 9600.0, "033000111", "Descuento de Cheques")
        self.tango(D(2026, 8, 6), "BDM", 25, 10000.0)
        self.tango(D(2026, 8, 6), "FPR", 25, -400.0, leyenda="INTERESES VTA.CH.")
        inf = self.correr()
        self.assertEqual(self.par_de(inf, 100)["nivel"], "Sugerido")
        self.assertIn("2 banco ↔ 1 Tango", self.par_de(inf, 100)["criterio"])
        self.assertEqual(self.par_de(inf, 9600)["nivel"], "Seguro")

    def test_posible_agrupado_y_fecha_corrida(self):
        self.banco(D(2026, 8, 12), "MACRO 222", 300.0, "ACREDITACION CHEQUE", "Cheques")
        self.banco(D(2026, 8, 12), "MACRO 222", 700.0, "ACREDITACION CHEQUE", "Cheques")
        self.banco(D(2026, 8, 12), "MACRO 222", 80.0, "ACREDITACION CHEQUE", "Cheques")
        self.tango(D(2026, 8, 11), "BDM", 25, 1000.0)
        self.banco(D(2026, 8, 24), "MACRO 222", -2983.0, "DEBITO PRESTAMOS", "Prestamo")
        self.tango(D(2026, 9, 1), "FPR", 25, -2983.0)
        inf = self.correr()
        self.assertEqual(self.par_de(inf, 300)["nivel"], "Posible")
        self.assertEqual(self.par_de(inf, -2983)["nivel"], "Posible")
        self.assertIn("banco 8 días antes", self.par_de(inf, -2983)["criterio"])

    def test_posible_exacto_con_cuit_distinto(self):
        self.banco(D(2026, 8, 5), "GALICIA 111", -1000.0, "TRANSF 27222222228")
        self.tango(D(2026, 8, 5), "O/P", 5, -1000.0, cuit=CUIT_A)
        par = self.par_de(self.correr(), -1000)
        self.assertEqual(par["nivel"], "Posible")
        self.assertIn("CUIT distinto", par["criterio"])

    def test_internas_son_seguro(self):
        self.banco(D(2026, 8, 6), "BBVA 333/2", -4000.0, "TRANSFERENCIA CUENTAS PAIS", "Transferencia Interna")
        self.banco(D(2026, 8, 6), "BBVA 333/1", 4000.0, "TRANSFERENCIA CUENTAS PAIS", "Transferencia Interna")
        inf = self.correr()
        self.assertEqual([p["nivel"] for p in inf["pares_internas"]], ["Seguro"])

    def test_resumen_por_nivel_y_cuenta(self):
        self.banco(D(2026, 8, 5), "GALICIA 111", 1000.0)
        self.tango(D(2026, 8, 5), "REC", 5, 1000.0)
        self.banco(D(2026, 8, 24), "GALICIA 111", -250.0, "DEBITO", "Prestamo")
        self.tango(D(2026, 9, 2), "FPR", 5, -250.0)
        r = self.correr()["resumen"][0]
        self.assertEqual(r["por_nivel"]["Seguro"], {"n": 1, "c": 100000})
        self.assertEqual(r["por_nivel"]["Posible"], {"n": 1, "c": 25000})
        self.assertEqual(r["por_nivel"]["Sugerido"], {"n": 0, "c": 0})

    def test_el_perfil_cambia_el_nivel(self):
        self.banco(D(2026, 8, 24), "MACRO 222", -2983.0, "DEBITO PRESTAMOS", "Prestamo")
        self.tango(D(2026, 9, 1), "FPR", 25, -2983.0)
        cfg = cz_config()
        cfg["niveles"] = {"fecha corrida": "Sugerido"}
        with patch.object(cz, "cargar_config", return_value=cfg):
            inf = self.correr(parchar=False)
        self.assertEqual(self.par_de(inf, -2983)["nivel"], "Sugerido")

    def test_nivel_invalido_en_el_perfil_frena(self):
        ruta = self.base / "clientes" / "x" / "perfil.json"
        ruta.parent.mkdir(parents=True)
        ruta.write_text('{"cruce": {"cuentas": {"B 1": 5}, "niveles": {"agrupado": "Casi"}}}', encoding="utf-8")
        with patch.object(cz, "BASE_REPO", str(self.base)):
            with self.assertRaises(SystemExit):
                cz.cargar_config("x")


class Cuits(unittest.TestCase):
    def test_cuit_del_banco(self):
        self.assertEqual(cz.cuit_del_banco("TRANSF:WY7ZEPN6-20111111112"), "20111111112")
        self.assertEqual(cz.cuit_del_banco("", "CUIT 27-22222222-8: proveedor"), "27222222228")
        self.assertEqual(cz.cuit_del_banco("CBU 28500331300000083019"), "")          # parte de un número largo
        self.assertEqual(cz.cuit_del_banco("TRANSF 30999999995", propio="30999999995"), "")
        self.assertEqual(cz.cuit_del_banco("TRANSF 20111111113"), "")               # verificador mal


def cz_config():
    cfg = dict(CFG)
    cfg["cuit_propio"] = "30999999995"
    return cfg


if __name__ == "__main__":
    unittest.main()
