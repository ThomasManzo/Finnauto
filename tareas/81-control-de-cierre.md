# Tarea 81 — Control de cierre del Cash Mensual

**Estado:** aprobada. La hizo Claude a pedido de Thomas (05/11/2026), después de la tarea 80.

## Objetivo
Que el cash avise solo cuando los movimientos no explican el saldo. En la tarea 80 aparecieron pagos que no
sumaban en ningún renglón; el saldo daba bien porque sale del banco, así que nadie lo veía.

## Qué cambió (`clientes/navar/herramientas/crear_cash.gs`)
- **Sección 7 del Cash Mensual, solo meses cerrados:** saldo real anterior + renglones = saldo que debería
  haber, contra el saldo real. La diferencia se separa en cuatro partes:
  1. transferencias internas que no se cancelan (un pase propio tiene dos patas y suma cero);
  2. bancos: saldo del extracto contra sus movimientos;
  3. sin explicar: movimientos en una categoría sin renglón en el cash;
  4. efectivo: cajas A y AA juntas contra sus arqueos.
- **Estado por mes:** REVISAR si 1, 2 o 3 llegan a $ 1 M. El efectivo se muestra pero no marca el mes: según
  Thomas, los préstamos entre las cajas de A y AA no se registran, así que no va a cerrar al peso. Se miran
  juntas para que esos préstamos se cancelen. Aviso arriba de todo, en C2.
- **Saldo inicial de la primera columna (las tres pantallas):** ahora es el saldo real del día anterior. Antes
  se calculaba para atrás (cierre menos lo que pasó), así que esa columna siempre cerraba y escondía errores.
- **Renglón "Otros" (las tres pantallas):** restaba los honorarios en vez de sumarlos: el "-" del renglón negaba
  solo la primera categoría. Lo encontró este control; ahora la suma va entre paréntesis.
- **Fórmula del saldo en una función** (`_saldoBancoAl_`), sin cambio de lógica.
- **Instrucciones:** el arqueo se carga como "Caja AA" o "Caja A", ya no como "Varios".
- **Aviso en `_validacionesSaldos_`:** si renombra una caja, hay que volver a armar el cash.

## Pases entre cuentas propias (`lector/pases_internos.py`, nuevo)
El control mostró transferencias internas sin su otra pata. La otra pata estaba en otro banco, el mismo día y por el
mismo importe, cargada como cobranza o proveedor porque ese banco escribe un texto genérico. El lector ahora la
busca y la pasa a interna. Si hay más de una candidata no adivina: queda como está y el control la sigue mostrando.

## El error que corrige (05/11/2026)
`arreglarValidaciones` renombró "Varios" a "Caja AA" después de armar el cash. Las fórmulas seguían buscando
"Varios", no encontraban arqueo y la Caja AA quedó como la suma de todos sus movimientos. Se corrige volviendo
a armar el cash; el nombre nuevo ya es el que usan los saldos.

## Pruebas
- `lector/pruebas/test_pases_internos.py` (datos inventados): pases, candidatas dudosas y lo que no se toca.
- `lector/pruebas/probar_control_cierre.cjs` (datos inventados): qué movimientos cuenta cada parte y cuándo
  marca REVISAR. Siguen pasando `probar_cash_cajas`, `probar_canchada_envases` y `probar_panel_canchada`.
- Contra los datos reales: la sección 7 se comparó con un cálculo aparte hecho desde los archivos de los
  lectores (los números quedan fuera del repo).

## Límites conocidos
- Una caja antes de su primer arqueo muestra el saldo de ese arqueo, plano: la parte de efectivo de esos meses
  no es un faltante.
- El control no ve un extracto atrasado: si un banco no mandó los últimos días, faltan a la vez su saldo y sus
  movimientos, y cierra igual.
- El control mide, no corrige: lo que no cierra se arregla en las reglas del lector.
