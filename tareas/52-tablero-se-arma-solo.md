# Tarea 52 — El tablero de siempre se rearma solo
Estado: lista para revisión
Rama: tarea/tablero-se-arma-solo

## Objetivo

Que el tablero que ve la dirección de NAVAR (el de siempre: barra lateral, Grupo / A / AA, solapas
Posición, A quién pagar, A cobrar, Proyección y Hallazgos) **se actualice solo todos los días**, sin
cambiar nada de su diseño ni de sus cuentas.

## Contexto

Se armaba a mano: bajar la Sheet como Excel, correr `lector/cash_limpio.py` y `finauto.py`, y copiar
`finauto.html` a `NAVAR - Datos/Tablero/` (de ahí lo sirve `tablero_web.gs`). Por eso quedaba viejo.

Primero se probó una página nueva que leía la Sheet en vivo; Thomas la descartó (07/10/2026): "yo
quiero el mismo diseño que el que está armado, nada más que se actualice solo". Quedó descartada.

## Archivos permitidos

- `clientes/navar/herramientas/tablero_web.gs` (solo agregar la copia en Excel; `doGet` no cambia)
- `clientes/navar/herramientas/importar_cashflow.gs` (llamar a la copia cuando importa algo; menú)
- `clientes/navar/herramientas/armar_tablero.py` (nuevo) y `clientes/navar/herramientas/vigilante.py`
- `lector/pruebas/test_armar_tablero.py` (nueva)
- esta consigna

## Resultado esperado

1. **La Sheet deja una copia en Excel** en `NAVAR - Datos/Tablero/fuente/` (`exportarParaTablero`)
   cada vez que la importación horaria trae algo nuevo, y desde el menú ("Rearmar el tablero ahora").
   Guarda las 3 últimas; las viejas van a la papelera. Si la copia falla, la importación igual queda.
2. **La notebook rearma el tablero** (`armar_tablero.py`), con el vigilante:
   - corre los dos programas de siempre (`cash_limpio.py` y `finauto.py --sin-memoria`) con la copia
     más nueva;
   - arma el tablero aparte y controla que sea un tablero de verdad antes de reemplazar
     `Tablero/finauto.html`; si algo falla, queda el anterior;
   - se repite al cambiar el día aunque la copia no cambie (lo vencido depende de la fecha).
3. El link del tablero no cambia: `tablero_web.gs` sirve el último `finauto.html`, como siempre.

## Comprobaciones

- Pruebas Python sin datos reales:
  - arma y reemplaza;
  - un tablero vacío o un paso que falla no pisa el anterior;
  - sin copia, avisa;
  - el vigilante usa la copia más nueva y vuelve a correr cada día.
- A mano con una copia vieja de la Sheet en una carpeta de prueba: arma el tablero sin tocar el repo.
- En vivo: "Rearmar el tablero ahora" → en ≤ 15 min `Tablero/finauto.html` nuevo → el link lo muestra.

## Qué hice
**La escribió Claude.**
- `tablero_web.gs`: `exportarParaTablero` y `rearmarTableroAhora`. Bajan la Sheet como Excel con el
  permiso de la cuenta, la guardan en `Tablero/fuente/` con fecha y hora, y dejan las 3 últimas.
- `importar_cashflow.gs`: si importó algo, llama a la copia (con `try`: la importación no depende de
  la copia). El menú suma "Rearmar el tablero ahora".
- `armar_tablero.py`: corre `cash_limpio.py` (con `--hoy`) y `finauto.py --sin-memoria` en
  `.run/tablero`. Si el resultado pesa menos de 100 KB o no es un tablero de NAVAR, no publica. Si está
  bien, lo copia a `.parte` y lo reemplaza de un saque.
- `vigilante.py`: fuente `tablero`, con la copia más nueva de `Tablero/fuente/`. Con `mirar_dia`, la
  firma cambia cada día y se vuelve a correr.
- Pruebas: `test_armar_tablero.py` (6). Probado a mano con la copia del 29/09 en una carpeta de
  prueba: armó el tablero (744 KB) sin escribir nada en el repo.
- La primera vez que corra la copia, Google pide permiso para "conectarse a un servicio externo". Es
  para bajar la copia de la propia Sheet y lo acepta Thomas.

## Revisión
