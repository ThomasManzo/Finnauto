# Tarea 42 — Un banco manual está al día si se subió el extracto, aunque ese día no haya movimientos
Estado: en curso (la escribe Claude: Codex sin cupo desde la 37)
Rama: tarea/aviso-subido

## Objetivo

El mail marcaba un banco manual como atrasado por la fecha de su **último movimiento**. Si el último
día hábil no tuvo movimientos, quedaba en ❌ aunque el extracto estuviera subido (BBVA, 01/10/2026:
archivo del 30/09, último movimiento el 29/09). Thomas: "si no hay movimiento es porque no hay".

## Archivos permitidos

- `clientes/navar/herramientas/aviso_diario.gs` — solo `manual()` en `_armarAviso_`.
- `lector/pruebas/probar_aviso_bajadas.cjs`
- `tareas/42-aviso-extracto-subido-sin-movimientos.md`

## Resultado esperado

- Banco manual en ✅ si el último movimiento es del último día hábil **o** si en `Bancos/<banco>/` hay un
  extracto (pdf/xls/xlsx/csv) con fecha de Drive de ese día o posterior. Texto: `al día, extracto
  subido el dd/mm (último movimiento dd/mm)`.
- En ❌, la antigüedad se cuenta desde lo más nuevo de las dos fechas.
- Los ilegibles (tarea 39) siguen teniendo prioridad en el texto del ❌.

## Qué hice

## Revisión
