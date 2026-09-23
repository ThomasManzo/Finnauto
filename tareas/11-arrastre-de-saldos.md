# Tarea 11 — Los bancos sin extracto nuevo arrastran el último saldo conocido
Estado: lista para revisión
Rama: tarea/arrastre-saldos

## Objetivo

En el bloque `1 · Bancos` de las pantallas de cash, hoy queda **la celda vacía** cuando un banco no
tiene extracto de ese día. Resultado: la pantalla muestra la posición incompleta y no se entiende
cuánta plata hay.

Pedido de Thomas (23/09): *"prefiero que carguen los saldos que tenemos hasta ahora y que los que
no, sean iguales al día anterior"*. O sea: **arrastrar el último saldo conocido** de cada cuenta
hasta que llegue uno nuevo.

**Con una condición que no se negocia: el saldo arrastrado tiene que verse distinto del confirmado.**
Si una cuenta muestra el saldo de hace ocho días como si fuera el de hoy, alguien lo va a leer como
plata confirmada. Hoy mismo pasa con una cuenta que viene del 15/09 y es la más negativa de todas.

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `CLAUDE.md`, `clientes/navar/documentos/manual_cash.md`
(§3 y §4).

Situación real al 23/09, para entender el caso: Galicia y Macro tienen saldo al 22/09, BBVA al
21/09, Corrientes al 16/09 y Nación al 15/09. Nación es la cuenta más negativa y la que tiene el
descubierto nuevo, así que es justo la que más importa no malinterpretar.

Un detalle del que conviene acordarse: el archivo de un banco puede llamarse con la fecha de hoy y
traer movimientos hasta ayer (el home banking no cierra el día en curso). El lector usa el
contenido, no el nombre, y eso está bien: no cambiarlo.

El tablero web **ya arrastra** (suma el último saldo de cada cuenta y lo avisa). Lo que falta es
que las pantallas de la planilla hagan lo mismo. Si de paso conviene unificar el criterio con el
tablero, decilo en "Qué hice", pero **no toques `dashboard/`** en esta tarea.

## Archivos permitidos

- `clientes/navar/herramientas/crear_cash.gs`
- `clientes/navar/documentos/manual_cash.md` — §3 y §4.
- `tareas/11-arrastre-de-saldos.md`

No tocar los lectores, `importar_cashflow.gs` ni `dashboard/`.

## Resultado esperado

1. En el bloque de bancos, cada cuenta muestra su **último saldo conocido** en todas las columnas
   posteriores, hasta que aparezca uno nuevo. Nunca más una celda vacía por falta de extracto.
2. **El arrastrado se distingue a simple vista**: elegí un recurso y explicá por qué (por ejemplo,
   en gris o en itálica, o con un asterisco y una nota al pie). Que se entienda sin leer el manual.
3. Al lado del nombre de cada banco, o en una fila debajo, **desde cuándo** es ese saldo: "al 15/09"
   o "hace 8 días". Que el número y su antigüedad viajen juntos.
4. En el total de bancos, aclarar cuántas cuentas están arrastradas: por ejemplo
   *"incluye 3 cuentas con saldo arrastrado (la más vieja, del 15/09)"*.
5. **Nada de esto cambia ninguna cuenta**: `Saldo inicial`, los `SALDO AL CIERRE` y el neteo con el
   descubierto siguen funcionando igual. Es presentación del bloque de bancos. Si al arrastrar un
   saldo se modificara algún total, **parar y explicarlo** en vez de cambiarlo.
6. Que el arrastre **no invente el futuro**: se arrastra hasta hoy (el día en curso), no a lo largo
   de las columnas estimadas hacia adelante, donde el saldo ya lo calcula la proyección.

## Comprobaciones

Apps Script no corre acá:

1. Explicar en criollo cómo quedó la fórmula del arrastre.
2. Ejemplo a mano con el caso real de arriba: qué tendría que mostrar cada uno de los cinco bancos
   en la columna de hoy, cuál en gris y con qué leyenda, y qué dice el total.
3. Guion de prueba en la planilla: qué mirar antes y después de correr "Armar solapa Cash".
4. Sin nombres propios de personas. Commit en la rama; si el sandbox no deja, anotarlo.

## Qué hice

- Trabajé en el worktree existente `Finnauto-tarea11`, rama `tarea/arrastre-saldos`.
- `crear_cash.gs`: agregué un detalle informativo por **banco + empresa + cuenta**, con saldo
  sin acuerdo y una fila debajo con estado y fecha en cada columna. El arrastrado queda gris
  e itálico y dice **ARRASTRADO · al dd/mm/aaaa**: el texto evita depender sólo del color.
  El margen por banco suma las cuentas y el acuerdo una sola vez; también queda gris si arrastra.
  El aviso junto al total cuenta las cuentas arrastradas, la fecha más vieja y las sin foto previa.
  Se actualiza con las listas y TODAY(); una cuenta nueva requiere rearmar las pantallas.
- Conservé las fórmulas auxiliares originales, el total real, Saldo inicial, ambos cierres,
  los totales operativos y el descubierto acordado/usado/disponible. El nuevo detalle no
  alimenta ninguno. **Después del último extracto, el total real conserva su vacío anterior**:
  el detalle arrastrado no reemplaza la proyección. El aviso y el manual explican esta diferencia.
  Tampoco corregí la regla anterior de tomar la primera foto en ciertos cortes sin saldo:
  corregirla en los auxiliares cambiaría totales; el nuevo detalle no usa esa regla.
- `manual_cash.md`: actualicé solamente §3 y §4. Actualicé también el texto de Instrucciones
  generado por el script. No toqué lectores, importador, tablero, datos privados ni otras solapas.
  No instalé dependencias y no publiqué cambios en Google Sheets.

### La fórmula en criollo

Para cada cuenta, busca la fecha más reciente de Saldos Bancarios que no pase del corte:
fin del período para columnas pasadas, hoy para la semana/mes actual. Toma el saldo de esa
fecha, aunque hayan pasado días sin extracto nuevo. Si la fecha es anterior al corte, lo marca
ARRASTRADO; si coincide, Confirmado. No busca por nombre de archivo. Si la columna empieza
mañana o después, deja vacío. Si no hay foto previa, lo dice en vez de traer una del futuro.
Cero es un saldo válido y visible. Si hay dos fotos de la misma cuenta en esa última fecha,
o el importe está vacío o es texto, pide revisar; no suma fotos duplicadas ni las muestra como
confirmadas. El conteo de antigüedad usa las fechas disponibles; ante REVISAR, primero resolver
la foto inválida, no interpretar el conteo como validación del importe.

### Ejemplo al 23/09/2026

La consigna aporta fechas, no importes. `S` representa el saldo de cada cuenta en la fecha
indicada, sin inventar montos. Suponiendo una cuenta por banco y sin otras cuentas:

| Banco | Saldo visible el 23/09 | Aspecto y leyenda debajo |
|---|---|---|
| Galicia | S del 22/09 | gris e itálica · ARRASTRADO · al 22/09/2026 |
| Macro | S del 22/09 | gris e itálica · ARRASTRADO · al 22/09/2026 |
| BBVA | S del 21/09 | gris e itálica · ARRASTRADO · al 21/09/2026 |
| Corrientes | S del 16/09 | gris e itálica · ARRASTRADO · al 16/09/2026 |
| Nación | S negativo del 15/09 | gris e itálica, signo menos visible · ARRASTRADO · al 15/09/2026 |

Los cinco están arrastrados respecto del 23/09, incluso los que tienen foto de ayer.
El aviso junto al total dice **“5 cuentas con saldo arrastrado · más viejo al 15/09/2026”**.
El margen con acuerdo de los cinco queda gris. En la columna del 22/09, Galicia y Macro
sí dicen Confirmado al 22/09; los otros tres arrastran. La semana y el mes que contienen
el 23/09 usan ese día como corte. Mañana y los períodos futuros quedan vacíos en el detalle.
El total real del diario el 23/09 sigue vacío si B3 es 22/09, exactamente como antes;
no se reemplaza por la suma de estas cinco fotos. La caja manual u otras cuentas, si existen,
se agregan al detalle y al conteo con su propia fecha.

### Qué comprobé acá

- JavaScriptCore de macOS cargó el script sin errores de sintaxis.
- Prueba local con una Sheet simulada y listas inventadas: generé las tres pantallas con
  el código anterior y el nuevo; comparé **2.591 fórmulas preexistentes**, identificando las
  referencias por su renglón para descontar el desplazamiento de filas. Todas conservaron
  su cálculo, incluidas las auxiliares de bancos y los totales. Esto compara fórmulas,
  **no es una ejecución ni una conciliación de importes en Google Sheets**.
- La prueba separó cuentas del mismo banco, empresas distintas e historia de una misma cuenta;
  verificó el balance de paréntesis de todas las fórmulas generadas. Herramientas temporales:
  `/tmp/probar_arrastre.js` y `/tmp/crear_cash_antes.gs`; comando usado:
  `/System/Library/Frameworks/JavaScriptCore.framework/Versions/A/Helpers/jsc /tmp/probar_arrastre.js`.
- `git diff --check` sin errores. Sólo los tres archivos permitidos tienen cambios.

### Guion de prueba en la planilla (pendiente)

1. En una copia descartable con listas ficticias, antes de actualizar el script, guardar por
   **etiqueta y fecha** valores y fórmulas del total real, Saldo inicial, ambos SALDO AL CIERRE,
   ingresos, egresos, deuda y descubierto acordado/usado/disponible de las tres pantallas.
   Mantener iguales las listas, B2/B3 y la inflación al comparar. Si se cambió la inflación
   a mano, conservar ese valor al rearmar (el comportamiento previo de rearmado no se modificó).
2. Usar cinco cuentas inventadas con las fechas del ejemplo; fijar el día de prueba en una
   copia o trasladar las fechas respecto de hoy. Pegar el script y correr “Armar solapa Cash”.
   Comparar cada importe guardado: ninguna diferencia. Revisar que los grupos de cuotas,
   auxiliares ocultas y fórmulas no se hayan desplazado mal. Si cambia un total, frenar.
3. Mirar hoy: cinco saldos grises con su fecha, cinco márgenes grises y aviso de cinco cuentas
   con la fecha más vieja. Revisar ancho, lectura y altura de las leyendas en diario, semanal
   y mensual. En el día con foto, Confirmado y sin itálica de arrastre; margen verde/ámbar/rojo
   según signo. En el futuro, saldo, leyenda y margen vacíos; el cierre proyectado sigue igual.
4. Cargar foto nueva de una cuenta con fecha de hoy: cambia su importe y fecha, deja de ser
   arrastrada y el conteo baja sin rearmar. Quitarla: vuelve el saldo previo y su advertencia.
   Verificar días intermedios, fin de semana, cambio de mes y período actual parcial.
5. Probar saldo 0 y negativo, dos cuentas del mismo banco con fechas distintas, otra empresa
   y caja manual. El acuerdo se suma una sola vez en el margen del banco. Antes de la primera
   foto debe decir Sin saldo previo; una foto futura no debe aparecer antes de su fecha.
6. Duplicar la última foto o dejar su importe vacío/texto: Revisar saldo / REVISAR con fecha,
   y margen Revisar cuentas. Corregirla: vuelve el saldo válido. Agregar una cuenta y rearmar:
   aparece con su fecha. Rearmar dos veces: sin filas ocultas equivocadas ni grupos duplicados.
7. Validar en es_AR que no haya errores de fórmula y que el gris prevalezca sobre los colores
   de margen incluso cuando el número es negativo. Apps Script y su formato condicional
   **no se ejecutaron acá**; esta validación visual y de recálculo queda para revisión.

### Commit

Intenté preparar el commit con `git add` de los tres archivos permitidos, pero el sandbox
lo rechazó: no puede crear `Finnauto/.git/worktrees/Finnauto-tarea11/index.lock`
(`Operation not permitted`). **No hay commit creado**; los cambios quedan en este worktree
y la revisión puede commitearlos en `tarea/arrastre-saldos`, como prevé tareas/LEEME.md.

### Dudas y alcance

No hace falta tocar el tablero para este cambio. En una tarea futura conviene contrastar el
criterio por cuenta y sus fechas con el tablero y acordar si se cambia la base de los totales;
esta tarea conserva los cálculos actuales por pedido expreso.


## Revisión
