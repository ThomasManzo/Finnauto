# Tarea 37 — Resumen semanal de principales clientes y proveedores (foto + mail de los lunes)
Estado: lista para revisión
Rama: tarea/resumen-semanal

## Objetivo

Que **cada lunes a la mañana** NAVAR reciba por mail, sin que nadie haga nada, un resumen de cómo
cambiaron sus 20 principales clientes (lo que les deben) y 20 principales proveedores (lo que deben
ellos) respecto del lunes anterior. Es para seguir el plan de regularización de Tango: ver si lo
vencido baja, quién mejoró, quién empeoró y quién sigue sin ningún pago registrado.

Para comparar hace falta historia, y hoy no la hay: la solapa "Principales 20" se recalcula todos los
días y pisa lo anterior. Esta tarea agrega **una foto semanal guardada** y **el mail que la compara**.

## Contexto

Leer antes: `tareas/LEEME.md`, `CLAUDE.md`, `clientes/navar/LEEME.md` (sección "Principales 20 +
último pago" dentro de "Dónde estamos (29/09/2026)"), `clientes/navar/herramientas/aviso_diario.gs`
(cómo arma y manda el mail diario, cómo lee la Sheet, cómo se instala su disparador) y
`lector/pruebas/probar_aviso_bajadas.cjs` (cómo se prueba Apps Script con dobles, sin Google).

Lo que ya existe en la Sheet "NAVAR - Cash Flow" (no se toca):
- **Cuentas a Cobrar**: `Cliente`, `Empresa` (A/AA), `Fecha Vencimiento`, `Saldo Pendiente` (fórmula).
- **Cuentas a Pagar**: `Proveedor`, `Empresa`, `Fecha Vencimiento`, `Saldo Pendiente` (fórmula).
- **Ultimos Pagos**: `Empresa | Tipo (Cliente/Proveedor) | Codigo | Razon Social | Fecha Ultimo Pago |
  Comprobante | Origen`, una fila por empresa + tipo + razón social.
- **Principales 20**: la pantalla, armada con fórmulas. **No leer esta solapa** (su ubicación de
  bloques ya cambió una vez porque alguien insertó una fila): el script calcula lo mismo desde las
  listas, **por encabezado, no por letra de columna**.

Reglas de la pantalla, que el script tiene que repetir igual (así los números del mail coinciden con
la solapa):
- por empresa (A, AA) y tipo (clientes = Cuentas a Cobrar, proveedores = Cuentas a Pagar);
- **saldo** = suma de `Saldo Pendiente` por razón social (con negativos: es el saldo neto);
- los **20** de mayor saldo;
- **vencido** = suma de `Saldo Pendiente` con `Fecha Vencimiento` anterior al día de la foto;
  **a vencer** = saldo − vencido;
- **vto. impago más viejo** = la menor `Fecha Vencimiento` con saldo > 0 ya vencida;
- **último pago** = `Fecha Ultimo Pago` de "Ultimos Pagos" para esa empresa + tipo + razón social
  (vacío si no hay).

Decisiones tomadas con Thomas (29/09/2026):
- **Lunes 08:00** (hora de Buenos Aires), después del mail diario de las 07:30.
- **Destinatarios**: los mismos del mail diario (`DESTINATARIOS` de `aviso_diario.gs`). Reusar esa
  variable, no copiar la lista.
- **Foto inicial**: se guarda a mano el día que se instala (desde el menú), así el primer lunes ya
  tiene contra qué comparar.

## Archivos permitidos

- `clientes/navar/herramientas/resumen_semanal.gs` (nuevo; en Apps Script será otro archivo del mismo
  proyecto)
- `clientes/navar/herramientas/importar_cashflow.gs`: **solo** agregar tres ítems al menú de
  `onOpen` (ver abajo). Nada más de ese archivo.
- `lector/pruebas/probar_resumen_semanal.cjs` (nuevo)
- esta consigna ("Qué hice" y `Estado:`)

## Resultado esperado

1. **Foto semanal** — `guardarFotoSemanal()`:
   - Calcula los 4 bloques (A/AA × clientes/proveedores) con las reglas de arriba.
   - Agrega filas a una lista nueva **"Principales 20 · historial"** (la crea si no existe, con
     encabezado en la fila 1): `Fecha foto | Empresa | Tipo | Puesto | Razon Social | Saldo | Vencido |
     A vencer | Vto Impago Mas Viejo | Ultimo Pago`. Una fila por cada uno de los 80. Solo agrega;
     nunca borra ni modifica fotos anteriores.
   - Si ya hay una foto **del mismo día**, la reemplaza (borra solo las filas de esa fecha y vuelve a
     escribir): correrla dos veces el mismo día no duplica.
   - Si falta alguna lista o algún encabezado necesario, no escribe nada y lanza un error claro
     (qué falta y dónde).
2. **Mail semanal** — `resumenSemanal()`: primero guarda la foto de hoy, después compara contra **la
   foto anterior más reciente** (no necesariamente de hace 7 días) y manda el mail. Contenido, en
   texto plano como el mail diario (frases cortas, montos en `$X M`, fechas `dd/mm`):
   - asunto: `NAVAR · Principales clientes y proveedores · semana del dd/mm`;
   - por cada bloque (Clientes A, Clientes AA, Proveedores A, Proveedores AA): total de los 20 y total
     vencido, cada uno con su diferencia contra la foto anterior (`$X M vencido (−$X M)`);
   - por bloque, **los 3 que más bajaron** su vencido y **los 3 que más subieron** (nombre, vencido
     actual, diferencia);
   - por bloque, **quién entró y quién salió** del top 20;
   - una sección **"Sin pagos registrados"**: los de los 20 actuales sin último pago, con su saldo;
   - si no hay foto anterior: lo mismo pero sin diferencias, y una línea que lo aclare;
   - pie: "Datos según Tango. Detalle en la solapa Principales 20 de la planilla."
   - **Adjunto**: la solapa "Principales 20" en PDF (exportación de esa sola solapa, apaisada). Si la
     exportación falla, el mail sale igual sin adjunto y lo dice en una línea.
3. **Instalación** — `instalarResumenSemanal()` (lunes 08:00, borra antes cualquier disparador de
   `resumenSemanal` para no duplicar) y `quitarResumenSemanal()`. Zona horaria: la del proyecto, que ya
   es Buenos Aires.
4. **Menú** (en `onOpen` de `importar_cashflow.gs`, en un bloque propio con separador):
   `Ver el resumen semanal (sin mandar)` (muestra el texto en un cuadro, sin mandar ni guardar foto),
   `Guardar foto semanal ahora` y `Instalar resumen semanal (lunes 08:00)`.
5. Comentarios en criollo en todo el archivo (qué hace y por qué). Sin nombres de personas de NAVAR en
   el mail.

## Comprobaciones

- `node lector/pruebas/probar_resumen_semanal.cjs` con dobles de `SpreadsheetApp`, `MailApp`,
  `UrlFetchApp`, `ScriptApp` y datos **inventados** (como `probar_aviso_bajadas.cjs`). Casos:
  - los 4 bloques salen iguales a un cálculo a mano de un ejemplo chico (saldo, vencido, a vencer,
    vto. impago más viejo, último pago), con **columnas en otro orden** que el de la Sheet real;
  - dos fotos en fechas distintas → diferencias, "más bajaron/subieron", entró/salió, sin pagos;
  - sin foto anterior → mail sin diferencias y con la aclaración;
  - foto del mismo día dos veces → no duplica; fotos anteriores intactas;
  - falta la lista "Ultimos Pagos" o un encabezado → error claro y no escribe nada;
  - falla la exportación a PDF → el mail sale sin adjunto y lo dice;
  - `instalarResumenSemanal` deja un solo disparador, lunes 08:00.
- Correr también `node lector/pruebas/probar_aviso_bajadas.cjs` (no se toca el aviso, pero comparte
  el proyecto de Apps Script).
- Qué **no** se puede probar acá: la exportación real a PDF, el envío real y el disparador real. Lo
  prueba Claude con Thomas al instalar (con "Ver el resumen semanal (sin mandar)" primero).

## Qué hice

**La escribió Claude, no Codex** (29/09/2026: Codex sin margen, pedido de Thomas).

- `clientes/navar/herramientas/resumen_semanal.gs` (nuevo). Capa fina de Google (`resumenSemanal`,
  `resumenSemanalPrueba`, `guardarFotoSemanal`, `instalarResumenSemanal`, `quitarResumenSemanal`) que
  llama a funciones con la Sheet y el "ahora" como parámetros (`_mandarResumenSemanal_`,
  `_verResumenSemanal_`, `_guardarFotoDeHoySemanal_`), y funciones puras para el cálculo
  (`_calcularFotoSemanal_`) y el texto (`_armarResumenSemanal_`). Columnas por encabezado (sin tildes
  ni mayúsculas, en cualquier orden); nombres con sufijo `Semanal` para no chocar con los otros `.gs`
  del proyecto. Usa `DESTINATARIOS` del aviso y `_registrar_` del importador (deja ok/ERROR en Registro).
- Foto: agrega a "Principales 20 · historial" (la crea con encabezado si no existe); si ya hay filas
  del mismo día las borra (de abajo hacia arriba) y reescribe; agranda la hoja si hace falta. La foto
  anterior es la más reciente con fecha menor a hoy.
- Mail: por bloque, total de los 20 y vencido con diferencia; los 3 que más bajaron y subieron su
  vencido (umbral $1 para no listar redondeos); entraron/salieron o "Los mismos 20"; sección "sin
  pagos registrados"; pie. Diferencias de menos de $X M se muestran como "sin cambios". PDF: export
  de la solapa por `gid`, apaisado, con el token del script; si falla, sale sin adjunto y lo dice.
- Disparador: lunes `atHour(8).nearMinute(15)` → entre 08:00 y 08:30 de Buenos Aires.
- `importar_cashflow.gs`: solo los tres ítems del menú, en un bloque propio.
- `lector/pruebas/probar_resumen_semanal.cjs` (nuevo): 9 grupos de casos con una Sheet falsa en
  memoria (todo lo que pide Comprobaciones, más: tope de 20 con empates, nota de crédito que resta y
  no cuenta como "más viejo", vencimiento el mismo día = no vencido, fechas como texto, vista previa
  que no manda ni guarda, el menú apunta a funciones que existen).

Cómo se probó:
- Node: el de la app de ChatGPT (`/Applications/ChatGPT.app/Contents/Resources/cua_node/bin/node`,
  v24), porque la Mac no tiene Node instalado. `probar_resumen_semanal.cjs`: todo OK.
  `probar_aviso_bajadas`, `probar_importador_ultimos_pagos`, `probar_importador_zona_horaria`,
  `probar_volcado_fechas`: OK. `probar_importador_filtros`: falla solo en la vieja expectativa
  "NO CUADRÓ" del aviso, igual que en `main` (ya anotado en la tarea 34); no es de esta tarea.
- **Con datos reales** (export de la Sheet con la bajada del 28/09): `_calcularFotoSemanal_` da los
  mismos totales que la solapa y que la validación contra Tango de ese día: clientes A $X M /
  vencido $X M; AA $X M / $X M; proveedores A $X M / $X M; AA $X M / $X M.
- Sin probar acá: la exportación real a PDF, el envío real y el disparador real.

Para instalar: pegar `resumen_semanal.gs` como archivo nuevo del proyecto y el `importar_cashflow.gs`
nuevo; recargar la Sheet; "Ver el resumen semanal (sin mandar)"; "Guardar foto semanal ahora" (foto
inicial); "Instalar resumen semanal". La primera vez que se corra algo del menú, Google va a pedir
permiso nuevo para "conectarse a un servicio externo" (lo usa la exportación a PDF): hay que
aceptarlo, porque el disparador del lunes no puede pedirlo.

## Revisión
