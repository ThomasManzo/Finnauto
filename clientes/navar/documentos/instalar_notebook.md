# Dejar finauto instalado en la notebook de NAVAR (Windows)

Para hacerlo por AnyDesk, de una sentada (~1 hora). Al terminar, la notebook hace sola lo que hoy
hace tu Mac: mira `NAVAR - Datos` en Drive y corre los lectores. Después, sobre esto mismo, se
suman la bajada de Tango por API y los bots de banco. Adentro de la sesión el Windows espera
`Ctrl` donde vos usás `Cmd` (Ctrl+C, Ctrl+V).

## 0. Antes de empezar (lo que tiene que existir)

- Un **usuario de Windows "finauto"** en la notebook, con clave que no vence (lo crea sistemas o
  el administrador de la máquina). Todo lo que sigue se hace **logueado con ese usuario**: las
  tareas programadas y las claves guardadas quedan atadas a él.
- Conexión a internet y a la red donde está el servidor de Tango (`servidor:17000`).

## 1. Google Drive para escritorio (10 min)

1. Descargar de google.com/drive/download e instalar.
2. Iniciar sesión con **finanzasnavar@gmail.com** (la cuenta de la empresa). Si `NAVAR - Datos`
   todavía es tuya, compartila con esa cuenta como Editor antes (Drive → clic derecho → Compartir).
3. En la configuración de Drive: **"Transmitir archivos"** (streaming) está bien, pero marcar
   `NAVAR - Datos` como **"Disponible sin conexión"** (clic derecho sobre la carpeta en el
   Explorador → Sin conexión), así los lectores siempre encuentran los archivos completos.
4. Verificar: en el Explorador aparece `G:\Mi unidad\NAVAR - Datos` (la letra puede ser otra).

## 2. Python (5 min)

1. python.org → Downloads → Windows → **Python 3.12** (64 bits). Al instalar, tildar
   **"Add python.exe to PATH"**. Instalar para todos los usuarios si lo pide.
2. Abrir PowerShell y comprobar: `python --version` → `Python 3.12.x`.
   Si dice que abre la tienda de Microsoft, cerrarla y usar la ruta completa:
   `C:\Users\finauto\AppData\Local\Programs\Python\Python312\python.exe`.

## 3. El repo finauto (10 min)

Sin git: GitHub → `ThomasManzo/Finnauto` → botón verde **Code → Download ZIP**. Descomprimir
en **`C:\finauto`** (que quede `C:\finauto\finauto.py`, no `C:\finauto\Finnauto-main\...`).
Para actualizar después (cada vez que Claude suba algo), un solo comando en PowerShell, sin
bajar nada a mano:

```powershell
powershell -ExecutionPolicy Bypass -File C:\finauto\clientes\navar\herramientas\actualizar.ps1
```

Baja la última versión de GitHub y pisa los archivos sin tocar el entorno, la memoria del
vigilante ni lo privado (las claves están en el llavero, no en archivos).

En PowerShell:

```powershell
cd C:\finauto
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
```

Si PowerShell se queja de "scripts deshabilitados" al activar el entorno, no hace falta
activarlo: siempre se llama a `.\.venv\Scripts\python.exe` directo, como arriba.

Comprobar que ve el Drive:

```powershell
.\.venv\Scripts\python.exe -c "from ingestas.drive_local import carpeta_datos; print(carpeta_datos())"
```

Tiene que imprimir la ruta a `NAVAR - Datos`. Si la carpeta es COMPARTIDA con la cuenta (no
propia), Drive la monta como acceso directo en `G:\.shortcut-targets-by-id\<id>\NAVAR - Datos`:
también la encuentra sola. Si imprime `None`: Drive no está montado; se puede fijar a mano con
la variable de entorno `FINAUTO_DRIVE` (a nivel Usuario, así la tarea programada la ve).

## 4. El vigilante (5 min)

```powershell
.\.venv\Scripts\python.exe clientes\navar\herramientas\vigilante.py --simular
powershell -ExecutionPolicy Bypass -File clientes\navar\herramientas\instalar_vigilante.ps1
```

Lo primero dice qué haría (tiene que reconocer bancos / tango / deuda / impuestos). Lo segundo
crea la tarea "finauto NAVAR vigilante" cada 15 minutos. Se ve en el Programador de tareas.
Log: `clientes\navar\privado\vigilante.log`.

**En la Mac, ese mismo día**, desinstalar el vigilante para que no corran dos:
`zsh clientes/navar/herramientas/instalar_vigilante.sh quitar`.

Limitación conocida: los PDF **escaneados** (el Nación de septiembre) solo se OCR-ean en la Mac.
Pero el resultado del OCR queda en `Bancos\nacion\.ocr\` dentro del Drive, y la notebook lo usa
tal cual. Si aparece un escaneado nuevo sin caché, el lector de bancos corta con un error claro
(no publica un para_pegar sin ese banco): se lee una vez en la Mac o se pide el extracto en Excel.

La primera corrida en la notebook relee las cuatro fuentes (no tiene memoria de qué procesó):
es normal y el control "se achicó de golpe" protege la Sheet.

## 5. Tango Live por API (primera corrida supervisada y tarea diaria)

El token ya se genera desde Live: abrir una consulta → Apertura → API → **Obtener token** y
copiarlo. No pegarlo en la pantalla de clave oculta de Python a través del escritorio remoto:
esa combinación puede guardar un carácter de más, uno de menos o el código de Ctrl+V. Se guarda
directamente desde el portapapeles, con formato validado, y nunca pasa por un archivo:

```powershell
cd C:\finauto; $null = Read-Host "Copia el token con Ctrl+C y despues apreta Enter aca"; Get-Clipboard | .\.venv\Scripts\python.exe -c "import sys,re; from nucleo import credenciales as c; t=sys.stdin.read().strip(); assert re.fullmatch(r'[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}', t), 'NO parece un token (%d caracteres), no guardé nada' % len(t); c.guardar('.','navar','tango_live','finanzasnavar@gmail.com',t); print('guardado ok', len(t))"
```

Después, en este orden:

1. **Prueba de estructura**, sin mostrar nombres ni montos. Confirma la dirección real de API,
   la consulta personalizada, las columnas y el total informado:
   ```powershell
   .\.venv\Scripts\python.exe ingestas\tango_live.py --cliente navar --probar cobranzas --empresa A
   ```
2. **Primera bajada a una carpeta local**, no a Drive. Genera las ocho fotos (cuatro de A y
   cuatro de AA) para comparar encabezados, estados y cantidades antes de publicar:
   ```powershell
   New-Item -ItemType Directory -Force C:\finauto\clientes\navar\privado\tango_api_prueba | Out-Null
   .\.venv\Scripts\python.exe ingestas\tango_live.py --cliente navar --destino C:\finauto\clientes\navar\privado\tango_api_prueba
   ```
   Confirmar especialmente que salgan las ocho `customQuery` configuradas. Todas las consultas
   piden fechas vacías salvo cheques propios: esa foto usa desde hoy menos 60 días, para cubrir
   el margen que necesita el lector sin traer pendientes históricos desde 1995. Los conteos de
   estados y los pares `Tipo/Clase` quedan en el log como control contra cambios futuros de Live.
3. **Bajada real a Drive**, recién después de aprobar la comparación:
   ```powershell
   .\.venv\Scripts\python.exe ingestas\tango_live.py --cliente navar
   ```
   Los archivos quedan con los mismos nombres y encabezados que los exports manuales. El
   vigilante procesa Cuentas a cobrar, Cuentas a pagar, Cheques y `Tesoreria AA` como siempre.
4. **Programar todos los días a las 05:45**:
   ```powershell
   powershell -ExecutionPolicy Bypass -File clientes\navar\herramientas\instalar_tango.ps1
   ```
   La tarea se llama `finauto NAVAR Tango`, no arranca una segunda instancia si la anterior
   sigue corriendo y corta después de una hora. El historial queda agregado en
   `clientes\navar\privado\tango_live.log`. Para quitarla, agregar `quitar` al comando.

## 6. Galicia: preparación y primera prueba en la notebook

**Recorrido preparado a partir de una prueba manual, todavía pendiente de una corrida completa del
bot.** La variante entra directo al login, abre la tarjeta de la única cuenta, lee los saldos y baja
la opción Excel. No abre el menú Cuentas ni usa filtros de fechas: Galicia entrega por defecto unos
30 días de movimientos.

1. Con el mismo usuario de Windows que correrá la tarea, desde `C:\finauto`, cargar las
   credenciales **en la notebook**. La administración las tipea sin compartirlas:
   ```powershell
   .\.venv\Scripts\python.exe setup_credenciales.py --cliente navar --banco galicia
   ```
   Es el equivalente a `python setup_credenciales.py --cliente navar --banco galicia` con
   el entorno elegido. Quedan en el llavero `finauto:navar:galicia` de esa máquina y usuario.
2. No completar una ruta local en el perfil. Con `carpeta_drive_destino` vacío, el orquestador
   encuentra `NAVAR - Datos` en el Drive montado y le suma `Bancos/galicia`. Si esa detección no
   funciona en una máquina particular, se puede fijar `carpeta_drive_destino` como excepción.
   Antes de pedir las credenciales, el comando frena y dice qué ruta buscó si la carpeta no existe.
   Se acepta el nombre corto o el nombre legal completo de la única empresa, pero el estado siempre
   guarda la misma clave. Se espera sólo la cuenta configurada. `activo: false` evita las corridas
   generales; **el comando con --banco explícito sí corre aunque esté en false**.
3. **No existe --simular en este orquestador.** No usar `--modo prueba` como simulación:
   entra al banco, descarga, publica y guarda estado. Para la primera prueba supervisada,
   pausar temporalmente la tarea del vigilante y ejecutar:
   ```powershell
   .\.venv\Scripts\python.exe orquestador\correr.py --cliente navar --banco galicia --modo prueba
   ```
   Log: `clientes/navar/.run/galicia/log.txt`. Capturas:
   `clientes/navar/.run/galicia/capturas/`. No subirlas a git: pueden contener datos reales.
4. Seguir la primera corrida con las capturas, en este orden:
   - `pantalla_login`: formulario directo con un único Usuario, una única Clave y un único Ingresar
     visibles. El bot no toca «Recordar usuario» y hace un solo intento.
   - `post_login`: el formulario desapareció y el nombre de la empresa quedó visible.
   - `inicio`: aparece la tarjeta con `N° 0005459-5 070-1`; el bot hace clic directamente ahí.
   - `cuenta_abierta`: la URL contiene `/cuentas/movimientos` y el título muestra esa cuenta.
   - `saldos`: se intentó leer Actual y Disponible. Si uno no se puede leer, queda avisado en el
     log pero los movimientos siguen.
   - `menu_descarga`: se abrió el botón junto a Filtros y aparece la opción exacta `Excel`.

   El archivo que entrega el banco debe llamarse como `Extracto_CC545950701.xlsx`. Ese nombre es
   la confirmación de cuenta que aporta la descarga, porque el contenido no trae el número. Antes
   de publicar, el lector exige movimientos, rechaza fechas futuras y también movimientos de más
   de 35 días. Si pasa, se copia como `Movimientos Galicia AAAA-MM-DD.xlsx` en `Bancos/galicia`;
   otra corrida del mismo día reemplaza ese archivo. Si la validación o la publicación falla, el
   temporal de esa corrida queda para revisar como
   `.run/galicia/descargas_temp/galicia_por_validar_<fecha>_<identificador>.xlsx`.

   Cada corrida vuelve a bajar aproximadamente los últimos 30 días del banco. El lector elimina los
   movimientos repetidos entre archivos; el estado solo marca hasta qué día se bajó. Si el bot falla varios días,
   la primera corrida que vuelva a funcionar recupera sola hasta esos 30 días. Un corte mayor puede
   dejar un hueco y requiere un extracto manual. Estado: `.run/galicia/estado_descargas.json`; no
   borrarlo a ciegas.
5. Sólo cuando pase la comparación, reanudar el vigilante y revisar su log y Registro en la
   Sheet. Desde `C:\finauto`, instalar la tarea **finauto NAVAR Galicia** con:
   ```powershell
   powershell -ExecutionPolicy Bypass -File clientes\navar\herramientas\instalar_galicia.ps1
   ```
   La notebook tiene que estar **prendida y sin suspenderse a las 05:45**, con Drive montado y
   con la sesión del mismo usuario que cargó las claves iniciada. A las **05:45 y 05:48** el
   navegador se abre solo porque por ahora el perfil de Galicia está en modo visible.
   La segunda corrida es el seguro si la primera falla en frío; reemplaza el archivo del día
   sin duplicar movimientos.

   En el Programador de tareas, elegir **finauto NAVAR Galicia** y usar «Ejecutar». Comprobar el
   archivo en `Bancos\galicia\`, el log en `clientes\navar\privado\galicia.log` y después Registro
   en la Sheet. El horario solo no certifica funcionamiento. Revisar también una pasada posterior
   del vigilante, a las 05:53/06:08: corre cada 15 minutos y, si Galicia tarda, recoge el Excel en
   la siguiente. El comando explícito no requiere activar las corridas generales.

### Qué puede fallar la primera vez

| Señal | Qué revisar |
|---|---|
| Login no avanza | `pantalla_login`, `login_enviado`, `post_login`, `ERROR_formulario_login` y `ERROR_login_no_confirmado`. El error indica si faltó un campo o si había más de uno visible. El bot hace un solo intento y no resuelve un segundo factor. Revisar con administración. |
| «Usuario ya conectado» | `post_login` y último error. Cerrar la sesión anterior de forma normal; el bot no fuerza su cierre. |
| Empresa no reconocida | `post_login` y `ERROR_*`. Se acepta el nombre corto o legal en cualquier parte visible de la página; no se abre el selector de empresas ni se hacen clics por coordenadas. |
| Cuenta no encontrada / no abre | `inicio`, `cuenta_abierta` y `ERROR_*`. Debe haber una sola tarjeta visible con el número configurado; al abrir se controlan URL y título. No se elige otra cuenta como reemplazo. |
| No se pudieron leer saldos | `saldos` y el aviso del log para Actual o Disponible. La descarga continúa; no se inventa un saldo. Comparar ambos importes con la pantalla antes de automatizar. |
| No aparece Excel o el archivo no pasa controles | `menu_descarga`, `ERROR_*` y Excel local. Revisar opción, extensión, número de cuenta en el nombre, encabezados, movimientos y fechas. No renombrar CSV a XLSX. |
| Al guardar aparece `Target page, context or browser has been closed` | El bot intenta rescatar solo el archivo nuevo que dejó el navegador: espera hasta 30 s, exige un único archivo estable durante 2 s y zip válido, y después valida el Excel antes de publicar. También busca en `C:\Users\<usuario>\Downloads\<guid>.tmp`: lo copia al temporal y lo borra de Descargas; si no puede borrarlo, avisa. En esa carpeta exige GUID nuevo y fecha posterior al clic. Si igual falla, mirar el log (cierre, caída o pestaña nueva y qué archivo encontró) y `.run/galicia/descargas_temp/`. El temporal se conserva si falla la validación o publicación. |
| Drive o tarea fallan | Usuario de Windows, sesión iniciada, Drive montado, ruta informada en el error y `log.txt`. Un error de configuración puede aparecer sólo en consola antes de crear log. |

Todo el recorrido de pantalla todavía necesita la corrida supervisada del bot. Revisar las capturas
en orden; pueden pisarse entre corridas, por lo que conviene conservar la evidencia local antes de
repetir. No se probaron con este cambio el login real, los clics, la lectura de saldos, la descarga,
los permisos, la sincronización de Drive ni la tarea programada. Los otros bancos siguen
desactivados y sin adaptación en esta tarea.

## Qué queda corriendo, en orden, cada mañana

| Hora | Qué | Dónde deja |
|---|---|---|
| 05:45 | Tango y Galicia | Carpetas de Tango y `Bancos\galicia\` · logs `privado\tango_live.log` y `privado\galicia.log` |
| 05:48 | Galicia (seguro si falla en frío) | Reemplaza el Excel del día en `Bancos\galicia\` |
| 05:53 / 06:08 | vigilante → lectores (sigue cada 15 min) | `_para la Sheet\` |
| 06:15–06:45 | importación diaria de la Sheet, además de la de cada hora | solapas de la Sheet + Registro |
| 07:00 | Objetivo: cash al día | Verificar Registro y fechas de los datos |
| 07:30 (07:15–07:45) | Aviso diario por mail | Mail de la empresa |

La notebook debe estar **prendida y sin suspenderse a las 05:45**. Después de pegar los dos
scripts nuevos, `importar_cashflow.gs` y `aviso_diario.gs`, correr una vez
**`instalarDisparador`** y una vez **`instalarAvisoDiario`** desde el editor de Apps Script.
Los disparadores viejos conservan el horario anterior hasta que se reinstalan.

La primera función reemplaza los activadores de `importarLoNuevo`, incluido el diario cargado
a mano, y deja exactamente dos: uno por hora y otro diario alrededor de las 06:30. El activador
manual ya no hace falta. La segunda reemplaza sólo el aviso y deja uno diario cerca de las
07:30, en Buenos Aires. La importación usa la zona horaria del proyecto (Buenos Aires).

Google puede adelantar o atrasar `nearMinute(30)` hasta 15 minutos: la importación diaria corre
entre 06:15 y 06:45, después de las pasadas del vigilante de 05:53/06:08; el aviso entre 07:15
y 07:45. El objetivo de las 07:00 depende de que los archivos se hayan procesado e importado;
comprobarlo en Registro.

Los errores del bot se revisan en su `log.txt` y capturas; pueden ocurrir antes de que el
vigilante vea un archivo. Los del procesamiento se revisan en `vigilante.log` y Registro.
