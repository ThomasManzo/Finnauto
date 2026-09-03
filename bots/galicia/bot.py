# -*- coding: utf-8 -*-
"""
bots.galicia — adaptador de Galicia Office Banking.

Es el ÚNICO archivo específico de Galicia: solo login + navegación + selectores.
El recorrido, las fechas, el estado y las salidas los pone el núcleo.

Portado 1:1 de bot_galicia.py (que funciona end-to-end, 15 empresas). Los
"aprendizajes del DOM" de Galicia están en los comentarios de cada método; si el
banco cambia la web, se ajustan acá y nada más.
"""

import re
import os
import datetime

from nucleo.log import log, captura
from nucleo.utilidades import _norm, _parse_monto, _slug, fmt, _click_robusto, MESES_ES
from bots.base import BotBanco

URL_GALICIA = "https://www.galicia.ar/empresas"


class BotGalicia(BotBanco):
    nombre = "Galicia"
    url = URL_GALICIA

    def __init__(self):
        # Nombre de pila del usuario logueado (ej "Luna"): sirve para abrir el
        # menú de empresas (el chip arriba a la derecha lleva el nombre).
        self._nombre_usuario = None

    # ============================================================
    #  LOGIN
    # ============================================================
    def hacer_login(self, page, usuario, clave, timeout):
        log("Abriendo Galicia...")
        page.goto(self.url, timeout=timeout)
        page.wait_for_timeout(2500)
        captura(page, "home_galicia")

        # Botón "Office Banking" (arriba a la derecha). El texto puede variar.
        clickeado = False
        for sel in ["text=Office Banking", "role=link[name=/office banking/i]",
                    "role=button[name=/office banking/i]"]:
            try:
                page.locator(sel).first.click(timeout=6000)
                clickeado = True
                break
            except Exception:
                continue
        if not clickeado:
            raise Exception("No encontré el botón 'Office Banking' en la home de Galicia.")

        page.wait_for_timeout(4000)
        captura(page, "pantalla_login")

        # La pantalla de login puede pedir Usuario+Clave (perfil nuevo) o solo la
        # clave (si recuerda el usuario -> "Hola, Luna"). Estrategia robusta: el
        # campo Usuario es el primer input de TEXTO visible que NO es password.
        try:
            inputs = page.locator("input")
            total = inputs.count()
            campo_user = None
            for i in range(total):
                inp = inputs.nth(i)
                try:
                    if not inp.is_visible():
                        continue
                    tipo = (inp.get_attribute("type") or "text").lower()
                    if tipo in ("text", "email", "tel", "search", ""):
                        campo_user = inp
                        break
                except Exception:
                    continue
            if campo_user is not None:
                campo_user.click(timeout=4000)
                campo_user.fill(usuario, timeout=5000)
                log("Usuario cargado.")
                # tildar "Recordar usuario" si está, para futuros logins
                try:
                    page.get_by_text(re.compile(r"(?i)recordar usuario")).first.click(timeout=2000)
                except Exception:
                    pass
                # por si hubiera un paso 'Continuar' antes de la clave
                if page.locator("input[type='password']:visible").count() == 0:
                    for sel in ["role=button[name=/continuar/i]", "text=Continuar", "text=Siguiente"]:
                        try:
                            page.locator(sel).first.click(timeout=3000)
                            page.wait_for_timeout(2000)
                            break
                        except Exception:
                            continue
            else:
                log("No hay campo de usuario (el navegador ya lo recuerda); voy directo a la clave.")
        except Exception as e:
            log("Aviso cargando usuario: %s" % e)

        # Campo de clave
        campo_clave = page.locator("input[type='password']").first
        campo_clave.fill(clave, timeout=timeout)
        captura(page, "clave_cargada")

        # Botón "Ingresar"
        for sel in ["role=button[name=/ingresar/i]", "text=Ingresar", "button:has-text('Ingresar')"]:
            try:
                page.locator(sel).first.click(timeout=6000)
                break
            except Exception:
                continue

        page.wait_for_timeout(6000)
        captura(page, "post_login")
        log("Login enviado.")

        # Capturar el nombre de pila del usuario (para abrir el menú de empresas).
        try:
            loc = page.get_by_text(re.compile(r"(?i)hola,?\s+([A-Za-zÁÉÍÓÚÑáéíóúñ]+)")).first
            m = re.search(r"(?i)hola,?\s+([A-Za-zÁÉÍÓÚÑáéíóúñ]+)", loc.inner_text())
            if m:
                self._nombre_usuario = m.group(1).strip()
                log("Usuario logueado: %s" % self._nombre_usuario)
        except Exception:
            pass

    # ============================================================
    #  EMPRESA ACTIVA + DESCUBRIR + CAMBIAR
    # ============================================================
    def capturar_empresa_activa(self, page):
        """Lee el nombre de la empresa abierta (chip arriba a la derecha)."""
        textos = []
        for sel in ["header", "body"]:
            try:
                loc = page.locator(sel).first
                if loc.count() > 0:
                    textos.append(loc.inner_text(timeout=3000))
            except Exception:
                continue
        sufijo = re.compile(r"(?i)\b(s\.?\s?a\.?|s\.?\s?c\.?\s?s\.?|s\.?\s?r\.?\s?l\.?|sas|scs)\b")
        nombre_pila = (self._nombre_usuario or "").lower()
        for txt in textos:
            for linea in txt.splitlines():
                l = linea.strip()
                if not l or len(l) > 60:
                    continue
                if nombre_pila and nombre_pila in l.lower():
                    continue  # es la línea del nombre de la persona
                if "$" in l or "N°" in l or "cuenta" in l.lower():
                    continue  # evitar montos / datos de cuenta
                if sufijo.search(l):
                    return l.strip()
        return None

    def descubrir_empresas(self, page, timeout, excluir, solo=None):
        """Abre 'Elegir otra empresa' y devuelve la lista completa de nombres."""
        log("Descubriendo empresas...")
        self._abrir_menu_empresas(page, timeout)
        self._click_elegir_otra_empresa(page, timeout)
        page.wait_for_timeout(2500)
        captura(page, "modal_empresas")

        nombres = self._leer_lista_empresas(page)
        self._cerrar_modal(page)

        # Sacar excluidas y duplicados, ordenar
        excluir_norm = set(e.strip().lower() for e in (excluir or []))
        limpias, vistos = [], set()
        for n in nombres:
            n = n.strip()
            if not n or n.lower() in vistos:
                continue
            if n.lower() in excluir_norm:
                log("  (excluida por config) %s" % n)
                continue
            vistos.add(n.lower())
            limpias.append(n)

        solo_norm = [s.strip().lower() for s in (solo or []) if s.strip()]
        if solo_norm:
            limpias = [n for n in limpias if any(s in n.lower() for s in solo_norm)]
            log("Filtro 'solo_estas_empresas' activo -> quedan %d." % len(limpias))

        log("Empresas encontradas: %d" % len(limpias))
        for n in limpias:
            log("   - %s" % n)
        return limpias

    def cambiar_a_empresa(self, page, nombre, timeout):
        """Selecciona una empresa por nombre desde el modal 'Elegí una empresa'."""
        self._abrir_menu_empresas(page, timeout)
        self._click_elegir_otra_empresa(page, timeout)
        page.wait_for_timeout(2000)

        # Buscar por nombre en el buscador del modal (placeholder 'Buscá por nombre')
        try:
            buscador = page.locator(
                "[data-automation-id='modalComponent'] input, input[placeholder*='nombre' i]").first
            buscador.fill(nombre, timeout=5000)
            page.wait_for_timeout(1500)
        except Exception:
            pass

        objetivo = _norm(nombre)
        filas = self._filas_empresa(page)
        n = filas.count()
        clickeado = False
        for i in range(n):
            f = filas.nth(i)
            try:
                if not f.is_visible():
                    continue
                if _norm(" ".join((f.inner_text() or "").split())) == objetivo:
                    f.click(timeout=timeout)
                    clickeado = True
                    break
            except Exception:
                continue
        if not clickeado:
            try:
                filas.filter(has_text=nombre).first.click(timeout=timeout)
                clickeado = True
            except Exception:
                pass
        if not clickeado:
            raise Exception("No encontré la empresa '%s' en el modal." % nombre)
        page.wait_for_timeout(5000)  # recarga el inicio de la empresa
        captura(page, "empresa_%s" % _slug(nombre))

    # ---- helpers del selector de empresas ----
    def _filas_empresa(self, page):
        # El modal NO es [role='dialog']: es data-automation-id='modalComponent' y
        # las empresas son filas de una react-bootstrap-table.
        return page.locator(
            "[data-automation-id='modalComponent'] .react-bootstrap-table tbody tr td div")

    def _leer_lista_empresas(self, page):
        nombres = []
        descartar = ("elegí una empresa", "elegi una empresa", "cancelar",
                     "buscá por nombre", "busca por nombre")
        try:
            filas = self._filas_empresa(page)
            ultimo_total, intentos = -1, 0
            while intentos < 25:
                for t in filas.all_inner_texts():
                    t = " ".join(t.split()).strip()
                    if t and t.lower() not in descartar and t not in nombres:
                        nombres.append(t)
                if len(nombres) == ultimo_total:
                    break
                ultimo_total = len(nombres)
                try:
                    page.mouse.wheel(0, 600)
                except Exception:
                    pass
                page.wait_for_timeout(400)
                intentos += 1
        except Exception as e:
            log("Aviso leyendo lista de empresas: %s" % e)
        return nombres

    def _elegir_visible(self, page):
        try:
            loc = page.locator("[idmodule='elegir-otra-empresa'], a[title='Elegir otra empresa']").first
            if loc.count() > 0 and loc.is_visible():
                return True
        except Exception:
            pass
        try:
            return page.get_by_text("Elegir otra empresa").first.is_visible()
        except Exception:
            return False

    def _abrir_menu_empresas(self, page, timeout):
        """Abre el desplegable del usuario (arriba a la derecha) y VERIFICA."""
        if self._elegir_visible(page):
            return
        # El botón real del chip de usuario:
        #   div[data-tour='perfil'] button[aria-haspopup='true']
        selectores = [
            "[data-tour='perfil'] button[aria-haspopup='true']",
            "[data-tour='perfil'] button",
        ]
        if self._nombre_usuario:
            selectores.append("text=%s" % self._nombre_usuario)
        selectores += [
            "header [class*='avatar']", "[class*='avatar']", "[class*='Avatar']",
            "header [class*='initial']", "header [class*='user']", "header [class*='usuario']",
            "button[aria-haspopup]", "header button:last-of-type",
        ]
        for sel in selectores:
            try:
                page.locator(sel).last.click(timeout=2500)
                page.wait_for_timeout(1000)
                if self._elegir_visible(page):
                    return
            except Exception:
                continue
        # Fallback: clickear varios puntos del extremo superior derecho
        try:
            w = page.viewport_size["width"]
            for dx, dy in [(-45, 40), (-90, 40), (-150, 40), (-45, 55), (-110, 55), (-200, 42)]:
                try:
                    page.mouse.click(w + dx, dy)
                    page.wait_for_timeout(900)
                    if self._elegir_visible(page):
                        return
                except Exception:
                    continue
        except Exception:
            pass
        captura(page, "ERROR_menu_no_abrio")
        raise Exception("No pude abrir el menú de empresas (arriba a la derecha).")

    def _click_elegir_otra_empresa(self, page, timeout):
        for sel in ["[idmodule='elegir-otra-empresa']", "a[title='Elegir otra empresa']",
                    "text=Elegir otra empresa"]:
            try:
                page.locator(sel).first.click(timeout=5000)
                return
            except Exception:
                continue
        raise Exception("No pude clickear 'Elegir otra empresa'.")

    def _cerrar_modal(self, page):
        for sel in ["text=Cancelar", "[role='dialog'] button[aria-label*='cerrar' i]", "text=×"]:
            try:
                page.locator(sel).first.click(timeout=2500)
                page.wait_for_timeout(1000)
                return
            except Exception:
                continue
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass

    # ============================================================
    #  CUENTA + SALDOS
    # ============================================================
    def ir_a_cuenta(self, page, timeout):
        """Menú Cuentas -> click en el monto de la cuenta -> movimientos."""
        for sel in ["role=link[name=/^cuentas$/i]", "text=Cuentas"]:
            try:
                page.locator(sel).first.click(timeout=6000)
                break
            except Exception:
                continue
        page.wait_for_timeout(3000)
        captura(page, "listado_cuentas")

        clickeado = False
        for sel in ["text=/\\$\\s?[0-9]/", "[class*='cuenta'] [class*='monto']",
                    "[class*='card'] >> text=/\\$/"]:
            try:
                page.locator(sel).first.click(timeout=6000)
                clickeado = True
                break
            except Exception:
                continue
        if not clickeado:
            raise Exception("No encontré el monto de la cuenta para hacer click.")
        page.wait_for_timeout(3500)
        captura(page, "movimientos")

    def capturar_saldos(self, page):
        """Lee 'Actual' y 'Disponible' de la tarjeta de Saldos.
        Estructura Galicia: <p>Actual</p><h4>$348.103.008,01</h4> (el monto es el
        <h4> hermano inmediato del <p> con el texto exacto)."""
        out = {"actual_texto": None, "actual": None,
               "disponible_texto": None, "disponible": None}
        for clave, etiqueta in (("actual", "Actual"), ("disponible", "Disponible")):
            try:
                loc = page.locator(
                    "xpath=//p[normalize-space(text())='%s']/following-sibling::h4[1]" % etiqueta).first
                loc.wait_for(state="visible", timeout=6000)
                txt = (loc.inner_text() or "").strip()
                out[clave + "_texto"] = txt
                out[clave] = _parse_monto(txt)
            except Exception as e:
                log("   Aviso: no pude leer saldo '%s': %s" % (etiqueta, str(e)[:80]))
        return out

    # ============================================================
    #  FILTRO DE FECHAS (calendario react-datepicker)
    # ============================================================
    def aplicar_filtro_fechas(self, page, desde, hasta, timeout):
        # Botón "Filtros" (OJO: hay un párrafo de ayuda que también dice "Filtros";
        # por eso apuntamos al BOTÓN / texto exacto, no a cualquier texto).
        _click_robusto(page, [
            lambda: page.get_by_role("button", name=re.compile(r"filtros", re.I)).first,
            lambda: page.get_by_text("Filtros", exact=True).first,
            lambda: page.locator("button:has-text('Filtros')").first,
            lambda: page.locator("[class*='filtro']:has-text('Filtros')").first,
        ], "Filtros")
        page.wait_for_timeout(1500)
        captura(page, "panel_filtros")

        self._abrir_calendario(page, timeout)
        captura(page, "calendario_abierto")

        self._ir_a_mes(page, desde.year, desde.month, timeout)
        self._click_dia(page, desde.day, timeout)
        page.wait_for_timeout(600)

        self._ir_a_mes(page, hasta.year, hasta.month, timeout)
        self._click_dia(page, hasta.day, timeout)
        page.wait_for_timeout(600)
        captura(page, "fechas_seleccionadas")

        ok = self._verificar_rango(page, desde, hasta)

        _click_robusto(page, [
            lambda: page.get_by_role("button", name=re.compile(r"aplicar", re.I)).first,
            lambda: page.get_by_text("Aplicar", exact=True).first,
            lambda: page.locator("button:has-text('Aplicar')").first,
        ], "Aplicar")
        page.wait_for_timeout(3500)
        captura(page, "movimientos_filtrados")
        return ok

    def _abrir_calendario(self, page, timeout):
        # OJO: si ya está abierto y se vuelve a clickear el campo, se CIERRA (toggle).
        if self._hay_calendario(page):
            return
        intentos = [
            lambda: page.locator("input[placeholder='Desde - Hasta']").first,
            lambda: page.locator(".react-datepicker-wrapper input").first,
            lambda: page.locator("xpath=//*[normalize-space(text())='Fecha']/following::input[1]").first,
            lambda: page.get_by_text(re.compile(r"\d{2}/\d{2}/\d{4}\s*-\s*\d{2}/\d{2}/\d{4}")).first,
            lambda: page.locator("input[readonly]").first,
        ]
        for hacer in intentos:
            if self._hay_calendario(page):
                return
            try:
                hacer().click(timeout=4000)
                page.wait_for_timeout(800)
                if self._hay_calendario(page):
                    return
            except Exception:
                continue
        if not self._hay_calendario(page):
            raise Exception("No pude abrir el calendario de fechas (campo 'Fecha').")

    def _hay_calendario(self, page):
        # Galicia usa react-datepicker con encabezado custom: el mes está en
        # <label class="MonthLabel"> y los días en .react-datepicker__day.
        for sel in (".react-datepicker", ".MonthLabel", ".react-datepicker__day"):
            try:
                if page.locator(sel).first.is_visible():
                    return True
            except Exception:
                continue
        return False

    def _leer_mes_calendario(self, page):
        try:
            txt = page.locator(".MonthLabel").first.inner_text().strip().lower()
            m = re.search(r"(%s)\s+(\d{4})" % "|".join(MESES_ES), txt)
            if m:
                return int(m.group(2)), MESES_ES.index(m.group(1)) + 1
        except Exception:
            pass
        return None

    def _ir_a_mes(self, page, anio, mes, timeout):
        for _ in range(24):
            actual = self._leer_mes_calendario(page)
            if not actual:
                return  # no pude leer el encabezado; confío en el click del día
            a_actual, m_actual = actual
            if a_actual == anio and m_actual == mes:
                return
            avanzar = (anio, mes) > (a_actual, m_actual)
            # prev = arrowback ; next = arrowfoward (sic, typo del banco)
            candidatos_next = ["button[aria-label='arrowfoward']", "button[aria-label*='foward' i]",
                               "button[aria-label*='next' i]"]
            candidatos_prev = ["button[aria-label='arrowback']", "button[aria-label*='back' i]",
                               "button[aria-label*='prev' i]"]
            sels = candidatos_next if avanzar else candidatos_prev
            clic_ok = False
            for sel in sels:
                try:
                    page.locator(sel).first.click(timeout=2500)
                    clic_ok = True
                    break
                except Exception:
                    continue
            if not clic_ok:
                log("Aviso: no pude mover el mes del calendario; intento clickear el día igual.")
                return
            page.wait_for_timeout(400)

    def _click_dia(self, page, dia, timeout):
        # react-datepicker marca cada día con '--0DD' (zero-padded) y los de otro
        # mes con '--outside-month' (los descartamos).
        dd = "%03d" % dia  # ej "026"
        sel = ".react-datepicker__day--%s:not(.react-datepicker__day--outside-month)" % dd
        try:
            loc = page.locator(sel).first
            loc.scroll_into_view_if_needed(timeout=2000)
            loc.click(timeout=timeout)
            return
        except Exception:
            pass
        candidatos = page.locator(".react-datepicker__day")
        n = candidatos.count()
        for i in range(n):
            c = candidatos.nth(i)
            try:
                if not c.is_visible():
                    continue
                cls = (c.get_attribute("class") or "")
                if "react-datepicker__day--outside-month" in cls:
                    continue
                if "--disabled" in cls or (c.get_attribute("aria-disabled") or "").lower() == "true":
                    continue
                if (c.inner_text() or "").strip() != str(dia):
                    continue
                c.click(timeout=timeout)
                return
            except Exception:
                continue
        raise Exception("No encontré el día %d en el calendario." % dia)

    def _verificar_rango(self, page, desde, hasta):
        try:
            esperado_desde = fmt(desde)
            esperado_hasta = fmt(hasta)
            txt = page.get_by_text(
                re.compile(r"\d{2}/\d{2}/\d{4}\s*-\s*\d{2}/\d{2}/\d{4}")).first.inner_text()
            ok = esperado_desde in txt and esperado_hasta in txt
            if not ok:
                log("Aviso: el rango mostrado ('%s') no coincide con lo pedido (%s - %s)." % (
                    txt.strip(), esperado_desde, esperado_hasta))
            return ok
        except Exception:
            return False

    # ============================================================
    #  DESCARGA (.CSV) — Galicia deja el nombre ORIGINAL (trae el CUIT)
    # ============================================================
    def descargar_csv(self, page, carpeta_destino, nombre_empresa, timeout, ctx):
        # Botón de descarga (ícono a la derecha de "Filtros", sin texto).
        _click_robusto(page, [
            lambda: page.get_by_role("button", name=re.compile(r"descarg", re.I)).first,
            lambda: page.locator("button[aria-label*='descarg' i]").first,
            lambda: page.locator("[class*='download'] button, button[class*='download']").first,
            lambda: page.get_by_role("button", name=re.compile(r"filtros", re.I)).locator("xpath=following::button[1]"),
            lambda: page.locator("button:right-of(:text('Filtros'))").first,
            lambda: page.locator("[class*='descarga']").first,
        ], "botón de descarga")
        page.wait_for_timeout(1200)
        captura(page, "menu_descarga")

        with page.expect_download(timeout=timeout) as info:
            _click_robusto(page, [
                lambda: page.get_by_text(".CSV", exact=True).first,
                lambda: page.get_by_role("menuitem", name=re.compile(r"csv", re.I)).first,
                lambda: page.get_by_text(re.compile(r"^\.?csv$", re.I)).first,
            ], ".CSV")
        descarga = info.value

        # Galicia: guardar con el nombre ORIGINAL (trae el CUIT, que usa el clasificador).
        nombre_orig = descarga.suggested_filename or "extracto.csv"
        destino = os.path.join(carpeta_destino, nombre_orig)
        if os.path.exists(destino):
            raiz, ext = os.path.splitext(nombre_orig)
            destino = os.path.join(carpeta_destino, "%s_%s%s" % (
                raiz, datetime.datetime.now().strftime("%H%M%S"), ext))
        descarga.save_as(destino)
        log("   Descargado: %s" % os.path.basename(destino))
        return destino

    def extraer_cuenta_id(self, archivo_csv):
        # 'Extracto_CC544961074.csv' -> '544961074'
        try:
            m = re.search(r"CC(\d+)", os.path.basename(archivo_csv or ""))
            if m:
                return m.group(1)
        except Exception:
            pass
        return None
