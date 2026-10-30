# Tarea 70 — Autorización por link de Mercado Libre y Mercado Pago (canje del código y renovación de tokens)
Estado: aprobada
Rama: tarea/70-autorizacion-meli

## Objetivo
Que un cliente nuevo autorice a Finauto con un link (un clic con su cuenta de Mercado Libre o de Mercado Pago) y
que, a partir de ahí, las bajadas tengan siempre un permiso vigente **sin que nadie vuelva a hacer nada**.
Esta tarea es solo la "llave": convertir el código que devuelve el link en tokens guardados en el llavero de la
máquina, y renovarlos solos. Las bajadas de ventas y liquidaciones van en otra tarea.

## Contexto
- Leer `AGENTS.md`, `CLAUDE.md` y `tareas/LEEME.md`. Mirar `ingestas/tango_live.py` (cómo se escribe una
  ingesta acá: solo biblioteca estándar, `urllib`, comentarios en criollo) y `nucleo/credenciales.py`
  (el llavero vía `keyring`).
- **El repo es público.** Nada de datos reales: ni nombres de clientes, ni montos, ni tokens, ni números de
  aplicación reales. En pruebas y ejemplos: cliente `ejemplo`, números inventados.
- Cómo funciona el permiso (verificado en la documentación oficial, 30/10/2026):
  - **Son dos aplicaciones separadas** (Mercado Libre y Mercado Pago lo exigen desde el 30/08/2026), cada una
    con su `client_id` (número) y `client_secret`. Las crea Thomas en sus cuentas de desarrollador.
  - **Ya están en el llavero** antes de correr esto, cargadas con el `setup_credenciales.py` de siempre:
    servicio `finauto:<cliente>:mercadolibre` y `finauto:<cliente>:mercadopago`, cuenta `credenciales`, JSON con
    `usuario` = client_id y `clave` = client_secret. Leerlas con `nucleo.credenciales.cargar(...)`.
  - **Link de autorización** (lo toca el cliente):
    - Mercado Libre: `https://auth.mercadolibre.com.ar/authorization?response_type=code&client_id=<ID>&redirect_uri=<URL>&state=<STATE>`
    - Mercado Pago: `https://auth.mercadopago.com/authorization?client_id=<ID>&response_type=code&platform_id=mp&state=<STATE>&redirect_uri=<URL>`
    - `redirect_uri` va codificada (`urllib.parse.quote(..., safe="")`) y tiene que ser **idéntica** a la cargada
      en la aplicación. Por defecto: `https://thomasmanzo.github.io/Finnauto/autorizado/` (una página estática que
      le muestra el código al cliente; no tiene servidor). Que se pueda cambiar con `--redirect`.
    - `state`: `ml-` o `mp-` + 8 caracteres al azar (`secrets.token_hex(4)`). La página de vuelta usa el prefijo
      para saber de cuál es. No hace falta guardarlo.
    - Sin PKCE (las aplicaciones se crean sin PKCE).
  - **Lo que vuelve**: el cliente ve un código y se lo manda a Thomas por WhatsApp. Lo copia como `ML: TG-...` o
    `MP: TG-...` (con la marca adelante). **El código vence a los 10 minutos** y se usa una sola vez.
  - **Canje del código** (`grant_type=authorization_code`, con `client_id`, `client_secret`, `code`, `redirect_uri`):
    - Mercado Libre: `POST https://api.mercadolibre.com/oauth/token`, parámetros **en el cuerpo**,
      `content-type: application/x-www-form-urlencoded`, `accept: application/json`.
    - Mercado Pago: `POST https://api.mercadopago.com/oauth/token`, cuerpo **JSON**. (No pude confirmar en la
      referencia si acepta también form; dejar el formato de cada fuente en una constante fácil de cambiar.)
    - Respuesta (las dos): `access_token`, `token_type`, `expires_in` (segundos), `scope`, `user_id`, `refresh_token`.
  - **Renovación** (`grant_type=refresh_token`, con `client_id`, `client_secret`, `refresh_token`), mismo endpoint:
    - Mercado Libre: el access token dura **6 horas**. El refresh token **se usa una sola vez**: cada renovación
      devuelve uno nuevo y el viejo queda inválido. Solo vale el último. Vence a los 6 meses sin uso.
    - Mercado Pago: el access token dura **180 días** y la renovación también devuelve un refresh token nuevo
      (hay que guardarlo cada vez).
    - Recomendación oficial: renovar solo cuando el token está por vencer.
  - Errores: `invalid_grant` = el código o el refresh token venció, ya se usó o el cliente revocó el permiso →
    **hay que volver a autorizar** (mandar el link de nuevo). `invalid_operator_user_id` = el cliente entró con la
    cuenta de un colaborador, no la principal.
- **Por qué importa el orden al renovar**: como el refresh token viejo deja de servir apenas se usa, el nuevo se
  tiene que guardar en el llavero **antes** de hacer cualquier otra cosa. Si se pierde, hay que pedirle al cliente
  que autorice de nuevo. Y dos programas renovando a la vez se pisarían: hace falta un candado.

## Archivos permitidos
- `ingestas/meli_oauth.py` (nuevo).
- `tests/test_meli_oauth.py` (nuevo).
- Esta consigna (sección "Qué hice").

## Resultado esperado

### `ingestas/meli_oauth.py`
Módulo con comentarios en criollo arriba (qué es, cómo se usa, las reglas de arriba resumidas). Solo biblioteca
estándar más `keyring` (ya está en `requirements.txt`).

Fuentes: `"mercadolibre"` y `"mercadopago"`. Todo lo que cambia entre las dos (URL del link, URL del token,
formato del cuerpo, si lleva `platform_id`) en un diccionario al principio.

Funciones:
- `link_autorizacion(cliente, fuente, redirect=REDIRECT_POR_DEFECTO)` → el link listo para mandar (lee el
  client_id del llavero).
- `limpiar_codigo(texto)` → saca espacios, saltos de línea y el prefijo `ML:` / `MP:` (con o sin espacio, mayúscula
  o minúscula). Si el prefijo no corresponde a la fuente (por ejemplo `MP:` al canjear Mercado Libre), error claro.
- `canjear_codigo(cliente, fuente, codigo, redirect=REDIRECT_POR_DEFECTO)` → canjea y guarda los tokens en el
  llavero. Devuelve un resumen **sin tokens** (`user_id`, `scope`, cuándo vence).
- `access_token(cliente, fuente)` → devuelve un access token vigente. Si vence en menos de 10 minutos (o ya
  venció), renueva primero. Es la función que van a usar las bajadas.
- `estado(cliente, fuente)` → dict sin secretos: si hay token, `user_id`, `scope`, vence (fecha y hora de Buenos
  Aires), si el `scope` incluye `offline_access`.

Guardado de los tokens:
- Llavero, servicio `finauto:<cliente>:<fuente>-token`, cuenta `token`, un JSON con `access_token`,
  `refresh_token`, `vence` (epoch, calculado con `expires_in` menos 60 s de margen), `user_id`, `scope`,
  `obtenido` (epoch). Nunca en archivos ni en el log.
- Al renovar: pedir el token nuevo → **guardarlo en el llavero** → recién ahí devolverlo.
- Candado para no renovar dos veces a la vez: archivo `clientes/<cliente>/.run/<fuente>/token.lock` (la carpeta
  `.run` ya está en `.gitignore`), creado con `os.open(..., O_CREAT | O_EXCL)`. Si existe y tiene más de 2 minutos,
  se considera abandonado y se borra. Si está tomado, esperar hasta 30 s y volver a leer el llavero (puede que el
  otro ya haya renovado). Funciona igual en Mac y en Windows.

Errores (una clase propia, por ejemplo `ErrorAutorizacion`, con un `motivo` en criollo que las bajadas van a
copiar a `control.json`):
- falta el client_id/secret en el llavero → "faltan las credenciales de la aplicación: correr setup_credenciales.py";
- no hay token → "todavía no autorizó: mandar el link";
- `invalid_grant` → "el permiso venció o lo revocaron: hay que mandar el link de nuevo";
- `invalid_operator_user_id` → "autorizó con la cuenta de un colaborador: tiene que entrar con la cuenta principal";
- cualquier otro HTTP → código y `error`/`message` de la respuesta, **sin** repetir el cuerpo del pedido (lleva el
  secret).
- Nunca imprimir ni loguear `client_secret`, `access_token`, `refresh_token` ni el código.

### Uso por consola
```
python -m ingestas.meli_oauth --cliente <c> --fuente mercadolibre link      # imprime el link
python -m ingestas.meli_oauth --cliente <c> --fuente mercadolibre canjear   # pide el código y lo canjea
python -m ingestas.meli_oauth --cliente <c> --fuente mercadolibre estado    # muestra si hay permiso y hasta cuándo
python -m ingestas.meli_oauth --cliente <c> --fuente mercadolibre probar    # renueva si hace falta y consulta /users/me
```
- `canjear` lee el código con `input()` (no como argumento: así no queda en el historial de la terminal) y acepta
  que llegue por la entrada estándar (`echo "ML: TG-..." | python -m ...`). Antes de pedirlo, recuerda en una
  línea que vence a los 10 minutos. Al terminar: "Listo: autorizado el usuario <user_id>. Vence <fecha>."
- `probar`: Mercado Libre `GET https://api.mercadolibre.com/users/me`; Mercado Pago
  `GET https://api.mercadopago.com/users/me`; los dos con `Authorization: Bearer <token>`. Imprime solo `id` y
  `nickname`.
- Salida en UTF-8 como en `tango_live.py`.

### `tests/test_meli_oauth.py`
Se corre con `python tests/test_meli_oauth.py`, sin pytest. Con un llavero falso en memoria y un HTTP falso (reemplazar la función que hace los pedidos; nada de red):
- el link de cada fuente tiene los parámetros de arriba, con la `redirect_uri` codificada y el `state` con el
  prefijo correcto;
- `limpiar_codigo` con `ML: TG-abc`, `ml:TG-abc`, `  TG-abc \n` y el error con el prefijo cambiado;
- el canje manda el cuerpo en el formato de cada fuente y guarda los tokens;
- `access_token` no renueva si falta mucho y sí si faltan menos de 10 minutos; después de renovar, el llavero
  tiene el refresh token **nuevo**;
- `invalid_grant` y `invalid_operator_user_id` dan el motivo en criollo;
- ninguna salida por consola contiene el secret, los tokens ni el código (capturar stdout/stderr);
- el candado: si hay un `token.lock` viejo (más de 2 minutos), se borra y sigue.

## Comprobaciones
- `python tests/test_meli_oauth.py` pasa. Se corre sin instalar nada, como los otros de `tests/` (mirar
  `tests/test_motor.py`): pytest no está instalado.
- `python tests/test_motor.py`, `python tests/test_lector.py` y `python tests/test_bot_generico.py` siguen
  pasando igual que en `main` (si alguno ya fallaba antes, anotarlo).
- `python -m ingestas.meli_oauth --help` muestra los cuatro comandos.
- `git grep -nE "TG-[0-9a-f]{6,}|APP_USR-[0-9]"` no encuentra tokens con pinta de reales.
- No se puede probar contra Mercado Libre ni Mercado Pago de verdad (hace falta la autorización del cliente):
  eso lo hace Claude en la Mac después del merge.

## Qué hice

- Creé `ingestas/meli_oauth.py`: links por fuente, limpieza y comprobación del prefijo,
  canje, renovación con margen, estado sin tokens y los cuatro comandos de consola.
  Las credenciales se leen con `nucleo.credenciales.cargar`; los tokens se guardan
  únicamente en el llavero. No se instalaron dependencias.
- El canje y la renovación comparten candado por cliente/fuente, recuperan candados
  de más de dos minutos y vuelven a leer el permiso después de esperar. El refresh
  nuevo se guarda antes de devolver el acceso. Los pedidos tienen timeout de 20 s,
  sin reintentos automáticos ni redirecciones que puedan reenviar secretos.
- `limpiar_codigo(texto, fuente=None)` conserva el uso con un argumento y permite
  validar el prefijo cuando se llama desde el canje. `--redirect` se admite antes
  o después del subcomando. Fechas con UTC-3, sin necesitar tzdata en Windows.
- Creé `tests/test_meli_oauth.py`: 9 pruebas con HTTP y llavero falsos, datos inventados
  y carpetas temporales. Cubren ambos formatos, renovación, rotación del refresh,
  errores, salidas sin secretos, fallo al guardar, candado viejo, espera, timeout y
  dos bajadas concurrentes que hacen una sola renovación. Pasan con Python 3 del
  sistema y con el entorno virtual existente del repo.
- Comprobaciones con `/Users/thomasmanzo/Documents/Finnauto/.venv/bin/python`:
  `test_lector.py` pasa; `test_motor.py` falla en «un punto por dia con movimiento» y
  «una transferencia entre empresas del grupo no entra al grafico». Reproduje las
  mismas dos fallas en una copia limpia de `main` (22f98f1).
  `test_bot_generico.py` no logra iniciar Chromium: `bootstrap_check_in ... Permission
  denied (1100)`; reproduje el mismo bloqueo en esa copia de `main`.
- El comando `python` no está en PATH; usé `python3` y el intérprete del entorno
  virtual. Con Python del sistema faltan openpyxl y Playwright; no instalé nada.
- `python3 -m ingestas.meli_oauth --help` muestra los cuatro comandos.
  `git diff --check` pasa. La búsqueda solicitada con `git grep` no encontró tokens
  con pinta de reales; también revisé los archivos nuevos con la misma expresión.
- No hice pedidos reales ni accedí a datos privados. Queda pendiente la prueba con
  autorización real en la Mac después del merge, tal como indica la consigna.

- No pude commitear: `git add` y `git commit` no pueden crear
  `/Users/thomasmanzo/Documents/Finnauto/.git/worktrees/tarea-70/index.lock`
  (`Operation not permitted`). Dejé los tres archivos sin commitear para revisión.

## Revisión
Claude, 30/10/2026:
- Leí `ingestas/meli_oauth.py` entero contra la consigna: links con los parámetros de cada documentación y la
  `redirect_uri` codificada; canje en form (ML) y JSON (MP); el refresh nuevo se guarda en el llavero antes de
  devolver el token; candado con espera, recuperación del abandonado y relectura; errores en criollo sin secretos;
  sin redirecciones que reenvíen claves. Bien.
- Corrí `python tests/test_meli_oauth.py` (9 pruebas, OK), `link` sin credenciales (motivo claro, sale con 1) y
  `estado` sin token (JSON sin secretos). No dejó carpetas de prueba en `clientes/`.
- Las fallas de `test_motor.py` y `test_bot_generico.py` ya estaban en `main`: no son de esta tarea.
- Falta (después del merge, en la Mac): `link` y `estado` con las credenciales reales; `canjear` y `probar` cuando
  autorice el cliente. Si el canje de MP rechaza el JSON, cambiar `formato` a `"form"` en `FUENTES`.
- Commit de Claude por Codex (el sandbox no le dejó crear el `index.lock`).
