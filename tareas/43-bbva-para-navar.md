# Tarea 43 — BBVA para NAVAR: bajar las dos cuentas corrientes
Estado: lista para revisión
Rama: tarea/bbva-navar

## Objetivo

Que la notebook de NAVAR baje sola, todos los días, los movimientos de las **dos cuentas corrientes de
BBVA** y los deje en `NAVAR - Datos/Bancos/bbva/`, como ya hace Galicia. El lector de extractos ya
entiende ese Excel; falta el bot que lo baja.

## Contexto

El 03/10/2026 Thomas consiguió un usuario de consulta propio de BBVA (el anterior quedaba en un loop
de vuelta al inicio) y describió el recorrido mirando la pantalla:

1. Login en `https://netcash.bbva.com.ar/local_pibee/SolicitarCredenciales.html` (el link que usa
   termina en `?20262704`, que parece un número de versión). Pide **tres datos**: "Código de empresa",
   "Código de usuario" y "Clave de acceso". Los dos últimos tienen ojito (se tipean ocultos). El botón
   "Ingresar" está apagado hasta que se completan.
2. Inicio: selector "Empresa / C.U.I.T." con **NAVAR SA 30-55852502-5**; abajo "Cuentas en pesos ·
   2 cuentas corrientes" con un **+** que despliega `#0489-000765/9` y `#0489-000806/5`.
3. Clic en la primera cuenta → pantalla "Saldos y movimientos" con `489-000765/9 (CC $)`, el saldo
   arriba a la derecha y los botones **Descargar** y **Filtrar**.
4. **Descargar** baja directo el Excel (`Movimientos.xls`, formato viejo de Excel, siempre ese
   formato), con los **últimos 60 días**.
5. Clic en el número de cuenta (`489-000765/9 (CC $) ▾`) → lista con buscador → `489-000806/5 (CC $)`
   → se recargan los movimientos → **Descargar** otra vez.

Lo que ya existe:
- `lector/extractos.py → leer_planilla_bbva` lee ese Excel (probado con el archivo real del 03/10:
  cuenta, CUIT, movimientos y saldo diario por "Saldo Disponible"). Saca la cuenta
  del **encabezado** del Excel, no del nombre del archivo, y junta varios archivos del mismo banco sin
  duplicar movimientos.
- `bots/galicia/navar.py` es el modelo: un solo intento de login, esperar un único elemento visible,
  confirmar cada pantalla antes de seguir, validar el archivo antes de publicarlo, copiar a Drive con
  un temporal para que el vigilante nunca vea un archivo a medias.
- Las credenciales viven en el llavero de Windows (`nucleo/credenciales.py`), hoy solo usuario y clave.
- `orquestador/correr.py` arma la variante NAVAR de Galicia con su carpeta de Drive.

Decisiones:
- **Las dos cuentas en la misma corrida** y en **dos archivos**: `Movimientos BBVA 489-000765-9
  AAAA-MM-DD.xls` y `Movimientos BBVA 489-000806-5 AAAA-MM-DD.xls` (la barra de la cuenta no puede ir
  en un nombre de archivo). El lector los junta.
- El **código de empresa** se guarda en el llavero junto con usuario y clave (mismo secreto), y
  `setup_credenciales.py` lo pide solo para BBVA. No va en el perfil ni en el repo.
- El archivo descargado se acepta solo si su encabezado dice la cuenta pedida y NAVAR (CUIT
  30558525025). Si una cuenta falla, la otra igual se publica y la corrida termina en error.
- Primero en **modo visible** y a mano; el horario diario se instala después de una prueba que salga
  bien (mismo camino que Galicia). El mail diario se cambia en otra tarea, cuando corra solo.

## Archivos permitidos

- `bots/bbva/__init__.py`, `bots/bbva/navar.py`, `bots/bbva/test_navar.py` (nuevos)
- `orquestador/correr.py` — registrar BBVA para NAVAR y su carpeta de Drive
- `nucleo/credenciales.py` — dato extra opcional (código de empresa)
- `setup_credenciales.py` — pedir el código de empresa para BBVA
- `clientes/navar/perfil.json` — solo el bloque `bancos.bbva`
- `clientes/navar/herramientas/instalar_bbva.ps1` (nuevo)
- `tareas/43-bbva-para-navar.md`

## Resultado esperado

1. `BotBbvaNavar`: login con los tres campos (un solo intento), confirma NAVAR SA y el CUIT, despliega
   las cuentas en pesos, abre la primera, lee el saldo, descarga; cambia a la segunda y descarga.
2. Validación de cada Excel: cuenta del encabezado = cuenta pedida, CUIT de NAVAR, fechas no más
   viejas que 65 días ni más de 4 días adelante (el banco fecha algunos débitos al día hábil
   siguiente). Una cuenta sin movimientos en 60 días no es error: se publica igual.
3. Publicación con temporal + `os.replace`, como Galicia. Correr dos veces el mismo día reemplaza.
4. `_ESTADO_BBVA_dd-mm.txt` y `_SALDOS_BBVA_dd-mm.txt` como cualquier banco (los escribe el núcleo).
5. `python setup_credenciales.py --cliente navar --banco bbva` pide código de empresa, usuario y clave.
6. `instalar_bbva.ps1`: tarea diaria 05:54 y 05:58 (después de Galicia, para no tener dos navegadores
   a la vez), log en `privado\bbva.log`. No se instala hasta que la prueba a mano salga bien.
7. Comentarios en criollo; sin datos reales en las pruebas.

## Comprobaciones

1. `python -m unittest bots.bbva.test_navar bots.galicia.test_navar` OK.
2. Prueba real en la notebook (la corre Thomas): actualizar, cargar credenciales, correr
   `python orquestador\correr.py --cliente navar --banco bbva --modo prueba` y mirar las capturas.
3. En la Mac: el lector lee los dos archivos publicados y los saldos coinciden con la pantalla.

## Qué hice

Lo escribió Claude (Thomas lo pidió así el 03/10; Codex sigue sin cupo).

- `bots/bbva/navar.py` — `BotBbvaNavar`, con el recorrido de Thomas:
  - Login: busca los tres campos por su `id` (`cod_emp`, `cod_usu`, `eai_password`) y, si cambian, por
    etiqueta. Si "Ingresar" no se enciende con los tres datos, prueba tecla por tecla; si sigue
    apagado, corta **sin apretar**. Después de Ingresar espera el CUIT de NAVAR (hasta 90 s).
  - Inicio: si la primera cuenta no está a la vista, aprieta el + de "Cuentas en pesos" (el botón de
    esa tarjeta a la izquierda del título; si no lo reconoce, aprieta el título). Abre la cuenta y
    confirma "Saldos y movimientos" + número de cuenta + botón Descargar.
  - Descarga cada cuenta, valida el Excel (cuenta del encabezado, CUIT, fechas entre hoy−65 y hoy+4) y
    publica `Movimientos BBVA <cuenta con guion> AAAA-MM-DD.xls` con temporal + `os.replace`.
  - Cambio de cuenta: clic en el número (`489-000765/9 (CC $)`), elige la otra en la lista, espera
    que la pantalla muestre la nueva y 1,5 s más.
  - Si una cuenta falla, la otra igual se publica y la corrida termina en error con el detalle.
  - Busca también dentro de iframes (el login trae uno).
- `nucleo/credenciales.py`: `guardar(..., extra)` y `dato_extra(...)`; `cargar` no cambia.
- `setup_credenciales.py`: con `--banco bbva` pide primero el código de empresa.
- `orquestador/correr.py`: `VARIANTES_NAVAR = ("galicia", "bbva")`; la carpeta de Drive se resuelve
  igual para las dos; el código de empresa se lee del llavero antes de abrir el navegador.
- `perfil.json` (bloque bbva): cuentas, prefijo, carpeta `Bancos/bbva`, visible, `incluir_hoy: false`
  (como Galicia: la segunda corrida del día ve que ya está al día y no vuelve a entrar).
- `instalar_bbva.ps1`: 05:54 y 05:58, log en `privado\bbva.log`.

Comprobaciones:
- `python -m unittest bots.bbva.test_navar bots.galicia.test_navar`: 57 OK. Lector: 30 OK.
- Pruebas nuevas con datos inventados: patrones de cuenta, nombre publicado, validación (cuenta
  distinta, otra empresa, fecha futura, vieja, sin movimientos), reemplazo del archivo del día, dos
  cuentas (cambia una vez; si falla una se publica la otra y avisa), sin código de empresa no abre el
  banco, llavero con el dato extra.
- Desde la Mac abrí la página de login real **sin credenciales**: encuentra los tres campos y el botón,
  que arranca apagado; con datos inventados se enciende con `fill` (no se apretó Ingresar).
- No probado: todo lo de después del login (desplegar cuentas, cambio de cuenta, Descargar). Se
  afina en la prueba en la notebook mirando las capturas. Tampoco hay rescate si la página se cierra
  al guardar (lo de Galicia del 28/09); se agrega si pasa.

## Revisión

**Claude, 03/10/2026 — primera prueba en la notebook.** El login entró (en la notebook `fill` no
encendió Ingresar y funcionó la carga tecla por tecla), pero a los 90 s no apareció el CUIT y se cortó.
Thomas vio que el inicio del banco tardaba mucho en abrir. Corrección: se espera hasta 4 minutos; el
inicio se reconoce por el CUIT, por "NAVAR SA" o por "Cuentas en pesos" (el CUIT del inicio vive en un
selector y puede no leerse como texto); mientras espera, cada 30 s anota la URL, si el formulario de
login sigue a la vista y deja una captura. Pruebas: 59 OK.
