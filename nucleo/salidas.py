# -*- coding: utf-8 -*-
"""
nucleo.salidas — deja en la carpeta de Drive los archivos que lee el clasificador:
  - _ESTADO_<Banco>_DD-MM.txt   (parte del día: qué salió OK / qué falló)
  - _SALDOS_<Banco>_DD-MM.json  (saldos por empresa, para la grilla SALDOS)

Sale 1:1 de los bots; lo único que cambia es el nombre del banco (parametrizado).
"""

import os
import json
import datetime

from nucleo.log import log


def escribir_saldos_drive(carpeta_drive, banco, hoy, saldos_lista):
    """Deja _SALDOS_<Banco>_DD-MM.json en Drive para que el clasificador (Apps
    Script) llene la columna del banco en la grilla SALDOS."""
    if not saldos_lista:
        return
    try:
        payload = {
            "banco": banco,
            "fecha": hoy.isoformat(),
            "generado": datetime.datetime.now().isoformat(timespec="seconds"),
            "empresas": saldos_lista,
        }
        nombre = "_SALDOS_%s_%s.json" % (banco, hoy.strftime("%d-%m"))
        destino = os.path.join(carpeta_drive, nombre)
        with open(destino, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        log("Saldos escritos en Drive: %s (%d empresas)" % (nombre, len(saldos_lista)))
    except Exception as e:
        log("Aviso: no pude escribir el archivo de saldos: %s" % e)


def escribir_estado_drive(carpeta_drive, banco, hoy, resultado):
    """Deja _ESTADO_<Banco>_DD-MM.txt en Drive (lo ven Thomas y Delfi): dice qué
    empresas se bajaron OK y cuáles fallaron (para bajarlas a mano ese día)."""
    try:
        nombre = "_ESTADO_%s_%s.txt" % (banco, hoy.strftime("%d-%m"))
        lineas = []
        lineas.append("Bot %s - %s" % (banco, datetime.datetime.now().strftime("%d/%m/%Y %H:%M")))
        lineas.append("")
        if resultado["fallaron"]:
            lineas.append(">>> ATENCION: %d empresa(s) fallaron. Bajar a mano hoy:" % len(resultado["fallaron"]))
            for f in resultado["fallaron"]:
                lineas.append("   - %s" % f)
        else:
            lineas.append("OK: no fallo ninguna empresa.")
        lineas.append("")
        lineas.append("Bajadas OK (%d): %s" % (len(resultado["ok"]), ", ".join(resultado["ok"]) or "-"))
        lineas.append("Sin novedades (%d): %s" % (len(resultado["sin_novedades"]), ", ".join(resultado["sin_novedades"]) or "-"))
        destino = os.path.join(carpeta_drive, nombre)
        with open(destino, "w", encoding="utf-8") as f:
            f.write("\n".join(lineas))
        log("Estado escrito en Drive: %s" % nombre)
    except Exception as e:
        log("No pude escribir el archivo de estado en Drive: %s" % e)
