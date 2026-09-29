# Tarea 30 — NAVAR: todo corre a las 05:45 para tener el cash al día a las 7
Estado: pendiente
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

## Revisión
