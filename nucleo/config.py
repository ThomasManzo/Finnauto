# -*- coding: utf-8 -*-
"""
nucleo.config — lee el PERFIL del cliente (clientes/<cliente>/perfil.json).

Acá está la clave de que finauto sea multi-cliente: TODO lo específico de un
cliente (carpeta de Drive, qué bancos usa, filtros de empresas, cómo nombra los
archivos) sale del perfil, NO del código. Hoy hay un solo perfil (maga), pero
sumar otra farmacia es agregar otra carpeta en clientes/ con su perfil.json.
"""

import os
import json


def ruta_cliente(base_repo, cliente):
    return os.path.join(base_repo, "clientes", cliente)


def cargar_perfil(base_repo, cliente):
    """Lee clientes/<cliente>/perfil.json y lo devuelve como dict."""
    ruta = os.path.join(ruta_cliente(base_repo, cliente), "perfil.json")
    if not os.path.exists(ruta):
        raise FileNotFoundError(
            "No existe el perfil del cliente '%s'. Esperaba: %s" % (cliente, ruta))
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def config_banco(perfil, banco):
    """Devuelve la config del banco pedido, mezclada con los defaults del cliente.

    Los valores del bloque 'bancos.<banco>' pisan a los generales del cliente.
    Así el perfil pone lo común una vez y cada banco solo lo que cambia.
    """
    bancos = perfil.get("bancos", {})
    if banco not in bancos:
        raise KeyError(
            "El banco '%s' no está en el perfil (bancos disponibles: %s)."
            % (banco, ", ".join(bancos.keys()) or "ninguno"))
    b = dict(bancos[banco] or {})
    # Defaults que pueden venir del nivel cliente y ser pisados por el banco:
    defaults = {
        "timeout_segundos": perfil.get("timeout_segundos", 45),
        "modo_visible": perfil.get("modo_visible", False),
        "incluir_hoy": perfil.get("incluir_hoy", True),
        "backfill_dias_primera_vez": perfil.get("backfill_dias_primera_vez", 0),
        "empresas_excluir": [],
        "solo_estas_empresas": [],
        "solo_empresa_activa": False,
        "nombre_archivo": "cuit",   # 'cuit' = deja el nombre original del CSV; 'empresa' = renombra
        "prefijo_archivo": "",
        "activo": True,
    }
    for k, v in defaults.items():
        b.setdefault(k, v)
    return b
