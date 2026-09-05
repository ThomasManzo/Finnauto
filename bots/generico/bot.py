# -*- coding: utf-8 -*-
"""
bots.generico — un solo bot que sirve para casi cualquier banco.

Thomas describió el recorrido que comparten casi todos los home banking:

    cuenta principal -> apretás en saldo -> salen los movimientos ->
    filtro de fecha -> aplicás -> salen los movimientos del rango ->
    botón de descarga -> listo

Si el RECORRIDO es siempre el mismo y lo único que cambia son los nombres de
los botones, entonces un banco nuevo no debería ser un programa nuevo: debería
ser una FICHA de selectores.

    bots/<banco>/selectores.json   <- lo único que se escribe por banco

Es la misma idea que ya usamos con los clientes: lo que varía va en datos, no en
código. Sumar Santander pasa de ser 600 líneas de Python a llenar un archivo.

Cómo funciona
-------------
Cada paso tiene una LISTA de selectores candidatos y se prueba en orden hasta
que uno funciona. No es una comodidad: los home banking cambian el frente cada
tanto, y tener 3 formas de encontrar el mismo botón es lo que evita que el bot
se caiga un martes cualquiera. El bot de Galicia ya funciona así; acá eso deja
de estar escondido en el código y pasa a ser configuración.

Cuándo NO usar esto
-------------------
Cuando un banco hace algo que no entra en el recorrido (un iframe raro, un
segundo factor en cada paso, una grilla que se arma con canvas). Para esos casos
sigue existiendo la opción de escribir un adaptador a mano heredando de
BotBanco: `bots/galicia/bot.py` es exactamente eso. El genérico es el default,
no una obligación.
"""

import io
import os
import re
import json
import datetime

from bots.base import BotBanco
from nucleo.log import log
from nucleo.utilidades import _norm, _parse_monto, _click_robusto


BASE_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def ruta_ficha(banco):
    return os.path.join(BASE_REPO, "bots", banco, "selectores.json")


def cargar_ficha(banco):
    ruta = ruta_ficha(banco)
    if not os.path.exists(ruta):
        raise IOError("No existe la ficha del banco: %s\n"
                      "Copiala de bots/_plantilla/selectores.json y completala "
                      "con la pasada de scripts/explorar_dom.py" % ruta)
    with io.open(ruta, encoding="utf-8") as f:
        return json.load(f)


class BotGenerico(BotBanco):
    """Bot manejado por ficha. Se instancia con el nombre del banco."""

    def __init__(self, banco, ficha=None):
        self.banco = banco
        self.f = ficha if ficha is not None else cargar_ficha(banco)
        self.nombre = self.f.get("nombre") or banco.capitalize()
        self.url = self.f.get("url", "")

    # ------------------------------------------------------------ helpers
    def _sels(self, *camino):
        """Devuelve la lista de selectores de un paso, o [] si no está definido."""
        d = self.f
        for k in camino:
            if not isinstance(d, dict) or k not in d:
                return []
            d = d[k]
        if isinstance(d, str):
            return [d]
        # Los que empiezan con '>>>' son TODO sin completar: no son selectores.
        return [s for s in (d or []) if isinstance(s, str) and not s.startswith(">>>")]

    def _click(self, page, camino, etiqueta, obligatorio=True):
        sels = self._sels(*camino)
        if not sels:
            if obligatorio:
                raise Exception("La ficha de %s no define '%s' (%s)" % (
                    self.banco, ".".join(camino), etiqueta))
            return False
        intentos = [self._locator(page, s) for s in sels]
        try:
            _click_robusto(page, intentos, etiqueta)
            return True
        except Exception:
            if obligatorio:
                raise
            return False

    def _locator(self, page, sel):
        """Un selector puede ser CSS o 'texto=Lo que dice el boton'.

        Se soporta la forma por texto porque en muchos bancos el boton no tiene
        ni id ni name, y lo unico estable es lo que dice.
        """
        s = sel.strip()
        if s.lower().startswith(("texto=", "text=")):
            t = s.split("=", 1)[1]
            return lambda: page.get_by_text(re.compile(re.escape(t), re.I)).first
        if s.lower().startswith("boton="):
            t = s.split("=", 1)[1]
            return lambda: page.get_by_role("button", name=re.compile(re.escape(t), re.I)).first
        return lambda: page.locator(s).first

    def _primer_texto(self, page, camino):
        for s in self._sels(*camino):
            try:
                loc = self._locator(page, s)()
                if loc.count() and loc.is_visible():
                    t = (loc.inner_text() or "").strip()
                    if t:
                        return t
            except Exception:
                continue
        return None

    def _esperar(self, page, camino, default=2000):
        page.wait_for_timeout(int(self.f.get("esperas", {}).get(camino, default)))

    # ------------------------------------------------------------ login
    def hacer_login(self, page, usuario, clave, timeout):
        page.goto(self.url, timeout=timeout)
        self._esperar(page, "despues_de_abrir", 2500)

        # Algunos bancos muestran un banner de cookies antes de todo.
        self._click(page, ("login", "cerrar_banner"), "banner", obligatorio=False)

        for sel in self._sels("login", "usuario"):
            try:
                page.locator(sel).first.fill(usuario, timeout=6000)
                break
            except Exception:
                continue
        else:
            raise Exception("No pude escribir el usuario (revisar login.usuario en la ficha)")

        # Bancos en dos pasos: primero usuario, despues clave.
        self._click(page, ("login", "siguiente"), "siguiente", obligatorio=False)
        self._esperar(page, "entre_usuario_y_clave", 1500)

        for sel in self._sels("login", "clave"):
            try:
                page.locator(sel).first.fill(clave, timeout=6000)
                break
            except Exception:
                continue
        else:
            raise Exception("No pude escribir la clave (revisar login.clave en la ficha)")

        self._click(page, ("login", "ingresar"), "ingresar")
        self._esperar(page, "despues_de_login", 6000)

        # Confirmar que realmente entro: si no, el bot sigue "trabajando" sobre
        # la pantalla de login y falla mucho mas tarde, con un error confuso.
        conf = self._sels("login", "confirmacion")
        if conf:
            for s in conf:
                try:
                    self._locator(page, s)().wait_for(state="visible", timeout=15000)
                    return
                except Exception:
                    continue
            raise Exception("Entre usuario y clave pero no aparecio la pantalla "
                            "esperada: revisar login.confirmacion, o el banco "
                            "pidio un segundo factor.")

    # ------------------------------------------------------------ empresas
    def capturar_empresa_activa(self, page):
        return self._primer_texto(page, ("empresas", "activa"))

    def descubrir_empresas(self, page, timeout, excluir, solo=None):
        # Muchas PYMEs tienen UNA sola empresa: ahi este paso no existe.
        if not self.f.get("empresas", {}).get("tiene", False):
            act = self.capturar_empresa_activa(page)
            return [act] if act else []

        self._click(page, ("empresas", "abrir_selector"), "selector de empresas")
        self._esperar(page, "menu_empresas", 2000)

        nombres, filas = [], self._sels("empresas", "filas")
        for sel in filas:
            try:
                loc = page.locator(sel)
                n = loc.count()
                for i in range(min(n, 200)):
                    t = (loc.nth(i).inner_text() or "").strip()
                    if t and t not in nombres:
                        nombres.append(t)
                if nombres:
                    break
            except Exception:
                continue

        self._click(page, ("empresas", "cerrar"), "cerrar selector", obligatorio=False)

        ex = [_norm(e) for e in (excluir or [])]
        so = [_norm(e) for e in (solo or [])] if solo else None
        out = []
        for n in nombres:
            if _norm(n) in ex:
                continue
            if so and _norm(n) not in so:
                continue
            out.append(n)
        return out

    def cambiar_a_empresa(self, page, nombre, timeout):
        if not self.f.get("empresas", {}).get("tiene", False):
            return
        self._click(page, ("empresas", "abrir_selector"), "selector de empresas")
        self._esperar(page, "menu_empresas", 2000)

        # Si hay buscador, se escribe: con 30 empresas, scrollear es fragil.
        for sel in self._sels("empresas", "buscador"):
            try:
                page.locator(sel).first.fill(nombre[:20], timeout=4000)
                page.wait_for_timeout(1200)
                break
            except Exception:
                continue

        for sel in self._sels("empresas", "filas"):
            try:
                loc = page.locator(sel)
                for i in range(min(loc.count(), 200)):
                    fila = loc.nth(i)
                    if _norm(fila.inner_text()) == _norm(nombre):
                        fila.scroll_into_view_if_needed(timeout=2500)
                        fila.click(timeout=6000)
                        self._esperar(page, "despues_de_cambiar_empresa", 4000)
                        return
            except Exception:
                continue
        raise Exception("No encontre la empresa '%s' en el selector" % nombre)

    # ------------------------------------------------------------ cuenta
    def ir_a_cuenta(self, page, timeout):
        """El paso que describio Thomas: entrar a la cuenta y apretar en saldo."""
        self._click(page, ("cuenta", "ir_a_cuentas"), "menu de cuentas", obligatorio=False)
        self._esperar(page, "listado_cuentas", 3000)
        self._click(page, ("cuenta", "abrir_saldo"), "saldo de la cuenta")
        self._esperar(page, "movimientos", 3500)

    def capturar_saldos(self, page):
        act = self._primer_texto(page, ("saldos", "actual"))
        dis = self._primer_texto(page, ("saldos", "disponible"))
        return {"actual_texto": act, "actual": _parse_monto(act) if act else None,
                "disponible_texto": dis, "disponible": _parse_monto(dis) if dis else None}

    # ------------------------------------------------------------ fechas
    def aplicar_filtro_fechas(self, page, desde, hasta, timeout):
        self._click(page, ("fechas", "abrir_filtros"), "filtros", obligatorio=False)
        self._esperar(page, "filtros_abiertos", 1500)

        fmt = self.f.get("fechas", {}).get("formato", "%d/%m/%Y")
        d, h = desde.strftime(fmt), hasta.strftime(fmt)

        modo = self.f.get("fechas", {}).get("modo", "inputs")
        if modo == "inputs":
            ok_d = self._escribir_fecha(page, ("fechas", "desde"), d)
            ok_h = self._escribir_fecha(page, ("fechas", "hasta"), h)
            if not (ok_d and ok_h):
                log("No pude cargar las fechas (revisar fechas.desde / fechas.hasta).")
                return False
        else:
            # Calendario: cada banco arma el suyo. Galicia usa react-datepicker y
            # tiene su propio adaptador. Si aparece otro calendario, conviene
            # escribir el adaptador a mano antes que forzar el generico.
            log("La ficha dice modo='%s': este banco necesita adaptador propio "
                "para el calendario." % modo)
            return False

        self._click(page, ("fechas", "aplicar"), "aplicar filtro")
        self._esperar(page, "despues_de_aplicar", 4000)

        # Verificar que el filtro efectivamente se aplico. Sin esto, el bot puede
        # descargar el periodo por default y nadie se entera hasta que faltan
        # movimientos en la planilla.
        conf = self._sels("fechas", "confirmacion")
        if not conf:
            return True
        for s in conf:
            try:
                self._locator(page, s)().wait_for(state="visible", timeout=10000)
                return True
            except Exception:
                continue
        return False

    def _escribir_fecha(self, page, camino, valor):
        for sel in self._sels(*camino):
            try:
                campo = page.locator(sel).first
                campo.click(timeout=4000)
                campo.fill("", timeout=3000)
                campo.type(valor, delay=40)
                page.keyboard.press("Escape")
                return True
            except Exception:
                continue
        return False

    # ------------------------------------------------------------ descarga
    def descargar_csv(self, page, carpeta_destino, nombre_empresa, timeout, ctx):
        espera = int(self.f.get("descarga", {}).get("espera_ms", 30000))
        with page.expect_download(timeout=espera) as info:
            self._click(page, ("descarga", "boton"), "boton de descarga")
            # Algunos bancos abren un menu para elegir CSV o Excel.
            self._click(page, ("descarga", "opcion"), "opcion CSV", obligatorio=False)
        descarga = info.value

        sugerido = descarga.suggested_filename or "extracto.csv"
        raiz, ext = os.path.splitext(sugerido)
        ext = ext or ".csv"
        sello = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        # El nombre ORIGINAL del banco se conserva a proposito: ahi suele venir
        # el numero de cuenta (Galicia lo pone como CC<numero>), y es de donde
        # sale extraer_cuenta_id(). Si se descarta, ese dato se pierde y el
        # registro de saldos queda sin poder decir a que cuenta corresponde.
        base = "%s_%s_%s_%s%s" % (self.banco, _norm(nombre_empresa).replace(" ", "-"),
                                  sello, raiz[:40], ext)
        destino = os.path.join(carpeta_destino, base)
        descarga.save_as(destino)
        log("Descargado: %s" % destino)
        return destino

    def extraer_cuenta_id(self, archivo_csv):
        patron = self.f.get("descarga", {}).get("patron_cuenta_id")
        if not patron:
            return None
        m = re.search(patron, os.path.basename(archivo_csv or ""))
        return m.group(1) if m else None
