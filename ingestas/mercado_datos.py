"""Bajada diaria. Cada fuente conserva su CSV anterior si no pudo completarse."""
import argparse
import csv
import datetime as dt
import io
import json
from pathlib import Path
import sys
from ingestas import meli_oauth, meli_ventas as ml, mp_liquidaciones as mp


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
    parser.add_argument('--solo', choices=['mercadolibre', 'mercadopago'])
    args = parser.parse_args(argv)
    ahora = dt.datetime.now(ml.HORA_BA)
    hasta = ahora.date() - dt.timedelta(days=1)
    try:
        sesion = ml.Sesion(args.cliente)
        control_ruta = args.salida / 'control.json'
        control = json.loads(control_ruta.read_text(encoding='utf-8')) if control_ruta.exists() else {}
        control.setdefault('fuentes', {})
    except Exception:
        print('No se pudo preparar la corrida: revisar el cliente y control.json.', file=sys.stderr)
        return 1
    control['corrida'] = ml.fecha(ahora.isoformat())
    ventas = None
    fallo = False
    for fuente in ('mercadolibre', 'mercadopago'):
        if args.solo and fuente != args.solo: continue
        carpeta = meli_oauth.BASE_REPO / 'clientes' / args.cliente / '.run' / fuente
        # El avance queda en liquidaciones, junto a los reportes, separado por fuente.
        marca = meli_oauth.BASE_REPO / 'clientes' / args.cliente / '.run/mercadopago/liquidaciones' / ('ultima-' + fuente + '.json')
        ruta = args.salida / ('ml_ventas.csv' if fuente == 'mercadolibre' else 'mp_movimientos.csv')
        resumen = dict(ok=False, filas=0, desde='', hasta='', motivo='')
        if fuente == 'mercadolibre': resumen['descuadradas'] = 0
        try:
            if args.desde > hasta: raise ml.ErrorDatos('la fecha desde debe ser anterior a hoy')
            if fuente == 'mercadolibre':
                anterior = json.loads(marca.read_text()) if marca.exists() else {}
                # Si se amplía el período, volver a buscar lo que antes no se había pedido.
                ultima = anterior.get('corrida') if anterior.get('desde', '9999') <= args.desde.isoformat() else None
                filas, resumen['descuadradas'] = ml.bajar(sesion, carpeta / 'cache', args.desde, hasta, ultima)
                columnas, campo_fecha = ml.COLUMNAS, 'fecha_venta'
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
                ml.guardar_json(marca, dict(corrida=ahora.isoformat(), desde=args.desde.isoformat()))
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
        if resumen['motivo']:
            resumen['ok'] = False
            fallo = True
        control['fuentes'][fuente] = resumen
        print(f"{fuente}: {resumen['filas']} filas" + (f", {resumen['descuadradas']} descuadradas" if fuente == 'mercadolibre' else '') + (f"; {resumen['motivo']}" if resumen['motivo'] else ''))
    try:
        ml.guardar_json(control_ruta, control)
    except OSError:
        print('No se pudo guardar control.json; revisar la carpeta de salida.', file=sys.stderr)
        return 1
    return int(fallo)


if __name__ == '__main__':
    sys.exit(main())
