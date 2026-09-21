# El cash de NAVAR: qué es, cómo funciona, cómo se mantiene

Escrito el 20/09/2026 para que Thomas pueda explicarlo sin leer código. Lo mismo, en
tablas cortas, está en la solapa **Instrucciones** de la Sheet.

## 1. La idea en una frase

**Los datos viven en listas; las pantallas son fórmula.** Nadie tipea un número en una
pantalla. Si un número está mal, está mal en una lista: se corrige ahí y las pantallas
cambian solas. Eso es lo que hace que se pueda mantener y automatizar.

## 2. Las solapas

| Solapa | Qué es | De dónde sale |
|---|---|---|
| **Cash** | Día por día: 7 días de extracto (real) + 28 adelante (estimado) | fórmula |
| **Cash Semanal** | Lunes a domingo: 4 semanas cerradas (real) + la actual + 12 adelante | fórmula |
| **Cash Mensual** | 3 meses cerrados (real) + el actual + 6 adelante; inflación editable (B4) | fórmula + Plan |
| **Plan** | Una fila por deuda con la decisión: pagar como está / refinanciar / posponer | Deuda Bancaria + Deuda Impositiva + vencido |
| Movimientos | LISTA: cada movimiento real de banco, clasificado | extractos → Importar Bancos |
| Saldos Bancarios | LISTA: saldo al cierre de cada día por cuenta | extractos → Importar Bancos |
| Cuentas a Cobrar / a Pagar | LISTA: facturas pendientes con vencimiento | Tango → Importar Tango |
| Cartera de Cheques | LISTA: cheques de terceros en cartera y propios entregados | Tango → Importar Tango |
| Deuda Bancaria | LISTA: cada línea con su capital + cronograma de cuotas | mapa de deuda → Importar Deuda |
| Deuda Impositiva | LISTA: cada deuda con ARCA/DGR/municipio con vencimiento | planilla de Celia → Importar Impuestos |

## 3. Cómo se lee una pantalla (las tres son iguales)

```
Hoy · Último día con extracto        ← hasta ahí es REAL; desde el día siguiente, ESTIMADO
FECHAS                               ← la fila de abajo dice por columna: real · estimado · real + est.
1 · Bancos                           ← saldo real de cada banco al cierre (vacío hacia adelante)
2 · Ingresos                         ← un renglón por concepto: real atrás, estimado adelante
3 · Egresos de la operación
4 · Deuda                            ← cuotas, planes de ARCA, regularización (en el mensual, según Plan)
Resultado de la operación            ← ingresos − egresos de la operación = capacidad de pago (~$100–150 M/mes)
Resultado después de la deuda        ← negativo = la deuda se come más de lo que la operación deja
Saldo de bancos al cierre            ← real hasta el último extracto; después cierre anterior + ingresos − egresos
Descubiertos acordados               ← $160 M
Saldo disponible                     ← cierre + descubiertos; negativo = hay que elegir qué no pagar
5 · Atrasado hoy                     ← lo vencido, por concepto; NO está en la curva; se paga por decisión en Plan
```

## 4. Cada renglón: real y estimado

| Renglón | REAL (extracto) | ESTIMADO |
|---|---|---|
| Cobranza acreditada | transferencias y depósitos de clientes | facturas A que vencen (Tango) · mensual: promedio × inflación |
| Cobranza AA (efectivo) | — (AA no pasa por banco) | facturas AA que vencen |
| Cheques de clientes | depositados + descontados (venta de valores) | cheques en cartera por fecha de cobro · mensual: promedio |
| Préstamos nuevos | préstamos acreditados | 0: es una decisión |
| Sin identificar | lo que el banco acreditó sin decir qué es | tiene que ser 0 |
| Proveedores A | pagos a proveedores | facturas A que vencen · mensual: el mayor entre Tango y promedio |
| Proveedores AA | — | facturas AA que vencen |
| Sueldos y cargas | Macro | proyectado con fecha · mensual: promedio |
| Impuestos corrientes | IVA, cargas, retenciones pagadas | mensual: promedio |
| Cheques propios | debitados | en cartera por fecha de pago |
| Intereses y gastos bancarios | extracto | promedio 90 días |
| Otros (tarjeta, honorarios) | extracto | proyectado con fecha · la cosecha no se proyecta: en 2027 compran canchada (va por Proveedores) |
| Cuotas bancarias y tarjeta | cuotas debitadas | cronograma · mensual: Plan |
| Impuestos: deuda y planes | — | Deuda Impositiva · mensual: Plan |
| Regularización de atrasado | — | mensual: Plan |

## 5. Cómo impacta cada movimiento

| Pasa esto | Dónde entra | Qué cambia |
|---|---|---|
| Un cliente paga por transferencia | Movimientos (real) · Tango: recibo, la factura sale de Cuentas a Cobrar | sube el saldo; baja lo estimado a cobrar y el vencido a cobrar |
| Un cliente paga con cheque | Tango: recibo + Cartera de Cheques | sube "cheques en cartera" (estimado); el saldo real no cambia hasta que se deposita o descuenta |
| Se descuenta un cheque | Movimientos (Descuento de Cheques) · sale de la cartera | sube el saldo; el interés va a gastos bancarios |
| Se paga a un proveedor | Movimientos (Proveedores) · Tango: orden de pago | baja el saldo; baja lo estimado y lo vencido a pagar |
| Se entrega un cheque propio | Cartera de Cheques (propio, fecha de pago) | aparece en "cheques propios" estimado; al debitarse pasa a real |
| **Se paga una cuota** | Movimientos (Prestamo egreso) · Deuda Bancaria: cuota → Pagado, capital baja | baja el saldo; baja "cuotas" estimado; **baja la deuda total en Plan**; baja "cuotas impagas" si estaba vencida |
| **Entra un préstamo** | Movimientos (Prestamo ingreso) · Deuda Bancaria: línea nueva + cronograma | sube el saldo hoy; **suben las cuotas futuras y la deuda total** |
| Se paga un impuesto | Movimientos (Impuestos) · Deuda Impositiva: fila → Pagado | baja el saldo; baja lo estimado y lo vencido de impuestos |
| Se firma un plan con ARCA | Deuda Impositiva: deuda → Pagado, se cargan las cuotas · o en Plan: "Refinanciar" | baja el stock vencido; aparecen cuotas mensuales |
| Se refinancia un préstamo | Deuda Bancaria: cronograma nuevo · mientras tanto, Plan: "Refinanciar" | cambian las cuotas futuras |
| Se usa más descubierto | el saldo del banco queda más negativo | baja el saldo y el disponible |
| Transferencia entre cuentas propias | Movimientos, INTERNO | no cambia nada |

## 6. Cómo se actualiza (desde el 20/09: sola)

| Paso | Quién | Qué hace | Dónde |
|---|---|---|---|
| 1 | NAVAR (Karina / Priscilla) | deja el archivo nuevo en Drive: extracto del banco, exports de Tango Live (cobranzas, pagos, cheques), planilla de impuestos de Celia, mapa de deuda | `NAVAR - Datos / Bancos/<banco>` · `Tango/<fecha>` · `Impuestos` · `Deuda` |
| 2 | la Mac de Thomas (**vigilante**, cada 15 min, launchd) | ve el archivo nuevo y corre el lector que corresponde; el lector deja el `para_pegar_*.xlsx` al lado | `herramientas/vigilante.py` · log en `privado/vigilante.log` |
| 3 | la Sheet (**disparador**, cada hora, Apps Script) | ve el `para_pegar` nuevo y lo importa; pisa lo que ese lector cargó antes, no toca fórmulas ni lo cargado a mano | solapa **Registro**: una fila por importación (o el error) |
| 4 | las pantallas | recalculan solas: B3 avanza, lo real reemplaza lo estimado, la cobranza que entró sale del "a cobrar" | Cash · Cash Semanal · Cash Mensual |
| a mano | quien cierra la caja AA | una fila por día en Saldos Bancarios: fecha, (varios), saldo | Saldos Bancarios |
| a mano | Priscilla + Thomas | las decisiones: pagar / refinanciar / posponer, gracia, cuotas, tasa | Plan |

### Las carpetas de Drive (`NAVAR - Datos`): una por export

Cada bot o persona deja su archivo en SU carpeta y nada más; el vigilante sabe qué hacer con cada una.

| Carpeta | Qué se deja | Nombre del archivo | A qué solapa va |
|---|---|---|---|
| `Bancos/<banco>` | el extracto (PDF) o el Excel del home banking. Se acumulan: cada mes se agrega el nuevo, nada se borra | como venga del banco | Saldos Bancarios · Movimientos |
| `Cuentas a cobrar` | Tango Live: composición de saldos de clientes, por empresa, un archivo por día | `A cobranzas 2026-09-22.xlsx` · `AA cobranzas 2026-09-22.xlsx` | Cuentas a Cobrar |
| `Cuentas a pagar` | Tango Live: composición de saldos de proveedores | `A pagos 2026-09-22.xlsx` · `AA pagos ...` | Cuentas a Pagar |
| `Cheques` | Tango Live: cheques de terceros en cartera y cheques propios emitidos | `A cheques terceros 2026-09-22.xlsx` · `A cheques propios 2026-09-22.xlsx` · `AA cheques terceros ...` | Cartera de Cheques |
| `Deuda bancaria` | el mapa de deuda cuando cambie | `Bancos_Navar.xlsx` | Deuda Bancaria |
| `Impuestos` | la planilla de Celia cuando cambie | `Control Vencimiento Impuestos.xlsx` | Deuda Impositiva |
| `_para la Sheet` | NO TOCAR: lo que generan los lectores; de acá lo levanta el disparador | `para_pegar_*.xlsx` | — |

Cada export de Tango es la **foto completa** de ese día (no "lo nuevo desde ayer"): se carga el más
nuevo de cada lista; los anteriores quedan como historia (sirven después para la bitácora: qué
estaba pendiente cada día). El nombre importa: primera palabra = empresa (A / AA), después qué es,
después la fecha. Los cheques en cartera **no salen del banco** (el banco no sabe qué cheques hay
en el cajón): salen de Tango. Del banco salen los depositados, descontados y debitados, que ya
vienen en el extracto.

Atajos del menú finauto: "Importar lo nuevo ahora" (lo mismo que el disparador, sin esperar),
"Armar solapa Cash" (solo si cambió la estructura; Plan no se toca). Para el PDF: bajar la Sheet
como Excel a `privado/NAVAR - Cash Flow (export Sheets <fecha>).xlsx` y correr
`python clientes/navar/herramientas/informe_situacion.py`.

**Después**: bots de banco + token de Tango Live en la notebook de NAVAR hacen el paso 1 solos
cada mañana. Nadie sube nada: el cash amanece al día.

## 7. Qué se corrigió el 19–20/09

- Las fórmulas se escribían con `,` y la planilla (en español) usa `;` → todo daba #ERROR!. Ahora el script prueba y reescribe solo.
- Los Excel del home banking (BBVA, Macro) vienen del más nuevo al más viejo → el saldo "al cierre del día" era el de la primera operación (Macro 15/09 daba +$71 M). Se ordenan cronológicamente.
- Las filas migradas del cash viejo (Origen "Manual", Estado "Real") se sumaban con el extracto → julio daba $1.225 M de ingresos en lugar de $757 M. Lo real es solo "Extracto".
- Las semanas arrancaban en el día de hoy → la semana en curso quedaba partida. Ahora van de lunes a domingo.
- Había dos renglones por concepto (uno real, uno estimado) con la mitad vacía → un renglón por concepto: real atrás, estimado adelante.
- Los días entre el último extracto y hoy se mostraban como "real" arrastrado → ahora lo real termina en el último extracto y desde el día siguiente es estimado.
- Faltaba ver los ~$150 M que deja la operación → filas "Resultado de la operación" y "Resultado después de la deuda".
- La columna "Fuente" hacía ilegible cada pantalla → se fue; el detalle está en Instrucciones.
- La solapa Plan arrancaba con "pagar todo como está" → arranca con la propuesta del PDF (Corrientes y Galicia a refinanciar, SICORE a plan, municipal a posponer), con el "por qué" en cada fila.
- La solapa Instrucciones describía la planilla vieja → rehecha en tablas.
