# Tarea 74 — Galicia para cualquier cliente de una sola empresa, y movimientos a CSV
Estado: lista para revisión
Rama: tarea/74-galicia-una-empresa

## Objetivo
El bot de Galicia que ya baja solo para NAVAR (`bots/galicia/navar.py`, tareas 17-29) tiene que servir para **otro
cliente con una sola empresa**, configurado desde su perfil, **sin cambiar en nada lo que hace hoy para NAVAR**. Y lo
que baje tiene que quedar en dos CSV con columnas fijas (`galicia_movimientos.csv`, `galicia_saldo.csv`) dentro de la
bajada diaria de `ingestas/mercado_datos.py`.

## Contexto
- Leer `AGENTS.md`, `CLAUDE.md`, `tareas/LEEME.md`, las consignas 71 a 73, `bots/galicia/navar.py`,
  `bots/galicia/test_navar.py`, `orquestador/correr.py`, `nucleo/config.py`, `nucleo/salidas.py`,
  `lector/extractos.py` (`leer_planilla_galicia`) e `ingestas/mercado_datos.py`.
- **El repo es público.** Nada de datos reales: empresa `EJEMPLO SA`, cuenta `0001234-5 999-1`, cliente `ejemplo`.
- **NAVAR está en producción** (su notebook baja `main` todos los días y corre el bot a las 05:45). Todo lo que hoy
  pasa con `--cliente navar` tiene que seguir exactamente igual: `bots/galicia/test_navar.py` y
  `orquestador/test_si_falta.py` tienen que seguir dando OK sin tocarlos.
- El perfil del cliente nuevo **no puede estar en el repo** (lleva el nombre de la empresa y la cuenta): vive en
  `clientes/<c>/privado/perfil.json` (`privado/` ya está en `.gitignore`).

### 1. Perfil en `privado/`
`nucleo/config.cargar_perfil`: si no existe `clientes/<c>/perfil.json`, buscar `clientes/<c>/privado/perfil.json`. Si
no está ninguno, el error nombra las dos rutas. NAVAR (que tiene el de la raíz) no cambia.

### 2. Bot de Galicia "una empresa"
- Nuevo `bots/galicia/una_empresa.py` con `BotGaliciaUnaEmpresa`, que **reusa el recorrido de `BotGaliciaNavar`**
  (login de un solo intento, cuenta por número, saldos, descarga del Excel con rescate, validación) pero:
  - la empresa sale del perfil (`solo_estas_empresas`: lista de nombres) y no de la constante `PATRON_EMPRESA`.
    Armar el patrón tolerante a espacios, puntos y "S.A." / "SA" / "SOCIEDAD ANONIMA" a partir de esos nombres;
  - `capturar_empresa_activa` devuelve el nombre del perfil que coincidió;
  - los mensajes no dicen "NAVAR";
  - la validación del Excel usa la cuenta del perfil (ver punto 3).
- En `bots/galicia/navar.py` se permite **solo** lo mínimo para poder heredar: pasar el patrón de la empresa, el
  nombre y la lectura del Excel a atributos o métodos que la clase NAVAR fije con los **mismos valores de hoy**. Nada
  más cambia ahí.
- `orquestador/correr.py`: si el bloque del banco en el perfil dice `"variante": "una_empresa"` (y el banco es
  `galicia`), usar `BotGaliciaUnaEmpresa` con el mismo tratamiento que la variante NAVAR (resultado estricto, marca de
  clave sin confirmar, contador), pero la carpeta de salida es **solo** `carpeta_drive_destino` del perfil (ruta
  absoluta; sin la detección de "NAVAR - Datos"). Si falta o no existe, cortar **antes** de abrir el banco, como hoy.
  Lo de NAVAR (`cliente == "navar"`) queda igual.

### 3. Lectura del Excel con la cuenta del perfil
`lector/extractos.leer_planilla_galicia(ruta, cuenta=...)`: parámetro opcional `cuenta`; si no se pasa, el valor de
hoy (lo usa NAVAR). La variante una_empresa le pasa la cuenta del perfil.

### 4. `ingestas/galicia_datos.py`: de las descargas a los CSV
Lee la carpeta de descargas del cliente (`carpeta_drive_destino` del bloque `galicia` de su perfil):
- **Movimientos:** todos los Excel `"<prefijo_archivo> AAAA-MM-DD.xlsx"` (los deja el bot; cada uno trae los
  últimos ~30 días, así que se pisan entre sí). Leerlos con `leer_planilla_galicia(ruta, cuenta)`, juntar y **quitar
  repetidos** (mismo `fecha`, `concepto`, `referencia`, `importe` y `saldo`). Además se conserva lo ya escrito en el
  `galicia_movimientos.csv` anterior (los Excel viejos pueden borrarse), con la misma regla de repetidos.
- **Saldo:** los `_SALDOS_Galicia_DD-MM.json` que deja el bot (`fecha` completa adentro; `empresas[0].saldo_actual`).
  Una fila por fecha (si hay dos del mismo día, la última por `generado`), conservando las del CSV anterior.

`galicia_movimientos.csv`, columnas en este orden: `fecha` (AAAA-MM-DD), `concepto`, `referencia`, `importe` (con
signo: lo que entra positivo, lo que sale negativo; 2 decimales), `saldo` (2 decimales, vacío si no vino), `tipo`.
Orden: por `fecha` y en el orden en que vienen en el Excel dentro del día.
`tipo` se decide por palabras del concepto, **en una tabla de constantes fácil de ajustar** (se afina con los datos
reales; comparar sin mayúsculas ni acentos), en este orden:
- `impuesto`: `IMP`, `LEY 25413`, `DEBITOS Y CREDITOS`, `PERCEP`, `RETEN`, `IIBB`, `INGRESOS BRUTOS`, `SIRCREB`, `IVA`;
- `comisión`: `COMISION`, `COM.`, `MANTENIMIENTO`, `CARGO`;
- `Tiendanube`: `TIENDANUBE`, `NUVEM`, `PAGO NUBE`;
- `transferencia`: `TRANSF`, `TRF`, `TRANSFERENCIA`, `DEBIN`, `ECHEQ`;
- `otro`: el resto.

`galicia_saldo.csv`: `fecha` (AAAA-MM-DD), `saldo` (2 decimales).

Escritura por temporal + `os.replace` (como los otros CSV). Integrar en `ingestas/mercado_datos.py` como fuente
**`galicia`** (`--solo galicia` también):
- si el cliente no tiene perfil, o su perfil no tiene un bloque `galicia` con `"activo": true` y
  `carpeta_drive_destino`, la fuente se saltea y no se escribe en `control.json` (como Tiendanube sin aplicación);
- `control.json`: `ok`, `filas`, `desde`, `hasta`, `motivo`; además `ultima_descarga` (fecha del Excel más nuevo).
  Si el Excel más nuevo tiene más de 2 días, `ok` false con motivo "el bot de Galicia no bajó nada desde <fecha>"
  (igual se escriben los CSV con lo que hay). Si no hay ningún Excel: `ok` false, "todavía no hay descargas de Galicia".
- Esta fuente **no** abre el banco: solo lee lo que dejó el bot (que se corre aparte con `orquestador/correr.py`).

### Ejemplos inventados (usar estos en las pruebas)
**Q.** Dos Excel: `Movimientos Galicia 2026-10-30.xlsx` con 3 movimientos (29/10 transferencia recibida +100000 saldo
500000; 29/10 `IMP. LEY 25413` −600 saldo 499400; 30/10 `COMISION MANTENIMIENTO` −5000 saldo 494400) y
`Movimientos Galicia 2026-10-31.xlsx` con esos mismos 3 más uno del 31/10 (`TRANSFERENCIA TIENDANUBE` +80000 saldo
574400) → 4 filas, tipos `transferencia`, `impuesto`, `comisión`, `Tiendanube`.
**R.** Dos `_SALDOS_Galicia_31-10.json` del mismo día con `generado` distinto → queda el más nuevo.
**S.** Perfil sin bloque `galicia` → la fuente no aparece en `control.json`. Excel más nuevo de hace 5 días → `ok`
false con el motivo.

## Archivos permitidos
- `nucleo/config.py`, `bots/galicia/navar.py` (solo lo mínimo, ver punto 2), `bots/galicia/una_empresa.py` (nuevo),
  `orquestador/correr.py`, `lector/extractos.py` (solo el parámetro `cuenta`), `ingestas/galicia_datos.py` (nuevo),
  `ingestas/mercado_datos.py`.
- `bots/galicia/test_una_empresa.py` y `tests/test_galicia_datos.py` (nuevos).
- Esta consigna (sección "Qué hice").

## Resultado esperado
- `python orquestador/correr.py --cliente ejemplo --banco galicia` con un perfil en `privado/` que diga
  `"variante": "una_empresa"` usa el bot nuevo (probado con página falsa / dobles, sin banco real).
- `python -m ingestas.mercado_datos --cliente <c> --salida <carpeta>` escribe además `galicia_movimientos.csv`,
  `galicia_saldo.csv` y la fuente `galicia`, o la saltea si el cliente no tiene Galicia.

## Comprobaciones
- `python bots/galicia/test_una_empresa.py`, `python tests/test_galicia_datos.py` (sin pytest; Excel armados con
  `openpyxl` del `.venv`), cubriendo: patrón de empresa desde el perfil (con y sin "S.A."), que NAVAR sigue usando su
  patrón y su cuenta, perfil en `privado/`, carpeta faltante corta antes de abrir el banco, ejemplos Q, R y S, CSV
  anterior conservado, escritura atómica.
- Siguen dando OK: `bots/galicia/test_navar.py`, `orquestador/test_si_falta.py`, `tests/test_meli_ventas.py`,
  `tests/test_meli_publicidad.py`, `tests/test_mp_liquidaciones.py`, `tests/test_meli_oauth.py`,
  `tests/test_tiendanube.py`.
- Lo que no se puede probar acá (el banco real): lo hace Claude en la Mac con el usuario del cliente.

## Qué hice

- `nucleo/config.py`: busca el perfil privado cuando no existe el de la raíz;
  conserva la prioridad de la raíz y nombra ambas rutas si no encuentra ninguno.
- `bots/galicia/una_empresa.py`: hereda el recorrido completo, usa los nombres y
  la cuenta del perfil y tolera espacios, puntos y variantes de sociedad anónima.
  En `navar.py` solo extraje atributos de nombre/patrón y un método de lectura;
  sus valores y mensajes siguen iguales. `lector/extractos.py` solo agrega la
  cuenta opcional, conservando el valor anterior por defecto.
- `orquestador/correr.py`: selecciona la variante, fuerza una sola empresa activa,
  valida la carpeta absoluta del perfil antes del llavero/login y aplica resultado
  estricto y contador de clave sin confirmar. NAVAR conserva su selección y Drive.
- `ingestas/galicia_datos.py`: lee Excel locales y saldos JSON, conserva los CSV
  anteriores, elimina repetidos, clasifica por la tabla `TIPOS`, ordena por fecha
  y elige el saldo con mayor `generado` entre los JSON de cada día. Los JSON
  presentes actualizan ese día del CSV; los días sin JSON se conservan.
- `ingestas/mercado_datos.py`: incorpora `galicia` y `--solo galicia`, ambos CSV
  con escritura temporal y `os.replace`, control de antigüedad y omisión de la
  fuente si no está configurada. `filas` cuenta movimientos; `desde`/`hasta`
  son sus fechas. Cada CSV se reemplaza de manera atómica por separado.
- Agregué `bots/galicia/test_una_empresa.py` (5 pruebas) y
  `tests/test_galicia_datos.py` (5): página falsa, login único, perfil privado,
  carpeta faltante, cuenta, resultado estricto, contador, Q/R/S, segunda corrida,
  historial, tipos, saldo vacío, conservación de otras fuentes y fallas de
  lectura/reemplazo sin perder el CSV anterior.
- Pruebas con `/Users/thomasmanzo/Documents/Finnauto/.venv/bin/python3`, sin pytest:
  NAVAR 42, reintentos 7, ventas 11, publicidad 3, liquidaciones 7, OAuth 9 y
  Tiendanube 13: todas OK, sin modificar sus archivos. Las pruebas existentes se
  ejecutaron con `PYTHONPATH=.`. Sin dependencias nuevas.
- No abrí bancos reales ni usé datos privados. Los documentos privados de NAVAR
  no están en este worktree; usé el contexto de las consignas. Queda para Claude
  la prueba real con el usuario del cliente, como indica la tarea.

- Las 10 pruebas nuevas y `git diff --check` también dan OK.
- No pude commitear: `git add` no pudo crear el `index.lock` del worktree
  (`Operation not permitted`, restricción del sandbox). Dejé los diez archivos
  en este worktree, rama `tarea/74-galicia-una-empresa`, para revisión y commit.

## Revisión

- 01/11/2026 (Claude): revisado el diff y las pruebas (5 + 5 nuevas; NAVAR 42 y reintentos 7 sin tocar, más las de
  ML/MP/publicidad/Tiendanube: todo OK). Lo de NAVAR queda igual: los valores fijos pasaron a atributos con los mismos
  valores, la cuenta por defecto del lector es la de siempre, y el orquestador solo agrega la rama nueva.
  Retoque de Claude: en `TIPOS`, `IMP` pasó a `IMP.` e `IMPUESTO` (si no, "PAGO IMPORTACION" quedaba como impuesto).
  **Merge pendiente del OK de Thomas** (toca código que corre en producción para NAVAR). Falta la prueba real con
  el usuario del cliente; la tarea programada no se instala hasta probarla.
