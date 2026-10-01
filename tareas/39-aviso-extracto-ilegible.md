# Tarea 39 — El mail dice "llegó pero no se pudo leer" en vez de "no se actualiza"
Estado: en curso (la escribe Claude: Codex sin cupo desde la 37)
Rama: tarea/aviso-ilegibles

## Objetivo

Que un extracto que **llegó a Drive pero el lector no pudo leer** salte en el mail de la mañana con su
nombre y el motivo. El 01/10/2026 el resumen de Corrientes vino en un formato nuevo, el lector lo salteó
y el mail dijo "último extracto del 16/09 · subir a mano": Thomas lo había subido. El formato se
arregló en la tarea 38; esta tarea evita que la próxima vez pase en silencio, con cualquier banco.

## Contexto

`lector/extractos.py` ya anota cada archivo que no pudo leer en `resumen_bancos_<fecha>.md`
(`- no pude leer corrientes/<archivo>: ValueError: <motivo>`) y el vigilante lo deja en
`_para la Sheet`. Como relee toda la carpeta cada vez, el resumen más nuevo lista todos los que
siguen sin leerse. `aviso_diario.gs` no lo mira (la tarea 32 sacó el detalle técnico).

## Archivos permitidos

- `clientes/navar/herramientas/aviso_diario.gs`
- `lector/pruebas/probar_aviso_bajadas.cjs`
- `tareas/39-aviso-extracto-ilegible.md`

## Resultado esperado

1. El aviso lee el `resumen_bancos_*.md` más nuevo de `_para la Sheet` y saca la lista de ilegibles
   (banco, archivo, motivo sin el nombre técnico del error).
2. **Banco manual atrasado con un ilegible:** la línea ❌ dice `llegó «archivo» pero no se pudo leer
   (motivo) · avisar a finauto · último extracto leído: dd/mm`, en vez de "subir a mano".
3. **Banco al día, o automático, con un ilegible:** va a ⚠️ REVISAR con el mismo texto (no cambia el ✅).
4. **Ilegible de un banco que no está en Saldos Bancarios:** ⚠️ REVISAR.
5. Si no se puede leer el resumen, ⚠️ "No se pudo leer Ilegibles", como las otras lecturas.
6. Pruebas en `probar_aviso_bajadas.cjs` para los cuatro casos y para la lectura del renglón.

## Comprobaciones

1. Node (`/Applications/ChatGPT.app/Contents/Resources/cua_node/bin/node`) con
   `probar_aviso_bajadas.cjs` OK.
2. Instalar en Apps Script solo si el editor tiene exactamente la versión de `main` (hash) y probar con
   "Ver el aviso de hoy (sin mandar)".

## Qué hice

## Revisión
