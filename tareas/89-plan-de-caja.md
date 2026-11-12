# Tarea 89 — Planilla "Plan": ventas proyectadas, contenedores, stock y caja por semana
Estado: lista para revisión
Rama: tarea/89-plan-de-caja

## Objetivo
Un script de Apps Script que arma y recalcula una planilla de Google llamada **Plan** para un cliente importador
(compra contenedores en China y vende por Mercado Libre y Tiendanube). La planilla responde tres preguntas:
1. Con las ventas que proyectamos, **¿cuándo se queda sin stock cada producto?** (y si el próximo contenedor llega a tiempo).
2. **¿Cuánta plata hay en caja cada semana** de acá a N meses, con los cobros, los pagos de contenedores, los gastos fijos y las deudas?
3. Si la caja baja del mínimo, **¿cuánto tiene que poner cada socio y en qué semana?**
Además, mes a mes, **real contra proyectado** (unidades y pesos por producto).

## Contexto
- Leer `AGENTS.md`, `CLAUDE.md` y `tareas/LEEME.md`. **El repo es público: nada de datos reales.** Ni nombres de
  cliente, socios, proveedores ni montos reales. Ejemplos inventados (SKU `AB1001`, socios `Socio A` y `Socio B`).
- El cliente ya tiene dos planillas que NO se tocan en esta tarea:
  - **Datos**: el depósito. Tiene LISTAS (verdes, las llena un importador automático con encabezados en la **fila 1**)
    y CARGAS (naranjas, las llena el cliente a mano: fila 1 = ayuda, encabezados en la **fila 2**, datos desde la fila 3).
  - **Tablero**: la foto "si cerramos hoy" (fórmulas). No se lee desde el Plan.
- **Plan lee de Datos y nunca escribe en Datos.** Los contenedores (los que vienen y los planeados) y sus pagos ya se
  cargan en Datos: el Plan no los vuelve a pedir. En el Plan el cliente carga SOLO dos cosas: la proyección de
  ventas y la configuración (caja mínima, horizonte, supuestos).
- **Siempre buscar columnas por el nombre del encabezado**, nunca por posición (el cliente agrega columnas, por
  ejemplo una "Recuperado" en el medio de Mermas). Si falta una columna necesaria, no calcular esa parte y avisarlo
  en Controles.
- Dos cambios en Datos los hace Claude por su lado (no son parte de esta tarea, pero el Plan los tiene que usar):
  - `Contenedores.estado` suma el valor **`planeado`** (contenedor que todavía no se pidió). Los demás valores:
    `en producción`, `en camino`, `en aduana`, `nacionalizado`.
  - `Contenedor_pagos` suma al final la columna **`estado`** con `pagado` o `previsto`. **Vacío = `pagado`** (las filas
    viejas no la tienen). Un pago `previsto` tiene fecha futura: es lo que se va a pagar.

### Lo que hay en Datos (solo las columnas que usa el Plan)
LISTAS (encabezado fila 1):
- `Ventas`: `fecha` (fecha y hora), `estado` (las que dicen `cancelada` o `devuelta` no cuentan), `sku`, `unidades`,
  `canal` (`Mercado Libre` / `Tiendanube`), `sku_conocido` (`sí`/`no`), `ingresos_productos` (lo que pagó el comprador
  por los productos), `total_neto` (lo que efectivamente cobró la empresa después de comisiones y envíos).
- `galicia_saldo`: `fecha`, `saldo` (banco; un saldo por día, no todos los días).
- `mp_saldo`: `fecha`, `disponible`, `a_liberar` (Mercado Pago; `a_liberar` puede venir vacío).
- `mp_movimientos`: `fecha_liberacion`, `monto_neto` (cobros de Mercado Pago que se liberan en una fecha futura).
- `ml_publicidad`: `fecha`, `costo` (gasto diario de publicidad de Mercado Libre).
- `dolar`: `fecha`, `compra`, `venta` (se usa `compra`).

CARGAS (encabezado fila 2, datos desde la fila 3):
- `Productos`: `sku`, `producto`, `activo` (`sí`/`no`).
- `Contenedores`: `contenedor`, `proveedor`, `fecha_pedido`, `llegada_estimada`, `llegada_real`, `estado`, `fob_usd`.
- `Contenedor_productos`: `contenedor`, `sku`, `unidades`, `fob_unitario_usd`.
- `Contenedor_pagos`: `fecha`, `contenedor`, `concepto` (`anticipo`, `saldo`, `flete`, `seguro`, `despacho`,
  `impuestos`, `otros`), `moneda` (`ARS`/`USD`), `importe`, `dolar` (si fue en pesos), `pagado_por` (`empresa`/`socios`),
  `estado` (`pagado`/`previsto`/vacío).
- `Stock_conteo`: `fecha`, `sku`, `unidades`.
- `Mermas`: `fecha`, `sku`, `unidades`.
- `Gastos_fijos`: `concepto`, `moneda`, `importe_mensual`, `desde`, `hasta` (vacío = sigue).
- `Deudas`: `fecha`, `acreedor`, `concepto`, `moneda`, `importe`, `vencimiento`, `pagada` (`sí`/`no`), `fecha_pago`.
- `Logistica_flex`: `periodo` (`AAAA-MM`), `importe` (factura mensual de envíos, en pesos).
- `Capital`: `fecha`, `socio`, `tipo` (`aporte`/`retiro`), `usd`, `pesos`.

Reglas que ya usa el Tablero y el Plan tiene que respetar:
- **SKU normalizado**: mayúsculas, sin espacios, guiones ni puntos (`ab-1001 ` → `AB1001`), en todas las solapas.
- **Stock a una fecha** = último conteo de ese SKU hasta esa fecha + unidades de contenedores con `llegada_real`
  posterior al conteo y hasta la fecha − ventas posteriores al conteo (sin canceladas ni devueltas) − mermas posteriores.
- Fechas en hora de Buenos Aires (`America/Argentina/Buenos_Aires`). Montos con formato argentino `1.234.567,89`.

## Archivos permitidos
- `planillas/plan/plan_calculo.gs` (nuevo): **todas las cuentas, sin `SpreadsheetApp`** (funciones puras que reciben
  tablas como arrays de objetos y devuelven tablas). Es lo que se prueba con Node.
- `planillas/plan/plan_planilla.gs` (nuevo): leer Datos y Plan, armar las solapas, escribir resultados, disparador.
- `planillas/plan/probar_plan.cjs` (nuevo): prueba con Node y datos inventados (estilo `lector/pruebas/probar_control_cierre.cjs`:
  carga el `.gs` real en un `vm` y verifica resultados).
- `planillas/plan/LEEME.md` (nuevo): qué es, cómo se instala, qué carga el cliente, qué hace cada solapa. En criollo.
- esta consigna (secciones "Qué hice" y `Estado:`).

## Resultado esperado

### Cómo corre
- **Proyecto de Apps Script independiente** (no atado a la planilla, igual que el importador de Datos: así los
  editores del Plan no ven ni tocan el script). Abre las dos planillas por id: constantes `ID_DATOS = "PONER_ID_DATOS"`
  e `ID_PLAN = "PONER_ID_PLAN"` arriba de todo (Claude pone los ids reales al instalar; en el repo quedan así).
- Funciones para correr desde el editor:
  - `armarPlan()`: crea o completa las solapas. **Nunca borra lo que el cliente cargó.** Se puede correr N veces.
  - `recalcularPlan()`: lee, calcula y escribe las pantallas. Tiene que tardar bastante menos de 6 min con ~10.000 ventas.
  - `instalarDisparador()` / `quitarDisparador()`: `recalcularPlan` cada hora (a los 10 min de cada hora, después
    del importador de Datos). Que no queden disparadores duplicados.
- Cada corrida deja una línea en una solapa `Registro` (fecha, función, OK/ERROR, detalle). Si algo falla, el error queda
  ahí y las pantallas no quedan a medio escribir (calcular todo primero, escribir después).

### Solapas
Colores como en Datos: naranja = carga el cliente; azul = pantalla (solo valores, protegida con advertencia).

1. **Config** (naranja, dos columnas: parámetro | valor, con una nota explicando cada uno). Si una celda está vacía se
   usa el valor por defecto, que se muestra en una tercera columna "si queda vacío".
   - `inicio del plan`: por defecto, hoy.
   - `meses a proyectar`: por defecto 6.
   - `caja mínima ($)`: por defecto vacío → sin aportes calculados y aviso en Controles.
   - `dólar del plan`: por defecto, el último `dolar.compra`.
   - `día de pago de gastos fijos`: por defecto 5.
   - `día de pago de la publicidad de ML`: por defecto 12 (la factura del mes M vence el 12 del mes M+1 y se paga aparte).
   - `día de pago de la Flex`: por defecto 10 (la factura del mes M se paga en el mes M+1).
   - `días hasta cobrar una venta`: por defecto 7.
   - `% que se cobra de cada venta`, `% de publicidad sobre ventas de ML`, `% de Flex sobre ventas de ML`: por
     defecto, el histórico de los últimos 3 meses cerrados (ver abajo). En la columna "si queda vacío" se muestra ese
     histórico calculado, para que el cliente vea de dónde sale.
   - `plazo de reposición (días)`: por defecto 120.
   - `reparto de aportes`: una fila por socio (los distintos `socio` de `Capital`), por defecto partes iguales.
     Si la suma no da 100 %, aviso en Controles y se reparte en partes iguales.

2. **Ventas proyectadas** (naranja). Columnas: `mes` (`AAAA-MM`) | `sku` | `producto` | `sugerido` | `unidades` |
   `precio_unitario` | `notas`.
   - `armarPlan` y `recalcularPlan` agregan las filas que falten: una por cada SKU activo de `Productos` × cada mes del
     horizonte. No duplican filas ni borran filas que el cliente agregó.
   - `sugerido` y `producto` los escribe el script (se pueden pisar en cada corrida). `unidades`, `precio_unitario` y
     `notas` son del cliente y **no se tocan nunca**.
   - `sugerido` = unidades vendidas en los últimos 90 días ÷ 3, redondeado.
   - Para las cuentas: unidades = `unidades` si está cargado, si no `sugerido`. Precio = `precio_unitario` si está
     cargado, si no el promedio de `ingresos_productos ÷ unidades` de los últimos 90 días de ese SKU.

3. **Stock proyectado** (pantalla). Una fila por SKU activo; columnas: stock a hoy, y por cada mes del horizonte las
   unidades al final del mes = stock anterior + llegadas estimadas del mes − unidades proyectadas.
   - Llegadas estimadas: unidades de `Contenedor_productos` de contenedores sin `llegada_real` (incluye `planeado`),
     en el mes de su `llegada_estimada`. Sin `llegada_estimada`: no suma y va a Controles.
   - Al lado: **mes en que se queda sin stock** (primer mes < 0) y **"pedir antes de"** = la fecha en que se queda sin
     stock − plazo de reposición. En rojo si esa fecha ya pasó o cae dentro del primer mes.
   - El stock negativo no recorta las ventas proyectadas (se avisa, no se corrige).

4. **Contenedores** (pantalla). Los contenedores de Datos que no están `nacionalizado`: contenedor, proveedor, estado,
   llegada estimada, FOB USD, pagado USD, previsto USD (con la fecha del próximo pago previsto), **sin programar USD**
   = FOB − pagado − previsto, contando solo `anticipo` y `saldo` contra el FOB. Pagos en pesos → a USD con su `dolar`
   (si no tiene, al dólar del plan). Si "sin programar" > 0, en amarillo: esa plata no está en la caja.

5. **Caja semanal** (pantalla). Una fila por semana (lunes a domingo) desde la semana del inicio hasta el fin del
   horizonte. Columnas, todas en pesos:
   - `caja al inicio`: la primera semana, último `galicia_saldo.saldo` + último `mp_saldo.disponible` hasta el inicio.
     Las siguientes, la caja al final de la anterior.
   - `cobros de Mercado Pago a liberar`: suma de `mp_movimientos.monto_neto` con `fecha_liberacion` en la semana y
     posterior a la fecha del último `mp_saldo` usado (lo que ya se vendió y todavía no se cobró).
   - `cobros de ventas proyectadas`: unidades × precio × `% que se cobra`, repartidas parejo en los días del mes, y
     corridas `días hasta cobrar`. Solo ventas desde el inicio (las de antes ya están en Mercado Pago).
   - `pagos de contenedores`: `Contenedor_pagos` con estado `previsto`, `pagado_por` = `empresa` (o vacío), fecha en
     la semana, a pesos al dólar del plan si es USD. Un previsto con fecha anterior al inicio cae en la primera semana
     y va a Controles ("pago previsto vencido").
   - `gastos fijos`: los vigentes en el mes (`desde` ≤ mes ≤ `hasta`), en la semana que contiene el día de pago. USD al
     dólar del plan.
   - `deudas`: `Deudas` no pagadas, por `vencimiento` (si no tiene, la primera semana). USD al dólar del plan.
   - `publicidad ML`: ventas proyectadas del mes por `Mercado Libre` × % de publicidad, en el día de pago del mes
     siguiente. Para la parte de canal: el reparto ML/Tiendanube de cada SKU en los últimos 90 días (sin ventas: todo ML).
   - `Flex`: igual, con el % de Flex.
   - `caja al final` = inicio + cobros − pagos.
   - `aporte necesario`: si la caja al final queda debajo de la caja mínima, lo que falta para llegar al mínimo. Ese
     aporte se suma a la caja al final (la semana siguiente arranca con el mínimo).
   - Una columna por socio con su parte del aporte, y una fila final de totales.
   - Arriba: caja más baja del horizonte y su semana, y total de aportes por socio.

6. **Real vs proyectado** (pantalla). Para los meses del horizonte que ya empezaron: mes | sku | unidades proyectadas |
   unidades reales | diferencia | $ proyectado | $ real (`ingresos_productos`). Ordenado por mes y por la diferencia en $.
   Para que haya con qué comparar, la proyección de un mes no se borra cuando el mes pasa (ver punto 2).

7. **Controles** (pantalla). Una fila por aviso: qué pasa y dónde. Al menos: columna faltante en Datos; caja mínima sin
   cargar; reparto que no da 100 %; contenedor sin `llegada_estimada`; contenedor con "sin programar" > 0; pago previsto
   vencido; SKU de Ventas proyectadas que no está en Productos; SKU con stock negativo hoy; ventas con `sku_conocido` = `no`
   en los últimos 90 días (cuántas, no cuentan en el sugerido).

8. **Leeme** (pantalla): qué carga el cliente (Config y Ventas proyectadas), qué sale de Datos, y que se recalcula solo
   cada hora. Sin nombres propios.

### Históricos ("últimos 3 meses cerrados" = los 3 meses calendario anteriores al mes del inicio)
- `% que se cobra` = Σ `total_neto` ÷ Σ `ingresos_productos` de las ventas que cuentan.
- `% de publicidad` = Σ `ml_publicidad.costo` ÷ Σ `ingresos_productos` de ventas de `Mercado Libre`.
- `% de Flex` = Σ `Logistica_flex.importe` de esos meses ÷ Σ `ingresos_productos` de ventas de `Mercado Libre` de los
  meses que tienen factura de Flex. Sin facturas: 0 % y aviso.

### Estilo
- Comentarios en criollo: qué hace cada parte y por qué. Thomas no programa.
- Cabecera de cada archivo con: qué hace, cómo se instala (crear proyecto independiente, pegar los dos `.gs`, poner los
  dos ids, correr `armarPlan`, `recalcularPlan`, `instalarDisparador`) y qué hacer si se copia a otra cuenta.
- Sin dependencias externas.

## Comprobaciones
Con Node (en la Mac de Thomas no hay `node` en el PATH; usar
`/Applications/ChatGPT.app/Contents/Resources/cua_node/bin/node`):
```
/Applications/ChatGPT.app/Contents/Resources/cua_node/bin/node planillas/plan/probar_plan.cjs
```
La prueba arma un juego chico e inventado (3 SKU, 2 socios, 2 contenedores: uno `en camino` con un pago `pagado` y uno
`previsto`, otro `planeado` sin pagos) y verifica **con números calculados a mano en la propia prueba**:
1. Stock a hoy de un SKU con conteo, una llegada, ventas (una `cancelada` que no cuenta) y una merma.
2. Mes sin stock y "pedir antes de" de un SKU que se agota, y que una llegada estimada lo corre.
3. Contenedores: pagado, previsto y sin programar (un `flete` que no cuenta contra el FOB).
4. Caja semanal: una semana con pago de contenedor previsto, gasto fijo en USD y deuda; la caja baja del mínimo y el
   aporte se reparte 50/50 (y 70/30 si se carga así); la semana siguiente arranca en el mínimo.
5. `unidades` cargada por el cliente gana sobre `sugerido`; una fila que el cliente agregó no se duplica ni se borra.
6. Históricos: % que se cobra, % de publicidad y % de Flex.
7. Columna faltante → esa parte no se calcula y aparece en Controles (sin romper el resto).
8. Fechas en el borde de semana (domingo → lunes) y de mes, en hora de Buenos Aires.

No se puede probar acá: la escritura real en Google Sheets, el disparador ni los tiempos. Eso lo hace Claude al instalar.
Anotar en "Qué hice" qué partes de `plan_planilla.gs` quedaron sin prueba.

## Qué hice
Lo escribió Claude: Codex estaba sin cupo y su modelo saturado (decisión de Thomas, 11/11).
- `planillas/plan/plan_calculo.gs`: todas las cuentas en `calcularPlan(entrada)`, sin Google. Revisa las columnas por nombre;
  si falta una solapa o columna, la parte que la usa (proyección, stock, contenedores, caja, real) queda en null y se avisa.
  Stock: cierre del día anterior al inicio y después día por día (llegadas estimadas − ventas proyectadas repartidas parejo).
  En la caja, la publicidad y la Flex se calculan sobre el mes entero proyectado y se pagan el mes siguiente. Las de meses
  anteriores al inicio se suponen cargadas en Deudas.
- `planillas/plan/plan_planilla.gs`: `armarPlan`, `recalcularPlan` (con lock; calcula todo antes de escribir),
  `instalarDisparador` y `quitarDisparador`. En Ventas proyectadas solo escribe `producto` y `sugerido` (de las filas del mes
  del inicio en adelante) y agrega abajo las filas que faltan. En Config solo escribe las columnas C y D.
- `planillas/plan/probar_plan.cjs`: 85 comprobaciones con datos inventados, los 8 puntos de la consigna. `TODO BIEN`.
- `planillas/plan/LEEME.md`.
- Sin probar (necesita Google): todo `plan_planilla.gs` salvo que compile, es decir escritura, formatos, colores,
  protección, disparador y tiempos. Se prueba al instalar.

## Revisión
