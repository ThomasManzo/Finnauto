# Tarea 59 — Saldos de bancos netos y "al día" aunque no haya movimientos
Estado: en curso
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

## Revisión
