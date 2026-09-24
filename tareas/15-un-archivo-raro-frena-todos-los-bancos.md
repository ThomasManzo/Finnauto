# Tarea 15 — Un export con otras columnas frena la lectura de TODOS los bancos
Estado: pendiente
Rama: tarea/bancos-tolerantes

## Objetivo

Desde las **17:36 del 23/09** el vigilante falla cada 15 minutos y **no procesa ningún banco**:

```
2026-09-23 22:38:07  bancos: 26 archivo(s) nuevos o cambiados → extractos.py
2026-09-23 22:38:09  bancos: FALLÓ (código 1): KeyError: 'Detalle'
```

Dos problemas, y el segundo es más grave que el primero:

**A.** El export nuevo de un banco trae **otros nombres de columna** y el lector revienta.
**B.** Un solo archivo ilegible **tumba la corrida entera**: los otros cuatro bancos, que están
perfectos, tampoco se procesan. Un archivo raro tiene que quedar afuera con un aviso, no frenar todo.

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `CLAUDE.md`.

El archivo que rompe es `Bancos/bbva/Movimientos BBVA 2026-09-23.xls`, y la causa está medida:

| Export | Columnas (fila 7) |
|---|---|
| BBVA hasta el 22/09 | `Fecha · Fecha Valor · Concepto · Codigo · Número Documento · Oficina · Crédito · Débito · Detalle` |
| BBVA del 23/09 | `Fecha · Fecha Valor · Concepto · Codigo · Nro de cheque · Oficina · Crédito · Débito · Saldo Parcial` |

`leer_planilla_bbva` (en `lector/extractos.py`, alrededor de la línea 179) hace `ix["Detalle"]` y
tira `KeyError` porque esa columna ya no existe.

El archivo nuevo, entero (tiene una sola fila de movimiento):

```
Empresa:          NAVAR SA(30558525025)
Cuenta:           489-000765/9(CC $)
Sucursal:         489 - EMPRESA POSADAS
Saldo:            -3.502.551,25
Movimientos de:   23-09-2026

Fecha       Fecha Valor  Concepto              Codigo  Nro de cheque  Oficina  Crédito     Débito  Saldo Parcial
23-09-2026  23-09-2026   TRANSFERENCIA CUENTA  842                    489-…    4.538.200           -8.040.751,25
```

Ojo con algo importante: en el formato viejo el saldo del día se sacaba buscando el texto
`Saldo Disponible: …` dentro de la columna `Detalle`. En este formato **el saldo viene en su propia
columna** (`Saldo Parcial`), que es más directo. Y además el encabezado trae `Saldo: -3.502.551,25`,
que **no coincide** con el `Saldo Parcial` de la fila (-8.040.751,25): decidir cuál se usa como
cierre del día y explicar por qué. (Probablemente uno es el saldo disponible y el otro el contable;
no inventar: si no se puede determinar, marcarlo para revisar y no pisar el saldo bueno.)

Este mismo problema ya apareció dos veces esta semana con los exports de Tango (columnas que cambian
de orden y de nombre entre descargas). **Es un patrón, no un caso aislado.**

## Archivos permitidos

- `lector/extractos.py`
- `clientes/navar/herramientas/vigilante.py` — sólo para que un lector que falla no impida que
  se publique lo que sí se pudo leer, si es que eso se resuelve ahí.
- `lector/pruebas/`
- `clientes/navar/documentos/manual_cash.md`
- `tareas/15-un-archivo-raro-frena-todos-los-bancos.md`

No tocar `lector/cash_limpio.py` ni `dashboard/` (los está tocando la tarea 14), ni
`importar_cashflow.gs`, ni `crear_cash.gs`.

## Resultado esperado

1. **B primero**: un archivo que no se puede leer se **saltea**, se cuenta y se informa en el
   resumen (`no pude leer <archivo>: <motivo>`), y **la corrida sigue** con el resto. Que el
   vigilante publique lo que sí se leyó. Si ningún archivo de un banco se pudo leer, ese banco
   queda sin datos nuevos, pero los otros cuatro tienen que entrar igual.
2. **A**: `leer_planilla_bbva` acepta los dos formatos. Las columnas se buscan por nombre entre
   alternativas (`Detalle` o `Saldo Parcial`; `Número Documento` o `Nro de cheque`), y si falta
   una que no es imprescindible, se sigue sin ella en vez de cortar.
3. Revisar los otros lectores de planilla (Macro, Galicia) con el mismo criterio: hoy cualquiera
   de ellos se cae igual si el banco cambia un encabezado.
4. Prueba automática: un Excel chico armado por la prueba con cada formato (el viejo, el nuevo, y
   uno con una columna imprescindible ausente) → el tercero se saltea con aviso y los dos primeros
   se leen bien.

## Comprobaciones

1. Correr el lector sobre una **copia** de la carpeta real de bancos (no sobre Drive) y pegar en
   "Qué hice": cuántos archivos se leyeron, cuántos se saltearon y por qué, y el último saldo por
   banco. Antes de esta tarea el resultado era: **falla total, cero bancos**. La copia está en
   `/private/tmp/claude-501/-Users-thomasmanzo-Documents-Finnauto/f6552fb9-9e4b-4af5-b4b5-9d35a7af4f0f/scratchpad/bancos`
   (si no está, copiarla desde Drive; **no escribir en Drive**).
2. Decir qué saldo se tomó para BBVA el 23/09 y por qué.
3. `python -m py_compile` y la prueba nueva.
4. `grep` de nombres propios de personas vacío. Commit en la rama.

## Qué hice

## Revisión
