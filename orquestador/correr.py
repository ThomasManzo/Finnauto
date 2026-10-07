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
import datetime
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

# Bancos con un recorrido propio para NAVAR (se importan recién cuando se usan).
# BBVA solo existe en su variante NAVAR, por eso no está en el registro general.
VARIANTES_NAVAR = ("galicia", "bbva")


# ---- reintentos (tarea 51) -------------------------------------------------------------
# Con --si-falta la corrida es un REINTENTO: si hoy ya bajó bien no hace nada, y si el banco ya
# recibió la clave y no confirmó la entrada MAX_CLAVES_SIN_CONFIRMAR veces hoy, no insiste (puede
# ser la clave, y seguir probando bloquearía el usuario). Las fallas antes de mandar la clave
# (página que no carga, sin internet) no cuentan: reintentar ahí no arriesga nada.
MAX_CLAVES_SIN_CONFIRMAR = 2
MARCA_CLAVE = "CLAVE ENVIADA SIN CONFIRMAR"      # la escribe el bot (bots/galicia/navar.py)
MARCA_FRENO = "NO SE REINTENTA"


def _estado_hoy(carpeta_drive, banco_nombre, hoy):
    """Texto del _ESTADO_ de hoy de ese banco ("" si todavía no hay)."""
    ruta = os.path.join(carpeta_drive or "", "_ESTADO_%s_%s.txt" % (banco_nombre, hoy.strftime("%d-%m")))
    try:
        with open(ruta, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def _ruta_contador(base_repo, cliente, banco, hoy):
    return os.path.join(base_repo, "clientes", cliente, ".run", banco,
                        "clave_sin_confirmar_%s.txt" % hoy.isoformat())


def _leer_contador(ruta):
    try:
        with open(ruta, encoding="utf-8") as f:
            return int(f.read().strip() or 0)
    except (OSError, ValueError):
        return 0


def _sumar_contador(ruta):
    n = _leer_contador(ruta) + 1
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(str(n))
    return n


def decidir_reintento(estado_txt, claves_sin_confirmar):
    """¿Corre este reintento? Devuelve (correr, motivo, freno). freno = se paró por la clave."""
    if "OK: no fallo ninguna empresa" in estado_txt:
        return False, "ya bajó bien hoy; no hace falta reintentar", False
    if claves_sin_confirmar >= MAX_CLAVES_SIN_CONFIRMAR:
        return False, ("el banco recibió la clave y no confirmó la entrada %d veces hoy; "
                       "no se reintenta para no bloquear el usuario" % claves_sin_confirmar), True
    return True, "", False


def correr_banco(cliente, banco, modo_forzado=None, navegador=None, si_falta=False):
    banco = banco.lower()
    variante_navar = cliente == "navar" and banco in VARIANTES_NAVAR
    if banco not in REGISTRO_BANCOS and not variante_navar:
        raise SystemExit("Banco desconocido: '%s'. Disponibles: %s"
                         % (banco, ", ".join(REGISTRO_BANCOS)))

    perfil = _config.cargar_perfil(BASE_REPO, cliente)
    cfg_banco = _config.config_banco(perfil, banco)
    ctx = _contexto.construir(BASE_REPO, cliente, banco, perfil, cfg_banco, modo_forzado)
    if navegador:
        ctx.navegador = "" if navegador == "chromium" else navegador
    if ctx.navegador:
        # Cada navegador guarda su propio perfil (cookies, "dispositivo reconocido"):
        # el de Chromium no le sirve a Edge y mezclarlos puede romper los dos.
        ctx.perfil_dir = ctx.perfil_dir + "_" + ctx.navegador

    if variante_navar:
        if banco == "galicia":
            from bots.galicia.navar import BotGaliciaNavar
            bot = BotGaliciaNavar(cfg_banco)
        else:
            from bots.bbva.navar import BotBbvaNavar
            bot = BotBbvaNavar(cfg_banco)
    else:
        bot = REGISTRO_BANCOS[banco]()
    ctx.banco_nombre = bot.nombre  # nombre lindo para _ESTADO_/_SALDOS_

    if variante_navar:
        fijada = cfg_banco.get("carpeta_drive_destino", "").strip()
        relativa = cfg_banco.get("carpeta_drive_relativa", "Bancos/" + banco).strip()
        if fijada:
            ctx.carpeta_drive = os.path.normpath(fijada)
            buscada = "carpeta_drive_destino=%s" % fijada
        else:
            from ingestas.drive_local import carpeta_datos
            raiz = carpeta_datos()
            relativa_sistema = relativa.replace("/", os.sep).replace("\\", os.sep)
            ctx.carpeta_drive = os.path.normpath(os.path.join(raiz, relativa_sistema)) if raiz else ""
            buscada = "NAVAR - Datos + %s (detección automática de Drive)" % relativa
        # También en prueba: no abrir el banco si no sabemos dónde publicar.
        if not os.path.isabs(ctx.carpeta_drive) or not os.path.isdir(ctx.carpeta_drive):
            raise SystemExit("No encontré la carpeta de %s antes de abrir el banco. Busqué: %s. "
                             "Revisar que Drive esté montado o fijar carpeta_drive_destino."
                             % (bot.nombre, buscada))

    hoy = datetime.date.today()
    contador = _ruta_contador(BASE_REPO, cliente, banco, hoy)
    if si_falta:
        correr, motivo, freno = decidir_reintento(_estado_hoy(ctx.carpeta_drive, ctx.banco_nombre, hoy),
                                                  _leer_contador(contador))
        if not correr:
            log("%s: %s." % (bot.nombre, motivo))
            if freno:
                _anotar_freno(ctx, hoy, motivo)
            return None

    usuario, clave = _cred.cargar(BASE_REPO, cliente, banco)
    if variante_navar and banco == "bbva":
        # BBVA pide un tercer dato para entrar; vive en el llavero junto con usuario y clave.
        bot.codigo_empresa = _cred.dato_extra(cliente, banco, "codigo_empresa")

    log("=== finauto :: cliente=%s banco=%s modo=%s ===" % (
        ctx.cliente_nombre, bot.nombre, "visible" if ctx.modo_visible else "invisible"))
    try:
        resultado = _loop.correr(bot, ctx, usuario, clave)
    except SystemExit:
        # El loop corta con SystemExit cuando falla el login y deja el motivo en el estado del día.
        if MARCA_CLAVE in _estado_hoy(ctx.carpeta_drive, ctx.banco_nombre, hoy):
            n = _sumar_contador(contador)
            log("%s: el banco recibió la clave y no confirmó la entrada (%d de %d hoy)."
                % (bot.nombre, n, MAX_CLAVES_SIN_CONFIRMAR))
        raise
    if variante_navar:
        if resultado["fallaron"] or not (resultado["ok"] or resultado["sin_novedades"]):
            raise RuntimeError("%s NAVAR no terminó bien; revisar log y capturas." % bot.nombre)
    return resultado




def _anotar_freno(ctx, hoy, motivo):
    """Deja en el estado de hoy, una sola vez, que no se reintenta y qué hacer (lo lee el mail)."""
    if MARCA_FRENO in _estado_hoy(ctx.carpeta_drive, ctx.banco_nombre, hoy):
        return
    from nucleo.salidas import escribir_estado_drive
    escribir_estado_drive(ctx.carpeta_drive, ctx.banco_nombre, hoy, {
        "ok": [], "sin_novedades": [],
        "fallaron": ["%s - %s: revisar la clave antes de volver a probar" % (MARCA_FRENO, motivo)]})


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
    ap.add_argument("--banco", help="banco a correr (galicia/bbva/comafi/santander)")
    ap.add_argument("--todos", action="store_true", help="correr todos los bancos activos del perfil")
    ap.add_argument("--modo", choices=["prueba", "produccion"], help="visible / invisible")
    ap.add_argument("--si-falta", action="store_true",
                    help="reintento: no hace nada si hoy ya bajó bien o si el banco ya rechazó la clave")
    ap.add_argument("--navegador", choices=["chromium", "msedge", "chrome"],
                    help="con qué navegador entrar (por defecto, el del perfil o Chromium)")
    args = ap.parse_args()

    if not args.cliente:
        return _todos_los_clientes(args)

    if args.todos:
        _bancos_de(args.cliente, args.modo)
        return

    if not args.banco:
        raise SystemExit("Falta --banco (o usá --todos).")
    correr_banco(args.cliente, args.banco, args.modo, args.navegador, si_falta=args.si_falta)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        log("ERROR INESPERADO:\n" + traceback.format_exc())
        sys.exit(1)
