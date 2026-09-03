# -*- coding: utf-8 -*-
"""
orquestador.correr — punto de entrada: corre la descarga de un banco para un cliente.

Uso:
    python orquestador/correr.py --cliente maga --banco galicia
    python orquestador/correr.py --cliente maga --banco galicia --modo prueba
    python orquestador/correr.py --cliente maga --todos            (todos los bancos activos)

'--modo prueba'      -> navegador visible (para depurar).
'--modo produccion'  -> navegador invisible (para la tarea de las 8:00).
(si no se pasa --modo, manda el modo_visible del perfil / la env BOT_MODO.)
"""

import os
import sys
import argparse
import traceback

# Hacer importable el repo (nucleo, bots) tanto con 'python -m' como script suelto.
BASE_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)

from nucleo import config as _config
from nucleo import contexto as _contexto
from nucleo import credenciales as _cred
from nucleo import loop as _loop
from nucleo.log import log

# Registro de bancos: nombre en el perfil -> clase del adaptador.
from bots.galicia import BotGalicia
from bots.comafi import BotComafi
from bots.santander import BotSantander

REGISTRO_BANCOS = {
    "galicia": BotGalicia,
    "comafi": BotComafi,
    "santander": BotSantander,
}


def correr_banco(cliente, banco, modo_forzado=None):
    banco = banco.lower()
    if banco not in REGISTRO_BANCOS:
        raise SystemExit("Banco desconocido: '%s'. Disponibles: %s"
                         % (banco, ", ".join(REGISTRO_BANCOS)))

    perfil = _config.cargar_perfil(BASE_REPO, cliente)
    cfg_banco = _config.config_banco(perfil, banco)
    ctx = _contexto.construir(BASE_REPO, cliente, banco, perfil, cfg_banco, modo_forzado)

    bot = REGISTRO_BANCOS[banco]()
    ctx.banco_nombre = bot.nombre  # nombre lindo para _ESTADO_/_SALDOS_

    usuario, clave = _cred.cargar(BASE_REPO, cliente, banco)

    log("=== finauto :: cliente=%s banco=%s modo=%s ===" % (
        ctx.cliente_nombre, bot.nombre, "visible" if ctx.modo_visible else "invisible"))
    return _loop.correr(bot, ctx, usuario, clave)


def main():
    ap = argparse.ArgumentParser(description="finauto - descarga de extractos bancarios")
    ap.add_argument("--cliente", required=True, help="carpeta del cliente (ej: maga)")
    ap.add_argument("--banco", help="banco a correr (galicia/comafi/santander)")
    ap.add_argument("--todos", action="store_true", help="correr todos los bancos activos del perfil")
    ap.add_argument("--modo", choices=["prueba", "produccion"], help="visible / invisible")
    args = ap.parse_args()

    if args.todos:
        perfil = _config.cargar_perfil(BASE_REPO, args.cliente)
        activos = [b for b, c in (perfil.get("bancos", {})).items() if (c or {}).get("activo", True)]
        if not activos:
            raise SystemExit("El perfil no tiene bancos activos.")
        for b in activos:
            try:
                correr_banco(args.cliente, b, args.modo)
            except SystemExit:
                raise
            except Exception:
                log("ERROR corriendo %s:\n%s" % (b, traceback.format_exc()))
        return

    if not args.banco:
        raise SystemExit("Falta --banco (o usá --todos).")
    correr_banco(args.cliente, args.banco, args.modo)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        log("ERROR INESPERADO:\n" + traceback.format_exc())
        sys.exit(1)
