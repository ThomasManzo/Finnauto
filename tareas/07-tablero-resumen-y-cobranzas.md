# Tarea 07 — Tablero: el día por día está incompleto, y falta el cuadro de vencidos
Estado: lista para revisión
Rama: tarea/tablero-resumen

## Objetivo

Tres cosas sobre el tablero web (`finauto.html`), en orden:

**A (BUG).** El día por día de cobranzas está incompleto: **saltan días**. Thomas (22/09): *"las
cuentas a pagar en el tablero está mal lo que entra día por día... saltan las cobranzas del 28 al
05/10"*. Además **sigue apareciendo "cobranza proyectada" de A y AA**, que es una estimación vieja
que ya se dio de baja, y hay cobranzas que no figuran. Hay que hacer que **entre todo** lo que
corresponde y que no entre lo que no.

**B.** En la pantalla **Posición**, además de lo vencido con proveedores, un **cuadro aparte con lo
vencido de las tres puntas: ARCA (impuestos), bancos y proveedores.** Es lo primero que preguntan.

**C (criterio general).** El tablero tiene que mostrar, resumido y claro, **lo que el cash no
alcanza a mostrar por sí solo o cuesta entender mirando la planilla**. No es una copia del cash con
otro color: es el resumen que se muestra en una reunión. Con ese criterio, proponé (y aplicá, si es
evidente) qué sacar de lo que hoy ocupa lugar sin decir nada.

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `CLAUDE.md`, `clientes/navar/LEEME.md` y
`clientes/navar/documentos/manual_cash.md`.

El tablero se arma con `dashboard/app.py` (HTML + JS en un archivo, sin librerías) sobre los datos
que prepara `dashboard/datos.py`, a partir de un contrato JSON que genera `lector/cash_limpio.py`
desde el export de la planilla. Capas actuales: Posición · A quién pagar · A cobrar · Proyección ·
Hallazgos (`CAPAS` en `app.py`).

Para reproducir (rutas absolutas; el contrato se lee, no se toca):

```
python finauto.py --contrato /Users/thomasmanzo/Documents/Finnauto/clientes/navar/contrato_2026-09-22.json --cliente navar --salidas <carpeta temporal tuya>
```

**Escribir las salidas a una carpeta temporal**, nunca a `clientes/navar/privado/salidas/`.

### Sobre A, para que no busques a ciegas

En el contrato hay varias listas de entrada de plata y cada una se suma en un lugar distinto
(`cobros_previstos`, `cuentas_a_cobrar_droguerias`, `cartera_cheques`...). La regla está escrita en
la cabecera de `lector/cash_limpio.py`: **si un cobro cae en dos listas se cuenta dos veces; si no
cae en ninguna, desaparece**. El síntoma de días salteados apunta a cobros que quedan fuera del
armado del día por día (filtrados por fecha, por estado, o por una categoría que no está mapeada).

Ojo con esto, que ya pasó hoy: la categoría `Cobranza AA` no estaba en
`clientes/navar/catalogo.json → mapa_categorias` y $520 M entraban como `SIN_MAPEAR`. Se arregló.
Revisá si hay otras categorías en la misma situación, y si el día por día las está tomando.

Sobre la **"cobranza proyectada"**: es la estimación por kg del cash viejo, que nunca se cumplía
(está documentado en `catalogo.json`, fuente `COBRANZA_PROYECTADA`, y en el LEEME). Se dio de baja.
Si sigue apareciendo en el tablero, hay que sacarla **o** dejarla claramente marcada como estimación
que no suma. Decidí y explicá cuál de las dos.

### Sobre B

Los tres números ya existen en el contrato / en los datos del tablero: vencido de proveedores
(Cuentas a Pagar), vencido impositivo (Deuda Impositiva) y cuotas bancarias vencidas e impagas
(Deuda Bancaria). El vencido total al 22/09 ronda los **$431 M**; el cuadro tiene que sumar
exactamente lo que el tablero ya informa como vencido, sin inventar una cuenta nueva.

Para cada una de las tres puntas mostrar, como mínimo: cuánto, desde cuándo (lo más viejo) y qué
pasa si no se paga (ARCA embarga cuentas; los bancos cortan las líneas que financian la caja; los
proveedores cortan la entrega). Esa última columna es lo que hace útil el cuadro.

La tarea 04 ya agregó a la Proyección el desglose por **débito automático vs por decisión** y por
banco: reusá ese trabajo, no lo dupliques.

## Archivos permitidos

- `dashboard/app.py`, `dashboard/datos.py`
- `clientes/navar/catalogo.json` — **solo** si aparece otra categoría sin mapear (agregar el mapeo,
  nada más).
- `clientes/navar/documentos/manual_cash.md` — si hace falta.
- `tareas/07-tablero-resumen-y-cobranzas.md`

No tocar `crear_cash.gs` (tarea 06), `importar_cashflow.gs` (tarea 05) ni los lectores.

## Comprobaciones

1. **A**: listar los días del período con cobranza esperada y mostrar que ya no hay huecos.
   Decir **cuál era la causa** de los días salteados, con la línea de código.
2. **Cuadre**: el total de cobranzas del día por día tiene que coincidir con el total que informa
   el tablero. Pegar los dos números.
3. **B**: los tres vencidos y su suma, contra el vencido total que ya informa el tablero. Si no
   cuadra, **no maquillarlo**: decir por qué no cuadra.
4. Regenerar el tablero a una carpeta temporal y revisarlo de verdad antes de darlo por hecho.
5. `grep` de nombres propios vacío. Commit en la rama.

## Qué hice

### Alcance y cambios

- Trabajé en el worktree existente, rama `tarea/tablero-resumen`. Solo cambié
  `dashboard/datos.py`, `dashboard/app.py` y esta consigna. No accedí a `privado/`,
  no modifiqué el contrato suministrado ni instalé dependencias.
- **Causa comprobada de A:** en la versión inicial, `dashboard/datos.py:420`
  recorría únicamente `contrato.get("cobros_previstos", [])` dentro de
  `ingresos_por_dia`. Las facturas de `cuentas_a_cobrar_droguerias` no entraban.
  Además, `dias_ord = sorted(por_dia)` (línea original 440) omitía los días vacíos.
  La ventana inclusiva terminaba en hoy + 30: eran 31 días, no 30.
- Ahora gráfico y proyección usan la misma cuenta diaria, con 30 fechas consecutivas
  del 22/09 al 21/10 inclusive. Se suman movimientos y facturas pendientes por empresa,
  sin internos/intercompany; se conserva el signo del importe (un crédito no se convierte
  en un ingreso positivo). La curva conserva su horizonte de 45 días.
- Excluí `COBRANZA_PROYECTADA` en una copia del contrato al entrar a `armar`, solo
  para NAVAR, antes de calcular los distintos bloques. En los 30 días se excluyen
  **$410.235.760,00** de la estimación por kg dada de baja. El contrato original
  sigue intacto. Los consumidores externos a `dashboard.datos.armar` no cambian;
  en particular, esto no corrige el informe separado que genera `finauto.py`.
- Cheques: mantuve la regla existente del tablero (cartera = decisión, no caja).
  El detalle diario muestra **$25.176.181,68** de cartera en el período, aparte del
  total de ingresos, con fechas. No la sumé a la curva ni otra vez a las facturas.
  Se excluyen propios y anulados. La conciliación de cada cheque contra Tango
  requiere datos de origen que no se verificaron aquí.
- No encontré `SIN_MAPEAR` en movimientos, cobros ni egresos del contrato suministrado;
  no fue necesario cambiar el catálogo. Esto no prueba categorías nuevas de otro export.
- **B:** cuadro en Posición para impuestos, bancos y proveedores: monto, fecha más
  antigua y consecuencia operativa de no pagar, expresada como riesgo. Reutiliza
  `proyeccion.vencido_stock.items`; no vuelve a sumar deuda bancaria ni impuestos.
  Se conserva el desglose por débito/banco de tarea 04 en Proyección. Si hubiera
  otros vencidos, se explicita cuánto queda fuera de las tres puntas.
- **C:** saqué la frase genérica del gráfico y puse período y total comprobable.
  El detalle diario queda plegado. Aclaré que el KPI de vencido es de proveedores
  y reemplacé “todavía no aprieta” por su alcance. No retiré el desglose de gastos:
  explica dónde se va la caja. Propongo evaluar con la dirección si conviene plegarlo
  también, después de validar visualmente; no hice una reorganización grande.

### Cuadres contra el contrato del 22/09

| Empresa | Suma diaria, 30 días | Proyección, primeros 30 días | Motor independiente `D.cobros`, mismo período |
|---|---:|---:|---:|
| GRUPO | $318.202.595,02 | $318.202.595,02 | $318.202.595,02 |
| A | $279.673.123,37 | $279.673.123,37 | $279.673.123,37 |
| AA | $38.529.471,65 | $38.529.471,65 | $38.529.471,65 |

Días con ingresos cargados del GRUPO (incluye movimiento real del 22/09, identificado
como real; no se presupone que todo sea facturación futura):

| Fecha | Importe |
|---|---:|
| 22/09 | $12.784.925,64 |
| 23/09 | $34.495.395,24 |
| 25/09 | $7.936.106,45 |
| 27/09 | $22.851.455,87 |
| 28/09 | $96.555.697,98 |
| 29/09 | $3.538.186,17 |
| 30/09 | $13.711.507,46 |
| 04/10 | $7.538.176,66 |
| 07/10 | $8.574.301,44 |
| 08/10 | $4.538.176,66 |
| 10/10 | $53.848.001,41 |
| 12/10 | $18.750.000,00 |
| 15/10 | $32.500.496,36 |
| 18/10 | $580.167,68 |

Los otros 16 días del período aparecen en cero: 24, 26/09; 01, 02, 03, 05, 06,
09, 11, 13, 14, 16, 17, 19, 20 y 21/10. Cero significa **sin ingreso cargado**,
no garantía de que no habrá cobranza. No se inventaron montos para llenar días.

| Vencido GRUPO | Monto | Desde |
|---|---:|---|
| ARCA / impuestos (incluye otros fiscos) | $547.565.756,95 | 11/06/2024 |
| Bancos | $379.505.910,33 | 10/06/2026 |
| Proveedores | $431.435.696,96 | 04/01/2026 |
| **Suma / stock total existente** | **$1.358.507.364,24** | |

**La referencia de ~$431 M de la consigna corresponde solo a proveedores**, no al
vencido total de las tres puntas. Los importes cuadran, al centavo, con el stock
existente; también se verificó proveedores contra KPI, bancos contra deuda bancaria
vencida e impuestos contra el desglose por débito. A: $1.273.799.021,24; AA:
$84.708.343,00. Los cálculos existentes usan float; las comparaciones se hicieron
con tolerancia menor a un centavo, sin ajustar montos para forzar coincidencias.

### Pruebas, límites y revisión pendiente

- Regeneré a `/tmp/finauto-tarea07/finauto.html` con:
  `python3 finauto.py --contrato /Users/thomasmanzo/Documents/Finnauto/clientes/navar/contrato_2026-09-22.json --cliente navar --salidas /tmp/finauto-tarea07 --sin-memoria`.
  `--sin-memoria` evita escribir la foto del cliente fuera de los archivos permitidos.
- Inspeccioné los datos del paquete y el HTML generado; comprobé todos los cuadres
  anteriores por las tres empresas. Un ejemplo inventado en `/tmp/verificar07.py`
  verifica límites de ventana, empresas, internos, crédito con signo y cheque anulado.
  Esas aserciones pasaron; el archivo temporal también incluye un intento de navegador
  que **no pudo ejecutarse**. No es una prueba integral pasada.
- `tests/test_motor.py` ejecutado con el Python del entorno existente: **dos fallos**,
  ambos expectativas antiguas de `ingresos_por_dia` (`tests/test_motor.py:1378` y
  `:1383`): pedían solo días con movimientos y una lista vacía para transferencias.
  Ahora hay fechas en cero sin sumar la transferencia. El resto de sus comprobaciones
  pasó. No cambié ese archivo porque no está permitido; queda actualizar esas dos
  expectativas durante la integración. `unittest discover` no sirve para estos
  scripts: con el entorno existente descubre 0 tests, y no lo cuento como validación.
- **Revisión visual pendiente:** Chromium instalado no pudo arrancar por
  `bootstrap_check_in ... Permission denied` del sandbox. El control de UI no tiene
  navegadores disponibles (`listBrowsers` devolvió vacío). No pude comprobar el
  render, navegación, tooltips ni tamaños de pantalla. Tampoco había `node` para
  el chequeo de sintaxis JS. No doy por verificado lo visual ni la ejecución del JS.
- `git diff --check` limpio. Búsqueda de los nombres propios de personas identificados
  en el contexto, en ambos archivos de código y en `finauto.html`: **sin resultados**.
- **Commit bloqueado:** `git add` falló al crear
  `/Users/thomasmanzo/Documents/Finnauto/.git/worktrees/Finnauto-tarea07/index.lock`
  con `Operation not permitted`. Los cambios quedan sin commit en esta rama para que
  el revisor los registre, conforme al circuito. No se intentó saltar el sandbox.
- No se verificaron la Sheet viva, la vigencia de las deudas ni el cobro real de las
  facturas. La evidencia es el contrato indicado; los saldos de caja de ese contrato
  tienen su propia antigüedad. Antes de usarlo en reunión, falta la revisión visual
  y la validación del dato de origen por quien administra el cash.


## Revisión
