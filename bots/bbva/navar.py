# -*- coding: utf-8 -*-
"""
bots.bbva.navar — baja los movimientos de las dos cuentas corrientes de NAVAR en BBVA.

EL RECORRIDO (lo describió Thomas mirando la pantalla el 03/10/2026)
    1. Login: "Código de empresa", "Código de usuario" y "Clave de acceso". Un solo intento:
       si algo no está como esperamos, se corta ANTES de apretar Ingresar, para no bloquear
       el usuario (pasó con Macro el 28/09).
    2. Inicio: se confirma NAVAR SA por el CUIT. En "Cuentas en pesos" se aprieta el + y
       aparecen las dos cuentas corrientes.
    3. Clic en la primera cuenta -> "Saldos y movimientos" -> "Descargar" baja un Excel (.xls)
       con los últimos 60 días.
    4. Clic en el número de cuenta -> se elige la segunda -> "Descargar" otra vez.

CADA ARCHIVO SE CONTROLA ANTES DE PUBLICARLO
    El Excel trae en el encabezado la empresa (con CUIT) y la cuenta. Si no dice la cuenta que
    pedimos o no es NAVAR, no se publica. Así, si la pantalla no llegó a cambiar de cuenta y
    bajamos dos veces la misma, salta el error en vez de esconder una cuenta.

QUÉ QUEDA EN DRIVE (NAVAR - Datos/Bancos/bbva)
    Movimientos BBVA 489-000765-9 AAAA-MM-DD.xls
    Movimientos BBVA 489-000806-5 AAAA-MM-DD.xls
    (la barra de la cuenta no puede ir en un nombre de archivo; va un guion)
    El lector de extractos los junta y no repite movimientos.
"""
import datetime
import os
import re
import shutil
import tempfile
import time
import uuid
from pathlib import Path

from bots.base import BotBanco
from nucleo.log import log, captura
from nucleo.utilidades import _parse_monto


URL_LOGIN = "https://netcash.bbva.com.ar/local_pibee/SolicitarCredenciales.html"
CUIT_NAVAR = "30558525025"
# El CUIT aparece con guiones en pantalla ("30-55852502-5").
PATRON_CUIT = re.compile(r"30-?55852502-?5")
PATRON_NAVAR = re.compile(r"\bNAVAR\s+S\.?\s*A\b", re.I)
# Cuánto se espera el inicio después de Ingresar.
ESPERA_INICIO_MS = 240000
# Los campos del login por su id (el usuario también se tipea oculto, como la clave).
IDS_LOGIN = {"Código de empresa": "cod_emp", "Código de usuario": "cod_usu",
             "Clave de acceso": "eai_password"}
# Un movimiento puede venir fechado hasta el día hábil siguiente (el 03/10 bajó uno del 01/10
# con fecha 02/10). Más adelante que esto ya no es un corrimiento de fecha: es un error.
DIAS_ADELANTE_TOLERADOS = 4
# El banco entrega 60 días; dejamos margen para no frenar por un día de diferencia.
DIAS_ATRAS_TOLERADOS = 65


def _marcos(page):
    """La página y sus marcos internos: el login de BBVA podría vivir dentro de un iframe."""
    try:
        return list(page.frames) or [page]
    except Exception:
        return [page]


def _visibles(locator):
    return [locator.nth(i) for i in range(locator.count()) if locator.nth(i).is_visible()]


def _esperar_unico(page, fabricas, descripcion, timeout):
    """Espera un único elemento visible. Cada 'fábrica' recibe un marco y devuelve un locator.

    Si una forma de buscar encuentra dos visibles, se corta: apretar el equivocado es peor que
    no apretar nada.
    """
    limite = time.monotonic() + max(timeout, 0) / 1000.0
    ultimo_error = None
    while True:
        for fabrica in fabricas:
            encontrados = []
            for marco in _marcos(page):
                try:
                    encontrados += _visibles(fabrica(marco))
                except Exception as e:
                    # La página se reconstruye mientras carga: se vuelve a mirar.
                    ultimo_error = e
            if len(encontrados) > 1:
                raise RuntimeError("%s aparece %d veces visible" % (descripcion, len(encontrados)))
            if len(encontrados) == 1:
                return encontrados[0]
        restante = int((limite - time.monotonic()) * 1000)
        if restante <= 0:
            detalle = " (%s)" % str(ultimo_error)[:100] if ultimo_error else ""
            raise RuntimeError("%s no apareció visible en %.1f s%s" % (
                descripcion, max(timeout, 0) / 1000.0, detalle))
        page.wait_for_timeout(min(250, restante))


def _hay_visible(page, fabrica):
    for marco in _marcos(page):
        try:
            if _visibles(fabrica(marco)):
                return True
        except Exception:
            pass
    return False


def _esperar_visible(page, fabrica, descripcion, timeout):
    """Espera que aparezca al menos una copia visible (sirve cuando puede haber varias)."""
    limite = time.monotonic() + max(timeout, 0) / 1000.0
    while not _hay_visible(page, fabrica):
        restante = int((limite - time.monotonic()) * 1000)
        if restante <= 0:
            raise RuntimeError("%s no apareció visible en %.1f s" % (descripcion, max(timeout, 0) / 1000.0))
        page.wait_for_timeout(min(250, restante))


def patron_cuenta(cuenta, inicio=False):
    """Cómo se ve la cuenta en pantalla.

    En el inicio: "#0489-000765/9". En Saldos y movimientos: "489-000765/9 (CC $)".
    """
    suc, resto = cuenta.split("-", 1)
    nucleo = r"0*%s-%s" % (re.escape(suc.lstrip("0")), re.escape(resto))
    if inicio:
        return re.compile(r"^\s*#?%s\s*$" % nucleo)
    return re.compile(r"^\s*%s\s*\(CC\s*\$\)\s*$" % nucleo)


def nombre_publicado(prefijo, cuenta, fecha, extension=".xls"):
    """'Movimientos BBVA 489-000765-9 2026-10-03.xls'."""
    return "%s %s %s%s" % (prefijo, cuenta.replace("/", "-"), fecha.isoformat(), extension)


class BotBbvaNavar(BotBanco):
    nombre = "BBVA"
    url = URL_LOGIN

    def __init__(self, cfg):
        super().__init__()
        self.cuentas = list(cfg["cuentas"])
        self.prefijo = cfg.get("prefijo_archivo") or "Movimientos BBVA"
        # Lo completa orquestador/correr.py desde el llavero (nunca desde el perfil).
        self.codigo_empresa = None
        self.saldos_por_cuenta = {}

    # ------------------------------------------------------------------ login
    @staticmethod
    def _campo(page, etiqueta, timeout):
        return _esperar_unico(page, [
            # Los id son los del formulario visto el 03/10/2026; si cambian, se busca por etiqueta.
            lambda m: m.locator("input#%s" % IDS_LOGIN[etiqueta]),
            lambda m: m.get_by_label(etiqueta, exact=True).and_(m.locator("input")),
            lambda m: m.get_by_placeholder(etiqueta, exact=True),
            lambda m: m.locator("input[aria-label=\"%s\"]" % etiqueta),
        ], "el campo %s" % etiqueta, timeout)

    @staticmethod
    def _habilitado(boton, page, espera_ms):
        limite = time.monotonic() + espera_ms / 1000.0
        while True:
            try:
                if boton.is_enabled() and boton.get_attribute("aria-disabled") != "true":
                    return True
            except Exception:
                pass
            if time.monotonic() >= limite:
                return False
            page.wait_for_timeout(200)

    def hacer_login(self, page, usuario, clave, timeout):
        if not self.codigo_empresa:
            raise RuntimeError("Falta el código de empresa (setup_credenciales.py --banco bbva).")
        log("Abriendo el login de BBVA...")
        page.goto(URL_LOGIN, timeout=timeout)
        try:
            empresa = self._campo(page, "Código de empresa", timeout)
            campo_usuario = self._campo(page, "Código de usuario", timeout)
            campo_clave = self._campo(page, "Clave de acceso", timeout)
            ingresar = _esperar_unico(page, [
                lambda m: m.locator("button#btn_submit"),
                lambda m: m.get_by_role("button", name="Ingresar", exact=True),
                lambda m: m.locator("button, a, input[type=submit]").filter(
                    has_text=re.compile(r"^\s*Ingresar\s*$")),
            ], "el botón Ingresar", timeout)
        except Exception:
            captura(page, "ERROR_formulario_login")
            raise
        captura(page, "pantalla_login")

        datos = ((empresa, self.codigo_empresa), (campo_usuario, usuario), (campo_clave, clave))
        for campo, valor in datos:
            campo.click(timeout=timeout)
            campo.fill(valor, timeout=timeout)
        # "Ingresar" está apagado hasta que el formulario ve los tres datos. Si con fill no
        # se enciende, se cargan tecla por tecla (algunos formularios solo escuchan teclas).
        if not self._habilitado(ingresar, page, 3000):
            log("   Ingresar seguía apagado: cargo los datos tecla por tecla.")
            for campo, valor in datos:
                campo.fill("", timeout=timeout)
                campo.press_sequentially(valor, delay=60, timeout=timeout)
            if not self._habilitado(ingresar, page, 5000):
                captura(page, "ERROR_ingresar_apagado")
                raise RuntimeError("El botón Ingresar sigue apagado con los tres datos cargados; "
                                   "no se intentó entrar.")
        captura(page, "datos_cargados")

        try:
            ingresar.click(timeout=timeout)
            captura(page, "login_enviado")
            # El inicio de BBVA tarda mucho (el 03/10 pasó los 90 s): se espera hasta 4 minutos.
            self._esperar_inicio(page, max(timeout, ESPERA_INICIO_MS))
        except Exception:
            captura(page, "ERROR_login_no_confirmado")
            raise
        captura(page, "post_login")
        log("Login confirmado.")

    @staticmethod
    def _en_inicio(page):
        """Algo que solo aparece adentro: el CUIT, el nombre de NAVAR o "Cuentas en pesos".

        Se aceptan las tres porque el CUIT del inicio vive en un selector y puede no leerse
        como texto. Igual, el Excel se controla por su CUIT antes de publicarlo.
        """
        return any(_hay_visible(page, f) for f in (
            lambda m: m.get_by_text(PATRON_CUIT),
            lambda m: m.get_by_text(PATRON_NAVAR),
            lambda m: m.get_by_text("Cuentas en pesos", exact=True),
        ))

    def _esperar_inicio(self, page, espera_ms):
        """Espera el inicio y, mientras tanto, cada 30 s deja una captura y anota dónde está.

        Así, si no llega, queda a la vista si seguía cargando o si volvió al login (el loop
        que tenía el usuario anterior).
        """
        arranque = time.monotonic()
        proximo_aviso = 30
        while not self._en_inicio(page):
            pasados = time.monotonic() - arranque
            if pasados * 1000 >= espera_ms:
                raise RuntimeError("el inicio de BBVA no apareció en %d s" % (espera_ms // 1000))
            if pasados >= proximo_aviso:
                try:
                    url = page.url
                except Exception:
                    url = "(sin URL)"
                en_login = _hay_visible(page, lambda m: m.locator("input#cod_emp"))
                log("   %d s esperando el inicio · %s%s" % (
                    proximo_aviso, url, " · el formulario de login sigue a la vista" if en_login else ""))
                captura(page, "esperando_inicio_%ds" % proximo_aviso)
                proximo_aviso += 30
            page.wait_for_timeout(500)
        log("   El inicio apareció a los %d s." % (time.monotonic() - arranque))

    # --------------------------------------------------------------- empresa
    def capturar_empresa_activa(self, page):
        # Una sola empresa: alcanza con ver su CUIT o su nombre en pantalla.
        return "NAVAR SA" if self._en_inicio(page) else None

    def descubrir_empresas(self, page, timeout, excluir, solo=None):
        return []

    def cambiar_a_empresa(self, page, nombre, timeout):
        raise RuntimeError("BBVA NAVAR tiene una sola empresa; no se abre el selector.")

    # ---------------------------------------------------------------- cuentas
    def _desplegar_cuentas(self, page, timeout):
        """Aprieta el + de "Cuentas en pesos" para que aparezcan las cuentas."""
        texto = _esperar_unico(page, [
            lambda m: m.get_by_text("Cuentas en pesos", exact=True),
        ], "el bloque Cuentas en pesos", timeout)
        caja_texto = texto.bounding_box()
        # El + es un botón de la misma tarjeta, a la izquierda del título.
        botones = []
        try:
            tarjeta = texto.locator("xpath=ancestor::*[.//button or .//*[@role='button']][1]")
            for b in _visibles(tarjeta.locator("button, [role=button]")):
                caja = b.bounding_box()
                if caja and caja_texto and caja["x"] + caja["width"] <= caja_texto["x"] + 2:
                    botones.append(b)
        except Exception as e:
            log("   Aviso: no pude mirar los botones de la tarjeta: %s" % str(e)[:100])
        if len(botones) == 1:
            botones[0].click(timeout=timeout)
        else:
            # Sin un + reconocible, se aprieta el título: en estas tarjetas suele desplegar igual.
            log("   El + no se reconoció (%d candidatos); aprieto el título." % len(botones))
            texto.click(timeout=timeout)

    def _esperar_cuenta_abierta(self, page, cuenta, timeout):
        """Confirma que la pantalla de movimientos muestra ESA cuenta y el botón Descargar."""
        _esperar_visible(page, lambda m: m.get_by_text("Saldos y movimientos", exact=True),
                         "el título Saldos y movimientos", timeout)
        _esperar_visible(page, lambda m: m.get_by_text(patron_cuenta(cuenta)),
                         "la cuenta %s en Saldos y movimientos" % cuenta, timeout)
        self._boton_descargar(page, timeout)

    def ir_a_cuenta(self, page, timeout):
        if self.capturar_empresa_activa(page) != "NAVAR SA":
            raise RuntimeError("No pude confirmar el CUIT de NAVAR; revisar captura.")
        captura(page, "inicio")
        primera = self.cuentas[0]
        en_inicio = lambda m: m.get_by_text(patron_cuenta(primera, inicio=True))
        if not _hay_visible(page, en_inicio):
            self._desplegar_cuentas(page, timeout)
        enlace = _esperar_unico(page, [en_inicio], "la cuenta %s en el inicio" % primera, timeout)
        captura(page, "cuentas_desplegadas")
        enlace.click(timeout=timeout)
        self._esperar_cuenta_abierta(page, primera, timeout)
        captura(page, "cuenta_abierta_%s" % primera.replace("/", "-"))

    def _cambiar_cuenta(self, page, cuenta, timeout):
        """Abre el selector del número de cuenta y elige la pedida."""
        cualquiera = re.compile(r"^\s*\d{3}-\d{6}/\d\s*\(CC\s*\$\)\s*$")
        selector = _esperar_unico(page, [
            lambda m: m.get_by_text(cualquiera),
        ], "el selector de cuenta", timeout)
        selector.click(timeout=timeout)
        captura(page, "lista_de_cuentas")
        # Con la lista abierta, el nombre de la cuenta pedida aparece una sola vez (en la lista).
        opcion = _esperar_unico(page, [
            lambda m: m.get_by_role("option", name=patron_cuenta(cuenta)),
            lambda m: m.get_by_text(patron_cuenta(cuenta)),
        ], "la cuenta %s en la lista" % cuenta, timeout)
        opcion.click(timeout=timeout)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        self._esperar_cuenta_abierta(page, cuenta, timeout)
        # La tabla se recarga después del título; un respiro antes de descargar. Si igual se
        # bajara la cuenta anterior, el control del encabezado del Excel lo frena.
        page.wait_for_timeout(1500)
        captura(page, "cuenta_abierta_%s" % cuenta.replace("/", "-"))

    def capturar_saldos(self, page):
        """El saldo de arriba a la derecha ("$ -1.234,56"). Si no se lee, no corta nada."""
        resultado = {"actual_texto": None, "actual": None,
                     "disponible_texto": None, "disponible": None}
        try:
            monto = _esperar_unico(page, [
                lambda m: m.get_by_text(re.compile(r"^\s*\$\s*-?\s*[\d.]+,\d{2}\s*$")),
            ], "el saldo de la cuenta", 8000)
            texto = (monto.inner_text(timeout=6000) or "").strip()
            valor = _parse_monto(texto.replace("$", "").replace(" ", ""))
            if valor is None:
                raise ValueError("el monto '%s' no es legible" % texto)
            resultado["actual_texto"], resultado["actual"] = texto, valor
        except Exception as e:
            log("   Aviso: no pude leer el saldo: %s" % str(e)[:120])
        captura(page, "saldo")
        return resultado

    def aplicar_filtro_fechas(self, page, desde, hasta, timeout):
        log("BBVA NAVAR no usa filtro: baja los últimos 60 días que trae el banco")
        return True

    # ---------------------------------------------------------------- descarga
    @staticmethod
    def _boton_descargar(page, timeout):
        return _esperar_unico(page, [
            lambda m: m.get_by_role("button", name=re.compile(r"^\s*Descargar\b", re.I)),
            lambda m: m.locator("button, a").filter(has_text=re.compile(r"^\s*Descargar\s*$")),
        ], "el botón Descargar", timeout)

    def validar_excel(self, ruta, cuenta, hoy=None):
        """El Excel tiene que ser de NAVAR y de ESA cuenta, con fechas razonables."""
        from lector.extractos import leer_planilla_bbva

        datos = leer_planilla_bbva(ruta)
        if datos["cuenta"] != cuenta:
            raise RuntimeError("El Excel dice la cuenta %s y se pidió %s." % (datos["cuenta"], cuenta))
        if datos.get("cuit") != CUIT_NAVAR:
            raise RuntimeError("El Excel no es de NAVAR (CUIT %s)." % datos.get("cuit"))
        hoy = hoy or datetime.date.today()
        mas_viejo = hoy - datetime.timedelta(days=DIAS_ATRAS_TOLERADOS)
        mas_nuevo = hoy + datetime.timedelta(days=DIAS_ADELANTE_TOLERADOS)
        for m in datos["movimientos"]:
            fecha = datetime.date.fromisoformat(str(m["fecha"])[:10])
            if fecha > mas_nuevo:
                raise RuntimeError("El Excel trae un movimiento con fecha futura: %s." % fecha)
            if fecha < mas_viejo:
                raise RuntimeError("El Excel trae un movimiento de hace más de %d días: %s." % (
                    DIAS_ATRAS_TOLERADOS, fecha))
        # Una cuenta sin movimientos en 60 días no es un error (la de recaudación puede estar
        # quieta): el archivo igual dice que se miró.
        if not datos["movimientos"]:
            log("   %s: sin movimientos en los últimos 60 días." % cuenta)
        return datos

    @staticmethod
    def publicar(temporal, carpeta_destino, nombre):
        """Copia a Drive con un temporal: el vigilante nunca ve un archivo a medias."""
        destino = os.path.join(carpeta_destino, nombre)
        fd, parcial = tempfile.mkstemp(suffix=".part", dir=carpeta_destino)
        os.close(fd)
        try:
            shutil.copyfile(temporal, parcial)
            os.replace(parcial, destino)  # si ya estaba el de hoy, lo reemplaza
        finally:
            if os.path.exists(parcial):
                os.remove(parcial)
        return destino

    def _descargar_una(self, page, cuenta, carpeta_destino, timeout, ctx):
        boton = self._boton_descargar(page, timeout)
        with page.expect_download(timeout=timeout) as info:
            boton.click(timeout=timeout)
        descarga = info.value
        extension = Path(descarga.suggested_filename or "").suffix.lower()
        if extension not in (".xls", ".xlsx"):
            raise RuntimeError("BBVA no entregó un Excel (llegó '%s')." % descarga.suggested_filename)

        # Cada corrida usa su propio temporal: nunca se pisa el de otra corrida.
        temporal = os.path.join(ctx.descargas_dir, "bbva_por_validar_%s_%s%s" % (
            datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S"), uuid.uuid4().hex, extension))
        try:
            descarga.save_as(temporal)
        except Exception as e:
            try:
                motivo = descarga.failure()
            except Exception as consulta:
                motivo = "no se pudo consultar: %s" % consulta
            raise RuntimeError("No se pudo guardar la descarga de %s: %s; Playwright: %s" % (
                cuenta, e, motivo or "sin detalle"))
        datos = self.validar_excel(temporal, cuenta)
        destino = self.publicar(temporal, carpeta_destino, nombre_publicado(
            self.prefijo, cuenta, datetime.date.today(), extension))
        try:
            os.remove(temporal)
        except OSError as e:
            log("   Aviso: se publicó, pero no pude borrar el temporal: %s" % e)
        log("   %s: descargado y validado, %d movimientos -> %s" % (
            cuenta, len(datos["movimientos"]), os.path.basename(destino)))
        return destino

    @staticmethod
    def _limpiar_temporales(carpeta):
        # Una semana de descargas fallidas queda para poder revisarlas; lo anterior se borra.
        limite = time.time() - 7 * 24 * 60 * 60
        for viejo in Path(carpeta).glob("bbva_por_validar_*"):
            try:
                if viejo.is_file() and viejo.stat().st_mtime < limite:
                    viejo.unlink()
            except OSError as e:
                log("   Aviso: no pude borrar temporal viejo %s: %s" % (viejo.name, e))

    def descargar_csv(self, page, carpeta_destino, nombre_empresa, timeout, ctx):
        # El nombre del método viene del contrato compartido; BBVA entrega un Excel.
        # Baja las dos cuentas: si una falla, la otra igual se publica y al final se avisa.
        if nombre_empresa != "NAVAR SA":
            raise RuntimeError("Falta confirmar la empresa antes de descargar.")
        self._limpiar_temporales(ctx.descargas_dir)
        publicados, errores = [], []
        for i, cuenta in enumerate(self.cuentas):
            try:
                if i > 0:
                    self._cambiar_cuenta(page, cuenta, timeout)
                    saldo = self.capturar_saldos(page)
                    log("   Saldo %s: %s" % (cuenta, saldo.get("actual_texto") or "?"))
                    self.saldos_por_cuenta[cuenta] = saldo.get("actual")
                publicados.append(self._descargar_una(page, cuenta, carpeta_destino, timeout, ctx))
            except Exception as e:
                captura(page, "ERROR_cuenta_%s" % cuenta.replace("/", "-"))
                log("   FALLÓ la cuenta %s: %s" % (cuenta, e))
                errores.append("%s: %s" % (cuenta, str(e)[:120]))
        if errores:
            raise RuntimeError("BBVA: %d de %d cuentas fallaron (%s). Publicadas: %s" % (
                len(errores), len(self.cuentas), "; ".join(errores),
                ", ".join(os.path.basename(p) for p in publicados) or "ninguna"))
        return publicados[0]

    def extraer_cuenta_id(self, archivo_csv):
        return " y ".join(self.cuentas)
