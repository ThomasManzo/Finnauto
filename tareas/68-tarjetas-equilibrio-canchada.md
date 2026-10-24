# Tarea 68 — Panel de canchada: tarjetas de "precio de equilibrio" y "TN de equilibrio"
Estado: pendiente
Rama: tarea/68-equilibrio

## Objetivo
Que el panel "Compra de canchada" muestre, de un vistazo, cuánto falta para que **la operación se
pague sola** (sin contar la deuda):
- **Precio de equilibrio**: a qué precio por kg habría que vender para que el resultado de la
  operación dé cero, con las TN que se venden.
- **TN de equilibrio**: cuántas TN por mes habría que vender, al precio actual, para que dé cero.

## Contexto
- Leer `AGENTS.md`, `CLAUDE.md`, `tareas/LEEME.md` y las tareas 62 a 66, consignas y "Qué hice".
- **Las cuentas las hace la planilla, no el panel** (regla de la 63). Las filas nuevas van en la solapa
  (`armarCompraCanchada` en `crear_cash.gs`) y el panel solo las lee por su texto.
- Hoy cada kilo vendido tiene un costo variable: canchada (precio de compra) + flete + costo de envase
  por kg (ya está calculado en la solapa) + comisión por kg. Los **gastos operativos sin secadero**
  son fijos por mes: no dependen de las TN.
- **El repo es público: nada de datos reales.** Ejemplos inventados.
- El 24/10 se agregó una copia de seguridad de lo cargado antes de borrar la solapa (`_ccRespaldo_`)
  y la limpieza de validaciones viejas. **No tocar ese mecanismo.**

## Archivos permitidos
- `clientes/navar/herramientas/crear_cash.gs` (solo el bloque de canchada).
- `dashboard/app.py` (solo `JS_CANCHADA` y su CSS).
- Pruebas del panel y de la solapa (`lector/pruebas/probar_canchada_envases.cjs`,
  `lector/pruebas/test_panel_canchada.py`) y esta consigna.

## Resultado esperado

### 1 · Filas nuevas en la solapa (fórmulas, una por mes)
- **"Costo variable por kg (canchada + flete + envase + comisión)"** = precio de canchada + flete +
  costo de envase por kg + comisión por kg.
- **"Margen por kg"** = precio de venta del mes − costo variable por kg.
- **"Precio de equilibrio de la operación ($/kg)"** = costo variable por kg + gastos operativos sin
  secadero del mes ÷ (TN vendidas del mes × 1000). Si las TN del mes son 0, vacío.
- **"TN de equilibrio por mes"** = gastos operativos sin secadero del mes ÷ margen por kg ÷ 1000. Si el
  margen es ≤ 0, el texto "no hay volumen que alcance".
- Ponerlas en un bloque chico **"Equilibrio de la operación (sin deuda)"**, después del resultado de la
  operación y antes de "Bancos y deuda". Explicar en la nota de abajo de la solapa que es una mirada
  **por kilo**: la canchada se toma a su precio, no según cuándo se paga.

### 2 · Panel
- **Dos tarjetas nuevas** en la fila de tarjetas, con el mismo estilo:
  - **"Precio de equilibrio"**:
    - en grande, el promedio de "Precio de equilibrio…" desde el mes en que la compra está a pleno
      (el mismo criterio que "Resultado de un mes típico");
    - abajo: "hoy $X/kg · falta +Y %", o "ya alcanza" si el precio actual lo supera;
    - roja si falta.
  - **"TN de equilibrio"**:
    - en grande, el promedio de "TN de equilibrio…" con el mismo criterio;
    - abajo: "hoy N TN/mes · faltan M TN";
    - roja si faltan;
    - si alguna dice "no hay volumen que alcance", mostrar eso.
- Si las tarjetas no entran en una fila en escritorio, que pasen a dos filas sin desbordar. El celular
  queda en una columna.
- En "El detalle", sumar las cuatro filas nuevas en una sección "Equilibrio (por kg)".

## Comprobaciones
1. Ejemplo a mano con números inventados, en "Qué hice": precio 2000, canchada 1200, flete 30, envase
   200, comisión 50, gastos fijos $100 M, 200 TN.
   - El costo variable da 1480 y el margen 520.
   - El precio de equilibrio da 1480 + 100 M / 200.000 = 1980.
   - Las TN de equilibrio dan 100 M / 520 / 1000 ≈ 192,3.
2. Prueba de la solapa: las fórmulas existen y apuntan a las filas correctas.
3. Prueba del render y del panel con `google.script.run` de mentira: las tarjetas muestran falta y ya
   alcanza.
4. Todas las pruebas que ya existen siguen pasando.

## Qué hice
(lo completa Codex)

## Revisión
(lo completa Claude)
