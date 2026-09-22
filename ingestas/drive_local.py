# -*- coding: utf-8 -*-
"""
ingestas.drive_local — dónde está montada la carpeta de Drive del cliente en ESTA máquina.

Google Drive para escritorio monta "Mi unidad" en lugares distintos según el sistema:
  · macOS:   ~/Library/CloudStorage/GoogleDrive-<cuenta>/Mi unidad/
  · Windows: G:\\Mi unidad\\  (o la letra que le toque), o ~/Google Drive/Mi unidad/
La carpeta del cliente (ej. "NAVAR - Datos") cuelga de ahí. Se puede fijar a mano con la
variable de entorno FINAUTO_DRIVE=<ruta completa a la carpeta del cliente>.
"""

import os
import glob


def carpeta_datos(nombre="NAVAR - Datos"):
    """Ruta a la carpeta del cliente dentro del Drive montado, o None si no se encuentra."""
    fijada = os.environ.get("FINAUTO_DRIVE")
    if fijada and os.path.isdir(fijada):
        return fijada
    home = os.path.expanduser("~")
    candidatos = []
    # macOS
    candidatos += glob.glob(os.path.join(home, "Library", "CloudStorage", "GoogleDrive-*", "Mi unidad", nombre))
    candidatos += glob.glob(os.path.join(home, "Library", "CloudStorage", "GoogleDrive-*", "My Drive", nombre))
    # Windows: unidad virtual (G:, H:, ...) o carpeta en el perfil
    for letra in "GHIJKLMNOPQRSTUVWXYZ":
        for mi in ("Mi unidad", "My Drive"):
            candidatos.append("%s:\\%s\\%s" % (letra, mi, nombre))
    for mi in ("Mi unidad", "My Drive"):
        candidatos.append(os.path.join(home, "Google Drive", mi, nombre))
        candidatos.append(os.path.join(home, "Mi unidad", nombre))
    # Carpeta COMPARTIDA con la cuenta (no propia): Drive la monta como acceso directo en
    # .shortcut-targets-by-id/<id de la carpeta>/<nombre>. El id no cambia. Vale en Mac y Windows.
    candidatos += glob.glob(os.path.join(home, "Library", "CloudStorage", "GoogleDrive-*", ".shortcut-targets-by-id", "*", nombre))
    for letra in "GHIJKLMNOPQRSTUVWXYZ":
        candidatos += glob.glob("%s:\\.shortcut-targets-by-id\\*\\%s" % (letra, nombre))
    candidatos += glob.glob(os.path.join(home, "Google Drive", ".shortcut-targets-by-id", "*", nombre))
    for c in candidatos:
        if os.path.isdir(c):
            return c
    return None
