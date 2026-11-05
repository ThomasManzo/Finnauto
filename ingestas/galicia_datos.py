"""Junta las descargas locales de Galicia sin entrar al banco ni usar el llavero."""
import csv
import datetime as dt
from decimal import Decimal
import json
from pathlib import Path
import re
import unicodedata

from lector.extractos import leer_planilla_galicia
from nucleo.config import cargar_perfil

COLUMNAS_MOVIMIENTOS = ['fecha', 'concepto', 'referencia', 'importe', 'saldo', 'tipo']
COLUMNAS_SALDO = ['fecha', 'saldo']
# Se revisan en este orden: por ejemplo, una transferencia de Tiendanube es Tiendanube.
TIPOS = (
    # "IMP." y no "IMP" a secas: si no, "PAGO IMPORTACION" quedaría como impuesto.
    ('impuesto', ('IMP.', 'IMPUESTO', 'LEY 25413', 'DEBITOS Y CREDITOS', 'PERCEP', 'RETEN',
                  'IIBB', 'INGRESOS BRUTOS', 'ING. BRUTOS', 'SIRCREB', 'IVA')),
    ('comisión', ('COMISION', 'COM.', 'MANTENIMIENTO', 'CARGO')),
    ('Tiendanube', ('TIENDANUBE', 'NUVEM', 'PAGO NUBE')),
    ('transferencia', ('TRANSF', 'TRF', 'TRANSFERENCIA', 'DEBIN', 'ECHEQ')),
)


def tipo(concepto):
    texto = ''.join(c for c in unicodedata.normalize('NFD', concepto.upper())
                    if not unicodedata.combining(c))
    for categoria, palabras in TIPOS:
        if any(p in texto for p in palabras):
            return categoria
    return 'otro'


def configuracion(base_repo, cliente):
    try:
        perfil = cargar_perfil(base_repo, cliente)
    except FileNotFoundError:
        return None
    cfg = perfil.get('bancos', {}).get('galicia')
    return cfg if (cfg and cfg.get('activo') is True and cfg.get('carpeta_drive_destino')) else None


def _leer_csv(ruta):
    if not ruta.exists():
        return []
    with ruta.open(encoding='utf-8', newline='') as archivo:
        return list(csv.DictReader(archivo))


def _monto(valor):
    return '' if valor in (None, '') else format(Decimal(str(valor)), '.2f')


def _movimiento(fila):
    # Una fila ya guardada conserva su tipo: el historial puede traer tipos revisados a mano, que la
    # regla por palabras no sabe deducir. La regla clasifica solo lo nuevo que llega del Excel.
    return dict(fecha=dt.date.fromisoformat(str(fila['fecha'])[:10]).isoformat(),
                concepto=fila['concepto'], referencia=str(fila.get('referencia', fila.get('ref')) or ''),
                importe=_monto(fila['importe']), saldo=_monto(fila['saldo']),
                tipo=fila.get('tipo') or tipo(fila['concepto']))


def leer(cfg, salida, hoy=None):
    """Prepara ambos CSV completos; si algo no se lee, todavía no se publicó nada."""
    hoy = hoy or dt.date.today()
    carpeta = Path(cfg['carpeta_drive_destino'])
    if not carpeta.is_absolute() or not carpeta.is_dir():
        raise ValueError('Revisar carpeta_drive_destino de Galicia: debe existir y ser absoluta.')
    salida = Path(salida)
    patron = re.compile(re.escape(cfg['prefijo_archivo']) + r' (\d{4}-\d{2}-\d{2})\.xlsx')
    archivos = []
    for ruta in carpeta.iterdir():
        coincide = patron.fullmatch(ruta.name)
        if ruta.is_file() and coincide:
            archivos.append((dt.date.fromisoformat(coincide[1]), ruta))
    archivos.sort()
    movimientos = []
    vistos = set()

    def agregar(filas):
        for original in filas:
            fila = _movimiento(original)
            clave = tuple(fila[c] for c in COLUMNAS_MOVIMIENTOS[:-1])
            if clave not in vistos:
                vistos.add(clave)
                movimientos.append(fila)

    # El historial conserva su orden; cada Excel agrega las novedades en el orden del banco.
    agregar(_leer_csv(salida / 'galicia_movimientos.csv'))
    for _, ruta in archivos:
        agregar(leer_planilla_galicia(ruta, cuenta=cfg['cuenta'])['movimientos'])
    movimientos.sort(key=lambda fila: fila['fecha'])

    saldos = {f['fecha']: dict(fecha=f['fecha'], saldo=_monto(f['saldo']))
              for f in _leer_csv(salida / 'galicia_saldo.csv')}
    recientes = {}
    for ruta in sorted(carpeta.glob('_SALDOS_Galicia_*.json')):
        datos = json.loads(ruta.read_text(encoding='utf-8'))
        fecha = dt.date.fromisoformat(datos['fecha']).isoformat()
        generado = dt.datetime.fromisoformat(datos['generado'])
        # Los archivos del bot usan hora local; si llega un huso explícito lo pasamos a Buenos Aires.
        if generado.tzinfo:
            generado = generado.astimezone(dt.timezone(dt.timedelta(hours=-3))).replace(tzinfo=None)
        saldo = datos['empresas'][0]['saldo_actual']
        if saldo is None:
            continue  # El bot puede bajar movimientos aunque no haya logrado leer el saldo.
        if fecha not in recientes or generado > recientes[fecha][0]:
            recientes[fecha] = (generado, _monto(saldo))
    for fecha, (_, saldo) in recientes.items():
        saldos[fecha] = dict(fecha=fecha, saldo=saldo)
    ultima = archivos[-1][0] if archivos else None
    motivo = ''
    if ultima is None:
        motivo = 'todavía no hay descargas de Galicia'
    elif (hoy - ultima).days > 2:
        motivo = 'el bot de Galicia no bajó nada desde ' + ultima.isoformat()
    # El rearmado usa lo ya bajado: sin esto, un bot que falló hoy se vería como una fuente al día.
    estado_hoy = carpeta / ('_ESTADO_Galicia_%s.txt' % hoy.strftime('%d-%m'))
    if not motivo and estado_hoy.exists() and 'OK: no fallo' not in estado_hoy.read_text(encoding='utf-8'):
        motivo = 'el bot de Galicia falló hoy; datos de la descarga del ' + ultima.isoformat()
    fechas = [f['fecha'] for f in movimientos]
    resumen = dict(ok=not motivo, filas=len(movimientos), desde=min(fechas, default=''),
                   hasta=max(fechas, default=''), motivo=motivo,
                   ultima_descarga=ultima.isoformat() if ultima else '')
    return movimientos, [saldos[f] for f in sorted(saldos)], resumen
