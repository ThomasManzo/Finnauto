# Tarea 35 — La bajada de Tango reintenta sola si falló
Estado: aprobada (mergeada 29/09; falta actualizar la notebook y volver a correr instalar_tango.ps1)
Rama: tarea/tango-reintento

## Objetivo

Que si la bajada de las 05:45 no pudo traer todo (servidor de Tango apagado, red caída), vuelva a
intentar sola varias veces en la mañana, **sin que nadie haga nada**, y que los reintentos no hagan
nada cuando ya bajó bien.

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `CLAUDE.md`, `clientes/navar/LEEME.md` (sección "Dónde
estamos" más nueva), `ingestas/tango_live.py` (`main`, `_escribir_parte_tango`),
`ingestas/test_tango_live.py` y `clientes/navar/herramientas/instalar_tango.ps1`.

Qué pasó el 29/09/2026: la tarea "finauto NAVAR Tango" corrió a las 05:45 y el parte
(`_para la Sheet/tango_ultima_bajada.txt`) quedó así:

```
2026-09-29T08:45:19+00:00
0 de 8
A cobranzas 2026-09-29.xlsx: <urlopen error [Errno 11001] getaddrinfo failed>
... (las 8 igual)
```

La notebook no encontraba a la máquina `servidor` en la red: el servidor de Tango estaba apagado o
todavía no estaba en la red. El bot de Galicia anduvo a las 05:48, así que había internet. A la
tarde Thomas corrió la bajada a mano y trajo 8 de 8. Hoy no hay ningún reintento: si falla a las
05:45, el día queda sin Tango.

Lo que ya existe y no cambia:
- El parte se escribe al final de cada bajada normal, con fecha UTC ISO, `N de 8` y las fallas.
- La bajada pisa los 8 archivos del día (mismo nombre). Correrla de nuevo es seguro: el vigilante
  reprocesa y la Sheet reimporta.
- La Sheet importa cada hora y además una vez cerca de las 06:30. El mail sale a las 07:30 y lee el
  parte (tareas 27, 31-33). **El aviso no se toca en esta tarea.**

## Archivos permitidos

- `ingestas/tango_live.py`
- `ingestas/test_tango_live.py`
- `clientes/navar/herramientas/instalar_tango.ps1`
- `clientes/navar/documentos/instalar_notebook.md` (solo §5, donde se describe la tarea de Tango)
- `tareas/35-tango-reintenta-solo.md`

## Resultado esperado

1. **`tango_live.py --si-falta`** (flag nuevo): antes de pedir el token o tocar la red, lee el parte
   en `<raíz>/_para la Sheet/tango_ultima_bajada.txt`.
   - Si el parte es **de hoy** y dice `8 de 8` (o `N de N`, con N igual al total), escribe en el log
     `ya bajó hoy completo a las HH:MM; no hago nada` y sale con código 0, **sin tocar nada**: ni el
     llavero, ni la red, ni los archivos, ni el parte.
   - En cualquier otro caso hace la bajada normal completa: parte de ayer, parte de hoy incompleto
     (`5 de 8`, `0 de 8`), sin parte o parte ilegible. Si el parte está ilegible, lo dice en el log.
   - "Hoy" es el día de `--hoy`. El día del parte se compara pasando su fecha UTC a la **hora local
     de la máquina** (`astimezone()` sin argumentos: la notebook está en hora de Buenos Aires). No
     usar `zoneinfo`: en Windows puede no tener la base de zonas horarias.
   - Sin `--si-falta` todo sigue igual que hoy.
2. **`instalar_tango.ps1`**: la misma tarea "finauto NAVAR Tango" con **varios disparadores
   diarios**: **05:45, 06:15, 06:45, 07:15, 09:00 y 12:00**. La acción siempre lleva `--si-falta`.
   Las horas van en una lista al principio del script, comentada: la primera baja y las demás solo
   reintentan si hace falta. Se mantienen `-MultipleInstances IgnoreNew`, el límite de 1 hora y el log
   agregado. El mensaje final lista las horas.
3. **§5 de `instalar_notebook.md`**: explicar los reintentos en dos o tres líneas y que, después de
   actualizar el código, hay que **volver a correr `instalar_tango.ps1`** para que se registren los
   disparadores nuevos.

## Comprobaciones

1. `python -m py_compile ingestas/tango_live.py` y `python -m unittest ingestas.test_tango_live`,
   con pruebas nuevas y sin red (reemplazar `token`, `llamar` o `bajar`):
   - parte de hoy `8 de 8` + `--si-falta`: no llama al token ni a la red, no escribe nada, sale 0;
   - parte de ayer `8 de 8` + `--si-falta`: baja;
   - parte de hoy `0 de 8` + `--si-falta`: baja y reescribe el parte;
   - sin parte, o con parte ilegible: baja;
   - sin `--si-falta`: baja aunque el parte de hoy diga `8 de 8`.
2. Revisar a mano que `instalar_tango.ps1` registre una sola tarea con los 6 disparadores y que la
   acción lleve `--si-falta`. En la Mac no hay PowerShell: anotarlo.
3. `grep` de nombres propios de personas vacío. Commit en la rama.

## Qué hice

- Agregué `--si-falta`: lee el parte antes del llavero y la red. Sólo saltea cuando
  confirma las ocho fotos del día local de `--hoy`; conserva archivos y parte sin escribir.
  Partes ausentes, incompletos, viejos, inválidos o inaccesibles dejan correr la bajada;
  los ilegibles se avisan. La conversión usa `astimezone()` sin base de zonas adicional.
- La bajada manual sin el flag mantiene su comportamiento. `--probar` y `--simular`
  siguen siendo modos de diagnóstico y conservan su comportamiento incluso con el flag.
- El instalador conserva una única tarea con seis disparadores diarios y `--si-falta`,
  el log agregado, `IgnoreNew` y el límite de una hora. Actualicé únicamente §5 del manual.
- Validación local: `python -m py_compile ingestas/tango_live.py` y
  `python -m unittest ingestas.test_tango_live`: **18 pruebas OK**, sin red ni llavero real.
  Cubren salida sin escrituras, parte viejo, 0/8, 5/8, ausente, ilegible, sin permiso,
  total incorrecto, fecha sin zona, bajada manual y cruce de medianoche UTC/hora local.
- Revisión manual del instalador: una llamada a `Register-ScheduledTask`, seis horas,
  acción con el flag y opciones conservadas. Esta Mac no tiene PowerShell: falta probar
  el registro efectivo en Windows. `git diff --check` sin errores; sin nombres de personas
  en las líneas agregadas.
- Para instalar después de revisar e integrar: actualizar la notebook y volver a ejecutar
  `powershell -ExecutionPolicy Bypass -File clientes\navar\herramientas\instalar_tango.ps1`.
  Esta tarea no modifica la notebook, la Sheet ni el aviso diario; no hace merge ni push.

## Revisión

**Claude, 29/09/2026.** Leí el diff completo y corrí `python -m unittest ingestas.test_tango_live`:
18 OK. Aprobado.
- `--si-falta` decide **antes** de pedir el token o tocar la red, y solo saltea con parte de hoy
  (hora local), `8 de 8` exacto contra `TOTAL_BAJADAS_DIARIAS` y sin líneas de falla. Cualquier
  otra cosa (parte viejo, incompleto, ausente o ilegible) baja las 8. Es lo pedido, y ante la duda
  prefiere bajar de más.
- Sin `--si-falta` no cambia nada: la corrida manual del 29/09 sigue funcionando igual.
- `instalar_tango.ps1`: una tarea, seis disparadores y la acción con el flag; se mantienen
  `IgnoreNew` (si la de 05:45 sigue corriendo a las 06:15, no se pisa), el límite de 1 hora y el log.
- Falta en Windows: `actualizar.ps1` y volver a correr `instalar_tango.ps1`. Verificar con
  `Get-ScheduledTask "finauto NAVAR Tango" | Select -Expand Triggers` que aparezcan las 6 horas.
