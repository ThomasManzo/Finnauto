# Tarea 05 — Que un filtro puesto a mano no vuelva a romper la importación
Estado: pendiente
Rama: tarea/importador-filtros

## Objetivo

Hoy (22/09) el cash estuvo roto varias horas porque alguien dejó **filtros puestos a mano** en
solapas de la planilla. El importador escribió sobre esas solapas y **desacomodó las filas**: un
cheque propio real de $10,8 M quedó con fecha de agosto y salió del cash, y cheques a cobrar de
noviembre aparecieron en 2027. Después, todas las importaciones automáticas empezaron a fallar con
`No se admite esta operación en un rango con una fila filtrada` y la planilla quedó congelada.

Que eso no pueda volver a pasar. Filtrar una lista para buscar algo es lo más normal del mundo:
el sistema tiene que aguantarlo.

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `CLAUDE.md`, `clientes/navar/documentos/manual_cash.md` §6.

Lo que pasó, con fechas (hora de la planilla, que va 4 h atrás de Buenos Aires):

- `11:55 tango ok` — esta importación **escribió mal**: había filtros activos y las columnas
  quedaron corridas entre sí. Las Observaciones de una fila describían el cheque correcto mientras
  la fecha era la de otra fila. Nadie se enteró: dijo `ok`.
- `13:32`, `14:16`, `14:32`, `15:32`, `16:32` — todas `ERROR` con el mensaje del rango filtrado.
- `16:51 tango ok` — recién después de sacar a mano los filtros de cinco solapas
  (Cuentas a Cobrar, Cuentas a Pagar, Cartera de Cheques, Movimientos y Saldos Bancarios).

**Lo más grave no es el error: es la importación que dijo `ok` y escribió mal.** Un error se ve;
un `ok` mentiroso no.

Quién escribe: `clientes/navar/herramientas/importar_cashflow.gs`, función `_volcar_` (escribe
columna por columna con `setValues` y estira fórmulas con `copyTo`), llamada desde `_importar_`.

Los análisis de las tareas 02 y 03 están en `tareas/02-*.md` y `tareas/03-*.md`, y en
`lector/pruebas/` quedaron dos scripts de comparación que sirven de referencia.

## Archivos permitidos

- `clientes/navar/herramientas/importar_cashflow.gs`
- `clientes/navar/herramientas/aviso_diario.gs` — si corresponde sumar una alerta (ver abajo).
- `clientes/navar/documentos/manual_cash.md` — §6 y §7.
- `tareas/05-importador-a-prueba-de-filtros.md`
- `lector/pruebas/` — si hacés una prueba.

## Resultado esperado

1. **Antes de escribir, el importador deja la solapa sin filtro y sin filas ocultas**, y cuando
   termina la deja como la encontró si eso es posible sin riesgo. En Apps Script: `sheet.getFilter()`
   y `.remove()`; ojo que también existen las **vistas de filtro** (`filter views`), que son otra cosa
   y no las remueve `getFilter()`. Si una vista de filtro no se puede manejar desde el script, hay
   que **detectarla y abortar con un error claro** en vez de escribir mal.
2. **Si por cualquier motivo no se puede garantizar la escritura correcta, NO escribir**: abortar y
   anotar en Registro con un mensaje que diga qué hacer ("sacá el filtro de la solapa X y volvé a
   correr Importar lo nuevo"). Vale más no importar que importar mal.
3. **Verificación después de escribir**: comparar unas cuantas filas escritas contra lo leído del
   `para_pegar` (por ejemplo, las primeras y las últimas de cada solapa, y que la cantidad de filas
   coincida). Si no coinciden, dejarlo en Registro como `ERROR` aunque la escritura no haya tirado
   excepción. Es lo que habría cazado el `ok` mentiroso de las 11:55.
4. Que el mensaje de Registro diga **en qué solapa** estuvo el problema (hoy el error no lo decía).
5. Si el aviso diario puede avisar "hay una importación que dijo ok pero no cuadró", sumalo.

## Comprobaciones

Apps Script no corre en el worktree. Entonces:

1. Explicar en "Qué hice" **exactamente** qué hace el código nuevo, paso por paso.
2. Dejar escrito el **guion de prueba manual** para correr en la planilla: qué filtro poner, en qué
   solapa, qué botón apretar y qué tendría que pasar (incluido el caso de la vista de filtro).
3. Si se puede probar la lógica pura con Node (como hizo la tarea 03 con `probar_volcado_fechas.cjs`),
   hacerlo y decir qué cubre y qué no.
4. `grep -n -i -E "priscilla|karina|celia|miriam|milagros|charles|thomas"` vacío en lo tocado.
5. Commitear en la rama; si el sandbox no deja, anotarlo.

## Qué hice

## Revisión
