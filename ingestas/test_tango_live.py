# -*- coding: utf-8 -*-
"""Pruebas sin red y con datos inventados para la bajada de Tango Live."""

import io
import os
import json
import tempfile
import datetime
import unittest
from contextlib import redirect_stdout
from unittest import mock
from urllib.parse import urlparse, parse_qs

from ingestas import tango_live as live
from lector import tango
from lector import tesoreria_aa


class RespuestaInventada:
    def __init__(self, cuerpo, status=200):
        self.status = status
        self._cuerpo = cuerpo.encode("utf-8")

    def read(self):
        return self._cuerpo

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def cuerpo(filas, total=None, sigue=False, pagina=0, succeeded=True, exception=None):
    return json.dumps({
        "resultData": {
            "list": filas,
            "pageIndex": pagina,
            "pageSize": len(filas),
            "totalCount": len(filas) if total is None else total,
            "totalPages": 2 if sigue else 1,
            "hasPreviousPage": pagina > 0,
            "hasNextPage": sigue,
        },
        "message": None if succeeded else "consulta rechazada",
        "exceptionInfo": exception,
        "succeeded": succeeded,
    })


class TangoLiveTest(unittest.TestCase):
    def setUp(self):
        self.cfg = {
            "url": "http://tango-inventado:17000",
            "empresas": {"A": 13, "AA": 56},
            "consultas": {
                "cobranzas": 101,
                "pagos": 102,
                "cheques_terceros": 103,
                "cheques_propios": 104,
                "movimientos_tesoreria": 105,
            },
            "custom_query": "-",
        }

    def test_url_headers_timeout_y_paginacion(self):
        respuestas = [
            RespuestaInventada(cuerpo([{"N": 1}], total=2, sigue=True, pagina=0)),
            RespuestaInventada(cuerpo([{"N": 2}], total=2, sigue=False, pagina=1)),
        ]
        pedidos = []

        def abrir(req, timeout):
            pedidos.append((req, timeout))
            return respuestas.pop(0)

        with mock.patch.object(live.urllib.request, "urlopen", side_effect=abrir):
            filas = live.bajar(
                self.cfg, "token-inventado", "A", 101,
                "01/01/1990", "31/12/2031")

        self.assertEqual([{"N": 1}, {"N": 2}], filas)
        self.assertEqual(2, len(pedidos))
        for indice, (req, timeout) in enumerate(pedidos):
            url = urlparse(req.full_url)
            query = parse_qs(url.query)
            self.assertEqual("/Api/GetApiLiveQueryData", url.path)
            self.assertEqual(["101"], query["process"])
            self.assertEqual(["01/01/1990"], query["fromDate"])
            self.assertEqual(["31/12/2031"], query["toDate"])
            self.assertEqual(["5000"], query["pageSize"])
            self.assertEqual([str(indice)], query["pageIndex"])
            self.assertNotIn("customQuery", query)
            headers = {k.lower(): v for k, v in req.headers.items()}
            self.assertEqual("token-inventado", headers["apiauthorization"])
            self.assertEqual("13", headers["company"])
            self.assertEqual(300, timeout)

    def test_custom_query_solo_se_manda_si_es_real(self):
        cfg = dict(self.cfg, custom_query="consulta guardada")
        query = parse_qs(urlparse(live.armar_url(
            cfg, 101, "01/01/1990", "31/12/2031")).query)
        self.assertEqual(["consulta guardada"], query["customQuery"])

    def test_total_incompleto_no_escribe_archivo(self):
        respuesta = RespuestaInventada(cuerpo([{"RAZON_SOCIAL": "Ejemplo"}], total=2))
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = os.path.join(carpeta, "salida.xlsx")
            with mock.patch.object(live.urllib.request, "urlopen", return_value=respuesta):
                with self.assertRaisesRegex(RuntimeError, "descarga incompleta"):
                    live.bajar_y_escribir(
                        self.cfg, "token", "A", "cobranzas", 101, ruta,
                        "01/01/1990", "31/12/2031")
            self.assertFalse(os.path.exists(ruta))

    def test_html_y_error_de_live_son_claros(self):
        with self.assertRaisesRegex(RuntimeError, "dirección no es la de la API"):
            live._respuesta("<html><body>Iniciando...</body></html>", "http://ejemplo")
        with self.assertRaisesRegex(RuntimeError, "succeeded=false"):
            live._respuesta(cuerpo([], succeeded=False), "http://ejemplo")
        with self.assertRaisesRegex(RuntimeError, "exceptionInfo"):
            live._respuesta(cuerpo([], exception="error inventado"), "http://ejemplo")

    def test_encabezados_y_codigos_de_las_cinco_consultas(self):
        casos = {
            "cobranzas": (
                {"TIPO_COMPROBANTE": "FAC", "NRO_COMPROBANTE": "0001",
                 "FECHA_DE_VENCIMIENTO": "2026-10-01T00:00:00", "RAZON_SOCIAL": "Cliente ejemplo",
                 "IMPORTE_PENDIENTE_CTE": 1200, "CAMPO_EXTRA": "se conserva"},
                {"Tipo comprobante": "FAC", "Nro. comprobante": "0001",
                 "Fecha de vencimiento": "2026-10-01T00:00:00", "Razón social": "Cliente ejemplo",
                 "Importe Pendiente (CTE)": 1200, "CAMPO_EXTRA": "se conserva"}),
            "pagos": (
                {"TIPO_DE_COMPROBANTE": "FAC", "NRO_COMPROBANTE": "0099",
                 "FECHA_DE_VENCIMIENTO": "2026-10-02T00:00:00", "RAZON_SOCIAL": "Proveedor ejemplo",
                 "TOTAL_PENDIENTE_CTE": 2300},
                {"Tipo de comprobante": "FAC", "Nro. comprobante": "0099",
                 "Fecha de vencimiento": "2026-10-02T00:00:00", "Razón social": "Proveedor ejemplo",
                 "Total pendiente (CTE)": 2300}),
            "cheques_terceros": (
                {"NRO_DE_CHEQUE": "123", "NRO_INTERNO": "9", "BANCO": "Banco ejemplo",
                 "CLIENTE": "Cliente ejemplo", "FECHA_DEL_CHEQUE": "2026-10-03T00:00:00",
                 "IMPORTE_CTE": 3400, "DESC_SUBESTADO": "Normal", "ESTADO": "C",
                 "PROVEEDOR": None, "TIPO_DE_CHEQUE": "Común"},
                {"Nro. de cheque": "123", "Estado": "En Cartera", "Cód. estado": "C"}),
            "cheques_propios": (
                {"NRO_DE_CHEQUE": "456", "BANCO": "Banco ejemplo", "COD_PROVEEDOR": "P1",
                 "RAZON_SOCIAL": "Proveedor ejemplo", "FECHA_DE_EMISION": "2026-09-01T00:00:00",
                 "FECHA_DEL_CHEQUE": "2026-10-04T00:00:00", "IMPORTE": 4500,
                 "ESTADO": "E", "TIPO_DE_CHEQUE": "Diferido"},
                {"Nro. de cheque": "456", "Estado": "Al Cobro", "Cód. estado": "E"}),
            "movimientos_tesoreria": (
                {"TIPO": "REC", "COMPROBANTE": "10", "FECHA": "2026-09-20T00:00:00",
                 "CONCEPTO": "Cobro inventado", "CLASE": 1, "TOTAL_CTE": 5600,
                 "COD_RELACIONADO": "C1", "DESC_RELACIONADO": "Cliente ejemplo",
                 "CLASIFICACION": "Caja"},
                {"Tipo": "REC", "Clase": "Cobros", "Total (cte)": 5600}),
        }
        for consulta, (original, esperado) in casos.items():
            with self.subTest(consulta=consulta):
                traducidas, columnas = live.traducir_filas(consulta, [original])
                for clave, valor in esperado.items():
                    self.assertEqual(valor, traducidas[0][clave])
                    self.assertIn(clave, columnas)
        desconocido, _ = live.traducir_filas("cheques_propios", [{"ESTADO": "Z"}])
        self.assertEqual("(código Z sin traducir)", desconocido[0]["Estado"])
        self.assertEqual("Z", desconocido[0]["Cód. estado"])

    def test_tesoreria_frena_tipo_clase_incompatible(self):
        filas = [{"TIPO": "REC", "CLASE": 2, "TOTAL_CTE": 100}]
        with self.assertRaisesRegex(RuntimeError, "Tipo/Clase incompatibles"):
            live.preparar_filas("movimientos_tesoreria", "AA", filas)

    def test_tesoreria_no_publica_clase_desconocida(self):
        filas = [{"TIPO": "REV", "CLASE": 9, "TOTAL_CTE": 100}]
        preparadas, _, conteo, pares = live.preparar_filas("movimientos_tesoreria", "AA", filas)
        self.assertEqual([], preparadas)
        self.assertIn("9→(código 9 sin traducir)", conteo)
        self.assertIn("REV→(código 9 sin traducir)", pares)

    def test_cheques_terceros_escribe_solo_en_cartera(self):
        filas = [
            {"NRO_DE_CHEQUE": "1", "ESTADO": "C", "IMPORTE_CTE": 10},
            {"NRO_DE_CHEQUE": "2", "ESTADO": "A", "IMPORTE_CTE": 20},
            {"NRO_DE_CHEQUE": "3", "ESTADO": "R", "IMPORTE_CTE": 30},
            {"NRO_DE_CHEQUE": "4", "ESTADO": "Z", "IMPORTE_CTE": 40},
        ]
        traducidas, _, conteo, _ = live.preparar_filas("cheques_terceros", "A", filas)
        self.assertEqual(["1"], [f["Nro. de cheque"] for f in traducidas])
        for codigo in ("C→En Cartera", "A→Aplicado", "R→Rechazado", "Z→(código Z sin traducir)"):
            self.assertIn(codigo, conteo)

    def test_eleccion_de_carpeta_tesoreria(self):
        with tempfile.TemporaryDirectory() as raiz:
            self.assertEqual(os.path.join(raiz, "Tesoreria AA"),
                             live.carpeta_consulta(raiz, "movimientos_tesoreria"))
            os.mkdir(os.path.join(raiz, "Tesorería AA"))
            self.assertEqual(os.path.join(raiz, "Tesorería AA"),
                             live.carpeta_consulta(raiz, "movimientos_tesoreria"))
            os.mkdir(os.path.join(raiz, "Tesoreria AA"))
            self.assertEqual(os.path.join(raiz, "Tesoreria AA"),
                             live.carpeta_consulta(raiz, "movimientos_tesoreria"))

    def test_excel_traducido_lo_entienden_los_dos_lectores(self):
        hoy = datetime.date(2026, 9, 25)
        ejemplos = {
            "cobranzas": [{
                "TIPO_COMPROBANTE": "FAC", "NRO_COMPROBANTE": "000123",
                "FECHA_DE_VENCIMIENTO": "2026-10-01T00:00:00",
                "RAZON_SOCIAL": "Cliente inventado", "IMPORTE_PENDIENTE_CTE": 12100,
            }],
            "pagos": [{
                "TIPO_DE_COMPROBANTE": "FAC", "NRO_COMPROBANTE": "000456",
                "FECHA_DE_VENCIMIENTO": "2026-10-02T00:00:00",
                "RAZON_SOCIAL": "Proveedor inventado", "TOTAL_PENDIENTE_CTE": 23200,
            }],
            "cheques_terceros": [{
                "NRO_DE_CHEQUE": "777", "BANCO": "Banco inventado", "CLIENTE": "Cliente cheque",
                "FECHA_DEL_CHEQUE": "2026-10-03T00:00:00", "IMPORTE_CTE": 34300,
                "ESTADO": "C", "DESC_SUBESTADO": "Normal", "TIPO_DE_CHEQUE": "Común",
            }],
            "cheques_propios": [{
                "NRO_DE_CHEQUE": "888", "BANCO": "Banco inventado", "COD_PROVEEDOR": "P1",
                "RAZON_SOCIAL": "Proveedor cheque", "FECHA_DE_EMISION": "2026-09-20T00:00:00",
                "FECHA_DEL_CHEQUE": "2026-10-04T00:00:00", "IMPORTE": 45400,
                "ESTADO": "E", "TIPO_DE_CHEQUE": "Diferido",
            }],
        }
        nombres = {
            "cobranzas": "A cobranzas 2026-09-25.xlsx",
            "pagos": "A pagos 2026-09-25.xlsx",
            "cheques_terceros": "A cheques terceros 2026-09-25.xlsx",
            "cheques_propios": "A cheques propios 2026-09-25.xlsx",
        }
        with tempfile.TemporaryDirectory() as carpeta:
            for consulta, filas in ejemplos.items():
                preparadas, columnas, _, _ = live.preparar_filas(consulta, "A", filas)
                live.escribir_xlsx(preparadas, os.path.join(carpeta, nombres[consulta]), columnas)

            resultado = tango.procesar(carpeta, "navar", hoy)
            cobrar = resultado["listas"]["cobrar"][0]
            pagar = resultado["listas"]["pagar"][0]
            cheques = resultado["listas"]["cheques"]
            self.assertEqual("Cliente inventado", cobrar["Cliente"])
            self.assertEqual("FAC 000123", cobrar["Nro Factura"])
            self.assertEqual(datetime.date(2026, 10, 1), cobrar["Fecha Vencimiento"])
            self.assertEqual(12100, cobrar["Saldo Pendiente"])
            self.assertEqual("Proveedor inventado", pagar["Proveedor"])
            self.assertTrue(any(c["Nro Cheque"] == "777" and c["Estado"] == "En Cartera" for c in cheques))
            # El export dice Al Cobro; el lector lo convierte al estado común de la
            # solapa y lo distingue por Tipo = Propio Emitido.
            self.assertTrue(any(c["Nro Cheque"] == "888" and c["Tipo"] == "Propio Emitido"
                                and c["Estado"] == "En Cartera" for c in cheques))

            tes_filas = [
                {"TIPO": "REC", "COMPROBANTE": "1", "FECHA": "2026-09-23T00:00:00",
                 "CONCEPTO": "Cobro de prueba", "CLASE": 1, "TOTAL_CTE": 1000,
                 "DESC_RELACIONADO": "Cliente de caja"},
                {"TIPO": "O/P", "COMPROBANTE": "2", "FECHA": "2026-09-24T00:00:00",
                 "CONCEPTO": "Pago de prueba", "CLASE": 2, "TOTAL_CTE": 600,
                 "DESC_RELACIONADO": "Proveedor de caja"},
            ]
            preparadas, columnas, _, _ = live.preparar_filas("movimientos_tesoreria", "AA", tes_filas)
            ruta_tes = os.path.join(carpeta, "AA movimientos tesoreria 2026-09-25.xlsx")
            live.escribir_xlsx(preparadas, ruta_tes, columnas)
            movimientos = tesoreria_aa.leer(ruta_tes, datetime.date(2026, 6, 1))
            self.assertEqual(["Cobranza AA", "Proveedores AA"], [m["Categoria"] for m in movimientos])
            self.assertEqual([1000, -600], [m["Importe"] for m in movimientos])

    def test_simular_lista_ocho_sin_leer_token(self):
        with tempfile.TemporaryDirectory() as carpeta, \
                mock.patch.object(live, "token", side_effect=AssertionError("no debe leer token")), \
                redirect_stdout(io.StringIO()) as salida:
            rc = live.main(["--cliente", "navar", "--simular", "--destino", carpeta,
                            "--hoy", "2026-09-25"])
        texto = salida.getvalue()
        self.assertEqual(0, rc)
        self.assertEqual(8, texto.count("bajaría"))
        self.assertEqual(8, texto.count("/Api/GetApiLiveQueryData?"))
        self.assertIn("fromDate=01%2F01%2F1990", texto)
        self.assertIn("toDate=31%2F12%2F2031", texto)

    def test_probar_no_imprime_datos(self):
        dato_sensible_inventado = "NOMBRE QUE NO DEBE SALIR"
        respuesta = cuerpo([{
            "RAZON_SOCIAL": dato_sensible_inventado,
            "TIPO_COMPROBANTE": "FAC",
            "NRO_COMPROBANTE": "123",
        }], total=1)
        with mock.patch.object(live, "llamar", return_value=(200, "http://ejemplo?process=1", respuesta)), \
                redirect_stdout(io.StringIO()) as salida:
            live._mostrar_prueba(
                self.cfg, "token", "cobranzas", "A", 101,
                "01/01/1990", "31/12/2031")
        self.assertNotIn(dato_sensible_inventado, salida.getvalue())


if __name__ == "__main__":
    unittest.main()
