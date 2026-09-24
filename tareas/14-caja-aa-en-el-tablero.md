# Tarea 14 — La caja de AA dice dos cosas distintas según dónde se mire
Estado: pendiente
Rama: tarea/caja-aa-tablero

## Objetivo

La planilla y el tablero muestran **el mismo concepto con dos números distintos**:

| | Caja en efectivo de AA al 23/09 |
|---|---|
| Planilla (solapa Cash) | **$27.675.788** |
| Tablero web (Posición) | **$12.800.000** |

El correcto es el de la planilla. El del tablero es el **arqueo crudo del 21/09**, sin los
movimientos de caja posteriores.

Que los dos salgan del mismo criterio. Un número que cambia según dónde se mire destruye la
confianza en toda la herramienta, y este se muestra en reuniones.

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `CLAUDE.md`, `clientes/navar/documentos/manual_cash.md`
y `tareas/13-hoy-no-existe-en-el-cash.md` (lo que ya se arregló del lado de la planilla).

**El criterio, ya definido y andando en la planilla:**

> saldo de caja = **último arqueo cargado a mano** + **todos los movimientos de caja posteriores**,
> hasta hoy.

Los movimientos de caja son las filas de la solapa **Movimientos** con Origen que empieza con
`Tango AA` (la tesorería en efectivo de AA, que viene de Tango) y Estado `Real`. El importe ya trae
el signo: los egresos son negativos, así que el neto es una suma directa.

Comprobación numérica del 23/09, para que sirva de caso de prueba:

```
12.800.000   arqueo del 21/09 (Saldos Bancarios, Origen "Manual")
  − 487.000  movimientos del 22/09
+15.362.788  movimientos del 23/09
─────────────
 27.675.788  ← lo que muestra la planilla
```

**Dónde está el número del tablero**: `lector/cash_limpio.py` arma `caja_hoy` y `caja_por_unidad`
tomando, por cuenta, el saldo del último día de la solapa **Saldos Bancarios**. Para las cuentas de
extracto está bien. Para la caja de AA (la cuenta cargada a mano, Origen "Manual") falta sumarle
los movimientos posteriores.

Ojo con no contar dos veces: hay que sumar **sólo** los movimientos **posteriores a la fecha del
arqueo**, no todos.

## Archivos permitidos

- `lector/cash_limpio.py`
- `dashboard/datos.py` y `dashboard/app.py` — sólo si hace falta para mostrarlo o rotularlo.
- `clientes/navar/herramientas/crear_cash.gs` — **un solo cambio**: la fila se sigue llamando
  `AA · caja en efectivo (carga manual)` y ya no se carga a mano. Renombrarla a algo como
  `AA · caja en efectivo (calculada desde el arqueo)` y ajustar la nota. **No tocar ninguna
  fórmula**: se arreglaron y verificaron ayer en producción.
- `clientes/navar/documentos/manual_cash.md` — dejar el criterio escrito en una línea, para que
  no vuelva a haber dos versiones.
- `tareas/14-caja-aa-en-el-tablero.md`

No tocar `importar_cashflow.gs`, `aviso_diario.gs`, `vigilante.py` ni los otros lectores.

## Resultado esperado

1. El tablero muestra la caja de AA con el mismo criterio que la planilla: **$27.675.788** con los
   datos del 23/09.
2. Si no hay ningún arqueo cargado, decirlo (`sin arqueo`), no mostrar 0 como si fuera un saldo.
3. Si el arqueo más nuevo es **posterior** a los movimientos, manda el arqueo (es la foto real).
4. Que quede una sola función o regla, con un comentario en criollo que diga por qué.

## Comprobaciones

1. Regenerar el tablero con el contrato real y **pegar en "Qué hice" el valor de la caja de AA y de
   la caja total**, comparados contra los de la planilla ($27.675.788 y −$157.747.412).
   Contrato: `/Users/thomasmanzo/Documents/Finnauto/clientes/navar/contrato_2026-09-23.json`
   (se lee, no se toca). **Salidas a una carpeta temporal**, nunca a `clientes/navar/privado/salidas/`.
2. Probar el caso sin arqueo y el caso con arqueo posterior a los movimientos.
3. `python -m py_compile` de lo tocado.
4. `grep` de nombres propios de personas vacío. Commit en la rama.

## Qué hice

## Revisión
