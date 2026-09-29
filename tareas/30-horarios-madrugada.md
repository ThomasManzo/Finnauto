# Tarea 30 — NAVAR: todo corre a las 05:45 para tener el cash al día a las 7
Estado: aprobada (mergeada el 29/09/2026)
Rama: tarea/horarios-madrugada

## Objetivo

Que los instaladores del repo dejen los horarios nuevos, para que un reinstalo no vuelva a los
viejos. NAVAR pidió (29/09/2026) tener el cash actualizado **a las 07:00**.

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `clientes/navar/herramientas/instalar_galicia.ps1`,
`clientes/navar/herramientas/instalar_tango.ps1`, `clientes/navar/herramientas/importar_cashflow.gs`
(`instalarDisparador` / `quitarDisparador`) y `clientes/navar/documentos/instalar_notebook.md`
(§5, §6 y la tabla "Qué queda corriendo, en orden, cada mañana").

Ya se cambió **a mano** en la notebook el 29/09 (y quedó confirmado con `Get-ScheduledTask`):
- `finauto NAVAR Galicia`: **05:45 y 05:48**. El segundo es el seguro: si la primera corrida falla
  en frío, la segunda la cubre. Correr dos veces no duplica: el archivo del día se reemplaza.
- `finauto NAVAR Tango`: **05:45**.
- El vigilante no cambia (cada 15 minutos; pasa a las 05:53 y a las 06:08).

La Sheet importa con `importarLoNuevo` **cada hora**, en un minuto que elige Google. Podría caer a las
06:05, antes de que el vigilante publique, y la siguiente sería a las 07:05. Hace falta además una
corrida **diaria entre las 6 y las 7**. Thomas la agrega a mano desde Activadores, pero
`instalarDisparador()` llama a `quitarDisparador()`, que **borra todos** los disparadores de
`importarLoNuevo`: un reinstalo la haría desaparecer.

## Archivos permitidos

- `clientes/navar/herramientas/instalar_galicia.ps1`
- `clientes/navar/herramientas/instalar_tango.ps1`
- `clientes/navar/herramientas/importar_cashflow.gs` — **solo** `instalarDisparador` (y su mensaje).
- `clientes/navar/documentos/instalar_notebook.md` — **solo** las partes de horarios de §5 y §6 y la
  tabla de la mañana.
- `tareas/30-horarios-madrugada.md`

## Resultado esperado

1. `instalar_galicia.ps1`: **dos disparadores diarios, 05:45 y 05:48**, en un solo
   `Register-ScheduledTask` (`-Trigger @(...)`). Comentario en criollo: el segundo es el seguro
   porque la primera corrida del día a veces falla en frío (tareas 27 a 29). Mensaje final con los
   dos horarios.
2. `instalar_tango.ps1`: **05:45**. Actualizar el comentario de cabecera y el mensaje.
3. `importar_cashflow.gs → instalarDisparador()`: después del de cada hora, crear también uno diario
   `ScriptApp.newTrigger("importarLoNuevo").timeBased().atHour(6).nearMinute(20).everyDays(1).create()`.
   Comentario: tiene que correr después del vigilante de las 05:53/06:08 y antes de las 07:00, y
   `nearMinute` tiene ±15 min. Actualizar el `_registrar_` y el `toast` para que digan las dos cosas.
   `quitarDisparador()` queda igual (borra los dos, que es lo correcto antes de recrearlos).
4. Guía: los horarios nuevos en §5 (Tango) y §6 (Galicia), y la tabla de la mañana en este orden:
   05:45 Tango y Galicia · 05:48 Galicia (seguro) · 05:53/06:08 vigilante · 06:05–06:35 importación
   diaria de la Sheet (+ la de cada hora) · 07:00 cash al día. Aclarar que la notebook tiene que estar
   **prendida y sin suspenderse a las 05:45** y que, después de pegar el `.gs` nuevo, hay que correr
   una vez `instalarDisparador` desde el editor (y que eso reemplaza el activador diario cargado a
   mano, que ya no hace falta).

## Comprobaciones

1. Revisar los dos `.ps1` contra el de Tango actual: cambian solo los horarios, los comentarios y los
   mensajes. No se puede correr PowerShell en la Mac; decirlo en "Qué hice".
2. Leer `instalarDisparador` completo: crea exactamente dos disparadores de `importarLoNuevo`.
3. Commit en la rama.

## Qué hice

- Galicia queda con dos disparadores diarios (05:45 y 05:48) en un solo registro de tarea;
  Tango queda a las 05:45. Actualicé comentarios y mensajes. Las acciones, opciones, logs
  y demás configuración de ambos instaladores se mantienen.
- instalarDisparador crea exactamente dos activadores de importarLoNuevo: cada hora y diario
  a las 06:20 aproximadas (±15 minutos). Actualicé Registro y toast. quitarDisparador no cambió.
- Actualicé sólo los horarios de §5/§6 y la tabla de la mañana, con la notebook encendida desde
  las 05:45 y el paso de ejecutar instalarDisparador después de pegar el .gs.
- Aclaré que 06:05 puede ser antes del vigilante de 06:08: estos horarios cumplen la consigna
  pero no garantizan por sí solos el cash al día a las 07:00; hay que verificar Registro.
- Verificación estática: revisé los diffs de ambos instaladores y la función completa; confirmé
  horarios, un Register-ScheduledTask por instalador, exactamente dos newTrigger y ningún cambio
  fuera de instalarDisparador en el .gs. git diff --check OK.
- No pude correr PowerShell en esta Mac (no está instalado). No ejecuté Apps Script ni cambié
  tareas o activadores reales: queda pendiente verificar la instalación en Windows y en la Sheet.

## Revisión

**Claude, 29/09/2026.** Los `.ps1` cambian solo los horarios, los comentarios y los mensajes. Galicia
queda con dos disparadores en un solo `Register-ScheduledTask`. `instalarDisparador` crea exactamente
dos (cada hora y diario ~06:20) y `quitarDisparador` borra los dos antes. La guía está al día. Buena
la advertencia de Codex: con `nearMinute(20)` la importación diaria podría caer a las 06:05, antes de
la pasada de las 06:08. En la práctica la de las 05:53 ya tendría todo (Tango y Galicia terminan
antes de las 05:50), pero es mejor no depender de eso: se pasa a `nearMinute(30)` (06:15–06:45) en la
tarea 31. Aprobada.

