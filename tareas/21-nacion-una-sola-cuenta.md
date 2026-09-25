# Tarea 21 — Nación: el mismo extracto aparece con dos números de cuenta
Estado: pendiente
Rama: tarea/nacion-cuenta

## Objetivo

Que todos los extractos del Nación caigan en **una sola cuenta**. Hoy el número sale a veces con 14
dígitos y a veces con 13, y el cash toma cada variante como una cuenta distinta. Resultado: suma el
saldo dos veces.

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `CLAUDE.md`, `clientes/navar/LEEME.md` y en
`lector/extractos.py` el encabezado (sección NACIÓN), `leer_pdf_nacion`, `_leer_extracto_nacion`,
`_leer_pantalla_nacion` y `procesar`.

Pasó el 25/09/2026 con `Bancos/nacion/Movimientos Nacion 25-09-2026.pdf` (escaneado, leído con OCR):
- `_leer_extracto_nacion` toma la cuenta con `CUENTA CORRIENTE\s+(\d{10,})` **solo de la página 1**.
- El extracto viejo (`nacion movimientos.pdf`) dice `19477890007728` en la página 1 y
  `1947789000772` en la página 2. El nuevo dice `1947789000772` en la página 1. El banco imprime
  las dos formas; no es un error del OCR.
- `_leer_pantalla_nacion` arma `casa + cuenta` = `19477890007728`.
- `procesar` agrupa los saldos por (cuenta, fecha). Con dos variantes quedan dos cuentas: la vieja
  arrastra −$101,7 M del 15/09 y la nueva −$97,8 M del 24/09. En la Sheet, `crear_cash.gs →
  _cuentasVistaBancos_` distingue cuentas por banco + empresa + número, así que **el Nación sumaría
  las dos**.
- **Parche manual del 25/09 (decisión de Thomas: procesarlo igual):** en la caché OCR de ese PDF
  (`Bancos/nacion/.ocr/Movimientos Nacion 25-09-2026.tsv`, generada en la Mac y copiada a Drive
  para la notebook) se reemplazó el renglón `1947789000772` por `19477890007728`. Verificado: los
  tres extractos quedan en una sola cuenta, con saldo −$97,8 M al 24/09. El próximo extracto que
  llegue con 13 dígitos vuelve a separar la cuenta; por eso esta tarea sigue haciendo falta.

## Archivos permitidos

- `lector/extractos.py`
- `clientes/navar/perfil.json` — **solo** `bancos.nacion` (una lista de cuentas conocidas).
- `tests/test_lector.py` (o el archivo de pruebas de lectores que exista; si no hay uno para esto,
  crear `lector/pruebas/test_nacion_cuenta.py` y anotarlo)
- `tareas/21-nacion-una-sola-cuenta.md`

## Resultado esperado

1. `perfil.json → bancos.nacion.cuentas_conocidas: ["19477890007728"]`, con un `_nota` que diga
   que el banco la imprime también sin el último dígito.
2. Una función chica que **normaliza la cuenta del Nación** antes de armar los movimientos. Si lo
   leído es igual a una cuenta conocida, o es una conocida sin su último dígito, se usa la
   conocida. En los dos lectores del Nación (extracto y pantalla 3270). Si lo leído no coincide con
   ninguna conocida, queda como vino y la `nota` de la lectura lo dice con `REVISAR: cuenta
   desconocida`. No adivinar.
3. En el extracto, buscar la cuenta en **todas** las páginas y preferir la que coincide con una
   conocida.
4. El lector recibe hoy la carpeta, no el cliente. Si leer `perfil.json` desde `extractos.py` obliga a
   cambiar firmas o llamadas del vigilante, **no hacerlo**: dejar la lista como constante al lado del
   encabezado NACIÓN (que ya tiene el número) y anotarlo en "Qué hice".

## Comprobaciones

1. `python -m py_compile lector/extractos.py`, JSON válido y las pruebas de lectores existentes OK.
2. Prueba nueva, sin PDFs reales: la función de normalización con `19477890007728`,
   `1947789000772`, un número ajeno y `?`.
3. En "Qué hice", decir qué pasaría con los dos extractos del Nación que hay hoy. Claude lo
   verifica con los reales en la Mac, porque los worktrees no tienen `privado/` ni Drive.
4. `grep` de nombres propios de personas vacío. Commit en la rama.

## Qué hice

## Revisión
