# Tarea 48 — Cruce banco ↔ Tango semanal, con mail a la administración
Estado: lista para revisión
Rama: tarea/cruce-semanal

## Objetivo
Que todos los miércoles le llegue a la administración (y a Thomas) un mail con lo que el banco debitó o
acreditó y todavía no está cargado en Tango, con un Excel para buscar cada movimiento.

## Contexto
La administración no tiene acceso a los bancos: carga los débitos cuando llegan los resúmenes, a fin de
mes (lo dijeron al contestar las consultas del cruce, 06/10/2026). Nosotros tenemos los extractos todos
los días. Decisiones de Thomas (06/10): miércoles 09:30; a Thomas y a la administración; el mail con
resumen por banco, lo que falta cargar en Tango y posibles errores de carga; el Excel con el detalle de
lo que no cruza (de los dos lados) para que lo puedan buscar.

## Archivos permitidos
`lector/cruce_semanal.py`, `lector/pruebas/test_cruce_semanal.py`, `lector/cruce.py` (referencia del
banco en los renglones; pagos a ARCA no son gastos), `lector/pruebas/test_cruce.py`,
`clientes/navar/perfil.json` (`pagos_de_impuestos`), `clientes/navar/herramientas/cruce_semanal.gs`,
`clientes/navar/herramientas/importar_cashflow.gs` (menú), `clientes/navar/herramientas/instalar_cruce_semanal.ps1`,
`lector/pruebas/probar_cruce_semanal.cjs`.

## Resultado esperado
- **Notebook, miércoles 08:30 (y 09:00):** `lector/cruce_semanal.py` corre el cruce del mes anterior y del
  mes en curso con lo que hay en Drive y deja en `NAVAR - Datos/Cruce/` el Excel ("Por banco", "Falta
  cargar en Tango", "Posibles errores", "Detalle de lo que no cruza") y `cruce_semanal_<fecha>.json`.
- **Sheet, miércoles 09:30:** `cruce_semanal.gs` arma el mail con el .json, adjunta el Excel y lo manda a
  la propiedad `DESTINATARIOS_CRUCE`. Si no hay cruce de hoy o su control no dio, no va a la
  administración: avisa a `DESTINATARIOS_FALLA`. Menú: ver sin mandar, instalar, quitar.
- "Falta cargar" = en el banco hace más de 7 días y no en Tango. Los gastos chicos del banco van como total
  por banco. Los pagos a ARCA (AFIP/ARCA/VEP) no son gastos: van uno por uno.
- En el cruce: los débitos de Impuestos solo los empareja "impuestos agrupados" o "exacto" (no las
  combinaciones generales, que podían mezclarlos con pagos a terceros).

## Comprobaciones
`python -m unittest lector.pruebas.test_cruce_semanal lector.pruebas.test_cruce ingestas.test_tango_live`
y `node lector/pruebas/probar_cruce_semanal.cjs` (más las otras `.cjs`). Corrida con datos reales como si
fuera miércoles 07/10 (fuera de Drive) y revisión del mail y del Excel.

## Qué hice
**La escribió Claude.** Todo lo de arriba. Pruebas: 2 nuevas del semanal en Python, 1 nueva del cruce
(pago a ARCA no es gasto), 1 ajustada; el `.cjs` del mail cubre el texto, cuándo se manda, la falla sin
cruce de hoy, la falla de control y que no se instala sin destinatarios. Los informes de julio a
septiembre dan los mismos pares que antes.

## Revisión
