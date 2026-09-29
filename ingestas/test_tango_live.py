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
            "consultas_personalizadas": {
                "A": {"cobranzas": 10, "pagos": 11, "cheques_terceros": 12,
                      "cheques_propios": 13},
                "AA": {"cobranzas": 14, "pagos": 15, "cheques_terceros": 16,
                       "movimientos_tesoreria": 17},
            },
            "dias_atras": {"cheques_propios": 60},
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
                self.cfg, "token-inventado", "A", "cobranzas", 101, "", "")

        self.assertEqual([{"N": 1}, {"N": 2}], filas)
        self.assertEqual(2, len(pedidos))
        for indice, (req, timeout) in enumerate(pedidos):
            url = urlparse(req.full_url)
            query = parse_qs(url.query, keep_blank_values=True)
            self.assertEqual("/Api/GetApiLiveQueryData", url.path)
            self.assertEqual(["101"], query["process"])
            self.assertEqual([""], query["fromDate"])
            self.assertEqual([""], query["toDate"])
            self.assertEqual(["5000"], query["pageSize"])
            self.assertEqual([str(indice)], query["pageIndex"])
            self.assertEqual(["10"], query["customQuery"])
            headers = {k.lower(): v for k, v in req.headers.items()}
            self.assertEqual("token-inventado", headers["apiauthorization"])
            self.assertEqual("13", headers["company"])
            self.assertEqual(300, timeout)

    def test_custom_query_es_obligatoria_y_el_rango_propio_es_sesenta_dias(self):
        cfg = dict(self.cfg)
        cfg["consultas_personalizadas"] = {"A": {}}
        with self.assertRaisesRegex(RuntimeError, "falta la consulta personalizada"):
            live.armar_url(cfg, "A", "cobranzas", 101, "", "")
        desde, hasta = live.rango_fechas(
            self.cfg, datetime.date(2026, 9, 25), "cheques_propios")
        self.assertEqual("27/07/2026", desde)
        self.assertEqual("", hasta)
        self.assertEqual(("", ""), live.rango_fechas(
            self.cfg, datetime.date(2026, 9, 25), "cobranzas"))

    def test_total_incompleto_no_escribe_archivo(self):
        respuesta = RespuestaInventada(cuerpo([{"RAZON_SOCIAL": "Ejemplo"}], total=2))
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = os.path.join(carpeta, "salida.xlsx")
            with mock.patch.object(live.urllib.request, "urlopen", return_value=respuesta):
                with self.assertRaisesRegex(RuntimeError, "descarga incompleta"):
                    live.bajar_y_escribir(
                        self.cfg, "token", "A", "cobranzas", 101, ruta,
                        "", "")
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
                 "FECHA_DE_EMISION": "2026-09-01T00:00:00",
                 "FECHA_DE_VENCIMIENTO": "2026-10-01T00:00:00", "COD_CLIENTE": "C1",
                 "RAZON_SOCIAL": "Cliente ejemplo", "DESCRIPCION_CONDICION_DE_VENTA": "Contado",
                 "IMPORTE_AL_VENCIMIENTO_CTE": 1500, "IMPORTE_PENDIENTE_CTE": 1200,
                 "CAMPO_EXTRA": "se conserva"},
                {"Tipo comprobante": "FAC", "Nro. comprobante": "0001",
                 "Fecha de emisión": "2026-09-01T00:00:00", "Cód. cliente": "C1",
                 "Fecha de vencimiento": "2026-10-01T00:00:00", "Razón social": "Cliente ejemplo",
                 "Descripción condición de venta": "Contado",
                 "Importe al Vencimiento (CTE)": 1500,
                 "Importe Pendiente (CTE)": 1200, "CAMPO_EXTRA": "se conserva"}),
            "pagos": (
                {"TIPO_DE_COMPROBANTE": "FAC", "NRO_COMPROBANTE": "0099",
                 "FECHA_DE_EMISION": "2026-09-02T00:00:00",
                 "FECHA_DE_VENCIMIENTO": "2026-10-02T00:00:00", "COD_PROVEEDOR": "P1",
                 "RAZON_SOCIAL": "Proveedor ejemplo", "TOTAL_AL_VENCIMIENTO_CTE": 2500,
                 "TOTAL_PENDIENTE_CTE": 2300},
                {"Tipo de comprobante": "FAC", "Nro. comprobante": "0099",
                 "Fecha de emisión": "2026-09-02T00:00:00", "Cód. proveedor": "P1",
                 "Fecha de vencimiento": "2026-10-02T00:00:00", "Razón social": "Proveedor ejemplo",
                 "Total al vencimiento (CTE)": 2500, "Total pendiente (CTE)": 2300}),
            "cheques_terceros": (
                {"NRO_DE_CHEQUE": "123", "BANCO": "Banco ejemplo", "COD_CLIENTE": "C1",
                 "CLIENTE": "Cliente ejemplo", "FECHA_DEL_CHEQUE": "2026-10-03T00:00:00",
                 "IMPORTE_CTE": 3400, "SUBESTADO": "N", "DESC_SUBESTADO": "Normal",
                 "COD_ESTADO": "C", "ESTADO": "C", "ORIGEN": "Recibo"},
                {"Nro. de cheque": "123", "Estado": "En Cartera", "Cód. estado": "C"}),
            "cheques_propios": (
                {"NRO_DE_CHEQUE": "456", "BANCO": "Banco ejemplo", "COD_PROVEEDOR": "P1",
                 "RAZON_SOCIAL": "Proveedor ejemplo", "FECHA_DE_EMISION": "2026-09-01T00:00:00",
                 "FECHA_DEL_CHEQUE": "2026-10-04T00:00:00", "IMPORTE": 4500,
                 "ESTADO": "E", "CUENTA_EMISION": "Cuenta ejemplo"},
                {"Nro. de cheque": "456", "Estado": "Al Cobro", "Cód. estado": "E"}),
            "movimientos_tesoreria": (
                {"TIPO": "REC", "COMPROBANTE": "10", "FECHA": "2026-09-20T00:00:00",
                 "FECHA_DE_EMISION": "2026-09-20T00:00:00",
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
            {"NRO_DE_CHEQUE": "1", "COD_ESTADO": "C", "ESTADO": "C", "IMPORTE_CTE": 10},
            {"NRO_DE_CHEQUE": "2", "COD_ESTADO": "A", "ESTADO": "A", "IMPORTE_CTE": 20},
            {"NRO_DE_CHEQUE": "3", "COD_ESTADO": "R", "ESTADO": "R", "IMPORTE_CTE": 30},
            {"NRO_DE_CHEQUE": "4", "COD_ESTADO": "X", "ESTADO": "X", "IMPORTE_CTE": 40},
        ]
        traducidas, _, conteo, _ = live.preparar_filas("cheques_terceros", "A", filas)
        self.assertEqual(["1"], [f["Nro. de cheque"] for f in traducidas])
        for codigo in ("C→En Cartera", "A→Aplicado", "R→Rechazado", "X→(código X sin traducir)"):
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
                "COD_ESTADO": "C", "ESTADO": "C", "DESC_SUBESTADO": "Normal",
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
        self.assertEqual(7, texto.count("fromDate=&toDate="))
        self.assertIn("fromDate=27%2F07%2F2026&toDate=", texto)
        self.assertEqual(8, texto.count("customQuery="))

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
                "", "")
        self.assertNotIn(dato_sensible_inventado, salida.getvalue())

    def test_parte_tango_ocho_de_ocho_es_atomico(self):
        marca = datetime.datetime(2026, 9, 28, 10, 31, tzinfo=datetime.timezone.utc)
        with tempfile.TemporaryDirectory() as raiz:
            live._escribir_parte_tango(raiz, 8, 8, [], "token-secreto", marca)
            carpeta = os.path.join(raiz, "_para la Sheet")
            archivos = os.listdir(carpeta)
            with open(os.path.join(carpeta, "tango_ultima_bajada.txt"),
                      encoding="utf-8") as archivo:
                texto = archivo.read()
        self.assertEqual(["tango_ultima_bajada.txt"], archivos)
        self.assertEqual("2026-09-28T10:31:00+00:00\n8 de 8\n", texto)

    def test_parte_tango_informa_fallas_sin_token(self):
        marca = datetime.datetime(2026, 9, 28, 10, 31, tzinfo=datetime.timezone.utc)
        secreto = "token-muy-secreto"
        error_largo = RuntimeError("falló la consulta con %s " % secreto + "x" * 300)
        with tempfile.TemporaryDirectory() as raiz:
            live._escribir_parte_tango(
                raiz, 6, 8,
                [("A pagos 2026-09-28.xlsx", error_largo),
                 ("AA cobranzas 2026-09-28.xlsx", "timeout")],
                secreto, marca)
            with open(os.path.join(raiz, "_para la Sheet", "tango_ultima_bajada.txt"),
                      encoding="utf-8") as archivo:
                texto = archivo.read()
        self.assertIn("6 de 8", texto)
        self.assertIn("A pagos 2026-09-28.xlsx:", texto)
        self.assertIn("AA cobranzas 2026-09-28.xlsx: timeout", texto)
        self.assertNotIn(secreto, texto)
        self.assertLessEqual(len(texto.splitlines()[2].split(": ", 1)[1]), 150)

    def test_si_falta_completo_no_toca_nada(self):
        with tempfile.TemporaryDirectory() as raiz:
            marca = datetime.datetime(2026, 9, 28, 10, 31).astimezone()
            live._escribir_parte_tango(raiz, 8, 8, [], ahora=marca)
            ruta = os.path.join(raiz, "_para la Sheet", "tango_ultima_bajada.txt")
            with open(ruta, "rb") as f:
                antes = f.read()
            fecha = os.stat(ruta).st_mtime_ns
            with mock.patch.object(live, "perfil", return_value=self.cfg), \
                    mock.patch.object(live, "token") as cred, \
                    mock.patch.object(live, "llamar") as red, \
                    mock.patch.object(live, "bajar_y_escribir") as bajar, \
                    mock.patch.object(live, "_escribir_parte_tango") as escribir, \
                    mock.patch.object(live.os, "makedirs") as carpetas, \
                    redirect_stdout(io.StringIO()) as salida:
                rc = live.main(["--destino", raiz, "--hoy", "2026-09-28", "--si-falta"])
            self.assertEqual(rc, 0)
            for accion in (cred, red, bajar, escribir, carpetas):
                accion.assert_not_called()
            self.assertIn("ya bajó hoy completo a las 10:31; no hago nada", salida.getvalue())
            with open(ruta, "rb") as f:
                self.assertEqual(f.read(), antes)
            self.assertEqual(os.stat(ruta).st_mtime_ns, fecha)

    def test_reintentos_y_bajada_manual(self):
        hoy = datetime.datetime(2026, 9, 28, 10, 31).astimezone().isoformat()
        ayer = datetime.datetime(2026, 9, 27, 10, 31).astimezone().isoformat()
        casos = [
            ("ayer", ayer + "\n8 de 8\n", True),
            ("falló todo", hoy + "\n0 de 8\n", True),
            ("parcial", hoy + "\n5 de 8\n", True),
            ("sin parte", None, True),
            ("ilegible", "no es un parte", True),
            ("sin permiso", None, True),
            ("otro total", hoy + "\n7 de 7\n", True),
            ("sin zona", "2026-09-28T10:31:00\n8 de 8\n", True),
            ("manual", hoy + "\n8 de 8\n", False),
        ]
        for nombre, parte, automatico in casos:
            with self.subTest(nombre=nombre), tempfile.TemporaryDirectory() as raiz:
                carpeta = os.path.join(raiz, "_para la Sheet")
                os.makedirs(carpeta)
                ruta = os.path.join(carpeta, "tango_ultima_bajada.txt")
                if parte is not None:
                    with open(ruta, "w", encoding="utf-8") as f:
                        f.write(parte)
                abrir_real = open

                def abrir(*args, **kwargs):
                    if nombre == "sin permiso" and args[0] == ruta:
                        raise PermissionError("parte bloqueado")
                    return abrir_real(*args, **kwargs)

                with mock.patch.object(live, "perfil", return_value=self.cfg), \
                        mock.patch.object(live, "token", return_value="ficticio") as cred, \
                        mock.patch.object(live, "bajar_y_escribir", return_value=(1, 1)) as bajar, \
                        mock.patch("builtins.open", side_effect=abrir), \
                        redirect_stdout(io.StringIO()) as salida:
                    args = ["--destino", raiz, "--hoy", "2026-09-28"]
                    rc = live.main(args + (["--si-falta"] if automatico else []))
                self.assertEqual(rc, 0)
                cred.assert_called_once()
                self.assertEqual(bajar.call_count, 8)
                with open(ruta, encoding="utf-8") as f:
                    self.assertEqual(f.read().splitlines()[1], "8 de 8")
                if nombre in ("ilegible", "sin permiso", "sin zona"):
                    self.assertIn("parte de Tango ilegible", salida.getvalue())

    @unittest.skipUnless(hasattr(__import__("time"), "tzset"), "requiere tzset")
    def test_parte_usa_dia_local_no_dia_utc(self):
        import time
        with tempfile.TemporaryDirectory() as raiz:
            live._escribir_parte_tango(raiz, 8, 8, [], ahora=datetime.datetime(
                2026, 9, 29, 1, 30, tzinfo=datetime.timezone.utc))
            try:
                with mock.patch.dict(os.environ, {"TZ": "UTC+3"}):
                    time.tzset()
                    with redirect_stdout(io.StringIO()) as salida:
                        self.assertTrue(live._bajada_completa_hoy(
                            raiz, datetime.date(2026, 9, 28)))
                        self.assertFalse(live._bajada_completa_hoy(
                            raiz, datetime.date(2026, 9, 29)))
                    self.assertIn("22:30", salida.getvalue())
            finally:
                time.tzset()

    def test_error_al_escribir_parte_no_rompe_bajada(self):
        with tempfile.TemporaryDirectory() as raiz, \
                mock.patch.object(live, "perfil", return_value=self.cfg), \
                mock.patch.object(live, "token", return_value="token-inventado"), \
                mock.patch.object(live, "bajar_y_escribir", return_value=(1, 1)), \
                mock.patch.object(live, "_escribir_parte_tango",
                                  side_effect=OSError("Drive no disponible")), \
                redirect_stdout(io.StringIO()) as salida:
            rc = live.main([
                "--cliente", "navar", "--destino", raiz, "--hoy", "2026-09-28"])
        self.assertEqual(0, rc)
        self.assertIn("no pude escribir el parte de Tango", salida.getvalue())


if __name__ == "__main__":
    unittest.main()
