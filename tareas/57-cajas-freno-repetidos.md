# Tarea 57 — Las cajas se frenan si el detalle de Tango trae renglones repetidos
Estado: aprobada (falta actualizar la notebook)
Rama: tarea/cajas-freno-repetidos

## Objetivo
Igual que el cruce (tarea 55): si el detalle de tesorería trae renglones repetidos enteros, la bajada
vino mal y `lector/cajas.py` no publica ninguna caja (el vigilante lo anota como falla y reintenta con
el archivo siguiente). Así una bajada rota no infla ni vacía los movimientos de caja.

## Qué hice
**La escribió Claude.** `leer_detalle` cuenta los renglones repetidos enteros y, si hay, corta con un
error claro. Prueba nueva en `test_cajas.py` con datos inventados.
