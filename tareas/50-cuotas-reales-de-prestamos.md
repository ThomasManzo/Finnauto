# Tarea 50 — Cuotas reales de los préstamos (tablas de amortización de los bancos)
Estado: aprobada
Rama: tarea/cuotas-reales

## Objetivo
Usar las tablas de amortización de los bancos (06/10/2026) para: (1) que la deuda bancaria de la Sheet
tenga las cuotas reales y no estimadas, y (2) que el mail semanal del cruce muestre, para cada cuota de
préstamo que el banco debitó y falta cargar en Tango, su desglose (capital, interés, IVA, percepción).

## Contexto
La administración contestó (06/10) que no carga los débitos de préstamos porque no tiene el desglose: el
banco debita un solo importe. El mapa de deuda solo trae el valor de la cuota y estima las siguientes.
Llegaron: el "Detalle de cuotas" de Galicia (PDF con texto) y el "Informe de deuda" del Nación
(escaneado). Faltan Macro, BBVA y Corrientes.

## Archivos permitidos
`lector/cuotas_prestamos.py` (nuevo), `lector/pruebas/test_cuotas_prestamos.py` (nuevo),
`lector/deuda_bancaria.py`, `lector/cruce_semanal.py`, `lector/pruebas/test_cruce_semanal.py`,
`clientes/navar/herramientas/cruce_semanal.gs`, `lector/pruebas/probar_cruce_semanal.cjs`,
`clientes/navar/herramientas/vigilante.py`.

## Resultado esperado
- Un Excel "Cuotas de prestamos.xlsx" en `NAVAR - Datos/Deuda bancaria/` (fuera de git): una fila por
  cuota con Banco, Línea del mapa (= Producto del mapa), Préstamo, Cuota, Vencimiento, Estado, Fecha de
  pago, Capital, Interés, IVA, Percepción IVA, Otros, Punitorios, Total, Fuente.
- `lector/cuotas_prestamos.py`: leer/escribir la tabla; leer el PDF de Galicia (comando
  `--galicia <pdf> --linea "<producto>"`, verifica que las partes sumen el total); desglose de una cuota;
  qué cuota corresponde a un débito (pagada ese día por ese importe, o del importe con vencimiento
  cercano; si hay dos posibles, ninguna).
- `deuda_bancaria.py`: los préstamos con tabla usan sus cuotas pendientes (capital en "Importe Capital",
  el resto en "Importe Interes", así el total de la Sheet = lo que debita el banco) en lugar de
  estimarlas. Toma la tabla de al lado del mapa (o `--cuotas`). El resumen usa capital + resto.
- `cruce_semanal`: columna "Desglose (tabla del banco)" en "Falta cargar en Tango" y una línea debajo
  de cada cuota en el mail.
- `vigilante.py`: si cambia la tabla de cuotas, rearma la deuda.

## Comprobaciones
Pruebas con datos inventados (cuotas, semanal, `.cjs`). Con datos reales: las cuotas a vencer del Nación
cierran al centavo con el total que imprime el banco; los débitos reales del 04/08, 04/09, 14/09 y 30/09
encuentran su cuota.

## Qué hice
**La escribió Claude.** Todo lo de arriba, con 10 pruebas nuevas (cuotas: 9; semanal: 1) y el caso en el
`.cjs` del mail. La tabla real (Galicia 18 cuotas; Nación: reprogramación 36 y CREAR 40) se armó fuera
del repo: Galicia con el comando; Nación con OCR de macOS y control cuota por cuota contra el total del
banco (las 53 cuotas a vencer cierran). La Sheet calcula "Importe Total Cuota" = capital + interés, que
es lo que usan el Cash y el informe.

## Revisión
06/10/2026: mergeada con el OK de Thomas.
