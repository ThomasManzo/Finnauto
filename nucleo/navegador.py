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
def abrir_navegador(perfil_dir, descargas_dir, headless, viewport=None):
    viewport = viewport or {"width": 1440, "height": 900}
    with sync_playwright() as p:
        contexto = p.chromium.launch_persistent_context(
            perfil_dir,
            headless=headless,
            accept_downloads=True,
            downloads_path=descargas_dir,
            args=["--start-maximized"],
            viewport=viewport,
        )
        page = contexto.pages[0] if contexto.pages else contexto.new_page()
        try:
            yield page
        finally:
            try:
                contexto.close()
            except Exception:
                pass
