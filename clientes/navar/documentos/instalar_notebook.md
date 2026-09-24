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

## 5. Tango Live por API (cuando soporte habilite el usuario finauto) (10 min)

1. En la notebook, entrar a Tango Live **con el usuario finauto**, abrir cualquiera de las
   cuatro consultas → Apertura → API → **Obtener token**. Copiar el token.
2. En la URL de esa pantalla (o en la barra de direcciones de cada consulta) está el número de
   proceso: anotar el de las cuatro consultas y el id de empresa de NAVAR SA Otros (el header
   `Company`; NAVAR SA es 13). Cargarlos en `clientes\navar\perfil.json` → `tango_live`.
3. Guardar el token en el llavero de la máquina (nunca en un archivo):
   ```powershell
   .\.venv\Scripts\python.exe setup_credenciales.py --cliente navar --banco tango_live
   ```
   usuario: `finauto` · clave: el token.
4. Probar una consulta y mirar cómo responde Live (esto se hace una vez, para ajustar el lector
   al formato real):
   ```powershell
   .\.venv\Scripts\python.exe ingestas\tango_live.py --probar cobranzas --empresa A
   ```
   Pasarle a Claude lo que imprime.
5. Cuando la prueba pase, la bajada entera:
   ```powershell
   .\.venv\Scripts\python.exe ingestas\tango_live.py
   ```
   Deja los siete Excel en sus carpetas de Drive; el vigilante hace el resto. Se programa a
   las 7:30 en el Programador de tareas (misma receta que el vigilante, una vez por día).

## 6. Galicia: preparación y primera prueba en la notebook

**Preparado para revisar, todavía no validado contra Galicia.** El adaptador original baja
CSV y el lector de NAVAR sólo toma Excel/PDF. La variante de NAVAR pide XLSX y frena si
no confirma empresa, cuenta, fechas o un Excel legible. No se comprobó que el menú actual
ofrezca esa opción ni que el número de cuenta sea un enlace: se debe mirar la primera vez.

1. Con el mismo usuario de Windows que correrá la tarea, desde `C:\finauto`, cargar las
   credenciales **en la notebook**. La administración las tipea sin compartirlas:
   ```powershell
   .\.venv\Scripts\python.exe setup_credenciales.py --cliente navar --banco galicia
   ```
   Es el equivalente a `python setup_credenciales.py --cliente navar --banco galicia` con
   el entorno elegido. Quedan en el llavero `finauto:navar:galicia` de esa máquina y usuario.
2. En `clientes/navar/perfil.json`, completar **bancos.galicia.carpeta_drive_destino** con
   la ruta absoluta existente a `NAVAR - Datos/Bancos/galicia`. Ejemplo JSON, sólo si coincide
   con el Explorador: `"G:\\Mi unidad\\NAVAR - Datos\\Bancos\\galicia"`.
   Puede estar en un acceso directo de Drive; usar la ruta comprobada en el punto 3.
   `carpeta_drive_relativa` documenta el destino, no se resuelve sola.
   Se espera empresa **NAVAR SA** (se admiten puntos y espacios) y cuenta **0005459-5 070-1**.
   No incluye otras empresas ni otras cuentas. `activo: false` evita las corridas generales;
   **el comando con --banco explícito sí corre aunque esté en false**.
3. **No existe --simular en este orquestador.** No usar `--modo prueba` como simulación:
   entra al banco, descarga, publica y guarda estado. Para la primera prueba supervisada,
   pausar temporalmente la tarea del vigilante y ejecutar:
   ```powershell
   .\.venv\Scripts\python.exe orquestador\correr.py --cliente navar --banco galicia --modo prueba
   ```
   Log: `clientes/navar/.run/galicia/log.txt`. Capturas:
   `clientes/navar/.run/galicia/capturas/`. No subirlas a git: pueden contener datos reales.
4. Revisar el Excel y compararlo contra el banco antes de reanudar el vigilante: empresa,
   cuenta, fechas, movimientos y saldos. Sale como `Movimientos GALICIA AAAA-MM-DD_HHMMSS_microsegundos.xlsx`
   en `Bancos/galicia`. La fecha del nombre es la descarga; las fechas del extracto mandan.
   Se valida con el lector existente antes de publicar; no se convierte CSV ni se inventan saldos.
   Si falla, el Excel queda local en `.run/galicia/descargas_temp/galicia_por_validar.xlsx`.
   Un extracto sin movimientos también frena: ese caso necesita validación manual.
   El rango termina ayer (`incluir_hoy: false`), arranca ayer en la primera corrida, y después
   retoma desde el último cierre guardado. No recupera historia anterior por sí solo; conservar
   los extractos previos. Estado: `.run/galicia/estado_descargas.json`; no borrarlo a ciegas.
5. Sólo cuando pase la comparación, reanudar el vigilante y revisar su log y Registro en la
   Sheet. En el Programador de tareas, crear **finauto NAVAR Galicia**, a las **07:00 cada día**:
   - Usuario: el mismo que cargó las claves y tiene Drive abierto; ejecutar sólo con sesión iniciada.
   - Programa: `C:\finauto\.venv\Scripts\python.exe`.
   - Argumentos: `orquestador\correr.py --cliente navar --banco galicia --modo produccion`.
   - Iniciar en: `C:\finauto`.
   - No iniciar otra instancia si ya está corriendo. Notebook encendida, sin suspensión y con Drive montado.
   - Revisar las próximas horas del vigilante y dejar una pasada posterior, por ejemplo 07:15.
     Corre cada 15 minutos: los horarios no garantizan que Galicia haya terminado. El Excel se
     publica al terminar la copia; si tarda, lo recoge una pasada posterior.
   Probar la tarea con «Ejecutar» y comprobar el archivo, log y Registro; el horario solo no
   certifica funcionamiento. El comando explícito no requiere activar las corridas generales.

### Qué puede fallar la primera vez

| Señal | Qué revisar |
|---|---|
| Login no avanza / segundo factor | `pantalla_login`, `post_login`, `ERROR_login`. No hay resolución automática de token ni espera interactiva prevista. Revisar con administración. |
| «Usuario ya conectado» | `post_login` y último error. Cerrar la sesión anterior de forma normal; el bot no fuerza su cierre. |
| Empresa no reconocida o cambio fallido | `modal_empresas`, `ERROR_menu_no_abrio`, `empresa_*`, `ERROR_*`. El original busca nombres en header/body y usa alternativas por coordenadas: son frágiles. Confirmar nombre y pantalla antes de ajustar. |
| Cuenta no encontrada / no abre | `listado_cuentas` y `movimientos`. El texto exacto y su click son supuestos pendientes de comprobar; no se elige otra cuenta como reemplazo. |
| Fechas no confirmadas | `panel_filtros`, `calendario_abierto`, `fechas_seleccionadas`, `movimientos_filtrados`. El calendario depende de clases y textos de la web. No se publica si devuelve una verificación fallida. |
| No hay XLSX o no pasa el lector | `menu_descarga`, `ERROR_*` y Excel local. Revisar opción disponible, encabezados, número de cuenta dentro del archivo y fechas. No renombrar CSV a XLSX. |
| Drive o tarea fallan | Ruta local, usuario de Windows, sesión iniciada, Drive montado y `log.txt`. Un error de configuración puede aparecer sólo en consola antes de crear log. |

El código heredado usa esperas fijas y no confirma el login al enviarlo; una falla puede
aparecer recién como error de empresa o cuenta. Revisar las capturas en orden. Las capturas
pueden pisarse entre corridas: conservar la evidencia local antes de repetir. No se probaron
acceso real, segundo factor, empresa, cuenta, export, permisos del usuario, sincronización de
Drive ni tarea programada. Los otros bancos siguen desactivados y sin adaptación en esta tarea.

## Qué queda corriendo, en orden, cada mañana

| Hora | Qué | Dónde deja |
|---|---|---|
| 7:00 | bots de banco (uno por banco) | `Bancos\<banco>\` |
| 7:30 | `tango_live.py` | `Cuentas a cobrar`, `Cuentas a pagar`, `Cheques` |
| cada 15 min | vigilante → lectores | `_para la Sheet\` |
| cada hora | disparador de la Sheet | solapas de la Sheet + Registro |

Los errores del bot se revisan en su `log.txt` y capturas; pueden ocurrir antes de que el
vigilante vea un archivo. Los del procesamiento se revisan en `vigilante.log` y Registro.
