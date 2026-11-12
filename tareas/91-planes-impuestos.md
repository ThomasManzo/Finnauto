# Tarea 91 — Planes de ARCA y Rentas proyectados desde la planilla de impuestos
Estado: aprobada
Rama: tarea/planes-impuestos

## Objetivo
La planilla de vencimientos trae solo la cuota del mes de cada plan de pagos: después de esa fecha el
Cash no veía ninguna cuota de planes. Desde noviembre la planilla trae el detalle de los planes: hay
que proyectar todas las cuotas que faltan.

## Contexto
- Solapa "PLANES VIGENTE ARCA ...": un renglón por plan con "cuota X de N", importe al 1er vto y fecha
  de ingreso (día de débito). Los planes recién firmados dicen solo "N".
- Solapa "PLAN DE PAGO RENTAS": "CUOTA k · importe · fecha" (el anticipo dice PAGADO).
- En Vencimientos esos mismos planes aparecen como un renglón del mes (ARCA, todos juntos) y la
  próxima cuota de Rentas: con las solapas, esos renglones se reemplazan para no sumar dos veces.

## Archivos permitidos
- `lector/deuda_impositiva.py`
- `lector/pruebas/test_planes_impuestos.py` (nuevo)

## Resultado esperado
Cuotas X..N mensuales, mismo día y mismo importe (estimado); "N" solo = 1 de N con aviso; Rentas tal
cual la solapa; lo impago anterior de Vencimientos se conserva; sin las solapas, todo igual que antes.

## Comprobaciones
`python -m unittest discover -s lector/pruebas -p 'test_*.py'`.

## Qué hice
Hecha por Claude (Codex saturado; Thomas pidió avanzar). `_leer_planes_arca`, `_leer_plan_rentas`,
`_cuotas_de_planes` y el reemplazo en `armar`. Pruebas con datos inventados: proyección, reemplazo
del renglón del mes, cuota vieja impaga que queda, plan "N" con aviso, Rentas sin el anticipo,
planilla vieja sin solapas, fin de mes. 175 pruebas OK.

## Revisión
Con la planilla real (solo en esta Mac) los planes de febrero a junio 2027 dan lo mismo que el
cronograma que armó NAVAR; NAVAR también toma los planes "6/8/9" como cuotas desde noviembre.
