# Tarea 42 — Un banco manual está al día si se subió el extracto, aunque ese día no haya movimientos
Estado: aprobada (mergeada el 01/10/2026; en Apps Script falta el retoque del asunto en singular)
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

- `manual()`: además de la fecha del último movimiento, mira el archivo más nuevo de `Bancos/<banco>/`
  (fecha de Drive), sin contar los que el lector no pudo leer. Si es del último día hábil o posterior,
  el banco está al día: `al día, extracto subido el dd/mm (último movimiento dd/mm)`. En ❌ la
  antigüedad sale de la más nueva de las dos fechas.
- Asunto en singular: `falta 1 cosa`.
- Pruebas: subido después del cierre (✅), subido antes (❌ por movimiento), subido más nuevo que el
  movimiento pero viejo (❌ "subido el"), y un ilegible que no cuenta como subido. Todo OK.
- Instalado en Apps Script y probado con datos reales: `☑ BBVA: al día, extracto subido el 30/09
  (último movimiento 29/09)`; solo falta Nación. **El retoque del asunto en singular no se pudo guardar
  en Apps Script** (el editor no registró el reemplazo en varios intentos): Apps Script tiene la versión
  del commit b22dce8 y el repo la cb4de4c. Se iguala al próximo pegado, o pegando a mano
  `Scripts/aviso_diario.gs.txt`.

## Revisión

**Claude, 01/10/2026.** Aprobada.
