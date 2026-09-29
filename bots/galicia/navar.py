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
        """Encuentra la flechita de descarga por su posición junto a Filtros."""
        filtros = self._esperar_unico_visible(page, [
            lambda: page.locator("button[aria-label='filter2']"),
            lambda: page.locator("button").filter(
                has_text=re.compile(r"^\s*Filtros\s*$")),
        ], "el botón Filtros de Movimientos", timeout)

        caja_filtros = filtros.bounding_box()
        if not caja_filtros:
            raise RuntimeError("el botón Filtros no tiene una posición legible")

        limite = time.monotonic() + max(timeout, 0) / 1000.0
        cantidad = 0
        while True:
            candidatos = []
            try:
                botones = page.locator("button")
                centro_y_filtros = caja_filtros["y"] + caja_filtros["height"] / 2
                borde_derecho_filtros = caja_filtros["x"] + caja_filtros["width"]
                for i in range(botones.count()):
                    boton = botones.nth(i)
                    if not boton.is_visible():
                        continue
                    caja = boton.bounding_box()
                    texto = (boton.inner_text() or "").strip()
                    if not caja or texto:
                        continue
                    centro_y = caja["y"] + caja["height"] / 2
                    if (abs(centro_y - centro_y_filtros) <= 10 and
                            borde_derecho_filtros <= caja["x"] <=
                            borde_derecho_filtros + 60):
                        candidatos.append(boton)
                cantidad = len(candidatos)
            except Exception:
                # Galicia reconstruye la barra mientras carga; volvemos a mirar hasta el límite.
                candidatos = []
                cantidad = 0

            if cantidad > 1:
                raise RuntimeError(
                    "el botón de descarga junto a Filtros: encontré %d candidatos" % cantidad)
            if cantidad == 1:
                return candidatos[0]

            restante_ms = int((limite - time.monotonic()) * 1000)
            if restante_ms <= 0:
                # La flechita no tiene nombre propio y la página deja copias escondidas;
                # por eso se reconoce solo al botón vacío ubicado junto a Filtros.
                raise RuntimeError(
                    "el botón de descarga junto a Filtros: encontré %d candidatos" % cantidad)
            page.wait_for_timeout(min(200, restante_ms))

    @staticmethod
    def _buscar_excel_del_menu(page, boton_descarga, timeout):
        """Encuentra el Excel del menú abierto y descarta los modales escondidos."""
        caja_boton = boton_descarga.bounding_box()
        if not caja_boton:
            raise RuntimeError("el botón de descarga no tiene una posición legible")

        limite = time.monotonic() + max(timeout, 0) / 1000.0
        cantidad = 0
        while True:
            candidatos = []
            try:
                opciones = page.get_by_text("Excel", exact=True)
                borde_inferior = caja_boton["y"] + caja_boton["height"]
                centro_x_boton = caja_boton["x"] + caja_boton["width"] / 2
                for i in range(opciones.count()):
                    opcion = opciones.nth(i)
                    if not opcion.is_visible():
                        continue
                    caja = opcion.bounding_box()
                    if not caja:
                        continue
                    centro_x = caja["x"] + caja["width"] / 2
                    distancia_vertical = caja["y"] - borde_inferior
                    if (0 <= distancia_vertical < 400 and
                            centro_x_boton - 300 <= centro_x <= centro_x_boton + 50):
                        candidatos.append(opcion)
                cantidad = len(candidatos)
            except Exception:
                candidatos = []
                cantidad = 0

            if cantidad > 1:
                raise RuntimeError(
                    "la opción Excel del menú: encontré %d candidatos" % cantidad)
            if cantidad == 1:
                return candidatos[0]

            restante_ms = int((limite - time.monotonic()) * 1000)
            if restante_ms <= 0:
                raise RuntimeError(
                    "la opción Excel del menú: encontré %d candidatos" % cantidad)
            page.wait_for_timeout(min(200, restante_ms))

    @staticmethod
    def _registrar_eventos_descarga(page):
        """El diagnóstico no debe frenar una descarga ni depender de una página viva."""
        def registrar(mensaje):
            try:
                log(mensaje)
            except Exception:
                pass

        def nueva_pagina(pagina):
            try:
                url = pagina.url or "(sin URL)"
            except Exception:
                url = "(sin URL)"
            registrar("   se abrió una pestaña nueva: %s" % url)

        for evento, mensaje in (
                ("close", "   la página se cerró"),
                ("crash", "   la página se cayó")):
            try:
                page.on(evento, lambda *args, texto=mensaje: registrar(texto))
            except Exception:
                pass
        try:
            page.context.on("page", nueva_pagina)
        except Exception:
            pass

    @staticmethod
    def _es_guid_tmp(nombre):
        return re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.tmp",
            nombre, re.I) is not None

    @staticmethod
    def _limpiar_descargas_usuario(carpeta, limite):
        # Descargas es compartida con la persona: no alcanza el nombre para borrar.
        # Sólo limpiamos el formato observado de Galicia y con más de una semana.
        import zipfile
        from openpyxl import load_workbook

        for archivo in carpeta.iterdir():
            try:
                if (not BotGaliciaNavar._es_guid_tmp(archivo.name)
                        or not archivo.is_file() or archivo.stat().st_mtime >= limite
                        or not zipfile.is_zipfile(archivo)):
                    continue
                with archivo.open("rb") as entrada:
                    libro = load_workbook(entrada, read_only=True, data_only=True)
                    try:
                        es_galicia = ("Movimientos" in libro.sheetnames
                                      and libro["Movimientos"]["A1"].value == "Fecha")
                    finally:
                        libro.close()
                if es_galicia:
                    archivo.unlink()
            except Exception as e:
                log("   Aviso: no limpié %s: %s" % (archivo, e))

    @staticmethod
    def _rescatar_descarga(carpeta, anteriores, temporal, espera=30, estabilidad=2,
                          usuario=None, anteriores_usuario=None, clic=None):
        # El 28/09 vimos que al cerrarse la página Chromium puede dejar el Excel
        # en Descargas del usuario, fuera de downloads_path. No repetimos el login.
        import zipfile

        carpetas = [(carpeta, anteriores, False)]
        if usuario is not None:
            carpetas.append((usuario, anteriores_usuario or set(), True))
        limite = time.monotonic() + espera
        observado = estable_desde = None
        while True:
            ahora = time.monotonic()
            nuevos, detalles = [], []
            lectura_fallida = False
            for ruta, previos, estricta in carpetas:
                try:
                    candidatos = []
                    for p in ruta.iterdir():
                        if p.name in previos or not p.is_file():
                            continue
                        if estricta:
                            if (not BotGaliciaNavar._es_guid_tmp(p.name)
                                    or clic is None or p.stat().st_mtime <= clic):
                                continue
                        elif p.name.startswith("galicia_por_validar_"):
                            continue
                        candidatos.append(p)
                    candidatos.sort(key=lambda p: p.name)
                    nuevos.extend((p, estricta) for p in candidatos)
                    detalles.append("%s: %d archivos nuevos (%s)" % (
                        ruta, len(candidatos), ", ".join(p.name for p in candidatos)))
                except OSError as e:
                    lectura_fallida = True
                    detalles.append("%s: no pude leer: %s" % (ruta, e))
            if len(nuevos) > 1:
                raise RuntimeError("Rescate: encontré %d archivos nuevos; no elijo uno. %s" %
                                   (len(nuevos), "; ".join(detalles)))
            try:
                if len(nuevos) == 1 and not lectura_fallida:
                    candidato, es_usuario = nuevos[0]
                    tamano = candidato.stat().st_size
                    identidad = (str(candidato), tamano)
                    if identidad != observado:
                        observado, estable_desde = identidad, ahora
                    detalles.append("%s, %d bytes; todavía no se estabilizó" % identidad)
                    if ahora - estable_desde >= estabilidad:
                        if zipfile.is_zipfile(candidato):
                            shutil.copyfile(candidato, temporal)
                            if es_usuario:
                                try:
                                    candidato.unlink()
                                except OSError as e:
                                    log("   Aviso: rescaté pero no pude borrar %s: %s" %
                                        (candidato, e))
                            log("   La página se cerró al guardar; tomé el archivo que dejó "
                                "el navegador (%s, %d bytes)" % identidad)
                            return
                        detalles[-1] = "%s, %d bytes; no es zip válido" % identidad
                else:
                    observado = estable_desde = None
            except OSError as e:
                observado = estable_desde = None
                detalles.append("no pude leer o copiar el archivo: %s" % e)
            restante = limite - time.monotonic()
            if restante <= 0:
                raise RuntimeError("Rescate agotado: busqué un único archivo nuevo; %s." %
                                   "; ".join(detalles))
            time.sleep(min(0.2, restante))

    def descargar_csv(self, page, carpeta_destino, nombre_empresa, timeout, ctx):
        # El nombre del método viene del contrato compartido; NAVAR publica un Excel.
        if _empresa(nombre_empresa) not in self.empresas:
            raise RuntimeError("Falta confirmar la empresa antes de descargar.")

        # Conservamos una semana de descargas fallidas para poder revisarlas.
        # El temporal único evita pisar otra corrida; no explica el cierre
        # intermitente observado el 28/09 (también ocurrió con nombre único).
        limite_antiguos = time.time() - 7 * 24 * 60 * 60
        carpeta_temporales = Path(ctx.descargas_dir)
        for patron in ("galicia_por_validar_*.xlsx", "*.tmp"):
            for antiguo in carpeta_temporales.glob(patron):
                try:
                    if antiguo.is_file() and antiguo.stat().st_mtime < limite_antiguos:
                        antiguo.unlink()
                except OSError as e:
                    log("   Aviso: no pude borrar temporal viejo %s: %s" %
                        (antiguo.name, e))

        usuario = Path.home() / "Downloads"
        if usuario.is_dir() and usuario.resolve() != carpeta_temporales.resolve():
            self._limpiar_descargas_usuario(usuario, limite_antiguos)
        else:
            usuario = None

        boton = self._buscar_boton_descarga(page, timeout)
        boton.click(timeout=timeout)
        captura(page, "menu_descarga")
        excel = self._buscar_excel_del_menu(page, boton, timeout)

        self._registrar_eventos_descarga(page)
        anteriores = {p.name for p in carpeta_temporales.iterdir() if p.is_file()}
        anteriores_usuario = ({p.name for p in usuario.iterdir() if p.is_file()}
                              if usuario is not None else set())
        with page.expect_download(timeout=timeout) as info:
            clic = time.time()
            excel.click(timeout=timeout)
        descarga = info.value
        nombre_origen = self._validar_nombre_descarga(descarga.suggested_filename)

        # Cada corrida usa su propio temporal: nunca pisamos el de otra corrida.
        import uuid
        temporal = os.path.join(
            ctx.descargas_dir,
            "galicia_por_validar_%s_%s.xlsx" % (
                datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S_%f"),
                uuid.uuid4().hex))
        try:
            descarga.save_as(temporal)
        except Exception as e:
            try:
                motivo = descarga.failure()
            except Exception as consulta_error:
                motivo = "no se pudo consultar: %s" % consulta_error
            log("   Falló guardar descarga de Galicia: %s; Playwright: %s" %
                (e, motivo or "sin detalle"))
            self._rescatar_descarga(
                carpeta_temporales, anteriores, temporal, usuario=usuario,
                anteriores_usuario=anteriores_usuario, clic=clic)
        self.validar_excel(temporal)

        # El archivo publicado lleva la fecha de la descarga. Una nueva corrida
        # del mismo día reemplaza ese archivo con la versión más reciente.
        nombre = "%s %s.xlsx" % (
            self.prefijo, datetime.date.today().isoformat())
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
        try:
            os.remove(temporal)
        except OSError as e:
            log("   Aviso: se publicó, pero no pude borrar el temporal %s: %s" %
                (os.path.basename(temporal), e))
        log("   Descargado y validado: %s (origen: %s)" % (
            os.path.basename(destino), nombre_origen))
        return destino

    def extraer_cuenta_id(self, archivo_csv):
        return self.cuenta
