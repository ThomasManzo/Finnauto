# Tarea 47 — El cruce usa la fecha del movimiento, no la de emisión
Estado: aprobada
Rama: tarea/fecha-movimiento

## Objetivo
Que el cruce banco ↔ Tango compare con la **fecha del movimiento** de Tango ("Fecha", la que se ve en la
pantalla del comprobante) y no con la "Fecha de emisión".

## Contexto
La administración contestó las consultas (06/10/2026) con capturas de Tango: dos "errores de carga" que
marcamos (un año 2036 y un recibo un mes corrido) eran de la **fecha de emisión**; la fecha del
movimiento estaba bien. También explicaron que cargan los débitos con la fecha del débito y la fecha
contable del mes siguiente. La consulta personalizada 21 de Live no traía la columna "Fecha"; Thomas la
agregó el 06/10.

## Archivos permitidos
`ingestas/tango_live.py`, `ingestas/test_tango_live.py`, `lector/cruce.py`, `lector/pruebas/test_cruce.py`.

## Resultado esperado
- La bajada traduce `FECHA` → "Fecha" (primera columna) y la exige: sin ella no publica el detalle.
- El cruce usa "Fecha"; si el archivo no la trae (el export a mano del 18/09), usa "Fecha de emisión" y
  lo avisa en el Resumen y en el `.md`.

## Comprobaciones
Pruebas (74 OK). En la notebook, `--probar detalle_tesoreria --empresa A` tiene que listar `FECHA`.

## Qué hice
**La escribió Claude.** Lo de arriba, con 2 pruebas nuevas del cruce (usa "Fecha" aunque la emisión diga
2036; avisa si falta) y las de la bajada actualizadas.

## Revisión
06/10/2026: mergeada con el OK de Thomas. `--probar` en la notebook confirmó que la consulta 21 trae `FECHA`.
