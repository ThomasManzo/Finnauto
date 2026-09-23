# Tarea 03 — Las fechas de cheques se rompen AL IMPORTAR a la Sheet (no en el lector)
Estado: lista para revisión
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

### Resultado y alcance

**Causa exacta no determinada. No apliqué un arreglo al importador.** Primero comparé
las 66 filas de los dos archivos autorizados, antes de escribir código de prueba.
El problema está confirmado en las fechas guardadas, pero estos archivos no permiten
atribuirlo con certeza a la conversión de Google ni a una línea del importador.

- 66 ID únicos en cada archivo, mismo orden y mismas filas físicas (2 a 67).
- 21 diferencias en `Fecha Pago / Cobro` (G), 45 coincidencias.
- 2 diferencias adicionales en `Fecha Emision` (F), ambas en filas que ya difieren en G.
- Las otras 10 columnas coinciden en las 66 filas. Para el número de cheque comparé
  su valor numérico: origen trae texto terminado en `.0`, destino trae número. Los
  vacíos `None`/cadena vacía se consideran equivalentes. No publiqué importes ni nombres.
- De las 21 fechas de G distintas, **10 tienen coincidencias de valor** en otra fila
  del origen y **11 no están en ninguna fila de G del origen**. Una coincidencia de
  valor no prueba que se haya copiado desde esa fila. Cuando hay varias, las muestro todas.

### Qué muestra el patrón

No hay un desplazamiento fijo ni una permutación de las 66 fechas. Entre las diez
coincidencias de valor hay desplazamientos distintos: Sheet fila 5 → origen 2,
6 → 3, 7 → 4, 11 → 5, 25 → 37, 30 → 44, 31 → 47, 34 → 50 y 36 → 53.
La fila 23 tiene tres candidatas: 29, 30 y 31. Es imposible adjudicarla a una sola.
Además, las fechas de origen de las filas 2, 3, 47, 50 y 53 siguen en su propia fila
y aparecen nuevamente en otra fila del destino: hay repeticiones, no solo reordenamiento.

Las filas 37 a 46 de la Sheet traen una secuencia quincenal: día 15 y día 25 de enero
a mayo de 2027. Ninguna de esas diez fechas existe en G del `para_pegar`. Tampoco existe
2026-08-17 (Sheet fila 4). El patrón se parece a un cronograma, pero eso no demuestra
de dónde vino ni autoriza a corregirlo por fórmula. Las 21 diferencias afectan 17
cheques de terceros y 4 propios; no son una única clase de cheque.

**Dos premisas de la consigna no se sostienen con los archivos disponibles:**

1. No están ordenados globalmente por fecha. En el origen, fila 53 = 2026-12-20 y
   fila 54 = 2024-12-12. En la Sheet, fila 3 = 2026-08-27 y fila 4 = 2026-08-17;
   fila 46 = 2027-05-25 y fila 47 = 2026-11-25. El tramo 2–53 del origen sí es ascendente.
2. El archivo actual no acredita ser la versión de las 15:53. Su `docProps/core.xml`
   declara `created` y `modified` = **2026-09-22T20:38:09Z**, es decir **17:38:09 de
   Buenos Aires**. Su modificación local también es posterior (20:38:18.733 UTC).
   Esto no prueba por sí solo qué contenido cambió, pero impide equiparar esta foto
   con la importada a las 15:55 solo porque tienen el mismo nombre.

El Registro exportado muestra `tango / ok` a las **11:55:30.699** de la planilla
(15:55 con el desfase de cuatro horas documentado en el LEEME), y después
`tango / ERROR` a las **13:32:30.049** (17:32 con ese mismo desfase):
`No se admite esta operación en un rango con una fila filtrada.` No hay pila ni solapa
indicada en ese error. La cartera exportada tiene un filtro A1:L67, columna Tipo =
`Propio Emitido`. Eso es evidencia de un filtro, no prueba de que haya causado las
fechas distintas. No atribuyo el error a Cartera sin conocer la operación que falló.

### Mapeo completo de las 66 filas

Las filas son números físicos de Excel/Sheet (encabezado = fila 1), no posiciones
dentro del filtro. La columna final responde dónde **existe el mismo valor** en
la columna original correspondiente. `ninguna` significa que no se puede obtener
esa fecha moviendo una fecha de esa columna del archivo analizado.

**Fecha Pago / Cobro**

| Fila Sheet | ID | Fila original | Fecha original | Fecha Sheet | Coincide | Filas originales con esa fecha |
|---|---|---|---|---|---|---|
| 2 | 1 | 2 | 2026-08-24 | 2026-08-24 | sí | 2 |
| 3 | 2 | 3 | 2026-08-27 | 2026-08-27 | sí | 3 |
| 4 | 3 | 4 | 2026-09-15 | 2026-08-17 | no | ninguna |
| 5 | 4 | 5 | 2026-09-25 | 2026-08-24 | no | 2 |
| 6 | 5 | 6 | 2026-09-30 | 2026-08-27 | no | 3 |
| 7 | 6 | 7 | 2026-10-02 | 2026-09-15 | no | 4 |
| 8 | 7 | 8 | 2026-10-03 | 2026-10-03 | sí | 8 |
| 9 | 8 | 9 | 2026-10-04 | 2026-10-04 | sí | 9 |
| 10 | 9 | 10 | 2026-10-05 | 2026-10-05 | sí | 10, 11, 12 |
| 11 | 10 | 11 | 2026-10-05 | 2026-09-25 | no | 5 |
| 12 | 11 | 12 | 2026-10-05 | 2026-10-05 | sí | 10, 11, 12 |
| 13 | 12 | 13 | 2026-10-06 | 2026-10-06 | sí | 13, 14, 15 |
| 14 | 13 | 14 | 2026-10-06 | 2026-10-06 | sí | 13, 14, 15 |
| 15 | 14 | 15 | 2026-10-06 | 2026-10-06 | sí | 13, 14, 15 |
| 16 | 15 | 16 | 2026-10-07 | 2026-10-07 | sí | 16, 17 |
| 17 | 16 | 17 | 2026-10-07 | 2026-10-07 | sí | 16, 17 |
| 18 | 17 | 18 | 2026-10-08 | 2026-10-08 | sí | 18 |
| 19 | 18 | 19 | 2026-10-09 | 2026-10-09 | sí | 19, 20, 21, 22, 23 |
| 20 | 19 | 20 | 2026-10-09 | 2026-10-09 | sí | 19, 20, 21, 22, 23 |
| 21 | 20 | 21 | 2026-10-09 | 2026-10-09 | sí | 19, 20, 21, 22, 23 |
| 22 | 21 | 22 | 2026-10-09 | 2026-10-09 | sí | 19, 20, 21, 22, 23 |
| 23 | 22 | 23 | 2026-10-09 | 2026-10-15 | no | 29, 30, 31 |
| 24 | 23 | 24 | 2026-10-10 | 2026-10-10 | sí | 24, 25 |
| 25 | 24 | 25 | 2026-10-10 | 2026-10-25 | no | 37 |
| 26 | 25 | 26 | 2026-10-11 | 2026-10-11 | sí | 26 |
| 27 | 26 | 27 | 2026-10-12 | 2026-10-12 | sí | 27, 28 |
| 28 | 27 | 28 | 2026-10-12 | 2026-10-12 | sí | 27, 28 |
| 29 | 28 | 29 | 2026-10-15 | 2026-10-15 | sí | 29, 30, 31 |
| 30 | 29 | 30 | 2026-10-15 | 2026-11-15 | no | 44 |
| 31 | 30 | 31 | 2026-10-15 | 2026-11-25 | no | 47 |
| 32 | 31 | 32 | 2026-10-18 | 2026-10-18 | sí | 32 |
| 33 | 32 | 33 | 2026-10-22 | 2026-10-22 | sí | 33, 66 |
| 34 | 33 | 34 | 2026-10-23 | 2026-12-10 | no | 50 |
| 35 | 34 | 35 | 2026-10-23 | 2026-10-23 | sí | 34, 35, 36 |
| 36 | 35 | 36 | 2026-10-23 | 2026-12-20 | no | 53 |
| 37 | 36 | 37 | 2026-10-25 | 2027-01-15 | no | ninguna |
| 38 | 37 | 38 | 2026-10-26 | 2027-01-25 | no | ninguna |
| 39 | 38 | 39 | 2026-10-26 | 2027-02-15 | no | ninguna |
| 40 | 39 | 40 | 2026-10-28 | 2027-02-25 | no | ninguna |
| 41 | 40 | 41 | 2026-11-04 | 2027-03-15 | no | ninguna |
| 42 | 41 | 42 | 2026-11-06 | 2027-03-25 | no | ninguna |
| 43 | 42 | 43 | 2026-11-12 | 2027-04-15 | no | ninguna |
| 44 | 43 | 44 | 2026-11-15 | 2027-04-25 | no | ninguna |
| 45 | 44 | 45 | 2026-11-19 | 2027-05-15 | no | ninguna |
| 46 | 45 | 46 | 2026-11-20 | 2027-05-25 | no | ninguna |
| 47 | 46 | 47 | 2026-11-25 | 2026-11-25 | sí | 47 |
| 48 | 47 | 48 | 2026-11-27 | 2026-11-27 | sí | 48 |
| 49 | 48 | 49 | 2026-12-03 | 2026-12-03 | sí | 49 |
| 50 | 49 | 50 | 2026-12-10 | 2026-12-10 | sí | 50 |
| 51 | 50 | 51 | 2026-12-12 | 2026-12-12 | sí | 51 |
| 52 | 51 | 52 | 2026-12-17 | 2026-12-17 | sí | 52 |
| 53 | 52 | 53 | 2026-12-20 | 2026-12-20 | sí | 53 |
| 54 | 53 | 54 | 2024-12-12 | 2024-12-12 | sí | 54 |
| 55 | 54 | 55 | 2024-12-20 | 2024-12-20 | sí | 55 |
| 56 | 55 | 56 | 2024-12-22 | 2024-12-22 | sí | 56 |
| 57 | 56 | 57 | 2024-12-26 | 2024-12-26 | sí | 57 |
| 58 | 57 | 58 | 2024-12-29 | 2024-12-29 | sí | 58 |
| 59 | 58 | 59 | 2025-01-20 | 2025-01-20 | sí | 59 |
| 60 | 59 | 60 | 2025-01-25 | 2025-01-25 | sí | 60 |
| 61 | 60 | 61 | 2025-01-26 | 2025-01-26 | sí | 61 |
| 62 | 61 | 62 | 2025-01-27 | 2025-01-27 | sí | 62 |
| 63 | 62 | 63 | 2025-01-28 | 2025-01-28 | sí | 63 |
| 64 | 63 | 64 | 2025-03-20 | 2025-03-20 | sí | 64 |
| 65 | 64 | 65 | 2025-12-20 | 2025-12-20 | sí | 65 |
| 66 | 65 | 66 | 2026-10-22 | 2026-10-22 | sí | 33, 66 |
| 67 | 66 | 67 | 2026-10-29 | 2026-10-29 | sí | 67 |
Fechas distintas sin coincidencia en esa columna original: 11.

**Fecha Emision (las dos diferencias; las otras 64 coinciden)**

| Fila Sheet | ID | Fila original | Fecha original | Fecha Sheet | Coincide | Filas originales con esa fecha |
|---|---|---|---|---|---|---|
| 4 | 3 | 4 | 2026-07-03 | 2025-12-04 | no | 2 |
| 5 | 4 | 5 | 2026-07-03 | 2025-12-04 | no | 2 |
Fechas distintas sin coincidencia en esa columna original: 0.


### Evidencia del formato y de las versiones

Ambos libros usan epoch 1900 (base 1899-12-30). En la cartera no hay fórmulas en
ninguno de los dos archivos. Las fechas están guardadas como valores numéricos,
no como textos ambiguos: en el XML, G4 pasa de 46280 a 46251, G5 de 46290 a 46258,
y G42 de 46332 a 46471. F4 y F5 pasan de 46206 a 45995. Por lo tanto, las diferencias
no son solo de formato visual. El origen usa `DD/MM/YYYY`.

Huellas SHA-256 de los archivos leídos (para identificar estas fotos sin guardarlas en git):

- `para_pegar_en_la_sheet_2026-09-22.xlsx`:
  `d789fcf22e08003aef64a9456fa76def92f2c2848753aed05ab923cf9f557bcb`.
- `NAVAR - Cash Flow (export Sheets 2026-09-22c).xlsx`:
  `0117ca4606cc2f9cbc3c81240337b36f3d420425ff3768c1d50ceda9e2088f44`.

### Revisión del código, con líneas

Referencias a `clientes/navar/herramientas/importar_cashflow.gs`, que quedó intacto:

- **195–196:** convierte y abre la Sheet temporal. No tenemos esa foto ni los valores
  que devolvió `getValues()` en producción; no se puede culpar o absolver esa conversión.
- **269–283 y 301–312:** normaliza encabezados y reordena columnas, sin transformar
  fechas. En estos archivos los 12 encabezados coinciden y no hay colisiones al
  normalizarlos; el destino solo agrega 14 columnas vacías.
- **286–315:** conserva filas manuales y agrega las nuevas completas. Las 66 filas
  del destino tienen marca `Tango Live`; con esta foto no queda ninguna `viva`.
  Renumerar solo cambia la primera celda, no la fecha. No hay desfasaje de fila aquí
  al ejecutar el código con los datos observados.
- **320–323:** cada columna toma `r[c]` del mismo arreglo `finales`, desde la misma
  fila inicial y con el mismo largo. Para Cartera `formulas: []` (66–67), por lo que
  no se omiten F ni G. La prueba local conserva todas las fechas. No simula filtros,
  concurrencia, fallos del servicio ni el código efectivamente instalado en Google.
- **225:** elimina la temporal al terminar. **143 y 206:** `ok` registra cantidades,
  no compara fechas contra el Excel. **172–177:** el Registro guarda nombre y detalle,
  no una huella del contenido importado. Falta evidencia histórica para cerrar la causa.

**No hay una línea demostrada como causante del cambio de fechas.** Cambiar la escritura
a un bloque, cambiar las fechas a ISO o quitar filtros ahora sería un arreglo supuesto.
Si una reproducción muestra que la temporal ya trae fechas distintas, corresponde
evaluar leer el XLSX sin conversión y verificar sus seriales; eso sería otra decisión
con evidencia, no una corrección aplicada en esta tarea.

### Archivos tocados y pruebas

- Este archivo: estado, diagnóstico, tabla y pasos de revisión.
- `clientes/navar/documentos/manual_cash.md`, §7: incidente abierto, explícitamente
  sin arreglo aplicado.
- `lector/pruebas/comparar_fechas_importacion.py`: lee los dos archivos sin escribirlos,
  empareja por ID, compara las 12 columnas, lista todas las coincidencias de fecha y
  calcula sus huellas. Rechaza ID repetidos, encabezados normalizados repetidos y fórmulas.
- `lector/pruebas/probar_volcado_fechas.cjs`: ejecuta el `.gs` real en memoria, sin
  reescribir su lógica. Prueba crecimiento, reducción, filas manuales, encabezados
  reordenados y repetición con datos inventados. Opcionalmente recibe las dos fotos por
  entrada estándar; los datos reales no quedan guardados en el script ni en archivos auxiliares.

Resultado: las pruebas inventadas pasan; con las **66 filas reales**, `_volcar_` produce
las 66 filas del origen con todas sus columnas y fechas intactas, también en la segunda
pasada. Esto prueba el armado local, **no** la API de Google ni la causa histórica.

Para repetir (pasar las dos rutas autorizadas de «Archivos para el análisis» como argumentos):

```sh
python lector/pruebas/comparar_fechas_importacion.py "$archivo_origen" "$export_sheet" --node /ruta/a/node
node lector/pruebas/probar_volcado_fechas.cjs </dev/null
```

Se usó el Python del entorno existente del repositorio principal (openpyxl ya declarado
en `requirements.txt`) y Node del runtime disponible. **No se instalaron dependencias.**
No se modificaron los archivos fuente, el lector, el vigilante, `crear_cash.gs` ni la Sheet.

### Qué falta probar en Google, y cómo

Apps Script y la conversión de Drive **no se ejecutaron acá**. La revisión debe hacerse
en una copia de la Sheet, con una versión congelada del XLSX, sin mezclarla con nuevos
archivos del vigilante y sin disparadores que se superpongan:

1. Recuperar, si existe, la revisión exacta del archivo de las 15:55 y confirmar qué
   versión del script estaba instalada. Anotar ID/revisión y huella del archivo;
   el nombre solo no basta. Comparar esa revisión con la foto actual.
2. En la copia, usar **finauto → Importar Tango (cobrar / pagar / cheques)**. No usar
   «Importar lo nuevo ahora»: puede saltarse el archivo por la firma guardada.
   Poner puntos de interrupción en Apps Script para inspeccionar la temporal al entrar
   a `_volcar_` de Cartera, `finales` después de la línea 315 y el destino tras la línea 324.
   La temporal se elimina al salir: capturar los valores antes del `finally`.
3. Comparar las 66 tuplas ID/número/importe/emisión/pago entre XLSX, temporal, `finales`
   y destino inmediato. Para la versión actual, G4 debe ser 2026-09-15, G5 2026-09-25,
   G42 2026-11-06, G43 2026-11-12 y G46 2026-11-20; F4/F5 deben ser 2026-07-03.
   El criterio completo es **cero diferencias en las 66 filas**, no solo estos ejemplos.
4. Repetir primero sin filtro y después con Tipo = `Propio Emitido`, en copias separadas
   del mismo estado inicial. Si falla, guardar función/línea y valores ya escritos.
   Si la temporal difiere, investigar conversión; si `finales` difiere, armado; si solo
   difiere el destino, escritura o actividad simultánea. No deducirlo del `ok`.
5. Exportar inmediatamente y volver a ejecutar el comparador. Repetir la importación:
   deben seguir siendo 66 filas y cero diferencias. Verificar el cheque propio afectado
   en el Cash de la copia y que ninguna fecha de la cartera actual pase a 2027.

### Controles finales

- `git diff --check`: sin errores.
- Búsqueda de nombres propios: vacía en el manual y los dos scripts nuevos, y en todo
  el texto agregado a esta consigna. La búsqueda sobre el archivo completo de la
  consigna devuelve tres líneas preexistentes: las dos rutas autorizadas y el propio
  comando de búsqueda. Se conservaron para no alterar las instrucciones originales.
- Estado final: `lista para revisión` del diagnóstico; **el incidente sigue abierto**.
- Commit intentado en `tarea/fechas-importacion`: el sandbox rechazó crear
  `Finnauto/.git/worktrees/Finnauto-tarea03/index.lock` (`Operation not permitted`).
  No se creó commit ni se agregaron archivos al índice. Quedan los cuatro archivos
  de esta entrega para que la revisión los commitee desde el repositorio principal,
  según el circuito de `tareas/LEEME.md`.

## Revisión

(lo completa Claude)
