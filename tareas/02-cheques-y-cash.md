# Tarea 02 — Fechas de cheques mal leídas + dos mejoras del cash
Estado: lista para revisión
Rama: tarea/cheques-y-cash

## Objetivo

Tres cosas, en este orden de importancia:

**A (BUG, lo más importante).** Las fechas de los cheques que el lector carga en la Sheet **no
coinciden con las de Tango**. Hay que encontrar por qué y arreglarlo.

**B.** En las pantallas de cash, el bloque de bancos tiene que mostrar el saldo **neteado con el
descubierto acordado**, con color: si al banco todavía le queda margen, en verde.

**C.** En la fila "Cuotas y tarjetas con débito automático" del cash, poder desplegar y ver el
detalle por banco.

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `CLAUDE.md`, `clientes/navar/LEEME.md` y
`clientes/navar/documentos/manual_cash.md` (§3 y §4 describen las pantallas).

Cliente real, en producción: los números de este cash se le muestran a la empresa. Un error acá
se ve en una reunión.

### A · La evidencia del bug (ya verificada, no hace falta re-descubrirla)

Comparación entre el export de Tango y lo que quedó en la solapa **Cartera de Cheques** de la Sheet:

| Cheque | Fecha en el export de Tango | Fecha en la Sheet | |
|---|---|---|---|
| Propio 68150612 (ENVASANDO S.R.L., $10.872.165,02) | `Fecha del cheque` = 2026-09-25 · `Fecha de emisión` = 2026-07-03 | pago 2026-08-24 · emisión 2025-12-04 | MAL |
| Propio 68150561 (ENVASANDO S.R.L., $11.000.000) | `Fecha del cheque` = 2026-09-15 · `Fecha de emisión` = 2026-07-03 | pago 2026-08-17 · emisión 2025-12-04 | MAL |
| Tercero 32283267 (VIMER, $5.000.000) | `Fecha del cheque` = 2026-11-06 | 2027-03-25 | MAL |
| Tercero 32283268 (VIMER, $5.000.000) | `Fecha del cheque` = 2026-11-12 | 2027-04-15 | MAL |
| Tercero 32283269 (VIMER, $5.600.000) | `Fecha del cheque` = 2026-11-20 | 2027-05-25 | MAL |
| Tercero 32487757 (VIMER, $600.000) | `Fecha del cheque` = 2026-10-18 | 2026-10-18 | BIEN |

Número de cheque e importe coinciden **siempre**; solo las fechas están mal, y **no en todas las
filas** (32487757 salió bien). Los corrimientos no son constantes, así que no es un offset fijo ni
un problema de zona horaria: mirar primero si las filas se están **desalineando** (fecha tomada de
otra fila) o si se lee una **columna por posición** en vez de por nombre.

Dato que probablemente importa: **el orden de columnas cambia entre exports del mismo tipo.**

- `A Cheques terceros 2026-09-21.xlsx` → `Nro. de cheque, Banco, Cliente, Cód. cliente, CUIT del cliente, CUIT del cheque, Fecha del cheque, Origen, Cód. estado, Desc. subestado, Estado, Subestado, Importe, Cuenta cartera, Tipo de cheque`
- El export del 22/09 del mismo tipo trae: `Nro. de cheque, Banco, Cód. cliente, Cliente, CUIT del cheque, Fecha del cheque, Origen, Desc. subestado, Cód. estado, Estado, Subestado, Importe, Tipo de cheque, Cuenta cartera` (cambia el orden y falta `CUIT del cliente`).
- `A Cheques propios 2026-09-21.xlsx` → `Nro. de cheque, Banco, Cód. proveedor, Razón social, Fecha de emisión, Fecha del cheque, Importe mon. cta., Estado, Cód. cta. emision, Tipo de cheque`; el del 22/09 es igual **sin** `Cód. cta. emision`.

Ojo con el vocabulario de Tango: en cheques propios, `Fecha de emisión` es cuándo se emitió y
**`Fecha del cheque` es la fecha de pago** (la que importa para el cash). En terceros, `Fecha del
cheque` es la fecha de cobro.

**Consecuencia que hay que verificar arreglada**: con la fecha correcta (25/09/2026, futura), el
cheque propio de ENVASANDO tiene que **aparecer como egreso en el cash el 25/09**. Hoy, con la
fecha mal (24/08, pasada), el lector lo marca `REVISAR` y lo saca del tablero. Lo mismo del otro
lado: los cheques de VIMER tienen que entrar a cobrar en **octubre y noviembre de 2026**, no en 2027.

Archivos de datos para reproducir (se leen, no se modifican; rutas absolutas, están fuera del worktree):

```
/Users/thomasmanzo/Library/CloudStorage/GoogleDrive-thomasezequielmanzo@gmail.com/Mi unidad/NAVAR - Datos/Cheques/
/Users/thomasmanzo/Documents/Finnauto/clientes/navar/privado/NAVAR - Cash Flow (export Sheets 2026-09-22b).xlsx
```

### B · El saldo neteado con el descubierto

Pedido textual de Thomas (22/09): *"si el saldo del banco es negativo real está bien, pero quiero
que se le descuente el descubierto: si en Nación el saldo es de −100 M, mostrarlo en verde, porque
es 100 M negativo pero el descubierto es de 100 M; en descubiertos baja el disponible y en el cash
se muestra el saldo neteado, o sea 0 en verde."*

O sea, en el bloque `1 · Bancos` de las tres pantallas, por banco:
**mostrado = saldo real + descubierto acordado de ese banco** (= cuánto margen le queda).

El descubierto acordado por banco ya lo calcula la pantalla: es la misma fuente que alimenta la
fila `Descubierto acordado` del bloque de descubiertos. **Reusar esa fuente, no inventar otra.**

Colores (propuesta a implementar, porque "0 en verde" esconde que la línea está agotada):

- **verde** si el neteado es > 0 (le queda margen);
- **amarillo/ámbar** si es exactamente 0 (usó todo el acuerdo: no queda aire);
- **rojo** si es < 0 (excedido, o sin acuerdo informado).

Casos reales que tienen que quedar bien: **Nación** está excedido y **Corrientes** no tiene acuerdo
informado (acordado = 0 o vacío) → esos dos NO pueden quedar en verde. Si el acuerdo de un banco es
vacío, tratarlo como 0, nunca como "sin límite".

No cambiar el bloque de descubiertos (acordado / usado / disponible): sigue igual y es el que
muestra el detalle. Tampoco cambiar `Saldo inicial` ni los `SALDO AL CIERRE`: **el neteo es solo
la presentación del bloque de bancos**, no entra en las cuentas de abajo. Si eso obliga a agregar
una fila aparte en vez de pisar la existente, agregarla y explicarlo.

### C · Desplegable de cuotas por banco

En las tres pantallas, la fila `Cuotas y tarjetas con débito automático` muestra un total. Hay que
poder abrirla y ver **una fila por banco** con lo que aporta a ese período.

En Google Sheets esto se hace con **agrupar filas** (`shiftRowGroupDepth` / `Sheet.getRowGroup`,
colapsadas por defecto), de modo que aparezca el `+` al costado. Las filas de detalle se calculan
con la misma fórmula del total pero filtrando por banco, tomando los bancos de la lista de Deuda
Bancaria (no una lista escrita a mano: si mañana hay un banco nuevo, tiene que aparecer solo).

Si al implementarlo resulta que agrupar filas rompe la estructura de la pantalla (las filas se
generan por fórmula y el alto es fijo), **parar y anotarlo en "Qué hice"** en vez de forzarlo:
es la mejora menos importante de las tres.

## Archivos permitidos

- `lector/tango.py` — el arreglo del bug A.
- `clientes/navar/herramientas/crear_cash.gs` — B y C.
- `clientes/navar/documentos/manual_cash.md` — documentar B y C (§3) y sumar el bug a la lista de
  errores corregidos (§7), con fecha 22/09.
- `tareas/02-cheques-y-cash.md` — este archivo: "Qué hice" y el Estado.
- Un archivo de prueba nuevo bajo `lector/pruebas/` si hace falta para A (ver más abajo).

**No tocar**: `vigilante.py`, `importar_cashflow.gs`, los otros lectores, `finauto.py`, ni nada de
`clientes/*/privado/` (leer sí, escribir no). No cambiar el formato del `para_pegar` (lo consume el
importador de la Sheet).

## Resultado esperado

1. **A**: la causa raíz identificada y explicada en criollo en "Qué hice" (qué línea, por qué), y
   arreglada. Las fechas del `para_pegar` tienen que coincidir con el export para **todas** las
   filas, no solo las seis de la tabla.
2. Una **prueba automática** que deje el bug clavado: un Excel chico armado por la prueba misma
   (datos inventados, dos o tres cheques, incluyendo un archivo con las columnas en otro orden y
   otro al que le falta una columna) → correr el parser → verificar que cada fecha salga donde
   corresponde. Que corra con `python -m pytest` o como script suelto; si el repo no usa pytest,
   seguir el estilo que ya haya.
3. **B** y **C** implementados en `crear_cash.gs`, con comentarios en criollo.
4. El manual actualizado.

## Comprobaciones

1. `python -m py_compile lector/tango.py` pasa.
2. La prueba nueva pasa.
3. Correr el lector sobre los archivos reales de Drive (ruta de arriba) y verificar **las seis
   filas de la tabla de evidencia**, una por una, contra el export. Pegar el resultado en "Qué hice".
4. Recorrer **todas** las filas de cheques del `para_pegar` generado y compararlas contra el
   export de origen: reportar cuántas coinciden y cuántas no. Que no queden diferencias.
5. Verificar que el cheque propio de ENVASANDO ($10.872.165,02) ya **no** quede marcado `REVISAR`,
   y que los tres de VIMER queden en 2026.
6. Apps Script no se puede ejecutar acá: para B y C, anotar en "Qué hice" qué se probó leyendo y
   qué queda para probar en la Sheet.
7. `grep -n -i -E "priscilla|karina|celia|miriam|milagros|charles|thomas" <archivos tocados>` vacío.
8. Commitear en la rama `tarea/cheques-y-cash`. Si el sandbox no deja commitear, anotarlo y seguir.

Al terminar: completar "Qué hice" y poner `Estado: lista para revisión`.

## Qué hice

### Cambios y alcance

- `lector/tango.py`: corregí `localizar` (líneas 195–223). Antes recorría nombres ordenados y
  pisaba la elección para cada empresa/lista: una minúscula podía ganarle a una fecha más nueva.
  Ahora elige por fecha `AAAA-MM-DD` del nombre; ante empate usa modificación y un desempate
  estable. Los archivos sin fecha quedan detrás de los fechados (entre ellos manda modificación).
  No cambié columnas, fechas de cada fila, filtros de negocio ni formato del `para_pegar`.
- `lector/pruebas/test_cheques.py`: prueba automática con dos fotos de propios y terceros,
  tres cheques inventados de cada tipo, columnas invertidas y una columna opcional ausente.
  Verifica selección, emisión, pago/cobro, observaciones y salida Excel. La foto vieja tiene una
  modificación más nueva a propósito. Confirmé que falla con `localizar` original y pasa ahora.
- `clientes/navar/herramientas/crear_cash.gs`: bancos con margen y tres colores; ceros visibles;
  saldos reales por banco en auxiliares ocultos, reutilizando el acuerdo existente. No entran
  acuerdos en Saldo inicial, cierres ni en el cálculo del descubierto usado/disponible.
  Cuotas con detalle por banco, grupos plegados y total que excluye el detalle para no duplicar.
  Los bancos se leen de líneas y cronograma de Deuda Bancaria. Se limpian grupos previos al rearmar.
  Instrucciones actualizadas con roles, sin nombres de personas.
- `clientes/navar/documentos/manual_cash.md`: §3 explica bancos y desplegable; §7 registra el
  error comprobado y aclara que el incidente de fechas en producción sigue abierto.
- Este archivo: estado, resultados y límites. No instalé dependencias. Usé Python del entorno
  ya existente del repo principal y Node del runtime disponible; ninguno se modificó.

### A: qué quedó comprobado y qué NO quedó resuelto

**No doy por arreglada la causa del incidente de producción.** La selección vieja era un bug
real, pero no explica las fechas equivocadas de la evidencia. El lector anterior, ejecutado
contra Drive, genera 60 filas: los dos propios y los terceros 32283267/32283268 ya salen con las
fechas correctas; 32283269 y 32487757 faltan porque toma la foto del 16/09. No encontré un
corrimiento de columnas o de filas en el parser: busca los encabezados por nombre y ordena
cada registro completo. Leer el export de la Sheet confirmó las fechas incorrectas denunciadas.
Queda pendiente rastrear qué archivo se importó y el paso de importación/conversión/carga en
producción. Leí el importador para orientarme, pero no lo modifiqué ni ejecuté.

Corrí `tango.procesar` directamente contra la carpeta absoluta de Drive indicada arriba,
con `hoy=2026-09-22`, y `escribir_para_pegar` hacia un directorio temporal que se eliminó al
terminar. No usé el CLI sobre Drive porque escribe al lado de las entradas. Ningún original,
archivo privado ni salida publicada fue modificado.

Selección corregida y comparación independiente, reabriendo el Excel generado y comparando
contra los encabezados del export (empresa, tipo, número, importe, emisión y pago/cobro;
contando también duplicados, faltantes y sobrantes):

| Export elegido | Filas admitidas y coincidentes |
|---|---:|
| A Cheques propios 2026-09-22.xlsx | 10 |
| A Cheques terceros 2026-09-21.xlsx | 42 |
| AA Cheques terceros 2026-09-21.xlsx | 14 |
| **Total** | **66/66; 0 diferencias, 0 faltantes, 0 sobrantes** |

Las filas no admitidas conservan las reglas previas de estado, importe y antigüedad. No había
export de terceros del 22/09 en la raíz de esa carpeta al verificar; no inventé uno.

| Cheque | Emisión generada | Pago/cobro export = salida | Importe | REVISAR al 22/09 |
|---|---|---|---:|---|
| 68150612 | 2026-07-03 | 2026-09-25 | 10.872.165,02 | No |
| 68150561 | 2026-07-03 | 2026-09-15 | 11.000.000 | Sí: venció realmente el 15/09 |
| 32283267 | vacía en este export | 2026-11-06 | 5.000.000 | No |
| 32283268 | vacía en este export | 2026-11-12 | 5.000.000 | No |
| 32283269 | vacía en este export | 2026-11-20 | 5.600.000 | No |
| 32487757 | vacía en este export | 2026-10-18 | 600.000 | No |

Pasé el `para_pegar` temporal por `cash_limpio.leer`: el propio de 10.872.165,02 aparece en
`egresos_cashflow` como CHEQUE el 2026-09-25, sin vencido pendiente; los cuatro terceros aparecen
en `cartera_cheques` en las fechas de octubre/noviembre de la tabla. Esto prueba el lector del
cash, no el recálculo del Apps Script ni el tablero publicado.

### B y C: pruebas locales y límites

- Sintaxis JavaScript: `node --check` pasó.
- Con una simulación local de las llamadas de Apps Script, comparé las fórmulas antes/después
  por concepto, compensando los cambios de número de fila: 1.200 en diario, 588 en semanal y
  354 en mensual permanecen iguales (incluidos inicial, cierres y descubiertos). Los totales
  de bloques ahora suman solo renglones principales; las cuotas detalladas no se suman dos veces.
- En las tres pantallas, quitar de la fórmula de detalle únicamente el filtro por banco deja
  exactamente la fórmula del total. Verifiqué creación de grupo, pedido de colapso, tres reglas
  de color que excluyen celdas vacías y un banco inventado nuevo al regenerar. No es ejecución
  real de Sheets ni una prueba visual. Los auxiliares de comprobación quedaron en `/tmp`,
  fuera del repo; la única prueba nueva versionable es la de cheques, como autoriza la consigna.
- Recalculé desde el export real de la Sheet: Nación −101.709.806,61 + 100.000.000 =
  **−1.709.806,61, rojo**; Corrientes −45.306.818,06 + 0 = **−45.306.818,06, rojo**.
  Galicia +1.651,17 y Macro +13.949.717,87 de margen. Un neto exactamente cero tiene formato
  visible y regla ámbar; el acuerdo vacío suma cero.
- Revisé la documentación oficial de
  [agrupación de filas](https://developers.google.com/apps-script/reference/spreadsheet/range#shiftrowgroupdepthdelta).
  La limpieza de grupos empieza en fila 2 para permitir volver a correr con el control arriba.
- **Límite de C:** las filas se crean al ejecutar `Armar solapa Cash`, y el código las dimensiona
  según los bancos encontrados. Un banco nuevo aparece sin editar código al rearmar, pero **no
  aparece inmediatamente por la mera importación de Deuda Bancaria**. Conectar esa regeneración
  al importador/disparador excede los archivos autorizados; no lo hice. Queda para revisión si
  esta limitación alcanza el pedido o si se abre otra tarea para automatizarla.
- Pendiente en la Sheet: ejecutar dos veces Armar solapa Cash; abrir/cerrar el `+` en las tres
  pantallas; comprobar fórmulas sin errores en configuración regional española, suma de detalle
  contra total, colores y ceros; cotejar los cierres antes/después; probar un banco nuevo al rearmar.
  No se publicó ni ejecutó Apps Script en producción.

### Comandos y controles finales

Desde la raíz, usando el Python del entorno existente:

```sh
python -m py_compile lector/tango.py
python -m unittest discover -s lector/pruebas
node --check < clientes/navar/herramientas/crear_cash.gs
git diff --check
```

Todos pasaron. El Python del sistema no tenía `openpyxl`: por eso usé el entorno existente,
sin instalar paquetes. El chequeo de nombres da vacío en código, prueba y manual. Sobre la
consigna completa devuelve cuatro coincidencias preexistentes (rutas, cita original y el propio
comando de búsqueda); no alteré esa evidencia ni las instrucciones para esconderlas.

### Commit

No pude commitear. En la rama correcta `tarea/cheques-y-cash`, `git add` de los cinco archivos
permitidos falló: `Unable to create .../.git/worktrees/Finnauto-tarea02/index.lock: Operation
not permitted`. El índice vive en el repo principal, fuera de los permisos de escritura del
sandbox. No cambié permisos ni intenté otro repositorio. Los cambios están sin stage y sin
commit, listos para que el revisor los commitee en esta rama.


## Revisión

(lo completa Claude)
