# Tarea 82 — Control diario de saldos contra movimientos
Estado: aprobada
Rama: tarea/control-diario

## Objetivo
Que todos los días se vea si cierra esta cuenta, banco por banco:

saldo del día anterior + ingresos − egresos = saldo del día.

El control de cierre mensual (tarea 81) no alcanza: un error de un día que se cancela al día siguiente no se ve
en el mes. El control mide y avisa: **no cambia ningún renglón ni ningún saldo del cash**.

## Contexto
- Todo está en `clientes/navar/herramientas/crear_cash.gs`, Apps Script de Google Sheets. Leer `armarCash`,
  `_armarPeriodica_`, `_saldoBancoAl_`, `_bancos_`, `_movDelMes_`, `_estadoControl_` y `_controlDeCierre_`.
- `_controlDeCierre_` hoy arma la sección 7, solo en Cash Mensual, con tolerancia de $ 1 M.
- Cada banco tiene en Saldos Bancarios un saldo por día con movimientos. Su Origen en Movimientos es
  `"Extracto " + b.nombre`. Las cajas (`b.caja`) están en Movimientos con Banco / Cuenta = `b.caja` y Origen `Tango*`.
- El saldo de una caja se calcula con sus propios movimientos, así que su diferencia solo es real el día de un
  arqueo. Antes de su primer arqueo el saldo queda plano. Por eso las cajas se muestran pero **nunca marcan REVISAR**.
- Un banco sin extracto no muestra diferencia, porque le faltan a la vez el saldo y los movimientos. Por eso el
  control tiene que mostrar el atraso de cada extracto y no dar por bueno un día sin datos.
- No usar datos reales en ningún archivo: el repo es público. Comentarios en criollo: Thomas no programa.

## Archivos permitidos
- `clientes/navar/herramientas/crear_cash.gs`
- `lector/pruebas/probar_control_diario.cjs` (nuevo)
- `lector/pruebas/probar_control_cierre.cjs` (solo si un cambio de firma lo exige, sin debilitar lo que prueba)
- `tareas/82-control-diario.md`

## Resultado esperado

### 1. Solapa nueva "Control diario"
Función `_armarControlDiario_(ss)`, llamada desde `armarCash` **antes** de armar las pantallas, porque Cash la
referencia. Sumarla a la lista de `_separadorLocal_` si corresponde. Constantes arriba de la función, comentadas:
`CONTROL_DIAS = 120`, `CONTROL_AVISO_DIAS = 30`, `CONTROL_ATRASO_DIAS = 7`, `TOLERANCIA_DIARIA = 1`.

- **Encabezado:** título con `_titulo_`; A2 "Hoy", B2 `=TODAY()`; C2 el aviso (punto 3); B3 el último día con
  extracto, igual que en las pantallas; una línea que explique cómo se lee.
- **Atraso, arriba de las columnas de cada cuenta:** "Último extracto" (`MAXIFS` de la fecha de Saldos Bancarios
  para esa cuenta) y "Días sin extracto" (hoy − esa fecha). En un banco, marcar "ATRASADO" si los días superan
  `CONTROL_ATRASO_DIAS`. En una caja la fila dice lo mismo, pero se lee como último arqueo y nunca marca atraso.
- **Tabla, una fila por día, la más nueva arriba** (fecha `=$B$2-i`, para que avance sola sin rearmar):
  1. Fecha
  2. Estado
  3. Saldo del día anterior
  4. Ingresos: `Tipo = Ingreso`, sin `Transferencia Interna`, `Estado = Real`, orígenes `ORIGENES_REALES`
  5. Egresos: lo mismo con `Tipo = Egreso`, mostrado en positivo (`-` de la suma con signo)
  6. Pases entre cuentas: neto de `Transferencia Interna`, con su signo
  7. Saldo que debería haber: 3 + 4 − 5 + 6
  8. Saldo del día
  9. DIFERENCIA: 8 − 7, redondeada al peso
  10. Una columna de diferencia por cada banco y después una por cada caja
  - Columnas auxiliares ocultas al final: el saldo de cada cuenta a esa fecha, con `_saldoBancoAl_(b, celdaFecha)`.
    Sumar una fila auxiliar oculta debajo de la última, para el "día anterior" de esa última.
- **Diferencia de una cuenta en un día:** saldo de hoy − saldo de ayer − movimientos del día de esa cuenta, redondeado
  al peso. Filtrar la fecha con `>=fecha` y `<fecha+1`, y `Estado = Real`. Si la fecha es posterior al último extracto
  de esa cuenta y la diferencia da 0, dejar la celda vacía, no 0: un día sin datos no es un día que cierra.
- **Estado de un día**, en este orden:
  1. "sin extracto" si la fecha es posterior a B3;
  2. "REVISAR" si llega a `TOLERANCIA_DIARIA`, en valor absoluto: algún banco, los pases, o lo que quede de la
     DIFERENCIA después de restarle todas las cuentas (movimientos de una cuenta sin saldo). Las cajas no marcan;
  3. "sin mov." si ingresos, egresos y pases dan 0 y la DIFERENCIA da 0;
  4. "OK".
  Las celdas vacías no pueden romper la fórmula: usar `N()`.
- **Formato:** verde en OK, rojo en REVISAR, gris en "sin extracto" y "sin mov." Columnas de cajas en gris, con una nota
  que explique por qué no marcan. Fila y columna de fecha fijas. Separador de miles sin decimales.
- **Velocidad:** escribir con `setFormulas` por bloque, no celda por celda. Al rearmar, limpiar los formatos
  condicionales y mostrar las filas y columnas antes de volver a ocultar.

### 2. Sección 7 también en la solapa Cash (la diaria)
- Generalizar `_controlDeCierre_` con opciones: título, textos de los renglones y tolerancia. Cash Mensual tiene que
  quedar **exactamente igual** que hoy, con sus textos y `TOLERANCIA_CONTROL`.
- Llamarla también con el período `"dia"`, con `TOLERANCIA_DIARIA`, textos "del día" y título "7 · Control del día: ¿los
  movimientos explican el saldo?". No agregarla a Cash Semanal. `_estadoControl_` recibe la tolerancia como parámetro
  opcional; sin él usa `TOLERANCIA_CONTROL`.

### 3. Aviso en C2
- **Solapa Control diario y solapa Cash:** "Control diario: OK" si no hay nada para revisar. Si no, un texto con los días en
  REVISAR de los últimos `CONTROL_AVISO_DIAS` y la cantidad de bancos en ATRASADO. En Cash suma además los REVISAR de su
  sección 7, porque ahí se ve lo que la solapa no ve: movimientos sin renglón.
- **Cash Mensual:** su aviso sigue igual.
- **Color en las tres solapas:** verde si dice OK y rojo si no. Hoy sale rojo aunque diga OK. Usar una regla condicional
  que no pise las demás reglas de la hoja.

### 4. Instrucciones
Actualizar en `armarInstrucciones` la línea de la sección 7, que ya no es solo de Cash Mensual, y agregar la solapa
Control diario a la lista de solapas: "fórmula sobre las listas", la carga "nadie".

## Comprobaciones
- `lector/pruebas/probar_control_diario.cjs`, con bancos y montos inventados. Sacar a funciones chicas lo que se pueda
  probar sin Sheet (`_estadoDia_`, `_movCuentaDelDia_` y las que hagan falta) y comprobar:
  - una diferencia que se cancela al día siguiente marca REVISAR en los dos días;
  - las cajas no marcan REVISAR, aunque tengan diferencia;
  - $ 0,40 de diferencia no marca, $ 1 sí;
  - los pases sin cancelar marcan;
  - un movimiento de una cuenta sin saldo marca;
  - una fecha posterior a B3 da "sin extracto", y un día sin nada da "sin mov.";
  - lo que mira cada cuenta: solo ese día, solo lo real, solo su origen;
  - `_estadoControl_` sin tolerancia sigue dando lo mismo que antes.
- Node está en `/Applications/ChatGPT.app/Contents/Resources/cua_node/bin/node`. Tienen que seguir pasando
  `probar_control_cierre.cjs`, `probar_cash_cajas*`, `probar_canchada_envases*` y `probar_panel_canchada*`.
- No se puede probar en la Sheet desde acá. Instalar y validar contra los datos reales lo hace Claude.

## Qué hice
- Modifiqué `clientes/navar/herramientas/crear_cash.gs`: nueva solapa Control diario con 120 días móviles, diferencias por banco y caja, saldos auxiliares ocultos, atraso de extractos y avisos de los últimos 30 días. Las cajas se muestran en gris y no disparan REVISAR ni ATRASADO.
- Agregué la sección 7 a Cash con tolerancia de un peso y textos del día. El mensual conserva su tolerancia, textos y redondeos; Cash Semanal no incorpora el control. C2 usa colores condicionales sin borrar las reglas de bancos. Actualicé Instrucciones.
- Creé `lector/pruebas/probar_control_diario.cjs` con datos inventados: evalúa las fórmulas de estados, filtros por cuenta/día/origen, pases, cuenta sin saldo, tolerancias, celdas vacías y fechas sin extracto. También comprueba armado por bloques, fila auxiliar, orden de cuentas, avisos y rearmado sin acumular reglas con una hoja simulada.
- Pasaron con el Node indicado: `probar_control_diario.cjs`, `probar_control_cierre.cjs`, `probar_cash_cajas.cjs`, `probar_canchada_envases.cjs` y `probar_panel_canchada.cjs`. `git diff --check` sin errores.
- No usé datos reales, no instalé dependencias y no hice commits. Solo toqué el script, la prueba nueva y esta consigna; no fue necesario modificar la prueba mensual.
- Pendiente de Claude: instalar y validar en Google Sheets, incluidos separadores locales, colores y cálculo con sus listas. Las pruebas locales simulan fórmulas y armado; no reemplazan esa validación. Sin otras dudas de alcance.
## Revisión
Revisión de Claude (06/11/2026). Tres retoques sobre lo de Codex, que pasaron las pruebas:
- El resto de la DIFERENCIA ahora marca solo si supera un peso por cuenta: sumar cuentas ya redondeadas puede errarle.
- "Sin renglón" vuelve a la decena también en el diario, como en el mensual: es una resta de redondeos.
- La nota de las cajas va una vez, en el título de la columna, no en cada celda.

Instalado aplicando solo los pedazos cambiados sobre la copia con los textos reales, con largo y huella verificados antes y
después de recargar. Contra los datos reales: los días con diferencia de bancos coinciden al peso con un cálculo aparte, Cash
Mensual conserva sus diferencias y no hay errores de fórmula en las pantallas (los números quedan fuera del repo).

Límite conocido: un pase cuya otra pata está en un banco con extracto atrasado marca REVISAR hasta que llega ese extracto.
