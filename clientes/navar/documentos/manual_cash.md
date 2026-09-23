# El cash de NAVAR: qué es, cómo funciona, cómo se mantiene

Escrito el 20/09/2026 (estructura v5 del 22/09) para poder explicarlo sin leer código. Lo mismo, en
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
| Deuda Impositiva | LISTA: cada deuda con ARCA/DGR/municipio con vencimiento; 'Debito Automatico' = planes con débito en CBU | planilla de vencimientos impositivos → importación automática |

## 3. Cómo se lee una pantalla (las tres son iguales; es el esqueleto de un cash a mano)

```
Hoy · Último día con extracto        ← hasta ahí es REAL; desde el día siguiente, ESTIMADO
FECHAS                               ← la fila de abajo dice por columna: real · estimado · real + est.
1 · Bancos                           ← saldo real + descubierto acordado por banco (vacío hacia adelante)
Saldo inicial                        ← el cierre del período anterior: de acá se parte
2 · Ingresos                         ← un renglón por concepto: real atrás, estimado adelante (SIN préstamos)
3 · Egresos de la operación
Resultado de la operación            ← ingresos − egresos de la operación, antes de cualquier deuda
4 · Deuda que sale sí o sí           ← lo que el banco / ARCA debita solo: cuotas y tarjetas con débito
                                        automático, planes vigentes. Los préstamos tomados entran acá restando
SALDO AL CIERRE pagando solo lo que sale sí o sí      ← escenario 1 (como "sin pago a proveedores")
5 · Deuda que se paga por decisión   ← cuotas por transferencia, VEP, planes nuevos, regularización
SALDO AL CIERRE pagando toda la deuda                 ← escenario 2; es el que arrastra al período siguiente
Deuda pospuesta acumulada            ← en el escenario 1: lo que se fue dejando de pagar, sumado
Resultado después de la deuda        ← negativo = la deuda se come más de lo que la operación deja
Venció en el período y no se pagó    ← solo en lo real: facturas e impuestos vencidos en el período que siguen impagos
Resultado pagando lo que vencía      ← el número honesto de la operación
Descubierto acordado · usado · disponible   ← disponible = acordado − usado, banco por banco
Saldo disponible (2 escenarios)      ← positivos + descubierto disponible; negativo = falta aun con todo el descubierto
6 · Atrasado hoy                     ← lo vencido, por concepto; es un STOCK, no está en la curva; se paga por decisión
```

**Bancos (22/09)**: cada banco muestra el saldo real más su descubierto acordado, tomado del
mismo acuerdo del bloque de descubiertos. Verde si da más de cero; ámbar si da exactamente cero
(línea agotada, el cero se ve); rojo si da negativo. Un acuerdo vacío vale cero. Por ejemplo,
saldo −100 M y acuerdo 100 M = 0 ámbar. El **Total saldo real de bancos**, el **Saldo inicial** y
los **SALDO AL CIERRE** siguen usando solamente los saldos reales. Esos saldos por banco quedan
en filas auxiliares ocultas: el acuerdo no se suma como si fuera plata que ingresó. El bloque de
descubierto acordado/usado/disponible conserva su cálculo.

**Detalle de cuotas (22/09)**: el `+` al costado de **Cuotas y tarjetas con débito automático**
abre una fila por banco en las tres pantallas; arranca plegado. Conserva las mismas fechas,
estados y signos del total: extractos para lo real, cronograma para diario/semanal y Plan para
el mensual. El detalle no se vuelve a sumar al total de deuda. Los bancos salen de Deuda Bancaria,
sin lista escrita a mano. Si se agrega un banco nuevo hay que ejecutar **Armar solapa Cash** para
crear su fila; las filas ya creadas actualizan sus importes por fórmula. La aparición de nuevas
filas no está conectada al disparador de importación.

**Qué pasa con lo que vence y no se paga**: desde el día siguiente entra en "Atrasado hoy"
(stock). Debajo del total, **"Venció en ese período y sigue impago hoy"** lo muestra en la
columna de su vencimiento original: día, semana de lunes a domingo o mes. Por ejemplo, una
factura del 25/09 impaga al 30/09 queda en el 25/09, en la semana del 21/09 o en septiembre.
Es la deuda pendiente **hoy**, no una foto de lo que estaba pendiente en aquel momento.
Este detalle no entra en la curva ni modifica ningún saldo al cierre.

Lo anterior al primer período visible se muestra en **"Venció antes del primer período visible"**.
Si faltan extractos y la pantalla diaria queda atrás, lo vencido después del último período
visible se muestra aparte también. Esos dos importes en B son totales fuera de las columnas
fechadas. **Total repartido por vencimiento = suma del renglón por períodos + antes + después**;
debe coincidir con **Total atrasado a pagar**. El control muestra la diferencia redondeada a
centavos y debe decir **0,00**; si no, revisar fechas vacías, cero o inválidas en las listas.
El detalle muestra centavos para que el formato no esconda diferencias.

Se mantienen los mismos filtros del stock: proveedores A y AA pendientes sin `REVISAR`,
cuotas bancarias `Pendiente`, impuestos distintos de `Pagado` y cheques propios `En Cartera`.
El vencido a cobrar es informativo y no suma. Una deuda de 2007 admitida por esos filtros va a
"antes"; si es de proveedores marcada `REVISAR`, sigue fuera tanto del total como del detalle.
No se cambia la decisión sobre deuda vieja con este reparto.

Cuando la lista registra el pago (o la factura sale de la nueva foto de pendientes), desaparece
del total y del detalle por fórmula, sin borrar nada en estas pantallas. No basta que el pago
figure en el extracto si la lista sigue desactualizada. Para pagar atrasado por decisión se usa
Plan ("Regularización"); eso aparece como cuota en el mensual. La fila preexistente "Venció en
el período y no se pagó" sigue siendo solo proveedores e impuestos y solo en lo real: no es el
total de este nuevo detalle. "Deuda pospuesta acumulada" conserva su lectura del escenario 1.

**Qué es "débito automático"**: la columna `Debito Automatico` de Deuda Bancaria y Deuda Impositiva.
Regla: préstamos, tarjetas e hipotecas = Sí (el banco lo debita si hay fondos); planes de pago
vigentes de ARCA = Sí (débito en CBU); el resto de impuestos = No (VEP). Se corrige por producto en
`catalogo.json → debito_automatico`.

## 4. Cada renglón: real y estimado

| Renglón | REAL (extracto) | ESTIMADO |
|---|---|---|
| Cobranza acreditada | transferencias y depósitos de clientes | facturas A que vencen (Tango) · mensual: promedio × inflación |
| Cobranza AA (efectivo) | recibos de AA en la tesorería de Tango (Origen Tango AA) | facturas AA que vencen |
| Cheques de clientes | depositados + descontados (venta de valores) | cheques en cartera por fecha de cobro · mensual: promedio |
| Sin identificar | lo que el banco acreditó sin decir qué es | tiene que ser 0 |
| Proveedores A | pagos a proveedores | facturas A que vencen · mensual: el mayor entre Tango y promedio |
| Proveedores AA | órdenes de pago de AA en la tesorería de Tango (Origen Tango AA) | facturas AA que vencen |
| Sueldos y cargas | Macro | proyectado con fecha · mensual: promedio |
| Impuestos corrientes | IVA, cargas, retenciones pagadas | mensual: promedio |
| Cheques propios | debitados | en cartera por fecha de pago |
| Intereses y gastos bancarios | extracto | promedio 90 días |
| Otros (tarjeta, honorarios) | extracto | proyectado con fecha · la cosecha no se proyecta: en 2027 compran canchada (va por Proveedores) |
| Cuotas y tarjetas con débito automático | cuotas debitadas | cronograma (Debito Automatico = Si) · mensual: Plan |
| Planes de ARCA con débito automático | — | Deuda Impositiva (Si) · mensual: Plan |
| Préstamos tomados | préstamos acreditados, restando | no se proyecta |
| Cuotas que se pagan por decisión | — | cronograma (No) · mensual: Plan |
| Impuestos por VEP y planes nuevos | — | Deuda Impositiva (No) · mensual: Plan |
| Regularización de atrasado | — | mensual: Plan |

El detalle **Venció en ese período y sigue impago hoy** no es real ni estimado de caja: es stock
actual repartido por vencimiento original. Incluye también bancos y cheques propios, conserva
los filtros del bloque 6 y no usa promedios, inflación ni cuotas decididas en Plan.

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
| 1 | la empresa o el bot | deja el archivo nuevo en SU carpeta de Drive | `NAVAR - Datos / Bancos/<banco>` · `Cuentas a cobrar` · `Cuentas a pagar` · `Cheques` · `Deuda bancaria` · `Impuestos` |
| 2 | la notebook de la empresa (**vigilante**, cada 15 min) | ve el archivo nuevo y corre el lector que corresponde; deja el `para_pegar_*.xlsx` en `_para la Sheet`; si una lista se achica de golpe, lo retiene | `herramientas/vigilante.py` · log en `privado/vigilante.log` |
| 3 | la Sheet (**disparador**, cada hora, Apps Script) | ve el `para_pegar` nuevo y lo importa; pisa lo que ese lector cargó antes, no toca fórmulas ni lo cargado a mano | solapa **Registro**: una fila por importación (o el error) |
| 4 | las pantallas | recalculan solas: B3 avanza, lo real reemplaza lo estimado, la cobranza que entró sale del "a cobrar" | Cash · Cash Semanal · Cash Mensual |
| cada mañana: el aviso | la Sheet (cerca de las 09:00 de Buenos Aires, una vez instalado) | primero recuerda qué falta subir por banco y por empresa; después resume el circuito | `herramientas/aviso_diario.gs` → mail de la empresa |
| a mano | quien hace el arqueo de caja | una fila por arqueo en Saldos Bancarios: fecha, Varios, AA, saldo, Manual | Saldos Bancarios |
| a mano | la dirección | las decisiones: pagar / refinanciar / posponer, gracia, cuotas, tasa | Plan |

El mail empieza con **Qué falta subir hoy**: un renglón por banco atrasado (la lista sale de
Saldos Bancarios), y por cada export de cobranzas, pagos y cheques de A y AA. Muestra la fecha
requerida y la última disponible; si no hay fecha, lo dice sin inventar desde cuándo falta.
Los bancos y el arqueo manual de caja AA deben cubrir el último día hábil cerrado: el lunes
alcanza con el viernes. Hábil significa lunes a viernes; todavía no contempla feriados.
Los seis exports y la tesorería AA deben tener **fecha de hoy en el nombre**; subir de nuevo un
archivo viejo no lo pone al día. Cheques toma el más nuevo entre propios y terceros por empresa
(según el control de seis combinaciones pedido; no certifica que ambos subtipos estén completos).
La tesorería se verifica en su carpeta de Drive; el arqueo, por una fila Manual de AA en
Saldos Bancarios con banco Varios, (varios) o Caja. No se deduce un arqueo de un movimiento de caja.

Después aparecen las alertas y un resumen de hasta cinco líneas por sección de lo recibido,
procesado e importado **desde el cierre anterior**, no de las últimas 24 horas: desde las 00:00
de hoy, o desde el sábado a las 00:00 si es lunes. Los pendientes viejos siguen alertando.
Si no se pudo leer una fuente, se informa sin declararla al día. “Está todo subido al día de hoy”
solo habla de las fuentes controladas: las alertas posteriores pueden indicar que falta procesar
o importar. No certifica los importes ni la conciliación del cash.

Si el vigilante no procesó, revisar la notebook y `NAVAR - Datos/_para la Sheet/vigilante.log`;
si la Sheet no importó, usar finauto → Importar lo nuevo ahora. Si hay un retenido, revisar el
export antes de publicarlo; ante errores de lectura o importación, revisar Registro y pedir ayuda
a finauto. Primero revisar `avisoDiarioPrueba()` (no manda mail); después instalar con
`instalarAvisoDiario()`, desde una sola cuenta. Queda programado a las **09:00 de Buenos Aires**;
Google lo ejecuta cerca de esa hora, con un margen de 15 minutos. Falta verificarlo e instalarlo
en la Sheet; este cambio de código por sí solo no crea el disparador.

### Importación y filtros (cambio preparado el 22/09, pendiente de probar en la Sheet)

Antes de cargar datos, el importador revisa las solapas del lector: si falta alguna, si no
puede consultar las vistas de filtro o si encuentra una vista guardada, frena con **ERROR**.
Para instalar esta versión, finauto debe habilitar **Google Sheets API** además de Drive API
en Servicios de Apps Script. Una vista guardada se debe eliminar en Datos → Vistas de filtro;
solo cerrarla no alcanza. Después: finauto → Importar lo nuevo ahora.

El filtro común se quita automáticamente y las filas ocultas se muestran antes de cargar.
Las listas quedan visibles: no se vuelve a ocultar por número de fila porque, al cambiar la
lista, esa posición puede corresponder a otro movimiento. Tampoco se repone el rango viejo
del filtro, que podría dejar datos nuevos afuera. Se puede volver a filtrar al terminar.

Después de escribir, se releen todas las celdas de datos cargadas, se comparan con lo preparado
(incluidas fechas, importes y filas manuales), se revisa lo borrado abajo y la cantidad de filas.
Si hay diferencia, Registro dice **ERROR / VERIFICACION_NO_CUADRA**, con solapa, fila y columna:
**no usar el cash para una reunión hasta revisar y reimportar**. El aviso diario destaca ese
fallo dentro de las últimas 24 horas. Los botones manuales también dejan Registro.

Este control compara contra la Sheet temporal convertida del `para_pegar`, no contra los
seriales originales del Excel; no valida la conversión ni las fórmulas del cash. No hay
reversión automática: si falla después de empezar, puede quedar una carga parcial. El candado
evita dos importadores simultáneos, pero no impide que una persona edite durante la carga.
Las vistas temporales del navegador y el comportamiento real de Google quedan por validar
en la prueba manual; no se afirma que la API muestre ese estado de cada navegador.

### Las carpetas de Drive (`NAVAR - Datos`): una por export

Cada bot o persona deja su archivo en SU carpeta y nada más; el vigilante sabe qué hacer con cada una.

| Carpeta | Qué se deja | Nombre del archivo | A qué solapa va |
|---|---|---|---|
| `Bancos/<banco>` | el extracto (PDF) o el Excel del home banking. Se acumulan: cada mes se agrega el nuevo, nada se borra | como venga del banco | Saldos Bancarios · Movimientos |
| `Cuentas a cobrar` | Tango Live: composición de saldos de clientes, por empresa, un archivo por día | `A cobranzas 2026-09-22.xlsx` · `AA cobranzas 2026-09-22.xlsx` | Cuentas a Cobrar |
| `Cuentas a pagar` | Tango Live: composición de saldos de proveedores | `A pagos 2026-09-22.xlsx` · `AA pagos ...` | Cuentas a Pagar |
| `Cheques` | Tango Live: cheques de terceros en cartera y cheques propios emitidos | `A cheques terceros 2026-09-22.xlsx` · `A cheques propios 2026-09-22.xlsx` · `AA cheques terceros ...` | Cartera de Cheques |
| `Deuda bancaria` | el mapa de deuda cuando cambie | `Bancos_Navar.xlsx` | Deuda Bancaria |
| `Impuestos` | la planilla de vencimientos impositivos cuando cambie | `Control Vencimiento Impuestos.xlsx` | Deuda Impositiva |
| `Tesorería AA` | Tango Live: movimientos de tesorería de NAVAR SA Otros (recibos, órdenes de pago, otros), un archivo por día | `AA movimientos tesoreria 2026-09-22.xlsx` | Movimientos (Origen Tango AA) |
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

## 7. Qué se corrigió el 19–22/09

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

- **22/09 — elección del export de cheques**: el lector elegía el último nombre alfabéticamente;
  con mayúsculas distintas terminaba usando el 16/09 aunque hubiera fotos del 21 y 22/09.
  Ahora manda la fecha del nombre del export. Verificación contra Drive: las 66 filas generadas
  coinciden con el origen, incluidas las seis de la evidencia. El cheque propio de $10.872.165,02
  entra como egreso el 25/09 sin REVISAR. **El incidente de fechas alteradas en la Sheet sigue
  abierto**: no se reprodujo esa alteración con el lector anterior y no se verificó la importación
  en Google Sheets. La selección vieja era un error comprobado, pero no explica por sí sola
  las fechas equivocadas que ya estaban cargadas.

- **22/09 — defensa del importador ante filtros (pendiente de validación en Google)**:
  se quitan filtros comunes y filas ocultas, se bloquean vistas guardadas y consultas fallidas,
  y se compara toda la carga después de escribir. Los errores indican la solapa y no se marca
  el archivo como importado cuando no cuadra. Esto agrega prevención y detección; no demuestra
  por sí solo la causa histórica de las fechas alteradas ni corrige cargas anteriores.
