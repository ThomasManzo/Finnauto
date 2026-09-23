# Tarea 11 — Los bancos sin extracto nuevo arrastran el último saldo conocido
Estado: pendiente
Rama: tarea/arrastre-saldos

## Objetivo

En el bloque `1 · Bancos` de las pantallas de cash, hoy queda **la celda vacía** cuando un banco no
tiene extracto de ese día. Resultado: la pantalla muestra la posición incompleta y no se entiende
cuánta plata hay.

Pedido de Thomas (23/09): *"prefiero que carguen los saldos que tenemos hasta ahora y que los que
no, sean iguales al día anterior"*. O sea: **arrastrar el último saldo conocido** de cada cuenta
hasta que llegue uno nuevo.

**Con una condición que no se negocia: el saldo arrastrado tiene que verse distinto del confirmado.**
Si una cuenta muestra el saldo de hace ocho días como si fuera el de hoy, alguien lo va a leer como
plata confirmada. Hoy mismo pasa con una cuenta que viene del 15/09 y es la más negativa de todas.

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `CLAUDE.md`, `clientes/navar/documentos/manual_cash.md`
(§3 y §4).

Situación real al 23/09, para entender el caso: Galicia y Macro tienen saldo al 22/09, BBVA al
21/09, Corrientes al 16/09 y Nación al 15/09. Nación es la cuenta más negativa y la que tiene el
descubierto nuevo, así que es justo la que más importa no malinterpretar.

Un detalle del que conviene acordarse: el archivo de un banco puede llamarse con la fecha de hoy y
traer movimientos hasta ayer (el home banking no cierra el día en curso). El lector usa el
contenido, no el nombre, y eso está bien: no cambiarlo.

El tablero web **ya arrastra** (suma el último saldo de cada cuenta y lo avisa). Lo que falta es
que las pantallas de la planilla hagan lo mismo. Si de paso conviene unificar el criterio con el
tablero, decilo en "Qué hice", pero **no toques `dashboard/`** en esta tarea.

## Archivos permitidos

- `clientes/navar/herramientas/crear_cash.gs`
- `clientes/navar/documentos/manual_cash.md` — §3 y §4.
- `tareas/11-arrastre-de-saldos.md`

No tocar los lectores, `importar_cashflow.gs` ni `dashboard/`.

## Resultado esperado

1. En el bloque de bancos, cada cuenta muestra su **último saldo conocido** en todas las columnas
   posteriores, hasta que aparezca uno nuevo. Nunca más una celda vacía por falta de extracto.
2. **El arrastrado se distingue a simple vista**: elegí un recurso y explicá por qué (por ejemplo,
   en gris o en itálica, o con un asterisco y una nota al pie). Que se entienda sin leer el manual.
3. Al lado del nombre de cada banco, o en una fila debajo, **desde cuándo** es ese saldo: "al 15/09"
   o "hace 8 días". Que el número y su antigüedad viajen juntos.
4. En el total de bancos, aclarar cuántas cuentas están arrastradas: por ejemplo
   *"incluye 3 cuentas con saldo arrastrado (la más vieja, del 15/09)"*.
5. **Nada de esto cambia ninguna cuenta**: `Saldo inicial`, los `SALDO AL CIERRE` y el neteo con el
   descubierto siguen funcionando igual. Es presentación del bloque de bancos. Si al arrastrar un
   saldo se modificara algún total, **parar y explicarlo** en vez de cambiarlo.
6. Que el arrastre **no invente el futuro**: se arrastra hasta hoy (el día en curso), no a lo largo
   de las columnas estimadas hacia adelante, donde el saldo ya lo calcula la proyección.

## Comprobaciones

Apps Script no corre acá:

1. Explicar en criollo cómo quedó la fórmula del arrastre.
2. Ejemplo a mano con el caso real de arriba: qué tendría que mostrar cada uno de los cinco bancos
   en la columna de hoy, cuál en gris y con qué leyenda, y qué dice el total.
3. Guion de prueba en la planilla: qué mirar antes y después de correr "Armar solapa Cash".
4. Sin nombres propios de personas. Commit en la rama; si el sandbox no deja, anotarlo.

## Qué hice

## Revisión
