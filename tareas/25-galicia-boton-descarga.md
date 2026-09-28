# Tarea 25 — Galicia NAVAR: encontrar el botón de descarga y la opción Excel
Estado: pendiente
Rama: tarea/galicia-boton-descarga

## Objetivo

Que el bot abra el menú de descarga (la flechita a la derecha de "Filtros") y elija **Excel** en
ese menú, sin confundirse con botones parecidos ni con ventanas escondidas de la página.

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `tareas/23-galicia-recorrido-real.md`,
`tareas/24-galicia-campos-login.md` y `bots/galicia/navar.py` (`_buscar_boton_descarga`,
`descargar_csv`, `_esperar_unico_visible`).

**Corrida del 27/09/2026 a las 22:01**: login confirmado, empresa `NAVAR SA`, cuenta abierta,
**saldos Actual y Disponible leídos bien** (coinciden con la pantalla). Después frenó con
`el botón Filtros de Movimientos no apareció visible en 45.0 s`.

**Diagnóstico en la notebook** (ya logueado y en la cuenta, sin clics; ventana de 1440×900). Cómo
están armados los elementos:

| Qué | Cómo es por dentro | Caja [x, y, ancho, alto] |
|---|---|---|
| Botón **Filtros** | `<button aria-label="filter2">` con texto visible "Filtros" (el texto está en un `<span class="button-wrap">` adentro). Como el `aria-label` manda sobre el texto, **su nombre accesible es "filter2"**, por eso `get_by_role("button", name="Filtros")` da 0. | [1243, 595, 101, 40] |
| **Botón de descarga** (la flechita) | `<button role="button" aria-label="Button">`, sin texto, clase con `button__border`. | [1352, 595, 40, 40] |
| Buscador de la tabla | `input` con placeholder "Buscá en la tabla" | [1002, 604, 224, 22] |
| Flechitas de cada fila | **50 botones** `aria-label="Button"` de 24×24, clase `button__simple`, en x=1286 | uno por fila |
| Otros `aria-label="Button"` | ninguno más en la fila de Filtros | — |

**Trampa de las ventanas escondidas.** La página tiene cargados modales y paneles que **no se ven**
en la foto de pantalla, pero que Playwright da como `visible=True` (tienen caja; se esconden con
opacidad o fuera del área visible):
- un panel de filtros (x≈1465, afuera de la ventana de 1440) con título "Filtros" y botones
  "Aplicar" y "Restablecer";
- modales con "Cancelar"/"Continuar", "Descargar constancia de CBU"/"Copiar datos",
  "Restablecer"/"Cancelar"/**"Descargar"** (probablemente el de "Personalizado") y
  "Ver Novedades"/"Omitir";
- un botón `aria-label="fileDownload"` en x=1586, afuera de la ventana.

En el orden de la página, lo que sigue a Filtros son **"Aplicar" y "Restablecer" del panel
escondido**. Por eso `filtros.locator("xpath=following::button[1]")`, que hoy es la tercera
alternativa, **caería en "Aplicar"**. Hay que sacarla. Por lo mismo, un `get_by_text("Excel")` suelto
podría encontrar también un "Excel" del modal "Personalizado" escondido.

El menú que abre la flechita (captura de Thomas) aparece **debajo del botón, alineado a su
derecha**, con cinco opciones en columna: `.CSV`, `.PDF`, `.SAP`, `Excel`, `Personalizado`.

## Archivos permitidos

- `bots/galicia/navar.py` — **solo** `_buscar_boton_descarga`, `descargar_csv` y ayudas nuevas que
  necesiten.
- `bots/galicia/test_navar.py`
- `tareas/25-galicia-boton-descarga.md`

## Resultado esperado

1. **Filtros**: único visible entre `page.locator("button[aria-label='filter2']")` y
   `page.locator("button").filter(has_text=re.compile(r"^\s*Filtros\s*$"))`, con la espera de
   `_esperar_unico_visible`. Sirve **solo como referencia de posición**: no se le hace clic.
2. **Botón de descarga por posición relativa a Filtros**: entre los `button` visibles, el que cumple
   **todo esto**: tiene caja; su centro vertical está a ±10 px del centro de Filtros; su borde
   izquierdo está entre el borde derecho de Filtros y 60 px más a la derecha; no tiene texto. Tiene
   que haber **exactamente uno**. Si hay cero o más de uno, frena diciendo cuántos encontró. **Se hace
   clic en el elemento elegido, nunca en coordenadas** (`element.click()`, no `page.mouse`). Sacar las
   alternativas `following::button[1]` y `name=/descarg/`. Esta última no aplica: el nombre es
   "Button". Dejar un comentario en criollo con el porqué: el botón no tiene nombre propio y la página
   tiene copias escondidas.
3. **Opción Excel por posición relativa al botón**: después del clic, esperar (hasta el `timeout`) un
   elemento con texto exacto `Excel` que esté **debajo** del botón de descarga (su borde superior por
   debajo del borde inferior del botón y a menos de 400 px) y horizontalmente cerca (centro entre
   300 px a la izquierda del botón y 50 px a su derecha). Exactamente uno; si no, frena con el
   conteo. Captura `menu_descarga` antes de elegir. Mismo criterio para el clic: sobre el elemento.
4. El resto de `descargar_csv` queda igual: el control del nombre `Extracto_CC545950701.xlsx`, la
   validación y la publicación.
5. **Tests** con dobles que tengan `bounding_box()`:
   - Fila con Filtros + flechita + un "Aplicar" escondido fuera de la ventana y 3 flechitas de fila
     de 24×24 → elige la flechita de la fila de Filtros.
   - Dos botones candidatos en la fila → frena. Ninguno → frena.
   - Menú con `Excel` debajo del botón + otro `Excel` lejos (modal escondido) → elige el de abajo.
   - Nunca se llama a `page.mouse`.

## Comprobaciones

1. `python -m py_compile bots/galicia/navar.py bots/galicia/test_navar.py`.
2. `python -m unittest bots.galicia.test_navar` OK.
3. Commit en la rama. Lo de pantalla lo prueba Thomas en la notebook.

## Qué hice

## Revisión
