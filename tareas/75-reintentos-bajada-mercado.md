# Tarea 75 — Bajada de mercados: reintentar cortes de lectura y repetir en el día solo lo que falló
Estado: pendiente
Rama: tarea/75-reintentos-bajada

## Objetivo
Que la bajada diaria de `ingestas/mercado_datos.py` se recupere sola cuando una fuente falla por un problema pasajero:
1. **Cortes a mitad de una respuesta** (la conexión se cae mientras se lee, o llega una respuesta cortada): reintentar
   igual que hoy se reintenta un corte de conexión, en vez de dar la fuente por perdida.
2. **Repetir en el día solo lo que falló:** con una opción nueva, la corrida baja únicamente las fuentes que todavía no
   tienen una bajada buena HOY. Así la misma tarea programada puede correr varias veces al día: la primera baja todo y
   las siguientes solo reintentan lo que quedó en rojo (o no hacen nada si todo dio bien).
3. **Tiendanube sin autorizar no es un error:** si están cargadas las credenciales de la aplicación pero todavía no se
   autorizó ninguna tienda, la fuente se saltea (no aparece en `control.json`), igual que cuando no hay aplicación.

## Contexto
- Leer `AGENTS.md`, `CLAUDE.md`, `tareas/LEEME.md` y las consignas 71, 72 y 73. Mismo estilo: biblioteca estándar,
  comentarios en criollo, escritura por temporal + `os.replace` (`ml.guardar_json`).
- **El repo es público.** Nada de datos reales: cliente `ejemplo`, números inventados.
- Lo que pasó (cliente de ejemplo): la corrida programada de las 06:30 arrancó con la computadora a batería entrando y
  saliendo de reposo. Mercado Libre y la publicidad quedaron en rojo con "no se pudo leer la respuesta de
  mercadolibre"; Mercado Pago dio bien. A la tarde, a mano, todo andaba.
- Hoy, en `ingestas/meli_ventas.py`, `Sesion.pedir` reintenta 429/5xx y `URLError`/`TimeoutError` (esperas 2, 4, 8,
  16, 32 s), pero `except (OSError, ValueError)` corta en el acto con "no se pudo leer la respuesta". Ahí caen, por
  ejemplo, `ConnectionResetError` durante `respuesta.read()` y un JSON cortado. `http.client.IncompleteRead` (y otras
  `http.client.HTTPException`) ni siquiera están contempladas: terminan en el mensaje genérico de `mercado_datos.py`.
  `Sesion` la usan Mercado Libre, Mercado Pago y la publicidad.
- En `ingestas/tiendanube.py`, `Sesion.pedir` ya reintenta `OSError`, pero `ValueError` (respuesta cortada) e
  `IncompleteRead` cortan sin reintentar.
- Cuando una fuente falla, su CSV anterior queda como estaba (no se pisa). Eso se mantiene.
- `control.json` lo leen las planillas: **su formato no cambia** (mismas claves en `fuentes` y `corrida`). Lo que haga
  falta recordar entre corridas va en `.run/`, fuera de la carpeta de salida.
- `mercado_datos.py` hoy saltea Tiendanube solo si `tn.tiene_aplicacion(cliente)` es falso. Con la aplicación cargada
  y sin token, `tn.Sesion` tira "falta autorizar Tiendanube" y la fuente queda en rojo. `tn.estado(cliente)` devuelve
  `hay_token`.

## Archivos permitidos
- `ingestas/meli_ventas.py` (solo `Sesion.pedir` y lo mínimo que necesite)
- `ingestas/tiendanube.py` (solo `Sesion.pedir` y, si hace falta, una función chica tipo `tiene_permiso`)
- `ingestas/mercado_datos.py`
- `tests/test_meli_ventas.py`, `tests/test_tiendanube.py`, `tests/test_mercado_datos.py` (nuevo si no existe)
- esta consigna (sección "Qué hice" y `Estado:`)

## Resultado esperado
1. **Reintentos de lectura** (`meli_ventas.Sesion.pedir` y `tiendanube.Sesion.pedir`): un corte durante la lectura
   (`OSError`, incluido `ConnectionResetError`; `http.client.HTTPException`, incluido `IncompleteRead`; y una respuesta
   que no se puede decodificar como JSON) se reintenta con las mismas esperas y la misma cantidad de intentos que un
   corte de conexión. Si se agotan los intentos, el mensaje sigue siendo "no se pudo leer la respuesta de <fuente>;
   revisar la conexión y volver a intentar". Un pedido con cuerpo (POST) que se cortó mientras se leía la respuesta
   **no se repite** (puede haber quedado hecho del otro lado): corta con el mensaje de siempre. Los `HTTPError` siguen
   como hoy.
2. **Opción `--solo-pendientes`** en `mercado_datos.py`:
   - Guarda, por cliente, la fecha (hora de Buenos Aires, como `ahora`) de la última bajada buena de cada fuente en
     `clientes/<c>/.run/mercado_datos_estado.json` (ej. `{"mercadolibre": "2026-01-15", ...}`), en todas las corridas,
     con o sin la opción. Se actualiza solo cuando la fuente terminó bien y su CSV quedó escrito.
   - Con la opción, se saltean las fuentes cuya última bajada buena es de hoy: **su resumen anterior en `control.json`
     queda tal cual** (no se borra ni se pone en cero). Las demás se bajan como siempre. `--solo` y
     `--solo-pendientes` juntos: se aplican los dos filtros.
   - Si con la opción no queda nada por bajar, la corrida termina enseguida, sin tocar `control.json`, sin pedir
     tokens ni conectarse, con salida 0 y una línea "Nada pendiente: todo se bajó bien hoy."
   - `corrida` en `control.json` se actualiza solo si se bajó al menos una fuente.
   - La salida (código de retorno) refleja solo las fuentes que se intentaron en esta corrida.
   - Mercado Pago necesita `ml_ventas.csv` para vincular pagos: si en esta corrida no se bajó Mercado Libre, usa el
     `ml_ventas.csv` que está en la carpeta (como ya hace hoy con `ventas is None`).
3. **Tiendanube sin autorizar se saltea:** si hay aplicación pero no hay permiso guardado, la fuente no se baja y se
   saca de `control.json`, igual que cuando no hay aplicación. Si el permiso existe pero no sirve (401, desinstalada),
   sigue en rojo como hoy.
4. Docstring de `mercado_datos.py` con un renglón que explique la opción nueva, en criollo.

## Comprobaciones
- `python -m pytest tests/test_meli_ventas.py tests/test_tiendanube.py tests/test_mercado_datos.py tests/test_meli_publicidad.py tests/test_mp_liquidaciones.py`
  da todo OK (las pruebas que ya existen no se cambian salvo que la consigna lo pida).
- Pruebas nuevas (sin red; `http` falso y `time.sleep` reemplazado):
  - `ConnectionResetError` en la lectura dos veces y después OK → devuelve los datos; se reintentó.
  - `IncompleteRead` siempre → "no se pudo leer la respuesta…" después de los intentos de siempre.
  - JSON cortado una vez y después bien → OK.
  - POST con corte en la lectura → no se repite el pedido.
  - Tiendanube: `ValueError`/`IncompleteRead` en la lectura una vez y después bien → OK.
  - `--solo-pendientes`: con el estado diciendo que Mercado Libre se bajó bien hoy y Mercado Pago no, solo se baja
    Mercado Pago y el resumen de Mercado Libre en `control.json` queda igual que antes.
  - `--solo-pendientes` con todo bajado hoy → no se conecta, no toca `control.json`, sale 0.
  - Una fuente que falla no actualiza su fecha en el estado.
  - Tiendanube con aplicación y sin permiso → no aparece en `control.json` y la salida no cuenta como falla.
- No se puede probar acá: la corrida real con el cliente (la hace Claude después de revisar).

## Qué hice

## Revisión
