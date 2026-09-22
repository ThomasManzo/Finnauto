# Tarea 01 — Aviso diario por mail: qué llegó, qué se procesó, qué falló
Estado: pendiente
Rama: tarea/aviso-diario

## Objetivo

Que cada mañana llegue un mail corto, en criollo, que diga si el cash de NAVAR amaneció al día:
qué archivos llegaron a Drive en las últimas 24 horas, cuáles procesó el vigilante, cuáles importó
la Sheet, y **qué falló o quedó trabado**, con la acción sugerida. Si no hay problemas, el mail
tiene que poder leerse en 10 segundos. Si no llegó nada, también lo dice (eso es información).

## Contexto

Leer antes: `AGENTS.md`, `CLAUDE.md`, `clientes/navar/LEEME.md` (sección "Próximos pasos") y
`clientes/navar/documentos/manual_cash.md` §6 ("Cómo se actualiza"). El circuito de actualización
es en tres pasos, y cada paso deja una huella distinta:

1. **Alguien deja un archivo en Drive** (`NAVAR - Datos/Bancos/<banco>`, `Cuentas a cobrar`,
   `Cuentas a pagar`, `Cheques`, `Deuda bancaria`, `Impuestos`, `Tesorería AA`).
   Huella: la fecha de modificación del archivo en Drive.
2. **El vigilante** (`clientes/navar/herramientas/vigilante.py`, corre cada 15 min en la notebook
   de NAVAR) ve el archivo y corre el lector. Huella: un `para_pegar_<tipo>_<fecha>.xlsx` nuevo en
   `NAVAR - Datos/_para la Sheet/` (o en `_para la Sheet/_retenido/` si el control de filas lo
   frenó). Además escribe `vigilante.log` en la notebook (`clientes/navar/privado/vigilante.log`),
   que **hoy no está en Drive**: parte de esta tarea es que lo esté.
3. **El disparador de la Sheet** (`importarLoNuevo` en `clientes/navar/herramientas/importar_cashflow.gs`,
   Apps Script, cada hora a los :32) importa el `para_pegar` nuevo. Huella: una fila en la solapa
   **Registro** de la Sheet (`Cuándo | Qué | Archivo | Estado | Detalle`, con `ok` o `ERROR`; la fila
   más nueva va arriba, fila 2).

Los tipos de `para_pegar` y a qué carpeta de Drive responde cada uno están en `IMPORTS` de
`importar_cashflow.gs` (prefijos `para_pegar_bancos_`, `para_pegar_en_la_sheet_` = Tango,
`para_pegar_deuda_`, `para_pegar_impuestos_`, `para_pegar_tesoreria_aa_`).

**Decisiones ya tomadas (no re-discutir):**
- El aviso se implementa en **Apps Script dentro de la Sheet**, no en Python: es el único lugar que
  ve a la vez Drive (DriveApp), la solapa Registro y puede mandar mail (MailApp) **sin guardar
  ninguna contraseña**. Se manda desde la cuenta dueña de la Sheet.
- **Destinatario: `finanzasnavar@gmail.com`** (la cuenta de la empresa). Como constante al principio
  del archivo, fácil de cambiar; se puede poner más de uno separados por coma.
- Hora: **07:30 de Buenos Aires**, todos los días. La Sheet quedó con zona horaria del Pacífico
  (eso explica que Registro muestre 4 horas menos), así que **toda fecha que se muestre en el mail
  se formatea explícitamente** con `Utilities.formatDate(fecha, "America/Argentina/Buenos_Aires", ...)`
  y el disparador se crea con `.inTimezone("America/Argentina/Buenos_Aires")`.
- **Sin nombres propios** de gente de NAVAR en el mail ni en el código: roles (administración, la
  dirección, finauto). El mail lo va a leer la empresa.
- Mismo estilo que `importar_cashflow.gs`: `var`, funciones auxiliares con guión bajo al final
  (`_algo_`), comentarios en criollo arriba de cada función diciendo qué hace y por qué. Reusar
  `CARPETA_RAIZ` y el patrón de recorrido de `_ultimoConPrefijo_` (el `.gs` nuevo vive en el
  mismo proyecto de Apps Script, así que puede llamar funciones del otro archivo; pero no las
  modifica).

## Archivos permitidos

- `clientes/navar/herramientas/aviso_diario.gs` — **nuevo**. Todo el aviso vive acá.
- `clientes/navar/herramientas/vigilante.py` — **solo** agregar que, al final de cada pasada en la que
  corrió algo (o falló algo), copie el log a Drive: `NAVAR - Datos/_para la Sheet/vigilante.log`
  (copia del archivo entero; el log es chico). Sin tocar nada más del vigilante.
- `clientes/navar/documentos/manual_cash.md` — agregar en §6 una fila a la tabla "Cómo se actualiza"
  (paso "cada mañana: el aviso") y un párrafo corto de qué dice el mail y qué hacer con cada alerta.
- `clientes/navar/LEEME.md` — en la tabla "Archivos de trabajo", una fila para `aviso_diario.gs`.
- `tareas/01-aviso-diario.md` — este archivo: completar "Qué hice" y cambiar el Estado.

Nada más. En particular **no tocar** `importar_cashflow.gs`, `crear_cash.gs`, los lectores ni nada
de `clientes/navar/privado/` (que además no existe en el worktree).

## Resultado esperado

`aviso_diario.gs` con estas funciones (nombres exactos, para que el menú y la guía coincidan):

- `avisoDiario()` — arma el texto y lo manda por `MailApp.sendEmail` a `DESTINATARIOS`, con asunto
  `NAVAR cash · <fecha dd/mm> · al día` o `NAVAR cash · <fecha> · ATENCIÓN (n)` según haya alertas.
- `avisoDiarioPrueba()` — arma el mismo texto y lo muestra con `Logger.log` y `SpreadsheetApp.getUi().alert`
  **sin mandar nada**. Es lo que se corre para ver cómo queda.
- `instalarAvisoDiario()` / `quitarAvisoDiario()` — crean/borran el disparador diario a las 07:30
  Buenos Aires, y anotan en la solapa Registro (`Qué` = `sistema`) como hace `instalarDisparador`.
- `_armarAviso_(ahora)` — la función pura que devuelve `{ asunto, cuerpo, alertas }`. Separarla
  de la que manda el mail para que la prueba y el envío usen exactamente el mismo texto.
- Menú: un `onOpen` **no** (ya existe en el otro archivo y se pisarían). En su lugar, dejar en el
  comentario de cabecera las tres líneas que hay que agregar al menú `finauto` de
  `importar_cashflow.gs` ("Ver el aviso de hoy (sin mandar)", "Instalar aviso diario 07:30",
  "Quitar aviso diario"). Ese cambio lo hace Claude al revisar.

**El cuerpo del mail** (texto plano, con secciones y guiones; nada de HTML), en este orden:

1. **Encabezado**: fecha de hoy; "Último extracto cargado: <fecha>" = la fecha más nueva en la
   columna Fecha de la solapa **Saldos Bancarios** con Origen `Extracto`; "Último export de
   Tango: <fecha>" = la fecha en el nombre del `para_pegar_en_la_sheet_<fecha>` más nuevo.
2. **Llegó a Drive (últimas 24 h)**: por carpeta, `- <carpeta>/<archivo> (hh:mm)`. Si nada:
   "- nada nuevo". Ignorar `_para la Sheet`, `Scripts`, `Tablero`, `_viejo`, `Tango` (la carpeta
   vieja de exports sueltos) y archivos ocultos.
3. **El vigilante procesó**: los `para_pegar_*` de `_para la Sheet` con fecha de modificación en las
   últimas 24 h (`- <tipo>: <archivo> (hh:mm)`), y aparte los que estén en `_retenido` de las últimas
   24 h como alerta. Si `_para la Sheet/vigilante.log` existe, agregar las últimas líneas de las
   últimas 24 h que contengan `FALLÓ` o `RETENIDO` (máximo 5 líneas, recortadas a 160 caracteres).
4. **La Sheet importó**: las filas de Registro de las últimas 24 h (`- hh:mm <Qué> <Estado> — <Detalle>`
   recortado a 120 caracteres). Ojo: la columna Cuándo está en hora de la Sheet; comparar como
   `Date` (eso es independiente de la zona) y **mostrar** en Buenos Aires.
5. **Alertas** (esta sección va arriba de todo, después del encabezado, si hay al menos una; si no,
   una sola línea "Sin alertas: el cash está al día."). Cada alerta = una línea con el problema y
   qué hacer, así:
   - Llegó un archivo a una carpeta de datos hace más de **2 horas** y no hay un `para_pegar` de su
     tipo posterior a él → "El vigilante no procesó <archivo>. Revisar que la notebook esté prendida
     y `vigilante.log`."
   - Hay un `para_pegar` con más de **2 horas** y ninguna fila de Registro de ese tipo posterior →
     "La Sheet no importó <archivo>. Abrir la Sheet → finauto → Importar lo nuevo ahora."
   - Alguna fila de Registro de las últimas 24 h con Estado `ERROR` → "Falló la importación de
     <Qué>: <Detalle>."
   - Algo en `_retenido` de las últimas 24 h → "El vigilante retuvo <archivo> (una lista se achicó
     más de la mitad). Revisar el export antes de publicarlo."
   - Último extracto con más de **7 días** → "Hace <n> días que no llega un extracto de banco. Pedirlo."
   - Último export de Tango con más de **3 días** → "Hace <n> días que no llega un export de Tango."
   - Falló el propio aviso al leer algo (try/catch por sección): la sección dice "(no pude leer esto:
     <error>)" y cuenta como alerta. El mail tiene que salir igual.

Mapa carpeta → tipo de `para_pegar` (para la alerta 1): `Bancos/*` → `para_pegar_bancos_`;
`Cuentas a cobrar`, `Cuentas a pagar`, `Cheques` → `para_pegar_en_la_sheet_`; `Deuda bancaria` →
`para_pegar_deuda_`; `Impuestos` → `para_pegar_impuestos_`; `Tesorería AA` (también sin tilde,
`Tesoreria AA`) → `para_pegar_tesoreria_aa_`.

Tope de tamaño: si una sección pasa de 25 líneas, cortar y agregar "... y <n> más".

## Comprobaciones

Apps Script **no se puede ejecutar en el worktree**: se comprueba lo comprobable y el resto lo hace
Claude en la Sheet al revisar. Lo que sí se tiene que hacer y anotar en "Qué hice":

1. **Sintaxis**: si hay `node` disponible, `node --check` no sirve para `.gs` directo; copiar a un
   `.js` temporal y correr `node --check`. Si no hay `node`, decirlo. No instalar nada para esto.
2. **La función pura se puede probar sin Google**: escribir en la cabecera del `.gs` (comentario) o
   en "Qué hice" un ejemplo de entrada/salida de `_armarAviso_` pensado a mano: qué asunto y qué
   alertas salen con (a) nada nuevo y extracto de hace 8 días, (b) un archivo en Bancos hace 3 h sin
   para_pegar, (c) todo ok. Es para que Claude pueda verificar la lógica leyendo.
3. `grep -n -i -E "priscilla|karina|celia|miriam|milagros|charles|maría rosa|thomas" clientes/navar/herramientas/aviso_diario.gs`
   tiene que devolver vacío.
4. `python -m py_compile clientes/navar/herramientas/vigilante.py` tiene que pasar, y el cambio en
   vigilante.py tiene que ser **solo** la copia del log (ver `git diff`), envuelta en try/except:
   si Drive no está montado o falla la copia, el vigilante no se cae por eso.
5. En el manual y el LEEME, las filas nuevas siguen el formato de las tablas existentes.
6. Commit(s) en la rama `tarea/aviso-diario`, con mensaje en criollo que diga qué y por qué.

Al terminar: completar "Qué hice" (archivos tocados, qué se probó, qué no se pudo probar, dudas) y
poner `Estado: lista para revisión`.

## Qué hice

(lo completa Codex)

## Revisión

(lo completa Claude)
