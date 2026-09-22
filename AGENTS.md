# Para cualquier agente de código (Codex, Cursor, etc.)

Este repo ya tiene su contexto escrito para Claude Code. Las reglas son las mismas para todos:

1. Leer **`CLAUDE.md`** completo antes de tocar nada.
2. Si el trabajo es sobre el cliente NAVAR: leer **`clientes/navar/LEEME.md`** (primero la sección
   "Próximos pasos") y **`clientes/navar/documentos/manual_cash.md`**.
3. Thomas no programa: consultarle antes de cambios grandes y dejar todo comentado en criollo
   (qué hace y por qué, no cómo).
4. **Sin nombres propios** de gente de NAVAR en la solapa Instrucciones de la Sheet ni en los PDF:
   usar roles (administración, la dirección, el estudio, finauto).
5. No trabajar sobre los mismos archivos que otro agente al mismo tiempo (Claude Code y Codex se
   pisan si editan la misma rama a la vez): uno a la vez.
6. Nada de lo que está en `clientes/*/privado/` sube a git (está en `.gitignore`); ahí viven los datos reales.
