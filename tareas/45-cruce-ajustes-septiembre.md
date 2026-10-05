# Tarea 45 — Cruce banco ↔ Tango: tres casos que aparecieron en septiembre
Estado: lista para revisión
Rama: tarea/cruce-ajustes

## Objetivo
Que el cruce (`lector/cruce.py`, tareas 40 y 44) empareje tres formas de cargar que aparecieron al
correr septiembre con el detalle de tesorería bajado por la API, y que avise de posibles errores de
tipeo. Sin tocar la Sheet.

## Contexto
Con datos reales (en `clientes/navar/privado/cruce/`, fuera de git) se vieron, cerrando al centavo:
1. **Impuestos (VEP de ARCA)**: el banco debita un solo renglón ("IMP. AFIP") y Tango carga varias
   órdenes de pago sin CUIT de un tercero: el impuesto y sus intereses, a veces en días distintos.
   Ejemplo inventado: banco −2.210.000 el 16; Tango −2.000.000 y −200.000 el 15 y −10.000 el 16.
2. **Descuento con la boleta en otro día**: el interés se carga el día del banco y la boleta de
   depósito uno a cuatro días después. Ejemplo inventado: banco +9.600 el 14; interés −400 el 14;
   boleta +10.000 el 16.
3. **Depósito acreditado en dos días**: una boleta = cheques que el banco acredita un día y el
   siguiente (los compensa la cámara en días distintos).
Además, un pago de tarjeta tenía en Tango los mismos dígitos que en el banco, pero en otro orden.

## Archivos permitidos
`lector/cruce.py`, `lector/pruebas/test_cruce.py`, `clientes/navar/perfil.json` (bloque `cruce`).

## Resultado esperado
- Regla **"impuestos agrupados"** (Sugerido): un débito de `categorias_impuestos` de al menos
  `impuestos_minimo` = la única combinación de órdenes de pago de `comprobantes_impuesto` sin CUIT de
  un tercero, dentro de la ventana de días. Si hay más de una combinación, va a Revisar.
- **"descuento neto corrido"** (Sugerido): segunda pasada de "descuento neto", con el interés dentro
  de la ventana del banco y la boleta hasta `dias_fecha_corrida`. La pasada normal (mismo día) va
  primero y sigue siendo Seguro.
- **"agrupado en dos días"** (Posible): una boleta = combinación única de créditos de cheques de dos
  días seguidos con movimientos; la combinación tiene que usar los dos días.
- Pista **"¿error de tipeo?"** en "Solo en banco": mismo banco, mismo signo, mismos dígitos en otro
  orden, hasta 45 días y más de $100.000.

## Comprobaciones
`python -m unittest lector.pruebas.test_cruce`; julio, agosto y septiembre con datos reales: cuenta de
control OK y revisión a mano de cada par nuevo.

## Qué hice
**La escribió Claude.** Las tres reglas, la pista y 7 pruebas nuevas con datos inventados (38 en total,
OK): impuestos en días distintos, impuestos que no toman pagos con CUIT ni montos chicos, impuestos
ambiguo a Revisar, descuento corrido, descuento del mismo día sigue Seguro, depósito en dos días y
pista de tipeo. Con datos reales, julio a septiembre: la cuenta de control da en todas las cuentas; los
pares nuevos se revisaron uno por uno (cierran al centavo). La mejora más grande es en Macro en
septiembre (impuestos y descuentos). Ojo al comparar con corridas viejas: Tango cambió desde el 18/09
(la administración cargó cosas después), así que agosto mejora también por eso.

## Revisión
