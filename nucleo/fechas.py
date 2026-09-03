# -*- coding: utf-8 -*-
"""
nucleo.fechas — la regla de negocio de QUÉ días bajar. NO cambiar sin avisar.

Regla (idéntica para todos los bancos):
  - hasta = HOY (o AYER si incluir_hoy=False)
  - desde = la última vez que se bajó con éxito esa empresa, pero como MÍNIMO
    AYER (así siempre se re-incluye el día anterior y se agarran los movimientos
    que se postean tarde). Si estuvo días sin correr (finde/feriado/PC apagada)
    rellena desde la última corrida. El solape NO duplica (dedup del clasificador).
"""

import datetime


def dia_objetivo(hoy, incluir_hoy):
    ayer = hoy - datetime.timedelta(days=1)
    return hoy if incluir_hoy else ayer


def rango_a_bajar(ultimo_iso, hoy, incluir_hoy, backfill):
    """Devuelve (desde, hasta) para una empresa, o None si ya está al día.

    ultimo_iso: 'AAAA-MM-DD' de la última bajada con éxito, o None (primera vez).
    """
    ayer = hoy - datetime.timedelta(days=1)
    hasta = dia_objetivo(hoy, incluir_hoy)

    if ultimo_iso:
        desde = min(ayer, datetime.date.fromisoformat(ultimo_iso))
    else:
        desde = ayer  # primera vez: ayer + hoy

    if backfill and backfill > 0:
        desde = min(desde, hasta - datetime.timedelta(days=backfill))

    if desde > hasta:
        return None  # ya al día, no hay nada nuevo
    return desde, hasta
