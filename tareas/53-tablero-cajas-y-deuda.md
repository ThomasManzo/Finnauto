# Tarea 53 — El tablero de siempre con las dos cajas y la deuda en dos bloques
Estado: aprobada (falta actualizar la notebook)
Rama: tarea/tablero-cajas-y-deuda

## Objetivo

Sumarle al tablero de siempre (`finauto.html`, el que se rearma solo desde la tarea 52) lo que ya tiene
el Cash de la Sheet: las dos cajas en efectivo (A y AA) y la deuda separada entre lo que sale sí o sí
(débito automático) y lo que se paga por decisión. Pedido de Thomas, 07/10/2026.

## Contexto

- El lector de la Sheet (`lector/cash_limpio.py`) calculaba solo la caja de AA (arqueo + movimientos de
  Tango con Origen "Tango AA"). Desde la tarea 48 también hay "Caja A" y los movimientos de caja dicen
  en `Banco / Cuenta` de qué caja son.
- El tablero ya tenía el reparto "Sale sí o sí / Se paga por decisión / Sin definir"
  (`obligaciones_por_debito`), pero todo caía en "Sin definir": el lector no leía la columna
  `Debito Automatico` de Deuda Bancaria ni de Deuda Impositiva.
- En la tabla de bancos aparecía una fila falsa: el título del segundo bloque de Deuda Bancaria
  ("B) Cronograma de Vencimientos (cuotas)") se leía como una línea de deuda.

## Archivos permitidos

`lector/cash_limpio.py`, `dashboard/datos.py`, `dashboard/app.py`,
`lector/pruebas/test_tablero_cajas_deuda.py` (nueva), esta consigna.

## Resultado esperado

1. **Cajas**: cada caja = su último arqueo (Saldos Bancarios, carga manual) + los movimientos de Tango
   posteriores de esa caja (Movimientos, `Banco / Cuenta` = "Caja A" / "Caja AA", Origen "Tango…").
   Es la misma cuenta que hace la solapa Cash. Un arqueo con fecha futura no se usa. Se puede aplicar
   dos veces sin sumar dos veces.
2. **Posición**: nueva tabla "Dónde está la plata hoy". Muestra las dos cajas y cada banco, con su
   saldo y de cuándo es el dato ("arqueo del dd/mm + n movimientos de Tango" o "extracto al dd/mm").
   Suma lo mismo que "Caja de hoy". Si un banco tiene dos cuentas, se distinguen por los últimos
   números.
3. **Deuda**: se lee `Debito Automatico` de las líneas, del cronograma y de los impuestos, así el
   reparto "sale sí o sí / por decisión" del tablero deja de estar vacío. Los títulos de bloque no se
   leen como bancos.

## Comprobaciones

- Pruebas con datos inventados (`test_tablero_cajas_deuda.py`, 7):
  - cajas A y AA con movimientos de Tango; quedan afuera los anteriores al arqueo, los posteriores a
    hoy, los manuales y los del banco;
  - aplicarlo dos veces da lo mismo;
  - sin arqueo, avisa;
  - la tabla de cuentas suma lo mismo que la caja;
  - el título del cronograma no es un banco;
  - se lee el débito automático;
  - no se usa el arqueo de mañana.
- Todas las pruebas del repo siguen pasando.
- A mano, con la copia del día de la Sheet: la "Caja de hoy" del tablero es igual a la del Cash, las
  cajas salen de sus arqueos y el reparto por débito suma lo mismo que la deuda total.

## Qué hice
**La escribió Claude.**
- `cash_limpio.py`:
  - `actualizar_cajas` reemplaza a `actualizar_caja_aa` (que queda como otro nombre de la misma
    función) y calcula las dos cajas;
  - guarda `contrato["cajas"]` y sigue completando `caja_aa` para lo que ya lo leía;
  - lee `debito_automatico` en líneas, cuotas e impuestos;
  - saltea las filas de título de bloque;
  - el aviso de "saldo viejo" no cuenta los arqueos de ninguna de las dos cajas.
- `datos.py`: `cuentas_de_hoy` arma la tabla, con nombres de banco prolijos. `armar` usa
  `actualizar_cajas`.
- `app.py`: la tabla "Dónde está la plata hoy" en Posición, con el mismo estilo del tablero.
- Probado con la copia del día de la Sheet (no se sube):
  - la caja de hoy coincide con la del Cash, peso por peso;
  - la fila falsa de bancos desapareció;
  - la deuda bancaria queda casi toda en "sale sí o sí"; lo "sin definir" son líneas que no tienen el
    dato cargado en la Sheet;
  - los impuestos se reparten entre "sale sí o sí" y "por decisión" según la columna.

## Revisión
