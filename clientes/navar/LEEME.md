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
python lector/cash_limpio.py --archivo "clientes/navar/privado/NAVAR - Cash Flow (export Sheets 2026-09-12).xlsx" --cliente navar --hoy 2026-08-31
python finauto.py --contrato clientes/navar/contrato_2026-08-31.json --cliente navar --salidas clientes/navar/privado/salidas
python clientes/navar/herramientas/propuesta.py        # el PDF para la dueña, con capturas del tablero
```

`--hoy 2026-08-31` porque los datos cargados son de ese lunes: con la fecha real
el tablero marcaría como vencidas cobranzas que son proyecciones de semanas
pasadas. Cuando carguen una semana nueva, se corre con la fecha de esa carga.

## Contrato (15/09/2026)

**NAVAR dio el OK el 15/09/2026.** Implementación $1.400.000 (pesos) + abono
USD 400/mes desde el mes 2, revisable a los 3 meses contra el acierto medido.
La presentación (PDF de propuesta + vista rápida del tablero + la Sheet) fue
lo que cerró. Primer peso cobrado de finauto.

## Dónde estamos (12/09/2026)

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
