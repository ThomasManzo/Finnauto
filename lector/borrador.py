# -*- coding: utf-8 -*-
"""
lector.borrador — el puente entre la reunión con el cliente y el motor.

EL CIRCUITO
-----------
    planilla desconocida
        -> lector/planilla.py      ve la estructura y arma las preguntas
        -> ESTE MODULO             deja un borrador con lo que dedujo
        -> [reunion con el cliente: se completa el borrador a mano]
        -> lector/borrador.py --aplicar   escribe mapeo.json y catalogo.json
        -> lector/extraer.py       planilla -> contrato.json
        -> simulador / proyeccion / consejo

POR QUE UN ARCHIVO Y NO UN ASISTENTE INTERACTIVO
------------------------------------------------
Un asistente que pregunta en la terminal obliga a contestar todo de una sentada,
y adelante del cliente eso no pasa: se contesta la mitad, se anota una duda, se
vuelve al otro día. Un archivo se edita en cualquier momento, se manda por mail,
queda como registro de lo que dijo el cliente, y se puede versionar.

QUE SE PRECOMPLETA Y QUE NO
---------------------------
Se precompleta lo que se puede deducir sin riesgo: la columna de fecha, la de
concepto, la de importe cuando hay una sola. Se deja explicitamente vacio todo
lo que, si se adivina mal, rompe el numero: cual de dos columnas de numeros es
el importe, y sobre todo cuantos dias se puede postergar cada tipo. Eso ultimo
no lo sabe ningun algoritmo: lo sabe el que paga.

Los tipos van ordenados POR PLATA, no alfabeticamente: en una reunion de una
hora conviene discutir primero los tres que mueven el 80%.

Uso:
    python lector/borrador.py --archivo "Cash.xlsx" --salida borrador.json
    python lector/borrador.py --aplicar borrador.json --cliente panaderia
"""

import io
import os
import re
import sys
import json
import argparse
import datetime
from collections import Counter, defaultdict, OrderedDict

BASE_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)

from lector.planilla import analizar, preguntas, _es_numero, _es_fecha, _vacio
from lector.agrupar import proponer

FALTA = ">>> COMPLETAR"


def _num(v):
    """Monto argentino o ingles -> float. Devuelve 0.0 si no se puede."""
    if isinstance(v, bool) or v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace("$", "").replace(" ", "")
    neg = s.startswith("-") or (s.startswith("(") and s.endswith(")"))
    s = re.sub(r"[^\d.,]", "", s)
    if not s:
        return 0.0
    # El ultimo separador manda: "1.234,56" -> coma decimal; "1,234.56" -> punto.
    if "," in s and "." in s:
        dec = "," if s.rfind(",") > s.rfind(".") else "."
    elif "," in s:
        dec = "," if len(s.split(",")[-1]) <= 2 else None
    elif "." in s:
        dec = "." if len(s.split(".")[-1]) <= 2 else None
    else:
        dec = None
    if dec == ",":
        s = s.replace(".", "").replace(",", ".")
    elif dec == ".":
        s = s.replace(",", "")
    else:
        s = s.replace(".", "").replace(",", "")
    try:
        v = float(s)
    except ValueError:
        return 0.0
    return -v if neg else v


def _hoja_principal(analisis):
    """La hoja de movimientos: la que tiene fecha, importe y mas filas."""
    mejor, mejor_p = None, -1
    for a in analisis:
        if a.get("vacia") or a.get("sin_tabla"):
            continue
        clases = [c["clase"] for c in a["columnas"]]
        if "fecha" not in clases or "numero" not in clases:
            continue
        if a["filas_datos"] > mejor_p:
            mejor, mejor_p = a, a["filas_datos"]
    return mejor


def _elegir(cols, clase, preferir=()):
    """Elige una columna de esa clase. Si hay varias, no adivina: devuelve None."""
    cands = [c for c in cols if c["clase"] == clase]
    if not cands:
        return None, []
    if len(cands) == 1:
        return cands[0], cands
    for pref in preferir:
        for c in cands:
            if pref in c["titulo"].upper():
                return c, cands
    return None, cands


def armar(archivo, analisis=None):
    analisis = analisis or analizar(archivo)
    hoja = _hoja_principal(analisis)
    if hoja is None:
        return {"_error": "No encontre ninguna hoja con fecha e importe juntos. "
                          "Revisar la radiografia y mapear a mano."}

    cols = hoja["columnas"]
    fecha, cf = _elegir(cols, "fecha", ("FECHA", "VENC", "PAGO"))
    imp, ci = _elegir(cols, "numero", ("IMPORTE", "MONTO", "EGRESO", "TOTAL"))
    tipo, ct = _elegir(cols, "categoria", ("TIPO", "RUBRO", "CATEG", "CONCEPTO"))
    texto = [c for c in cols if c["clase"] == "texto"]
    concepto = max(texto, key=lambda c: c["distintos"]) if texto else None

    def ref(c, cands, que):
        if c is not None:
            return c["titulo"]
        if not cands:
            return FALTA + ": no encontre ninguna columna de %s" % que
        return FALTA + ": hay varias (%s), cual es %s?" % (
            ", ".join(x["titulo"] for x in cands[:6]), que)

    mapeo = OrderedDict([
        ("_ayuda", "Que columna de la planilla es cada cosa. Se completa con el "
                   "cliente: lo que quedo en '" + FALTA + "' es justamente lo que "
                   "no se puede adivinar sin romper el numero."),
        ("archivo_ejemplo", os.path.basename(archivo)),
        ("hoja", hoja["hoja"]),
        ("fila_encabezado", hoja["fila_encabezado"]),
        ("columnas", OrderedDict([
            ("fecha", ref(fecha, cf, "la fecha del movimiento")),
            ("importe", ref(imp, ci, "el importe del movimiento")),
            ("tipo", ref(tipo, ct, "la categoria del movimiento")),
            ("concepto", concepto["titulo"] if concepto else
             FALTA + ": el texto que describe el movimiento"),
        ])),
        ("_signo", OrderedDict([
            ("_ayuda", "Como distingue la planilla un egreso de un ingreso."),
            ("modo", FALTA + ": 'signo' (negativo=egreso), 'columnas' (una de "
                             "egresos y otra de ingresos) o 'todos_egresos'"),
            ("columna_ingresos", ""),
        ])),
    ])

    # --- catalogo: los rubros, ordenados POR PLATA
    tipos, deducidos = [], False
    if tipo is not None and imp is not None:
        tipos = _tipos_con_peso(archivo, hoja, tipo, imp)
    elif tipo is not None:
        tipos = [{"id": v, "movimientos": n} for v, n in tipo["valores"]]
    elif concepto is not None and imp is not None:
        # La planilla no tiene columna de categoria. Es el caso mas comun en una
        # empresa chica, y sin rubros el motor se queda sin nada: el proyector
        # cae del 93% al 4% de cobertura.
        #
        # Pero la informacion esta escrita en el concepto. Se proponen grupos
        # mirando SOLO el texto. Medido sobre 1069 movimientos reales, agrupar
        # asi da 87% de pureza contra los rubros de verdad.
        #
        # Son una PROPUESTA: van con nombre provisorio para que el cliente los
        # confirme o los junte.
        tipos = _tipos_deducidos(archivo, hoja, concepto, imp)
        deducidos = True

    catalogo = OrderedDict([
        ("_deducidos", deducidos),
        ("_aviso_deducidos",
         ("OJO: la planilla NO tiene columna de categoria. Estos rubros los "
          "propuso el sistema agrupando por las palabras del concepto. Hay que "
          "revisarlos CON EL CLIENTE: confirmar los que estan bien, juntar los "
          "que son lo mismo y descartar los que no sirven. El campo '_ejemplos' "
          "muestra que movimientos cayeron en cada grupo.") if deducidos else ""),
        ("_ayuda", "Un tipo por cada valor de la columna de categoria. "
                   "'dias_tolerancia' es LA pregunta: cuantos dias se puede correr "
                   "ese pago. 0 = no se puede mover. Ordenados por plata: en una "
                   "reunion conviene empezar por los que mueven el 80%."),
        ("_pregunta", "Para cada uno: si manana no alcanza la plata, ¿este se "
                      "puede postergar? ¿Cuantos dias? ¿Que pasa si no se paga?"),
        ("tipos", OrderedDict([
            ("_ayuda", "dias_tolerancia: 0 = intocable. divisible: si se puede "
                       "pagar una parte. interno: si no sale plata del grupo."),
            ("valores", [_tipo_vacio(t) for t in tipos]),
        ])),
        ("excepciones_por_concepto", {"_ayuda": "Cuando dentro de un mismo tipo hay "
                                                "cosas distintas. Se llena despues, "
                                                "mirando datos reales.",
                                      "reglas": []}),
        ("orden_de_pateo", {"_ayuda": "En que orden mover los pagos cuando falta "
                                      "plata. Lo decide el dueno.",
                            "prioridad_por_tipo": [FALTA]}),
    ])

    return OrderedDict([
        ("_generado", datetime.datetime.now().isoformat(timespec="seconds")),
        ("_como_sigue", [
            "1. Llevar las preguntas de abajo a la reunion con quien carga los numeros.",
            "2. Completar todo lo que diga '" + FALTA + "'.",
            "3. python lector/borrador.py --aplicar este_archivo.json --cliente <nombre>",
            "4. python lector/extraer.py --archivo la_planilla.xlsx --cliente <nombre>",
        ]),
        ("mapeo", mapeo),
        ("catalogo", catalogo),
        ("preguntas_para_el_cliente", _preguntas_todas(analisis, deducidos, tipos, hoja)),
    ])


def _preguntas_todas(analisis, deducidos, tipos, hoja):
    """Las preguntas de la radiografia, mas la que importa cuando no hay rubros."""
    qs = [{"hoja": h, "pregunta": q, "respuesta": ""} for h, q in preguntas(analisis)]
    if not deducidos:
        return qs

    # Cuando los rubros los dedujo el sistema, esta es LA pregunta de la reunion:
    # va primera y con los grupos concretos adelante. Agrupando por texto es
    # normal que quede un grupo por empleado en vez de uno de "sueldos"; eso lo
    # junta una persona en diez segundos, pero hay que preguntarlo.
    nombres = ", ".join(t["id"] for t in tipos[:10] if t["id"] != "SIN_AGRUPAR")
    qs.insert(0, {
        "hoja": hoja["hoja"],
        "pregunta": ("Esta planilla NO tiene columna de rubro, asi que los agrupe "
                     "mirando las palabras del concepto: %s. ¿Estan bien? ¿Cuales "
                     "hay que juntar en uno solo (por ejemplo, varios grupos que "
                     "en realidad son todos sueldos)? ¿Y como se llama cada uno?"
                     % nombres),
        "respuesta": ""})
    sin = [t for t in tipos if t["id"] == "SIN_AGRUPAR"]
    if sin and sin[0]["pct"] > 5:
        qs.insert(1, {
            "hoja": hoja["hoja"],
            "pregunta": ("Hay %d movimientos (%.0f%% de la plata) que no comparten "
                         "palabra con ningun otro y quedaron sin agrupar. ¿Son "
                         "gastos de una sola vez o hay algo que se repite y se "
                         "escribe distinto cada vez?" % (sin[0]["movimientos"],
                                                         sin[0]["pct"])),
            "respuesta": ""})
    return qs


def _tipos_deducidos(archivo, hoja, colc, coli):
    """Rubros propuestos a partir del texto, cuando no hay columna de categoria."""
    from lector.planilla import leer_hoja
    import openpyxl
    wb = openpyxl.load_workbook(archivo, data_only=True, read_only=True)
    filas = leer_hoja(wb[hoja["hoja"]])
    wb.close()
    cuerpo = [f for f in filas[hoja["fila_encabezado"]:] if any(not _vacio(v) for v in f)]

    movs = []
    for f in cuerpo:
        c = f[colc["col"]] if colc["col"] < len(f) else None
        v = f[coli["col"]] if coli["col"] < len(f) else None
        if _vacio(c):
            continue
        movs.append({"concepto": str(c).strip(), "importe": abs(_num(v))})

    grupos, sueltos = proponer(movs)
    total = sum(g["importe"] for g in grupos) + sum(
        abs(m["importe"]) for m in sueltos) or 1.0
    out = [{"id": g["palabra"], "movimientos": g["movimientos"],
            "importe": g["importe"], "pct": 100.0 * g["importe"] / total,
            "ejemplos": g["ejemplos"]}
           for g in grupos]
    if sueltos:
        imp = sum(abs(m["importe"]) for m in sueltos)
        out.append({"id": "SIN_AGRUPAR", "movimientos": len(sueltos), "importe": imp,
                    "pct": 100.0 * imp / total,
                    "ejemplos": [m["concepto"][:52] for m in
                                 sorted(sueltos, key=lambda x: -abs(x["importe"]))[:3]]})
    return out


def _tipo_vacio(t):
    d = OrderedDict([("id", t["id"]), ("nombre", t["id"])])
    if "importe" in t:
        d["_peso"] = "%d movimientos, %s (%.0f%% del total)" % (
            t["movimientos"], _fmt(t["importe"]), t["pct"])
    else:
        d["_peso"] = "%d movimientos" % t["movimientos"]
    if t.get("ejemplos"):
        d["_ejemplos"] = t["ejemplos"]
        d["_nota"] = "Rubro PROPUESTO por el sistema (la planilla no traia categoria). Confirmar el nombre con el cliente."
    d["dias_tolerancia"] = FALTA
    d["consecuencia"] = FALTA + ": que pasa si no se paga a tiempo"
    d["divisible"] = FALTA
    return d


def _fmt(v):
    s = format(int(round(abs(v))), ",d").replace(",", ".")
    return ("-$" if v < 0 else "$") + s


def _tipos_con_peso(archivo, hoja, colt, coli):
    """Cuanto mueve cada tipo: lo que decide por cual empezar a preguntar."""
    from lector.planilla import leer_hoja
    import openpyxl
    wb = openpyxl.load_workbook(archivo, data_only=True, read_only=True)
    filas = leer_hoja(wb[hoja["hoja"]])
    wb.close()
    cuerpo = [f for f in filas[hoja["fila_encabezado"]:] if any(not _vacio(v) for v in f)]

    agg = defaultdict(lambda: [0, 0.0])
    for f in cuerpo:
        t = f[colt["col"]] if colt["col"] < len(f) else None
        if _vacio(t):
            continue
        v = f[coli["col"]] if coli["col"] < len(f) else None
        agg[str(t).strip()][0] += 1
        agg[str(t).strip()][1] += abs(_num(v))
    total = sum(x[1] for x in agg.values()) or 1.0
    out = [{"id": k, "movimientos": n, "importe": s, "pct": 100.0 * s / total}
           for k, (n, s) in agg.items()]
    return sorted(out, key=lambda x: -x["importe"])


# ------------------------------------------------------------------ aplicar
def _faltantes(obj, camino=""):
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.startswith("_"):
                continue
            out += _faltantes(v, "%s.%s" % (camino, k) if camino else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out += _faltantes(v, "%s[%d]" % (camino, i))
    elif isinstance(obj, str) and obj.startswith(FALTA):
        out.append((camino, obj))
    return out


def aplicar(ruta_borrador, cliente, forzar=False):
    with io.open(ruta_borrador, encoding="utf-8") as f:
        b = json.load(f)

    faltan = _faltantes({"mapeo": b.get("mapeo", {}), "catalogo": b.get("catalogo", {})})
    if faltan and not forzar:
        return None, faltan

    destino = os.path.join(BASE_REPO, "clientes", cliente)
    if not os.path.isdir(destino):
        os.makedirs(destino)
    escritos = []
    for nombre, contenido in (("mapeo.json", b["mapeo"]), ("catalogo.json", b["catalogo"])):
        ruta = os.path.join(destino, nombre)
        with io.open(ruta, "w", encoding="utf-8") as f:
            f.write(json.dumps(contenido, ensure_ascii=False, indent=2))
            f.write(u"\n")
        escritos.append(ruta)

    # Las respuestas del cliente se guardan aparte: son el registro de lo que
    # dijo, y en tres meses nadie se acuerda de por que un tipo quedo en 0 dias.
    qs = [q for q in b.get("preguntas_para_el_cliente", []) if q.get("respuesta")]
    if qs:
        ruta = os.path.join(destino, "respuestas_del_cliente.json")
        with io.open(ruta, "w", encoding="utf-8") as f:
            f.write(json.dumps(qs, ensure_ascii=False, indent=2))
            f.write(u"\n")
        escritos.append(ruta)
    return escritos, faltan


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="Borrador de mapeo y catalogo")
    ap.add_argument("--archivo", help="planilla a analizar")
    ap.add_argument("--salida", default="borrador.json")
    ap.add_argument("--aplicar", help="borrador ya completado")
    ap.add_argument("--cliente", help="carpeta del cliente (ej: panaderia)")
    ap.add_argument("--forzar", action="store_true",
                    help="aplicar aunque queden cosas sin completar")
    args = ap.parse_args()

    if args.aplicar:
        if not args.cliente:
            ap.error("--aplicar necesita --cliente")
        escritos, faltan = aplicar(args.aplicar, args.cliente, args.forzar)
        if escritos is None:
            print("  Todavia falta completar %d cosa(s):\n" % len(faltan))
            for camino, txt in faltan:
                print("   . %-34s %s" % (camino, txt[len(FALTA):].lstrip(": ") or "(sin valor)"))
            print("\n  Completalas en %s y volve a correr." % args.aplicar)
            print("  (--forzar aplica igual, pero el motor va a fallar donde falte)")
            sys.exit(1)
        print("  Escrito:")
        for e in escritos:
            print("   . %s" % e)
        print("\n  Siguiente: python lector/extraer.py --archivo <planilla> --cliente %s"
              % args.cliente)
        return

    if not args.archivo:
        ap.error("Indica --archivo <planilla> o --aplicar <borrador>")
    b = armar(args.archivo)
    with io.open(args.salida, "w", encoding="utf-8") as f:
        f.write(json.dumps(b, ensure_ascii=False, indent=2, default=str))
        f.write(u"\n")

    faltan = _faltantes({"mapeo": b.get("mapeo", {}), "catalogo": b.get("catalogo", {})})
    print("  Borrador: %s" % args.salida)
    print("  Quedaron %d cosa(s) para completar con el cliente." % len(faltan))
    print("  Preguntas para la reunion: %d" % len(b.get("preguntas_para_el_cliente", [])))
    tipos = b.get("catalogo", {}).get("tipos", {}).get("valores", [])
    if tipos:
        print("\n  Tipos encontrados (ordenados por plata: empezar por estos):")
        for t in tipos[:8]:
            print("   . %-24s %s" % (t["id"][:24], t.get("_peso", "")))


if __name__ == "__main__":
    main()
