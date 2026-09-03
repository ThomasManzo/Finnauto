# -*- coding: utf-8 -*-
"""
bots.comafi — adaptador de Comafi Empresas (eBanking).

>>> ESTADO: ANDAMIAJE. El recorrido (motor) ya lo pone el núcleo y funciona.
    Lo específico de Comafi (los SELECTORES del DOM) está marcado con
    # >>> TODO COMAFI y hay que afinarlo contra la web real, igual que se hizo
    con Galicia (correr en modo prueba, mirar capturas, ajustar selectores).

DIFERENCIA CLAVE con Galicia: el clasificador de Comafi identifica la farmacia
por el NOMBRE DEL ARCHIVO (no por el CUIT). Por eso descargar_csv renombra el
extracto como '<prefijo>_<Empresa>_<DD-MM>.csv'.
"""

import re
import os
import datetime

from nucleo.log import log, captura
from nucleo.utilidades import _norm, _parse_monto, _slug, fmt, _click_robusto
from bots.base import BotBanco

# URL confirmada por captura (2026-08-29). Comafi pide TOKEN solo para autorizar
# operaciones, NO para consultar -> el login para bajar extractos es usuario+clave.
URL_COMAFI = "https://ebanking.comafiempresas.com.ar/login"


class BotComafi(BotBanco):
    nombre = "Comafi"
    url = URL_COMAFI

    def __init__(self):
        self._nombre_usuario = None

    def hacer_login(self, page, usuario, clave, timeout):
        """>>> TODO COMAFI: verificar contra la pantalla real:
          - Si hay pantalla intermedia ('Empresas' vs 'Individuos').
          - Selectores exactos de usuario/clave y del botón Ingresar.
          - Si pide segundo factor para VER extractos (Galicia no lo pedía)."""
        log("Abriendo Comafi...")
        page.goto(self.url, timeout=timeout)
        page.wait_for_timeout(3000)
        captura(page, "home_comafi")

        # >>> TODO COMAFI: si hay un botón/solapa para entrar a "Empresas", clickearlo.
        for sel in ["text=Empresas", "role=link[name=/empresas/i]", "role=button[name=/empresas/i]"]:
            try:
                page.locator(sel).first.click(timeout=3000)
                page.wait_for_timeout(2000)
                break
            except Exception:
                continue
        captura(page, "pantalla_login")

        # Campo Usuario: primer input de texto visible que NO sea password (robusto).
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

        campo_clave = page.locator("input[type='password']").first
        campo_clave.fill(clave, timeout=timeout)
        captura(page, "clave_cargada")

        for sel in ["role=button[name=/ingresar/i]", "text=Ingresar", "button:has-text('Ingresar')",
                    "role=button[name=/aceptar/i]", "text=Aceptar"]:
            try:
                page.locator(sel).first.click(timeout=6000)
                break
            except Exception:
                continue

        page.wait_for_timeout(6000)
        captura(page, "post_login")
        log("Login enviado.")
        # >>> TODO COMAFI: capturar nombre de usuario / empresa activa del encabezado.

    def capturar_empresa_activa(self, page):
        """>>> TODO COMAFI: ubicar dónde muestra Comafi la empresa activa.
        De arranque reusa la heurística de Galicia (línea corta con sufijo societario)."""
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
                    continue
                if "$" in l or "N°" in l or "cuenta" in l.lower():
                    continue
                if sufijo.search(l):
                    return l.strip()
        return None

    def descubrir_empresas(self, page, timeout, excluir, solo=None):
        """>>> TODO COMAFI: la estructura (abrir selector -> leer filas -> cerrar)
        está lista; faltan los SELECTORES reales de Comafi."""
        log("Descubriendo empresas...")
        nombres = []
        try:
            self._abrir_selector_empresas(page, timeout)
            page.wait_for_timeout(2000)
            captura(page, "selector_empresas")
            nombres = self._leer_lista_empresas(page)
            self._cerrar_modal(page)
        except Exception as e:
            log("Aviso descubriendo empresas: %s" % e)
            captura(page, "ERROR_selector_empresas")

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

    def _abrir_selector_empresas(self, page, timeout):
        """>>> TODO COMAFI: reemplazar por el/los selector(es) reales."""
        for sel in ["text=Cambiar empresa", "text=Elegir empresa", "text=Seleccionar empresa",
                    "[aria-haspopup='true']", "button:has-text('empresa')"]:
            try:
                page.locator(sel).first.click(timeout=3000)
                page.wait_for_timeout(1000)
                return
            except Exception:
                continue
        raise Exception("TODO COMAFI: no pude abrir el selector de empresas (ajustar selectores).")

    def _leer_lista_empresas(self, page):
        """>>> TODO COMAFI: reemplazar el locator de las filas por el real."""
        nombres = []
        descartar = ("cambiar empresa", "elegir empresa", "cancelar", "buscar", "buscar por nombre")
        try:
            filas = page.locator("[role='dialog'] li, [role='listbox'] [role='option'], table tbody tr")
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

    def cambiar_a_empresa(self, page, nombre, timeout):
        """>>> TODO COMAFI: afinar apertura + fila objetivo + buscador."""
        self._abrir_selector_empresas(page, timeout)
        page.wait_for_timeout(1500)

        for sel in ["[role='dialog'] input", "input[placeholder*='nombre' i]", "input[placeholder*='buscar' i]"]:
            try:
                page.locator(sel).first.fill(nombre, timeout=3000)
                page.wait_for_timeout(1200)
                break
            except Exception:
                continue

        objetivo = _norm(nombre)
        filas = page.locator("[role='dialog'] li, [role='listbox'] [role='option'], table tbody tr")
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
            raise Exception("No encontré la empresa '%s' en el selector de Comafi." % nombre)
        page.wait_for_timeout(5000)
        captura(page, "empresa_%s" % _slug(nombre))

    def _cerrar_modal(self, page):
        for sel in ["text=Cancelar", "[role='dialog'] button[aria-label*='cerrar' i]", "text=×"]:
            try:
                page.locator(sel).first.click(timeout=2500)
                page.wait_for_timeout(800)
                return
            except Exception:
                continue
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass

    def ir_a_cuenta(self, page, timeout):
        """>>> TODO COMAFI: menú 'Cuentas'/'Saldos y movimientos' -> abrir la cuenta."""
        for sel in ["role=link[name=/movimientos/i]", "text=Movimientos",
                    "role=link[name=/saldos y movimientos/i]", "text=Saldos y movimientos",
                    "role=link[name=/^cuentas$/i]", "text=Cuentas"]:
            try:
                page.locator(sel).first.click(timeout=5000)
                page.wait_for_timeout(1500)
                break
            except Exception:
                continue
        page.wait_for_timeout(2500)
        captura(page, "listado_cuentas")

        for sel in ["text=/\\$\\s?[0-9]/", "[class*='cuenta']", "table tbody tr"]:
            try:
                page.locator(sel).first.click(timeout=5000)
                break
            except Exception:
                continue
        page.wait_for_timeout(3000)
        captura(page, "movimientos")

    def capturar_saldos(self, page):
        """>>> TODO COMAFI: ubicar las etiquetas/estructura reales de Actual/Disponible."""
        out = {"actual_texto": None, "actual": None,
               "disponible_texto": None, "disponible": None}
        for clave, etiqueta in (("actual", "Actual"), ("disponible", "Disponible")):
            txt = None
            try:
                loc = page.locator(
                    "xpath=//*[normalize-space(text())='%s']/following-sibling::*[1]" % etiqueta).first
                loc.wait_for(state="visible", timeout=4000)
                txt = (loc.inner_text() or "").strip()
            except Exception:
                pass
            if txt:
                out[clave + "_texto"] = txt
                out[clave] = _parse_monto(txt)
            else:
                log("   Aviso: no pude leer saldo '%s' (ajustar selector Comafi)." % etiqueta)
        return out

    def aplicar_filtro_fechas(self, page, desde, hasta, timeout):
        """>>> TODO COMAFI: según el control real. Puede ser (a) inputs donde se
        ESCRIBE dd/mm/aaaa, o (b) un datepicker (portar los helpers de Galicia)."""
        captura(page, "antes_filtro")
        for sel in ["role=button[name=/filtr/i]", "text=Filtros", "text=Filtrar",
                    "role=button[name=/buscar/i]"]:
            try:
                page.locator(sel).first.click(timeout=3000)
                page.wait_for_timeout(1000)
                break
            except Exception:
                continue
        captura(page, "panel_filtros")

        ok = False
        try:
            campos = page.locator("input[placeholder*='/'], input[type='date'], input[name*='fecha' i]")
            if campos.count() >= 2:
                campos.nth(0).fill(fmt(desde), timeout=4000)
                campos.nth(1).fill(fmt(hasta), timeout=4000)
                ok = True
            elif campos.count() == 1:
                campos.nth(0).fill("%s - %s" % (fmt(desde), fmt(hasta)), timeout=4000)
                ok = True
        except Exception as e:
            log("Aviso escribiendo fechas: %s" % e)
        captura(page, "fechas_cargadas")
        if not ok:
            log("TODO COMAFI: no pude cargar las fechas (revisar el control de fechas real).")

        for sel in ["role=button[name=/aplicar/i]", "text=Aplicar",
                    "role=button[name=/buscar/i]", "text=Buscar", "role=button[name=/filtrar/i]"]:
            try:
                page.locator(sel).first.click(timeout=4000)
                page.wait_for_timeout(3000)
                break
            except Exception:
                continue
        captura(page, "movimientos_filtrados")
        return ok

    def descargar_csv(self, page, carpeta_destino, nombre_empresa, timeout, ctx):
        """>>> TODO COMAFI: afinar el botón de descarga y la opción .CSV/Excel.
        Guarda con el NOMBRE DE LA EMPRESA en el nombre (clave para el clasificador)."""
        _click_robusto(page, [
            lambda: page.get_by_role("button", name=re.compile(r"descarg|export", re.I)).first,
            lambda: page.locator("button[aria-label*='descarg' i], button[aria-label*='export' i]").first,
            lambda: page.get_by_text(re.compile(r"descargar|exportar", re.I)).first,
            lambda: page.locator("[class*='download'] button, button[class*='download']").first,
        ], "botón de descarga")
        page.wait_for_timeout(1200)
        captura(page, "menu_descarga")

        with page.expect_download(timeout=timeout) as info:
            _click_robusto(page, [
                lambda: page.get_by_text(".CSV", exact=True).first,
                lambda: page.get_by_role("menuitem", name=re.compile(r"csv", re.I)).first,
                lambda: page.get_by_text(re.compile(r"^\.?csv$", re.I)).first,
                lambda: page.get_by_text(re.compile(r"excel", re.I)).first,  # fallback
            ], ".CSV")
        descarga = info.value

        # Comafi: renombrar con el NOMBRE de la empresa (lo usa el clasificador).
        ext = os.path.splitext(descarga.suggested_filename or "extracto.csv")[1] or ".csv"
        prefijo = ctx.prefijo_archivo or "Comafi"
        fecha_tag = datetime.date.today().strftime("%d-%m")
        base = "%s_%s_%s%s" % (prefijo, _slug(nombre_empresa or "empresa"), fecha_tag, ext)
        destino = os.path.join(carpeta_destino, base)
        if os.path.exists(destino):
            raiz, e = os.path.splitext(base)
            destino = os.path.join(carpeta_destino, "%s_%s%s" % (
                raiz, datetime.datetime.now().strftime("%H%M%S"), e))
        descarga.save_as(destino)
        log("   Descargado: %s" % os.path.basename(destino))
        return destino
