# Tarea 27 — Galicia NAVAR: temporal único por corrida y nombre del archivo publicado
Estado: aprobada (mergeada el 28/09/2026; falta la prueba de dos corridas seguidas en la notebook)
Rama: tarea/galicia-temporal-unico

## Objetivo

Que el bot de Galicia pueda correr **todos los días**. Hoy anda solo la primera vez: desde la segunda
falla al guardar la descarga, porque el archivo temporal de la corrida anterior sigue en la carpeta
con el mismo nombre.

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `tareas/23-galicia-recorrido-real.md`,
`bots/galicia/navar.py → descargar_csv`, `nucleo/navegador.py → abrir_navegador` y
`nucleo/fechas.py → rango_a_bajar`.

**Lo que pasó (28/09/2026):**
- 00:27, primera corrida con `descargas_temp` vacía → OK. Queda
  `.run/galicia/descargas_temp/galicia_por_validar.xlsx`.
- 07:00 (tarea programada) y 19:45 (tarea lanzada a mano) → las dos fallan igual, un segundo
  después de abrir el menú de descarga:
  `FALLO NAVAR SA: Download.save_as: Target page, context or browser has been closed`.
  No queda captura de error, porque la página ya no existe.
- 19:47: **se borra a mano `galicia_por_validar.xlsx`** y se relanza la tarea → **OK**, publica y
  deja saldos.
- En `descargas_temp` quedaron además dos archivos `<guid>.tmp` de 87.723 bytes. Son las descargas
  de las corridas fallidas: Playwright las guarda con nombre de GUID en `downloads_path`. Son Excel
  válidos de Galicia (110 movimientos, 28/08–22/09). Es decir, **el banco entregó el archivo**; lo
  que falló fue el `save_as` sobre un destino que ya existía, en Windows. El mensaje de Playwright
  engaña.

**Otra cosa, que no es falla:** `rango_a_bajar` hace `desde = min(ayer, último)`, así que **cada
corrida vuelve a bajar el último día guardado**. Nunca devuelve "sin novedades" una vez que hubo
una bajada. No rompe nada (el lector descarta repetidos), pero el `_nota` del perfil y la §6 dicen
que "el estado evita bajar dos veces el mismo día", y eso es falso.

## Archivos permitidos

- `bots/galicia/navar.py` — **solo** `descargar_csv` y una ayuda nueva si hace falta.
- `bots/galicia/test_navar.py`
- `clientes/navar/perfil.json` — **solo** `_nota` y `prefijo_archivo` de `bancos.galicia`.
- `clientes/navar/documentos/instalar_notebook.md` — **solo** la §6.
- `tareas/27-galicia-temporal-unico.md`

No tocar `nucleo/` (ni `fechas.py`: el comportamiento de volver a bajar el último día se queda).

## Resultado esperado

1. **Temporal con nombre único por corrida**: por ejemplo
   `galicia_por_validar_<AAAA-MM-DD_HHMMSS_microsegundos>.xlsx` en `ctx.descargas_dir`. Nunca se
   guarda encima de un archivo existente.
2. **Limpieza**:
   - Si la validación y la publicación salen bien, se borra el temporal de esa corrida.
   - Si fallan, **se conserva** (sirve para revisar), con su nombre único.
   - Al empezar `descargar_csv`, borrar de `ctx.descargas_dir` los `galicia_por_validar_*.xlsx` y los
     `*.tmp` con **más de 7 días**, para que la carpeta no crezca sin fin. Nada más que esos dos
     patrones.
   - Comentario en criollo con el porqué: en Windows, guardar encima del temporal anterior hacía
     fallar la descarga con un mensaje engañoso ("página cerrada"); pasó el 28/09.
3. **Si `save_as` falla igual**: log con la causa y, si `descarga.failure()` devuelve algo, también
   eso. Sin reintentos: con el nombre único no debería repetirse, y si se repite queremos verlo.
4. **Notas**: corregir el `_nota` de `bancos.galicia` y la §6. Cada corrida vuelve a bajar
   (el banco trae 30 días, así que es gratis) y el lector descarta repetidos. El estado solo marca
   hasta qué día se bajó. Sacar el "evita bajar dos veces el mismo día". Agregar en "Qué puede
   fallar" una fila para `Target page, context or browser has been closed` al guardar: mirar
   `descargas_temp` (si quedó un `.tmp`, el banco entregó; revisar permisos y espacio).
5. **Nombre del archivo publicado** (pedido de Thomas, 28/09): que se llame
   **`Movimientos Galicia AAAA-MM-DD.xlsx`**, con la fecha **del día de la descarga** y sin hora. Por
   ejemplo, `Movimientos Galicia 2026-09-28.xlsx`.
   - `bancos.galicia.prefijo_archivo` pasa a `"Movimientos Galicia"`. El formato de la fecha va en el
     código, con un comentario.
   - **Si ese día ya hay un archivo con ese nombre, se reemplaza** (con el mismo `os.replace` de hoy).
     El más nuevo trae los mismos 30 días más lo que haya entrado después, así que queda un archivo
     por día. Si la validación falla, no se publica y el anterior del día queda intacto.
   - El lector no depende del nombre (reconoce el banco por la carpeta). Solo ignora los que empiezan
     con `para_pegar` o `~$`, así que no hay que tocarlo.
   - Actualizar la §6 con el nombre nuevo.
6. **Tests**:
   - Dos descargas seguidas con el mismo `ctx.descargas_dir` y un doble de `Download` cuyo `save_as`
     **falla si el destino existe** (así se reproduce el caso): las dos pasan.
   - Tras una publicación OK, el temporal ya no está.
   - Con una validación que falla, el temporal queda.
   - La limpieza borra un `galicia_por_validar_*.xlsx` y un `.tmp` viejos (fechas de modificación
     puestas a mano), no toca uno nuevo ni otro archivo cualquiera.
   - El publicado se llama `Movimientos Galicia <hoy AAAA-MM-DD>.xlsx`; una segunda publicación del
     mismo día lo reemplaza (queda uno solo) y una validación fallida no toca el existente.

## Comprobaciones

1. `python -m py_compile bots/galicia/navar.py bots/galicia/test_navar.py` y JSON válido.
2. `python -m unittest bots.galicia.test_navar` OK.
3. Commit en la rama. La prueba real es en la notebook: dos corridas seguidas sin borrar nada a mano.

## Qué hice

- Cada corrida guarda la descarga en un temporal propio con fecha, hora e identificador único. Si
  valida y publica bien, borra ese temporal; si falla la validación o la publicación, lo conserva.
  Al empezar, limpia solamente los `galicia_por_validar_*.xlsx` y `*.tmp` de más de siete días.
- Si Playwright falla al guardar, el log muestra el error y también la causa que informa la
  descarga, cuando está disponible. No agrega reintentos.
- El archivo publicado se llama `Movimientos Galicia AAAA-MM-DD.xlsx`. Una segunda corrida del
  mismo día lo reemplaza después de validar; una fallida deja intacto el anterior.
- Corregí la nota del perfil y la sección 6 de la guía: Galicia vuelve a bajar sus últimos 30 días
  en cada corrida; el lector descarta repetidos. Agregué cómo revisar el mensaje engañoso de
  "página cerrada" y los archivos temporales.
- Agregué pruebas con Excel inventados para dos corridas seguidas, reemplazo diario, conservación
  ante fallas de validación o publicación, limpieza selectiva y registro de fallas de guardado.
  `python -m unittest bots.galicia.test_navar`: **26 pruebas OK**. Compilación, JSON válido y
  `git diff --check`: OK.
- No pude probar el banco, Playwright real, los permisos de Windows, Drive ni la tarea programada.
  La prueba final es en la notebook: correr Galicia dos veces seguidas sin borrar temporales.

## Revisión

**Claude, 28/09/2026.** Hace lo pedido. El temporal es único por corrida (fecha + uuid), se borra
después de publicar y queda si falla la validación o la publicación. La limpieza solo borra
`galicia_por_validar_*.xlsx` y `*.tmp` de más de 7 días. El `save_as` fallido deja en el log la
causa y el `failure()`. El publicado se llama `Movimientos Galicia AAAA-MM-DD.xlsx` y una segunda
corrida del mismo día lo reemplaza con `os.replace`. `_nota` y §6 corregidos (ya no dicen que el
estado evita bajar dos veces). 26 tests OK, compila, JSON válido, `git diff --check` limpio. No toca
`nucleo/` ni los lectores. Aprobada.

Menores, sin cambio:
- `import uuid` quedó adentro de la función; es solo estilo.
- El `galicia_por_validar.xlsx` sin sufijo que dejó la corrida del 28/09 a las 19:47 no entra en el
  patrón de limpieza. Ya no molesta (el nombre nuevo nunca coincide), pero queda ahí hasta que se
  borre a mano.
- Si Drive o el vigilante justo tienen abierto el archivo del día cuando una segunda corrida lo
  reemplaza, `os.replace` puede fallar en Windows. Sería un fallo de ese día, visible en el log, y
  la corrida siguiente lo resuelve.

