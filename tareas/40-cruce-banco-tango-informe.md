# Tarea 40 — Cruce banco ↔ Tango: informe de un mes cerrado
Estado: pendiente
Rama: tarea/cruce-banco-tango

## Objetivo

Un programa nuevo, `lector/cruce.py`, que tome **un mes** y empareje cada movimiento de los
extractos bancarios de la empresa A con lo que Tango registró en tesorería (recibos, órdenes de
pago, boletas de depósito, transferencias entre cuentas), y deje un **informe** (Excel + resumen en
texto) con tres grupos:

1. **Conciliado**: está en el banco y en Tango (y con qué regla se emparejó).
2. **Solo en banco**: pasó por el banco y Tango no lo tiene → falta imputarlo en Tango.
3. **Solo en Tango**: Tango lo tiene y el banco no → todavía no se acreditó, o es un error de
   carga. Aparte, lo que **nunca pasa por el banco** (efectivo, cheques endosados).

En esta etapa **no se toca la Sheet**: el informe es para revisarlo a mano con agosto 2026. Cuando
esté validado, otra tarea hará que alimente la Sheet.

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `CLAUDE.md`, `clientes/navar/LEEME.md` (secciones del
18/09 y del 25/09), `lector/extractos.py` (encabezado y `clasificar`) y `lector/tesoreria_aa.py`
(como ejemplo de estilo: lectura por encabezado, `_norm`, `_m`, resumen `.md`).

**Por qué hace falta.** Tango "no se concilia": hay cobranzas que entran al banco y nadie imputa,
órdenes de pago cargadas que el banco nunca debitó, gastos bancarios que no están en Tango. Sin el
cruce, el cash mezcla lo real con lo que alguien cargó.

**Las dos puntas.**

- **Banco**: la solapa **Movimientos** de la Sheet, leída desde un export de la Sheet en Excel
  (`--sheet`). Columnas (por encabezado): `ID, Fecha, Empresa, Tipo, Categoria, Concepto / Detalle,
  Importe, Medio de Pago, Banco / Cuenta, Origen, Estado, Referencia, Semana (lunes), Observaciones`.
  Solo cuentan las filas cuyo `Origen` empieza con `"Extracto"` (hay también filas de Tango AA,
  "Manual" y "Proyeccion": se ignoran). `Importe` viene con signo (+ entra, − sale). `Banco / Cuenta`
  es `"<BANCO> <nro de cuenta>"`, por ejemplo `"GALICIA 0005459-5 070-1"`.
  El CUIT de la contraparte, cuando lo hay, está dentro de `Concepto / Detalle` (11 dígitos
  seguidos, a veces pegado a otro texto, p. ej. `"TRANSF:ABC123-20111111112"`) o en
  `Observaciones` con guiones (`"CUIT 20-11111111-2"`). En Galicia el concepto ya incluye las
  "Leyendas adicionales" (nombre y CUIT). El CUIT propio de NAVAR (`30558525025`) no cuenta como
  contraparte.

- **Tango**: el export de Tango Live **"Detalle de comprobantes" de Tesorería** de la empresa A
  (`--tango`). Es **un renglón por imputación contable** (un recibo tiene un renglón por cada
  cuenta: la cuenta del banco, "VALORES A DEPOSITAR", "CAJA", retenciones, "DEUDORES POR VENTAS"...).
  Hoja `Detalle de comprobantes`, encabezado en la fila 1. Columnas que se usan (por encabezado):

  | Columna | Para qué |
  |---|---|
  | `Fecha de emisión` | fecha del comprobante |
  | `Cód. comprobante` / `Desc. comprobante` | tipo: `REC` recibo, `O/P` orden de pago, `OPF` orden de pago varios, `FPR` factura contado proveedor (bancos: intereses, préstamos), `EXT` "extracto bancario" (transferencias entre cuentas propias), `BDM`/`BDG`/`BNA`/`BDC`/`BDF` boletas de depósito (Macro/Galicia/Nación/Corrientes/Francés), `RCT` rechazo de cheque, `REV` reversión, `FAC`, `NC1` |
  | `Comprobante` | número (con espacios adelante: limpiar) |
  | `Nro. interno` | agrupa los renglones de un mismo comprobante |
  | `Cód. cuenta` / `Desc. contable` | la cuenta imputada en ese renglón |
  | `Debe (cte) (renglón)` / `Haber (cte) (renglón)` | importe del renglón. **Para una cuenta de banco, Debe − Haber es el movimiento en el banco con el mismo signo que el extracto** (Debe = entra, Haber = sale) |
  | `Total comp. (cte)` | total del comprobante (solo informativo) |
  | `CUIT cliente (encab.)` / `CUIT proveedor (encab.)` | CUIT de la contraparte (formato `20-11111111-2`) |
  | `Razón social (encab.)` / `Proveedor (encab.)` | nombre de la contraparte |
  | `Leyenda` | texto libre de quien cargó (p. ej. "VENTA VALORES", "INTERESES VTA VALORES MACRO") |

  Hay una fila casi vacía al final (sin fecha): se descarta. Resolver columnas por encabezado con
  alternativas (como `_rangos_`/`_columnas` en otros lectores), porque más adelante este mismo export
  va a llegar por la API de Live y los nombres pueden variar un poco.

**Qué renglones de Tango entran al cruce.** Solo los renglones cuya cuenta es una **cuenta de banco
con extracto** (lista en el perfil, abajo). Esos son los que tienen que aparecer en el banco. Los
demás renglones de un recibo u orden de pago no se emparejan, pero sirven para el bloque "no pasa
por el banco" (ver Resultado).

**Correspondencia de cuentas** (va al perfil, bloque nuevo `cruce`):

| Cuenta del extracto (`Banco / Cuenta`) | `Cód. cuenta` de Tango |
|---|---|
| `GALICIA 0005459-5 070-1` | 5 |
| `MACRO 3-033-0000083019-1` | 25 |
| `BBVA 489-000765/9` | 89 |
| `BBVA 489-000806/5` (cuenta recaudadora) | 89 |
| `NACION 19477890007728` | 88 |
| `CORRIENTES 130559` | 4 |

Las dos cuentas de BBVA van a la misma cuenta de Tango: la recaudadora pasa todo a la principal. Las
transferencias **entre dos cuentas del extracto que van a la misma cuenta de Tango** se cancelan
entre sí y Tango no las registra: se apartan como "internas de la misma cuenta" (no son ni conciliado
ni diferencia). Cuentas de Tango sin extracto (Mercado Pago 106, tarjetas 98/110/111/113, créditos
hipotecarios 8/47): quedan afuera y se listan en el resumen como "cuentas de Tango sin extracto".

**Lo que se vio en una prueba con los datos reales de agosto** (hecha por Claude; los números acá
son inventados, los patrones son reales):

- **Uno a uno, importe exacto**: la mayoría de la plata. Transferencias a proveedores (O/P), sueldos
  (OPF), cobranzas por transferencia (REC), transferencias entre bancos propios (EXT, un renglón en
  cada banco), cuotas de préstamo (FPR). El banco acredita el mismo día o hasta 2-3 días hábiles
  después; a veces el banco tiene la fecha **antes** que Tango (se cargó tarde).
- **Varios a uno por día (depósitos y descuentos de cheques)**: el banco acredita **un renglón por
  cheque** ("CREDITO DESCUENTO DOCUMENTO", "ACREDITACION CHEQUE", "RECAUDACION ACREDITACION CHEQUE")
  y Tango carga **una boleta de depósito** (BDG/BDM) por el total. Ejemplo inventado: banco el 26/08
  con 9 créditos que suman 33.000.000,00; Tango el 26/08 con una BDG de 33.000.000,00.
- **Descuento de cheques en Macro, neto de intereses**: Tango carga la boleta **bruta** (BDM) y los
  intereses aparte (FPR con leyenda "INTERESES VTA..."); el banco acredita el **neto**. Ejemplo
  inventado: banco 06/08, 3 créditos que suman 35.000.000; Tango 06/08, 3 BDM por 35.900.000 y 3 FPR
  de intereses por −900.000. Neto = 35.000.000. Se empareja el bloque del día.
- **Uno a varios al revés**: una boleta de Tango del día 11 que el banco acredita el 12 en dos
  renglones.
- **Gastos e impuestos bancarios**: cientos de renglones chicos por mes (impuesto a los débitos y
  créditos, percepciones, comisiones). Tango casi no los carga, o los carga juntos. No tiene sentido
  emparejarlos uno por uno: se informan como total por cuenta.
- Hay renglones de Tango con **fecha imposible** (p. ej. año 2036 por un error de tipeo).

## Archivos permitidos

- `lector/cruce.py` (nuevo)
- `lector/pruebas/test_cruce.py` (nuevo, con datos inventados)
- `clientes/navar/perfil.json` (solo agregar el bloque `cruce`; no tocar nada más)

## Resultado esperado

### Uso

```
python lector/cruce.py --cliente navar --mes 2026-08 \
    --sheet "<export de la Sheet>.xlsx" \
    --tango "<carpeta o archivo del detalle de comprobantes de A>" \
    --salidas clientes/navar/privado/cruce
```

Deja en `--salidas`:
- `cruce_<AAAA-MM>.xlsx`
- `resumen_cruce_<AAAA-MM>.md`

No escribe en ningún otro lado, no sube nada a Drive y no toca la Sheet.

### Bloque `cruce` en `perfil.json`

Con `_ayuda` en criollo. Al menos: `empresa` ("A"), `cuentas` (la tabla de arriba: cuenta del
extracto → código de Tango), `cuit_propio`, `dias_antes` (cuántos días el banco puede tener la fecha
**antes** que Tango; default 3), `dias_despues` (cuántos días después; default 5), `tolerancia`
(pesos de diferencia aceptada; default 1), `categorias_gastos` (`["Impuestos", "Gastos Bancarios"]`),
`comprobantes_deposito` (`["BDM","BDG","BNA","BDC","BDF"]`), `leyendas_intereses_descuento`
(palabras que marcan un FPR como interés de descuento: `["INTERES", "VTA", "VALORES"]` o similar,
documentado). Que todo lo específico de NAVAR salga del perfil, no del código.

### Qué movimientos entran

- **Ventana de carga**: banco y Tango desde 10 días antes del mes hasta 10 días después (si hay),
  para que un movimiento del 31/08 pueda encontrar su par del 02/09 y al revés.
- **Qué se informa**: un movimiento del banco pertenece al mes por **su fecha de banco**; uno de
  Tango sin par, por **su fecha de Tango**. Un par conciliado se informa en el mes si cualquiera de
  las dos fechas cae en el mes (no duplicar: si se corre julio y agosto, un par cruzado aparece en
  los dos, está bien, pero dentro de un mismo informe aparece una vez).
- Cada renglón (de un lado o del otro) se usa **como máximo una vez**.

### Reglas, en este orden (cada par guarda el nombre de la regla que lo emparejó)

Siempre: misma cuenta (según la tabla), mismo signo, fecha del banco entre
`fecha Tango − dias_antes` y `fecha Tango + dias_despues`, diferencia de importe ≤ `tolerancia`.

1. **`exacto`** — uno a uno. Si hay varios candidatos, desempatar: primero el que tiene el **mismo
   CUIT** (CUIT del banco = CUIT del comprobante de Tango), después la fecha más cercana, después el
   primero. Para que el desempate no dependa del orden, recorrer primero los importes con un solo
   candidato de cada lado.
2. **`mismo CUIT`** — uno a varios en cualquier dirección: un renglón del banco con CUIT X contra
   varios renglones de Tango (de la misma cuenta, dentro de la ventana) cuyo comprobante tiene CUIT
   X y suman lo mismo; o varios del banco con CUIT X contra uno de Tango con CUIT X. Buscar la
   combinación entre como máximo 10 candidatos por lado; si hay más de una combinación que da,
   no emparejar (va a "Revisar").
3. **`bloque del día`** — depósitos y descuentos: todos los créditos del banco que quedan sin par en
   una cuenta y un día D, de categorías "Cheques" o "Descuento de Cheques", contra todos los
   renglones de Tango sin par de esa cuenta en **un** día T (T entre D − `dias_despues` y D +
   `dias_antes`) de comprobantes de depósito **más** los FPR de intereses de descuento de ese mismo
   día T. Si las sumas dan igual, se empareja el bloque entero. Probar T del más cercano al más
   lejano.
4. **`agrupado`** — último recurso, uno a varios sin CUIT: un renglón de Tango contra una
   combinación de renglones del banco **del mismo día** (misma cuenta, mismo signo, como máximo 12
   candidatos), o al revés. **Solo si la combinación es única.** Si hay más de una, no emparejar y
   listar en "Revisar". Estos pares se marcan para mirarlos con cuidado.

Lo que no entra en ninguna regla queda como diferencia.

### Clasificación final

- **Conciliado**: todos los pares/grupos, con la regla.
- **Solo en banco**, en dos bloques:
  - **Falta imputar en Tango**: todo lo que no es gasto ni impuesto. Con el CUIT y el nombre si el
    concepto los trae, y un **candidato probable** de Tango si existe (mismo importe fuera de la
    ventana de fechas, o mismo CUIT con otro importe), para ayudar a encontrarlo.
  - **Gastos e impuestos bancarios**: categorías de `categorias_gastos`. No van uno por uno: una fila
    por cuenta con cantidad y total, y al lado el total de los renglones de Tango de esa cuenta que
    quedaron sin par y parecen gastos (FPR/OPF sin CUIT de un tercero, o con CUIT del banco), para
    comparar los totales. El detalle igual va en su solapa.
- **Solo en Tango**:
  - **Sin movimiento en el banco**: renglones de cuenta de banco sin par. Si la fecha de Tango es
    posterior a la última fecha del extracto de esa cuenta menos `dias_despues`, marcar "todavía no
    acreditado (probable)"; si no, "no aparece en el banco: revisar".
  - **No pasa por el banco** (informativo, no es diferencia): de los recibos y órdenes de pago del
    mes, los renglones en "CAJA" (efectivo) y, en órdenes de pago, los renglones en "VALORES A
    DEPOSITAR" (cheques de terceros **endosados**). Una fila por comprobante con contraparte, CUIT,
    importe y cuenta. Los renglones en "VALORES A DEPOSITAR" de los recibos (cheques recibidos) van
    solo como total: llegan al banco después, con la boleta de depósito.
    Los nombres de esas cuentas ("CAJA", "VALORES A DEPOSITAR") se buscan por descripción, desde el
    perfil.
- **Revisar**: fechas imposibles (más de 60 días fuera de la ventana; se listan y no se emparejan),
  combinaciones ambiguas de las reglas 2 y 4, y renglones de Tango con importe cero o sin cuenta.
- **Internas de la misma cuenta**: las transferencias entre las dos cuentas de BBVA (ver Contexto).

### El Excel `cruce_<AAAA-MM>.xlsx`

Solapas, en este orden:

1. **Resumen**: una fila por cuenta del extracto con: movimientos del banco en el mes (cantidad,
   total entradas, total salidas), conciliado ($ y % del total movido, entradas y salidas por
   separado), solo en banco sin gastos, gastos e impuestos, solo en Tango, revisar. Una fila de
   total. Debajo: la **cuenta de control** (ver Comprobaciones) y las cuentas de Tango sin extracto.
2. **Conciliado**: una fila por renglón del banco y una por renglón de Tango, agrupadas por un
   número de par (`Par`), con: Par, Regla, Lado (Banco/Tango), Fecha, Cuenta, Importe, Concepto o
   leyenda, Comprobante de Tango, CUIT, Contraparte, Días de diferencia (fecha banco − fecha Tango).
3. **Solo en banco**: Fecha, Cuenta, Categoría, Concepto, Importe, CUIT, Contraparte (si el concepto la
   trae), Candidato probable en Tango, ID de la fila de Movimientos.
4. **Gastos bancarios**: el detalle de los gastos e impuestos sin par.
5. **Solo en Tango**: Fecha, Cuenta, Tipo, Comprobante, Contraparte, CUIT, Importe, Leyenda,
   Estado ("todavía no acreditado (probable)" / "no aparece en el banco: revisar").
6. **No pasa por banco**: efectivo y endosos (y el total de cheques recibidos).
7. **Revisar**.

Importes como número con formato `#,##0.00`, fechas como fecha `dd/mm/aaaa`, encabezados en
negrita, filtros activados, anchos razonables. Sin fórmulas.

### El resumen `resumen_cruce_<AAAA-MM>.md`

Corto, en criollo, para leer en 2 minutos: por cuenta, cuánto de lo que se movió en el banco está
conciliado; los 10 movimientos más grandes que faltan imputar en Tango; los 10 más grandes que Tango
tiene y el banco no; total de gastos bancarios sin imputar; cuántos pares salieron por cada regla;
y cualquier "Revisar". Montos con `_m` (formato `$X`).

### Código

- Funciones separadas y testeables: leer banco, leer Tango, emparejar (una función por regla),
  clasificar, escribir Excel, escribir resumen. El emparejado trabaja con listas de diccionarios y no
  sabe nada de archivos.
- Importes en centavos (enteros) para comparar sin errores de redondeo.
- Validación del CUIT con dígito verificador antes de usarlo para emparejar.
- Comentarios en criollo explicando el porqué de cada regla (sobre todo el neto de intereses y la
  ventana de fechas).
- Solo `openpyxl` y la biblioteca estándar (ya están). Nada de pandas.

## Comprobaciones

1. `python -m pytest lector/pruebas/test_cruce.py` pasa. Las pruebas usan **datos inventados** armados
   en el test (dos Excel chicos creados con openpyxl en una carpeta temporal: una Sheet con la solapa
   Movimientos y un detalle de comprobantes), y cubren como mínimo:
   - uno a uno exacto, con el banco 2 días después y con el banco 1 día antes;
   - desempate por CUIT entre dos candidatos del mismo importe;
   - mismo CUIT: una O/P contra dos transferencias del banco;
   - bloque del día con boleta bruta + intereses = neto del banco;
   - una boleta de Tango acreditada al día siguiente en dos renglones (agrupado);
   - ambigüedad (dos combinaciones posibles) → queda en Revisar, no se empareja;
   - transferencia entre dos cuentas propias (EXT en Tango con renglón en cada banco);
   - transferencia entre las dos cuentas de BBVA → "Internas de la misma cuenta";
   - gastos bancarios → a su bloque, no a "Falta imputar";
   - un recibo en CAJA y una O/P con VALORES A DEPOSITAR → "No pasa por banco";
   - fecha imposible → Revisar;
   - un movimiento del 31 del mes con su par el 2 del mes siguiente → conciliado;
   - filas de Movimientos con Origen "Manual" o de Caja AA → ignoradas.
2. **Cuenta de control**, calculada por el programa y escrita en el Resumen y en el `.md`: para cada
   cuenta, suma del banco en el mes = conciliado (lado banco, pares del mes) + solo en banco + gastos
   + internas + revisar (lado banco). Tiene que dar **exacto**; si no da, el programa lo dice en
   grande en el resumen y termina con código de salida distinto de cero.
3. Correr el programa sobre los datos inventados del test y abrir el Excel: que se lea bien.
4. **No se puede probar con datos reales** (los worktrees no tienen `privado/`): eso lo hace Claude
   después de revisar el diff, con agosto 2026.

## Qué hice

## Revisión
