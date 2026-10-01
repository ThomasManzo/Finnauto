# NAVAR S.A. — la carpeta del cliente

Yerbatera en Corrientes. **Primer cliente real de finauto** (12/09/2026).
No es el piloto del plan comercial: es una asesoría para ordenar la parte
financiera, y finauto es la herramienta con la que se hace.

## Qué hay acá

| Archivo | Qué es | ¿Sube a git? |
|---|---|---|
| `perfil.json` | Lo operativo: bancos, de dónde sale cada dato, dónde caen los extractos. | Sí |
| `catalogo.json` | El vocabulario del cliente: tipos de pago, tolerancias, proveedores, ingresos. **Es un BORRADOR**: lo que está en `null` o en `_pendiente` se pregunta, no se adivina. | Sí |
| `documentos/` | El checklist de implementación y los arreglos del esqueleto. | Sí |
| `herramientas/` | Los scripts de este cliente (migración, arreglo del cash, PDFs). | Sí |
| `privado/` | Planillas, PDFs generados, capturas y el diagnóstico con montos reales. | **No** (está en `.gitignore`) |
| `memoria/` | Las fotos de cada proyección, para conciliar después. Se crea sola al correr `finauto.py`. | No |

## El tablero (la URL que ve NAVAR)

**https://script.google.com/macros/s/AKfycbwj83jJ691gpSoD46ptTYnbzzjQ1nlWIWDdU3kG4MgXniCWEWO5s4wYUTVKeWZC5YbM/exec**

La sirve `herramientas/tablero_web.gs` (en el proyecto de Apps Script se llama `Código.gs`) leyendo
el último `finauto.html` de `NAVAR - Datos/Tablero/`. **La URL no cambia**: para actualizar el
tablero alcanza con dejar un `finauto.html` nuevo en esa carpeta. Sólo entran las cuentas de Google
que estén en la lista `PERMITIDOS` del script (ya tiene las de NAVAR).

Para regenerarlo: bajar la Sheet como Excel a `privado/`, correr `lector/cash_limpio.py` y después
`finauto.py --contrato ... --salidas privado/salidas`, y copiar `salidas/finauto.html` a la carpeta
`Tablero` de Drive.

## La Sheet (la fuente de verdad)

**"NAVAR - Cash Flow"** en el Drive de Thomas (id `1u9CfWz_MntC2xO_gcDGaohEVMZNUNbHv0WoFSqKK7e8`).
Hasta que se presente el proyecto queda ahí; después pasa a una cuenta de NAVAR.
Para leerla desde finauto se baja como Excel (por el conector de Drive o
Archivo → Descargar) a `privado/NAVAR - Cash Flow (export Sheets <fecha>).xlsx`.

## Cómo se corre todo (hoy)

```bash
source .venv/bin/activate
python lector/tango.py --carpeta "clientes/navar/privado/tango/2026-09-16" --cliente navar --hoy 2026-09-16 --sheet "clientes/navar/privado/NAVAR - Cash Flow (export Sheets 2026-09-12).xlsx"
python lector/extractos.py --carpeta clientes/navar/privado/bancos --cliente navar --hoy 2026-09-18 --sheet "clientes/navar/privado/NAVAR - Cash Flow (con Tango 2026-09-16).xlsx"
python lector/deuda_bancaria.py --archivo clientes/navar/privado/bancos/Bancos_Navar.xlsx --cliente navar --hoy 2026-09-18 --bancos clientes/navar/privado/bancos/para_pegar_bancos_2026-09-18.xlsx --sheet "clientes/navar/privado/NAVAR - Cash Flow (con bancos 2026-09-18).xlsx"
python lector/deuda_impositiva.py --archivo "clientes/navar/privado/impuestos/Control Vencimiento Impuestos.xlsx" --cliente navar --hoy 2026-09-18 --sheet "clientes/navar/privado/NAVAR - Cash Flow (con deuda 2026-09-18).xlsx"
python lector/cash_limpio.py --archivo "clientes/navar/privado/NAVAR - Cash Flow (con impuestos 2026-09-18).xlsx" --cliente navar --hoy 2026-09-18
python finauto.py --contrato clientes/navar/contrato_2026-09-18.json --cliente navar --salidas clientes/navar/privado/salidas
python clientes/navar/herramientas/propuesta.py        # el PDF para la dueña, con capturas del tablero
```

`--hoy 2026-08-31` porque los datos cargados son de ese lunes: con la fecha real
el tablero marcaría como vencidas cobranzas que son proyecciones de semanas
pasadas. Cuando carguen una semana nueva, se corre con la fecha de esa carga.

## El checklist vivo

https://claude.ai/artifact/K8SzFarJZTEhNw4rP1hX7q — tildes y minutos guardados y compartidos. La versión en texto está en `documentos/CHECKLIST_IMPLEMENTACION.md`.

## Contrato (15/09/2026)

**NAVAR dio el OK el 15/09/2026.** Implementación $1.400.000 (pesos) + abono
USD 400/mes desde el mes 2, revisable a los 3 meses contra el acierto medido.
La presentación (PDF de propuesta + vista rápida del tablero + la Sheet) fue
lo que cerró. Primer peso cobrado de finauto.

## Dónde estamos (29/09/2026) — la mañana corre sola; bancos: Galicia sí, el resto no

**La mañana de NAVAR** (pedido del cliente: cash al día a las 07:00), instalado y verificado el 29/09:

| Hora | Qué | Dónde |
|---|---|---|
| 05:45 | Tango (`finauto NAVAR Tango`) y Galicia (`finauto NAVAR Galicia`) | notebook, Programador de tareas |
| 05:48 | Galicia otra vez (seguro: la primera corrida a veces falla en frío) | notebook |
| 05:53 / 06:08 | vigilante → lectores | notebook, cada 15 min |
| 06:15–06:45 | la Sheet importa (diario) + la de cada hora | Apps Script, `instalarDisparador` |
| 07:15–07:45 | aviso diario por mail | Apps Script, `instalarAvisoDiario` |

- Aviso: `aviso_diario.gs → DESTINATARIOS` tiene **4 casillas** (la de la empresa + 3 personas de
  NAVAR, pedido de Thomas 29/09). Para sumar/quitar, se edita esa línea (repo + Apps Script); no hace
  falta reinstalar el disparador.
- Zona horaria del proyecto de Apps Script: Buenos Aires (verificado 29/09).
- **Cómo se actualiza el código de Apps Script sin errores** (29/09): comparar primero el editor con la
  versión anterior del repo (hash), traer la nueva desde GitHub por commit, reemplazar el contenido
  del modelo de ese archivo (`monaco.editor.getModels()` → el que corresponde → `pushEditOperations`;
  no hace falta abrirlo en pantalla, que con clics automatizados cambia de archivo con retraso),
  guardar (Cmd+S), **recargar y volver a comparar**. Las funciones de
  instalación se corren **desde el menú finauto de la Sheet**, no desde el selector del editor: el
  selector, automatizado, corrió otra función (una vez `onOpen`, otra casi `avisoDiario`, que manda
  el mail). Confirmar siempre en Ejecuciones qué corrió.
- Los `.gs` al día siguen en `NAVAR - Datos/Scripts/` (`*.gs.txt`).

**01/10/2026 — extractos que llegan y no se leen.** Banco de Corrientes mandó el resumen en otro formato
("RESUMEN A PEDIDO") y el lector lo salteó en silencio; el mail decía "subir a mano". Arreglado: el
lector lee los dos formatos (tarea 38) y el mail ahora dice **"llegó «archivo» pero no se pudo leer
(motivo) · avisar a finauto"** para cualquier banco (tarea 39). Si aparece esa línea, el archivo está
en Drive: hay que enseñarle al lector el formato, no volver a subirlo.

**Bancos:**
- **Galicia**: automático y cerrado (ver abajo, 28/09).
- **Macro**: **bloqueado** (28/09) y **con claves expuestas**. En un diagnóstico, las claves se
  tipearon en la consola y quedaron unos 15 min como nombres de archivo en Drive; se borraron. Falta:
  que el administrador de banca empresas de NAVAR desbloquee el usuario y **cambiar la clave personal
  y la clave empresa**. Después: diagnóstico corregido (**solo Enter, nunca texto**), consigna,
  claves nuevas en la notebook (Macro pide 3 datos: usuario, clave y clave empresa). El recorrido a
  mano y el export ya se vieron: `macro.com.ar/biempresas` → usuario → clave → clave empresa →
  "CUENTA CORRIENTE BANCARIA" → al pie, **XLS** de "Descargar listado completo" (no el del inicio, que
  baja la lista de cuentas). El export trae ~30 días y el número de cuenta adentro.
- **BBVA**: el login entra y vuelve al inicio en un loop. Espera **usuario de consulta propio**.
- **Nación / Corrientes**: sin bot. Nación: tarea 21 (cuenta con 13 o 14 dígitos) sigue pendiente.
- Decidido: **usuarios de consulta propios por banco** (checklist 1.3b). NAVAR ofreció crearlos.

**Hecho 29/09:** el mail diario ya es una checklist (tareas 32 y 33, instaladas y probadas con datos
reales).

**Principales 20 + último pago (29/09, pedido de NAVAR para el plan de regularización de Tango):**
- **Solapa "Principales 20"** en la Sheet (armada a mano, fórmulas): los 20 clientes que más deben y
  los 20 proveedores a los que más se les debe, **A y AA por separado** (4 bloques: A arriba, AA abajo;
  clientes a la izquierda, proveedores a la derecha). Por cada uno: saldo, vencido, a vencer,
  vencimiento impago más viejo y **último pago registrado**. Una fórmula `LET/MAP` por bloque sobre
  Cuentas a Cobrar (B cliente, C empresa, F vto, J saldo) y Cuentas a Pagar (B, C, G vto, K saldo): si
  se insertan columnas en esas listas, la solapa se rompe. **No insertar filas en la solapa**: el
  29/09 alguien insertó una arriba del bloque AA y desalineó las fórmulas (corregido).
- **Último pago**: tareas 34 y 36. La bajada de Tango trae ahora **9 fotos** (se sumó la tesorería de
  A: consulta **19** de Live, "Finauto A tesorería", últimos 400 días, carpeta `Tesoreria A`; **no**
  entra al Cash, que para A sale de los extractos). `lector/ultimos_pagos.py` arma la lista
  **"Ultimos Pagos"** (una fila por empresa + tipo + razón social; ~1150 filas; la solapa tiene 1999:
  el importador no agrega filas). En la API, `Cód. relacionado` trae `C`/`P` y el código real va
  adelante de la descripción (`900001 - ...`): de eso se ocupó la 36. Validado 29/09: 80 de 80 contra
  la lista y la lista contra el Excel crudo. "Sin pagos en el último año" (A) / "sin pagos registrados"
  (AA) = ningún recibo/OP en la ventana, **según Tango**.
- El mail diario cuenta 9 bajadas (`TANGO_BAJADAS` en `aviso_diario.gs`, tiene que coincidir con
  `TOTAL_BAJADAS_DIARIAS` de `tango_live.py`). Apps Script actualizado el 29/09 (importador y aviso,
  hash igual a `main`) y copia en `NAVAR - Datos/Scripts/`.
- **Resumen semanal por mail** (tarea 37, instalado 01/10/2026): `resumen_semanal.gs` guarda cada
  lunes una foto de los 80 en la lista **"Principales 20 · historial"** y manda a `DESTINATARIOS` un
  mail que compara con la foto anterior (totales y vencido con diferencia, los que más bajaron/subieron,
  entraron/salieron, sin pagos) con la solapa en PDF. Disparador: lunes 08:00–08:30. Calcula desde las
  listas por encabezado (no lee la solapa). Foto inicial: 01/10 (con los datos de la bajada del 30/09),
  así el lunes 05/10 ya compara. Necesitó un permiso nuevo de Google ("conectarse a un servicio
  externo", para el PDF), aceptado por Thomas el 01/10. Menú: "Ver el resumen semanal (sin mandar)",
  "Guardar foto semanal ahora", "Instalar resumen semanal". **Primer envío real: lunes 05/10, mirar
  que haya llegado y el PDF adjunto.**
- **PDF para mandar por mail**: `herramientas/principales20_pdf.py` (lee el export de la Sheet, 3
  páginas). El del 28/09 no tiene la columna de último pago.

**Pendiente, en orden:** método fijo por banco
(checklist, diagnóstico único en el repo y ayudas comunes) antes de Macro, **esperando OK de Thomas** ·
Macro (desbloqueo + claves nuevas) · BBVA (usuario propio) · `_SALDOS_` de Galicia a la Sheet · probar
el modo invisible de Galicia · tarea 21 (Nación). (La 20 dice "falta pegar el .gs" en su estado, pero se instaló y probó el
25/09: el `importar_cashflow.gs` que había en Apps Script el 29/09 era idéntico al del repo con la 20.)

## Dónde estamos (28/09/2026) — Galicia baja solo

**El bot de Galicia anduvo de punta a punta el 28/09 a las 00:27** en la notebook (`--modo prueba`):
login directo, empresa, cuenta 0005459-5 070-1, saldos Actual y Disponible, descarga Excel,
validación y publicación en `Bancos/galicia`. El Excel publicado (110 movimientos, 28/08–22/09)
coincide uno por uno con un export a mano, y el saldo final coincide con la pantalla.

- Recorrido (tareas 23 a 25): `empresas.bancogalicia.com.ar/login` → tarjeta de la cuenta en el inicio
  → tarjeta Saldos → flechita al lado de "Filtros" → **Excel**. Trae los **últimos 30 días**; no se usa
  el filtro de fechas. El lector descarta los repetidos entre archivos.
- La cuenta se confirma en pantalla y por el nombre del archivo del banco (`Extracto_CC545950701.xlsx`):
  el contenido no trae el número.
- Saldos en `Bancos/galicia/_SALDOS_Galicia_<dd-mm>.json` (actual y disponible; el acuerdo de
  descubierto es disponible − actual). **La Sheet todavía no los lee**: el acordado del Cash sigue
  saliendo del mapa de deuda.
- Lecciones de la página (para Macro/BBVA): las etiquetas del formulario tienen su propio `aria-label`
  (buscar campos por `id`); hay modales escondidos que Playwright da como "visibles"; los botones
  de ícono no tienen nombre útil (se ubican por posición relativa, clic sobre el elemento). Cuando
  algo falla, un script de diagnóstico que **solo lista** lo que ve ahorra vueltas.
- Credenciales: llavero de la notebook, `finauto:navar:galicia` (usuario de consulta, sin segundo factor).

**Galicia cerrado el 29/09/2026 00:54**: cinco corridas seguidas de la tarea programada con OK,
una en frío. El rescate de la tarea 29 se probó en real a las 00:50: la página se cerró al guardar
y el bot tomó el `.tmp` de `C:\Users\USer\Downloads`. Historia de la falla intermitente de la
descarga en las tareas 27 a 29.
- Horario: tarea `finauto NAVAR Galicia` con dos disparadores (el segundo, 3 minutos después, de
  seguro). Pedido del cliente: que todo corra a las **05:45** para tener el cash actualizado a las 7.
  Los instaladores del repo todavía tienen los horarios viejos (07:00 Galicia, 07:30 Tango).
- Pendiente: probar el modo invisible · conectar `_SALDOS_` a la Sheet · pasar los horarios nuevos
  a los instaladores y sumar a la Sheet una importación diaria entre las 6 y las 7.

## Dónde estábamos (25/09/2026) — Tango llega solo, por API

**Tango ya no se exporta a mano.** (Desde el 29/09 la bajada es a las 05:45 y reintenta sola a las 06:15, 06:45, 07:15, 09:00 y 12:00 si no bajó 8 de 8; tarea 35. El 29/09 falló a las 05:45 porque el servidor de Tango no estaba en la red.) Recorrido de cada mañana: 07:30 la tarea "finauto NAVAR Tango"
de la notebook corre `ingestas/tango_live.py`, que deja 8 Excel en Drive con el mismo formato que
los exports a mano (4 de A y 4 de AA). Después el vigilante corre los lectores (cada 15 min) y el
disparador de la Sheet importa (cada hora). Primera corrida real el 25/09: Registro ok con 374
cobranzas, 535 pagos y 77 cheques, y tesorería AA con 761 movimientos. Los números coinciden con los
exports a mano del 23/09 en todo lo que no cambió en dos días. Log de la bajada:
`C:\finauto\clientes\navar\privado\tango_live.log`.

- **Token** en el llavero de la notebook (`finauto:navar:tango_live`, usuario de Tango
  finanzasnavar@gmail.com). Se guarda **desde el portapapeles** (comando en `instalar_notebook.md`
  §5): pegar en la pantalla de clave oculta por escritorio remoto guardó basura tres veces.
- **Consultas personalizadas de Live ("Finauto ...", en Mis consultas): NO BORRARLAS NI
  EDITARLAS.** La bajada depende de ellas (`perfil.json → tango_live.consultas_personalizadas`).
  A: cobranzas 10 · pagos 11 · cheques terceros 18 (filtro En Cartera) · cheques propios 13 (Al
  Cobro + Diferido). AA: cobranzas 14 · pagos 15 · cheques terceros 16 (En Cartera) · tesorería 17.
  Si alguien les cambia columnas, el lector deja de encontrarlas. La API las pide por número:
  guardar una "nueva" cambia el número.
- **Cheques propios**: Tango nunca los marca como debitados ("Al Cobro" junta todo desde 1995). La
  bajada pide solo fecha del cheque desde hoy − 60 días (`dias_atras`).
- **Hallazgo 25/09**: con la API entran 19 cheques propios por $210,4 M (todos a Envasando SRL),
  contra 9 por $85,9 M del export a mano. Los 10 de más tienen fecha en 2027, y el filtro "año
  actual" del export a mano los dejaba afuera. **Confirmado con NAVAR el 25/09: son reales.**
- **Hallazgo 25/09**: con los exports a mano, "Nro Cheque" de terceros de A mostraba el CUIT del
  cheque (esa columna no venía). Con la API es el número real. Eso destapó que el importador
  frenaba con números como texto: arreglo manual (columna D de Cartera de Cheques en "Texto sin
  formato") y arreglo de fondo en la tarea 20.
- Estado `X` en cheques de terceros de A (107, históricos): no se sabe qué es; queda afuera.
- Plan B si la API falla: exportar a mano como antes y dejar el Excel en la misma carpeta de Drive.

**Pendiente de Tango**: certificar la tarea de las 07:30 (mirar el log del 26/09).

**Importador de la Sheet (25/09, tareas 20 y 22, pegadas en Apps Script y probadas):** los números de
comprobante, cuenta y referencia se guardan como texto (la columna D de Cartera de Cheques ya no
necesita formato manual). Las fechas se importan a las 00:00 de la zona de la Sheet. **La Sheet
queda en hora de Buenos Aires.** Antes, al cambiarla, las fechas caían a las 04:00 y la columna de
hoy del Cash quedaba vacía. Reimportado el 25/09 a las 19:00: Tango 374/535/77, Bancos 251/2.462,
Tesorería AA 761. Ojo: al arreglarse las fechas, la caja de AA se corrió un día respecto de lo que
se veía antes, cuando estaba un día antes de lo real. Lo correcto es lo de ahora.
**Macro al 25/09: −$49,8 M con acuerdo de ~$50 M → margen $0,16 M.** Hecho el 25/09: consulta vieja 12 borrada en Live, zona horaria de la Sheet en
Buenos Aires. Token: Thomas decidió no regenerarlo (quedó escrito en un chat de trabajo).

## Dónde estamos (24/09/2026, madrugada) — listo para automatizar

El circuito quedó andando de punta a punta y con los frenos puestos. Lo hecho el 23-24/09:

- **Cash**: una fila por banco con el **margen** (saldo + descubierto acordado) y semáforo:
  negro = no toca el descubierto · ámbar = lo usa dentro del acuerdo (hoy Galicia y Macro) ·
  rojo = excedido (Corrientes y Nación). El color va en el **formato condicional escrito con el
  separador de la planilla** (`;`): con `,` las reglas son inválidas y no pintan. Ese fue el bug.
- **Hoy existe**: cada origen corre hasta SU fecha (`$B$3` extracto bancario, `$B$5` caja de AA),
  así lo real de AA del día suma aunque el banco venga atrasado. Los bancos arrastran el último
  saldo conocido hasta hoy, sin filas de texto.
- **Caja AA calculada**: último arqueo + movimientos de tesorería posteriores. Igual en la
  planilla y en el tablero (27.675.788 al 23/09).
- **Lectores tolerantes**: un archivo ilegible ya no tumba la corrida de los cinco bancos
  (lo que pasó con el BBVA del 23/09, que cambió `Detalle` por `Saldo Parcial`).
- **Importador a prueba de filtros**, con verificación de lo escrito. **Requiere el servicio
  "Google Sheets API" habilitado en el proyecto de Apps Script** (Servicios → +): sin eso aborta
  toda importación. Ya está habilitado.
- **Aviso diario instalado**, 09:00 de Buenos Aires, a la casilla de la empresa.
- Los `.gs` al día viven en Drive `NAVAR - Datos/Scripts/`. **Pegarlos desde ahí**: el editor de
  Apps Script no guarda de forma confiable cuando se automatiza el pegado.

### Lo que sigue (las automatizaciones)
1. ~~**Tango por API**~~ ✅ 25/09 (ver arriba).
2. **Bots de banco**: esperan el operador de consulta de cada banco.
3. **El tablero web nunca se implementó**: `tablero_web.gs` (Código.gs) está pegado pero sin
   deployment, así que no hay URL para compartir. PERMITIDOS ya tiene los mails de NAVAR.
4. **Agujero conocido**: las cuotas bancarias no se dan de baja solas. Proveedores, impuestos y
   cheques sí (cada export de Tango es la foto de lo pendiente: lo pagado deja de venir). Las
   cuotas salen del mapa de deuda, que se actualiza a mano. Cerrarlo cruzando el débito del
   extracto contra el cronograma.
5. **Pregunta abierta al banco**: el export de BBVA del 23/09 trae dos saldos que no coinciden
   (−8.040.751 en "Saldo Parcial" y −3.502.551 en el encabezado). El lector lo marca REVISAR.

## Próximos pasos (al 22/09/2026, 3 a.m.) — para retomar en un chat nuevo

0. **(22/09, de noche)** Hoy no llegó nada nuevo a Drive: el 23/09 Thomas pide los extractos de los 5 bancos (18/09 → hoy) y baja de nuevo los exports de Tango; recién ahí corre el circuito y se regenera el PDF. Detalle visto: las horas de la solapa **Registro** están 4 hs atrás (la Sheet quedó en zona horaria del Pacífico); se arregla en la Sheet: Archivo → Configuración → Zona horaria → Buenos Aires. El informe (`informe_situacion.py`) ya sale sin nombres propios. Hay un `AGENTS.md` en la raíz para que Codex u otro agente lea las mismas reglas.
1. **Extractos de banco del 18/09 en adelante** → `NAVAR - Datos/Bancos/<banco>/` (Thomas los baja hoy). El vigilante en la notebook y el disparador de la Sheet hacen el resto; verificar en la solapa Registro y regenerar el PDF (`herramientas/informe_situacion.py`, bajando antes la Sheet como Excel a `privado/`).
2. **Tango por API**: cuando Miriam (soporte Tango) habilite el usuario `finauto`, seguir `documentos/instalar_notebook.md` §5 (token al llavero, `ingestas/tango_live.py --probar cobranzas`, ajustar el parser al JSON real). Los 5 procesos y las 2 empresas ya están en `perfil.json`.
3. **Bots de banco**: esperan el operador de consulta de cada banco (Priscilla, cuando MR esté en Corrientes). Orden Galicia → Macro → BBVA → Nación → Corrientes; guía §6.
4. **Preguntas abiertas a la empresa**: qué son las salidas de caja de AA "débito y gastos bancarios" ($58 M en junio); confirmar la regla de débito automático (`catalogo.json → debito_automatico`); plan de compra de canchada 2027; tesorería AA: cheques endosados.
5. Pendientes chicos: aviso diario por mail (qué llegó / qué falló); cruce banco ↔ Tango de endosos (`lector/cruce.py`); mudar el tablero web a los mismos bloques.
6. Regla de trabajo (memoria `feedback-pasada-de-errores-completa`): una pasada de errores = recomputar cada total desde las listas y compararlo con la celda; decir qué se verificó y qué no.

## Dónde estamos (20/09/2026)

**Leer primero `documentos/manual_cash.md`**: qué es cada solapa, cómo se lee, qué es real y
qué estimado, cómo impacta cada movimiento y cómo se actualiza. Lo mismo, en tablas, está en
la solapa Instrucciones de la Sheet.

- ✅ **Cash v5 (22/09)**: pantalla calcada de un cash a mano: Saldo inicial → ingresos → egresos → Resultado de la operación → Deuda que sale sí o sí (débito automático) → SALDO AL CIERRE escenario 1 → Deuda por decisión → SALDO AL CIERRE escenario 2 → Deuda pospuesta acumulada → Venció y no se pagó / Resultado pagando lo que vencía → Descubierto acordado/usado/disponible (banco por banco) → Saldo disponible × 2 → Atrasado (stock). Columna `Debito Automatico` en Deuda Bancaria / Deuda Impositiva / Plan (col N). Préstamos fuera de la operación. Instrucciones y manual sin nombres propios.
- ✅ **Cash v4 en la Sheet** (`herramientas/crear_cash.gs`, corrido el 20/09 desde finauto → Armar solapa Cash): **Cash** (7 días de extracto + 28 adelante), **Cash Semanal** (lunes a domingo: 4 + actual + 12), **Cash Mensual** (3 + actual + 6, inflación en B4), **Plan** (una fila por deuda con decisión, con la propuesta cargada) e **Instrucciones**. Un renglón por concepto: real hasta el último extracto (17/09), estimado desde el día siguiente. Sin columna "Fuente"; ceros en blanco; filas "Resultado de la operación" (~$100–150 M/mes) y "Resultado después de la deuda". Semanal y diario usan el cronograma tal cual; **el mensual usa lo decidido en Plan** (columnas O..U).
- ✅ **Scripts en Apps Script** (proyecto "NAVAR SA": `Código.gs` = tablero web, `Importar_cashflow.gs`, `Crear_Cashflow.gs`), pegados y corridos por Claude desde Chrome. Copias en Drive `NAVAR - Datos/Scripts/`. Las columnas de las listas se resuelven por encabezado (`_rangos_`): agregar una columna a mano (Thomas sumó "Año" en Cuentas a Cobrar) ya no corre las fórmulas. Las fórmulas se escriben con `,` y el script las reescribe con `;` si la planilla (es_AR) las rechaza.
- ✅ **Errores corregidos 19–20/09** (detalle en `manual_cash.md` §7): separador `;`; Excel del home banking en orden inverso (Macro 15/09 daba +$71 M); filas migradas "Manual/Real" sumadas al extracto (julio $1.225 M en vez de $757 M); semanas partidas en hoy; signo de los intereses estimados; AA estimada faltaba en el mensual.
- ✅ **Informe** `privado/salidas/NAVAR - Situación y plan 2026-09-19.pdf` (`herramientas/informe_situacion.py`): sin plan −$348 M en marzo; con la propuesta +$145 M. Prioridades de pago y preguntas para Priscilla.
- ⬜ **Pendiente de Thomas**: borrar las solapas viejas "Semanal" y "Mensual" (las nuevas son "Cash Semanal" / "Cash Mensual"); no agregar columnas a mano en las listas (Importar Tango las pisa); cargar la caja AA a mano en Saldos Bancarios ("(varios)"); revisar/decidir en Plan con Priscilla.
- ✅ **Actualización automática**: la Sheet tiene un disparador horario (`importarLoNuevo`: importa solo lo nuevo de Drive, anota en la solapa Registro) y el **vigilante** (`herramientas/vigilante.py`) mira `NAVAR - Datos/{Bancos/<banco>, Cuentas a cobrar, Cuentas a pagar, Cheques, Deuda bancaria, Impuestos}` y corre el lector que corresponde (control: si una solapa pierde más de la mitad de las filas, retiene y no publica). **Desde el 22/09 corre en la notebook de NAVAR** (`C:\finauto`, tarea programada cada 15 min, `instalar_vigilante.ps1`; el de la Mac se desinstaló). Actualizar el código allá: `actualizar.ps1`. Guía: `documentos/instalar_notebook.md`. Log: `clientes\navar\privado\vigilante.log` en la notebook.
- ✅ **Informe v2** (`herramientas/informe_situacion.py`): lee el export de la Sheet; tres escenarios (A sin tocar nada −$501 M, B plan propuesto −$168 M, C lo que haría falta +$115 M en marzo); banco por banco con "si dicen que no". Se regenera bajando la Sheet como Excel a `privado/`.
- ⬜ **Falta**: costo de cosecha (no está en ninguna lista); cruce banco ↔ Tango (`lector/cruce.py`); tablero web con los mismos bloques; bots de banco + token de Tango Live (dependen de NAVAR).

## Dónde estábamos (18/09/2026)

- ✅ **Primera conexión a la notebook de NAVAR hecha (16/09 a la noche).** Tango es **Delta 5 (25.01.000.4297)**, corre en el navegador contra `servidor:17000` (hay un servidor aparte en la red; la notebook es un cliente). Dos empresas: **NAVAR SA** (id 13, la asumimos "A") y **NAVAR SA Otros** ("AA"). Se entró con la cuenta nexo de Priscilla (autorizado por WhatsApp); el usuario propio de consulta sigue pendiente.
- ✅ **Exports de Tango Live bajados** (15 archivos + SQL de cada consulta): cobranzas, pagos, cheques de terceros, cheques propios (solo A), saldos, movimientos, ventas. En `privado/tango/2026-09-16/` y en Drive `NAVAR - Datos/Tango`. Cuenta de Google de la empresa: `finanzasnavar@gmail.com` (creada por Thomas; falta pasar la clave a Priscilla).
- ✅ **`lector/tango.py` escrito y corrido**: arma Cuentas a Cobrar / a Pagar / Cartera de Cheques con nombre. Deja `para_pegar_en_la_sheet_<fecha>.xlsx`, `resumen_tango_<fecha>.md` y una copia de la Sheet con las filas. Reglas: residuos ≤ $1 afuera; vencido antes de 2026 y cheques con fecha pasada → marcados **`REVISAR:`** (no suman al tablero, salen en Hallazgos).
- ✅ **Tablero corrido con datos de Tango** (`privado/salidas/finauto.html`, capturas `tango_*.png`). ⚠️ **Números sin validar**: vencido con proveedores pasa de $206 M a **$432 M**. Ningún número sale a NAVAR sin que Karina lo confirme.
- ✅ `herramientas/importar_cashflow.gs`: Apps Script con tres botones en el menú "finauto" de la Sheet: **Importar Tango** (cobrar/pagar/cheques), **Importar Bancos** (saldos/movimientos), **Importar Deuda** (deuda bancaria). Cada uno busca el `para_pegar_*` más nuevo en `NAVAR - Datos` y pisa lo que ese mismo lector cargó antes (respeta fórmulas y lo cargado a mano). Thomas instaló la versión "Tango" el 17/09; **hay que pegar esta versión encima**.
- ⏳ Hallazgos grandes para la reunión con Karina: Tango **no se concilia** (CAJA CONTADO -$497 M; cheques propios "Al Cobro" desde 1995; $5.700 M de cheques históricos sin marcar); deuda vieja a cobrar $55 M / a pagar $187 M desde 2007; 88 proveedores con saldo. Ver `privado/tango/2026-09-16/resumen_tango_2026-09-16.md`.
- ⏳ Automatización de Tango: Live expone una **API** (`GET Api/GetApiLiveQueryData/{process}/...`, headers `ApiAuthorization` + `Company: 13`; cobranzas = proceso 17952) y "Mis suscripciones" por mail. Con un token de un usuario propio, la ingesta diaria sale sin usuario SQL ni scraping.
- ⬜ Pendiente de Thomas: factura del 50 %, WhatsApp a Priscilla (CUIT, stock, margen) y al contador (ARCA), pegar/importar Tango en la Sheet, validar con Karina, rediseño visual del tablero (dirección elegida: barra lateral oscura + números serif, ver `scratchpad/estilos/D_final`).
- ✅ **Extractos de los 5 bancos leídos** (`privado/bancos/{bbva,galicia,macro,corrientes,nacion}/`, `lector/extractos.py`): **2.375 movimientos** reales jun→sep clasificados, saldo real por cuenta y día. **Posición en cuentas corrientes al 15-17/09: -$189,5 M** (BBVA +$6,4 M · Galicia -$9,1 M · Macro -$39,7 M · Corrientes -$45,3 M · Nación -$101,7 M). Viven de descubiertos y de descontar cheques (Galicia $356 M en 3 meses). Sueldos ~$100 M/mes por Macro. CUIT **30-55852502-5**. El Nación llegó el 18/09 **escaneado** (imagen): se lee con OCR de macOS (`lector/herramientas/ocr_mac.swift`) y se controla con la cadena de saldos; las transferencias entre bancos cruzan al peso con los otros extractos. El 14/09 el Nación pagó la tarjeta AgroNación ($82,8 M) y una cuota impaga ($17,5 M) con un descubierto nuevo de $100 M: por eso está en -$101,7 M.
- ✅ **Mapa de deuda bancaria cargado** (`privado/bancos/Bancos_Navar.xlsx` → `lector/deuda_bancaria.py` → solapa Deuda Bancaria, líneas + cronograma). **Deuda total con bancos: $2.653 M** (Corrientes $1.073 M · Nación $673 M · Macro $361 M · BBVA $309 M · Galicia $237 M), de los cuales ~$196 M son descubiertos usados (ya están en la caja). **Cuotas vencidas e impagas: $362 M** (Corrientes: 4 préstamos con 3-4 cuotas impagas c/u, situación BCRA 3, 92 días; BBVA cuota del 11/09). Vencen en 30 días: $160 M; en 90: $469 M. Margen libre de descubierto: **$11 M** (Macro $10,3 M + Galicia $0,9 M; Nación excedido, Corrientes sin acuerdo informado). Faltan: hipoteca "La Gloria" y tarjeta corporativa Nación (sin importe), venta de valores Macro ($270 M acordado, sin saldo), cuota real de Galicia (estimada $23,5 M), y los $260 M de "operaciones diferidas" de la AgroNación (Envasando SRL $245 M) que el mapa no suma.
- ✅ **BCRA consultado** (`privado/bcra/`): deuda bancaria total **$3.486 M** (jul-26), situación 2 en Nación (refinanciado, 18 días) y Corrientes; 1 en BBVA, Galicia, Macro. 24 meses de historia guardados.
- ✅ **Deuda impositiva cargada** (`privado/impuestos/Control Vencimiento Impuestos.xlsx`, la planilla de Celia revisada por el contador el 18/09 → `lector/deuda_impositiva.py` → solapa Deuda Impositiva): **$604,7 M pendientes, $547,6 M vencidos** (SICORE 2024 $315 M, tasa de comercio $110 M, planes ARCA $67 M...). Urgente antes del 25-26/09: $49,7 M (mail de Celia). Los planes que propone el contador (SICORE: contado $13,3 M + 9 × $32,2 M) van como nota, no como cuotas, hasta que se firmen. Vencido total como stock: **$1.344 M** (proveedores 435 · bancos 362 · impuestos 548).
- ✅ **Tesorería de Tango jun→hoy** (`privado/tango/2026-09-18/A tesoreria detalle jun-hoy.xlsx`, 3.927 renglones): trae CUIT de clientes y proveedores, la cuenta por la que entró/salió cada peso, recibos y órdenes de pago con importe. Es la base del cruce banco ↔ Tango (pendiente de escribir: `lector/cruce.py`). Recibos de A: $679 / 750 / 542 / 420 M por mes (jun→sep), 3× lo que entra al banco como cobranza: la diferencia son cheques descontados o endosados.
- ✅ **Diseño del cash nuevo** (`documentos/cash_v2_diseno.md`, mock `privado/salidas/cash_v2_mock.png`) y `herramientas/crear_cash.gs`: arma las solapas **Cash** (día por día: 7 atrás real, 28 adelante) y **Cash Semanal** (4 atrás, 12 adelante, como el cash viejo) con fórmulas sobre las listas. Bloques: bancos (saldo · acuerdo · disponible) · ingresos · egresos · saldo y disponible al cierre · atrasado (stock).
- ✅ **Respuestas de Priscilla (18/09)** aplicadas: los $570 M del Macro sin descripción son **venta de valores** (descuento de cheques) → categoría nueva "Descuento de Cheques" (es cobranza en cheque adelantada, no préstamo); "N/C DEUD. PUBLICA" = transferencias de clientes → Cobranza; BBVA $15,5 M pendientes = la cuota impaga colgada; AgroNación $260 M diferidos = pagos a proveedores con tarjeta que entran en próximos resúmenes → 3 resúmenes estimados en el cronograma; Corrientes: refinanciación en curso; **AA opera en efectivo, sin bancos** (Tango registra, la caja es física: se carga a mano); cheques: casi siempre se descuentan, a veces se endosan (endoso = O/P, descuento = boleta de depósito en Tango); la "cobranza proyectada" del cash viejo era una estimación por kg que nunca se cumplía (se borra); sueldos del 1 al 10, horas extras en AA; cobranzas las carga Karina cuando entra la plata, O/P Milagros cuando se paga.
- ✅ **Cash Mensual** (3 meses reales + 6 proyectados, inflación editable 1,7 %/mes) en `crear_cash.gs`, mock `privado/salidas/cash_mensual_mock.png`: ingresos operativos ~$510–555 M/mes contra egresos ~$525–665 M/mes → saldo en bancos de -$150 M a **-$508 M en marzo** si no se refinancia nada; disponible negativo desde septiembre.
- ✅ (19/09) Archivos subidos a Drive, scripts pegados, botones corridos; las preguntas a Priscilla contestadas.

**Decisiones que no hay que re-litigar:** no hay servidor pago; la notebook de NAVAR es el
"servidor" (bots, Tango, finauto, Drive para escritorio) y Apps Script sirve el tablero.
Las claves de banco las carga alguien de NAVAR en esa máquina; Thomas no las ve.

## Dónde estábamos (12/09/2026)

1. ✅ Descubrimiento y diagnóstico del cash viejo (`privado/diagnostico_2026-09-12.md`): 10 errores de fórmula, ±49% de error en la proyección de ingresos.
2. ✅ Cash nuevo (Cowork + `arreglar_cash_v2.py`), en Google Sheets, con las 6 semanas reales, 8 proyectadas y los stocks de deuda al 31/08.
3. ✅ `lector/cash_limpio.py` → contrato → `finauto.py` → tablero con los números de NAVAR. Lo vencido entra a la curva el día 1.
4. ✅ PDF de propuesta para la dueña (`privado/salidas/NAVAR - Propuesta finauto 2026-09-12.pdf`). **Pendiente que Thomas valide los números antes de mandarlo.**
5. ⬜ Presentación del proyecto (lunes 14/09 o después). Recién ahí: propiedad de la Sheet a NAVAR, permisos, exports de Tango, reunión con quien carga (10 preguntas).
6. ⬜ Fase 2: Tango automático; fase 3: bancos en una máquina del cliente.

## Cómo se corre (cuando haya contrato)

```bash
source .venv/bin/activate
python finauto.py --contrato clientes/navar/contrato_<fecha>.json --cliente navar
```

## Archivos de trabajo

| Archivo | Qué es |
|---|---|
| `documentos/CHECKLIST_IMPLEMENTACION.md` | El paso a paso de la semana de implementación (16–22/09), con qué/cómo/para qué y columna de tiempos. Se convierte en el checklist de onboarding del cliente 2. |
| `documentos/ARREGLOS_ESQUELETO.md` | Los 8 arreglos al esqueleto del cash nuevo, con celda y fórmula. Para pasarle a quien lo edite. |
| `herramientas/migrar_cash_viejo.py` | Convierte el cash viejo (6 semanas reales + 8 proyectadas) en filas para pegar en el esqueleto nuevo. Deja `privado/datos_migrados_del_cash_viejo.xlsx`. Se corre con `python clientes/navar/herramientas/migrar_cash_viejo.py`. |
| `herramientas/propuesta.py` | Genera el PDF para la dueña con los números del contrato y las capturas de `privado/capturas/`. |
| `herramientas/importar_cashflow.gs` | Apps Script: menú finauto → Importar Tango / Bancos / Deuda / Impuestos + Armar solapa Cash / Plan. Cada botón busca el `para_pegar_*` más nuevo en Drive y pisa lo que ese mismo lector cargó antes. |
| `herramientas/aviso_diario.gs` | Apps Script: aviso por mail cerca de las 07:30 de Buenos Aires con llegadas, procesos, importaciones y alertas; permite probar sin mandar e instalar o quitar el aviso. |
| `herramientas/crear_cash.gs` | Apps Script: arma Cash, Cash Semanal, Cash Mensual, Plan e Instrucciones con fórmulas sobre las listas. Se corre después de cambiar la estructura; Plan no se pisa salvo con "Armar solapa Plan". |
| `documentos/manual_cash.md` | El manual del cash: solapas, lectura, real/estimado, impacto de cada movimiento, rutina de actualización, errores corregidos. |
| `herramientas/informe_situacion.py` | El PDF "Situación y plan" (proyección sin plan / con plan, prioridades, preguntas). |
| `herramientas/importar_tango.gs` | Apps Script para la Sheet: menú "finauto → Importar Tango". Busca en Drive el último `para_pegar_en_la_sheet_*.xlsx`, borra las filas de Tango anteriores y las "agregado", pega las nuevas sin tocar las fórmulas. |
| `herramientas/tablero_web.gs` | El Apps Script que sirve el tablero en una URL privada de Google (lee `NAVAR - Datos/Tablero/finauto.html` de Drive, lista de mails permitidos, banda si tiene más de 48 hs). Se pega en la Sheet → Extensiones → Apps Script. |
| `herramientas/arreglar_cash_v2.py` | Toma el cash que devolvió Cowork (`privado/NAVAR_-_Cash_Flow_Limpio.xlsx`), regenera el consolidado con semanas lunes-domingo, vacía los ejemplos y mueve los proyectados a las listas. Deja **`privado/NAVAR - Cash Flow Limpio v2.xlsx`, que es la versión buena**. |

## El cash nuevo (el entregable)

`privado/NAVAR - Cash Flow Limpio v2.xlsx`. Verificado el 12/09 recalculándolo
completo: coincide al peso con las 8 semanas proyectadas del cash viejo. Tres
cosas para saber al mirarlo:
- El horizonte arranca el lunes 31/08. Como es fin de mes, "Sem 1 Ago 26" tiene
  un solo día (el 31/08) y ahí cae toda la primera semana migrada. Es normal:
  los datos migrados son agregados semanales fechados en el lunes.
- El bloque "Vencido a la fecha" muestra ~$109M "vencido a cobrar": son las
  cobranzas proyectadas para el 31/08 y el 07/09, que ya pasaron. Desaparece
  cuando carguen lo real de esas semanas.
- Los $124M de cheques en cartera entran como cobro el 31/08 porque el cash
  viejo no tenía fecha de cobro por cheque. Se corrige con el detalle de Tango.
