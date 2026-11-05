# Tarea 80 — Comisiones de vendedores: renglón propio y pagos mal clasificados

**Estado:** aprobada. La hizo Claude con los mayores de A y AA que pasó Thomas (05/11/2026); pedido: "acomodalo".

## Objetivo
Los vendedores facturan como proveedores, así que el cash no mostraba sus comisiones. Al cruzar los mayores
con la tesorería y los movimientos aparecieron además pagos reales mal clasificados.

## Qué cambió
- `lector/comisiones.py` (nuevo): categoría "Comisiones". La lista de vendedores NO está en el repo: vive en
  Drive, `NAVAR - Datos/Comisiones/vendedores.json`. Sin ese archivo no se marca nada.
- `lector/extractos.py`:
  - Macro "TRF MO CCDO DIST T - <CUIT propio>" es a otro titular: ya no es Transferencia Interna.
  - "TRANSF <CUIT> FAC comisiones" ya no es gasto bancario.
  - Nación "DEB.TRAN.INTERB" a otro titular ya no cae en Otros: es pago a proveedor.
  - Los pagos a vendedores por banco se marcan por CUIT en el texto o cruzando con las órdenes de pago de Tango.
- `lector/cajas.py`: pagos a vendedores de la lista, y comisiones por sueldos si la leyenda lo dice.
- `crear_cash.gs`: renglón "Comisiones de vendedores" en los tres cash, y la categoría en la validación.

## Comprobaciones
- Pruebas: `lector/pruebas/test_comisiones.py` (datos inventados) y toda la suite.
- Simulación con los datos reales: las cajas conservan cantidad de filas y suma; en bancos solo cambian las
  categorías previstas.

## Después de instalar
En la notebook: `actualizar.ps1`, y después `vigilante.py --forzar bancos` y `--forzar cajas`. Los lectores
releen todo, así que también se corrige lo ya cargado.
