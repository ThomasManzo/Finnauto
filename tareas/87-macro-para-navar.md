# Tarea 87 — bot de Macro para NAVAR
Estado: pendiente
Rama: tarea/macro-para-navar

## Objetivo
Que la notebook de NAVAR baje sola, todos los días, el Excel de movimientos de la cuenta corriente de
Macro (Banca Internet Empresas), lo controle, lo publique en Drive `NAVAR - Datos/Bancos/macro` y deje
`_ESTADO_` y `_SALDOS_`, igual que ya hacen Nación (`bots/nacion/navar.py`) y BBVA (`bots/bbva/navar.py`).
Si falla, queda en rojo en el `_ESTADO_` (el mail lo lee) y los reintentos del día no insisten con la
clave. **Los movimientos con fecha futura se dejan afuera y se avisan: no se tira el archivo entero.**

## Contexto
- Leer `AGENTS.md` y `CLAUDE.md`. Modelos a copiar: `bots/nacion/navar.py`, `bots/bbva/navar.py` (con sus
  `test_navar.py`), `orquestador/correr.py` (`VARIANTES_NAVAR`, `EXTRA_LLAVERO`, `--si-falta`, marca
  `CLAVE_ENVIADA_SIN_CONFIRMAR` de `bots/galicia/navar.py`) y `clientes/navar/herramientas/instalar_nacion.ps1`.
- **Seguridad, sin excepción** (el 28/09/2026 se filtraron las claves de Macro y el usuario se bloqueó):
  - Usuario, contraseña y clave empresa viven solo en el llavero (`finauto:navar:macro`). Nunca en el
    perfil, en logs, en nombres de archivo, en capturas ni en commits. No loguear el valor de ningún campo.
  - **No sacar capturas de pantalla mientras haya un campo de login con algo tipeado.** Las capturas de
    error del login se sacan ANTES de tipear o después de dejar la pantalla de login; si no se puede
    garantizar, no se saca captura en ese punto.
  - **Un solo intento de login por corrida.** Si algo no está como se espera (no hay exactamente un campo
    o un botón), se corta ANTES de tipear o de apretar. Si aparece captcha, token, código por SMS o
    segundo factor: se corta con un error claro y no se reintenta.
  - El repo es público: **nada de datos reales** (números de cuenta, montos, nombres) en código, pruebas
    ni en "Qué hice". Ojo: `lector/extractos.py` tiene un número de cuenta real escrito; no copiarlo.
    El número de cuenta NO va en el perfil: el bot lo lee de la pantalla y del Excel (ver abajo).

### El recorrido (relevado con `scripts/diagnostico_macro.py` el 09/11/2026 y capturas de Thomas)
Incluye también un arreglo chico al diagnóstico (ya hecho por Claude en `main`, no tocar).
Plataforma Technisys, todo en `https://www.macro.com.ar/biempresas/` (la dirección no cambia entre pantallas;
cada botón hace un envío del formulario). La página tiene un marco de Hotjar que no importa.
1. **Usuario.** Primera pantalla. *No se relevó el campo* (la foto falló). Buscar el único campo visible
   que no es de clave, por etiqueta o placeholder que diga "Usuario"; y el único botón para avanzar
   ("Continuar", "Ingresá", "Siguiente" o similar). Si no hay exactamente uno de cada, cortar sin tipear.
2. **Contraseña.** Texto "Ingresá la contraseña que generaste en la Nueva App Macro…". Campo
   `input#login_textField2` (type=password, placeholder "Contraseña nueva app Macro"), botón
   `button#processSystem_UserLogin` ("INGRESÁ"). Hay un cartel fijo del banco que dice "ALERTA
   VIRUS/ESTAFAS … NO INGRESES TOKEN": es publicidad de seguridad, **no** es un pedido de token (no
   frenar por la palabra "TOKEN" sola; sí por un campo o pedido de código/token).
3. **Clave empresa.** Título "Ingreso a Banca Internet Empresas", "Ingresá la clave empresa", fila
   "NAVAR SA". Campo `input#login_textField1` (type=password, etiqueta "Clave empresa"), botón
   `button#actionButtonInit2` ("Ingresar"). Confirmar que la fila dice NAVAR SA antes de tipear.
   Desde que se apretó el botón de la contraseña, cualquier falla del login lleva la marca
   `CLAVE_ENVIADA_SIN_CONFIRMAR` (el orquestador ya cuenta 2 por día y frena).
4. **Inicio.** Arriba dice NAVAR SA. **Puede aparecer un cartel encima (ej. "Ya podés generar tu ID
   FAL…") con una cruz para cerrar: cerrarlo si está.** Puede no estar; puede ser otro. No apretar nada
   del cartel salvo la cruz/cerrar. Tabla `table#collectionTableCuentas` (Cuenta · Número · Disponible ·
   Acciones), una fila "CUENTA CORRIENTE BANCARIA". De esa fila leer el **Número** (para comparar con el
   Excel) y el **Disponible** (saldo, negativo con formato `$-1.234.567,89`).
   **Ojo:** el botón XLS de "Descargar listado completo" del inicio (`#actionButtonDescargaXlsCuentas`)
   baja "Consolidada Cuentas.xls", que trae **solo la lista de cuentas con el saldo, sin movimientos.
   Ese NO sirve.**
5. **Cuenta.** Clic en `td#collectionTableCuentas_ON-REGISTER` (texto "CUENTA CORRIENTE BANCARIA"; Thomas
   entra tocando el número de la cuenta en esa misma fila, también sirve). Se confirma que se está
   adentro por el título `p[role=heading]` "CUENTA CORRIENTE BANCARIA" y la solapa activa `button#logMov`
   ("Últimos movimientos"). Arriba a la izquierda: Tipo · **Número** · Moneda (comparar el Número con el
   del inicio). Arriba a la derecha: **"Saldo disponible"** (`label#constantLabel0`; es el saldo real de
   la cuenta, negativo: coincide con el Saldo del renglón más nuevo de la tabla), **"ACUERDO"** y
   **"SALDO A GIRAR"** (= acuerdo + saldo). Tabla `table#collectionTableMovimientos`, paginada.
6. **Pedido del XLS.** Al pie, "Descargar listado completo" con botones PDF · **XLS** · TXT · MacrOnline ·
   TXTComas. El XLS tiene **el mismo id** que el del inicio (`#actionButtonDescargaXlsCuentas`): apretarlo
   solo después de confirmar el paso 5. **No baja en el momento**: aparece abajo el cartel "Te informamos
   que estamos procesando la descarga. En unos minutos podrás visualizarla en Más > Consultas y
   solicitudes > Bandeja de descargas" con el botón **"IR A BANDEJA DE DESCARGAS"**. Anotar la hora del
   pedido (como Nación con la notificación).
7. **Bandeja de descargas** (botón del cartel; si no aparece, por el menú Más > Consultas y solicitudes >
   Bandeja de descargas). Título "Bandeja de Descargas", botón redondo de recargar arriba a la derecha y
   una tabla: Descripción · Nombre · Extension · Fecha de inicio · Fecha de Fin · Estado. Cada fila:
   "Últimos Movimientos" · "Ultimos_Movimientos" · "xls" · `dd/mm/aaaa h:mm` · `dd/mm/aaaa h:mm` ·
   "Finalizado" + **flechita naranja de descarga** (ícono sin texto: ubicarlo dentro de la celda Estado de
   esa fila). Quedan las descargas de días anteriores: **elegir la fila de ESTE pedido** = descripción
   "Últimos Movimientos", extensión xls, Fecha de inicio igual o posterior a la hora del pedido (con 2
   minutos de margen por relojes corridos; si hay varias, la más nueva) y Estado "Finalizado". Si todavía
   no está o no dice Finalizado: recargar cada 10 s, hasta 180 s; después, falla con motivo claro. Las
   selecciones de esta pantalla **no se relevaron**: buscarlas por texto y estructura, y si no hay
   exactamente una fila candidata, cortar con captura (acá ya no hay claves a la vista). La flechita baja
   directo (`page.expect_download`) "Ultimos_Movimientos.xls".
8. **Salir** con `a#widgetLogoutBtn` al terminar (si falla el salir, solo se avisa en el log).

### El Excel bueno ("Ultimos_Movimientos.xls", .xls viejo de JasperReports; ejemplo inventado)
```
Últimos Movimientos
CUENTA CORRIENTE BANCARIA
Tipo     | | Cuenta Corriente
Número   | | 123456789012345
Moneda   | | PESOS
Fecha | | | Nro. de Referencia | Causal | Concepto | Importe | | | | Saldo
05/11/2026 (celda fecha) | | | 1000001 | 123 | DEBITO PRESTAMOS REC | -1000.00 | | | | -2000.00
04/11/2026 ...                                                            ...              -1000.00
...
Fecha de descarga: 06/11/2026 08:50:00
Empresa: 30111111118 - EMPRESA DE PRUEBA SA
Operador: Persona Inventada
```
Del más nuevo al más viejo; unos 25-30 días. `lector/extractos.py:leer_planilla_macro` ya lo lee (y
`_filas_planilla` lee .xls y .xlsx).

## Archivos permitidos
- `bots/macro/__init__.py`, `bots/macro/navar.py`, `bots/macro/test_navar.py` (nuevos)
- `orquestador/correr.py` (sumar `macro` a `VARIANTES_NAVAR`, `EXTRA_LLAVERO` y la elección del bot)
- `setup_credenciales.py` (Macro pide tres datos; ver abajo)
- `clientes/navar/perfil.json` (solo el bloque `bancos.macro`)
- `clientes/navar/herramientas/instalar_macro.ps1` (nuevo)
- `nucleo/loop.py` y `nucleo/salidas.py`: **solo** lo mínimo para los avisos (ver abajo)
- esta consigna (sección "Qué hice" y `Estado:`)

## Resultado esperado
1. **`setup_credenciales.py --cliente navar --banco macro`** pide usuario (puede verse), contraseña y
   **clave empresa ocultas** (`getpass`, las dos). La clave empresa se guarda como dato extra
   `clave_empresa` en el mismo secreto. Los otros bancos no cambian.
2. **`bots/macro/navar.py`**, clase `BotMacroNavar(BotBanco)`, `nombre = "Macro"`, con el recorrido de
   arriba. Reusar las ayudas de BBVA/Nación (`_esperar_unico`, `_hay_visible`, `publicar`, etc.).
   - Una sola empresa (NAVAR SA), como Nación: `descubrir_empresas` → `[]`.
   - `aplicar_filtro_fechas`: no filtra (el export trae lo que trae), devuelve True.
   - `capturar_saldos`: `actual` = "Saldo disponible" de la cuenta (si no se lee, el "Disponible" de la
     tabla del inicio); `disponible` = "SALDO A GIRAR"; guardar también el "ACUERDO" en el texto del log.
     Si no se leen, no corta. Montos con formato `$ -49.596.953,29`.
   - **Saldo de pantalla y movimientos futuros** (visto el 09/11: la tabla traía un movimiento del 11/11 y
     el "Saldo disponible" ya lo incluía). Después de validar el Excel, el `saldo_actual` que va a
     `_SALDOS_` es el de la pantalla **solo si coincide con el Saldo del renglón más nuevo que queda
     publicado**. Si no coincide (por ejemplo, porque se sacaron futuros), `saldo_actual` va en `None`, el
     texto de pantalla se conserva en `saldo_actual_texto` y se suma un aviso. Así el lector nunca toma
     un saldo que incluye movimientos que no están en el archivo.
   - `extraer_cuenta_id`: el número de la fila "Número" del Excel (solo dígitos).
3. **Control del Excel antes de publicar** (`validar_excel`, función pura, testeable):
   - título "Últimos Movimientos" y "CUENTA CORRIENTE BANCARIA", moneda PESOS;
   - el Número del Excel = el Número leído en el inicio (solo dígitos); si difieren, no se publica;
   - el pie "Empresa: <CUIT> - …" trae el CUIT de NAVAR (`PATRON_CUIT` de `bots/bbva/navar.py`);
   - el pie "Fecha de descarga: dd/mm/aaaa hh:mm:ss" es igual o posterior a la hora del pedido (2 min de
     margen): si es más viejo, es un archivo de otro día de la bandeja y no se publica;
   - la **cadena de saldos** cierra al centavo (cada saldo = saldo del renglón más viejo + importe);
   - ningún movimiento más viejo que `dias_atras_tolerados` (perfil, 45);
   - **fechas futuras (fecha > hoy): esos renglones se sacan y se avisan.** Si quedan movimientos, se
     publica una copia limpia en **.xlsx** con el mismo formato (encabezado, renglones que quedan, pie)
     para que `leer_planilla_macro` la lea igual; si no había futuros, se publica el .xls original tal
     cual. El aviso dice cuántos renglones, de qué fechas y la suma de sus importes (sin conceptos).
     Como el Excel va del más nuevo al más viejo, sacar los de arriba no rompe la cadena.
   - Cualquier otro problema: no se publica y la corrida falla con el motivo.
4. **Publicación**: `Movimientos Macro AAAA-MM-DD.xls` (o `.xlsx` si es la copia limpia) en la carpeta
   de Drive del perfil (`carpeta_drive_relativa: "Bancos/macro"`), con el temporal + `os.replace` de BBVA.
   Temporales `macro_por_validar_*` en la carpeta de descargas, limpiados a la semana. Si el archivo trae
   0 movimientos, no se publica y es "sin novedades" (como Nación).
5. **Avisos en el `_ESTADO_`**: el bot deja sus avisos en `self.avisos` (lista de textos). `nucleo/loop.py`
   los junta en `resultado["avisos"]` si el bot los tiene (con `getattr`, para no tocar a los otros bancos)
   y `escribir_estado_drive` agrega al final una línea `AVISO: …` por cada uno. **La línea
   "OK: no fallo ninguna empresa." no cambia** (el `--si-falta` y el mail dependen de ella).
6. **Orquestador**: `--banco macro` para `--cliente navar` usa `BotMacroNavar`; la clave empresa sale del
   llavero (`EXTRA_LLAVERO["macro"] = "clave_empresa"`). Si falta, error claro que nombra
   `setup_credenciales.py --cliente navar --banco macro`, sin abrir el banco.
7. **Perfil** (`bancos.macro`): `activo: false`, `solo_estas_empresas: ["NAVAR SA"]`, `solo_empresa_activa:
   true`, `nombre_archivo: "excel_navar"`, `prefijo_archivo: "Movimientos Macro"`, `modo_visible: true`,
   `carpeta_drive_destino: ""`, `carpeta_drive_relativa: "Bancos/macro"`, `incluir_hoy: false`,
   `dias_atras_tolerados: 45`, `limite_segundos: 600`, y una `_nota` en criollo. Sin número de cuenta.
8. **`instalar_macro.ps1`**, copia de `instalar_nacion.ps1`: tarea `finauto NAVAR Macro`, log
   `clientes\navar\privado\macro.log`, `--si-falta`, horas `06:25, 06:30, 07:05, 09:05, 12:05, 16:05`, y
   la opción `quitar`.
9. Comentarios en criollo en todo (Thomas no programa): qué hace cada paso y por qué.

## Comprobaciones
- `python -m unittest bots.macro.test_navar` con Excel **inventados** armados en la prueba (.xlsx con el
  formato de arriba). Casos mínimos: archivo bueno; número de cuenta distinto; CUIT de otra empresa;
  cadena de saldos rota; movimiento demasiado viejo; **dos renglones con fecha futura → se sacan, se
  avisa, la copia limpia la lee `leer_planilla_macro` con los movimientos que quedan y la cadena sigue
  cerrando**; todos futuros → no se publica nada; sin movimientos → sin novedades; "Fecha de descarga"
  anterior al pedido → no se publica; lectura de montos `$ -1.234.567,89` → -1234567.89.
- Elección de la fila de la bandeja (función pura con textos inventados, como `elegir_notificacion` de
  Nación): filas de días anteriores no sirven; la de este pedido sí; margen de reloj; "En proceso" no
  sirve todavía; dos del pedido → la más nueva; ninguna → None.
- Saldo para `_SALDOS_`: pantalla igual al renglón más nuevo → se usa; distinto (había futuros) → `None`
  + aviso.
- Prueba de que el `_ESTADO_` con avisos sigue diciendo "OK: no fallo ninguna empresa." y suma las
  líneas `AVISO:`; y de que sin avisos queda igual que antes.
- `python -m unittest bots.nacion.test_navar bots.bbva.test_navar bots.galicia.test_navar` y
  `python -m unittest discover tests` siguen pasando.
- `setup_credenciales.py`: prueba de que para `macro` la clave empresa se pide con `getpass` (simulando
  `input`/`getpass`), sin tocar el llavero real.
- No se puede probar contra el banco (no hay claves en el worktree): la prueba real la hace Claude con
  Thomas en la notebook.

## Qué hice

## Revisión
