"""Publicidad por día: conservamos lo antiguo porque la API solo deja mirar 90 días."""
import datetime as dt
import json
from pathlib import Path
import urllib.parse
from ingestas import meli_ventas as ml

METRICAS = 'clicks,prints,cost,direct_units_quantity,indirect_units_quantity,organic_units_quantity,direct_amount,indirect_amount,total_amount'
COLUMNAS = 'fecha,id_publicacion,costo,clics,unidades_directas,unidades_indirectas,unidades_organicas,ventas_por_anuncio'.split(',')


def _http(pedido):
    return ml._http(pedido)


def metricas(registro):
    return registro.get('metrics', registro)


def tiene_movimiento(registro):
    return any(ml.decimal(metricas(registro).get(k)) != 0 for k in METRICAS.split(','))


def armar_filas(acumulado, desde, hasta):
    filas = []
    for item, dias in acumulado.items():
        for fecha, registro in dias.items():
            if not desde.isoformat() <= fecha <= hasta.isoformat() or not tiene_movimiento(registro):
                continue
            m = metricas(registro)
            filas.append(dict(zip(COLUMNAS, [fecha, item, ml.monto(abs(ml.decimal(m.get('cost')))),
                m.get('clicks', 0), m.get('direct_units_quantity', 0), m.get('indirect_units_quantity', 0),
                m.get('organic_units_quantity', 0), ml.monto(m.get('total_amount'))])))
    return sorted(filas, key=lambda f: (f['fecha'], f['id_publicacion']))


def bajar(sesion, carpeta, desde, hasta):
    carpeta = Path(carpeta)
    inicio = max(desde, hasta + dt.timedelta(days=1) - dt.timedelta(days=89))
    def pedir(ruta, version, **params):
        return sesion.pedir('mercadolibre', 'https://api.mercadolibre.com' + ruta + '?' +
                            urllib.parse.urlencode(params), _http, encabezados={'Api-Version': str(version)})
    anunciantes = pedir('/advertising/advertisers', 1, product_id='PADS')['advertisers']
    if not anunciantes:
        return []
    acumulado = {p.stem: json.loads(p.read_text(encoding='utf-8')) for p in carpeta.glob('*.json')}
    nuevos = {}
    for anunciante in anunciantes:
        sitio = urllib.parse.quote(str(anunciante['site_id']), safe='')
        ident = urllib.parse.quote(str(anunciante['advertiser_id']), safe='')
        ruta = f'/advertising/{sitio}/advertisers/{ident}/product_ads/ads/search'
        params = dict(date_from=inicio.isoformat(), date_to=hasta.isoformat(), metrics=METRICAS)
        offset, avisos = 0, {}
        while True:
            respuesta = pedir(ruta, 2, limit=100, offset=offset, **params)
            resultados = respuesta['results']
            avisos.update({str(r['item_id']): r for r in resultados})
            offset += len(resultados)
            if offset >= respuesta['paging']['total']: break
            if not resultados: raise ml.ErrorDatos('la búsqueda de publicidad quedó incompleta')
        totales = {}
        for item, aviso in avisos.items():
            # Pisamos también los días que ahora quedaron en cero; no deben conservar gasto viejo.
            dias = {}
            if tiene_movimiento(aviso):
                detalle = pedir(f'/advertising/{sitio}/product_ads/ads/{urllib.parse.quote(item, safe="")}',
                                2, aggregation_type='DAILY', **params)
                dias = {r['date'][:10]: metricas(r) for r in detalle['results']}
            nuevos[item] = dias
            for fecha, m in dias.items():
                totales[fecha] = totales.get(fecha, ml.decimal(0)) + ml.decimal(m.get('cost'))
        control = pedir(ruta, 2, limit=1, aggregation_type='DAILY', **params)
        esperados = {r['date'][:10]: ml.decimal(metricas(r).get('cost')) for r in control['results']}
        if any(abs(totales.get(d, 0) - esperados.get(d, 0)) > 1 for d in totales.keys() | esperados.keys()):
            raise ml.ErrorDatos('el costo diario de los avisos no coincide con el total de publicidad de la cuenta')
    # Primero validamos toda la cuenta; después guardamos lo nuevo y conservamos los días antiguos.
    for item, dias in nuevos.items():
        anteriores = acumulado.setdefault(item, {})
        for dia in list(anteriores):
            if inicio.isoformat() <= dia <= hasta.isoformat(): del anteriores[dia]
        anteriores.update(dias)
        ml.guardar_json(carpeta / (item + '.json'), anteriores)
    return armar_filas(acumulado, desde, hasta)
