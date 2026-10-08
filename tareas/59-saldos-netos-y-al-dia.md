# Tarea 59 — Saldos de bancos netos y "al día" aunque no haya movimientos
Estado: aprobada (sin el cambio del Cash, que se volvió atrás); falta actualizar la notebook
Rama: tarea/saldos-netos

## Objetivo

Pedido de Thomas (08/10/2026), mirando el tablero y el Cash:

1. **Bancos: mostrar el saldo real (neto).** Si es negativo, es el descubierto usado. El Cash hoy
   muestra "saldo + descubierto acordado" (el margen) y confunde: el mismo banco tiene un número en
   el tablero y otro en el Cash.
2. **Un banco sin movimientos no tiene que parecer atrasado.** Hoy el rótulo dice "extracto al
   <fecha del último movimiento>": Galicia decía "al 01/10" aunque el bot bajó todos los días (la
   cuenta no se movió). Se usa el saldo que el bot lee en la pantalla del banco al bajar
   (`_SALDOS_<Banco>_DD-MM.json`): si coincide con el último saldo de los extractos, el saldo vale
   también para el cierre del día anterior a la bajada.
3. **Cajas: sin "arqueo del … + N movimientos de Tango".** Alcanza con la fecha del dato.

## Archivos permitidos

- `lector/extractos.py` — `procesar`, el resumen y un ayudante para `_SALDOS_`.
- `lector/pruebas/test_saldo_de_pantalla.py` (nuevo)
- `dashboard/datos.py` — `cuentas_de_hoy` (el texto de "de cuándo es el dato").
- `lector/pruebas/test_tablero_cajas_deuda.py` — la nota esperada.
- `clientes/navar/herramientas/crear_cash.gs` — la sección "1 · Bancos" y sus textos.
- `tareas/59-saldos-netos-y-al-dia.md`

## Resultado esperado

1. `procesar`: por cada banco, el `_SALDOS_` más nuevo de su carpeta. Si su saldo coincide (±$0,50)
   con el último saldo de esa cuenta y la fecha de la bajada − 1 día es posterior, se agrega un saldo
   en esa fecha con la observación "saldo de la pantalla del banco al bajar: sin movimientos desde el
   DD/MM". Si no coincide, no se agrega nada y el resumen lo anota.
2. Tablero: bancos "al DD/MM"; cajas "al DD/MM".
3. Cash, sección 1: cada banco muestra su saldo real. Rojo = excedido del acuerdo (saldo + acordado <
   0), ámbar = usando descubierto (saldo < 0), negro = positivo. Título y textos acordes.
4. Pruebas con datos inventados.

## Qué hice

Lo escribió Claude.

- `lector/extractos.py`: `saldos_de_pantalla` (el `_SALDOS_` más nuevo de la carpeta del banco) y
  `completar_con_pantalla`. La pantalla de una bajada de madrugada es el cierre del día anterior: si
  coincide con el último saldo de esa cuenta (±$0,50), se repite en ese día con la observación "saldo
  de la pantalla del banco al bajar: sin movimientos desde el DD/MM". Si no coincide, nada, y el
  resumen lo anota. Bancos sin bot (sin `_SALDOS_`) no cambian.
- `dashboard/datos.py`: "De cuándo es el dato" dice solo "al DD/MM" (bancos y cajas).
- `crear_cash.gs`: la sección 1 muestra el saldo real (neto); el acuerdo ya no se suma, solo decide el
  color (rojo = saldo + acuerdo < 0, ámbar = saldo < 0). Título, nota e Instrucciones acordes.
- Pruebas: 6 nuevas (saldo de pantalla), la del tablero actualizada; lectores 137 OK, bots 75 OK,
  pruebas de Node OK. `tests/test_motor.py` tiene 2 fallas que ya estaban en `main` (no son de esto).
- Con los extractos reales (en la Mac, sin publicar nada): Galicia pasa a tener saldo al día anterior
  a la bajada, con la observación de "sin movimientos"; los demás bancos no cambian.

## Revisión

**Claude, 08/10/2026.** `crear_cash.gs` instalado en Apps Script: lo instalado era la versión de la
tarea 48 con montos reales en las propuestas del Plan (en el repo van como "$X M"), así que se aplicó
solo este cambio sobre lo instalado y se verificó por huella después de recargar; la copia de Drive
`Scripts/crear_cash.gs.txt` quedó igual. Falta: que Thomas rearme el Cash desde el menú finauto, y
actualizar la notebook (lector y tablero corren allá).

**Claude, 08/10/2026 — corrección.** Thomas: el formato del **Cash** está bien como estaba; lo que
quería cambiar es el **tablero**. Se volvió atrás `crear_cash.gs` (repo, Apps Script y la copia de Drive
quedaron como antes, verificado por huella). Se mantienen: el saldo de pantalla en el lector (solo
agrega un saldo cuando no hubo movimientos) y el "al DD/MM" del tablero. El formato de bancos del
tablero (saldo real / descubierto usado / neto) va aparte, después de confirmarlo con Thomas.
