# -*- coding: utf-8 -*-
"""
ingestas.cheques — lee el "Listado de cheques emitidos" que se baja del banco
y lo convierte en OBLIGACIONES del contrato.

POR QUÉ EXISTE
--------------
Los cheques a pagar son el intocable más duro: si no se cubre uno, la empresa
va al BCRA. Hoy se cargan A MANO (se baja el listado semanal del banco y se hace
un BUSCARV contra la planilla para ver cuáles ya están cargados). Eso es el punto
débil del circuito: si se pasa uno, el problema es grave.

Este módulo automatiza esa carga: lee el CSV del banco, normaliza y deja cada
cheque como una obligación con su fecha de vencimiento (= Fecha de pago), lista
para que el simulador la reserve.

FORMATO (Galicia — "ListadoChequesEmitidos*.csv")
-------------------------------------------------
- Separador ';'
- La fila 1 es un encabezado de grupos ("Datos del cheque;;;;...") -> se saltea.
- La fila 2 tiene los nombres de columna reales.
- Importes en formato argentino: "$14.779.136,29"
- Fechas dd/mm/aaaa

Otros bancos traerán otro formato: se agrega otra función parse_<banco>() y se
elige por config del cliente. La SALIDA (la obligación normalizada) es siempre igual.
"""

import os
import re
import csv
import json
import unicodedata
from datetime import datetime

# Estados del listado del banco -> ¿sigue pendiente de debitarse?
# 'Pagado' ya salió de la cuenta; el resto todavía va a impactar.
ESTADOS_PAGADO = {"PAGADO", "DEBITADO", "RECHAZADO", "ANULADO"}


def _norm(s):
    """MAYÚSCULAS, sin acentos, espacios colapsados (para comparar encabezados).

    Además saca los indicadores ordinales 'º' y '°', porque el banco escribe
    "Nº de cheque" y sin esto no matchearía con "N DE CHEQUE".
    """
    s = str(s or "").strip()
    s = s.replace("º", "").replace("°", "").replace("Nro", "N").replace("nro", "N")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s).upper().strip()


def _monto(txt):
    """'$14.779.136,29' -> 14779136.29 ; devuelve 0.0 si no puede."""
    if txt is None:
        return 0.0
    s = str(txt).strip()
    if not s:
        return 0.0
    neg = s.startswith("-") or s.startswith("(")
    s = re.sub(r"[^\d,.]", "", s)
    if not s:
        return 0.0
    # formato AR: '.' miles, ',' decimales
    s = s.replace(".", "").replace(",", ".")
    try:
        v = float(s)
    except ValueError:
        return 0.0
    return -v if neg else v


def _fecha(txt):
    """'03/09/2026' -> '2026-09-03' ; None si no puede."""
    s = str(txt or "").strip()
    m = re.match(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})", s)
    if not m:
        return None
    d, mes, a = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if a < 100:
        a += 2000
    try:
        return datetime(a, mes, d).strftime("%Y-%m-%d")
    except ValueError:
        return None


def _abrir(path):
    """Lee el archivo probando encodings (los export de banco varían)."""
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                return f.read(), enc
        except UnicodeDecodeError:
            continue
    raise IOError("No pude leer el archivo con ningún encoding conocido: %s" % path)


def _indices(encabezado):
    """Mapa nombre_normalizado -> índice de columna (primera aparición).

    El listado repite nombres ('CUIT/CUIL/CDI' aparece 3 veces, 'Razón social' 2),
    así que nos quedamos con la PRIMERA de cada uno, que es la que nos sirve.
    """
    idx = {}
    for i, h in enumerate(encabezado):
        n = _norm(h)
        if n and n not in idx:
            idx[n] = i
    return idx


def parse_galicia(path, unidad_por_librador=None):
    """Lee el CSV de cheques emitidos y devuelve (obligaciones, resumen).

    unidad_por_librador: dict opcional {'SPEEDMED SA': 'SPEEDMED', ...} para
    mapear la razón social del librador a la unidad de negocio del cliente.
    """
    texto, enc = _abrir(path)
    filas = list(csv.reader(texto.splitlines(), delimiter=";"))
    if not filas:
        return [], {"error": "archivo vacío"}

    # Buscar la fila de encabezado real (la que tiene 'N DE CHEQUE')
    fila_enc = None
    for i, fila in enumerate(filas[:6]):
        if any(_norm(c).startswith("N DE CHEQUE") or _norm(c) == "NO DE CHEQUE" for c in fila):
            fila_enc = i
            break
    if fila_enc is None:
        return [], {"error": "no encontré la fila de encabezados (busco 'Nº de cheque')"}

    idx = _indices(filas[fila_enc])

    def col(fila, *nombres):
        for n in nombres:
            i = idx.get(n)
            if i is not None and i < len(fila):
                return fila[i].strip()
        return ""

    obligaciones, vistos, saltadas = [], set(), 0
    for fila in filas[fila_enc + 1:]:
        if not fila or not any(c.strip() for c in fila):
            continue
        nro = col(fila, "N DE CHEQUE", "NO DE CHEQUE")
        if not nro:
            continue

        cuenta = col(fila, "CUENTA LIBRADORA")
        banco = col(fila, "BANCO EMISOR")
        estado_banco = col(fila, "ESTADO")
        fpago = _fecha(col(fila, "FECHA DE PAGO"))
        importe = _monto(col(fila, "IMPORTE"))
        librador = col(fila, "RAZON SOCIAL")

        # Clave anti-duplicado: banco + cuenta + número de cheque.
        # Esto reemplaza el BUSCARV manual: si ya se cargó, no se vuelve a cargar.
        clave = "%s|%s|%s" % (_norm(banco), cuenta, nro)
        if clave in vistos:
            saltadas += 1
            continue
        vistos.add(clave)

        pendiente = _norm(estado_banco) not in ESTADOS_PAGADO

        obligaciones.append({
            "id": clave,
            "tipo": "CHEQUE",
            "categoria": "proveedores",
            "dias_tolerancia": 0,
            "consecuencia": "BCRA",
            "fecha_vencimiento": fpago,
            "fecha_emision": _fecha(col(fila, "FECHA DE EMISION")),
            "importe": importe,
            "contraparte": col(fila, "EMITIDO A"),
            "contraparte_cuit": col(fila, "CUIT/CUIL/CDI"),
            "unidad": (unidad_por_librador or {}).get(_norm(librador), _norm(librador)),
            "banco": banco,
            "cuenta": cuenta,
            "referencia": nro,
            "motivo": col(fila, "MOTIVO Y DESCRIPCION"),
            "estado_banco": estado_banco,
            "pendiente": pendiente,
        })

    pend = [o for o in obligaciones if o["pendiente"]]
    resumen = {
        "archivo": os.path.basename(path),
        "encoding": enc,
        "leidos": len(obligaciones) + saltadas,
        "cheques": len(obligaciones),
        "duplicados_salteados": saltadas,
        "pendientes": len(pend),
        "importe_pendiente": round(sum(o["importe"] for o in pend), 2),
        "estados": _contar(obligaciones, "estado_banco"),
        "sin_fecha_pago": len([o for o in obligaciones if not o["fecha_vencimiento"]]),
    }
    return obligaciones, resumen


def _contar(items, campo):
    out = {}
    for it in items:
        k = it.get(campo) or "(vacío)"
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def proximos(obligaciones, desde=None, hasta=None):
    """Filtra los cheques pendientes que vencen en el rango [desde, hasta]."""
    out = []
    for o in obligaciones:
        if not o["pendiente"] or not o["fecha_vencimiento"]:
            continue
        f = o["fecha_vencimiento"]
        if desde and f < desde:
            continue
        if hasta and f > hasta:
            continue
        out.append(o)
    return sorted(out, key=lambda o: o["fecha_vencimiento"])


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Parser del listado de cheques emitidos del banco")
    ap.add_argument("archivo", help="CSV bajado del banco")
    ap.add_argument("--json", help="guardar las obligaciones en este archivo")
    ap.add_argument("--desde", help="AAAA-MM-DD")
    ap.add_argument("--hasta", help="AAAA-MM-DD")
    args = ap.parse_args()

    obl, res = parse_galicia(args.archivo)
    print("=== RESUMEN ===")
    for k, v in res.items():
        print("  %-22s %s" % (k, v))

    if args.desde or args.hasta:
        prox = proximos(obl, args.desde, args.hasta)
        tot = sum(o["importe"] for o in prox)
        print("\n=== VENCEN entre %s y %s: %d cheques  ·  $%s ===" % (
            args.desde or "(inicio)", args.hasta or "(fin)", len(prox), format(round(tot, 2), ",.2f")))

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(obl, f, ensure_ascii=False, indent=2)
        print("\nGuardado: %s" % args.json)
