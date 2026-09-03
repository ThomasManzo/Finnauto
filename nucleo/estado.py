# -*- coding: utf-8 -*-
"""
nucleo.estado — recuerda hasta qué día se bajó cada empresa (anti-duplicado).

Es un JSON { "NOMBRE EMPRESA": "AAAA-MM-DD" } por cliente+banco. Con eso el bot
sabe desde qué día bajar la próxima vez y no repite (además, el clasificador
dedup por huellas, así que el solape de un día tampoco duplica).
"""

import os
import json


def cargar(estado_path):
    if os.path.exists(estado_path):
        try:
            with open(estado_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def guardar(estado_path, estado):
    os.makedirs(os.path.dirname(estado_path), exist_ok=True)
    with open(estado_path, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)
