# Tarea 44 — La bajada de Tango trae el detalle de tesorería de A (para el cruce)
Estado: aprobada
Rama: tarea/tesoreria-a-detalle

## Objetivo
Que la bajada diaria de Tango (07:30) traiga también el **detalle de comprobantes de tesorería de A**
(un renglón por cuenta imputada), para que el cruce banco ↔ Tango (`lector/cruce.py`, tarea 40) tenga
el dato al día sin exports a mano.

## Contexto
- La consulta 19 ("Finauto A tesorería", proceso 11591) trae un renglón por **comprobante**: sirve para
  "último pago", pero no dice por qué cuenta de banco entró o salió la plata. El cruce necesita el
  **detalle**: Live → Tesorería → Consultas → Comprobantes → Detalle (proceso **12480**).
- 05/10/2026: Thomas creó en Live la consulta personalizada **21 "Finauto A tesoreria detalle"** con
  18 columnas (las que lee el cruce). No borrarla ni editarla.
- El número de proceso se confirmó por la hoja `_metadata` del export a mano (campo `access`), que
  coincide con los procesos conocidos (cobranzas, pagos, tesorería).

## Archivos permitidos
`ingestas/tango_live.py`, `ingestas/test_tango_live.py`, `clientes/navar/perfil.json`,
`lector/cruce.py` (solo para reconocer el archivo de la API), `clientes/navar/herramientas/aviso_diario.gs`,
`lector/pruebas/probar_aviso_bajadas.cjs` y las pruebas `.cjs` que cuentan bajadas.

## Resultado esperado
- Nueva consulta `detalle_tesoreria` (solo A): proceso 12480, consulta 21, últimos 120 días, carpeta
  `NAVAR - Datos/Tesoreria A detalle/`, archivo `A tesoreria detalle <fecha>.xlsx` con los encabezados
  del export manual. Si faltan las columnas que usa el cruce, no se publica (error en el log y en el mail).
- La bajada pasa de 9 a **10** fotos (6 de A, 4 de AA): `TOTAL_BAJADAS_DIARIAS` y `TANGO_BAJADAS`.
- El mail de las 09:00 nombra la foto nueva como "detalle de tesorería".
- El vigilante NO la procesa (todavía no alimenta la Sheet): solo queda en Drive para el cruce.

## Comprobaciones
- `python -m unittest ingestas.test_tango_live lector.pruebas.test_cruce` y el `.cjs` del aviso.
- En la notebook: `--probar detalle_tesoreria --empresa A` muestra las columnas que manda la API
  (solo estructura, sin datos) y confirma los nombres supuestos (`CUIT_ENCAB`, `DEBE_CTE_RENGLON`...).

## Qué hice
**La escribió Claude** (Codex en pausa). Los nombres de la API se tomaron del `_metadata` del export a
mano: se confirman con `--probar` en la notebook antes de dar la tarea por cerrada. `lector/cruce.py`
ahora reconoce el detalle por sus encabezados (la API no le pone nombre a la hoja). Pruebas: 23 de la
bajada (3 nuevas: el cruce lee la foto, sin columnas no se publica, solo A con ventana de 120 días),
31 del cruce, `.cjs` del aviso con el caso "falló solo el detalle".

## Revisión
05/10/2026: mergeada con el OK de Thomas. `--probar detalle_tesoreria --empresa A` en la notebook
confirmó los nombres de la API: llegan las 18 columnas y se traducen todas. Vienen 4 más sin
equivalencia (`ID_SBA04`, `ASOCIA_UNIDADES`, `ID_SBA01`, `COD_TIPO_CUENTA`) que quedan al final.
