# Tarea 32 — El mail diario como checklist simple
Estado: pendiente
Rama: tarea/aviso-checklist

> **Renumerada el 29/09/2026** (antes era "30-aviso-checklist-y-madrugada": chocaba con la tarea 30
> de horarios, escrita en paralelo en otro chat). **La parte de horarios ya está hecha e instalada**
> por las tareas 30 y 31: bajadas a las 05:45 (Galicia también a las 05:48, de seguro), importación
> diaria de la Sheet entre 06:15 y 06:45 además de la de cada hora, y **el mail a las 07:30** (07:15–07:45),
> que es lo último que pidió Thomas. `DESTINATARIOS` ya tiene cuatro casillas. Esta tarea queda
> **solo con la checklist**; no tocar horarios, instaladores ni `DESTINATARIOS`.

## Objetivo

Dos cosas que pidió NAVAR (29/09/2026):

1. **El mail diario tiene que ser una checklist**: qué llegó, qué falta y, de lo que falta, cuál es
   lo último que hay. Hoy tiene demasiado ruido técnico: lo que procesó el vigilante, lo que importó
   la Sheet línea por línea y errores viejos ya resueltos.
2. ~~A las 07:00 el cash tiene que estar actualizado~~ → **hecho** en las tareas 30 y 31 (ver arriba).

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `CLAUDE.md`, `clientes/navar/LEEME.md` (secciones del
25, 28 y 29/09), `tareas/27-aviso-con-bajadas-automaticas.md` (qué se hizo recién y por qué),
`clientes/navar/herramientas/aviso_diario.gs` entero, `lector/pruebas/probar_aviso_bajadas.cjs`,
`clientes/navar/herramientas/instalar_tango.ps1` e `instalar_galicia.ps1`.

**Lo que ya existe (tarea 27) y se reutiliza:**
- Parte de Tango: `_para la Sheet/tango_ultima_bajada.txt` (fecha UTC, `N de 8` y una línea por falla).
- Parte de Galicia: `Bancos/galicia/_ESTADO_Galicia_DD-MM.txt` (OK o `>>> ATENCION` con motivo).
- `FUENTES_AUTOMATICAS = ["tango", "tesoreria_aa", "galicia"]`.
- Lectura de Saldos Bancarios (último extracto por banco), Registro (importaciones), entradas de Drive
  (archivos por carpeta) y marca de vida del vigilante.

**El horario nuevo** (los horarios del Programador de tareas de la notebook los cambia Thomas; esta
tarea deja los scripts y la guía iguales a lo que corre):
- 05:45: bot de Galicia y bajada de Tango, a la vez.
- Vigilante cada 15 min: procesa entre las 05:53 y las 06:08.
- La Sheet importa cada hora, hoy cerca del minuto :32, o sea hacia las 06:33.
- La Sheet además importa todos los días entre 06:15 y 06:45 (tarea 31).
- 07:30: el mail (entre 07:15 y 07:45). **Ya instalado.**

## Archivos permitidos

- `clientes/navar/herramientas/aviso_diario.gs`
- `lector/pruebas/probar_aviso_bajadas.cjs`
- `tareas/32-aviso-checklist.md`

(Los instaladores y la guía ya no: sus horarios los resolvieron las tareas 30 y 31.)

## Resultado esperado

### 1. El mail: una checklist

Así, con datos reales del 28/09 a las 9:00 (el formato manda; el texto exacto puede ajustarse):

```
Asunto: NAVAR · 28/09 · faltan 6 cosas

✅ LLEGÓ HOY
☑ Tango A: cobranzas, pagos, cheques terceros, cheques propios (05:46)
☑ Tango AA: cobranzas, pagos, cheques terceros, tesorería (05:46)
☑ La Sheet se actualizó (06:33)

❌ FALTA
☐ Galicia: el bot falló a las 05:45 (se cerró el navegador al guardar).
   Último extracto: 28/09 00:27
☐ Macro: último extracto del 25/09 (hace 3 días) · subir a mano
☐ BBVA: último extracto del 24/09 (hace 4 días) · subir a mano
☐ Nación: último extracto del 24/09 (hace 4 días) · subir a mano
☐ Corrientes: último extracto del 16/09 (hace 12 días) · subir a mano
☐ Arqueo caja AA: último del 21/09 (hace 7 días) · cargar a mano
```

Reglas:
- **Una línea por fuente, siempre las mismas**, cada una en ✅ o en ❌ (nunca en las dos). Las
  fuentes son:
  - Tango A (4 fotos) y Tango AA (4 fotos, incluida tesorería);
  - cada banco que aparezca en Saldos Bancarios (Galicia automático, el resto manual);
  - el arqueo de caja AA;
  - "La Sheet se actualizó".
  Deuda bancaria e impuestos **no** van: se cargan cuando cambian, no todos los días.
- **Tango:** ✅ con la hora del parte si es de hoy y `8 de 8`. Si faltó alguna foto, una línea ❌
  por empresa con qué faltó, el motivo corto del parte y la fecha del último archivo de esa foto.
  Sin parte de hoy: ❌ "la bajada de Tango no corrió hoy · última: dd/mm hh:mm · revisar la notebook".
- **Galicia (y todo banco en `FUENTES_AUTOMATICAS`):** ✅ si el `_ESTADO_` de hoy dice OK: hora y
  "movimientos hasta dd/mm" (la última fecha que tiene en Saldos Bancarios). ❌ si falló o no hay parte
  de hoy: motivo corto + "Último extracto: dd/mm hh:mm", que es la fecha y hora (de modificación) del
  último Excel publicado en `Bancos/galicia`. **Ojo con el nombre:** desde la tarea 27 el bot publica
  `Movimientos Galicia AAAA-MM-DD.xlsx` (uno por día, se reemplaza); antes publicaba
  `Movimientos GALICIA <fecha_hora>.xlsx`. Buscar `^Movimientos Galicia .*\.xlsx$` **sin distinguir
  mayúsculas** y quedarse con el más nuevo por fecha de modificación.
  Galicia corre **dos veces** (05:45 y 05:48) y la segunda **pisa** el `_ESTADO_` del día: se usa ese
  archivo tal como está (si la primera falló y la segunda anduvo, es ✅). **No** se usa la fecha del último movimiento
  para decidir si falta (ver la revisión de la tarea 27).
- **Bancos manuales y arqueo:** ✅ si están al cierre hábil anterior ("Macro: al día, extracto hasta
  dd/mm"); ❌ si no: "último extracto del dd/mm (hace N días) · subir a mano". Misma lógica que hoy
  en `_faltantesAviso_`.
- **La Sheet se actualizó:** ✅ si el Registro tiene un `ok` de hoy **posterior** a las bajadas
  automáticas de hoy, con la hora. Si no: ❌ "la Sheet no importó lo de hoy · última importación:
  dd/mm hh:mm".
- **Asunto:** `NAVAR · dd/mm · todo al día` o `NAVAR · dd/mm · faltan N cosas` (N = líneas ❌).
- **⚠️ REVISAR** (sección al final, **solo si hay algo**): la notebook no está procesando (marca de
  vida de más de 60 min), una importación con ERROR **sin un `ok` posterior del mismo tipo**, un
  archivo retenido por el vigilante, o que no se pudo leer algo (Drive, Registro, etc.). **Se sacan
  del mail:** "Llegó a Drive", "El vigilante procesó", "La Sheet importó" (el detalle línea por
  línea), "Último export de Tango", "Último extracto cargado" y cualquier error que ya tenga un `ok`
  posterior. Hoy sale "Falló la importación de tesoreria_aa (rate limit)" del sábado a las 08:32,
  aunque el reintento de las 09:33 dio ok: eso no tiene que salir más.
- `avisoDiarioPrueba` sigue mostrando exactamente el mismo texto que se mandaría.

### 2. Horarios

**Ya hecho** (tareas 30 y 31, instalado el 29/09). No tocar.

## Comprobaciones

1. `probar_aviso_bajadas.cjs` actualizado con fotos inventadas. Casos:
   - todo al día (asunto "todo al día", sin ❌ ni ⚠️);
   - Tango 6 de 8 (❌ con qué faltó);
   - sin parte de Tango hoy;
   - Galicia ATENCIÓN (❌ con motivo y "Último extracto");
   - Galicia OK con último movimiento de hace 4 días (✅, no ❌);
   - "Último extracto" de Galicia con los dos nombres de archivo (viejo y nuevo) en la carpeta: toma el más nuevo;
   - manual atrasado y manual al día;
   - Sheet sin importar hoy;
   - ERROR con `ok` posterior (no sale) y ERROR sin `ok` posterior (sale en ⚠️);
   - un lunes.
   En cada caso, afirmar el asunto y qué líneas aparecen.
2. Si no hay `node`, dejarlo anotado. Claude lo corre con el JavaScript de macOS.
3. `grep` de nombres propios de personas vacío en lo agregado. Commit en la rama.

## Qué hice

## Revisión
