# -*- coding: utf-8 -*-
"""
nucleo.utilidades — helpers chicos que usan todos los bots.

Salen 1:1 de bot_galicia.py / bot_comafi.py (eran idénticos en los dos), así que
ahora viven una sola vez acá.
"""

import re
import datetime

MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _norm(s):
    """Normaliza para comparar nombres de empresa: minúsculas, sin acentos, y
    espacios/puntos colapsados. Así 'Speedmed Sa' == 'SPEEDMED SA' y
    'Farmacia Rotonda S. C. S.' matchea aunque cambie el espaciado."""
    s = (s or "").lower().strip()
    for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n")):
        s = s.replace(a, b)
    s = s.replace(".", " ")
    return " ".join(s.split())


def fmt(fecha):
    """Fecha -> 'dd/mm/aaaa'."""
    return fecha.strftime("%d/%m/%Y")


def _slug(s):
    """Texto -> nombre seguro para archivos (solo letras/números/_)."""
    return "".join(c if c.isalnum() else "_" for c in s)[:40]


def _parse_monto(txt):
    """Convierte un monto argentino '$348.103.008,01' (o '-$1.234,50') a float
    348103008.01. Devuelve None si no puede."""
    if not txt:
        return None
    s = txt.strip()
    neg = s.startswith("-") or s.startswith("(")
    # dejar solo dígitos, puntos y comas
    s = re.sub(r"[^\d.,]", "", s)
    if not s:
        return None
    # formato AR: '.' miles, ',' decimales -> saco puntos, coma->punto
    s = s.replace(".", "").replace(",", ".")
    try:
        val = float(s)
        return -val if neg else val
    except ValueError:
        return None


def _click_robusto(page, intentos, etiqueta):
    """Prueba varios locators (funciones que devuelven un Locator) y clickea el
    primero visible. Evita agarrar elementos escondidos/fuera de pantalla.
    'intentos' es una lista de lambdas: [lambda: page.locator(...).first, ...]."""
    ultimo = None
    for hacer in intentos:
        try:
            loc = hacer()
            loc.wait_for(state="visible", timeout=4000)
            try:
                loc.scroll_into_view_if_needed(timeout=2500)
            except Exception:
                pass
            loc.click(timeout=6000)
            return
        except Exception as e:
            ultimo = e
            continue
    raise Exception("No pude clickear '%s' (%s)" % (etiqueta, str(ultimo)[:100]))


def _pasa_filtros(nombre, excluir, solo):
    """True si 'nombre' debe procesarse según los filtros del perfil del cliente.
    excluir = lista de nombres a saltar; solo = si tiene algo, SOLO esos."""
    nl = nombre.lower()
    if any(e.strip().lower() == nl for e in (excluir or []) if e.strip()):
        return False
    sol = [s.strip().lower() for s in (solo or []) if s.strip()]
    if sol and not any(s in nl for s in sol):
        return False
    return True
