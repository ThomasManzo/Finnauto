# Tarea 90 — Solapa "Cash histórico": los días que salen del Cash
Estado: pendiente
Rama: tarea/cash-historico

## Objetivo
El Cash (día por día) muestra solo los últimos 7 días con extracto y 28 hacia adelante. Los días más
viejos desaparecen de la vista y NAVAR no tiene dónde verlos día por día. Queremos una solapa nueva,
**"Cash histórico"**, con los mismos renglones que el Cash y una columna por cada día pasado: desde el
primer día con extracto hasta el día anterior a la primera columna del Cash. Cada día que sale del Cash
pasa solo a la histórica, sin que nadie toque nada.

## Contexto
- `clientes/navar/herramientas/crear_cash.gs` arma el Cash con `_armarPeriodica_(ss, "Cash", "dia")`.
  Todas las fórmulas de una columna dependen solo de la fecha de esa columna (fila 6, `{D}`), de la
  columna anterior (por ejemplo "Saldo inicial = cierre del período anterior") y de las celdas fijas
  `$B$2` (hoy), `$B$3` (último día con extracto) y `$B$5` (último día con caja) de la misma solapa. Por
  eso una columna del Cash copiada a la derecha con `copyTo` (como "arrastrar") sigue siendo correcta
  para el día siguiente.
- Primera columna del Cash = `$B$3 - 6` (`DIAS_ATRAS = 7`). La última columna de la histórica tiene que
  ser `$B$3 - 7`.
- Armar la histórica con el armador celda por celda NO sirve: son más de 150 columnas por más de 150
  renglones y Apps Script corta a los 6 minutos. La idea es copiar, que es una sola llamada:
  1. `armarCashHistorico()`: borra la solapa "Cash histórico" si existe y la crea **duplicando la
     solapa "Cash"** (copia renglones, grupos, filas ocultas, formatos y formatos condicionales). Deja la
     columna A y la columna B y borra las demás columnas de días (la columna "Fuente"/notas del final,
     si existe, se quita también o se deja al final; lo que quede más simple y prolijo). En B6 pone
     como fecha fija (valor, no fórmula) el primer día con extracto
     (`MIN` de las fechas de Movimientos con Origen "Extracto*"), con el mismo formato de fecha. Después
     llama a `_extenderHistorico_()`.
  2. `_extenderHistorico_()`: mira la fecha de la última columna de la histórica y `$B$3 - 7` (el B3 de
     la propia histórica o del Cash: es la misma fórmula). Si faltan días, copia la última columna hacia
     la derecha tantas veces como falten, con UNA llamada `copyTo` sobre el rango, y la fila 6 de las
     columnas nuevas queda como "fecha de la columna de la izquierda + 1". Si no falta nada, no hace
     nada. Agrega columnas a la hoja si no alcanzan (`insertColumnsAfter`).
  - Todo en la histórica es pasado, así que la parte estimada de cada fórmula da cero sola; no hay que
    tocar fórmulas.
- Dónde se llama:
  - `armarCash()`: al final, `armarCashHistorico()` (si cambian los renglones del Cash, la histórica se
    rehace igual).
  - `importarLoNuevo()` en `importar_cashflow.gs`: si entró algo (`hubo`), llamar a
    `_extenderHistorico_()` **antes** de `exportarParaTablero()`, dentro de un try/catch que solo anota en
    el Logger. Un error de la histórica nunca puede frenar ni marcar como fallida la importación. Si la
    solapa no existe, no hace nada (no la crea: crearla es de `armarCash` o del menú).
  - Menú "finauto" (`onOpen`): un ítem "Armar solapa Cash histórico" que llama a `armarCashHistorico`.
- La solapa queda ubicada inmediatamente a la derecha de "Cash". Título en A1:
  "CASH · <cliente> · histórico día por día (los días que ya salieron del Cash)". Fila 1 y columna A
  inmovilizadas, como en el Cash.
- Instrucciones (`armarInstrucciones`): un renglón para la solapa nueva en la tabla de solapas
  (qué es, de dónde sale: "fórmula sobre las listas, copia del Cash", quién la toca: "nadie").
- Revisar si algo recorre todas las solapas (por ejemplo `_separadorLocal_`, `arreglarValidaciones`,
  `exportarParaTablero`, `tablero_web.gs`) y si la solapa nueva le cambia algo; anotarlo en "Qué hice".

## Archivos permitidos
- `clientes/navar/herramientas/crear_cash.gs`
- `clientes/navar/herramientas/importar_cashflow.gs` (solo el llamado en `importarLoNuevo` y el ítem del menú)
- `lector/pruebas/probar_cash_historico.cjs` (nuevo)
- este archivo de tarea ("Qué hice")

## Resultado esperado
- `armarCashHistorico()` y `_extenderHistorico_()` en `crear_cash.gs`, comentadas en criollo.
- La cuenta de "cuántas columnas faltan" en una función pura chica (fecha de la última columna, B3,
  DIAS_ATRAS → cantidad), para poder probarla sin la Sheet.
- Los tres llamados (armarCash, importarLoNuevo, menú) y el renglón de Instrucciones.

## Comprobaciones
- `probar_cash_historico.cjs` (node, como los otros `probar_*.cjs`, con un SpreadsheetApp de juguete o
  probando solo la función pura): última columna 01/11 y B3 11/11 → faltan 3 (02, 03 y 04/11); última
  columna 04/11 y B3 11/11 → faltan 0; B3 que retrocede → faltan 0 (nunca negativo).
- Con un mock mínimo: `_extenderHistorico_` hace una sola copia para N columnas y no hace nada si no existe
  la solapa.
- Las pruebas `.cjs` que ya existen siguen pasando (correrlas con
  `/Applications/ChatGPT.app/Contents/Resources/cua_node/bin/node`).
- No se puede probar en la Sheet real desde el worktree: lo instala y lo prueba Claude.

## Qué hice

## Revisión
