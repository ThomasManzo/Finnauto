"""Liquidaciones sin cambiar la configuración que usa el vendedor."""
import csv
import datetime as dt
import io
import json
from pathlib import Path
from zoneinfo import ZoneInfo
import time
import urllib.parse
import urllib.request
from ingestas import meli_oauth
from ingestas.meli_ventas import ErrorDatos, atomico, fecha, instante, limites, meses, monto

BASE = 'https://api.mercadopago.com/v1/account/settlement_report'
COLUMNAS = 'id_origen,tipo_transaccion,medio_pago,monto_bruto,comision,impuestos,monto_neto,fecha_transaccion,fecha_liquidacion,fecha_liberacion,unidad_negocio,id_venta_ml'.split(',')
ORIGEN = 'SOURCE_ID,TRANSACTION_TYPE,PAYMENT_METHOD_TYPE,TRANSACTION_AMOUNT,FEE_AMOUNT,TAXES_AMOUNT,REAL_AMOUNT,TRANSACTION_DATE,SETTLEMENT_DATE,MONEY_RELEASE_DATE'.split(',')


def _http(pedido):
    with urllib.request.build_opener(meli_oauth._SinRedireccion()).open(pedido, timeout=60) as respuesta:
        return respuesta.status, respuesta.read()


def _fecha_reporte(valor, configuracion):
    if not valor:
        return ''
    dato = dt.datetime.fromisoformat(str(valor).replace('Z', '+00:00'))
    if dato.tzinfo is None:
        zona = configuracion.get('display_timezone') or '-03:00'
        if zona in ('UTC', 'Z'):
            huso = dt.timezone.utc
        elif zona.startswith(('+', '-')):
            horas, minutos = zona[1:].split(':')
            huso = dt.timezone((1 if zona[0] == '+' else -1) * dt.timedelta(hours=int(horas), minutes=int(minutos)))
        else:
            huso = ZoneInfo(zona)
        dato = dato.replace(tzinfo=huso)
    return fecha(dato.isoformat())


def _convertir(encabezados, registros, ventas, configuracion, vistas=None):
    if not {'SOURCE_ID', 'REAL_AMOUNT'}.issubset(encabezados):
        raise ErrorDatos('al reporte le faltan SOURCE_ID o REAL_AMOUNT; revisar las columnas con el vendedor')
    vinculos = {}
    for venta in ventas:
        # La cabecera es la venta del reporte; las hijas no deben pisarla.
        for pago in venta.get('id_pago_mp', '').split('|'):
            if pago:
                vinculos.setdefault(pago, venta['id_venta'])
    filas = []
    vistas = set() if vistas is None else vistas
    for registro in registros:
        if not any(v not in (None, '') for v in registro.values()): continue
        # Comparar el renglón original completo: dos movimientos que difieren
        # en una columna no exportada siguen siendo dos movimientos distintos.
        identidad = tuple(sorted((str(k), str(v)) for k, v in registro.items()))
        if identidad in vistas:
            continue
        vistas.add(identidad)
        fila = dict.fromkeys(COLUMNAS, '')
        for destino, origen in zip(COLUMNAS, ORIGEN):
            valor = registro.get(origen)
            if valor in (None, ''): continue
            if destino in COLUMNAS[3:7]:
                # Los reportes separados por ; pueden traer coma decimal.
                fila[destino] = monto(str(valor).replace(',', '.'))
            elif destino in COLUMNAS[7:10]:
                fila[destino] = _fecha_reporte(valor, configuracion)
            else:
                fila[destino] = str(valor)
        fila['unidad_negocio'] = ' / '.join(str(registro[c]) for c in ('BUSINESS_UNIT', 'SUB_UNIT') if registro.get(c))
        fila['id_venta_ml'] = vinculos.get(fila['id_origen'], '')
        filas.append(fila)
    return filas


def leer_reporte(texto, configuracion, ventas=(), vistas=None):
    """Función pura: texto CSV y configuración → movimientos con columnas fijas."""
    lector = csv.DictReader(io.StringIO(texto.lstrip('\ufeff')), delimiter=configuracion.get('separator') or ',')
    return _convertir(lector.fieldnames or [], lector, ventas, configuracion, vistas)


def leer_archivo(contenido, formato, configuracion, ventas, vistas=None):
    if formato.upper() != 'XLSX':
        return leer_reporte(contenido.decode('utf-8-sig'), configuracion, ventas, vistas)
    try:
        import openpyxl
    except ImportError:
        raise ErrorDatos('el reporte es Excel y falta openpyxl en este entorno') from None
    libro = openpyxl.load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
    try:
        registros = libro.active.iter_rows(values_only=True)
        encabezados = next(registros, ())
        return _convertir(encabezados, (dict(zip(encabezados, r)) for r in registros), ventas, configuracion, vistas)
    finally:
        libro.close()


def bajar(sesion, carpeta, desde, hasta, ventas=()):
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    def pedir(sufijo='', cuerpo=None, crudo=False):
        return sesion.pedir('mercadopago', BASE + sufijo, _http, cuerpo, crudo)
    configuracion = pedir('/config')  # Solo lectura: nunca configurar ni programar reportes.
    def listar():
        datos = pedir('/list')
        if not isinstance(datos, list):
            raise ErrorDatos('la lista de liquidaciones vino en un formato inesperado')
        return datos
    listado = listar()
    pendientes, archivos = {}, {}
    for inicio, fin in meses(desde, hasta):
        a, b = limites(inicio, fin)
        clave = inicio.isoformat() + '_' + fin.isoformat()
        existentes = list(carpeta.glob(clave + '.csv')) + list(carpeta.glob(clave + '.xlsx'))
        if existentes:
            archivos[clave] = existentes[0]
            continue
        pendientes[clave] = (a, b)
        coincidencias = [r for r in listado if r.get('status') == 'processed' and instante(r['begin_date']) == a and instante(r['end_date']) == b]
        if not coincidencias:
            # Dejar constancia del pedido aceptado para no repetirlo en la misma fecha.
            marca = carpeta / (clave + '.pedido.json')
            hoy = dt.datetime.now(meli_oauth.HORA_BA).date().isoformat()
            if not marca.exists() or json.loads(marca.read_text()).get('fecha') != hoy:
                utc = lambda f: f.astimezone(dt.timezone.utc).isoformat().replace('+00:00', 'Z')
                pedir(cuerpo={'begin_date': utc(a), 'end_date': utc(b)})
                atomico(marca, json.dumps({'fecha': hoy}).encode())
    for vuelta in range(21):
        for clave, (a, b) in list(pendientes.items()):
            reporte = next((r for r in listado if r.get('status') == 'processed' and instante(r['begin_date']) == a and instante(r['end_date']) == b), None)
            if reporte:
                formato = reporte.get('format') or Path(reporte['file_name']).suffix.lstrip('.')
                if formato.upper() not in {'CSV', 'XLSX'}: raise ErrorDatos('el reporte no es CSV ni Excel')
                contenido = pedir('/' + urllib.parse.quote(reporte['file_name'], safe=''), crudo=True)
                # Validar antes de guardar: una respuesta rota no debe quedar congelada en caché.
                leer_archivo(contenido, formato, configuracion, ventas)
                ruta = carpeta / (clave + '.' + formato.lower())
                atomico(ruta.with_suffix('.config.json'), json.dumps(configuracion).encode())
                atomico(ruta, contenido)
                archivos[clave] = ruta
                del pendientes[clave]
        if not pendientes or vuelta == 20: break
        time.sleep(30)
        listado = listar()
    filas, vistas = [], set()
    for clave, ruta in sorted(archivos.items()):
        config_guardada = ruta.with_suffix('.config.json')
        config_mes = json.loads(config_guardada.read_text()) if config_guardada.exists() else configuracion
        for fila in leer_archivo(ruta.read_bytes(), ruta.suffix[1:], config_mes, ventas, vistas):
            # El primer mes se pide entero; el CSV respeta el corte solicitado.
            dia = (fila['fecha_liquidacion'] or fila['fecha_transaccion'])[:10]
            if dia and not desde.isoformat() <= dia <= hasta.isoformat(): continue
            filas.append(fila)
    motivo = 'faltan liquidaciones de: ' + ', '.join(pendientes) if pendientes else ''
    return filas, motivo
