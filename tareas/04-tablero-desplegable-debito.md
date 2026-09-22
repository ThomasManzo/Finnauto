# Tarea 04 — Tablero: desplegar las obligaciones por débito automático y por banco
Estado: lista para revisión
Rama: tarea/tablero-debito

## Objetivo

En el tablero web, poder **desplegar** las obligaciones y verlas separadas en dos grupos —
**las que el banco debita solo** y **las que se pagan por decisión** — y dentro de cada grupo,
**por banco**. Cerrado se ve el total, como ahora; abierto se ve el detalle.

Es el equivalente en el tablero de lo que la tarea 02 hizo en la planilla (la fila "Cuotas y
tarjetas con débito automático" que se abre y muestra el detalle por banco).

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `CLAUDE.md`, `clientes/navar/LEEME.md`.

El tablero es `dashboard/app.py` (arma `finauto.html`: HTML + JS en un solo archivo, sin
librerías) y los datos se los prepara `dashboard/datos.py`. El tablero ya tiene una tarjeta
**"Lo que se debe a los bancos"** con una tabla por banco (`db.por_banco`, alrededor de la
línea 1100 de `dashboard/app.py`): banco, deuda, vencido, en 30 días, descubierto usado/acordado
y situación BCRA. Ese es el lugar natural para colgar el despliegue; si conviene otra tarjeta,
decidilo y explicá por qué.

La distinción que hay que mostrar ya existe en los datos: la columna **`Debito Automatico`**
(Sí/No) de la solapa **Deuda Bancaria** (líneas y cronograma) y de **Deuda Impositiva**.
Significa: **Sí** = el banco o el organismo lo debita solo si hay fondos (préstamos, tarjetas,
hipotecas, planes de ARCA con débito en CBU); **No** = se paga por decisión (transferencia, VEP,
planes nuevos, regularización). Las excepciones están en `clientes/navar/catalogo.json →
debito_automatico`. Es la misma regla que explica `clientes/navar/documentos/manual_cash.md` §3.

**Por qué importa**: es la diferencia entre lo que va a salir de la cuenta quiera o no la empresa,
y lo que la dirección puede decidir posponer. Es la pregunta que hacen en la reunión.

## Archivos permitidos

- `dashboard/app.py`
- `dashboard/datos.py`
- `clientes/navar/documentos/manual_cash.md` — una línea donde corresponda, si hace falta.
- `tareas/04-tablero-desplegable-debito.md` — este archivo.

No tocar los lectores, `finauto.py`, `importar_cashflow.gs` ni `crear_cash.gs` (los están
modificando otras tareas en paralelo: no las pises).

## Resultado esperado

- Cerrado, la tarjeta se ve como hoy más **dos totales**: "sale sí o sí" y "se paga por decisión".
- Al desplegar, el detalle **por banco** dentro de cada grupo, con el importe y la fecha de lo
  que viene (por lo menos: lo vencido y lo que vence en 30 días).
- Los impuestos con débito automático (planes de ARCA en CBU) también son "sale sí o sí": si la
  tarjeta es solo de bancos, decidir si se suman o si van en su propia fila, y explicarlo.
- El despliegue se hace **sin librerías** y con el estilo que ya usa el tablero (`el()`, clases
  `card`, `num`, `neg`, `resumen`, `envuelve`). Que funcione con el teclado y que, si el
  navegador no corre el JS, el detalle igual esté en el HTML (nada de contenido que aparezca solo
  por script).
- Si un banco no tiene la columna cargada, mostrarlo como "sin definir" en vez de asumir que se
  debita solo. **Nunca** contar una obligación en los dos grupos: los totales tienen que sumar.

## Comprobaciones

1. `python -m py_compile dashboard/app.py dashboard/datos.py` pasa.
2. Regenerar el tablero y abrirlo para verificar. El contrato real está en
   `/Users/thomasmanzo/Documents/Finnauto/clientes/navar/contrato_2026-09-22.json` (se lee, no se
   toca; está fuera del worktree, gitignoreado). Comando:
   `python finauto.py --contrato <ese json> --cliente navar --salidas <carpeta temporal tuya>`.
   **Escribir las salidas a una carpeta temporal**, no a `clientes/navar/privado/salidas/`.
3. **Cuadre**: "sale sí o sí" + "se paga por decisión" + "sin definir" tiene que dar exactamente
   el total que ya muestra la tarjeta hoy. Pegar los tres números y el total en "Qué hice".
4. Decir cuántos bancos quedaron en cada grupo y si alguno quedó "sin definir".
5. `grep -n -i -E "priscilla|karina|celia|miriam|milagros|charles|thomas"` vacío en lo tocado.
6. Commitear en `tarea/tablero-debito`; si el sandbox no deja, anotarlo.

Al terminar: "Qué hice" y `Estado: lista para revisión`.

## Qué hice

- Trabajé en el worktree asignado, rama `tarea/tablero-debito`. Toqué solamente
  `dashboard/app.py`, `dashboard/datos.py` y esta consigna. No cambié lectores,
  planillas, manual ni datos de origen. Sin dependencias nuevas.
- Agregué tres grupos excluyentes: **Sale sí o sí**, **Se paga por decisión** y
  **Sin definir**. Aceptan booleanos y textos Sí/Si/No; vacío o desconocido queda
  sin definir. No se deduce el débito por producto ni se hereda una marca ausente.
- Conservé la tarjeta bancaria en Proyección y su tabla actual. Los grupos reparten
  el **capital vigente sin descubiertos**; el cronograma se muestra aparte, por banco,
  con importe y fecha de cada cuota, vencido y próximos 30 días. No sumé cuotas al
  capital. Conservé el criterio de fechas existente: hoy inclusive y día 30 exclusivo.
- Los impuestos tienen tarjeta propia y los mismos grupos: así los planes con débito
  en CBU no alteran el total bancario. Si no viene el banco, dice **Banco/CBU sin informar**.
- El detalle se genera en Python dentro del HTML, con `details/summary` nativos,
  foco visible y caracteres escapados. Sin JavaScript quedan los detalles de todas
  las unidades a la vista; con JavaScript se copia el correspondiente a la empresa.
  No se calcula plata en el navegador. Las sumas nuevas usan aritmética decimal.
- **Cuadre real, GRUPO y A:** $0,00 (automático) + $0,00 (decisión) +
  $2.739.983.590,31 (sin definir) = **$2.739.983.590,31**, exactamente el capital
  bancario anterior. Vencido: **$379.505.910,33**; próximos 30 días:
  **$247.039.549,72**. También cuadran por grupo y por banco, al centavo.
- **Bancos:** 0 con automático informado, 0 con pago por decisión informado y
  **5 bancos sin definir**: BBVA, CORRIENTES, GALICIA, MACRO y NACION. En GRUPO el
  contrato trae además un encabezado convertido en banco:
  `B) Cronograma de Vencimientos (cuotas)`, sin unidad/producto y con $0. La vista
  conserva esa sexta entrada tal como la tabla anterior; no es un sexto banco real.
  AA no tiene deuda bancaria ni impositiva en el contrato.
- **Impuestos, aparte:** $0,00 + $0,00 + $604.746.328,81 = **$604.746.328,81**.
  El contrato indicado no tiene `debito_automatico` en ninguna línea, cuota ni impuesto.
  Por eso todo queda sin definir: para presentar una separación real hay que hacer
  llegar la columna al contrato desde el lector. No modifiqué ese lector porque está
  fuera de alcance. Tampoco inventé el banco/CBU de los impuestos.
- **Verificado:** compilación de ambos módulos; corrida completa de `finauto.py` con
  el contrato indicado y `--salidas /tmp/tarea04-tablero --sin-memoria` (para no escribir
  fuera de los archivos autorizados); cuadres reales; comparación de todos los campos
  bancarios previos contra `HEAD`, sin cambios para GRUPO/A/AA. Pruebas inventadas en
  `/tmp/tarea04_verificar.py`: grupos mezclados en un banco, booleanos/textos/vacíos,
  capital separado de cuotas, descubiertos excluidos, ayer/hoy/días 29 y 30, unidades,
  ausencia de deuda, impuesto automático sin banco y escape HTML. Inspección del HTML:
  12 desplegables con detalle, fechas e importes ya presentes e identificadores únicos.
- **No verificado visualmente:** Chromium no pudo arrancar por restricciones del
  sandbox (`bootstrap_check_in: Permission denied`); la herramienta de interfaz no
  tiene navegadores disponibles. Quedan pendientes abrir/cerrar por teclado, cambio
  de empresa y revisión visual con/sin JavaScript y en móvil. Tampoco pude ejecutar
  el chequeo de sintaxis con Node porque no está instalado. No presento estas pruebas
  como realizadas. El HTML regenerado está en `/tmp/tarea04-tablero/finauto.html`.
- Búsqueda de nombres: vacía en ambos archivos de código; reemplacé también las
  menciones anteriores de comentarios por roles. Esta consigna conserva las menciones
  y rutas originales de sus instrucciones; no agregué nombres propios en «Qué hice».
- **Commit pendiente por sandbox:** `git add` falló al crear `index.lock` en el
  directorio git del worktree (`Operation not permitted`). No pude crear el commit;
  los tres archivos quedan modificados en esta rama para que el revisor los commitee.

## Revisión

(lo completa Claude)
