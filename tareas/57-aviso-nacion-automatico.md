# Tarea 57 — El mail diario trata a Nación como banco automático
Estado: en curso
Rama: tarea/aviso-nacion

## Objetivo

Desde el 07/10/2026 Nación baja solo (tarea 56, notebook 06:10 con reintentos hasta las 16:00). El
mail diario todavía lo trata como banco "a subir a mano". Tiene que tratarlo como Galicia: ✅ si el
bot bajó hoy, ❌ "el bot falló / no corrió" con los reintentos, y la fecha del último extracto.

## Archivos permitidos

- `clientes/navar/herramientas/aviso_diario.gs`
- `lector/pruebas/probar_aviso_bajadas.cjs`
- `tareas/57-aviso-nacion-automatico.md`

## Resultado esperado

1. `FUENTES_AUTOMATICAS` incluye `nacion`; el parte se lee de `Bancos/nacion/_ESTADO_Nacion_DD-MM.txt`
   (ya lo escribe el núcleo con ese nombre).
2. Hasta qué hora reintenta cada banco sale de un mapa (`galicia` y `nacion`: 16 hs); Tango sigue
   igual.
3. "Último extracto" acepta `.xls` (Nación) además de `.xlsx`.
4. Pruebas nuevas con datos inventados; las existentes siguen igual.
5. Claude lo pega en Apps Script y lo prueba con "Ver el aviso de hoy (sin mandar)".

## Qué hice

## Revisión
