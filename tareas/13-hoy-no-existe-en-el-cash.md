# Tarea 13 — El día de hoy queda en blanco y lo real de hoy no se suma
Estado: pendiente
Rama: tarea/hoy-en-el-cash

## Objetivo

Cuatro defectos del cash, verificados el 23/09 con datos reales en producción. Los cuatro tienen
el mismo origen: **el cash trata como "último día que existe" la fecha del último extracto
bancario, y descarta todo lo que pasó después**, aunque haya datos reales cargados.

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `CLAUDE.md` y `clientes/navar/documentos/manual_cash.md`.

Situación del 23/09: último extracto bancario = **22/09** (celda `B3`). Pero la solapa
**Movimientos** tiene movimientos **reales del 23/09** (la caja en efectivo de AA, que viene de la
tesorería de Tango): ingresos por $1.085.411 y $15.000.000, y egresos por $250.000, $100.000,
$310.000 y $62.623. Nada de eso aparece en el cash.

### Defecto 1 · Los bancos quedan vacíos en la columna de hoy

Fórmula actual de cada banco (ejemplo, Nación):

```
=IF(B$6>$B$3,"",SUMIFS('Saldos Bancarios'!$E:$E, ... ))
```

`B$6` es la fecha de la columna y `$B$3` el último día con extracto. Si la columna es **posterior**
al último extracto, devuelve **vacío**. Por eso el 23/09 los cinco bancos están en blanco.

La tarea 11 pedía arrastrar el último saldo conocido y **no se cumplió para la columna de hoy**,
que es justamente donde más se nota. Tiene que arrastrar **hasta hoy inclusive**, marcado como
arrastrado (gris e itálica, con la fecha de la que viene), como ya está resuelto para las columnas
anteriores.

### Defecto 2 · Lo real de hoy no se suma

Todas las filas de conceptos cortan en el último extracto:

```
SUMIFS(Movimientos!$G:$G, Movimientos!$B:$B,">="&B$6, Movimientos!$B:$B,"<"&MIN((B$6+1),$B$3+1), ...)
```

Ese `MIN(..., $B$3+1)` tapa cualquier movimiento real posterior al último extracto bancario.

**El problema conceptual**: hoy hay un solo corte "real/estimado" para todo, y está atado al
extracto del banco. Pero los datos no llegan todos juntos: la caja de AA puede estar al 23/09 y el
extracto de Nación al 15/09. **Un movimiento real cargado tiene que sumar el día que ocurrió**,
venga de donde venga.

Proponer y aplicar un criterio: lo real se suma siempre por su fecha, y el rótulo real/estimado de
cada columna pasa a describir **qué parte** de esa columna es real (o se calcula por fuente).
Cuidado con no contar dos veces: si un día tiene movimiento real de una fuente y estimación de
otra para el mismo concepto, la estimación de ese concepto no va.

### Defecto 3 · La columna Origen está en rojo en todas las filas importadas

La solapa Movimientos tiene validación de datos en `J2:J5000` que sólo admite:

```
Tango, Banco, Manual, Proyeccion
```

Pero el importador escribe valores como `Extracto MACRO`, `Extracto GALICIA` y
`Tango AA · movimientos tesorería · AA Movimientos 2026-09-23.xlsx`. Resultado: **miles de celdas
marcadas como inválidas** (el triangulito rojo) y un desplegable que ofrece valores que el sistema
no usa. Lo mismo hay que revisar en las otras columnas con validación: `E` (Categoria), `C`
(Empresa), `D` (Tipo), `H` (Medio de Pago), `K` (Estado); comprobar cuáles coinciden con lo que
escriben hoy los lectores y cuáles no.

Decidir qué hacer y explicarlo: o la validación pasa a aceptar los prefijos reales, o se saca de
las columnas que llena el importador (una validación que marca en rojo el 100 % de las filas no
protege nada, sólo ensucia).

### Defecto 4 · La caja en efectivo de AA tiene que calcularse sola

Hoy la fila `AA - caja en efectivo (carga manual)` es un número fijo que alguien tipea.

Pedido de Thomas (23/09), textual: *"la caja debería calcularse sola; por ejemplo, el dato real del
21/09 fue de 12.800.000, bueno, qué movimientos tuvo la caja desde entonces que sumen y resten a la
caja que tenés hoy"*.

O sea: **saldo de caja = último arqueo cargado a mano + todos los movimientos de caja posteriores**
(los de la tesorería de AA, que ya están en Movimientos con su fecha, su signo y medio de pago
`Efectivo`). El arqueo manual sigue existiendo como punto de partida y de control: cuando se carga
uno nuevo, vuelve a ser la base y lo anterior queda como historia.

Si el arqueo nuevo **no coincide** con el saldo calculado, eso es información valiosa (falta cargar
algo, o hay una diferencia de caja): mostrarlo, no taparlo.

## Archivos permitidos

- `clientes/navar/herramientas/crear_cash.gs`
- `clientes/navar/documentos/manual_cash.md`
- `tareas/13-hoy-no-existe-en-el-cash.md`

No tocar `aviso_diario.gs` (lo está arreglando la tarea 12), ni `importar_cashflow.gs`, ni los
lectores, ni `dashboard/`.

## Comprobaciones

Apps Script no corre en el worktree. Entonces, en "Qué hice":

1. Para cada defecto: qué línea lo causaba y cómo quedó.
2. **El caso del 23/09, número por número**: qué tiene que mostrar la columna de hoy en cada banco
   (arrastrado y de qué fecha), cuánto en Cobranza AA, cuánto en Proveedores AA y en Otros, y cuánto
   en la caja de AA partiendo de los 12.800.000 del 21/09.
3. Qué columnas quedaron con validación y cuáles no, y por qué.
4. El guion de prueba en la planilla, paso por paso.
5. Sin nombres propios de personas. Commit en la rama.

## Qué hice

## Revisión
