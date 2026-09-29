# Tarea 29 — Galicia NAVAR: el rescate tiene que mirar la carpeta Descargas de Windows
Estado: lista para revisión
Rama: tarea/galicia-rescate-descargas

## Objetivo

Que el rescate de la tarea 28 encuentre el archivo **donde de verdad queda**. Cuando la página se
cierra, el Excel no cae en la carpeta del bot sino en la carpeta Descargas del usuario de Windows.

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `tareas/28-galicia-rescatar-descarga.md` (entera, con la
Revisión) y `bots/galicia/navar.py` (`_rescatar_descarga`, `_registrar_eventos_descarga`,
`descargar_csv`).

**Corrida del 28/09/2026 a las 23:26**, tarea programada, "en frío" (3 horas sin correr), ya con la
tarea 28:

```
23:26:55 Login confirmado. … Empresa activa al entrar: NAVAR SA
23:27:00 Saldo Actual … | Galicia NAVAR no usa filtro …
23:27:03    la página se cerró
23:27:03    Falló guardar descarga de Galicia: Download.save_as: Target page, context or browser has been closed; …
23:27:33 FALLO NAVAR SA: Rescate agotado: busqué … en …\.run\galicia\descargas_temp …; encontré 0 archivos nuevos.
```

Búsqueda posterior en la notebook: el archivo apareció en
**`C:\Users\USer\Downloads\58baa3dd-8d7d-4f77-b2e7-d3716493fcf4.tmp`**, de **87.723 bytes**, con hora
**23:27:03** (el mismo segundo del cierre). Los `.tmp` de las fallas anteriores también estaban ahí:
Thomas los copió desde esa carpeta, y dos de ellos, abiertos en la Mac, son Excel válidos de Galicia.

Lo que muestra:
- Se cierra **la página principal** (el evento `close`). **No** se registró ninguna pestaña nueva.
- Cuando pasa eso, Chromium termina la descarga en la carpeta **Descargas del usuario** con nombre
  `<guid>.tmp`, y no en `downloads_path`.
- El archivo llega **completo**.
- Sigue siendo intermitente: falla la primera corrida después de un rato y anda la siguiente.

## Archivos permitidos

- `bots/galicia/navar.py` — **solo** `_rescatar_descarga`, `descargar_csv` y ayudas nuevas.
- `bots/galicia/test_navar.py`
- `clientes/navar/documentos/instalar_notebook.md` — **solo** la fila `Target page...` de la §6.
- `tareas/29-galicia-rescate-en-descargas.md`

No tocar `nucleo/`.

## Resultado esperado

1. **Dos carpetas vigiladas**: `ctx.descargas_dir` (como hoy) y la carpeta Descargas del usuario
   (`Path.home() / "Downloads"`; si no existe, se sigue solo con la del bot). La foto "antes del clic"
   se toma de **las dos**.
2. **En la carpeta Descargas del usuario, reglas más estrictas**, porque ahí también baja cosas la
   gente:
   - Solo nombres con forma de GUID + `.tmp`: `^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.tmp$`,
     sin distinguir mayúsculas.
   - Que **no estuviera** en la foto de antes del clic **y** que su fecha de modificación sea
     posterior al clic.
   - Estable 2 s y zip válido, como hoy.
3. **Único entre las dos carpetas**: si entre las dos hay más de un candidato, frena con el conteo y
   los nombres. En la carpeta del bot las reglas quedan como hoy.
4. **Después de rescatar desde Descargas del usuario**: copiar al temporal único y **borrar el `.tmp`
   de Descargas** (tiene movimientos reales y no debe quedar ahí). Si no se puede borrar, avisar en el
   log y seguir.
5. **Limpieza de Descargas del usuario** al empezar `descargar_csv`: borrar solo los archivos con forma
   de GUID + `.tmp`, de más de 7 días **y** que sean zip cuyo contenido tenga una hoja `Movimientos`
   con el encabezado `Fecha` en A1. O sea, solo lo que es seguro que dejó este bot. Nada más.
6. El mensaje de "rescate agotado" dice **qué carpetas** miró y qué encontró en cada una.
7. **§6, fila `Target page...`**: el archivo aparece en `C:\Users\<usuario>\Downloads\<guid>.tmp`; el
   bot lo toma solo y lo borra de ahí.
8. **Tests** (dobles de carpeta; `Path.home()` inyectable o parcheado):
   - La página se cierra y aparece un GUID.tmp válido en Descargas del usuario → se publica y el
     `.tmp` desaparece de Descargas.
   - Un archivo que ya estaba en Descargas antes del clic → no se toma.
   - En Descargas aparece un archivo nuevo **sin** forma de GUID (`informe.xlsx`) → no se toma.
   - Candidatos en las dos carpetas a la vez → frena con el conteo.
   - La limpieza borra un GUID.tmp viejo que es un Excel de Galicia, y **no** borra un GUID.tmp viejo
     que no lo es ni un archivo viejo cualquiera.

## Comprobaciones

1. `python -m py_compile bots/galicia/navar.py bots/galicia/test_navar.py`.
2. `python -m unittest bots.galicia.test_navar` OK.
3. Commit en la rama. La prueba real: una corrida **en frío** (la primera después de un rato largo)
   que termine con `La página se cerró al guardar; tomé el archivo…` y `OK: 1`, y después dos más con OK.

## Qué hice

- El rescate toma la foto previa de la carpeta del bot y de Downloads del usuario, si existe.
  En Downloads exige GUID.tmp (también mayúsculas), nombre ausente en la foto y modificación
  posterior al clic. Cuenta los candidatos entre ambas carpetas antes de elegir.
- Mantiene los dos segundos de estabilidad, zip válido y validación del Excel antes de publicar.
  Tras copiar desde Downloads borra el origen; si Windows no deja, avisa y continúa.
- La limpieza de Downloads sólo borra GUID.tmp de más de siete días cuyo libro tenga la hoja
  Movimientos y Fecha en A1. Otros archivos, libros y temporales recientes quedan intactos.
- El error por espera agotada detalla cada carpeta y sus candidatos. Actualicé únicamente la
  fila autorizada de la guía; no modifiqué nucleo ni el registro de eventos.
- Pruebas con carpetas y Excel inventados: rescate y borrado desde Downloads, archivos previos,
  nombre común, fecha anterior, candidatos en ambas carpetas, limpieza selectiva y borrado
  impedido. Path.home está parcheado en todas las pruebas para no tocar Descargas reales.
- Verificado: 40 pruebas OK, py_compile de ambos archivos y git diff --check limpio.
  Sin dependencias nuevas. Falta la corrida real en frío con rescate y OK: 1, seguida de otras
  dos con OK; no se probó Windows, banco ni Drive desde este entorno.

## Revisión
