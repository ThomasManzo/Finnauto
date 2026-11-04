"""Bajada diaria. Cada fuente conserva su CSV anterior si no pudo completarse.
Con --solo-pendientes se repite solamente lo que todavía no salió bien hoy.
"""
import argparse
import csv
import datetime as dt
import io
import json
from pathlib import Path
import sys
from ingestas import dolar, galicia_datos as galicia
from ingestas import meli_oauth, meli_ventas as ml, mp_liquidaciones as mp, meli_publicidad as ads, tiendanube as tn


def escribir_csv(ruta, columnas, filas):
    texto = io.StringIO(newline='')
    escritor = csv.DictWriter(texto, fieldnames=columnas)
    escritor.writeheader()
    escritor.writerows(filas)
    ml.atomico(ruta, texto.getvalue().encode('utf-8'))


def leer_csv(ruta):
    if not ruta.exists():
        return []
    with ruta.open(encoding='utf-8', newline='') as archivo:
        return list(csv.DictReader(archivo))


def main(argv=None):
    parser = argparse.ArgumentParser(description='Ventas y liquidaciones a CSV')
    parser.add_argument('--cliente', required=True)
    parser.add_argument('--salida', required=True, type=Path)
    parser.add_argument('--desde', type=dt.date.fromisoformat, default=dt.date(2025, 10, 1))
    parser.add_argument('--solo', choices=['mercadolibre', 'mercadopago', 'mercadolibre_publicidad', 'tiendanube', 'galicia', 'dolar'])
    parser.add_argument('--solo-pendientes', action='store_true')
    args = parser.parse_args(argv)
    ahora = dt.datetime.now(ml.HORA_BA)
    hasta = ahora.date() - dt.timedelta(days=1)
    try:
        sesion = ml.Sesion(args.cliente)
        control_ruta = args.salida / 'control.json'
        control = json.loads(control_ruta.read_text(encoding='utf-8')) if control_ruta.exists() else {}
        control.setdefault('fuentes', {})
        estado_ruta = meli_oauth.BASE_REPO / 'clientes' / args.cliente / '.run/mercado_datos_estado.json'
        estado = json.loads(estado_ruta.read_text(encoding='utf-8')) if estado_ruta.exists() else {}
        if not isinstance(estado, dict):
            raise ValueError('estado inválido')
    except Exception:
        print('No se pudo preparar la corrida: revisar el cliente, control.json y el estado de las bajadas.', file=sys.stderr)
        return 1
    intentadas = 0
    control_cambio = False
    ventas = None
    fallo = False
    for fuente in ('mercadolibre', 'mercadopago', 'mercadolibre_publicidad', 'tiendanube', 'galicia', 'dolar'):
        if args.solo and fuente != args.solo: continue
        if args.solo_pendientes and estado.get(fuente) == ahora.date().isoformat():
            # Mercado Pago vincula sus pagos con ml_ventas.csv. Si Mercado Libre se acaba de bajar bien
            # en esta corrida, se rehace Mercado Pago para que las ventas nuevas no queden sin vincular.
            if not (fuente == 'mercadopago' and ventas is not None):
                continue
        carpeta = meli_oauth.BASE_REPO / 'clientes' / args.cliente / '.run' / fuente
        # El avance queda en liquidaciones, junto a los reportes, separado por fuente.
        marca = meli_oauth.BASE_REPO / 'clientes' / args.cliente / '.run/mercadopago/liquidaciones' / ('ultima-' + fuente + '.json')
        ruta = args.salida / {'mercadolibre': 'ml_ventas.csv', 'mercadopago': 'mp_movimientos.csv', 'mercadolibre_publicidad': 'ml_publicidad.csv', 'tiendanube': 'tn_ordenes.csv', 'galicia': 'galicia_movimientos.csv', 'dolar': 'dolar.csv'}[fuente]
        resumen = dict(ok=False, filas=0, desde='', hasta='', motivo='')
        if fuente == 'mercadolibre': resumen['descuadradas'] = 0
        if fuente == 'tiendanube': resumen['raras'] = 0
        if fuente == 'galicia': resumen['ultima_descarga'] = ''
        try:
            if fuente == 'tiendanube' and (not tn.tiene_aplicacion(args.cliente)
                    or not tn.estado(args.cliente)['hay_token']):
                control_cambio |= fuente in control['fuentes']
                control['fuentes'].pop(fuente, None)
                continue
            if fuente == 'galicia':
                cfg = galicia.configuracion(meli_oauth.BASE_REPO, args.cliente)
                if cfg is None:
                    control_cambio |= fuente in control['fuentes']
                    control['fuentes'].pop(fuente, None)
                    continue
                filas, saldos, resumen = galicia.leer(cfg, args.salida, ahora.date())
                escribir_csv(ruta, galicia.COLUMNAS_MOVIMIENTOS, filas)
                escribir_csv(args.salida / 'galicia_saldo.csv', galicia.COLUMNAS_SALDO, saldos)
            else:
                if args.desde > hasta: raise ml.ErrorDatos('la fecha desde debe ser anterior a hoy')
                if fuente == 'mercadolibre':
                    anterior = json.loads(marca.read_text()) if marca.exists() else {}
                    # Si se amplía el período, volver a buscar lo que antes no se había pedido.
                    ultima = anterior.get('corrida') if anterior.get('desde', '9999') <= args.desde.isoformat() else None
                    filas, resumen['descuadradas'] = ml.bajar(sesion, carpeta / 'cache', args.desde, hasta, ultima)
                    columnas, campo_fecha = ml.COLUMNAS, 'fecha_venta'
                elif fuente == 'dolar':
                    filas = dolar.bajar(args.salida, args.desde, hasta)
                    columnas, campo_fecha = dolar.COLUMNAS, 'fecha'
                elif fuente == 'tiendanube':
                    sesion_tn = tn.Sesion(args.cliente)
                    marca = carpeta / 'cache' / 'ultima.json'
                    anterior = json.loads(marca.read_text(encoding='utf-8')) if marca.exists() else {}
                    ultima = anterior.get('corrida') if (anterior.get('desde', '9999') <= args.desde.isoformat()
                        and anterior.get('store_id') == sesion_tn.permiso['store_id']) else None
                    filas, resumen['raras'] = tn.bajar(sesion_tn, carpeta / 'cache', args.desde, hasta, ultima)
                    columnas, campo_fecha = tn.COLUMNAS, 'fecha'
                elif fuente == 'mercadolibre_publicidad':
                    carpeta = meli_oauth.BASE_REPO / 'clientes' / args.cliente / '.run/mercadolibre/publicidad'
                    filas = ads.bajar(sesion, carpeta, args.desde, hasta)
                    columnas, campo_fecha = ads.COLUMNAS, 'fecha'
                else:
                    if ventas is None: ventas = leer_csv(args.salida / 'ml_ventas.csv')
                    filas, motivo = mp.bajar(sesion, carpeta / 'liquidaciones', args.desde, hasta, ventas)
                    if motivo: raise ml.ErrorDatos(motivo)
                    columnas, campo_fecha = mp.COLUMNAS, 'fecha_liquidacion'
                escribir_csv(ruta, columnas, filas)
                if fuente == 'mercadolibre': ventas = filas
                fechas = [f[campo_fecha][:10] for f in filas if f[campo_fecha]]
                resumen.update(ok=True, filas=len(filas), desde=min(fechas, default=''), hasta=max(fechas, default=''))
                try:
                    avance = dict(corrida=ahora.isoformat(), desde=args.desde.isoformat())
                    if fuente == 'tiendanube': avance['store_id'] = sesion_tn.permiso['store_id']
                    ml.guardar_json(marca, avance)
                except OSError:
                    # El CSV ya está completo. Sin marca se repite la búsqueda en la
                    # próxima corrida; eso cuesta tiempo pero no pierde movimientos.
                    print(f'{fuente}: no se pudo guardar el avance; se volverá a buscar en la próxima corrida.')
        except meli_oauth.ErrorAutorizacion as exc:
            resumen['motivo'] = 'hay que volver a autorizar o revisar el permiso: ' + exc.motivo
        except ml.ErrorDatos as exc:
            resumen['motivo'] = str(exc)
        except Exception:
            resumen['motivo'] = 'no se pudo completar la fuente; revisar los archivos, el formato y la conexión'
        intentadas += 1
        if resumen['ok'] and not resumen['motivo']:
            # Recién con los CSV escritos damos el día por terminado para esta fuente.
            estado[fuente] = ahora.date().isoformat()
            try:
                ml.guardar_json(estado_ruta, estado)
            except OSError:
                print(f'{fuente}: no se pudo guardar el estado; se volverá a intentar en la próxima corrida.')
        if resumen['motivo']:
            resumen['ok'] = False
            fallo = True
        control['fuentes'][fuente] = resumen
        print(f"{fuente}: {resumen['filas']} filas" + (f", {resumen['descuadradas']} descuadradas" if fuente == 'mercadolibre' else '') + (f"; {resumen['motivo']}" if resumen['motivo'] else ''))
    if intentadas:
        control['corrida'] = ml.fecha(ahora.isoformat())
    elif args.solo_pendientes and not control_cambio:
        print('Nada pendiente: todo se bajó bien hoy.')
        return 0
    try:
        ml.guardar_json(control_ruta, control)
    except OSError:
        print('No se pudo guardar control.json; revisar la carpeta de salida.', file=sys.stderr)
        return 1
    return int(fallo)


if __name__ == '__main__':
    sys.exit(main())
