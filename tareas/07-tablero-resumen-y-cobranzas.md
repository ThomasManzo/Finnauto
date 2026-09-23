# Tarea 07 — Tablero: el día por día está incompleto, y falta el cuadro de vencidos
Estado: pendiente
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

## Revisión
