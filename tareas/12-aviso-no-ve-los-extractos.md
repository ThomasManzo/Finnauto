# Tarea 12 — El aviso dice "no hay extractos cargados" cuando sí los hay
Estado: lista para revisión
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

Implementado en el worktree existente, rama `tarea/aviso-extractos`, limpia al arrancar.
Se pasó a `en curso` al comenzar y a `lista para revisión` al terminar.

- `aviso_diario.gs`: reconoce el prefijo Extracto en los dos lugares que antes exigían
  igualdad (último extracto y fecha por banco), sin distinguir mayúsculas ni espacios externos.
  El banco sale del texto de Origen; para filas antiguas con sólo Extracto, usa Banco.
  Cada banco atrasado muestra fecha, días corridos de antigüedad y cierre requerido.
  No cambia la regla: último día hábil cerrado, lunes mira viernes, sin calendario de feriados.
- Revisado el resto del aviso: no lee Movimientos ni sus orígenes Tango AA.
  Tipo identifica claves internas del circuito; Estado usa los valores completos ok/ERROR,
  por lo que ahí corresponde igualdad, no prefijo. Se limpian espacios en Registro y
  se normalizan mayúsculas de Tipo y Estado para evitar falsos pendientes.
- `manual_cash.md`: aclaración breve en §6 sobre Origen y antigüedad por banco.
- Esta consigna: estado, pruebas y ejemplos. No se tocaron otros archivos ni datos privados.
  No se instalaron dependencias.

**Pruebas:** no hay Node en PATH; se compiló el archivo completo con `new Function` en V8.
Se ejecutaron lectura de Saldos Bancarios con servicios simulados y armado real del aviso,
con `Utilities.formatDate` reemplazado por Intl en Buenos Aires. Pasaron siete escenarios:
fechas de la consigna; todos los bancos al día; ninguna fila Extracto; mayúsculas y espacios;
Manual/Tango AA no acreditan extractos; fechas inválidas/futuras no tapan atrasos por banco;
formato viejo Extracto y banco nuevo sin lista fija. UTF-8 estricto y ausencia de caracteres
rotos verificados; búsqueda de nombres de personas de tarea 01 vacía en el script.
`git diff --check` pasó.

**Ejemplo del 23/09/2026 a las 09:00:** se reprodujeron las cinco fechas y los Origen
informados en la consigna, sin acceder a la Sheet ni a privado. Para aislar bancos se
supuso arqueo AA del 22/09, seis exports Tango y tesorería AA fechados hoy y subidos a las
09:00, y publicado Tango de hoy a las 09:00; sin fallos, retenidos ni pendientes de más
de dos horas. Estos últimos datos son inventados: la consigna no informa su estado real.
No se pretende describir el resto del circuito productivo.

Asunto: `NAVAR cash · 23/09 · ATENCIÓN (2)`. Texto exacto de las secciones pedidas:

```text
Qué falta subir hoy
- Extracto de BBVA: el último extracto es del 21/09/2026, hace 2 días; falta actualizar al 22/09/2026.
- Extracto de NACION: el último extracto es del 15/09/2026, hace 8 días; falta actualizar al 22/09/2026.

NAVAR cash · 23/09/2026
Último extracto cargado: 23/09/2026
Último export de Tango: 23/09/2026

Sin alertas del circuito.

Llegó a Drive (desde el cierre anterior)
- ejemplo (09:00)
- ejemplo (09:00)
- ejemplo (09:00)
- ejemplo (09:00)
- ejemplo (09:00)
... y 2 más

El vigilante procesó
- tango: para_pegar_en_la_sheet_2026-09-23.xlsx (09:00)

La Sheet importó
- nada nuevo
```

BBVA y Nación son los únicos atrasados: 21/09 < cierre 22/09 y 15/09 < cierre 22/09.
Galicia y Macro del 22/09, y Corrientes del 23/09 no se piden.
Los nombres se conservan como aparecen en Origen (por eso NACION sale en mayúsculas).
Con los cinco al 22/09, el asunto es `NAVAR cash · 23/09 · al día`, la primera sección dice
`Está todo subido al día de hoy.` y no hay alertas del circuito.

**Sin ninguna fila Extracto:** conservar sólo el arqueo y las mismas entradas ficticias.
Asunto: `NAVAR cash · 23/09 · ATENCIÓN (2)`. Texto exacto:

```text
Qué falta subir hoy
- Extractos de banco: no hay bancos identificables en Saldos Bancarios; revisar la lista.

NAVAR cash · 23/09/2026
Último extracto cargado: sin datos
Último export de Tango: 23/09/2026

Alertas
- No hay extractos cargados. Pedir un extracto de banco y revisar la importación.

Llegó a Drive (desde el cierre anterior)
- ejemplo (09:00)
- ejemplo (09:00)
- ejemplo (09:00)
- ejemplo (09:00)
- ejemplo (09:00)
... y 2 más

El vigilante procesó
- tango: para_pegar_en_la_sheet_2026-09-23.xlsx (09:00)

La Sheet importó
- nada nuevo
```

**Límites:** probado localmente con servicios simulados, sin envío de mails, instalación
ni modificación de producción. Queda pegar el script y contrastar `avisoDiarioPrueba()`
con la Sheet al revisar. La fecha por banco es la más nueva del banco, no una certificación
por cuenta; un banco ausente de toda la lista no puede descubrirse sin otra fuente.

**Commit bloqueado por permisos:** `git add` de los tres archivos falló con
`Unable to create .../Finnauto/.git/worktrees/Finnauto-tarea12/index.lock: Operation not permitted`.
El índice vive fuera de la raíz permitida; no se intentó sortear la restricción.
Los cambios quedaron guardados, sin staging ni commit. Queda commitear en esta rama desde
el entorno con acceso a Git: `Corrige el aviso de extractos y muestra atrasos por banco`.

## Revisión
