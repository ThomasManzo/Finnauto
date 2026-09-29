# Tarea 36 — Últimos pagos: el código viene en la descripción, no en "Cód. relacionado"
Estado: lista para revisión
Rama: tarea/ultimos-pagos-codigo

## Objetivo

Que la lista "Ultimos Pagos" (tarea 34) tenga la **razón social limpia**, tal como la escribe la Sheet
en Cuentas a Cobrar / Cuentas a Pagar, y el **código de Tango** en la columna `Codigo`. Hoy, con los
datos reales, sale al revés y ningún nombre cruza con la Sheet.

## Contexto

Leer antes: `tareas/LEEME.md`, `tareas/34-ultimos-cobros-y-pagos.md`, `lector/ultimos_pagos.py` y
`lector/pruebas/test_ultimos_pagos.py`.

Primera corrida real (29/09/2026, archivos de la bajada por API de A y AA). La columna
`Cód. relacionado` **no trae el código del cliente/proveedor**: trae una letra de tipo.

| Empresa | `Cód. relacionado` | Renglones |
|---|---|---|
| A | `C` | 2.092 |
| A | `P` | 1.691 |
| A | vacío | 1.304 |
| AA | `P` / `C` / vacío | 3.351 / 1.182 / 1.266 |

El código real viene **adelante en `Desc. relacionado`**, separado por `" - "`:
`900001 - [cliente 1]`, `[codigo] - [proveedor 1]`, `MIG001 - MIGUEL ([cliente 1])`.
En los dos archivos **todas** las descripciones con relacionado tienen ese prefijo (una sola de AA es
`" - "` sola, sin código ni nombre). Los prefijos son de 4 a 6 caracteres sin espacios; casi todos
letras mayúsculas y números, pero hay `NUÑ004`, `U&G001` y `C&D000` (con Ñ y &). Hay nombres con doble
espacio adentro (`U & G  SRL`) que se tienen que conservar tal cual.

Hoy `_relacionado()` solo saca el prefijo si coincide con `Cód. relacionado` o si esa columna está
vacía y el prefijo es `[A-Za-z0-9]+`. Con `C`/`P` no lo saca: la lista queda con
`Razon Social = "900001 - [cliente 1]"` y `Codigo = "C"`. Además, como el
agrupado es por razón social, **un mismo cliente con dos códigos queda en dos renglones** en vez de uno.

Comprobado (Claude, simulando la regla de abajo sobre la salida real): de los 80 nombres de la solapa
"Principales 20" cruzan 73. Los 7 restantes no tienen ningún pago en la ventana (es un dato, no un error).

## Archivos permitidos

- `lector/ultimos_pagos.py`
- `lector/pruebas/test_ultimos_pagos.py`
- esta consigna ("Qué hice" y `Estado:`)

## Resultado esperado

1. `_relacionado(codigo, nombre)`:
   - Si `Desc. relacionado` empieza con un prefijo **sin espacios de 3 a 8 caracteres** seguido de
     `" - "` y un nombre no vacío, el prefijo es el **código** y lo de después (sin espacios en las
     puntas, con los del medio intactos) es la **razón social**, cuando `Cód. relacionado` está
     vacío, es una sola letra (`C`, `P` o cualquier otra) o es igual al prefijo.
   - Si `Cód. relacionado` trae un código de verdad (más de una letra) distinto del prefijo, se usa ese
     código y el nombre se deja entero (caso no visto; mejor no adivinar).
   - `Desc. relacionado` igual a `" - "` o vacío → "sin relacionado" (ya existe ese motivo).
2. El agrupado sigue siendo por empresa + tipo + razón social (ya limpia): un cliente con dos códigos
   queda en un renglón con `Codigo = "cod1 / cod2"`.
3. Nada más cambia (encabezados, marca, reglas de tipos/clases, salidas).

## Comprobaciones

- `python -m unittest lector.pruebas.test_ultimos_pagos` con pruebas nuevas, datos inventados:
  - `Cód. relacionado = "C"` y `Desc = "900001 - CLIENTE INVENTADO S.A."` → razón social
    `CLIENTE INVENTADO S.A.`, código `900001`;
  - lo mismo con `"P"` y `"U&G001 - U & G  SRL"` → `U & G  SRL` (doble espacio intacto), código `U&G001`;
  - `Ñ` en el código (`NUÑ004 - ...`);
  - dos códigos, misma razón social, con `C` en `Cód. relacionado` → un solo renglón, los dos códigos;
  - `Desc = " - "` → ignorado "sin relacionado";
  - las pruebas que ya existían siguen pasando.
- `python -m unittest ingestas.test_tango_live` sigue OK (no se toca, pero se corre).

## Qué hice

- Corregí únicamente `_relacionado()` en el lector: el prefijo de 3 a 8 caracteres
  sin espacios pasa a ser el código cuando la columna separada está vacía, contiene
  una sola letra o coincide con el prefijo. Admite Ñ, & y otros caracteres sin espacios.
  Si hay un código distinto, conserva ese código y la descripción entera.
- Las descripciones vacías o `" - "` quedan sin nombre y se descartan por el motivo
  existente `sin relacionado`. Se conservan los espacios internos de la razón social.
  El agrupado y las demás reglas no cambiaron: ahora reciben el nombre limpio.
- Agregué pruebas inventadas de C/P/otra letra, Ñ y &, coincidencia y conflicto de
  códigos, límites de longitud, prefijos con espacios, nombre faltante y agrupado de
  dos códigos en un solo cliente. Comprobé también los valores escritos en el Excel.
- `python -m unittest lector.pruebas.test_ultimos_pagos ingestas.test_tango_live`:
  **29 pruebas OK** (9 del lector/vigilante y 20 de Tango). `git diff --check`: OK.
  Persisten las advertencias previas de archivos de estado sin cerrar en el vigilante;
  no se modificó ese archivo. No se tocaron datos reales ni se agregaron dependencias.
- Queda para después de integrar: actualizar la notebook, reprocesar `ultimos_pagos`
  e importar la salida para comprobar el cruce real con la Sheet. Sin merge ni push.


## Revisión
