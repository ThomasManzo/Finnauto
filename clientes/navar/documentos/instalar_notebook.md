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

## 5. Tango Live por API (cuando Miriam habilite el usuario finauto) (10 min)

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

## 6. Bots de banco (cuando haya operador de consulta) (por banco, 1–2 h la primera vez)

1. **Alguien de NAVAR** carga el usuario y la clave del operador de consulta en el llavero
   (vos mirás para otro lado; la clave no se ve al tipear):
   ```powershell
   .\.venv\Scripts\python.exe setup_credenciales.py --cliente navar --banco galicia
   ```
2. En `clientes\navar\perfil.json` poner `"activo": true` en ese banco y
   `"carpeta_drive_destino"` = la carpeta `Bancos\<banco>` del Drive montado.
3. Primera corrida **en modo visible**, mirando por AnyDesk:
   ```powershell
   .\.venv\Scripts\python.exe orquestador\correr.py --cliente navar --banco galicia --modo prueba
   ```
   Si el banco cambió una pantalla, el bot deja capturas en `clientes\navar\.run\galicia\`; con
   eso se ajustan los selectores (eso lo hace Claude, no vos).
4. Cuando corre entera, tarea programada a las 7:00, modo producción:
   `orquestador\correr.py --cliente navar --banco galicia --modo produccion`.
5. Siguiente banco. Orden: Galicia (adaptador listo) → Macro → BBVA → Nación → Corrientes.

## Qué queda corriendo, en orden, cada mañana

| Hora | Qué | Dónde deja |
|---|---|---|
| 7:00 | bots de banco (uno por banco) | `Bancos\<banco>\` |
| 7:30 | `tango_live.py` | `Cuentas a cobrar`, `Cuentas a pagar`, `Cheques` |
| cada 15 min | vigilante → lectores | `_para la Sheet\` |
| cada hora | disparador de la Sheet | solapas de la Sheet + Registro |

Si algo falla, queda en `vigilante.log` y en la solapa Registro. El aviso por mail (qué llegó y
qué no) es el paso siguiente.
