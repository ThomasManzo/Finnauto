# -*- coding: utf-8 -*-
"""Controles de NAVAR: no publicar otra cuenta ni un CSV disfrazado de Excel."""
import datetime
import os
import re
import shutil
import tempfile
from pathlib import Path

from bots.galicia.bot import BotGalicia
from nucleo.log import log, captura
from nucleo.utilidades import _click_robusto


def _empresa(texto):
    return re.sub(r"[\s.]", "", texto or "").upper()


class BotGaliciaNavar(BotGalicia):
    def __init__(self, cfg):
        super().__init__()
        self.cuenta = cfg["cuenta"]
        self.empresas = {_empresa(n) for n in cfg["solo_estas_empresas"]}
        self.prefijo = cfg["prefijo_archivo"]
        self.rango = None

    def hacer_login(self, page, usuario, clave, timeout):
        """En NAVAR el formulario siempre pide Usuario y Clave; no adivinamos sesiones recordadas."""
        log("Abriendo Galicia...")
        page.goto(self.url, timeout=timeout)
        captura(page, "home_galicia")

        _click_robusto(page, [
            lambda: page.get_by_role("link", name=re.compile(r"^office banking$", re.I)),
            lambda: page.get_by_role("button", name=re.compile(r"^office banking$", re.I)),
        ], "Office Banking")

        campo_usuario = page.get_by_label("Usuario", exact=True)
        try:
            campo_usuario.wait_for(state="visible", timeout=timeout)
            if campo_usuario.count() != 1:
                raise RuntimeError("el campo Usuario aparece más de una vez")
        except Exception as e:
            captura(page, "ERROR_formulario_login")
            raise RuntimeError("no cargó el formulario de login; revisar captura") from e
        captura(page, "pantalla_login")

        campo_clave = page.get_by_label("Clave", exact=True)
        try:
            campo_clave.wait_for(state="visible", timeout=timeout)
            if campo_clave.count() != 1:
                raise RuntimeError("el campo Clave aparece más de una vez")
            campo_usuario.fill(usuario, timeout=timeout)
            campo_clave.fill(clave, timeout=timeout)
        except Exception as e:
            captura(page, "ERROR_formulario_login")
            raise RuntimeError("no cargó el formulario de login; revisar captura") from e
        captura(page, "clave_cargada")

        ingresar = page.get_by_role("button", name="Ingresar", exact=True)
        if ingresar.count() != 1:
            captura(page, "ERROR_formulario_login")
            raise RuntimeError("no cargó el formulario de login; falta un único botón Ingresar")
        # Un solo intento: si el banco no confirma la entrada, se frena para no bloquear el usuario.
        try:
            ingresar.click(timeout=timeout)
            captura(page, "login_enviado")
            campo_usuario.wait_for(state="hidden", timeout=timeout)
            empresa = page.locator("header").filter(has_text=re.compile(
                r"NAVAR\s+(?:S\.?\s*A\.?|SOCIEDAD\s+ANONIMA)", re.I))
            empresa.wait_for(state="visible", timeout=timeout)
        except Exception as e:
            captura(page, "ERROR_login_no_confirmado")
            raise RuntimeError("login no confirmado; revisar captura") from e
        captura(page, "post_login")
        log("Login confirmado.")

    def capturar_empresa_activa(self, page):
        # Hay una sola empresa. En pantalla figura con el nombre legal completo,
        # pero el estado usa siempre la misma clave corta entre corridas.
        try:
            texto = page.locator("header").inner_text(timeout=5000)
        except Exception:
            return None
        normalizado = _empresa(texto)
        return "NAVAR SA" if any(nombre in normalizado for nombre in self.empresas) else None

    def descubrir_empresas(self, page, timeout, excluir, solo=None):
        # La empresa ya está activa y el perfil ordena no abrir el desplegable.
        return []

    def cambiar_a_empresa(self, page, nombre, timeout):
        raise RuntimeError("Galicia NAVAR tiene una sola empresa activa; no se abre el selector.")

    @staticmethod
    def _unico_visible(opciones, descripcion):
        """Elige una coincidencia visible sin recurrir a .first ni a coordenadas."""
        for loc in opciones:
            visibles = []
            for i in range(loc.count()):
                candidato = loc.nth(i)
                if candidato.is_visible():
                    visibles.append(candidato)
            if len(visibles) > 1:
                raise RuntimeError("%s aparece más de una vez; revisar captura." % descripcion)
            if len(visibles) == 1:
                return visibles[0]
        raise RuntimeError("No encontré %s; revisar captura." % descripcion)

    def ir_a_cuenta(self, page, timeout):
        # El motor permite seguir si no pudo leer la empresa. Acá eso no alcanza:
        # el lector atribuye todo a una cuenta fija, así que ante dudas frenamos.
        if _empresa(self.capturar_empresa_activa(page)) not in self.empresas:
            raise RuntimeError("No pude confirmar la empresa de NAVAR; revisar captura.")

        # Esta pantalla todavía no se vio completa. Dejamos evidencia a ambos lados
        # de cada clic para afinar sólo este selector en la próxima corrida supervisada.
        captura(page, "antes_menu_cuentas")
        navegacion = page.get_by_role("navigation")
        menu_cuentas = self._unico_visible([
            navegacion.get_by_role("link", name="Cuentas", exact=True),
            navegacion.get_by_role("button", name="Cuentas", exact=True),
            navegacion.get_by_role("menuitem", name="Cuentas", exact=True),
            page.locator("nav").get_by_role("link", name="Cuentas", exact=True),
            page.locator("nav").get_by_role("button", name="Cuentas", exact=True),
        ], "el ítem Cuentas del menú lateral")
        menu_cuentas.click(timeout=timeout)
        captura(page, "despues_click_menu_cuentas")

        digitos = r"\s+".join(re.escape(parte) for parte in self.cuenta.split())
        patron_cuenta = re.compile(r"^\s*(?:N[°º]\s*)?%s\s*$" % digitos, re.I)
        cuenta = page.get_by_text(patron_cuenta)
        cuenta.wait_for(state="visible", timeout=timeout)
        captura(page, "despues_menu_cuentas")
        cuenta = self._unico_visible([cuenta], "la cuenta pedida")

        captura(page, "antes_abrir_cuenta")
        cuenta.click(timeout=timeout)
        captura(page, "despues_click_abrir_cuenta")
        cuenta_abierta = page.get_by_text(patron_cuenta)
        cuenta_abierta.wait_for(state="visible", timeout=timeout)
        captura(page, "despues_abrir_cuenta")
        if len([cuenta_abierta.nth(i) for i in range(cuenta_abierta.count())
                if cuenta_abierta.nth(i).is_visible()]) != 1:
            raise RuntimeError("No pude confirmar la cuenta abierta.")

    def aplicar_filtro_fechas(self, page, desde, hasta, timeout):
        self.rango = None
        # El motor no mira el False del bot original: frenamos antes de descargar.
        if not super().aplicar_filtro_fechas(page, desde, hasta, timeout):
            raise RuntimeError("No pude confirmar las fechas elegidas; no publico el extracto.")
        self.rango = (desde, hasta)
        return True

    def validar_excel(self, ruta):
        from lector.extractos import leer_planilla_galicia

        # El export de Galicia no incluye la cuenta (comprobado 25/09). La cuenta se
        # confirma en pantalla; acá exigimos formato legible, movimientos y fechas.
        datos = leer_planilla_galicia(ruta)
        if not datos["movimientos"]:
            raise RuntimeError("Excel sin movimientos legibles; revisar antes de marcarlo al día.")
        desde, hasta = self.rango
        for mov in datos["movimientos"]:
            fecha = datetime.date.fromisoformat(str(mov["fecha"])[:10])
            if not desde <= fecha <= hasta:
                raise RuntimeError("El Excel trae movimientos fuera del rango pedido.")
        return datos

    def descargar_csv(self, page, carpeta_destino, nombre_empresa, timeout, ctx):
        # El nombre del método viene del contrato compartido; NAVAR necesita Excel.
        if self.rango is None or _empresa(nombre_empresa) not in self.empresas:
            raise RuntimeError("Falta confirmar empresa o fechas antes de descargar.")
        _click_robusto(page, [
            lambda: page.get_by_role("button", name=re.compile(r"descarg", re.I)).first,
            lambda: page.locator("button[aria-label*='descarg' i]").first,
            lambda: page.get_by_role("button", name=re.compile(r"filtros", re.I)).locator("xpath=following::button[1]"),
        ], "botón de descarga")
        page.wait_for_timeout(1200)
        captura(page, "menu_descarga")
        with page.expect_download(timeout=timeout) as info:
            page.get_by_text(re.compile(r"^\.?xlsx$", re.I)).click(timeout=timeout)
        descarga = info.value
        if Path(descarga.suggested_filename).suffix.lower() != ".xlsx":
            raise RuntimeError("El banco no entregó XLSX; no se renombra un CSV como Excel.")
        temporal = os.path.join(ctx.descargas_dir, "galicia_por_validar.xlsx")
        descarga.save_as(temporal)
        self.validar_excel(temporal)
        nombre = "%s %s.xlsx" % (self.prefijo, datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S_%f"))
        destino = os.path.join(carpeta_destino, nombre)
        # El vigilante sólo ve el Excel cuando terminó de copiarse y fue validado.
        fd, parcial = tempfile.mkstemp(suffix=".part", dir=carpeta_destino)
        os.close(fd)
        try:
            shutil.copyfile(temporal, parcial)
            os.replace(parcial, destino)
        finally:
            if os.path.exists(parcial):
                os.remove(parcial)
        return destino

    def extraer_cuenta_id(self, archivo_csv):
        return self.cuenta
