# -*- coding: utf-8 -*-
"""
nucleo.log — logueo a archivo + consola, y capturas de pantalla numeradas.

Se configura una vez por corrida (configurar(...)) con las rutas del cliente/banco
en curso, y después se usa log(msg) y captura(page, nombre) desde cualquier lado.
Esto reemplaza las funciones log()/captura() que estaban repetidas en cada bot.
"""

import os
import datetime

# Estado del módulo (se setea con configurar()). Arranca con valores neutros
# para que log() funcione aunque todavía no se haya configurado.
_ARCHIVO_LOG = None
_CARPETA_CAPTURAS = None
_cap_n = [0]


def configurar(archivo_log, carpeta_capturas):
    """Setea a dónde escribe el log y dónde se guardan las capturas."""
    global _ARCHIVO_LOG, _CARPETA_CAPTURAS
    _ARCHIVO_LOG = archivo_log
    _CARPETA_CAPTURAS = carpeta_capturas
    _cap_n[0] = 0


def log(msg):
    linea = "[%s] %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(linea)
    if not _ARCHIVO_LOG:
        return
    try:
        with open(_ARCHIVO_LOG, "a", encoding="utf-8") as f:
            f.write(linea + "\n")
    except Exception:
        pass


def captura(page, nombre):
    """Guarda una foto de la pantalla actual. Sirve para depurar sin ver la web.
    Cada captura se numera (01_, 02_, ...) para que queden en orden."""
    if not _CARPETA_CAPTURAS:
        return
    try:
        _cap_n[0] += 1
        archivo = os.path.join(_CARPETA_CAPTURAS, "%02d_%s.png" % (_cap_n[0], nombre))
        page.screenshot(path=archivo, full_page=False)
    except Exception:
        pass
