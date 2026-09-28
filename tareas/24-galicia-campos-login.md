# Tarea 24 — Galicia NAVAR: encontrar Usuario y Clave por su id
Estado: aprobada (mergeada el 27/09/2026)
Rama: tarea/galicia-campos-login

## Objetivo

Que el login de Galicia encuentre **un solo** campo Usuario y **un solo** campo Clave. Hoy frena
con `el campo Usuario aparece 2 veces visible` y nunca llega a escribir.

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `tareas/23-galicia-recorrido-real.md` y
`bots/galicia/navar.py → hacer_login`.

Corrida del 27/09/2026 a las 21:55: `ERROR en el login: el campo Usuario aparece 2 veces visible`.
Después se corrió en la notebook un diagnóstico que abre `https://empresas.bancogalicia.com.ar/login`
sin escribir nada. Esto es lo que ve Playwright:

| Búsqueda | Coincidencias visibles |
|---|---|
| `get_by_label("Usuario", exact=True)` | **2**: un `<label aria-label="Usuario">` (la etiqueta misma) y `<input id="userInput" name="userId" type="text">` |
| `get_by_role("textbox", name="Usuario", exact=True)` | 1: el `input#userInput` |
| `get_by_label("Clave", exact=True)` | **2**: un `<label aria-label="Clave">` y `<input id="userPassword" name="password" type="password">` |
| `input:visible` | 3: `#userInput`, `#userPassword` y el checkbox "Recordar usuario" (sin id) |
| `get_by_role("button", name="Ingresar", exact=True)` | 1: `<button aria-label="Ingresar">` (con clase `button-disabled` hasta que se llenan los campos) |

La etiqueta tiene su propio `aria-label`, así que `get_by_label` la cuenta como un elemento
etiquetado "Usuario". Por eso `_esperar_unico_visible` encuentra dos y frena. **El freno es
correcto**; lo que está mal es la forma de buscar.

## Archivos permitidos

- `bots/galicia/navar.py` — **solo** `hacer_login`.
- `bots/galicia/test_navar.py`
- `tareas/24-galicia-campos-login.md`

Nada más.

## Resultado esperado

1. En `hacer_login`, las opciones para cada campo, en este orden:
   - Usuario: `page.locator("input#userInput")` → `page.get_by_role("textbox", name="Usuario", exact=True)`.
   - Clave: `page.locator("input#userPassword")` → `page.locator("input[type='password']")`.
   - **Sacar `get_by_label`** de las dos listas.
   - Ingresar queda como está.

   Un comentario en criollo: la etiqueta del formulario tiene su propio `aria-label`, así que buscar
   por etiqueta devuelve la etiqueta y el campo. Los `id` son los del formulario visto el 27/09.
2. Se mantiene todo lo demás: `_esperar_unico_visible`, el único intento, la confirmación posterior.
3. **Test**: una página falsa donde `get_by_label("Usuario")` devolvería dos visibles (etiqueta +
   campo) y `locator("input#userInput")` uno solo. El login elige el campo, lo llena una vez y no
   llama a `get_by_label`. Lo mismo para Clave. Ajustar `test_login_directo` si hace falta.

## Comprobaciones

1. `python -m py_compile bots/galicia/navar.py bots/galicia/test_navar.py`.
2. `python -m unittest bots.galicia.test_navar` OK.
3. Commit en la rama. Lo de pantalla lo prueba Thomas en la notebook.

## Qué hice

- En `hacer_login`, Usuario se busca primero como `input#userInput` y después por rol textbox;
  Clave se busca primero como `input#userPassword` y después por tipo password. Eliminé las dos
  búsquedas por etiqueta y dejé sin cambios el botón Ingresar, el único intento y la confirmación.
- Dejé comentado por qué no se usa la etiqueta y que los `id` salen del formulario observado el
  27/09.
- El doble de la página ahora reproduce que cada `get_by_label` devolvería etiqueta y campo. El test
  confirma que esa API no se consulta, que los `id` eligen los campos y que cada uno se llena una
  sola vez.
- `python -m py_compile bots/galicia/navar.py bots/galicia/test_navar.py` y
  `python -m unittest bots.galicia.test_navar`: 17 pruebas OK.
- No se pudo probar la pantalla real del banco; la verificación final corresponde a la próxima
  corrida supervisada en la notebook.

## Revisión

**Claude, 27/09/2026.** Hizo justo lo pedido: `input#userInput` e `input#userPassword` primero, con
alternativas por rol y por `type=password`, y sin `get_by_label`. Solo tocó `hacer_login`. En el test,
la página falsa ahora devuelve etiqueta + campo por `get_by_label` (el caso real) y se comprueba que el
login no la consulta y llena cada campo una sola vez. 17 OK, compila, `git diff --check` limpio.
Aprobada.

