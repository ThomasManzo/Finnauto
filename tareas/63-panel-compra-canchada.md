# Tarea 63 — Apartado "Compra de canchada" en el tablero: panel con controles conectado a la planilla
Estado: pendiente
Rama: tarea/63-panel-canchada

## Objetivo
Un apartado nuevo del tablero de siempre, "Compra de canchada", en la barra lateral debajo de
"Hallazgos". Ahí se mueven los supuestos del escenario de compra de canchada con controles
deslizables y se ve al instante cómo queda la caja mes a mes. Lo que se mueve se guarda en la solapa
"Cash compra canchada" de la planilla, y el panel muestra lo que calcula la planilla. **Las cuentas
viven en un solo lugar (la planilla); el panel no calcula plata.**

Maqueta aprobada por la dirección (la tiene Thomas; descripción abajo, en "Resultado esperado").

## Contexto
- **El tablero** (`dashboard/app.py` → `finauto.html`): lo arma la notebook del cliente una vez por día.
  Lo sirve `clientes/navar/herramientas/tablero_web.gs` (`doGet`), una aplicación web de Apps Script
  que ejecuta como el dueño y deja entrar solo a las cuentas de `PERMITIDOS`.
  - El HTML se sirve con `HtmlService`: **adentro de la aplicación web existe `google.script.run`**,
    y así el apartado le habla a la planilla en vivo.
  - Abierto como archivo suelto (sin la aplicación web), `google` no existe: el apartado tiene que
    decirlo en una línea ("este apartado funciona desde el link del tablero") y no romper nada.
- **La solapa "Cash compra canchada"** (tarea 62, función `armarCompraCanchada()` en
  `clientes/navar/herramientas/crear_cash.gs`). Leer el comentario largo arriba de esa función.
  - Supuestos en la columna B, filas 4 a 13, identificados por el texto de la columna A. Los textos
    exactos están en `CC_SUPUESTOS`:
    - precio de venta hoy, suba por mes, durante cuántos meses sube;
    - días de cobro;
    - precio de la canchada, flete, en cuántas partes se paga;
    - stock propio;
    - gasto del secadero y la hoja verde que deja de estar;
    - primer mes.
  - Dos filas por mes, editables, identificadas por su texto: **"TN vendidas"** y **"TN compradas"**
    (columnas B a O = 14 meses).
  - Resultados: filas por texto de la columna A, por ejemplo:
    - "Mes", "Precio ($/kg, sin IVA)";
    - "Cobranza de las ventas (según los días de cobro)";
    - "Total egresos de la operación", "Resultado de la operación (antes de la deuda)";
    - "Total deuda del mes", "Saldo del mes pagando la deuda que vence", "Saldo acumulado";
    - "Descubierto acordado con los bancos";
    - "Saldo disponible (acumulado + descubierto): si da negativo, eso es lo que falta financiar";
    - y los renglones de gastos, canchada y flete.
  - **Buscar siempre por texto, nunca por número de fila**: la solapa se rearma y las filas se pueden mover.
- **El repo es público: nada de datos reales** en código, comentarios, pruebas ni en esta consigna.
  Ejemplos inventados. Los valores reales están en la planilla y no se copian.

## Archivos permitidos
- `clientes/navar/herramientas/tablero_web.gs` (funciones nuevas del lado del servidor).
- `dashboard/app.py` (apartado nuevo: botón en la barra, `CAPAS`, JS, CSS).
- `dashboard/datos.py` (solo para pasar la marca de que este cliente tiene el apartado, leída del perfil).
- `clientes/navar/perfil.json` (la marca: `"tablero": {"escenario_canchada": true}` o similar).
- Pruebas nuevas: `lector/pruebas/probar_panel_canchada.cjs` (servidor) y un test de Python del render.
- `tareas/63-panel-compra-canchada.md`.

No tocar `crear_cash.gs`, `importar_cashflow.gs` ni la notebook.

## Resultado esperado

### 1 · Servidor (`tablero_web.gs`)
- `leerEscenarioCanchada()` devuelve un objeto con:
  - `supuestos`: clave → valor, con las claves de `CC_SUPUESTOS`;
  - `meses`: fechas ISO;
  - `filas`: texto → 14 números;
  - `hora`: cuándo se leyó;
  - `falta`: el texto de "Faltan cargar".
- `guardarEscenarioCanchada(cambios)` recibe `{supuestos: {...}, tnVendidas: [14], tnCompradas: [14]}`
  (cualquiera de las partes, o varias).
  - Valida:
    - números y rangos razonables;
    - `partes` entero de 1 a 6;
    - `mesesSuba` entero de 0 a 14;
    - `suba` entre 0 y 0,5;
    - TN de 0 a 5000.
  - Escribe solo esas celdas, buscándolas por texto.
  - Hace `SpreadsheetApp.flush()` y devuelve `leerEscenarioCanchada()` ya recalculado.
  - Usa `LockService` para que dos personas no se pisen.
- Las dos funciones repiten el control de `PERMITIDOS` de `doGet`: si el mail no está, error y no
  leen ni escriben nada.
- `guardarPlanOriginalCanchada()` y `volverAlPlanOriginalCanchada()`:
  - la primera guarda una foto de los supuestos y de las dos filas de TN en las Propiedades del
    script (`PropertiesService`, clave `canchada_plan_original`);
  - la segunda la repone.
  - Si no hay foto, `volver…` contesta un error claro.
  - La primera vez que se guarda algo desde el panel y no hay foto, se saca la foto **antes** de
    escribir, así el "original" es lo que había.
- La planilla se abre con `SpreadsheetApp.openById(...)`: la aplicación web no tiene "planilla
  activa". El id va en una constante con un comentario; no es un dato sensible (ya está en la URL de
  la planilla).

### 2 · Apartado en el tablero (`dashboard/app.py`)
- Botón nuevo en la barra lateral, "Compra de canchada", con ícono de líneas, debajo de "Hallazgos".
  Aparece solo si el paquete trae la marca del perfil.
- **Mismo estilo del tablero**: colores, tipografías, `.kpis`/`.kpi`, `h2`, tablas, `button.mini`. Sin
  librerías ni CDN: gráfico SVG a mano como los otros.
- Contenido, de arriba hacia abajo:
  1. **Una línea de texto**: "Escenario conectado a la solapa Cash compra canchada de la planilla:
     movés un control, se guarda ahí y vuelve el número que calcula la planilla."
  2. **Supuestos**: 10 controles en una grilla de 5 columnas. Cada uno con su nombre, el valor en
     grande (serif) y una barra deslizable con el mínimo y el máximo abajo.
     - **Canchada: precio de compra** ($/kg, de 900 a 1.800, de a 5).
     - **Canchada: flete** ($/kg, de 0 a 100).
     - **TN compradas por mes**, de 0 a 600, de a 10. La barra pone el mismo valor en los 14 meses.
       Abajo, "cambiar mes por mes" abre una fila de 14 casilleros chicos.
     - **TN vendidas por mes**: igual que la anterior.
     - **Precio de venta hoy** ($/kg, de 1.000 a 3.000).
     - **Suba del precio por mes** (0 a 20%, de a 0,5).
     - **Durante cuántos meses sube** (0 a 14).
     - **Días promedio de cobro** (0 a 90).
     - **Canchada: partes de pago** (1 a 6; mostrar "4 (0/30/60/90)").
     - **Secadero y hoja verde que dejan de estar** ($ por mes, de 0 a 400 M, de a 1 M).

     Arriba a la derecha:
     - un estado: "guardado en la planilla · recalculado hace N s", o "guardando…", o el error;
     - los botones **"Volver al plan original"** y **"Guardar como plan original"**.
  3. **Cuatro tarjetas** (`.kpis`). Salen de las filas que devuelve la planilla; no se recalcula plata:
     - **Peor saldo acumulado**: el mínimo de "Saldo acumulado", con el mes.
     - **Se pasa del descubierto en**: el primer mes en que "Saldo disponible…" da negativo, o
       "no se pasa".
     - **Plata que hay que conseguir**: el máximo de −"Saldo disponible…" (0 si nunca es negativo).
     - **Resultado de un mes típico**: el promedio de "Saldo del mes…" desde el mes en que la compra
       está a pleno (mes número = partes de pago) hasta el último.

     En rojo (`.kpi.malo`) cuando son malas.
  4. **Gráfico "Caja mes a mes"**:
     - línea del saldo acumulado, con puntos rojos donde el disponible es negativo;
     - barras del saldo del mes (verde si es positivo, rojo si es negativo, con transparencia);
     - línea punteada ámbar en −descubierto, con la etiqueta "límite del descubierto".
  5. **Tabla "El detalle"**, una columna por mes. Filas: cobranza; gastos sin secadero (gastos +
     menos secadero); canchada + flete; deuda; saldo del mes; saldo acumulado (en negrita). En
     millones, sin decimales, con punto de miles. Abajo, la nota de qué no incluye; usar el texto de
     la solapa.
- **Cuándo se guarda**:
  - al soltar la barra (`change`, no `input`). Mientras se arrastra, solo cambia el número grande;
  - si se suelta otra en menos de 0,8 s, se espera y se manda todo junto;
  - mientras guarda, los controles siguen usables y el estado dice "guardando…";
  - si hay error, se vuelve al último valor bueno y el error se muestra en el estado.
- Al entrar al apartado, `leerEscenarioCanchada()` y se pintan los controles con lo que hay en la planilla.
- Si "Faltan cargar" no está vacío, una banda ámbar arriba de las tarjetas lo dice tal cual.
- Celular: los controles en una columna, la tabla con desplazamiento horizontal (`.envuelve`).

### 3 · Marca por cliente
- `perfil.json` de NAVAR: la marca que prende el apartado.
- `datos.py` la pasa al paquete. Para otros clientes, el botón no aparece.

## Comprobaciones
1. `probar_panel_canchada.cjs`, con una planilla de juguete inventada que tenga los textos de la solapa:
   - lee bien;
   - guarda por texto aunque las filas cambien de lugar;
   - rechaza valores fuera de rango;
   - rechaza un mail que no está en `PERMITIDOS`;
   - la foto del plan original se saca antes de la primera escritura;
   - volver al plan original repone todo.
2. Test de Python:
   - el render con la marca prendida incluye el botón y el apartado;
   - sin la marca, no aparece;
   - el HTML no tiene `<script src=`.
3. Las pruebas que ya existen siguen pasando: `python -m pytest`, más todos los `.cjs` de
   `lector/pruebas/` con Node.
4. Explicar en "Qué hice", en criollo, cómo llega un cambio desde la barra hasta la planilla y vuelta.
5. Lo que no se puede probar desde el worktree (la aplicación web real, `google.script.run`) lo
   prueba Claude después en la planilla. Anotar qué mirar.

## Qué hice
(lo completa Codex)

## Revisión
(lo completa Claude: pegar tablero_web.gs en Apps Script, nueva versión de la implementación con la
misma URL, rearmar el tablero en la notebook con `actualizar.ps1` y probar el apartado en vivo)
