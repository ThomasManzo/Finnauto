# Tarea 18 — AGREGADO (25/09, escrito después de que Codex arrancó)

Esto **manda sobre** lo que diga `tareas/18-tango-api-de-verdad.md` donde se contradigan. Mismos
archivos permitidos, misma rama (`tarea/tango-api`). Al terminar, contestá en "Qué hice" de la
consigna original qué parte de este agregado aplicaste.

## Qué cambió: ahora hay consultas personalizadas en Live

Se guardaron en Live (Mis consultas, usuario de la API) ocho consultas con **las mismas columnas del
export a mano**. Con el parámetro `customQuery=<número>`, la API devuelve esas columnas en vez de la
vista por defecto. Comprobado contra el Tango real el 25/09: montos al peso contra la pantalla y
contra el export a mano del 23/09.

| Empresa (Company) | Consulta | process | customQuery |
|---|---|---|---|
| A (13) | cobranzas | 17952 | 10 |
| A (13) | pagos | 17696 | 11 |
| A (13) | cheques_terceros | 11583 | 12 |
| A (13) | cheques_propios | 11584 | 13 |
| AA (56) | cobranzas | 17952 | 14 |
| AA (56) | pagos | 17696 | 15 |
| AA (56) | cheques_terceros | 11583 | 16 |
| AA (56) | movimientos_tesoreria | 11591 | 17 |

## Cambios sobre la consigna

1. **`perfil.json → tango_live`**: los números de `customQuery` van **por empresa y consulta**
   (la tabla de arriba). Estructura sugerida:
   `"consultas_personalizadas": {"A": {"cobranzas": 10, ...}, "AA": {"cobranzas": 14, ...}}`.
   La clave vieja `custom_query: "-"` se borra.
2. **Sin `customQuery` no se baja.** Si una (empresa, consulta) no tiene número, error claro para
   esa bajada ("falta la consulta personalizada en perfil.json"); no volver a la vista por
   defecto, porque le faltan columnas.
3. **Fechas**: esto reemplaza el rango 01/01/1990 → +5 años del punto 1 de "Resultado esperado".
   - Todas las consultas, **menos cheques propios**: `fromDate=` y `toDate=` **vacíos**. Así lo
     arma la propia pantalla de Live y trae todo sin filtro de fecha.
   - **cheques_propios**: `fromDate` = **hoy − 60 días** (DD/MM/AAAA, calculado desde `--hoy`) y
     `toDate` vacío. Por qué: Tango nunca marca como debitado un cheque propio, así que "Al Cobro"
     junta todo desde 1995 (21.951 cheques); lo único que separa lo pendiente es la fecha.
     **Comprobado el 25/09**: con `fromDate=26/08/2026` vinieron 19 cheques con FECHA_DEL_CHEQUE
     del 27/08/2026 al 25/05/2027 y FECHA_DE_EMISION desde 10/2025. O sea, **filtra por fecha
     del cheque**, no por emisión: los diferidos emitidos hace meses entran igual. El lector usa
     de hoy − 30 en adelante, así que 60 deja margen. Los 60 días van en `perfil.json`
     (ej. `"dias_atras": {"cheques_propios": 60}`), no fijos en el código.
4. **Columnas que devuelve cada consulta personalizada** (comprobado) y a qué encabezado del export
   a mano se traducen:

   - **cobranzas** (A y AA): ID_GVA12, TIPO_COMPROBANTE→`Tipo comprobante`,
     NRO_COMPROBANTE→`Nro. comprobante`, FECHA_DE_VENCIMIENTO→`Fecha de vencimiento`,
     FECHA_DE_EMISION→`Fecha de emisión`, ID_GVA14, COD_CLIENTE→`Cód. cliente`,
     RAZON_SOCIAL→`Razón social`, DESCRIPCION_CONDICION_DE_VENTA→`Descripción condición de venta`,
     IMPORTE_AL_VENCIMIENTO_CTE→`Importe al Vencimiento (CTE)`,
     IMPORTE_PENDIENTE_CTE→`Importe Pendiente (CTE)`.
   - **pagos** (A y AA): ID_CPA01, ID_CPA04, FECHA_DE_VENCIMIENTO→`Fecha de vencimiento`,
     TIPO_DE_COMPROBANTE→`Tipo de comprobante`, NRO_COMPROBANTE→`Nro. comprobante`,
     FECHA_DE_EMISION→`Fecha de emisión`, COD_PROVEEDOR→`Cód. proveedor`,
     RAZON_SOCIAL→`Razón social`, TOTAL_AL_VENCIMIENTO_CTE→`Total al vencimiento (CTE)`,
     TOTAL_PENDIENTE_CTE→`Total pendiente (CTE)`.
   - **cheques_terceros** (A y AA): ID_SBA14, ID_GVA14, NRO_DE_CHEQUE→`Nro. de cheque`,
     FECHA_DEL_CHEQUE→`Fecha del cheque`, BANCO→`Banco`, COD_ESTADO→`Cód. estado` (el código tal
     cual), ESTADO→`Estado` (**traducido a texto**: viene el mismo código que COD_ESTADO),
     SUBESTADO→`Subestado`, DESC_SUBESTADO→`Desc. subestado`, ORIGEN→`Origen`,
     COD_CLIENTE→`Cód. cliente`, CLIENTE→`Cliente`, IMPORTE_CTE→`Importe (CTE)`.
   - **cheques_propios** (solo A): ID_SBA15, NRO_DE_CHEQUE→`Nro. de cheque`,
     FECHA_DE_EMISION→`Fecha de emisión`, FECHA_DEL_CHEQUE→`Fecha del cheque`, ID_CPA01,
     COD_PROVEEDOR→`Cód. proveedor`, RAZON_SOCIAL→`Razón social`, ESTADO→`Estado` (traducido) y
     el código en `Cód. estado`, BANCO→`Banco`, CUENTA_EMISION→`Cuenta emisión`,
     IMPORTE→`Importe mon. cta.`.
   - **movimientos_tesoreria** (solo AA): TIPO→`Tipo`, ID_SBA04, COMPROBANTE→`Comprobante`,
     FECHA→`Fecha`, FECHA_DE_EMISION→`Fecha de emisión`, CONCEPTO→`Concepto`, CLASE→`Clase`
     (traducido), TOTAL_CTE→`Total (cte)`, COD_RELACIONADO→`Cód. relacionado`,
     DESC_RELACIONADO→`Desc. relacionado`, CLASIFICACION→`Clasificación`.

   Los ID_* no tienen equivalente: van al final con su nombre, como dice la consigna.
5. **Códigos: ahora confirmados** (ya no son "inferidos"):
   - cheques_propios: **E = Al Cobro**. La API dio 39 cheques E por $582.964.152,10 y el
     export a mano del 23/09 tenía 39 "Al Cobro" por el mismo importe, al centavo. La consulta
     guardada (13) ahora filtra **Estado = Al Cobro o Diferido**, así que R/X ya no vienen. El
     código de "Diferido" no se vio nunca: si aparece, queda `"(código X sin traducir)"` y se ve
     en el resumen.
   - movimientos_tesoreria: **1 = Cobros, 2 = Pagos, 4 = Otros movimientos de bancos y carteras,
     6 = Rechazo de cheques de terceros**. API 25/09: 1206 / 4255 / 308 / 9. A mano 23/09: 1204 /
     4252 / 308 / 9.
   - cheques_terceros: C / A / R como estaba. **Aparece una `X`** (107 en A) que no está en ningún
     export a mano: queda `"(código X sin traducir)"`, que es justamente lo que pide el punto 4 de la
     consigna. No adivinarla.
6. **Cheques de terceros de A: 75.624 filas** con la consulta personalizada (sin filtro de estado).
   Sigue valiendo el punto 6: escribir solo los C (hoy 45).

## Números para la corrida supervisada (no son para los tests)

cobranzas A 345 / pendiente 413.697.844,58 · pagos A 425 / 638.905.653,94 · cheques propios A 19 desde el 26/08 (cambia con la fecha) · cobranzas AA 33 / 88.852.823,49 · pagos AA 119 / 176.429.819,12 · cheques
terceros AA 268 (C = 14) · tesorería AA 5.778.
