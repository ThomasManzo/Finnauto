# Tarea 16 — Saber si la notebook está viva (hoy el silencio es ambiguo)
Estado: lista para revisión
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

- Toqué únicamente los cuatro archivos permitidos, en el worktree de `tarea/latido-vigilante`.
- `vigilante.py`: una marca UTC en `vigilante_ultima_pasada.txt`, reemplazada mediante un
  temporal ya cerrado. Se escribe antes del estado y de los lectores, incluso con `--simular`.
  Elegí archivo aparte porque una línea diaria no permite detectar un corte de una hora.
  No agrega líneas al log en pasadas vacías. Si falla la escritura, informa por consola y deja
  seguir el procesamiento; no falsea una marca nueva. No instalé dependencias.
- `aviso_diario.gs`: lee el contenido, no la fecha de sincronización. Corte de más de 60 minutos
  primero en el cuerpo y en las alertas. Muestra hoy/ayer/fecha anterior en Buenos Aires.
  Falta de archivo, duplicados, fecha inválida o futura quedan como señal no verificable.
- `manual_cash.md` §6: alcance de la marca, instalación pendiente, revisión de Drive, sesión
  de Windows, escritorio remoto y suspensión. No se afirma la causa del corte real.

### Comprobaciones locales

- Compilación OK con `PYTHONPYCACHEPREFIX=/tmp/tarea16-pycache
  /Users/thomasmanzo/Documents/Finnauto/.venv/bin/python -m py_compile
  clientes/navar/herramientas/vigilante.py` (en una sola línea). El primer intento con Python
  del sistema falló por permisos de su caché fuera del sandbox; se repitió con caché temporal.
- Ejecuté `main()` con argumentos `--simular`, usando `FINAUTO_DRIVE` en una carpeta temporal
  vacía y redirigiendo ESTADO/LOG a esa misma carpeta. Resultado observado:
  `2026-09-24T23:06:17+00:00`. Pasada normal vacía: marca presente y ningún log creado.
- Con fuente y proceso ficticios: lector con código 1 y lector con timeout conservan la marca.
  Fallo inventado al reemplazarla: conserva la anterior y elimina el temporal. No se ejecutó
  ningún lector real ni se accedió a `privado/` ni al Drive del cliente.
- Ejecuté el código JavaScript en V8 con servicios de Google simulados. Armado del mail:
  marca fresca, 60 minutos exactos, 60 minutos y un segundo, ayer, días anteriores, ausente
  y futura. Verifiqué que la alerta de vida encabeza el cuerpo en los casos correspondientes.
  Lectura: fecha UTC válida, inválida, día inexistente, sin zona, archivo ausente y duplicado.
  El formateo de fechas se reemplazó por Intl en Buenos Aires; no es una corrida en Apps Script.
- `git diff --check`: OK. Búsqueda sin distinguir mayúsculas de nombres de personas conocidos
  por el contexto: vacía en ambos scripts y el manual. La consigna conserva sus menciones
  preexistentes a agentes, sin agregar nombres de personas.

### Ejemplos a mano del mail (inventados)

Para un aviso del 24/09/2026 a las 09:00 de Buenos Aires, sin cambiar las otras fuentes:

**Marca fresca** `2026-09-24T11:45:00+00:00`:

```text
Qué falta subir hoy
[los faltantes de las fuentes, si los hay]

NAVAR cash · 24/09/2026
Vigilante: última pasada a las 08:45 de hoy. Es señal de vida, no de procesamiento correcto.
[último extracto, Tango y demás secciones habituales]
```

**Marca vieja** `2026-09-23T23:00:00+00:00`:

```text
Estado del vigilante
La notebook no está procesando: última pasada a las 20:00 de ayer. Revisar que esté prendida y que la tarea programada corra. Revisar también la sincronización de Drive.

Qué falta subir hoy
[los faltantes de las fuentes, si los hay]
```

La misma advertencia queda primera en “Alertas” y suma una alerta al asunto; el resto del
mail mantiene sus datos. Los corchetes de estos ejemplos son aclaraciones, no texto generado.

### Límites y entrega

No instalé los cambios ni mandé mails. Falta verificar la sincronización del reemplazo en
Drive, `avisoDiarioPrueba()` en Google y las ejecuciones con escritorio remoto desconectado,
sesión bloqueada/cerrada y suspensión. La marca prueba el inicio de la revisión, no su final;
una simulación también la renueva. Si Drive no está disponible no puede publicarse una marca.


El commit se intentó en la rama indicada, pero `git add` y `git commit` fallaron con
`Unable to create .../.git/worktrees/Finnauto-tarea16/index.lock: Operation not permitted`.
El índice está fuera del directorio permitido por el sandbox. Los cuatro archivos quedan
modificados y sin commit para que quien revisa los agregue y commitee, según `tareas/LEEME.md`.

## Revisión
