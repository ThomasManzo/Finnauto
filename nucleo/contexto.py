# -*- coding: utf-8 -*-
"""
nucleo.contexto — junta en un solo objeto TODO lo resuelto para una corrida
(rutas de runtime + settings del cliente/banco), así el loop no anda pidiendo
diez parámetros sueltos.

Archivos de runtime (perfil del navegador, capturas, estado, log, descargas
temporales) viven por cliente+banco en:
    clientes/<cliente>/.run/<banco>/
Esa carpeta .run/ está en .gitignore (son datos de la máquina, no código).
"""

import os
from dataclasses import dataclass, field


@dataclass
class Contexto:
    base_repo: str
    cliente: str            # carpeta del cliente (ej "maga")
    cliente_nombre: str     # nombre lindo (ej "MAGA+")
    banco: str              # "galicia" | "comafi" | "santander"
    banco_nombre: str       # "Galicia" | "Comafi" | "Santander" (para nombres de archivo)

    carpeta_drive: str
    perfil_dir: str
    descargas_dir: str
    capturas_dir: str
    estado_path: str
    log_path: str

    timeout_ms: int = 45000
    modo_visible: bool = False
    incluir_hoy: bool = True
    backfill: int = 0

    excluir: list = field(default_factory=list)
    solo: list = field(default_factory=list)
    solo_activa: bool = False
    nombre_archivo: str = "cuit"      # 'cuit' = deja el nombre original; 'empresa' = renombra
    prefijo_archivo: str = ""

    def crear_carpetas(self):
        for c in (self.capturas_dir, self.perfil_dir, self.descargas_dir):
            os.makedirs(c, exist_ok=True)
        os.makedirs(os.path.dirname(self.estado_path), exist_ok=True)


def construir(base_repo, cliente, banco, perfil, cfg_banco, modo_forzado=None):
    """Arma el Contexto a partir del perfil del cliente y la config del banco.

    modo_forzado: None | 'prueba' | 'produccion' (viene de --modo o BOT_MODO).
    """
    run_dir = os.path.join(base_repo, "clientes", cliente, ".run", banco)

    modo_visible = bool(cfg_banco.get("modo_visible", False))
    mf = (modo_forzado or os.environ.get("BOT_MODO", "")).strip().lower()
    if mf == "prueba":
        modo_visible = True
    elif mf == "produccion":
        modo_visible = False

    return Contexto(
        base_repo=base_repo,
        cliente=cliente,
        cliente_nombre=perfil.get("cliente", cliente),
        banco=banco,
        banco_nombre=banco.capitalize(),
        carpeta_drive=perfil.get("carpeta_drive_destino", "").strip(),
        perfil_dir=os.path.join(run_dir, "perfil_navegador"),
        descargas_dir=os.path.join(run_dir, "descargas_temp"),
        capturas_dir=os.path.join(run_dir, "capturas"),
        estado_path=os.path.join(run_dir, "estado_descargas.json"),
        log_path=os.path.join(run_dir, "log.txt"),
        timeout_ms=int(cfg_banco.get("timeout_segundos", 45)) * 1000,
        modo_visible=modo_visible,
        incluir_hoy=bool(cfg_banco.get("incluir_hoy", True)),
        backfill=int(cfg_banco.get("backfill_dias_primera_vez", 0)),
        excluir=cfg_banco.get("empresas_excluir", []) or [],
        solo=cfg_banco.get("solo_estas_empresas", []) or [],
        solo_activa=bool(cfg_banco.get("solo_empresa_activa", False)),
        nombre_archivo=cfg_banco.get("nombre_archivo", "cuit"),
        prefijo_archivo=cfg_banco.get("prefijo_archivo", "") or "",
    )
