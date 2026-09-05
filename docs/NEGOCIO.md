# El negocio — lo que hay que entender antes de tocar código

> Este archivo existe porque el 05/09/2026 perdimos un día entero en correcciones
> que salían todas del mismo lugar: yo no entendía el negocio. El caso testigo
> fue tratar a MAGA (farmacia, **compra**) y a Speedmed (droguería, **compra y
> vende**) como si fueran lo mismo.
>
> Thomas: *"pensémoslo como una empresa: vos ponés el código que yo no sé, yo el
> conocimiento en finanzas y en el negocio que vos no tenés."*
>
> Acá se anotan las respuestas. **Si algo no está acá, no se asume: se pregunta.**
> Y si algo está acá, se asume sin volver a preguntar.

---

## Lo que YA sé (confirmado por Thomas, no re-preguntar)

| # | Hecho | Cuándo se aclaró |
|---|---|---|
| 1 | **MAGA es farmacia**: le compra a las droguerías, no les vende. Tiene deuda con ellas, no cuentas a cobrar. | 05/09 |
| 2 | **Speedmed es droguería**: les compra y les vende. Tiene las dos cosas. | 05/09 |
| 3 | El dueño es el mismo pero **son negocios distintos**. Nunca consolidar en un solo número. | 05/09 |
| 4 | Un período de 45 días **no está cerrado**: se paga a 30/45/60 y se cobra a 30/45/60. Por eso importa el timeline, no el saldo final. | 05/09 |
| 5 | Muchas compras a droguerías **se cancelan sin pasar por el banco**: notas de crédito, endoso de cheques, compensación con cuentas a cobrar. El Cash es flujo de caja, no resultado. | 05/09 |
| 6 | Las **NCR restan** a la deuda, estén cargadas como estén en la planilla. | 05/09 |
| 7 | La deuda a droguerías que Thomas cuenta son **solo las filas de droguerías**: sin NCR y sin `REFINANCIACION`. | 05/09 |
| 8 | **"DJ" = D.Jaimovich**. Sus honorarios son el 10% del resultado del mes anterior: **fecha fija, monto variable**. | 04/09 |
| 9 | Una fecha pasada significa lo **opuesto** según el bloque: en cobranza = vencido (no cobramos); en deuda = ya se pagó. | 03/09 |
| 10 | Los **cheques y los sueldos** son los dos únicos que no se pueden patear. Cheque impago = BCRA. | 03/09 |
| 11 | **Adelantar cobros no es una palanca** en este rubro: es muy difícil. | 04/09 |
| 12 | Transferencias y depósitos entre cuentas propias son **internos**: no mueven la caja del grupo. | 03/09 |
| 13 | El "faro" para saber si un número da o no da es la solapa **Posición Consolidada** (hay dos versiones: con y sin que MAGA le pague a Speed). | 05/09 |

---

## Lo que falta (las preguntas)

*Se completan a medida que Thomas contesta. Cada respuesta pasa arriba, a la
tabla de hechos confirmados.*

### A · Estructura del grupo

- [ ] **A1** ¿Cuántas empresas hay y cuál es cuál? (MAGA+, MAGA, Speedmed, ¿otras?)
- [ ] **A2** Las 14 farmacias, ¿son 14 razones sociales o una sola con 14 locales?
- [ ] **A3** ¿Qué diferencia hay entre "MAGA" y "MAGA+"?
- [ ] **A4** ¿Qué es Quintana? (aparece como `SUELDO_QUINTANA` y `ALQUILER QUINTANA`)
- [ ] **A5** ¿Speedmed le vende a las farmacias del grupo? ¿Eso es la deuda intercompany?

### B · El circuito comercial

- [ ] **B1** ¿A quién le compra Speedmed y a quién le vende?
- [ ] **B2** Las farmacias del grupo, ¿le compran a Speedmed, directo a droguerías, o las dos?
- [ ] **B3** ¿Qué son DDS, Suizo y Cofaloza exactamente?
- [ ] **B4** ¿A cuántos días compra Speed y a cuántos cobra?
- [ ] **B5** ¿Qué es `REFINANCIACION` y por qué va aparte de la deuda?

### C · Los pagos que no pasan por el banco

- [ ] **C1** ¿Cómo se generan las NCR? ¿Descuentos, devoluciones, bonificaciones?
- [ ] **C2** ¿Cuándo se paga endosando un cheque en vez de transferir?
- [ ] **C3** ¿Cómo funciona compensar con una droguería que es cliente y proveedor a la vez?
- [ ] **C4** ¿Qué proporción de las compras se cancela por fuera de la caja?

### D · Los ingresos

- [ ] **D1** ¿De dónde entra la plata en una farmacia y en qué proporción?
- [ ] **D2** ¿A cuántos días acredita tarjeta / Mercado Pago?
- [ ] **D3** ¿Qué es "Cartera de CH" y cuándo se vuelve caja?
- [ ] **D4** ¿Cada cuánto y con qué plazo paga PAMI? ¿Y las obras sociales?
- [ ] **D5** ¿Qué parte de la venta es realmente predecible?

### E · La caja

- [ ] **E1** ¿Por qué hay 5 bancos? ¿Cada farmacia tiene cuenta en varios?
- [ ] **E2** ¿Qué es FIMA y para qué se usa?
- [ ] **E3** ¿Para qué se guarda efectivo y cuánto es lo normal?
- [ ] **E4** ¿Hay descubierto o líneas de crédito disponibles?

### F · Las decisiones

- [ ] **F1** ¿Qué es lo primero que mirás cuando abrís el Cash a la mañana?
- [ ] **F2** ¿Cuál es la decisión que más se repite en la semana?
- [ ] **F3** ¿Qué significa "estar apretado"? ¿Un número concreto?
- [ ] **F4** ¿Quién decide qué se paga y qué se patea?
- [ ] **F5** ¿Qué mirás para decidir si se puede retirar plata?

### G · El calendario

- [ ] **G1** ¿Qué pasa cada día de la semana? (¿los lunes cobranzas, los viernes droguerías?)
- [ ] **G2** ¿Qué fechas fijas tiene el mes?
- [ ] **G3** ¿Hay estacionalidad en la venta?

### H · Los límites

- [ ] **H1** ¿Qué pasa concretamente si no le pagás a una droguería?
- [ ] **H2** ¿Qué pasa si rebota un cheque, más allá del BCRA?
- [ ] **H3** ¿Qué es lo que nunca hay que hacer?

### I · La Posición Consolidada

- [ ] **I1** ¿Qué muestra exactamente y cómo se lee?
- [ ] **I2** ¿Qué significa "con que MAGA le pague a Speed"? ¿Cuál de las dos versiones es la que decide?
- [ ] **I3** ¿Con qué frecuencia se actualiza?

### J · Para los próximos clientes

- [ ] **J1** ¿A qué tipo de empresas apuntás además de farmacias?
- [ ] **J2** De todo esto, ¿qué es propio de farmacias y qué le sirve a cualquier PyME?
- [ ] **J3** ¿Qué pregunta le harías vos a un cliente nuevo en la primera reunión?
