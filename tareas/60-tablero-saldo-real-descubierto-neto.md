# Tarea 60 — Tablero: saldo real, descubierto usado y neto por cuenta
Estado: aprobada (pedido de Thomas, 08/10/2026)
Rama: tarea/tablero-neto

## Objetivo

En el tablero, "Dónde está la plata hoy" tiene que mostrar por cuenta: **saldo real** (la plata que
hay), **descubierto usado** (lo que se debe al banco por tener la cuenta en negativo) y **neto** (saldo
real − descubierto usado), con una fila de totales. El Cash NO cambia (ver la corrección de la 59).

## Archivos permitidos

- `dashboard/app.py` — solo la tabla "Dónde está la plata hoy".
- `tareas/60-tablero-saldo-real-descubierto-neto.md`

## Qué hice

Lo escribió Claude.

- Columnas: Cuenta · Empresa · Saldo real · Descubierto usado · Neto · Dato al. Banco positivo → todo
  en saldo real; banco negativo → todo en descubierto usado (en rojo); una caja en efectivo no tiene
  descubierto (su saldo va entero a saldo real). Fila "Total" con las tres sumas. La nota de abajo
  explica las tres columnas; ya no dice nada de arqueos.
- El JS del tablero pasa `node --check`; lo vi renderizado con datos inventados (las sumas cierran:
  neto total = saldo real − descubierto usado = suma de saldos). Pruebas de lectores OK.
