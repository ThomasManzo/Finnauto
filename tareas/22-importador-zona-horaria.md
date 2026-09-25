# Tarea 22 — El importador corre las fechas 4 horas si la Sheet no está en la hora del Pacífico
Estado: aprobada (mergeada 25/09)
Rama: tarea/importador-zona-horaria

## Objetivo

Que las fechas importadas lleguen a la Sheet **a las 00:00 del día que dice el archivo**, esté la
Sheet en la zona horaria que esté. Así se puede dejar la Sheet en hora de Buenos Aires, que es lo
correcto para NAVAR.

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `CLAUDE.md`, `clientes/navar/LEEME.md` y en
`clientes/navar/herramientas/importar_cashflow.gs` las funciones `_importarConLock_`,
`_volcarSinFiltro_`, `_verificarVolcado_` y `_mismoDato_`. En `crear_cash.gs`, cómo se arman las
fechas de las columnas de Cash (`$B$3`) y la condición `D(c) > $B$2` de las filas de bancos.

Pasó el 25/09/2026:
- La Sheet estaba en hora del Pacífico (el Registro marcaba 3-4 hs de menos). Thomas la pasó a
  **Buenos Aires** y reimportó Tango, Bancos y Tesorería AA.
- `_importarConLock_` convierte el `para_pegar_*.xlsx` en una Sheet temporal
  (`Drive.Files.copy(..., mimeType: GOOGLE_SHEETS)`). Esa temporal queda en la zona de la cuenta
  (Pacífico, UTC−7). `getValues()` devuelve las fechas como `Date` a las 00:00 **del Pacífico**, y
  `setValues()` en la Sheet de Buenos Aires las guarda como **04:00**.
- Confirmado en la Sheet: `=TEXT(Cash!B3;"dd/mm/yyyy hh:mm")` → `25/09/2026 04:00`.
- Efecto: en Cash, la columna del día de hoy vale "25/09 04:00", que es mayor que `HOY()` (25/09
  00:00). Las filas de bancos tienen `=IF(fecha > $B$2; ""; ...)`, así que **el día de hoy queda
  vacío** (Total saldo real de bancos vacío, aunque el Macro trae saldo del 25/09). Los días
  anteriores no se ven afectados.
- `_verificarVolcado_` no lo detectó: compara `Date` contra `Date` por `getTime()`, y el instante es
  el mismo; lo que cambia es la zona en que se interpreta.
- **Arreglo manual del 25/09:** volver la Sheet a la hora del Pacífico y reimportar. Esta tarea
  hace que no haga falta.

## Archivos permitidos

- `clientes/navar/herramientas/importar_cashflow.gs`
- `lector/pruebas/probar_importador_filtros.cjs` (o una prueba nueva `.cjs` al lado; anotarlo)
- `tareas/22-importador-zona-horaria.md`

## Resultado esperado

1. En `_importarConLock_`, apenas se abre la temporal y **antes de leer nada**, ponerle la zona
   horaria de la Sheet destino (`origen.setSpreadsheetTimeZone(destino.getSpreadsheetTimeZone())`).
   Comentar en criollo por qué.
2. Red de seguridad al escribir: en las listas, las fechas son de día, no de hora. Si una fecha
   que se va a escribir no cae a las 00:00 **en la zona de la Sheet destino**, se lleva a las 00:00
   de ese día. Usar `Utilities.formatDate` con la zona del destino para saber el día; no restar
   horas a mano. Tiene que valer para las columnas de fecha de todas las solapas (`Fecha`,
   `Fecha Emision`, `Fecha Vencimiento`, `Fecha Pago / Cobro`, etc.). Si alguna columna de fecha
   lleva hora a propósito, no tocarla y anotarla en "Qué hice".
3. `_verificarVolcado_`: además de lo que ya controla, frenar con un mensaje claro si una fecha
   escrita en la lista **no** es 00:00 en la zona de la Sheet (`"fechas corridas por zona horaria"`).
4. Nada más cambia.

## Comprobaciones

1. Prueba `.cjs` sin Apps Script real: simular una temporal en UTC−7 y un destino en UTC−3, con una
   fecha 25/09 00:00. Tiene que quedar escrita como 25/09 00:00 del destino y pasar la verificación.
   Sin el arreglo, la prueba tiene que fallar.
2. Dejar escrito cómo lo prueba Thomas en la Sheet: pegar el `.gs`, poner la Sheet en Buenos Aires,
   correr Importar Tango, Bancos y Tesorería AA. Con `=TEXT(Cash!B3;"dd/mm/yyyy hh:mm")` tiene que
   dar `00:00`, y la columna de hoy de Cash tiene que mostrar los bancos.
3. `grep` de nombres propios de personas vacío. Commit en la rama.

## Qué hice

- Apenas se abre la Sheet temporal, el importador toma la zona horaria de la Sheet destino y se
  la aplica antes de consultar cualquier solapa. Así la conversión del Excel no depende de la
  zona configurada en la cuenta que creó la temporal.
- Declaré de forma explícita las columnas de fecha de todas las listas: emisiones, vencimientos,
  pagos/cobros, movimientos, saldos y fechas de deuda. Antes de escribirlas se conserva el día
  que muestran en la zona destino y se las lleva a las 00:00 de esa zona, sin restar horas a mano.
- La verificación posterior ahora frena con `fechas corridas por zona horaria` si Google devuelve
  alguna de esas fechas con una hora distinta de 00:00. El control anterior de igualdad exacta
  entre fechas se mantiene.
- Revisé los encabezados de todas las salidas. No hay una columna de fecha que lleve hora a
  propósito: todas representan un día contable, de emisión, vencimiento, pago o cierre.
- Agregué `lector/pruebas/probar_importador_zona_horaria.cjs`, con datos inventados. Comprueba que
  la temporal recibe la zona antes de leerse, simula 25/09 00:00 en UTC−7 contra un destino UTC−3,
  verifica que se escriba 25/09 00:00 y confirma que, sin normalizar, las 04:00 disparan el error.
- Pasaron la prueba nueva, la sintaxis del `.gs` y las pruebas existentes de filtros, vistas,
  filas ocultas, achicamiento/crecimiento, repetición, Registro y fechas. No se usaron datos reales
  ni se agregaron nombres propios de personas.

### Prueba pendiente en la Sheet

Apps Script real no se puede ejecutar desde este entorno. Para revisar la instalación:

1. Copiar la versión nueva de `importar_cashflow.gs` a `NAVAR - Datos/Scripts/`, pegarla completa
   en Apps Script y guardar.
2. En Archivo → Configuración, dejar la zona horaria de la Sheet en Buenos Aires.
3. Ejecutar, en este orden, `Importar Tango`, `Importar Bancos` e `Importar Tesorería AA`.
4. Confirmar que las tres líneas nuevas de `Registro` terminen en `ok`.
5. En una celda libre, probar `=TEXT(Cash!B3;"dd/mm/yyyy hh:mm")`: debe terminar en `00:00`.
6. Revisar que la columna de hoy de Cash muestre los saldos de bancos y no quede vacía por la
   condición de fecha.

## Revisión

**Claude, 25/09/2026.** Leí el diff completo. Aprobado.
- La temporal recibe la zona del destino **antes** de cualquier lectura. Es la causa real, porque
  `getValues()` interpreta las fechas con la zona de la planilla que se lee.
- La lista `fechas` por solapa es explícita, y la normalización usa `Utilities.formatDate` y
  `parseDate` en la zona del destino (sin restar horas a mano). También alcanza a las filas
  conservadas (`vivas`), que son de día.
- La verificación frena con "fechas corridas por zona horaria". Queda como red de seguridad: con
  la temporal igualada, no debería dispararse.
- Costo: dos llamadas a `Utilities` por fecha al escribir y otras dos al verificar. Con Movimientos
  (~2.500 filas) sigue lejos del límite de 6 minutos.
- En esta Mac no hay `node`: la prueba `.cjs` no la corrí yo; Codex informa que pasa.
