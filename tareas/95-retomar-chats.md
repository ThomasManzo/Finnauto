# Tarea 95: retomar un chat de Claude Code desde Codex (y al revés)

## Objetivo
Que Codex pueda seguir un tema justo donde lo dejó un chat de Claude Code (por ejemplo, si Thomas se quedó sin
cupo en la mitad de una reunión), y que Codex pueda pedirle cosas a Claude Code por línea de comandos.

## Contexto
Los chats de Claude Code se guardan como archivos `.jsonl` en `~/.claude/projects/<carpeta-del-proyecto>/`
(un archivo por chat; cada renglón es un JSON: mensajes del usuario, de Claude, resultados de herramientas,
resúmenes y títulos). Son muy grandes (hasta 130 MB) porque guardan todas las salidas de herramientas.
El ejecutable de Claude Code de la app de escritorio está en
`~/Library/Application Support/Claude/claude-code/<versión>/<hash>/claude.app/Contents/MacOS/` y cambia de
carpeta con cada versión. No hay `claude` en el PATH.

## Archivos permitidos
- `herramientas/retomar_chat.py` (nuevo)
- `herramientas/claude.sh` (nuevo)
- `pruebas/test_retomar_chat.py` (nuevo, con un `.jsonl` inventado armado dentro de la prueba)
- Esta consigna (sección "Qué hice").

## Resultado esperado
1. `python herramientas/retomar_chat.py --lista`: los 20 chats más recientes del proyecto, con fecha de última
   modificación, tamaño, título (el título que guarde el archivo; si no hay, el primer mensaje del usuario
   recortado) y el id corto (primeros 8 caracteres del nombre del archivo).
2. `python herramientas/retomar_chat.py --chat <id corto o parte del título> [--ultimos 30]`: imprime solo el
   texto de los últimos N mensajes de usuario y de Claude (sin salidas de herramientas, sin imágenes, sin
   bloques de razonamiento), cada uno con fecha y "Thomas:" o "Claude:", y recortado a 1.500 caracteres. Si
   hubo un resumen por compactación, mostrar primero el último resumen (recortado a 4.000 caracteres).
   Tiene que leer el archivo de forma eficiente (de atrás para adelante o por renglones), sin cargar 130 MB en
   memoria de golpe.
3. `--proyecto <ruta>` opcional para otra carpeta; por defecto, la de este repo
   (`~/.claude/projects/-Users-<usuario>-Documents-Finnauto`, armada con el usuario actual, sin hardcodear nombres).
4. `herramientas/claude.sh`: busca el ejecutable de Claude Code más nuevo dentro de la carpeta de la app y le
   pasa todos los argumentos (ejemplo: `herramientas/claude.sh -p "pregunta"`). Si no lo encuentra, lo dice en
   criollo y sale con error.
5. Comentarios en criollo: qué hace y por qué. Sin datos reales en ningún archivo.

## Comprobaciones
- `.venv/bin/python -m unittest pruebas.test_retomar_chat` pasa (lista, búsqueda por título e id, últimos N,
  resumen primero, salidas de herramientas excluidas).
- `herramientas/claude.sh --version` muestra la versión.

## Qué hice
Estado: lista para revisión
Rama: tarea/95-retomar-chats

- Agregué `herramientas/retomar_chat.py`: lista los 20 chats más recientes, busca por
  prefijo de id o título (sin distinguir mayúsculas), muestra los últimos mensajes y
  antepone el último resumen. Lee por renglones y conserva solo los mensajes pedidos,
  recortados; excluye herramientas, imágenes y razonamiento.
- `--proyecto` recibe la carpeta que contiene los `.jsonl`. Sin ese argumento usa la
  carpeta de Claude correspondiente a `~/Documents/Finnauto`, también desde el worktree.
  Avisa si falta la carpeta, no encuentra el chat o hay varias coincidencias.
- Agregué `herramientas/claude.sh`, ejecutable: encuentra el binario más reciente por
  fecha de modificación y conserva todos los argumentos. Si falta, explica qué hacer.
- Agregué `pruebas/test_retomar_chat.py`, con datos inventados: listado y límite de 20,
  búsqueda por título e id, últimos N, resumen primero, exclusión de herramientas,
  recortes, renglón incompleto y errores de búsqueda/cantidad.
- Verificado: `.venv/bin/python -m unittest pruebas.test_retomar_chat` (5 pruebas OK);
  `herramientas/claude.sh --version` (2.1.325). También probé el wrapper con binarios
  ficticios: ausencia, elección del más reciente y argumentos con espacios.
- Sin dependencias nuevas, sin leer chats reales ni datos privados. No cambié el enlace
  `.venv` que ya estaba sin versionar. Sin dudas pendientes.


## Revisión
