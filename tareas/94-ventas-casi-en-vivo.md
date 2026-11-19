# Tarea 94 — Ventas casi en vivo (bajada rápida cada 30 min)
Estado: lista para revisión (revisada por Claude)
Rama: tarea/94-ventas-casi-en-vivo

## Objetivo
Que un tablero muestre las ventas de Mercado Libre y Tiendanube del día con media hora o una hora de
atraso, no solamente las del día anterior. Para eso hacen falta:
1. una **bajada rápida** de ventas que pueda correr cada 30 minutos sin gastar cientos de pedidos a la
   API cada vez;
2. que las ventas incluyan **el día de hoy**, aunque todavía no esté cerrado;
3. que dos bajadas no se pisen si arrancan a la vez;
4. un aviso cuando la carpeta de salida es de Google Drive para escritorio y la aplicación de Drive está
   cerrada, porque entonces los CSV no suben a la nube. Además, intentar abrirla.

## Contexto
- `ingestas/mercado_datos.py` es la bajada diaria y corre varias veces por día con `--solo-pendientes`.
  Hoy baja todo hasta **ayer**: `hasta = hoy - 1 día`. Después de la primera corrida buena del día, las
  demás no hacen nada.
- `ingestas/meli_ventas.py::bajar` vuelve a pedir en cada corrida los pagos, el envío y los costos de
  todas las órdenes de los últimos 15 días y de las que todavía no terminaron (función `refrescar`). Una
  corrida completa hace unos 900 pedidos y tarda unos 6 minutos. Está bien hacerlo pocas veces por día,
  pero no cada 30 minutos.
- `ingestas/tiendanube.py::bajar` es liviano: pocas órdenes. Con `hasta = hoy` alcanza.
- Mercado Pago (liquidaciones y saldo), publicidad, Galicia y dólar **siguen como están**: día cerrado,
  ayer.
- La aplicación de Google Drive para escritorio en macOS se llama "Google Drive". Cuando está cerrada,
  los archivos se escriben igual en `~/Library/CloudStorage/GoogleDrive-*/...` pero no suben.

## Archivos permitidos
- `ingestas/mercado_datos.py`
- `ingestas/meli_ventas.py`
- `ingestas/tiendanube.py` (solo si hace falta)
- `ingestas/drive_local.py` (agregar la función del aviso de Drive)
- `tests/test_mercado_datos.py`, `tests/test_meli_ventas.py`, `tests/test_tiendanube.py`
- esta consigna (sección "Qué hice")

## Resultado esperado
1. **Hoy incluido en ventas**: en `mercado_datos.py`, `mercadolibre` y `tiendanube` usan `hasta = hoy`
   (hora de Buenos Aires) en todas las corridas, no solo en la rápida. Las demás fuentes siguen con
   `hasta = ayer`. En `control.json`, el `hasta` de esas dos fuentes puede ser hoy.
2. **Bandera `--rapida`** en `mercado_datos.py`:
   - corre solo `mercadolibre` y `tiendanube`. Si además viene `--solo`, respeta esa fuente cuando es
     una de esas dos;
   - no mira ni modifica el estado de `--solo-pendientes` (`.run/mercado_datos_estado.json`): las
     corridas diarias siguen haciendo su pasada completa;
   - en Mercado Libre, `bajar(..., rapida=True)`:
     - busca solo las órdenes **creadas desde ayer** más las **actualizadas desde la última corrida**
       (`date_last_updated` desde `ultima` menos 2 días, como hoy);
     - vuelve a pedir detalles únicamente de las órdenes nuevas, las incompletas (les falta algún
       archivo de caché) y aquellas cuyo `date_last_updated` cambió. **No** aplica la regla de los
       15 días ni la de "todavía no terminó";
     - el CSV se arma igual que siempre, con **todas** las órdenes de la caché dentro de
       `desde..hasta`: la rápida no puede achicar `ml_ventas.csv`;
   - la marca de avance (`ultima-mercadolibre.json` / `cache/ultima.json`) se actualiza igual que en
     la corrida normal.
3. **`actualizado` por fuente**: cuando una fuente sale bien (en cualquier corrida), su resumen de
   `control.json` suma `actualizado: "AAAA-MM-DD HH:MM"`, en hora de Buenos Aires. Con eso el tablero
   sabe de qué hora es cada dato. `control['corrida']` sigue como está.
4. **Una corrida por vez**: candado de archivo (`fcntl.flock`) en
   `clientes/<cliente>/.run/mercado_datos.lock`:
   - si está tomado, la `--rapida` sale con código 0 y escribe "Hay otra bajada en curso; esta se
     saltea.";
   - la corrida normal espera hasta 20 minutos; si sigue tomado, sale con código 1 y un mensaje claro;
   - en Windows, donde no existe `fcntl`, se sigue sin candado. Dejar un comentario que lo explique.
5. **Aviso de Drive**: en `drive_local.py`, `revisar_drive_escritorio(ruta_salida)`:
   - devuelve `''` si la ruta no está bajo `~/Library/CloudStorage/GoogleDrive-*`, si no es macOS o si
     el proceso "Google Drive" está corriendo (`pgrep -x "Google Drive"`);
   - si está cerrado, intenta `open -a "Google Drive"` y devuelve un texto como
     `"Google Drive estaba cerrado; se volvió a abrir a las HH:MM"`, o `"... y no se pudo abrir"`;
   - `mercado_datos.py` la llama al empezar. Si devuelve texto, lo imprime y lo guarda en
     `control['aviso_drive']`. Si devuelve `''`, borra esa clave.
   - Ninguna falla de esta revisión corta la bajada.
6. Comentarios en criollo en cada cambio: qué hace y por qué.

## Comprobaciones
- `PYTHONPATH=. python -m unittest discover -s tests` en verde, con pruebas nuevas e inventadas para:
  - la rápida no pide detalles de una orden vieja sin cambios, sí de una nueva y sí de una con
    `date_last_updated` distinto;
  - la rápida no achica el CSV: una orden vieja de la caché sigue en las filas;
  - `--rapida` no toca el estado de pendientes y solo corre ML y TN;
  - ventas con `hasta = hoy` y Mercado Pago con `hasta = ayer`;
  - `actualizado` en el resumen;
  - candado tomado: la rápida sale con 0 y no escribe nada;
  - `revisar_drive_escritorio` con `subprocess` simulado: ruta fuera de Drive, Drive abierto y Drive
    cerrado.
- Sin datos reales ni nombres de clientes en código, pruebas o esta consigna. No usar
  `clientes/*/privado/` ni la red.

## Qué hice
- `ingestas/mercado_datos.py`: agregué `--rapida` para ML y TN, sin leer ni escribir el
  estado diario. Las ventas incluyen hoy en Buenos Aires; las otras fuentes conservan ayer.
  Cada fuente exitosa informa `actualizado`. El candado protege toda la corrida: la rápida
  se saltea si está ocupado y la normal espera hasta 20 minutos. En Windows sigue sin candado.
- `ingestas/meli_ventas.py`: la rápida busca creadas desde ayer y actualizadas desde la
  última corrida menos dos días. Pide detalles solo de nuevas, cambiadas o incompletas,
  incluyendo faltantes de órdenes históricas. Arma el CSV con toda la caché del período.
- `ingestas/drive_local.py`: revisión del proceso de Drive en macOS, intento de apertura
  y aviso que se imprime y se guarda o elimina en `control.json`, sin frenar la bajada.
- Pruebas en `tests/test_mercado_datos.py`, `tests/test_meli_ventas.py` y
  `tests/test_tiendanube.py`: datos inventados, APIs y procesos simulados; cubren fechas,
  historial, refresco selectivo, marcas, pendientes, candado, espera y avisos de Drive.
- Validación: `PYTHONPATH=. /Users/thomasmanzo/Documents/Finnauto/.venv/bin/python3 -m unittest discover -s tests`
  terminó con **88 pruebas OK**. `git diff --check` sin errores.
- Decisión menor: `--rapida --solo` con una fuente distinta de ML o TN informa un error de
  argumentos, para no aparentar una bajada que no se ejecutó.
- Sin red, sin acceso a `clientes/*/privado/`, sin dependencias nuevas y sin commit.
  Todo quedó en este worktree y en la rama indicada. Los documentos locales de NAVAR no
  están en el worktree; se usó el contexto de esta consigna. No se probó contra servicios
  reales ni se instaló una tarea programada (fuera del alcance). Sin dudas pendientes.

## Revisión
- Diff revisado. 88 pruebas OK y 43 de `bots.galicia.test_navar` OK.
- Corrida real de `--rapida` hacia una carpeta de prueba:
  - 48 s y ~100 pedidos, contra ~6 min y ~900 de la completa;
  - el CSV de ventas conserva todas las filas anteriores y suma las de hoy;
  - `actualizado` aparece en las dos fuentes.
- Falta el OK de Thomas para mergear y para instalar el launchd de cada 30 min.
