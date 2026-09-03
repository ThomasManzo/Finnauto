# -*- coding: utf-8 -*-
"""
setup_credenciales.py — carga las credenciales de un banco para un cliente,
encriptadas con DPAPI (atadas a este usuario + esta PC). Correr una vez por
banco/cliente en la PC donde va a correr el bot.

Uso:
    python setup_credenciales.py --cliente maga --banco galicia

Pide usuario y clave por consola (la clave no se ve al tipear) y las deja en
clientes/<cliente>/.credenciales/<banco>.dat (fuera de git, nunca en texto plano).
"""

import os
import sys
import getpass
import argparse

BASE_REPO = os.path.dirname(os.path.abspath(__file__))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)

from nucleo import credenciales as _cred


def main():
    ap = argparse.ArgumentParser(description="Cargar credenciales encriptadas (DPAPI)")
    ap.add_argument("--cliente", required=True, help="carpeta del cliente (ej: maga)")
    ap.add_argument("--banco", required=True, help="banco (galicia/comafi/santander)")
    args = ap.parse_args()

    print("Cargando credenciales de %s para el cliente %s." % (args.banco, args.cliente))
    print("(Se guardan encriptadas con DPAPI en esta PC; nunca en texto plano.)\n")

    usuario = input("Usuario del banco: ").strip()
    clave = getpass.getpass("Clave del banco (no se ve al tipear): ").strip()
    if not usuario or not clave:
        print("Usuario o clave vacios. Cancelado.")
        sys.exit(1)

    ruta = _cred.guardar(BASE_REPO, args.cliente, args.banco, usuario, clave)
    print("\nListo. Credenciales guardadas en:\n  %s" % ruta)
    print("Recorda: este archivo NO sirve en otra PC/usuario -> regeneralo alla.")


if __name__ == "__main__":
    main()
