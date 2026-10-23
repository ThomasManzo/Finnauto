# Tarea 62 — Escenario "Cash compra canchada": la compra de canchada mes a mes, sin secadero
Estado: aprobada e instalada (23/10/2026)
Rama: tarea/62-cash-compra-canchada

## Objetivo
Ver en la planilla, mes por mes y durante 14 meses, cómo pega en la caja un plan de compra de
canchada cuando el secadero deja de andar:
- la compra según su esquema de pago;
- menos lo que gastaban el secadero y la hoja verde;
- las ventas con su precio y sus subas, cobradas según los días promedio de cobro;
- la deuda que vence en cada mes.

## Contexto
- La dirección planteó comprar canchada todos los meses y no arrancar el secadero. Pidió verlo
  "en el cash".
- El Cash Mensual proyecta con el promedio de los 3 meses cerrados y solo 6 meses hacia adelante.
  Ese promedio incluye la cosecha y el secadero.
- Meterlo adentro del Cash Mensual cambiaría la pantalla que se usa todos los días y el Plan, que
  tiene 7 meses. Por eso va en una solapa aparte que **lee** el Cash Mensual y las listas de deuda.
- La tarea 10 ("Modelo Nuevo") apunta a lo mismo, pero arma todo desde cero con muchos supuestos.
  Esto es más corto: usa la base del cash y la corrige.

## Qué hice
**La escribió Claude** (Thomas: "reflejá lo que te dije en el cash").

- `clientes/navar/herramientas/crear_cash.gs`: función nueva `armarCompraCanchada()` y dos
  ayudantes, `_ccLeerEditable_` y `_ccReponerEditable_`. Arma la solapa "Cash compra canchada".
  No cambia ninguna función existente.
  - Supuestos editables (amarillo), **vacíos en el código**: los valores del cliente se cargan en la
    planilla y se conservan al rearmar. Son:
    - precio de venta hoy, suba por mes y cuántos meses sube;
    - días de cobro;
    - precio de la canchada, flete y en cuántas partes se paga;
    - stock propio inicial;
    - gasto del secadero y la hoja verde que deja de estar;
    - primer mes.
  - Leídos de otras solapas (gris), por texto del renglón y no por posición:
    - promedio de egresos: el promedio de los 3 meses cerrados de "Total egresos de la operación". Ese
      renglón no tiene "Prom. base": el primer armado lo buscaba ahí y daba vacío;
    - inflación (`Cash Mensual!B4`);
    - saldo de partida y descubierto acordado (del Cash Mensual, el mes anterior al primero).
  - Renglones:
    - TN vendidas × precio = ventas;
    - cobranza corrida por los días de cobro (parte entera en meses y fracción);
    - gastos base × inflación, menos secadero y hoja verde;
    - canchada en N partes iguales desde el mes de compra, más el flete;
    - deuda: la del Cash Mensual (respeta lo decidido en Plan) mientras el Cash Mensual llega; después,
      la del cronograma por mes de vencimiento (automática y por decisión), con un renglón que dice de
      dónde sale cada mes;
    - saldo del mes, acumulado, descubierto y saldo disponible;
    - TN compradas y stock total.
  - Fila "Faltan cargar": lista los supuestos vacíos para que un cero no se lea como dato.
- `clientes/navar/herramientas/importar_cashflow.gs`: ítem de menú "Armar solapa Cash compra
  canchada (escenario)".
- Pruebas: las 11 `.cjs` siguen pasando. La función nueva no tiene prueba propia, porque sus
  números son fórmulas de la planilla. Se verifica en la planilla contra una cuenta hecha aparte.

## Revisión
- **Instalada el 23/10/2026.**
  - En crear_cash se insertó solo el bloque nuevo sobre lo instalado; fuera del bloque, lo instalado
    no cambió.
  - Las huellas coinciden después de recargar.
  - La solapa está armada y los supuestos cargados (los valores, solo en la planilla).
- **Verificación contra una cuenta aparte, con los mismos datos de la planilla:**
  - la base de gastos es el promedio de los 3 meses cerrados;
  - la inflación del primer mes;
  - la cobranza del primer mes (fracción de días);
  - la canchada en 4 partes (rampa 1/4, 2/4, 3/4, 4/4);
  - la deuda igual al Cash Mensual de noviembre a abril;
  - el saldo del mes y el acumulado.
  Todo da igual.
- **Primer armado con dos errores, corregidos en el segundo commit:**
  - la base daba vacía, porque el total de egresos no tiene "Prom. base";
  - la deuda salía del cronograma tal cual y no coincidía con el Cash Mensual.
- En el editor, un clic de más corrió `armarCash` en modo depuración. Es seguro: rearma desde las
  listas y no toca el Plan. Se dejó terminar.
