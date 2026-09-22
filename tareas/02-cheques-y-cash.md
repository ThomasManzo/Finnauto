# Tarea 02 — Fechas de cheques mal leídas + dos mejoras del cash
Estado: pendiente
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

(lo completa Codex)

## Revisión

(lo completa Claude)
