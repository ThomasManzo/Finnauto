# Tarea 65 — Escenario de canchada: gastos de envase, comisiones y "Bancos y deuda"
Estado: pendiente
Rama: tarea/65-envases-y-bancos

## Objetivo
Completar el escenario "Cash compra canchada" (solapa de la planilla + panel del tablero) con lo que
pidió la administración del cliente:
1. **Gastos de envase**: un supuesto nuevo, con un desplegable con cada gasto, cada uno editable.
2. **Comisiones**: pasan a ser un costo por kilo vendido; ya no van dentro de la base fija.
3. **"Bancos y deuda"**: los intereses y gastos bancarios salen de los gastos operativos y se juntan
   con la deuda en un renglón propio.
4. El renglón de gastos se pasa a llamar **"Gastos operativos sin secadero"**.

Todo **sin contar dos veces**: lo que se pasa a un supuesto nuevo se resta de la base.

## Contexto
- Leer `AGENTS.md`, `CLAUDE.md`, `tareas/LEEME.md` y las tareas 62, 63 y 64, consignas y "Qué hice".
  La 62 armó la solapa (`armarCompraCanchada()` en `crear_cash.gs`, con `CC_SUPUESTOS`); la 63 y la
  64, el panel (`JS_CANCHADA` en `dashboard/app.py`) y el servidor (`tablero_web.gs`, con
  `PANEL_CC_SUPUESTOS`, que tiene que ser igual a `CC_SUPUESTOS`; la prueba lo controla).
- Hoy la base de gastos es el promedio de los 3 meses cerrados del total de egresos de la operación
  del Cash Mensual, × inflación, menos el secadero.
  - Esa base **ya incluye**:
    - las estampillas que se pagaron;
    - las comisiones, porque los vendedores facturan y se les paga como a un proveedor;
    - los intereses y gastos bancarios.
  - **No incluye envases**: en esos meses no se les pagó a los proveedores de envases (quedó como deuda).
- Los valores reales se cargan en la planilla, no en el código. **El repo es público: nada de datos
  reales**. En código y pruebas, celdas vacías y ejemplos inventados.

## Archivos permitidos
- `clientes/navar/herramientas/crear_cash.gs` (solo el bloque de la tarea 62: `CC_SUPUESTOS`,
  `armarCompraCanchada` y sus ayudantes).
- `clientes/navar/herramientas/tablero_web.gs` (`PANEL_CC_SUPUESTOS` y validación de las claves nuevas).
- `dashboard/app.py` (`JS_CANCHADA` y su CSS).
- Pruebas: `lector/pruebas/probar_panel_canchada.cjs`, `lector/pruebas/test_panel_canchada.py`, y una
  prueba nueva si hace falta para las fórmulas de la solapa.
- `tareas/65-envases-comisiones-bancos-en-canchada.md`.

## Resultado esperado

### 1 · Supuestos nuevos en la solapa (celdas amarillas, vacías en el código, se conservan al rearmar)
- **Gastos de envase**, en $ sin IVA. Cada uno con dos celdas: **por paquete de 1 kg** y **por paquete
  de ½ kg**:
  - estampillas;
  - paquetes;
  - pallets;
  - stretch;
  - termocontraíble.

  No van, porque ya están en otro lado: canchada, logística, movimiento de canchada, repuestos,
  personal, energía, combustible.
- **Mezcla de venta: % de kilos en paquetes de 1 kg**. El resto es ½ kg.
- **Pago de los envases**: "contado" o "30 días". En la planilla, una validación de lista con esas dos
  opciones.
- **Comisión de los vendedores ($ por kg vendido)**.
- **Ajustes de la base** (para no contar dos veces):
  - **Estampillas pagadas por mes en la base ($)**: se resta de la base;
  - **Kilos vendidos por mes en la base**: la base resta comisión × estos kilos.
- **Intereses y gastos bancarios de la base**: no se carga a mano. Se lee del Cash Mensual,
  promedio de los 3 meses cerrados del renglón "Intereses y gastos bancarios", buscado por texto como
  el resto. Va en gris, como los otros datos leídos.

### 2 · Cuentas (en la solapa, con fórmulas)
- **Costo de envase por kg** = mezcla × (suma de los 5 gastos de 1 kg) + (1 − mezcla) × (suma de los
  5 gastos de ½ kg) × 2. El ½ kg se pasa a kilo: dos paquetes hacen un kilo.
- **Gastos de envase del mes** = TN vendidas × 1000 × costo por kg. Con "contado" se paga en el mes;
  con "30 días", al mes siguiente. Para el primer mes con "30 días": lo del mes anterior se supone
  igual al primer mes, como hace la cobranza.
- **Comisiones del mes** = TN vendidas × 1000 × comisión por kg, pagadas en el mes.
- **Gastos operativos sin secadero** (renombrar el renglón de gastos) =
  (base − intereses y gastos bancarios de la base − estampillas de la base − comisión × kilos de la
  base) × inflación − secadero. Mostrarlo como un renglón, y abajo, agrupado, el detalle de cada resta,
  para que se vea de dónde sale.
- **Bancos y deuda** (renombrar el bloque de deuda, con su total):
  - intereses y gastos bancarios = promedio de la base × inflación;
  - deuda con débito automático;
  - deuda que se paga por decisión;
  - el renglón que dice de dónde sale cada mes.
- El **total de egresos de la operación** queda: gastos operativos sin secadero + gastos de envase +
  comisiones + canchada + flete. El resultado de la operación y los saldos siguen igual.
- "Faltan cargar" incluye los supuestos nuevos.

### 3 · Panel (`JS_CANCHADA`)
- Un control nuevo, **"Gastos de envase"**:
  - muestra el costo por kg resultante en grande;
  - un botón "ver detalle" abre un desplegable con los 5 gastos × 2 formatos, cada uno con casillero
    numérico;
  - también la mezcla (% 1 kg) y el pago (contado / 30 días, como dos botones).
  Al confirmar un valor entra por el mismo `ccCambio`.
- Un control nuevo, **"Comisión de los vendedores ($/kg)"**, con barra y número, como los otros.
- Los ajustes de la base (estampillas y kilos de la base) **no** van en la grilla de controles. Van en
  un "ver cómo se arma la base" chico, debajo de la tabla.
- La tabla "El detalle" queda con estas filas:
  - cobranza;
  - gastos operativos sin secadero;
  - gastos de envase;
  - comisiones;
  - canchada + flete;
  - bancos y deuda;
  - saldo del mes;
  - saldo acumulado.
- El servidor valida las claves nuevas:
  - montos ≥ 0;
  - mezcla entre 0 y 1 (en el panel se escribe 0 a 100);
  - pago "contado" o "30 días".

## Comprobaciones
1. Ejemplo hecho a mano en "Qué hice", con números inventados simples: 100 TN vendidas, mezcla 50%,
   gastos de 1 kg que suman 100 y de ½ kg que suman 60. El costo por kg da 0,5 × 100 + 0,5 × 120 = 110,
   y el mes da $11 M. Mostrar qué da cada renglón el primer y el segundo mes con contado y con 30 días.
2. Prueba de la solapa: se arma con una planilla de juguete y las fórmulas nuevas existen y apuntan a
   las filas correctas. Si no se puede evaluar fórmulas, controlar el texto de la fórmula.
3. Pruebas del panel y del servidor con las claves nuevas: guardar, validar y rechazar.
4. Todas las pruebas que ya existen siguen pasando.
5. Lo que no se puede probar sin la planilla real queda anotado para Claude.

## Qué hice
(lo completa Codex)

## Revisión
(lo completa Claude: instalar crear_cash con solo el bloque cambiado, tablero_web.gs sobre lo instalado,
nueva versión de la aplicación web, cargar los valores reales en la planilla, rearmar la solapa y el
tablero, y verificar contra una cuenta aparte)
