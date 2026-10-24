# Tarea 66 — Escenario de canchada: compras automáticas para tener siempre N meses de stock listo
Estado: lista para revisión
Rama: tarea/66-stock-cobertura

## Objetivo
Hoy las toneladas compradas se cargan a mano mes por mes. La empresa trabaja con una regla:
**tener siempre stock de canchada lista para moler que cubra N meses de ventas** (hoy, 4). Con esa
regla, las compras salen solas: cada mes se compra lo que falta para llegar al objetivo.
Se mantiene la opción de cargar las compras a mano, para comparar con un plan fijo.

## Contexto
- Leer `AGENTS.md`, `CLAUDE.md`, `tareas/LEEME.md` y las tareas 62 a 65, consignas y "Qué hice".
- Hoy la solapa "Cash compra canchada" tiene:
  - la fila "TN compradas" (editable por mes);
  - la fila "TN vendidas" (editable por mes);
  - el supuesto "Stock de canchada propia al empezar (TN)";
  - abajo, un renglón de stock = inicial + compradas − vendidas.
  La compra de canchada (pagos en partes) y el flete usan "TN compradas".
- La canchada comprada puede venir **estacionada** (lista ya) o **verde** (lista recién después de
  unos meses).
- **El repo es público: nada de datos reales.** Los valores se cargan en la planilla.

## Archivos permitidos
Los mismos que la tarea 65: el bloque de `armarCompraCanchada` en `crear_cash.gs`, `tablero_web.gs`
(supuestos y validación), `JS_CANCHADA` en `dashboard/app.py`, las pruebas del panel y de la solapa, y
esta consigna.

## Resultado esperado

### 1 · Supuestos (solapa, amarillo, vacíos en el código, se conservan al rearmar)
- **Stock de canchada lista para moler hoy (TN)**. Reemplaza al texto "Stock de canchada propia al
  empezar (TN)". Mantener la clave `stock`, para que el valor cargado se conserve. Si hace falta,
  aceptar el texto viejo al leer lo guardado.
- **Meses de cobertura** (entero, de 1 a 12): cuántos meses de ventas tiene que cubrir el stock listo.
- **Meses hasta que la canchada comprada está lista** (entero, de 0 a 8): 0 = se compra estacionada.
- **Compras**: "automáticas" o "a mano" (validación de lista en la planilla).

### 2 · Cuentas (fórmulas en la solapa)
- Con mes m (0 = primer mes), L = meses hasta estar lista y N = meses de cobertura:
  - **llegan(m)** = compradas(m − L). Si m − L < 0, 0: no se suponen compras anteriores pendientes.
  - **stock listo a fin de mes(m)** = stock listo(m − 1) + llegan(m) − vendidas(m). Para m = 0 se parte
    del supuesto "stock hoy".
  - **objetivo(m)** = vendidas(m+1) + … + vendidas(m+N). Más allá del último mes, repetir las ventas del
    último mes.
  - **compra automática(m)** = máx(0, objetivo(m+L) + vendidas(m+L) − stock listo(m+L−1) sin esta
    compra). O sea: lo que hace falta comprar hoy para que, cuando esté lista, el stock llegue al objetivo.
  - **No hay referencia circular**: el stock hasta m+L−1 depende solo de compras anteriores a m.
  - Si m + L pasa del último mes, usar las ventas del último mes.
- **TN compradas** (la fila que usan pagos y flete) = la manual si "a mano", la automática si "automáticas".
  - Dejar dos filas a la vista: "TN compradas (a mano)", editable, y "TN compradas (lo que se usa)",
    calculada.
  - **Ojo con lo guardado**: la fila editable vieja se llamaba "TN compradas". Hay que conservar sus
    valores en la fila "a mano" al rearmar.
- **Renglones nuevos abajo**:
  - "Stock listo a fin de mes (TN)";
  - "Meses que cubre" = stock listo ÷ promedio de las ventas de los N meses siguientes;
  - "Falta canchada para moler (TN)" = máx(0, −stock listo). Si hay faltante, la planilla lo marca en rojo.
- **Primer mes**: si el stock de hoy no llega al objetivo, la compra automática del primer mes cubre
  la diferencia, más lo que se vende en el mes (con L = 0).
- "Faltan cargar" incluye los supuestos nuevos.

### 3 · Panel
- Controles nuevos, con barra y número como los otros:
  - **stock hoy (TN)**, de 0 a 3000;
  - **meses de cobertura**, de 1 a 12;
  - **meses hasta estar lista**, de 0 a 8.
- **Compras**: dos botones, "automáticas" y "a mano".
  - En "automáticas", el control "TN compradas por mes" se muestra deshabilitado, con la fila
    calculada de la planilla mes a mes ("cambiar mes por mes" muestra los valores, sin editar).
  - En "a mano", funciona como hoy.
- **Tarjeta nueva** (una quinta, o reemplazar la que menos sirva, y explicarlo): **"Compra del primer
  mes"**, en TN y en $. Abajo, el mínimo de "meses que cubre" y en qué mes, en rojo si queda por debajo
  de la cobertura pedida.
- En "El detalle", una sección "Canchada (TN)" con: vendidas, compradas, llegan, stock listo y meses
  que cubre.

## Comprobaciones
1. Ejemplo a mano en "Qué hice", con números inventados: stock hoy 500, ventas 100 por mes, N = 4.
   - Con L = 0, la compra del mes 0 da 400 − 500 + 100 = 0 y la del mes 1 da 100.
   - Mostrar también un caso con L = 2.
2. Prueba de la solapa: las fórmulas nuevas existen, apuntan a las filas correctas y no hay
   referencias circulares, controlando el texto de las fórmulas.
3. Pruebas del servidor y del panel con las claves nuevas.
4. Todas las pruebas que ya existen siguen pasando.

## Qué hice
- Trabajé sobre main con la 65 ya mergeada y su corrección del secadero por inflación intacta.
  Agregué stock listo hoy (con la misma clave `stock`), cobertura, meses hasta estar lista y modo
  de compras. Los supuestos nuevos nacen vacíos; cobertura y plazo aceptan solo enteros en sus
  rangos, y compras tiene la lista «automáticas» / «a mano».
- Separé las filas «TN compradas (a mano)», «TN compradas (automáticas)» y «TN compradas (lo que
  se usa)». Pagos en partes y flete siguen usando esta última. Al rearmar, el stock y las compras
  cargados con los textos viejos se recuperan en los renglones nuevos. Las fotos del plan original
  siguen guardando la clave `tnCompradas`, ahora correspondiente exclusivamente a la fila manual.
- La compra automática proyecta el stock antes de que llegue esa compra: stock inicial + todas
  las compras anteriores − ventas hasta ese momento. Con un plazo fijo, esas compras anteriores
  ya llegaron entonces. La fórmula no usa stock futuro ni compras actuales o posteriores, así
  evita ciclos. Suma las próximas N ventas para el objetivo y repite las últimas ventas cuando
  sale de los catorce meses, tanto para el objetivo como para el consumo hasta la llegada.
- Agregué llegadas, stock listo, objetivo, meses que cubre y faltante. El faltante positivo tiene
  formato rojo. Si no hay ventas previstas, la cobertura queda vacía en la planilla y el panel
  muestra «sin ventas», para no dividir por cero. Una fila adicional trae el valor de la compra
  del mes (sin flete), calculado en la planilla, para que la tarjeta no calcule plata en JavaScript.
- El panel agrega los tres controles de stock, cobertura y plazo, y los botones de modo. En
  automático la barra, el número y los catorce casilleros de compras quedan deshabilitados y
  muestran la fila calculada. En manual recuperan la fila editable. Se mantiene el guardado por
  `ccCambio`, el agrupado de 0,8 segundos y la recuperación ante errores.
- Elegí **agregar una quinta tarjeta** para conservar los cuatro indicadores de caja. Muestra TN
  y valor de la primera compra; debajo, la menor cobertura con su mes, en rojo si es inferior a
  la pedida. Aclaré que ese importe es el valor completo sin flete, mientras el pago de caja sigue
  el esquema de partes. El detalle tiene otra tabla «Canchada (TN)» con las cinco filas pedidas.
- Archivos tocados: `clientes/navar/herramientas/crear_cash.gs` (solo bloque de canchada),
  `clientes/navar/herramientas/tablero_web.gs` (supuestos, validación y las dos referencias a la
  fila manual para guardar y fotografiar), `dashboard/app.py` (JS y CSS del panel),
  `lector/pruebas/probar_panel_canchada.cjs`, `lector/pruebas/probar_canchada_envases.cjs`,
  `lector/pruebas/test_panel_canchada.py` y esta consigna. Las dos referencias del servidor son
  necesarias por el cambio de nombre de la fila; no cambié la mecánica de permisos ni guardado.
- Comprobaciones: **301 pruebas de Python y 52 subpruebas pasaron**, más los **13 archivos `.cjs`**.
  La prueba de la hoja controla referencias, conservación y migración, validaciones, faltantes y
  formato rojo. Un evaluador mínimo ejecuta las fórmulas de stock emitidas, detecta recursión y
  compara los catorce meses con una simulación aparte: plazos 0/2/8, cobertura 1/4/12, ventas
  variables, ventas cero, stock insuficiente y compras manuales. El servidor prueba límites,
  enteros, opciones de modo y que guardar compras manuales no pisa la fila calculada.
- En Chromium con `google.script.run` simulado comprobé los dos modos, bloqueo de los catorce
  meses en automático, recuperación de la fila manual, edición mensual, guardado conjunto de
  stock/cobertura/plazo y rechazo de cobertura fraccionaria. Revisé la quinta tarjeta, el aviso
  rojo, el contraste del botón seleccionado y la tabla de TN en escritorio y celular. Capturas:
  `/private/tmp/66-panel-desktop.png` y `/private/tmp/66-panel-mobile.png`.
  Tras el ajuste visual, volvieron a pasar las seis pruebas de render del panel y las pruebas
  del navegador. `git diff --check` sin errores. No instalé dependencias nuevas.

### Ejemplo a mano — todos los valores son inventados

Stock listo inicial **500 TN**, ventas **100 TN por mes**, cobertura **4 meses**. El objetivo
  de fin de mes es siempre **400 TN**.

| Plazo | Mes (desde 0) | Compra de ese mes (TN) | Llegan listas (TN) | Stock listo al cierre (TN) | Meses que cubre |
| --- | ---: | ---: | ---: | ---: | ---: |
| L = 0 | 0 | 0 | 0 | 400 | 4 |
| L = 0 | 1 | 100 | 100 | 400 | 4 |
| L = 0 | 2 | 100 | 100 | 400 | 4 |
| L = 2 | 0 | 200 | 0 | 400 | 4 |
| L = 2 | 1 | 100 | 0 | 300 | 3 |
| L = 2 | 2 | 100 | 200 | 400 | 4 |
| L = 2 | 3 | 100 | 100 | 400 | 4 |

Con L = 0: compra(0) = máximo(0, 400 + 100 − 500) = **0**;
  compra(1) = máximo(0, 400 + 100 − 400) = **100**.

Con L = 2: antes de llegar la compra del mes 0 se vendieron 200 TN, por lo que el stock
  proyectado antes del mes 2 es 500 − 200 = 300. Se compra máximo(0, 400 + 100 − 300) = **200**.
  Para la compra del mes 1, antes del mes 3 ya llegó ese pedido: 500 + 200 − 300 = 400;
  compra(1) = máximo(0, 400 + 100 − 400) = **100**. El mes 1 cubre solo tres meses: no se inventan
  pedidos pendientes anteriores que eviten esa baja transitoria.

### Para la revisión en vivo

- Instalar el bloque de canchada, rearmar la solapa (conserva stock y compras anteriores) y cargar
  cobertura, plazo y modo en las celdas nuevas. Instalar el servidor actualizado y generar el
  tablero nuevo antes de probar el panel: cambiaron los textos de las filas del contrato.
- Comparar contra una cuenta aparte las compras, llegadas, stock, cobertura y caja (pagos en
  partes y flete) en ambos modos, especialmente los primeros meses con plazo y el extremo final.
  Verificar la lista de compras, validaciones de enteros, rojo del faltante, conservación al
  rearmar y botones del plan original. Una foto vieja no contiene cobertura/plazo/modo: esos
  campos conservan su valor actual al recuperarla; guardar el plan completo como original una
  vez cargados los supuestos nuevos.
- El evaluador local cubre las fórmulas de stock, pero no sustituye al motor de Sheets ni comprueba
  permisos de la aplicación web real. La instalación y comparación real quedan para Claude.
- Worktree `/private/tmp/finnauto-66`, rama `tarea/66-stock-cobertura`. Sin datos reales, archivos
  privados, Drive ni planilla del cliente. No cambié main ni publiqué nada.

## Revisión
(lo completa Claude)
