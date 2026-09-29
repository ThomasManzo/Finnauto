# Tarea 34 — Último cobro de cada cliente y último pago a cada proveedor
Estado: lista para revisión
Rama: tarea/ultimos-pagos

## Objetivo

NAVAR pidió seguir día a día a sus **20 principales clientes** (los que más deben) y **20 principales
proveedores** (a los que más se les debe), cada uno con la **fecha de su último pago** registrado en
Tango. Sirve para ver dónde Tango está atrasado: un cliente que debe mucho y "no paga hace meses"
puede ser un cliente moroso o un recibo que nadie cargó.

Lo que deben y lo que se les debe **ya llega** a la Sheet todos los días (listas Cuentas a Cobrar y
Cuentas a Pagar). Lo que falta es la fecha del último pago. Esta tarea hace que llegue sola, cada
mañana, a una lista nueva de la Sheet, **"Ultimos Pagos"**: un renglón por cliente o proveedor de
cada empresa (A y AA) con la fecha y el comprobante de su último cobro o pago.

La pantalla con los rankings ("Principales 20") **no es parte de esta tarea**: la arma Claude en la
Sheet con fórmulas sobre las listas, como el resto de las pantallas.

## Contexto

- **De dónde sale el último pago**: de los movimientos de tesorería de Tango (Live → Tesorería →
  Comprobantes, proceso `11591`), un renglón por comprobante: recibos (`REC`), órdenes de pago
  (`O/P`, `OPF`), etc., con el cliente o proveedor en `Cód. relacionado` / `Desc. relacionado`.
  - **AA** ya baja todos los días (`consultas_personalizadas.AA.movimientos_tesoreria = 17`) a la
    carpeta `Tesoreria AA/` y lo lee `lector/tesoreria_aa.py` para la caja de AA.
  - **A** hoy **no baja**. Su historia completa son ~262 mil renglones desde 1995, así que se pide
    solo una ventana de fechas (último año y un poco más).
- **Consulta personalizada de A**: creada en Live el 29/09/2026 ("Finauto A tesorería", empresa
  NAVAR SA = Company 13, proceso 11591), con las mismas columnas que la 17 de AA: **`customQuery=19`**.
  Probada desde la notebook el 29/09 (llamada directa, sin tocar el perfil): devuelve `TIPO, ID_SBA04,
  COMPROBANTE, FECHA, FECHA_DE_EMISION, CONCEPTO, CLASE, TOTAL_CTE, COD_RELACIONADO, DESC_RELACIONADO,
  CLASIFICACION`. Sin fechas: 262.500 renglones (desde 1995). Con `fromDate=01/09/2026`: 340
  renglones, con `FECHA` desde el 01/09 → **`fromDate` filtra por `FECHA`**. ~340 por mes, así que
  400 días son ~4.500 renglones (una página de 5000).
- **Va después de la tarea 35** (`tareas/35-tango-reintenta-solo.md`, reintentos de la bajada con
  `--si-falta`), que toca los mismos archivos. **No arrancar hasta que la 35 esté mergeada en `main`**;
  la rama de esta tarea sale de ese `main`. La 35 decide "ya bajó completo" con `N de N` contra el
  total: al pasar de 8 a 9 bajadas, `--si-falta` tiene que seguir funcionando (un parte de hoy
  `8 de 9` **no** cuenta como completo).
- **Cuidado con las carpetas**: el vigilante corre `lector/tesoreria_aa.py` con el archivo más nuevo
  de `Tesoreria AA/`, y lo carga como **caja en efectivo de AA**. Si el archivo de A cae ahí, la
  plata de A aparece como caja de AA en el Cash. **El de A va a una carpeta propia, `Tesoreria A/`**, y
  nada que lea `Tesoreria AA/` tiene que verlo.
- Lo visto en el export a mano de A del 16/09 (no está en el worktree; no hace falta):
  - Clase `Cobros`: `REC` (recibos) y `FAC` (facturas contado: el cliente pagó en el momento).
    Clase `Pagos`: `O/P`, `OPF` (órdenes de pago), `FPR` (factura contado de proveedor).
    `REV` son anulaciones (importe negativo).
  - En el export a mano `Desc. relacionado` venía como `"038037 - ROSARIO MAYORISTA SRL"` (código y
    nombre juntos). Por API vienen `COD_RELACIONADO` y `DESC_RELACIONADO` separados, pero el lector
    tiene que aguantar las dos formas.
  - El importe de algunos recibos vino con cotización 25 y no está entendido: **esta tarea no usa
    importes**, solo fechas y comprobantes.
- En la Sheet, las listas Cuentas a Cobrar y Cuentas a Pagar identifican al cliente/proveedor por
  **razón social** (columnas `Cliente` / `Proveedor`) y por `Empresa` (A o AA), sin código. La
  pantalla va a cruzar por empresa + razón social, así que la razón social de "Ultimos Pagos" tiene
  que quedar **tal como la escribe Tango**, sin el código adelante y sin espacios de más en las
  puntas (los del medio se dejan: hay razones sociales con doble espacio y tienen que coincidir).
- Un mismo nombre puede tener dos códigos en Tango (pasa con un cliente de A). En "Ultimos Pagos"
  queda un renglón por **empresa + tipo + razón social**, con el último pago entre todos sus códigos.

## Archivos permitidos

- `ingestas/tango_live.py` y `ingestas/test_tango_live.py`
- `clientes/navar/perfil.json` (solo la sección `tango_live`)
- `lector/ultimos_pagos.py` (nuevo) y su prueba en `lector/pruebas/test_ultimos_pagos.py` (nueva)
- `clientes/navar/herramientas/vigilante.py`
- `clientes/navar/herramientas/importar_cashflow.gs` y una prueba nueva en `lector/pruebas/` si hace falta
  (hay ejemplos `probar_importador_*.cjs`)
- esta consigna (secciones "Qué hice" y `Estado:`)

**No tocar** `lector/tesoreria_aa.py` ni `clientes/navar/herramientas/aviso_diario.gs`.

## Resultado esperado

1. **Bajada de A** (`ingestas/tango_live.py` + `perfil.json`):
   - `movimientos_tesoreria` deja de ser solo de AA: también se baja de A, con su consulta
     personalizada (`consultas_personalizadas.A.movimientos_tesoreria`).
   - A se pide **desde hoy − 400 días** (configurable en `perfil.json`, en el mismo espíritu que
     `dias_atras.cheques_propios`). **AA sigue exactamente como hoy** (sin fechas: trae todo).
   - El archivo de A queda en `Tesoreria A/A movimientos tesoreria <fecha>.xlsx`. El de AA sigue en
     `Tesoreria AA/` como hoy (incluida la tolerancia a la carpeta con tilde).
   - Las bajadas diarias pasan de 8 a **9**, y el parte para el mail (`tango_ultima_bajada.txt`) dice
     "9 de 9". Actualizar `_ayuda` / `_movimientos_tesoreria` del perfil para que digan esto.
   - `--si-falta` (de la tarea 35) sigue andando con 9: parte de hoy `9 de 9` → no hace nada;
     `8 de 9` o un parte viejo `8 de 8` → baja.
2. **Lector nuevo** `lector/ultimos_pagos.py`:
   - Entrada: el archivo de A (`--a`) y el de AA (`--aa`), ambos obligatorios. Si falta uno, no
     escribe nada y termina con error (el importador pisa la lista entera: un archivo con una sola
     empresa borraría la otra).
   - Encabezados por nombre, no por posición. Aguanta `Total (cte)` o `Total (ext)`, y
     `Desc. relacionado` con o sin `"<código> - "` adelante.
   - Reglas:
     - **Cliente**: clase `Cobros`, tipo `REC` o `FAC`.
     - **Proveedor**: clase `Pagos`, tipo `O/P`, `OPF` o `FPR`.
     - Se ignoran: `REV` y cualquier renglón con importe negativo, renglones sin relacionado, y el
       relacionado NAVAR S.A. / `NAV007` en AA (es un pase interno, como en `tesoreria_aa.py`).
     - Por empresa + tipo + razón social: la **fecha más reciente** (`Fecha`, o `Fecha de emisión`
       si `Fecha` viene vacía) y el comprobante de ese día (si hay varios el mismo día, el de número
       más alto).
   - Salida: `para_pegar_ultimos_pagos_<hoy>.xlsx` con **una solapa "Ultimos Pagos"** y estas
     columnas, en este orden:
     `Empresa · Tipo · Codigo · Razon Social · Fecha Ultimo Pago · Comprobante · Origen`
     - `Tipo` es `Cliente` o `Proveedor`.
     - `Codigo`: los códigos de Tango de esa razón social, separados por ` / ` si son varios.
     - `Comprobante`: tipo y número, p. ej. `REC A0000000040563`.
     - `Origen`: `Tango tesorería · <nombre del archivo>` (es la marca que usa el importador).
   - También un `resumen_ultimos_pagos_<hoy>.md` corto: cuántos clientes y proveedores por empresa,
     rango de fechas de cada archivo, y cuántos renglones se ignoraron por cada motivo.
   - Mismo estilo que `lector/tesoreria_aa.py` (argumentos `--hoy`, `--cliente`; comentarios en criollo).
3. **Vigilante** (`vigilante.py`): una fuente nueva, `ultimos_pagos`, que mira `Tesoreria A/` y
   `Tesoreria AA/` (sin subcarpetas). Cuando cambia cualquiera de las dos corre el lector con el
   **más nuevo de cada una**, y sus salidas van a `_para la Sheet/` por el mismo camino que las
   demás (`mover_salidas`). Si una de las dos carpetas no tiene archivo, esa fuente no corre. La fuente
   `tesoreria_aa` sigue igual. Actualizar el docstring de arriba ("QUÉ MIRA").
4. **Importador** (`importar_cashflow.gs`):
   - Entrada nueva en `IMPORTS` (`ultimos_pagos`, prefijo `para_pegar_ultimos_pagos_`, solapa
     "Ultimos Pagos" → hoja "Ultimos Pagos"). Sin columnas de fórmula; `Fecha Ultimo Pago` es fecha;
     `Codigo` y `Comprobante` son texto; marca en `Origen` = `Tango tesorería`; sin ID.
   - Sumarla a `ORDEN_AUTO` y al menú ("Importar Últimos pagos (Tango)").
   - La hoja "Ultimos Pagos" la crea Claude a mano en la Sheet, con el encabezado, antes de
     instalar. Si el importador necesita algo más de la hoja (formato, fila de encabezado en un lugar
     fijo), anotarlo en "Qué hice".

## Comprobaciones

- `python -m unittest ingestas.test_tango_live` pasa, con los tests viejos adaptados a 9 bajadas y
  tests nuevos para:
  - A pide `fromDate` = hoy − 400 días y AA sigue sin fechas;
  - el archivo de A cae en `Tesoreria A/` y **nunca** en `Tesoreria AA/`;
  - "9 de 9" en el parte;
  - `--si-falta` con parte de hoy `9 de 9` no baja, y con `8 de 9` o `8 de 8` sí.
- `--simular` muestra 9 "bajaría", y la de A con `fromDate`.
- Prueba de `lector/ultimos_pagos.py` con dos Excel **inventados** y chicos (A y AA). Tiene que cubrir:
  - desc con y sin código adelante;
  - un REV más nuevo que el último REC (se ignora);
  - dos códigos con la misma razón social (un renglón, los dos códigos);
  - un pase a NAVAR S.A. en AA (se ignora);
  - dos recibos el mismo día (gana el número más alto);
  - falta el archivo de AA (no escribe nada y sale con error).
- Vigilante: prueba (o, si no se puede, una explicación en "Qué hice") de que un archivo nuevo en
  `Tesoreria A/` dispara `ultimos_pagos` y **no** `tesoreria_aa`.
- Importador: si hay prueba `.cjs`, que cubra que se pisan solo los renglones con la marca y que la
  fecha entra como fecha.
- Qué **no** se puede probar en el worktree: la bajada real contra Live, el vigilante en la notebook
  y el importador en la Sheet. Lo prueba Claude con Thomas después del merge.

## Qué hice

- Rama creada desde `main` `5e3c9a7`, con la tarea 35 ya integrada.
- Tango baja nueve archivos: tesorería de A usa consulta 19 y
  `dias_atras.movimientos_tesoreria_A = 400`, con carpeta exclusiva `Tesoreria A/`.
  AA conserva consulta 17, fechas vacías y la tolerancia a `Tesorería AA/`.
  El parte y `--si-falta` usan nueve: 9/9 saltea, 8/9 y los partes viejos 8/8 reintentan.
- Nuevo `lector/ultimos_pagos.py`: exige ambos archivos y valida sus encabezados antes
  de escribir. Agrupa por empresa/tipo/razón social, conserva espacios internos y códigos
  con ceros, desempata por número de comprobante y resume descartes y fechas por archivo.
  No suma importes: sólo usa su signo para descartar negativos. También descarta importes
  no legibles, fechas no válidas y comprobantes vacíos, dejando el motivo en el resumen.
  Las salidas se generan junto al archivo de A; el Excel se reemplaza de una vez.
- Vigilante: `ultimos_pagos` toma el último `.xlsx` por modificación de cada carpeta,
  sin subcarpetas ni temporales `.parte.xlsx`. Si falta una empresa no corre. Usa
  `mover_salidas` y sus controles existentes. Para esta fuente la firma incluye también
  modificación: una corrección del mismo tamaño debe volver a leerse. La fuente de caja
  `tesoreria_aa` no cambió.
- Importador: nueva entrada, menú y orden automático; reemplaza sólo la marca
  `Tango tesorería`, conserva otras filas, fecha como fecha, códigos/comprobantes como texto.
- Con autorización expresa en este chat, ajusté **sólo el conteo de importadores** de la
  prueba existente `lector/pruebas/probar_importador_filtros.cjs`: usa el largo de
  `ORDEN_AUTO` en lugar del número fijo anterior. No cambié su prueba del aviso.

### Validación local (sin red, credenciales ni datos reales)

- `python -m py_compile ingestas/tango_live.py lector/ultimos_pagos.py clientes/navar/herramientas/vigilante.py`: OK.
- `python -m unittest ingestas.test_tango_live lector.pruebas.test_ultimos_pagos lector.pruebas.test_cheques_en_cartera lector.pruebas.test_extractos_tolerantes`:
  **42 pruebas OK**. Las 19 de Tango incluyen fechas de A/AA, carpetas separadas y partes
  9/9, 8/9 y 8/8. Las 7 nuevas del lector/vigilante cubren los casos de la consigna y
  ejecutan lectores reales sobre Excel inventados, publicando en una carpeta temporal.
  Un nuevo A dispara sólo `ultimos_pagos`; un nuevo AA dispara éste y `tesoreria_aa`.
  Repetir sin cambios no corre; cambiar la modificación del mismo archivo sí.
- `--simular --hoy 2026-09-29 --destino /private/tmp/tango34-simulacion`: nueve bajadas,
  A desde 25/08/2025, AA sin fechas. No consulta Tango ni escribe archivos.
- `node lector/pruebas/probar_importador_ultimos_pagos.cjs`: OK (marca, manuales, otros
  orígenes, texto, fecha a medianoche de Buenos Aires, menú y repetición sin duplicados).
- `node lector/pruebas/probar_importador_zona_horaria.cjs`: OK.
- `probar_importador_filtros.cjs`: pasan las comprobaciones del importador, incluido el
  nuevo conteo. Su última prueba del **aviso** falla buscando la frase `NO CUADRÓ`;
  comprobado el mismo fallo en `main` sin estos cambios. El aviso ahora dice
  `Falló la importación de ... VERIFICACION_NO_CUADRA`. Es una expectativa previa
  desactualizada, fuera del ajuste autorizado del conteo; queda para el responsable del aviso.
- El vigilante emite advertencias previas `ResourceWarning` por sus `open(ESTADO)` sin
  contexto; no afectan estas pruebas y no se modificaron. Sin dependencias nuevas.

### Antes de instalar / límites

- **Pendiente importante fuera del alcance:** `aviso_diario.gs` compara literalmente
  `parte.ok === 8 && parte.total === 8`. Con 9/9, el mail puede decir "parte incompleto
  (9 de 9)" y tampoco enumera tesorería de A. **Hay que adaptar el aviso antes de desplegar
  este cambio**. No se tocó porque la consigna lo prohíbe expresamente. El instalador y
  algunos documentos anteriores también conservan textos de "ocho"; no afectan el reloj,
  pero conviene actualizarlos junto al despliegue (fuera de los archivos permitidos).
- Crear en la Sheet **Ultimos Pagos**, encabezados en **fila 1**, columnas A:G:
  `Empresa | Tipo | Codigo | Razon Social | Fecha Ultimo Pago | Comprobante | Origen`.
  Sin fórmulas. Dar formato fecha a E, texto a C/F y suficientes filas para todos los
  relacionados más los manuales (el importador no amplía la cantidad de filas).
  No dejar vistas de filtro guardadas; mantiene el requisito de Sheets API habilitada.
- Tras integrar: actualizar notebook y pegar el importador revisado en Apps Script;
  probar la consulta 19, la bajada 9/9, la publicación de las dos empresas, el registro
  de importación y que A no entre en la caja de AA. Nada de eso se probó contra servicios
  reales aquí. No hubo merge, push, cambios en Drive ni en la Sheet.
- La ventana de A limita la historia: no aparecer en esta lista significa "sin pago
  reconocido en el archivo leído", no "nunca pagó". El ranking Principales 20 queda para
  la Sheet como indica la consigna. No se tocó `lector/tesoreria_aa.py`.


## Revisión
