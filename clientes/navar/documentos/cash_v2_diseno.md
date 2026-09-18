# Cash v2 — diseño (18/09/2026, a confirmar por Thomas)

Por qué: el cash armado hasta el 17/09 (solapa "CASH FLOW CONSOLIDADO" + tablero con
escenarios, retiro, capacidad, "qué patear") no se entiende. Thomas: "no puedo presentar
esto hasta que yo entienda qué calcula y cómo toma los datos". Se simplifica.

## Qué se arma

Una sola pantalla: solapa **Cash** en la Sheet. Todo por fórmula desde las listas
(Movimientos, Cuentas a Cobrar, Cuentas a Pagar, Cartera de Cheques, Deuda Bancaria,
Saldos Bancarios). Nadie tipea un número en la pantalla. El tablero web muestra lo mismo.

```
BANCOS HOY          por banco: saldo real · acuerdo · disponible        → total disponible
INGRESOS            Ayer (real) | Sem 1 | Sem 2 | Sem 3 | Sem 4
EGRESOS             Ayer (real) | Sem 1 | Sem 2 | Sem 3 | Sem 4
                    = saldo proyectado al cierre de cada semana
ATRASADO (stock)    proveedores · bancos · ARCA · cheques propios       → no suma en la curva
```

- El bloque "VENCIDO A LA FECHA" pasa abajo, como stock.
- "Saldo Inicial del Periodo" = suma de saldos reales de bancos (Saldos Bancarios), nunca editado.
- Saldos Bancarios suma dos columnas: **Acuerdo de descubierto** y **Disponible** (= saldo + acuerdo).

## Reglas de simplificación

1. Una fuente por renglón: banco, Tango, mapa de deuda o contador. Sin "agregado cash viejo", sin "Otros".
2. Real y estimado en columnas distintas, nunca sumados. "Ayer" es banco; las semanas son listas con fecha.
3. Sin proyecciones a mano. Se borra "Cobranza proyectada A/AA". El estimado es Tango por vencimiento,
   con el % de cumplimiento de los últimos 3 meses al lado.
4. Lo atrasado es un número, no un movimiento: no arranca la curva en rojo.
5. Del tablero se van escenarios, retiro, "qué patear", memoria. Quedan Cash, A cobrar, A pagar, Hallazgos.

## Ingresos (propuesta de Thomas, 18/09)

| Línea | Fuente |
|---|---|
| Cobranza real (ayer) | banco (Movimientos), con cliente por el cruce |
| Cobranza facturas A pendientes | Tango, por fecha de vencimiento |
| Cobranza facturas AA pendientes | Tango, por fecha de vencimiento |
| Cheques en cartera | Tango, por fecha de cobro, sin los endosados |
| Financiación | préstamos nuevos, descuento de cheques, venta de valores (suben en Deuda Bancaria) |
| Sin identificar | lo que no cruzó; tiene que valer $0 |

"Cobranza canchada" (¿cancelada?): pendiente de aclarar. Si es "facturas cobradas que se dan
de baja", es la salida del cruce, no una línea del cash.

Egresos, espejado: pagos reales ayer · proveedores pendientes (Tango, por vencimiento) · sueldos
y cargas · cuotas bancarias (cronograma) · impuestos (contador) · cheques propios (por fecha de
pago) · intereses y gastos bancarios.

## Cruces

| Cruce | Clave | Resultado |
|---|---|---|
| Cobranzas | recibo Tango (cliente, fecha, importe) ↔ acreditación banco (fecha, importe, CUIT) | factura pendiente con plata de ese CUIT = cobrada sin imputar → baja |
| Pagos | orden de pago Tango ↔ débito banco (CUIT proveedor / "CH. nº") | proveedor pagado; cheque propio en cartera con débito = pagado |
| Cuotas | cronograma Deuda Bancaria ↔ débito banco (banco, importe ±3%, fecha) | ya funciona (`lector/deuda_bancaria.py`) |

Lo que no cruza → "Sin identificar". Hoy: $570 M (Macro, 27 acreditaciones solo con número de operación).

## Ritmo diario

Cada mañana, dos archivos en Drive: movimientos de ayer del banco y recibos de ayer de Tango.
Importador → cruce → la pantalla muestra "Ayer". Hasta bots + token de Tango, exporta Priscilla.

## Pedido a Priscilla (18/09)

1. Los $570 M de Macro con solo número de operación: ¿cheques de clientes depositados o venta de valores (descuento)? Liquidaciones.
2. "N/C DEUD. PUBLICA-P.PREVIO" de Macro (~$20 M, dos por mes): qué es.
3. AgroNación: los $260 M "diferidos" (Envasando $245 M): ¿deuda con el banco o con el proveedor? ¿vencimiento?
4. Tango: export de recibos de cobranza y de órdenes de pago jun→sep; padrón de clientes y proveedores con CUIT.
5. Quién carga las cobranzas en Tango y cuándo.
6. Si marcan los cheques endosados en Tango.
7. Corrientes: límite del acuerdo en cta. cte. y estado de la negociación por las cuotas impagas.

## Dos solapas, no una (pedido de Thomas, 18/09 tarde)

- **Cash**: día por día. 7 días para atrás (real, del extracto) y 28 para adelante (estimado).
  Arriba los bancos, abajo lo atrasado. Es la pantalla principal.
- **Cash Semanal**: semana por semana, como el cash viejo de NAVAR: 4 semanas para atrás (real)
  y 12 para adelante (estimado). Mismos renglones; el saldo inicial sale de Cash.
Las arma `herramientas/crear_cash.gs` (menú finauto → Armar solapa Cash).

"Cobranza canchada" (aclarado): es una categoría del cash viejo ($18,75 M por mes): la venta de
yerba canchada (a granel, a industria: Las Marías). En Tango son facturas como las demás, así
que hoy está adentro de "Cobranza facturas A"; cuando se marquen los clientes de canchada en
el catálogo, se separa en su propio renglón.

## Orden de construcción

1. Solapa Cash en la Sheet (fórmulas sobre las listas) + columnas Acuerdo/Disponible en Saldos Bancarios.
2. Cruce de cobranzas y pagos (`lector/cruce.py`) cuando lleguen recibos, órdenes de pago y CUIT.
3. Tablero: mismos 4 bloques; se borra lo demás.
