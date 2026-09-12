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




def _bancos_de(cliente, modo):
    """Todos los bancos activos de un cliente, uno por vez.

    Si uno falla los demas siguen: que venza la clave de Comafi no puede dejar
    sin extractos a Galicia. Al final se levanta el error para que el que llamo
    sepa que este cliente no quedo completo.
    """
    perfil = _config.cargar_perfil(BASE_REPO, cliente)
    # Las claves que empiezan con "_" son comentarios del perfil (misma
    # convencion que el catalogo: "_ayuda", "_nota"), no bancos.
    activos = [b for b, c in (perfil.get("bancos", {})).items()
               if not b.startswith("_") and isinstance(c, dict)
               and c.get("activo", True)]
    if not activos:
        raise SystemExit("El perfil de %s no tiene bancos activos." % cliente)
    fallaron = []
    for b in activos:
        try:
            correr_banco(cliente, b, modo)
        except SystemExit:
            raise
        except Exception:
            log("ERROR corriendo %s de %s:" % (b, cliente))
            log(traceback.format_exc())
            fallaron.append(b)
    if fallaron:
        raise RuntimeError("fallaron " + ", ".join(fallaron))


def _clientes_disponibles():
    base = os.path.join(BASE_REPO, "clientes")
    if not os.path.isdir(base):
        return []
    out = []
    for n in sorted(os.listdir(base)):
        if n.startswith("_") or n.startswith("."):
            continue
        if os.path.isfile(os.path.join(base, n, "perfil.json")):
            out.append(n)
    return out


def _todos_los_clientes(args):
    """Corre todos los bancos activos de todos los clientes, uno por vez.

    SI UNO FALLA, LOS DEMAS SIGUEN. Un cliente con la clave vencida no puede
    dejar sin extractos a los otros dos -- y al final se dice cual fallo, para
    que el problema no quede escondido en el medio de la salida.
    """
    clientes = _clientes_disponibles()
    if not clientes:
        raise SystemExit("No hay ningun cliente en clientes/ con perfil.json.")

    log("Clientes a correr: %s" % ", ".join(clientes))
    fallaron = []
    for c in clientes:
        log("")
        log("=" * 60)
        log("  CLIENTE: %s" % c)
        log("=" * 60)
        try:
            _bancos_de(c, args.modo)
        except SystemExit as e:
            # Un cliente sin bancos activos (recien sumado, o todavia en fase 1
            # sin credenciales) no es un error: se saltea y se sigue con los
            # demas. Sin esto, SystemExit no cae en el except de abajo y corta
            # la corrida de TODOS los clientes por uno que no tenia nada que
            # correr. Aparecio el dia que se sumo NAVAR con los 5 bancos en
            # activo=false.
            log("SALTEO el cliente %s: %s" % (c, e))
        except Exception as e:
            fallaron.append((c, str(e)))
            log("FALLO el cliente %s: %s" % (c, e))

    log("")
    if fallaron:
        log("TERMINO CON ERRORES. Fallaron: %s"
            % ", ".join("%s (%s)" % (c, e[:60]) for c, e in fallaron))
        return 1
    log("Todos los clientes corrieron bien.")
    return 0


def main():
    ap = argparse.ArgumentParser(description="finauto - descarga de extractos bancarios")
    # UN CLIENTE, O TODOS.
    #
    # Thomas (07/09/2026): "¿cómo pega eso con que se tenga que consultar el
    # bot 2 bancos distintos de dos empresas distintas?".
    #
    # Cada cliente ya tiene lo suyo separado -- su perfil, sus bancos, sus
    # credenciales cifradas y su carpeta de destino -- pero habia que
    # invocarlos de a uno. Con dos clientes eso son cuatro comandos a mano
    # todos los dias, que es exactamente como se olvida uno.
    #
    # Los bancos corren en SERIE y no en paralelo, a proposito: son sesiones de
    # home banking con login, y dos navegadores compitiendo por la misma
    # maquina hacen fallar los dos.
    ap.add_argument("--cliente", help="carpeta del cliente (ej: maga). "
                                      "Sin esto, corren TODOS los clientes")
    ap.add_argument("--banco", help="banco a correr (galicia/comafi/santander)")
    ap.add_argument("--todos", action="store_true", help="correr todos los bancos activos del perfil")
    ap.add_argument("--modo", choices=["prueba", "produccion"], help="visible / invisible")
    args = ap.parse_args()

    if not args.cliente:
        return _todos_los_clientes(args)

    if args.todos:
        _bancos_de(args.cliente, args.modo)
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
