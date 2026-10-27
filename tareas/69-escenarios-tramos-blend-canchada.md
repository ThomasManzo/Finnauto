# Tarea 69 — Canchada: tramos de pago, blend con canchada comprada, escenarios guardados y la operación sin bancos
Estado: lista para revisión
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
- Trabajé en este worktree, rama `tarea/69-escenarios-canchada`. Toqué únicamente los bloques
  permitidos de `crear_cash.gs`, `tablero_web.gs`, `dashboard/app.py`, las tres pruebas de canchada
  existentes y esta consigna. Sin dependencias nuevas, Google, archivos privados ni datos reales.
- La solapa tiene los siete plazos iniciales y tres lugares libres, porcentajes editables, control
  del 100 % y desplegables que incorporan los nombres nuevos. Cada compra llena primero el tramo 1,
  después el 2 y el resto. Los pagos recorren el mes de compra y los cuatro siguientes; el flete
  sigue al contado. Las TN de los tramos quedan agrupadas y cerradas, para abrirlas con el +.
  La tabla de plazos también se conserva al rearmar y se guarda dentro de cada escenario.
- Migré el stock de los dos textos anteriores y los planes de una a cinco cuotas, incluidos los
  plazos de dos, tres y cinco cuotas que no están entre los siete iniciales. Los tramos arrancan
  en cero y el resto usa el plazo anterior. No modifiqué `_ccRespaldo_` ni la limpieza de validaciones.
  Las validaciones nuevas respetan el separador español y admiten blend de 0 a 100 %.
- Separé propia usada, comprada usada y sus stocks. La cobertura incluye lo comprado que todavía
  está estacionándose; el stock comprado listo y el faltante de mezcla se muestran aparte.
  La compra automática toma el mayor de dos faltantes: cobertura total al cierre del mes y
  comprada necesaria cuando ese pedido esté listo. Usa solo ventas y pedidos anteriores, sin ciclos.
- Agregué el acumulado operativo desde cero. El panel abre en «Solo la operación», muestra sus
  cuatro indicadores, barras y acumulado; permite pasar a bancos y deuda y recuerda la elección.
  Conservé las tarjetas de compra/cobertura y equilibrio. Los costos, pagos, stock y resultados
  siguen calculándose en la planilla; el panel resume y presenta esas filas.
- Agregué guardar con nombre, listar, abrir, borrar y comparar. El servidor mantiene permisos y
  candado, pide confirmación para reemplazar y admite hasta 20 fotos. Cada foto guarda supuestos,
  filas manuales, plazos, fecha, resultados mensuales y valores de tarjetas. Al abrir recalcula;
  editar el plan abierto no cambia las fotos guardadas. Cada foto usa una propiedad y se controla
  su tamaño antes de escribirla.
- El original viejo se convierte en «Plan original»: se aplica su entrada, se toma la foto
  recalculada y se repone lo que estaba abierto, incluso si falla el guardado. Como antes no había
  foto de resultados, los resultados del original migrado son los del día de la migración.
  Los supuestos que no existían en esa foto se completan con los actuales.
- La comparación agrega línea punteada, diferencia mensual y referencia en las tarjetas.
  Empareja meses por fecha, no por posición; si no hay mes comparable lo dice. La tabla de
  escenarios se ordena por acumulado operativo y avisa que las fotos no se actualizan solas.

### Ejemplos a mano — todos inventados

- **Tramos:** compra de 300 TN a $1.000/kg; 100 TN contado y 200 TN en 0/30/60/90.
  Mes 1: $100 M + $50 M = **$150 M**. Mes 2: $100 M + $50 M + $50 M = **$200 M**.
  Mes 3: **$250 M**. Desde el mes 4: $100 M + cuatro cuotas de $50 M = **$300 M**.
  Si se compran solo 50 TN con tramo 1 de 100, las 50 van al tramo 1 y los otros quedan en cero.
- **Blend:** stock propio 500 TN, tope 60 %, ventas 200 TN mensuales, lista en cero meses.
  En los primeros cuatro meses se usan **120 propias + 80 compradas**; la propia cierra en
  380, 260, 140 y 20 TN. El quinto mes usa **20 propias + 180 compradas**; desde el sexto,
  **0 propias + 200 compradas**. Las compras automáticas no dejan negativo el stock comprado
  con plazo cero, aunque haya mucha propia almacenada.
- **Acumulado operativo:** resultados de +$12 M, −$5 M y +$9 M dan acumulados de
  **$12 M, $7 M y $16 M**. El saldo inicial del banco y su descubierto no entran en esa suma.

### Pruebas y revisión pendiente

- Suite completa con el Python, PYTHONPATH y opciones indicados: **305 pruebas y 52 subpruebas
  pasaron**. Fallaron las dos del bot (`test_recorrido_completo` y `test_errores_claros`), porque
  Chromium no puede arrancar en este sandbox: `bootstrap_check_in: Permission denied`.
  Los **13 archivos .cjs** pasaron con el Node indicado. Las pruebas específicas se repitieron
  después de los últimos ajustes y pasan. `git diff --check` sin errores.
- La prueba de solapa ejecuta las fórmulas emitidas y las compara con una simulación aparte:
  blend 0/60/100 %, plazos de maduración 0/2/8, cobertura 1/4/12, ventas variables y cero,
  compras manuales, reparto de tramos, migración 1–5, aviso del 100 %, conservación y ausencia
  de ciclos. También controla las referencias del acumulado y las reglas con separador español.
- El servidor se prueba con hoja y propiedades inventadas: permisos, rangos, filas movidas,
  recalculado, migración del original sin dejar cambios en el plan abierto, fotos que no cambian,
  reemplazo confirmado, límite de 20, borrado y restauración de la tabla de plazos.
  El JS real del panel corre con DOM y `google.script.run` simulados: guardar, listar, abrir,
  cancelar/confirmar reemplazo y borrado, comparación, línea punteada, diferencias, tarjetas,
  límite y cambio de vista con memoria local. No agregué librerías ni `<script src=`.
- **Caso que necesita decisión en la revisión:** el sistema anterior aceptaba seis cuotas, pero
  la tabla pedida solo permite mes 0 a mes 4 (cinco vencimientos). No se pueden conservar seis
  cuotas iguales dentro de esos cinco meses. Si encuentra seis, frena antes de borrar la solapa;
  una foto original con seis también queda intacta y avisa. Hace falta decidir si se amplía la
  tabla al mes 5 o se cambia ese plazo a mano. No comprimí ni adelanté pagos silenciosamente.
- Queda para la revisión en vivo instalar los bloques y regenerar el tablero; revisar escritorio
  y celular, validaciones y desplegables en Sheets, comparación de las fórmulas con una cuenta
  aparte y permisos de la aplicación web. La revisión visual y las dos pruebas que necesitan
  Chromium deben hacerse fuera de este sandbox. No instalé ni publiqué nada.


- Intenté preparar los archivos y commitear. El sandbox rechazó la creación de
  `/Users/thomasmanzo/Documents/Finnauto/.git/worktrees/finnauto-69/index.lock`
  con `Operation not permitted`. Los siete archivos quedaron **sin commit**, para la revisión.

## Revisión
- Claude revisó y aprobó: las 307 pruebas de Python y los 13 `.cjs` pasan fuera del sandbox. Mergeada
  (2585afe).
- Al instalarla aparecieron tres cosas que las pruebas no veían, porque la planilla está en español. Las
  corrigió Claude (d8fdf79) y sumó un control a la prueba:
  - el control de la tabla de plazos usaba un decimal con punto (`0.000001`) y daba `#ERROR!`. Ahora usa
    `ROUND(...;6)=1`;
  - `MAX(0,-X)` en "Falta canchada comprada" quedaba como `MAX(0-X)`: Sheets toma "0,-" como decimal y
    mostraba negativos. Ahora es `MAX(-X,0)`. **Regla: en fórmulas, nada de "número,-" ni decimales con
    punto**;
  - la tabla de plazos estaba arriba del renglón de meses, dentro de las filas fijas: en una pantalla chica
    la solapa no se podía desplazar. Pasó abajo de todo, después de las notas.
- Instalada: crear_cash (solo el bloque) y tablero_web (desde el ID de canchada; el ID se conserva). Solapa
  rearmada y aplicación web en versión 10.
  - Los valores cargados se conservaron: el stock pasó a "stock propio" y las 4 partes a "0/30/60/90".
  - Comparado con una cuenta aparte: precio, cuotas de la compra (95,6 / 191 / 287 / 382 M), blend 180 + 120
    TN, stock propio y comprado, resultado y acumulado de la operación. Todo coincide.
- Copia en Drive `Scripts/crear_cash.gs.txt` actualizada: es igual a la instalada.
