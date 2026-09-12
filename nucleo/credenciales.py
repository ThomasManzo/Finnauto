# -*- coding: utf-8 -*-
"""
nucleo.credenciales — guarda/lee las credenciales del banco en el llavero del
sistema operativo. Nunca en texto plano, nunca en un archivo del repo.

Multiplataforma vía `keyring`, que por debajo habla con el almacén nativo:
  · macOS    -> Llavero (Keychain)
  · Windows  -> Administrador de credenciales
  · Linux    -> Secret Service (GNOME Keyring / KWallet)

Igual que el esquema anterior con DPAPI, las entradas quedan atadas al USUARIO
+ la MÁQUINA: no viajan a otra computadora. Al mudarse de equipo hay que volver
a correr setup_credenciales.py allá.

Una entrada por cliente/banco, bajo el servicio "finauto:<cliente>:<banco>".
El bot nunca expone la clave en logs.
"""

import sys
import json

from nucleo.log import log

# Cuenta fija dentro de cada entrada del llavero. Usuario y clave van juntos
# como JSON en un solo secreto: así funciona igual en todos los backends de
# keyring, sin depender de get_credential() que no todos implementan.
_CUENTA = "credenciales"


def _servicio(cliente, banco):
    return "finauto:%s:%s" % (cliente, banco)


def ubicacion(cliente, banco):
    """Texto legible de donde quedan guardadas, para mensajes al usuario."""
    return "llavero del sistema, entrada '%s'" % _servicio(cliente, banco)


def _keyring():
    try:
        import keyring
        return keyring
    except ImportError:
        log("ERROR: falta la dependencia 'keyring'. Instalala con: pip install keyring")
        sys.exit(1)


def guardar(base_repo, cliente, banco, usuario, clave):
    """Guarda usuario+clave en el llavero del sistema y devuelve donde quedaron.

    base_repo se mantiene en la firma por compatibilidad con las llamadas
    existentes; con el llavero ya no se escribe nada dentro del repo.
    """
    kr = _keyring()
    datos = json.dumps({"usuario": usuario, "clave": clave})
    try:
        kr.set_password(_servicio(cliente, banco), _CUENTA, datos)
    except Exception as e:
        log("ERROR guardando en el llavero del sistema: %s" % e)
        sys.exit(1)
    return ubicacion(cliente, banco)


def cargar(base_repo, cliente, banco):
    """Lee del llavero y devuelve (usuario, clave).

    Corta el programa con un mensaje claro si no hay nada guardado en esta
    maquina para ese cliente/banco.
    """
    kr = _keyring()
    servicio = _servicio(cliente, banco)
    try:
        datos = kr.get_password(servicio, _CUENTA)
    except Exception as e:
        log("ERROR leyendo el llavero del sistema: %s" % e)
        sys.exit(1)

    if not datos:
        log("ERROR: no hay credenciales guardadas para cliente=%s banco=%s en esta maquina."
            % (cliente, banco))
        log("Corre primero: python setup_credenciales.py --cliente %s --banco %s"
            % (cliente, banco))
        sys.exit(1)

    try:
        d = json.loads(datos)
        return d["usuario"], d["clave"]
    except Exception as e:
        log("ERROR: la entrada '%s' del llavero esta corrupta (%s)." % (servicio, e))
        log("Regenerala con: python setup_credenciales.py --cliente %s --banco %s"
            % (cliente, banco))
        sys.exit(1)


def borrar(cliente, banco):
    """Elimina la entrada del llavero. True si habia algo para borrar."""
    kr = _keyring()
    try:
        kr.delete_password(_servicio(cliente, banco), _CUENTA)
        return True
    except Exception:
        return False
