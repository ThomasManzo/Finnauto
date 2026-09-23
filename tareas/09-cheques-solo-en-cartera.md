# Tarea 09 — Que un export de cheques mal filtrado no pueda ensuciar el cash
Estado: pendiente
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

## Revisión
