# -*- coding: utf-8 -*-
"""
nucleo.navegador — abre el navegador (Chromium vía Playwright) con perfil
persistente (recuerda cookies / "dispositivo reconocido" para no revalidar).

Se usa como context manager:

    with abrir_navegador(perfil_dir, descargas_dir, headless) as page:
        ...usar page...
"""

import json
import os
import sys
from contextlib import contextmanager

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Falta Playwright. Instalalo con:  pip install -r requirements.txt")
    print("Y después:  python -m playwright install chromium")
    sys.exit(1)


def _sin_guardar_claves(perfil_dir):
    """Apaga el "¿Guardar contraseña?" de Chrome en el perfil del bot (10/11/2026).

    El cartel no traba al bot, pero no queremos que el navegador ofrezca guardar claves de bancos:
    si alguien lo acepta, la clave quedaría guardada en el perfil del navegador, fuera del llavero.
    Se escribe en las preferencias del perfil ANTES de abrirlo; si ya estaba apagado, no toca nada.
    """
    ruta = os.path.join(perfil_dir, "Default", "Preferences")
    try:
        with open(ruta, encoding="utf-8") as f:
            prefs = json.load(f)
    except (OSError, ValueError):
        prefs = {}
    perfil = prefs.setdefault("profile", {})
    if prefs.get("credentials_enable_service") is False and perfil.get("password_manager_enabled") is False:
        return
    prefs["credentials_enable_service"] = False
    perfil["password_manager_enabled"] = False
    try:
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(prefs, f)
    except OSError as e:
        print("Aviso: no pude apagar el guardado de claves del navegador: %s" % e)


@contextmanager
def abrir_navegador(perfil_dir, descargas_dir, headless, viewport=None, canal=None):
    """canal: None = el Chromium que trae Playwright (el de siempre).
    "msedge" = el Microsoft Edge instalado en la máquina; "chrome" = el Google Chrome instalado.
    Sirve para probar si un banco anda mejor con un navegador "de verdad".
    """
    viewport = viewport or {"width": 1440, "height": 900}
    opciones = {}
    if canal:
        opciones["channel"] = canal
    _sin_guardar_claves(perfil_dir)
    with sync_playwright() as p:
        contexto = p.chromium.launch_persistent_context(
            perfil_dir,
            headless=headless,
            accept_downloads=True,
            downloads_path=descargas_dir,
            args=["--start-maximized"],
            viewport=viewport,
            **opciones
        )
        page = contexto.pages[0] if contexto.pages else contexto.new_page()
        try:
            yield page
        finally:
            try:
                contexto.close()
            except Exception:
                pass
