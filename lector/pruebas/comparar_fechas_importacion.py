"""Compara dos fotos de la cartera sin modificarlas ni guardar datos reales.

Uso: python comparar_fechas_importacion.py PARA_PEGAR EXPORT_SHEET
Con --node /ruta/a/node también prueba el volcado local con esas mismas filas.
La tabla sale por pantalla: quien la revise decide dónde conservarla.
"""

import argparse
from collections import Counter, defaultdict
from datetime import date, datetime
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import unicodedata

import openpyxl


def normalizar(valor):
    texto = unicodedata.normalize("NFD", str(valor or "").lower())
    return " ".join("".join(c for c in texto if not unicodedata.combining(c)).split())


def leer(ruta):
    libro = openpyxl.load_workbook(ruta, read_only=True, data_only=False)
    try:
        filas = list(libro["Cartera de Cheques"].values)
        encabezados = list(filas[0])
        nombres = [normalizar(c) for c in encabezados if c]
        if len(nombres) != len(set(nombres)):
            raise ValueError("Hay encabezados repetidos: no se puede emparejar sin ambigüedad")
        datos = [(i, list(r)) for i, r in enumerate(filas[1:], 2) if r[0] is not None]
        ids = [r[0] for _, r in datos]
        if len(ids) != len(set(ids)):
            raise ValueError("Hay ID repetidos: no se puede emparejar sin ambigüedad")
        if any(isinstance(v, str) and v.startswith("=") for _, r in datos for v in r):
            raise ValueError("Hay fórmulas: hace falta revisar sus valores antes de comparar")
        return encabezados, datos
    finally:
        libro.close()


def fecha(valor):
    return valor.isoformat()[:10] if isinstance(valor, (date, datetime)) else str(valor or "vacía")


def candidatos(datos, columna):
    # Una fecha repetida no permite elegir un cheque: mostramos TODAS las filas posibles.
    resultado = defaultdict(list)
    for fila, valores in datos:
        resultado[valores[columna]].append(fila)
    return resultado


def comparar(origen, destino):
    enc_o, datos_o = origen
    enc_d, datos_d = destino
    por_id = {r[0]: (fila, r) for fila, r in datos_o}
    if set(por_id) != {r[0] for _, r in datos_d}:
        raise ValueError("Los ID no son los mismos: revisar altas y bajas antes de comparar")
    indices = [(nombre, enc_o.index(nombre), enc_d.index(nombre)) for nombre in enc_o if nombre]
    distintos = Counter()
    for _, r in datos_d:
        _, original = por_id[r[0]]
        for nombre, co, cd in indices:
            a, b = original[co], r[cd]
            # El export vuelve numérico el número de cheque guardado como texto.
            iguales = float(a) == float(b) if nombre == "Nro Cheque" else (a or "") == (b or "")
            if not iguales:
                distintos[nombre] += 1
    print(f"Filas: origen {len(datos_o)}, destino {len(datos_d)}. ID únicos y conjuntos iguales.")
    print("Diferencias por columna:", dict(distintos))
    for nombre in ("Fecha Pago / Cobro", "Fecha Emision"):
        co, cd = enc_o.index(nombre), enc_d.index(nombre)
        posibles = candidatos(datos_o, co)
        print(f"\n{nombre}\n")
        print("| Fila Sheet | ID | Fila original | Fecha original | Fecha Sheet | Coincide | Filas originales con esa fecha |")
        print("|---|---|---|---|---|---|---|")
        sin_origen = 0
        for fila, r in datos_d:
            fila_o, original = por_id[r[0]]
            misma = original[co] == r[cd]
            if not misma and not posibles[r[cd]]:
                sin_origen += 1
            if nombre == "Fecha Emision" and misma:
                continue
            filas = ", ".join(map(str, posibles[r[cd]])) or "ninguna"
            print(f"| {fila} | {int(r[0])} | {fila_o} | {fecha(original[co])} | {fecha(r[cd])} | {'sí' if misma else 'no'} | {filas} |")
        print(f"Fechas distintas sin coincidencia en esa columna original: {sin_origen}.")
    return distintos


def serializar(valor):
    if isinstance(valor, (date, datetime)):
        return {"fecha": valor.isoformat()}
    raise TypeError(type(valor).__name__)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("origen", type=Path)
    parser.add_argument("destino", type=Path)
    parser.add_argument("--node", help="Ejecutable Node para probar _volcar_ sin Google")
    args = parser.parse_args()
    for ruta in (args.origen, args.destino):
        print(ruta.name, "SHA-256:", sha256(ruta.read_bytes()).hexdigest())
    origen, destino = leer(args.origen), leer(args.destino)
    comparar(origen, destino)
    if args.node:
        entrada = {nombre: [enc] + [r for _, r in datos]
                   for nombre, (enc, datos) in (("origen", origen), ("destino", destino))}
        subprocess.run([args.node, str(Path(__file__).with_name("probar_volcado_fechas.cjs"))],
                       input=json.dumps(entrada, default=serializar), text=True, check=True)


if __name__ == "__main__":
    main()
