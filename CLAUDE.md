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
  DPAPI (`credenciales.py`), log/capturas (`log.py`), salidas a Drive (`salidas.py`),
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
- **Nombre del archivo descargado**: Galicia deja el nombre ORIGINAL (trae el CUIT que usa el
  clasificador); Comafi RENOMBRA con el nombre de la empresa. Eso lo maneja `descargar_csv` de
  cada banco + `nombre_archivo` en el perfil.
- **Credenciales**: DPAPI, por-usuario+por-máquina, en `clientes/<c>/.credenciales/<banco>.dat`
  (gitignored). NO viajan a otra PC → regenerar con `setup_credenciales.py`.
- **Runtime** (perfil navegador, capturas, estado, log): `clientes/<c>/.run/<banco>/` (gitignored).
- **Python en la PC de Thomas**: usar el real (`C:\Users\thoma\AppData\Local\Programs\Python\Python314\python.exe`);
  `python` a secas puede resolver al stub de Microsoft Store.
- **Playwright**: `python -m playwright install chromium` una vez.

## Estado / pendiente (ver docs/MANANA_THOMAS.md para el detalle)
- ⚠️ El refactor de Galicia se portó 1:1 pero **NO se corrió aún desde esta estructura**.
  Falta una corrida de prueba antes de reemplazar producción.
- Faltan las piezas 2-6 (clasificación, cobranzas, disponibilidad+simulador, dashboard, EERR).
  El dashboard tiene un primer mockup visual en `dashboard/`.

## Preferencia de Thomas
Consultarle antes de cambios grandes; dejar todo lo más limpio y comentado posible. Thomas no
programa: los comentarios tienen que explicar el "qué/por qué" en criollo.
