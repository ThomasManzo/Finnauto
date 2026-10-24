# Tarea 65 — Escenario de canchada: gastos de envase, comisiones y "Bancos y deuda"
Estado: aprobada e instalada (23/10/2026; falta actualizar la notebook para el panel)
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
- Agregué los diez importes de envase (cinco gastos × dos formatos), mezcla, pago, comisión por
  kilo y ajustes de la base. Todos nacen vacíos y se conservan al rearmar. El pago tiene una lista
  que acepta solamente «contado» y «30 días». El promedio bancario se lee por texto del Cash
  Mensual y queda gris; no se carga desde el panel.
- Las fórmulas calculan el costo por kilo con la mezcla y los dos paquetes de ½ kg por kilo.
  El pago a 30 días toma las TN del mes anterior; para el primero toma las del primero.
  Comisiones se calcula por los kilos vendidos y se paga en el mes.
- Separé «Gastos operativos sin secadero», con sus restas agrupadas debajo, y «Bancos y deuda».
  El total operativo suma solo gastos operativos, envases, comisiones, canchada y flete: no vuelve
  a sumar el detalle de las restas. Bancos se resta de la base y se suma una sola vez junto con
  la deuda. Apliqué el secadero como resta posterior a la inflación, tal como indica la fórmula
  nueva de esta consigna; antes también se inflaba esa resta.
- El panel tiene doce controles: agregué comisión con barra y número, y envases con costo por kilo
  leído de la planilla y «ver detalle» para editar los diez gastos, mezcla y pago. Los ajustes de la
  base están en «ver cómo se arma la base», debajo de la tabla, junto con los importes leídos y la
  explicación de las restas. La tabla tiene los ocho renglones pedidos. No agregué cuentas de
  envases ni de la base en el navegador: las hace la planilla.
- Todo entra por el mismo `ccCambio`, conservando la espera de 0,8 segundos y los cambios hechos
  durante un guardado. Los campos nuevos rechazan números vacíos, negativos o no finitos; mezcla
  acepta 0 a 100 y se manda como 0 a 1. El servidor valida las claves y las opciones de pago;
  las definiciones de supuestos siguen siendo idénticas en los dos scripts.
- Archivos tocados: `clientes/navar/herramientas/crear_cash.gs` (solo el bloque de canchada),
  `clientes/navar/herramientas/tablero_web.gs` (solo supuestos y validación), `dashboard/app.py`
  (solo JS y CSS del panel), `lector/pruebas/probar_panel_canchada.cjs`,
  `lector/pruebas/test_panel_canchada.py`, la prueba nueva
  `lector/pruebas/probar_canchada_envases.cjs` y esta consigna.
- Comprobaciones: **300 pruebas de Python y 52 subpruebas pasaron**, más los **13 archivos `.cjs`**.
  La hoja de juguete comprueba las fórmulas y sus referencias, los catorce meses, que la resta
  bancaria coincide con lo sumado en bancos, la lista de pago, los faltantes y la conservación al
  rearmar, incluyendo ceros. El servidor se prueba con todas las claves nuevas, valores inválidos,
  filas movidas y recuperación del original, incluyendo campos nuevos vacíos.
- En Chromium con `google.script.run` simulado comprobé: edición de envases, mezcla y pago en una
  sola tanda; rechazo de mezcla 101%; comisión con número; ajustes de la base; otra edición durante
  un guardado; y recuperación de los campos ante un error. Revisé escritorio y celular, sin
  desbordamiento de la página. Capturas locales: `/private/tmp/65-panel-desktop.png` y
  `/private/tmp/65-panel-mobile.png`. No se instalaron dependencias: usé los entornos disponibles.
  Las pruebas con navegador se ejecutaron fuera del sandbox. `git diff --check` sin errores.

### Ejemplo a mano — todos los valores son inventados

En ambos meses se venden **100 TN**. Mezcla 50%; cada uno de los cinco gastos vale 20 por paquete
  de 1 kg y 12 por paquete de ½ kg: suman 100 y 60. El costo por kilo es
  **0,5 × 100 + 0,5 × 60 × 2 = 110**. Envases del mes: **100 × 1000 × 110 = $11 M**.

Para completar los demás renglones: venta a $1000/kg, sin suba, cobro contado; comisión $10/kg;
  base $30 M, de los cuales bancos $2 M, estampillas $1 M y comisión de base $1 M
  (100.000 kilos × $10). Sin inflación; secadero $5 M. Sin compras ni flete en estos dos meses
  (se vende stock propio). Deuda automática $3 M y por decisión $1 M por mes.
  Saldo inicial cero y descubierto $10 M.

| Renglón (millones de pesos, salvo costo/kg) | Contado mes 1 | Contado mes 2 | 30 días mes 1 | 30 días mes 2 |
| --- | ---: | ---: | ---: | ---: |
| Costo de envase ($/kg) | 110 | 110 | 110 | 110 |
| Cobranza | 100 | 100 | 100 | 100 |
| Base antes de restar | 30 | 30 | 30 | 30 |
| Menos bancos de la base | −2 | −2 | −2 | −2 |
| Menos estampillas de la base | −1 | −1 | −1 | −1 |
| Menos comisiones de la base | −1 | −1 | −1 | −1 |
| Menos secadero | −5 | −5 | −5 | −5 |
| **Gastos operativos sin secadero** | **21** | **21** | **21** | **21** |
| Gastos de envase | 11 | 11 | 11 | 11 |
| Comisiones del mes | 1 | 1 | 1 | 1 |
| Canchada + flete | 0 | 0 | 0 | 0 |
| Total egresos de la operación | 33 | 33 | 33 | 33 |
| Resultado de la operación | 67 | 67 | 67 | 67 |
| Intereses y gastos bancarios | 2 | 2 | 2 | 2 |
| Deuda automática | 3 | 3 | 3 | 3 |
| Deuda por decisión | 1 | 1 | 1 | 1 |
| **Bancos y deuda** | **6** | **6** | **6** | **6** |
| **Saldo del mes** | **61** | **61** | **61** | **61** |
| **Saldo acumulado** | **61** | **122** | **61** | **122** |
| Descubierto | 10 | 10 | 10 | 10 |
| Saldo disponible | 71 | 132 | 71 | 132 |

Con 30 días, el mes 1 paga las ventas anteriores supuestas iguales al mes 1 y el mes 2 paga las del
  mes 1: por eso ambos dan $11 M. Para distinguir el corrimiento, si el mes 2 vendiera 200 TN,
  envases contado daría $22 M ese mes y a 30 días seguiría dando $11 M.

### Para la revisión en vivo

- La prueba local controla el texto de las fórmulas; no ejecuta el motor de Google Sheets.
  Claude debe instalar solo el bloque cambiado de crear_cash y las modificaciones del servidor,
  rearmar la solapa, cargar los supuestos nuevos reales ahí y publicar la nueva versión del tablero.
- Comparar base, promedio bancario, envases (incluido el primer mes a 30 días), comisiones, deuda
  y saldos contra una cuenta aparte. Verificar agrupación, lista de pago y conservación al rearmar.
- Probar en la aplicación web real el guardado y los botones del plan original. Si la foto guardada
  es anterior a estos supuestos, no contiene las claves nuevas: al volver conserva esos campos
  actuales. Guardar como original el plan completo cuando estén cargados los supuestos nuevos.
- Worktree `/private/tmp/finnauto-65`, rama `tarea/65-envases-y-bancos`. No accedí a datos reales,
  archivos privados, Drive ni la planilla del cliente; no cambié main ni publiqué nada.

## Revisión
- Claude (23/10) revisó y aprobó. **Corrección**: la consigna era ambigua y la resta del secadero había
  quedado sin inflación. Se volvió a inflar, porque está en pesos de los meses base, igual que la base;
  la prueba se ajustó (commit de Claude en la rama). Mergeada a main (ec7f959).
- **Instalada**:
  - crear_cash: solo el bloque de canchada sobre lo instalado;
  - Código.gs: el bloque de canchada sobre lo instalado, con los `PERMITIDOS` reales y el ID;
  - las huellas coinciden después de recargar;
  - aplicación web en versión 7, con el mismo link;
  - la solapa se rearmó y se cargaron los valores reales en la planilla.
- **Verificado en la planilla**:
  - costo de envase por kg y su monto del mes;
  - comisiones;
  - las restas de la base (bancos, estampillas, comisiones, secadero inflado);
  - el total de egresos;
  - bancos y deuda.
  Todo cierra con la cuenta aparte.
