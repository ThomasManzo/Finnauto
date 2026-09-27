# Tarea 19 — Galicia NAVAR: correcciones antes de la primera corrida completa en el banco
Estado: pendiente
Rama: tarea/galicia-correcciones

## Objetivo

La tarea 17 dejó el bot de Galicia para NAVAR preparado pero sin probar. En la revisión (ver
"Revisión" de `tareas/17-galicia-para-navar.md`) aparecieron tres problemas. Uno impide que el bot
publique nunca, otro lo rompe en cada actualización y otro deja huecos. El 27/09 se hizo un ensayo
en la notebook, con el código de hoy, y aparecieron cuatro más, todos de pantalla (puntos 4 a 7 del
Contexto). Corregir los siete para que la próxima corrida supervisada llegue hasta el Excel.

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `CLAUDE.md`, `tareas/17-galicia-para-navar.md` (entera,
incluida la Revisión), `bots/galicia/navar.py`, `bots/galicia/test_navar.py`, el bloque NAVAR de
`orquestador/correr.py`, `nucleo/fechas.py → rango_a_bajar`, `ingestas/drive_local.py → carpeta_datos`
y `lector/extractos.py → leer_planilla_galicia` y `procesar`.

1. **El export de Galicia no trae el número de cuenta** (comprobado en dos exports reales, 18/08–08/09
   y 26/08–22/09). Encabezados reales: `Fecha, Descripción, Origen, Débitos, Créditos, Grupo de
   Conceptos, Concepto, Número de Terminal, ...` y después `Saldo`. Ninguna celda tiene `0005459` ni
   `5459`. Hoy `validar_excel` exige la cuenta en el contenido, así que siempre frena.
2. **`clientes/navar/herramientas/actualizar.ps1` copia el repo entero sobre `C:\finauto`, incluido
   `perfil.json`.** Todo lo que se complete a mano en el perfil de la notebook se pierde en la
   próxima actualización. `carpeta_drive_destino` vacío hace frenar al orquestador.
3. **Rango de fechas.** `rango_a_bajar` aplica `backfill` en **todas** las corridas:
   `desde = min(desde, hasta - backfill)`. Con `backfill_dias_primera_vez: 7`, cada mañana baja los
   últimos 7 días + ayer. `lector/extractos.py` junta todos los archivos de la carpeta y descarta
   repetidos por (cuenta, fecha, importe) contando multiplicidad, así que la superposición no duplica.
   Eso resuelve el hueco inicial (el último export a mano llega al 22/09), los fines de semana y los
   feriados, donde hoy "sin movimientos" cuenta como falla.

**Lo que mostró el ensayo del 27/09/2026 en la notebook** (dos corridas en `--modo prueba`, con
capturas; el usuario de consulta entra bien y **no pide segundo factor** para consultar):

4. **La página tarda en cargar y el bot no espera.** Después del clic en "Office Banking" hay una
   espera fija de 4 s. En la primera corrida la pantalla de login estaba **en blanco** a los 4 s: el
   bot no vio el campo Usuario, concluyó "el navegador ya lo recuerda", cargó solo la clave y el
   botón "Ingresar" quedó deshabilitado. Lo mismo después de "Ingresar": a los 6 s el inicio todavía
   muestra el esqueleto gris (sin menú ni empresa), así que `capturar_empresa_activa` devuelve nada.
   El formulario real tiene dos campos con etiqueta visible: **"Usuario"** y **"Clave"**, y un
   botón **"Ingresar"**.
5. **NAVAR tiene una sola empresa y el nombre en pantalla es otro.** Arriba a la derecha se ve el
   nombre del usuario y debajo **`NAVAR SOCIEDAD ANONIMA`**. El inicio también dice
   `NAVAR SOCIEDAD ANONIMA - CONSUMO MASIVO`. El bot busca "NAVAR SA": la heurística heredada
   (busca sufijos tipo "S.A.", "SRL") no reconoce "SOCIEDAD ANONIMA", y `_empresa()` normalizado
   da `NAVARSOCIEDADANONIMA` ≠ `NAVARSA`. Resultado: "No pude confirmar la empresa".
   Además el bot intenta abrir el desplegable de empresas, que en MAGA hacía falta (14 empresas) y
   **en NAVAR no**: la empresa ya está activa al entrar.
6. **Clics a ciegas.** Al no poder abrir ese desplegable, `_abrir_menu_empresas` del bot original prueba
   selectores genéricos (`button[aria-haspopup]`, `header button:last-of-type`) y después **clics por
   coordenadas**. Uno de esos clics terminó en **"Cheques"** del menú lateral (captura
   `ERROR_menu_no_abrio`: "Necesitás permisos para emitir cheques"). No rompió nada porque el usuario
   es de consulta, pero en un banco **no se hacen clics a ciegas**.
7. **"Cuentas" aparece dos veces en el inicio**: en el menú lateral y como título de la tarjeta de
   cuentas. `ir_a_cuenta` hace `page.get_by_text("Cuentas", exact=True).click()`; con dos
   coincidencias Playwright corta por modo estricto. La tarjeta del inicio muestra la cuenta como
   `CC` con el texto **`N° 0005459-5 070-1`** (con el prefijo `N° `, así que `exact=True` sobre el
   número solo tampoco la encontraría si están en el mismo elemento). La pantalla de "Cuentas" (la
   del menú lateral) **todavía no se vio**.
   Otro detalle: arriba aparece un aviso negro "Todavía no activaste tu Office Token..." con una ✕.
   Es informativo, no bloquea; no hace falta cerrarlo, pero que no confunda la búsqueda de textos.

## Archivos permitidos

- `bots/galicia/navar.py`
- `bots/galicia/test_navar.py`
- `orquestador/correr.py` — **solo** el bloque `if cliente == "navar" and banco == "galicia"`.
- `clientes/navar/perfil.json` — **solo** `bancos.galicia`.
- `clientes/navar/documentos/instalar_notebook.md` — **solo** la sección 6.
- `tareas/19-galicia-correcciones.md`

No tocar `nucleo/`, el bot original `bots/galicia/bot.py`, los lectores ni el vigilante.

## Resultado esperado

1. **Cuenta**: sacar la exigencia de la cuenta dentro del Excel. La cuenta se confirma en pantalla
   (`ir_a_cuenta` ya exige que aparezca una sola vez y siga visible al abrir); dejar un comentario
   que diga por qué no se busca en el archivo (el export no la trae, comprobado 25/09). Se mantienen:
   que sea XLSX, que `leer_planilla_galicia` lo lea con movimientos y que las fechas estén en el rango.
2. **Carpeta**: si `carpeta_drive_destino` está vacío, resolverla como
   `carpeta_datos()` + `carpeta_drive_relativa` (`Bancos/galicia`), con separadores del sistema.
   Si igual no existe, frenar antes del llavero como hoy, con un mensaje que diga qué se buscó.
   `carpeta_drive_destino` sigue sirviendo para fijarla a mano si hiciera falta.
3. **Rango**: `bancos.galicia.backfill_dias_primera_vez: 7` en el perfil, con un `_nota` en criollo
   que explique que aplica a todas las corridas y por qué conviene.
4. **§6 de `instalar_notebook.md`**: sacar el paso de completar la ruta a mano (ahora la encuentra
   sola), explicar la ventana de 7 días y aclarar que el export no trae la cuenta y que por eso se
   confirma en pantalla. Revisar que la tabla "Qué puede fallar" siga siendo cierta.
5. **Tests** (`test_navar.py`, sin banco ni llavero): un Excel inventado **sin la cuenta** en el
   contenido y con los encabezados reales pasa; siguen frenando fecha fuera de rango, encabezado
   incompatible, filtro no confirmado y carpeta inexistente. La carpeta se resuelve desde un
   `FINAUTO_DRIVE` temporal cuando `carpeta_drive_destino` está vacío. Sumar tests de lo nuevo que
   se pueda probar sin navegador: que los dos nombres de empresa se reconozcan y otro no, y que
   `cambiar_a_empresa` / `descubrir_empresas` de la variante no hagan clics (frenen o devuelvan vacío).
6. **Login que espera y se confirma** (en `navar.py`, sobrescribiendo `hacer_login`; no tocar el
   original): después del clic en "Office Banking", **esperar** (hasta el `timeout` del contexto) a que
   el campo con etiqueta "Usuario" esté visible. Llenar Usuario y Clave **por su etiqueta**
   (`get_by_label` o equivalente), no "el primer campo de texto". Si el campo Usuario no aparece,
   frenar con "no cargó el formulario de login"; no asumir que el navegador lo recuerda.
   Después de "Ingresar", **confirmar que entró**: esperar a que el nombre de la empresa aparezca en
   el encabezado (y el formulario de login ya no esté). Si no, frenar con "login no confirmado" y
   captura. Nunca reintentar el login solo: varios intentos fallidos bloquean el usuario.
7. **Una sola empresa, sin desplegable**: `bancos.galicia.solo_empresa_activa: true` en el perfil (el
   motor ya soporta ese modo: no llama a `descubrir_empresas`). `solo_estas_empresas` pasa a aceptar
   `NAVAR SA` y `NAVAR SOCIEDAD ANONIMA`. `capturar_empresa_activa` de la variante busca esos nombres en
   el encabezado (no la heurística de sufijos) y devuelve siempre el nombre canónico **`NAVAR SA`**
   (es la clave del estado anti-duplicado; no debe cambiar entre corridas). `descubrir_empresas` y
   `cambiar_a_empresa` de la variante **no hacen clics**: si alguien los llama, frenan con un mensaje
   claro. Ningún clic por coordenadas en la variante de NAVAR.
8. **Ir a la cuenta sin ambigüedad**: el clic a "Cuentas" tiene que apuntar al ítem del **menú lateral**
   (por rol de enlace/botón/ítem de menú dentro de la navegación, o equivalente robusto), no a
   cualquier texto "Cuentas". Si hay más de una coincidencia, frenar; no usar `.first`. La cuenta
   se busca aceptando el prefijo `N° ` (el número exacto, con o sin prefijo, **una sola vez**). Como la
   pantalla de "Cuentas" no se vio todavía, dejar capturas antes y después de cada clic y un comentario
   que diga que este paso se afina en la próxima corrida supervisada.

## Comprobaciones

1. `python -m py_compile bots/galicia/navar.py bots/galicia/test_navar.py orquestador/correr.py` y JSON
   válido de `perfil.json`.
2. `python -m unittest bots.galicia.test_navar` OK.
3. Dejar escrito qué NO se pudo probar (todo lo de pantalla del banco). Las capturas del ensayo
   del 27/09 **no están en el repo** (tienen datos reales); lo de pantalla está descrito arriba.
4. `grep` de nombres propios de personas vacío en lo agregado. Commit en la rama.

## Qué hice

## Revisión
