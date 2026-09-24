# Tarea 15 — Un export con otras columnas frena la lectura de TODOS los bancos
Estado: lista para revisión
Rama: tarea/bancos-tolerantes

## Objetivo

Desde las **17:36 del 23/09** el vigilante falla cada 15 minutos y **no procesa ningún banco**:

```
2026-09-23 22:38:07  bancos: 26 archivo(s) nuevos o cambiados → extractos.py
2026-09-23 22:38:09  bancos: FALLÓ (código 1): KeyError: 'Detalle'
```

Dos problemas, y el segundo es más grave que el primero:

**A.** El export nuevo de un banco trae **otros nombres de columna** y el lector revienta.
**B.** Un solo archivo ilegible **tumba la corrida entera**: los otros cuatro bancos, que están
perfectos, tampoco se procesan. Un archivo raro tiene que quedar afuera con un aviso, no frenar todo.

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `CLAUDE.md`.

El archivo que rompe es `Bancos/bbva/Movimientos BBVA 2026-09-23.xls`, y la causa está medida:

| Export | Columnas (fila 7) |
|---|---|
| BBVA hasta el 22/09 | `Fecha · Fecha Valor · Concepto · Codigo · Número Documento · Oficina · Crédito · Débito · Detalle` |
| BBVA del 23/09 | `Fecha · Fecha Valor · Concepto · Codigo · Nro de cheque · Oficina · Crédito · Débito · Saldo Parcial` |

`leer_planilla_bbva` (en `lector/extractos.py`, alrededor de la línea 179) hace `ix["Detalle"]` y
tira `KeyError` porque esa columna ya no existe.

El archivo nuevo, entero (tiene una sola fila de movimiento):

```
Empresa:          NAVAR SA(30558525025)
Cuenta:           489-000765/9(CC $)
Sucursal:         489 - EMPRESA POSADAS
Saldo:            -3.502.551,25
Movimientos de:   23-09-2026

Fecha       Fecha Valor  Concepto              Codigo  Nro de cheque  Oficina  Crédito     Débito  Saldo Parcial
23-09-2026  23-09-2026   TRANSFERENCIA CUENTA  842                    489-…    4.538.200           -8.040.751,25
```

Ojo con algo importante: en el formato viejo el saldo del día se sacaba buscando el texto
`Saldo Disponible: …` dentro de la columna `Detalle`. En este formato **el saldo viene en su propia
columna** (`Saldo Parcial`), que es más directo. Y además el encabezado trae `Saldo: -3.502.551,25`,
que **no coincide** con el `Saldo Parcial` de la fila (-8.040.751,25): decidir cuál se usa como
cierre del día y explicar por qué. (Probablemente uno es el saldo disponible y el otro el contable;
no inventar: si no se puede determinar, marcarlo para revisar y no pisar el saldo bueno.)

Este mismo problema ya apareció dos veces esta semana con los exports de Tango (columnas que cambian
de orden y de nombre entre descargas). **Es un patrón, no un caso aislado.**

## Archivos permitidos

- `lector/extractos.py`
- `clientes/navar/herramientas/vigilante.py` — sólo para que un lector que falla no impida que
  se publique lo que sí se pudo leer, si es que eso se resuelve ahí.
- `lector/pruebas/`
- `clientes/navar/documentos/manual_cash.md`
- `tareas/15-un-archivo-raro-frena-todos-los-bancos.md`

No tocar `lector/cash_limpio.py` ni `dashboard/` (los está tocando la tarea 14), ni
`importar_cashflow.gs`, ni `crear_cash.gs`.

## Resultado esperado

1. **B primero**: un archivo que no se puede leer se **saltea**, se cuenta y se informa en el
   resumen (`no pude leer <archivo>: <motivo>`), y **la corrida sigue** con el resto. Que el
   vigilante publique lo que sí se leyó. Si ningún archivo de un banco se pudo leer, ese banco
   queda sin datos nuevos, pero los otros cuatro tienen que entrar igual.
2. **A**: `leer_planilla_bbva` acepta los dos formatos. Las columnas se buscan por nombre entre
   alternativas (`Detalle` o `Saldo Parcial`; `Número Documento` o `Nro de cheque`), y si falta
   una que no es imprescindible, se sigue sin ella en vez de cortar.
3. Revisar los otros lectores de planilla (Macro, Galicia) con el mismo criterio: hoy cualquiera
   de ellos se cae igual si el banco cambia un encabezado.
4. Prueba automática: un Excel chico armado por la prueba con cada formato (el viejo, el nuevo, y
   uno con una columna imprescindible ausente) → el tercero se saltea con aviso y los dos primeros
   se leen bien.

## Comprobaciones

1. Correr el lector sobre una **copia** de la carpeta real de bancos (no sobre Drive) y pegar en
   "Qué hice": cuántos archivos se leyeron, cuántos se saltearon y por qué, y el último saldo por
   banco. Antes de esta tarea el resultado era: **falla total, cero bancos**. La copia está en
   `/private/tmp/claude-501/-Users-thomasmanzo-Documents-Finnauto/f6552fb9-9e4b-4af5-b4b5-9d35a7af4f0f/scratchpad/bancos`
   (si no está, copiarla desde Drive; **no escribir en Drive**).
2. Decir qué saldo se tomó para BBVA el 23/09 y por qué.
3. `python -m py_compile` y la prueba nueva.
4. `grep` de nombres propios de personas vacío. Commit en la rama.

## Qué hice

- Estado inicial cambiado a `en curso`; trabajo en el worktree provisto, rama
  `tarea/bancos-tolerantes`. No se escribió en Drive ni se usó `clientes/*/privado/`.
- `lector/extractos.py`: cada archivo se lee de forma independiente; si falla se descarta
  entero, se cuenta y se informa el motivo. También avisa si no reconoció ninguna fila.
  Si todos fallan, deja resumen pero no genera un Excel vacío. BBVA acepta ambos formatos;
  Macro y Galicia resuelven columnas por nombre y alternativas; las opcionales no cortan.
  Se mantiene la deduplicación entre PDF y Excel. Se quitaron nombres de personas de notas
  existentes del lector y se dejó un error claro cuando el OCR devuelve texto vacío.
- `clientes/navar/herramientas/vigilante.py`: registra errores parciales y recupera del último
  publicado las filas faltantes de los bancos con errores antes de aplicar los controles y
  publicar. Esto evita borrar su historia o frenar a los otros bancos por el achicamiento.
  Conserva fechas, saldos nuevos y pagos repetidos reales. Admite rutas Windows y Mac.
- `lector/pruebas/test_extractos_tolerantes.py`: 10 pruebas con Excel inventados y carpetas
  temporales. Cubren ambos BBVA, columna imprescindible ausente, referencias opcionales,
  columnas reordenadas, saldo contradictorio, archivos PDF/Excel corruptos, fallo a mitad
  de lectura, publicación con un banco fallido, recuperación repetida sin duplicar,
  recuperación de saldos con fechas originales, publicación previa del mismo día,
  ausencia de publicación previa y rechazo de una salida totalmente vacía.
- `clientes/navar/documentos/manual_cash.md`: explicado qué se saltea, cómo se conserva
  historia y cuándo un saldo queda para revisar. No se instalaron dependencias nuevas.

### Corrida sobre la copia real

Se usó exclusivamente la carpeta temporal indicada en Comprobaciones, que ya existía.
Intérprete: `/Users/thomasmanzo/Documents/Finnauto/.venv/bin/python` (el worktree no trae .venv).
Comando: `python lector/extractos.py --carpeta <copia indicada> --cliente navar --hoy 2026-09-24`.

**Resultado final: salida 0; 24 archivos leídos, 2 salteados; 2.230 movimientos.**
Se generaron `para_pegar_bancos_2026-09-24.xlsx` y `resumen_bancos_2026-09-24.md` en esa copia.
Los dos salteados son `nacion/Nacion Saldo 18-09.pdf` y `nacion/nacion movimientos.pdf`:
el OCR no devolvió texto. Al primer intento Swift no pudo usar su caché habitual; se reintentó
con `SWIFT_MODULECACHE_PATH=/private/tmp/t15-swift` y
`CLANG_MODULE_CACHE_PATH=/private/tmp/t15-clang`. Swift terminó, pero sin texto reconocido.
No se inventó un saldo de Nación ni se buscó en Drive otra fuente. La falla queda aislada y
los otros cuatro bancos entran. La librería PDF además emite avisos sobre `fontTools` ausente;
no impidieron esta lectura y no se instaló esa dependencia.

Última foto leída (importes verificados en el Excel generado, con centavos):

| Banco / cuenta | Fecha | Saldo |
|---|---|---:|
| BBVA principal | 21/09/2026 | $7.642.055,79 |
| BBVA recaudación | 16/09/2026 | $0,00 |
| Galicia | 22/09/2026 | -$9.998.348,83 |
| Macro | 23/09/2026 | -$43.392.742,64 |
| Corrientes | 16/09/2026 | -$45.306.818,06 |
| Nación | sin lectura válida en esta corrida | sin saldo nuevo |

**BBVA 23/09:** se leyó el movimiento de $4.538.200. No se tomó como cierre ni
-$8.040.751,25 de Saldo Parcial ni -$3.502.551,25 del encabezado: la diferencia no prueba
cuál es contable/disponible. El resumen dice REVISAR y se conserva la foto del 21/09.
No se extrapoló un saldo a partir del importe del movimiento.

### Validación y límites

- `python -m unittest lector.pruebas.test_extractos_tolerantes lector.pruebas.test_cheques_en_cartera -q`:
  **16 pruebas OK** (10 nuevas y 6 existentes; incluye controles de retención del vigilante).
- `python -m py_compile lector/extractos.py clientes/navar/herramientas/vigilante.py lector/pruebas/test_extractos_tolerantes.py`: OK.
- `git diff --check`: OK. Búsqueda de nombres de personas del contexto en los archivos
  tocados: sin coincidencias.
- La publicación del vigilante se probó en carpetas temporales con ejemplos inventados,
  incluso caída de más de la mitad de las filas y un banco entero ilegible. La corrida real
  fue del lector sobre la copia, sin ejecutar el vigilante productivo ni importar la Sheet.
  El resumen refleja los saldos de la lectura nueva; si el vigilante recupera historia,
  agrega un aviso de filas recuperadas (no recalcula ese resumen histórico).
- Pendiente para producción: revisión e instalación de la rama en la notebook, recuperación
  o regeneración del OCR de Nación y confirmación del cierre BBVA. No se tocó Apps Script.


- **Commit pendiente por sandbox:** `git add` fue rechazado al crear
  `/Users/thomasmanzo/Documents/Finnauto/.git/worktrees/Finnauto-tarea15/index.lock`
  (`Operation not permitted`). Los cinco archivos quedaron en el worktree, sin stage ni
  commit, como contempla `tareas/LEEME.md`. Para la revisión, usar `git diff` y revisar también
  el archivo nuevo `lector/pruebas/test_extractos_tolerantes.py`; `git diff main..rama`
  todavía no incluye estos cambios. No se intentó eludir la restricción.

## Revisión
