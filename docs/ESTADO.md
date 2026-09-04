# Estado del proyecto — finauto

> Documento vivo. Se actualiza cada tanto para tener el orden mental: dónde
> estamos, qué falta, qué quedó pendiente y qué ideas hay dando vueltas.

**Última actualización:** 2026-09-04
**Repo:** github.com/ThomasManzo/Finnauto
**Cliente #1:** MAGA+ / Speedmed (ya manifestaron interés en comprar el software)

---

## 1. Dónde estamos

El proyecto tiene **3 capas**. Este es el estado real de cada pieza:

### Capa 1 — Bots (automatización / entrada de datos)

| Pieza | Estado | Detalle |
|---|---|---|
| Bot Galicia (producción) | ✅ Andando | El bot viejo corre solo a las 8:00 (tarea `BotGaliciaExtractos`). **Intacto, no lo tocamos.** |
| Bot Galicia (finauto) | 🟡 Refactorizado, sin probar | Portado 1:1 a núcleo + adaptador. Compila e importa, pero **nunca corrió contra el banco**. |
| Bot Comafi | 🟡 Andamiaje | Estructura lista, faltan los selectores reales (`# >>> TODO COMAFI`). |
| Bot Santander | ⬜ Esqueleto | Solo el contrato de la clase. |
| Parser de cheques del banco | ✅ Probado con datos reales | 61 cheques leídos, 58 pendientes, 0 duplicados. Reemplaza el BUSCARV manual. |

### Capa 2 — Los datos (el verdadero activo)

| Pieza | Estado | Detalle |
|---|---|---|
| Exportador (Apps Script) | ✅ v1.4 | Lee MOVIMIENTOS, SALDOS, caja de hoy, ingresos previstos del cashflow, cobranza y deuda con droguerías. Busca por encabezados, no por filas fijas. |
| Contrato (JSON) | ✅ v1.2 | La fuente de verdad que consumen las herramientas. Las visuales **nunca** tocan una celda. |
| Catálogo por cliente | ✅ Completo | Tipos, tolerancias, divisible, internos, excepciones por concepto, orden de pateo, entidades propias, modelo de ingresos. **Todo lo de MAGA vive acá, nada en el código.** |
| Auditoría de calidad | ✅ 10 chequeos | Genérica: se apoya en el catálogo del cliente. |

### Capa 3 — Herramientas

| Pieza | Estado | Detalle |
|---|---|---|
| `simulador/semana.py` | ✅ Con datos reales | Escenario conservador vs optimista de N días. |
| `simulador/timeline.py` | ✅ Con datos reales | Día por día entre dos fechas, marca los días bajo el mínimo. |
| `simulador/consejo.py` | ✅ Con datos reales | Qué patear, en el orden de decisión de Thomas, con pagos parciales. |
| Dashboard "Caja al Día" | 🟡 Mockup | Diseñado (blanco/verde/naranja) pero **con datos de ejemplo, sin conectar**. |
| Simulador web | 🟡 Mockup | Ídem: anda, pero no lee el contrato. |

### Transversal

| | |
|---|---|
| Tests | ✅ 24, corren sin instalar nada (`python tests/test_motor.py`) |
| Documentación | ✅ README, CLAUDE.md, ARQUITECTURA, mapa de Capa 2, IDEAS, este archivo |

---

## 2. Qué falta

**Para cerrar el motor (lo más cerca):**
- Nada bloqueante. El motor está funcionando y auditado. Ver "descartado" abajo.

**Para que sea un producto usable:**
1. **Conectar las pantallas al motor** — hoy los mockups muestran datos inventados. Es el paso más visible y el que se le muestra a un cliente.
2. **Probar el bot nuevo contra el banco** — el refactor de Galicia nunca corrió de verdad.
3. **Que el bot baje el listado de cheques solo** — hoy se baja a mano cada semana. El bot ya entra al banco; es casi el mismo trabajo.

**Para escalar a otros clientes:**
4. **El reconocedor de planillas** (idea de Thomas) — que deduzca solo el modelo de datos de un Cash desconocido. Es el cuello de botella del negocio: sin esto, cada cliente nuevo son semanas de configuración.

**Piezas del sistema original todavía no tocadas:**
5. Cobranzas de droguerías (RAL) — el cruce manual de los lunes.
6. Cartera de cheques — hoy se carga a mano y son ingresos con fecha cierta.
7. Análisis EERR.

---

## 3. Pendientes y decisiones abiertas

| Tema | Estado |
|---|---|
| `HONORARIO` fijo vs variable | Pendiente. Hoy criterio conservador (tolerancia 0). En la planilla hay un solo valor. |
| PAMI | **Queda manual.** Thomas tiene dudas sobre el calendario real de quincenas cruzadas. No modelar todavía. |
| Venta diaria automática | Requiere el histórico de ventas por farmacia. Hoy manual. |
| Contrato de venta a MAGA+ | Pendiente de cerrar por escrito. |
| Repo `finauto` vs `Finnauto` | Quedó con doble N. Se puede renombrar en GitHub cuando quieras. |

### ❌ Descartado (para no volver a proponerlo)

- **Adelantar cobros como palanca** — Thomas: *"es muy difícil en este rubro"*. No se construye.
- **Calibración automática (proyectado vs real)** — Thomas: *"entender si algo se cumplió es más complicado"*. Queda como idea de largo plazo, no como próximo paso.

---

## 4. Decisiones ya tomadas (no re-litigar)

- **Dos repos separados:** `MAGA` (sistema productivo actual) y `Finnauto` (el producto).
- **La lógica del cliente vive en su catálogo, nunca en el código.** Otra empresa = otro catálogo.
- **Las herramientas visuales leen el contrato, nunca una celda de la planilla.**
- **El administrativo sigue en su Excel; el dueño ve el tablero.** Mismo dato abajo, distinta interfaz arriba.
- **Multi-cliente diferido:** la estructura lo soporta; la decisión "Google vs backend propio" se toma cuando haya volumen.

---

## 5. Números clave descubiertos (MAGA+)

| | |
|---|---|
| Caja hoy (bancos + efectivo) | $1.183.497.652 |
| **Solo el 9% de los egresos es flexible** | $114M flexible vs $1.158M rígido |
| Deuda viva con droguerías | $2.690.750.655 |
| Día crítico detectado | 25/09/2026 — cae a $135M, bajo el mínimo de $200M |

> El dato del **9%** es el más importante del proyecto: significa que postergar
> pagos casi no mueve la aguja. Cualquier consejo que dé el sistema tiene que
> partir de ahí.

---

## 6. Los 9 errores que encontramos (y que los tests ahora cuidan)

Cada uno hacía que el motor mintiera. Ninguno lo encontró el sistema: los
encontró Thomas mirando datos reales.

1. Transferencias y depósitos **internos** contados como gasto.
2. **NCR** sumando deuda en vez de restarla.
3. Filas de **saldo** ("Con pago a droguerías") sumadas 200 veces → $249 mil millones.
4. La deuda **intercompany** arrastrando el mismo saldo día a día.
5. "Fecha pasada" significa lo **opuesto** en cobranza (vencido) y en deuda (pagado).
6. Una **cuota de préstamo** cargada como retiro de socios → el motor la proponía patear.
7. El tipo `PAGO` como **cajón de sastre**: ~$458M de internos + impuestos + sueldos.
8. **Cargador de catálogo duplicado** → el consejo proponía postergar impuestos y sueldos.
9. `TRANSFERENCIA A TERCEROS` ($155M) cargado a veces como servicio, a veces como interno.

---

## 7. Cómo correr todo

```bash
# 1. Exportar el contrato desde el Cash (Apps Script -> exportarContratoEnLog)
# 2. Bajar el JSON de Drive

# Auditoría de calidad (SIEMPRE antes de confiar en el número)
python auditoria/revisar.py --contrato contrato.json

# Escenario de la semana
python simulador/semana.py --contrato contrato.json --cheques cheques.csv --dias 7

# Timeline día por día
python simulador/timeline.py --contrato contrato.json --cheques cheques.csv --dias 21 --minimo 200000000

# Qué patear si falta plata
python simulador/consejo.py --contrato contrato.json --cheques cheques.csv --minimo 200000000

# Tests
python tests/test_motor.py
```

---

## 8. Ideas en el backlog

Ver **`docs/IDEAS.md`** para el detalle. En orden de cuánto diferencian al producto:

1. **Reconocedor de planillas** (onboarding automático de clientes nuevos) ⭐
2. **Alertas** en vez de tablero — el dueño no abre nada, le llega el aviso
3. Que el bot baje el listado de cheques
4. Automatizar el cruce de cuentas a cobrar (RAL)
5. Roles: cada usuario su vista
