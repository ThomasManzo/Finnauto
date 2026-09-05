# -*- coding: utf-8 -*-
"""
bots.generico.validar — revisa una ficha de banco SIN tocar el banco.

Sirve para lo que estamos haciendo ahora: dejar todo armado aunque no haya
acceso. Dice qué le falta a una ficha, qué está a medio completar y qué pasos
van a fallar cuando llegue el momento de correrla de verdad.

No puede saber si un selector es CORRECTO — eso solo lo dice el banco. Sí puede
saber si está PRESENTE, si quedó un '>>> COMPLETAR' y si el conjunto es
coherente (ej: `tiene: true` en empresas pero sin selector para abrir el
selector de empresas).

Uso:
    python bots/generico/validar.py --banco comafi
    python bots/generico/validar.py --todos
"""

import os
import sys
import glob
import argparse

BASE_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)

from bots.generico.bot import cargar_ficha, BotGenerico


# (camino, obligatorio, para que sirve)
CAMPOS = [
    (("login", "usuario"), True, "escribir el usuario"),
    (("login", "clave"), True, "escribir la clave"),
    (("login", "ingresar"), True, "apretar ingresar"),
    (("login", "confirmacion"), True, "saber que el login funciono"),
    (("empresas", "activa"), False, "leer que empresa esta abierta"),
    (("empresas", "abrir_selector"), False, "abrir el selector de empresas"),
    (("empresas", "filas"), False, "leer la lista de empresas"),
    (("cuenta", "abrir_saldo"), True, "entrar a los movimientos (el 'apretar en saldo')"),
    (("saldos", "actual"), True, "leer el saldo actual"),
    (("saldos", "disponible"), False, "leer el saldo disponible"),
    (("fechas", "desde"), True, "cargar la fecha desde"),
    (("fechas", "hasta"), True, "cargar la fecha hasta"),
    (("fechas", "aplicar"), True, "aplicar el filtro"),
    (("fechas", "confirmacion"), True, "saber que el filtro se aplico de verdad"),
    (("descarga", "boton"), True, "descargar el archivo"),
]


def revisar(banco):
    ficha = cargar_ficha(banco)
    bot = BotGenerico(banco, ficha)

    faltan, opcionales, ok = [], [], []
    for camino, obligatorio, para in CAMPOS:
        sels = bot._sels(*camino)
        if sels:
            ok.append((".".join(camino), len(sels)))
        elif obligatorio:
            faltan.append((".".join(camino), para))
        else:
            opcionales.append((".".join(camino), para))

    # Coherencias que un ojo humano pasa por alto.
    avisos = []
    emp = ficha.get("empresas", {})
    if emp.get("tiene"):
        for k in ("abrir_selector", "filas"):
            if not bot._sels("empresas", k):
                avisos.append("empresas.tiene = true pero falta 'empresas.%s': "
                              "o se completa, o se pone tiene = false." % k)
    modo = ficha.get("fechas", {}).get("modo", "inputs")
    if modo != "inputs":
        avisos.append("fechas.modo = '%s': el bot generico solo maneja 'inputs'. "
                      "Un calendario necesita adaptador propio (ver bots/galicia)." % modo)
    # El banco de prueba corre desde un archivo local: la url la pone quien lo
    # usa, no la ficha. Sin esta excepcion, el validador ladra siempre.
    if not ficha.get("_url_en_runtime"):
        if str(ficha.get("url", "")).startswith(">>>") or not ficha.get("url"):
            avisos.append("Falta la url del home banking.")
    # Un solo candidato por paso funciona, pero se rompe al primer rediseño.
    unicos = [c for c, n in ok if n == 1]
    if len(unicos) > 6:
        avisos.append("%d pasos tienen un solo selector candidato. Conviene "
                      "agregar una alternativa a los mas importantes: cuando el "
                      "banco cambia el frente, el que tiene uno solo se cae." % len(unicos))

    return {"banco": banco, "ok": ok, "faltan": faltan,
            "opcionales": opcionales, "avisos": avisos}


def imprimir(r):
    L = 70
    listo = not r["faltan"]
    print("=" * L)
    print("  FICHA: %s   ->   %s" % (r["banco"].upper(),
                                     "LISTA PARA PROBAR" if listo else "INCOMPLETA"))
    print("=" * L)
    print("  Completos: %d de %d pasos obligatorios+opcionales" % (
        len(r["ok"]), len(CAMPOS)))

    if r["faltan"]:
        print("\n  [X] FALTA (sin esto el bot no corre):")
        for c, para in r["faltan"]:
            print("      . %-28s %s" % (c, para))
    if r["opcionales"]:
        print("\n  [ ] Sin completar, pero opcionales:")
        for c, para in r["opcionales"]:
            print("      . %-28s %s" % (c, para))
    if r["avisos"]:
        print("\n  [!] Avisos:")
        for a in r["avisos"]:
            print("      . %s" % a)
    if listo and not r["avisos"]:
        print("\n  Nada pendiente. Falta la unica prueba que no se puede hacer")
        print("  desde aca: correrla contra el banco.")
    print("")
    return listo


def main():
    ap = argparse.ArgumentParser(description="Valida fichas de banco sin tocar el banco")
    ap.add_argument("--banco")
    ap.add_argument("--todos", action="store_true")
    args = ap.parse_args()

    if args.todos:
        fichas = sorted(glob.glob(os.path.join(BASE_REPO, "bots", "*", "selectores.json")))
        bancos = [os.path.basename(os.path.dirname(f)) for f in fichas]
        bancos = [b for b in bancos if not b.startswith("_")]
        todo_ok = True
        for b in bancos:
            todo_ok = imprimir(revisar(b)) and todo_ok
        sys.exit(0 if todo_ok else 1)

    if not args.banco:
        ap.error("Indica --banco <nombre> o --todos")
    sys.exit(0 if imprimir(revisar(args.banco)) else 1)


if __name__ == "__main__":
    main()
