# -*- coding: utf-8 -*-
"""
nucleo.credenciales — guarda/lee las credenciales del banco encriptadas con DPAPI.

DPAPI (win32crypt) encripta atado al USUARIO + la MÁQUINA de Windows: el archivo
.dat NO sirve si se copia a otra PC u otro usuario -> hay que regenerarlo ahí.
Nunca se guarda la clave en texto plano y el bot no la expone en logs.

Multi-cliente/banco: cada uno tiene su archivo en
  clientes/<cliente>/.credenciales/<banco>.dat
(esa carpeta está en .gitignore; nunca sube al repo).
"""

import os
import sys
import json

from nucleo.log import log


def ruta_credenciales(base_repo, cliente, banco):
    return os.path.join(base_repo, "clientes", cliente, ".credenciales", "%s.dat" % banco)


def guardar(base_repo, cliente, banco, usuario, clave):
    """Encripta usuario+clave con DPAPI y los deja en el .dat del cliente/banco."""
    import win32crypt
    datos = json.dumps({"usuario": usuario, "clave": clave}).encode("utf-8")
    encriptado = win32crypt.CryptProtectData(datos, None, None, None, None, 0)
    ruta = ruta_credenciales(base_repo, cliente, banco)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "wb") as f:
        f.write(encriptado)
    return ruta


def cargar(base_repo, cliente, banco):
    """Lee y desencripta el .dat. Corta el programa con un mensaje claro si falta
    o si fue copiado de otra PC (DPAPI no lo puede abrir)."""
    ruta = ruta_credenciales(base_repo, cliente, banco)
    if not os.path.exists(ruta):
        log("ERROR: no existe %s. Corré primero: python setup_credenciales.py --cliente %s --banco %s"
            % (ruta, cliente, banco))
        sys.exit(1)
    try:
        import win32crypt
        with open(ruta, "rb") as f:
            encriptado = f.read()
        datos = win32crypt.CryptUnprotectData(encriptado, None, None, None, 0)[1]
        d = json.loads(datos.decode("utf-8"))
        return d["usuario"], d["clave"]
    except Exception as e:
        log("ERROR desencriptando credenciales: %s" % e)
        log("Puede que el archivo se haya copiado de otra PC/usuario. Regeneralo con setup_credenciales.py acá.")
        sys.exit(1)
