# Cómo trabajamos con tus datos

> Una carilla. Está escrita para mandarla **antes** de que la pidan.
>
> El premortem del 06/09/2026 marcó esto como uno de los fallos más probables:
> *"lo que un dueño pide antes de dar acceso no es cifrado, es un contrato: qué
> datos tocás, dónde quedan, quién responde si un consejo sale mal, y qué pasa
> cuando termina la relación."*
>
> El punto no es el texto: es **tenerlo ya escrito**. Contestar "te la mando" en
> una reunión cuesta tres semanas de silencio.

---

## En dos fases, y la primera no toca ningún banco

**Fase 1 — solo una planilla exportada.**
Vos me pasás una copia de tu planilla de flujo de fondos, exportada como archivo.
Nada más. Con eso ya puedo mostrarte tu posición, tu deuda por proveedor, tu día
crítico y los errores que encuentre en tus propios números.

**No hace falta darme acceso a nada** para ver si esto te sirve.

**Fase 2 — automatizar la carga.**
Recién si la fase 1 te convenció, se automatiza la descarga de los extractos del
banco para que el tablero se actualice solo. Eso sí requiere credenciales, y no
se hace sin el punto siguiente resuelto.

---

## Qué toco, exactamente

| | |
|---|---|
| **Fase 1** | Tu planilla de flujo de fondos. Solo lectura. |
| **Fase 2** | Los extractos de tus cuentas. Solo lectura: **no muevo un peso, no cargo un pago, no firmo nada.** |

Lo que **nunca** toco: tu facturación, tus clientes, tus empleados, tu
contabilidad. El sistema lee flujo de fondos y nada más.

## Las credenciales

Si se llega a la fase 2, **las cargás vos**, en tu equipo, y quedan cifradas con
el mecanismo del propio Windows (DPAPI). **Yo no las veo ni las puedo ver**: no
viajan, no se guardan en ningún servidor y no salen de tu máquina.

Si en algún momento querés cortar, cambiás la clave del banco y se terminó. No
hace falta pedirme nada.

## Dónde quedan tus datos

En tu Drive y en tu equipo. El único archivo que se genera es un JSON con tus
propios números, que queda en **tu** Drive.

Cuando trabajo con tus datos, tengo una copia local mientras dura el trabajo.
**Al terminar la relación se borra**, y te lo confirmo por escrito.

## Qué NO hago, y conviene decirlo antes

- **No soy tu contador ni tu asesor impositivo.** Esto es flujo de fondos, no
  balance ni impuestos.
- **No decido por vos.** El sistema dice "con esta caja cubrís lo vencido y te
  sobra X". Pagar o no pagar lo decidís vos.
- **No garantizo una proyección.** Una proyección es una estimación sobre el
  comportamiento pasado. Cuando le erra, te muestro **por cuánto le erró** — esa
  es justamente la parte que se mide.

## Quién responde si algo sale mal

Si un número está mal por un error del sistema, lo arreglo y te muestro qué pasó.
Por eso el tablero trae una sección de **"lo que no sabe"** y otra que contrasta
sus números **contra los tuyos**: no para quedar bien, sino para que una
diferencia aparezca en la pantalla y no en una decisión.

Las decisiones financieras siguen siendo tuyas.

## Confidencialidad

Nada de lo que vea de tu empresa se comparte, se muestra a terceros ni se usa
como ejemplo con otro cliente **sin tu autorización escrita**. Si querés que
firmemos un acuerdo de confidencialidad antes de arrancar, lo firmo.

## Cuando termina

Te llevás todo: la planilla es tuya, el JSON es tuyo, el tablero generado es
tuyo. Borro mi copia local y te lo confirmo.

---

*Si algo de acá no te cierra, decímelo antes de arrancar y lo cambiamos.*
