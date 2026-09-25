# Tarea 19 — Galicia NAVAR: tres correcciones antes de la primera prueba en el banco
Estado: pendiente
Rama: tarea/galicia-correcciones

## Objetivo

La tarea 17 dejó el bot de Galicia para NAVAR preparado pero sin probar. En la revisión (ver
"Revisión" de `tareas/17-galicia-para-navar.md`) aparecieron tres problemas. Uno impide que el bot
publique nunca, otro lo rompe en cada actualización y otro deja huecos. Corregirlos para que la
primera corrida supervisada en la notebook tenga chances reales de salir bien.

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
   `FINAUTO_DRIVE` temporal cuando `carpeta_drive_destino` está vacío.

## Comprobaciones

1. `python -m py_compile bots/galicia/navar.py bots/galicia/test_navar.py orquestador/correr.py` y JSON
   válido de `perfil.json`.
2. `python -m unittest bots.galicia.test_navar` OK.
3. Dejar escrito qué NO se pudo probar (todo lo de pantalla del banco).
4. `grep` de nombres propios de personas vacío en lo agregado. Commit en la rama.

## Qué hice

## Revisión
