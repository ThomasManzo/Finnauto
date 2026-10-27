# Tarea 69 — Canchada: tramos de pago, blend con canchada comprada, escenarios guardados y la operación sin bancos
Estado: consigna, lanzada a Codex (27/10/2026)
Rama: tarea/69-escenarios-canchada

## Objetivo
Cuatro pedidos de la dirección después de la reunión del 26/10, sobre la solapa "Cash compra canchada" y el
panel "Compra de canchada" del tablero:
1. Que **distintas toneladas se paguen a distintos plazos** (por ejemplo, una parte al contado y el resto a
   0/30/60/90).
2. Que la **canchada propia en stock no se pueda moler sola**: necesita un **blend** con canchada comprada,
   así que aunque haya stock propio, todos los meses hay que comprar una parte.
3. **Guardar varios escenarios con nombre**, abrirlos, borrarlos y **compararlos**.
4. Ver **la operación sola, mes a mes, sin bancos ni deuda** (y poder cambiar a la vista con deuda).

## Contexto
- Leer `AGENTS.md`, `CLAUDE.md`, `tareas/LEEME.md` y las tareas 62 a 68 (consignas, "Qué hice" y
  "Revisión").
- **Las cuentas las hace la planilla, no el panel** (regla de la 63). Todo número nuevo es una fila con
  fórmula en `armarCompraCanchada` (`crear_cash.gs`); el panel solo lee filas por su texto.
- **No tocar** el respaldo `_ccRespaldo_` ni la limpieza de validaciones (24/10). Las validaciones usan el
  separador de la planilla (`_separadorDeEstaPlanilla_`): la planilla está en español y una fórmula con ","
  rompe el rearmado y borra los valores cargados.
- Lo cargado a mano (amarillo) se conserva al rearmar. Si cambia el texto de un supuesto, migrar el valor
  viejo (ver cómo se hizo en la 65 y la 66).
- **El repo es público: nada de datos reales.** En pruebas y ejemplos, números inventados.

## Archivos permitidos
- `clientes/navar/herramientas/crear_cash.gs` (solo el bloque de canchada).
- `clientes/navar/herramientas/tablero_web.gs` (solo las funciones de canchada y `PANEL_CC_SUPUESTOS`).
- `dashboard/app.py` (solo `JS_CANCHADA` y su CSS).
- Pruebas de canchada en `lector/pruebas/` (las tres que existen y nuevas si hace falta) y esta consigna.

## Resultado esperado

### 1 · Tramos de pago de la canchada (reemplaza "en cuántas partes se paga")
- **Tabla de plazos** en la solapa: un bloque chico, editable (amarillo). Cada renglón tiene el nombre de un
  plazo y qué % se paga en el mes de la compra y en los 4 meses siguientes (mes 0 a mes 4; 30 días = mes
  siguiente). Al lado, un control que avise si no suma 100 %. Plazos iniciales:
  - contado: 100 / 0 / 0 / 0 / 0;
  - 30 días: 0 / 100 / 0 / 0 / 0;
  - 60 días: 0 / 0 / 100 / 0 / 0;
  - 90 días: 0 / 0 / 0 / 100 / 0;
  - 0/30/90: 33,33 / 33,33 / 0 / 33,34 / 0;
  - 0/30/60/90: 25 / 25 / 25 / 25 / 0;
  - 30/60/90/120: 0 / 25 / 25 / 25 / 25.
  Se pueden agregar renglones (hasta 10) y quedan en el desplegable.
- **Supuestos nuevos** (iguales todos los meses):
  - "Tramo 1: TN por mes" y "Tramo 1: plazo" (desplegable con los nombres de la tabla);
  - "Tramo 2: TN por mes" y "Tramo 2: plazo";
  - "El resto de la compra: plazo".
- Reparto de cada mes: la compra del mes (a mano o automática) llena primero el tramo 1 hasta sus TN,
  después el tramo 2, y lo que sobra va al plazo del resto. Si la compra del mes es menor que el tramo 1,
  todo va al tramo 1.
- "Compra de canchada (lo que se paga en el mes)" = suma de lo que vence ese mes de las compras de ese
  mes y de los 4 anteriores, según el plazo de cada tramo. Mostrar las TN de cada tramo por mes en filas
  agrupadas (con +), para que se vea el reparto.
- **Migración**: si la solapa tenía "en cuántas partes se paga" = N, el resto queda con el plazo
  equivalente (4 → "0/30/60/90", 1 → "contado"), y los tramos 1 y 2 en 0 TN. El resultado tiene que dar
  igual que antes.
- El flete sigue pagándose el mes de la compra.

### 2 · Blend: la canchada propia no se muele sola
- **Supuestos**:
  - el que hoy es "Stock de canchada lista para moler hoy (TN)" pasa a ser **"Stock de canchada propia hoy
    (TN)"** (migrar el valor);
  - nuevo: **"Máximo de canchada propia en la mezcla (%)"**, inicial **60 %**, editable (0 a 100).
- **Cada mes**:
  - propia usada = lo menor entre el stock propio al empezar el mes y el máximo % × TN vendidas;
  - comprada usada = TN vendidas − propia usada;
  - el stock propio baja con lo usado (no se repone: no hay secadero);
  - el stock comprado = el del mes anterior + lo que llega listo − la comprada usada.
- **Cobertura**: cuenta el stock total (propio + comprado). La dirección aclaró que el stock no tiene que
  estar listo para envasar para contar.
- **Compras automáticas**: compran lo que haga falta para las dos condiciones:
  - llegar a la cobertura con el stock total;
  - que nunca falte canchada comprada para la mezcla.
  Tienen en cuenta "Meses hasta que la canchada comprada está lista". Sin referencias circulares: seguir
  la técnica de la 66 (calcular lo de antes sin mirar el futuro).
- **Filas nuevas** en el bloque de toneladas:
  - propia usada;
  - comprada usada;
  - stock propio a fin de mes;
  - stock comprado a fin de mes;
  - stock total a fin de mes;
  - "Falta canchada comprada para la mezcla (TN)", en rojo si es > 0. Puede pasar con compras a mano, o
    los primeros meses si la canchada tarda en estar lista.
  "Meses que cubre" pasa a usar el stock total.
- Ejemplo a mano (inventado) para "Qué hice": stock propio 500, máximo 60 %, ventas 200 por mes, lista en
  0 meses.
  - Mes 1: propia 120, comprada 80.
  - El stock propio dura hasta que quedan menos de 120; ese mes se usa lo que queda y el resto es comprada.

### 3 · Escenarios guardados y comparación
- **En el servidor** (`tablero_web.gs`), cada escenario guarda:
  - el nombre;
  - la fecha;
  - los supuestos y las filas a mano (como hoy la foto del plan original);
  - una **foto de los resultados** en ese momento: por mes, el resultado de la operación, el acumulado de la
    operación, el saldo del mes con deuda y el saldo acumulado; además, los valores de las tarjetas.
  - Se guarda en propiedades del script, una clave por escenario. Tope de 20 escenarios, con un mensaje
    claro al llegar.
  - Funciones: guardar con nombre (si ya existe el nombre, preguntar antes de pisar), listar, abrir (escribe
    los supuestos en la solapa y devuelve el escenario recalculado) y borrar.
  - El "plan original" actual se migra a un escenario llamado "Plan original". Los botones "Volver al plan
    original" y "Guardar como plan original" se reemplazan por los nuevos.
  - Mismo lock y mismos permisos que hoy.
- **En el panel**:
  - Arriba, un selector **"Escenario"**: abre uno guardado. Al lado, los botones **"Guardar como…"**
    (pide el nombre) y **"Borrar"** (con confirmación).
  - **"Comparar con…"** (desplegable con los guardados). Al elegir uno:
    - el gráfico suma la línea del escenario comparado, punteada, sobre la misma vista (operación o con
      deuda);
    - la tabla de "El detalle" suma una fila "Diferencia contra «nombre»" del resultado del mes;
    - las tarjetas muestran debajo "vs «nombre»: +X M".
  - **Tabla "Escenarios guardados"**, debajo del gráfico, una fila por escenario: nombre, guardado el,
    resultado de un mes típico (operación), acumulado de la operación al último mes, peor saldo acumulado
    con deuda, plata que hay que conseguir, precio de equilibrio y TN de equilibrio. Ordenada por el
    acumulado de la operación.
  - Aclarar en chico: "Los números de cada escenario son los del día en que se guardó. Para actualizarlos,
    abrirlo y volver a guardarlo."

### 4 · La operación sola, mes a mes (sin bancos ni deuda)
- **Fila nueva en la solapa**: "Resultado de la operación acumulado (sin deuda)" = suma del resultado de la
  operación desde el primer mes. Arranca en 0: no usa el saldo de partida ni el descubierto, que son de
  los bancos.
- **En el panel**: un selector arriba del gráfico, **"Solo la operación" / "Con bancos y deuda"**. Arranca
  en "Solo la operación".
  - **Solo la operación**:
    - barras: el resultado de la operación de cada mes;
    - línea: el acumulado de la operación;
    - sin la línea del descubierto;
    - leyenda acorde;
    - tarjetas: resultado de un mes típico, peor mes (monto y mes), acumulado de la operación al último mes y
      meses en pérdida, además de las de equilibrio, compra y cobertura que ya están;
    - la tabla de "El detalle" sin las filas de bancos y deuda, con el resultado del mes y el acumulado de
      la operación.
  - **Con bancos y deuda**: como hoy.
  - Recordar la vista elegida en el navegador (localStorage, con try/catch).

## Comprobaciones
1. Ejemplos a mano en "Qué hice", con números inventados:
   - **tramos**: 300 TN por mes, tramo 1 = 100 TN contado, resto a 0/30/60/90, precio 1.000. Mes 1 paga
     100 M + 50 M; mes 2, 100 + 50 + 50; desde el mes 4, 100 + 200 = 300 M por mes;
   - **blend**: el de arriba;
   - **acumulado de la operación** de 3 meses.
2. **Prueba de la solapa**: la migración de "partes" da el mismo resultado que antes; los tramos reparten
   bien; un plazo que no suma 100 % muestra el aviso; el blend nunca usa más propia que el tope; las
   compras automáticas nunca dejan negativo el stock comprado cuando la canchada está lista en 0 meses;
   sin referencias circulares.
3. **Prueba del panel** con `google.script.run` de mentira: guardar, listar, abrir, borrar, pisar con
   confirmación, comparar (línea punteada, fila de diferencia y "vs"), tope de 20 y el cambio de vista
   operación ↔ con deuda.
4. Todas las pruebas que ya existen siguen pasando. Sin `<script src=` nuevos ni librerías.

## Qué hice
(Codex)

## Revisión
(Claude)
