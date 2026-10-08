# Tarea 56 — Nación para NAVAR: bot de BNA+ Empresas y lector de su Excel
Estado: lista para revisión
Rama: tarea/nacion-navar

## Objetivo

Que la notebook de NAVAR baje sola los movimientos de la cuenta corriente de Nación y los deje en
`NAVAR - Datos/Bancos/nacion/`, y que el lector de extractos entienda ese Excel. Hoy Nación llega
escaneado y la notebook no puede leerlo.

## Contexto

El 07/10/2026 Thomas tuvo acceso de consulta a la cuenta en BNA+ Empresas y describió el recorrido:

1. Login en `https://digital.bna.com.ar/loginStep1`: DNI + usuario → "Continuar" → contraseña →
   "Continuar" → inicio de BNA+ Empresas (dice NAVAR SA). No pide token para consultar.
2. Inicio → "Mis cuentas" → clic en la cuenta (CUENTA CORRIENTE PESOS) → "Detalle de cuenta" con
   Saldo, Saldo disponible y "Movimientos".
3. **La descarga es diferida**: "Descargar" → "Archivo XLS" muestra "Estamos generando tu archivo.
   Cuando esté listo, podrás descargarlo desde tus notificaciones". Unos segundos después aparece en
   la campanita una notificación "Descarga de listado"; al abrirla se ve el adjunto
   `Ultimos movimientos.xls`, que se descarga con un clic.
4. Para que el archivo sea chico y salga rápido, antes se usa "Filtrar": Desde / Hasta → "Buscar".

El Excel (formato viejo `.xls`): encabezado "Banco Nación [BNA + Empresas]" / "Últimos movimientos" y
la tabla **Fecha · Comprobante · Concepto · Monto · Saldo**, del más nuevo al más viejo. Importes como
texto (`$ -1.234,56`). **No trae el número de cuenta.** Mirando la cadena, el Saldo de cada renglón es
el de **antes** del movimiento: el saldo de después = Saldo + Monto (el último renglón cierra con el
saldo de la pantalla).

Lo que se vio en el código de la página (sin entrar): el paso 1 del login devuelve si hay que mostrar
captcha (`showCaptcha`), y la página carga BioCatch (análisis de comportamiento). Si aparece el "No soy
un robot", **el bot para** y no intenta resolverlo.

## Archivos permitidos

- `lector/extractos.py` — `leer_planilla_nacion` y su registro en `BANCOS`.
- `lector/pruebas/test_nacion_planilla.py` (nuevo)
- `bots/nacion/__init__.py`, `bots/nacion/navar.py`, `bots/nacion/test_navar.py` (nuevos)
- `orquestador/correr.py`, `nucleo/credenciales.py`, `setup_credenciales.py` — Nación como variante
  NAVAR y el DNI como dato extra del llavero.
- `clientes/navar/perfil.json` — solo el bloque `bancos.nacion`.
- `clientes/navar/herramientas/instalar_nacion.ps1` (nuevo)
- `tareas/56-nacion-para-navar.md`

## Resultado esperado

1. `leer_planilla_nacion`: lee el Excel, toma la cuenta del **nombre del archivo** (13-14 dígitos; lo
   pone el bot), controla la cadena de saldos (detecta si el Saldo es antes o después del movimiento;
   si no cierra de ninguna forma, el archivo no se lee) y da el saldo al cierre de cada día.
2. `BotNacionNavar`: login en dos pasos (un solo intento; se frena si aparece captcha), confirma NAVAR,
   abre la cuenta, filtra los **últimos días** (perfil `dias_a_bajar`, 5 por defecto: si un día falla,
   el siguiente lo recupera; el lector no duplica), pide el XLS, espera la notificación nueva (hasta 3
   minutos), baja el adjunto, lo valida (cadena de saldos y fechas dentro del filtro) y publica
   `Movimientos Nacion <cuenta> AAAA-MM-DD.xls`.
3. `setup_credenciales.py --banco nacion` pide DNI, usuario y clave (los tres al llavero).
4. `instalar_nacion.ps1`: 06:02 y 06:06, después de Galicia. No se instala hasta que la prueba a mano
   salga bien.
5. Pruebas con datos inventados.

## Comprobaciones

1. Pruebas nuevas y las existentes de lectores y bots OK.
2. En la Mac, el lector con el Excel real: la cadena cierra y el saldo final es el de la pantalla
   (se anota en el LEEME, no acá).
3. Prueba real en la notebook (la corre Thomas) con `--modo prueba`.

## Qué hice

Lo escribió Claude (03-07/10 Thomas pidió que los bots los escriba Claude).

- `lector/extractos.py`: `leer_planilla_nacion` + registro en `BANCOS` (Nación ahora acepta planilla
  además de PDF). Cuenta del nombre del archivo; prueba la cadena con el Saldo "de antes" y "de
  después" y usa la que cierra; si ninguna, error. Importes `$ -1.234,56` con `_monto_nacion`.
- `bots/nacion/navar.py`: `BotNacionNavar` con el recorrido de Thomas. Usa los ayudantes de espera de
  `bots/bbva/navar.py`. Frena si aparece un reCAPTCHA visible (la casilla o la prueba; el sellito
  invisible no cuenta). Filtro: los dos campos de fecha del panel se reconocen por tener una fecha
  dd/mm/aaaa; se cargan con `fill` + Tab y se verifica que quedaron. La notificación se elige por su
  hora (la más nueva desde el pedido, con 2 minutos de margen); si no llegó, vuelve a Inicio y
  reabre la campanita cada 10 s, hasta 3 minutos. La campanita se busca por nombre accesible
  ("notificación"/"mensaje"); si no se reconoce, va a la bandeja por la ruta de la plataforma
  (`/communications`, no verificada).
- `orquestador/correr.py`: Nación como variante NAVAR; `EXTRA_LLAVERO` (BBVA código de empresa,
  Nación DNI). `setup_credenciales.py` pide el DNI con `--banco nacion`.
- `perfil.json` (bloque nacion): cuenta, prefijo, `dias_a_bajar: 5`, carpeta, visible. Se sacó una
  nota vieja con datos de situación crediticia.
- `instalar_nacion.ps1`: 05:52 y 05:57, log `privado\nacion.log`.

Comprobaciones:
- Pruebas: bots 75 OK (Nación 15 nuevas), lectores OK (5 nuevas de Nación). Todo con datos inventados.
- Lector con el Excel real del 07/10: cadena OK y saldos coinciden con la pantalla y con la Sheet
  (anotado en el LEEME, no acá).
- Login real abierto desde la Mac **sin credenciales**: encuentra DNI (`#document`), usuario
  (`#username`) y Continuar (apagado hasta cargar datos). No se apretó Continuar.
- No probado: todo lo de después del login (campanita, filtro, adjunto). Se afina con la prueba en
  la notebook mirando las capturas.

## Revisión
