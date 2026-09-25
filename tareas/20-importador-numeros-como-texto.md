# Tarea 20 — El importador frena por números de comprobante que la Sheet convierte en número
Estado: lista para revisión
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
   identificadores o texto libre y se escriben como texto (por ejemplo `texto: [...]`). Claude
   revisó el 25/09 los `para_pegar_*` de la semana: estas columnas traen textos que son **solo
   dígitos**, y la Sheet los convertiría a número.
   - Cartera de Cheques → `Nro Cheque` (el que falló).
   - Saldos Bancarios → `Cuenta / Nro` (ej. `130559`, `19477890007728`).
   - Movimientos (bancos y tesorería AA) → `Referencia` y `Concepto / Detalle`. Hay referencias de
     **30 dígitos** (Macro: `033000953674800000000011381061`). Convertidas a número pierden
     precisión y el dato queda **roto**, no solo mal verificado.
   - Por las dudas, aunque hoy no fallan: Cuentas a Cobrar → `Nro Factura`; Cuentas a Pagar →
     `Nro Factura / OC`.
   Revisar las solapas de impuestos y deuda y anotar en "Qué hice" si hay otras.
   No se sabe por qué las de bancos no frenaron hasta ahora. Puede ser que esas columnas ya estén
   en formato texto en la Sheet. Para la tarea no importa: se fuerza el formato igual.
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

- Agregué en cada bloque de `IMPORTS` la lista explícita `texto`. Quedaron cubiertos `Nro
  Factura`, `Nro Factura / OC`, `Nro Cheque`, `Cuenta / Nro`, `Referencia` y `Concepto /
  Detalle`, incluidas las dos fuentes que cargan Movimientos.
- Antes de pegar, el importador pone esas columnas en formato texto. El rango incluye tanto las
  filas que se escriben como las filas viejas que se limpian debajo, para no perder ceros ni
  precisión aunque cambie la cantidad de registros.
- `_mismoDato_` sigue comparando las fechas por su instante exacto. Como red de seguridad, ahora
  acepta `"55"` contra `55`, pero no `"0055"` contra `55` ni un identificador que exceda la
  precisión segura de un número.
- Revisé impuestos y deuda bancaria. No agregué otras columnas: `Nro Cuota` sale como número o
  como una leyenda, y `Periodo` es texto descriptivo; ninguna necesita cubrir el caso de un
  identificador numérico recibido como texto.
- Verifiqué la sintaxis, los casos de achicar/agrandar/repetir el volcado, filtros, filas ocultas,
  cola borrada, Registro y fechas. También simulé la conversión automática de la Sheet: `0055`
  quedó como texto y el formato se aplicó antes de escribir. El único llamado a `_mismoDato_` es
  el control posterior al volcado.
- La prueba existente `probar_importador_filtros.cjs` conserva la expectativa anterior (`"10"`
  contra `10` era distinto). No la modifiqué porque está fuera de los archivos permitidos; corrí
  esa misma prueba en memoria con la expectativa nueva y pasó completa.
- El cambio no agrega nombres propios de personas.

### Prueba pendiente en la Sheet

No se puede ejecutar Apps Script desde este entorno. Para la revisión:

1. Copiar `importar_cashflow.gs` desde `NAVAR - Datos/Scripts/`, pegarlo completo en Apps Script
   de la Sheet y guardar.
2. En `Cartera de Cheques`, volver temporalmente la columna D a formato `Automático`, para probar
   el caso que fallaba.
3. Ejecutar `finauto → Importar Tango (cobrar / pagar / cheques)`.
4. Confirmar que termine sin `VERIFICACION_NO_CUADRA` y que `Nro Cheque` quede en formato texto.
5. Revisar en `Registro` una línea `ok` con 374 / 535 / 77, o con las cantidades del archivo más
   nuevo si cambiaron.

## Revisión

**Claude, 25/09/2026.** Leí el diff completo. Aprobado, con una prueba ajustada y un control extra
en la Sheet.

- Bien: la lista `texto` es explícita por solapa y cubre las seis columnas (incluidas las dos
  fuentes de Movimientos). El formato `@` se pone **antes** de escribir y sobre toda la altura
  (filas nuevas y cola que se borra). `_mismoDato_` acepta `"55"`/`55` y rechaza `"0055"`/`55` y los
  números fuera de la precisión segura, que es justo el caso de la referencia de 30 dígitos del
  Macro. Las fechas siguen igual.
- Filas conservadas (cargadas a mano) que hoy son número: `setValues` las vuelve a escribir como
  número aunque la celda sea texto, y el control compara número con número. No rompe.
- **Ajuste de Claude:** `lector/pruebas/probar_importador_filtros.cjs` esperaba
  `_mismoDato_(10,'10') === false` (el comportamiento viejo). Quedó en `true`, más dos casos que
  tienen que seguir distintos (`"0055"` y la referencia de 30 dígitos). En esta Mac no hay `node`:
  no la pude correr. Codex dice que corrió la misma prueba con la expectativa nueva y pasó.
- **Control extra al probar en la Sheet:** `crear_cash.gs → _cuentasVistaBancos_` arma las filas por
  cuenta con condiciones `"=130559"` sobre `Cuenta / Nro`. Con la tarea, esa columna pasa de número
  a texto. Después de pegar el `.gs`, correr también **Importar Bancos** y confirmar en **Cash** que
  cada banco sigue mostrando su saldo (Nación −97,8 M, Macro −49,8 M, BBVA +12,0 M). Si alguna fila
  queda vacía, correr **Armar solapa Cash** para regenerar las condiciones.
