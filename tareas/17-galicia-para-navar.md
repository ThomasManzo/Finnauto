# Tarea 17 — Dejar listo el bot de Galicia para NAVAR
Estado: pendiente
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

## Revisión
