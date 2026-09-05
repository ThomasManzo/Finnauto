# -*- coding: utf-8 -*-
"""
simulador.ajustes — "¿y si a este lo estiro 25 días en vez de 15?"

Idea de Thomas:

    "en vez de dejar algo fijo o variable... en el simulador sumarle la variable
     de que ademas del monto sea el dia, osea elegir dentro de la app cuantos
     dias podes mover cierto pago"

Es un cambio de fondo en cómo hay que leer el catálogo:

    catalogo.json  -> lo que NORMALMENTE pasa   (el valor por defecto)
    ajustes        -> lo que pasa ESTA SEMANA   (lo que sabe el que decide)

El catálogo no puede saber que el martes hablaste con la droguería y te dieron
diez días más. Eso lo sabés vos, y el simulador tiene que poder tomarlo sin que
haya que editar el catálogo: si cada excepción de una semana se escribiera en el
catálogo, en tres meses el catálogo dejaría de describir a la empresa.

Por eso los ajustes son EXPLÍCITOS, TEMPORALES y VISIBLES:
  · explícitos → hay que pedirlos, nunca se aplican solos;
  · temporales → viven en su propio archivo, no ensucian el catálogo;
  · visibles   → el escenario siempre imprime qué se está asumiendo.

Dos formas de usarlos:

    --mover "SUIZO=25"                  rápido, para una pregunta suelta
    --ajustes ajustes.json              para un escenario armado

Formato del archivo:

    {
      "por_concepto": [
        {"contiene": "SUIZO", "dias_tolerancia": 25,
         "_nota": "hablado con el vendedor el 4/9"}
      ]
    }
"""

import io
import json


class AjusteRiesgoso(Exception):
    pass


# Mover ESTO no es "estirar un pago": es aceptar una consecuencia que no se
# arregla con una llamada. El simulador igual lo deja hacer (el que decide es
# el dueño, no el software) pero no en silencio.
CONSECUENCIAS_GRAVES = {
    "BCRA": "el cheque rebota y la empresa queda informada en el BCRA",
    "laboral": "son sueldos: se atrasa el pago a la gente",
    "fiscal": "son impuestos o cargas: corren intereses y multas",
}


def cargar(ruta):
    if not ruta:
        return []
    with io.open(ruta, encoding="utf-8") as f:
        d = json.load(f)
    return [r for r in d.get("por_concepto", []) if r.get("contiene")]


def desde_cli(pares):
    """['SUIZO=25', 'FINANCIERA=10'] -> reglas."""
    out = []
    for p in pares or []:
        if "=" not in p:
            raise ValueError("Formato esperado TEXTO=DIAS, recibi: %r" % p)
        txt, dias = p.rsplit("=", 1)
        out.append({"contiene": txt.strip(), "dias_tolerancia": int(dias),
                    "_nota": "pedido por linea de comandos"})
    return out


def aplicar(egresos, reglas, permitir_graves=False):
    """Pisa la tolerancia de los egresos que matcheen. Devuelve (egresos, cambios).

    Matchea contra el CONCEPTO y contra el NOMBRE: el concepto es lo que escribió
    el administrativo ("Drogueria Suizo S.A.") y el nombre es cómo lo llama el
    catálogo ("Pago a drogueria"). Buscar en los dos evita tener que adivinar
    cuál de los dos texto usar.
    """
    if not reglas:
        return egresos, []

    cambios, out = [], []
    for e in egresos:
        texto = ((e.get("concepto") or "") + " " + (e.get("nombre") or "")).upper()
        regla = None
        for r in reglas:
            if r["contiene"].upper() in texto:
                regla = r
                break
        if regla is None:
            out.append(e)
            continue

        antes = e.get("tolerancia")
        nuevo = int(regla["dias_tolerancia"])
        grave = CONSECUENCIAS_GRAVES.get(e.get("consecuencia") or "")
        if grave and nuevo > (antes or 0) and not permitir_graves:
            raise AjusteRiesgoso(
                "'%s' no se puede estirar asi nomas: %s.\n"
                "     Si igual lo queres simular, agrega --forzar." % (
                    (e.get("concepto") or e.get("nombre"))[:50], grave))

        e = dict(e, tolerancia=nuevo, rigido=(nuevo == 0), ajustado=True)
        cambios.append({"concepto": e.get("concepto") or e.get("nombre"),
                        "antes": antes, "ahora": nuevo,
                        "importe": e.get("importe", 0.0),
                        "grave": bool(grave), "nota": regla.get("_nota", "")})
        out.append(e)

    # Un ajuste que no matchea nada casi siempre es un error de tipeo, y el
    # escenario saldria "bien" por la razon equivocada. Se avisa.
    tocadas = set()
    for c in cambios:
        for r in reglas:
            if r["contiene"].upper() in (c["concepto"] or "").upper():
                tocadas.add(r["contiene"])
    for r in reglas:
        if r["contiene"] not in tocadas:
            cambios.append({"concepto": None, "sin_efecto": r["contiene"]})
    return out, cambios


def imprimir(cambios, fmt):
    if not cambios:
        return
    reales = [c for c in cambios if c.get("concepto")]
    huerfanos = [c for c in cambios if c.get("sin_efecto")]
    if reales:
        print("  >> ESTAS ASUMIENDO (ajustes manuales, no salen del catalogo)")
        for c in reales:
            antes = "rigido" if c["antes"] == 0 else ("%s dias" % c["antes"])
            marca = "  [!]" if c["grave"] else ""
            print("     . %-30s %s -> %s dias   %s%s" % (
                (c["concepto"] or "")[:30], antes, c["ahora"], fmt(c["importe"]), marca))
            if c.get("nota"):
                print("       (%s)" % c["nota"])
    for c in huerfanos:
        print("  [!] El ajuste '%s' no matcheo ningun pago: revisa como esta escrito." % c["sin_efecto"])
    print("")
