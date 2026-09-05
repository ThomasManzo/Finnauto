# Estado del proyecto — finauto

> Documento vivo. Se actualiza cada tanto para tener el orden mental: dónde
> estamos, qué falta, qué quedó pendiente y qué ideas hay dando vueltas.

**Última actualización:** 2026-09-04
**Repo:** github.com/ThomasManzo/Finnauto — *se queda con doble N (decidido)*
**Cliente #1:** MAGA+ / Speedmed

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

## 1. Dónde estamos

### Capa 1 — Bots (el eslabón que falta)

| Pieza | Estado | Detalle |
|---|---|---|
| Bot Galicia (producción) | ✅ Andando | Corre solo a las 8:00 (`BotGaliciaExtractos`). Intacto. |
| Bot Galicia (finauto) | 🟡 Sin probar | Portado a núcleo + adaptador. Compila, **nunca corrió contra el banco**. |
| Bot Comafi | 🟡 Andamiaje | Falta una pasada de DOM en vivo (`# >>> TODO COMAFI`). |
| Bot Santander | ⬜ Esqueleto | Solo el contrato de la clase. |
| Bot cheques emitidos | ⬜ No existe | El parser sí; falta que el bot lo **baje solo**. |
| Bot cobranzas (RAL) | ⬜ No existe | Hoy es un BUSCARV manual todos los lunes. |

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

**61 tests**, corren sin instalar nada: `python tests/test_motor.py`

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

## 3. Qué falta

**Ahora (la cadena, en orden):**
1. **Comafi** — necesita una pasada de DOM con el banco abierto.
2. **Galicia finauto** — probarlo de verdad contra el banco.
3. **Bot de cheques emitidos** — el bot ya entra al banco; es casi el mismo trabajo.
4. **Bot / cruce de cobranzas (RAL)** — y que marque las cobradas solas.
5. Santander (cuando haga falta).

**Después:**
6. Conectar el dashboard y el simulador web al contrato.
7. Que el dash aconseje, no solo muestre.

**Para escalar a otros clientes:**
8. **Reconocedor de planillas** — el cuello de botella del negocio.

**Sin tocar todavía:** cartera de cheques, análisis EERR.

---

## 4. Pendientes y decisiones abiertas

| Tema | Estado |
|---|---|
| **Honorarios DJ: ¿"DJ" son las iniciales de D.Jaimovich?** | ❓ **Pregunta abierta.** En la planilla conviven "honorarios DJ", "honorarios D.jaimovich" y "honorarios junio D.Jaimovich". Hoy solo se marca `DJ` como palabra suelta (criterio conservador: marca de menos, no de más). |
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

# Tests
python tests/test_motor.py
```

---

## 10. Ideas en el backlog

Ver `docs/IDEAS.md`. En orden de cuánto diferencian al producto:

1. **Reconocedor de planillas** (onboarding automático) ⭐
2. **Alertas** en vez de tablero — al dueño le llega el aviso, no abre nada
3. Que los bots marquen las cobranzas como pagadas solas
4. Roles: cada usuario su vista
