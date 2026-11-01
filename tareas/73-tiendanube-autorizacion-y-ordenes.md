# Tarea 73 — Tiendanube: autorización por link y bajada diaria de órdenes a CSV
Estado: pendiente
Rama: tarea/73-tiendanube

## Objetivo
Lo mismo que las tareas 70 y 71 hicieron con Mercado Libre, ahora para **Tiendanube**:
1. **Autorización:** armar el link para el dueño de la tienda, canjear el código que le devuelve la página de vuelta y
   guardar el permiso en el llavero de la Mac.
2. **Bajada diaria:** bajar las órdenes de la tienda y dejarlas en `tn_ordenes.csv` (columnas fijas) más su resumen
   en `control.json`, dentro de la misma corrida diaria de `ingestas/mercado_datos.py`.

## Contexto
- Leer `AGENTS.md`, `CLAUDE.md`, `tareas/LEEME.md`, las consignas 70, 71 y 72, `ingestas/meli_oauth.py` y
  `ingestas/mercado_datos.py`. Mismo estilo: solo biblioteca estándar (`urllib`), comentarios en criollo, una sola
  función HTTP por módulo, reglas en funciones puras, escritura por temporal + `os.replace`.
- **El repo es público.** Nada de datos reales: cliente `ejemplo`, tienda y números inventados.
- La aplicación de Tiendanube (privada, "para tus clientes") la crea Thomas en el Portal de Socios. Sus credenciales
  las carga con `python setup_credenciales.py --cliente <c> --banco tiendanube` (usuario = **ID de la aplicación**,
  clave = **Client Secret**), igual que las de Mercado Libre. Leerlas con el mismo lector que usa `meli_oauth.py`.
- Página de vuelta (ya existe): `https://thomasmanzo.github.io/Finnauto/autorizado/`. Muestra el `code` que llega en la
  dirección; con un `state` que no empieza con `ml`/`mp` lo muestra sin prefijo. Igual, `canjear` acepta que le peguen
  el código con un prefijo `TN: ` y lo saca.

### Autorización (documentación oficial, nuvemshop.dev, revisada por Claude el 01/11/2026)
- **Link:** `https://www.tiendanube.com/apps/<app_id>/authorize?state=<state>`. El `state` lo arma el programa
  (`tn-` + 8 caracteres al azar). El dueño (o alguien con acceso al administrador de la tienda, con la sesión iniciada)
  lo abre, acepta, y vuelve a la página con `?code=...&state=...`. **El código vence a los 5 minutos.**
- **Canje:** `POST https://www.tiendanube.com/apps/authorize/token` con **JSON**
  `{"client_id": "<app_id>", "client_secret": "<secret>", "grant_type": "authorization_code", "code": "<code>"}`.
  Responde `access_token`, `token_type` (`bearer`), `scope` (separado por comas, ej. `read_orders,read_products`) y
  `user_id` (= número de la tienda; algunas respuestas lo traen como `store_id`: aceptar cualquiera de los dos).
- **El token no vence** (deja de servir si desinstalan la aplicación o se pide uno nuevo). No hay renovación.
- Guardar en el llavero, como hace `meli_oauth.py`, en `finauto:<cliente>:tiendanube-token`: `access_token`,
  `store_id`, `scope`. **Nunca imprimir ni guardar en archivos el token, el secret ni el código.**
- Errores en criollo, sin mostrar el cuerpo de la respuesta (puede traer el código o el secret): código vencido o ya
  usado, credenciales de la aplicación inválidas, falta autorizar, la aplicación fue desinstalada (401 en la API).

CLI (como el de la 70):
`python -m ingestas.tiendanube --cliente <c> link | canjear | estado | probar`
- `link`: imprime el link (lee el ID de la aplicación del llavero).
- `canjear`: pide el código por la entrada estándar (sin mostrarlo de vuelta), canjea y guarda.
- `estado`: si hay permiso, número de tienda y permisos (`scope`). Sin mostrar el token.
- `probar`: un pedido a la API (`GET /store` o una orden) y dice "OK" o el motivo.

### API (documentación oficial)
- Base: `https://api.tiendanube.com/2025-03/<store_id>`. Encabezados: `Authorization: Bearer <access_token>` y
  **`User-Agent: Finauto (contacto@finauto.com.ar)`** (sin User-Agent la API contesta 400).
- Límite: 2 pedidos por segundo sostenidos (balde de 40). Si contesta `429`, esperar lo que diga
  `x-rate-limit-reset` (milisegundos) o, si no viene, 2, 4, 8, 16, 32 s; reintentar también ante 5xx y cortes de red,
  como `meli_ventas.Sesion`. `401` = la aplicación se desinstaló o el permiso no sirve → la fuente queda en error
  ("hay que volver a autorizar Tiendanube"). `402` = la tienda o la aplicación tiene un pago pendiente → error con ese
  motivo.
- Órdenes: `GET /orders?created_at_min=<ISO>&created_at_max=<ISO>&per_page=200&page=1` y también
  `updated_at_min=<ISO>` para traer solo lo que cambió. Paginar **siguiendo el encabezado `Link` (`rel="next"`)**
  hasta que no haya siguiente (no armar las páginas a mano). `x-total-count` trae el total.
- Campos de cada orden que se usan: `id`, `number`, `created_at`, `updated_at`, `status` (`open`, `closed`,
  `cancelled`), `payment_status` (`pending`, `authorized`, `paid`, `abandoned`, `refunded`, `voided`), `subtotal`,
  `total`, `shipping_cost_customer`, `payment_details.installments`, `products[]` con `sku`, `name`, `quantity`,
  `price`. Los importes vienen como texto con punto decimal (ej. `"12500.00"`).
- Las fechas vienen con huso (ej. `2026-09-10T11:06:30-0300` o `+0000`): todo a hora de Buenos Aires.

### `tn_ordenes.csv` (en la carpeta `--salida`)
Columnas, en este orden:
`numero_orden,fecha,estado_pago,sku,producto,cantidad,precio,subtotal,descuento,costo_envio,total,cuotas,neto_cobrado,fecha_acreditacion`
- **Una fila por producto.** Los importes de la orden (`subtotal`, `descuento`, `costo_envio`, `total`, `cuotas`) van
  **solo en la primera fila** de la orden; en las demás, vacíos (para que sumar no duplique).
- `numero_orden` = `number`; `fecha` = `created_at` (AAAA-MM-DD HH:MM, Buenos Aires).
- `estado_pago`: `cancelada` si `status == "cancelled"`; si no, según `payment_status`: `paid` → `pagada`,
  `pending` → `pendiente`, `authorized` → `autorizada`, `refunded` → `reintegrada`, `voided` → `anulada`,
  `abandoned` → `abandonada`; otro valor → tal cual.
- `sku` tal cual viene (sin normalizar); `producto` = `name`; `cantidad` = `quantity`; `precio` = `price` (2 decimales).
- `subtotal` = `subtotal`; `costo_envio` = `shipping_cost_customer` (0 si viene vacío); `total` = `total`;
  `descuento` = `total − subtotal − costo_envio` (negativo o 0; así la fila cierra siempre: subtotal + descuento +
  costo_envio = total). Si da **positivo** (más de 1 peso), la orden cuenta como rara en el control (ver abajo) y el
  descuento se escribe igual.
- `cuotas` = `payment_details.installments` (vacío si no viene).
- `neto_cobrado` y `fecha_acreditacion`: **vacías** por ahora (las va a llenar el cruce con el banco, otra tarea).
- Van las órdenes con `fecha` ≥ `--desde`, de todos los estados. Orden: por `fecha` y `numero_orden`.
- Montos con punto decimal, sin miles, 2 decimales; números de orden como texto.

### Caché y corrida diaria
- Caché en `clientes/<c>/.run/tiendanube/cache/` (un JSON por orden). Primera corrida: todo desde `--desde`, de a un
  mes. Después: las creadas en los últimos 2 meses completos más las cambiadas desde la última corrida buena − 2 días
  (`updated_at_min`). Lo demás sale de la caché. La fecha de la última corrida buena va en un archivo de esa carpeta.
- Integrar en `ingestas/mercado_datos.py` como fuente **`tiendanube`** (después de las otras tres; `--solo tiendanube`
  también vale). Si falla, su CSV anterior queda como estaba y las otras fuentes siguen.
- **Si el cliente no tiene cargadas las credenciales de la aplicación de Tiendanube** (no está en el llavero), la fuente
  no se corre y no se escribe en `control.json` (así un cliente sin Tiendanube no queda en rojo todos los días). Si
  hay credenciales pero no hay permiso, error: "falta autorizar Tiendanube".
- `control.json`: fuente `tiendanube` con `ok`, `filas`, `desde`, `hasta`, `motivo` y además `raras` (órdenes cuyo
  descuento calculado da positivo). Conservar las otras fuentes.

### Ejemplos inventados (usar estos en las pruebas)
**M.** Orden `id 9000001`, `number 1001`, `created_at "2026-09-10T11:06:30-0300"`, `status open`,
`payment_status paid`, dos productos: `sku "AB 100"`, "Lámpara", 2 × `"10000.00"`; `sku "AB-200"`, "Pantalla", 1 ×
`"5000.00"`. `subtotal "25000.00"`, `shipping_cost_customer "3000.00"`, `total "26000.00"`, `installments 3`.
→ dos filas: la primera `1001, 2026-09-10 11:06, pagada, AB 100, Lámpara, 2, 10000.00, 25000.00, -2000.00, 3000.00,
26000.00, 3, , ` y la segunda `1001, 2026-09-10 11:06, pagada, AB-200, Pantalla, 1, 5000.00` con los importes vacíos.

**N.** Orden cancelada con `payment_status refunded` → `estado_pago cancelada`.

**O.** Orden con `subtotal "10000.00"`, envío `"0.00"` y `total "10500.00"` → `descuento 500.00` y cuenta como rara.

**P.** Canje: respuesta con `store_id` en vez de `user_id` → se guarda igual. Código pegado como `TN: abc123` → se
canjea `abc123`.

## Archivos permitidos
- `ingestas/tiendanube.py` (nuevo): autorización (CLI) y bajada de órdenes.
- `ingestas/mercado_datos.py` (cambios: fuente `tiendanube`).
- `tests/test_tiendanube.py` (nuevo).
- Esta consigna (sección "Qué hice").

## Resultado esperado
- `python -m ingestas.tiendanube --cliente <c> link|canjear|estado|probar` funciona como el de la 70.
- `python -m ingestas.mercado_datos --cliente <c> --salida <carpeta>` escribe además `tn_ordenes.csv` y la fuente
  `tiendanube` en `control.json` (o la saltea si el cliente no tiene Tiendanube).

## Comprobaciones
- `python tests/test_tiendanube.py` (sin pytest; HTTP y llavero falsos), cubriendo: link con `state`; canje (M/P,
  JSON, sin imprimir secretos, errores en criollo sin cuerpo de respuesta); ejemplos M, N y O; paginación por `Link`;
  429 con `x-rate-limit-reset`; 401 y 402; caché e incremental por `updated_at_min`; cliente sin credenciales (se
  saltea); CSV anterior intacto si falla; `control.json` conserva las otras fuentes.
- `python tests/test_meli_ventas.py`, `tests/test_meli_publicidad.py`, `tests/test_mp_liquidaciones.py` y
  `tests/test_meli_oauth.py` siguen dando OK.
- Lo que no se puede probar acá (la tienda real): lo hace Claude en la Mac cuando el cliente autorice.

## Qué hice

## Revisión
