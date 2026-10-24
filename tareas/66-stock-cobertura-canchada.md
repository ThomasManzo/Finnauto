# Tarea 66 — Escenario de canchada: compras automáticas para tener siempre N meses de stock listo
Estado: pendiente (arrancar cuando la 65 esté mergeada: tocan los mismos archivos)
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
(lo completa Codex)

## Revisión
(lo completa Claude)
