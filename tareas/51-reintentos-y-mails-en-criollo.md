# Tarea 51 — Reintentos todo el día y mails en criollo
Estado: lista para revisión
Rama: tarea/reintentos-y-mails

## Objetivo

Que cuando algo de la mañana falla (Tango, Galicia, la importación), **se arregle solo** si se puede,
y que los mails digan **en criollo** qué pasó, si se va a reintentar solo y qué hay que hacer si no.
La idea (pedido de Thomas): no tener que conectarse a la notebook cada vez que algo falla, salvo
cuando de verdad hace falta.

## Contexto

Leer antes: `tareas/LEEME.md`, `CLAUDE.md` (**repo público: nada de datos reales**), las tareas 26, 30,
33, 35, 39 y 48, `ingestas/tango_live.py` (`main`, `--si-falta`, el parte), `orquestador/correr.py`,
`nucleo/loop.py`, `nucleo/salidas.py` (`escribir_estado_drive`), `bots/galicia/navar.py`
(`hacer_login`), `clientes/navar/herramientas/instalar_tango.ps1`, `instalar_galicia.ps1` y
`aviso_diario.gs`.

Lo que existe hoy:
- **Tango**: baja a las 05:45 y reintenta con `--si-falta` a las 06:15, 06:45, 07:15, 09:00 y 12:00
  (tarea 35). `--si-falta` no hace nada si el parte de hoy ya está completo.
- **Galicia**: corre a las 05:45 y a las 05:48 (las dos bajan de nuevo). Si las dos fallan, el día
  queda sin Galicia. El login se intenta **una sola vez por corrida** para no bloquear el usuario.
  El resultado queda en `Bancos/galicia/_ESTADO_Galicia_DD-MM.txt` ("OK: no fallo ninguna empresa." o
  ">>> ATENCION ..." con el motivo; si falló el login, "LOGIN FALLIDO - <error técnico>").
- **Vigilante** (cada 15 min) y **la Sheet** (cada hora) ya reintentan solos.
- **El mail** sale una vez, cerca de las 07:30. Si después algo se arregla solo, nadie se entera; y
  los motivos van en idioma técnico ("getaddrinfo failed", "Timeout 30000ms exceeded").

Decisiones ya tomadas (Thomas, 06/10/2026):
- Reintentar **todo el día**, pero sin poner en riesgo el usuario del banco.
- El seguimiento va a los mismos destinatarios del mail de la mañana (propiedad `DESTINATARIOS`).

## Archivos permitidos

- `clientes/navar/herramientas/instalar_tango.ps1`, `clientes/navar/herramientas/instalar_galicia.ps1`
- `orquestador/correr.py` (opción `--si-falta`), `bots/galicia/navar.py` (marcar el intento de clave),
  `nucleo/salidas.py` solo si hace falta leer el estado del día
- `clientes/navar/herramientas/aviso_diario.gs`, `clientes/navar/herramientas/importar_cashflow.gs`
  (solo el menú)
- pruebas: `lector/pruebas/probar_aviso_bajadas.cjs`, `lector/pruebas/probar_aviso_seguimiento.cjs`
  (nueva), `bots/galicia/test_navar.py`, `orquestador/test_si_falta.py` (nueva)
- esta consigna

## Resultado esperado

1. **Tango reintenta hasta la noche**: horarios 05:45, 06:15, 06:45, 07:15 y cada hora de 08:00 a
   20:00, siempre con `--si-falta` salvo la primera. Nada más cambia en la bajada.
2. **Galicia con `--si-falta`** (`orquestador/correr.py`):
   - Si el estado de hoy de ese banco dice OK, termina sin abrir el navegador ("ya bajó hoy").
   - **Freno anti-bloqueo**: cada vez que el bot **envió la clave** y el banco no confirmó la entrada,
     se suma uno a un contador del día en `clientes/navar/.run/<banco>/clave_sin_confirmar_<fecha>.txt`.
     Con 2 en el día, `--si-falta` no vuelve a intentar y deja en el estado del día una línea clara:
     "no se reintenta para no bloquear el usuario: revisar la clave". Las fallas **antes** de enviar
     la clave (página que no carga, sin internet) no cuentan: reintentar ahí no arriesga nada.
   - Horarios: 05:45 (normal), 05:48, 06:30, 07:15, 09:00, 12:00 y 16:00 (todos con `--si-falta`).
3. **Mail de la mañana en criollo**: cada renglón que falla dice:
   - qué pasó, traducido: sin conexión con el servidor de Tango (¿está prendido?), Tango rechazó la
     clave, el servidor respondió con error, la página del banco no cargó, el banco no confirmó la
     entrada, la Sheet no pudo cargar, Drive no terminó de sincronizar... El texto técnico no va;
   - **qué pasa ahora**: "se reintenta solo hasta las 20:00" (Tango) / "hasta las 16:00" (Galicia), o
     "no se reintenta: revisar la clave" cuando actuó el freno;
   - si ya no quedan reintentos: "hay que revisar la notebook".
4. **Mail de seguimiento** (`avisoSeguimiento`, cerca de las 12:30 y de las 17:30):
   - Solo mira lo **automático** (Tango, Galicia, la importación de la Sheet, la notebook).
   - Se manda solo si **a la mañana faltaba algo automático** y cambió algo desde el último mail:
     "✅ Se arregló solo: …" / "❌ Sigue faltando: … · <qué hacer>". A las 12:30, si sigue faltando lo
     mismo, se manda igual una vez (para que alguien lo mire); a las 17:30, solo si cambió.
   - Si a la mañana estaba todo bien, no se manda nada.
   - Menú: "Ver el seguimiento (sin mandar)", "Instalar seguimiento (12:30 y 17:30)", "Quitar seguimiento".
     Instalar el aviso diario no borra el seguimiento ni al revés.

## Comprobaciones

- Pruebas Python (datos inventados): `--si-falta` con estado OK no abre el banco; con estado de
  falla sí; con 2 claves sin confirmar no reintenta y lo deja escrito; una falla antes de enviar la
  clave no suma al contador; el contador es por día.
- `.cjs`: el mail de la mañana traduce los errores típicos y dice hasta cuándo se reintenta; el
  seguimiento no se manda si a la mañana estaba todo bien, se manda con "se arregló solo" cuando
  cambió, se manda a las 12:30 si sigue igual y no a las 17:30 si sigue igual.
- Todas las pruebas que ya existen siguen pasando.
- No se puede probar acá: el Programador de tareas de Windows ni el banco. Se instala en la notebook
  con los dos `instalar_*.ps1` y se mira el log del día siguiente.

## Qué hice
**La escribió Claude.**
- `instalar_tango.ps1`: 05:45, 06:15, 06:45, 07:15 y cada hora de 08:00 a 20:00, todas con `--si-falta`
  (la de las 05:45 baja porque todavía no hay parte del día).
- `bots/galicia/navar.py`: si el clic en Ingresar no sale, el error es el de siempre; si salió y el banco
  no confirmó la entrada, el error empieza con `CLAVE ENVIADA SIN CONFIRMAR` (queda en el estado del día).
- `orquestador/correr.py`: `--si-falta` (`decidir_reintento`): estado de hoy OK → no abre el banco;
  2 claves sin confirmar en el día (contador en `.run/<banco>/clave_sin_confirmar_<fecha>.txt`) → no
  insiste y reescribe el estado del día, una sola vez, con "NO SE REINTENTA - … revisar la clave".
- `instalar_galicia.ps1`: 05:45, 05:48, 06:30, 07:15, 09:00, 12:00 y 16:00, todas con `--si-falta`. Antes
  la de las 05:48 bajaba de nuevo aunque la de las 05:45 hubiera andado; ahora no repite el login.
- `aviso_diario.gs`:
  - `_enCriolloAviso_` traduce los errores típicos (conexión, clave, HTTP, tiempo, Google saturado,
    verificación del importador); lo que no reconoce queda recortado.
  - `_quePasaAhoraAviso_` agrega "se reintenta solo hasta las 20:00 / 16:00", "revisar la clave" o
    "ya no quedan reintentos hoy: hay que revisar la notebook".
  - El mail marca qué renglones son automáticos (`automaticos`).
  - `avisoDiario` guarda lo que faltaba (propiedades `aviso_manana_<fecha>`; borra las de días
    anteriores).
  - `avisoSeguimiento` / `seguimientoPrueba` / `instalarSeguimiento` / `quitarSeguimiento`, con
    `_seguimientoAviso_` puro.
- `importar_cashflow.gs`: tres renglones de menú.
- Fuera de la lista: `lector/pruebas/probar_importador_filtros.cjs` esperaba el texto viejo de la
  alerta ("Falló la importación de…"); ahora espera el nuevo, en criollo.

Pruebas:
- `orquestador/test_si_falta.py` (7, nuevas).
- `bots.galicia.test_navar` (2 nuevas).
- `probar_aviso_seguimiento.cjs` (nueva).
- `probar_aviso_bajadas.cjs` con los textos nuevos.
- En total 183 de Python y los 10 `.cjs`. `probar_volcado_fechas.cjs` falló una vez cerca de la
  medianoche y pasó en las 4 corridas siguientes; no lo toca esta tarea (posible prueba sensible a la
  hora).

Falta, en la notebook:
1. `actualizar.ps1`, `instalar_tango.ps1` e `instalar_galicia.ps1`.
2. Mirar el log del día siguiente.

Falta, en Apps Script:
1. Pegar `aviso_diario.gs` e `importar_cashflow.gs`.
2. Desde el menú, "Instalar seguimiento".

## Revisión
