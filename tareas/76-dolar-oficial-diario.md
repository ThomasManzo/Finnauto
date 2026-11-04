# Tarea 76 — Fuente "dolar": cotización del dólar oficial, todos los días, a CSV
Estado: lista para revisión
Rama: tarea/75-reintentos-bajada (se suma a la 75 porque toca el mismo `mercado_datos.py`)

## Objetivo
Una fuente más en la bajada diaria: guardar la cotización del dólar oficial de cada día en `dolar.csv`, con su historial.

## Contexto
- Leer `tareas/LEEME.md` y `ingestas/mercado_datos.py`. Mismo estilo: biblioteca estándar, comentarios en criollo.
- Repo público: pruebas con números inventados y cliente `ejemplo`.
- API pública, sin clave ni token: `GET https://api.argentinadatos.com/v1/cotizaciones/dolares/oficial`. Devuelve una
  lista con TODO el historial: `[{"casa": "oficial", "compra": 4, "venta": 4, "fecha": "2011-01-03"}, ...]`.

## Archivos permitidos
- `ingestas/dolar.py` (nuevo), `ingestas/mercado_datos.py`, `tests/test_dolar.py` (nuevo), `tests/test_mercado_datos.py`
- esta consigna ("Qué hice" y `Estado:`)

## Resultado esperado
- `ingestas/dolar.py`: `COLUMNAS = ['fecha', 'compra', 'venta', 'fuente']`, `fuente` = `argentinadatos`; `compra` y
  `venta` con 2 decimales (`Decimal`, no float).
- `bajar(salida, desde, hasta, http=...)` devuelve las filas a escribir, ordenadas por fecha:
  - toma de la API solo las filas con `desde <= fecha <= hasta`. `hasta` es ayer (el mismo de `mercado_datos`): **la de
    hoy no se guarda**, porque puede cambiar en el día y una fila guardada no se vuelve a pisar;
  - **lo que ya está en `dolar.csv` no se pisa ni se borra**: solo se suman las fechas nuevas;
  - respuesta que no sea una lista, o fila sin fecha válida o con compra/venta que no sean números mayores a cero:
    `ml.ErrorDatos`, y el archivo queda como estaba.
- Pedido con `User-Agent` genérico (`finauto`), timeout 60, hasta 3 intentos ante 429/5xx o corte de red. Error final:
  `ml.ErrorDatos('no se pudo consultar el dólar; revisar la conexión y volver a intentar')`.
- `mercado_datos.py`: fuente `dolar` al final de la lista y en `--solo`; ruta `dolar.csv`; no necesita token ni perfil.
  Se resume en `control.json` como las demás (`ok`, `filas`, `desde`, `hasta`, `motivo`) y respeta `--solo-pendientes`.

## Comprobaciones
`PYTHONPATH=. /Users/thomasmanzo/Documents/Finnauto/.venv/bin/python3 -m unittest discover -s tests` da todo OK, con pruebas
sin red de: filtro por fechas (hoy afuera), suma sin pisar una fila existente con otro valor, respuesta inválida deja
el archivo igual y marca la fuente en rojo, reintento ante corte. Las pruebas que ya cuentan fuentes o escrituras se
ajustan solo si la fuente nueva lo exige, y se anota en "Qué hice".

## Qué hice
- Agregué `ingestas/dolar.py`: consulta pública con User-Agent `finauto`, timeout de 60 segundos
  y hasta 3 intentos ante 429, 5xx o cortes. Lee los importes directamente con Decimal y los
  guarda con 2 decimales. Valida toda la respuesta antes de devolver filas para escribir.
- Conserva todas las filas existentes de `dolar.csv`, suma solo fechas nuevas del período
  solicitado y ordena por fecha. La corrida usa ayer como límite, sin incorporar hoy.
- Integré `dolar` al final de las fuentes y en `--solo`, con resumen en `control.json` y
  estado diario para `--solo-pendientes`. No necesita token ni perfil.
- Agregué `tests/test_dolar.py` y amplié `tests/test_mercado_datos.py`, usando datos inventados,
  cliente `ejemplo` y respuestas simuladas. Ajusté la lista de fuentes del caso «todo listo».
- Verificación específica: 6 pruebas de dólar y 10 del coordinador, todas OK.
- La primera suite completa ejecutó 67 pruebas: falló únicamente
  `test_corrida_completa_y_ampliar_periodo` de `tests/test_tiendanube.py`, porque ahora debe
  simular también el dólar y contar una fuente adicional. Pedí autorización para ese ajuste,
  ya que el archivo no figura en «Archivos permitidos»; todavía no lo modifiqué.
- No pude commitear: `git add` falló con `Operation not permitted` al crear
  `/Users/thomasmanzo/Documents/Finnauto/.git/worktrees/tarea-75/index.lock`.
  Los cambios quedan en este worktree y rama para que Claude los revise y commitee.
- `git diff --check` pasó sin errores.
- No instalé dependencias ni usé datos privados. Los cambios concurrentes de Tiendanube
  son ajenos a esta tarea y se conservaron.

## Revisión
Claude, 04/11/2026: revisé el diff. Ajusté `tests/test_tiendanube.py` (fuera de la lista de Codex): simula también el
dólar, así la prueba no sale a internet, y cuenta 5 fuentes. Corrida real comprobada contra la fuente. Pruebas: ver abajo el commit.
