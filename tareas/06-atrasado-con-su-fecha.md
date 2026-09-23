# Tarea 06 — Lo que venció y no se pagó tiene que verse en la fecha que correspondía
Estado: lista para revisión
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

- Trabajé en el worktree recibido, rama `tarea/atrasado-con-fecha`, inicialmente limpio.
  Pasé el estado a `en curso` antes de editar la implementación.
- Toqué solamente los tres archivos permitidos. En `manual_cash.md`, solamente §3 y §4.
  No usé datos reales ni `privado/`, ni modifiqué importadores, lectores o dashboard.
- Elegí (a): un renglón por período debajo del bloque 6, con fechas repetidas ahí para poder
  leerlo sin confundir los totales en B con la primera fecha. Evita crear miles de filas por
  vencimientos históricos y se actualiza por fórmula sin rearmar filas cada día.
- `crear_cash.gs`: agregué el rango de vencimiento a cada concepto del stock y una función que
  toma SU MISMA fórmula y le agrega límites de fechas. Conserva importes, estados, filtros y
  exclusiones actuales; el vencido a cobrar no se incluye. Día/semana/mes usan inicio incluido
  y fin excluido, además de vencimiento anterior a hoy. El detalle no depende del corte real
  del extracto, de promedios, de inflación ni de Plan.
- Agregué importes separados para antes del primer período y después del último. El segundo
  cubre un extracto tan atrasado que la pantalla diaria ya no alcanza a hoy. La deuda de 2007
  va a antes si integra el stock; proveedores con `REVISAR` siguen excluidos. No cambié esa regla.
- Agregué total repartido y diferencia contra el total original, redondeada a centavos, con cero
  visible. Stock y detalle muestran centavos; las etiquetas nuevas se ajustan en su celda.
  Fechas vacías/cero no se disfrazan de deuda antigua: si el stock las incluye, provocan diferencia
  para revisar. El control no garantiza detectar datos inválidos que el propio stock ya excluya.
- Actualicé la explicación en Instrucciones y manual: es el pendiente de hoy ubicado en su fecha
  original, no una historia de saldos. El pago desaparece por fórmula cuando se actualiza la lista
  (estado o nueva foto de pendientes); no afirmo que el extracto actualice por sí solo esa lista.

### Verificación local realizada

- Ejecuté el JavaScript con el motor de macOS (`osascript -l JavaScript`), sin instalar dependencias.
  Usé un simulador temporal de las llamadas de la Sheet y un evaluador acotado de `SUMIFS` con datos
  inventados. Archivos de apoyo en `/tmp/navar06_test_setup.py` y `/tmp/navar06_test.js`, fuera del repo;
  no son una prueba dentro de Google Sheets ni un evaluador completo de sus fórmulas.
- Comparé todas las fórmulas y valores de las celdas preexistentes generadas por la versión de HEAD
  y por la nueva, en las tres pantallas: idénticos. La maqueta no tenía bancos; por eso esto verifica
  la estructura común, no una corrida con las listas y bancos reales. También comprobé que no
  quedaran marcadores de fórmula sin resolver. Se generaron 1413/693/417 fórmulas en diario/semanal/mensual.
- Caso base al 30/09/2026: proveedor A 100,25 del 25/09; AA 50,50 del 21/09; proveedor antiguo
  admitido 20 del 01/01/2007; cuota bancaria 30,75 del 28/09; impuesto 40 del 31/08; cheque propio
  10,10 del 29/09. Total independiente: **251,60**. Cuadró con la suma por períodos + antes + después.
  Septiembre dio 191,60; semana del 21/09 dio 150,75; semana del 28/09 dio 40,85.
- Agregué casos excluidos: proveedor `REVISAR`, filas pagadas, cheque de terceros, cheque debitado,
  vencido a cobrar, vencimiento de hoy y futuro. Conservé intencionalmente el filtro vigente de
  cheques propios (el stock no excluye sus observaciones `REVISAR`).
- Al marcar pagada la factura de 100,25, el total bajó a **151,35** y desapareció del 25/09.
  Con saldo pendiente de 60,25, quedó solo ese importe en el día. Probé límites de semana/mes,
  extracto atrasado y una fecha vacía con importe 7: el control detectó diferencia 7.
- `git diff --check`: sin errores. Búsqueda sin distinguir mayúsculas de los nombres de personas
  identificados en el contexto: sin coincidencias en `crear_cash.gs` ni `manual_cash.md`.
  La consigna conserva el texto original del pedido; no se publica al cliente.

### Guion pendiente en una copia de prueba de la Sheet

1. Guardar una copia con las listas inventadas anteriores y los cierres de la versión anterior.
   Instalar esta versión de `crear_cash.gs` en esa copia y ejecutar **Armar solapa Cash**.
   No usar **Armar solapa Plan**, porque reemplaza decisiones. No hacerlo primero en producción.
2. Para repetir el ejemplo, fijar temporalmente B2 en 30/09/2026 y B3 en 29/09/2026 en las tres
   pantallas. Usar fechas reales de celda, no textos. Ver que no haya `#ERROR!` o `#VALUE!` y que
   las fechas repetidas abajo se vean como fechas (incluido el separador regional de fórmulas).
3. Revisar bloque 6: total 251,60 en las tres pantallas. La factura de 100,25 debe quedar el
   25/09 en Cash, en la semana del 21/09 en Semanal y en septiembre en Mensual. Sumar el renglón
   completo + antes + después: debe dar 251,60 y el control debe mostrar 0,00. No sumar a cobrar.
4. El importe antiguo 20 debe quedar en antes, sin aparecer otra vez en la primera columna.
   Marcar ese proveedor `REVISAR`: deben bajar tanto stock como antes en 20.
5. Volver al caso base. Cambiar la factura de 100,25 a Pagado: total 151,35 y su importe desaparece
   de los tres detalles, sin rearmar. Probar también quitarla de la foto de pendientes y pago parcial.
   Comparar versiones con las mismas listas: todos los cierres y disponibles deben ser iguales.
6. Fijar B2 primero en 25/09 y luego en 26/09: la factura no está vencida el 25, entra el 26 en la
   columna original del 25 (o su semana/mes). Si el día quedó fuera de la ventana, debe estar en antes.
7. Atrasar B3 hasta julio en Cash: los vencimientos de septiembre deben ir a después del último
   período, sin perderse ni moverse a julio. El control debe seguir en 0,00. Probar una fecha vacía
   o cero con importe: revisar cualquier diferencia señalada, sin inventarle una fecha.
8. Rearmar dos veces y revisar que no se dupliquen filas, que las etiquetas sean legibles y que el
   detalle conserve centavos. Restituir las fórmulas originales de B2/B3 antes de usar la copia.

### Límites y continuación

- No corrí Apps Script ni recalculé una Sheet real: quedan pendientes separadores regionales,
  evaluación nativa de fechas vacías/texto, permisos, rendimiento, aspecto visual y conciliación
  con datos reales. La prueba local no sustituye esos controles antes de publicar.
- Tiene sentido llevar este mismo detalle informativo y su conciliación al tablero web en la tarea
  07, conservando los filtros y dejando fuera la curva. No lo implementé acá para no pisar esa tarea.

- **Commit pendiente por sandbox**: intenté `git add` con los tres archivos permitidos y falló:
  `Unable to create '/Users/thomasmanzo/Documents/Finnauto/.git/worktrees/Finnauto-tarea06/index.lock': Operation not permitted`.
  No se pudo preparar el índice ni crear el commit. Los cambios quedan en esta rama/worktree para
  que el revisor los commitee, conforme a `tareas/LEEME.md`. No cambié permisos ni toqué `main`.
- Estado final: **lista para revisión**; implementación terminada, con verificación en Sheet y
  commit pendientes explícitos.

## Revisión
