# Tarea 12 — El aviso dice "no hay extractos cargados" cuando sí los hay
Estado: pendiente
Rama: tarea/aviso-extractos

## Objetivo

El aviso diario ya está instalado en la planilla y **da un diagnóstico falso**. Probado el 23/09
con datos reales, dice:

- `último extracto cargado: sin datos`
- alerta: *"No hay extractos cargados. Pedir un extracto de banco y revisar la importación."*
- en "Qué falta subir hoy" marca **los cinco bancos** como faltantes, con la coletilla
  *"sin fecha disponible (no se puede determinar desde cuándo falta)"*.

Y es falso: la planilla tiene **242 saldos y 2.405 movimientos** de extracto, con Galicia y Macro
al 22/09, BBVA al 21/09, Corrientes al 23/09 y Nación al 15/09.

Este es el peor error posible en esta herramienta: **un aviso que grita cuando está todo bien
enseña a ignorarlo**, y el día que avise de verdad nadie lo va a leer.

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `tareas/01-aviso-diario.md` y `tareas/08-aviso-9am-que-falta.md`.

**La causa ya está identificada, no hace falta buscarla.** La columna `Origen` de la solapa
**Saldos Bancarios** no dice `Extracto` a secas: dice **el banco al lado**. Valores reales medidos hoy:

```
'Extracto MACRO'        73 filas
'Extracto BBVA'         55
'Extracto GALICIA'      46
'Extracto CORRIENTES'   37
'Extracto NACION'       31
'Manual'                 2
```

El aviso compara por igualdad contra `"Extracto"`, no encuentra nada, y de ahí salen los tres
síntomas. Las fórmulas del cash ya lo resuelven bien: usan `MAXIFS(...;"Extracto*")`, con comodín.

**De paso, eso da la solución al segundo problema**: como el Origen trae el banco, se puede sacar
de ahí **la fecha del último extracto de cada banco** y decir "falta Nación (el último es del
15/09, hace 8 días)" en lugar de "sin fecha disponible". Era justo lo que la tarea 08 quería y no
pudo, y ahora sí se puede.

La solapa **Movimientos** usa la misma convención (`Extracto MACRO`, y además `Tango AA · ...`):
revisar si el aviso la mira en algún lado con el mismo criterio equivocado.

## Archivos permitidos

- `clientes/navar/herramientas/aviso_diario.gs`
- `clientes/navar/documentos/manual_cash.md` — si hace falta.
- `tareas/12-aviso-no-ve-los-extractos.md`

No tocar `crear_cash.gs` ni `importar_cashflow.gs`: acaban de pegarse en producción.

## Resultado esperado

1. El aviso reconoce el Origen **por prefijo** (`Extracto...`), no por igualdad. Y el nombre del
   banco sale de ese mismo campo, no de una lista escrita a mano.
2. `Último extracto cargado` muestra la fecha real, y la alerta de "no hay extractos" sólo aparece
   si de verdad no hay ninguno.
3. "Qué falta subir hoy" nombra **banco por banco** con su fecha y su antigüedad: por ejemplo
   *"Nación: el último extracto es del 15/09, hace 8 días"*, y no lista los que están al día.
4. Revisar que el resto del mail no tenga el mismo problema de comparación exacta en ningún otro
   campo (Origen, Estado, Tipo).
5. **Acentos**: verificar que el archivo esté en UTF-8 y que los textos con tilde estén bien
   escritos en el código (último, llegó, procesó). Si aparece algún caracter raro, corregirlo.

## Comprobaciones

1. Rehacer los ejemplos a mano con **los datos reales de hoy** y pegar en "Qué hice" el texto
   exacto que saldría: encabezado, sección "Qué falta subir hoy" y alertas. Con Galicia y Macro al
   22/09, BBVA al 21/09, Corrientes al 23/09 y Nación al 15/09, **los únicos que tienen que
   aparecer como faltantes son los que de verdad están atrasados**.
2. Probar también el caso de que no haya ninguna fila de extracto (ahí sí la alerta corresponde).
3. `grep` de nombres propios de personas vacío. Commit en la rama.

## Qué hice

## Revisión
