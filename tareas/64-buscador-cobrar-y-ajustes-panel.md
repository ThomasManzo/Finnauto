# Tarea 64 — Buscador en "A cobrar" y tres ajustes del panel "Compra de canchada"
Estado: pendiente
Rama: tarea/64-buscador-y-panel

## Objetivo
Cuatro cambios chicos del tablero, pedidos por la administración del cliente:
1. En "A cobrar", un buscador por nombre de cliente y la lista más corta.
2. En el panel "Compra de canchada" (tarea 63), cada control se puede **escribir con el número**
   además de moverlo con la barra.
3. En el mismo panel, una leyenda clara del gráfico.
4. En el mismo panel, la banda amarilla aparece solo cuando de verdad falta cargar algo.

## Contexto
- Leer `AGENTS.md`, `CLAUDE.md`, `tareas/LEEME.md` y la consigna y el "Qué hice" de
  `tareas/63-panel-compra-canchada.md`.
- "A cobrar" es `verCobrar()` en `dashboard/app.py`. Hoy muestra todas las filas de `d.a_cobrar.filas`
  de la empresa elegida arriba (GRUPO / A / AA) en una tabla larga.
- El panel de canchada es `JS_CANCHADA` en `dashboard/app.py`. La lógica de guardar (agrupar cambios,
  esperar 0,8 s, no pisar lo que se mueve mientras guarda, volver al último valor bueno si hay error)
  **no se cambia**: los números escritos entran por el mismo camino que las barras.
- **El repo es público: nada de datos reales.** Ejemplos inventados en pruebas.

## Archivos permitidos
- `dashboard/app.py`
- `lector/pruebas/test_panel_canchada.py` y un test nuevo de Python para el buscador, si hace falta.
- `tareas/64-buscador-cobrar-y-ajustes-panel.md`

## Resultado esperado

### 1 · Buscador en "A cobrar"
- Arriba de la tabla "Quién nos debe", una caja "Buscar cliente…", con el estilo de los `input`
  del tablero.
- **Busca solo por nombre del cliente**, sin importar mayúsculas ni acentos ("garcia" encuentra
  "García"), y **en A y AA juntas**, sin importar la empresa elegida arriba.
  - Si el paquete trae las filas de las dos empresas por separado, se buscan en las dos y se muestra
    una columna "Empresa".
  - Si la fila del GRUPO ya junta las dos empresas, se usa esa.
- **Lista corta**:
  - sin texto en la caja, se ven los **10 que más deben** (por total) y abajo un botón `mini`
    "ver todos (N)" que despliega el resto y cambia a "ver menos";
  - con texto, se ven todas las coincidencias, y si no hay ninguna, "No hay clientes con ese nombre".
- Los KPIs de arriba no cambian con la búsqueda.

### 2 · Escribir el número en el panel
- En cada uno de los 10 controles, el valor grande se puede tocar para escribirlo: se vuelve un
  casillero numérico con el mismo tamaño y tipografía, o se agrega un casillero chico al lado. Elegí
  lo que quede más claro y anotalo.
- Al confirmar (Enter o al salir del casillero) se valida igual que el servidor: mismos rangos, y
  partes y meses enteros. Si está mal, se marca en rojo con el motivo y **no se manda**.
- Si está bien, se mueve la barra a ese valor y entra por el mismo `ccCambio`.
- **Los valores escritos pueden quedar fuera de la escala de la barra** (por ejemplo, un precio de
  canchada mayor al máximo de la barra): se guardan igual, y la barra queda en el tope con una
  aclaración chica "fuera de la escala".
- Unidades: en "Suba del precio" se escribe el porcentaje (5 = 5%); en "Secadero" se escriben
  millones (281 = $281 M). El panel convierte antes de mandar, como ya hace con la barra.

### 3 · Leyenda del gráfico "Caja mes a mes"
- Arriba del gráfico, una leyenda con una muestra de cada cosa y su explicación en criollo:
  - **línea negra con puntos**: saldo acumulado a fin de cada mes (lo que queda después de todo);
  - **puntos rojos**: meses en que ni usando el descubierto alcanza;
  - **barras verdes / rojas**: lo que gana o pierde la caja en cada mes;
  - **línea punteada ámbar**: el límite del descubierto acordado con los bancos (por debajo de esa
    línea, falta plata).
- Los colores de la leyenda tienen que ser los mismos del gráfico.

### 4 · Banda de "Faltan cargar"
- Hoy aparece siempre, aunque diga "nada: el escenario está completo". Tiene que aparecer **solo**
  cuando `falta` no está vacío y no empieza con "nada".

## Comprobaciones
1. Test de Python del render:
   - el buscador está en el HTML;
   - la búsqueda ignora acentos y mayúsculas (probar la función de normalizar del JS con un caso
     inventado, o, si no se puede, dejarlo anotado);
   - sigue sin haber `<script src=`.
2. Probar en un navegador con un `google.script.run` de mentira (como en la 63):
   - escribir un valor válido guarda y mueve la barra;
   - uno inválido se marca y no se manda;
   - uno fuera de la escala se guarda;
   - la leyenda se ve;
   - la banda no aparece con "nada: …".
   Capturas de escritorio y celular.
3. Todas las pruebas que ya existen siguen pasando.

## Qué hice
(lo completa Codex)

## Revisión
(lo completa Claude)
