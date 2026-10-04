# Tarea 41 — El mail diario no pide el arqueo de caja AA
Estado: aprobada (mergeada e instalada en Apps Script el 01/10/2026)
Rama: tarea/aviso-sin-arqueo

## Objetivo

Sacar del mail diario la línea "Arqueo caja AA". Pedido de Thomas (01/10/2026): el arqueo se consigue
por fuera y no hace falta que el mail lo pida. Además la regla pedía un arqueo de cada día hábil y el
conteo se hace semanal, así que salía en ❌ todos los días.

## Archivos permitidos

- `clientes/navar/herramientas/aviso_diario.gs` — solo la línea del arqueo en `_armarAviso_`.
- `lector/pruebas/probar_aviso_bajadas.cjs`
- `tareas/41-aviso-sin-arqueo.md`

## Resultado esperado

- El mail no tiene línea de arqueo. Las filas de caja AA de Saldos Bancarios siguen sin contarse como
  banco. La caja AA del cash (Sheet y tablero) no cambia: sigue siendo último arqueo + Tango AA.
- Pruebas: una casilla menos por mail; un arqueo viejo ya no suma faltantes.

## Qué hice

- `aviso_diario.gs`: se sacó la llamada que armaba la línea del arqueo (queda un comentario con el
  porqué). Las filas de caja AA de Saldos Bancarios se siguen salteando como banco.
- Pruebas: 5 casillas por mail en vez de 6; un arqueo viejo ya no cuenta como faltante. Todo OK con el
  Node de la app de ChatGPT.
- Instalado en Apps Script (el editor tenía la versión de la tarea 39) y probado con datos reales:
  `NAVAR · 01/10 · faltan 2 cosas` (BBVA y Nación), sin línea de arqueo; Corrientes ya ☑ al 30/09.

## Revisión

**Claude, 01/10/2026.** Cambio mínimo, pedido por Thomas. Aprobada.
