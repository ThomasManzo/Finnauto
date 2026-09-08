# Backlog de ideas — finauto

Ideas que fueron saliendo en las charlas con Thomas. No están ordenadas por prioridad
sino por cuánto diferencian al producto.

---

## 1. Reconocedor de planillas (el motor de onboarding) ⭐

**Idea de Thomas (2026-09-04).** Hoy el exportador va a buscar cosas que ya sabe que
existen (la tabla de MOVIMIENTOS, la grilla de SALDOS). Para MAGA alcanza, porque
conocemos su Cash. **Pero para un cliente nuevo que no conocemos, no.**

La idea: un **reconocedor** que abre la planilla de cualquier cliente, **recorre TODAS
las solapas** y deduce solo el modelo de datos.

Qué haría:
- Lista todas las solapas con sus dimensiones.
- Por cada una: encuentra dónde está la fila de encabezado, qué columnas tiene y una
  muestra de valores.
- **Clasifica cada solapa**: "esto parece una tabla de movimientos" (tiene fecha +
  importe + un campo tipo), "esto parece una grilla de saldos" (nombres en la columna A,
  bancos en la fila 1), "esto parece un cashflow" (fechas como columnas), "no la reconozco".
- **Deduce el vocabulario solo**: junta los valores distintos de cada columna categórica
  y arma la lista de tipos, bancos y unidades del cliente.
- Emite un borrador de `catalogo.json` + el mapeo de solapas, para que un humano lo
  confirme o corrija.

**Por qué vale tanto:** el `catalogo.json` de MAGA lo escribimos a mano, a lo largo de
varias charlas. Con el reconocedor, eso se genera solo en minutos. Es la diferencia entre
"cada cliente nuevo son dos semanas de configuración" y "cada cliente nuevo son 20
minutos y una revisión". **Es el cuello de botella de la escalabilidad del negocio.**

---

## 2. "¿Qué pateo?" — que además de informar, aconseje ⭐

Hoy el simulador avisa que faltan $X. El paso siguiente es que **diga qué hacer**:
ordenar los egresos por `dias_tolerancia` y proponer *"pateá el retiro de socios y el
pago al proveedor X unos días y te cierra"*.

Ampliación de Thomas: que **mire hacia adelante**, no solo la semana en curso —
*"esta semana estás complicado, pero la que viene entra esto y esto; pateá esto unos
días y te cierra mejor"*.

Para esto hay que **modelar la lógica de decisión de Thomas**: él se ofreció a
responder preguntas con opciones para ir codificando cómo decide. Es lo que convierte
la herramienta en un asesor y no en un tablero.

---

## 3. Calibración automática (el sistema aprende solo) ⭐

Guardar lo proyectado vs. lo que realmente entró/salió. Con unos meses de historia, el
motor ajusta solo: *"las obras sociales entran en promedio 4 días más tarde de lo
estimado"*, *"la venta diaria se subestima un 6%"*.

**Por qué importa:** las proyecciones mejoran sin que nadie afine nada a mano, el
producto vale más con el tiempo, y se vuelve difícil de abandonar. Thomas lo ve como un
diferenciador central: "que el motor vaya entendiendo qué hay detrás de cada cosa".

---

## 4. Alertas en vez de tablero

El dueño no abre nada; le llega el aviso: *"el jueves te quedás corto por $X"*,
*"mañana vencen 3 cheques por $Y"*, *"se ajustó la proyección de OS"*.

El tablero es para cuando querés mirar; **la alerta es para cuando no estás mirando**.
Para un dueño que no abre planillas, vale más que cualquier gráfico.

---

## 5. Que el bot baje el listado de cheques

El listado de cheques emitidos se baja **a mano todas las semanas** del home banking y
se cruza con BUSCARV. El parser (`ingestas/cheques.py`) ya resuelve el cruce, pero la
descarga sigue siendo manual.

**El bot de Galicia ya entra al banco todos los días.** Sumarle la descarga de ese
listado es prácticamente el mismo trabajo que ya hace con los extractos, y cierra el
circuito del intocable más peligroso (si no se cubre un cheque, la empresa va al BCRA).

---

## 6. Automatizar el cruce de cuentas a cobrar (RAL)

Todos los lunes se baja un listado de RAL (clientes, fechas, vencimientos, montos) y se
cruza con BUSCARV contra las cuentas a cobrar. **RAL solo funciona dentro de la red**,
así que la descarga difícilmente se pueda automatizar — **pero el cruce sí**: mismo
patrón que el parser de cheques (dedupe + sumar lo que no cruza).

Lo mismo aplica a **Cartera de CH**, que hoy se carga a mano y son ingresos con fecha
cierta.

---

## 7. Roles: cada usuario su vista

El administrativo carga en la planilla que ya conoce (cero fricción); el dueño ve el
tablero y las alertas. **Mismo dato abajo, distinta interfaz arriba.** Es la forma de
no perder a ninguno de los dos — el error clásico de los proyectos de automatización.

---

## 8. Proyección de cobranza de obras sociales (Zetti) ⭐⭐

**Idea de Thomas (2026-09-08), y la que más diferencia de todo el backlog.**

Una farmacia vende y cobra tres veces: el mostrador (hoy), la tarjeta (a días) y
**la obra social (cuando quiera)**. La tercera es la que rompe la caja, y es la
única que nadie proyecta bien — porque proyectarla no es leer un vencimiento, es
saber **cuánto tarda de verdad cada obra social en pagar, y cuánto de lo
presentado termina débito**.

Thomas tiene las dos cosas que hacen falta y que un competidor no puede comprar:

- el **histórico de cobros de MAGA+ con obras sociales**
- una planilla grande con el **modelo de cobranzas de OS de FARMA24**

### La distinción que ordena esto

**Zetti es una fuente de datos. La proyección es el producto.**

El valor no está en conectarse a Zetti: está en poder decirle a un dueño *"OSDE
te paga a 62 días, no a los 30 que dice el convenio, y te debita el 4%"*. Eso se
puede demostrar **hoy**, con un export del histórico a mano, sin tocar Zetti.

Por eso el orden es: primero la proyección sobre el histórico exportado; recién
si demuestra valor, automatizar la ingesta. Al revés — conector primero — se
paga la parte más difícil antes de saber si la fácil valía algo.

### Lo que habría que medir del histórico

- días reales entre presentación y cobro, por obra social (mediana, no promedio:
  un pago atrasado seis meses no describe al resto)
- **porcentaje de débito** por obra social: lo presentado que nunca se cobra
- estacionalidad y cortes (PAMI paga mínimo dos veces al mes — ¿cuándo?)

Y después, lo mismo que hace `memoria/`: proyectar, guardar, y a los dos meses
poder decir cuánto le erró. Es la idea 3 aplicada a la cobranza.

---

## 9. Aviso diario (WhatsApp / mail)

**Idea de Thomas (2026-09-08).** Todos los días a la mañana, un mensaje al dueño
y al tesorero: *"Hoy tenés 5 cheques por $X. Hay $Y en las cuentas. Faltan $Z"*.

Es la idea 4 con canal y horario. Y el costo es bajísimo **porque el número ya
está calculado**: la cadena corre todos los días a las 8:00 y deja el tablero
armado. Falta el último tramo, mandar tres líneas.

**Una corrección al plan, para no descubrirla a mitad de camino:** la API de
WhatsApp *no* es simple de arrancar. Es cuenta de Meta Business, un proveedor
(Twilio, 360dialog), y **plantillas que Meta tiene que aprobar** — fuera de una
ventana de 24hs no se puede mandar texto libre. Días de trámite, y se paga por
mensaje.

Entonces: **primero por mail**, que es gratis y sale el mismo día que se decida.
Si el cliente lo lee todas las mañanas, el trámite de WhatsApp está justificado
por algo probado. Si no lo lee, el canal no era el problema.

---

## 10. Valor presente: qué vale hoy lo que te van a pagar en 60 días

**Idea de Thomas (2026-09-08).** Un toggle en el tablero que muestre las cuentas
a cobrar futuras descontadas a valor presente, o expresadas en dólar MEP.

Con inflación, que una obra social pague a 60 días no es una demora: es una
**quita**, y nadie la ve porque el monto nominal no cambia. Poner los dos
números al lado convierte "cobramos tarde" en un costo con signo pesos.

**Es la más barata de todas:** la cartera ya tiene fecha e importe, descontar es
una fórmula, y no hace falta ningún dato nuevo. Único cuidado: la tasa es un
supuesto y tiene que verse como supuesto — editable y a la vista, no escondida
en el código.

---

## 11. Alerta temprana de cheque rechazado

**Idea de Thomas (2026-09-08).** Si el bot detecta en el extracto la leyenda de
un rechazo (sin fondos, defecto formal), que dispare aviso inmediato a
cobranzas. Cuanto antes se sabe, antes se reclama el reemplazo.

Encaja con lo que ya existe — el bot entra al banco todos los días — pero
depende de un dato que hay que verificar primero: **si el extracto que baja trae
la descripción del movimiento** con la leyenda, o solo importe y fecha. Media
hora de mirar un extracto real contesta si esto es una tarde o un proyecto.

---

## 12. Proyección de IVA e Ingresos Brutos ⚠

**Idea de Thomas (2026-09-08).** Avisar antes de fin de mes cuánto va a haber que
pagar de impuestos, en vez de enterarse el día que avisa el contador.

El dolor es real y está bien identificado. **Pero hay una objeción que conviene
tener escrita antes de prometerlo:**

El motor lee un **cashflow**, no el libro de IVA. La base imponible no está en
lo que entró y salió de la caja: está en lo **facturado** (IVA débito) y en el
**crédito fiscal de las compras**, que son otra cosa y viven en otro lado —
sistema de gestión y contador. Estimarlo desde la caja da un número parecido y
equivocado.

Y equivocarse acá pesa distinto que en el resto del producto: un tablero que
proyecta mal se corrige; un número de impuestos que el cliente usó para
planificar es un problema de él y una responsabilidad tuya.

**Si se hace, se hace con la fuente correcta** (el libro de IVA o el sistema de
gestión) y rotulado como estimación. Antes de eso, no.
