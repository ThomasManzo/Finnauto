# Tarea 67 — Apartado "Calendario" en el tablero: vencimientos día por día, egresos e ingresos
Estado: pendiente
Rama: tarea/67-calendario

## Objetivo
Un apartado nuevo del tablero, **"Calendario"**, en la barra lateral debajo de "A cobrar". Muestra en
un calendario mensual qué vence cada día, con un selector **Egresos / Ingresos**. Al tocar un día se ve
el detalle. La dirección aprobó una maqueta: abajo, la descripción.

## Contexto
- Leer `AGENTS.md`, `CLAUDE.md`, `tareas/LEEME.md`, `dashboard/LEEME.md` y las tareas 63 y 64, para el
  estilo del tablero.
- El tablero (`dashboard/app.py`) se arma una vez por día con los datos del paquete
  (`dashboard/datos.py`, función `armar`, a partir del "contrato" que arma `lector/cash_limpio.py`
  desde la planilla).
  **Este apartado no necesita hablar con la planilla en vivo**: alcanza con los datos del día.
- Datos que hacen falta, con su fecha, importe, empresa (A o AA) y un texto corto de qué es. Hoy están
  en las listas que lee `cash_limpio.py`. Revisar qué llega ya al contrato o al paquete y agregar lo
  que falte en `datos.py`:
  - **Proveedores**: facturas pendientes (`Cuentas a Pagar`) por fecha de vencimiento.
  - **Cuotas de bancos**: cronograma de `Deuda Bancaria`, estado Pendiente, con la marca de débito
    automático.
  - **Impuestos y planes de ARCA**: `Deuda Impositiva` no pagada, con la marca de débito automático.
  - **Cheques propios** en cartera, por fecha de pago.
  - **Facturas a cobrar** pendientes (`Cuentas a Cobrar`) por fecha de vencimiento.
  - **Cheques de terceros** en cartera, por fecha de cobro.
  Usar las mismas exclusiones que el resto del tablero y el cash (por ejemplo, las filas marcadas
  "REVISAR", lo cobrado y lo pagado).
- **El repo es público: nada de datos reales.** Pruebas con datos inventados.

## Archivos permitidos
- `dashboard/app.py` (apartado nuevo, CSS y JS)
- `dashboard/datos.py` (armar la lista de vencimientos del paquete)
- `lector/cash_limpio.py`, **solo si** algún dato no llega al contrato. Anotar qué y por qué.
- Pruebas nuevas en `lector/pruebas/` (Python) y esta consigna.

## Resultado esperado

### Reglas de qué va dónde (decididas con la dirección)
- **Egresos**:
  - **"Sale sí o sí"** (rojo `#B4321F`): cuotas de bancos con débito automático, planes e impuestos
    de ARCA con débito automático, y **cheques propios**.
  - **"Por decisión"** (dorado `#C9A64A`): facturas de proveedores, cuotas sin débito automático,
    VEPs e impuestos sin débito.
- **Ingresos**, todo junto pero en dos tonos:
  - **cheques de terceros = firme** (verde `#2F6B45`);
  - **facturas a cobrar = esperado** (verde claro, el mismo verde con transparencia).
- **Sin duplicar**: cada factura cobrada ya no está pendiente, y su cheque está en la cartera. Igual,
  controlar en una prueba que un mismo importe no entre dos veces por la misma fuente.
- **Lo vencido no va en el calendario**: va en una tarjeta aparte ("ya vencido y sin pagar" en
  egresos; "ya vencido y sin cobrar" en ingresos).
- **Cheques con fecha ya pasada y todavía en cartera**: no se muestran como si fueran a entrar o salir.
  Se cuentan en una línea chica: "N cheques con fecha pasada sin actualizar en Tango ($X)".
- **Sin saldo proyectado por día** (decisión de la dirección).
- Respeta la empresa elegida arriba (GRUPO / A / AA).

### Pantalla (como la maqueta aprobada)
1. Arriba, dos botones: **"EGRESOS · lo que sale"** y **"INGRESOS · lo que entra"**. El elegido va
   relleno en tinta.
2. **Cuatro tarjetas** (`.kpis`), según la vista:
   - **Egresos**: sale sí o sí en el mes; vence y se paga por decisión en el mes; el día más pesado
     (fecha y monto); ya vencido y sin pagar (aparte del calendario).
   - **Ingresos**: cheques que se cobran en el mes (firme); facturas que vencen en el mes (esperado);
     el día más fuerte; ya vencido y sin cobrar.
   - En ingresos, debajo de las tarjetas, una nota: "Las facturas no se cobran el día que vencen: en
     promedio llegan alrededor de un mes después." Calcular el número con los datos: atraso promedio
     ponderado por importe de las facturas ya vencidas.
3. **Cabecera del mes**:
   - "‹ oct · noviembre 2026 · dic ›", para moverse de a un mes, desde el actual hasta 3 meses adelante;
   - a la derecha, la leyenda de colores.
4. **Grilla del mes**, de lunes a domingo, con los fines de semana con fondo apenas distinto. Cada día
   tiene:
   - el número del día;
   - el total en grande (serif), en rojo si es un día "pesado" (≥ 50% del día más alto del mes);
   - debajo, en chico, la parte firme: sí o sí en egresos, cheques en ingresos;
   - abajo, una barrita repartida por color; el alto relativo al día más alto, de 24 px como máximo;
   - los días sin nada, con "—" tenue.
5. **Al tocar un día**, a la derecha de la grilla (abajo en el celular):
   - el título con la fecha y "N vencimientos · $total";
   - una tabla: punto de color, qué es (cuota, impuesto, proveedor, cheque…), detalle (banco y línea,
     nombre del proveedor o cliente, n° de cheque), empresa e importe en pesos completos;
   - ordenada primero lo firme y después lo esperado o por decisión, de mayor a menor.
   Al entrar al apartado se abre el día más pesado del mes.
6. Abajo, una nota que explique cómo leer la grilla: el total, la parte en rojo, la barrita y que se
   toca un día.
- **Estilo**: el del tablero. Tipografías, líneas en vez de cajas, `button.mini`, sin librerías ni CDN.
- **Celular**: la grilla sigue de 7 columnas, más compacta, y el detalle va debajo.

## Comprobaciones
1. Prueba de Python de `datos.py` con un contrato inventado. Controla que:
   - cada tipo cae en su grupo (sí o sí, por decisión, firme, esperado);
   - lo vencido queda afuera del calendario y entra en la tarjeta;
   - los cheques con fecha pasada se cuentan aparte;
   - el atraso promedio ponderado da lo que tiene que dar en un ejemplo a mano;
   - no hay duplicados.
2. Prueba del render:
   - con datos, el botón y el apartado aparecen;
   - no hay `<script src=`.
3. Probarlo en el navegador con el paquete de prueba: las dos vistas, moverse de mes, tocar días,
   GRUPO / A / AA, escritorio y celular. Dejar capturas.
4. Todas las pruebas que ya existen siguen pasando.

## Qué hice
(lo completa Codex)

## Revisión
(lo completa Claude: comparar contra la planilla los totales de un mes real)
