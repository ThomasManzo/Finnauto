# -*- coding: utf-8 -*-
"""
auditoria.revisar — control de calidad del contrato ANTES de confiar en el numero.

POR QUE EXISTE
--------------
En una sola noche de mirar datos reales aparecieron 8 errores de clasificacion
(movimientos internos disfrazados, notas de credito sumando en vez de restar,
filas de saldo sumadas 200 veces, una cuota de prestamo cargada como retiro de
socios, un tipo usado como cajon de sastre...). Cada uno hacia que el motor
mintiera. Y ninguno lo encontro el sistema: los encontro una persona mirando.

Este modulo convierte esa busqueda manual en una herramienta: revisa el contrato
y lista TODO lo que no entiende o le parece sospechoso, para que un humano lo
confirme de una sola vez en vez de descubrirlo de a uno.

IMPORTANTE - ES GENERICO
------------------------
No sabe nada de ningun cliente en particular. Todas las reglas se apoyan en el
catalogo del cliente (que tipos existen, cuales son sus unidades, cuales son sus
entidades propias). Otra empresa con otro Cash y otras finanzas se audita igual,
solo cambia su catalogo.

Uso:
    python auditoria/revisar.py --contrato c.json [--cliente maga]
"""

import os
import sys
import json
import argparse
import datetime
from collections import defaultdict, Counter

BASE_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)

from simulador.semana import cargar_catalogo, cargar_contrato, meta_de, _rigido

CRITICO, REVISAR, INFO = "CRITICO", "REVISAR", "INFO"


def _m(x):
    signo = "-" if x < 0 else ""
    return signo + "$" + format(abs(round(x, 2)), ",.0f")


def _norm(s):
    return " ".join(str(s or "").upper().split())


# ============================================================ chequeos
def tipos_sin_catalogo(movs, cat, hall):
    """Un tipo que el catalogo no conoce -> el motor no sabe si es rigido."""
    conocidos = set(cat["tipos"])
    faltan = defaultdict(lambda: [0, 0.0])
    for m in movs:
        t = m.get("tipo") or ""
        if t not in conocidos:
            faltan[t or "(vacio)"][0] += 1
            faltan[t or "(vacio)"][1] += float(m.get("importe") or 0)
    for t, (n, imp) in sorted(faltan.items(), key=lambda kv: -kv[1][1]):
        hall.append((CRITICO, "Tipo desconocido en el catalogo",
                     "'%s': %d movimientos, %s. El motor no sabe si es rigido o flexible." % (t, n, _m(imp))))


def sin_concepto(movs, hall):
    """Sin concepto no se pueden aplicar las excepciones (que es donde vive el matiz)."""
    faltan = [m for m in movs if not (m.get("concepto") or "").strip()]
    if faltan:
        imp = sum(float(m.get("importe") or 0) for m in faltan)
        hall.append((REVISAR, "Movimientos sin concepto",
                     "%d movimientos (%s) no tienen concepto: no se les puede aplicar ninguna excepcion." %
                     (len(faltan), _m(imp))))


def cajon_de_sastre(movs, cat, hall):
    """Detecta un tipo que esta sirviendo de bolsa para cosas de OTRO tipo.

    Contar conceptos distintos no sirve: SUELDO tiene 93 conceptos distintos y
    esta perfecto (son nombres de empleados). La senal util es otra: que los
    conceptos de un tipo NOMBREN a otro tipo del catalogo. Si adentro de 'PAGO'
    hay conceptos que dicen "servicios", "impuesto" o "haberes", ese tipo se esta
    usando como cajon de sastre.

    Es generico: los nombres a buscar salen del catalogo del cliente.
    """
    # Vocabulario: para cada tipo, las palabras que lo delatan (su id y su nombre).
    # DOS cuidados para no llenar de falsos positivos:
    #  1) Solo palabras UNICAS de un tipo. "SUELDO" esta en SUELDO y en
    #     SUELDO_QUINTANA, asi que no distingue nada -> se descarta.
    #  2) Match por PALABRA COMPLETA, no por substring: si no, "PERSONALES" de
    #     "BIENES PERSONALES" matchea con "PERSONAL" de "Comisiones al personal".
    bruto = {}
    for tid, meta in cat["tipos"].items():
        palabras = set()
        for txt in (tid, meta.get("nombre", "")):
            for w in _norm(txt).replace("_", " ").split():
                # Palabras demasiado genericas: aparecen en cualquier concepto y
                # no distinguen nada (ej "PERSONAL" esta en "Comisiones al
                # personal" pero tambien en "BIENES PERSONALES" y en "PRESTAMO
                # PERSONAL", que no tienen nada que ver).
                if len(w) >= 5 and w not in GENERICAS:
                    palabras.add(w)
        bruto[tid] = palabras

    veces = Counter(w for ps in bruto.values() for w in ps)
    vocab = {t: {w for w in ps if veces[w] == 1} for t, ps in bruto.items()}
    vocab = {t: ps for t, ps in vocab.items() if ps}

    def _palabras(texto):
        out = set()
        for w in texto.replace("_", " ").replace("(", " ").replace(")", " ").replace(",", " ").replace("-", " ").split():
            out.add(w)
            if w.endswith("ES") and len(w) > 5:
                out.add(w[:-2])      # PERSONALES -> PERSONAL
            if w.endswith("S") and len(w) > 4:
                out.add(w[:-1])      # SERVICIOS -> SERVICIO
        return out

    por_tipo = defaultdict(list)
    for m in movs:
        por_tipo[m.get("tipo") or "(vacio)"].append(m)

    for t, items in sorted(por_tipo.items()):
        intrusos = defaultdict(lambda: [0, 0.0, []])
        for m in items:
            c = _norm(m.get("concepto"))
            if not c:
                continue
            pal_c = _palabras(c)
            for otro, palabras in vocab.items():
                if otro == t:
                    continue
                if palabras & pal_c:
                    imp = float(m.get("importe") or 0)
                    intrusos[otro][0] += 1
                    intrusos[otro][1] += imp
                    if len(intrusos[otro][2]) < 2:
                        intrusos[otro][2].append("'%s'" % c[:34])
                    break
        for otro, (n, imp, ej) in sorted(intrusos.items(), key=lambda kv: -kv[1][1]):
            if n >= 3:
                hall.append((REVISAR, "Tipo usado como cajon de sastre",
                             "Dentro de '%s' hay %d movimientos (%s) cuyo concepto habla de '%s'. "
                             "Ej: %s" % (t, n, _m(imp), otro, ", ".join(ej))))


# Palabras demasiado comunes como para identificar un tipo (ver cajon_de_sastre).
GENERICAS = {"PAGOS", "OTROS", "VARIOS", "PERSONAL", "PERSONALES", "SOCIALES",
             "TRANSFERENCIA", "TRANSFERENCIAS", "PROVEEDORES", "DIARIA", "TOTAL"}


# Palabras que indican que el concepto describe un GASTO. Si aparecen, el nombre
# de la entidad propia esta ahi como CENTRO DE COSTO (a que local se le imputa),
# no como destinatario del pago. Ej: "comisiones agosto, comp.sueldo-varela" no
# es una transferencia a Varela; es un sueldo imputado a Varela.
PALABRAS_DE_GASTO = [
    "SUELDO", "HABERES", "COMISION", "ALQUILER", "IMPUESTO", "SERVICIO",
    "HONORARIO", "CARGA", "VEP", "AFIP", "SEGURO", "ABONO", "GASTO", "COMPRA",
    "FLETE", "LIMPIEZA", "MANTENIMIENTO", "LUZ", "GAS", "AGUA", "INTERNET",
    "SINDICATO", "PEAJE", "HIGIENE", "PUBLICIDAD",
    # RRHH: tambien describen un gasto imputado a un local, no una transferencia
    "VACACIONES", "ADELANTO", "VALE", "EXTRA", "RESCISION", "INDEMNIZ",
    "PRESTAMO PERSONAL", "CONSULT", "AGUINALDO", "LICENCIA", "BONO",
]


def posibles_internos(movs, cat, propias, hall, palabras_gasto=None):
    """Un pago cuyo concepto nombra a una empresa/local DEL PROPIO GRUPO puede ser
    un movimiento interno (la plata no sale del grupo).

    OJO con el falso positivo: el nombre de un local tambien aparece cuando se
    lo usa como CENTRO DE COSTO ("comp.sueldo-varela" es un sueldo imputado a
    Varela, no una transferencia a Varela). Por eso se separan en dos niveles:
    si el concepto menciona un tipo de gasto, es centro de costo (INFO); si no,
    la entidad es probablemente el destinatario (CRITICO)."""
    if not propias:
        return
    palabras = palabras_gasto or PALABRAS_DE_GASTO
    alta = defaultdict(lambda: [0, 0.0, []])
    baja = defaultdict(lambda: [0, 0.0])
    for m in movs:
        meta = meta_de(m, cat)
        if meta.get("interno"):
            continue
        c = _norm(m.get("concepto"))
        if not c:
            continue
        for p in propias:
            if p and p in c:
                es_gasto = any(w in c for w in palabras)
                imp = float(m.get("importe") or 0)
                if es_gasto:
                    baja[p][0] += 1
                    baja[p][1] += imp
                else:
                    alta[p][0] += 1
                    alta[p][1] += imp
                    if len(alta[p][2]) < 3:
                        alta[p][2].append("%s %s '%s'" % (m.get("fecha"), _m(imp), c[:38]))
                break
    for p, (n, imp, ej) in sorted(alta.items(), key=lambda kv: -kv[1][1]):
        hall.append((CRITICO, "Posible movimiento interno NO marcado",
                     "El concepto nombra a '%s' (entidad propia) y NO describe un gasto: "
                     "%d movimientos, %s. Ej: %s" % (p, n, _m(imp), "  |  ".join(ej))))
    tot_n = sum(v[0] for v in baja.values())
    tot_i = sum(v[1] for v in baja.values())
    if tot_n:
        hall.append((INFO, "Entidades propias usadas como centro de costo",
                     "%d movimientos (%s) nombran un local propio pero describen un gasto "
                     "(sueldo, comision, alquiler...). Se interpretan como imputacion, no como interno." %
                     (tot_n, _m(tot_i))))


def concepto_en_varios_tipos(movs, hall):
    """El mismo concepto cargado bajo tipos distintos = criterio inconsistente."""
    por_concepto = defaultdict(set)
    montos = defaultdict(float)
    for m in movs:
        c = _norm(m.get("concepto"))[:40]
        if not c:
            continue
        por_concepto[c].add(m.get("tipo") or "(vacio)")
        montos[c] += float(m.get("importe") or 0)
    for c, tipos in sorted(por_concepto.items(), key=lambda kv: -montos[kv[0]]):
        if len(tipos) > 1:
            hall.append((REVISAR, "Mismo concepto en tipos distintos",
                         "'%s' aparece como %s (total %s). Uno de los dos esta mal." %
                         (c[:40], " y ".join(sorted(tipos)), _m(montos[c]))))


def montos_atipicos(movs, hall, veces=20):
    """Un movimiento muchisimo mas grande que la mediana de su tipo suele ser un
    error de carga (un cero de mas) o algo que no pertenece a ese tipo."""
    por_tipo = defaultdict(list)
    for m in movs:
        imp = float(m.get("importe") or 0)
        if imp > 0:
            por_tipo[m.get("tipo") or "(vacio)"].append((imp, m))
    for t, items in por_tipo.items():
        if len(items) < 8:
            continue
        vals = sorted(i[0] for i in items)
        mediana = vals[len(vals) // 2]
        if mediana <= 0:
            continue
        for imp, m in sorted(items, key=lambda x: -x[0])[:3]:
            if imp > mediana * veces:
                hall.append((REVISAR, "Monto atipico para su tipo",
                             "%s de %s el %s (%s) es %.0fx la mediana del tipo (%s)." %
                             (t, _m(imp), m.get("fecha"), (m.get("concepto") or "")[:30],
                              imp / mediana, _m(mediana))))


def duplicados(movs, hall):
    """Misma fecha, tipo, importe y concepto: puede ser doble carga."""
    vistos = Counter()
    for m in movs:
        k = (m.get("fecha"), m.get("tipo"), round(float(m.get("importe") or 0), 2),
             _norm(m.get("concepto"))[:30])
        vistos[k] += 1
    for (f, t, imp, c), n in sorted(vistos.items(), key=lambda kv: -kv[1]):
        if n > 1 and imp > 0:
            hall.append((INFO, "Posible carga duplicada",
                         "%d veces: %s %s %s '%s'. Puede ser legitimo (varias cuotas iguales)." %
                         (n, f, t, _m(imp), c[:30])))


def fechas_raras(movs, hall):
    hoy = datetime.date.today()
    lim_pasado = (hoy - datetime.timedelta(days=730)).isoformat()
    lim_futuro = (hoy + datetime.timedelta(days=730)).isoformat()
    viejos = [m for m in movs if m.get("fecha") and m["fecha"] < lim_pasado]
    lejos = [m for m in movs if m.get("fecha") and m["fecha"] > lim_futuro]
    sinf = [m for m in movs if not m.get("fecha")]
    if viejos:
        hall.append((INFO, "Movimientos muy viejos", "%d anteriores a %s." % (len(viejos), lim_pasado)))
    if lejos:
        hall.append((REVISAR, "Movimientos muy a futuro", "%d posteriores a %s." % (len(lejos), lim_futuro)))
    if sinf:
        hall.append((CRITICO, "Movimientos sin fecha",
                     "%d movimientos sin fecha: quedan afuera de cualquier escenario." % len(sinf)))


def importes_invalidos(movs, hall):
    cero = [m for m in movs if float(m.get("importe") or 0) == 0]
    neg = [m for m in movs if float(m.get("importe") or 0) < 0]
    if cero:
        hall.append((INFO, "Importes en cero", "%d movimientos con importe 0." % len(cero)))
    if neg:
        imp = sum(float(m.get("importe") or 0) for m in neg)
        hall.append((REVISAR, "Importes negativos en egresos",
                     "%d movimientos negativos (%s). En una tabla de egresos un negativo suele ser "
                     "una devolucion o un error de signo." % (len(neg), _m(imp))))


def cobertura_ingresos(contrato, hall):
    cob = contrato.get("cobros_previstos", [])
    if not cob:
        hall.append((CRITICO, "Sin ingresos previstos",
                     "El contrato no trae cobros previstos: el escenario solo veria egresos."))
        return
    sin_nat = [c for c in cob if not c.get("naturaleza")]
    if sin_nat:
        hall.append((REVISAR, "Ingresos sin naturaleza",
                     "%d cobros sin FIJO/VARIABLE: el escenario conservador no sabe si contarlos." % len(sin_nat)))


# ============================================================ resumen
def margen_de_maniobra(movs, cat, desde, hasta):
    rig = flex = inte = 0.0
    for m in movs:
        f = m.get("fecha")
        if not f or f < desde or f > hasta:
            continue
        meta = meta_de(m, cat)
        imp = float(m.get("importe") or 0)
        if meta.get("interno"):
            inte += imp
        elif _rigido(meta):
            rig += imp
        else:
            flex += imp
    return rig, flex, inte


# ============================================================ main
# ===========================================================================
# CHEQUEOS DE COMPLETITUD
#
# Todos salen de errores REALES encontrados el 05/09/2026 en el Cash de MAGA.
# Ninguno tiraba una excepcion: el contrato salia prolijo con la mitad de los
# datos afuera, y eso es lo peor que puede pasar. Thomas lo puso asi: "no
# importa arreglar errores, el tema es que esos errores sirvan para las demas
# empresas".
#
# La forma de todos es la misma: comparar dos cosas que TIENEN que cuadrar. Si
# no cuadran, falta un pedazo, aunque nadie haya fallado.
# ===========================================================================

def _suma(filas, filtro=None):
    return sum(abs(float(x.get("importe") or 0)) for x in (filas or [])
               if filtro is None or filtro(x))


def _unidades(filas):
    return set((x.get("unidad") or "").strip() for x in (filas or [])
               if (x.get("unidad") or "").strip())


def completitud(contrato):
    """Los chequeos que detectan datos faltantes. Devuelve lista de hallazgos."""
    out = []
    mov = contrato.get("movimientos", [])
    cob = contrato.get("cobros_previstos", [])
    deuda = contrato.get("deuda_droguerias", [])
    cobrar = contrato.get("cuentas_a_cobrar_droguerias", [])
    por_unidad = contrato.get("caja_por_unidad") or {}

    # --- 1) UNA UNIDAD QUE TIENE CAJA PERO NO TIENE DATOS ---------------
    # El caso MAGA: la caja mostraba SPEEDMED y MAGA, y la deuda venia solo de
    # SPEEDMED porque la hoja de MAGA se salteaba en silencio. Faltaba el 51%.
    if por_unidad:
        con_caja = set(k.strip().upper() for k in por_unidad if por_unidad[k])
        for nombre, filas in (("movimientos", mov), ("cobros previstos", cob),
                              ("deuda con droguerias", deuda),
                              ("cuentas a cobrar", cobrar)):
            if not filas:
                continue
            presentes = set(u.upper() for u in _unidades(filas))
            if not presentes:
                continue
            faltan = con_caja - presentes
            if faltan:
                out.append(("FALTA UNA UNIDAD",
                            "%s: hay caja de %s pero ningun dato de %s. "
                            "Casi siempre significa que una hoja no se esta "
                            "leyendo." % (nombre, ", ".join(sorted(con_caja)),
                                          ", ".join(sorted(faltan)))))

    # --- 2) UN BLOQUE QUE TERMINA ANTES QUE LOS DEMAS -------------------
    # El caso deuda: llegaba al 25/09 mientras el resto llegaba al 16/10. Sumarlo
    # como "la deuda" daba la mitad, y el informe decia que sobraba plata.
    topes = {}
    for nombre, filas in (("movimientos", mov), ("cobros previstos", cob),
                          ("deuda con droguerias", deuda),
                          ("cuentas a cobrar", cobrar)):
        f = [x.get("fecha") for x in (filas or []) if x.get("fecha")]
        if f:
            topes[nombre] = max(f)
    if len(topes) > 1:
        mas_lejos = max(topes.values())
        for nombre, tope in sorted(topes.items()):
            dias = (datetime.date.fromisoformat(mas_lejos) -
                    datetime.date.fromisoformat(tope)).days
            if dias > 15:
                out.append(("BLOQUE CORTO",
                            "%s llega hasta %s, pero otros datos llegan hasta "
                            "%s (%d dias mas). Si se proyecta ese periodo, este "
                            "bloque va a quedar corto." % (nombre, tope,
                                                           mas_lejos, dias)))

    # --- 3) LOS DOS LADOS NO SON COMPARABLES ---------------------------
    # Entra 2,5 veces lo que sale. Puede estar bien (compras que se cancelan por
    # fuera de la caja) o puede faltar la mitad de los gastos. Se pregunta.
    ti, te = _suma(cob), _suma(mov)
    if ti and te:
        if ti / te > 2.0:
            out.append(("LADOS DESPAREJOS",
                        "Entra %.1f veces lo que sale. Preguntar si hay compras "
                        "que se cancelan sin pasar por el banco (notas de "
                        "credito, endoso de cheques, compensacion) o si faltan "
                        "gastos por cargar." % (ti / te)))
        elif te / ti > 2.0:
            out.append(("LADOS DESPAREJOS",
                        "Sale %.1f veces lo que entra. O faltan ingresos por "
                        "cargar, o la empresa se financia con algo que no "
                        "figura." % (te / ti)))

    # --- 4) MOVIMIENTOS SIN CATEGORIA ----------------------------------
    # Sin tipo el motor no los puede modelar: no entran en ninguna proyeccion.
    sin_tipo = [x for x in mov if not (x.get("tipo") or "").strip()]
    if sin_tipo:
        imp = _suma(sin_tipo)
        pct = 100.0 * imp / te if te else 0
        out.append(("SIN CATEGORIA",
                    "%d movimiento(s) sin tipo, por %s (%.0f%% de los egresos). "
                    "El motor no los puede clasificar ni proyectar."
                    % (len(sin_tipo), _m(imp), pct)))

    # --- 5) UN BLOQUE VACIO QUE DEBERIA TENER ALGO ---------------------
    # Si hay cuentas a cobrar pero cero deuda (o al reves), suele ser que uno de
    # los dos bloques no se encontro, no que la empresa no deba nada.
    if cobrar and not deuda:
        out.append(("BLOQUE VACIO",
                    "Hay %d fila(s) de cuentas a cobrar pero NINGUNA de deuda. "
                    "Es raro: revisar que el bloque de deuda se este leyendo."
                    % len(cobrar)))
    if deuda and not cobrar:
        out.append(("BLOQUE VACIO",
                    "Hay %d fila(s) de deuda pero NINGUNA de cuentas a cobrar. "
                    "Revisar que ese bloque se este leyendo." % len(deuda)))

    # --- 6) LOS AVISOS DEL PROPIO EXPORT --------------------------------
    # Viajan en el contrato y nadie los miraba. Si el export tuvo algo para
    # decir, la auditoria lo repite.
    for a in (contrato.get("avisos") or []):
        if "OJO" in a.upper() or "NO ENCONTRE" in a.upper() or "FALTA" in a.upper():
            out.append(("AVISO DEL EXPORT", a))

    return out


def imprimir_completitud(hallazgos):
    L = 74
    print("=" * L)
    print("  COMPLETITUD DE LOS DATOS")
    print("=" * L)
    if not hallazgos:
        print("  Nada que reportar: los bloques cierran entre si.\n")
        return
    print("  Estos no son errores de calculo: son datos que FALTAN. Ninguno")
    print("  hace fallar nada, y por eso son los que mas caro salen.\n")
    for tipo, texto in hallazgos:
        linea = "  [%s] " % tipo
        for palabra in texto.split():
            if len(linea) + len(palabra) + 1 > L - 2:
                print(linea)
                linea = "      "
            linea += palabra + " "
        print(linea.rstrip())
        print("")


def main():
    ap = argparse.ArgumentParser(description="Auditoria de calidad del contrato")
    ap.add_argument("--contrato", required=True)
    ap.add_argument("--cliente", default="maga")
    ap.add_argument("--desde")
    ap.add_argument("--dias", type=int, default=30)
    args = ap.parse_args()

    cat = cargar_catalogo(args.cliente)
    contrato = cargar_contrato(args.contrato)
    movs = contrato.get("movimientos", [])

    # entidades propias del cliente (para detectar internos). Sale del catalogo.
    ruta = os.path.join(BASE_REPO, "clientes", args.cliente, "catalogo.json")
    with open(ruta, "r", encoding="utf-8") as f:
        raw = json.load(f)
    propias = [_norm(x) for x in raw.get("entidades_propias", {}).get("valores", [])]
    for u in raw.get("unidades", {}).get("valores", []):
        propias.append(_norm(u.get("id")))
        propias.append(_norm(u.get("nombre")))
    propias = sorted(set(p for p in propias if p and len(p) > 3))

    # La completitud va PRIMERO. Si faltan datos, todo lo que venga despues
    # opina sobre una foto incompleta -- que fue exactamente lo que paso el
    # 05/09: el motor analizaba con la mitad de la deuda afuera.
    imprimir_completitud(completitud(contrato))

    hall = []
    tipos_sin_catalogo(movs, cat, hall)
    sin_concepto(movs, hall)
    cajon_de_sastre(movs, cat, hall)
    posibles_internos(movs, cat, propias, hall)
    concepto_en_varios_tipos(movs, hall)
    montos_atipicos(movs, hall)
    duplicados(movs, hall)
    fechas_raras(movs, hall)
    importes_invalidos(movs, hall)
    cobertura_ingresos(contrato, hall)

    # ---- reporte ----
    L = 78
    print("=" * L)
    print("  AUDITORIA DEL CONTRATO  -  %s" % contrato.get("cliente", args.cliente))
    print("=" * L)
    print("  Movimientos: %d  |  Cobros previstos: %d  |  Deuda: %d" % (
        len(movs), len(contrato.get("cobros_previstos", [])), len(contrato.get("deuda_droguerias", []))))

    desde = args.desde or datetime.date.today().isoformat()
    hasta = (datetime.date.fromisoformat(desde) + datetime.timedelta(days=args.dias)).isoformat()
    rig, flex, inte = margen_de_maniobra(movs, cat, desde, hasta)
    tot = rig + flex
    print("\n  MARGEN DE MANIOBRA (%s a %s)" % (desde, hasta))
    print("    Rigido  : %18s" % _m(rig))
    print("    Flexible: %18s   %s de los egresos" % (
        _m(flex), ("%.1f%%" % (100 * flex / tot)) if tot else "-"))
    print("    Interno : %18s   (no es gasto)" % _m(inte))
    if tot and (flex / tot) < 0.15:
        print("    -> Muy poco margen: postergar pagos casi no mueve la aguja.")
        print("       Las palancas reales son los cobros y la financiacion.")

    for sev in (CRITICO, REVISAR, INFO):
        items = [h for h in hall if h[0] == sev]
        if not items:
            continue
        print("\n" + "-" * L)
        print("  [%s]  %d hallazgo(s)" % (sev, len(items)))
        print("-" * L)
        for _, titulo, det in items[:25]:
            print("  * %s" % titulo)
            print("      %s" % det)
        if len(items) > 25:
            print("  ... y %d mas." % (len(items) - 25))

    if not hall:
        print("\n  [OK] Sin hallazgos. El contrato se ve consistente.")
    else:
        print("\n" + "=" * L)
        print("  TOTAL: %d hallazgos (%d criticos)." % (
            len(hall), len([h for h in hall if h[0] == CRITICO])))
        print("  Los CRITICOS afectan el numero: conviene resolverlos antes de confiar en el escenario.")


if __name__ == "__main__":
    main()
