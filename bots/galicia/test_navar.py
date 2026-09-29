"""Controles de Galicia NAVAR sin entrar al banco ni tocar el llavero."""
import datetime as dt
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from openpyxl import Workbook, load_workbook

from bots.galicia.navar import BotGaliciaNavar, URL_LOGIN


BASE = Path(__file__).resolve().parents[2]


def _configuracion():
    perfil = json.loads((BASE / "clientes/navar/perfil.json").read_text(encoding="utf-8"))
    return perfil["bancos"]["galicia"]


def _escribir_excel(ruta, fechas, encabezado_creditos="Créditos", importe=100):
    """Imita el export real de Galicia, que no incluye ni cuenta ni columna Saldo."""
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Movimientos"
    hoja.append([
        "Fecha", "Descripción", "Origen", "Débitos", encabezado_creditos,
        "Grupo de Conceptos", "Concepto", "Número de Terminal",
        "Observaciones Cliente", "Número de Comprobante",
        "Leyendas Adicionales 1", "Leyendas Adicionales 2",
        "Leyendas Adicionales 3", "Leyendas Adicionales 4",
    ])
    for fecha in fechas:
        hoja.append([
            dt.datetime.combine(fecha, dt.time()), "Movimiento inventado", "", 0, importe,
            "", "", "", "", "123", "", "", "", "",
        ])
    libro.save(ruta)


class ElementoFalso:
    def __init__(self, texto="", visible=True, al_click=None, caja=None):
        self.texto = texto
        self.visible = visible
        self.al_click = al_click
        self.caja = caja
        self.clics = 0
        self.valor = None
        self.llenados = 0

    def is_visible(self):
        return self.visible

    def click(self, timeout=None):
        self.clics += 1
        if self.al_click:
            self.al_click()

    def fill(self, valor, timeout=None):
        self.valor = valor
        self.llenados += 1

    def wait_for(self, state=None, timeout=None):
        if state == "hidden" and not self.visible:
            return
        if state == "visible" and self.visible:
            return
        raise RuntimeError("estado no alcanzado: %s" % state)

    def inner_text(self, timeout=None):
        return self.texto

    def bounding_box(self):
        return self.caja


class ListaFalsa:
    def __init__(self, elementos=None):
        self.elementos = list(elementos or [])

    def count(self):
        return len(self.elementos)

    def nth(self, indice):
        return self.elementos[indice]

    def filter(self, has_text=None):
        if has_text is None:
            return self
        return ListaFalsa([
            elemento for elemento in self.elementos
            if has_text.search(elemento.texto)
        ])


class PaginaEsperaFalsa:
    def wait_for_timeout(self, milisegundos):
        pass


class PaginaConTextos(PaginaEsperaFalsa):
    def __init__(self, textos, url=""):
        self.elementos = [ElementoFalso(texto, visible) for texto, visible in textos]
        self.url = url

    def get_by_text(self, patron, exact=None):
        if isinstance(patron, str):
            elegidos = [e for e in self.elementos
                        if (e.texto == patron if exact else patron in e.texto)]
        else:
            elegidos = [e for e in self.elementos if patron.search(e.texto)]
        return ListaFalsa(elegidos)


class PaginaLoginFalsa(PaginaEsperaFalsa):
    def __init__(self):
        self.url = ""
        self.usuario = ElementoFalso("Usuario")
        self.clave = ElementoFalso("Clave")
        self.etiqueta_usuario = ElementoFalso("Usuario")
        self.etiqueta_clave = ElementoFalso("Clave")
        self.empresa = ElementoFalso("NAVAR SOCIEDAD ANONIMA", visible=False)
        self.ingresar = ElementoFalso("Ingresar", al_click=self._entrar)
        self.consultas_por_etiqueta = 0

    def _entrar(self):
        self.usuario.visible = False
        self.empresa.visible = True

    def goto(self, url, timeout=None):
        self.url = url

    def get_by_label(self, nombre, exact=None):
        self.consultas_por_etiqueta += 1
        if nombre == "Usuario":
            return ListaFalsa([self.etiqueta_usuario, self.usuario])
        return ListaFalsa([self.etiqueta_clave, self.clave])

    def get_by_role(self, rol, name=None, exact=None):
        if rol == "textbox":
            return ListaFalsa([self.usuario])
        if rol == "button" and name == "Ingresar":
            return ListaFalsa([self.ingresar])
        return ListaFalsa()

    def locator(self, selector):
        if selector == "input#userInput":
            return ListaFalsa([self.usuario])
        if selector == "input#userPassword":
            return ListaFalsa([self.clave])
        if selector == "input[type='password']":
            return ListaFalsa([self.clave])
        return ListaFalsa()

    def get_by_text(self, patron, exact=None):
        return ListaFalsa([self.empresa] if patron.search(self.empresa.texto) else [])


class PaginaSaldosFalsa(PaginaEsperaFalsa):
    def locator(self, selector):
        if "//*[normalize-space(.)='Actual']/following-sibling" in selector:
            return ListaFalsa([ElementoFalso("- $1.234,50")])
        if "//*[normalize-space(.)='Disponible']/following-sibling" in selector:
            return ListaFalsa([ElementoFalso("$765,50")])
        return ListaFalsa()


class PaginaDescargaFalsa(PaginaEsperaFalsa):
    def __init__(self, botones, filtros, opciones_excel=None):
        self.botones = botones
        self.filtros = filtros
        self.opciones_excel = list(opciones_excel or [])

    @property
    def mouse(self):
        raise AssertionError("No se debe usar page.mouse")

    def locator(self, selector):
        if selector == "button[aria-label='filter2']":
            return ListaFalsa([self.filtros])
        if selector == "button":
            return ListaFalsa(self.botones)
        return ListaFalsa()

    def get_by_text(self, texto, exact=None):
        if texto == "Excel" and exact:
            return ListaFalsa(self.opciones_excel)
        return ListaFalsa()


class PaginaQueNoSePuedeTocar:
    def __getattr__(self, nombre):
        raise AssertionError("Intentó usar la página: %s" % nombre)


class DescargaFalsa:
    """Imita Windows: no deja guardar encima de un archivo que ya existe."""
    suggested_filename = "Extracto_CC545950701.xlsx"

    def __init__(self, importe=100, fallar=False):
        self.importe = importe
        self.fallar = fallar
        self.destinos = []

    def save_as(self, destino):
        self.destinos.append(Path(destino))
        if Path(destino).exists():
            raise RuntimeError("el destino ya existe")
        if self.fallar:
            raise RuntimeError("Target page, context or browser has been closed")
        _escribir_excel(destino, [dt.date.today()], importe=self.importe)

    def failure(self):
        return "descarga interrumpida" if self.fallar else None


class PaginaConDescargaFalsa:
    def __init__(self, descarga):
        self.descarga = descarga

    def expect_download(self, timeout=None):
        return self

    def __enter__(self):
        return SimpleNamespace(value=self.descarga)

    def __exit__(self, tipo, valor, traza):
        return False


class PruebaNavar(unittest.TestCase):
    def setUp(self):
        self.cfg = _configuracion()
        self.bot = BotGaliciaNavar(self.cfg)
        # Ninguna prueba debe mirar ni limpiar Descargas reales de esta máquina.
        self.casa = tempfile.TemporaryDirectory()
        self.addCleanup(self.casa.cleanup)
        self.home = Path(self.casa.name)
        parche = patch("bots.galicia.navar.Path.home", return_value=self.home)
        parche.start()
        self.addCleanup(parche.stop)

    def _correr_descarga(self, temporales, publicados, descarga, al_click=None):
        boton = ElementoFalso("Descargar")
        excel = ElementoFalso("Excel", al_click=al_click)
        pagina = PaginaConDescargaFalsa(descarga)
        ctx = SimpleNamespace(descargas_dir=str(temporales))
        with patch.object(self.bot, "_buscar_boton_descarga", return_value=boton), \
                patch.object(self.bot, "_buscar_excel_del_menu", return_value=excel), \
                patch("bots.galicia.navar.captura"):
            return self.bot.descargar_csv(pagina, str(publicados), "NAVAR SA", 10, ctx)

    def test_unico_visible_ignora_oculto(self):
        oculto = ElementoFalso(visible=False)
        visible = ElementoFalso(visible=True)
        elegido = self.bot._esperar_unico_visible(
            PaginaEsperaFalsa(), [ListaFalsa([oculto, visible])], "ejemplo", 10)
        self.assertIs(elegido, visible)

    def test_unico_visible_frena_con_dos(self):
        with self.assertRaisesRegex(RuntimeError, "2 veces visible"):
            self.bot._esperar_unico_visible(
                PaginaEsperaFalsa(),
                [ListaFalsa([ElementoFalso(), ElementoFalso()])], "ejemplo", 10)

    def test_unico_visible_frena_al_vencer(self):
        with self.assertRaisesRegex(RuntimeError, "no apareció visible"):
            self.bot._esperar_unico_visible(
                PaginaEsperaFalsa(), [ListaFalsa([ElementoFalso(visible=False)])],
                "ejemplo", 0)

    def test_login_directo(self):
        pagina = PaginaLoginFalsa()
        self.bot.hacer_login(pagina, "usuario inventado", "clave inventada", 10)
        self.assertEqual(pagina.url, URL_LOGIN)
        self.assertEqual(pagina.usuario.valor, "usuario inventado")
        self.assertEqual(pagina.clave.valor, "clave inventada")
        self.assertEqual(pagina.usuario.llenados, 1)
        self.assertEqual(pagina.clave.llenados, 1)
        self.assertEqual(pagina.consultas_por_etiqueta, 0)
        self.assertEqual(pagina.ingresar.clics, 1)

    def test_cuenta_abierta_con_titulo_completo(self):
        pagina = PaginaConTextos(
            [
                ("Cuenta Corriente $ N° 0005459-5 070-1", True),
                ("N° 0005459-5 070-1", True),
            ],
            url="https://empresas.bancogalicia.com.ar/cuentas/movimientos")
        self.bot._esperar_cuenta_abierta(pagina, 10)

    def test_saldos_con_formato_argentino(self):
        saldos = self.bot.capturar_saldos(PaginaSaldosFalsa())
        self.assertEqual(saldos["actual"], -1234.50)
        self.assertEqual(saldos["disponible"], 765.50)
        self.assertEqual(saldos["actual_texto"], "- $1.234,50")

    def test_nombres_de_descarga(self):
        self.assertEqual(
            self.bot._validar_nombre_descarga("Extracto_CC545950701.xlsx"),
            "Extracto_CC545950701.xlsx")
        with self.assertRaisesRegex(RuntimeError, "cuenta pedida"):
            self.bot._validar_nombre_descarga("Extracto_CC999999999.xlsx")
        with self.assertRaisesRegex(RuntimeError, "XLSX"):
            self.bot._validar_nombre_descarga("Extracto_CC545950701.csv")

    def test_descarga_se_elige_por_posicion_junto_a_filtros(self):
        filtros = ElementoFalso("Filtros", caja={
            "x": 1243, "y": 595, "width": 101, "height": 40})
        descarga = ElementoFalso("", caja={
            "x": 1352, "y": 595, "width": 40, "height": 40})
        aplicar_escondido = ElementoFalso("Aplicar", caja={
            "x": 1465, "y": 595, "width": 100, "height": 40})
        flechas_filas = [ElementoFalso("", caja={
            "x": 1286, "y": y, "width": 24, "height": 24})
            for y in (650, 700, 750)]
        pagina = PaginaDescargaFalsa(
            [filtros, aplicar_escondido, descarga] + flechas_filas, filtros)

        elegido = self.bot._buscar_boton_descarga(pagina, 0)

        self.assertIs(elegido, descarga)

    def test_descarga_frena_con_dos_candidatos(self):
        filtros = ElementoFalso("Filtros", caja={
            "x": 1243, "y": 595, "width": 101, "height": 40})
        candidatos = [ElementoFalso("", caja={
            "x": x, "y": 595, "width": 40, "height": 40})
            for x in (1352, 1388)]
        pagina = PaginaDescargaFalsa([filtros] + candidatos, filtros)

        with self.assertRaisesRegex(RuntimeError, "encontré 2 candidatos"):
            self.bot._buscar_boton_descarga(pagina, 0)

    def test_descarga_frena_sin_candidatos(self):
        filtros = ElementoFalso("Filtros", caja={
            "x": 1243, "y": 595, "width": 101, "height": 40})
        flecha_fila = ElementoFalso("", caja={
            "x": 1286, "y": 650, "width": 24, "height": 24})
        pagina = PaginaDescargaFalsa([filtros, flecha_fila], filtros)

        with self.assertRaisesRegex(RuntimeError, "encontré 0 candidatos"):
            self.bot._buscar_boton_descarga(pagina, 0)

    def test_excel_se_elige_debajo_del_boton(self):
        filtros = ElementoFalso("Filtros", caja={
            "x": 1243, "y": 595, "width": 101, "height": 40})
        descarga = ElementoFalso("", caja={
            "x": 1352, "y": 595, "width": 40, "height": 40})
        excel_menu = ElementoFalso("Excel", caja={
            "x": 1190, "y": 740, "width": 180, "height": 32})
        excel_modal = ElementoFalso("Excel", caja={
            "x": 1510, "y": 300, "width": 180, "height": 32})
        pagina = PaginaDescargaFalsa(
            [filtros, descarga], filtros, [excel_modal, excel_menu])

        elegido = self.bot._buscar_excel_del_menu(pagina, descarga, 0)

        self.assertIs(elegido, excel_menu)

    def test_excel_realista_dentro_de_30_dias_pasa(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "inventado.xlsx"
            _escribir_excel(ruta, [dt.date.today() - dt.timedelta(days=30)])
            datos = self.bot.validar_excel(ruta)
        self.assertEqual(len(datos["movimientos"]), 1)

    def test_excel_con_fecha_futura_frena(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "inventado.xlsx"
            _escribir_excel(ruta, [dt.date.today() + dt.timedelta(days=1)])
            with self.assertRaisesRegex(RuntimeError, "fecha futura"):
                self.bot.validar_excel(ruta)

    def test_excel_con_fecha_de_hace_40_dias_frena(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "inventado.xlsx"
            _escribir_excel(ruta, [dt.date.today() - dt.timedelta(days=40)])
            with self.assertRaisesRegex(RuntimeError, "anterior a 35 días"):
                self.bot.validar_excel(ruta)

    def test_excel_sin_movimientos_frena(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "inventado.xlsx"
            _escribir_excel(ruta, [])
            with self.assertRaisesRegex(RuntimeError, "sin movimientos"):
                self.bot.validar_excel(ruta)

    def test_excel_con_encabezado_incompatible_frena(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "inventado.xlsx"
            _escribir_excel(ruta, [dt.date.today()], "No es crédito")
            with self.assertRaises(ValueError):
                self.bot.validar_excel(ruta)

    def test_dos_corridas_publican_un_archivo_diario_sin_pisar_temporal(self):
        with tempfile.TemporaryDirectory() as carpeta:
            temporales = Path(carpeta) / "descargas_temp"
            publicados = Path(carpeta) / "galicia"
            temporales.mkdir()
            publicados.mkdir()
            primera = DescargaFalsa(100)
            destino = self._correr_descarga(temporales, publicados, primera)
            self.assertEqual(Path(destino).name,
                             "Movimientos Galicia %s.xlsx" % dt.date.today())
            self.assertFalse(primera.destinos[0].exists())

            segunda = DescargaFalsa(200)
            self.assertEqual(self._correr_descarga(temporales, publicados, segunda), destino)
            self.assertNotEqual(primera.destinos[0], segunda.destinos[0])
            self.assertFalse(segunda.destinos[0].exists())
            self.assertEqual(list(publicados.iterdir()), [Path(destino)])
            libro = load_workbook(destino, read_only=True)
            try:
                self.assertEqual(libro.active["E2"].value, 200)
            finally:
                libro.close()

    def test_validacion_fallida_conserva_temporal_y_publicado_anterior(self):
        with tempfile.TemporaryDirectory() as carpeta:
            temporales = Path(carpeta) / "descargas_temp"
            publicados = Path(carpeta) / "galicia"
            temporales.mkdir()
            publicados.mkdir()
            destino = self._correr_descarga(temporales, publicados, DescargaFalsa(100))
            fallida = DescargaFalsa(200)
            with patch.object(self.bot, "validar_excel", side_effect=ValueError("mal encabezado")):
                with self.assertRaisesRegex(ValueError, "mal encabezado"):
                    self._correr_descarga(temporales, publicados, fallida)
            self.assertTrue(fallida.destinos[0].exists())
            self.assertEqual(list(publicados.iterdir()), [Path(destino)])
            libro = load_workbook(destino, read_only=True)
            try:
                self.assertEqual(libro.active["E2"].value, 100)
            finally:
                libro.close()

    def test_publicacion_fallida_conserva_temporal_y_publicado_anterior(self):
        with tempfile.TemporaryDirectory() as carpeta:
            temporales = Path(carpeta) / "descargas_temp"
            publicados = Path(carpeta) / "galicia"
            temporales.mkdir()
            publicados.mkdir()
            destino = self._correr_descarga(temporales, publicados, DescargaFalsa(100))
            fallida = DescargaFalsa(200)
            with patch("bots.galicia.navar.shutil.copyfile",
                       side_effect=OSError("Drive no disponible")):
                with self.assertRaisesRegex(OSError, "Drive no disponible"):
                    self._correr_descarga(temporales, publicados, fallida)
            self.assertTrue(fallida.destinos[0].exists())
            self.assertEqual(list(publicados.iterdir()), [Path(destino)])
            libro = load_workbook(destino, read_only=True)
            try:
                self.assertEqual(libro.active["E2"].value, 100)
            finally:
                libro.close()

    def test_limpieza_solo_borra_temporales_permitidos_con_mas_de_siete_dias(self):
        with tempfile.TemporaryDirectory() as carpeta:
            temporales = Path(carpeta) / "descargas_temp"
            publicados = Path(carpeta) / "galicia"
            temporales.mkdir()
            publicados.mkdir()
            nombres = ["galicia_por_validar_viejo.xlsx", "descarga.tmp",
                       "galicia_por_validar_nuevo.xlsx", "otro.xlsx", "otro.tmp"]
            for nombre in nombres:
                (temporales / nombre).write_text("inventado")
            viejo = time.time() - 8 * 24 * 60 * 60
            for nombre in ("galicia_por_validar_viejo.xlsx", "descarga.tmp", "otro.xlsx"):
                os.utime(temporales / nombre, (viejo, viejo))
            self._correr_descarga(temporales, publicados, DescargaFalsa())
            self.assertEqual({p.name for p in temporales.iterdir()},
                             {"galicia_por_validar_nuevo.xlsx", "otro.xlsx", "otro.tmp"})

    def test_save_as_fallido_informa_causa_y_playwright(self):
        with tempfile.TemporaryDirectory() as carpeta:
            temporales = Path(carpeta) / "descargas_temp"
            publicados = Path(carpeta) / "galicia"
            temporales.mkdir()
            publicados.mkdir()
            fallida = DescargaFalsa(fallar=True)
            with patch("bots.galicia.navar.log") as registrar,                     patch.object(self.bot, "_rescatar_descarga",
                                 side_effect=RuntimeError("sin archivo nuevo")):
                with self.assertRaisesRegex(RuntimeError, "sin archivo nuevo"):
                    self._correr_descarga(temporales, publicados, fallida)
            self.assertIn("descarga interrumpida", registrar.call_args[0][0])
            self.assertEqual(list(publicados.iterdir()), [])

    def test_rescate_publica_excel_nuevo_y_descarta_anteriores_y_temporal(self):
        with tempfile.TemporaryDirectory() as carpeta:
            temporales = Path(carpeta) / "temp"
            publicados = Path(carpeta) / "salida"
            temporales.mkdir()
            publicados.mkdir()
            anterior = temporales / "anterior.tmp"
            _escribir_excel(anterior, [dt.date.today()], importe=999)
            descarga = DescargaFalsa(fallar=True)

            def llegada():
                _escribir_excel(temporales / "guid.tmp", [dt.date.today()], importe=123)
                (temporales / "galicia_por_validar_parcial.xlsx").write_text("incompleto")

            with patch("bots.galicia.navar.time.sleep"),                     patch("bots.galicia.navar.time.monotonic", side_effect=range(100)):
                destino = self._correr_descarga(
                    temporales, publicados, descarga, al_click=llegada)
            libro = load_workbook(destino)
            self.assertEqual(libro.active["E2"].value, 123)
            libro.close()
            self.assertTrue(anterior.exists())
            self.assertFalse(descarga.destinos[0].exists())

    def test_rescate_frena_con_dos_nuevos(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta)
            def llegada():
                (ruta / "uno.tmp").write_text("uno")
                (ruta / "dos.tmp").write_text("dos")
            with self.assertRaisesRegex(RuntimeError, "2 archivos nuevos"):
                self._correr_descarga(ruta, ruta, DescargaFalsa(fallar=True), llegada)

    def test_rescate_sin_nuevo_no_toma_archivo_anterior(self):
        for con_anterior in (False, True):
            with self.subTest(con_anterior=con_anterior), tempfile.TemporaryDirectory() as carpeta:
                ruta = Path(carpeta)
                if con_anterior:
                    _escribir_excel(ruta / "viejo.tmp", [dt.date.today()])
                rescatar = self.bot._rescatar_descarga
                def corto(*args, **kwargs):
                    return rescatar(*args, espera=0.001, **kwargs)
                with patch.object(self.bot, "_rescatar_descarga", side_effect=corto):
                    with self.assertRaisesRegex(RuntimeError, "0 archivos nuevos"):
                        self._correr_descarga(ruta, ruta, DescargaFalsa(fallar=True))
                self.assertFalse(list(ruta.glob("Movimientos*")))

    def test_rescate_no_zip_frena(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta)
            with patch("bots.galicia.navar.time.sleep"),                     patch("bots.galicia.navar.time.monotonic", side_effect=range(100)):
                with self.assertRaisesRegex(RuntimeError, "no es zip válido"):
                    self._correr_descarga(
                        ruta, ruta, DescargaFalsa(fallar=True),
                        lambda: (ruta / "guid.tmp").write_text("no es un Excel"))

    def test_rescate_espera_dos_segundos_y_reinicia_si_cambia_tamano(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta)
            candidato = ruta / "guid.tmp"
            _escribir_excel(candidato, [dt.date.today()])
            reloj = [0.0]
            esperas = []
            def dormir(segundos):
                reloj[0] += segundos
                esperas.append(reloj[0])
                if len(esperas) == 5:
                    # Sigue siendo un zip válido, pero la descarga aún crecía.
                    with candidato.open("ab") as archivo:
                        archivo.write(b"mas")
            with patch("bots.galicia.navar.time.monotonic", side_effect=lambda: reloj[0]),                     patch("bots.galicia.navar.time.sleep", side_effect=dormir):
                self.bot._rescatar_descarga(ruta, set(), ruta / "copia.xlsx")
            self.assertGreaterEqual(reloj[0], 3)
            self.assertEqual((ruta / "copia.xlsx").read_bytes(), candidato.read_bytes())

    def test_rescate_archivo_que_no_se_estabiliza_frena(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta)
            candidato = ruta / "guid.tmp"
            candidato.write_bytes(b"a")
            reloj = [0.0]
            def dormir(segundos):
                reloj[0] += segundos
                with candidato.open("ab") as archivo:
                    archivo.write(b"a")
            with patch("bots.galicia.navar.time.monotonic", side_effect=lambda: reloj[0]),                     patch("bots.galicia.navar.time.sleep", side_effect=dormir):
                with self.assertRaisesRegex(RuntimeError, "no se estabilizó"):
                    self.bot._rescatar_descarga(ruta, set(), ruta / "copia.xlsx", espera=3)

    def test_save_as_exitoso_no_busca_rescate(self):
        with tempfile.TemporaryDirectory() as carpeta:
            with patch.object(self.bot, "_rescatar_descarga") as rescatar:
                self._correr_descarga(Path(carpeta), Path(carpeta), DescargaFalsa())
            rescatar.assert_not_called()

    def test_nombre_incorrecto_no_llega_al_rescate(self):
        with tempfile.TemporaryDirectory() as carpeta:
            descarga = DescargaFalsa(fallar=True)
            descarga.suggested_filename = "Extracto_CC999999999.xlsx"
            with patch.object(self.bot, "_rescatar_descarga") as rescatar:
                with self.assertRaisesRegex(RuntimeError, "cuenta pedida"):
                    self._correr_descarga(Path(carpeta), Path(carpeta), descarga)
            rescatar.assert_not_called()
            self.assertEqual(descarga.destinos, [])

    def test_eventos_de_pagina_quedan_registrados(self):
        eventos, contexto = {}, {}
        pagina = SimpleNamespace(
            on=lambda evento, funcion: eventos.update({evento: funcion}),
            context=SimpleNamespace(
                on=lambda evento, funcion: contexto.update({evento: funcion})))
        with patch("bots.galicia.navar.log") as registrar:
            self.bot._registrar_eventos_descarga(pagina)
            eventos["close"]()
            eventos["crash"]()
            contexto["page"](SimpleNamespace(url="https://ejemplo.invalid/descarga"))
        textos = [c.args[0] for c in registrar.call_args_list]
        self.assertIn("la página se cerró", textos[0])
        self.assertIn("la página se cayó", textos[1])
        self.assertIn("https://ejemplo.invalid/descarga", textos[2])

    def test_rescate_desde_downloads_publica_y_borra_guid(self):
        descargas = self.home / "Downloads"
        descargas.mkdir()
        guid = descargas / "ABCDEF12-1234-1234-1234-123456789ABC.TMP"
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta)
            def llegada():
                _escribir_excel(guid, [dt.date.today()])
                os.utime(guid, (time.time() + 1, time.time() + 1))
            with patch("bots.galicia.navar.time.sleep"),                     patch("bots.galicia.navar.time.monotonic", side_effect=range(100)):
                destino = self._correr_descarga(ruta, ruta, DescargaFalsa(fallar=True), llegada)
            self.assertTrue(Path(destino).exists())
            self.assertFalse(guid.exists())

    def test_downloads_ignora_anterior_nombre_comun_y_fecha_anterior(self):
        for caso in ("ya estaba", "nombre común", "fecha anterior"):
            with self.subTest(caso=caso), tempfile.TemporaryDirectory() as carpeta:
                descargas = self.home / "Downloads"
                descargas.mkdir(exist_ok=True)
                archivo = descargas / (
                    "informe.xlsx" if caso == "nombre común"
                    else "abcdef12-1234-1234-1234-123456789abc.tmp")
                def escribir():
                    _escribir_excel(archivo, [dt.date.today()])
                    if caso == "fecha anterior":
                        os.utime(archivo, (time.time() - 60, time.time() - 60))
                if caso == "ya estaba":
                    escribir()
                rescatar = self.bot._rescatar_descarga
                def corto(*args, **kwargs):
                    return rescatar(*args, espera=0.001, **kwargs)
                with patch.object(self.bot, "_rescatar_descarga", side_effect=corto):
                    with self.assertRaisesRegex(RuntimeError, "Downloads: 0 archivos nuevos"):
                        self._correr_descarga(
                            Path(carpeta), Path(carpeta), DescargaFalsa(fallar=True),
                            None if caso == "ya estaba" else escribir)
                self.assertTrue(archivo.exists())
                archivo.unlink()

    def test_rescate_candidatos_en_ambas_carpetas_frena(self):
        descargas = self.home / "Downloads"
        descargas.mkdir()
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta)
            def llegada():
                for archivo in (ruta / "bot.tmp",
                                descargas / "abcdef12-1234-1234-1234-123456789abc.tmp"):
                    _escribir_excel(archivo, [dt.date.today()])
                    os.utime(archivo, (time.time() + 1, time.time() + 1))
            with self.assertRaisesRegex(RuntimeError, "2 archivos nuevos") as error:
                self._correr_descarga(ruta, ruta, DescargaFalsa(fallar=True), llegada)
            self.assertIn(str(descargas), str(error.exception))
            self.assertIn("bot.tmp", str(error.exception))

    def test_limpieza_downloads_solo_guid_viejo_con_formato_galicia(self):
        descargas = self.home / "Downloads"
        descargas.mkdir()
        archivos = [
            descargas / ("%08x-1234-1234-1234-123456789abc.tmp" % i)
            for i in range(5)]
        viejo_galicia, nuevo_galicia, no_zip, otra_hoja, otro_encabezado = archivos
        _escribir_excel(viejo_galicia, [dt.date.today()])
        _escribir_excel(nuevo_galicia, [dt.date.today()])
        no_zip.write_text("ajeno")
        for archivo, hoja, encabezado in (
                (otra_hoja, "Otra", "Fecha"), (otro_encabezado, "Movimientos", "Otro")):
            libro = Workbook()
            libro.active.title = hoja
            libro.active["A1"] = encabezado
            libro.save(archivo)
        cualquiera = descargas / "informe.xlsx"
        _escribir_excel(cualquiera, [dt.date.today()])
        viejo = time.time() - 8 * 24 * 60 * 60
        for archivo in [viejo_galicia, no_zip, otra_hoja, otro_encabezado, cualquiera]:
            os.utime(archivo, (viejo, viejo))
        with tempfile.TemporaryDirectory() as carpeta:
            self._correr_descarga(Path(carpeta), Path(carpeta), DescargaFalsa())
        self.assertFalse(viejo_galicia.exists())
        for archivo in [nuevo_galicia, no_zip, otra_hoja, otro_encabezado, cualquiera]:
            self.assertTrue(archivo.exists(), archivo.name)

    def test_rescate_avisa_si_no_puede_borrar_downloads_y_publica(self):
        descargas = self.home / "Downloads"
        descargas.mkdir()
        guid = descargas / "abcdef12-1234-1234-1234-123456789abc.tmp"
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta)
            def llegada():
                _escribir_excel(guid, [dt.date.today()])
                os.utime(guid, (time.time() + 1, time.time() + 1))
            with patch("bots.galicia.navar.time.sleep"),                     patch("bots.galicia.navar.time.monotonic", side_effect=range(100)),                     patch.object(Path, "unlink", side_effect=PermissionError("ocupado")),                     patch("bots.galicia.navar.log") as registrar:
                destino = self._correr_descarga(ruta, ruta, DescargaFalsa(fallar=True), llegada)
            self.assertTrue(Path(destino).exists())
            self.assertTrue(guid.exists())
            self.assertTrue(any("no pude borrar" in c.args[0] for c in registrar.call_args_list))

    def test_filtro_no_toca_la_pagina(self):
        pagina = PaginaQueNoSePuedeTocar()
        self.assertTrue(self.bot.aplicar_filtro_fechas(
            pagina, dt.date.today(), dt.date.today(), 10))

    def test_carpeta_drive_se_resuelve_desde_variable(self):
        from orquestador.correr import correr_banco

        with tempfile.TemporaryDirectory() as carpeta:
            destino = Path(carpeta) / "Bancos" / "galicia"
            destino.mkdir(parents=True)
            recibida = {}

            def corrida_falsa(bot, ctx, usuario, clave):
                recibida["carpeta"] = ctx.carpeta_drive
                return {"fallaron": [], "ok": ["NAVAR SA"], "sin_novedades": []}

            with patch.dict(os.environ, {"FINAUTO_DRIVE": carpeta}), \
                    patch("orquestador.correr._cred.cargar", return_value=("usuario", "clave")), \
                    patch("orquestador.correr._loop.correr", side_effect=corrida_falsa):
                correr_banco("navar", "galicia")

        self.assertEqual(Path(recibida["carpeta"]), destino)

    def test_carpeta_inexistente_frena_antes_del_llavero(self):
        from orquestador.correr import correr_banco

        with tempfile.TemporaryDirectory() as carpeta:
            with patch.dict(os.environ, {"FINAUTO_DRIVE": carpeta}), \
                    patch("orquestador.correr._cred.cargar",
                          side_effect=AssertionError("Tocó el llavero")):
                with self.assertRaisesRegex(SystemExit, r"Bancos/galicia"):
                    correr_banco("navar", "galicia")

    def test_empresa_y_perfil(self):
        self.assertTrue(self.cfg["solo_empresa_activa"])
        self.assertNotIn("backfill_dias_primera_vez", self.cfg)
        pagina = PaginaConTextos([
            ("NAVAR SOCIEDAD ANONIMA", True),
            ("NAVAR SOCIEDAD ANÓNIMA - CONSUMO MASIVO", True),
        ])
        self.assertEqual(self.bot.capturar_empresa_activa(pagina), "NAVAR SA")

    def test_empresa_unica_no_hace_clics(self):
        pagina = PaginaQueNoSePuedeTocar()
        self.assertEqual(self.bot.descubrir_empresas(pagina, 10, []), [])
        with self.assertRaisesRegex(RuntimeError, "una sola empresa activa"):
            self.bot.cambiar_a_empresa(pagina, "NAVAR SA", 10)


if __name__ == "__main__":
    unittest.main()
