# -*- coding: utf-8 -*-
"""
bots.base — el CONTRATO que cumple cada banco.

Un banco nuevo = una clase que hereda de BotBanco e implementa estos pasos con
los selectores de ESE banco. Todo lo demás (recorrido, fechas, estado, Drive)
lo pone el núcleo. Así, sumar Santander (o el banco que sea) es escribir solo
este puñado de métodos, no reescribir el motor.

Cada método recibe 'page' (la pestaña de Playwright) y actúa sobre la web como
lo haría una persona: buscar un botón, clickearlo, leer un texto, etc.
"""

from abc import ABC, abstractmethod


class BotBanco(ABC):
    # Nombre lindo del banco (para nombres de archivo _ESTADO_/_SALDOS_).
    nombre = "Banco"
    # URL de entrada del home banking.
    url = ""

    # ---- Pasos de la web (los implementa cada banco) ----

    @abstractmethod
    def hacer_login(self, page, usuario, clave, timeout):
        """Entra al home banking con usuario + clave y deja la sesión abierta."""

    @abstractmethod
    def capturar_empresa_activa(self, page):
        """Devuelve el nombre de la empresa que quedó abierta al entrar, o None."""

    @abstractmethod
    def descubrir_empresas(self, page, timeout, excluir, solo):
        """Devuelve la lista de nombres de empresa disponibles (ya filtrada)."""

    @abstractmethod
    def cambiar_a_empresa(self, page, nombre, timeout):
        """Selecciona la empresa 'nombre' desde el selector del banco."""

    @abstractmethod
    def ir_a_cuenta(self, page, timeout):
        """Navega hasta la pantalla de movimientos/extracto de la cuenta abierta."""

    @abstractmethod
    def capturar_saldos(self, page):
        """Devuelve dict con saldo Actual/Disponible:
        {actual_texto, actual, disponible_texto, disponible} (valores o None)."""

    @abstractmethod
    def aplicar_filtro_fechas(self, page, desde, hasta, timeout):
        """Filtra el rango [desde, hasta] en la pantalla de movimientos.
        Devuelve True/False (si pudo verificar que el rango quedó cargado)."""

    @abstractmethod
    def descargar_csv(self, page, carpeta_destino, nombre_empresa, timeout, ctx):
        """Descarga el extracto en .CSV y lo guarda en carpeta_destino.
        Devuelve la ruta del archivo guardado.

        OJO al NOMBRE del archivo (lo espera el clasificador):
          - Galicia: deja el nombre ORIGINAL del CSV (trae el CUIT).
          - Comafi:  renombra con el NOMBRE de la empresa/farmacia.
        Por eso este paso es de cada banco (usa ctx.nombre_archivo / prefijo)."""

    # ---- opcional (default sirve para la mayoría) ----

    def extraer_cuenta_id(self, archivo_csv):
        """ID de cuenta para el registro de saldos. Default: None.
        Galicia lo saca del nombre del CSV (CC<numero>); otros pueden dejarlo en None."""
        return None
