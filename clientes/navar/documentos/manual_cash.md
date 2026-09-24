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
1 · Bancos                           ← saldo por cuenta + fecha; margen con acuerdo por banco (vacío en el futuro)
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

**Bancos (23/09, arrastre preparado para revisión)**: cada cuenta tiene dos renglones:
**saldo sin acuerdo** y, justo debajo de cada importe, **fecha y estado**. La cuenta se distingue
por banco, empresa y número. La última foto se busca hasta el cierre del período pasado o hasta
hoy en el período actual. Si es anterior a ese corte, ambos renglones quedan **grises y en
itálica**, con **“ARRASTRADO · al dd/mm/aaaa”**: no es plata confirmada para ese día. Si coincide,
dice **“Confirmado · al dd/mm/aaaa”** (confirmado por la foto cargada, no por una conciliación).
Cero se ve como 0; un negativo conserva el signo. Sin foto anterior dice **“Sin saldo previo”**,
sin traer datos de un día posterior. Una última foto duplicada, vacía o con texto en el importe
dice **“Revisar saldo”**, sin presentarla como cero.

Después aparece el **margen con acuerdo por banco**: suma los saldos de sus cuentas y agrega
el acuerdo una sola vez. Si alguna cuenta arrastra, el margen también queda gris e itálico.
Con todas las fotos al corte: verde si queda margen, ámbar si da cero y rojo si está excedido.
Un acuerdo vacío vale cero; saldo −100 M y acuerdo 100 M = 0. Si falta un saldo válido, dice
“Revisar cuentas”. Los períodos que empiezan después de hoy quedan vacíos en este detalle.
La semana y el mes en curso muestran la foto hasta hoy, no hasta su cierre futuro.

Junto al **Total saldo real de bancos**, un aviso por columna cuenta las cuentas con fecha
arrastrada y muestra la más vieja; también cuenta las que no tienen saldo previo. Cuenta
cuentas, no bancos; incluye la caja manual. **El detalle es informativo: el total preexistente,
Saldo inicial, SALDO AL CIERRE y el neteo del descubierto conservan exactamente su cálculo y
su corte de extracto.** Las filas auxiliares originales siguen ocultas y alimentan esos
cálculos. Por eso, después del último extracto el detalle puede mostrar saldos arrastrados
mientras el total real sigue vacío y el cierre ya es una proyección. No sumar el detalle como
si fuera una nueva base del cash. Si el detalle por cuenta difiere del total anterior, revisar
las fuentes; esta mejora de presentación no corrige el cálculo anterior.

Los importes, fechas, leyendas y colores se actualizan por fórmula. Al aparecer una **cuenta
nueva**, ejecutar **Armar solapa Cash** para crear sus filas. La fecha viene de Saldos Bancarios
(contenido del extracto), nunca del nombre del archivo. La fila general “real / estimado” sigue
hablando de los flujos: la confirmación de cada cuenta se lee debajo de su propio importe.

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

**Caja AA (planilla y tablero):** último arqueo Manual + suma con signo de Movimientos con Origen `Tango AA*` y Estado `Real`, posteriores al arqueo y hasta hoy; un nuevo arqueo reemplaza la base y, si falta, dice **sin arqueo**.

## 4. Cada renglón: real y estimado

| Renglón | REAL (extracto) | ESTIMADO |
|---|---|---|
| Saldo por cuenta (detalle informativo) | última foto hasta el corte; fecha visible, gris e itálica si arrastra | vacío si el período empieza después de hoy; no modifica la proyección |
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
| 2 | la notebook de la empresa (**vigilante**, cada 15 min) | ve el archivo nuevo y corre el lector que corresponde; deja el `para_pegar_*.xlsx` en `_para la Sheet`; si una lista se achica o crece de golpe, lo retiene | `herramientas/vigilante.py` · log en `privado/vigilante.log` |
| 3 | la Sheet (**disparador**, cada hora, Apps Script) | ve el `para_pegar` nuevo y lo importa; pisa lo que ese lector cargó antes, no toca fórmulas ni lo cargado a mano | solapa **Registro**: una fila por importación (o el error) |
| 4 | las pantallas | recalculan solas: B3 avanza, lo real reemplaza lo estimado, la cobranza que entró sale del "a cobrar" | Cash · Cash Semanal · Cash Mensual |
| cada mañana: el aviso | la Sheet (cerca de las 09:00 de Buenos Aires, una vez instalado) | prioriza una señal de vida atrasada o no verificable; recuerda qué falta subir y resume el circuito | `herramientas/aviso_diario.gs` → mail de la empresa |
| a mano | quien hace el arqueo de caja | una fila por arqueo en Saldos Bancarios: fecha, Varios, AA, saldo, Manual | Saldos Bancarios |
| a mano | la dirección | las decisiones: pagar / refinanciar / posponer, gracia, cuotas, tasa | Plan |

Si la señal de vida está fresca, el mail empieza con **Qué falta subir hoy**: un renglón por banco atrasado (la lista sale de
Saldos Bancarios, del banco que acompaña a `Extracto` en Origen), y por cada export de cobranzas, pagos y cheques de A y AA. Muestra la fecha
requerida y la última disponible; para cada banco también dice cuántos días corridos tiene
el último extracto. Reconoce tanto `Extracto BANCO` como el formato viejo `Extracto` (en ese
caso usa la columna Banco). Si no hay fecha, lo dice sin inventar desde cuándo falta.
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

### Señal de vida del vigilante (tarea 16, preparada para revisión)

Cada pasada reemplaza `_para la Sheet/vigilante_ultima_pasada.txt` con una sola fecha UTC
(por ejemplo `2026-09-24T11:45:00+00:00`). No acumula líneas en el log. Se escribe al comenzar
la revisión, antes de leer el estado o ejecutar lectores: también queda si no hay entradas,
si falla un lector o si se usa `--simular`. La simulación actualiza esta señal, aunque no corre
lectores. `--hoy` no modifica la marca: siempre usa el reloj real de la máquina.

El aviso muestra la hora en Buenos Aires. Si pasaron **más de 60 minutos**, abre con
**Estado del vigilante**, antes de los faltantes, y pone el corte como primera alerta.
Con exactamente 60 minutos aún se considera fresca. Para hoy y ayer usa esas palabras;
para días anteriores muestra la fecha completa. Una marca fresca confirma que el vigilante
arrancó recientemente, **no que terminó ni que los lectores salieron bien**: siguen valiendo
las alertas del log y de Registro.

Si falta la marca, está mal escrita, hay duplicados, no se puede leer o indica una hora futura,
el mail dice que no se puede verificar la señal; no inventa una última pasada. Una marca vieja
puede deberse a que no corre la notebook **o a una sincronización de Drive detenida**. Revisar
ambas cosas. Si Drive no está montado o no permite escribir, no habrá una marca nueva en la
nube; una marca local por sí sola no prueba que Google la haya recibido.

En el Programador de tareas de Windows, revisar la última ejecución, el resultado y si está
seleccionado **“Ejecutar solo cuando el usuario haya iniciado sesión”**. Comprobar qué pasa
al desconectar escritorio remoto, bloquear la sesión y cerrar sesión: no asumir que son lo
mismo ni que explican por sí solos el corte. Revisar además suspensión de la notebook y que
Drive para escritorio siga disponible en la sesión que ejecuta la tarea. No cambiar esa opción
sin probar el acceso a Drive desde la sesión resultante.

Para ponerlo en uso hay que actualizar `vigilante.py` en la notebook y `aviso_diario.gs` en
Apps Script. Verificar primero que la marca avance localmente y en Drive tras una pasada sin
entradas; después revisar `avisoDiarioPrueba()` sin mandar mail. Repetir desconectando escritorio
remoto y revisar las ejecuciones siguientes. **Estas comprobaciones en la notebook y Google
siguen pendientes**; las pruebas locales no certifican la instalación ni explican el corte real.

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

- **23/09 — cheques: defensa preparada para revisión, todavía sin instalar**:
  terceros entra solo con `Cód. estado = C` o `Estado = En Cartera`, sin importar mayúsculas,
  acentos ni espacios. Si ambos tienen valor, ambos deben coincidir: una contradicción queda
  afuera. Sin esas columnas, o con ambos valores vacíos, no se adivina; el resumen avisa y cuenta
  lo descartado por motivo. No se usa Subestado para reemplazar Estado.
  Propios requiere `Estado = Al Cobro` (pendiente de débito según Tango); el export revisado
  trae ese texto y no trae código de estado. No se inventa un código equivalente. Se mantiene
  el descarte de fechas de más de 30 días atrás y la marca `REVISAR` para las vencidas recientes.
  El resumen también cuenta filas sin fecha o importe.
  El vigilante conserva el control de achicamiento y retiene crecimientos **mayores al triple
  y con más de 100 filas extra**, incluso desde una solapa vacía. Así una lista chica puede
  crecer normalmente: 332 → 337 pasa; 1.694 → 75.611 se retiene con su resumen en `_retenido`.
  Sin publicación anterior no hay comparación: el filtro del lector sigue funcionando.
  La prueba real descartó 75.579 cheques aplicados, rechazados o anulados del export histórico.
  Los dos exports no representan la misma cartera: los resultados completos y esa limitación
  están documentados en `tareas/09-cheques-solo-en-cartera.md`. Este cambio no concilia Tango
  contra el banco ni corrige la Sheet ya cargada.

## 8. Modelo Nuevo: proyección desde supuestos (tarea 10, pendiente de probar en Google)

**Cash, Cash Semanal y Cash Mensual siguen como están.** Proyectan lo que viene según lo que
vino y las listas vigentes: sirven para manejar la próxima semana. **Modelo Nuevo** arma la
operación nueva desde kilos, precios, puestos y plazos: sirve para decidir y negociar. No fuerza
un resultado positivo ni negativo; muestra lo que dan los datos, o **—** cuando no se sabe.

### Cómo se arma y qué se carga

En Apps Script, actualizar `crear_cash.gs` y ejecutar **`armarModeloNuevo()`**. Crea **Supuestos**
y **Modelo Nuevo**; no corre `armarCash()`, no modifica las tres pantallas actuales, Plan ni
Instrucciones. No se agregó un botón porque eso requería modificar otro archivo. Repetir esta
función conserva los valores y la tabla de puestos de Supuestos, y rearma sólo Modelo Nuevo.
Si faltan listas o encabezados, los avisa; corregirlos y volver a ejecutar la función.

En Supuestos, las celdas amarillas arrancan **vacías**, incluidas las confirmaciones. Cada fila
indica unidad, rol que provee el dato y una nota. Hay doce cantidades de venta, doce cobros de
ventas anteriores y doce pagos operativos anteriores. Estos últimos importes son el arranque del
modelo: lo pendiente de la operación hasta hoy que se cobrará o pagará después. No incluyen
capital, intereses ni impuestos ya cargados en el cronograma de deuda. Hay que informar **0**
cuando se sabe que no existen; dejarlos vacíos mantiene el faltante.

La tabla de personal empieza en la fila 71 y permite una fila por puesto hasta la 1000:
**rol · unidad · bruto/honorario · quién lo provee · nota · Sueldo/Honorario · mes de entrada**.
Para calcular hacen falta rol, importe, tipo y mes entero entre 1 y 12. Las filas totalmente
vacías no son puestos. Una fila parcialmente cargada bloquea personal. Al terminar, confirmar
“Nómina completa”; confirmarla sin puestos declara explícitamente que no hay sueldos ni
honorarios. No se precargó una dotación supuesta. No insertar filas dentro del bloque superior.

La inflación **se lee de Cash Mensual!B4** (Supuestos!C67 es un vínculo, no otro dato editable).
No se escribe ni reemplaza el valor existente. Si falta esa celda, no es numérica o falta la
solapa, los cálculos que dependen de ella muestran **—**. Revisarla antes de usar el modelo.

**Fechas:** son doce períodos. El primero va desde mañana hasta fin de mes; los otros once son
meses completos. Las filas “Desde” y “Hasta” muestran las fechas exactas; “Hasta” no se incluye.
El primer volumen debe ser lo que se venderá en los días restantes, no el volumen del mes entero.
Al avanzar el día, cambia el horizonte: actualizar kilos del primer período, pendientes de arranque
y confirmaciones; al cambiar de mes, reubicar los doce volúmenes y los meses de incorporación y
cuotas. Para conservar un escenario de negociación, guardar una copia con fecha: no es una foto
histórica congelada ni una bitácora automática.

### Qué hacen las fórmulas

- **Ventas:** kilos del período × precio del primer período × `(1 + inflación)^meses transcurridos`.
  Kilos y porcentajes no se inflan. Los precios, costos por kilo y gastos mensuales sí. Se supone
  venta y compra parejas dentro de cada período, sin redondear los resultados intermedios.
- **Cobranza según días:** cada venta diaria se cobra tantos días corridos después como indique
  la condición. La fórmula cruza ese intervalo desplazado con las fechas de cada columna y toma
  la parte que cae adentro. Suma las partes de todos los períodos anteriores y del actual; luego
  agrega los cobros anteriores informados. **30 días no es siempre una columna**, porque los meses
  tienen distinta duración. Si falta el volumen o precio de un mes que aporta a esa cobranza,
  también queda incompleta la cobranza del mes de destino.
- **Canchada:** kilos vendidos × kilos de canchada por kilo vendido × precio de canchada actualizado.
  Ese costo se muestra como base informativa. Se compra para el consumo del período. La parte
  anticipada se paga al inicio de ese mismo período; el resto se reparte según los días de pago,
  con el mismo cruce de fechas que las cobranzas. El total operativo suma **el pago**, no vuelve
  a sumar la base de compra. No modela anticipos en meses anteriores a la compra.
- **Packaging, sueldos y otros gastos:** packaging se paga en el período de venta. Sueldos y
  honorarios entran desde el mes de incorporación y continúan los meses siguientes; las cargas
  se calculan sólo sobre sueldos. Los importes mensuales de personal, seguros, energía, gas e
  impuestos se prorratean por días cuando el primer período es parcial. No modela bajas,
  aguinaldos ni escalones salariales adicionales. Si hacen falta, debe ampliarse antes de usarlo.
- **Comisiones y fletes:** comisión sobre venta facturada o cobranza total, según la elección;
  se paga en ese período. Fletes permite tarifa por kilo (actualizada por inflación) o porcentaje
  de venta facturada. Impuestos corrientes son un importe mensual provisto por el estudio, sin
  duplicar cargas ni deuda impositiva. No se adivinan alícuotas ni tratamientos tributarios.
- **Imprevistos:** si se pide que sean `p` del **total** operativo, la provisión es
  `otros egresos × p / (1 − p)`. Incluye pagos operativos de arranque; excluye indemnizaciones y
  deuda. No se permite 100%. Así el porcentaje no se aplica a una base distinta de la pedida ni
  crea una fórmula circular.
- **Indemnizaciones:** total nominal dividido en cuotas mensuales iguales desde el mes informado,
  sin inflación. Si el total es 0, mes y cuotas no son necesarios. Las cuotas fuera de los doce
  períodos quedan informadas en “Indemnizaciones pendientes después del horizonte”.
- **Deuda:** lee directamente capital, interés y total del cronograma de Deuda Bancaria, e importes
  de Deuda Impositiva, por vencimiento. Separa `Si`/`Sí` de `No` en `Debito Automatico`, admite
  diferencias de mayúsculas y espacios. No recalcula tasas ni inventa cuotas. Verifica que capital
  más interés coincida con la cuota al centavo; un interés vacío **no** equivale a interés cero.
  Excluye Pagado; el estado pendiente debe decir Pendiente. Estados inesperados, importes o fechas
  faltantes, importes negativos o un débito sin clasificar bloquean el bloque de deuda. Además hay
  que confirmar cobertura de los doce períodos: ninguna fórmula puede deducir cuotas que faltan
  en el origen. Los vencimientos anteriores a mañana quedan fuera de los flujos; para pagarlos,
  acordar y cargar un cronograma, sin duplicar la obligación. **El modelo usa el cronograma real,
  no las propuestas de Plan** que hoy utiliza Cash Mensual.
- **Caja y saldos:** toma la última foto hasta hoy por **banco + empresa + cuenta**, incluida caja
  física si está registrada. No suma acuerdos de descubierto. Muestra la fecha más antigua usada
  y requiere confirmar que las fotos representan la caja de hoy. Datos vacíos o dos fotos en la
  última fecha de la misma cuenta bloquean el saldo. Desde ahí acumula por separado el escenario
  pagando toda la deuda y el escenario pagando sólo lo automático. Los saldos del período no
  incluyen caja inicial; los acumulados sí. Una fuente vieja no se vuelve actual por fórmula:
  actualizarla antes de confirmar.
- **Capital de trabajo:** venta diaria × días de cobro, más costo diario de canchada × días de stock,
  menos costo diario de canchada × parte no anticipada × días de pago. Es la necesidad al ritmo
  de cada período: positivo = plata a financiar, negativo = financiación neta de proveedores.
  Stock vacío muestra **—** y el neto dice **sin stock**; es opcional y no bloquea la
  operación. Stock cero muestra 0. Esta necesidad no se resta otra vez de la caja, que ya respeta
  cobros y pagos. No es el saldo exacto de cuentas a cobrar/pagar de una transición con estacionalidad:
  esos saldos del modelo se muestran aparte en las filas 55 y 56. Tampoco programa compras para
  formar stock ni calcula stock de packaging o producto terminado. Si se necesita financiar un
  stock inicial o compras anticipadas, incorporar su calendario antes de tomar el saldo como
  una proyección completa de esa transición.

**Faltantes:** arriba figura la lista de supuestos o fuentes que impiden cerrar cada período,
sin repetir textos idénticos. Debajo, desde la fila 66, está el motivo por renglón; sirve cuando
la lista de arriba es larga. Un total sólo se calcula si todos sus componentes están completos.
Un dato faltante no se convierte en cero ni desaparece dentro de una suma. El cero confirmado
se muestra como `0,00`. Los bloques independientes pueden calcularse aunque otro esté incompleto.

### Ejemplo hecho a mano — ficticio, no cargar en la planilla del cliente

Para verificar sin datos reales, suponer hoy **31/08/2026**, por lo que los primeros períodos son
septiembre (30 días) y octubre (31 días). En una copia descartable se puede fijar B4 de Modelo
Nuevo en `01/09/2026`; “Hasta” y los períodos siguientes se recalculan desde esa fecha.

Supuestos de prueba: 100.000 kg en cada período; precio $1.000/kg; cobro a 30 días; canchada
0,7 kg/kg a $500, pago a 30 días y anticipo 0%; packaging $100/kg; un sueldo bruto $1.000.000 y
un honorario $200.000, ambos desde mes 1; cargas 20%; comisión 1% facturada; flete $10/kg;
seguros $100.000, energía $200.000, gas $100.000 e impuestos corrientes $200.000 por mes;
imprevistos 10% del total operativo; inflación 0%; stock 10 días. Pendientes operativos anteriores:
0 en todos los meses. Indemnización $2.000.000 en dos cuotas desde mes 1. Nómina y fuentes completas.

Para esta prueba, caja inicial $5.000.000. En **cada uno** de los dos meses, cronograma ficticio:
automático capital $2.000.000 + interés $200.000 + impuesto $300.000; por decisión capital
$1.000.000 + interés $100.000 + impuesto $400.000. Todo Pendiente y con su débito clasificado.
Estos números son únicamente un ejemplo de comprobación; no están en el generador de supuestos.

Cuenta del plazo: las ventas de septiembre se cobran del 1 al 30 de octubre. A eso se agrega
el 31 de octubre la venta del 1 de octubre: `$100.000.000 + $100.000.000 / 31`.
Canchada se paga igual: `$35.000.000 + $35.000.000 / 31`. Sin canchada, los otros gastos suman
$14.000.000. En septiembre, imprevistos = `$14.000.000 × 10% / 90%`.

Importes siguientes en **millones de pesos**, salvo kilos y precio. Se muestran seis decimales
para facilitar el control; la planilla calcula sin ese redondeo.

| Renglón | Septiembre | Octubre |
|---|---:|---:|
| Ventas, kg | 100.000 | 100.000 |
| Precio, $/kg | 1.000 | 1.000 |
| Ventas facturadas | 100,000000 | 100,000000 |
| Cobranza del modelo | 0,000000 | 103,225806 |
| Cobros anteriores | 0,000000 | 0,000000 |
| **Total ingresos** | **0,000000** | **103,225806** |
| Canchada, base de compra (no se suma a pagos) | 35,000000 | 35,000000 |
| Canchada, pago | 0,000000 | 36,129032 |
| Packaging | 10,000000 | 10,000000 |
| Sueldos brutos | 1,000000 | 1,000000 |
| Cargas | 0,200000 | 0,200000 |
| Honorarios | 0,200000 | 0,200000 |
| Comisiones | 1,000000 | 1,000000 |
| Fletes | 1,000000 | 1,000000 |
| Seguros | 0,100000 | 0,100000 |
| Energía | 0,200000 | 0,200000 |
| Gas | 0,100000 | 0,100000 |
| Impuestos corrientes | 0,200000 | 0,200000 |
| Pagos operativos anteriores | 0,000000 | 0,000000 |
| Imprevistos | 1,555556 | 5,569892 |
| **Total egresos operativos** | **15,555556** | **55,698925** |
| **Resultado operativo antes de deuda** | **−15,555556** | **47,526882** |
| Indemnizaciones | 1,000000 | 1,000000 |
| Capital automático | 2,000000 | 2,000000 |
| Interés automático | 0,200000 | 0,200000 |
| Impuestos automáticos | 0,300000 | 0,300000 |
| **Total deuda automática** | **2,500000** | **2,500000** |
| **Saldo del período, sólo automático** | **−19,055556** | **44,026882** |
| Capital por decisión | 1,000000 | 1,000000 |
| Interés por decisión | 0,100000 | 0,100000 |
| Impuestos por decisión | 0,400000 | 0,400000 |
| **Total deuda por decisión** | **1,500000** | **1,500000** |
| **Saldo del período, toda la deuda** | **−20,555556** | **42,526882** |
| Saldo inicial, escenario toda la deuda | 5,000000 | −15,555556 |
| **Acumulado, toda la deuda** | **−15,555556** | **26,971326** |
| **Acumulado, sólo automático** | **−14,055556** | **29,971326** |
| Plata en la calle según días de cobro | 100,000000 | 96,774194 |
| Stock de canchada según días | 11,666667 | 11,290323 |
| Financiación de proveedores | 35,000000 | 33,870968 |
| **Capital de trabajo neto con stock** | **76,666667** | **74,193548** |
| Indemnizaciones después del horizonte | 0,000000 | 0,000000 |
| Ventas del modelo pendientes al cierre | 100,000000 | 96,774194 |
| Canchada del modelo pendiente al cierre | 35,000000 | 33,870968 |

### Guion de prueba en Google Sheets (todavía pendiente)

1. Trabajar en una **copia descartable**, con listas ficticias. Antes, anotar los valores y fórmulas
   de Cash, Cash Semanal, Cash Mensual y Plan. Correr `armarModeloNuevo()` desde Apps Script.
   Deben aparecer sólo las dos solapas nuevas; los supuestos editables vacíos, ninguna dotación
   precargada, la inflación vinculada a la celda existente, egresos y saldos incompletos como **—**.
2. Leer “Faltan datos” y el detalle al pie. Cargar sólo precio: se habilita el precio si hay inflación,
   pero no ventas sin kilos. Vaciarlo: vuelve **—**. Cargar 0 con los demás requisitos completos:
   el resultado es 0 visible. Texto, negativos indebidos, porcentajes fuera de rango o un mes
   fraccionario deben rechazarse al cargar o quedar marcados como inválidos en el cálculo.
3. Completar el ejemplo anterior, incluidos ceros, puestos y confirmaciones. En la copia, fijar
   temporalmente la fecha de inicio indicada y crear una foto de caja ficticia de $5.000.000 con
   fecha hasta hoy. Verificar **cada renglón** de las primeras dos columnas contra la tabla.
   No agregar estos supuestos a la versión entregada ni a la planilla del cliente.
4. Probar 0, 15, 30 y 75 días; cambio de mes y febrero. Con anticipo 50%, la primera salida de
   canchada del ejemplo debe ser $17.500.000; con plazo 0, $35.000.000. Borrar kilos de septiembre:
   se bloquea su facturación y también la cobranza/pago de octubre que dependía de ese mes.
5. Cambiar comisión a Cobrada: en septiembre del ejemplo debe ser 0. Cambiar flete a 1% de venta:
   debe seguir en $1.000.000. Inflación 10%: precio del período 2 pasa a $1.100. Vaciar inflación:
   se bloquean sus dependientes. No hay una segunda celda editable de inflación.
6. Quitar el mes de un puesto: personal y total operativo deben quedar **—**. Mes 2 para honorarios:
   no paga honorarios en mes 1. Indemnización 0 admite mes/cuotas vacíos; importe positivo los exige.
   Cuotas que exceden el horizonte dejan remanente visible. Imprevistos 100% no debe calcularse.
7. Vaciar días de stock: fila stock muestra **—**, alcance dice “Sin stock”; no finge stock 0.
   Con días 0, stock muestra 0. Cambiar cobro/pago debe cambiar tanto caja como capital de trabajo;
   el capital de trabajo no se vuelve a descontar de los saldos.
8. En una cuota, cambiar Si a No: debe pasar de bloque conservando capital e interés. Vaciar interés,
   fecha, estado o débito: deuda y saldos dependientes muestran **—**, no una cuota menor. Marcar
   Pagado: sale de la proyección. Verificar que no usa Plan y que no suma vencido previo como si
   fuera una cuota futura. Una lista vacía sólo da ausencia de pagos tras confirmar cobertura.
9. Agregar dos cuentas del mismo banco y otra empresa: suma la última foto de cada combinación,
   sin duplicar la historia. Un importe vacío en la última foto o una foto duplicada bloquea caja;
   una foto vieja queda expuesta por fecha. Quitar confirmación de caja vuelve **—** los acumulados,
   pero no impide ver un resultado operativo completo.
10. Reejecutar `armarModeloNuevo()`: debe conservar todos los supuestos y puestos cargados. Comparar
    las otras cuatro solapas con el paso 1: sin cambios. Revisar separadores en es_AR, ausencia de
    errores nativos, tiempos de recálculo de los rangos abiertos y lectura de textos largos.
    Restaurar o descartar la copia; no publicar un ejemplo como si fueran datos reales.

### Para que sea la base del mensual

Primero, confirmar los supuestos con sus proveedores, los cronogramas completos y los saldos;
conciliar los pendientes de arranque para no duplicar deuda ni omitir pagos. Acordar si hay stock
inicial, anticipos anteriores a las compras, aguinaldos, bajas o condiciones comerciales que
necesiten calendarios propios. Confirmar fecha de entrada en vigencia, actualización de supuestos,
tratamiento de inflación y quién guarda cada versión. Después, con una tarea aparte, cambiar la
fuente operativa de Cash Mensual y acordar cómo aplica las decisiones de Plan, con un puente entre
real y proyectado. **Esta tarea no hace ese reemplazo.**

## 9. Extractos ilegibles y columnas cambiadas (tarea 15, preparado para revisión)

Un archivo ilegible se saltea entero, se cuenta y se informa como **“no pude leer archivo:
motivo”** en el resumen de bancos. El resto sigue. Si ninguno se pudo leer, queda el resumen
pero no se genera una publicación vacía. Un extracto sin movimientos ni saldos reconocibles
se marca para revisar; no se toma como una confirmación de que la cuenta está vacía.

BBVA, Macro y Galicia buscan las columnas por nombre, admitiendo acentos, espacios,
mayúsculas y las alternativas conocidas. Referencias, leyendas y saldos opcionales pueden
faltar; fecha, concepto e importes no se adivinan. Macro ya no depende del lugar de la columna.

BBVA admite **Detalle / Saldo Disponible** y **Saldo Parcial**, y referencias con **Número
Documento / Nro de cheque**. En el formato viejo se mantiene el saldo diario que ya se había
contrastado con el PDF. En el nuevo, si el último Saldo Parcial no coincide con el encabezado
(o falta ese encabezado), entran los movimientos pero **no se publica ese saldo**: queda
**REVISAR**. No se afirma que uno sea disponible y otro contable sin evidencia. Si coinciden,
se usan los saldos parciales diarios, respetando el orden del export (más nuevo primero).
Para el archivo del 23/09 se conserva la última foto válida anterior, con su fecha original.

El vigilante deja los errores en su log. Antes de publicar, recupera del último
`para_pegar_bancos` publicado las filas faltantes de los bancos con archivos fallidos,
sin duplicar movimientos ni pisar saldos recién leídos. **No cambia las fechas antiguas**.
El resumen indica cuántas filas recuperó; sus totales por banco describen la lectura nueva,
antes de esa recuperación. Así la importación completa no borra la historia de un banco que
hoy no se pudo leer. Los controles de achicamiento y crecimiento siguen funcionando.
Sin publicación anterior no se puede recuperar historia: se publica lo legible y se avisa.
Un saldo no confirmado no se convierte en cero ni en saldo actualizado.

Los archivos fallidos requieren corrección o una nueva descarga; al cambiar las fuentes el
vigilante vuelve a procesar. Para reintentar después de arreglar el entorno de OCR sin cambiar
los archivos se puede usar `--forzar bancos`. Esta mejora está probada sobre copias y ejemplos;
no significa que ya esté instalada en la notebook ni importada en la Sheet.
