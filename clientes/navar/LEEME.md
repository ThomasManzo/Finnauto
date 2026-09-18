# NAVAR S.A. — la carpeta del cliente

Yerbatera en Corrientes. **Primer cliente real de finauto** (12/09/2026).
No es el piloto del plan comercial: es una asesoría para ordenar la parte
financiera, y finauto es la herramienta con la que se hace.

## Qué hay acá

| Archivo | Qué es | ¿Sube a git? |
|---|---|---|
| `perfil.json` | Lo operativo: bancos, de dónde sale cada dato, dónde caen los extractos. | Sí |
| `catalogo.json` | El vocabulario del cliente: tipos de pago, tolerancias, proveedores, ingresos. **Es un BORRADOR**: lo que está en `null` o en `_pendiente` se pregunta, no se adivina. | Sí |
| `documentos/` | El checklist de implementación y los arreglos del esqueleto. | Sí |
| `herramientas/` | Los scripts de este cliente (migración, arreglo del cash, PDFs). | Sí |
| `privado/` | Planillas, PDFs generados, capturas y el diagnóstico con montos reales. | **No** (está en `.gitignore`) |
| `memoria/` | Las fotos de cada proyección, para conciliar después. Se crea sola al correr `finauto.py`. | No |

## La Sheet (la fuente de verdad)

**"NAVAR - Cash Flow"** en el Drive de Thomas (id `1u9CfWz_MntC2xO_gcDGaohEVMZNUNbHv0WoFSqKK7e8`).
Hasta que se presente el proyecto queda ahí; después pasa a una cuenta de NAVAR.
Para leerla desde finauto se baja como Excel (por el conector de Drive o
Archivo → Descargar) a `privado/NAVAR - Cash Flow (export Sheets <fecha>).xlsx`.

## Cómo se corre todo (hoy)

```bash
source .venv/bin/activate
python lector/tango.py --carpeta "clientes/navar/privado/tango/2026-09-16" --cliente navar --hoy 2026-09-16 --sheet "clientes/navar/privado/NAVAR - Cash Flow (export Sheets 2026-09-12).xlsx"
python lector/extractos.py --carpeta clientes/navar/privado/bancos --cliente navar --hoy 2026-09-18 --sheet "clientes/navar/privado/NAVAR - Cash Flow (con Tango 2026-09-16).xlsx"
python lector/deuda_bancaria.py --archivo clientes/navar/privado/bancos/Bancos_Navar.xlsx --cliente navar --hoy 2026-09-18 --bancos clientes/navar/privado/bancos/para_pegar_bancos_2026-09-18.xlsx --sheet "clientes/navar/privado/NAVAR - Cash Flow (con bancos 2026-09-18).xlsx"
python lector/cash_limpio.py --archivo "clientes/navar/privado/NAVAR - Cash Flow (con deuda 2026-09-18).xlsx" --cliente navar --hoy 2026-09-18
python finauto.py --contrato clientes/navar/contrato_2026-09-18.json --cliente navar --salidas clientes/navar/privado/salidas
python clientes/navar/herramientas/propuesta.py        # el PDF para la dueña, con capturas del tablero
```

`--hoy 2026-08-31` porque los datos cargados son de ese lunes: con la fecha real
el tablero marcaría como vencidas cobranzas que son proyecciones de semanas
pasadas. Cuando carguen una semana nueva, se corre con la fecha de esa carga.

## El checklist vivo

https://claude.ai/artifact/K8SzFarJZTEhNw4rP1hX7q — tildes y minutos guardados y compartidos. La versión en texto está en `documentos/CHECKLIST_IMPLEMENTACION.md`.

## Contrato (15/09/2026)

**NAVAR dio el OK el 15/09/2026.** Implementación $1.400.000 (pesos) + abono
USD 400/mes desde el mes 2, revisable a los 3 meses contra el acierto medido.
La presentación (PDF de propuesta + vista rápida del tablero + la Sheet) fue
lo que cerró. Primer peso cobrado de finauto.

## Dónde estamos (18/09/2026)

- ✅ **Primera conexión a la notebook de NAVAR hecha (16/09 a la noche).** Tango es **Delta 5 (25.01.000.4297)**, corre en el navegador contra `servidor:17000` (hay un servidor aparte en la red; la notebook es un cliente). Dos empresas: **NAVAR SA** (id 13, la asumimos "A") y **NAVAR SA Otros** ("AA"). Se entró con la cuenta nexo de Priscilla (autorizado por WhatsApp); el usuario propio de consulta sigue pendiente.
- ✅ **Exports de Tango Live bajados** (15 archivos + SQL de cada consulta): cobranzas, pagos, cheques de terceros, cheques propios (solo A), saldos, movimientos, ventas. En `privado/tango/2026-09-16/` y en Drive `NAVAR - Datos/Tango`. Cuenta de Google de la empresa: `finanzasnavar@gmail.com` (creada por Thomas; falta pasar la clave a Priscilla).
- ✅ **`lector/tango.py` escrito y corrido**: arma Cuentas a Cobrar / a Pagar / Cartera de Cheques con nombre. Deja `para_pegar_en_la_sheet_<fecha>.xlsx`, `resumen_tango_<fecha>.md` y una copia de la Sheet con las filas. Reglas: residuos ≤ $1 afuera; vencido antes de 2026 y cheques con fecha pasada → marcados **`REVISAR:`** (no suman al tablero, salen en Hallazgos).
- ✅ **Tablero corrido con datos de Tango** (`privado/salidas/finauto.html`, capturas `tango_*.png`). ⚠️ **Números sin validar**: vencido con proveedores pasa de $206 M a **$432 M**. Ningún número sale a NAVAR sin que Karina lo confirme.
- ✅ `herramientas/importar_cashflow.gs`: Apps Script con tres botones en el menú "finauto" de la Sheet: **Importar Tango** (cobrar/pagar/cheques), **Importar Bancos** (saldos/movimientos), **Importar Deuda** (deuda bancaria). Cada uno busca el `para_pegar_*` más nuevo en `NAVAR - Datos` y pisa lo que ese mismo lector cargó antes (respeta fórmulas y lo cargado a mano). Thomas instaló la versión "Tango" el 17/09; **hay que pegar esta versión encima**.
- ⏳ Hallazgos grandes para la reunión con Karina: Tango **no se concilia** (CAJA CONTADO -$497 M; cheques propios "Al Cobro" desde 1995; $5.700 M de cheques históricos sin marcar); deuda vieja a cobrar $55 M / a pagar $187 M desde 2007; 88 proveedores con saldo. Ver `privado/tango/2026-09-16/resumen_tango_2026-09-16.md`.
- ⏳ Automatización de Tango: Live expone una **API** (`GET Api/GetApiLiveQueryData/{process}/...`, headers `ApiAuthorization` + `Company: 13`; cobranzas = proceso 17952) y "Mis suscripciones" por mail. Con un token de un usuario propio, la ingesta diaria sale sin usuario SQL ni scraping.
- ⬜ Pendiente de Thomas: factura del 50 %, WhatsApp a Priscilla (CUIT, stock, margen) y al contador (ARCA), pegar/importar Tango en la Sheet, validar con Karina, rediseño visual del tablero (dirección elegida: barra lateral oscura + números serif, ver `scratchpad/estilos/D_final`).
- ✅ **Extractos de los 5 bancos leídos** (`privado/bancos/{bbva,galicia,macro,corrientes,nacion}/`, `lector/extractos.py`): **2.375 movimientos** reales jun→sep clasificados, saldo real por cuenta y día. **Posición en cuentas corrientes al 15-17/09: -$189,5 M** (BBVA +$6,4 M · Galicia -$9,1 M · Macro -$39,7 M · Corrientes -$45,3 M · Nación -$101,7 M). Viven de descubiertos y de descontar cheques (Galicia $356 M en 3 meses). Sueldos ~$100 M/mes por Macro. CUIT **30-55852502-5**. El Nación llegó el 18/09 **escaneado** (imagen): se lee con OCR de macOS (`lector/herramientas/ocr_mac.swift`) y se controla con la cadena de saldos; las transferencias entre bancos cruzan al peso con los otros extractos. El 14/09 el Nación pagó la tarjeta AgroNación ($82,8 M) y una cuota impaga ($17,5 M) con un descubierto nuevo de $100 M: por eso está en -$101,7 M.
- ✅ **Mapa de deuda bancaria cargado** (`privado/bancos/Bancos_Navar.xlsx` → `lector/deuda_bancaria.py` → solapa Deuda Bancaria, líneas + cronograma). **Deuda total con bancos: $2.653 M** (Corrientes $1.073 M · Nación $673 M · Macro $361 M · BBVA $309 M · Galicia $237 M), de los cuales ~$196 M son descubiertos usados (ya están en la caja). **Cuotas vencidas e impagas: $362 M** (Corrientes: 4 préstamos con 3-4 cuotas impagas c/u, situación BCRA 3, 92 días; BBVA cuota del 11/09). Vencen en 30 días: $160 M; en 90: $469 M. Margen libre de descubierto: **$11 M** (Macro $10,3 M + Galicia $0,9 M; Nación excedido, Corrientes sin acuerdo informado). Faltan: hipoteca "La Gloria" y tarjeta corporativa Nación (sin importe), venta de valores Macro ($270 M acordado, sin saldo), cuota real de Galicia (estimada $23,5 M), y los $260 M de "operaciones diferidas" de la AgroNación (Envasando SRL $245 M) que el mapa no suma.
- ✅ **BCRA consultado** (`privado/bcra/`): deuda bancaria total **$3.486 M** (jul-26), situación 2 en Nación (refinanciado, 18 días) y Corrientes; 1 en BBVA, Galicia, Macro. 24 meses de historia guardados.
- ⬜ Lo que todavía falta en el tablero: **Deuda Impositiva** (ARCA, IIBB, planes de pago: sale del contador) y la **caja de AA** (sigue con la carga manual del 31/08: $39,3 M; no hay extractos de AA). El tablero lo dice en Hallazgos.
- ⬜ Pendiente de Thomas (18/09): subir `para_pegar_bancos_2026-09-18.xlsx` y `para_pegar_deuda_2026-09-18.xlsx` a Drive, pegar el `importar_cashflow.gs` nuevo y correr los tres botones; subir el `finauto.html` nuevo a `NAVAR - Datos/Tablero`; preguntar por los $260 M diferidos de la AgroNación, el "N/C DEUD. PUBLICA" del Macro y los $15,5 M pendientes del BBVA.

**Decisiones que no hay que re-litigar:** no hay servidor pago; la notebook de NAVAR es el
"servidor" (bots, Tango, finauto, Drive para escritorio) y Apps Script sirve el tablero.
Las claves de banco las carga alguien de NAVAR en esa máquina; Thomas no las ve.

## Dónde estábamos (12/09/2026)

1. ✅ Descubrimiento y diagnóstico del cash viejo (`privado/diagnostico_2026-09-12.md`): 10 errores de fórmula, ±49% de error en la proyección de ingresos.
2. ✅ Cash nuevo (Cowork + `arreglar_cash_v2.py`), en Google Sheets, con las 6 semanas reales, 8 proyectadas y los stocks de deuda al 31/08.
3. ✅ `lector/cash_limpio.py` → contrato → `finauto.py` → tablero con los números de NAVAR. Lo vencido entra a la curva el día 1.
4. ✅ PDF de propuesta para la dueña (`privado/salidas/NAVAR - Propuesta finauto 2026-09-12.pdf`). **Pendiente que Thomas valide los números antes de mandarlo.**
5. ⬜ Presentación del proyecto (lunes 14/09 o después). Recién ahí: propiedad de la Sheet a NAVAR, permisos, exports de Tango, reunión con quien carga (10 preguntas).
6. ⬜ Fase 2: Tango automático; fase 3: bancos en una máquina del cliente.

## Cómo se corre (cuando haya contrato)

```bash
source .venv/bin/activate
python finauto.py --contrato clientes/navar/contrato_<fecha>.json --cliente navar
```

## Archivos de trabajo

| Archivo | Qué es |
|---|---|
| `documentos/CHECKLIST_IMPLEMENTACION.md` | El paso a paso de la semana de implementación (16–22/09), con qué/cómo/para qué y columna de tiempos. Se convierte en el checklist de onboarding del cliente 2. |
| `documentos/ARREGLOS_ESQUELETO.md` | Los 8 arreglos al esqueleto del cash nuevo, con celda y fórmula. Para pasarle a quien lo edite. |
| `herramientas/migrar_cash_viejo.py` | Convierte el cash viejo (6 semanas reales + 8 proyectadas) en filas para pegar en el esqueleto nuevo. Deja `privado/datos_migrados_del_cash_viejo.xlsx`. Se corre con `python clientes/navar/herramientas/migrar_cash_viejo.py`. |
| `herramientas/propuesta.py` | Genera el PDF para la dueña con los números del contrato y las capturas de `privado/capturas/`. |
| `herramientas/importar_tango.gs` | Apps Script para la Sheet: menú "finauto → Importar Tango". Busca en Drive el último `para_pegar_en_la_sheet_*.xlsx`, borra las filas de Tango anteriores y las "agregado", pega las nuevas sin tocar las fórmulas. |
| `herramientas/tablero_web.gs` | El Apps Script que sirve el tablero en una URL privada de Google (lee `NAVAR - Datos/Tablero/finauto.html` de Drive, lista de mails permitidos, banda si tiene más de 48 hs). Se pega en la Sheet → Extensiones → Apps Script. |
| `herramientas/arreglar_cash_v2.py` | Toma el cash que devolvió Cowork (`privado/NAVAR_-_Cash_Flow_Limpio.xlsx`), regenera el consolidado con semanas lunes-domingo, vacía los ejemplos y mueve los proyectados a las listas. Deja **`privado/NAVAR - Cash Flow Limpio v2.xlsx`, que es la versión buena**. |

## El cash nuevo (el entregable)

`privado/NAVAR - Cash Flow Limpio v2.xlsx`. Verificado el 12/09 recalculándolo
completo: coincide al peso con las 8 semanas proyectadas del cash viejo. Tres
cosas para saber al mirarlo:
- El horizonte arranca el lunes 31/08. Como es fin de mes, "Sem 1 Ago 26" tiene
  un solo día (el 31/08) y ahí cae toda la primera semana migrada. Es normal:
  los datos migrados son agregados semanales fechados en el lunes.
- El bloque "Vencido a la fecha" muestra ~$109M "vencido a cobrar": son las
  cobranzas proyectadas para el 31/08 y el 07/09, que ya pasaron. Desaparece
  cuando carguen lo real de esas semanas.
- Los $124M de cheques en cartera entran como cobro el 31/08 porque el cash
  viejo no tenía fecha de cobro por cheque. Se corrige con el detalle de Tango.
