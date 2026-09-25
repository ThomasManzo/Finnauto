# Tarea 20 — El importador frena por números de comprobante que la Sheet convierte en número
Estado: pendiente
Rama: tarea/importador-texto

## Objetivo

Que el importador de la Sheet deje de dar `VERIFICACION_NO_CUADRA` cuando un identificador
(número de cheque, de factura, referencia) viene como texto con solo dígitos. Hoy la Sheet lo
convierte a número al escribirlo, y el control de lo escrito lo ve distinto. Además, esos
identificadores tienen que quedar **como texto** en la Sheet: no son cantidades y pueden tener
ceros adelante.

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `CLAUDE.md`, `clientes/navar/LEEME.md` y en
`clientes/navar/herramientas/importar_cashflow.gs` las funciones `_volcarSinFiltro_`,
`_verificarVolcado_` y `_mismoDato_`.

Pasó el 25/09/2026, con la primera bajada de Tango por API:
- El lector deja en `para_pegar_en_la_sheet_*.xlsx`, solapa Cartera de Cheques, `Nro Cheque` como
  texto (`"4658867"`). El importador convierte el xlsx a una Sheet temporal y lo lee como texto.
- `setValues` escribe `"4658867"` en `Cartera de Cheques`. La Sheet (configuración es_AR) lo
  interpreta y guarda el **número** `4658867`.
- `_verificarVolcado_` relee y `_mismoDato_` compara con `===`: `"4658867" !== 4658867`, así que
  tira `VERIFICACION_NO_CUADRA: Cartera de Cheques fila 2, columna Nro Cheque`. Cobrar y Pagar ya se
  habían cargado. Como la importación queda en ERROR, el disparador horario la reintenta cada hora.
- Con los exports a mano no pasaba porque, en cheques de terceros de A, el lector ponía en `Nro
  Cheque` el CUIT (con guiones = texto). La API trae el número real.
- **Arreglo manual aplicado ese día:** la columna D de Cartera de Cheques se puso en "Texto sin
  formato" a mano y la reimportación dio ok (374 / 535 / 77). Esta tarea hace que no dependa de eso.

## Archivos permitidos

- `clientes/navar/herramientas/importar_cashflow.gs`
- `tareas/20-importador-numeros-como-texto.md`

## Resultado esperado

1. En la configuración de cada solapa (`IMPORTS`), una lista **explícita** de columnas que son
   identificadores y se escriben como texto. Como mínimo: Cartera de Cheques → `Nro Cheque`;
   Cuentas a Cobrar → `Nro Factura`; Cuentas a Pagar → `Nro Factura / OC`; Movimientos →
   `Referencia`. Revisar las demás solapas del archivo y anotar en "Qué hice" si hay otras.
2. Antes de escribir esas columnas, ponerles formato de texto (`setNumberFormat("@")`) en el rango
   que se va a escribir, **y en el que se limpia abajo**. Así una fila futura tampoco se convierte.
3. `_mismoDato_`: además de fechas, considerar iguales un número y un texto que la Sheet habría
   convertido a ese número (`"55"` y `55`; cuidar `"0055"` contra `55`: **no** son iguales si la
   columna es de texto). Es una red de seguridad; lo principal es el punto 2. Comentar en criollo
   por qué.
4. Nada más cambia: mismo orden, mismas marcas, mismo Registro.

## Comprobaciones

1. No hay forma de correr Apps Script acá. Dejar escrito, paso a paso, cómo lo prueba Thomas en la
   Sheet: pegar el `.gs` desde `NAVAR - Datos/Scripts/` y correr "Importar Tango". Tiene que dar ok
   aunque la columna D vuelva a formato "Automático", y en Registro la línea tiene que decir
   374/535/77 o lo que traiga ese día.
2. Revisar a mano que ningún otro llamado a `_mismoDato_` cambie de comportamiento con fechas.
3. `grep` de nombres propios de personas vacío. Commit en la rama.

## Qué hice

## Revisión
