# Tarea 28 — Galicia NAVAR: rescatar la descarga cuando la página se cierra
Estado: pendiente
Rama: tarea/galicia-rescatar-descarga

## Objetivo

Que Galicia deje de fallar "una de cada dos". Cuando el guardado de la descarga falla porque la página
se cerró, el bot tiene que **tomar el archivo que el navegador ya dejó en su carpeta de descargas** y
seguir con los mismos controles de siempre.

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `tareas/27-galicia-temporal-unico.md` (entera, con la
Revisión), `bots/galicia/navar.py → descargar_csv` y `nucleo/navegador.py → abrir_navegador`
(contexto persistente con `downloads_path = ctx.descargas_dir`).

**Corridas en la notebook, 27-28/09/2026:**

| Hora | Cómo | Resultado |
|---|---|---|
| 28/09 00:27 | PowerShell | OK |
| 28/09 07:00 | tarea programada | FALLO `Download.save_as: Target page, context or browser has been closed` |
| 28/09 19:45 | tarea programada | FALLO, mismo mensaje |
| 28/09 19:47 | tarea programada | OK |
| 28/09 20:11 | tarea programada, **ya con la tarea 27** (temporal único) | FALLO, mismo mensaje. `Download.failure()` también da "Target page... closed" |
| 28/09 20:13 | tarea programada | OK (`Movimientos Galicia 2026-09-28.xlsx`) |

Lo que se sabe:
- **Es intermitente.** La tarea 27 descartó que la causa fuera el temporal anterior.
- Las tres fallas fueron la **primera corrida después de un rato**; las que anduvieron vinieron
  minutos después de otra.
- En cada falla, el `download` **llegó** (el `suggested_filename` ya era `Extracto_CC545950701.xlsx`
  y pasó el control), pero la **página principal ya no existía**: tampoco se pudo sacar la captura
  de error.
- **El archivo quedó completo** en `ctx.descargas_dir` con nombre de GUID (`<guid>.tmp`, 87.723
  bytes). Dos de esos, abiertos en la Mac, son Excel válidos de Galicia: el lector los lee
  (110 movimientos, 28/08–22/09).
- No sabemos qué cierra la página (una pestaña aparte que baja y se cierra, un cierre de la página,
  una caída del proceso). Esta tarea no depende de saberlo, pero tiene que dejarlo **registrado**.

## Archivos permitidos

- `bots/galicia/navar.py` — **solo** `descargar_csv` y ayudas nuevas.
- `bots/galicia/test_navar.py`
- `clientes/navar/documentos/instalar_notebook.md` — **solo** la fila de `Target page...` de la tabla
  "Qué puede fallar" de la §6.
- `tareas/28-galicia-rescatar-descarga.md`

No tocar `nucleo/`.

## Resultado esperado

1. **Antes del clic en Excel**: guardar la lista de archivos que hay en `ctx.descargas_dir`, con sus
   nombres. Registrar en el log, sin frenar nada, estos eventos: `page.on("close")`, `page.on("crash")`
   y `page.context.on("page")` (una pestaña nueva, con su URL si la tiene). Que el log diga "la página
   se cerró", "la página se cayó" o "se abrió una pestaña nueva: <url>".
2. **Si `save_as` falla** (cualquier excepción): no frenar todavía. Buscar en `ctx.descargas_dir` un
   archivo **que no estaba antes del clic** y que no sea un `galicia_por_validar_*`. Esperar hasta
   30 s a que:
   - aparezca **exactamente uno** (si hay más de uno nuevo, frena con el conteo);
   - su tamaño no cambie durante 2 s seguidos;
   - sea un zip válido (`zipfile.is_zipfile`).

   Entonces copiarlo al temporal único de la corrida y seguir **por el mismo camino** que un
   `save_as` exitoso: `validar_excel`, publicación, borrado del temporal. El control del nombre
   (`_validar_nombre_descarga` sobre `suggested_filename`) ya se hizo antes del `save_as` y **sigue
   siendo obligatorio**: si no pasó, no se llega acá.
3. Si no aparece ningún archivo en 30 s, o no se estabiliza, o no es zip: frenar como hoy, con un
   mensaje que diga qué se buscó y qué se encontró.
4. Log claro cuando se rescata: `"   La página se cerró al guardar; tomé el archivo que dejó el navegador (<nombre>, <bytes> bytes)"`.
5. Comentario en criollo con el porqué: pasó el 28/09, intermitente, el archivo llegaba completo.
6. **§6, fila `Target page...`**: el bot ahora rescata el archivo solo. Si igual falla, mirar el log
   (qué evento de página se registró) y `descargas_temp`.
7. **Tests** (dobles, sin navegador):
   - `save_as` falla y en la carpeta aparece un `<guid>.tmp` que es un Excel válido → se publica.
   - `save_as` falla y aparecen dos archivos nuevos → frena con el conteo.
   - `save_as` falla y no aparece nada (con un tiempo de espera chico en el test) → frena.
   - `save_as` falla y el archivo nuevo no es zip → frena.
   - Un archivo que **ya estaba** antes del clic nunca se toma.
   - `save_as` anda → mismo comportamiento que hoy (no busca nada en la carpeta).

## Comprobaciones

1. `python -m py_compile bots/galicia/navar.py bots/galicia/test_navar.py`.
2. `python -m unittest bots.galicia.test_navar` OK.
3. Commit en la rama. La prueba real: **tres corridas seguidas de la tarea programada con OK**, con al
   menos una que sea "la primera después de un rato" (por ejemplo, la de las 07:00).

## Qué hice

## Revisión
