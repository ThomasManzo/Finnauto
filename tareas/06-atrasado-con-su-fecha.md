# Tarea 06 — Lo que venció y no se pagó tiene que verse en la fecha que correspondía
Estado: pendiente
Rama: tarea/atrasado-con-fecha

## Objetivo

Pedido de Thomas (22/09), textual: *"cuando hay un pago programado con proveedores y no se paga,
pasa automáticamente al apartado 6 del cash, 'Atrasado hoy'. Bueno, que quede en la fila del día
que corresponde: ejemplo, 25/09 no se pagó tal factura; eso suma al atrasado, pero **en la fecha
que correspondía pagarlo**. O sea, el 26/09, si eso está impago, va a aparecer en algún apartado
con la fecha que correspondía."*

Traducido: hoy, cuando una obligación vence y no se paga, desaparece de la curva y reaparece como
un monto sin fecha en el bloque `6 · Atrasado hoy`. Se pierde **cuándo** tendría que haberse pagado.
Hay que conservar esa fecha y poder verla.

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `CLAUDE.md` y sobre todo
`clientes/navar/documentos/manual_cash.md` §3 (cómo se lee una pantalla) y §4.

Cómo funciona hoy, para no romperlo:

- `6 · Atrasado hoy` es un **stock**, no está en la curva de caja. Eso está bien y no se discute:
  si lo vencido entrara en la curva, el saldo al cierre estaría contando dos veces la misma plata.
- Existe además la fila `Venció en el período y no se pagó (proveedores + impuestos)`, que ya mira
  lo vencido **dentro del período**, y `Resultado de la operación pagando lo que vencía`.
- Las listas (Cuentas a Pagar, Deuda Impositiva, Deuda Bancaria) tienen la fecha de vencimiento de
  cada renglón: **el dato ya está**, lo que falta es mostrarlo por fecha.

Lo que hay que resolver, y es la parte de criterio: en las pantallas diarias/semanales/mensuales
cada columna es un período. Una factura que venció el 25/09 y sigue impaga el 30/09 **tiene que
aparecer en la columna del 25/09**, no en la de hoy. Es decir: el atrasado se reparte por fecha de
vencimiento original, no por la fecha en que se mira.

Decidir y explicar cómo se muestra sin ensuciar la lectura. Dos caminos posibles (elegir uno y
justificarlo, o proponer uno mejor):

- **(a)** Un renglón nuevo debajo del bloque 6, tipo "Venció ese día y sigue impago", con el importe
  en la columna del día/semana/mes en que venció. Queda fuera de la curva, como el resto del bloque 6.
- **(b)** Desplegable dentro de `6 · Atrasado hoy`, con una fila por fecha de vencimiento.

Reglas que no se pueden romper:

- **Nada de esto entra en la curva ni cambia ningún saldo al cierre.** Es información, no caja.
- Lo que se pague deja de aparecer al día siguiente, solo, sin que nadie borre nada.
- Tiene que funcionar en las tres pantallas (Cash, Cash Semanal, Cash Mensual), agrupando por el
  período que corresponda.
- La suma de lo repartido por fecha tiene que dar **exactamente** el total del bloque 6. Verificarlo.

Si además tiene sentido reflejarlo en el tablero web, decilo en "Qué hice" pero **no lo hagas acá**:
el tablero lo toca la tarea 07 y se pisarían.

## Archivos permitidos

- `clientes/navar/herramientas/crear_cash.gs`
- `clientes/navar/documentos/manual_cash.md` — §3 y §4.
- `tareas/06-atrasado-con-su-fecha.md`

No tocar `importar_cashflow.gs` (lo toca la tarea 05) ni `dashboard/` (tarea 07) ni los lectores.

## Comprobaciones

1. Explicar el criterio elegido y por qué, en criollo.
2. Dejar el guion de prueba manual: qué mirar en la planilla para ver que cuadra (el total del
   bloque 6 contra la suma del detalle por fecha).
3. Que quede claro qué pasa con lo que venció **antes** del primer período visible de la pantalla
   (hay deuda vencida de 2007 en las listas): proponer un criterio, por ejemplo una columna
   "antes del período" o dejarlo solo en el total.
4. `grep` de nombres propios vacío. Commit en la rama.

## Qué hice

## Revisión
