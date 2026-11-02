"""Ventas de Mercado Libre: cuentas separadas de las consultas a internet."""
import datetime as dt
from decimal import Decimal, ROUND_HALF_UP
import email.utils
from http.client import HTTPException
import json
import os
from pathlib import Path
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from ingestas import meli_oauth

HORA_BA = meli_oauth.HORA_BA
IMPUESTO_BONIFICACION_FLEX = Decimal('0.006')
VALIDOS = {'approved', 'refunded', 'charged_back', 'in_mediation'}
COLUMNAS = 'id_venta,id_pack,fecha_venta,estado,sku,id_publicacion,titulo,variante,unidades,precio_unitario,ingresos_productos,cargo_venta_impuestos,ingresos_envio,costos_envio,descuentos_bonificaciones,anulaciones_reembolsos,otros_cargos,total,tiene_cuotas,venta_por_publicidad,forma_entrega,provincia_comprador,fecha_entregado,id_pago_mp,descuadrada'.split(',')
IMPORTES = COLUMNAS[10:18]


class ErrorDatos(Exception):
    """Un motivo apto para mostrar sin cuerpos HTTP ni credenciales."""


def decimal(valor):
    return Decimal(str(valor or 0))


def monto(valor):
    valor = decimal(valor).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
    return format(abs(valor) if valor == 0 else valor, '.2f')


def instante(valor):
    fecha = dt.datetime.fromisoformat(str(valor).replace('Z', '+00:00'))
    return (fecha if fecha.tzinfo else fecha.replace(tzinfo=HORA_BA)).astimezone(HORA_BA)


def fecha(valor):
    return instante(valor).strftime('%Y-%m-%d %H:%M') if valor else ''


def meses(desde, hasta):
    inicio = desde.replace(day=1)
    while inicio <= hasta:
        siguiente = (inicio.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
        yield inicio, min(hasta, siguiente - dt.timedelta(days=1))
        inicio = siguiente


def limites(inicio, fin):
    return (dt.datetime.combine(inicio, dt.time.min, HORA_BA),
            dt.datetime.combine(fin, dt.time(23, 59, 59), HORA_BA))


def atomico(ruta, contenido):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    nombre = None
    try:
        with tempfile.NamedTemporaryFile(dir=ruta.parent, delete=False) as archivo:
            nombre = archivo.name
            archivo.write(contenido)
        os.replace(nombre, ruta)
    finally:
        if nombre and os.path.exists(nombre):
            os.unlink(nombre)


def guardar_json(ruta, datos):
    atomico(ruta, json.dumps(datos, ensure_ascii=False).encode('utf-8'))


def _http(pedido):
    with urllib.request.build_opener(meli_oauth._SinRedireccion()).open(pedido, timeout=60) as respuesta:
        return respuesta.status, respuesta.read()


class Sesion:
    # Una sesión compartida por corrida evita pedir el mismo permiso por cada pago.
    def __init__(self, cliente):
        meli_oauth._validar(cliente, 'mercadolibre')
        self.cliente, self.tokens = cliente, {}

    def pedir(self, fuente, url, http, cuerpo=None, crudo=False, encabezados=None):
        if fuente not in self.tokens:
            self.tokens[fuente] = meli_oauth.access_token(self.cliente, fuente)
        renovado, intentos = False, 0
        while True:
            pedido = urllib.request.Request(url, data=None if cuerpo is None else json.dumps(cuerpo).encode(),
                headers={'Authorization': 'Bearer ' + self.tokens[fuente], 'Content-Type': 'application/json', **(encabezados or {})})
            try:
                codigo, datos = http(pedido)
                if codigo == 203:
                    raise ErrorDatos('no se pudo generar el reporte; volver a intentar más tarde')
                return datos if crudo else (json.loads(datos) if datos else {})
            except urllib.error.HTTPError as exc:
                if exc.code == 401 and not renovado:
                    self.tokens[fuente] = meli_oauth.access_token(self.cliente, fuente)
                    renovado = True
                    continue
                # 429 = "demasiados pedidos"; 5xx = el servidor tuvo un problema pasajero.
                if (exc.code == 429 or exc.code >= 500) and intentos < 5:
                    espera = 2 ** (intentos + 1)
                    valor = exc.headers.get('Retry-After') if exc.headers else None
                    if valor:
                        try:
                            espera = max(0, float(valor))
                        except ValueError:
                            try:
                                espera = max(0, email.utils.parsedate_to_datetime(valor).timestamp() - time.time())
                            except (ValueError, TypeError):
                                pass
                    time.sleep(espera)
                    intentos += 1
                    continue
                raise ErrorDatos(f'no se pudo consultar {fuente} (HTTP {exc.code}); revisar el permiso o intentar más tarde') from None
            except urllib.error.URLError:
                # Un corte de red en una corrida de horas no tiene que tirar todo: reintentar.
                if intentos < 5:
                    time.sleep(2 ** (intentos + 1))
                    intentos += 1
                    continue
                raise ErrorDatos(f'no se pudo conectar con {fuente}; revisar la conexión y volver a intentar') from None
            except (OSError, HTTPException, ValueError):
                # Un POST puede haber quedado hecho aunque se corte la respuesta.
                if cuerpo is None and intentos < 5:
                    time.sleep(2 ** (intentos + 1))
                    intentos += 1
                    continue
                raise ErrorDatos(f'no se pudo leer la respuesta de {fuente}; revisar la conexión y volver a intentar') from None


def armar_venta(ordenes, pagos, envio=None, costos=None, pagos_envio=None):
    """Devuelve (filas, descuadrada); el envío compartido se cuenta una sola vez."""
    envio, costos = envio or {}, costos or {}
    pagos = list({str(p['id']): p for p in pagos if p.get('status') in VALIDOS}.values())
    pagos_envio = pagos_envio_validos(pagos_envio or [])
    pagos_envio = [p for p in pagos_envio if str(p['id']) not in {str(p['id']) for p in pagos}]
    cargos = [c for p in pagos for c in p.get('charges_details', []) if c.get('accounts', {}).get('from') == 'collector']
    def cargo(*tipos):
        return sum((decimal(c.get('amounts', {}).get('original')) for c in cargos if c.get('type') in tipos), Decimal(0))
    receptor = decimal(costos.get('receiver', {}).get('cost'))
    flex = envio.get('logistic_type') == 'self_service'
    d = Decimal(0)
    if flex:
        remitentes = costos.get('senders', [])
        if sum(decimal(s.get('cost')) for s in remitentes) > 0:
            d = sum((decimal(s.get('save')) for s in remitentes), Decimal(0))
        elif receptor == 0:
            d = decimal(costos.get('gross_amount'))
    impuesto = decimal(monto(d * IMPUESTO_BONIFICACION_FLEX))
    neto = sum((decimal(p.get('transaction_details', {}).get('net_received_amount')) for p in pagos), Decimal(0))
    anulacion = Decimal(0)
    if any(decimal(p.get('transaction_amount_refunded')) > 0 for p in pagos):
        anulacion = -neto - (d - impuesto if envio.get('status') == 'cancelled' else 0)
    importes = [sum(decimal(i['unit_price']) * decimal(i['quantity']) for o in ordenes for i in o['order_items']),
                -cargo('fee', 'tax') - impuesto, receptor,
                -cargo('shipping') if any(c.get('type') == 'shipping' for c in cargos) else (Decimal(0) if flex else -receptor),
                d, anulacion, -cargo('coupon')]
    total = sum(importes)
    # El envío cobrado aparte ayuda al control, pero sus impuestos no cambian la venta.
    aparte = sum((decimal(p.get('transaction_amount')) - decimal(p.get('transaction_amount_refunded'))
                  for p in pagos_envio), Decimal(0)) if importes[3] != -receptor else Decimal(0)
    descuadrada = abs(total - (neto + d - impuesto + anulacion + aparte)) > 1
    base = dict.fromkeys(COLUMNAS, '')
    base.update(zip(IMPORTES, map(monto, importes + [total])))
    base.update(fecha_venta=min((fecha(o.get('date_closed')) for o in ordenes if o.get('date_closed')), default=''),
        tiene_cuotas='sí' if any(c.get('name') == 'financing_add_on_fee' for c in cargos) else 'no',
        forma_entrega={'self_service': 'flex', 'fulfillment': 'full', 'xd_drop_off': 'correo', 'drop_off': 'correo', 'cross_docking': 'correo'}.get(envio.get('logistic_type'), 'otra' if envio else 'acordar'),
        provincia_comprador=envio.get('receiver_address', {}).get('state', {}).get('name', ''),
        fecha_entregado=fecha(envio.get('status_history', {}).get('date_delivered')),
        id_pago_mp='|'.join(str(p['id']) for p in pagos + pagos_envio), descuadrada='sí' if descuadrada else 'no')
    def estado(orden):
        est = envio.get('status')
        if est == 'cancelled': return 'Cancelada'
        if (orden.get('status') == 'cancelled' and (est == 'delivered' or base['fecha_entregado'])) or (est == 'not_delivered' and envio.get('substatus') == 'returned'): return 'Devuelta'
        if orden.get('status') == 'cancelled': return 'Cancelada'
        if any(p.get('status') in {'in_mediation', 'charged_back'} for p in pagos): return 'En reclamo'
        if est == 'delivered': return 'Entregada'
        if est == 'shipped': return 'En camino'
        return 'Por despachar' if pagos else 'Sin pago'
    grupo = str(ordenes[0].get('pack_id') or ordenes[0]['id'])
    # Una orden con varios ítems también necesita detalle, sin repetir la plata.
    cabecera = len(ordenes) > 1 or sum(len(o['order_items']) for o in ordenes) > 1
    filas = []
    if cabecera:
        filas.append(dict(base, id_venta=grupo, id_pack=grupo, estado=f"Paquete de {sum(len(o['order_items']) for o in ordenes)} productos"))
    for orden in sorted(ordenes, key=lambda o: str(o['id'])):
        for item in orden['order_items']:
            producto = item['item']
            fila = dict(base, id_venta=str(orden['id']) if cabecera else grupo, id_pack=grupo if cabecera else '',
                fecha_venta=fecha(orden.get('date_closed')), estado=estado(orden), sku=producto.get('seller_sku') or '',
                id_publicacion=str(producto['id']), titulo=producto.get('title', ''),
                variante=' | '.join(f"{a['name']} : {a['value_name']}" for a in producto.get('variation_attributes', [])),
                unidades=str(item['quantity']), precio_unitario=monto(item['unit_price']))
            if cabecera:
                fila.update(dict.fromkeys(IMPORTES + ['descuadrada'], ''))
            filas.append(fila)
    return filas, descuadrada


def pagos_envio_validos(pagos):
    return list({str(p['id']): p for p in pagos if p.get('description') == 'marketplace_shipment'
                 and p.get('status') in VALIDOS}.values())


def buscar_pago_envio(orden, pagos, costos):
    receptor = decimal(costos.get('receiver', {}).get('cost'))
    productos = sum(decimal(i['unit_price']) * decimal(i['quantity']) for i in orden['order_items'])
    cobrado = sum(decimal(p.get('transaction_amount')) for p in pagos if p.get('status') in VALIDOS)
    return receptor > 0 and cobrado < productos + receptor - 1


def refrescar(orden, guardada, pagos, envio, completo, hoy):
    """Volvemos a mirar lo reciente, lo que cambió o lo que todavía puede resolverse."""
    final = not (orden.get('shipping') or {}).get('id') or envio.get('status') in {'delivered', 'cancelled'} or (
        envio.get('status') == 'not_delivered' and envio.get('substatus') == 'returned')
    return (not guardada or not completo or
            guardada.get('date_last_updated') != orden.get('date_last_updated') or
            not orden.get('date_closed') or instante(orden['date_closed']).date() >= hoy - dt.timedelta(days=15) or
            not final or any(p.get('status') in {'in_mediation', 'charged_back'} for p in pagos))


def bajar(sesion, carpeta, desde, hasta, ultima=None):
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    def pedir(ruta, fuente='mercadolibre'):
        host = 'https://api.mercadolibre.com' if fuente == 'mercadolibre' else 'https://api.mercadopago.com'
        return sesion.pedir(fuente, host + ruta, _http)
    vendedor = meli_oauth.estado(sesion.cliente, 'mercadolibre')['user_id']
    if not vendedor:
        raise ErrorDatos('hay que volver a autorizar Mercado Libre con la cuenta del vendedor')
    ordenes = {str(o['id']): o for p in carpeta.glob('orden-*.json') for o in [json.loads(p.read_text())]}
    # Los últimos 2 meses completos (más el actual) se vuelven a mirar siempre.
    ventana = hasta.replace(day=1)
    for _ in range(2):
        ventana = (ventana - dt.timedelta(days=1)).replace(day=1)
    inicio = max(desde, ventana) if ultima and ordenes else desde
    consultas = [('date_created', *limites(a, b)) for a, b in meses(inicio, hasta)]
    if ultima and ordenes:
        consultas.append(('date_last_updated', instante(ultima) - dt.timedelta(days=2), dt.datetime.now(HORA_BA)))
    nuevas = {}
    for filtro, a, b in consultas:
        offset = 0
        while True:
            params = {'seller': vendedor, f'order.{filtro}.from': a.isoformat(timespec='milliseconds'), f'order.{filtro}.to': b.replace(microsecond=999000).isoformat(timespec='milliseconds'), 'sort': 'date_asc', 'limit': 50, 'offset': offset}
            respuesta = pedir('/orders/search?' + urllib.parse.urlencode(params))
            resultados = respuesta['results']
            nuevas.update({str(o['id']): o for o in resultados})
            offset += len(resultados)
            if offset >= respuesta['paging']['total']: break
            if not resultados: raise ErrorDatos('la búsqueda de ventas quedó incompleta; volver a intentar')
    # Cada orden se guarda recién después de sus detalles: si la corrida se corta a mitad
    # (la primera tarda horas), lo bajado queda y la próxima sigue desde ahí.
    def leer(tipo, ident):
        ruta = carpeta / f'{tipo}-{ident}.json'
        return json.loads(ruta.read_text()) if ident and ruta.exists() else {}
    hoy = hasta + dt.timedelta(days=1)
    bajados = set()
    for ident, orden in nuevas.items():
        recursos = [('pago', p['id'], '/v1/payments/', 'mercadopago') for p in orden.get('payments', [])]
        envio = (orden.get('shipping') or {}).get('id')
        if envio:
            recursos += [('envio', envio, '/shipments/', 'mercadolibre'), ('costos', envio, '/shipments/', 'mercadolibre')]
        guardada = ordenes.get(ident)
        pagos = [leer('pago', p['id']) for p in orden.get('payments', [])]
        completo = all((carpeta / f'{t}-{i}.json').exists() for t, i, _, _ in recursos)
        necesita = envio and completo and buscar_pago_envio(orden, pagos, leer('costos', envio))
        if necesita:
            completo = (carpeta / f'envio_pagos-{envio}.json').exists()
        aparte = pagos_envio_validos(leer('envio_pagos', envio).get('results', []))
        if not refrescar(orden, guardada, pagos + aparte, leer('envio', envio), completo, hoy):
            continue
        for tipo, ident_recurso, prefijo, fuente in recursos:
            clave = f'{tipo}-{ident_recurso}'
            if clave not in bajados:
                dato = pedir(prefijo + urllib.parse.quote(str(ident_recurso), safe='') + ('/costs' if tipo == 'costos' else ''), fuente)
                guardar_json(carpeta / (clave + '.json'), dato)
                bajados.add(clave)
        pagos = [leer('pago', p['id']) for p in orden.get('payments', [])]
        if envio and buscar_pago_envio(orden, pagos, leer('costos', envio)):
            clave = f'envio_pagos-{envio}'
            if clave not in bajados:
                dato = pedir('/v1/payments/search?' + urllib.parse.urlencode({'external_reference': envio}), 'mercadopago')
                guardar_json(carpeta / (clave + '.json'), dato)
                bajados.add(clave)
        guardar_json(carpeta / f'orden-{ident}.json', orden)
    ordenes.update(nuevas)
    # Órdenes viejas que ya estaban en la caché antes de que existiera la búsqueda del pago de
    # envío aparte: se completan una sola vez (después ya queda el archivo y no se vuelve a pedir).
    for orden in ordenes.values():
        envio = (orden.get('shipping') or {}).get('id')
        if not envio or not orden.get('date_closed') or not desde <= instante(orden['date_closed']).date() <= hasta:
            continue
        clave = f'envio_pagos-{envio}'
        if clave in bajados or (carpeta / (clave + '.json')).exists():
            continue
        pagos = [leer('pago', p['id']) for p in orden.get('payments', [])]
        if buscar_pago_envio(orden, pagos, leer('costos', envio)):
            dato = pedir('/v1/payments/search?' + urllib.parse.urlencode({'external_reference': envio}), 'mercadopago')
            guardar_json(carpeta / (clave + '.json'), dato)
            bajados.add(clave)
    grupos = {}
    for orden in ordenes.values():
        if orden.get('date_closed') and desde <= instante(orden['date_closed']).date() <= hasta:
            grupos.setdefault(str(orden.get('pack_id') or orden['id']), []).append(orden)
    bloques, descuadradas = [], 0
    for grupo in grupos.values():
        envios = {(o.get('shipping') or {}).get('id') for o in grupo} - {None}
        if len(envios) > 1: raise ErrorDatos('un paquete tiene varios envíos; revisar antes de sumar sus importes')
        envio = next(iter(envios), None)
        pagos = [leer('pago', p['id']) for o in grupo for p in o.get('payments', [])]
        filas, descuadre = armar_venta(grupo, pagos, leer('envio', envio), leer('costos', envio), leer('envio_pagos', envio).get('results', []))
        bloques.append(filas)
        descuadradas += int(descuadre)
    bloques.sort(key=lambda filas: (filas[0]['fecha_venta'], filas[0]['id_venta']))
    return [f for bloque in bloques for f in bloque], descuadradas
