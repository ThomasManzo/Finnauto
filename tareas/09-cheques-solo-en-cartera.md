# Tarea 09 — Que un export de cheques mal filtrado no pueda ensuciar el cash
Estado: lista para revisión
Rama: tarea/cheques-en-cartera

## Objetivo

El 22/09 un export de **cheques de terceros** vino sin filtrar y trajo **75.611 filas con cheques
desde 1994** (cobrados, rechazados y aplicados) en lugar de las **~1.694** que están realmente en
cartera. Si eso entra al cash, la cobranza estimada se va a las nubes: los cheques en cartera son
ingreso futuro. Se frenó a mano antes de que se procesara, pero el sistema no lo habría frenado.

Que el lector se defensa solo: **quedarse únicamente con lo que está en cartera**, sin importar
qué traiga el export.

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `CLAUDE.md`, `clientes/navar/documentos/manual_cash.md`.

Evidencia medida sobre los dos exports reales del mismo proceso de Tango (11583):

| | Export bueno (21/09) | Export malo (22/09) |
|---|---|---|
| Filas | 1.694 | 75.611 |
| `Estado` / `Cód. estado` | todas `En Cartera` / `C` | `Aplicado`/`A` 73.671 · `Rechazado`/`R` 1.801 · vacío 16.615 · más las En Cartera |
| Columnas | 15, incluye `CUIT del cliente` | 14, otro orden, sin `CUIT del cliente` |
| Fechas | 2026-01-01 → 2027-02-18 | **1994-04-07** → 2027-02-18 |

O sea: son **dos vistas guardadas distintas** de la misma consulta; la buena filtra por estado y la
otra no. El nombre del archivo es igual, así que por el nombre no se distinguen.

Hoy el control del vigilante (`control_contra_anterior`) solo frena cuando una lista **se achica**
más de la mitad. Una lista que **explota** pasa derecho. Eso también hay que cubrirlo.

## Archivos permitidos

- `lector/tango.py` — el filtro por estado.
- `clientes/navar/herramientas/vigilante.py` — el control por crecimiento desmedido.
- `clientes/navar/catalogo.json` — si conviene que los estados válidos sean configurables.
- `clientes/navar/documentos/manual_cash.md` — §6/§7.
- `lector/pruebas/`
- `tareas/09-cheques-solo-en-cartera.md`

## Resultado esperado

1. **Cheques de terceros**: entran al cash solo los que están **en cartera**. Mirar `Cód. estado`
   (`C`) y `Estado` (`En Cartera`), tolerando mayúsculas, acentos y espacios; si ninguna de las dos
   columnas viene, **no adivinar**: dejar la lista afuera y avisar, en vez de cargar cualquier cosa.
2. **Cheques propios**: el equivalente es lo que todavía no se debitó. Revisá qué estados trae ese
   export (hoy `Al Cobro`) y aplicá el mismo criterio, explicándolo.
3. Lo descartado se **cuenta y se informa** en el resumen del lector: "se ignoraron N cheques que no
   están en cartera (Aplicado, Rechazado, ...)". Que se vea, no que desaparezca en silencio.
4. **Vigilante**: además del control por achicamiento, frenar cuando una solapa **crece de forma
   desmedida** respecto de la anterior (por ejemplo más de 3 veces, o más de X filas), con el mismo
   mecanismo de `_retenido` y un mensaje que diga qué pasó. Elegí el umbral y justificalo: tiene que
   dejar pasar un crecimiento normal (de 332 a 337 filas) y frenar 1.694 → 75.611.
5. Prueba automática de las dos cosas, con datos inventados.

## Comprobaciones

1. Correr el lector contra los dos exports reales (rutas abajo, se leen nada más) y reportar:
   cuántas filas entran y cuántas se descartan en cada uno. **Con el export malo, el resultado
   tiene que ser prácticamente igual al del bueno.**
2. `python -m py_compile` de lo tocado + la prueba nueva.
3. `grep` de nombres propios vacío. Commit en la rama.

```
"/Users/thomasmanzo/Library/CloudStorage/GoogleDrive-thomasezequielmanzo@gmail.com/Mi unidad/NAVAR - Datos/Cheques/A Cheques terceros 2026-09-21.xlsx"
"/Users/thomasmanzo/Library/CloudStorage/GoogleDrive-thomasezequielmanzo@gmail.com/Mi unidad/NAVAR - Datos/Cheques/_revisar/A Cheques terceros 2026-09-22 (TRAE HISTORIA DESDE 1994 - NO USAR).xlsx"
```

## Qué hice

Implementado en el worktree y rama indicados, sin modificar los exports ni publicar en Drive,
la Sheet o la notebook. Estado final: lista para revisión **con discrepancia en la evidencia**.

### Cambios

- `lector/tango.py`: terceros admite C / En Cartera normalizados. Si ambos valores vienen,
  deben coincidir; un valor vacío permite usar el otro. Sin columnas o sin valores válidos,
  queda afuera con motivo contado. Encabezados exactos para no confundir Estado con Subestado.
  Propios exige Al Cobro; conserva las reglas de fechas y cuenta además faltantes de fecha/importe.
  El resumen informa cantidad total descartada y detalle por estado o motivo.
- `clientes/navar/herramientas/vigilante.py`: retiene si la cantidad supera el triple **y**
  aumenta más de 100 filas. Evita alarmas por listas chicas o crecimiento normal y frena el caso
  1.694 → 75.611. Conserva achicamiento y compara también solapas nuevas (antes = 0).
  Se cierra el Excel al contar y una salida sana no cancela la retención de otra en la misma tanda.
- `clientes/navar/documentos/manual_cash.md`: §6/§7 explica filtro, umbral y límites.
- `lector/pruebas/test_cheques_en_cartera.py`: pruebas con datos inventados de estados,
  columnas ausentes, contradicciones, resumen, umbrales y traslado real a `_retenido`.
- `lector/pruebas/comparar_cartera_real.py`: comprobación reproducible que ejecuta `procesar`
  para cada export por separado, usando sus rutas originales solo para lectura. No genera
  archivos ni imprime identidades de cheques o clientes; muestra cantidades e importes agregados.
- Esta consigna. Sin dependencias nuevas ni cambios al catálogo.

### Evidencia real (fecha común de cálculo: 22/09/2026)

Se leyeron exactamente las dos rutas pedidas. **La tabla del Contexto no coincide con los
archivos disponibles**: el bueno no tiene 1.694 En Cartera; tiene 42. En el malo no hay estados
vacíos entre sus 75.611 filas. Los estados medidos fueron:

| Estado | Bueno 21/09 | Malo 22/09 |
|---|---:|---:|
| En Cartera / C | 42 | 32 |
| Aplicado / A | 1.568 | 73.671 |
| Rechazado / R | 48 | 1.801 |
| Anulado / X | 36 | 107 |
| **Total leído** | **1.694** | **75.611** |

| Resultado del lector | Bueno | Malo |
|---|---:|---:|
| Filas descartadas por estado | 1.652 | 75.579 |
| Filas que entran a la lista | 42 | 32 |
| Importe de esas filas | $98.679.158,47 | $70.786.624,80 |
| De ellas, marcadas REVISAR (fecha pasada) | 0 | 2 |
| Habilitadas para el cash (sin REVISAR) | 42 | 30 |
| Importe habilitado para el cash | $98.679.158,47 | $69.076.889,69 |

La comparación de todas las columnas generadas, salvo ID y observaciones de origen, encuentra
28 filas habilitadas idénticas, 14 solo en el bueno y 2 solo en el malo. **No se cumple la
expectativa de resultados prácticamente iguales**: hay $29.602.268,78 menos habilitados en el
malo. No se inventó ni se recuperó ninguna fila histórica para forzar igualdad. Hay que revisar
las vistas/fotos de Tango para explicar la diferencia; estos archivos solos no prueban su causa.
Sí queda demostrado que **ninguno de los 75.579 cheques fuera de cartera entra en la salida**.
La protección por estado no certifica que Tango haya traído toda la cartera real.

Además, se leyó `Cheques/A Cheques propios 2026-09-22.xlsx` para comprobar estados:
39 filas, todas `Al Cobro`, sin columna de código de estado. Por eso propios sigue exigiendo
ese texto, sin suponer que el código C de terceros tenga el mismo significado.

El filtro por texto En Cartera y Al Cobro **ya existía al arrancar esta rama**. No se atribuye
a esta tarea haber agregado esa defensa desde cero: se reforzó la lectura del código, la
validación de columnas y los avisos; la retención por crecimiento sí es nueva.

### Comprobaciones

Python usado: `/Users/thomasmanzo/Documents/Finnauto/.venv/bin/python` (entorno existente).

- `python -m unittest discover -s lector/pruebas`: 7 pruebas OK (incluye la prueba anterior).
- `python -m py_compile lector/tango.py clientes/navar/herramientas/vigilante.py lector/pruebas/test_cheques_en_cartera.py lector/pruebas/comparar_cartera_real.py`: OK.
- `git diff --check`: OK.
- Comparación real: `python -m lector.pruebas.comparar_cartera_real "<ruta buena indicada arriba>" "<ruta mala indicada arriba>" --hoy 2026-09-22`.
- Nombres propios de personas del cliente: control sobre archivos nuevos y líneas agregadas,
  más el manual completo; sin coincidencias. No se suben exports ni datos individuales a git.
- No se instaló el cambio ni se ejecutó el vigilante contra producción. Queda para revisión
  la discrepancia entre exports antes de dar por validada la integridad de la cartera.


### Commit pendiente por permiso del entorno

Se intentó `git add` de los seis archivos y commit en `tarea/cheques-en-cartera`, pero el
sandbox rechazó crear `/Users/thomasmanzo/Documents/Finnauto/.git/worktrees/Finnauto-tarea09/index.lock`
(`Operation not permitted`). No quedó commit ni staging. Según el circuito de `tareas/LEEME.md`,
el revisor debe commitear estos cambios desde un entorno con acceso al índice del worktree.

## Revisión
