# Plan comercial — finauto

> **Escrito el 06/09/2026.** Responde las 17 preguntas del brief comercial.
> Documento vivo: se corrige con lo que digan las primeras conversaciones, no
> con lo que parezca prolijo acá.
>
> Regla que atraviesa todo: **el objetivo de la fase 1 no es facturar, es
> conseguir un precio pagado y una medición de acierto.** Todo lo demás se
> subordina a eso.

---

## 0 · Tres correcciones al material que ya tenés

Antes del plan, tres cosas del dossier que hay que arreglar porque van a costar reuniones.

### 0.1 · La página 3 no puede ir al cliente

El dossier se titula *"Dossier para la conversación comercial"*, pero la página 3
—*"Thomas ya no trabaja en la empresa donde se construyó todo esto... no hay acceso a los
bancos... el dato es una foto que no se puede refrescar"*— está escrita para vos y para mí,
no para un dueño.

Un prospecto que lee eso no piensa "qué honesto": piensa **"al tipo lo echaron y su único
caso ya no es cliente"**. Es información verdadera y necesaria — internamente.

**Partilo en dos archivos**: `dossier-cliente.pdf` (páginas 1 y 2) y el resto en
`docs/ESTADO.md`, donde ya vive.

### 0.2 · Sacá el número de tests

*"Terminado — 358 tests"* le habla a un ingeniero. A un dueño de farmacia le dice dos cosas
malas: que esto es software (cuando le estás vendiendo asesoría) y que hay 358 cosas que
podrían romperse.

Reemplazalo por lo que el test **compra**: *"Terminado. Se contrasta solo contra tus propios
números todos los días."* El rigor se demuestra mostrando el contraste, no contándolo.

### 0.3 · Los números de MAGA+ no son material de venta

$915M, $963,9M, $8.640M, "14 farmacias más su droguería": eso identifica a la empresa para
cualquiera del rubro. Tu propio `COMO_TRABAJAMOS.md` promete que **nada se usa como ejemplo
con otro cliente sin autorización escrita** — y esa promesa es uno de tus mejores argumentos.
Romperla en la primera reunión, delante del tipo al que se la estás prometiendo, es el peor
negocio posible.

**Dos salidas, en este orden:**

1. **Pedile autorización escrita a MAGA+** para usar el caso, anonimizado o no. Si vas a
   pedirles el export de octubre igual (§ conciliación), pedí las dos cosas juntas. Un
   "cadena de 14 farmacias del AMBA, con autorización para contarlo" vale muchísimo más
   que un caso sin nombre.
2. **Mientras tanto**, el dossier habla de **tipos** de hallazgo, no de montos:
   *"En el primer cashflow real que analicé aparecieron cuatro errores que el dueño no tenía
   identificados: un tablero de decisión apuntando a una columna de cinco meses atrás, deuda
   inflada por notas de crédito mal netadas, cheques endosados contados como caja, y un
   horizonte de 45 días que sumaba 56."* Cero montos, cero identificación, y el argumento
   queda intacto — porque lo que impresiona no es el monto, **es que el dueño no lo sabía**.

---

## 1 · El ICP: a quién

### 1.1 · La distinción que falta en el brief

La pregunta *"¿el criterio 'dependencia del crédito de proveedores' es suficiente para
segmentar?"* mezcla dos cosas que conviene separar, porque se resuelven distinto:

| | Qué es | Tiene que ser |
|---|---|---|
| **Criterio de targeting** | Cómo armás la lista de a quién escribirle | **Observable desde afuera**, sin hablar con ellos |
| **Criterio de calificación** | Cómo decidís si vale la pena seguir | Se descubre **en la conversación** |

**"Dependencia del crédito de proveedores" es un criterio de calificación excelente y un
criterio de targeting inservible**: no existe forma de mirar una farmacia desde afuera y
saber si vive del plazo de la droguería.

Entonces la respuesta a la pregunta 2 es: **no alcanza, pero no porque sea flojo — porque
está en la etapa equivocada del embudo.**

### 1.2 · Los criterios de targeting (para armar la lista)

Todos verificables sin hablar con nadie:

| Criterio | Umbral | Por qué |
|---|---|---|
| **Rubro** | Farmacia o droguería | Tenés el catálogo, el vocabulario, los plazos y los hallazgos. Salir del rubro ahora te tira a la basura tu única ventaja. |
| **Tamaño** | **4 a 25 bocas** | Menos de 4: el dueño lleva la cuenta de memoria. Más de 25: ya hay un gerente financiero y un ERP, y el ciclo de venta se hace de meses. |
| **Estructura** | **Más de una razón social** | Es el mejor proxy observable que existe. Implica el problema de consolidación, que es exactamente lo que el motor resuelve y lo que un Excel no. |
| **Geografía** | AMBA primero | La visita presencial es parte del producto ("asesoría, no software"). Un viaje a Córdoba por una reunión de 30 minutos no cierra. |
| **Antigüedad** | +10 años | Empresa con plazos consolidados con proveedores y planilla histórica. Una cadena nueva no tiene deuda vieja ni tolerancia acumulada. |

### 1.3 · Los criterios de calificación (para la conversación)

Ordenados por poder de discriminación. **Las tres primeras deciden**; el resto es color.

1. **"¿Cuánto tardás en saber a quién le tenés que pagar esta semana?"**
   La mejor pregunta que podés hacer, mejor que la del dossier. Mide el dolor en **horas**,
   que es la unidad que después se convierte en precio. Y es difícil de contestar
   defensivamente: nadie presume de tardar poco en algo que odia.
   - *< 30 minutos* → no hay dolor, o ya lo resolvieron. Descalifica.
   - *2 a 6 horas* → **el corazón del ICP.**
   - *"no sé / lo hace el contador / me entero cuando rebota"* → dolor alto, pero verificá
     que el dueño sea el que decide (si no, no hay comprador).

2. **"¿Tenés línea bancaria disponible hoy? ¿Y la estás usando?"**
   La del dossier, pero **partida en dos**, porque un dueño contesta "sí, tengo línea" por
   orgullo aun teniéndola agotada. Lo que buscás es *tengo pero no la uso porque está cara*
   o *no tengo*. Un "sí, tengo y la uso" descalifica: no viven al límite del proveedor.

3. **"En los últimos seis meses, ¿alguna droguería te frenó o te amenazó con frenarte la
   compra?"**
   Convierte el concepto abstracto de "tolerancia del proveedor" en un evento que pasó o no
   pasó. Un sí es la señal más fuerte de todas: **ya sufrieron el costo de equivocarse.**

4. ¿En qué armás la posición? (Excel/Sheets = califica · ERP con tesorería = descalifica)
5. ¿Quién la arma? (el dueño o un administrativo = califica · el contador externo = duda)
6. ¿Alguna vez te enteraste tarde de que no llegabas a un pago?
7. ¿Cómo proyectás lo que vas a cobrar de obras sociales?
8. ¿Cuántas razones sociales manejás, y cómo las mirás juntas?

Las diez preguntas del brief están bien, pero **diez preguntas no entran en 30 minutos** si
además querés escuchar. Estas ocho, con las tres primeras como filtro duro, sí.

### 1.4 · Prioridad (pregunta 3)

| Prioridad | Perfil | Por qué |
|---|---|---|
| **1** | Cadenas de 6-15 bocas, varias razones sociales, AMBA, sin ERP | El centro exacto del ICP |
| **2** | **Droguerías chicas y medianas** | Están del otro lado del mismo problema: cobran a plazo de las farmacias y le pagan a plazo a los laboratorios. El motor les sirve casi igual — y entienden el vocabulario sin explicación |
| **3** | Cadenas de 4-6 bocas | Menos dolor, ciclo más corto, buen terreno de práctica |
| **4** | **MAGA+** | Ver §7.4: no es prioridad 1 por tamaño, es un caso aparte |
| — | Farmacia individual, cadena +25 bocas, otro rubro | No ahora |

---

## 2 · La lista: cómo conseguir nombres sin red

Es tu problema más duro y el dossier lo dice: *"sin red de contactos en el rubro fuera del
ex empleador"*. La aritmética honesta primero.

### 2.1 · La aritmética que falta en el brief

El objetivo del brief es **10-20 conversaciones → 5 diagnósticos → 2 pilotos → 1 cliente
pago**. Los ratios son razonables. Lo que falta es la etapa de arriba:

```
  ~80 contactos identificados
  →  ~50 aproximaciones efectivas (llegaste a la persona que decide)
  →  10-20 conversaciones de 30 min      [tasa realista en frío: 20-35%]
  →   5 diagnósticos
  →   2 pilotos
  →   1 cliente pago
```

**Ochenta nombres.** Si planificás para 20, te quedás sin embudo en la semana 3 y el
proyecto se muere por falta de gente con quien hablar, no por falta de producto. Ese es el
número que hay que ir a buscar antes de escribir el primer mail.

### 2.2 · Los canales, ordenados por señal

**A · Los comerciales de las droguerías. El mejor canal que tenés, y por lejos.**

Un vendedor de Suizo, Del Sud o Cofaloza visita cada cadena de su zona todas las semanas.
Sabe cuántas bocas tiene cada una, quién decide, y —esto es lo importante— **quién paga
tarde**. Es literalmente una lista viva del ICP, caminando.

Por qué te atendería: presentarle a un cliente algo que le ordene la caja **le conviene**,
porque un cliente que proyecta mejor le paga más prolijo. No le estás pidiendo un favor.

Cómo pedirlo, y el límite: *"¿A quién de tu cartera le vendría bien esto?"*. Nunca al
revés — no le preguntes quién está complicado, ni uses nada que sepas de MAGA+. Esa línea
no se cruza: si un comercial percibe que hablás de la caja de un cliente tuyo, perdés el
canal entero y la reputación con él.

**B · Contadores que atienden farmacias.**
Ven el cashflow de varias, no pueden construir esto, y son a quienes el dueño le pregunta
"¿llego?". Un contador que te deriva queda mejor parado con su cliente. Buscalos por
estudios especializados en el rubro.

**C · Colegios y cámaras.**
Colegios de Farmacéuticos provinciales y de CABA, COFA, FACAF, cámaras de farmacias
regionales. Sirven para dos cosas: el padrón (targeting) y la charla. **Una charla de 20
minutos —"tres errores que encontré en el cashflow de una farmacia"— te pone diez dueños
adelante en una hora.** Es el canal de mayor apalancamiento por tiempo invertido.

**D · LinkedIn directo.**
A dueños y a *gerentes administrativos* de cadenas. El gerente administrativo suele ser
mejor puerta: sufre el problema en carne propia, contesta más, y te lleva al dueño con el
dolor ya explicado.

**E · El ex empleador.**
Aparece último a propósito. **Pedir referidos a MAGA+ antes de que te paguen invierte la
relación**: pasás de proveedor a alguien que pide favores. Después de que paguen, un
referido de ellos vale más que veinte mails fríos.

### 2.3 · La primera aproximación (pregunta 5)

Tres reglas, y después el texto:

1. **No mencionar software, sistema, IA, automatización ni tablero.** Vendés una lectura de
   su caja. La herramienta es asunto tuyo.
2. **Pedir 30 minutos, no una reunión.** El compromiso tiene que ser chico y con final.
3. **La oferta es un diagnóstico gratis que le cuesta un archivo, no una demo.**

> **Asunto:** Tres errores que encontré en el cashflow de una farmacia
>
> [Nombre], soy Thomas Manzo. Trabajé cuatro años en la administración de una cadena de
> farmacias del AMBA, manejando la caja diaria y la deuda con las droguerías.
>
> Armé una herramienta para contestar la pregunta que teníamos todas las semanas: **a quién
> le pagamos y a quién le pedimos una semana más.** Cuando la corrí sobre el cashflow real,
> aparecieron cuatro errores que nadie había visto — entre ellos, que el tablero con el que
> se decidía apuntaba a una columna de cinco meses atrás.
>
> Estoy tomando algunas cadenas para hacer el mismo diagnóstico sin cargo, para validar que
> sirva más allá de un solo caso. **No necesito acceso a nada: alcanza con una copia
> exportada de tu planilla de flujo de fondos.**
>
> ¿Tenés 30 minutos esta semana o la próxima?

Por qué funciona: abre con credencial operativa (no técnica), el gancho es un **hallazgo**
y no una funcionalidad, y elimina de entrada la objeción más grande —el acceso— antes de
que la piense.

---

## 3 · La reunión 1: 30 minutos, sin demo

**La decisión estructural más importante de todo el plan: en la primera reunión no se
muestra nada.**

El premortem marcó esto como uno de los fallos más probables: el valor de finauto solo
existe sobre datos reales, así que una demo genérica te iguala a cualquier consultor de
Excel. La demo sin sus datos **te resta**. La solución no es una demo mejor: es no hacerla.

| Minutos | Qué |
|---|---|
| **0-3** | Quién sos. Cuatro años operando la caja de una cadena. **Terminá con una pregunta, no con un pitch.** |
| **3-20** | **Descubrimiento.** Las 8 preguntas de §1.3, con las tres primeras sí o sí. Escuchar. Si hablás más del 30% del tiempo, la reunión salió mal aunque te hayas sentido bien. |
| **20-25** | **Devolución en voz alta.** Repetirle su problema mejor de lo que él lo dijo: *"O sea que todos los lunes perdés tres horas armando esto a mano, y aun así el mes pasado te enteraste tarde de un pago."* Acá se gana o se pierde: si asiente, entendiste el negocio. |
| **25-30** | **El pedido.** Un solo archivo: la planilla de flujo de fondos exportada. Fecha concreta para la reunión 2. Mandale `COMO_TRABAJAMOS.md` **antes de que lo pida**. |

Si en el minuto 20 quedó claro que no califica (tiene línea y la usa, o tarda 20 minutos en
armar la posición), **cerrá temprano y bien**: agradecé, contá en una frase qué hacés, y
pedile un referido. Una reunión que descalifica en 20 minutos es un éxito, no un fracaso —
te ahorró un piloto que no iba a cerrar.

---

## 4 · La reunión 2: el diagnóstico

Entre la 1 y la 2 corrés `finauto.py` sobre su planilla. Esa corrida es el producto.

### 4.1 · Qué mostrar (pregunta 7)

**Exactamente tres cosas, en este orden, y nada más:**

1. **Un error de sus propios números.** Lo primero, siempre. Es lo único que un consultor
   con Excel no puede improvisar, y lo que convierte la conversación de "me querés vender
   algo" a "cómo sabés eso". Si no encontraste ningún error, decilo — *"tu planilla está
   bien armada, no encontré inconsistencias"*— y ganás igual, porque nadie más se lo dijo.
2. **Su día crítico.** Una fecha y un monto. *"El 25 te quedás en $X, abajo de tu mínimo."*
   Una fecha concreta en el futuro es lo que produce la reacción física.
3. **El reparto de esta semana.** A quién pagarle y a quién estirar, ordenado por quién
   puede cortarle la compra primero. Es la decisión que ya toma todas las semanas, hecha
   por él, delante de él.

Cerrás con **una** pregunta: *"¿esto te sirve?"*. Y te callás.

### 4.2 · Qué NO mostrar (pregunta 8)

- **Las seis capas del tablero.** Mostrás dos. El resto aparece en el piloto.
- **El motor, los tests, la arquitectura, el contrato JSON, los bots, el repo.** Nada de
  esto le importa a un dueño y todo lo mueve al casillero "software".
- **El roadmap y lo que falta.** Contarle lo que viene le da un motivo perfecto para
  esperar. Vendés lo que hay hoy.
- **Los números de MAGA+.** Ver §0.3.
- **El precio**, si él no lo pregunta. Va en la reunión 3, con la propuesta escrita. Si lo
  pregunta, tenés el número listo (§6) y lo decís sin titubear — titubear en el precio es
  lo que lo baja.

---

## 5 · El piloto (preguntas 9, 10)

### 5.1 · La idea central: el piloto ES tu medición de acierto

Tu lista de faltantes dice *"segunda foto para validar el forecasting"* y *"una medición de
acierto"*. El dossier lo dice mejor: *"un motor de predicción que nunca mostró un acierto es
una hipótesis, no un producto"*.

**No hace falta resolverlo antes de vender: el piloto lo produce.** Si el piloto empieza
guardando una proyección y termina conciliándola, entonces:

- el cliente paga por el piloto,
- y el piloto te devuelve **la prueba que te falta para vender el siguiente**.

Esto convierte tu carencia más grande en el entregable final del piloto. Es el punto de
apalancamiento de todo el plan.

### 5.2 · Diseño

**Duración: 6 semanas.** Ni 4 ni 12.

- Menos de 6 y no entra un ciclo mensual completo (sueldos, impuestos, alquileres se mueven
  entre el 1 y el 15), así que no hay nada que conciliar.
- Más de 8 y el dueño pierde el hilo, cambia la prioridad, y el piloto muere sin decisión.

| Semana | Qué pasa |
|---|---|
| **0** | Carga de la planilla, solapa de config, **se guarda la proyección inicial**. Primera lectura. |
| **1-5** | Una lectura semanal. 45 minutos, presencial o por video. El informe queda por escrito, fechado. |
| **6** | **La conciliación.** Qué se proyectó, qué pasó, por cuánto le erró y en qué tipo de movimiento. Más la propuesta de continuidad. |

### 5.3 · El criterio de éxito, escrito antes de empezar

Esto es lo que hace que el piloto termine en una decisión y no en un silencio. **Se acuerda
por escrito en la propuesta, antes de cobrar.**

> *El piloto se considera exitoso si al final de las 6 semanas se cumplen al menos 3 de
> estos 5:*
>
> 1. Se identificaron **inconsistencias en los números propios** que la empresa no tenía
>    detectadas.
> 2. El tiempo de armar la posición semanal bajó de **N horas a menos de 30 minutos**.
>    *(N se mide en la semana 0 — sin ese número no hay antes/después.)*
> 3. Se anticipó **al menos un día crítico** con más de 7 días de aviso.
> 4. **Al menos una decisión de pago o postergación** se tomó usando el reparto del sistema.
> 5. La proyección inicial se concilió y el desvío de la caja acumulada a 30 días quedó
>    **por debajo del 10%**.

Los cinco salen de tu lista del brief; la diferencia es que están **cuantificados y
acordados de antemano**. Un indicador que se define al final se define para justificar lo
que pasó.

Y el punto 5 tiene un beneficio secundario grande: **te obliga a medir tu propio error y a
mostrarlo**. Un asesor que llega con "le erré 6% y acá está por qué" es más creíble que uno
que llega con un acierto perfecto.

---

## 6 · El precio (preguntas 11, 12)

### 6.1 · Qué pasa con tu hipótesis actual

**USD 500 de implementación + USD 100/mes.**

- **La implementación está bien.** No por el monto sino por la función: lo que comprás con
  ese cobro es **el precedente**, que es lo que te falta. Cobrar poco la primera vez es
  correcto; cobrar cero no.
- **El mensual es el problema.** No porque sea bajo, sino porque **lo estás fijando antes de
  poder medir lo que entrega** — y el mensual es todo el negocio. USD 100 ancla la
  recurrencia para siempre, y de un ancla no se sube: se renegocia con desgaste.

Además, USD 100/mes contra un cliente en el que detectás inconsistencias de nueve cifras es
una desproporción que **te resta credibilidad**. Un precio demasiado bajo hace pensar que el
que lo puso no cree del todo en lo que vende.

### 6.2 · La estructura recomendada

**Cobrá el piloto entero como un fee fijo, y no cotices el mensual todavía.**

| | Monto | Cuándo | Qué compra |
|---|---|---|---|
| **Diagnóstico** | **$0** | Antes de la reunión 2 | Tu entrada. Le cuesta un archivo. |
| **Piloto de 6 semanas** | **USD 600-900**, todo incluido | 50% al arrancar, 50% en la semana 6 | Implementación + 6 lecturas + la conciliación |
| **Abono mensual** | **Se cotiza en la semana 6**, contra el resultado medido | Desde el mes 2 | La recurrencia |

**Cómo se justifica** (pregunta 12), y es una sola frase que además es verdad:

> *"El abono lo fijamos al final del piloto, cuando los dos sepamos cuánto te dio. Ponerle
> precio ahora sería adivinar."*

Un dueño de PyME escucha eso y entiende **exactamente** lo que hacés: no le vendés una
promesa, le vendés una medición. Y a vos te deja fijar la recurrencia **con el número del
punto 5.2 en la mano** en vez de con una hipótesis.

### 6.3 · Detalles que importan en Argentina

- **Cotizá en USD, cobrá en pesos** al tipo de cambio del día de la factura. Estándar en
  servicios y evita la renegociación por inflación.
- **El abono se ajusta cada 3 meses** por índice o por acuerdo. Dejalo escrito desde el
  primer contrato; agregarlo después es una conversación incómoda.
- **Cobrá el 50% del piloto por adelantado, siempre.** No por el dinero: porque **un
  prospecto que no adelanta el 50% no va a mandar la planilla a tiempo ni a reservar los 45
  minutos semanales.** El pago por adelantado es el filtro de compromiso más barato que
  existe.

### 6.4 · El caso MAGA+

MAGA+ hoy califica para tu propio test de éxito: ya no sos parte de la empresa.

Es, además, **el prospecto más avanzado que tenés**: es el único con el diagnóstico hecho,
los hallazgos entregados, el tablero corriendo, la config armada y la relación viva. Todo el
embudo de §2 existe para llegar a la posición en la que **ya estás** con ellos.

Al mismo tiempo no puede ser tu único plan, por dos razones: tu propio criterio de éxito
dice *"una cadena ajena"*, y una negociación con un ex empleador tiene una asimetría que no
controlás.

**Lo concreto, y con fecha:** mandales **esta semana** una propuesta escrita de una carilla
—alcance, precio, plazo, criterio de éxito— junto con el pedido del export de octubre y la
autorización para usar el caso. **Las tres cosas en el mismo mail**, mientras la relación
está tibia. Cada semana que pasa, esa temperatura baja.

---

## 7 · Los papeles (preguntas 13, 14)

> **Esto no es asesoramiento legal ni impositivo.** Es la lista de lo que hace falta y por
> qué. Los puntos marcados con ⚠ confirmalos con un contador antes de firmar nada.

### 7.1 · El mínimo indispensable

| Documento | Estado | Cuándo se usa |
|---|---|---|
| **Cómo trabajamos con tus datos** | ✅ Ya lo tenés | Se manda **antes** de que lo pidan, después de la reunión 1 |
| **Propuesta / orden de trabajo** | ❌ Falta | Una carilla: alcance, entregables, plazo, precio, forma de pago y **el criterio de éxito de §5.3**. Aceptada por mail responde igual que una firma. |
| **NDA recíproco** | ❌ Falta | Dos carillas, mutuo. Que sea **recíproco** importa: te iguala, no te subordina. |
| **Factura** | ⚠ Verificar | Monotributo. Sin factura no hay cliente formal, y una PyME que no puede computar el gasto no compra. |

**Lo que NO hace falta ahora:** SRL, marca registrada, seguro de responsabilidad civil
profesional, contrato de 20 páginas. Todo eso se justifica con clientes pagando, no antes.
⚠ El seguro sí conviene mirarlo cuando haya recurrencia.

### 7.2 · Trabajar con datos de un tercero sin sociedad constituida

⚠ Confirmá con un contador, pero la forma habitual:

- **Como persona física monotributista podés contratar y facturar.** No necesitás sociedad
  para un piloto.
- **La confidencialidad es contractual, no societaria.** El NDA y la cláusula de tu
  `COMO_TRABAJAMOS.md` es lo que te obliga y lo que lo tranquiliza a él. Una SRL no agrega
  protección de datos: agrega separación patrimonial, que es otra cosa y que importa
  después.
- **Datos personales:** la Ley 25.326 apunta a datos de personas físicas. Un cashflow
  empresarial no es el centro de esa ley, pero si en la planilla hay nombres de empleados
  (sueldos) o de personas físicas, sí entra. **Práctica sana: pedí la planilla sin la hoja
  de sueldos nominada**, o que los sueldos vayan agregados por total.

### 7.3 · El punto de la fase 2 que hay que revisar ahora ⚠

Este es el riesgo legal más concreto que tenés y no está en tu lista.

**Los términos y condiciones de los home banking argentinos prohíben que el titular comparta
sus credenciales con un tercero o permita el acceso automatizado por su cuenta.** Que estén
cifradas con DPAPI resuelve el problema técnico —vos no las ves— pero **no resuelve el
contractual**: el banco no distingue "cifradas" de "compartidas". Si hay un fraude en esa
cuenta, aunque no tenga nada que ver con vos, el banco puede desconocer el reclamo del
cliente por incumplimiento de los términos. Ese es su riesgo, y él te lo va a trasladar a
vos.

**La mitigación es arquitectónica y ya casi la tenés:** que en fase 2 **el bot corra en la
máquina del cliente**, no en la tuya. Cambia la figura por completo — pasás de "un tercero
entra a tu banco" a "una herramienta que corre en tu equipo, con tus credenciales, y te
deja el archivo". DPAPI ya es por-usuario y por-máquina, así que el diseño empuja para ese
lado solo.

Y en la propuesta, una línea explícita: *"la automatización de la descarga corre en un
equipo tuyo, con tus credenciales; yo no las veo ni las tengo."*

### 7.4 · Un párrafo que conviene agregarle a `COMO_TRABAJAMOS.md`

Hoy el documento dice qué hacés y qué no. Le falta **el techo de responsabilidad**, que es
lo primero que mira un dueño con abogado:

> *La responsabilidad total por cualquier reclamo vinculado a este servicio se limita al
> monto efectivamente facturado en los últimos tres meses. Las decisiones financieras y sus
> consecuencias son de la empresa.*

⚠ Revisalo con un contador o abogado, pero algo con esa forma tiene que estar. Sin techo de
responsabilidad, un consejo que sale mal es un problema sin límite.

---

## 8 · Señales (preguntas 15, 16)

### 8.1 · Que resuelve un problema real

**Ignorá lo que dicen. Mirá lo que hacen.** Los elogios son gratis; estas cinco no:

1. **Reenvía tu informe a alguien más sin que se lo pidas** — al socio, al contador, al
   hijo. Es la señal más fuerte que existe: le sirvió para algo suyo.
2. **Te escribe entre visitas.** *"Che, ¿cómo quedo si le pago a Suizo el jueves?"* Significa
   que entró en su circuito de decisión.
3. **Cambia una decisión de pago por lo que mostró el tablero, y te lo cuenta.**
4. **El administrativo te manda la planilla sin que la pidas.** El equipo lo adoptó, no solo
   el dueño. Es la señal de que sobrevive a un mal mes.
5. **Te pide sumar un banco, una empresa o una vista.** Está proyectando el uso hacia
   adelante.

**Contraseñales** — atención con estas, porque se sienten bien:

- Elogios entusiastas sin ninguna de las cinco de arriba. *"Buenísimo esto"* es lo que dice
  alguien que no lo va a usar.
- Reprograma la lectura semanal dos veces seguidas.
- Nunca discute un número. **Un cliente que usa el tablero encuentra errores y te los
  marca.** El silencio no es conformidad: es que no lo abrió.

### 8.2 · Cuándo dejar de agregar funcionalidades (pregunta 16)

**Ahora.** Y conviene que sea una regla escrita, no una intención, porque el premortem
marcó el estancamiento por construcción como uno de los fallos más probables — y tu propio
patrón de commits lo confirma: el motor avanza rápido porque es lo que sale bien.

**Regla propuesta, para pegar arriba de `ESTADO.md`:**

> **Congelamiento de funcionalidades hasta el primer peso cobrado.**
> No se construye nada nuevo salvo que se cumpla una de estas tres:
> 1. Un prospecto **con nombre y apellido** está frenado por eso.
> 2. Es necesario para **cobrar o para medir** (facturación, conciliación, informe en PDF).
> 3. Está roto.
>
> Todo lo demás va a `IDEAS.md` y se decide con un cliente pagando.

Lo que **sí** entra por la puerta 2, y por eso conviene hacerlo ya:

- **El informe en PDF** (ya lo tenés anotado). El HTML no se manda por mail.
- **La propuesta de una carilla y el NDA** (§7.1).
- **La conciliación de octubre** (§9).

Lo que **no** entra, aunque tiente: bots de Comafi/Santander/Provincia. Están bloqueados por
acceso, no por código, y **la fase 1 no los necesita** — tu propio diseño en dos fases lo
resuelve. Se construyen cuando un cliente pagando los pida.

### 8.3 · Convertir el primer caso en repetible (pregunta 17)

En este orden, y no antes:

1. **Cliente 1:** anotá **el tiempo real** de cada paso del onboarding. Sin ese número no
   sabés cuántos clientes entran en tu semana — que es el techo real del modelo mientras
   estés solo.
2. **Cliente 2:** convertí ese registro en un **checklist de onboarding**. Lo que se repitió
   dos veces, se escribe.
3. **Cliente 3:** recién ahí, el **reconocedor de planillas**. Construirlo antes es
   optimizar un proceso que todavía no conocés. Con tres planillas distintas encima de la
   mesa vas a saber qué generalizar; con una, vas a generalizar la de MAGA.

---

## 9 · El plan de 8 semanas

Fechas reales. La columna de la derecha es lo único que cuenta.

| Semana | Fechas | Foco | Termina con |
|---|---|---|---|
| **1** | 7-13/09 | **Papeles y MAGA+** | Propuesta + NDA escritos · mail a MAGA+ con las 3 cosas (§6.4) · informe en PDF |
| **2** | 14-20/09 | **La lista** | 80 nombres en una planilla · 10 comerciales de droguería y 5 contadores contactados |
| **3** | 21-27/09 | **Primeras conversaciones** | 5 reuniones de 30 min hechas · las 3 preguntas de calificación probadas |
| **4** | 28/09-4/10 | **Primeros diagnósticos** | 2 planillas ajenas corridas end-to-end · **se sabe si la config alcanza** |
| **5** | 5-11/10 | **⚠ Conciliación** | El export de octubre de MAGA+ pedido y conciliado · el resultado en el tablero |
| **6** | 12-18/10 | **Cerrar el primer piloto** | 1 propuesta de piloto entregada con precio |
| **7-8** | 19/10-1/11 | **Piloto en marcha + seguir prospectando** | Primer pago recibido · embudo con 10 conversaciones más |

**El hito que define todo:** al final de la semana 4 tenés que haber corrido **una planilla
que no sea de MAGA**. Es la única forma de saber si la config alcanza, y si no alcanza,
enterarte con tres semanas por delante en vez de con un cliente esperando.

---

## 10 · Lo que solo podés decidir vos

Tres números que no puedo inventar y que cambian todo el plan:

1. **Cuántos meses aguantás sin cobrar.** Si son 2, el plan de 8 semanas es lo único que
   importa y MAGA+ pasa a ser prioridad absoluta. Si son 8, podés hacer el embudo bien.
   **Debería estar escrito arriba de `ESTADO.md`.**
2. **Tu piso de precio por hora.** Sin eso no sabés si un piloto de USD 700 por 6 semanas te
   sirve o te empobrece. Cronometrá una corrida completa de MAGA+ una sola vez y hacé la
   cuenta.
3. **Cuántos clientes querés.** No es lo mismo un plan para 3 clientes de asesoría cara que
   uno para 30 de abono chico. Hoy el diseño —vos corrés todo— es de 3 a 5. Está bien, pero
   conviene que sea una decisión y no un default.

---

## Anexo · Dónde está contestada cada pregunta

| # | Pregunta | § |
|---|---|---|
| 1 | ¿Cuál debería ser el ICP inicial? | §1.2 |
| 2 | ¿"Dependencia del crédito de proveedores" alcanza para segmentar? | §1.1 — no: es calificación, no targeting |
| 3 | ¿Qué empresas son prioritarias? | §1.4 |
| 4 | ¿Cómo conseguir contactos de dueños/directores? | §2.2 |
| 5 | ¿Cómo realizar la primera aproximación? | §2.3 |
| 6 | ¿Cómo estructurar una reunión de 30 minutos? | §3 |
| 7 | ¿Qué debería mostrarse en una demo? | §4.1 |
| 8 | ¿Qué no debería mostrarse? | §4.2 |
| 9 | ¿Cómo diseñar el piloto? | §5.2, §5.3 |
| 10 | ¿Cuánto debería durar? | §5.2 — 6 semanas |
| 11 | ¿Qué debería cobrarse? | §6.2 |
| 12 | ¿Cómo justificar implementación + suscripción? | §6.2 |
| 13 | ¿Qué contrato y documentación mínima hacen falta? | §7.1 |
| 14 | ¿Cómo trabajar legalmente con datos de terceros? | §7.2, §7.3 |
| 15 | ¿Qué señales indican que resuelve un problema? | §8.1 |
| 16 | ¿Cuándo dejar de agregar funcionalidades? | §8.2 — ahora |
| 17 | ¿Cómo convertir el primer caso en repetible? | §8.3 |
