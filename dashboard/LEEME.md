# El tablero

    python finauto.py --contrato datos/CONTRATO_<cliente>_<fecha>.json

Eso arma **todo** y deja en `salidas/`:

| | |
|---|---|
| `finauto.html` | **el tablero**: seis capas, un botón por empresa. Es lo que se muestra. |
| `informe.html` | una sola página, para mandar por mail o imprimir. |

## Los archivos

| | |
|---|---|
| `datos.py` | calcula **todo** y lo devuelve como JSON. Acá vive la plata. |
| `app.py` | el HTML del tablero. Solo muestra: no hace una sola cuenta. |
| `generar.py` | el informe de una página. Comparte los hallazgos con la app. |

## La regla que ordena todo esto

**La plata se calcula en Python. El HTML solo muestra.**

Es tentador hacer la calculadora de retiro en JavaScript: son cuatro sumas. El
problema es que a la semana hay dos motores —uno con tests y otro sin— y se
despegan sin que nadie se entere. Por eso las cuatro ventanas de la calculadora
(7/14/30/45 días) vienen **precalculadas**: mover el selector no recalcula nada.

## Y por qué no hay librerías

Los gráficos son SVG escrito a mano. No es purismo: el archivo tiene que abrirse
en una reunión **sin internet**. Cualquier `<script src>` de un CDN es una forma
de que el tablero aparezca vacío justo cuando importa.

*(Antes había acá dos maquetas HTML con números inventados. Se borraron: una
maqueta que no lee el contrato real no prueba nada y se termina mostrando por
error.)*
