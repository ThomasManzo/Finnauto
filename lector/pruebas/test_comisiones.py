# -*- coding: utf-8 -*-
"""Tarea 80: comisiones a vendedores separadas de proveedores. Datos inventados."""
import datetime
import json
import os
import tempfile
import unittest

import openpyxl

from lector import cajas, comisiones, extractos

PROPIO = "30111111118"
VENDEDOR = "20222222223"
F = datetime.datetime(2026, 8, 10)


def fila(concepto, importe, cat="Proveedores MP y Logist.", banco="MACRO 1", fecha=F):
    return {"Tipo": "Egreso" if importe < 0 else "Ingreso", "Categoria": cat, "Concepto / Detalle": concepto,
            "Importe": importe, "Banco / Cuenta": banco, "Fecha": fecha, "Observaciones": "x"}


class Reglas(unittest.TestCase):
    def cat(self, concepto, importe=-100.0):
        return extractos.clasificar({"concepto": concepto, "importe": importe}, PROPIO)

    def test_distinto_titular_con_cuit_propio_es_pago(self):
        r = self.cat("TRF MO CCDO DIST T - " + PROPIO)
        self.assertEqual(("Proveedores MP y Logist.", False), (r[1], r[3]))
        self.assertNotIn("CUIT", r[4])

    def test_cuit_propio_sin_distinto_titular_sigue_interno(self):
        self.assertEqual("Transferencia Interna", self.cat("TRANSF %s VAR" % PROPIO)[1])

    def test_factura_de_comisiones_no_es_gasto_bancario(self):
        self.assertEqual("Proveedores MP y Logist.", self.cat("TRANSF %s FAC comisiones" % VENDEDOR)[1])

    def test_comision_del_banco_sigue_gasto_bancario(self):
        self.assertEqual("Gastos Bancarios", self.cat("COMISION TRANSFERE")[1])
        self.assertEqual("Gastos Bancarios", self.cat("D 500 COMI TRANSFERENCIA")[1])

    def test_nacion_a_otro_titular_es_proveedor_y_a_uno_mismo_interno(self):
        self.assertEqual("Proveedores MP y Logist.", self.cat("DEB.TRAN.INTERB - CUIT/CUIL: " + VENDEDOR)[1])
        self.assertEqual("Transferencia Interna", self.cat("DEB.TRAN.INTERBMISMO TIT - CUIT/CUIL: 20333333334")[1])


class MarcarBanco(unittest.TestCase):
    def test_por_cuit_en_el_texto_incluso_desde_otros(self):
        f = fila("DEB.TRAN.INTERB - CUIT/CUIL: " + VENDEDOR, -500.0, cat="Otros", banco="NACION 1")
        self.assertEqual(1, comisiones.marcar_banco([f], {VENDEDOR}, []))
        self.assertEqual("Comisiones", f["Categoria"])

    def test_por_orden_de_pago_una_sola_vez(self):
        filas = [fila("TRF MO CCDO", -500.0), fila("TRF MO CCDO", -500.0)]
        pagos = [{"fecha": F.date(), "importe": 500.0, "banco": "MACRO"}]
        self.assertEqual(1, comisiones.marcar_banco(filas, {VENDEDOR}, pagos))
        self.assertEqual(["Comisiones", "Proveedores MP y Logist."], [f["Categoria"] for f in filas])

    def test_no_marca_otro_banco_otra_fecha_ni_ingresos(self):
        pagos = [{"fecha": F.date(), "importe": 500.0, "banco": "MACRO"}]
        lejos = F + datetime.timedelta(days=8)
        filas = [fila("x", -500.0, banco="GALICIA 1"), fila("x", -500.0, fecha=lejos), fila("x", 500.0)]
        self.assertEqual(0, comisiones.marcar_banco(filas, {VENDEDOR}, pagos))

    def test_interno_no_se_toca(self):
        f = fila("TRANSF", -500.0, cat="Transferencia Interna")
        pagos = [{"fecha": F.date(), "importe": 500.0, "banco": "MACRO"}]
        self.assertEqual(0, comisiones.marcar_banco([f], {VENDEDOR}, pagos))


class Archivos(unittest.TestCase):
    def test_sin_lista_no_pasa_nada_y_cuit_malo_avisa(self):
        with tempfile.TemporaryDirectory() as raiz:
            self.assertEqual(set(), comisiones.cargar_vendedores(raiz))
            os.makedirs(os.path.join(raiz, "Comisiones"))
            with open(os.path.join(raiz, comisiones.RUTA_LISTA), "w", encoding="utf-8") as f:
                json.dump({"vendedores": [{"cuit": "123"}]}, f)
            with self.assertRaises(ValueError):
                comisiones.cargar_vendedores(raiz)

    def test_lee_las_ordenes_de_pago_del_detalle(self):
        with tempfile.TemporaryDirectory() as raiz:
            os.makedirs(os.path.join(raiz, "Tesoreria A detalle"))
            wb = openpyxl.Workbook()
            wb.active.append(["Fecha", "Cód. comprobante", "Desc. contable", "Haber (cte) (renglón)", "CUIT proveedor (encab.)"])
            wb.active.append([F, "O/P", "BANCO MACRO 1", 500.0, "20-22222222-3"])
            wb.active.append([F, "O/P", "CAJA", 300.0, "20-22222222-3"])
            wb.active.append([F, "O/P", "BANCO MACRO 1", 700.0, "20-99999999-3"])
            wb.save(os.path.join(raiz, "Tesoreria A detalle", "A.xlsx"))
            pagos = comisiones.pagos_de_banco(raiz, {VENDEDOR})
            self.assertEqual([(500.0, "MACRO")], [(p["importe"], p["banco"]) for p in pagos])


class Cajas(unittest.TestCase):
    CFG = {"A": {"cuentas": ["CAJA"]}, "AA": {"cuentas": ["CAJA AA"]}, "vendedores": {VENDEDOR}}

    def cat(self, cuit, leyenda, contra="ACREEDORES VARIOS", haber=100.0):
        caja = {"cuenta": "CAJA AA", "debe": 0.0, "haber": haber, "tipo": "O/P", "razon": "X", "leyenda": leyenda,
                "cuit_proveedor": cuit, "tipo_cuenta": "O"}
        otro = {"cuenta": contra, "debe": haber, "haber": 0.0, "tipo_cuenta": "O", "leyenda": leyenda}
        return cajas.categoria("AA", [caja], [otro], self.CFG)

    def test_vendedor_de_la_lista(self):
        self.assertEqual("Comisiones", self.cat(VENDEDOR, "PAGO"))

    def test_otro_proveedor_sigue_proveedor(self):
        self.assertEqual("Proveedores AA", self.cat("20999999993", "PAGO"))

    def test_comision_por_sueldos(self):
        self.assertEqual("Comisiones", self.cat("", "COMISIONES VTAS", contra="SUELDOS Y JORNALES A PAGAR"))

    def test_sueldo_comun_sigue_sueldo(self):
        self.assertEqual("Sueldos y Jornales", self.cat("", "SUELDOS", contra="SUELDOS Y JORNALES A PAGAR"))

    def test_gasto_bancario_con_la_palabra_no_es_comision(self):
        self.assertEqual("Otros", self.cat("", "DEBITO Y COMISIONES BANCARIAS", contra="OTROS GASTOS"))


if __name__ == "__main__":
    unittest.main()
