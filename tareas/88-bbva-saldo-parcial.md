# Tarea 88 — BBVA: publicar el saldo del archivo diario ("Saldo Parcial")
Estado: aprobada
Rama: tarea/bbva-saldo-parcial

## Objetivo
Cuando NAVAR baja de BBVA el archivo diario (el que trae la columna "Saldo Parcial"), el lector hoy
tira el saldo y avisa "REVISAR saldo… No se publica el saldo parcial". El Cash queda mostrando un
saldo viejo de BBVA. Queremos que ese saldo se publique solo cuando el archivo cierra.

## Contexto
- `lector/extractos.py`, función `leer_planilla_bbva`. BBVA tiene dos formatos de planilla:
  - **viejo** ("Últimos 60 días"): columna "Detalle" con "Saldo Disponible: …". Anda bien, no se toca.
  - **diario**: columna "Saldo Parcial". Las filas vienen **de la más nueva a la más vieja** y el
    "Saldo Parcial" de cada fila es el saldo **ANTES** de ese movimiento, no después.
- Hoy el código compara el "Saldo Parcial" de la primera fila contra el "Saldo:" del encabezado. Con la
  regla de arriba eso nunca coincide (salvo casualidad), y por eso se descarta siempre.
- Ejemplo inventado (encabezado "Saldo: 1.150,00"), filas de más nueva a más vieja:

  | Fecha      | Crédito | Débito | Saldo Parcial |
  |------------|---------|--------|---------------|
  | 23-09-2026 |         | -200   | 1350          |
  | 23-09-2026 | 400     |        | 950           |
  | 23-09-2026 |         | -50    | 1000          |

  Cadena: 1000 − 50 = 950 ✓; 950 + 400 = 1350 ✓; cierre = 1350 − 200 = **1150** = encabezado ✓.
- Se verificó (Claude, contra archivos reales que no están en el repo) que todos los archivos diarios
  que hay cumplen esta regla.
- **Mismo día en varios archivos**: NAVAR baja el archivo varias veces por día, y los archivos del
  mismo día pisan el saldo uno al otro en `procesar` (gana el último leído, que es por orden de nombre).
  Un archivo bajado a la mañana tiene menos movimientos y su saldo queda viejo. Para la misma cuenta y
  el mismo día tiene que ganar el saldo del archivo que trae **más movimientos de ese día**; si empatan,
  el último leído (como hoy).

## Archivos permitidos
- `lector/extractos.py` (solo `leer_planilla_bbva` y el paso 2 de `procesar`, donde se arma `por_dia`)
- `lector/pruebas/test_extractos_tolerantes.py` (ajustar el ejemplo del formato diario si hace falta)
- `lector/pruebas/test_bbva_saldo_parcial.py` (nuevo)
- este archivo de tarea ("Qué hice")

## Resultado esperado
1. En el formato diario, `leer_planilla_bbva`:
   - controla la cadena: para cada par de filas seguidas, `parcial(más vieja) + importe(más vieja)` =
     `parcial(más nueva)` (tolerancia 0,01);
   - calcula el cierre de cada día como `parcial + importe` de la fila más nueva de ese día;
   - si la cadena cierra **y** el cierre del último día es igual al "Saldo:" del encabezado, publica los
     cierres de cada día en `saldos_por_dia` y no pone la nota "REVISAR saldo";
   - si algo no cierra, se queda como hoy: entran los movimientos, no entra el saldo y la nota dice
     REVISAR. La nota tiene que decir cuál de las dos cosas falló (cadena o encabezado) y con qué números.
2. Formato viejo: igual que hoy.
3. En `procesar`, al juntar `saldos_por_dia` de varias lecturas de la misma cuenta y día, gana la lectura
   con más movimientos de ese día (empate: la última leída). Los saldos que vienen de movimientos con
   saldo (PDF) siguen como hoy.
4. Comentarios en criollo explicando la regla del "saldo de antes del movimiento".

## Comprobaciones
- Pruebas nuevas con ejemplos inventados (montos chicos, cuenta "111-000111/1", empresa de ejemplo):
  a) el ejemplo de arriba publica 1150 el 23/09 sin nota REVISAR;
  b) mismo archivo con encabezado 1350 (el criterio viejo) → no publica y la nota dice REVISAR;
  c) cadena rota (cambiar un parcial) → no publica, nota REVISAR;
  d) dos días en el mismo archivo → un cierre por día;
  e) dos archivos del mismo día y cuenta: uno con 1 movimiento (cierre 500) y otro con 3 (cierre 0),
     con nombres tales que el de 1 movimiento se lee último → el saldo publicado es 0.
- `.venv/bin/python -m unittest lector.pruebas.test_bbva_saldo_parcial lector.pruebas.test_extractos_tolerantes`
  y el resto de `lector/pruebas/test_*.py` que ya pasaban, siguen pasando.

## Qué hice
- `lector/extractos.py`: el formato diario valida la cadena usando el saldo anterior al
  movimiento y calcula los cierres sumando el importe. Publica solamente si la cadena y el
  encabezado cierran (tolerancia de un centavo). Las notas de revisión indican qué falló y
  los números involucrados; un parcial ausente también impide publicar. Se conserva el
  tratamiento del formato viejo y de los movimientos con saldo de PDF.
- En el paso 2 de `procesar`, para cada cuenta y fecha gana la lectura con más movimientos
  de ese día, contados antes de quitar duplicados; en empate gana la última lectura.
- `lector/pruebas/test_bbva_saldo_parcial.py`: ocho pruebas con datos inventados para cadena
  correcta, encabezado incorrecto, cadena rota, dos días, cierre cero de la lectura más
  completa, empate, parcial ausente y tolerancia de un centavo.
- `lector/pruebas/test_extractos_tolerantes.py`: corregí el parcial del ejemplo diario para
  que represente el saldo antes del movimiento.
- Desde este worktree, con `/Users/thomasmanzo/Documents/Finnauto/.venv/bin/python`:
  - `-m unittest lector.pruebas.test_bbva_saldo_parcial lector.pruebas.test_extractos_tolerantes`:
    18 pruebas, OK.
  - `-m unittest discover -s lector/pruebas -p 'test_*.py'`: 172 pruebas, OK.
  - La suite mostró avisos por el PDF inválido de prueba y archivos sin cerrar en
    `vigilante.py`; no hubo fallas. `git diff --check` pasó.
- Intenté `git add` y `git commit` en `tarea/bbva-saldo-parcial`, pero el sandbox
  impidió crear `Finnauto/.git/worktrees/finauto-tarea-88/index.lock`
  (`Operation not permitted`). Los cambios quedan sin commit para que Claude los commitee.
- No usé datos reales ni archivos privados, ni instalé dependencias. Sin dudas pendientes.

## Revisión
Claude, 11/11/2026: revisé el diff, corrí las 172 pruebas (OK) y corrí `procesar` con los archivos
reales de BBVA (solo en esta Mac, fuera del repo): la cuenta principal queda con un cierre por día que
coincide con el banco y la secundaria cierra en cero, sin errores. Thomas dio el OK general para
subirla. Al actualizar la notebook hay que borrar el saldo de BBVA que se cargó a mano en Saldos
Bancarios para el 11/11 (si no, ese día se suma dos veces).

