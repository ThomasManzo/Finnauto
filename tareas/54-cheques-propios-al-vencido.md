# Tarea 54 — Los cheques propios vencidos suman al vencido del tablero
Estado: aprobada e instalada (07/10/2026 02:01: el link muestra el tablero nuevo)
Rama: tarea/cheques-propios-al-vencido

## Objetivo

Que el vencido del tablero sea igual al atrasado del Cash. La diferencia eran los cheques propios con
fecha de pago pasada y sin debitar: el Cash los cuenta ("Cheques propios vencidos sin debitar") y el
tablero los mandaba a Hallazgos. Pedido de Thomas, 07/10/2026: "sumalo al vencido".

## Archivos permitidos

`lector/cash_limpio.py`, `dashboard/datos.py`, `dashboard/app.py`,
`lector/pruebas/test_tablero_cajas_deuda.py`, esta consigna.

## Resultado esperado

- Un cheque **propio** marcado REVISAR (fecha de pago pasada) ya no se descarta: entra como salida
  vencida, igual que cualquier cheque propio con fecha pasada. Los de **terceros** con fecha pasada
  siguen en Hallazgos: no son deuda.
- Posición, "Vencido e impago": cuarta fila "Cheques propios sin debitar" (riesgo de rechazo: multa y
  cuenta inhabilitada). El título deja de decir "las tres puntas".
- Proyección: el texto del stock vencido nombra los cheques propios.

## Comprobaciones

- Prueba con datos inventados:
  - un cheque propio con fecha pasada va al vencido;
  - uno de terceros sigue en Hallazgos;
  - el stock lo cuenta como "cheques".
- Con la copia del día de la Sheet: el vencido total del tablero es igual al atrasado del Cash.

## Qué hice
**La escribió Claude.**
- `cash_limpio.py`: el REVISAR de cheques solo saltea los de terceros.
- `datos.py`: `por_tipo["cheques"]` y la cuarta fila del resumen de vencidos.
- `app.py`: los textos.
- Prueba nueva en `test_tablero_cajas_deuda.py`.
- Verificado con la copia del día (no se sube): el total vencido del tablero coincide peso por peso
  con el del Cash.

## Revisión
