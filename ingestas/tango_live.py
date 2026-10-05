# -*- coding: utf-8 -*-
"""
ingestas.tango_live — baja las consultas de Tango Live por API y deja Excel con el
mismo contrato que los exports manuales que ya leen lector/tango.py y
lector/tesoreria_aa.py.

Cada empresa y proceso tiene una consulta personalizada de Live con las mismas
columnas del export manual. La API igual usa nombres como NRO_COMPROBANTE y
códigos de estado: acá se traducen antes de escribir. Las columnas que no tienen
una equivalencia comprobada se conservan, al final, con su nombre original.

La llamada comprobada contra Tango es:
    GET <url>/Api/GetApiLiveQueryData?process=...&fromDate=DD/MM/AAAA&...
    headers: ApiAuthorization: <token> · Company: <id>

USO
    python ingestas/tango_live.py --cliente navar
    python ingestas/tango_live.py --cliente navar --probar cobranzas --empresa A
    python ingestas/tango_live.py --cliente navar --simular
    python ingestas/tango_live.py --cliente navar --destino <carpeta local>
"""

import os
import sys
import json
import datetime
import argparse
import urllib.request
import urllib.error
import urllib.parse
from collections import Counter, OrderedDict

# En Windows la tarea corre sin terminal y guarda el texto en un log. UTF-8 evita
# que una flecha o un acento haga fallar una descarga que ya terminó bien.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)

from nucleo import credenciales as _cred
from ingestas.drive_local import carpeta_datos

# Dónde va cada consulta y cómo se llama el archivo. Tesorería se resuelve aparte
# porque en instalaciones viejas puede existir con tilde; el nombre oficial es sin tilde.
DESTINO = {
    "cobranzas": ("Cuentas a cobrar", "%s cobranzas %s.xlsx"),
    "pagos": ("Cuentas a pagar", "%s pagos %s.xlsx"),
    "cheques_terceros": ("Cheques", "%s cheques terceros %s.xlsx"),
    "cheques_propios": ("Cheques", "%s cheques propios %s.xlsx"),
    "movimientos_tesoreria": ("Tesoreria AA", "%s movimientos tesoreria %s.xlsx"),
    # Detalle de comprobantes de tesorería (un renglón por cuenta imputada): lo usa el cruce
    # banco ↔ Tango (lector/cruce.py) para saber por qué cuenta de banco entró o salió cada peso.
    # Carpeta propia: no se mezcla con "Tesoreria A", que es otra consulta (un renglón por comprobante).
    "detalle_tesoreria": ("Tesoreria A detalle", "%s tesoreria detalle %s.xlsx"),
}
# Consultas que existen solo para la empresa A (AA no tiene cheques propios ni bancos).
SOLO_A = {"cheques_propios", "detalle_tesoreria"}
PAGINA = 5000
TIMEOUT_PAGINA = 300
# El circuito diario tiene seis fotos de A y cuatro de AA. Si una configuración
# queda incompleta, el parte debe mostrar que faltó algo en vez de decir 6 de 6.
# Tiene que coincidir con TANGO_BAJADAS de clientes/navar/herramientas/aviso_diario.gs.
TOTAL_BAJADAS_DIARIAS = 10

# Qué encabezado manual corresponde a cada campo comprobado de la API. El orden
# es el orden útil del export manual; todo campo no listado se agrega después sin
# cambiarle el nombre. Un mismo código puede producir texto + código visible.
COLUMNAS_EXPORT = {
    "cobranzas": [
        ("Cód. cliente", "COD_CLIENTE", "crudo"),
        ("Razón social", "RAZON_SOCIAL", "crudo"),
        ("Tipo comprobante", "TIPO_COMPROBANTE", "crudo"),
        ("Nro. comprobante", "NRO_COMPROBANTE", "crudo"),
        ("Fecha de emisión", "FECHA_DE_EMISION", "crudo"),
        ("Fecha de vencimiento", "FECHA_DE_VENCIMIENTO", "crudo"),
        ("Importe al Vencimiento (CTE)", "IMPORTE_AL_VENCIMIENTO_CTE", "crudo"),
        ("Importe Pendiente (CTE)", "IMPORTE_PENDIENTE_CTE", "crudo"),
        ("Descripción condición de venta", "DESCRIPCION_CONDICION_DE_VENTA", "crudo"),
    ],
    "pagos": [
        ("Cód. proveedor", "COD_PROVEEDOR", "crudo"),
        ("Razón social", "RAZON_SOCIAL", "crudo"),
        ("Tipo de comprobante", "TIPO_DE_COMPROBANTE", "crudo"),
        ("Nro. comprobante", "NRO_COMPROBANTE", "crudo"),
        ("Fecha de emisión", "FECHA_DE_EMISION", "crudo"),
        ("Fecha de vencimiento", "FECHA_DE_VENCIMIENTO", "crudo"),
        ("Total al vencimiento (CTE)", "TOTAL_AL_VENCIMIENTO_CTE", "crudo"),
        ("Total pendiente (CTE)", "TOTAL_PENDIENTE_CTE", "crudo"),
    ],
    "cheques_terceros": [
        ("Nro. de cheque", "NRO_DE_CHEQUE", "crudo"),
        ("Banco", "BANCO", "crudo"),
        ("Cód. cliente", "COD_CLIENTE", "crudo"),
        ("Cliente", "CLIENTE", "crudo"),
        ("Fecha del cheque", "FECHA_DEL_CHEQUE", "crudo"),
        ("Importe (CTE)", "IMPORTE_CTE", "crudo"),
        ("Estado", "ESTADO", "estado_terceros"),
        ("Subestado", "SUBESTADO", "crudo"),
        ("Desc. subestado", "DESC_SUBESTADO", "crudo"),
        ("Cód. estado", "COD_ESTADO", "codigo"),
        ("Origen", "ORIGEN", "crudo"),
    ],
    "cheques_propios": [
        ("Nro. de cheque", "NRO_DE_CHEQUE", "crudo"),
        ("Banco", "BANCO", "crudo"),
        ("Cód. proveedor", "COD_PROVEEDOR", "crudo"),
        ("Razón social", "RAZON_SOCIAL", "crudo"),
        ("Fecha de emisión", "FECHA_DE_EMISION", "crudo"),
        ("Fecha del cheque", "FECHA_DEL_CHEQUE", "crudo"),
        ("Importe mon. cta.", "IMPORTE", "crudo"),
        ("Estado", "ESTADO", "estado_propios"),
        ("Cód. estado", "ESTADO", "codigo"),
        ("Cuenta emisión", "CUENTA_EMISION", "crudo"),
    ],
    "movimientos_tesoreria": [
        ("Tipo", "TIPO", "crudo"),
        ("Comprobante", "COMPROBANTE", "crudo"),
        ("Fecha", "FECHA", "crudo"),
        ("Fecha de emisión", "FECHA_DE_EMISION", "crudo"),
        ("Concepto", "CONCEPTO", "crudo"),
        ("Clase", "CLASE", "clase_tesoreria"),
        ("Total (cte)", "TOTAL_CTE", "crudo"),
        ("Cód. relacionado", "COD_RELACIONADO", "crudo"),
        ("Desc. relacionado", "DESC_RELACIONADO", "crudo"),
        ("Clasificación", "CLASIFICACION", "crudo"),
    ],
}

# Columnas del detalle de tesorería, con los nombres del export manual que lee lector/cruce.py.
COLUMNAS_EXPORT["detalle_tesoreria"] = [
    ("Fecha de emisión", "FECHA_DE_EMISION", "crudo"),
    ("Cód. comprobante", "COD_COMPROBANTE", "crudo"),
    ("Desc. comprobante", "DESC_COMPROBANTE", "crudo"),
    ("Comprobante", "COMPROBANTE", "crudo"),
    ("Nro. interno", "NRO_INTERNO", "crudo"),
    ("Renglón", "RENGLON", "crudo"),
    ("Cód. cuenta", "COD_CUENTA", "crudo"),
    ("Desc. contable", "DESC_CONTABLE", "crudo"),
    ("Desc. cuenta", "DESC_CUENTA", "crudo"),
    ("Banco", "BANCO", "crudo"),
    ("Debe (cte) (renglón)", "DEBE_CTE_RENGLON", "crudo"),
    ("Haber (cte) (renglón)", "HABER_CTE_RENGLON", "crudo"),
    ("Total comp. (cte)", "TOTAL_COMP_CTE", "crudo"),
    ("CUIT cliente (encab.)", "CUIT_ENCAB", "crudo"),
    ("CUIT proveedor (encab.)", "CUIT_PROVEEDOR_ENCAB", "crudo"),
    ("Razón social (encab.)", "RAZON_SOCIAL_ENCAB", "crudo"),
    ("Proveedor (encab.)", "PROVEEDOR_ENCAB", "crudo"),
    ("Leyenda", "LEYENDA", "crudo"),
]
# Sin estas el cruce no puede trabajar: si Live deja de mandarlas, no se publica el archivo.
DETALLE_OBLIGATORIAS = ("Fecha de emisión", "Cód. comprobante", "Cód. cuenta",
                        "Debe (cte) (renglón)", "Haber (cte) (renglón)")

TRADUCCIONES = {
    "estado_terceros": {"C": "En Cartera", "A": "Aplicado", "R": "Rechazado"},
    "estado_propios": {"E": "Al Cobro"},
    "clase_tesoreria": {
        "1": "Cobros",
        "2": "Pagos",
        "4": "Otros movimientos de bancos y carteras",
        "6": "Rechazo de cheques de terceros",
    },
}

CAMPO_CODIGO = {
    "cheques_terceros": ("COD_ESTADO", "estado_terceros"),
    "cheques_propios": ("ESTADO", "estado_propios"),
    "movimientos_tesoreria": ("CLASE", "clase_tesoreria"),
}


def log(msg):
    print("%s  %s" % (datetime.datetime.now().strftime("%H:%M:%S"), msg))


def perfil(cliente):
    with open(os.path.join(BASE_REPO, "clientes", cliente, "perfil.json"), encoding="utf-8") as f:
        p = json.load(f)
    cfg = p.get("tango_live")
    if not cfg:
        sys.exit("perfil.json no tiene la sección 'tango_live'")
    return cfg


def token(cliente):
    _, tok = _cred.cargar(BASE_REPO, cliente, "tango_live")
    return tok


def rango_fechas(cfg, hoy, consulta, empresa="AA"):
    """Propios y tesorería de A tienen ventana; AA conserva toda su historia."""
    clave = consulta
    if consulta == "movimientos_tesoreria" and empresa == "A":
        clave = "movimientos_tesoreria_A"
    elif consulta not in ("cheques_propios", "detalle_tesoreria"):
        return "", ""
    try:
        dias = int(cfg.get("dias_atras", {}).get(clave))
    except (TypeError, ValueError):
        raise RuntimeError("falta dias_atras.%s válido en perfil.json" % clave)
    if dias <= 0:
        raise RuntimeError("dias_atras.%s debe ser mayor que cero" % clave)
    return (hoy - datetime.timedelta(days=dias)).strftime("%d/%m/%Y"), ""


def consulta_personalizada(cfg, empresa, consulta):
    valor = cfg.get("consultas_personalizadas", {}).get(empresa, {}).get(consulta)
    if valor in (None, ""):
        raise RuntimeError(
            "falta la consulta personalizada en perfil.json para %s %s"
            % (empresa, consulta))
    return valor


def armar_url(cfg, empresa, consulta, proceso, desde, hasta, pagina=0, tam=PAGINA):
    """Arma la API real y exige la vista personalizada de esa empresa/lista."""
    parametros = [
        ("process", proceso),
        ("fromDate", desde),
        ("toDate", hasta),
        ("pageSize", tam),
        ("pageIndex", pagina),
        ("customQuery", consulta_personalizada(cfg, empresa, consulta)),
    ]
    return "%s/Api/GetApiLiveQueryData?%s" % (
        cfg["url"].rstrip("/"), urllib.parse.urlencode(parametros))


def llamar(cfg, tok, empresa, consulta, proceso, desde, hasta, pagina=0, tam=PAGINA):
    url = armar_url(cfg, empresa, consulta, proceso, desde, hasta, pagina, tam)
    req = urllib.request.Request(url, headers={
        "ApiAuthorization": tok,
        "Company": str(cfg["empresas"][empresa]),
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_PAGINA) as r:
            cuerpo = r.read().decode("utf-8", errors="replace")
            return r.status, url, cuerpo
    except urllib.error.HTTPError as e:
        return e.code, url, e.read().decode("utf-8", errors="replace")


def _respuesta(cuerpo, url):
    """Valida la envoltura comprobada de Live y devuelve los datos de una página."""
    try:
        j = json.loads(cuerpo)
    except (TypeError, ValueError):
        muestra = str(cuerpo or "")[:160].replace("\n", " ")
        if "iniciando" in muestra.lower() or "<html" in muestra.lower():
            raise RuntimeError(
                "Live devolvió HTML ('Iniciando...'): la dirección no es la de la API; "
                "debe usar /Api/GetApiLiveQueryData con parámetros después de '?'")
        raise RuntimeError("Live no devolvió JSON en %s: %s" % (url, muestra))
    if not isinstance(j, dict):
        raise RuntimeError("Live devolvió JSON, pero no el objeto esperado en %s" % url)
    if j.get("exceptionInfo"):
        raise RuntimeError("Live informó exceptionInfo en %s: %s" % (url, j.get("exceptionInfo")))
    if j.get("succeeded") is not True:
        raise RuntimeError("Live respondió succeeded=false en %s: %s" % (
            url, j.get("message") or "sin detalle"))
    datos = j.get("resultData")
    if not isinstance(datos, dict) or not isinstance(datos.get("list"), list):
        raise RuntimeError("Live no trajo resultData.list en %s" % url)
    if not all(isinstance(f, dict) for f in datos["list"]):
        raise RuntimeError("Live trajo una fila que no es un objeto en %s" % url)
    try:
        total = int(datos["totalCount"])
    except (KeyError, TypeError, ValueError):
        raise RuntimeError("Live no trajo un totalCount válido en %s" % url)
    return {
        "filas": datos["list"],
        "total": total,
        "sigue": datos.get("hasNextPage") is True,
        "pagina": datos.get("pageIndex"),
    }


def bajar(cfg, tok, empresa, consulta, proceso, desde, hasta):
    """Trae todas las páginas y no entrega una foto si no cierra con totalCount."""
    filas = []
    pagina = 0
    total_esperado = None
    while True:
        st, url, cuerpo = llamar(
            cfg, tok, empresa, consulta, proceso, desde, hasta, pagina, PAGINA)
        if st != 200:
            raise RuntimeError("Live devolvió HTTP %s en %s: %s" % (st, url, cuerpo[:300]))
        datos = _respuesta(cuerpo, url)
        if total_esperado is None:
            total_esperado = datos["total"]
        elif datos["total"] != total_esperado:
            raise RuntimeError("totalCount cambió durante la paginación: %d → %d" % (
                total_esperado, datos["total"]))
        filas.extend(datos["filas"])
        if not datos["sigue"]:
            break
        if not datos["filas"]:
            raise RuntimeError("Live dice que hay otra página, pero la página %d vino vacía" % pagina)
        pagina += 1
    if len(filas) != (total_esperado or 0):
        raise RuntimeError(
            "descarga incompleta: junté %d filas y Live informó totalCount=%d; no se escribe el archivo"
            % (len(filas), total_esperado or 0))
    return filas


def _codigo(v):
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v if v is not None else "").strip().upper()


def _traducir_codigo(v, tipo):
    codigo = _codigo(v)
    if codigo in TRADUCCIONES[tipo]:
        return TRADUCCIONES[tipo][codigo]
    return "(código %s sin traducir)" % (codigo or "vacío")


def _columnas_api(filas):
    columnas = []
    for fila in filas:
        for clave in fila:
            if clave not in columnas:
                columnas.append(clave)
    return columnas


def traducir_filas(consulta, filas):
    """Pone encabezados de export manual y conserva al final lo no equivalente."""
    if consulta not in COLUMNAS_EXPORT:
        raise KeyError("consulta sin traducción: %s" % consulta)
    api = _columnas_api(filas)
    especificacion = COLUMNAS_EXPORT[consulta]
    consumidas = {origen for _, origen, _ in especificacion}
    columnas = [destino for destino, origen, _ in especificacion if origen in api]
    columnas += [c for c in api if c not in consumidas]
    salida = []
    for original in filas:
        nueva = OrderedDict()
        for destino, origen, transformacion in especificacion:
            if origen not in api:
                continue
            valor = original.get(origen)
            if transformacion == "codigo":
                valor = _codigo(valor)
            elif transformacion in TRADUCCIONES:
                valor = _traducir_codigo(valor, transformacion)
            nueva[destino] = valor
        for columna in api:
            if columna not in consumidas:
                nueva[columna] = original.get(columna)
        salida.append(nueva)
    return salida, columnas


def conteo_codigos(consulta, empresa, filas):
    if consulta not in CAMPO_CODIGO:
        return None
    campo, tipo = CAMPO_CODIGO[consulta]
    conteo = Counter(_codigo(f.get(campo)) for f in filas)
    partes = []
    for codigo in sorted(conteo):
        partes.append("%s→%s %s" % (
            codigo or "vacío",
            _traducir_codigo(codigo, tipo),
            format(conteo[codigo], ",d").replace(",", "."),
        ))
    return "%s %s: %s" % (consulta.replace("_", " "), empresa, " · ".join(partes) or "sin filas")


def validar_tesoreria(filas, empresa="AA"):
    """La relación Tipo/Clase detecta si Live cambió la traducción ya confirmada."""
    # En A algunos recibos y órdenes son movimientos entre bancos/carteras:
    # se pueden exportar, pero el lector de últimos pagos no los toma como pagos.
    esperado = {
        "REC": ("Cobros", "Otros movimientos de bancos y carteras"),
        "O/P": ("Pagos",),
        "OPF": ("Pagos", "Otros movimientos de bancos y carteras"),
        "FPR": ("Pagos",),
        "EXT": ("Otros movimientos de bancos y carteras",),
        "RCT": ("Rechazo de cheques de terceros",),
    }
    pares = Counter((str(f.get("Tipo") or "").strip().upper(), str(f.get("Clase") or "").strip())
                    for f in filas)
    texto = " · ".join("%s→%s %s" % (t or "vacío", c or "vacío", n)
                       for (t, c), n in sorted(pares.items())) or "sin filas"
    malos = [(t, c, " o ".join(esperado[t])) for (t, c) in pares
             if t in esperado and c not in esperado[t]]
    if malos:
        detalle = "; ".join("%s vino como '%s' y debía ser '%s'" % x for x in malos)
        raise RuntimeError(
            "Tesorería tiene Tipo/Clase incompatibles (%s). Conteo: %s. No se escribe el archivo"
            % (detalle, texto))
    return "tesorería %s pares Tipo/Clase: " % empresa + texto


def preparar_filas(consulta, empresa, filas):
    """Traduce, controla y aplica el único filtro previo: terceros en cartera."""
    linea_codigos = conteo_codigos(consulta, empresa, filas)
    traducidas, columnas = traducir_filas(consulta, filas)
    linea_pares = None
    if consulta == "movimientos_tesoreria":
        linea_pares = validar_tesoreria(traducidas, empresa)
        # El lector viejo toma cualquier clase desconocida como "Otros". Como no
        # podemos tocarlo en esta tarea, la dejamos visible en el conteo pero no
        # la publicamos: sería adivinar una categoría de caja.
        traducidas = [f for f in traducidas
                      if not str(f.get("Clase") or "").startswith("(código ")]
    if consulta == "cheques_terceros":
        traducidas = [f for f in traducidas if _codigo(f.get("Cód. estado")) == "C"]
    if consulta == "detalle_tesoreria" and filas:
        faltan = [c for c in DETALLE_OBLIGATORIAS if c not in columnas]
        if faltan:
            raise RuntimeError(
                "al detalle de tesorería le faltan columnas que usa el cruce (%s): ¿alguien editó la "
                "consulta personalizada en Live? No se escribe el archivo" % ", ".join(faltan))
    return traducidas, columnas, linea_codigos, linea_pares


def _valor_excel(v):
    if isinstance(v, str) and len(v) >= 10 and v[4:5] == "-" and v[7:8] == "-":
        try:
            return datetime.datetime.fromisoformat(v[:19])
        except ValueError:
            return v
    return v


def escribir_xlsx(filas, ruta, columnas=None):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    columnas = list(columnas or _columnas_api(filas))
    ws.append(columnas or ["(sin filas)"])
    for fila in filas:
        ws.append([_valor_excel(fila.get(c)) for c in columnas])
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    tmp = ruta + ".parte.xlsx"
    try:
        wb.save(tmp)
        os.replace(tmp, ruta)  # aparece entero: el vigilante nunca ve media descarga
    finally:
        wb.close()
        if os.path.exists(tmp):
            os.unlink(tmp)


def bajar_y_escribir(cfg, tok, empresa, consulta, proceso, ruta, desde, hasta):
    """Unidad atómica: sólo escribe después de bajar, cerrar y controlar todo."""
    originales = bajar(cfg, tok, empresa, consulta, proceso, desde, hasta)
    filas, columnas, linea_codigos, linea_pares = preparar_filas(consulta, empresa, originales)
    if linea_codigos:
        log(linea_codigos)
    if linea_pares:
        log(linea_pares)
    escribir_xlsx(filas, ruta, columnas)
    return len(originales), len(filas)


def carpeta_consulta(raiz, consulta, empresa="AA"):
    if consulta != "movimientos_tesoreria":
        return os.path.join(raiz, DESTINO[consulta][0])
    if empresa == "A":
        return os.path.join(raiz, "Tesoreria A")
    sin_tilde = os.path.join(raiz, "Tesoreria AA")
    con_tilde = os.path.join(raiz, "Tesorería AA")
    if os.path.isdir(sin_tilde):
        return sin_tilde
    if os.path.isdir(con_tilde):
        return con_tilde
    return sin_tilde


def _resumir_error_parte(error, tok):
    """Deja sólo un motivo corto; nunca copia el token ni filas descargadas."""
    texto = " ".join(str(error or "sin detalle").split())
    if tok:
        texto = texto.replace(str(tok), "[token oculto]")
    return texto[:150]


def _escribir_parte_tango(raiz, ok, total, fallas, tok="", ahora=None):
    """Publica de una vez el resultado que leerá el aviso de las 09:00."""
    carpeta = os.path.join(raiz, "_para la Sheet")
    os.makedirs(carpeta, exist_ok=True)
    destino = os.path.join(carpeta, "tango_ultima_bajada.txt")
    temporal = os.path.join(carpeta, ".tango_ultima_bajada.%d.tmp" % os.getpid())
    marca = ahora or datetime.datetime.now(datetime.timezone.utc)
    if marca.tzinfo is None:
        marca = marca.replace(tzinfo=datetime.timezone.utc)
    marca = marca.astimezone(datetime.timezone.utc).replace(microsecond=0)
    lineas = [marca.isoformat(), "%d de %d" % (ok, total)]
    for nombre, error in fallas:
        lineas.append("%s: %s" % (nombre, _resumir_error_parte(error, tok)))
    try:
        with open(temporal, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lineas) + "\n")
        os.replace(temporal, destino)
    finally:
        if os.path.exists(temporal):
            os.unlink(temporal)


def _bajada_completa_hoy(raiz, hoy):
    """Sólo evitamos la bajada cuando el parte confirma todas las fotos del día."""
    ruta = os.path.join(raiz, "_para la Sheet", "tango_ultima_bajada.txt")
    try:
        with open(ruta, encoding="utf-8") as f:
            lineas = f.read().splitlines()
        marca = datetime.datetime.fromisoformat(lineas[0])
        if marca.tzinfo is None:
            raise ValueError("fecha sin zona horaria")
        ok, total = (int(n) for n in lineas[1].split(" de "))
        if not 0 <= ok <= total or total <= 0:
            raise ValueError("conteo inválido")
        # La fecha UTC puede ser de mañana cuando acá todavía es hoy.
        local = marca.astimezone()
    except FileNotFoundError:
        return False
    except (OSError, UnicodeError, ValueError, IndexError, OverflowError):
        log("AVISO: parte de Tango ilegible; vuelvo a intentar la bajada completa")
        return False
    if (local.date() == hoy and ok == total == TOTAL_BAJADAS_DIARIAS
            and not any(linea.strip() for linea in lineas[2:])):
        log("ya bajó hoy completo a las %s; no hago nada" % local.strftime("%H:%M"))
        return True
    return False


def pendientes(cfg):
    """Las diez fotos válidas: seis de A y cuatro de AA."""
    return [(empresa, consulta, proceso)
            for empresa, empresa_id in cfg.get("empresas", {}).items() if empresa_id
            for consulta, proceso in cfg.get("consultas", {}).items() if proceso
            if not (empresa != "A" and consulta in SOLO_A)]


def _mostrar_prueba(cfg, tok, consulta, empresa, proceso, desde, hasta):
    st, url, cuerpo = llamar(
        cfg, tok, empresa, consulta, proceso, desde, hasta, pagina=0, tam=5)
    print("GET", url)
    print("HTTP", st)
    if st != 200:
        raise RuntimeError("Live devolvió HTTP %s" % st)
    datos = _respuesta(cuerpo, url)
    filas = datos["filas"]
    traducidas, columnas, linea_codigos, linea_pares = preparar_filas(consulta, empresa, filas)
    print("totalCount:", datos["total"])
    print("columnas API:", _columnas_api(filas))
    print("columnas traducidas:", columnas)
    print("conteo por código:", linea_codigos or "no aplica")
    if linea_pares:
        print("control Tipo/Clase:", linea_pares)
    if consulta == "cheques_terceros":
        print("filas C dentro de la muestra:", len(traducidas))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cliente", default="navar")
    ap.add_argument("--hoy", default=datetime.date.today().isoformat())
    ap.add_argument("--destino", default=None,
                    help="carpeta raíz (default: NAVAR - Datos en el Drive montado)")
    ap.add_argument("--probar", default=None,
                    help="consulta: trae 5 filas y muestra sólo estructura y conteos")
    ap.add_argument("--empresa", default="A")
    ap.add_argument("--simular", action="store_true")
    ap.add_argument("--si-falta", action="store_true",
                    help="baja sólo si el parte no confirma todas las fotos de hoy")
    a = ap.parse_args(argv)
    cfg = perfil(a.cliente)
    hoy = datetime.date.fromisoformat(a.hoy)

    if a.probar:
        if a.empresa not in cfg.get("empresas", {}):
            raise SystemExit("empresa desconocida: %s" % a.empresa)
        proceso = cfg.get("consultas", {}).get(a.probar)
        if not proceso:
            raise SystemExit("la consulta %s no tiene número de proceso en perfil.json" % a.probar)
        desde, hasta = rango_fechas(cfg, hoy, a.probar, a.empresa)
        _mostrar_prueba(cfg, token(a.cliente), a.probar, a.empresa, proceso, desde, hasta)
        return 0

    raiz = a.destino or carpeta_datos()
    if a.simular and not raiz:
        raiz = "<NAVAR - Datos>"
    if not raiz:
        raise SystemExit("no encuentro la carpeta de Drive montada; pasá --destino o fijá FINAUTO_DRIVE")

    trabajos = pendientes(cfg)
    faltan = [c for c, p in cfg.get("consultas", {}).items() if not p]
    faltan += [e for e, eid in cfg.get("empresas", {}).items() if not eid]
    if faltan:
        log("sin número todavía (se saltean): %s" % ", ".join(faltan))

    if a.simular:
        for empresa, consulta, proceso in trabajos:
            carpeta = carpeta_consulta(raiz, consulta, empresa)
            nombre = DESTINO[consulta][1] % (empresa, a.hoy)
            try:
                desde, hasta = rango_fechas(cfg, hoy, consulta, empresa)
                url = armar_url(cfg, empresa, consulta, proceso, desde, hasta, 0, PAGINA)
                log("bajaría %s · GET %s" % (os.path.join(carpeta, nombre), url))
            except Exception as ex:
                log("%s: FALLÓ: %s" % (nombre, ex))
                return 1
        return 0

    if a.si_falta and _bajada_completa_hoy(raiz, hoy):
        return 0

    tok = token(a.cliente)
    ok = 0
    fallas = []
    for empresa, consulta, proceso in trabajos:
        carpeta = carpeta_consulta(raiz, consulta, empresa)
        nombre = DESTINO[consulta][1] % (empresa, a.hoy)
        ruta = os.path.join(carpeta, nombre)
        try:
            desde, hasta = rango_fechas(cfg, hoy, consulta, empresa)
            recibidas, escritas = bajar_y_escribir(
                cfg, tok, empresa, consulta, proceso, ruta, desde, hasta)
            detalle = "%d filas" % escritas
            if escritas != recibidas:
                detalle += " (%d recibidas antes del filtro)" % recibidas
            log("%s: %s → %s" % (nombre, detalle, os.path.relpath(ruta, raiz)))
            ok += 1
        except Exception as ex:
            log("%s: FALLÓ: %s" % (nombre, ex))
            fallas.append((nombre, ex))
    log("listo: %d de %d" % (ok, len(trabajos)))
    try:
        _escribir_parte_tango(raiz, ok, TOTAL_BAJADAS_DIARIAS, fallas, tok)
        log("parte para el aviso diario: _para la Sheet/tango_ultima_bajada.txt")
    except Exception as ex:
        # Drive puede demorarse o no estar montado: se avisa, pero no se convierte
        # una bajada que terminó bien en una corrida fallida.
        log("AVISO: no pude escribir el parte de Tango para el mail diario: %s" % ex)
    return 0 if ok == len(trabajos) else 1


if __name__ == "__main__":
    sys.exit(main())
