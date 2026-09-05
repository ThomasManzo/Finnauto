# El negocio — lo que hay que entender antes de tocar código

> Este archivo existe porque el 05/09/2026 perdimos un día entero en correcciones
> que salían todas del mismo lugar: yo no entendía el negocio.
>
> Thomas: *"pensémoslo como una empresa: vos ponés el código que yo no sé, yo el
> conocimiento en finanzas y en el negocio que vos no tenés."*
>
> **Regla: si algo está acá, se asume sin volver a preguntar. Si no está, se
> pregunta — no se inventa.**

---

## 1 · Quién es quién

| | |
|---|---|
| **MAGA** (= MAGA+, misma cosa) | 14 farmacias. **Compra**, no vende a droguerías. |
| **Speedmed** | 1 droguería. **Compra y vende.** |
| **Dominico** | Arriba de la farmacia Dominico: centro de operaciones de Speedmed + administración de las dos. |
| **Quintana** | Oficina en Recoleta que se alquilaba. La inversión salió mal (equipo caro, negocio que no funcionaba), se redujo la gente y se mudó todo a Dominico. |

**Las 14 farmacias son 14 razones sociales distintas.** No por estructura
financiera: en Buenos Aires **no se pueden tener más de 3 farmacias a nombre de
uno**. Todas las cadenas están así.

> **Generalizable:** una restricción regulatoria puede partir un solo negocio en
> muchas razones sociales. El sistema nunca debe asumir *una empresa = una
> unidad de decisión*.

### La relación entre las dos

Speedmed le vende a las farmacias de MAGA. Y **consigue mejores precios en
laboratorios (Elea, Bernabó) gracias al volumen que le da MAGA.**

Durante mucho tiempo Speedmed no le facturaba a MAGA, o le facturaba en 0. Hace
poco empezó a facturarle **al costo**, como si fuera una droguería más — pero
**sin necesidad de que MAGA pague**. MAGA solo transfiere cuando Speedmed
necesita cubrir cheques.

> MAGA por sí sola **no es un negocio rentable**. El valor está en el conjunto.

---

## 2 · El circuito comercial

```
LABORATORIOS ──30 a 90 días──► SPEEDMED ──35 días──► FARMACIAS (MAGA y de afuera)
DROGUERÍAS  ──38 a 45 días──►     │
                                  └──► MAGA (38 días, pero no paga: solo cubre cheques)

DROGUERÍAS ──38/45 días──► MAGA  (Cofaloza, Suizo, Del Sud)
PROVEEDORES DE INSUMOS ──con cheque──► MAGA
```

### Plazos reales

| Quién | A quién | Plazo |
|---|---|---|
| Speedmed | Droguería del Sud | **38 días** |
| Speedmed | Suizo | **45 días** |
| Speedmed | Laboratorios | **30/35/40/45/50/55/60**, algunos **90** |
| MAGA | Suizo y DDS | igual que Speed |
| MAGA | Speedmed | 38 días *(nominal)* |
| Speedmed | **cobra** a farmacias | **~35 días** promedio |

Excepciones: Raspo Munro a 45, cooperativa Mendoza, etc. **El plazo de cada
cliente está en las cuentas a cobrar** — no hay que asumirlo.

> **Generalizable:** los plazos son el dato central y ya están en la planilla del
> cliente. Un motor no debe promediarlos: son un contrato por contraparte.

### Refinanciación (va aparte de la deuda)

Deuda que Speedmed —y algo MAGA— tenía con Droguería del Sud. Se refinanció:
**USD 219.000 por mes**. Se hace un cheque, se retira en efectivo, DDS manda una
financiera y se lo lleva en pesos.

Va aparte **porque se paga aparte**, no porque sea menos real.

---

## 3 · Los pagos que no pasan por el banco

Esto es lo que hace que el Cash nunca cierre contra el resultado, y **está bien
que sea así**.

### Notas de crédito (NCR)

| | |
|---|---|
| **En Speedmed** | Acuerdo comercial con DDS: **descuento por volumen**. No dependen de nada más. |
| **En MAGA** | Las **obras sociales pagan una parte en notas de crédito**. PAMI paga una parte en DDS y otra en Suizo. Son **bonificaciones**. |

> **Esto es enorme y yo no lo tenía:** el cobro de MAGA a una obra social se
> materializa como **menos deuda con la droguería**, no como plata en el banco.
> Un ingreso que nunca toca la caja.

### Endoso de cheques

A mano y por decisión: *"si recibimos un cheque de Suizo de 100, le debemos 250
hace dos semanas, y esos 100 no los necesitamos para lo inmediato, se endosa y
listo."*

### Compensación

| Con quién | Cómo |
|---|---|
| **Cofaloza** | Compensa cuentas a cobrar de **Speedmed** contra deuda de **MAGA** (le compra a Speed y le vende a MAGA). Baja las dos a la vez, en empresas distintas. |
| **DDS** | Compensación **semanal** con Speedmed: se paga o se cobra **la diferencia**. Si Speed tiene más a cobrar que la deuda de las dos juntas, el sobrante compensa a MAGA. |

Qué empresa termina pagando **depende de a quién le dé a favor esa semana**.

> **Generalizable:** cuando una contraparte es cliente *y* proveedor, deuda y
> cobranza no son dos números independientes. Y la compensación puede cruzar
> entre empresas del grupo.

---

## 4 · De dónde entra la plata

| Fuente | Monto | Predecible |
|---|---|---|
| Mostrador (efectivo + Mercado Pago) | $2.300–2.700M | ✅ sí |
| Obras sociales | $500–800M | ✅ salvo PAMI |
| Notas de crédito de obras sociales | ~$510M | ✅ pero **no es caja** |

- **Mercado Pago:** acredita **al día siguiente** (según forma de pago del cliente).
- **OSDE y la mayoría:** 30 días, **alrededor del 15 de cada mes**.
- **PAMI:** *"indescifrable"*. Debería pagar a 45 días por presentación. **Es gran
  parte del negocio y es lo único que no se puede proyectar.**
- **Cartera de CH** (cheques a favor de Speedmed): si el estado es **depositado**
  se vuelve caja; si es **endosado**, baja deuda.

> **El riesgo real del negocio tiene nombre: PAMI.** Es grande e impredecible.
> Todo lo demás se proyecta bien.

---

## 5 · La caja

- **5 bancos**, todas las farmacias tienen cuenta en todos. El que más se usa es
  **Galicia**.
- **FIMA** = la cuenta remunerada de Galicia.
- **Efectivo:** se guarda los días previos a una salida grande (sueldos en
  efectivo, honorarios DJ). Si no, se deposita.
- **Las líneas de financiamiento bancario están agotadas.** Y hay una preferencia
  deliberada: **apalancarse con proveedores antes que con el banco.**

> **Generalizable y central:** en este negocio el crédito bancario no es la
> palanca. **El proveedor es la línea de crédito.**

---

## 6 · Cómo se decide

**La decisión que más se repite:** *"¿cuánto le pago a las droguerías que le
debo?"*

Después: cuándo conviene pagar la refinanciación, y si conviene compensar con
Speed o que le paguen.

### "Estar apretado"

Para Thomas, **menos de $50M**. Pero es una sensación, no una regla:

> *"podés tener un cobro al día siguiente y con ese cobro decidir no pagarle a
> las droguerías y te financiás con eso."*

### Qué pasa si no pagás

**Nada inmediato.** Después de un tiempo te **bloquean la compra**, pero hay
**entre 1 y 3 semanas de tolerancia**.

### Lo único intocable

> *"Un cheque no puede rebotar. No es un escenario que se permite."*
> *"Nunca quedarte sin la plata suficiente para cubrir al otro día los cheques."*

### Los retiros de accionistas

Dos accionistas: **DJ y Adrián**. Se les planteaba así:

> *"Hoy pagamos refinanciación + la cuota del préstamo para el adelantamiento de
> ganancias + ahorramos para la compra del fondo de comercio, y no llegamos con
> las droguerías por X semanas."*

La **compra del fondo de comercio** son **USD 315.000 trimestrales**.

No es que las tres cosas caigan el mismo día, pero sí el mismo mes. Cuando se
juntaban, se informaba: *se puede hacer, siempre y cuando nos atrasemos con las
droguerías y corramos el riesgo de que nos bloqueen.*

> **Ese es el modelo de decisión real, y no es "¿me alcanza?".** Es: *¿cuánto
> atraso con proveedores estoy dispuesto a acumular para hacer esto otro?*

---

## 7 · El calendario

**Vencimientos semanales (religiosos):**

| Día | Qué vence |
|---|---|
| Jueves | **Suizo** |
| Viernes | **DDS** en MAGA y en Speed · **Cofaloza** en MAGA |

Que venzan **no significa que se paguen**: es la fecha del resumen semanal.

**Del mes:** no hay fechas fijas. Sueldos, impuestos, cargas sociales y
alquileres se mueven **entre el 1 y el 15**.

**Estacionalidad: mucha.** Junio (época de resfríos) no se parece a agosto o
septiembre.

---

## 8 · La Posición Consolidada — el faro

Tres escenarios, todos "cobrando y pagando todo en fecha, sin atrasarse un día":

| # | Escenario | Para qué se usa |
|---|---|---|
| 1 | **Sin** pago a droguerías | Cuando el negocio estaba peor: ver si al menos se cubrían los cheques de la semana. |
| 2 | **Con** pago a droguerías | Cómo quedarías si pagaras todo en fecha. |
| 3 | Con pago a droguerías **y MAGA pagándole a Speedmed** | Qué pasaría si Speedmed fuera un proveedor rígido más. **Muestra qué tan rentable es uno del otro.** |

Está linkeada al Cash: se actualiza todo el tiempo.

---

## 9 · Qué de todo esto sirve para OTROS clientes

*Thomas: "no sé, ayudame". Esta sección es mi análisis, sujeto a corrección.*

### El modelo general no es "farmacia". Es **empresa que se financia con sus proveedores.**

| Patrón general (vendible a cualquier PyME) | Específico de farmacias |
|---|---|
| Compra a plazo y vende a plazo → el ciclo nunca cierra en una fecha | PAMI, obras sociales |
| **El proveedor es la línea de crédito**, no el banco | Droguerías por nombre |
| Cada proveedor tiene una **tolerancia de atraso** antes de cortarte | Tolerancia de 1-3 semanas |
| Obligaciones **sin** tolerancia (cheques, sueldos) vs **con** tolerancia | Regulación: 3 farmacias por titular |
| Contrapartes que son cliente **y** proveedor → compensación | Estacionalidad por resfríos |
| Cobros que se materializan **sin tocar la caja** (NCR, endoso) | |
| Retiros de socios que compiten con el pago a proveedores | |
| Un ingreso grande e impredecible que domina el riesgo | *(en farmacias: PAMI)* |

**La pregunta de la primera reunión** —que Thomas no pudo contestar y yo deduzco
de todo lo anterior— no es sobre plazos ni sobre el Excel. Es:

> **"¿A quién le podés pagar tarde, y cuánto, antes de que te corten?"**

Porque ahí está la caja real de una PyME argentina: no en el banco, sino en
cuánto aguantan sus proveedores. Todo lo demás es contabilidad.
