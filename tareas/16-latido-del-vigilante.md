# Tarea 16 — Saber si la notebook está viva (hoy el silencio es ambiguo)
Estado: pendiente
Rama: tarea/latido-vigilante

## Objetivo

Hoy el vigilante **sólo escribe en el log cuando hace algo**. Si no llegó ningún archivo nuevo,
no anota nada. Resultado: no se puede distinguir "no había nada que procesar" de "la notebook
está apagada o la tarea programada no corre". Pasó hoy: 14 horas sin una línea y no había forma
de saber cuál de las dos cosas era.

Que el sistema pueda decir **"la notebook está viva y miró a tal hora"**.

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `CLAUDE.md`, `clientes/navar/documentos/manual_cash.md` §6.

`clientes/navar/herramientas/vigilante.py` corre cada 15 minutos en la notebook de la empresa
(tarea programada de Windows). Al final de `main()` hay un `if not corridos ... pass  # silencio`.
El log se copia a Drive (`_para la Sheet/vigilante.log`) y de ahí lo lee el aviso diario de las
09:00 (`clientes/navar/herramientas/aviso_diario.gs`).

**El silencio en el log fue una decisión deliberada** (para no llenarlo de ruido cada 15 minutos)
y está bien como criterio. Lo que falta es una señal de vida que no sea ruido.

## Archivos permitidos

- `clientes/navar/herramientas/vigilante.py`
- `clientes/navar/herramientas/aviso_diario.gs`
- `clientes/navar/documentos/manual_cash.md`
- `tareas/16-latido-del-vigilante.md`

No tocar los lectores ni `importar_cashflow.gs` ni `crear_cash.gs`.

## Resultado esperado

1. El vigilante deja una **marca de vida** en cada pasada, sin ensuciar el log: por ejemplo un
   archivo aparte y chiquito en `_para la Sheet/` (algo tipo `vigilante_ultima_pasada.txt`) con
   la fecha y hora de la última vez que miró, o una sola línea por día en el log. Elegí y explicá.
   **No** una línea cada 15 minutos.
2. El **aviso de las 09:00** usa esa marca: si la última pasada es de hace más de **1 hora**, la
   primera alerta del mail pasa a ser *"la notebook no está procesando: última pasada a las HH:MM
   de ayer/hoy. Revisar que esté prendida y que la tarea programada corra."* Es la alerta más
   importante de todas: si la notebook no corre, **nada** de lo demás pasa, y el resto del mail
   dice "no llegó nada" como si fuera normal.
3. Que la marca se escriba **aunque la pasada no haga nada y aunque falle un lector**: es una
   señal de "estoy viva", no de "salió todo bien".
4. Tener en cuenta que la tarea de Windows puede estar configurada para correr **sólo con el
   usuario conectado**: si eso explica un corte, dejarlo anotado en el manual como algo a revisar
   (la conexión de escritorio remoto se cae y la sesión se bloquea).

## Comprobaciones

1. `python -m py_compile clientes/navar/herramientas/vigilante.py`.
2. Correr el vigilante con `--simular` y mostrar que la marca se escribe igual.
3. Para el `.gs`: ejemplo a mano del texto del mail en los dos casos (marca fresca y marca vieja).
4. `grep` de nombres propios de personas vacío. Commit en la rama.

## Qué hice

## Revisión
