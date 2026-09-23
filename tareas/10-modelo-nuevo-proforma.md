# Tarea 10 — La proyección del modelo nuevo (armada de abajo hacia arriba)
Estado: lista para revisión
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

- Trabajé en el worktree existente `Finnauto-tarea10`, rama `tarea/modelo-nuevo`.
  Cambié sólo los tres archivos permitidos. No leí ni usé `privado/`, datos reales ni servicios
  del cliente. No instalé dependencias.
- En `crear_cash.gs` agregué **`armarModeloNuevo()`**, un punto de entrada independiente:
  crea Supuestos y Modelo Nuevo, conserva lo cargado al rearmar y no ejecuta `armarCash()`.
  No cambié las funciones del cash existente, sus fórmulas ni Plan. No agregué menú porque el
  archivo del menú está fuera del alcance. Se ejecuta desde el selector de Apps Script.
- Supuestos editables sin valores iniciales: volúmenes de doce períodos, precios y condiciones,
  anticipo, packaging, cargas, indemnizaciones, comisiones y base, fletes elegibles, seguros,
  energía, gas, impuestos, imprevistos y stock opcional. Personal admite puestos e incorporaciones
  por rol, bruto/honorario, tipo y mes; requiere confirmar la nómina completa. Inflación es un
  vínculo a **Cash Mensual!B4**, sin escribir ni duplicar el supuesto.
- Agregué cobros y pagos operativos de arranque por período, también vacíos: de otro modo se
  estaría suponiendo que no había operación pendiente antes del modelo. Deben informarse los
  ceros, si corresponden. Exigen también confirmar cobertura de deuda y actualización de caja.
- Modelo con operación arriba, indemnizaciones aparte, capital e intereses automáticos debajo,
  saldo del período, deuda por decisión, segundo saldo y dos acumulados. Lee las dos listas de
  deuda por encabezado, no propone refinanciaciones ni usa estimaciones de Plan. Revisa importes,
  fechas, estados y débito; los vacíos no se convierten en cero. Caja usa la última foto por
  banco + empresa + cuenta hasta hoy y expone la fecha más antigua utilizada.
- La fila superior lista faltantes concretos, con detalle por renglón al pie. Los bloques
  incompletos y sus saldos muestran **—**; los ceros explícitos o calculables se ven como 0,00.
  Calcula capital de trabajo por días de cobro, pago y stock, y muestra por separado cuentas a
  cobrar/pagar generadas por el modelo que quedan pendientes al cierre.
- En `manual_cash.md`, §8, dejé las fórmulas explicadas en criollo, el ejemplo ficticio completo
  de septiembre/octubre (cada renglón), el guion de prueba en Sheets y los pasos previos a adoptar
  este modelo como base del mensual. La propia pantalla incluye un guion corto de prueba.

### Qué comprobé

- Ejecuté el JavaScript del archivo con JavaScriptCore mediante `osascript`, con una imitación
  local de las operaciones de Sheet: sintaxis, creación de las dos hojas, supuestos inicialmente
  vacíos y conservación de precio y puesto cargados al repetir armado. Esa ejecución no accedió
  a Google ni automatizó una aplicación. Sólo creó archivos temporales en `/tmp`.
- Analicé las fórmulas generadas y las evalué con un evaluador local acotado a las funciones usadas.
  Contrasté **cada renglón calculado de los primeros dos meses** contra las cuentas independientes
  del ejemplo del manual, incluidos resultados, deuda, caja acumulada y capital de trabajo.
- Verifiqué vacíos frente a cero, dependencia entre períodos, plazo 0/15/30/75/400 días, anticipo,
  mes parcial y febrero bisiesto contra una simulación diaria independiente en las doce columnas.
  También bases de comisión y flete, inflación, stock opcional, personal incompleto y mes
  fraccionario, imprevistos inválidos, deuda pagada y deuda sin interés/débito informado.
- Probé las fórmulas de caja con varias cuentas y empresas del mismo banco, fechas distintas,
  importe vacío, foto duplicada y confirmación faltante. Probé que la fila superior nombre
  supuestos concretos. `git diff --check` pasó. No agregué nombres de personas en el código ni
  en el texto para la planilla.
- **No ejecuté Apps Script ni abrí la Sheet real.** El evaluador y la imitación local no prueban
  el motor de Google: quedan pendientes separador es_AR, funciones matriciales LET/MAP, tiempos
  de recálculo, validaciones reales y presentación visual. Los scripts de comprobación quedaron
  temporales en `/tmp`, fuera del repo; el guion reproducible de aceptación está en el manual.

### Convenciones y límites para revisar

- Doce períodos desde mañana: el primero puede ser parcial. Las fechas avanzan con hoy; hay que
  mantener cantidades y pendientes de arranque y guardar una copia fechada para negociar.
- Ventas/compras parejas dentro de cada período; inflación común desde el primer período;
  importes mensuales prorrateados si el primero es parcial. No se inventaron fechas de cobro
  individuales ni tasas de deuda. El ejemplo numérico sólo vive en documentación y pruebas.
- El anticipo se paga al inicio del período de compra, no meses antes. El stock opcional calcula
  necesidad de capital, no un calendario de compras para constituirlo. El neto de capital de
  trabajo es orientativo al ritmo del período y **no** vuelve a descontarse de caja. Sin días de
  stock se indica expresamente que falta ese componente.
- No hay calendario de aguinaldos/bajas ni refinanciación del vencido: si hacen falta, deben
  acordarse antes de usar la proyección para esa transición. Deuda vencida antes del horizonte
  no entra como un pago nuevo sin fecha acordada. El manual explica estas limitaciones.
- **Sin commit por restricción del sandbox.** Intenté `git add` de los tres archivos y Git
  respondió `Operation not permitted` al crear
  `/Users/thomasmanzo/Documents/Finnauto/.git/worktrees/Finnauto-tarea10/index.lock`.
  El índice está fuera de las rutas permitidas. Los cambios quedan sin stage en este worktree;
  corresponde hacer el commit desde un entorno con acceso, como prevé `tareas/LEEME.md`.

## Revisión
