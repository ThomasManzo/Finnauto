# -*- coding: utf-8 -*-
"""Recorrido observado de Galicia para NAVAR, con frenos antes de cada clic."""
import datetime
import os
import re
import shutil
import tempfile
import time
from pathlib import Path

from bots.galicia.bot import BotGalicia
from nucleo.log import log, captura
from nucleo.utilidades import _parse_monto


URL_LOGIN = "https://empresas.bancogalicia.com.ar/login"
PATRON_EMPRESA = re.compile(
    r"NAVAR\s+(?:S\.?\s*A\.?|SOCIEDAD\s+AN[OÓ]NIMA)", re.I)


def _empresa(texto):
    return re.sub(r"[\s.]", "", texto or "").upper()


class BotGaliciaNavar(BotGalicia):
    def __init__(self, cfg):
        super().__init__()
        self.cuenta = cfg["cuenta"]
        self.empresas = {_empresa(n) for n in cfg["solo_estas_empresas"]}
        self.prefijo = cfg["prefijo_archivo"]
        # El nombre que entrega Galicia usa la cuenta sin separadores ni ceros iniciales.
        self.cuenta_en_archivo = re.sub(r"\D", "", self.cuenta).lstrip("0") or "0"

    @staticmethod
    def _esperar_unico_visible(page, opciones, descripcion, timeout):
        """Espera una alternativa con un solo elemento visible; ignora sus copias ocultas."""
        limite = time.monotonic() + max(timeout, 0) / 1000.0
        ultimo_error = None
        while True:
            for opcion in opciones:
                try:
                    locator = opcion() if callable(opcion) else opcion
                    visibles = [locator.nth(i) for i in range(locator.count())
                                if locator.nth(i).is_visible()]
                except Exception as e:
                    ultimo_error = e
                    continue
                if len(visibles) > 1:
                    raise RuntimeError("%s aparece %d veces visible" % (
                        descripcion, len(visibles)))
                if len(visibles) == 1:
                    return visibles[0]

            restante_ms = int((limite - time.monotonic()) * 1000)
            if restante_ms <= 0:
                detalle = " (%s)" % str(ultimo_error)[:100] if ultimo_error else ""
                raise RuntimeError("%s no apareció visible en %.1f s%s" % (
                    descripcion, max(timeout, 0) / 1000.0, detalle))
            page.wait_for_timeout(min(200, restante_ms))

    @staticmethod
    def _esperar_alguno_visible(page, opcion, descripcion, timeout):
        """Espera al menos una coincidencia visible; puede haber varias válidas."""
        limite = time.monotonic() + max(timeout, 0) / 1000.0
        while True:
            try:
                locator = opcion() if callable(opcion) else opcion
                for i in range(locator.count()):
                    if locator.nth(i).is_visible():
                        return locator.nth(i)
            except Exception:
                # La página puede reconstruirse mientras termina de cargar.
                pass
            restante_ms = int((limite - time.monotonic()) * 1000)
            if restante_ms <= 0:
                raise RuntimeError("%s no apareció visible en %.1f s" % (
                    descripcion, max(timeout, 0) / 1000.0))
            page.wait_for_timeout(min(200, restante_ms))

    def hacer_login(self, page, usuario, clave, timeout):
        """Entra por el formulario directo y hace un solo intento para no bloquear el usuario."""
        log("Abriendo el login directo de Galicia...")
        page.goto(URL_LOGIN, timeout=timeout)

        try:
            # La etiqueta tiene su propio aria-label: buscar por etiqueta devuelve
            # la etiqueta y el campo. Estos id son los vistos en el formulario del 27/09.
            campo_usuario = self._esperar_unico_visible(page, [
                lambda: page.locator("input#userInput"),
                lambda: page.get_by_role("textbox", name="Usuario", exact=True),
            ], "el campo Usuario", timeout)
            campo_clave = self._esperar_unico_visible(page, [
                lambda: page.locator("input#userPassword"),
                lambda: page.locator("input[type='password']"),
            ], "el campo Clave", timeout)
            ingresar = self._esperar_unico_visible(page, [
                lambda: page.get_by_role("button", name="Ingresar", exact=True),
            ], "el botón Ingresar", timeout)
        except Exception:
            captura(page, "ERROR_formulario_login")
            raise

        captura(page, "pantalla_login")
        campo_usuario.fill(usuario, timeout=timeout)
        campo_clave.fill(clave, timeout=timeout)
        captura(page, "clave_cargada")

        try:
            ingresar.click(timeout=timeout)
            captura(page, "login_enviado")
            campo_usuario.wait_for(state="hidden", timeout=timeout)
            self._esperar_alguno_visible(
                page, lambda: page.get_by_text(PATRON_EMPRESA),
                "el nombre de la empresa después del login", timeout)
        except Exception:
            captura(page, "ERROR_login_no_confirmado")
            raise
        captura(page, "post_login")
        log("Login confirmado.")

    def capturar_empresa_activa(self, page):
        # El nombre aparece más de una vez en el inicio; alcanza con una copia visible.
        try:
            coincidencias = page.get_by_text(PATRON_EMPRESA)
            if any(coincidencias.nth(i).is_visible() for i in range(coincidencias.count())):
                return "NAVAR SA"
        except Exception:
            pass
        return None

    def descubrir_empresas(self, page, timeout, excluir, solo=None):
        return []

    def cambiar_a_empresa(self, page, nombre, timeout):
        raise RuntimeError("Galicia NAVAR tiene una sola empresa activa; no se abre el selector.")

    def _patron_cuenta(self):
        partes = [re.escape(parte) for parte in self.cuenta.split()]
        return re.compile(r"N[°º]\s*%s" % r"\s+".join(partes), re.I)

    def _esperar_cuenta_abierta(self, page, timeout):
        """Confirma URL y título; el número puede repetirse en la pantalla de movimientos."""
        limite = time.monotonic() + max(timeout, 0) / 1000.0
        vio_numero = False
        url_actual = ""
        while True:
            try:
                url_actual = str(page.url or "")
                numeros = page.get_by_text(self._patron_cuenta())
                vio_numero = any(numeros.nth(i).is_visible() for i in range(numeros.count()))
            except Exception:
                vio_numero = False
            if "/cuentas/movimientos" in url_actual and vio_numero:
                return
            restante_ms = int((limite - time.monotonic()) * 1000)
            if restante_ms <= 0:
                raise RuntimeError(
                    "la cuenta no quedó confirmada: URL=%s; número visible=%s" %
                    (url_actual or "(sin URL)", "sí" if vio_numero else "no"))
            page.wait_for_timeout(min(200, restante_ms))

    def ir_a_cuenta(self, page, timeout):
        if _empresa(self.capturar_empresa_activa(page)) not in self.empresas:
            raise RuntimeError("No pude confirmar la empresa de NAVAR; revisar captura.")

        captura(page, "inicio")
        tarjeta = self._esperar_unico_visible(page, [
            lambda: page.get_by_text(self._patron_cuenta()),
        ], "la tarjeta de la cuenta %s" % self.cuenta, timeout)
        tarjeta.click(timeout=timeout)
        self._esperar_cuenta_abierta(page, timeout)
        captura(page, "cuenta_abierta")

    def capturar_saldos(self, page):
        """Lee Actual y Disponible dentro de la tarjeta Saldos; un faltante no corta movimientos."""
        resultado = {"actual_texto": None, "actual": None,
                     "disponible_texto": None, "disponible": None}
        for clave, etiqueta in (("actual", "Actual"), ("disponible", "Disponible")):
            # Parte del título Saldos y toma el primer importe hermano de la etiqueta.
            xpath = (
                "xpath=//*[normalize-space(.)='Saldos']/ancestor::*["
                ".//*[normalize-space(.)='Actual'] and "
                ".//*[normalize-space(.)='Disponible']][1]"
                "//*[normalize-space(.)='%s']/following-sibling::*[1]" % etiqueta)
            try:
                monto = self._esperar_unico_visible(
                    page, [lambda ruta=xpath: page.locator(ruta)],
                    "el saldo %s" % etiqueta, 6000)
                texto = (monto.inner_text(timeout=6000) or "").strip()
                valor = _parse_monto(texto)
                if valor is None:
                    raise ValueError("el monto '%s' no es legible" % texto)
                resultado[clave + "_texto"] = texto
                resultado[clave] = valor
            except Exception as e:
                log("   Aviso: no pude leer saldo '%s': %s" % (etiqueta, str(e)[:120]))
        captura(page, "saldos")
        return resultado

    def aplicar_filtro_fechas(self, page, desde, hasta, timeout):
        log("Galicia NAVAR no usa filtro: baja los últimos 30 días que trae el banco")
        return True

    def validar_excel(self, ruta):
        from lector.extractos import leer_planilla_galicia

        datos = leer_planilla_galicia(ruta)
        if not datos["movimientos"]:
            raise RuntimeError("Excel sin movimientos legibles; revisar antes de marcarlo al día.")

        hoy = datetime.date.today()
        limite_viejo = hoy - datetime.timedelta(days=35)
        for movimiento in datos["movimientos"]:
            fecha = datetime.date.fromisoformat(str(movimiento["fecha"])[:10])
            if fecha > hoy:
                raise RuntimeError("El Excel trae un movimiento con fecha futura: %s." % fecha)
            if fecha < limite_viejo:
                raise RuntimeError("El Excel trae un movimiento anterior a 35 días: %s." % fecha)
        return datos

    def _validar_nombre_descarga(self, nombre):
        nombre = os.path.basename(nombre or "")
        if Path(nombre).suffix.lower() != ".xlsx":
            raise RuntimeError("El banco no entregó un archivo XLSX.")
        digitos_nombre = re.sub(r"\D", "", Path(nombre).stem)
        if self.cuenta_en_archivo not in digitos_nombre:
            raise RuntimeError("El nombre del archivo no permite confirmar la cuenta pedida.")
        return nombre

    def _buscar_boton_descarga(self, page, timeout):
        # Si el ícono no tiene nombre accesible, usamos el botón inmediatamente
        # posterior a Filtros en los controles de Movimientos.
        filtros = self._esperar_unico_visible(page, [
            lambda: page.get_by_role("button", name="Filtros", exact=True),
        ], "el botón Filtros de Movimientos", timeout)
        return self._esperar_unico_visible(page, [
            lambda: page.get_by_role("button", name=re.compile(r"descarg", re.I)),
            lambda: page.locator("button[aria-label*='descarg' i]"),
            lambda: filtros.locator("xpath=following::button[1]"),
        ], "el botón de descarga junto a Filtros", timeout)

    def descargar_csv(self, page, carpeta_destino, nombre_empresa, timeout, ctx):
        # El nombre del método viene del contrato compartido; NAVAR publica un Excel.
        if _empresa(nombre_empresa) not in self.empresas:
            raise RuntimeError("Falta confirmar la empresa antes de descargar.")

        boton = self._buscar_boton_descarga(page, timeout)
        boton.click(timeout=timeout)
        captura(page, "menu_descarga")
        excel = self._esperar_unico_visible(page, [
            lambda: page.get_by_text("Excel", exact=True),
            lambda: page.get_by_role("menuitem", name="Excel", exact=True),
        ], "la opción Excel", timeout)

        with page.expect_download(timeout=timeout) as info:
            excel.click(timeout=timeout)
        descarga = info.value
        nombre_origen = self._validar_nombre_descarga(descarga.suggested_filename)

        temporal = os.path.join(ctx.descargas_dir, "galicia_por_validar.xlsx")
        descarga.save_as(temporal)
        self.validar_excel(temporal)

        nombre = "%s %s.xlsx" % (
            self.prefijo, datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S_%f"))
        destino = os.path.join(carpeta_destino, nombre)
        # Drive ve el archivo sólo después de copiarlo completo y validarlo.
        fd, parcial = tempfile.mkstemp(suffix=".part", dir=carpeta_destino)
        os.close(fd)
        try:
            shutil.copyfile(temporal, parcial)
            os.replace(parcial, destino)
        finally:
            if os.path.exists(parcial):
                os.remove(parcial)
        log("   Descargado y validado: %s (origen: %s)" % (
            os.path.basename(destino), nombre_origen))
        return destino

    def extraer_cuenta_id(self, archivo_csv):
        return self.cuenta
