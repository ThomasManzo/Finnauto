# -*- coding: utf-8 -*-
"""
bots.nacion.navar — baja los movimientos de la cuenta corriente de NAVAR en BNA+ Empresas.

EL RECORRIDO (lo describió Thomas mirando la pantalla el 07/10/2026)
    1. Login en dos pasos: DNI + usuario -> "Continuar" -> contraseña -> "Continuar".
       Un solo intento. Si aparece el "No soy un robot", el bot PARA: no lo resuelve.
    2. Inicio (dice NAVAR SA) -> "Mis cuentas" -> la cuenta -> "Detalle de cuenta".
    3. "Filtrar": Desde / Hasta -> "Buscar". Se piden solo los últimos días (perfil
       "dias_a_bajar"): el archivo sale chico y rápido, y si un día falló, el siguiente lo recupera
       (el lector no repite movimientos).
    4. "Descargar" -> "Archivo XLS". El banco NO lo baja en el momento: avisa "Estamos generando tu
       archivo" y a los segundos deja una notificación "Descarga de listado" en la campanita.
    5. Campanita -> la notificación nueva -> el adjunto "Ultimos movimientos.xls" -> se descarga.

CADA ARCHIVO SE CONTROLA ANTES DE PUBLICARLO
    El Excel no dice la cuenta, así que se controla de otra forma: la cadena de saldos tiene que
    cerrar al centavo (lo hace el lector) y todas las fechas tienen que caer dentro del filtro que
    se pidió. Así, si la notificación fuera de un pedido viejo, salta el error.

QUÉ QUEDA EN DRIVE (NAVAR - Datos/Bancos/nacion)
    Movimientos Nacion <cuenta> AAAA-MM-DD.xls   (el número va en el nombre: el lector lo necesita)
"""
import datetime
import os
import re
import time
import uuid
from pathlib import Path

from bots.base import BotBanco
from bots.bbva.navar import (BotBbvaNavar, PATRON_NAVAR, _esperar_unico, _esperar_visible,
                             _hay_visible, _visibles)
from nucleo.log import log, captura
from nucleo.utilidades import _parse_monto


URL_LOGIN = "https://digital.bna.com.ar/loginStep1"
# Cuánto se espera la notificación con el archivo (Thomas: un mes tardó unos 19 s).
ESPERA_ARCHIVO_S = 180
# Cuánto se espera el inicio después de la contraseña.
ESPERA_INICIO_MS = 120000
PATRON_FECHA_HORA = re.compile(r"(\d\d)/(\d\d)/(\d{4})\s+(\d\d):(\d\d)")


def _fecha(d):
    return d.strftime("%d/%m/%Y")


def hora_de_notificacion(texto):
    """'Descarga de listado ... 07/10/2026 21:15' -> datetime, o None si no trae fecha y hora."""
    m = PATRON_FECHA_HORA.search(texto or "")
    if not m:
        return None
    d, mes, a, h, mi = (int(x) for x in m.groups())
    return datetime.datetime(a, mes, d, h, mi)


def elegir_notificacion(textos, pedido, margen_min=2):
    """De los textos de las notificaciones "Descarga de listado", el índice de la más nueva que sea
    de ESTE pedido (con hora igual o posterior al pedido, con unos minutos de margen por si el reloj
    de la notebook y el del banco no coinciden). None si todavía no llegó."""
    desde = pedido.replace(second=0, microsecond=0) - datetime.timedelta(minutes=margen_min)
    candidatas = []
    for i, t in enumerate(textos):
        hora = hora_de_notificacion(t)
        if hora is not None and hora >= desde:
            candidatas.append((hora, i))
    return max(candidatas)[1] if candidatas else None


def nombre_publicado(prefijo, cuenta, fecha):
    """'Movimientos Nacion 12345678901234 2026-10-07.xls'."""
    return "%s %s %s.xls" % (prefijo, cuenta, fecha.isoformat())


class BotNacionNavar(BotBanco):
    nombre = "Nacion"
    url = URL_LOGIN

    def __init__(self, cfg):
        super().__init__()
        self.cuenta = re.sub(r"\D", "", cfg["cuenta"])
        self.prefijo = cfg.get("prefijo_archivo") or "Movimientos Nacion"
        self.dias = max(1, int(cfg.get("dias_a_bajar", 5)))
        # Lo completa orquestador/correr.py desde el llavero (nunca desde el perfil).
        self.dni = None
        self.desde = self.hasta = None

    # ----------------------------------------------------------------- captcha
    @staticmethod
    def hay_captcha(page):
        """¿Hay un "No soy un robot" a la vista? El reCAPTCHA invisible (el sellito de la esquina)
        no cuenta: solo la casilla o la prueba de imágenes."""
        try:
            for marco in page.locator("iframe[src*='recaptcha']").all():
                src = marco.get_attribute("src") or ""
                if "size=invisible" in src or not marco.is_visible():
                    continue
                caja = marco.bounding_box()
                if caja and caja["height"] > 40:
                    return True
        except Exception:
            pass
        return False

    def _frenar_si_captcha(self, page):
        if self.hay_captcha(page):
            captura(page, "ERROR_captcha")
            raise RuntimeError("Apareció el 'No soy un robot'. El bot no lo resuelve: hoy Nación queda "
                               "manual. No reintentar en seguida.")

    # ------------------------------------------------------------------- login
    @staticmethod
    def _campo(page, placeholder, etiqueta, timeout):
        # Solo campos de verdad: la caja que envuelve al campo también lleva el mismo placeholder.
        return _esperar_unico(page, [
            lambda m: m.locator("input[placeholder=\"%s\"]" % placeholder),
            lambda m: m.get_by_label(etiqueta, exact=True).and_(m.locator("input")),
        ], "el campo %s" % etiqueta, timeout)

    @staticmethod
    def _continuar(page, timeout):
        return _esperar_unico(page, [
            lambda m: m.get_by_role("button", name="Continuar", exact=True),
        ], "el botón Continuar", timeout)

    @staticmethod
    def _cargar(page, boton, datos, timeout):
        """Carga los datos y espera que el botón se encienda (si no, prueba tecla por tecla)."""
        for campo, valor in datos:
            campo.click(timeout=timeout)
            campo.fill(valor, timeout=timeout)
        if BotBbvaNavar._habilitado(boton, page, 3000):
            return
        log("   Continuar seguía apagado: cargo los datos tecla por tecla.")
        for campo, valor in datos:
            campo.fill("", timeout=timeout)
            campo.press_sequentially(valor, delay=60, timeout=timeout)
        if not BotBbvaNavar._habilitado(boton, page, 5000):
            captura(page, "ERROR_continuar_apagado")
            raise RuntimeError("El botón Continuar sigue apagado con los datos cargados; no se intentó entrar.")

    def hacer_login(self, page, usuario, clave, timeout):
        if not self.dni:
            raise RuntimeError("Falta el DNI (setup_credenciales.py --banco nacion).")
        log("Abriendo el login de BNA+ Empresas...")
        page.goto(URL_LOGIN, timeout=timeout)
        try:
            dni = self._campo(page, "Ingresá tu DNI", "DNI", timeout)
            campo_usuario = self._campo(page, "Ingresá tu nombre de usuario", "Usuario", timeout)
            continuar = self._continuar(page, timeout)
        except Exception:
            captura(page, "ERROR_formulario_login")
            raise
        captura(page, "pantalla_login")
        self._cargar(page, continuar, ((dni, self.dni), (campo_usuario, usuario)), timeout)
        continuar.click(timeout=timeout)

        # Paso 2: la contraseña. Si el banco decide mostrar el captcha, aparece acá.
        try:
            limite = time.monotonic() + timeout / 1000.0
            while True:
                self._frenar_si_captcha(page)
                if _hay_visible(page, lambda m: m.locator("input[placeholder=\"Ingresá tu contraseña\"]")):
                    break
                if time.monotonic() > limite:
                    raise RuntimeError("no apareció el paso de la contraseña")
                page.wait_for_timeout(300)
            campo_clave = self._campo(page, "Ingresá tu contraseña", "Contraseña", timeout)
            continuar = self._continuar(page, timeout)
        except Exception:
            captura(page, "ERROR_paso_contrasena")
            raise
        self._frenar_si_captcha(page)
        self._cargar(page, continuar, ((campo_clave, clave),), timeout)
        self._frenar_si_captcha(page)
        captura(page, "contrasena_cargada")
        try:
            continuar.click(timeout=timeout)
            self._esperar_inicio(page)
        except Exception:
            captura(page, "ERROR_login_no_confirmado")
            raise
        captura(page, "post_login")
        log("Login confirmado.")

    def _esperar_inicio(self, page):
        """Espera "Mis cuentas" o el nombre de NAVAR; cada 30 s anota dónde está y saca captura."""
        arranque = time.monotonic()
        aviso = 30
        while not self._en_inicio(page):
            self._frenar_si_captcha(page)
            pasados = time.monotonic() - arranque
            if pasados * 1000 >= ESPERA_INICIO_MS:
                raise RuntimeError("el inicio de BNA+ no apareció en %d s" % (ESPERA_INICIO_MS // 1000))
            if pasados >= aviso:
                log("   %d s esperando el inicio · %s" % (aviso, page.url))
                captura(page, "esperando_inicio_%ds" % aviso)
                aviso += 30
            page.wait_for_timeout(500)

    @staticmethod
    def _en_inicio(page):
        return (_hay_visible(page, lambda m: m.get_by_text(PATRON_NAVAR)) and
                _hay_visible(page, lambda m: m.get_by_text(re.compile(r"^\s*Mis cuentas"))))

    # ----------------------------------------------------------------- empresa
    def capturar_empresa_activa(self, page):
        return "NAVAR SA" if _hay_visible(page, lambda m: m.get_by_text(PATRON_NAVAR)) else None

    def descubrir_empresas(self, page, timeout, excluir, solo=None):
        return []

    def cambiar_a_empresa(self, page, nombre, timeout):
        raise RuntimeError("Nación NAVAR tiene una sola empresa; no se abre el selector.")

    # ------------------------------------------------------------------ cuenta
    def _es_la_cuenta(self, texto):
        """El inicio muestra la cuenta recortada ("N° 7890007728"): vale si es el final del número."""
        digitos = re.sub(r"\D", "", texto or "")
        return len(digitos) >= 4 and self.cuenta.endswith(digitos)

    def ir_a_cuenta(self, page, timeout):
        if self.capturar_empresa_activa(page) != "NAVAR SA":
            raise RuntimeError("No pude confirmar NAVAR en el inicio; revisar captura.")
        captura(page, "inicio")
        candidatos = []
        for marco in page.frames:
            try:
                for el in _visibles(marco.get_by_text(re.compile(r"^\s*N[°º]\s*\d+\s*$"))):
                    if self._es_la_cuenta(el.inner_text()):
                        candidatos.append(el)
            except Exception:
                pass
        if len(candidatos) != 1:
            raise RuntimeError("la cuenta en Mis cuentas: encontré %d candidatas" % len(candidatos))
        candidatos[0].click(timeout=timeout)
        _esperar_visible(page, lambda m: m.get_by_text("Detalle de cuenta", exact=True),
                         "el Detalle de cuenta", timeout)
        _esperar_visible(page, lambda m: m.get_by_text(re.compile(re.escape(self.cuenta))),
                         "el número de cuenta en el detalle", timeout)
        captura(page, "detalle_de_cuenta")

    def capturar_saldos(self, page):
        """Saldo y Saldo disponible del detalle. Si no se leen, no corta nada."""
        resultado = {"actual_texto": None, "actual": None, "disponible_texto": None, "disponible": None}
        for clave, etiqueta in (("actual", "Saldo"), ("disponible", "Saldo disponible")):
            try:
                ruta = "xpath=//*[normalize-space(.)='%s']/following-sibling::*[1]" % etiqueta
                monto = _esperar_unico(page, [lambda m, r=ruta: m.locator(r)], "el %s" % etiqueta, 6000)
                texto = (monto.inner_text(timeout=6000) or "").strip()
                limpio = texto.replace("$", "").replace(" ", "")
                valor = _parse_monto(limpio)
                if valor is None:
                    raise ValueError("el monto '%s' no es legible" % texto)
                resultado[clave + "_texto"], resultado[clave] = texto, valor
            except Exception as e:
                log("   Aviso: no pude leer '%s': %s" % (etiqueta, str(e)[:120]))
        return resultado

    # ------------------------------------------------------------------ filtro
    def ventana(self, hoy=None):
        """Los días que se piden: de hoy - (dias_a_bajar - 1) a hoy."""
        hoy = hoy or datetime.date.today()
        return hoy - datetime.timedelta(days=self.dias - 1), hoy

    @staticmethod
    def _campos_fecha(page):
        """Los dos campos de fecha del panel de filtros, de arriba a abajo (Desde, Hasta).

        En una sesión nueva vienen VACÍOS (07/10: el bot los buscaba por la fecha de adentro y no
        encontró ninguno). Se prueban tres formas, en orden:
          1. los campos del calendario de la página (react-datepicker);
          2. el primer campo que sigue a los títulos "Desde" y "Hasta";
          3. los campos que ya tienen una fecha dd/mm/aaaa.
        """
        def ordenar(campos):
            con_y = []
            for el in campos:
                caja = el.bounding_box()
                con_y.append((caja["y"] if caja else 0, el))
            return [el for _, el in sorted(con_y, key=lambda c: c[0])]

        formas = [
            lambda m: _visibles(m.locator(".react-datepicker__input-container input")),
            lambda m: [el for titulo in ("Desde", "Hasta") for el in _visibles(m.locator(
                "xpath=//*[normalize-space(text())='%s']/following::input[1]" % titulo))],
            lambda m: [el for el in _visibles(m.locator("input"))
                       if re.fullmatch(r"\d\d/\d\d/\d{4}", (el.input_value() or "").strip())],
        ]
        for forma in formas:
            campos = []
            for marco in page.frames:
                try:
                    campos += forma(marco)
                except Exception:
                    pass
            if len(campos) == 2:
                return ordenar(campos)
        return []

    def aplicar_filtro_fechas(self, page, desde, hasta, timeout):
        # El rango lo decide el bot (no el del núcleo): siempre los últimos días, para recuperar
        # solo lo que haya fallado antes.
        self.desde, self.hasta = self.ventana()
        log("   Filtro: %s a %s" % (_fecha(self.desde), _fecha(self.hasta)))
        filtrar = _esperar_unico(page, [
            lambda m: m.get_by_role("button", name=re.compile(r"^\s*Filtrar")),
            lambda m: m.locator("button, a").filter(has_text=re.compile(r"^\s*Filtrar")),
        ], "el botón Filtrar", timeout)
        filtrar.click(timeout=timeout)
        _esperar_visible(page, lambda m: m.get_by_text(re.compile(r"Seleccion[aá] los siguientes filtros")),
                         "el panel de filtros", timeout)
        campos = self._campos_fecha(page)
        if len(campos) != 2:
            captura(page, "ERROR_campos_fecha")
            raise RuntimeError("en el panel de filtros esperaba 2 fechas (Desde/Hasta) y hay %d" % len(campos))
        for campo, valor in zip(campos, (_fecha(self.desde), _fecha(self.hasta))):
            campo.click(timeout=timeout)
            campo.fill(valor, timeout=timeout)
            # Tab cierra el calendario sin cerrar el panel (Escape podría cerrar los dos).
            campo.press("Tab")
            page.wait_for_timeout(300)
            if (campo.input_value() or "").strip() != valor:
                captura(page, "ERROR_fecha_no_tomada")
                raise RuntimeError("la fecha %s no quedó cargada en el filtro" % valor)
        captura(page, "filtro_cargado")
        buscar = _esperar_unico(page, [
            lambda m: m.get_by_role("button", name="Buscar", exact=True),
        ], "el botón Buscar", timeout)
        buscar.click(timeout=timeout)
        page.wait_for_timeout(1500)
        captura(page, "movimientos_filtrados")
        return True

    # ---------------------------------------------------------------- descarga
    def _pedir_xls(self, page, timeout):
        descargar = _esperar_unico(page, [
            lambda m: m.get_by_text("Descargar", exact=True),
            lambda m: m.get_by_role("button", name=re.compile(r"^\s*Descargar")),
        ], "el botón Descargar", timeout)
        descargar.click(timeout=timeout)
        xls = _esperar_unico(page, [
            lambda m: m.get_by_text("Archivo XLS", exact=True),
        ], "la opción Archivo XLS", timeout)
        pedido = datetime.datetime.now()
        xls.click(timeout=timeout)
        captura(page, "xls_pedido")
        try:
            _esperar_visible(page, lambda m: m.get_by_text(re.compile(r"Estamos generando tu archivo")),
                             "el aviso de que se está generando el archivo", 15000)
        except Exception as e:
            log("   Aviso: no vi el cartel de 'generando tu archivo' (%s); sigo igual." % str(e)[:80])
        return pedido

    @staticmethod
    def _abrir_notificaciones(page, timeout):
        """Abre la campanita. Se prueban varias formas porque no tiene texto propio."""
        campana = None
        for fabrica in (
                lambda m: m.get_by_role("button", name=re.compile(r"notificaci|mensaje", re.I)),
                lambda m: m.get_by_role("link", name=re.compile(r"notificaci|mensaje", re.I)),
                lambda m: m.locator("a[href*='ommunication'], [aria-label*='otificaci'], [aria-label*='ensaje']")):
            try:
                campana = _esperar_unico(page, [fabrica], "la campanita", 2500)
                break
            except Exception:
                continue
        if campana is not None:
            campana.click(timeout=timeout)
        else:
            # Sin una campanita reconocible, se va directo a la bandeja (ruta de la plataforma).
            log("   No reconocí la campanita; voy directo a la bandeja de mensajes.")
            page.goto("https://digital.bna.com.ar/communications", timeout=timeout)
        _esperar_visible(page, lambda m: m.get_by_text("Recibidos", exact=True),
                         "la bandeja de notificaciones", timeout)

    def _buscar_notificacion(self, page, pedido, timeout):
        """Espera la notificación de ESTE pedido y la abre. Devuelve el elemento clickeado."""
        limite = time.monotonic() + ESPERA_ARCHIVO_S
        vuelta = 0
        while True:
            vuelta += 1
            self._abrir_notificaciones(page, timeout)
            page.wait_for_timeout(1500)
            filas, textos = [], []
            for marco in page.frames:
                try:
                    for asunto in _visibles(marco.get_by_text("Descarga de listado", exact=True)):
                        # El renglón de la notificación: el primer contenedor que trae fecha y hora.
                        fila = asunto.locator("xpath=ancestor::*[contains(normalize-space(.), ':')][1]")
                        filas.append(asunto)
                        textos.append(fila.inner_text(timeout=3000))
                except Exception:
                    pass
            i = elegir_notificacion(textos, pedido)
            if i is not None:
                log("   Llegó la notificación (%s)." % " ".join(textos[i].split())[:80])
                captura(page, "notificacion")
                filas[i].click(timeout=timeout)
                return
            if time.monotonic() > limite:
                captura(page, "ERROR_sin_notificacion")
                raise RuntimeError("la notificación con el archivo no llegó en %d s" % ESPERA_ARCHIVO_S)
            log("   Todavía no llegó la notificación (vuelta %d); espero 10 s." % vuelta)
            page.wait_for_timeout(10000)
            # Se vuelve al inicio para que la bandeja se cargue de nuevo al reabrirla.
            try:
                _esperar_unico(page, [lambda m: m.get_by_text("Inicio", exact=True)], "Inicio", 5000).click()
                page.wait_for_timeout(1500)
            except Exception:
                pass

    def validar_excel(self, ruta, desde, hasta):
        """Cadena de saldos (la controla el lector) y fechas dentro del filtro pedido."""
        from lector.extractos import leer_planilla_nacion

        datos = leer_planilla_nacion(ruta)
        if datos["cuenta"] != self.cuenta:
            raise RuntimeError("el archivo quedó con la cuenta %s y se pidió %s" % (datos["cuenta"], self.cuenta))
        for m in datos["movimientos"]:
            if not (desde <= m["fecha"] <= hasta):
                raise RuntimeError("el Excel trae un movimiento del %s, fuera del filtro %s a %s: puede ser "
                                   "un listado viejo" % (m["fecha"], _fecha(desde), _fecha(hasta)))
        return datos

    @staticmethod
    def _limpiar_temporales(carpeta):
        # Una semana de descargas fallidas queda para poder revisarlas; lo anterior se borra.
        limite = time.time() - 7 * 24 * 60 * 60
        for viejo in Path(carpeta).glob("nacion_por_validar_*"):
            try:
                if viejo.is_file() and viejo.stat().st_mtime < limite:
                    viejo.unlink()
            except OSError as e:
                log("   Aviso: no pude borrar temporal viejo %s: %s" % (viejo.name, e))

    def descargar_csv(self, page, carpeta_destino, nombre_empresa, timeout, ctx):
        # El nombre del método viene del contrato compartido; Nación entrega un Excel.
        if nombre_empresa != "NAVAR SA":
            raise RuntimeError("Falta confirmar la empresa antes de descargar.")
        if self.desde is None:
            raise RuntimeError("Falta aplicar el filtro de fechas antes de descargar.")
        self._limpiar_temporales(ctx.descargas_dir)
        pedido = self._pedir_xls(page, timeout)
        self._buscar_notificacion(page, pedido, timeout)
        adjunto = _esperar_unico(page, [
            lambda m: m.get_by_text(re.compile(r"movimientos\.xls\s*$", re.I)),
        ], "el adjunto del listado", timeout)
        with page.expect_download(timeout=timeout) as info:
            adjunto.click(timeout=timeout)
        descarga = info.value
        # El número de cuenta va en el nombre: el lector lo necesita (el Excel no lo trae).
        temporal = os.path.join(ctx.descargas_dir, "nacion_por_validar_%s_%s_%s.xls" % (
            self.cuenta, datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S"), uuid.uuid4().hex[:8]))
        descarga.save_as(temporal)
        datos = self.validar_excel(temporal, self.desde, self.hasta)
        if not datos["movimientos"]:
            os.remove(temporal)
            log("   Sin movimientos del %s al %s: no hay nada que publicar." % (
                _fecha(self.desde), _fecha(self.hasta)))
            return None
        destino = BotBbvaNavar.publicar(temporal, carpeta_destino,
                                        nombre_publicado(self.prefijo, self.cuenta, datetime.date.today()))
        try:
            os.remove(temporal)
        except OSError as e:
            log("   Aviso: se publicó, pero no pude borrar el temporal: %s" % e)
        log("   Descargado y validado: %d movimientos -> %s (%s)" % (
            len(datos["movimientos"]), os.path.basename(destino), datos.get("nota", "")))
        return destino

    def extraer_cuenta_id(self, archivo_csv):
        return self.cuenta
