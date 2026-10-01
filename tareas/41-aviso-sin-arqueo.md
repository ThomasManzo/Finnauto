# Tarea 41 — El mail diario no pide el arqueo de caja AA
Estado: en curso (la escribe Claude: Codex sin cupo desde la 37)
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

## Revisión
