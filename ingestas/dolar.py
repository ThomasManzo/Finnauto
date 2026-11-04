"""Dólar oficial: sumamos días nuevos sin cambiar el historial ya guardado."""
import csv
import datetime as dt
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from http.client import HTTPException
import json
from pathlib import Path
import time
import urllib.error
import urllib.request

from ingestas import meli_ventas as ml

COLUMNAS = ['fecha', 'compra', 'venta', 'fuente']
URL = 'https://api.argentinadatos.com/v1/cotizaciones/dolares/oficial'
ERROR_CONEXION = 'no se pudo consultar el dólar; revisar la conexión y volver a intentar'


def _http(pedido):
    with urllib.request.urlopen(pedido, timeout=60) as respuesta:
        return respuesta.status, respuesta.read()


def _consultar(http):
    pedido = urllib.request.Request(URL, headers={'User-Agent': 'finauto'})
    for intento in range(3):
        try:
            codigo, cuerpo = http(pedido)
            if codigo != 200:
                raise urllib.error.HTTPError(URL, codigo, '', None, None)
            return cuerpo
        except urllib.error.HTTPError as exc:
            if exc.code != 429 and not 500 <= exc.code <= 599:
                break
        except (OSError, HTTPException):
            pass
        # Una falla pasajera puede resolverse sola; nunca hacemos más de tres pedidos.
        if intento < 2:
            time.sleep(2 ** (intento + 1))
    raise ml.ErrorDatos(ERROR_CONEXION)


def _monto(valor):
    # JSON se lee directamente como Decimal para no perder centavos al pasar por float.
    if isinstance(valor, bool) or not isinstance(valor, (int, Decimal)):
        raise ValueError()
    numero = Decimal(valor)
    if not numero.is_finite() or numero <= 0:
        raise ValueError()
    return format(numero.quantize(Decimal('.01'), rounding=ROUND_HALF_UP), '.2f')


def bajar(salida, desde, hasta, http=_http):
    """Devuelve el historial completo para escribir en salida/dolar.csv; no escribe archivos."""
    cuerpo = _consultar(http)
    try:
        datos = json.loads(cuerpo, parse_float=Decimal, parse_constant=Decimal)
        if not isinstance(datos, list):
            raise ValueError()
        nuevas = {}
        for fila in datos:
            if not isinstance(fila, dict) or not isinstance(fila.get('fecha'), str):
                raise ValueError()
            fecha = dt.date.fromisoformat(fila['fecha'])
            if fecha.isoformat() != fila['fecha']:
                raise ValueError()
            compra, venta = _monto(fila.get('compra')), _monto(fila.get('venta'))
            if desde <= fecha <= hasta:
                nuevas[fecha.isoformat()] = dict(fecha=fecha.isoformat(), compra=compra,
                    venta=venta, fuente='argentinadatos')
    except (ValueError, TypeError, InvalidOperation):
        raise ml.ErrorDatos('la respuesta del dólar tiene datos inválidos; revisar la fuente y volver a intentar') from None

    # Validamos incluso los días fuera del período antes de devolver algo para guardar.
    ruta = Path(salida) / 'dolar.csv'
    anteriores = []
    if ruta.exists():
        with ruta.open(encoding='utf-8', newline='') as archivo:
            anteriores = list(csv.DictReader(archivo))
    guardadas = {fila['fecha'] for fila in anteriores}
    return sorted(anteriores + [fila for fecha, fila in nuevas.items() if fecha not in guardadas],
                  key=lambda fila: fila['fecha'])
