# Tarea 18 — Que la bajada de Tango por API funcione de verdad
Estado: lista para revisión
Rama: tarea/tango-api

## Objetivo

`ingestas/tango_live.py` se escribió **a ciegas**, antes de tener el token. El 24-25/09 se probó
contra el Tango real de NAVAR y **no funciona tal como está**. Arma mal la dirección, espera nombres de
columnas que la API no devuelve y guarda la tesorería en una carpeta que nadie lee.

Hay que dejarlo de modo que **los Excel que baja sean iguales a los que se exportaban a mano desde
Live**: mismos encabezados, mismos textos de estado, mismas carpetas y mismos nombres de archivo.
Así `lector/tango.py`, `lector/tesoreria_aa.py` y el vigilante siguen como están y no se enteran
de que el archivo vino por API.

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `CLAUDE.md`, `clientes/navar/LEEME.md` (sección
"Dónde estamos (24/09/2026)"), `ingestas/tango_live.py`, `lector/tango.py` (en especial `_norm`,
`_col`, `_motivo_estado_cheque`, `leer_*`), `lector/tesoreria_aa.py` y en
`clientes/navar/herramientas/vigilante.py` las funciones `fuentes()` y `tango_ultimos()`.

Todo lo que sigue se **comprobó contra el Tango real** (Thomas corrió los comandos en la notebook).
No hay acceso a esa red desde el worktree: las pruebas se hacen con respuestas inventadas.

### 1. La llamada (comprobado)

La pantalla de Live (Apertura → API) dibuja la dirección como
`Api/GetApiLiveQueryData/{process}/{fromDate}/...`, **pero cada parámetro dice "(Query)"**.
La forma de ruta devuelve la página HTML de Live ("Iniciando...") con HTTP 200, no datos.
Lo que funciona:

```
GET http://servidor:17000/Api/GetApiLiveQueryData?process=17952&fromDate=01/01/2000&toDate=31/12/2030&pageSize=5000&pageIndex=0
headers:  ApiAuthorization: <token>     Company: 13
```

- Fechas en **DD/MM/AAAA** (con `/`). Filtran de verdad: 01/09–24/09/2026 trajo 32 cobranzas
  y 01/01/2000–31/12/2030 trajo 344, la foto completa de lo pendiente.
- `pageSize=5000` es aceptado (devolvió 5000 de 18208).
- `customQuery`: en Live no hay ninguna consulta personalizada guardada (el campo sale vacío).
  No mandarlo, salvo que `perfil.json → tango_live.custom_query` tenga un valor real
  (hoy dice `"-"`, que hay que tratar como "no hay").

### 2. La respuesta (comprobado)

```json
{"resultData": {"list": [ {...}, {...} ],
                "pageIndex": 0, "pageSize": 5, "totalCount": 32, "totalPages": 7,
                "hasPreviousPage": false, "hasNextPage": true},
 "message": null, "exceptionInfo": null, "succeeded": true}
```

Las fechas vienen como `"2026-09-19T00:00:00"` y los importes como número (`12100.0000000`).

### 3. Las columnas que devuelve la API, consulta por consulta (comprobado)

No son las del export a mano. Vienen en MAYÚSCULAS_CON_GUION_BAJO y **faltan algunas** (la API
devuelve la vista por defecto del proceso, no la que se arma en pantalla).

| Consulta (proceso) | Columnas de la API |
|---|---|
| cobranzas (17952) | ID_GVA12, TIPO_COMPROBANTE, NRO_COMPROBANTE, FECHA_DE_VENCIMIENTO, ID_GVA14, RAZON_SOCIAL, TELEFONO, IMPORTE_PENDIENTE_CTE, IMPORTE_PENDIENTE_EXT |
| pagos (17696) | ID_CPA01, ID_CPA04, FECHA_DE_VENCIMIENTO, TIPO_DE_COMPROBANTE, NRO_COMPROBANTE, RAZON_SOCIAL, TELEFONO, TOTAL_PENDIENTE_CTE, TOTAL_PENDIENTE_EXT |
| cheques_terceros (11583) | ID_SBA14, ID_GVA14, ID_CPA01, NRO_INTERNO, NRO_DE_CHEQUE, FECHA_DEL_CHEQUE, BANCO, ESTADO, DESC_SUBESTADO, ORIGEN, TIPO_DE_CHEQUE, CLIENTE, PROVEEDOR, MONEDA_DE_LA_CUENTA, IMPORTE_CTE, IMPORTE_EXT |
| cheques_propios (11584) | NRO_CHEQUERA, ID_SBA15, NRO_DE_CHEQUE, FECHA_DE_EMISION, FECHA_DEL_CHEQUE, ID_CPA01, COD_PROVEEDOR, RAZON_SOCIAL, ESTADO, TIPO_DE_CHEQUE, COD_BANCO, BANCO, COD_CTA_EMISION, CUENTA_EMISION, CONCILIADO, CONCILIADO_RECHAZADO, IMPORTE, IMPORTE_REEXP_CTE, IMPORTE_REEXP_EXT |
| movimientos_tesoreria (11591, solo AA) | TIPO, ID_SBA04, COMPROBANTE, FECHA, CONCEPTO, CLASE, TOTAL_CTE, COD_RELACIONADO, DESC_RELACIONADO, CLASIFICACION |

Los encabezados del **export a mano** (lo que los lectores ya entienden) son:

- cobranzas: `Cód. cliente, Razón social, Tipo comprobante, Nro. comprobante, Fecha de emisión, Fecha de vencimiento, Importe al Vencimiento (CTE), Importe Pendiente (CTE), Descripción condición de venta`
- pagos: `Cód. proveedor, Razón social, Tipo de comprobante, Nro. comprobante, Fecha de emisión, Fecha de vencimiento, Total al vencimiento (CTE), Total pendiente (CTE)`
- cheques terceros (AA): `Nro. de cheque, Nro. interno, Banco, Cód. cliente, Cliente, CUIT del cheque, Fecha del cheque, Fecha extracto, Fecha extracto (rechazado), Importe, Importe (CTE), Estado, Subestado, Cód. estado, Cuenta cartera, Cta. destino, Proveedor, Cód. proveedor, Tipo de cheque`
- cheques propios: `Nro. de cheque, Nombre de banco, Cód. proveedor, Razón social, Fecha de emisión, Fecha del cheque, Fecha de rechazo, Importe mon. cta., Estado, Nro. comp. emisión, Tipo de cheque`
- tesorería AA: `Tipo, Comprobante, Fecha, Fecha de emisión, Concepto, Clase, Total (cte), Cód. relacionado, Desc. relacionado, Clasificación`

Ojo con un detalle que ya muerde: `lector/tango.py` busca `"nro. comprobante"` (con punto). Con
el nombre de la API, `NRO_COMPROBANTE` queda como `"nro comprobante"` y no coincide. Entonces cae en el
"contiene `comprobante`" y agarra **Tipo comprobante**, que viene antes. Por eso hay que traducir
los encabezados en la bajada y no confiar en que `_col` los adivine. `lector/tesoreria_aa.py` usa
claves exactas (`"Total (cte)"`, `"Desc. relacionado"`...): sin traducción no lee nada.

Lo que **falta** en la API y no se inventa: en cobranzas, fecha de emisión, importe al
vencimiento y condición de venta; en pagos, fecha de emisión y total al vencimiento. El lector
ya tolera que falten: sin importe al vencimiento usa el pendiente, y la emisión queda vacía.
Anotarlo en el docstring como limitación conocida.

### 4. Los estados vienen como CÓDIGO, no como texto (comprobado; la traducción, en parte inferida)

- **cheques_terceros → `ESTADO`**: `C`, `A`, `R`. **Comprobado**: el export a mano de AA tenía la
  columna `Cód. estado` con C/A/R y `Estado` con En Cartera / Aplicado / Rechazado (16 / 238 / 14
  el 16/09; la API dio 14 / 240 / 14 el 25/09).
- **cheques_propios → `ESTADO`**: `E`, `R`, `X` (en los primeros 5000: 4734 / 188 / 78). **Inferido**
  por proporciones contra el export a mano (Al Cobro 97% / Rechazado 2% / Anulado 1%):
  E = Al Cobro, R = Rechazado, X = Anulado. Se confirma en la primera corrida supervisada.
- **movimientos_tesoreria → `CLASE`**: `1`, `2`, `4`, `6` (en los primeros 5000 de 5777:
  1205 / 3780 / 6 / 9). El export a mano del 23/09 (5774 filas) tenía Pagos 4252, Cobros 1204,
  Otros movimientos de bancos y carteras 308, Rechazo de cheques de terceros 9. **Inferido**:
  1 = Cobros, 2 = Pagos, 4 = Otros movimientos de bancos y carteras, 6 = Rechazo de cheques de
  terceros. El 6 (9 = 9) es firme; el resto se confirma en la corrida supervisada. En el export a mano
  cada clase va con tipos fijos: Cobros ↔ REC, Pagos ↔ O/P, OPF, FPR, Otros ↔ EXT, Rechazo ↔ RCT,
  y REV (anulación) puede ir con cualquiera.

### 5. La carpeta de tesorería (bug)

`DESTINO["movimientos_tesoreria"]` dice `"Tesorería AA"` (con tilde). En Drive la carpeta real es
**`Tesoreria AA`** (sin tilde) y el vigilante mira primero esa; si tiene archivos, no mira la otra.
Resultado actual: la bajada crearía una carpeta nueva que nadie lee.

### 6. Cuántas filas (comprobado)

cobranzas A 344 · AA 34; pagos A 424 · AA 115; cheques terceros A **64.951** · AA 268;
cheques propios A 18.208; tesorería AA 5.777. En cheques de terceros de A, la API devuelve **toda
la historia**; el export a mano traía solo los En Cartera (25). El lector solo usa los `C`.

Además, con `fromDate=01/01/2000` los cheques propios dan 18.208, y el export a mano daba 22.533.
Hay cheques "Al Cobro" desde 1995, y puede ser el corte de fecha. El lector descarta igual los
propios viejos, pero la foto tiene que ser completa: usar un desde bien atrás.

## Archivos permitidos

- `ingestas/tango_live.py`
- `ingestas/test_tango_live.py` (nuevo)
- `clientes/navar/herramientas/instalar_tango.ps1` (nuevo)
- `clientes/navar/perfil.json` — **solo** el bloque `tango_live` (textos `_ayuda`/`_origen`, y si
  hace falta una clave nueva para el rango de fechas).
- `clientes/navar/documentos/instalar_notebook.md` — **solo** la sección 5.
- `tareas/18-tango-api-de-verdad.md`

No tocar los lectores, el vigilante, `nucleo/`, `setup_credenciales.py` ni los `.gs`.

## Resultado esperado

1. **La llamada** con parámetros después de `?` (armados con `urllib.parse.urlencode`), fechas
   DD/MM/AAAA, `pageSize=5000`, timeout de 300 s por página. Rango: desde `01/01/1990` hasta el
   31/12 de dentro de 5 años (calculado desde `--hoy`, no fijo).
2. **Paginar con `hasNextPage`**. Al terminar, si las filas juntadas no son `totalCount`, **error y
   no se escribe el archivo**. Si `succeeded` no es `true`, si viene `exceptionInfo` o si la
   respuesta no es JSON, error claro. Para el HTML de "Iniciando...", el mensaje tiene que decir
   que la dirección no es la de la API.
3. **Traducir encabezados** a los del export a mano, con un diccionario por consulta escrito a la
   vista, comentado en criollo. Las columnas de la API que no tengan equivalente se dejan al final
   con su nombre original: no se pierde nada. Las que no vienen, no se inventan.
   - cobranzas: TIPO_COMPROBANTE→`Tipo comprobante`, NRO_COMPROBANTE→`Nro. comprobante`,
     FECHA_DE_VENCIMIENTO→`Fecha de vencimiento`, RAZON_SOCIAL→`Razón social`,
     IMPORTE_PENDIENTE_CTE→`Importe Pendiente (CTE)`.
   - pagos: TIPO_DE_COMPROBANTE→`Tipo de comprobante`, NRO_COMPROBANTE→`Nro. comprobante`,
     FECHA_DE_VENCIMIENTO→`Fecha de vencimiento`, RAZON_SOCIAL→`Razón social`,
     TOTAL_PENDIENTE_CTE→`Total pendiente (CTE)`.
   - cheques terceros: NRO_DE_CHEQUE→`Nro. de cheque`, NRO_INTERNO→`Nro. interno`, BANCO→`Banco`,
     CLIENTE→`Cliente`, PROVEEDOR→`Proveedor`, FECHA_DEL_CHEQUE→`Fecha del cheque`,
     IMPORTE_CTE→`Importe (CTE)`, DESC_SUBESTADO→`Subestado`, TIPO_DE_CHEQUE→`Tipo de cheque`,
     y ESTADO (código) → **`Cód. estado`** (el código tal cual) **más** una columna `Estado` con el
     texto (C→En Cartera, A→Aplicado, R→Rechazado).
   - cheques propios: NRO_DE_CHEQUE→`Nro. de cheque`, BANCO→`Nombre de banco`,
     COD_PROVEEDOR→`Cód. proveedor`, RAZON_SOCIAL→`Razón social`, FECHA_DE_EMISION→`Fecha de emisión`,
     FECHA_DEL_CHEQUE→`Fecha del cheque`, IMPORTE→`Importe mon. cta.`, TIPO_DE_CHEQUE→`Tipo de cheque`,
     ESTADO → `Estado` con el texto (E→Al Cobro, R→Rechazado, X→Anulado) y el código en `Cód. estado`.
   - tesorería: TIPO→`Tipo`, COMPROBANTE→`Comprobante`, FECHA→`Fecha`, CONCEPTO→`Concepto`,
     CLASE→`Clase` con el texto (1→Cobros, 2→Pagos, 4→Otros movimientos de bancos y carteras,
     6→Rechazo de cheques de terceros), TOTAL_CTE→`Total (cte)`, COD_RELACIONADO→`Cód. relacionado`,
     DESC_RELACIONADO→`Desc. relacionado`, CLASIFICACION→`Clasificación`.
4. **Código de estado o clase desconocido**: no adivinar. El texto queda `"(código X sin traducir)"`.
   Así el lector lo deja afuera y se ve en su resumen. Además, una línea de log por consulta con
   el conteo por código (ej. `cheques propios A: E→Al Cobro 17.500 · R→Rechazado 600 · X→Anulado 108`),
   que es lo que se va a mirar en la corrida supervisada para confirmar lo inferido.
5. **Control de la tesorería**: contar los pares (Tipo, Clase) ya traducidos y avisar en el log si
   aparece un REC que no sea Cobros, un O/P, OPF o FPR que no sea Pagos, un EXT que no sea Otros o un RCT
   que no sea Rechazo. Si pasa, la traducción de CLASE está mal: **no se escribe el archivo**.
6. **Cheques de terceros: escribir solo los `C` (en cartera)**, como el export a mano de A. Son
   65 mil filas de historia que el lector descarta igual, y en Drive pesan. El conteo del punto 4
   se hace sobre todas, antes de filtrar.
7. **Carpeta de tesorería**: usar `Tesoreria AA` si existe; si no, `Tesorería AA` si existe; si no
   hay ninguna, crear `Tesoreria AA`. Nombre de archivo: `AA movimientos tesoreria <hoy>.xlsx`.
8. **`--probar <consulta> --empresa X`**: con la llamada nueva, 5 filas. Mostrar URL (sin token),
   HTTP, `totalCount`, columnas de la API, columnas después de traducir y conteo por código.
   **No imprimir filas con datos** (nombres, montos): se pega en chats.
9. `--simular` sigue sin tocar red ni llavero y muestra la URL que usaría.
10. **`instalar_tango.ps1`**, calcado de `instalar_vigilante.ps1`: tarea "finauto NAVAR Tango",
    todos los días a las **07:30**, `ingestas\tango_live.py --cliente navar`, iniciar en el repo,
    `-MultipleInstances IgnoreNew`, límite de 1 hora, con opción `quitar`. La salida de cada
    corrida se agrega a `clientes\navar\privado\tango_live.log`: si la tarea falla de madrugada,
    tiene que quedar rastro.
11. **`instalar_notebook.md` §5** reescrita con lo aprendido:
    - Token: se guarda **desde el portapapeles**. Pegar con Ctrl+V o clic derecho en la pantalla
      de clave oculta de Python, a través del escritorio remoto, guardó basura tres veces. Con
      `\x16` (el Ctrl+V), con un carácter de más y con uno de menos. El comando que funcionó:
      ```powershell
      cd C:\finauto; $null = Read-Host "Copia el token con Ctrl+C y despues apreta Enter aca"; Get-Clipboard | .\.venv\Scripts\python.exe -c "import sys,re; from nucleo import credenciales as c; t=sys.stdin.read().strip(); assert re.fullmatch(r'[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}', t), 'NO parece un token (%d caracteres), no guardé nada' % len(t); c.guardar('.','navar','tango_live','finanzasnavar@gmail.com',t); print('guardado ok', len(t))"
      ```
      El usuario del llavero es `finanzasnavar@gmail.com`: con ese usuario de Tango se generó el token.
    - Probar con `--probar`, primera bajada **a una carpeta local** con `--destino` (no a Drive),
      comparar, y recién después la bajada a Drive y `instalar_tango.ps1`.

## Comprobaciones

1. `python -m py_compile ingestas/tango_live.py ingestas/test_tango_live.py` y JSON válido de `perfil.json`.
2. `python -m unittest ingestas.test_tango_live`, **sin red** (reemplazar `urllib.request.urlopen`
   por respuestas inventadas, con nombres y montos inventados). Tiene que cubrir:
   - la URL con `?process=...&fromDate=DD/MM/AAAA...` y los dos headers;
   - paginación en 2+ páginas, y error sin archivo si no cierra con `totalCount`;
   - el HTML "Iniciando..." y `succeeded: false`, con error claro;
   - encabezados traducidos en las 5 consultas y códigos traducidos, incluido uno desconocido;
   - el control Tipo/Clase de tesorería frena si hay un REC con clase Pagos;
   - cheques de terceros: solo quedan los C;
   - elección de carpeta `Tesoreria AA` / `Tesorería AA`;
   - **integración con los lectores**: el Excel que deja la bajada (con datos inventados, en una
     carpeta temporal) se procesa con `lector.tango.procesar(...)` y con `lector/tesoreria_aa.py`, y
     salen las filas esperadas: cliente, nro de comprobante con número (no "FAC FAC"), vencimiento,
     pendiente, cheque en cartera, propio Al Cobro a vencer, cobro y pago de AA.
3. `python ingestas/tango_live.py --cliente navar --simular --destino <carpeta temporal>`: lista
   las **8** bajadas sin pedir el token. De A: cobranzas, pagos, cheques terceros y cheques propios.
   De AA: cobranzas, pagos, cheques terceros y tesorería. AA no tiene cheques propios y la
   tesorería es solo de AA, según las reglas de `pendientes`.
4. Dejar escrito qué NO se pudo probar: la red de NAVAR, el Tango real, la tarea programada y lo
   inferido del punto 4 del Contexto.
5. `grep` de nombres propios de personas vacío en lo agregado. Commit en la rama.

## Qué hice

Trabajo terminado en el worktree de `tarea/tango-api`. Se tocaron únicamente los seis archivos
permitidos:

- `ingestas/tango_live.py`: llamada real con parámetros de query y la consulta personalizada
  obligatoria de cada empresa/lista; páginas de 5.000 con timeout de 300 s;
  validación de `succeeded`, `exceptionInfo`, JSON, `resultData.list`, `hasNextPage` y
  `totalCount`. Una foto incompleta no llega a escribirse.
- La misma ingesta traduce a los encabezados manuales antes de crear el Excel, conserva al final
  los campos sin equivalencia, convierte códigos a texto y registra los conteos por código.
  Terceros publica sólo `C`; Tesorería controla los pares Tipo/Clase. Un código desconocido se
  muestra como tal. En Tesorería además se excluye de la publicación porque el lector existente
  toma toda clase desconocida como “Otros”; publicarla sería inventar una categoría y el lector
  no se podía tocar en esta tarea. El código queda visible en el log para revisar.
- `--probar` trae cinco filas pero muestra únicamente URL sin token, HTTP, total, encabezados y
  conteos; no imprime nombres ni montos. `--simular` no toca red ni llavero y lista las ocho
  bajadas con su URL. La tesorería elige primero `Tesoreria AA`, tolera la variante con tilde y
  crea la carpeta sin tilde si no existe ninguna.
- `ingestas/test_tango_live.py`: 12 pruebas sin red con respuestas y datos inventados. Cubren URL,
  headers, timeout, consulta personalizada obligatoria, dos páginas, cierre contra `totalCount`, HTML “Iniciando”,
  `succeeded=false`, `exceptionInfo`, las cinco traducciones, códigos desconocidos, filtro de
  terceros, freno Tipo/Clase, elección de carpeta y no exposición de datos en `--probar`.
  La integración crea Excel temporales y verifica que `lector.tango.procesar` y
  `lector.tesoreria_aa.leer` obtienen cliente, comprobante numérico, vencimiento, pendiente,
  cheque de terceros, cheque propio, cobro y pago de AA.
- `clientes/navar/herramientas/instalar_tango.ps1`: nueva tarea diaria `finauto NAVAR Tango` a
  las 07:30, desde el repo, una sola instancia, límite de una hora y salida acumulada en
  `privado/tango_live.log`; admite `quitar`. La salida de Python se fuerza a UTF-8 para que la
  consola de Windows no falle por acentos o flechas.
- `clientes/navar/documentos/instalar_notebook.md` §5: token validado desde el portapapeles,
  prueba de estructura, primera descarga local, descarga a Drive y recién después instalación.
  `clientes/navar/perfil.json`: se modificó solamente el bloque `tango_live`.

**Agregado del 25/09 aplicado:** se reemplazó la vista por defecto por las ocho `customQuery`
10–17, configuradas por empresa y consulta; si falta una, esa bajada falla sin volver al formato
incompleto. Se agregaron al traductor las columnas completas de las consultas guardadas. Todas
las fotos mandan `fromDate` y `toDate` vacíos salvo cheques propios: toma
`dias_atras.cheques_propios = 60` desde el perfil y, para 25/09/2026, arma **27/07/2026** hasta
vacío. Se aplicó literalmente la regla “hoy menos 60 días” indicada por el usuario; el 26/08 que
figura como ejemplo en el agregado equivale a 30 días y no se usó. Las equivalencias confirmadas
quedaron como tales: propios traduce sólo `E = Al Cobro`; Tesorería conserva 1/2/4/6; terceros
mantiene C/A/R y deja X sin traducir. El filtro final de terceros sigue publicando sólo C.

**Comprobaciones realizadas:**

- `python -m unittest ingestas.test_tango_live`: 12 pruebas OK.
- `python -m py_compile ingestas/tango_live.py ingestas/test_tango_live.py`: OK.
- `python -m json.tool clientes/navar/perfil.json`: OK.
- `python tests/test_lector.py`: todos los chequeos existentes pasaron.
- Simulación con fecha 25/09/2026 y carpeta temporal: exactamente ocho bajadas, todas con su
  `customQuery`; siete con fechas vacías y cheques propios desde 27/07/2026, sin leer el token.
- `git diff --check`: OK. No se agregaron nombres propios de personas ni dependencias.

**No se pudo probar en este entorno:** la red y el Tango real de NAVAR, el token del llavero ni
la ejecución del `.ps1`/Programador de tareas de Windows. Las equivalencias de códigos y las
consultas personalizadas fueron confirmadas externamente según el agregado; las pruebas locales
verifican que el programa respete ese contrato. La guía conserva una primera descarga local
supervisada antes de publicar en Drive.

## Revisión
