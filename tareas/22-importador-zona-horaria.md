# Tarea 22 — El importador corre las fechas 4 horas si la Sheet no está en la hora del Pacífico
Estado: pendiente
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

## Revisión
