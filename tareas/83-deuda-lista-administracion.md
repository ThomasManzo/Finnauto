# Tarea 83 — Deuda de proveedores según la lista de la administración
Estado: lista para revisión
Rama: tarea/deuda-lista-admin

## Objetivo
La administración de la empresa A pasó una lista de su deuda con proveedores, dividida en "real" (se paga) y "no real"
(deuda vieja que van a dar de baja: se tiene presente, pero no suma). Decisión de Thomas: la Sheet muestra **lo que dice esa
lista**. Lo que Tango trae distinto para las facturas hasta la fecha de la lista queda afuera. Lo facturado después de esa fecha
se sigue tomando de Tango, como siempre. La empresa AA no cambia.

## Contexto
- `lector/tango.py`, `leer_pagos`: arma "Cuentas a Pagar" desde el export "Pagos a realizar", que trae `Cód. proveedor`.
  Una fila cuyas Observaciones empiezan con `REVISAR:` no suma en el cash (`crear_cash.gs`, filtro `<>REVISAR*`) ni en el
  tablero (`lector/cash_limpio.py`, que la informa agrupada por motivo: el texto hasta el primer " · "). Hoy lo vencido antes del
  1 de enero se marca `REVISAR: deuda vieja`.
- `Saldo Pendiente` en la Sheet es Importe Total − Pagado. La importación borra las filas viejas de Tango reconociendo las marcas
  "Tango Live" / "REVISAR:" en Observaciones: toda fila nueva tiene que llevar `Tango Live` (ver `origen`).
- `clientes/navar/herramientas/vigilante.py` corre `lector/tango.py` sobre una carpeta temporal, y conoce la raíz de Drive. Mirá cómo
  `lector/comisiones.py` lee `Comisiones/vendedores.json` desde la raíz: es el modelo a seguir para una lista privada.
- La lista tiene datos reales: vive **solo en Drive**, en `Proveedores/lista_administracion.json`. No se versiona, no la vas a ver.

## Archivos permitidos
- `lector/tango.py`
- `clientes/navar/herramientas/vigilante.py` (solo pasar la ruta de la lista)
- `clientes/navar/herramientas/crear_cash.gs` (solo el punto 3)
- `clientes/navar/herramientas/resumen_semanal.gs` y `clientes/navar/herramientas/principales20_pdf.py` (solo el punto 4)
- `lector/pruebas/test_tango_lista_admin.py` (nuevo)
- `tareas/83-deuda-lista-administracion.md`

## Resultado esperado

### 1. La lista
`python lector/tango.py ... --lista-proveedores <ruta>` (opcional). El vigilante la pasa si el archivo existe. Formato:
```json
{"empresa": "A", "fecha": "2030-01-31",
 "real": [{"codigo": "PRV001", "nombre": "Proveedor Inventado", "ajuste": -100.50}],
 "no_real": [{"codigo": "PRV002", "nombre": "Otro Inventado", "saldo": 2500.00}]}
```

### 2. Reglas, solo para filas de `empresa` con **Fecha de emisión <= fecha de la lista**
Una factura posterior a la lista sigue las reglas de siempre, sea del proveedor que sea.
- **Proveedor en `real`:** suma siempre, aunque esté vencida hace años: no lleva `REVISAR: deuda vieja`. Se le aplica su `ajuste`, que es
  un monto fijo:
  - negativo: se suma a `Pagado` de sus facturas, de la que vence antes a la que vence después, sin que ninguna quede con saldo negativo.
    Si no alcanza (porque ya se pagaron), lo que sobra se descarta, no se pasa a otro proveedor;
  - positivo: se suma a `Importe Total` de su factura de vencimiento más nuevo;
  - la fila ajustada lo aclara en Observaciones, después del origen.
- **Proveedor en `no_real`:** sus facturas no entran. En su lugar, entra **una fila por cada proveedor de la lista, tenga o no facturas en
  Tango**: Proveedor = `nombre`, Importe Total = `saldo`, Pagado 0, emisión y vencimiento = fecha de la lista, Nro "LISTA ADMINISTRACION",
  Observaciones `REVISAR: deuda no real · <origen>`.
- **Proveedor en ninguna de las dos:** la factura entra con Observaciones `REVISAR: fuera de la lista de la administración · <origen>`.
- Los residuos de $ 1 o menos se descartan antes, como hoy.
- Sin lista, o con lista ilegible: todo sigue como hoy, sin cortar la corrida, y el resumen lo avisa en una línea visible.
- El resumen suma una línea por regla con cantidad y monto.

### 3. Cash: renglón informativo
En la sección 6 ("Atrasado hoy") de `crear_cash.gs`, debajo de "Total atrasado a pagar" y sin sumar en él ni en el control de lo repartido:
"Deuda no real de proveedores (no suma)", en cursiva gris, con `SUMIFS` de Saldo Pendiente sobre Observaciones `REVISAR: deuda no real*`. No
tiene que romper `_atrasadoEntre_`, ni la columna diaria o mensual: si hace falta, va fuera del arreglo `atrasado`. Actualizar Instrucciones con una línea.

### 4. Resumen semanal y PDF de Principales 20
Hoy suman todas las filas de Cuentas a Pagar. Que ignoren las filas con Observaciones que empiezan con `REVISAR: deuda no real` o
`REVISAR: fuera de la lista`. El resto de `REVISAR` sigue como hoy.

## Comprobaciones
- `lector/pruebas/test_tango_lista_admin.py`, con datos inventados, ejecutable con `python`: cada regla del punto 2, incluidas factura posterior a la
  lista de proveedor no real y de proveedor fuera de lista (entran normal); factura vieja de proveedor real (suma); ajuste negativo repartido en dos facturas;
  ajuste mayor que la deuda (no queda negativo); ajuste positivo; proveedor no real sin facturas (igual tiene fila); empresa AA (no cambia); lista ausente y
  lista rota (como hoy, con aviso).
- Python: `.venv/bin/python` del repo principal `/Users/thomasmanzo/Documents/Finnauto`. Node: `/Applications/ChatGPT.app/Contents/Resources/cua_node/bin/node`.
  Tienen que seguir pasando `lector/pruebas/probar_control_diario.cjs`, `probar_control_cierre.cjs`, `probar_cash_cajas.cjs`, y las pruebas de tango que ya existan.
- Sin datos reales en ningún archivo. Comentarios en criollo. No instalar nada, no commitear.

## Qué hice
- `lector/tango.py`: agregué `--lista-proveedores`, lectura y validación del JSON privado, aviso visible cuando falta o es inválido, y las reglas por empresa/código/fecha de emisión. Los residuos se descartan primero. Los ajustes negativos se reparten por vencimiento y el sobrante se descarta; los positivos van a la última factura alcanzada. Todas las filas conservan la marca Tango Live.
- Los proveedores no reales tienen una fila informativa cada uno, aunque no tengan facturas ni haya un export de pagos de A. El resumen informa cantidades y montos de las reglas aplicadas, los ajustes y sus sobrantes.
- `vigilante.py`: pasa la ruta de Drive si existe. Respeté el alcance “solo pasar la ruta”: cambiar únicamente el JSON no agrega un disparador nuevo; se relee cuando vuelve a correr Tango.
- `crear_cash.gs`: agregué el renglón informativo gris y en cursiva debajo del total atrasado, fuera del arreglo que alimenta el reparto, y la explicación en Instrucciones.
- `resumen_semanal.gs` y `principales20_pdf.py`: excluyen las dos marcas pedidas únicamente de Cuentas a Pagar; conservan los demás REVISAR.
- `lector/pruebas/test_tango_lista_admin.py`: cinco pruebas con Excel y JSON temporales inventados. Cubren las reglas pedidas, AA sin cambios de datos, residuos, lista inválida, falta de export y los totales del PDF. Los ID se renumeran como antes para toda la lista.
- Comprobaciones: pasaron 39 pruebas con el Python indicado (`test_tango_lista_admin`, `test_cheques`, `test_cheques_en_cartera` e `ingestas.test_tango_live`). El archivo nuevo también pasó ejecutado directamente con Python.
- Con el Node indicado pasaron `probar_control_diario.cjs`, `probar_control_cierre.cjs`, `probar_cash_cajas.cjs` y `probar_resumen_semanal.cjs`. Una comprobación adicional en memoria confirmó que la foto semanal excluye ambas marcas en proveedores y conserva deuda vieja y cobranzas. `git diff --check` sin errores.
- Criterios para casos no definidos: sin fecha de emisión comprobable se mantienen las reglas habituales; un ajuste positivo sin factura alcanzada no inventa deuda y queda avisado como no aplicado. JSON con códigos repetidos, cruces entre real/no_real, importes no finitos o empresa distinta de A se considera inválido.
- No accedí a datos reales ni a producción. Los documentos locales de NAVAR no están en este worktree; usé el contexto de la consigna, como indica tareas/LEEME.md. Falta la revisión en la Sheet real y con la lista privada por quien lleva NAVAR; no generé ni envié un PDF real.
- Solo modifiqué los archivos permitidos. Sin dependencias nuevas y sin commits, por pedido de Thomas.

## Revisión
Revisión de Claude (06/11/2026): leí el diff y corrí el lector sobre el export real con la lista privada, sin tocar la Sheet. Real, no real y vencido
coinciden al centavo con la lista y con un cálculo aparte (los números quedan fuera del repo). AA no cambia. Falta: subir la lista a Drive, instalar los .gs,
ajustar a mano la solapa Principales 20 y validar en la Sheet. Límite conocido: el ajuste es fijo; hay que actualizarlo con cada lista nueva.
