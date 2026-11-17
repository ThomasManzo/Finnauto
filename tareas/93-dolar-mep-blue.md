# Tarea 93 — Dólar oficial, MEP y blue por día a dolar_tipos.csv
Estado: lista para revisión
Rama: tarea/93-dolar-mep-blue

## Objetivo
Sumar a la bajada diaria (`ingestas/mercado_datos.py`) una fuente nueva, `dolar_tipos`, que escribe `dolar_tipos.csv` con una
fila por fecha y tipo de cambio: oficial, MEP y blue. `dolar.csv` (solo oficial) **no cambia**: lo usan planillas.

## Contexto
- Leer `AGENTS.md`, `CLAUDE.md`, `tareas/LEEME.md`, `tareas/76-dolar-oficial-diario.md` y `ingestas/dolar.py`: misma fuente,
  mismo estilo y mismas reglas. Reusar lo que se pueda de `dolar.py` (consulta con 3 intentos, `_monto`, validación).
- **El repo es público.** Nada de datos reales; números inventados.
- Fuente, gratis y sin clave: `GET https://api.argentinadatos.com/v1/cotizaciones/dolares/` devuelve, en un solo pedido, una
  lista de `{"casa": "...", "compra": n, "venta": n, "fecha": "AAAA-MM-DD"}` de todas las casas. Interesan `oficial`,
  `bolsa` (es el MEP) y `blue`. Las demás casas se ignoran.

## Archivos permitidos
- `ingestas/dolar.py`
- `ingestas/mercado_datos.py`
- `tests/test_dolar.py`, `tests/test_mercado_datos.py`, `tests/test_tiendanube.py`, `tests/test_galicia_datos.py` (estos tres
  últimos, solo lo mínimo para que sigan sin red con la fuente nueva)
- esta consigna (sección "Qué hice" y `Estado:`)

## Resultado esperado
1. En `ingestas/dolar.py`: `COLUMNAS_TIPOS = ['fecha', 'tipo', 'compra', 'venta', 'fuente']`, `TIPOS = {'oficial': 'oficial',
   'bolsa': 'mep', 'blue': 'blue'}` y `bajar_tipos(salida, desde, hasta, http=_http)`, que devuelve el historial completo para
   `salida/dolar_tipos.csv` sin escribir archivos, igual que `bajar`.
2. Mismas reglas que `bajar`:
   - solo fechas entre `desde` y `hasta`, y `hasta` es ayer en Buenos Aires;
   - una fila ya guardada (misma `fecha` y `tipo`) nunca se pisa;
   - `fuente` = `argentinadatos`;
   - importes con dos decimales;
   - una respuesta con datos inválidos en las casas que interesan da `ErrorDatos` y no devuelve nada.
   Una casa que no interesa con datos raros no es error.
3. Orden del CSV: por `fecha` y, dentro de cada fecha, `oficial`, `mep`, `blue`.
4. `mercado_datos.py`: fuente `dolar_tipos` después de `dolar`, archivo `dolar_tipos.csv`, también en `--solo`. Va en
   `control.json` y en el estado de `--solo-pendientes`; si falla, el CSV anterior queda igual. Igual que `dolar`, no pide
   perfil ni token. El resumen toma `desde` y `hasta` de la columna `fecha`. Sumar un renglón en criollo al docstring.

## Comprobaciones
Pruebas sin red, con `http` falso y `time.sleep` reemplazado:
- Una respuesta inventada con las tres casas y otra que no interesa da solo oficial, mep y blue, en ese orden, con dos decimales.
- No pisa filas guardadas y no duplica en una segunda corrida.
- Corta en `hasta` y arranca en `desde`.
- Un importe inválido en `blue` da `ErrorDatos`. Uno inválido en una casa ignorada no.
- Corrida de `mercado_datos` con la fuente: aparece en `control.json` y, si falla, el CSV anterior queda.
- `dolar.csv` y `bajar` no cambian de comportamiento: las pruebas que ya existen pasan sin tocarlas.
Comando: `PYTHONPATH=. /Users/thomasmanzo/Documents/Finnauto/.venv/bin/python3 -m unittest discover -s tests` (no hay pytest).
No se puede probar acá: la corrida real, la hace Claude después de revisar.

## Qué hice
- Agregué `COLUMNAS_TIPOS`, `TIPOS` y `bajar_tipos` en `ingestas/dolar.py`. Reutiliza la consulta
  con hasta tres intentos y la validación de importes con Decimal. Consulta todas las casas en un
  pedido, toma oficial/bolsa/blue y devuelve oficial/mep/blue ordenados por fecha y tipo.
- Conserva cada fila guardada por fecha y tipo, incluso fuera del período solicitado; suma solo
  las nuevas entre desde y hasta. Valida las casas elegidas antes de devolver el historial,
  ignora los datos de otras casas y no escribe archivos por su cuenta.
- Integré `dolar_tipos` después de `dolar` en `ingestas/mercado_datos.py`, también en `--solo`,
  `control.json` y el estado diario de `--solo-pendientes`. Usa ayer en Buenos Aires como límite,
  sin pedir perfil ni token. Una falla conserva el CSV anterior.
- Amplié `tests/test_dolar.py` y `tests/test_mercado_datos.py` con respuestas inventadas y sin red:
  orden, decimales, límites de fechas, historial sin pisar ni duplicar, datos inválidos, reintentos,
  resumen, estado y recuperación después de una falla. Las pruebas existentes de dólar quedaron intactas.
- Ajusté lo mínimo en `tests/test_tiendanube.py`: simular la fuente nueva y contarla en la corrida
  completa. No hizo falta modificar `tests/test_galicia_datos.py`.
- Verificación: `PYTHONPATH=. /Users/thomasmanzo/Documents/Finnauto/.venv/bin/python3 -m unittest discover -s tests`
  terminó OK: 90 pruebas. `git diff --check` también pasó.
- No usé datos reales ni carpetas privadas, no consulté la API real y no instalé dependencias.
  La corrida real queda para Claude después de revisar, como pide la consigna. Sin dudas pendientes.
- No hice commits por indicación de Thomas. Todos los cambios quedan en este worktree y rama
  `tarea/93-dolar-mep-blue`. La consigna ya estaba sin seguimiento en git al comenzar y así queda.
