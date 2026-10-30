# Tarea 71 — Bajadas diarias de Mercado Libre (ventas) y Mercado Pago (liquidaciones) a CSV
Estado: pendiente
Rama: tarea/71-bajadas-meli

## Objetivo
Un programa que, con el permiso que ya dejó la tarea 70, baje solo las ventas de Mercado Libre y las liquidaciones
de Mercado Pago de un cliente, y las deje en una carpeta como **CSV con columnas fijas** más un `control.json`.
Un tablero (otra parte del sistema, que no se toca acá) lee esos archivos todos los días.
La idea central: **cada venta de Mercado Libre tiene que dar la misma plata que el reporte "Ventas" que el vendedor
baja a mano desde Mercado Libre**, columna por columna. Las reglas de abajo salen de comparar ese reporte con la API
para un mes real (las verificó Claude el 30/10/2026: el total de la venta coincide al peso en casi todas; lo que
no coincide son devoluciones que el reporte todavía mostraba "en revisión").

## Contexto
- Leer `AGENTS.md`, `CLAUDE.md`, `tareas/LEEME.md` y `ingestas/meli_oauth.py` (tarea 70). Seguir su estilo: solo
  biblioteca estándar (`urllib`), comentarios en criollo, sin dependencias nuevas. (`openpyxl` ya está en el `.venv`
  y se puede usar solo para leer un reporte en Excel, ver Mercado Pago.)
- **El repo es público.** Nada de datos reales: cliente `ejemplo`, números inventados (como los de abajo).
- **Permisos:** `meli_oauth.access_token(cliente, "mercadolibre")` y `meli_oauth.access_token(cliente, "mercadopago")`
  devuelven un token vigente (lo renuevan solos). Se manda como `Authorization: Bearer <token>`. Si tiran
  `meli_oauth.ErrorAutorizacion`, la fuente queda en error con el motivo en criollo ("hay que volver a autorizar…").
  Pedir el token **una vez por corrida y por fuente** (y otra vez solo si una llamada da 401).
- **El usuario** (vendedor) es `user_id` en `meli_oauth.estado(cliente, "mercadolibre")`.
- **Límite de velocidad:** Mercado Libre contesta `429` seguido. Reintentar con espera creciente (respetar
  `Retry-After` si viene; si no, 2, 4, 8, 16, 32 s) y como mucho 4 pedidos en paralelo. Un mes son ~500 ventas y
  ~1.500 pedidos: la primera corrida (un año) puede tardar horas; por eso hay caché (ver abajo).
- **Horas:** la API devuelve fechas con distintos husos (`-04:00`, `Z`). En los CSV todo va en hora de Buenos Aires
  (`meli_oauth.HORA_BA`, UTC-3), formato `AAAA-MM-DD HH:MM`.

### De dónde sale cada cosa (Mercado Libre)
1. **Órdenes:** `GET https://api.mercadolibre.com/orders/search?seller=<user_id>&order.date_created.from=<desde>&order.date_created.to=<hasta>&sort=date_asc&limit=50&offset=<n>`
   (fechas como `2026-09-01T00:00:00.000-03:00`). Pedir **de a un mes** y paginar con `offset` hasta `paging.total`.
   También existe el filtro `order.date_last_updated.from/.to` (para traer solo lo que cambió).
   Campos que se usan de cada orden: `id`, `pack_id` (puede ser `null`), `status` (`paid`, `cancelled`, …),
   `date_closed`, `date_last_updated`, `order_items[]` (`item.id`, `item.title`, `item.seller_sku`,
   `item.variation_attributes[]` con `name` y `value_name`, `quantity`, `unit_price`), `payments[].id`, `shipping.id`.
2. **Pago con el detalle de cargos:** `GET https://api.mercadopago.com/v1/payments/<id>` **con el token de Mercado
   Pago**. Campos: `status`, `installments`, `transaction_amount`, `transaction_amount_refunded`,
   `transaction_details.net_received_amount` y `charges_details[]`, cada uno con `type` (`fee`, `tax`, `shipping`,
   `coupon`, …), `name`, `accounts.from` / `accounts.to` y `amounts.original` / `amounts.refunded`.
   **Solo cuentan los cargos con `accounts.from == "collector"`** (los que paga el vendedor) y **solo los pagos con
   `status` en `approved`, `refunded`, `charged_back`, `in_mediation`**: una orden puede traer pagos rechazados que
   igual listan cargos, y esos no van.
3. **Envío:** `GET https://api.mercadolibre.com/shipments/<id>` (formato clásico, **sin** el encabezado
   `x-format-new`). Campos: `logistic_type`, `status`, `substatus`, `receiver_address.state.name`,
   `status_history.date_delivered`.
4. **Costos del envío:** `GET https://api.mercadolibre.com/shipments/<id>/costs`. Campos: `gross_amount`,
   `receiver.cost` (lo que pagó el comprador), `senders[].cost` y `senders[].save`.
   Una orden sin `shipping.id` (entrega a acordar) no tiene envío ni costos.

### Cómo se arma cada venta (las reglas)
**Agrupar:** la "venta" del reporte es el `pack_id` si la orden lo tiene, y si no, el `id` de la orden.
- Grupo de **una** orden → **una fila**: `id_venta` = pack_id (o id de la orden), `id_pack` vacío.
- Grupo de **varias** órdenes (paquete) → **una fila cabecera** con la plata de todo el paquete (`id_venta` =
  `id_pack` = pack_id, `estado` = `Paquete de N productos`, sin sku/publicación/título/variante/unidades/precio) y
  **una fila hija por orden** (`id_venta` = id de la orden, `id_pack` = pack_id, con sku, publicación, título,
  variante, unidades y precio, y **todas las columnas de importe vacías**). Las hijas copian `forma_entrega`,
  `provincia_comprador` y `fecha_entregado` de la cabecera.

**Importes** (de la cabecera o de la fila única; sumando todas las órdenes y pagos válidos del grupo; 2 decimales).
Abreviaturas: `cargos(tipos)` = suma de `amounts.original` de los cargos válidos de esos tipos; `d` = bonificación
de envío Flex (abajo); `imp_d = round(d × 0,006, 2)`.

| Columna | Regla |
|---|---|
| `ingresos_productos` | Σ `unit_price × quantity` de los ítems |
| `cargo_venta_impuestos` | `−cargos(fee, tax) − imp_d` |
| `ingresos_envio` | `receiver.cost` |
| `costos_envio` | `−cargos(shipping)`; si no hay cargos de envío: `0` si es Flex (`logistic_type == "self_service"`), si no `−receiver.cost` |
| `descuentos_bonificaciones` | `d`: solo Flex. Si Σ `senders[].cost` > 0 → Σ `senders[].save`; si no, si `receiver.cost == 0` → `gross_amount`; si no → 0. No Flex → 0 |
| `anulaciones_reembolsos` | Si algún pago válido tiene `transaction_amount_refunded > 0`: `−Σ net_received_amount`, y si además el envío está `cancelled` (nunca salió), también `−(d − imp_d)`. Si no, 0 |
| `otros_cargos` | `−cargos(coupon)` |
| `total` | la suma de las 7 columnas de arriba |

Por qué: la bonificación Flex la paga Mercado Libre aparte y le retienen el 0,6 % de impuesto a los débitos y
créditos (por eso `imp_d`). Dejar `0.006` en una constante con nombre, porque se puede ajustar en la prueba.
**Control propio:** `control_total = Σ net_received_amount + d − imp_d + anulaciones_reembolsos`. Si
`|total − control_total| > 1`, la venta cuenta como **descuadrada** (no se corrige nada, solo se cuenta; ver
`control.json`).

**Las demás columnas** (fila única o hija; la cabecera solo lleva las que tienen sentido para el paquete):
- `fecha_venta`: `date_closed` (no `date_created`) en hora de Buenos Aires.
- `estado` (palabras fijas, no las del reporte): `Cancelada` si el envío está `cancelled` o la orden está
  `cancelled` sin entregar; `Devuelta` si la orden está `cancelled` y el envío llegó a `delivered`, o si el envío
  está `not_delivered` con `substatus` `returned`; `En reclamo` si algún pago está `in_mediation` o
  `charged_back`; `Entregada` si el envío está `delivered`; `En camino` si está `shipped`; `Por despachar` en el
  resto de los casos con pago aprobado; `Sin pago` si no hay pago válido.
- `sku` = `seller_sku` tal cual (sin normalizar); `id_publicacion` = `item.id`; `titulo` = `item.title`;
  `variante` = cada atributo como `nombre : valor`, unidos con ` | ` (ej. `Color : Negro`); `unidades` =
  `quantity`; `precio_unitario` = `unit_price`. Si una orden trae más de un ítem, una fila hija por ítem.
- `tiene_cuotas`: `sí` si algún cargo válido se llama `financing_add_on_fee`, si no `no`.
- `venta_por_publicidad`: **vacío** por ahora (sale de otra API; queda para otra tarea).
- `forma_entrega`: `self_service` → `flex`; `fulfillment` → `full`; `xd_drop_off`, `drop_off`, `cross_docking`
  → `correo`; sin envío → `acordar`; cualquier otro → `otra`.
- `provincia_comprador` = `receiver_address.state.name`; `fecha_entregado` = `status_history.date_delivered`
  (hora de Buenos Aires; vacío si no se entregó).
- `id_pago_mp`: los `id` de los pagos válidos del grupo, unidos con `|`.

**Filas que van:** las ventas con `fecha_venta` ≥ `--desde` (por defecto `2025-10-01`). Orden: por `fecha_venta`
y después por `id_venta`, con cada cabecera seguida de sus hijas.

### Ejemplos inventados (usar estos en las pruebas)
**A. Correo, una orden con `pack_id` propio.** Orden `id 2000000000000001`, `pack_id 2000000000000101`,
`date_closed "2026-09-10T11:06:30.000-04:00"`, un ítem (`MLA1000000001`, "Lámpara de escritorio", sku `AB 100`,
variante `Color`/`Negro`) × 2 a 10.000. Pago `90000000001` aprobado, 1 cuota, `transaction_amount` 20000,
`net_received_amount` 11480, cargos del vendedor: `fee meli_percentage_fee` 2600, `fee flat_fee` 400,
`tax tax_withholding_collector-debitos_creditos` 120, `tax tax_withholding_sirtac-caba` 100,
`shipping shp_cross_docking` 5000, `coupon coupon_fee` 300; y uno de `ml` a `payer` (`coupon coupon_rebate` 300)
que **no cuenta**. Envío `xd_drop_off`, `delivered`, provincia `Córdoba`, entregado
`"2026-09-12T15:20:00.000-04:00"`; costos: `receiver.cost` 0, `senders` `[{cost 5000, save 0}]`, `gross_amount` 5000.
→ `id_venta 2000000000000101`, `id_pack` vacío, `fecha_venta 2026-09-10 12:06`, `estado Entregada`, productos
`20000.00`, cargo `-3220.00`, ingresos envío `0.00`, costos envío `-5000.00`, descuentos `0.00`, anulaciones
`0.00`, otros `-300.00`, **total `11480.00`** (= neto: sin descuadre), `tiene_cuotas no`, `correo`, `Córdoba`,
`fecha_entregado 2026-09-12 16:20`, `id_pago_mp 90000000001`, `variante Color : Negro`.

**B. Flex, Mercado Libre bonifica todo el envío.** Orden sin `pack_id`, 1 × 30.000, pago con `fee
meli_percentage_fee` 4000 y `tax …debitos_creditos` 180 (neto 25820). Envío `self_service`; costos:
`receiver.cost` 0, `senders [{cost 0, save 0}]`, `gross_amount` 5000.
→ `d = 5000`, `imp_d = 30.00`; cargo `-4210.00`, costos envío `0.00`, descuentos `5000.00`, total `30790.00`;
control `25820 + 5000 − 30 = 30790` ✓. `forma_entrega flex`.

**C. Flex, el vendedor paga parte.** Como B pero `senders [{cost 4500, save 500}]`, `gross_amount` 10000 →
`d = 500`, `imp_d = 3.00`.

**D. Correo, el comprador paga el envío y no hay cargo de envío.** `receiver.cost` 3000, sin cargos `shipping` →
ingresos envío `3000.00`, costos envío `-3000.00`.

**E. Cancelada antes de salir.** Como B, con el pago `refunded` (`transaction_amount_refunded` 30000) y el envío
`cancelled` → anulaciones `−25820 − (5000 − 30) = -30790.00`, total `0.00`, `estado Cancelada`.

**F. Devuelta después de entregar.** Como B, pago `refunded`, envío `delivered`, orden `cancelled` → anulaciones
`-25820.00` (la bonificación queda), total `4970.00`, `estado Devuelta`.

**G. Paquete de dos órdenes** (mismo `pack_id`, mismo envío, un pago cada una) → una cabecera
`Paquete de 2 productos` con la suma de todo y dos hijas con importes vacíos.

**H. Pago rechazado.** Una orden con un pago `rejected` (que lista cargos) y otro `approved`: solo cuenta el aprobado.

### Mercado Pago: reporte de liquidaciones
Es el mismo reporte que el vendedor ya usa ("liquidaciones" / *settlement*). Verificado en la documentación:
- Configuración: `GET https://api.mercadopago.com/v1/account/settlement_report/config` (columnas, `separator`,
  `display_timezone`, `frequency.format`). **Prohibido cambiarla** (nada de `POST`/`PUT` a `/config` ni a
  `/schedule`): el vendedor la usa para sus propios reportes.
- Lista: `GET https://api.mercadopago.com/v1/account/settlement_report/list` → lista con `id`, `file_name`,
  `begin_date`, `end_date` (UTC, ej. `2026-09-01T03:00:00Z` / `2026-10-01T02:59:59Z` = septiembre en Buenos
  Aires), `created_from` (`manual`/`schedule`), `status` (`processed` cuando está listo), `format` (`CSV`/`XLSX`).
- Pedir uno: `POST https://api.mercadopago.com/v1/account/settlement_report` con JSON
  `{"begin_date": "...Z", "end_date": "...Z"}` → `202` (se genera aparte, aparece en la lista al rato). `203` =
  no se pudo, pedirlo de nuevo más tarde.
- Bajar: `GET https://api.mercadopago.com/v1/account/settlement_report/<file_name>` → el archivo.

Qué hacer en cada corrida:
1. Partir el período en **meses de Buenos Aires** desde `--desde` hasta ayer.
2. **Mes cerrado:** si en la lista hay uno `processed` con exactamente ese `begin_date`/`end_date`, usarlo; si no,
   pedirlo con `POST`. Una vez bajado, guardarlo en la caché y no volver a bajarlo.
3. **Mes en curso:** un reporte desde el 1° hasta el final de ayer. Si ya existe uno con esas fechas, usarlo; si no,
   pedirlo (así se pide como mucho uno por día).
4. Esperar los pedidos mirando la lista cada 30 s, hasta 10 minutos. Si alguno no llegó, seguir con lo que hay y
   poner en el `motivo` qué mes falta.
5. Leer el archivo con el `separator` de la configuración (puede venir `;`) y por **nombre de columna**
   (`SOURCE_ID`, `TRANSACTION_TYPE`, …). Si viene en Excel (`.xlsx`), leerlo con `openpyxl`. Si falta una columna,
   dejarla vacía; si faltan `SOURCE_ID` o `REAL_AMOUNT`, la fuente queda en error con el motivo.
6. Unir todos los meses sin duplicar filas (misma fila completa = duplicada).

### Archivos de salida (en la carpeta `--salida`)
Reglas: CSV UTF-8, separado por coma, encabezado tal cual; montos con punto decimal, sin miles, 2 decimales; lo
que entra positivo, lo que se descuenta negativo; identificadores como texto. **Cada corrida reescribe el archivo
entero** escribiendo primero a un temporal en la misma carpeta y después `os.replace`. Si una fuente falla, **su**
CSV anterior queda como estaba.

`ml_ventas.csv`, columnas en este orden:
`id_venta,id_pack,fecha_venta,estado,sku,id_publicacion,titulo,variante,unidades,precio_unitario,ingresos_productos,cargo_venta_impuestos,ingresos_envio,costos_envio,descuentos_bonificaciones,anulaciones_reembolsos,otros_cargos,total,tiene_cuotas,venta_por_publicidad,forma_entrega,provincia_comprador,fecha_entregado,id_pago_mp`

`mp_movimientos.csv`, columnas en este orden (de la columna del reporte):
`id_origen` (SOURCE_ID), `tipo_transaccion` (TRANSACTION_TYPE), `medio_pago` (PAYMENT_METHOD_TYPE), `monto_bruto`
(TRANSACTION_AMOUNT), `comision` (FEE_AMOUNT), `impuestos` (TAXES_AMOUNT), `monto_neto` (REAL_AMOUNT),
`fecha_transaccion` (TRANSACTION_DATE), `fecha_liquidacion` (SETTLEMENT_DATE), `fecha_liberacion`
(MONEY_RELEASE_DATE), `unidad_negocio` (BUSINESS_UNIT y SUB_UNIT unidos con ` / `, sin vacíos), `id_venta_ml`
(el `id_venta` de `ml_ventas` cuyo `id_pago_mp` contiene ese SOURCE_ID; vacío si no hay).
Fechas pasadas a Buenos Aires; montos tal cual vienen (con su signo).

`control.json`: si ya existe, **conservar las otras fuentes** que tenga (las escriben otros programas) y
reemplazar solo `mercadolibre` y `mercadopago`:
```
{"corrida": "2026-11-05 07:10",
 "fuentes": {"mercadolibre": {"ok": true, "filas": 512, "desde": "2025-10-01", "hasta": "2026-11-04",
                              "motivo": "", "descuadradas": 3},
             "mercadopago": {"ok": true, "filas": 690, "desde": "2025-10-01", "hasta": "2026-11-04", "motivo": ""}}}
```
`filas` = filas escritas; `desde`/`hasta` = fecha mínima y máxima de los datos; `motivo` en criollo si `ok` es
false; `descuadradas` = ventas con `|total − control_total| > 1`.

### Caché (para no bajar todo cada día)
En `clientes/<cliente>/.run/mercadolibre/cache/` (ya está en `.gitignore`): un JSON por orden, pago, envío y costos.
En cada corrida: buscar las órdenes de **los últimos 2 meses** completos más las que cambiaron desde la última
corrida buena (`order.date_last_updated.from` = última corrida − 2 días); para esas, volver a bajar pago, envío y
costos. Lo demás sale de la caché. La primera vez (sin caché) se baja todo desde `--desde`. Los reportes de
Mercado Pago bajados van en `clientes/<cliente>/.run/mercadopago/liquidaciones/`. Guardar la fecha de la última
corrida buena en un archivo de esa carpeta.

## Archivos permitidos
- `ingestas/meli_ventas.py` (nuevo): Mercado Libre → filas de `ml_ventas`.
- `ingestas/mp_liquidaciones.py` (nuevo): Mercado Pago → filas de `mp_movimientos`.
- `ingestas/mercado_datos.py` (nuevo): el que se corre; llama a los dos, escribe los CSV y `control.json`.
- `tests/test_meli_ventas.py`, `tests/test_mp_liquidaciones.py` (nuevos).
- Esta consigna (sección "Qué hice").

## Resultado esperado
- `python -m ingestas.mercado_datos --cliente <c> --salida <carpeta> [--desde 2025-10-01] [--solo mercadolibre|mercadopago]`
  hace todo lo de arriba. Imprime un resumen corto por fuente (filas, descuadradas, motivo). Sale con código 1 si
  alguna fuente falló (igual escribe `control.json`).
- En `meli_ventas.py`, las reglas de importes en **una función pura** (recibe las órdenes del grupo, sus pagos,
  envío y costos ya bajados, y devuelve las filas), separada de lo que baja de internet, para poder probarla y
  ajustarla sin red.
- Lo mismo en `mp_liquidaciones.py`: una función pura que recibe el texto del reporte y la configuración y
  devuelve las filas.
- Nunca imprimir ni guardar tokens. Mensajes y comentarios en criollo.
- Las llamadas HTTP pasan por una sola función por módulo (fácil de reemplazar en las pruebas).

## Comprobaciones
- `python tests/test_meli_ventas.py` y `python tests/test_mp_liquidaciones.py` (sin pytest, como
  `tests/test_meli_oauth.py`), con HTTP falso y llavero falso, cubriendo:
  - los ejemplos A a H dan exactamente los valores de arriba;
  - un 429 se reintenta y después sale bien; un `ErrorAutorizacion` deja la fuente en error con motivo y no pisa el
    CSV anterior;
  - Mercado Pago: usa un reporte existente del mes cerrado; pide (`POST`) el que falta y lo espera; lee un reporte
    con `;`; no duplica filas; completa `id_venta_ml`; **nunca** llama a `/config` con otro método que `GET`;
  - `control.json` conserva una fuente ajena que ya estaba;
  - la escritura es por temporal + `os.replace`.
- `python tests/test_meli_oauth.py` sigue dando OK.
- Lo que no se puede probar acá (datos reales): lo corre Claude en la Mac del cliente y compara contra los reportes
  que el vendedor bajó a mano.

## Qué hice

## Revisión
