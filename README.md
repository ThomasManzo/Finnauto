# finauto

**Sistema de automatización financiera para PyMEs**: de la descarga de extractos
y listados a la decisión de a quién pagar, en un solo producto. Nombre de
trabajo `finauto`. Primer cliente pago: NAVAR S.A. (15/09/2026).

## Mapa de la carpeta (leer esto primero)

Todo lo que hay en `Finnauto/` cae en una de estas cinco cosas:

| Carpeta | Qué es | ¿La abrís vos? |
|---|---|---|
| **`clientes/`** | **Un cliente, una carpeta.** `navar/` y `maga/`. Adentro: `LEEME.md` (empezar por ahí), el perfil y el catálogo (lo que el motor sabe del cliente), `documentos/` (checklist, propuestas), `herramientas/` (los scripts de ese cliente) y `privado/` (planillas, PDFs y datos reales; no sube a git). | **Sí, es la que usás.** |
| **`docs/`** | Lo escrito para pensar: estado del proyecto, el negocio, el plan comercial, cómo trabajamos con los datos, ideas. | Cuando querés el panorama. |
| **El motor** (`nucleo/`, `bots/`, `lector/`, `simulador/`, `dashboard/`, `auditoria/`, `memoria/`, `informe/`, `ingestas/`, `exportador/`, `orquestador/`) | El código que hace el trabajo. Es compartido: no sabe de ningún cliente, lee `clientes/<c>/`. | No hace falta. |
| **`tests/`** y **`scripts/`** | Las pruebas automáticas (300 chequeos) y utilidades sueltas (el banco de prueba, el explorador de selectores). | No. |
| **Comandos** (`finauto.py`, `setup_credenciales.py`) | Los dos que se corren desde la terminal. | `finauto.py`, cada semana. |

### El motor, pieza por pieza (por si hace falta buscar algo)

| Carpeta | Hace |
|---|---|
| `nucleo/` | El recorrido de los bots de banco, fechas, estado, credenciales, log. |
| `bots/` | Un adaptador por banco (Galicia listo; genérico por ficha para los demás). |
| `lector/` | Lee planillas: la radiografía de una desconocida, y `cash_limpio.py` (el Cash Flow nuevo → contrato). |
| `simulador/` | Escenarios, proyección, día crítico, a quién pagar, plan mínimo. |
| `dashboard/` | El tablero (HTML que se abre con doble click) y el informe. |
| `auditoria/` | Controles: que el dato esté completo, que cierre contra el cliente, que cada peso esté en un solo lugar. |
| `memoria/` | Qué se proyectó vs. qué pasó (la bitácora). |
| `informe/` | Los PDF: visita, dossier, manual. |
| `ingestas/` | Parsers de listados del banco (cheques). |
| `exportador/` | El Apps Script de Google Sheets (el de MAGA). |
| `orquestador/` | El comando que corre los bots por cliente y banco. |

## Cómo se corre

```
pip install -r requirements.txt
python -m playwright install chromium
python setup_credenciales.py --cliente maga --banco galicia
python orquestador/correr.py --cliente maga --banco galicia --modo prueba
```

- `--modo prueba` = navegador visible (para depurar) · `--modo produccion` = invisible.
- `--todos` corre todos los bancos activos del perfil.

## Estado

⚠️ **El refactor de Galicia se portó 1:1 del bot probado, pero todavía NO se corrió
contra el banco desde esta estructura nueva.** Antes de reemplazar producción hay
que hacer una corrida de prueba. Ver `docs/MANANA_THOMAS.md`.

## Cómo se corre

Un solo comando arma todo el material de una visita:

```bash
python finauto.py --contrato datos/CONTRATO_maga_2026-09-05.json
```

Controla el dato, lo contrasta contra los números del propio cliente, arma el
tablero y el informe, y guarda la foto de hoy en la memoria.

**Lo último no es un extra.** Es lo único que hace que la segunda visita valga
más que la primera — y la foto de hoy solo se puede sacar hoy.

### Las herramientas por separado

```bash
python dashboard/app.py       --contrato c.json    # el tablero
python dashboard/generar.py   --contrato c.json    # el informe de una página
python simulador/proveedores.py   --contrato c.json --cliente maga
python simulador/disponibilidad.py --contrato c.json --retiro 150000000
python simulador/posicion.py  --contrato c.json
python simulador/proyeccion.py --contrato c.json
python auditoria/contraste.py --contrato c.json
python auditoria/revisar.py   --contrato c.json
```
