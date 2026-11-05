# Tarea 78 — Bajada del saldo diario de Mercado Pago a mp_saldo.csv
Estado: lista para revisión
Rama: tarea/78-saldo-mercado-pago

## Objetivo
Sumar a `ingestas/mercado_datos.py` una fuente nueva, `mercadopago_saldo`, que escribe `mp_saldo.csv` con una fila por día.
El saldo sale del reporte de liberaciones de Mercado Pago (`release_report`), que trae la columna `BALANCE_AMOUNT`.

## Contexto
- Leer `AGENTS.md`, `CLAUDE.md`, `tareas/LEEME.md` y `ingestas/mp_liquidaciones.py`, que resuelve el mismo problema para
  otro reporte: seguir su estilo y reusar `atomico`, `fecha`, `instante`, `limites`, `meses`, `monto`, `ErrorDatos`.
- **El repo es público.** Nada de datos reales: cliente `ejemplo`, números inventados.
- **Prohibido tocar la configuración de los reportes.** `/config` se lee con GET y nunca se manda POST ni PUT ahí. Tampoco
  programar reportes.
- Endpoints, base `https://api.mercadopago.com/v1/account/release_report`:
  - `GET /config`: da, entre otros, `separator` y `display_timezone`.
  - `GET /list`: lista con `id`, `begin_date`, `end_date`, `status` (`enabled` o `processed` = listo; `pending` = se está
    generando), `format` (`CSV` o `XLSX`), `file_name`.
  - `POST` a la base, con `{"begin_date": ..., "end_date": ...}` en UTC: pide un reporte (responde 202).
  - `GET /<file_name>`: baja el archivo.
- Forma del CSV (separador `;`, ejemplo inventado, sin todas las columnas):
  ```
  DATE;SOURCE_ID;DESCRIPTION;NET_CREDIT_AMOUNT;NET_DEBIT_AMOUNT;BALANCE_AMOUNT
  2026-01-10T00:00:00.000-03:00;;;1000.00;0.00;1000.00
  2026-01-10T09:00:00.000-03:00;111;payment;50.00;0.00;1050.00
  2026-01-10T10:00:00.000-03:00;;asset_management;2.50;0.00;1052.50
  2026-01-12T08:00:00.000-03:00;222;payout;0.00;52.50;1000.00
  ;;;1000.00;0.00;0.00
  ```
  La primera fila, con `DESCRIPTION` vacía, es el saldo de apertura. La última, con `DATE` vacía, es el total: se ignora.

## Archivos permitidos
- `ingestas/mp_saldo.py` (nuevo)
- `ingestas/mercado_datos.py`
- `tests/test_mp_saldo.py` (nuevo), `tests/test_mercado_datos.py`, `tests/test_tiendanube.py`, `tests/test_galicia_datos.py`
  (estos tres, solo lo mínimo para que sigan sin red con la fuente nueva)
- esta consigna (sección "Qué hice" y `Estado:`)

## Resultado esperado
1. `ingestas/mp_saldo.py` con `COLUMNAS = ['fecha', 'disponible', 'a_liberar', 'intereses_del_dia']` y una función
   `bajar(sesion, carpeta, ruta_csv, desde, hasta)` que devuelve `(filas, motivo)`, igual que `mp_liquidaciones.bajar`.
2. **Acumula y no pisa:** las filas que ya están en `mp_saldo.csv` quedan exactamente como están, aunque el reporte diga otra
   cosa para esa fecha. Solo se agregan fechas posteriores a la última guardada. Sin CSV previo, arranca en `desde`. Si ya
   está todo hasta `hasta`, devuelve lo guardado sin conectarse ni pedir token.
3. **Solo días cerrados:** `hasta` es ayer en hora de Buenos Aires; lo calcula `mercado_datos.py`.
4. **Reportes:** el período pendiente se parte por mes con `meses` y `limites`. Para cada tramo usa, en este orden: el archivo
   ya guardado en `carpeta` (`<inicio>_<fin>.csv`), un reporte CSV listo de `/list` con ese mismo inicio y fin, o un pedido nuevo.
   No pide si ya hay uno `pending` de ese tramo, ni repite un pedido del mismo día (marca `.pedido.json`, como en
   `mp_liquidaciones`). Espera con `time.sleep` hasta unos 5 minutos en total. Si no llegó, devuelve `motivo` con los tramos
   que faltan y no agrega nada de ese tramo ni de los posteriores, para no dejar días salteados.
5. **Validar antes de guardar en caché:** tienen que estar las columnas `DATE`, `DESCRIPTION`, `NET_CREDIT_AMOUNT`,
   `NET_DEBIT_AMOUNT` y `BALANCE_AMOUNT`, y una fila de apertura. Cada `BALANCE_AMOUNT` tiene que ser el anterior + crédito -
   débito. Si no, `ErrorDatos`: el CSV no se toca y el archivo roto no queda guardado. Un corte entre la última fila ya guardada
   en `mp_saldo.csv` y la apertura del reporte **no** es error, porque una fila vieja puede ser una lectura de pantalla.
6. **Cada día del tramo tiene su fila:**
   - `disponible`: el último `BALANCE_AMOUNT` del día. Un día sin movimientos repite el saldo anterior. Con dos decimales.
   - `intereses_del_dia`: la suma de crédito - débito de las filas `asset_management` de ese día, `0.00` si no hay.
   - `a_liberar`: vacío.
   La fecha es la de la columna `DATE` tal como viene (los primeros 10 caracteres): el reporte ya está en la zona horaria
   de la cuenta.
7. `mercado_datos.py`: fuente `mercadopago_saldo`, justo después de `mercadopago`, archivo `mp_saldo.csv`, también en `--solo`.
   Mismo tratamiento que las demás: entra en `control.json` y en el estado de `--solo-pendientes`, y si falla, el CSV anterior
   queda igual y la fuente queda en rojo. Un `motivo` hace fallar la fuente, igual que en `mercadopago`. El rango `desde` y `hasta`
   del resumen sale de la columna `fecha`. Sumar un renglón en criollo al docstring.

## Comprobaciones
Pruebas sin red, con `http` falso y `time.sleep` reemplazado, en `tests/test_mp_saldo.py`:
- El ejemplo de arriba da 3 filas: 10 con 1052.50 e intereses 2.50, 11 con 1052.50 e intereses 0.00, 12 con 1000.00.
- Una fila ya guardada con otro importe queda igual y solo se agregan las fechas nuevas; una segunda corrida no duplica.
- Todo al día: no se conecta ni pide token.
- Saldos que no encadenan: `ErrorDatos`, sin caché y sin tocar el CSV.
- Reporte que no llega: `motivo`, sin agregar el tramo, y una segunda corrida del mismo día no repite el POST.
- Nunca se manda POST ni PUT a `/config`.
- Corrida de `mercado_datos` con la fuente: aparece en `control.json`; si falla, el CSV anterior queda.
Comando: `PYTHONPATH=. /Users/thomasmanzo/Documents/Finnauto/.venv/bin/python3 -m unittest discover -s tests` (no hay pytest).
No se puede probar acá: la corrida real con el cliente, la hace Claude después de revisar.

## Qué hice

- Agregué `ingestas/mp_saldo.py`: conserva las filas anteriores, calcula cierres diarios e intereses netos y deja `a_liberar` vacío. Si ya está al día, devuelve el historial sin red ni token.
- Los reportes se buscan primero en caché y después en la lista, aceptando CSV `enabled` o `processed`. Se consultan los pendientes durante un máximo de diez esperas de 30 segundos en total. La marca del pedido evita repetirlo el mismo día; un tramo faltante frena también los posteriores.
- Antes de guardar cada reporte se comprueban columnas, apertura, fechas, importes y la cadena de saldos. Una diferencia respecto de una lectura histórica no pisa esa lectura ni genera error. `/config` se consulta únicamente con GET; no se configuran ni programan reportes.
- Integré `mercadopago_saldo` en `ingestas/mercado_datos.py`, después de `mercadopago`, con `--solo`, `control.json`, estado de pendientes y resumen por `fecha`. El cierre sigue siendo ayer en Buenos Aires. El CSV se escribe únicamente cuando la fuente termina sin faltantes ni errores.
- Agregué `tests/test_mp_saldo.py` y las comprobaciones de integración en `tests/test_mercado_datos.py`. Ajusté los dobles de prueba y el orden esperado en `tests/test_tiendanube.py`; `tests/test_galicia_datos.py` no necesitó cambios.
- Validación: `PYTHONPATH=. /Users/thomasmanzo/Documents/Finnauto/.venv/bin/python3 -m unittest discover -s tests`: **78 pruebas, OK**. `git diff --check`: sin errores. Se cubrieron días sin movimientos, intereses netos, historial intacto, segunda corrida, caché de varios meses, respuesta inválida, espera, pedido no duplicado, pendientes y control de fallas.
- Usé solamente ejemplos inventados y carpetas temporales, con HTTP falso y esperas reemplazadas. No accedí a datos reales ni instalé dependencias. La corrida real queda para Claude después de la revisión, como indica la consigna.
- Cambios dejados en este worktree y rama `tarea/78-saldo-mercado-pago`, **sin commit**, por instrucción de Thomas. La consigna ya estaba sin seguimiento al comenzar y sigue así. Sin dudas pendientes de implementación.
