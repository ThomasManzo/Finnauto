# -*- coding: utf-8 -*-
"""
finauto — un solo comando que arma todo el material de una visita.

POR QUE EXISTE
--------------
Hasta acá cada herramienta se corría por separado: el contraste, el simulador,
la posición, la app, el informe. Eso está bien para desarrollar y es pésimo para
trabajar: **antes de una reunión nadie se acuerda de correr siete comandos en el
orden correcto**, y el que se olvida es siempre el que hacía falta.

    python finauto.py --contrato datos/CONTRATO_maga_2026-09-05.json

Eso deja en `salidas/` todo lo que se muestra y todo lo que se manda, y en
pantalla el resumen de lo que hay que mirar antes de salir.

QUE HACE, EN ORDEN
------------------
    1. controla el dato        ¿falta algo? ¿es coherente?
    2. contrasta               ¿coincide con los números del propio cliente?
    3. arma la app             el tablero con el que se muestra
    4. arma el informe         la hoja que se manda por mail
    5. guarda la memoria       la foto de hoy, para poder decir después
                               "te lo dije y pasó"

El paso 5 no es un extra: es lo único que hace que la segunda visita valga más
que la primera. Y solo funciona si la foto se toma HOY — dentro de un mes ya no
se puede tomar la de hoy.
"""

import io
import os
import sys
import json
import argparse
import datetime
import subprocess

BASE_REPO = os.path.dirname(os.path.abspath(__file__))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)


def _linea(t=""):
    print(t)



def _parrafo(txt, ancho=68, sangria="      "):
    linea = sangria
    for p in txt.split():
        if len(linea) + len(p) + 1 > ancho:
            print(linea)
            linea = sangria
        linea += p + " "
    print(linea.rstrip())


def _titulo(n, t):
    print("\n" + "=" * 72)
    print("  %s · %s" % (n, t))
    print("=" * 72)


def correr(contrato_path, cliente="maga", salidas="salidas", con_memoria=True):
    with io.open(contrato_path, encoding="utf-8") as f:
        contrato = json.load(f)

    if not os.path.isabs(salidas):
        salidas = os.path.join(BASE_REPO, salidas)
    if not os.path.isdir(salidas):
        os.makedirs(salidas)

    hechos = []

    # ---------------------------------------------------------- 1. el dato
    _titulo(1, "EL DATO: ¿está completo y es coherente?")
    try:
        from auditoria import revisar as REV
        if hasattr(REV, "completitud"):
            avisos = REV.completitud(contrato) or []
            if not avisos:
                _linea("   Sin agujeros detectados.")
            for aviso in avisos:
                # completitud() devuelve (TITULO, explicacion). Imprimirlo como
                # tupla cruda hace que el resumen parezca salida de debug justo
                # donde se lee antes de una reunion.
                if isinstance(aviso, (tuple, list)) and len(aviso) >= 2:
                    _linea("   [%s]" % aviso[0])
                    _parrafo(str(aviso[1]))
                else:
                    _linea("   . " + str(aviso))
        else:
            _linea("   (el módulo de auditoría no expone completitud())")
    except Exception as e:
        _linea("   No pude correr la auditoría: %s" % e)
    for a in (contrato.get("avisos") or [])[:3]:
        _linea("   · " + str(a)[:200])

    # ------------------------------------------------- 2. contra el cliente
    _titulo(2, "EL MOTOR CONTRA LOS NÚMEROS DEL CLIENTE")
    try:
        from auditoria import contraste as CT
        filas, ref = CT.contrastar(contrato)
        CT.imprimir(filas, ref)
    except Exception as e:
        _linea("   No pude contrastar: %s" % e)

    # ------------------------------------------------------------ 3. la app
    _titulo(3, "EL TABLERO")
    from dashboard import app as APP
    from dashboard import datos as DATOS
    paquete = DATOS.armar(contrato, cliente)
    ruta_app = os.path.join(salidas, "finauto.html")
    with io.open(ruta_app, "w", encoding="utf-8") as f:
        f.write("<!doctype html>\n<html lang=\"es\">\n")
        f.write(APP.render(paquete))
        f.write("\n</html>")
    _linea("   %s  (%d KB)" % (ruta_app, os.path.getsize(ruta_app) // 1024))
    hechos.append(ruta_app)

    # -------------------------------------------------------- 4. el informe
    _titulo(4, "EL INFORME PARA MANDAR")
    from dashboard import generar as GEN
    ruta_inf = os.path.join(salidas, "informe.html")
    with io.open(ruta_inf, "w", encoding="utf-8") as f:
        f.write("<!doctype html>\n<html lang=\"es\"><head>"
                "<meta charset=\"utf-8\">"
                "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n")
        f.write(GEN.render(contrato, cliente))
        f.write("\n</head></html>")
    _linea("   %s  (%d KB)" % (ruta_inf, os.path.getsize(ruta_inf) // 1024))
    hechos.append(ruta_inf)

    # -------------------------------------------------------- 5. la memoria
    if con_memoria:
        _titulo(5, "LA MEMORIA: la foto de hoy")
        try:
            from memoria import registro as MEM
            # guardar() devuelve (ruta, foto). Antes se imprimia la tupla entera
            # como si fuera la ruta y el paso 5 fallaba con un error de formato.
            ruta = MEM.guardar(cliente, contrato, dias=30,
                               etiqueta="automática %s" % datetime.date.today())
            if isinstance(ruta, (tuple, list)):
                ruta = ruta[0]
            _linea("   Guardada: %s" % ruta)
            _linea("   Esto es lo que dentro de un mes permite decir \"te lo dije\".")
            _linea("   La foto de hoy solo se puede sacar hoy.")
        except Exception as e:
            _linea("   No pude guardar la memoria: %s" % e)

    # ----------------------------------------------------------- el resumen
    _titulo("", "ANTES DE SALIR")
    d = paquete["datos"][paquete["unidades"][0]]
    k = d["kpis"]
    _linea("   Cliente : %s   ·   datos al %s" % (paquete["cliente"], paquete["fecha"]))
    _linea("   Caja    : %s" % _m(k["caja"]))
    _linea("   Vencido : %s   <- lo que puede cortarte la compra" % _m(k["vencido"]))
    _linea("   Retiro  : %s" % ("hasta " + _m(k["margen"]) if k["se_puede"]
                                else "NO — faltan " + _m(k["falta"])))
    if paquete["hallazgos"]:
        _linea("")
        _linea("   Para contar en la reunión:")
        for h in paquete["hallazgos"]:
            import re
            t = re.sub("<[^>]+>", "", h["titulo"])
            _linea("     · %s%s" % (t, ("  " + _m(h["monto"])) if h["monto"] else ""))
    _linea("")
    for h in hechos:
        _linea("   Abrir: %s" % h)
    return hechos


def _m(v):
    signo = "-" if v < 0 else ""
    return signo + "$" + format(int(round(abs(v))), ",d").replace(",", ".")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(
        description="Arma todo el material de una visita, de una sola vez")
    ap.add_argument("--contrato", required=True)
    ap.add_argument("--cliente", default="maga")
    ap.add_argument("--salidas", default="salidas")
    ap.add_argument("--sin-memoria", action="store_true",
                    help="no guardar la foto de hoy (para pruebas)")
    args = ap.parse_args()
    correr(args.contrato, args.cliente, args.salidas, not args.sin_memoria)


if __name__ == "__main__":
    main()
