# Tarea 48 — Las cajas de A y de AA en el cash, con "de qué caja sale" y la leyenda
Estado: pendiente
Rama: tarea/cajas-a-y-aa

## Objetivo

NAVAR pidió (06/10/2026) dos cosas en la planilla:

1. Que **los movimientos de caja de las dos empresas** (A y AA) estén en la solapa Movimientos y que el
   cash muestre **el saldo de cada caja por separado**: "Caja A (efectivo)" y "Caja AA (efectivo)".
   Hoy solo está la de AA; la plata que entra y sale por caja en A no aparece en el cash.
2. Que cada movimiento de caja diga **de qué caja de Tango sale** y **la leyenda** que escribe quien
   carga la orden (ej. "VIATICOS VIAJE A ROSARIO", "PAGO PLANILLA SUELDOS QUINCENA"). Dos columnas nuevas.

El saldo de cada caja arranca del **arqueo** (conteo físico) que carga la administración, y le suma los
movimientos de caja posteriores. Es lo mismo que hoy hace la caja de AA, extendido a A.

**Lo que no puede pasar: contar dos veces la misma plata.** Un depósito de la caja al banco tiene que
bajar la caja y subir el banco, y no aparecer como cobro nuevo.

## Contexto

Leer antes: `tareas/LEEME.md`, `CLAUDE.md` (**el repo es público: nada de datos reales**),
`ingestas/tango_live.py`, `lector/tesoreria_aa.py`, `clientes/navar/herramientas/vigilante.py`,
`clientes/navar/herramientas/importar_cashflow.gs`, `clientes/navar/herramientas/crear_cash.gs`
(sobre todo `CORTE_REAL`, `ORIGENES_REALES`, `_real_`, el bloque de saldos por banco con `movCaja`
y `_bancos_`), `clientes/navar/herramientas/aviso_diario.gs` y las tareas 34, 44 y 47.

Lo que existe hoy:
- **Tango "Detalle de comprobantes" de tesorería** (proceso 12480): un renglón por cuenta imputada. Columnas
  útiles: `Fecha` (fecha del movimiento, tarea 47), `Fecha de emisión`, `Cód. comprobante`, `Comprobante`,
  `Nro. interno` (agrupa los renglones de un comprobante), `Cód. cuenta`, `Desc. cuenta`,
  `Debe (cte) (renglón)`, `Haber (cte) (renglón)`, `Razón social (encab.)`, `Leyenda`. La API además manda
  `COD_TIPO_CUENTA` (se conserva al final con su nombre de API; ver si distingue caja/banco/otras).
  - **A**: ya baja todos los días (consulta 21, `Tesoreria A detalle/`, 120 días) para el cruce.
  - **AA**: consulta **22** creada el 06/10/2026 en Live (empresa 56), mismas columnas. **Todavía no baja.**
    Probada: devuelve las columnas de la 21 más `FECHA`, `COD_TIPO_CUENTA`, `COD_PROVEEDOR_ENCAB`.
- La caja de AA hoy: `lector/tesoreria_aa.py` lee la consulta 17 (un renglón por **comprobante**, sin cuenta
  ni leyenda) y escribe en Movimientos filas con `Banco / Cuenta` = "Caja AA", Origen "Tango AA · …".
  El cash suma esas filas al último arqueo de "Caja AA" (Saldos Bancarios, carga manual).
- Lo visto en los datos (ejemplo de la forma, montos y textos inventados):
  - En A hay dos cuentas de caja en Tango: una de **contado** (cobros, pagos a proveedores, sueldos,
    gastos y algún depósito al banco) y una de **facturación** (casi solo facturas de contado).
  - En AA hay una caja **del directorio** (casi todos los movimientos, todos con leyenda) y una de contado.
  - Un comprobante típico de pago por caja: renglón 1 `GASTOS VARIOS` Debe 120.000; renglón 2
    `CAJA X` Haber 120.000; Leyenda "PASAJES VIAJE PROVEEDOR". A la caja le corresponde **su** renglón:
    −120.000.
  - Un recibo puede imputarse parte a caja y parte a banco o a valores a depositar: a la caja le toca solo
    su renglón.

**Qué cuentas son "caja" de cada empresa** lo define el perfil, no el código (nueva sección de
`perfil.json`, ver abajo). La lista real la confirma Claude con NAVAR antes de pasar la tarea.

## Archivos permitidos

- `ingestas/tango_live.py`, `ingestas/test_tango_live.py`
- `clientes/navar/perfil.json` (secciones `tango_live` y la nueva `cajas`)
- `lector/cajas.py` (nuevo) y `lector/pruebas/test_cajas.py` (nuevo)
- `lector/tesoreria_aa.py` (solo si hace falta para reusar funciones; deja de correr en el circuito)
- `clientes/navar/herramientas/vigilante.py`
- `clientes/navar/herramientas/importar_cashflow.gs`
- `clientes/navar/herramientas/crear_cash.gs`
- `clientes/navar/herramientas/aviso_diario.gs`
- pruebas `.cjs` en `lector/pruebas/` (nuevas o las que cuentan bajadas / fuentes)
- esta consigna ("Qué hice" y `Estado:`)

## Resultado esperado

1. **Bajada** (`tango_live.py` + perfil): `detalle_tesoreria` también para **AA** (consulta 22), carpeta
   propia `Tesoreria AA detalle/` (nunca mezclar con `Tesoreria AA/` ni con la de A). Ventana de días
   configurable por empresa; para las dos, **180 días**. Bajadas diarias de 10 a **11**; actualizar
   `TOTAL_BAJADAS_DIARIAS`, `TANGO_BAJADAS` del aviso y la lista de fotos de AA en el aviso.
2. **Perfil, sección nueva `cajas`**:
   ```json
   "cajas": {
     "_ayuda": "Qué cuentas de tesorería de Tango son caja física de cada empresa (por el comienzo de Desc. cuenta, sin importar mayúsculas). Cada empresa suma sus cuentas en una sola caja del cash.",
     "A":  {"nombre_en_el_cash": "Caja A",  "cuentas": ["<completa Claude>"]},
     "AA": {"nombre_en_el_cash": "Caja AA", "cuentas": ["<completa Claude>"]}
   }
   ```
3. **Lector nuevo `lector/cajas.py`** (reemplaza a `tesoreria_aa.py` en el circuito diario):
   - Entrada: el detalle más nuevo de A y el de AA (`--a`, `--aa`; los dos obligatorios, como en la tarea 34:
     si falta uno no escribe nada).
   - Por cada renglón cuya `Desc. cuenta` empiece con una de las cuentas de caja de esa empresa, **una fila de
     Movimientos**:
     - `Fecha` = `Fecha` del movimiento (si viene vacía, `Fecha de emisión`)
     - `Empresa` = A / AA
     - `Importe` = Debe − Haber (entra positivo, sale negativo; las reversiones quedan con su signo)
     - `Tipo` = Ingreso si el importe es positivo, si no Egreso
     - `Medio de Pago` = "Efectivo"
     - `Banco / Cuenta` = el `nombre_en_el_cash` de la empresa ("Caja A" / "Caja AA")
     - `Estado` = "Real"
     - `Referencia` = código y número de comprobante
     - `Concepto / Detalle` = contraparte (`Razón social (encab.)`) · leyenda, recortado
     - **`Cuenta Tango`** = la `Desc. cuenta` de ese renglón (de qué caja de Tango sale)
     - **`Leyenda`** = la leyenda del comprobante
   - `Origen`: para **AA** debe seguir empezando con `Tango AA` (lo usan las fórmulas del cash); para **A**,
     `Tango caja A · …`. Ojo: `Tango A*` como patrón también agarra `Tango AA`; por eso el de A no
     empieza con "Tango A".
   - **Categoría**, mirando los otros renglones del mismo comprobante (`Nro. interno`):
     - si otro renglón es una **cuenta de banco** u **otra caja** (de la misma o de la otra empresa), es un
       pase entre cuentas propias → `Transferencia Interna`. Esto cubre los depósitos de la caja al banco y
       los pases entre cajas, y es lo que evita contar dos veces;
     - si la contraparte es la propia NAVAR S.A., `Transferencia Interna` (igual que hoy en `tesoreria_aa.py`);
     - cobros (recibos, facturas de contado): A → la categoría de cobranza de A que use hoy el cash para lo
       cobrado; AA → `Cobranza AA`;
     - sueldos (otro renglón de sueldos y jornales, o concepto/leyenda que lo diga) → `Sueldos y Jornales`;
     - pagos a proveedores (acreedores) → A: `Proveedores MP y Logist.`; AA: `Proveedores AA`;
     - gastos varios, viáticos y el resto → `Otros`.
     Las categorías tienen que ser las que **ya existen** en la Sheet (validación de la columna Categoria).
     Para distinguir banco/caja usar `COD_TIPO_CUENTA` si resulta confiable en los datos; si no, el perfil.
   - Salida: `para_pegar_cajas_<hoy>.xlsx` (solapa Movimientos, mismo encabezado que hoy + las dos columnas
     nuevas al final) y un `resumen_cajas_<hoy>.md`: por empresa y por cuenta de caja, cantidad de
     movimientos, total de entradas y salidas por mes y cuántos quedaron como transferencia interna.
4. **Vigilante**: fuente nueva `cajas` (mira las dos carpetas de detalle; corre con el más nuevo de cada
   una). La fuente `tesoreria_aa` deja de correr (no se borra el lector viejo; se deja comentado por qué).
5. **Importador** (`importar_cashflow.gs`): entrada `cajas` que en Movimientos pisa solo las filas con marca
   `Tango AA` y `Tango caja A` (Origen). Sacar `tesoreria_aa` de `ORDEN_AUTO`. **Las dos columnas nuevas
   van al final de Movimientos**; los otros importadores (bancos) no las traen y no tienen que fallar por eso
   (si el importador hoy exige que el xlsx tenga todas las columnas de la hoja, ajustarlo y probarlo).
6. **Cash** (`crear_cash.gs`):
   - `_bancos_`: reconocer las dos cajas (`Caja A`, `Caja AA`, y el viejo "(varios)" como AA), con
     etiqueta "Caja A (efectivo)" / "Caja AA (efectivo)", carga manual.
   - El saldo de cada caja = último arqueo de **esa** caja (Saldos Bancarios) + movimientos posteriores de
     **esa** caja: filtrar Movimientos por `Banco / Cuenta` = nombre de la caja y Origen que empiece con
     "Tango" (hoy filtra solo por Origen "Tango AA").
   - Lo real de A por caja tiene que sumar en los renglones de ingresos/egresos del cash igual que lo del
     extracto: agregar el origen `Tango caja A*` a `ORIGENES_REALES` con su propia fecha de corte (último
     día con movimientos de caja de A), como ya existe para AA.
   - Nada más del cash cambia de lugar ni de fórmula.
7. **Aviso**: `FUENTES_AUTOMATICAS` y cualquier referencia a `tesoreria_aa` pasan a `cajas`.

## Comprobaciones

- Pruebas Python con detalles **inventados** de A y AA:
  - pago por caja (2 renglones) → una fila, negativa, con cuenta y leyenda;
  - recibo mitad caja y mitad banco → solo la parte de caja;
  - depósito caja → banco y pase entre cajas → `Transferencia Interna`, nunca cobranza ni pago;
  - reversión → resta;
  - cuenta que no está en el perfil → no entra;
  - falta un archivo → no escribe nada;
  - el Origen de A **no** matchea el patrón `Tango AA*` y el de AA sí.
- `python -m unittest ingestas.test_tango_live` con 11 bajadas, y las pruebas `.cjs` del aviso e importador.
- Prueba del importador: Movimientos con las dos columnas nuevas; filas de bancos sin esas columnas no se rompen.
- `crear_cash.gs`: prueba `.cjs` (con dobles, como las otras) de que la fórmula de saldo de "Caja A" filtra
  por su caja y la de "Caja AA" por la suya.
- Qué **no** se puede probar acá: los datos reales, la Sheet y el arqueo. Lo valida Claude con NAVAR:
  saldo de cada caja contra el arqueo, totales viejos de AA contra los nuevos, y que el total del cash no
  cambie por los pases internos.

## Qué hice

## Revisión
