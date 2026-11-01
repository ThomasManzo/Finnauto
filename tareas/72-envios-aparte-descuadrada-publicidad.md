# Tarea 72 — Mercado Libre: pagos de envío aparte, columna `descuadrada`, publicidad y bajada diaria más liviana
Estado: aprobada
Rama: tarea/72-envios-publicidad

## Objetivo
Cuatro mejoras a la bajada de la tarea 71 (`ingestas/meli_ventas.py`, `ingestas/mercado_datos.py`):
1. **Pagos de envío aparte:** encontrar el pago de Mercado Pago con el que el comprador pagó el envío cuando no
   está entre los pagos de la orden, para que el control de la venta cierre y ese movimiento de Mercado Pago quede
   vinculado a su venta.
2. **Columna `descuadrada`** en `ml_ventas.csv`, para que el tablero sepa qué ventas no cierran.
3. **`ml_publicidad.csv`:** costo y resultados de los anuncios de Mercado Libre (Mercado Ads), por día y publicación.
4. **Bajada diaria más liviana:** hoy cada corrida vuelve a bajar pago, envío y costos de todas las órdenes de los
   últimos 2 meses (miles de pedidos, media hora o más). Bajar de nuevo solo lo que puede haber cambiado.

## Contexto
- Leer `AGENTS.md`, `CLAUDE.md`, `tareas/LEEME.md`, la consigna `tareas/71-bajadas-mercadolibre-mercadopago.md`
  (reglas, salidas, caché) y el código de la 71. Mismo estilo: biblioteca estándar, comentarios en criollo, sin
  dependencias nuevas, una sola función HTTP por módulo, reglas en funciones puras.
- **El repo es público.** Nada de datos reales: cliente `ejemplo`, números inventados.
- Claude verificó todo lo de abajo contra la API real el 01/11/2026 (en la Mac, sin datos al repo).

### 1. Pagos de envío aparte
Cuando el comprador paga el envío, a veces Mercado Pago lo cobra en **un pago separado** que no figura en
`orders[].payments`. Ese pago:
- se encuentra con `GET https://api.mercadopago.com/v1/payments/search?external_reference=<shipping.id>` (token de
  **Mercado Pago**; `<shipping.id>` es el número de envío de la orden);
- de los resultados, cuentan los que tienen `description == "marketplace_shipment"` y `status` en los válidos de la 71
  (`approved`, `refunded`, `charged_back`, `in_mediation`); su `order.id` es el número de envío;
- trae `transaction_amount`, `transaction_amount_refunded`, `transaction_details.net_received_amount` y unos cargos
  chicos de impuestos.

**Cuándo buscarlo:** solo para envíos con `receiver.cost > 0` (de `/shipments/<id>/costs`) donde la suma de
`transaction_amount` de los pagos válidos de la orden es menor que `ingresos_productos + receiver.cost − 1`
(o sea, el envío no se cobró adentro del pago de la orden). Guardar la respuesta en la caché como
`envio_pagos-<shipping.id>.json` (con las mismas reglas de refresco que pago/envío/costos, ver punto 4).

**Qué cambia en la venta (y qué NO):**
- **Las columnas de importe NO cambian.** Se comparó con el reporte del vendedor: con el pago aparte o sin él,
  `ingresos_productos`, `cargo_venta_impuestos`, `ingresos_envio`, `costos_envio`, etc. dan lo mismo que el reporte
  si se calculan como en la 71. Los impuestos del pago aparte **no** van a `cargo_venta_impuestos`.
- `id_pago_mp`: se agregan los `id` de esos pagos después de los de la orden (unidos con `|`). Así el movimiento
  `SETTLEMENT_SHIPPING` de `mp_movimientos.csv` queda con su `id_venta_ml` (eso ya lo hace la 71 a partir de
  `id_pago_mp`).
- **Control:** `control_total` de la 71 suma además `Σ (transaction_amount − transaction_amount_refunded)` de los pagos
  de envío aparte, **salvo** cuando `costos_envio == −ingresos_envio` (en ese caso el reporte ya cancela el envío
  del comprador contra su costo y el pago aparte se compensa por otro lado; sumarlo descuadraría). Usar el bruto
  (`transaction_amount`), no el neto: el reporte no descuenta los impuestos de ese pago.
- `armar_venta` recibe los pagos de envío aparte como un argumento nuevo (opcional, por defecto ninguno), separado de
  los pagos de la orden, para que no se mezclen en los cargos.

### 2. Columna `descuadrada`
- Nueva columna **al final** de `ml_ventas.csv`, después de `id_pago_mp`: `sí` o `no`.
- Va en la fila única o en la cabecera del paquete. En las filas hijas, **vacía**.
- La cantidad de `sí` es exactamente `descuadradas` de `control.json`.

### 3. `ml_publicidad.csv` (Mercado Ads)
Todos los pedidos con el token de **Mercado Libre** y el encabezado `Api-Version` indicado:
1. Anunciante: `GET https://api.mercadolibre.com/advertising/advertisers?product_id=PADS` (`Api-Version: 1`) →
   `advertisers[]` con `advertiser_id` y `site_id` (ej. `MLA`). Si no hay anunciante (la cuenta no usa anuncios):
   `ml_publicidad.csv` solo con encabezado y la fuente `ok`.
2. Avisos con sus totales del período: `GET https://api.mercadolibre.com/advertising/<site_id>/advertisers/<advertiser_id>/product_ads/ads/search?limit=100&offset=<n>&date_from=AAAA-MM-DD&date_to=AAAA-MM-DD&metrics=<m>`
   (`Api-Version: 2`), paginando con `paging.total`. Cada resultado trae `item_id` y `metrics` con los totales.
3. Por cada aviso con algún número distinto de cero en el período: detalle por día con
   `GET https://api.mercadolibre.com/advertising/<site_id>/product_ads/ads/<item_id>?date_from=…&date_to=…&metrics=<m>&aggregation_type=DAILY`
   (`Api-Version: 2`) → `results[]` con `date` y las métricas.
4. Control: `GET …/advertisers/<advertiser_id>/product_ads/ads/search?limit=1&date_from=…&date_to=…&metrics=<m>&aggregation_type=DAILY`
   devuelve el total de la cuenta por día. La suma de `cost` por día de todos los avisos tiene que dar igual que ese
   total (±1 peso por día); si no, la fuente queda en error con el motivo.

`<m>` = `clicks,prints,cost,direct_units_quantity,indirect_units_quantity,organic_units_quantity,direct_amount,indirect_amount,total_amount`.

**Límite importante:** Mercado Ads solo da los **últimos 90 días** (`date_from` no puede ser anterior a hoy − 90
días, y entre `date_from` y `date_to` no puede haber más de 90 días: si no, contesta 400). Por eso:
- cada corrida pide desde `max(--desde, hoy − 89 días)` hasta ayer;
- lo bajado se **acumula** en la caché (`clientes/<c>/.run/mercadolibre/publicidad/<item_id>.json`, un registro por
  día; lo nuevo pisa lo viejo del mismo día), porque lo que tenga más de 90 días ya no se puede volver a pedir;
- el CSV se arma con **todo lo acumulado** desde `--desde`.

Columnas de `ml_publicidad.csv`, en este orden: `fecha` (AAAA-MM-DD), `id_publicacion` (`item_id`), `costo` (`cost`,
positivo, 2 decimales), `clics`, `unidades_directas`, `unidades_indirectas`, `unidades_organicas`,
`ventas_por_anuncio` (`total_amount`, 2 decimales). Solo filas con algún número distinto de cero. Orden: `fecha`,
después `id_publicacion`. Escritura por temporal + `os.replace`, como los otros CSV.

En `control.json`, fuente nueva **`mercadolibre_publicidad`**, con el mismo formato que las otras (`ok`, `filas`,
`desde`, `hasta`, `motivo`). Si falla, su CSV anterior queda como estaba y las otras fuentes siguen.
`--solo` acepta también `mercadolibre_publicidad`. `venta_por_publicidad` de `ml_ventas.csv` **sigue vacía**
(Mercado Ads no dice venta por venta qué vino de un anuncio).

### 4. Bajada diaria más liviana (Mercado Libre)
Hoy (71) cada corrida vuelve a bajar pago, envío y costos de **todas** las órdenes de los últimos 2 meses. Cambiar a:
- Las búsquedas de órdenes quedan igual (últimos 2 meses completos + las cambiadas desde la última corrida − 2 días).
- Para cada orden encontrada, volver a bajar sus detalles (pago, envío, costos y, si corresponde, los pagos de envío
  aparte) **solo si** se cumple alguna:
  - no está en la caché o le falta algún detalle;
  - su `date_last_updated` es distinto del de la caché;
  - `date_closed` de los últimos **15 días**;
  - el envío guardado no está en un estado final (`delivered`, `cancelled`, o `not_delivered` con `substatus`
    `returned`), o algún pago guardado está `in_mediation` o `charged_back`.
- El resto sale de la caché. La orden se sigue guardando recién después de sus detalles (como quedó en la 71), para
  que una corrida cortada no deje órdenes sin detalle.
- Lo mismo para la primera corrida (sin caché): baja todo.

### Ejemplos inventados (usar estos en las pruebas)
**I. Correo, el vendedor paga una parte y el comprador paga su parte aparte.** Orden sin `pack_id`, 1 × 50.000.
Pago de la orden aprobado, `transaction_amount` 50000, `net_received_amount` 16000, cargos del vendedor:
`fee meli_percentage_fee` 7000, `tax …debitos_creditos` 300, `tax …sirtac` 700, `shipping shp_cross_docking` 26000.
Envío `xd_drop_off` (id `40000000001`), `delivered`; costos: `receiver.cost` 11000, `senders [{cost 15000, save 15000}]`,
`gross_amount` 60000. Pago aparte (búsqueda por `external_reference=40000000001`): id `90000000009`,
`description marketplace_shipment`, aprobado, `transaction_amount` 11000, `net_received_amount` 10930.
→ productos `50000.00`, cargo `-8000.00`, ingresos envío `11000.00`, costos envío `-26000.00`, total `27000.00`.
Sin el pago aparte: control `16000` → descuadrada. Con el pago aparte: control `16000 + 11000 = 27000` ✓,
`descuadrada no`, `id_pago_mp` = `<id del pago de la orden>|90000000009`.

**J. Flex, el comprador paga el envío aparte.** Como B de la 71 (1 × 30.000, neto 25820, `self_service`, sin cargos de
envío) pero `receiver.cost` 6000, `senders [{cost 0, save 0}]`. Pago aparte de 6000.
→ ingresos envío `6000.00`, costos envío `0.00`, descuentos `0.00` (porque `receiver.cost` no es 0), cargo `-4180.00`,
total `31820.00`; control `25820 + 6000 = 31820` ✓.

**K. El reporte ya cancela el envío.** Correo, `receiver.cost` 5000, sin cargos de envío en el pago (→ costos envío
`-5000.00`, igual a −ingresos envío). Hay un pago aparte de 5000: **no** se suma al control (la venta cierra sin él),
pero su id **sí** va a `id_pago_mp`.

**L. Publicidad.** Anunciante `{advertiser_id 123, site_id "MLA"}`. Avisos del período: `MLA1000000001` (costo 1500,
clics 30, 2 unidades directas…) y `MLA1000000002` (todo en cero: no se pide su detalle). Detalle diario del primero:
`2026-10-01` costo 1000.25, clics 20, directas 1, indirectas 0, orgánicas 1, `total_amount` 25000; `2026-10-02` costo
499.75, clics 10, directas 1, indirectas 1, orgánicas 0, `total_amount` 40000. Total de la cuenta por día: 1000.25 y
499.75 ✓ → dos filas en `ml_publicidad.csv`. Si el total de la cuenta de un día diera otro número (ej. 1200), la
fuente queda en error y el CSV anterior no se toca.

## Archivos permitidos
- `ingestas/meli_ventas.py`, `ingestas/mercado_datos.py` (cambios).
- `ingestas/meli_publicidad.py` (nuevo): Mercado Ads → filas de `ml_publicidad`.
- `tests/test_meli_ventas.py` (cambios), `tests/test_meli_publicidad.py` (nuevo). `tests/test_mp_liquidaciones.py`
  solo si hace falta por la columna nueva.
- Esta consigna (sección "Qué hice").

## Resultado esperado
- `python -m ingestas.mercado_datos --cliente <c> --salida <carpeta> [--desde 2025-10-01] [--solo mercadolibre|mercadopago|mercadolibre_publicidad]`
  escribe `ml_ventas.csv` (con `descuadrada`), `mp_movimientos.csv`, `ml_publicidad.csv` y `control.json`
  (con las tres fuentes, conservando las ajenas).
- Orden de las fuentes en la corrida: mercadolibre, mercadopago, mercadolibre_publicidad (la publicidad no depende de
  las otras; si falla, no frena nada).
- Una corrida con la caché al día baja muchos menos detalles que antes (comprobarlo en una prueba con HTTP falso:
  una orden vieja, entregada y sin cambios no genera pedidos de detalle).

## Comprobaciones
- `python tests/test_meli_ventas.py`, `python tests/test_meli_publicidad.py`, `python tests/test_mp_liquidaciones.py`
  y `python tests/test_meli_oauth.py` dan OK (sin pytest), con HTTP falso y llavero falso, cubriendo:
  - ejemplos I, J y K (importes, control, `id_pago_mp`, `descuadrada`), y que los A a H de la 71 sigan igual;
  - `descuadrada` vacía en las hijas y la cantidad de `sí` igual a `descuadradas`;
  - la búsqueda del pago aparte se hace solo cuando corresponde (no en A, donde `receiver.cost` es 0, ni cuando el
    pago de la orden ya incluye el envío);
  - ejemplo L, el error por total distinto, el 400 por fechas viejas no se dispara (la ventana respeta los 90 días),
    la acumulación (una segunda corrida con otra ventana conserva los días viejos de la caché) y la cuenta sin anunciante;
  - el refresco del punto 4 (orden vieja sin cambios: cero pedidos; orden con `date_last_updated` nuevo, reciente o
    con envío no final: vuelve a pedir).
- Lo que no se puede probar acá (datos reales): lo corre Claude en la Mac y compara.

## Qué hice

- Modifiqué `ingestas/meli_ventas.py`: búsqueda y caché de pagos de envío aparte con
  token de Mercado Pago; se filtran por descripción y estado, se agregan sus IDs y su
  bruto menos reintegros al control cuando corresponde. Los importes de la venta y
  sus cargos quedan iguales. Agregué `descuadrada` al final, vacía en las hijas.
- El refresco de detalles ahora contempla los últimos 15 días, cambios de fecha de
  actualización, detalles faltantes, envíos no finales y pagos en reclamo. Una orden
  vieja entregada sin cambios usa la caché; la orden se guarda después de sus detalles.
- Agregué `ingestas/meli_publicidad.py`: anunciante, avisos paginados, detalle diario
  solo de avisos con movimiento, encabezados de versión y control del costo por día.
  Pide desde el máximo entre `--desde` y hoy menos 89 días, hasta ayer. Acumula por
  publicación, conserva días antiguos y arma las filas ordenadas desde `--desde`.
- Modifiqué `ingestas/mercado_datos.py`: tercera fuente y opción `--solo`, CSV atómico,
  control separado y continuidad de las otras fuentes ante errores. Sin anunciante
  escribe solamente el encabezado. `venta_por_publicidad` sigue vacía.
- Amplié `tests/test_meli_ventas.py` y agregué `tests/test_meli_publicidad.py` con datos
  inventados y HTTP falso: I/J/K y regresión A–H, filtros de pagos, búsqueda y caché,
  vínculo de `SETTLEMENT_SHIPPING`, columna y conteo de descuadres, refresco y estados
  finales, ejemplo L, paginación, ventana de fechas, acumulación, cuenta sin anuncios,
  error de control que conserva el CSV anterior y orden/aislamiento de las fuentes.
- Pruebas: `python3 tests/test_meli_ventas.py` (11),
  `python3 tests/test_meli_publicidad.py` (3), `python3 tests/test_mp_liquidaciones.py`
  (6, con Excel omitido por ese intérprete) y `python3 tests/test_meli_oauth.py` (9): OK.
  Repetí liquidaciones con `/Users/thomasmanzo/Documents/Finnauto/.venv/bin/python3`:
  las 6 pasaron, incluida Excel. `git diff --check`: OK. Sin dependencias nuevas.
- No usé datos reales ni archivos privados. Los documentos privados de NAVAR no
  existen en este worktree; trabajé con el contexto de las consignas 71 y 72.
  Queda para Claude la comparación con la API y los reportes reales en la Mac.
- No pude commitear: `git add` falló al crear el `index.lock` del worktree por
  permisos del sandbox (`Operation not permitted`). Dejé todos los archivos en
  esta rama/worktree para que Claude los revise y commitee.

## Revisión

- 01/11/2026 (Claude): revisado el diff y las pruebas (11 + 3 + 7 + 9 OK). Retoques de Claude:
  (1) `meli_ventas.py`: pasada única que busca el pago de envío aparte también para las órdenes viejas que ya
  estaban en la caché (sin eso, el arreglo solo llegaba a los últimos meses);
  (2) `mp_liquidaciones.py`: si el reporte de un mes ya se está generando (por ejemplo, el mensual que programó el
  vendedor), se espera ese en vez de pedir otro igual (Mercado Pago contestaba error 500), y un pedido rechazado deja
  el mes como faltante sin frenar los demás. Prueba nueva.
- Prueba real en la Mac (fuera del repo): las ventas descuadradas bajan de 92 a 37 (36 entregas "a acordar" con
  pagos extra, a revisar con un reporte del vendedor, y 1 suelta); septiembre contra el reporte sigue igual.
  Publicidad: el costo de septiembre por publicación y día suma exactamente el total de la cuenta; historial desde
  hace 90 días. La corrida diaria con la caché al día tarda ~12 minutos (incluye la pasada única).
