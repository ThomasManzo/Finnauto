# Tarea 23 — Galicia NAVAR: el recorrido real, sin calendario
Estado: lista para revisión
Rama: tarea/galicia-recorrido-real

## Objetivo

Reescribir el recorrido del bot de Galicia para NAVAR copiando **lo que hace una persona**, no lo que
hacía el bot de MAGA. Hasta ahora se armó a ciegas y fue tropezando de a una pantalla. El 27/09
Thomas hizo el recorrido a mano con capturas y es más corto que el que tiene el bot:

**login → inicio → clic en la cuenta → leer saldos → descargar Excel.** Sin menú "Cuentas", sin
filtro de fechas, sin calendario. El Excel que da el banco por defecto trae **los últimos 30 días**,
y eso alcanza: el lector ya descarta los repetidos entre archivos que se superponen.

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `CLAUDE.md`, `tareas/19-galicia-correcciones.md` (entera),
`bots/galicia/navar.py`, `bots/galicia/test_navar.py`, `nucleo/loop.py` (qué llama y en qué orden),
`nucleo/utilidades.py → _parse_monto` y `lector/extractos.py → leer_planilla_galicia`.

**Por qué falló la última corrida (27/09, 20:49 y 20:50):** las dos veces
`ERROR en el login: no cargó el formulario de login`, **a los 4 segundos**. El `timeout` es de 45 s,
así que no fue por falta de espera. Fue una excepción inmediata, casi seguro porque
`get_by_label("Usuario", exact=True)` encontró **más de un elemento** (una copia oculta del
formulario), y `wait_for` corta en el acto por modo estricto. El log no dice la causa porque el
mensaje de afuera tapa la de adentro.

**El recorrido real, pantalla por pantalla** (capturas de Thomas, 27/09):

1. **Login directo**: `https://empresas.bancogalicia.com.ar/login`. No hace falta pasar por la home ni
   por "Office Banking". El formulario dice "Iniciá sesión" y tiene dos campos con etiqueta visible,
   **Usuario** y **Clave**, un checkbox "Recordar usuario" (no tocarlo) y el botón **Ingresar**,
   que se habilita cuando los dos campos tienen algo.
2. **Inicio** (`/inicio`): arriba a la derecha, el nombre del usuario y `NAVAR SOCIEDAD ANONIMA`.
   Hay una tarjeta "Cuentas" con **una sola cuenta**: `CC`, el saldo y `N° 0005459-5 070-1`,
   y debajo un enlace "Ir a cuentas". **Thomas hace clic en la tarjeta de la cuenta** (donde está
   el saldo).
3. **Cuenta** (`/cuentas/movimientos`): el título dice **`Cuenta Corriente $ N° 0005459-5 070-1`**
   (con una flechita de desplegable). Debajo hay tres tarjetas:
   - **Saldos**: la etiqueta `Actual` con el monto abajo (formato `- $X`) y la etiqueta
     `Disponible` con su monto ("saldo actual más el acuerdo para descubierto").
   - **Acuerdos para descubierto**: `Usado: $X de $Y` y `Vencimiento: dd/mm/aaaa`.
   - Impuestos y comisiones (no interesa).

   Después viene la tabla **Movimientos**, con un buscador, el botón **Filtros** y, a su derecha, un
   **botón con ícono de descarga (flecha hacia abajo), sin texto**.
4. **Descarga**: ese botón abre un menú con cinco opciones: `.CSV`, `.PDF`, `.SAP`, **`Excel`**,
   `Personalizado`. Con **Excel** baja un archivo llamado **`Extracto_CC545950701.xlsx`**, que es la
   cuenta sin ceros adelante ni separadores: `0005459-5 070-1` → `545950701`.

**El Excel real** (el de Thomas del 27/09, revisado en la Mac): una hoja `Movimientos`. Encabezados
`Fecha, Descripción, Origen, Débitos, Créditos, Grupo de Conceptos, Concepto, Número de Terminal,
Observaciones Cliente, Número de Comprobante, Leyendas Adicionales 1..4`. Fechas como datetime. El
bajado el 27/09 va del **27/08 al 22/09**: 31 días hacia atrás, y el último movimiento es el último
día con movimientos, no ayer. **No trae el número de cuenta en ninguna celda.**
`leer_planilla_galicia` lo lee bien (111 movimientos).

## Archivos permitidos

- `bots/galicia/navar.py`
- `bots/galicia/test_navar.py`
- `clientes/navar/perfil.json` — **solo** `bancos.galicia`.
- `clientes/navar/documentos/instalar_notebook.md` — **solo** la sección 6.
- `tareas/23-galicia-recorrido-real.md`

No tocar `nucleo/`, `orquestador/`, el bot original `bots/galicia/bot.py`, los lectores ni el
vigilante. Si algo no se puede hacer sin tocarlos, anotarlo en "Qué hice" y preguntar.

## Resultado esperado

Todo en `BotGaliciaNavar`, sobrescribiendo lo heredado. Se mantienen: un solo intento de login,
cero clics por coordenadas, nada de `.first` para **elegir dónde hacer clic**, y frenar ante la duda.

1. **Una ayuda para "el único visible, esperando"**: una función que, hasta el `timeout`, busque
   entre las opciones de locator y devuelva **el único elemento visible**. Si hay dos o más
   visibles, frena. Los ocultos se ignoran. Si se acaba el tiempo, frena. Reemplaza a
   `_unico_visible` (que no espera) en todos los clics y campos del recorrido.
2. **Login**: `page.goto("https://empresas.bancogalicia.com.ar/login")`, sin pasar por la home.
   Usuario, Clave e Ingresar con la ayuda del punto 1 (por etiqueta, con alternativa por rol
   `textbox` de nombre "Usuario" y el `input[type=password]` visible para la clave). La
   confirmación de entrada queda como está: formulario oculto y nombre de NAVAR visible en la página.
   **Cuando frene, que el mensaje del log diga la causa real** (por ejemplo "el campo Usuario
   aparece 2 veces visible" o "no apareció en 45 s"), no solo "no cargó el formulario".
3. **Ir a la cuenta**: en el inicio, hacer clic en el elemento visible con `N° 0005459-5 070-1`
   (la tarjeta de la cuenta), usando la ayuda del punto 1. **Sacar el paso del menú "Cuentas".**
   Confirmar que se abrió con dos cosas: la URL contiene `/cuentas/movimientos` y es visible un
   texto que **contiene** `N° 0005459-5 070-1` (el título es `Cuenta Corriente $ N° ...`, así que el
   patrón no puede estar anclado con `^...$`). Si el número aparece más de una vez en esa pantalla
   no es error: alcanza con uno visible y la URL. Capturas `inicio`, `cuenta_abierta`.
4. **Saldos**: `capturar_saldos` propio que lea en la tarjeta "Saldos" el monto que sigue a la
   etiqueta exacta `Actual` y el que sigue a `Disponible`, con `_parse_monto` (ya entiende
   `- $X`). Devuelve las mismas claves que el original (`actual`, `actual_texto`,
   `disponible`, `disponible_texto`), así el motor los guarda en `_SALDOS_` sin tocar `nucleo/`.
   El acuerdo de descubierto sale como `disponible − actual`: no hace falta leerlo aparte. Si no
   puede leer algún saldo, lo avisa en el log y **sigue** (los movimientos importan más).
   Captura `saldos`.
5. **Sin filtro de fechas**: `aplicar_filtro_fechas` no toca la pantalla. Solo loguea "Galicia NAVAR
   no usa filtro: baja los últimos 30 días que trae el banco" y devuelve `True`.
6. **Descarga**: clic en el botón de descarga que está a la derecha de "Filtros" (por rol/nombre
   o aria-label si tiene; si no, el botón que sigue a "Filtros" dentro de la sección Movimientos,
   pero **único visible**). Captura `menu_descarga`. Después, clic en la opción de texto exacto
   **`Excel`** del menú abierto; hoy busca `xlsx`, y **esa opción no existe**. Controles sobre la
   descarga:
   - `suggested_filename` termina en `.xlsx`.
   - `suggested_filename` contiene los dígitos de la cuenta sin ceros adelante (`545950701`, calculado
     desde `cfg["cuenta"]`, no escrito a mano). **Es la única prueba de cuenta que da el archivo.**
     Si no coincide, frena y no publica.
7. **Validación del Excel** (reemplaza a la de "rango pedido"):
   - `leer_planilla_galicia` lo lee y trae **al menos un** movimiento.
   - Ninguna fecha es **posterior a hoy**.
   - Ninguna fecha es anterior a **hoy − 35 días**. El banco da unos 31, y los 4 de margen son para
     no frenar por un borde de calendario. Si trae algo más viejo, es otro export y hay que mirarlo.
   - Se deja de exigir `self.rango` para descargar.

   La publicación sigue igual: copia temporal + `os.replace`, con el nombre
   `Movimientos GALICIA <fecha y hora>.xlsx`.
8. **Perfil**: sacar `backfill_dias_primera_vez` (ya no se usa para bajar) y actualizar el `_nota`:
   baja siempre los 30 días que da el banco, y el estado solo evita bajar dos veces el mismo día.
9. **§6 de `instalar_notebook.md`**: describir el recorrido nuevo (login directo, tarjeta de la cuenta,
   saldos, descarga Excel de 30 días), qué se confirma en cada paso, qué captura mirar si falla, y que
   si el bot falla varios días seguidos el primer día que ande **recupera hasta 30 días** solo.
   Sacar todo lo del calendario y la ventana de 7 días.
10. **Tests** (sin banco ni llavero, con dobles como los que ya hay):
    - La ayuda del punto 1: un oculto + un visible → elige el visible; dos visibles → frena; nada
      visible → frena al vencer el tiempo.
    - Confirmación de cuenta con el texto `Cuenta Corriente $ N° 0005459-5 070-1` → pasa.
    - Nombre de descarga `Extracto_CC545950701.xlsx` → pasa; `Extracto_CC999999999.xlsx` → frena;
      un `.csv` → frena.
    - Excel inventado con los encabezados reales, fechas dentro de 30 días → pasa; con una fecha
      futura → frena; con una de hace 40 días → frena; sin movimientos → frena.
    - `aplicar_filtro_fechas` no toca la página.
    - Sacar los tests del calendario y del rango que ya no aplican.

## Comprobaciones

1. `python -m py_compile bots/galicia/navar.py bots/galicia/test_navar.py` y JSON válido de
   `perfil.json`.
2. `python -m unittest bots.galicia.test_navar` OK.
3. `grep` de nombres propios de personas vacío en lo agregado; tampoco montos reales. Commit en la
   rama.
4. Dejar escrito qué NO se pudo probar: todo lo de pantalla. Lo prueba Thomas en la notebook con
   `--modo prueba`.

## Qué hice

- Reemplacé el paso por la home por el login directo de Galicia. Usuario, Clave, Ingresar y cada
  clic del recorrido usan una ayuda que espera al único elemento visible, ignora copias ocultas y
  frena con la causa concreta ante duplicados o vencimiento del tiempo.
- El inicio abre directamente la tarjeta del número de cuenta configurado. La pantalla siguiente
  se confirma por URL y por al menos una aparición visible del número completo; ya no se abre el
  menú Cuentas.
- Agregué la lectura propia de Actual y Disponible dentro de la tarjeta Saldos. Si falta uno, queda
  un aviso y la descarga de movimientos continúa.
- Eliminé el uso del filtro y del calendario. El bot abre el botón de descarga junto a Filtros,
  elige la opción exacta Excel y controla extensión y cuenta mediante el nombre original.
- El Excel se publica sólo si el lector encuentra movimientos y todas sus fechas están entre hoy
  y hoy menos 35 días. Ya no depende de un rango elegido en pantalla.
- Actualicé el perfil para quitar el backfill del banco y documentar que cada archivo trae unos
  30 días. Reescribí la sección 6 de la guía con el recorrido, las capturas y la recuperación tras
  varios días de falla.
- Rehice los tests con datos inventados: cubren el selector visible, login directo, confirmación de
  cuenta, saldos, nombres de descarga, fechas válidas/futuras/viejas, archivo vacío, ausencia de
  filtro, empresa y carpeta de Drive. `python -m unittest bots.galicia.test_navar`: 17 pruebas OK.
- Verifiqué compilación y JSON válido. No se pudo probar ninguna pantalla, clic o descarga real del
  banco, ni la sincronización con Drive o la tarea programada; eso requiere `--modo prueba` en la
  notebook.

## Revisión
