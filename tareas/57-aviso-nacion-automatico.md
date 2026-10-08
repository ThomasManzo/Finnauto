# Tarea 57 — El mail diario trata a Nación como banco automático
Estado: lista para revisión
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

- `aviso_diario.gs`: `nacion` en `FUENTES_AUTOMATICAS`; `NACION_REINTENTA_HASTA = 16` y un mapa
  `BANCOS_REINTENTAN_HASTA` (Galicia y Nación) en vez del `galicia ? … : Tango`; el "Último extracto"
  acepta `.xls`. El parte se lee igual que el de Galicia (`_ESTADO_Nacion_DD-MM.txt`, cabecera
  "Bot Nacion - …", el formato de `nucleo/salidas`).
- `probar_aviso_bajadas.cjs`: caso nuevo de Nación (bajó, falló con reintentos hasta las 16:00, no
  corrió). Un caso viejo usaba NACION como ejemplo de banco manual: ahora usa uno desconocido.
- Node: todas las pruebas OK, datos inventados.

## Revisión
