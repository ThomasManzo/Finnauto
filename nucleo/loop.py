# -*- coding: utf-8 -*-
"""
nucleo.loop — el RECORRIDO genérico, igual para todos los bancos.

Es el corazón que antes estaba copiado en el main() de cada bot. Ahora vive una
sola vez acá y le pide al "bot" (el adaptador del banco) los pasos concretos
(login, cambiar de empresa, ir a la cuenta, saldos, fechas, descarga). El loop
pone: la regla de fechas, el estado anti-duplicado, el manejo de errores por
empresa (si una falla, la anota y sigue) y las salidas a Drive.

Se portó 1:1 de main() de bot_galicia.py; solo se cambiaron las llamadas a
funciones sueltas por métodos del bot y los parámetros por el Contexto.
"""

import os
import sys
import datetime

from nucleo import log as _log
from nucleo.log import log, captura
from nucleo import estado as _estado
from nucleo import fechas as _fechas
from nucleo.navegador import abrir_navegador
from nucleo.salidas import escribir_estado_drive, escribir_saldos_drive
from nucleo.utilidades import _pasa_filtros, fmt


def correr(bot, ctx, usuario, clave):
    """Corre la descarga completa de un banco para un cliente.

    bot: instancia de bots.base.BotBanco (adaptador del banco).
    ctx: nucleo.contexto.Contexto ya construido.
    usuario, clave: credenciales ya desencriptadas.
    """
    ctx.crear_carpetas()
    _log.configurar(ctx.log_path, ctx.capturas_dir)

    estado = _estado.cargar(ctx.estado_path)
    timeout = ctx.timeout_ms

    hoy = datetime.date.today()

    if not ctx.carpeta_drive or not os.path.isdir(ctx.carpeta_drive):
        log("ERROR: la carpeta de Drive no existe: '%s'" % ctx.carpeta_drive)
        log("Revisá 'carpeta_drive_destino' en el perfil y que Google Drive Escritorio esté instalado.")
        # igual seguimos si es una prueba (para poder mirar capturas)
        if not ctx.modo_visible:
            sys.exit(1)

    resultado = {"ok": [], "fallaron": [], "sin_novedades": []}
    saldos_lista = []

    with abrir_navegador(ctx.perfil_dir, ctx.descargas_dir, headless=not ctx.modo_visible) as page:
        # 1) LOGIN
        try:
            bot.hacer_login(page, usuario, clave, timeout)
        except Exception as e:
            log("ERROR en el login: %s" % e)
            captura(page, "ERROR_login")
            escribir_estado_drive(ctx.carpeta_drive, ctx.banco_nombre, hoy,
                                  {"ok": [], "fallaron": ["LOGIN FALLIDO - " + str(e)], "sin_novedades": []})
            sys.exit(1)

        # 2) Empresa activa al entrar (no aparece en el selector; se procesa directo)
        activa = bot.capturar_empresa_activa(page)
        log("Empresa activa al entrar: %s" % (activa or "(no la pude leer)"))
        empresa_actual = activa

        if ctx.solo_activa:
            empresas = [activa or "EMPRESA_ACTIVA"]
            log("Modo prueba 'solo_empresa_activa': bajo únicamente '%s'." % empresas[0])
        else:
            try:
                otras = bot.descubrir_empresas(page, timeout, ctx.excluir, ctx.solo)
            except Exception as e:
                log("ERROR descubriendo empresas: %s" % e)
                captura(page, "ERROR_empresas")
                otras = []
            empresas = []
            if activa and _pasa_filtros(activa, ctx.excluir, ctx.solo):
                empresas.append(activa)
            elif not activa:
                empresas.append("EMPRESA_ACTIVA")  # la procesamos igual, sin nombre
            for o in otras:
                if activa and o.lower() == activa.lower():
                    continue
                empresas.append(o)

        if not empresas:
            log("No hay empresas para procesar (revisá filtros).")

        # 3) Por cada empresa: fechas -> (cambio) -> cuenta -> saldos -> filtro -> descarga
        for nombre in empresas:
            try:
                rango = _fechas.rango_a_bajar(estado.get(nombre), hoy, ctx.incluir_hoy, ctx.backfill)
                if rango is None:
                    log("%s: sin días nuevos (ya al día). Salto." % nombre)
                    resultado["sin_novedades"].append(nombre)
                    continue
                desde, hasta = rango

                log("== %s == bajando %s a %s" % (nombre, fmt(desde), fmt(hasta)))
                necesita_cambio = (
                    not ctx.solo_activa
                    and nombre != "EMPRESA_ACTIVA"
                    and (empresa_actual is None or nombre.lower() != empresa_actual.lower())
                )
                if necesita_cambio:
                    bot.cambiar_a_empresa(page, nombre, timeout)
                    empresa_actual = nombre

                bot.ir_a_cuenta(page, timeout)

                # Saldos (Actual/Disponible) ANTES de filtrar. No aborta si falla.
                saldos = bot.capturar_saldos(page)
                log("   Saldo Actual: %s | Disponible: %s" % (
                    saldos.get("actual_texto") or "?", saldos.get("disponible_texto") or "?"))

                bot.aplicar_filtro_fechas(page, desde, hasta, timeout)
                archivo_csv = bot.descargar_csv(page, ctx.carpeta_drive, nombre, timeout, ctx)

                saldos_lista.append({
                    "empresa": nombre,
                    "cuenta": bot.extraer_cuenta_id(archivo_csv),
                    "archivo_extracto": os.path.basename(archivo_csv) if archivo_csv else None,
                    "saldo_actual": saldos.get("actual"),
                    "saldo_actual_texto": saldos.get("actual_texto"),
                    "saldo_disponible": saldos.get("disponible"),
                    "saldo_disponible_texto": saldos.get("disponible_texto"),
                    "leido": datetime.datetime.now().isoformat(timespec="seconds"),
                })

                estado[nombre] = hasta.isoformat()
                _estado.guardar(ctx.estado_path, estado)
                resultado["ok"].append(nombre)

            except Exception as e:
                log("FALLO %s: %s" % (nombre, e))
                captura(page, "ERROR_%s" % nombre[:30])
                resultado["fallaron"].append("%s (%s)" % (nombre, str(e)[:120]))
                # seguimos con la próxima; el día queda pendiente y se reintenta mañana.
                continue

    # 4) Salidas a Drive
    escribir_estado_drive(ctx.carpeta_drive, ctx.banco_nombre, hoy, resultado)
    escribir_saldos_drive(ctx.carpeta_drive, ctx.banco_nombre, hoy, saldos_lista)
    log("TERMINADO. OK: %d | Fallaron: %d | Sin novedades: %d" % (
        len(resultado["ok"]), len(resultado["fallaron"]), len(resultado["sin_novedades"])))
    return resultado
