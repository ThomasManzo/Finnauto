# Tarea 03 — Las fechas de cheques se rompen AL IMPORTAR a la Sheet (no en el lector)
Estado: pendiente
Rama: tarea/fechas-importacion

## Objetivo

Encontrar la causa exacta por la que las fechas de la solapa **Cartera de Cheques** de la Sheet
no coinciden con el archivo que genera el lector, y arreglarla. Es un bug en producción: por esto
un cheque propio real desapareció del cash y hay cheques a cobrar con fechas de 2027 que no existen.

## Contexto

Esto continúa la tarea 02. **El diagnóstico de la 02 apuntaba al lector y era equivocado**: el
lector está bien. Lo que sigue ya está verificado y no hace falta re-descubrirlo.

`para_pegar_en_la_sheet_2026-09-22.xlsx` (generado por el lector el 22/09 a las 15:53, todavía está
en `_para la Sheet/` en Drive) tiene **66 filas** en Cartera de Cheques, ordenadas por fecha
ascendente, con `datetime` reales y formato `DD/MM/YYYY`, epoch 1900. Todas sus fechas coinciden
con los exports de Tango.

La Sheet, después de importarlo (Registro: `tango ... ok`, 22/09 15:55), tiene **las mismas 66
filas**, mismo ID, mismo número de cheque, mismo importe — **y distinta fecha** en varias:

| ID | Nro cheque | Fecha en el para_pegar | Fecha en la Sheet |
|---|---|---|---|
| 3 | 68150561 | 2026-09-15 | 2026-08-17 |
| 4 | 68150612 | 2026-09-25 | 2026-08-24 |
| 31 | 32487757 | 2026-10-18 | 2026-10-18 (coincide) |
| 41 | 32283267 | 2026-11-06 | 2027-03-25 |
| 42 | 32283268 | 2026-11-12 | 2027-04-15 |
| 45 | 32283269 | 2026-11-20 | 2027-05-25 |

Los corrimientos no son constantes (−29, −32, +139, +154, +186 días) y **algunas filas coinciden**.
Se bajó la Sheet dos veces con veinte minutos de diferencia: da igual las dos veces, así que no es
una exportación desactualizada.

Dato para la hipótesis principal: en el para_pegar la lista está **ordenada por fecha ascendente**
y en la Sheet la columna de fechas **también** queda ascendente, pero abarcando un rango distinto.
Eso hace pensar en un **desfasaje de la columna de fechas respecto de las demás** (la fecha de una
fila termina en otra), no en una conversión de fecha mal hecha. Hay que confirmarlo con datos, no
suponerlo.

Quién escribe esas celdas: `clientes/navar/herramientas/importar_cashflow.gs`, función `_volcar_`
(escribe columna por columna, saltando las de fórmula) llamada desde `_importar_` (que primero
convierte el .xlsx a una Sheet temporal con `Drive.Files.copy` y después lee de ahí). Para la
solapa Cartera de Cheques la configuración es `formulas: []`, `colMarca: "Observaciones"`,
`marcas: ["Tango Live","REVISAR:","AGREGADO"]`, `conId: true`.

**Sospechosos, por orden:** (1) la conversión .xlsx → Sheet temporal que hace `Drive.Files.copy`;
(2) el armado de `finales` en `_volcar_` (mezcla de `vivas` + `nuevas` y renumerado de ID);
(3) la escritura columna por columna cuando la cantidad de filas cambia; (4) el orden/duplicados
de encabezados y la normalización `_n_`.

## Archivos permitidos

- `clientes/navar/herramientas/importar_cashflow.gs` — el arreglo.
- `clientes/navar/documentos/manual_cash.md` — §7, registrar el error y cómo se detectó.
- `tareas/03-fechas-en-la-importacion.md` — este archivo.
- `lector/pruebas/` — si sirve para dejar clavado el patrón encontrado.

No tocar el lector (la tarea 02 ya lo dejó bien), ni `vigilante.py`, ni `crear_cash.gs`.

## Resultado esperado

1. **El mapeo exacto, con datos**: comparar las **66 filas** del para_pegar contra las 66 de la
   Sheet y decir en criollo qué le pasó a la columna de fechas. Concretamente: para cada fila de
   la Sheet cuya fecha no coincide, buscar **de qué fila del para_pegar salió esa fecha**. Si hay
   un patrón (un desfasaje de N filas, un subconjunto, un orden distinto), describirlo; si no lo
   hay, decirlo y explicar qué otra cosa muestra la evidencia.
2. La causa identificada en el código, citando la línea.
3. El arreglo, con comentario en criollo de qué pasaba y por qué.
4. Si la causa resulta estar en la conversión de Google y no en el código, decirlo claramente y
   proponer cómo evitarla (por ejemplo leer el .xlsx sin convertirlo, o escribir las fechas como
   texto ISO y formatearlas en la Sheet). No inventar un arreglo que no se pueda verificar.

Archivos para el análisis (se leen, no se tocan; rutas absolutas):

```
/Users/thomasmanzo/Library/CloudStorage/GoogleDrive-thomasezequielmanzo@gmail.com/Mi unidad/NAVAR - Datos/_para la Sheet/para_pegar_en_la_sheet_2026-09-22.xlsx
/Users/thomasmanzo/Documents/Finnauto/clientes/navar/privado/NAVAR - Cash Flow (export Sheets 2026-09-22c).xlsx
```

## Comprobaciones

1. La comparación de las 66 filas, con su resultado, pegada en "Qué hice" (tabla o resumen claro).
2. Si se toca el .gs: que el cambio sea el mínimo necesario y esté explicado.
3. Apps Script no corre acá: decir explícitamente qué queda por probar en la Sheet y cómo probarlo
   (qué botón, qué mirar, qué tendría que dar).
4. `grep -n -i -E "priscilla|karina|celia|miriam|milagros|charles|thomas"` vacío en lo tocado.
5. Commitear en `tarea/fechas-importacion`; si el sandbox no deja, anotarlo.

Al terminar: "Qué hice" y `Estado: lista para revisión`.

## Qué hice

(lo completa Codex)

## Revisión

(lo completa Claude)
