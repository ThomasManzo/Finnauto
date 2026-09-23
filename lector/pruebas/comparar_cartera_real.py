"""Compara dos exports en memoria. Solo imprime cantidades y totales, sin datos de cheques.

Uso: python -m lector.pruebas.comparar_cartera_real BUENO MALO --hoy 2026-09-22
No escribe en Drive ni genera archivos para importar.
"""
import argparse
from collections import Counter
from decimal import Decimal
from unittest.mock import patch

from lector import tango


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('bueno')
    ap.add_argument('malo')
    ap.add_argument('--hoy', required=True)
    args = ap.parse_args()
    resultados = []
    for etiqueta, ruta in [('bueno', args.bueno), ('malo', args.malo)]:
        # Pasamos un solo export por vez al circuito normal, sin copiar datos reales.
        with patch.object(tango, 'localizar', return_value={('A', 'cheques_terceros'): ruta}):
            res = tango.procesar('', 'navar', args.hoy)
        filas = res['listas']['cheques']
        desc = res['descartes'][('A', 'cheques_terceros')]
        revisar = [f for f in filas if f['Observaciones'].startswith(tango.MARCA_REVISAR)]
        cash = [f for f in filas if not f['Observaciones'].startswith(tango.MARCA_REVISAR)]
        monto = lambda fs: sum((Decimal(str(f['Importe'])) for f in fs), Decimal(0))
        print(etiqueta, 'leídas=', len(filas) + sum(n for n, _ in desc.values()),
              'entran a lista=', len(filas), 'descartadas=', sum(n for n, _ in desc.values()),
              'REVISAR=', len(revisar), 'habilitadas cash=', len(cash),
              'importe lista=', monto(filas), 'importe cash=', monto(cash))
        for motivo, (n, _) in desc.items():
            print(' ', n, motivo)
        # Comparamos todas las columnas salvo ID y origen; el orden no cambia la igualdad.
        clave = lambda f: tuple((k, v) for k, v in f.items() if k not in ('ID', 'Observaciones'))
        resultados.append(Counter(clave(f) for f in cash))
    print('Filas cash idénticas=', resultados[0] == resultados[1],
          'solo bueno=', sum((resultados[0] - resultados[1]).values()),
          'solo malo=', sum((resultados[1] - resultados[0]).values()))


if __name__ == '__main__':
    main()
