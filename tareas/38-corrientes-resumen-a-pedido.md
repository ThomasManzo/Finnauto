# Tarea 38 — Corrientes: leer el formato "RESUMEN A PEDIDO"
Estado: aprobada (mergeada el 01/10/2026, con OK de Thomas)
Rama: tarea/corrientes-a-pedido

## Objetivo

Que el lector de extractos lea el resumen de Banco de Corrientes en el formato nuevo ("RESUMEN A
PEDIDO"). El 01/10/2026 se subió `Res_130559 NAVAR SA - 15 AL 30 SEPTIEMBRE 2026.pdf`, el lector lo
salteó ("no se reconocieron movimientos ni saldos") y el mail siguió diciendo que Corrientes no se
actualiza desde el 16/09.

## Contexto

`lector/extractos.py → leer_pdf_corrientes` solo conoce el formato del resumen de cuenta (el del
01/06 al 17/09), donde cada línea dice si es débito o crédito:

```
16/06/26 Acred. Ch.Camara 1532532 Cr 1,566,916.00 -42,384,095.55
```

El formato "A PEDIDO" (generado por GeneXus) sale así del texto del PDF (`pypdf`). Los importes de
este ejemplo son **inventados**; la forma es la real:

```
130559 30/09/26Número de cuenta: Estado de Cuenta al:
FECHA CONCEPTO REFERENCIA DEBITOS CREDITOS SALDOCHEQUE
SALDO INICIAL -1,000,000.00
15/09/26 10.00Imp. ley 25413 s/debitos -1,000,010.00
15/09/26 500.00Acred. transferencia -999,510.00
DENOMINACION CTA29/09/26 1,000.00Com.x servicios varios -1,000,510.00
SALDO FINAL -1,000,510.00
Total ret. Imp. Ley 25.413 s/débitos: 15/09/26 al 30/09/26 30.18del
```

- **No dice si es débito o crédito.** Se deduce del saldo: el saldo de la línea menos el anterior.
- El importe queda **pegado** al concepto, y a veces un pedazo del concepto (`DENOMINACION CTA`) aparece
  **antes** de la fecha.
- Importes en formato inglés, como el formato viejo (`NUM_US`, `_us`).
- La cuenta es `130559` (sale como `130559/1` en el detalle).

## Archivos permitidos

- `lector/extractos.py` — solo la parte de Corrientes.
- `lector/pruebas/test_corrientes_a_pedido.py` (nuevo)
- `tareas/38-corrientes-resumen-a-pedido.md`

## Resultado esperado

1. El formato viejo sigue igual.
2. Si el formato viejo no encuentra movimientos y el texto tiene `SALDO INICIAL`, se lee como
   "A PEDIDO":
   - solo las líneas entre `SALDO INICIAL` y `SALDO FINAL`;
   - cada movimiento: fecha `dd/mm/yy`, importe, concepto y saldo; el texto antes de la fecha se suma
     al concepto;
   - el signo sale de la cadena de saldos. Si el salto de saldo no coincide con el importe, **el
     archivo no se lee** (error claro), en vez de publicar un movimiento con el signo inventado;
   - al final, el último saldo tiene que ser igual a `SALDO FINAL`; si no, error claro.
3. La lectura deja una nota de control como la de Macro: "cadena de saldos OK: inicial …, movimientos
   …, final …".
4. Pruebas con texto inventado: formato nuevo (débitos, un crédito, concepto partido), cadena que no
   cierra (error), saldo final que no coincide (error) y formato viejo sin cambios.

## Comprobaciones

1. `python -m unittest lector.pruebas.test_corrientes_a_pedido` y las pruebas de lectores existentes OK.
2. En la Mac, con el PDF real: el lector lo lee y la cadena cierra (lo hace Claude; no va al repo).
3. Después de mergear: actualizar la notebook. El vigilante relee toda la carpeta de bancos cuando
   cambia cualquier archivo (Galicia cambia todos los días), así que Corrientes entra solo.

## Qué hice

- `leer_pdf_corrientes`: si el formato de siempre no encuentra movimientos y el texto tiene
  `SALDO INICIAL`, llama a `_corrientes_a_pedido`. El formato viejo no cambia.
- `_corrientes_a_pedido`: lee solo entre `SALDO INICIAL` y `SALDO FINAL`; cada línea es fecha +
  importe + concepto + saldo, y lo que queda antes de la fecha se suma al concepto. El signo sale del
  salto de saldo. Si el salto no coincide con el importe, o el último saldo no es el `SALDO FINAL`,
  da error y el archivo no se lee. La cuenta sale de `130559/1` si no está al principio. Deja una
  nota "cadena de saldos OK" como Macro.
- `lector/pruebas/test_corrientes_a_pedido.py`: 4 casos con texto inventado (formato nuevo con
  débitos, crédito y concepto partido; cadena que no cierra; saldo final distinto; formato viejo).
  Con las pruebas existentes de lectores: 30 OK.
- **Con el PDF real en la Mac** (`Res_130559 … 15 AL 30 SEPTIEMBRE 2026.pdf`): cuenta 130559, 8
  movimientos del 15/09 al 30/09, todos débitos (suman 26.619,50, igual al total de DEBITOS del
  resumen), cadena de saldos OK hasta el saldo final −45.324.830,66. Los dos PDF viejos de Corrientes
  se siguen leyendo igual (137 y 1 movimientos).
- No cubierto: un resumen "A PEDIDO" **sin** movimientos en el período (solo saldo inicial = final)
  sigue sin dar saldo, como antes con el formato viejo.

## Revisión
