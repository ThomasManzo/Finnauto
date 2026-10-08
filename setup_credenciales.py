# -*- coding: utf-8 -*-
"""
setup_credenciales.py — carga las credenciales de un banco para un cliente en
el llavero del sistema (Llavero de macOS / Administrador de credenciales de
Windows / Secret Service en Linux). Correr una vez por banco/cliente en la
maquina donde va a correr el bot.

Uso:
    python setup_credenciales.py --cliente maga --banco galicia

Pide usuario y clave por consola (la clave no se ve al tipear) y las deja en el
llavero del sistema, atadas a este usuario y esta maquina. Nunca en texto plano
ni en un archivo del repo.
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
    ap = argparse.ArgumentParser(
        description="Cargar credenciales de banco en el llavero del sistema")
    ap.add_argument("--cliente", required=True, help="carpeta del cliente (ej: maga)")
    ap.add_argument("--banco", required=True, help="banco (galicia/bbva/nacion/comafi/santander)")
    args = ap.parse_args()

    print("Cargando credenciales de %s para el cliente %s." % (args.banco, args.cliente))
    print("(Se guardan en el llavero del sistema de esta maquina; nunca en texto plano.)\n")

    # Algunos bancos piden un tercer dato para entrar: BBVA el código de empresa y Nación el DNI.
    # Se guarda junto con usuario y clave, en el llavero.
    extra = {}
    pedido = {"bbva": ("codigo_empresa", "Codigo de empresa"), "nacion": ("dni", "DNI")}.get(args.banco.lower())
    if pedido:
        campo, texto = pedido
        extra[campo] = input("%s: " % texto).strip()
        if not extra[campo]:
            print("%s vacio. Cancelado." % texto)
            sys.exit(1)

    usuario = input("Usuario del banco: ").strip()
    clave = getpass.getpass("Clave del banco (no se ve al tipear): ").strip()
    if not usuario or not clave:
        print("Usuario o clave vacios. Cancelado.")
        sys.exit(1)

    destino = _cred.guardar(BASE_REPO, args.cliente, args.banco, usuario, clave, extra)
    print("\nListo. Credenciales guardadas en:\n  %s" % destino)
    print("Recorda: esta entrada NO viaja a otra maquina/usuario -> regenerala alla.")


if __name__ == "__main__":
    main()
