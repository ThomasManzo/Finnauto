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
