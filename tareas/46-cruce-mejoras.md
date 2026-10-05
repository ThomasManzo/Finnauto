# Tarea 46 — Cruce banco ↔ Tango: cheques propios, neto con cargos y otras mejoras
Estado: lista para revisión
Rama: tarea/cruce-mejoras

## Objetivo
Que el cruce (`lector/cruce.py`) deje de mostrar como diferencia cosas que no lo son, antes de armar el
cruce semanal automático. Todo salió de revisar julio a septiembre con datos reales (en
`clientes/navar/privado/cruce/`, fuera de git).

## Contexto (ejemplos inventados; los patrones son reales)
1. **Cheques propios**: el banco debita "48HS. CANJE ZONAL" / "CHEQUE CANJE INTERNO" / "PAGO DE CHEQUE DE
   CAMARA" cuando se cobra un cheque propio. Esos cheques están en la foto "A cheques propios" de la
   bajada (fecha del cheque, importe, cuenta emisión, razón social, fecha de emisión). Hay series de
   cheques del mismo importe una semana aparte.
2. **Órdenes de pago con cheques diferidos**: Tango imputa la orden al banco el día que se emite, pero el
   banco debita cada cheque meses después. Ejemplo: orden de 30.000 = cheques de 10.000 y 20.000
   emitidos ese día al mismo proveedor.
3. **Préstamo neto de sellos**: banco +99.000; Tango recibo +100.000 y orden de pago −1.000 (sellos), el
   mismo día.
4. **eCheq en tres días**: una boleta = cheques acreditados entre el 13 y el 15.
5. **Anulaciones que no son REV**: "EXT 123/1" da vuelta la "EXT 123" y se vuelve a cargar como "EXT 124".
6. **Interés mal escrito**: "INTERSES VTA.CH." no se reconocía como interés de descuento.
7. **Mes vencido**: cuotas e intereses del mes cargados todos el día 1 del mes siguiente.
8. La columna "Gastos que Tango tiene sin par" sumaba cuotas de préstamo.

## Archivos permitidos
`lector/cruce.py`, `lector/pruebas/test_cruce.py`, `clientes/navar/perfil.json` (bloque `cruce`).

## Resultado esperado
- `--cheques` (archivo o carpeta `Cheques`, opcional). Regla **cheque propio** (Seguro; "por fecha",
  Sugerido, cuando hay varios del mismo importe o quedó solo por otra elección).
- Órdenes de pago cuyos cheques (mismo proveedor, misma cuenta, misma fecha de emisión) suman la orden →
  "No pasa por banco" como "Pago con cheques propios diferidos". Si suman menos, queda en "Solo en Tango"
  con la explicación. Cheques con fecha pasada que el banco no debitó → "Revisar".
- Reglas **neto con cargos** (Sugerido), **agrupado en varios días** (2 o 3 días, Posible; reemplaza a
  "agrupado en dos días") y **cargado a mes vencido** (Sugerido, antes de fecha corrida).
- Anulaciones generales (mismo importe con signo contrario, misma cuenta, ≤ 5 días) no suman.
- Interés de descuento: "INTER" + VTA/VALORES. Margen de carga 40 días (era 10).
- Columna renombrada "Cargos del banco en Tango sin par", sin cuotas de préstamo.

## Comprobaciones
`python -m unittest lector.pruebas.test_cruce` y julio a septiembre con datos reales (control OK,
revisión a mano de cada par nuevo).

## Qué hice
**La escribió Claude.** Todo lo de arriba, con 11 pruebas nuevas (49 del cruce, 72 con la bajada; OK).
Ajustes al revisar con datos reales: (a) los cheques del mismo importe una semana aparte se emparejan por
fecha más cercana y quedan Sugerido; (b) "mes vencido" corre antes de "fecha corrida", porque describe
mejor las cuotas del día 1; (c) tres pruebas viejas de "fecha corrida" usaban justo una cuota del día 1:
se movió la fecha inventada. También: "impuestos agrupados" al revés (una orden de pago de Tango = varios débitos de ARCA del mismo
período, p. ej. planes de pago). Resultado: julio de 82 % a 95 % conciliado; agosto de 88 % a 97 %;
septiembre de 74 % a 76 % (septiembre está incompleto: extracto de Nación hasta el 24/09). Control OK en
los tres. Limitación: la foto de cheques propios trae solo los últimos 60 días (`dias_atras`), así que
los cheques cobrados antes no se pueden emparejar.

## Revisión
