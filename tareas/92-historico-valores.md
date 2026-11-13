# Tarea 92 — Cash histórico con valores (no fórmulas)
Estado: aprobada
Rama: tarea/historico-valores

## Objetivo
La histórica de la tarea 90 tenía ~160 columnas de fórmulas que se recalculaban en cada importación.
El 12/11 la carga de bancos llegó al límite de 6 minutos. Cada día de la histórica tiene que
calcularse una sola vez y quedar como número fijo.

## Contexto
- El mismo 12/11 se borró la solapa oculta "Cash Flow Consolidado" (el cash viejo de septiembre:
  11.700 SUMIFS sobre Movimientos, nadie la usaba; respaldo en Drive `NAVAR - Datos/anteriores`).
  La carga de bancos pasó de 308 s a 39 s.

## Archivos permitidos
- `clientes/navar/herramientas/crear_cash.gs` (solo la histórica)
- `lector/pruebas/probar_cash_historico.cjs`

## Resultado esperado
Columnas: A renglones · días (valores) · modelo oculto (fórmulas, fila 6 vacía) · auxiliar oculta.
`armarCashHistorico` arma todo y congela; `_extenderHistorico_` agrega los días que salieron del Cash
copiando el modelo una vez y congelándolos. Para corregir días viejos: rearmar desde el menú.

## Qué hice
Hecha por Claude con el OK de Thomas ("aliviar la planilla"). Pasan las 16 pruebas `.cjs`.

## Revisión
Se instala y se mide la carga de bancos con la histórica armada.
