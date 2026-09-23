# Tarea 08 — El aviso de la mañana: a las 9, y enfocado en qué falta subir
Estado: pendiente
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

## Revisión
