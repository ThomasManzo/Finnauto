"""Tiendanube: permiso en el llavero y órdenes para la bajada diaria.

Uso: python3 -m ingestas.tiendanube --cliente ejemplo link|canjear|estado|probar.
El código dura cinco minutos; el permiso no vence y no se renueva. La caché
contiene órdenes, nunca claves. El avance se guarda después de publicar el CSV.
"""
import argparse
import contextlib
import datetime as dt
from decimal import Decimal
import getpass
import io
import json
import math
import re
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from ingestas import meli_oauth as oauth, meli_ventas as ml
from nucleo import credenciales

API = 'https://api.tiendanube.com/2025-03'
TOKEN_URL = 'https://www.tiendanube.com/apps/authorize/token'
USER_AGENT = 'Finauto (contacto@finauto.com.ar)'
COLUMNAS = 'numero_orden,fecha,estado_pago,sku,producto,cantidad,precio,subtotal,descuento,costo_envio,total,cuotas,neto_cobrado,fecha_acreditacion'.split(',')
ESTADOS = dict(paid='pagada', pending='pendiente', authorized='autorizada',
               refunded='reintegrada', voided='anulada', abandoned='abandonada')


class ErrorTiendanube(ml.ErrorDatos):
    """Mensaje para la consola y control.json, sin datos de los pedidos."""


def _validar(cliente):
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', cliente):
        raise ErrorTiendanube('cliente inválido: usar letras, números, guiones o guion bajo')


def _llavero():
    return oauth._llavero()


def _aplicacion(cliente, opcional=False):
    _validar(cliente)
    try:
        # Solo una entrada ausente permite saltear la fuente. Un llavero roto
        # o una entrada incompleta deben avisar, para no ocultar un problema.
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            if _llavero().get_password(f'finauto:{cliente}:tiendanube', 'credenciales') is None:
                if opcional:
                    return None
                raise ValueError()
            usuario, clave = credenciales.cargar(oauth.BASE_REPO, cliente, 'tiendanube')
        if not re.fullmatch(r'[0-9]+', str(usuario)) or not clave:
            raise ValueError()
        return str(usuario), str(clave)
    except (Exception, SystemExit):
        raise ErrorTiendanube('no se pudieron leer las credenciales de Tiendanube: revisar el llavero o correr setup_credenciales.py') from None


def tiene_aplicacion(cliente):
    return _aplicacion(cliente, opcional=True) is not None


def _permiso(dato):
    tienda = dato.get('user_id') or dato.get('store_id')
    if (not re.fullmatch(r'[0-9]+', str(tienda)) or
            not isinstance(dato.get('access_token'), str) or not dato['access_token'] or
            not isinstance(dato.get('scope'), str)):
        raise ValueError()
    return dict(access_token=dato['access_token'], store_id=str(tienda), scope=dato['scope'])


def _leer(cliente):
    _validar(cliente)
    try:
        crudo = _llavero().get_password(f'finauto:{cliente}:tiendanube-token', 'token')
        return _permiso(json.loads(crudo)) if crudo is not None else None
    except Exception:
        raise ErrorTiendanube('no se pudo leer el permiso de Tiendanube: revisar el llavero o volver a autorizar') from None


def _resumen(dato):
    return dict(hay_token=dato is not None, store_id=dato['store_id'] if dato else None,
                scope=dato['scope'] if dato else None)


def estado(cliente):
    return _resumen(_leer(cliente))


def link_autorizacion(cliente):
    app, _ = _aplicacion(cliente)
    return f'https://www.tiendanube.com/apps/{app}/authorize?' + urllib.parse.urlencode({'state': 'tn-' + secrets.token_hex(4)})


def limpiar_codigo(texto):
    codigo = re.sub(r'\s+', '', texto)
    codigo = re.sub(r'^TN:', '', codigo, flags=re.I)
    if not codigo or ':' in codigo:
        raise ErrorTiendanube('falta el código de Tiendanube o tiene un prefijo incorrecto')
    return codigo


def _http(pedido):
    # No seguir redirecciones: podrían llevar el permiso a otro servidor.
    with urllib.request.build_opener(oauth._SinRedireccion()).open(pedido, timeout=60) as respuesta:
        return json.load(respuesta), dict(respuesta.headers)


def canjear_codigo(cliente, codigo):
    app, clave = _aplicacion(cliente)
    cuerpo = dict(client_id=app, client_secret=clave, grant_type='authorization_code', code=limpiar_codigo(codigo))
    pedido = urllib.request.Request(TOKEN_URL, data=json.dumps(cuerpo).encode(),
        headers={'Content-Type': 'application/json', 'User-Agent': USER_AGENT})
    try:
        respuesta, _ = _http(pedido)
        dato = _permiso(respuesta)
    except urllib.error.HTTPError as exc:
        # Solo usamos el tipo de error conocido; nunca mostramos el cuerpo.
        try:
            error = json.loads(exc.read()).get('error')
        except Exception:
            error = None
        if error == 'invalid_client' or exc.code in (401, 403):
            motivo = 'credenciales de la aplicación Tiendanube inválidas'
        elif error == 'invalid_grant' or exc.code == 400:
            motivo = 'el código venció o ya se usó: hay que volver a autorizar Tiendanube'
        else:
            motivo = 'no se pudo canjear el código de Tiendanube; volver a autorizar e intentar de nuevo'
        raise ErrorTiendanube(motivo) from None
    except Exception:
        # No repetir el canje: si se cortó la respuesta, el código pudo gastarse.
        raise ErrorTiendanube('no se pudo completar el canje de Tiendanube: revisar la conexión y volver a autorizar') from None
    try:
        _llavero().set_password(f'finauto:{cliente}:tiendanube-token', 'token', json.dumps(dato))
    except Exception:
        raise ErrorTiendanube('no se pudo guardar el permiso de Tiendanube en el llavero: volver a autorizar') from None
    return _resumen(dato)


class Sesion:
    def __init__(self, cliente):
        self.permiso = _leer(cliente)
        if self.permiso is None:
            raise ErrorTiendanube('falta autorizar Tiendanube')
        self.base = API + '/' + self.permiso['store_id']
        self.proximo = 0

    def pedir(self, url):
        # También comprobamos los links de paginación antes de mandar el token.
        destino, base = urllib.parse.urlsplit(url), urllib.parse.urlsplit(self.base)
        if (destino.scheme != base.scheme or destino.netloc != base.netloc or
                destino.path not in (base.path + '/orders', base.path + '/store')):
            raise ErrorTiendanube('Tiendanube devolvió un enlace de paginación inválido')
        for intento in range(6):
            espera = self.proximo - time.monotonic()
            if espera > 0:
                time.sleep(espera)
            self.proximo = time.monotonic() + .5
            pedido = urllib.request.Request(url, headers={
                'Authorization': 'Bearer ' + self.permiso['access_token'], 'User-Agent': USER_AGENT})
            try:
                datos, encabezados = _http(pedido)
                return datos, {k.lower(): v for k, v in encabezados.items()}
            except urllib.error.HTTPError as exc:
                if exc.code == 401:
                    raise ErrorTiendanube('hay que volver a autorizar Tiendanube: la aplicación fue desinstalada o el permiso no sirve') from None
                if exc.code == 402:
                    raise ErrorTiendanube('la tienda o la aplicación Tiendanube tiene un pago pendiente') from None
                if (exc.code != 429 and not 500 <= exc.code < 600) or intento == 5:
                    raise ErrorTiendanube(f'no se pudo consultar Tiendanube (HTTP {exc.code})') from None
                demora = 2 ** (intento + 1)
                if exc.code == 429:
                    encabezados = {k.lower(): v for k, v in (exc.headers or {}).items()}
                    try:
                        valor = float(encabezados['x-rate-limit-reset']) / 1000
                        if math.isfinite(valor) and valor >= 0:
                            demora = valor
                    except (KeyError, ValueError, TypeError):
                        pass
            except (OSError, urllib.error.URLError):
                if intento == 5:
                    raise ErrorTiendanube('no se pudo conectar con Tiendanube: revisar la conexión') from None
                demora = 2 ** (intento + 1)
            except (ValueError, TypeError):
                raise ErrorTiendanube('no se pudo leer la respuesta de Tiendanube') from None
            time.sleep(demora)


def siguiente(link):
    for parte in link.split(','):
        enlace = re.match(r'\s*<([^>]+)>', parte)
        relacion = re.search(r';\s*rel\s*=\s*"([^"]+)"', parte, re.I)
        if enlace and relacion and 'next' in relacion[1].split():
            return enlace[1]
    return None


def ordenes(sesion, parametros):
    url = sesion.base + '/orders?' + urllib.parse.urlencode(dict(parametros, per_page=200, page=1))
    vistas = set()
    while url:
        if url in vistas:
            raise ErrorTiendanube('Tiendanube repitió una página: la bajada quedó incompleta')
        vistas.add(url)
        datos, encabezados = sesion.pedir(url)
        if not isinstance(datos, list):
            raise ErrorTiendanube('Tiendanube no devolvió una lista de órdenes')
        yield from datos
        enlace = siguiente(encabezados.get('link', ''))
        url = urllib.parse.urljoin(url, enlace) if enlace else None


def instante(valor):
    # Python 3 de algunas Mac exige los dos puntos en el huso (-03:00).
    return ml.instante(re.sub(r'([+-]\d{2})(\d{2})$', r'\1:\2', str(valor)))


def fecha(valor):
    return instante(valor).strftime('%Y-%m-%d %H:%M')


def armar_orden(orden):
    subtotal, envio, total = (ml.decimal(orden.get(k)) for k in ('subtotal', 'shipping_cost_customer', 'total'))
    if not all(v.is_finite() for v in (subtotal, envio, total)):
        raise ErrorTiendanube('una orden de Tiendanube trae importes inválidos')
    descuento = total - subtotal - envio
    pago = orden.get('payment_status', '')
    estado_pago = 'cancelada' if orden.get('status') == 'cancelled' else ESTADOS.get(pago, pago)
    filas = []
    for producto in orden['products']:
        fila = dict.fromkeys(COLUMNAS, '')
        fila.update(numero_orden=str(orden['number']), fecha=fecha(orden['created_at']),
                    estado_pago=estado_pago, sku=producto.get('sku'), producto=producto['name'],
                    cantidad=producto['quantity'], precio=ml.monto(producto['price']))
        if not filas:
            fila.update(subtotal=ml.monto(subtotal), descuento=ml.monto(descuento),
                        costo_envio=ml.monto(envio), total=ml.monto(total),
                        cuotas=(orden.get('payment_details') or {}).get('installments', ''))
        filas.append(fila)
    return filas, descuento > Decimal(1)


def bajar(sesion, carpeta, desde, hasta, ultima=None):
    """Busca por mes y por cambios. Una falla no adelanta la última corrida buena."""
    inicio = desde
    if ultima:
        # Dos meses completos anteriores al día de corrida, más el mes en curso.
        inicio = (hasta + dt.timedelta(days=1)).replace(day=1)
        for _ in range(2):
            inicio = (inicio - dt.timedelta(days=1)).replace(day=1)
        inicio = max(desde, inicio)
    consultas = []
    for primero, ultimo in ml.meses(inicio, hasta):
        minimo = dt.datetime.combine(max(inicio, primero), dt.time.min, ml.HORA_BA)
        maximo = dt.datetime.combine(ultimo, dt.time.max, ml.HORA_BA)
        consultas.append(dict(created_at_min=minimo.isoformat(), created_at_max=maximo.isoformat()))
    if ultima:
        consultas.append(dict(updated_at_min=(instante(ultima) - dt.timedelta(days=2)).isoformat()))
    for parametros in consultas:
        for orden in ordenes(sesion, parametros):
            ident = str(orden['id'])
            if not re.fullmatch(r'[0-9]+', ident):
                raise ErrorTiendanube('Tiendanube devolvió una orden sin identificador válido')
            armar_orden(orden)
            # Guardamos solo los campos usados: la API también trae datos personales
            # que no hacen falta para este CSV. La tienda evita mezclar permisos.
            dato = {k: orden.get(k) for k in ('id', 'number', 'created_at', 'updated_at', 'status',
                'payment_status', 'subtotal', 'total', 'shipping_cost_customer', 'payment_details', 'products')}
            dato['products'] = [{k: p.get(k) for k in ('sku', 'name', 'quantity', 'price')} for p in orden['products']]
            dato['payment_details'] = {'installments': (orden.get('payment_details') or {}).get('installments', '')}
            ml.guardar_json(carpeta / f'orden-{ident}.json', dict(store_id=sesion.permiso['store_id'], orden=dato))
    acumuladas = []
    for ruta in carpeta.glob('orden-*.json'):
        dato = json.loads(ruta.read_text(encoding='utf-8'))
        orden = dato['orden']
        if dato['store_id'] == sesion.permiso['store_id'] and desde <= instante(orden['created_at']).date() <= hasta:
            acumuladas.append(orden)
    acumuladas.sort(key=lambda o: (fecha(o['created_at']), int(o['number'])))
    filas, raras = [], 0
    for orden in acumuladas:
        nuevas, rara = armar_orden(orden)
        filas.extend(nuevas)
        raras += int(rara)
    return filas, raras


def main(argv=None):
    parser = argparse.ArgumentParser(description='Autorización de Tiendanube')
    parser.add_argument('--cliente', required=True)
    parser.add_argument('comando', choices=['link', 'canjear', 'estado', 'probar'])
    args = parser.parse_args(argv)
    try:
        if args.comando == 'link':
            print(link_autorizacion(args.cliente))
        elif args.comando == 'canjear':
            print('El código vence a los 5 minutos y se usa una sola vez.')
            codigo = getpass.getpass('Código: ') if sys.stdin.isatty() else sys.stdin.readline()
            dato = canjear_codigo(args.cliente, codigo)
            print(f"Listo: autorizada la tienda {dato['store_id']}.")
        elif args.comando == 'estado':
            print(json.dumps(estado(args.cliente), ensure_ascii=False))
        else:
            sesion = Sesion(args.cliente)
            sesion.pedir(sesion.base + '/store')
            print('OK')
        return 0
    except ErrorTiendanube as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except (EOFError, KeyboardInterrupt):
        print('Autorización cancelada.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
