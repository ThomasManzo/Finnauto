# -*- coding: utf-8 -*-
"""
bots.santander — adaptador de Santander (Office Banking / Supernet Empresas).

>>> ESTADO: NO EMPEZADO. Es un esqueleto para mostrar lo poco que hay que
    escribir para sumar un banco: solo estos métodos con los selectores de
    Santander. El motor (recorrido, fechas, estado, Drive) ya está en el núcleo
    y no se toca.

Cómo completarlo (mismo camino que Galicia/Comafi):
  1. Poner la URL real de entrada en URL_SANTANDER.
  2. Correr en modo prueba (navegador visible), mirar las capturas, y afinar los
     selectores de cada paso.
  3. Definir si el archivo se identifica por CUIT (dejar nombre original) o por
     nombre de empresa (renombrar), y ajustar descargar_csv + el perfil.

Sugerencia: como base, copiar la estructura de bots/galicia/bot.py (si Santander
usa react-datepicker) o de bots/comafi/bot.py (si usa inputs de fecha de texto).
"""

from bots.base import BotBanco

URL_SANTANDER = ""  # >>> TODO SANTANDER: poner la URL real de entrada.


def _pendiente(paso):
    raise NotImplementedError(
        "Santander: el paso '%s' todavía no está implementado. "
        "Ver bots/santander/bot.py y usar Galicia/Comafi como molde." % paso)


class BotSantander(BotBanco):
    nombre = "Santander"
    url = URL_SANTANDER

    def __init__(self):
        self._nombre_usuario = None

    def hacer_login(self, page, usuario, clave, timeout):
        _pendiente("hacer_login")

    def capturar_empresa_activa(self, page):
        _pendiente("capturar_empresa_activa")

    def descubrir_empresas(self, page, timeout, excluir, solo):
        _pendiente("descubrir_empresas")

    def cambiar_a_empresa(self, page, nombre, timeout):
        _pendiente("cambiar_a_empresa")

    def ir_a_cuenta(self, page, timeout):
        _pendiente("ir_a_cuenta")

    def capturar_saldos(self, page):
        _pendiente("capturar_saldos")

    def aplicar_filtro_fechas(self, page, desde, hasta, timeout):
        _pendiente("aplicar_filtro_fechas")

    def descargar_csv(self, page, carpeta_destino, nombre_empresa, timeout, ctx):
        _pendiente("descargar_csv")
