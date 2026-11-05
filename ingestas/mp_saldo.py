"""Saldo diario de Mercado Pago: conserva el historial y agrega días cerrados."""
import csv
import datetime as dt
from decimal import Decimal, InvalidOperation
import io
import json
from pathlib import Path
import time
import urllib.parse

from ingestas import meli_oauth
from ingestas.mp_liquidaciones import _http
from ingestas.meli_ventas import ErrorDatos, atomico, fecha, instante, limites, meses, monto

BASE = 'https://api.mercadopago.com/v1/account/release_report'
COLUMNAS = ['fecha', 'disponible', 'a_liberar', 'intereses_del_dia']
REPEDIR_SEGUNDOS = 2 * 60 * 60
REQUERIDAS = {'DATE', 'DESCRIPTION', 'NET_CREDIT_AMOUNT', 'NET_DEBIT_AMOUNT', 'BALANCE_AMOUNT'}


def leer_reporte(contenido, configuracion, desde, hasta):
    """Comprueba toda la cadena antes de calcular los cierres que faltan."""
    try:
        lector = csv.DictReader(io.StringIO(contenido.decode('utf-8-sig')),
                                delimiter=configuracion.get('separator') or ';')
        if not REQUERIDAS.issubset(lector.fieldnames or []):
            raise ErrorDatos('al reporte de saldo le faltan columnas obligatorias')
        saldo, apertura, anterior = None, None, None
        cierres, intereses = {}, {}
        for registro in lector:
            if not registro.get('DATE'):
                continue  # El total del reporte no es un movimiento.
            dia = dt.date.fromisoformat(registro['DATE'][:10])
            # Validar la fecha completa sin cambiar el día escrito por la cuenta.
            instante(registro['DATE'])
            valores = [Decimal(registro[c].replace(',', '.')) for c in
                       ('NET_CREDIT_AMOUNT', 'NET_DEBIT_AMOUNT', 'BALANCE_AMOUNT')]
            if not all(v.is_finite() for v in valores):
                raise ErrorDatos('el reporte de saldo trae un importe inválido')
            credito, debito, nuevo = valores
            if saldo is None:
                if registro['DESCRIPTION'].strip():
                    raise ErrorDatos('al reporte de saldo le falta la fila de apertura')
                apertura = dia
            elif nuevo != saldo + credito - debito:
                raise ErrorDatos('los saldos del reporte no encadenan con sus créditos y débitos')
            if anterior is not None and dia < anterior:
                raise ErrorDatos('el reporte de saldo tiene fechas fuera de orden')
            saldo, anterior = nuevo, dia
            cierres[dia] = saldo
            if registro['DESCRIPTION'] == 'asset_management':
                intereses[dia] = intereses.get(dia, Decimal(0)) + credito - debito
        if apertura is None or apertura > desde:
            raise ErrorDatos('falta una apertura que cubra los días solicitados')
        saldo = cierres[max(d for d in cierres if d <= desde)]
        filas = []
        dia = desde
        while dia <= hasta:
            saldo = cierres.get(dia, saldo)
            filas.append(dict(fecha=dia.isoformat(), disponible=monto(saldo), a_liberar='',
                              intereses_del_dia=monto(intereses.get(dia, 0))))
            dia += dt.timedelta(days=1)
        return filas
    except (ValueError, TypeError, KeyError, InvalidOperation, csv.Error):
        raise ErrorDatos('el reporte de saldo tiene fechas, importes o columnas inválidos') from None


def bajar(sesion, carpeta, ruta_csv, desde, hasta):
    """Devuelve el historial ampliado; el llamador guarda solo si no hay faltantes."""
    ruta_csv, carpeta = Path(ruta_csv), Path(carpeta)
    filas = []
    if ruta_csv.exists():
        with ruta_csv.open(encoding='utf-8-sig', newline='') as archivo:
            filas = list(csv.DictReader(archivo))
        if filas:
            desde = max(dt.date.fromisoformat(f['fecha']) for f in filas) + dt.timedelta(days=1)
    if desde > hasta:
        return filas, ''  # No hace falta ni consultar el permiso cuando ya está al día.

    def pedir(sufijo='', cuerpo=None, crudo=False):
        return sesion.pedir('mercadopago', BASE + sufijo, _http, cuerpo, crudo)

    configuracion, listado = None, None

    def listar():
        datos = pedir('/list')
        if not isinstance(datos, list):
            raise ErrorDatos('la lista de reportes de saldo vino en un formato inesperado')
        return datos

    tramos = list(meses(desde, hasta))
    esperas = 0
    hoy = fecha(dt.datetime.now(meli_oauth.HORA_BA).isoformat())[:10]
    for numero, (inicio, fin) in enumerate(tramos):
        clave = inicio.isoformat() + '_' + fin.isoformat()
        ruta = carpeta / (clave + '.csv')
        config_ruta = ruta.with_suffix('.config.json')
        corte = max(inicio, desde)
        if ruta.exists():
            config = json.loads(config_ruta.read_text()) if config_ruta.exists() else {'separator': ';'}
            filas.extend(leer_reporte(ruta.read_bytes(), config, corte, fin))
            continue
        if configuracion is None:
            configuracion = pedir('/config')  # Solo lectura; no cambiar ni programar reportes.
            listado = listar()
        a, b = limites(inicio, fin)

        def coincide(reporte):
            return instante(reporte['begin_date']) == a and instante(reporte['end_date']) == b

        def candidato():
            return next((r for r in listado if r.get('status') in ('enabled', 'processed')
                         and (r.get('format') or Path(r.get('file_name', '')).suffix[1:]).upper() == 'CSV'
                         and coincide(r)), None)

        reporte = candidato()
        marca = carpeta / (clave + '.pedido.json')
        pendiente = any(r.get('status') == 'pending' and coincide(r) for r in listado)
        # Mercado Pago a veces acepta un pedido y no lo genera: pasado un rato se puede volver a pedir.
        pedido = json.loads(marca.read_text()) if marca.exists() else {}
        vigente = pedido.get('fecha') == hoy and time.time() - pedido.get('hora', 0) < REPEDIR_SEGUNDOS
        if not reporte and not pendiente and not vigente:
            utc = lambda valor: valor.astimezone(dt.timezone.utc).isoformat().replace('+00:00', 'Z')
            pedir(cuerpo={'begin_date': utc(a), 'end_date': utc(b)})
            atomico(marca, json.dumps({'fecha': hoy, 'hora': time.time()}).encode())
        # Cinco minutos compartidos entre todos los meses, no cinco por cada uno.
        while not reporte and esperas < 10:
            time.sleep(30)
            esperas += 1
            listado = listar()
            reporte = candidato()
        if not reporte:
            faltantes = [i.isoformat() + '_' + f.isoformat() for i, f in tramos[numero:]]
            return filas, 'faltan saldos de: ' + ', '.join(faltantes)
        contenido = pedir('/' + urllib.parse.quote(reporte['file_name'], safe=''), crudo=True)
        nuevas = leer_reporte(contenido, configuracion, corte, fin)
        atomico(config_ruta, json.dumps(configuracion).encode())
        atomico(ruta, contenido)
        filas.extend(nuevas)
    return filas, ''
