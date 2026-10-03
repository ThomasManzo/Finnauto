# -*- coding: utf-8 -*-
"""
nucleo.navegador — abre el navegador (Chromium vía Playwright) con perfil
persistente (recuerda cookies / "dispositivo reconocido" para no revalidar).

Se usa como context manager:

    with abrir_navegador(perfil_dir, descargas_dir, headless) as page:
        ...usar page...
"""

import sys
from contextlib import contextmanager

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Falta Playwright. Instalalo con:  pip install -r requirements.txt")
    print("Y después:  python -m playwright install chromium")
    sys.exit(1)


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
