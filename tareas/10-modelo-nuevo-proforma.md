# Tarea 10 — La proyección del modelo nuevo (armada de abajo hacia arriba)
Estado: pendiente
Rama: tarea/modelo-nuevo

## Objetivo

Armar en la planilla la **estructura vacía** de una proyección a 12 meses del **modelo operativo
nuevo** de la empresa: cada supuesto en una celda editable, y la proyección calculada a partir de
esos supuestos. Hoy no tenemos los números; el punto de esta tarea es que **cuando lleguen, se
carguen y salga sola**, y que mientras tanto quede a la vista qué falta.

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `CLAUDE.md`, `clientes/navar/LEEME.md` y
`clientes/navar/documentos/manual_cash.md` (§2, §3 y §4).

**Por qué hace falta.** Las tres pantallas actuales proyectan con el **promedio de los últimos tres
meses × inflación**. Eso sirve para las próximas semanas, pero asume la empresa funcionando como
viene: con cosecha propia y la dotación actual. La empresa está cambiando de modelo: deja de
cosechar y secar, pasa a **comprar canchada y vender molida**, con una estructura más chica y un
equipo comercial nuevo. Para eso hay que proyectar de abajo hacia arriba, renglón por renglón.

Pedido de la dirección (23/09), resumido: proyectar sólo la planilla de sueldos y honorarios del
personal que queda (incluidas las incorporaciones necesarias, por ejemplo el comercial y los
vendedores), los costos de indemnización, la compra de canchada y los insumos de packaging para
las ventas proyectadas, las comisiones de vendedores, los fletes, los seguros, los impuestos, los
servicios públicos (energía y gas) y **una provisión acotada como % del total** para gastos menores
e imprevistos. Hasta ahí la parte operativa. **Por debajo de esa línea**, la parte financiera: los
pagos proyectados de capital e intereses. El resultado esperado es negativo, y ese número es la
base para mostrarle a las familias y para negociar con los acreedores.

**La estructura ya existe y no se rediseña**: el cash v5 ya separa `Resultado de la operación
(antes de la deuda)` de la deuda, y la deuda en "sale sí o sí" y "por decisión", con dos saldos al
cierre. Esta proyección tiene que respetar exactamente ese esqueleto, para que se lea igual.

## Archivos permitidos

- `clientes/navar/herramientas/crear_cash.gs`
- `clientes/navar/documentos/manual_cash.md`
- `tareas/10-modelo-nuevo-proforma.md`

No tocar los lectores, `importar_cashflow.gs`, `dashboard/` ni `finauto.py`.

## Resultado esperado

Dos solapas nuevas, armadas por el script (como se arman hoy Cash / Plan / Instrucciones):

### 1 · `Supuestos`

Una fila por supuesto, con: **qué es · unidad · valor (celda editable, VACÍA) · quién lo provee ·
nota**. Agrupados por bloque. Como mínimo:

- **Ventas**: kilos por mes (una celda por mes, para poder poner estacionalidad) · precio por kilo ·
  condición de cobro (días).
- **Canchada**: precio por kilo · kilos de canchada por kilo vendido (rendimiento) · **condición de
  pago (días)** · si hay anticipos.
- **Packaging**: costo por kilo vendido.
- **Personal**: una fila por puesto que queda (sueldo bruto mensual) y una por incorporación
  prevista, con el mes en que entra. Cargas sociales como % sobre el bruto.
- **Indemnizaciones**: importe total y **en qué mes se paga** (si se paga en cuotas, cuántas).
- **Comercial**: comisión (%) y sobre qué base (venta facturada o cobrada).
- **Fletes**: $/kg o % sobre la venta (que se pueda elegir cuál).
- **Seguros**, **energía**, **gas**: importe mensual.
- **Imprevistos**: % sobre el total de egresos operativos.
- **Inflación mensual**: reusar la celda que ya existe, no crear otra.

**Ninguna celda arranca con un número inventado.** Vacío significa "falta el dato", y la proyección
tiene que **decirlo** (ver abajo), no tratarlo como cero.

### 2 · `Modelo Nuevo`

12 meses en columnas, con el mismo esqueleto que las otras pantallas:

```
Ventas (kg · $)
1 · Ingresos                      cobranza según la condición de cobro
2 · Egresos de la operación       canchada (según su condición de pago) · packaging · sueldos y
                                  cargas · comisiones · fletes · seguros · energía y gas ·
                                  impuestos · imprevistos (%)
Resultado de la operación (antes de la deuda)
3 · Indemnizaciones               aparte: es por única vez, no es operación corriente
4 · Deuda que sale sí o sí        capital + intereses, del cronograma de Deuda Bancaria
SALDO DEL PERÍODO pagando solo lo automático
5 · Deuda que se paga por decisión
SALDO DEL PERÍODO pagando toda la deuda
Saldo acumulado                   arrastra de mes a mes; parte del saldo real de hoy
Capital de trabajo                ver abajo
```

- **La deuda no se estima**: sale del cronograma real de Deuda Bancaria y Deuda Impositiva, igual
  que en Cash Mensual, respetando la columna `Debito Automatico`.
- **Capital de trabajo**: calcularlo explícitamente a partir de las condiciones cargadas
  (días de cobro, días de pago, días de stock si se carga), no como un número suelto. Que se vea
  **cuánta plata queda atrapada** en el ciclo: es la mitad de la respuesta que busca la dirección.
- **Fila "Faltan datos"** arriba de todo: lista los supuestos vacíos que impiden que el mes cierre.
  Mientras haya alguno, los totales de ese bloque se muestran como `—`, **nunca como 0**. Un cero
  se lee como "no hay gasto" y acá significa "no lo sabemos".

### 3 · Cómo se conecta con el cash de hoy

**No pisar** Cash, Cash Semanal ni Cash Mensual: el modelo nuevo es una pantalla aparte. En el
manual, explicar en criollo la diferencia: una proyecta lo que viene según lo que vino (sirve para
la semana que viene), la otra proyecta el modelo nuevo según supuestos (sirve para decidir y
negociar). Dejar anotado qué haría falta para que, cuando el modelo nuevo se confirme, pase a ser
la base del mensual.

## Comprobaciones

Apps Script no corre en el worktree:

1. Explicar en criollo cómo quedó armada cada fórmula importante (cobranza según días, canchada
   según rendimiento y días de pago, capital de trabajo).
2. Dejar un ejemplo numérico hecho a mano: con supuestos inventados simples (por ejemplo 100.000 kg
   a $1.000, canchada 0,7 kg por kg a $500 pagada a 30 días), qué tendría que dar cada renglón el
   primer y el segundo mes. Sirve para que el revisor verifique leyendo.
3. Dejar el guion de prueba en la planilla: qué correr, qué mirar, qué tendría que pasar al llenar
   un supuesto y al vaciarlo.
4. **Sin nombres propios** de personas en las solapas ni en el código: roles.
5. Commit en la rama; si el sandbox no deja, anotarlo.

## Qué hice

## Revisión
