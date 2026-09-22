# Para cualquier agente de código (Codex, Cursor, etc.)

Este repo ya tiene su contexto escrito para Claude Code. Las reglas son las mismas para todos:

1. Leer **`CLAUDE.md`** completo antes de tocar nada.
2. Si el trabajo es sobre el cliente NAVAR: leer **`clientes/navar/LEEME.md`** (primero la sección
   "Próximos pasos") y **`clientes/navar/documentos/manual_cash.md`**.
3. Thomas no programa: consultarle antes de cambios grandes y dejar todo comentado en criollo
   (qué hace y por qué, no cómo).
4. **Sin nombres propios** de gente de NAVAR en la solapa Instrucciones de la Sheet ni en los PDF:
   usar roles (administración, la dirección, el estudio, finauto).
5. **Reparto de trabajo**: Claude Code piensa y decide con Thomas y lleva lo de NAVAR que necesita
   datos reales; Codex ejecuta tareas aisladas. Cada tarea es un archivo `tareas/<nn>-<nombre>.md`
   y se hace en un worktree propio (rama `tarea/<nombre>`), nunca en `main` directo. El circuito
   completo y la plantilla están en **`tareas/LEEME.md`**: leerlo antes de arrancar una tarea.
6. Nada de lo que está en `clientes/*/privado/` sube a git (está en `.gitignore`); ahí viven los datos reales.
