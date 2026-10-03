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


def guardar(base_repo, cliente, banco, usuario, clave, extra=None):
    """Guarda usuario+clave en el llavero del sistema y devuelve donde quedaron.

    base_repo se mantiene en la firma por compatibilidad con las llamadas
    existentes; con el llavero ya no se escribe nada dentro del repo.

    extra: datos de más que pide algún banco para entrar (BBVA pide además el
    "código de empresa"). Van en el mismo secreto que usuario y clave.
    """
    kr = _keyring()
    secreto = dict(extra or {})
    secreto.update({"usuario": usuario, "clave": clave})
    datos = json.dumps(secreto)
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


def dato_extra(cliente, banco, campo):
    """Lee un dato de más guardado junto con usuario y clave (ej: codigo_empresa).

    Si no está, corta con el mismo mensaje que cuando faltan las credenciales:
    hay que volver a correr setup_credenciales.py, que ahora lo pide.
    """
    kr = _keyring()
    servicio = _servicio(cliente, banco)
    try:
        datos = json.loads(kr.get_password(servicio, _CUENTA) or "{}")
    except Exception as e:
        log("ERROR leyendo '%s' del llavero del sistema: %s" % (campo, e))
        sys.exit(1)
    valor = str(datos.get(campo) or "").strip()
    if not valor:
        log("ERROR: falta '%s' en las credenciales de cliente=%s banco=%s." % (campo, cliente, banco))
        log("Corre de nuevo: python setup_credenciales.py --cliente %s --banco %s" % (cliente, banco))
        sys.exit(1)
    return valor


def borrar(cliente, banco):
    """Elimina la entrada del llavero. True si habia algo para borrar."""
    kr = _keyring()
    try:
        kr.delete_password(_servicio(cliente, banco), _CUENTA)
        return True
    except Exception:
        return False
