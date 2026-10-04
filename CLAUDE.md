# Contexto para Claude Code — finauto (producto unificado MAGA+/Speedmed → farmacias/PYME)

Handoff maestro. Leer antes de tocar nada.

## Qué es finauto
El **producto nuevo y unificado** que Thomas quiere vender a farmacias y comercios PYME:
automatización financiera de punta a punta (6 piezas, ver README). Se construye reusando
y refactorizando el código del sistema productivo actual de MAGA+ (que vive en el repo
`MAGA`, separado). finauto NO toca ese repo ni la producción.

## Decisiones tomadas (2026-09-03, con Thomas)
- Vender el **sistema completo** (6 piezas), no solo los bots.
- **Multi-cliente diferido**: la estructura ya lo soporta (`clientes/<cliente>/perfil.json`),
  pero la decisión de "mantener stack Google vs backend propio" se define en Fase 5.
- Nombre de trabajo: **finauto** (comercial a definir).

## Arquitectura (lo que está armado — Fase 1)
- **`nucleo/`** = el MOTOR, compartido, sin nada específico de un banco. Puesto: recorrido
  (`loop.py`), regla de fechas (`fechas.py`), estado anti-duplicado (`estado.py`), credenciales
  llavero del sistema (`credenciales.py`), log/capturas (`log.py`), salidas a Drive (`salidas.py`),
  navegador Playwright (`navegador.py`), config del cliente (`config.py`), `contexto.py`.
- **`bots/base.py`** = el CONTRATO (`BotBanco`, clase abstracta). Un banco = una clase que lo
  implementa con SUS selectores. Galicia ✅ (portado 1:1 del bot que funciona), Comafi 🟡
  (andamiaje, `# >>> TODO COMAFI`), Santander ⬜ (esqueleto).
- **`clientes/maga/perfil.json`** = todo lo hardcodeado de MAGA (carpeta Drive, filtros de
  empresas, `nombre_archivo` cuit/empresa, prefijos). Sumar cliente = otro perfil.
- **`orquestador/correr.py`** = entrypoint CLI.

Esencia del refactor: el motor que estaba **duplicado** en `bot_galicia.py` y `bot_comafi.py`
ahora vive **una sola vez** en `nucleo/`. Se portó SIN cambiar la lógica.

## Cómo sumar un banco nuevo
1. `bots/<banco>/bot.py`: clase `Bot<Banco>(BotBanco)` implementando los métodos del contrato
   (login, capturar_empresa_activa, descubrir_empresas, cambiar_a_empresa, ir_a_cuenta,
   capturar_saldos, aplicar_filtro_fechas, descargar_csv; opcional extraer_cuenta_id).
2. Registrarlo en `orquestador/correr.py` (`REGISTRO_BANCOS`).
3. Agregar su bloque en el perfil del cliente (`activo`, filtros, `nombre_archivo`, prefijo).
4. Afinar selectores en modo prueba mirando capturas (mismo proceso que Galicia).

## OJO / convenciones
- **EL REPO ES PÚBLICO (GitHub). Nada de datos reales en archivos versionados**: ni montos, ni nombres
  de personas, ni mails, ni nombres de clientes/proveedores de un cliente, ni situación de deuda. Eso va
  en `clientes/<c>/privado/` o en los documentos que no se versionan (`clientes/navar/LEEME.md`,
  `clientes/navar/documentos/`, `docs/`: están en `.gitignore`, viven solo en esta Mac). En código,
  comentarios, pruebas y consignas de `tareas/`: ejemplos inventados. Los mails del aviso van en las
  Propiedades del script de Apps Script. (Incidente 04/10/2026: había datos reales en el repo; se
  limpió y se reescribió el historial.)
- **Nombre del archivo descargado**: Galicia deja el nombre ORIGINAL (trae el CUIT que usa el
  clasificador); Comafi RENOMBRA con el nombre de la empresa. Eso lo maneja `descargar_csv` de
  cada banco + `nombre_archivo` en el perfil.
- **Credenciales**: llavero del sistema vía `keyring` (Keychain en macOS, Administrador de
  credenciales en Windows), servicio `finauto:<cliente>:<banco>`. Por-usuario+por-máquina:
  NO viajan a otra máquina → regenerar con `setup_credenciales.py`.
- **Runtime** (perfil navegador, capturas, estado, log): `clientes/<c>/.run/<banco>/` (gitignored).
- **Python**: en la Mac, entorno virtual del repo (`.venv`, se activa con
  `source .venv/bin/activate`). En Windows, usar el intérprete real
  (`C:\Users\thoma\AppData\Local\Programs\Python\Python314\python.exe`); `python` a secas
  puede resolver al stub de Microsoft Store.
- **Playwright**: `python -m playwright install chromium` una vez.

## Cliente real: NAVAR S.A. (desde 12/09/2026, contrato 15/09)
Yerbatera en Corrientes. Vive en `clientes/navar/`: **leer su `LEEME.md` primero**, empezando por
la sección "Dónde estamos" más nueva. Ahí está el estado real; esta sección es solo el mapa.

- **Fuente de verdad: la Sheet "NAVAR - Cash Flow"** (Google Sheets, en hora de Buenos Aires). Las
  LISTAS tienen los datos y las pantallas (Cash, Cash Semanal, Cash Mensual, Plan) son fórmula. Los
  scripts de Apps Script (`clientes/navar/herramientas/*.gs`) se pegan a mano en el editor; la copia
  al día vive en Drive `NAVAR - Datos/Scripts/`.
- **La notebook de NAVAR es el "servidor"** (Windows, `C:\finauto`, sin servidor pago). Tiene la
  bajada de Tango por API a las 07:30 (`ingestas/tango_live.py`), el bot de Galicia a las 07:00 y el
  vigilante cada 15 min (`clientes/navar/herramientas/vigilante.py`). El vigilante mira
  `NAVAR - Datos` en Drive y corre los lectores (`lector/`). La Sheet importa lo nuevo cada hora.
  El código se actualiza allá con `actualizar.ps1`, que baja `main` de GitHub y **pisa el repo**
  (menos `.venv`, `.run`, `privado`). Por eso lo que depende de la máquina no va en archivos del repo.
- Thomas está conectado a la notebook por Chrome Remote Desktop: **los comandos de allá los corre
  él, de a uno**, y pega la salida.
- Datos reales en `clientes/navar/privado/` (gitignored) y en Drive. Nunca a Codex ni a GitHub.
- Tango: 8 consultas personalizadas de Live ("Finauto ...", customQuery 10-18) de las que depende
  la bajada. **No borrarlas ni editarlas.** Detalle en el LEEME.

## Cómo trabajamos (desde 22/09/2026)
- **Claude = cerebro, Codex = ejecutor.** El código de tareas aisladas lo escribe Codex, a partir de
  consignas en `tareas/<nn>-<nombre>.md`, en un worktree y rama propios. Claude escribe la consigna,
  revisa el diff y, **con el OK de Thomas**, mergea a `main` y sube a GitHub. Circuito completo en
  `tareas/LEEME.md`. Lo que necesita la Sheet, Drive o la pantalla de Thomas lo hace Claude.
- Hay chats en paralelo (bancos, cruce banco ↔ Tango): antes de crear una consigna, mirar
  `tareas/` y tomar el número libre siguiente. Al terminar, borrar el worktree y la rama mergeada.
- Nada sale a NAVAR sin validar los números antes (ver memoria del proyecto).

## Estado / pendiente (28/09/2026)
- ✅ Tango por API, automático de punta a punta (tareas 18, 20, 22).
- ✅ Galicia: bot en la notebook, baja solo (tareas 17, 19, 23-26). Pendientes finos en el LEEME.
- ⬜ Macro (usuario bloqueado, se pide desbloqueo), BBVA (login en loop), Nación (escaneado: la
  notebook no tiene OCR; tarea 21 para la cuenta de 13/14 dígitos), Corrientes.
- ⬜ Cruce banco ↔ Tango (chat propio). ⬜ Aviso de las 9:00 adaptado a la bajada automática.
  ⬜ Cuotas bancarias que se den de baja solas. ⬜ Tablero web con los bloques del Cash nuevo
  (después de los bancos).
- ⬜ Producto general (fuera de NAVAR): piezas 2-6 del README. El refactor de Galicia para MAGA
  sigue sin corrida en producción (la variante de NAVAR sí corre).

## Preferencia de Thomas
Consultarle antes de cambios grandes; dejar todo lo más limpio y comentado posible. Thomas no
programa: los comentarios tienen que explicar el "qué/por qué" en criollo.
