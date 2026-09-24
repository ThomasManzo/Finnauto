# Tarea 17 — Dejar listo el bot de Galicia para NAVAR
Estado: lista para revisión
Rama: tarea/galicia-navar

## Objetivo

NAVAR ya tiene el usuario de consulta de **Galicia**. Dejar el bot listo para que baje el extracto
solo, todas las mañanas, desde la notebook — **sin correrlo** (las credenciales viven en el llavero
de esa máquina y acá no están).

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `CLAUDE.md` (sección "Cómo sumar un banco nuevo") y
`clientes/navar/LEEME.md`.

Lo que ya existe y **no hay que rehacer**:

- `bots/galicia/` con el bot portado 1:1 del que funciona en producción para el otro cliente.
- `nucleo/` con el motor compartido (recorrido, fechas, estado anti-duplicado, credenciales por
  llavero, capturas, navegador).
- `orquestador/correr.py` con el registro de bancos.
- `clientes/navar/perfil.json` ya tiene un bloque `bancos.galicia`.

**Advertencia importante**: ese bot nunca se corrió desde esta estructura, ni para el otro cliente.
Está portado pero sin probar. No lo des por bueno: leelo y decí qué te parece frágil.

## Archivos permitidos

- `clientes/navar/perfil.json` — completar el bloque de Galicia (filtros de empresa,
  `nombre_archivo`, prefijo, carpeta de destino).
- `orquestador/correr.py` — si hace falta registrar algo para NAVAR.
- `bots/galicia/` — sólo si hay algo claramente roto; si tocás el bot, explicá por qué.
- `clientes/navar/documentos/instalar_notebook.md` — el paso a paso para dejarlo andando.
- `tareas/17-galicia-para-navar.md`

No tocar los lectores, `crear_cash.gs`, `importar_cashflow.gs` ni `vigilante.py`.

## Resultado esperado

1. El perfil de NAVAR completo para Galicia: **dónde deja el archivo** (`NAVAR - Datos/Bancos/galicia`),
   **con qué nombre** (que `lector/extractos.py` lo entienda; hoy los archivos se llaman
   `Movimientos GALICIA <fecha>.xlsx`) y qué cuentas/empresas mirar.
2. **La cuenta**: NAVAR opera en Galicia con `0005459-5 070-1`. Que el bot baje esa.
3. Un apartado en `instalar_notebook.md`, en criollo, con: cómo se cargan las credenciales
   (`python setup_credenciales.py --cliente navar --banco galicia`, **en la notebook**), cómo se
   corre a mano la primera vez para mirar las capturas, y cómo se programa para que corra cada
   mañana **antes** del vigilante.
4. Una lista honesta de **qué puede fallar la primera vez** (selectores cambiados, segundo factor,
   la pantalla de "usuario ya conectado", el cambio de empresa) y cómo se diagnostica con las
   capturas.

## Comprobaciones

1. `python -m py_compile` de lo tocado y `python -c "import json;json.load(open('clientes/navar/perfil.json'))"`.
2. `python orquestador/correr.py --cliente navar --banco galicia --simular` (o el equivalente que
   exista) tiene que decir qué haría **sin** abrir el navegador ni pedir credenciales. Si ese modo
   no existe, decilo; no lo inventes a medias.
3. Dejar escrito qué NO se pudo probar sin credenciales ni red de la empresa.
4. `grep` de nombres propios de personas vacío. Commit en la rama.

## Qué hice

- Trabajé en el worktree y rama `tarea/galicia-navar`, sin datos privados, acceso al banco ni cambios en producción.
- `clientes/navar/perfil.json`: empresa NAVAR SA, cuenta 0005459-5 070-1, nombre Excel
  `Movimientos GALICIA <fecha y hora>.xlsx`, destino documentado `NAVAR - Datos/Bancos/galicia`,
  corte hasta ayer. La ruta absoluta queda vacía porque depende del montaje de la notebook:
  completarla allí en `bancos.galicia.carpeta_drive_destino`. No inventé letra de unidad.
  Sigue `activo: false` para no sumarlo a corridas generales sin validación; el comando explícito sí corre.
- `bots/galicia/navar.py`: variante aislada para NAVAR. Era necesario porque el original elige
  el primer monto y descarga CSV, que el lector de NAVAR no toma. Confirma empresa normalizada,
  busca la cuenta exacta, exige filtro de fechas confirmado, solicita XLSX, verifica cuenta en
  el contenido y lectura con el lector existente, y controla fechas antes de publicar por
  copia temporal. Si no hay movimientos legibles frena. No cambié el bot original ni el núcleo.
- `orquestador/correr.py`: conecta esa variante sólo para NAVAR/Galicia, toma el destino del
  bloque bancario y frena antes del llavero si falta. Devuelve error si el recorrido falla o
  queda sin empresas, en lugar de aparentar éxito.
- `clientes/navar/documentos/instalar_notebook.md`: credenciales en la notebook, primera
  corrida supervisada, controles, capturas, programación 07:00 y pasada posterior del
  vigilante. Aclara que modo prueba publica; pausar vigilante durante la validación inicial.
  Diagnóstico de selectores, segundo factor, usuario conectado, cambio de empresa y descarga.
- `bots/galicia/test_navar.py`: prueba reproducible con Excel ficticio y llamadas reemplazadas
  para no entrar al banco. Acepta ejemplo compatible; rechaza otra cuenta, fecha fuera de
  rango, encabezado incompatible, filtro no confirmado y destino vacío antes del llavero;
  normaliza nombre con puntos. Comando: `python -m unittest bots.galicia.test_navar`.
- Verificado con el Python del entorno existente del repo principal (sin instalar nada):
  unittest OK; `python -m py_compile orquestador/correr.py bots/galicia/navar.py bots/galicia/test_navar.py`
  OK; JSON válido; `git diff --check` limpio. Búsqueda de nombres de personas conocidos en
  líneas agregadas y archivos nuevos: sin coincidencias.
- `python orquestador/correr.py --cliente navar --banco galicia --simular`: código 2,
  argumento no reconocido. **No existe ese modo**, no se implementó una simulación parcial.
  No abrió navegador ni pidió credenciales.
- **Pendiente real:** confirmar que el número de cuenta sea clickeable, que el menú ofrezca
  XLSX y que su contenido traiga cuenta y encabezados compatibles. Son supuestos explícitos,
  protegidos con errores; los tests ficticios no prueban el DOM ni el export del banco.
  Tampoco se probaron login, segundo factor, sesión ya conectada, cambio de empresa,
  permisos, sincronización, horarios ni importación en la Sheet. No está certificado para
  producción; requiere primera prueba supervisada. El lector atribuye cuenta fija y no
  concilia saldos: la comparación contra el banco sigue siendo necesaria.
- Fragilidades heredadas: esperas fijas, reconocimiento heurístico de empresa en header/body,
  alternativas por coordenadas, ausencia de confirmación explícita de login. El calendario
  depende de clases/textos. No hay resolución automática de segundo factor ni sesión previa.
  El rango inicial cubre ayer; la historia previa debe conservarse. El programador y Drive
  requieren comprobarse en la notebook. No se tocaron lectores, vigilante ni scripts de Sheet.


- Commit intentado, pero el sandbox impidió crear `Finnauto/.git/worktrees/Finnauto-tarea17/index.lock`
  (`Operation not permitted`). Los cambios quedan sin commit en este worktree para que
  el revisor los agregue y commitee, según el circuito de tareas/LEEME.md.

## Revisión
