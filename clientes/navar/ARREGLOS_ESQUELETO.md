# Arreglos al esqueleto "NAVAR - Cash Flow Limpio"

Revisado el 12/09/2026 sobre `NAVAR - Cash Flow Limpio - Esqueleto.xlsx` (11 solapas,
consolidado de 438 columnas: 365 días + 59 semanas + 12 meses + año).

**El diseño está bien y no se cambia**: listas de detalle + un consolidado que se
calcula solo. Lo de abajo son correcciones puntuales, en orden de importancia.
Cada una dice qué celda, qué fórmula y cómo copiarla.

> **Estado al 12/09/2026 (noche):** Cowork aplicó los 8 puntos en
> `NAVAR_-_Cash_Flow_Limpio.xlsx`. Al revisarlo aparecieron tres cosas más, que
> arregla `arreglar_cash_v2.py` y deja en `privado/NAVAR - Cash Flow Limpio v2.xlsx`
> (**la v2 es la buena**):
> 1. Las semanas del consolidado eran bloques de 7 días desde el 1° de cada mes
>    (martes a lunes en septiembre). Ahora son lunes a domingo, cortadas en el
>    borde de mes.
> 2. Las filas EJEMPLO seguían en las listas e inventaban números. Vaciadas.
> 3. Lo proyectado de proveedores, cobranzas, impuestos, cheques, préstamos y
>    hoja verde estaba en Movimientos como "Proyectado", y esas filas del
>    consolidado solo leen Real + listas. Movido a las listas como filas
>    agregadas (marcadas "AGREGADO del cash viejo").
>
> La v2 se recalculó con un motor de Excel en Python y coincide al peso con las 8
> semanas proyectadas del cash viejo.

> Regla para copiar fórmulas en `Cash Flow Consolidado`: las columnas de tipo
> **Día** (fila 6 = "Día") llevan la fórmula SUMIFS; las de tipo **Semana / Mes /
> Año** llevan `=SUM(...)` de los días y **no se tocan**. Al copiar una fórmula
> corregida hay que pegarla SOLO en las columnas Día de esa fila. La forma segura:
> filtrar/seleccionar por el valor "Día" de la fila 6, o pegar de a bloques de 7
> salteando la columna Semana.

---

## 1 · Lo vencido no aparece en ninguna semana futura ⚠ (el más importante)

**Qué pasa.** Las filas que leen listas de detalle (Cuentas a Cobrar, Cuentas a
Pagar, Deuda Impositiva, cronograma de Deuda Bancaria, Cartera de Cheques) suman
lo pendiente **en la columna del día de vencimiento**. Una factura vencida el
20/08 que sigue impaga cae en la columna del 20/08 (pasado) y nunca en el futuro.
Resultado: la **deuda atrasada con proveedores** (hoy ~$206M) y los impuestos
vencidos **no están en el cash proyectado**. Es justo lo que el cliente quiere
mirar.

**Arreglo.** Agregar un bloque **"VENCIDO A LA FECHA (a regularizar)"** arriba del
consolidado, entre la fila 3 y la 4 (insertar 6 filas). No es por día: es un
stock, calculado a hoy. Fórmulas (columna B):

| Fila | Texto (col A) | Fórmula (col B) |
|---|---|---|
| a | Vencido a cobrar (clientes) | `=SUMIFS('Cuentas a Cobrar'!$I$2:$I$5000,'Cuentas a Cobrar'!$F$2:$F$5000,"<"&TODAY())` |
| b | Vencido a pagar (proveedores) | `=SUMIFS('Cuentas a Pagar'!$J$2:$J$5000,'Cuentas a Pagar'!$G$2:$G$5000,"<"&TODAY())` |
| c | Impuestos vencidos impagos | `=SUMIFS('Deuda Impositiva'!$D$2:$D$5000,'Deuda Impositiva'!$C$2:$C$5000,"<"&TODAY(),'Deuda Impositiva'!$E$2:$E$5000,"<>Pagado")` |
| d | Cuotas bancarias vencidas impagas | `=SUMIFS('Deuda Bancaria'!$G$34:$G$199,'Deuda Bancaria'!$D$34:$D$199,"<"&TODAY(),'Deuda Bancaria'!$H$34:$H$199,"Pendiente")` |
| e | Cheques propios vencidos sin pagar | `=SUMIFS('Cartera de Cheques'!$H$2:$H$5000,'Cartera de Cheques'!$F$2:$F$5000,"<"&TODAY(),'Cartera de Cheques'!$B$2:$B$5000,"Propio Emitido",'Cartera de Cheques'!$I$2:$I$5000,"En Cartera")` |
| f | **TOTAL VENCIDO A PAGAR** | `=b+c+d+e` |

Y una fila más en el cuerpo del consolidado, después de "SALDO FINAL DEL DIA":
**"Saldo si regularizo todo lo vencido"** = `=B40 - $B$f` (con la referencia
absoluta al total). Muestra los dos mundos: el saldo "pateando" y el saldo
"poniéndose al día".

## 2 · Hoja Verde, Insumos y Otros se caen del cashflow

**Qué pasa.** `Cuentas a Pagar` admite 5 categorías (`Proveedores MP y Logist.`,
`Proveedores AA`, `Hoja Verde`, `Insumos`, `Otro`), pero el consolidado solo suma
lo pendiente de las dos primeras (filas 25 y 26). Una factura pendiente de hoja
verde cargada en Cuentas a Pagar **no aparece en ninguna semana**.

**Arreglo.** Tres filas, misma forma que la 25:

`B27` (Pago Insumos):
```
=SUMIFS(Movimientos!$G$2:$G$5000,Movimientos!$B$2:$B$5000,B$5,Movimientos!$E$2:$E$5000,"Insumos",Movimientos!$K$2:$K$5000,"Real")-SUMIFS('Cuentas a Pagar'!$J$2:$J$5000,'Cuentas a Pagar'!$G$2:$G$5000,B$5,'Cuentas a Pagar'!$D$2:$D$5000,"Insumos")
```
`B28` (Pago Hoja Verde):
```
=SUMIFS(Movimientos!$G$2:$G$5000,Movimientos!$B$2:$B$5000,B$5,Movimientos!$E$2:$E$5000,"Hoja Verde",Movimientos!$K$2:$K$5000,"Real")-SUMIFS('Cuentas a Pagar'!$J$2:$J$5000,'Cuentas a Pagar'!$G$2:$G$5000,B$5,'Cuentas a Pagar'!$D$2:$D$5000,"Hoja Verde")
```
`B31` (Otros Egresos):
```
=SUMIFS(Movimientos!$G$2:$G$5000,Movimientos!$B$2:$B$5000,B$5,Movimientos!$E$2:$E$5000,"Otros",Movimientos!$K$2:$K$5000,"Real",Movimientos!$G$2:$G$5000,"<0")-SUMIFS('Cuentas a Pagar'!$J$2:$J$5000,'Cuentas a Pagar'!$G$2:$G$5000,B$5,'Cuentas a Pagar'!$D$2:$D$5000,"Otros")
```
Copiar cada una a todas las columnas **Día** de su fila.

Además: en la validación de `Cuentas a Pagar!D2:D500` cambiar `Otro` por
`Otros`, para que coincida con el nombre en Movimientos.

## 3 · Columna Empresa en TODAS las listas

**Qué pasa.** `Saldos Bancarios`, `Cartera de Cheques`, `Deuda Bancaria` y `Deuda
Impositiva` no tienen columna Empresa (A/AA). El cash viejo separaba "Caja AA";
el tablero de finauto muestra la posición **por empresa** con un botón. Sin esto,
el consolidado sirve para el grupo pero no se puede ver A y AA por separado.

**Arreglo.** Agregar columna `Empresa` con validación `A,AA` en:
- `Saldos Bancarios`: entre `Banco` y `Cuenta / Nro`.
- `Cartera de Cheques`: después de `Tipo`.
- `Deuda Bancaria` (bloques A y B): después de `Banco`.
- `Deuda Impositiva`: después de `Impuesto`.

Las fórmulas del consolidado no cambian (suman las dos); las columnas nuevas
las usa finauto.

## 4 · Subir el tope de 500 filas a 5000

Todas las fórmulas leen hasta la fila 500 (Movimientos, listas) y el cronograma
bancario hasta la 199. Nadie sabe cuántos movimientos por mes tienen; si son
200, en marzo se corta **sin avisar** (las filas de abajo simplemente no suman).

**Arreglo.** Buscar y reemplazar en toda la planilla: `$500` → `$5000` y
`$199` → `$1999`. Extender las validaciones de datos y las fórmulas de las
columnas calculadas de cada lista (Saldo Pendiente, Estado, Días de Atraso,
Semana) hasta la fila 5000.

## 5 · Regla de carga: factura pagada con cheque

**Qué pasa.** Si una factura se paga con cheque propio y la marcan "Pagado" al
**emitir** el cheque, se cuenta una vez (fila 21, cheque en cartera hasta que se
paga). Si la dejan pendiente hasta que el cheque **se cobra**, se cuenta dos
veces (fila 25 + fila 21). Nada en la planilla impide la segunda.

**Arreglo.** En `Instrucciones`, agregar la regla: *"Una factura pagada con cheque
propio se marca Pagado (columna Pagado = importe) el día que se emite el cheque.
El cheque queda en Cartera de Cheques con estado En Cartera hasta que se debita;
ahí pasa a Depositado/Acreditado."* Y la simétrica para clientes: *"Una factura
cobrada con cheque de terceros se marca Cobrado el día que se recibe el cheque."*

## 6 · Horizonte y saldo inicial

`B2` = 01/01/2026 y `B3` = 0. Para arrancar: `B2` = el lunes desde el que cargan
(sugerido: 31/08/2026, así el cash viejo y el nuevo se solapan una semana y se
puede comparar) y `B3` = bancos + efectivo real de ese lunes, **sin cheques**.

## 7 · Un bloque "Posición de deuda" (lo que ellos miran)

**Qué pasa.** El cash viejo tenía, abajo, la evolución de deuda impositiva /
proveedores / bancaria (inicial, ingreso, pago, final). Estaba mal calculado
(sumaba los pagos como deuda nueva), pero **es lo que el cliente mira**. El
esqueleto nuevo tiene el detalle en solapas pero **ningún lugar donde ver el
total de deuda de hoy y cuánto vence en las próximas semanas**.

**Arreglo.** Solapa nueva `Posición de Deuda` (todo fórmulas, nada a mano):

| | Pendiente total | Vencido | Vence en 7 días | En 30 días | En 90 días |
|---|---|---|---|---|---|
| Proveedores (Cuentas a Pagar) | `SUMIFS(J, estado<>Pagado)` | `venc < HOY` | `HOY ≤ venc < HOY+7` | … | … |
| Impositiva | ídem sobre Deuda Impositiva | | | | |
| Bancaria (cronograma) | ídem sobre Deuda Bancaria B) | | | | |
| Cheques propios en cartera | ídem sobre Cartera | | | | |
| **TOTAL** | | | | | |

Más una línea con el capital vigente total de las líneas (bloque A de Deuda
Bancaria) y la situación BCRA por banco. Con eso el objetivo del cliente
("adelantarse a los vencimientos impositivos y bancarios") tiene una pantalla.

## 8 · Menores

- `Movimientos!M` (Semana): la fórmula `=IF(A3="","",B3-WEEKDAY(B3,2)+1)` devuelve
  `""` cuando no hay ID. Si cargan una fila sin ID, la semana queda vacía y esa
  fila no entra en ninguna vista semanal. Cambiar la condición a `B3=""`
  (por fecha, no por ID).
- `Vista Semanal`: aclarar en Instrucciones que la llena finauto (es lo que hace
  `memoria/`), no la persona de oficina. Dejar la solapa, pero que nadie la
  cargue a mano.
- La fila 9 "Saldo Bancario Real (control)" solo muestra valor los días en que se
  cargó un saldo. Está bien, pero conviene rotularla *"(solo los días con
  extracto cargado)"* para que no parezca que falta dato.
- Nombre del archivo: quitar "Esqueleto" cuando se entregue.
