# Estado del proyecto — finauto

> Documento vivo. Se actualiza cada tanto para tener el orden mental: dónde
> estamos, qué falta, qué quedó pendiente y qué ideas hay dando vueltas.

**Última actualización:** 2026-09-12
**Repo:** github.com/ThomasManzo/Finnauto — *se queda con doble N (decidido)*
**Cliente #1:** **NAVAR S.A.** (yerbatera, Corrientes) — **cliente real desde el 12/09/2026**
**MAGA+ / Speedmed:** prospecto, ya no empleador. El caso con el que se construyó todo.

> **12/09/2026 — llegó el primer cliente, y no es una farmacia.** NAVAR S.A. es
> una yerbatera en Corrientes. Llegó por una recruiter a la que Thomas le había
> mandado el CV; lo contrataron para *ordenar toda la parte financiera*. Es
> asesoría + finauto, no el piloto de 6 semanas del plan comercial.
>
> Lo que cambia:
> - **El ICP del plan (farmacias, AMBA) quedó atrás en la práctica.** El patrón
>   general de `NEGOCIO.md` §9 (empresa que se financia con proveedores) sí aplica.
> - **La fuente de datos es Tango + un cashflow semanal en Excel**, no Google
>   Sheets. El `Exportador.gs` no aplica a este cliente; el `lector/` sí (para
>   los exports de Tango) y hace falta un lector nuevo para el cashflow semanal.
> - **Los bots no se tocan hasta la fase 2.** Cinco bancos (Nación, Corrientes,
>   Macro, BBVA, Galicia), todos en `activo=false`.
>
> Todo lo del cliente vive en `clientes/navar/` (ver su `LEEME.md`). El
> diagnóstico de su planilla, con montos, está en `clientes/navar/privado/`
> (no sube a git).

> **06/09/2026 — cambió el encuadre.** Thomas ya no trabaja en MAGA+. Su
> posición: *"no voy a trabajar sobre el cash original de MAGA y Speedmed sin
> que antes me pague"*.
>
> Consecuencias directas sobre el plan:
>
> - **No hay cash de producción.** La copia ES el entorno. El paso "pasar el
>   export a producción" queda sin sentido hasta que haya contrato.
> - **Los bots están frenados por partida doble**: contraseñas cambiadas y sin
>   acceso. Ya estaban parados hasta el primer cliente; ahora no es una
>   decisión, es un hecho.
> - **El trigger del clasificador tampoco se instala**: no hay operación diaria
>   que automatizar.
> - **El dato es una foto del 05/09/2026 y no se puede refrescar.** Alcanza para
>   construir y demostrar; no alcanza para operar.
>
> **Lo único que mueve la aguja ahora es lo que sirva para vender.** El motor ya
> está; lo que no existe es con qué mostrarlo.
>
> *(No hay riesgo de perder el dato: las planillas son de la cuenta personal de
> Thomas, que es dueña del cash y del clasificador. Puede copiarlas cuando
> quiera.)*

---

## 0. La cadena (el orden de trabajo)

Thomas lo definió así, y es el orden en que se construye:

```
   BOTS          →      INFO        →   MUESTRA DE INFO   →   DASHBOARD
(bajan datos)      (se transcriben      (contrato JSON)       (visual)
                    donde corresponde)
```

Con ramificaciones en el medio, que son las que hacen al producto:
- el dash no solo **muestra**, también **aconseja**;
- los bots no solo **bajan**, también **dan por pagadas** las cobranzas.

**Regla de orden: primero se terminan todos los bots.** Conectar el dashboard a
un contrato que se genera a mano es una demo, no un producto.

---

## 0.a El modelo de negocio (define las prioridades)

Thomas lo dejó explícito:

> "Mi idea NO es 'te vendo todo, 1 o 2 días y chau'. Es asesorar a las empresas,
> no venderles un software y olvidarme al segundo día."

**No es un detalle comercial: cambia qué hay que construir.**

| Si fuera venta de software | Como es asesoría |
|---|---|
| El cliente lo usa solo | **Vos** corrés las herramientas |
| Onboarding automático | Onboarding = **una reunión** que las herramientas preparan |
| Dashboards para el cliente | Un **documento** por visita |
| El éxito es que no te necesite | El éxito es que la próxima visita valga más que la anterior |

Consecuencias sobre el backlog:

- **La memoria sube a lo más importante.** Es lo que sostiene una cuenta
  recurrente: *"el mes pasado te dije que el 25 quedabas corto"*. Sin registro,
  cada visita arranca de cero.
- **El entregable es un documento, no una terminal.** Hoy todo imprime en
  pantalla y no queda nada que el cliente pueda guardar o mostrarle al contador.
- **El dashboard baja de prioridad.** Sigue teniendo sentido como algo que
  Thomas muestra en la reunión, no como algo que el cliente abre solo.
- **`respuestas_del_cliente.json` no es configuración: es el legajo.** Lo que
  cada cliente contestó, acumulado, es el activo que no se copia con software.

---

## 1. Dónde estamos

### Capa 1 — Bots

> **Bloqueado por acceso:** cambiaron las claves de todos los bancos. No se puede
> probar nada contra un home banking real hasta que MAGA vuelva a dar acceso.
> Por eso el trabajo se corrió a **dejar todo armado y probado sin banco**.

| Pieza | Estado | Detalle |
|---|---|---|
| **Bot genérico** | ✅ **Probado de punta a punta** | Un solo motor para casi cualquier banco, manejado por ficha. |
| Banco de prueba | ✅ | Home banking falso local que reproduce el recorrido real. |
| Validador de fichas | ✅ | Revisa una ficha sin tocar el banco. |
| Ficha `prueba` | ✅ Completa | Ejemplo lleno de cómo se completa una ficha. |
| Ficha `comafi` | 🟡 Armada, vacía | Espera la pasada de DOM. |
| Ficha `santander` | 🟡 Armada, vacía | Ídem. |
| Bot Galicia (producción) | ✅ Andando | Corre solo a las 8:00. Intacto. |
| Bot Galicia (finauto) | 🟡 Sin probar | Adaptador propio (calendario react-datepicker). |
| Bot cheques emitidos | ⬜ No existe | El parser sí; falta que el bot lo baje. |
| Bot cobranzas (RAL) | ⬜ No existe | Hoy BUSCARV manual los lunes. |

### Capa 2 — Los datos

| Pieza | Estado |
|---|---|
| Exportador (Apps Script) v1.4 | ✅ |
| Contrato JSON v1.2 | ✅ |
| Catálogo por cliente | ✅ |
| Auditoría de calidad (10 chequeos) | ✅ |
| Parser de cheques del banco | ✅ Probado con datos reales |

### Capa 3 — Herramientas

| Pieza | Estado |
|---|---|
| `simulador/semana.py` — escenario conservador/optimista | ✅ |
| `simulador/timeline.py` — día por día | ✅ |
| `simulador/consejo.py` — qué patear, con pagos parciales | ✅ |
| `simulador/ajustes.py` — **cuántos días podés mover ESE pago** | ✅ nuevo |
| `memoria/registro.py` — **qué se proyectó vs qué pasó** | ✅ nuevo |
| Dashboard "Caja al Día" | 🟡 Mockup, sin conectar |
| Simulador web | 🟡 Mockup, sin conectar |

**63 tests del motor** + **20 del bot genérico** (contra el banco de prueba).

---

## 2. Los tres ejes del modelo

Empezó con uno solo y ya son tres. Confundirlos fue fuente de errores reales:

| Eje | Qué dice | Dónde vive |
|---|---|---|
| **Fecha** (`dias_tolerancia`) | Cuántos días se puede correr | catálogo = *default* |
| **Monto** (`monto_variable`) | Si el importe es cierto o estimado | catálogo |
| **Ajuste manual** | Lo que sabés vos **esta semana** | `--mover`, fuera del catálogo |

El caso testigo: **Honorarios DJ** = 10% del resultado del mes anterior. Fecha
fija, monto estimado. Yo había asumido que "variable" quería decir "pateable" —
estaba mal, y el catálogo ahora lo dice explícito para que nadie lo repita.

Y el ajuste manual: el catálogo no puede saber que el martes hablaste con la
droguería y te dieron diez días más. Por eso los ajustes son **explícitos**
(hay que pedirlos), **temporales** (no ensucian el catálogo) y **visibles** (el
escenario siempre imprime qué está asumiendo).

---

## 2.b El bot genérico: un banco = una ficha

Thomas describió el recorrido que comparten casi todos los home banking:

> cuenta principal → apretás en saldo → salen los movimientos → filtro de fecha
> → aplicás → botón de descarga → listo

Si el recorrido es siempre el mismo y solo cambian los nombres de los botones,
un banco nuevo **no es un programa nuevo: es una ficha**.

```
bots/<banco>/selectores.json    <- lo único que se escribe por banco
```

Es la misma decisión que ya tomamos con los clientes: **lo que varía va en datos,
no en código**. Sumar Santander pasa de ~600 líneas de Python a llenar un archivo.

Cada paso tiene una **lista de candidatos** que se prueban en orden. No es
comodidad: los bancos cambian el frente cada tanto, y tener 2 o 3 formas de
encontrar el mismo botón es lo que evita que el bot se caiga un martes cualquiera.

**Dos confirmaciones obligatorias**, porque son los dos errores silenciosos que
más caro salen:
- `login.confirmacion` — si el login falló, el bot sigue clickeando sobre la
  pantalla de login y el error aparece tres pasos después diciendo cualquier cosa.
- `fechas.confirmacion` — si el filtro no se aplicó, el bot descarga el período
  por default, la descarga "funciona", y nadie se entera hasta que faltan
  movimientos en la planilla.

**Cuándo NO usarlo:** si un banco hace algo que no entra en el recorrido (un
calendario tipo el de Galicia, un iframe raro, un segundo factor en cada paso),
sigue existiendo la opción de un adaptador a mano. El genérico es el default,
no una obligación.

---

## 2.c NAVAR: qué se hizo y qué sigue (12/09/2026)

| Paso | Estado |
|---|---|
| Descubrimiento (cash semanal, Tango con 2 empresas A/AA, 5 bancos, situación 2 en dos) | ✅ |
| Radiografía de la planilla con `lector/planilla.py` | ✅ La ve, no la entiende: es un cashflow (semanas en columnas), no una tabla de movimientos |
| Diagnóstico a mano de la planilla | ✅ **9 errores de fórmula** verificados y la proyección de ingresos con **±48% de error** medido con sus propias 6 pestañas |
| `clientes/navar/perfil.json` + `catalogo.json` borrador | ✅ 11 tipos, 2 unidades, 5 bancos, 10 preguntas pendientes |
| Cash nuevo: listas + consolidado calculado, en Google Sheets ("NAVAR - Cash Flow") | ✅ Diseño de Cowork, corregido por `clientes/navar/arreglar_cash_v2.py` (semanas lunes-domingo, ejemplos, proyectados a las listas, stocks de deuda). Recalculado y verificado al peso |
| `lector/cash_limpio.py`: la Sheet → contrato v1.2 | ✅ Tercera puerta de entrada al motor (junto al Exportador y a `lector/extraer.py`) |
| Tablero con los números de NAVAR | ✅ Con vocabulario por cliente (`catalogo.vocabulario`) y lo vencido entrando el día 1 |
| PDF de propuesta para la dueña | ✅ `clientes/navar/propuesta.py`. Thomas valida los números antes de mandarlo |
| Presentación del proyecto, exports de Tango, reunión con quien carga | ⬜ Desde el 14/09 |
| Fase 2 (Tango automático) y 3 (bancos en una máquina del cliente) | ⬜ Recién si la fase 1 convence |

**Bugs del motor que destapó NAVAR (arreglados el 12/09):** `finauto.py` imprimía
la tupla de `memoria.guardar()`; `gastos_del_periodo` cargaba los proveedores de
"maga" fijo; el gráfico de la curva explotaba con una curva plana (`Math.min.apply`
con un tercer argumento que se ignora); la proyección no restaba lo ya vencido
(la caja parecía $600M mejor de lo que es); el tablero hablaba de droguerías y
PAMI a cualquier cliente.

**Bug que destapó el cliente nuevo:** `orquestador/correr.py` sin `--cliente`
corría todos los clientes, y uno sin bancos activos cortaba la corrida entera
(`SystemExit` no cae en `except Exception`). Arreglado: se saltea y sigue.

## 3. Qué falta

**Bloqueado hasta que haya acceso a los bancos:**
- Completar las fichas de Comafi y Santander (`scripts/explorar_dom.py`).
- Probar el bot Galicia refactorizado contra el banco.
- Bot que baje el listado de cheques emitidos.

*Todo eso es ahora una tarde de trabajo, no una semana: el motor ya está probado
y lo único que falta es llenar selectores.*

**Se puede hacer sin bancos:**
1. Conectar el dashboard y el simulador web al contrato.
2. Que el dash aconseje, no solo muestre.
3. Cruce de cobranzas (RAL) — el BUSCARV de los lunes.
4. Cartera de cheques.

**Para escalar a otros clientes:**
5. **Reconocedor de planillas** — el cuello de botella del negocio.

**Sin tocar todavía:** análisis EERR.

---

## 4. Pendientes y decisiones abiertas

| Tema | Estado |
|---|---|
| Honorarios DJ | ✅ **Resuelto.** Thomas confirmó que DJ = D.Jaimovich. Los tres conceptos son monto variable ($202.737.150). Al aplicarlo apareció que `DJ` también es *Declaración Jurada* en los impuestos: de ahí salió `solo_tipos` en las excepciones. |
| Cargas sociales cargadas como `SUELDO` | El catálogo tiene `VEP_AFIP`, la planilla usa `SUELDO`. Ambos rígidos, así que no cambia ningún número. Anotado. |
| PAMI | Queda **manual**. No modelar todavía. |
| Venta diaria automática | Requiere histórico de ventas por farmacia. |
| Contrato de venta a MAGA+ | Pendiente por escrito. |

### ❌ Descartado

- **Adelantar cobros como palanca** — *"es muy difícil en este rubro"*.

*(La "calibración automática" ya no está descartada: Thomas la reformuló como
**memoria interna** — registrar en vez de inferir — y así construida sí sirve.
Ver sección 5.)*

---

## 5. La memoria interna

Idea de Thomas: el modelo tiene que **acordarse** de lo que proyectó.

```bash
python memoria/registro.py guardar   --contrato c.json   # foto de lo que creo que va a pasar
python memoria/registro.py conciliar --contrato c_nuevo.json  # contra lo que paso
python memoria/registro.py resumen                       # como se porta cada tipo
```

Distingue **CUMPLIO / CAMBIO_FECHA / CAMBIO_MONTO / CAMBIO_AMBOS / NO_APARECIO**,
y aparte las **sorpresas** (lo que pasó sin que nadie lo proyectara — suele ser
la razón real por la que un mes no cierra).

Es a propósito un módulo **tonto**: registra y compara, no infiere nada. Con una
sola proyección conciliada, cualquier "ajuste automático" sería inventar un
número con una muestra de uno — y el propio resumen lo dice cuando hay pocas.

Primera foto ya guardada: `clientes/maga/memoria/proyeccion_2026-09-04.json`
(226 movimientos hasta el 04/10).

---

## 6. Decisiones ya tomadas (no re-litigar)

- **Dos repos:** `MAGA` (productivo actual) y `Finnauto` (el producto).
- **La lógica del cliente vive en su catálogo, nunca en el código.**
- **Las herramientas leen el contrato, nunca una celda.**
- **El administrativo sigue en su Excel; el dueño ve el tablero.**
- **`dias_tolerancia` del catálogo es un DEFAULT, no una ley.**
- **Primero los bots, después el dashboard.**
- Multi-cliente diferido: la estructura lo soporta.

---

## 7. Números clave (MAGA+)

| | |
|---|---|
| Caja hoy (bancos + efectivo) | $1.183.497.652 |
| **Solo el 9% de los egresos es flexible** | $114M flexible vs $1.158M rígido |
| Deuda viva con droguerías | $2.690.750.655 |
| Día crítico detectado | 25/09/2026 — cae a $135M, bajo el mínimo de $200M |

> El **9%** es el dato más importante del proyecto: postergar pagos casi no
> mueve la aguja. Cualquier consejo tiene que partir de ahí.

---

## 8. Los 9 errores que encontramos (y que los tests ahora cuidan)

Ninguno lo encontró el sistema: los encontró Thomas mirando datos reales.

1. Transferencias y depósitos **internos** contados como gasto.
2. **NCR** sumando deuda en vez de restarla.
3. Filas de **saldo** sumadas 200 veces → $249 mil millones.
4. La deuda **intercompany** arrastrando el mismo saldo día a día.
5. "Fecha pasada" significa lo **opuesto** en cobranza (vencido) y en deuda (pagado).
6. Una **cuota de préstamo** cargada como retiro → el motor la proponía patear.
7. El tipo `PAGO` como **cajón de sastre** (~$458M).
8. **Cargador de catálogo duplicado** → proponía postergar impuestos y sueldos.
9. `TRANSFERENCIA A TERCEROS` ($155M) a veces servicio, a veces interno.

Y dos que aparecieron construyendo lo nuevo:

10. `conciliar()` no filtraba internos y `guardar()` sí: cada transferencia
    propia figuraba como "movimiento que nadie proyectó".
11. Matcheo por subcadena: `"D.J"` pegaba dentro de `"D.Jaimovich"` — y encima
    de forma inconsistente. De ahí salió `palabra_completa`.

---

## 9. Cómo correr todo

```bash
# Auditoría de calidad (SIEMPRE antes de confiar en el número)
python auditoria/revisar.py --contrato contrato.json

# Escenario / timeline / consejo
python simulador/semana.py   --contrato c.json --cheques ch.csv --dias 7
python simulador/timeline.py --contrato c.json --cheques ch.csv --dias 21 --minimo 200000000
python simulador/consejo.py  --contrato c.json --cheques ch.csv --minimo 200000000

# "¿y si a la financiera la estiro 20 días?"
python simulador/consejo.py --contrato c.json --minimo 200000000 --mover "FINANCIERA=20"

# "¿y si los honorarios DJ salen 20% más caros?"
python simulador/consejo.py --contrato c.json --minimo 200000000 --estres 20

# Memoria
python memoria/registro.py guardar --contrato c.json

# Bancos: validar una ficha sin tocar el banco
python bots/generico/validar.py --todos

# Relevar un banco nuevo (interactivo: entras y navegas vos)
python scripts/explorar_dom.py --banco comafi

# Tests
python tests/test_motor.py           # 63 del motor
python tests/test_bot_generico.py    # el bot, contra el banco de prueba
```

---

## 10. Ideas en el backlog

Ver `docs/IDEAS.md`. En orden de cuánto diferencian al producto:

1. **Reconocedor de planillas** (onboarding automático) ⭐
2. **Alertas** en vez de tablero — al dueño le llega el aviso, no abre nada
3. Que los bots marquen las cobranzas como pagadas solas
4. Roles: cada usuario su vista
