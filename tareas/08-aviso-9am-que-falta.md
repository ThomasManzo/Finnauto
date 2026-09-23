# Tarea 08 — El aviso de la mañana: a las 9, y enfocado en qué falta subir
Estado: lista para revisión
Rama: tarea/aviso-9am

## Objetivo

Cambiar el aviso diario (ya escrito en `clientes/navar/herramientas/aviso_diario.gs`, tarea 01)
para que salga **a las 09:00 de Buenos Aires** y para que lo principal del mail sea **qué falta
subir hoy**, no qué pasó ayer.

Razón de Thomas (22/09): *"la alerta debería ser a las 9 de la mañana diciendo lo que falta por
subir, que de todas formas, como todavía no está automatizado, no se va a subir nada antes de las
9 de la mañana"*. O sea: hasta que los bots y la API de Tango estén, alguien tiene que subir los
archivos a mano, y el mail es el recordatorio de qué falta.

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `tareas/01-aviso-diario.md` (la consigna original y lo
que hizo Codex) y `clientes/navar/documentos/manual_cash.md` §6.

El aviso ya está escrito y revisado, con `_armarAviso_(ahora, datos)` separado de la parte que
manda el mail, y con alertas por antigüedad (extracto de más de 7 días, export de Tango de más de
3). **Falta instalarlo en la planilla**: el disparador todavía no existe. Esta tarea lo deja listo
para instalar con la hora nueva.

## Archivos permitidos

- `clientes/navar/herramientas/aviso_diario.gs`
- `clientes/navar/herramientas/importar_cashflow.gs` — **solo** las etiquetas del menú si hablan de
  las 07:30 (la tarea 05 también toca este archivo: tocá únicamente esas líneas).
- `clientes/navar/documentos/manual_cash.md` — §6.
- `tareas/08-aviso-9am-que-falta.md`

## Resultado esperado

1. El disparador se crea a las **09:00** de Buenos Aires (`atHour(9)`), y las funciones y etiquetas
   que dicen "07:30" pasan a decir "09:00".
2. El mail arranca con una sección **"Qué falta subir hoy"**, antes que nada. Una línea por fuente
   que esté atrasada, diciendo **qué es y desde cuándo falta**, con este criterio:
   - **Extractos de banco**: uno por banco. Si el último saldo de ese banco es de hace más de 1 día
     hábil, falta. Hoy, por ejemplo, Corrientes y Nación venían de varios días atrás mientras BBVA,
     Galicia y Macro estaban al día: el mail tiene que nombrar **a los dos que faltan**, no decir
     "faltan extractos" en general. Los bancos salen de la lista de Saldos Bancarios, no escritos a mano.
   - **Exports de Tango**: cobranzas, pagos y cheques, **por empresa (A y AA)**. Si el más nuevo de
     una de esas seis combinaciones es de ayer o más viejo, falta. Hoy pasó exactamente eso: los de
     A estaban al día y los de AA eran del día anterior.
   - **Tesorería de AA** y el **arqueo de caja**, que se cargan a mano.
   - Si no falta nada: una sola línea, "Está todo subido al día de hoy."
3. Lo que hoy es el cuerpo (llegó / se procesó / se importó / alertas) queda **después**, más corto.
4. Como el mail sale a las 09:00 y nadie sube nada antes, la ventana que mira para decir "falta"
   tiene que ser **desde el cierre del día anterior**, no "últimas 24 horas" corridas. Explicá en un
   comentario cómo quedó esa cuenta y qué pasa un lunes (el viernes es el último día hábil).

## Comprobaciones

1. Los mismos ejemplos a mano que dejó la tarea 01, recalculados con la sección nueva: qué dice el
   mail (a) si no falta nada, (b) si faltan dos bancos, (c) si falta AA. Pegarlos en "Qué hice".
2. Que no queden referencias a las 07:30 en ningún lado.
3. `grep` de nombres propios vacío. Commit en la rama.

## Qué hice

Implementado en el worktree existente, rama `tarea/aviso-9am`, limpia al comenzar.
Solo se modificaron los cuatro archivos permitidos:

- `aviso_diario.gs`: disparador `atHour(9).nearMinute(0)` con zona Buenos Aires;
  sección inicial completa de faltantes (sin truncarla), asunto que cuenta faltantes y alertas,
  y resumen posterior de hasta cinco líneas por sección. Se conserva la detección de trabas,
  errores y antigüedad del circuito anterior. La frase de fuentes al día no afirma que el
  procesamiento ni los importes estén validados.
- Lee Banco, Empresa, Origen y Fecha de Saldos Bancarios por encabezado. Agrupa bancos sin
  escribir sus nombres a mano, toma su último saldo de Extracto y excluye Varios/(varios)/Caja.
  Para arqueo exige AA, origen Manual y uno de esos nombres de caja. Una fila sin fecha o
  una fecha futura no acredita actualización. Si no hay lista o falla su lectura, lo informa.
- Controla las seis combinaciones Tango A/AA × cobranzas/pagos/cheques desde los archivos
  de entrada, usando la fecha válida del nombre, no la modificación en Drive ni el consolidado.
  Tesorería AA usa la fecha del nombre en su carpeta, con prefijo AA. Subir hoy un archivo
  de ayer no lo convierte en actual. Fechas inválidas, futuras o ausentes no acreditan carga.
- `importar_cashflow.gs`: únicamente la etiqueta del menú que instala el aviso.
- `manual_cash.md`: únicamente §6, con criterios, fuentes, ventana y límites.
- Esta consigna: estado y entrega; no se cambió la consigna original ni Revisión.

**Criterios adoptados y límites para revisar:**

- Bancos y arqueo deben cubrir el último día hábil cerrado; el lunes, el viernes. Hábil es
  lunes a viernes, sin calendario de feriados. El arqueo no tenía umbral explícito: se adoptó
  el cierre anterior porque es una carga manual del saldo físico.
- Los exports de Tango y tesorería AA deben llevar fecha de hoy. Esto sigue la regla explícita
  de que un export de ayer falta, aunque a las 9 todavía no haya empezado la carga manual.
- La actividad se cuenta desde la medianoche posterior al último cierre hábil: martes desde
  las 00:00 del martes; lunes desde las 00:00 del sábado. Los pendientes anteriores siguen
  alertando; no desaparecen por salir de esa ventana.
- Cada faltante muestra fecha requerida y última disponible. Sin historia fechada no se
  inventa desde cuándo falta. Cheques agrupa propios/terceros por empresa y toma el más nuevo,
  conforme a las seis combinaciones pedidas; no certifica ambos subtipos por separado.
- Un banco ausente por completo de Saldos Bancarios no se puede descubrir desde esa lista.
  Los nombres de banco se agrupan sin distinguir mayúsculas; no se inventan equivalencias.
- El control comprueba fechas y presencia, no abre los exports para certificar sus datos ni
  concilia importes. No se leyó ni creó nada en `privado/`, ni se instalaron dependencias.

**Pruebas ejecutadas:**

No hay Node en el PATH. Se compiló el `.gs` completo con `new Function` en el motor JavaScript
V8 de la herramienta y se ejecutó `_armarAviso_` con datos inventados y `Utilities.formatDate`
reemplazado por `Intl.DateTimeFormat` en Buenos Aires. Pasaron 12 comprobaciones: los tres
casos de abajo, lunes, fecha imposible, saldo futuro, fallo de Drive, saldos vacíos, ausencia
de los siete exports, origen incorrecto del arqueo, banco nuevo sin extracto y no modificación
de la foto de entrada. Además se probó un lunes completo con viernes al día y actividad justo
antes/después del cierre, la lectura de saldos con servicios simulados y error de Drive, y la
instalación simulada: hora 9, minuto 0, zona correcta y borrado solo del aviso previo.
El primer intento de ese bloque adicional tuvo un error en el reemplazo de Utilities del arnés;
se corrigió el arnés y se ejecutó completo con éxito; no era un error del archivo `.gs`.

`git diff --check` pasó. La búsqueda de nombres propios indicada en tarea 01 quedó vacía en
`aviso_diario.gs`. No quedan referencias al horario viejo en el script, el importador ni el
manual. **La comprobación global del horario no puede quedar vacía dentro de este alcance**:
quedan referencias históricas en esta consigna y tarea 01, y una descripción desactualizada en
`clientes/navar/LEEME.md:128`. LEEME y tarea 01 están fuera de los archivos permitidos y no se
tocaron; queda para integración actualizar la descripción de LEEME.

**Ejemplos reproducidos (datos inventados, no estado real del cliente):**

`ahora = 2026-09-22T09:00:00-03:00`. Base: cinco bancos (BBVA, Galicia, Macro, Corrientes,
Nación), todos con saldo Extracto del 21/09, arqueo Manual de AA en (varios) del 21/09;
seis archivos `A/AA cobranzas/pagos/cheques terceros 2026-09-22.xlsx` y
`AA movimientos tesoreria 2026-09-22.xlsx`, modificados hoy 08:30; publicado Tango de hoy
08:40; Registro, retenidos, log y errores vacíos. Ninguna entrada supera dos horas.

(a) Base, nada falta. Asunto: `NAVAR cash · 22/09 · al día`. Primera sección:

```text
Qué falta subir hoy
Está todo subido al día de hoy.
```

(b) Solo cambiar Corrientes al 17/09 y Nación al 18/09. Asunto:
`NAVAR cash · 22/09 · ATENCIÓN (2)`. Primera sección:

```text
Qué falta subir hoy
- Extracto de Corrientes: falta actualizar al 21/09/2026; última fecha disponible: 17/09/2026.
- Extracto de Nación: falta actualizar al 21/09/2026; última fecha disponible: 18/09/2026.
```

(c) Volver a la base y cambiar la fecha del nombre de los tres exports AA al 21/09 (aunque
se hayan subido hoy). Asunto: `NAVAR cash · 22/09 · ATENCIÓN (3)`. Primera sección:

```text
Qué falta subir hoy
- Tango AA — cobranzas: falta actualizar al 22/09/2026; última fecha disponible: 21/09/2026.
- Tango AA — pagos: falta actualizar al 22/09/2026; última fecha disponible: 21/09/2026.
- Tango AA — cheques: falta actualizar al 22/09/2026; última fecha disponible: 21/09/2026.
```

En los tres, después aparece fecha de hoy, último extracto y Tango, “Sin alertas del circuito”,
cinco entradas y “... y 2 más”, el publicado Tango y “La Sheet importó / - nada nuevo”. No
se afirma importación: el publicado reciente aún no supera el umbral de dos horas.

**No verificado desde acá:** Drive y Sheet reales, formatos de sus filas actuales, permisos,
MailApp, entrega del correo, sincronización y disparador real. No se envió ni instaló nada.
Falta pegar el código, revisar `avisoDiarioPrueba()` contra Drive/Saldos/Registro reales y luego
instalar desde una sola cuenta. La hora es aproximada (margen de Google), no puntual al minuto.

**Commit bloqueado por el sandbox:** se intentó `git add` únicamente de los cuatro archivos.
Falló con `Unable to create .../Finnauto/.git/worktrees/Finnauto-tarea08/index.lock:
Operation not permitted`. El índice está fuera de la raíz permitida; no se intentó sortear
la restricción. Los cambios quedaron guardados, sin staging ni commit. Queda hacer el commit
en esta rama desde el entorno con permisos, con mensaje sugerido:
`Mueve el aviso a las 9 y detalla qué fuentes falta actualizar`.


## Revisión
