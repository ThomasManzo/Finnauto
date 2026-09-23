# Tarea 05 — Que un filtro puesto a mano no vuelva a romper la importación
Estado: lista para revisión
Rama: tarea/importador-filtros

## Objetivo

Hoy (22/09) el cash estuvo roto varias horas porque alguien dejó **filtros puestos a mano** en
solapas de la planilla. El importador escribió sobre esas solapas y **desacomodó las filas**: un
cheque propio real de $10,8 M quedó con fecha de agosto y salió del cash, y cheques a cobrar de
noviembre aparecieron en 2027. Después, todas las importaciones automáticas empezaron a fallar con
`No se admite esta operación en un rango con una fila filtrada` y la planilla quedó congelada.

Que eso no pueda volver a pasar. Filtrar una lista para buscar algo es lo más normal del mundo:
el sistema tiene que aguantarlo.

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `CLAUDE.md`, `clientes/navar/documentos/manual_cash.md` §6.

Lo que pasó, con fechas (hora de la planilla, que va 4 h atrás de Buenos Aires):

- `11:55 tango ok` — esta importación **escribió mal**: había filtros activos y las columnas
  quedaron corridas entre sí. Las Observaciones de una fila describían el cheque correcto mientras
  la fecha era la de otra fila. Nadie se enteró: dijo `ok`.
- `13:32`, `14:16`, `14:32`, `15:32`, `16:32` — todas `ERROR` con el mensaje del rango filtrado.
- `16:51 tango ok` — recién después de sacar a mano los filtros de cinco solapas
  (Cuentas a Cobrar, Cuentas a Pagar, Cartera de Cheques, Movimientos y Saldos Bancarios).

**Lo más grave no es el error: es la importación que dijo `ok` y escribió mal.** Un error se ve;
un `ok` mentiroso no.

Quién escribe: `clientes/navar/herramientas/importar_cashflow.gs`, función `_volcar_` (escribe
columna por columna con `setValues` y estira fórmulas con `copyTo`), llamada desde `_importar_`.

Los análisis de las tareas 02 y 03 están en `tareas/02-*.md` y `tareas/03-*.md`, y en
`lector/pruebas/` quedaron dos scripts de comparación que sirven de referencia.

## Archivos permitidos

- `clientes/navar/herramientas/importar_cashflow.gs`
- `clientes/navar/herramientas/aviso_diario.gs` — si corresponde sumar una alerta (ver abajo).
- `clientes/navar/documentos/manual_cash.md` — §6 y §7.
- `tareas/05-importador-a-prueba-de-filtros.md`
- `lector/pruebas/` — si hacés una prueba.

## Resultado esperado

1. **Antes de escribir, el importador deja la solapa sin filtro y sin filas ocultas**, y cuando
   termina la deja como la encontró si eso es posible sin riesgo. En Apps Script: `sheet.getFilter()`
   y `.remove()`; ojo que también existen las **vistas de filtro** (`filter views`), que son otra cosa
   y no las remueve `getFilter()`. Si una vista de filtro no se puede manejar desde el script, hay
   que **detectarla y abortar con un error claro** en vez de escribir mal.
2. **Si por cualquier motivo no se puede garantizar la escritura correcta, NO escribir**: abortar y
   anotar en Registro con un mensaje que diga qué hacer ("sacá el filtro de la solapa X y volvé a
   correr Importar lo nuevo"). Vale más no importar que importar mal.
3. **Verificación después de escribir**: comparar unas cuantas filas escritas contra lo leído del
   `para_pegar` (por ejemplo, las primeras y las últimas de cada solapa, y que la cantidad de filas
   coincida). Si no coinciden, dejarlo en Registro como `ERROR` aunque la escritura no haya tirado
   excepción. Es lo que habría cazado el `ok` mentiroso de las 11:55.
4. Que el mensaje de Registro diga **en qué solapa** estuvo el problema (hoy el error no lo decía).
5. Si el aviso diario puede avisar "hay una importación que dijo ok pero no cuadró", sumalo.

## Comprobaciones

Apps Script no corre en el worktree. Entonces:

1. Explicar en "Qué hice" **exactamente** qué hace el código nuevo, paso por paso.
2. Dejar escrito el **guion de prueba manual** para correr en la planilla: qué filtro poner, en qué
   solapa, qué botón apretar y qué tendría que pasar (incluido el caso de la vista de filtro).
3. Si se puede probar la lógica pura con Node (como hizo la tarea 03 con `probar_volcado_fechas.cjs`),
   hacerlo y decir qué cubre y qué no.
4. `grep -n -i -E "priscilla|karina|celia|miriam|milagros|charles|thomas"` vacío en lo tocado.
5. Commitear en la rama; si el sandbox no deja, anotarlo.

## Qué hice

### Alcance y recorrido del código

Trabajé en el worktree y rama indicados. No accedí a datos privados, no publiqué scripts,
no ejecuté importaciones en producción ni mandé mails. Solo cambié los archivos permitidos.

1. `importar_cashflow.gs`: `_importar_` toma un candado del documento para que dos ejecuciones
   de este importador no mezclen sus escrituras. Si está ocupado, devuelve un error para reintentar.
2. Convierte el `para_pegar` como antes. Antes de escribir datos comprueba que existan todas las
   solapas de origen y destino del lector y consulta las vistas guardadas con
   `Sheets.Spreadsheets.get`. **Nuevo requisito de instalación: habilitar Google Sheets API
   en Servicios**, además de Drive API. No instalé dependencias locales.
3. Si la API no responde, falta el servicio o hay vistas guardadas en cualquiera de las solapas
   afectadas, aborta antes de cargar la primera. El mensaje identifica las solapas y qué hacer.
   Bloquea incluso vistas cerradas: la API no informa qué vista tiene abierta cada persona.
4. En todas las solapas afectadas quita el filtro común con `getFilter().remove()`, muestra todas
   las filas con `showRows` y hace `flush`. Repite esa preparación al entrar a cada volcado.
   Una excepción al quitar el filtro o mostrar filas corta la carga. Comprueba que no quede filtro.
   No repone filtros ni filas ocultas: los números de fila pueden corresponder a otros datos y
   el rango anterior del filtro puede excluir filas nuevas. Esa decisión está explicada en el manual.
5. Conserva el armado por encabezados, filas manuales, marcas de reemplazo, ID y fórmulas existente.
   Agregué rechazo de encabezados duplicados, columna de marca ausente y filas no vacías sin el
   campo identificador de la columna B, para evitar descartarlas y declarar éxito silenciosamente.
6. Después del volcado y de extender fórmulas, hace `flush` y relee **todas las celdas de datos**
   del bloque: nuevas, manuales conservadas y cola borrada. Compara valores y tipos exactamente;
   las fechas se comparan por milisegundos. Las columnas declaradas de fórmula y encabezados
   vacíos quedan fuera de la comparación. Comprueba además la última fila con datos en B contra
   la cantidad esperada. No se limita a una muestra ni a sumas que pueden ocultar fechas corridas.
7. Si no coincide, lanza `VERIFICACION_NO_CUADRA` con solapa, fila y columna (sin publicar valores).
   Cualquier excepción del volcado agrega solapa/bloque y advierte sobre posible carga parcial.
   El disparador registra ERROR y no guarda la firma del archivo fallido; permite reintentarlo.
8. Los cinco botones manuales ahora registran ok o ERROR, igual que el disparador. Registro
   también se deja sin filtro común y con filas visibles antes de insertar su entrada.
9. `aviso_diario.gs`: destaca explícitamente los registros con `VERIFICACION_NO_CUADRA` de las
   últimas 24 horas, además de la alerta de error que ya existía. No afirma que hubo un ok:
   la nueva verificación impide que ese resultado llegue a ok.
10. `manual_cash.md`: solo agregados en §6 y §7, con operación, instalación y límites.
    `probar_importador_filtros.cjs`: prueba nueva con datos inventados.
    `probar_volcado_fechas.cjs`: adapté el doble de Sheet a las nuevas llamadas de filtro/flush
    y compartí Date con el contexto JavaScript para comparar fechas como ocurre en Apps Script.

### Comprobaciones locales

Usé Node ya disponible en `/Applications/ChatGPT.app/Contents/Resources/cua_node/bin/node`:

```sh
node lector/pruebas/probar_importador_filtros.cjs
node lector/pruebas/probar_volcado_fechas.cjs </dev/null
node --check < clientes/navar/herramientas/importar_cashflow.gs
node --check < clientes/navar/herramientas/aviso_diario.gs
git diff --check
```

La prueba nueva ejecuta las funciones reales con un doble de planilla en memoria. Cubre
achicar, agrandar, lista vacía, preservar manuales, columnas reordenadas, repetir sin duplicar,
quitar filtro y mostrar filas antes de escribir, fallo al quitar filtro sin modificar celdas,
API ausente/respuesta incompleta/vistas guardadas, fecha corrompida silenciosamente, cola no
borrada, ERROR en ambos caminos, firma automática sin avance y alerta diaria sin enviar mail.
No simula la conversión XLSX, el motor de fórmulas ni el comportamiento del servidor Google.

El chequeo de nombres dio vacío en código, pruebas y manual. En la consigna devuelve
únicamente el propio comando de búsqueda preexistente; no cambié esa instrucción.

### Guion manual pendiente (primero en una COPIA de la Sheet)

1. Copiar la planilla y usar archivos inventados en una carpeta Drive de prueba; cambiar
   `CARPETA_RAIZ` solo en el proyecto de esa copia. No instalar disparadores ni mandar mails.
   Habilitar Drive API y Google Sheets API. Preparar `para_pegar` con tres cheques de fechas e
   importes distintos, filas para cobrar/pagar y bancos, y anotar sus datos completos.
2. En Cartera de Cheques: Datos → Crear un filtro, dejar visible solo un tipo de cheque;
   ocultar además una fila a mano. Hacer lo mismo con un criterio en Cuentas a Cobrar y Pagar.
   Menú finauto → Importar Tango. Debe terminar ok en Registro; las tres listas deben quedar
   visibles y sin filtros. Comparar TODAS las fechas, números, importes y observaciones con
   el archivo, además de contar las filas y conservar una fila manual inventada.
3. Repetir con filtros en Movimientos y Saldos Bancarios → Importar Bancos. Probar también
   Importar Tesorería AA, Impuestos y ambos bloques de Deuda. Verificar que sus fórmulas sigan
   presentes, que no se invadan los títulos del otro bloque y que los totales del cash cuadren
   al recomputarlos desde las listas. Estos cálculos no se probaron localmente.
4. Cambiar el archivo para que tenga más filas, luego menos y luego solo encabezados. Repetir
   la importación, comprobar limpieza de restos y conservación de manuales. Volver al archivo
   con datos. Revisar especialmente la plantilla de fórmulas tras una lista vacía (comportamiento
   anterior conservado; esta tarea no modifica su estrategia).
5. Crear y guardar una **vista de filtro en la última solapa de Tango**, Cartera de Cheques.
   Dejarla abierta y apretar Importar Tango: debe haber ERROR que la nombre y ninguna lista
   de Tango cargada. Cerrar la vista y repetir: también debe bloquear. Eliminarla y correr
   Importar lo nuevo ahora con archivo nuevo/no importado: debe cargar y recién entonces
   guardar su firma. Una vista en una solapa ajena a ese lector no debe bloquearlo.
6. Deshabilitar Sheets API en la copia: Importar Tango debe dar ERROR por no poder comprobar
   vistas y no cargar datos. Rehabilitar. Probar una protección que impida quitar un filtro
   con la cuenta ejecutora: ERROR con solapa, sin cargar las listas.
7. En la copia, insertar temporalmente antes de `_verificarVolcado_` una alteración de una
   fecha recién escrita. Importar: debe decir ERROR / VERIFICACION_NO_CUADRA, nunca ok ni
   toast de listo; señalar fila/columna y no avanzar firma. Quitar la alteración y reimportar.
   Ejecutar avisoDiarioPrueba: debe destacar NO CUADRÓ sin enviar nada.
8. Probar una vista temporal de navegador (si Google la ofrece a esa cuenta) y dos usuarios
   con vistas distintas. Este caso **no está validado**: no asumir que aparece en `filterViews`.
   Medir duración con listas del tamaño habitual y verificar permisos, filas agrupadas/ocultas,
   formatos regionales y fechas después de la conversión. No desplegar dando estos puntos por hechos.

### Límites y dudas para revisión

- No probé Apps Script ni la Sheet real. Los filtros son evidencia del incidente; estas pruebas
  no demuestran la causa histórica de las fechas alteradas ni reparan cargas anteriores.
- Se compara contra el origen YA convertido por Drive. Si esa conversión altera una fecha,
  este control no lo detecta: hay que cotejar el XLSX original en la prueba manual.
- Las vistas guardadas se detectan; no se puede afirmar desde acá cobertura de vistas temporales
  del navegador. El candado tampoco bloquea ediciones humanas, otros scripts o filtros que
  alguien agregue durante la ejecución. No existe una transacción con reversión de toda la carga.
- Ante un fallo después de empezar puede quedar carga parcial. El error lo advierte; no usar
  el cash hasta revisar y reimportar. Si Google impide escribir incluso en Registro (protección,
  permisos, indisponibilidad), tampoco es posible garantizar la anotación; revisar Ejecuciones.
- Las columnas calculadas no se comparan contra valores del Excel. El control de cantidad sigue
  el contrato existente de la columna B. No certifica sumas de pantallas ni exactitud del lector.
- La alerta diaria sigue la ventana existente de 24 horas; no audita antiguos ok ni detecta
  alteraciones humanas posteriores a la importación.
- Documentación consultada: [filtros y vistas de Google Sheets](https://developers.google.com/workspace/sheets/api/guides/filters)
  y [Sheet de Apps Script](https://developers.google.com/apps-script/reference/spreadsheet/sheet).


### Commit

No pude commitear: `git add` de los seis archivos permitidos falló al crear
`Finnauto/.git/worktrees/Finnauto-tarea05/index.lock` con `Operation not permitted`.
El índice está fuera de los permisos de escritura del sandbox. No cambié permisos ni intenté
esquivar esa restricción. Los cambios quedan sin stage y sin commit en `tarea/importador-filtros`
para que el revisor los commitee. Estado: lista para revisión, con validación en Google pendiente.

## Revisión
