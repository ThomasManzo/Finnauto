# Tarea 27 — El aviso de las 9:00 tiene que saber que Tango y Galicia bajan solos
Estado: lista para revisión
Rama: tarea/aviso-bajadas

## Objetivo

Que el mail de las 09:00 diga, en una línea por bajada automática, si **corrió hoy y cómo le fue**
("Tango 07:30: 8 de 8", "Galicia 07:00: OK") y avise **el mismo día** si no corrió o falló, con la
indicación correcta ("revisar la notebook"). Hoy el aviso está pensado para exports subidos a mano:
dice "falta actualizar", "subida manual" y "pedir un export actualizado".

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `CLAUDE.md`, `clientes/navar/LEEME.md` (secciones del
25 y 28/09), `clientes/navar/herramientas/aviso_diario.gs` entero, `ingestas/tango_live.py`
(`main`) y `nucleo/salidas.py → escribir_estado_drive`.

Cómo es el circuito desde el 25-28/09 (en la notebook de NAVAR):
- **07:00 bot de Galicia.** Al terminar, deja en Drive `Bancos/galicia/_ESTADO_Galicia_DD-MM.txt`
  (`escribir_estado_drive`). Dos ejemplos reales:
  ```
  Bot Galicia - 28/09/2026 00:27

  OK: no fallo ninguna empresa.

  Bajadas OK (1): NAVAR SA
  Sin novedades (0): -
  ```
  ```
  Bot Galicia - 27/09/2026 22:02

  >>> ATENCION: 1 empresa(s) fallaron. Bajar a mano hoy:
     - NAVAR SA (el botón Filtros de Movimientos no apareció visible en 45.0 s)

  Bajadas OK (0): -
  Sin novedades (0): -
  ```
- **07:30 bajada de Tango** (`ingestas/tango_live.py`, tarea "finauto NAVAR Tango"). Deja 8 Excel
  (4 de A, 4 de AA, incluida la tesorería de AA) y escribe su salida en `privado/tango_live.log`
  **de la notebook**, que no se ve desde Drive. Si falla de madrugada, el mail no lo sabe.
- **Cada 15 min el vigilante.** Ya deja su marca de vida en `_para la Sheet/vigilante_ultima_pasada.txt`
  (fecha UTC ISO) y el aviso la lee (`_leerDatosAviso_ → Latido`). Esta tarea copia ese patrón.
- `_faltantesAviso_` ya pide las fotos de Tango "de hoy" (bien), pero con texto de carga manual.
  `_armarAviso_` además alerta si el último `para_pegar_en_la_sheet_*` tiene más de 3 días, con
  "Pedir un export actualizado". Eso quedó viejo.
- Los demás bancos (Macro, BBVA, Nación, Corrientes) y el arqueo de caja AA **siguen siendo a mano**
  por ahora: su texto actual está bien.

## Archivos permitidos

- `ingestas/tango_live.py`
- `ingestas/test_tango_live.py`
- `clientes/navar/herramientas/aviso_diario.gs`
- `lector/pruebas/probar_aviso_bajadas.cjs` (nuevo; mismo estilo que `probar_importador_filtros.cjs`:
  cargar el `.gs` en un contexto de Node y probar con una foto de datos inventada, sin Google)
- `tareas/27-aviso-con-bajadas-automaticas.md`

## Resultado esperado

1. **`tango_live.py` deja su propio parte en Drive.** Al terminar una bajada normal (no `--probar`
   ni `--simular`), siempre, aunque fallen consultas, escribe `<raíz>/_para la Sheet/tango_ultima_bajada.txt`
   de forma atómica (temporal que empiece con `.` + `os.replace`). Contenido en texto simple:
   - línea 1: fecha y hora UTC ISO, mismo formato que la marca de vida del vigilante;
   - línea 2: `8 de 8` (o `N de 8`);
   - una línea por consulta que falló, con el nombre del archivo y el error cortado a ~150
     caracteres, **sin token ni datos de clientes**.

   Si no puede escribirlo (Drive no montado), avisarlo en el log y seguir: no puede romper la bajada.
   Si `--destino` apunta a otra carpeta, el parte va a `<destino>/_para la Sheet/`.
2. **El aviso lee los dos partes** en `_leerDatosAviso_`, cada uno en su propio `leer(...)`, así una
   falla no tapa a la otra:
   - `tango_ultima_bajada.txt` (en `_para la Sheet`);
   - el `_ESTADO_Galicia_DD-MM.txt` **de hoy** (en `Bancos/galicia`). Hoy = zona de Buenos Aires.
3. **Encabezado del mail**, una línea por bajada automática:
   - Tango: `Bajada de Tango: hoy 07:31 · 8 de 8`. Si hay fallas: `hoy 07:31 · 6 de 8` + alerta con
     las consultas que fallaron. Si el parte no es de hoy: alerta `La bajada de Tango de hoy no corrió
     (último parte: dd/mm hh:mm). Revisar que la notebook esté prendida y la tarea "finauto NAVAR Tango"`.
   - Galicia: `Bot de Galicia: hoy hh:mm · OK`. Si el estado dice ATENCION: alerta con el motivo. Si no
     hay `_ESTADO_` de hoy: alerta `El bot de Galicia no corrió hoy. Revisar la tarea "finauto NAVAR Galicia"`.
4. **Textos en `_faltantesAviso_`:** para las fuentes automáticas (fotos de Tango, tesorería AA y el
   extracto de Galicia), cuando falta lo de hoy, decir `no llegó la bajada automática de hoy; revisar la
   notebook` en vez de "falta actualizar". Sacar "(subida manual)" de Tesorería AA. Las demás
   fuentes, sin cambios.
5. **Qué es automático:** una lista explícita al principio del `.gs` (por ejemplo
   `FUENTES_AUTOMATICAS = ["tango", "tesoreria_aa", "galicia"]`), comentada. Cuando se automatice
   Macro, se agrega ahí y listo.
6. **Sacar** la alerta de "más de 3 días sin export de Tango / pedir un export": la reemplaza el punto 3.
7. Nada más cambia: mismo asunto, mismas secciones, mismo horario, mismas funciones públicas.

## Comprobaciones

1. `python -m py_compile ingestas/tango_live.py` y `python -m unittest ingestas.test_tango_live`,
   con pruebas nuevas: el parte se escribe con 8 de 8, con fallas (sin token en el texto), y un error
   al escribirlo no rompe la bajada.
2. `node lector/pruebas/probar_aviso_bajadas.cjs` con fotos inventadas. Casos: Tango 8/8 hoy; Tango
   6/8; parte de Tango de ayer; Galicia OK hoy; Galicia ATENCION; sin `_ESTADO_` de hoy; un lunes. En
   cada caso, qué líneas y alertas salen. Anotar si no hay `node` para correrlo.
3. Dejar escrito cómo lo prueba Thomas: pegar el `.gs` y correr "Ver el aviso de hoy (sin mandar)".
4. `grep` de nombres propios de personas vacío en lo agregado. Commit en la rama.

## Qué hice

- `ingestas/tango_live.py` ahora deja `_para la Sheet/tango_ultima_bajada.txt` después de cada
  corrida normal: hora UTC, cantidad sobre 8 y una línea corta por consulta fallida. Se publica de
  forma atómica, no incluye el token y una falla al escribirlo queda en el log sin romper la bajada.
- `aviso_diario.gs` lee por separado el parte de Tango y el estado diario de Galicia. El encabezado
  informa hora y resultado de cada automatización, y genera la alerta correspondiente si falló, si
  el parte es viejo o si no apareció el de hoy.
- Declaré `FUENTES_AUTOMATICAS` con Tango, tesorería AA y Galicia. Sus faltantes ahora indican que no
  llegó la bajada automática y que hay que revisar la notebook; las fuentes manuales conservan su
  texto. Saqué la alerta vieja de pedir un export de Tango por antigüedad.
- Agregué pruebas Python para el parte 8 de 8, las fallas sin token y el error de escritura. Agregué
  una prueba Node con datos inventados para Tango 8/8 y 6/8, parte de ayer, Galicia OK/ATENCIÓN/sin
  estado y el cierre de un lunes.
- Verifiqué compilación y 15 pruebas Python, la prueba nueva del aviso y la prueba anterior del
  importador: todo pasa. También confirmé que no agregué nombres propios de personas.
- Prueba pendiente en Google: pegar `clientes/navar/herramientas/aviso_diario.gs` en Apps Script y
  ejecutar **«Ver el aviso de hoy (sin mandar)»** antes de dejarlo enviando correos.

## Revisión
