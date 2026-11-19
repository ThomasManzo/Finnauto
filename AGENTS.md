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
7. **Si Claude no está (por ejemplo, Thomas se quedó sin cupo) y Thomas te pide seguir un tema**, el
   contexto vive en archivos, no en los chats. Leer en este orden y solo lo del tema:
   - `docs/mapa_de_chats.md` (solo en la Mac de Thomas): qué temas hay, quién los llevaba y en qué estado.
   - El LEEME del cliente, empezando por la sección "Dónde estamos" más nueva: NAVAR en
     `clientes/navar/LEEME.md`; Horizon Global en Google Drive, en
     `~/Library/CloudStorage/GoogleDrive-*/Mi unidad/01 Trabajo/Finauto/Clientes/Horizon Global/00 LEEME.md`
     (y los `estado_*.md` de su carpeta `04 Sistema/`).
   - Las reglas que Thomas fue dando, en `~/.claude/projects/*Finnauto/memory/` (un archivo por regla;
     `MEMORY.md` es el índice).
   Reglas que no cambian: validar cada número contra la fuente antes de mostrarlo y, si no cierra, parar
   y consultar; no mandar mensajes, mails ni compartir nada con terceros (eso lo hace Thomas); ninguna
   clave pasa por el chat; el repo es público, sin datos reales. Al terminar, dejar el estado nuevo en
   el LEEME del cliente (sección "Dónde estamos" con fecha), para que el próximo, sea Claude o Codex, siga.
