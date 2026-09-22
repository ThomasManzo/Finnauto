# tareas/ — cómo trabajan juntos Claude Code (cerebro) y Codex (ejecutor)

Decisión de Thomas (22/09/2026): las ideas y las decisiones se toman con Claude Code; el código de
las tareas aisladas lo escribe Codex. Los dos se hablan **por archivos en este repo**, no por chats.

## El circuito

1. **Claude escribe la consigna** en `tareas/<nn>-<nombre>.md` (plantilla abajo) y la commitea en `main`.
2. **Thomas le dice a Codex**: "hacé la tarea `tareas/<nn>-<nombre>.md`".
3. **Codex la ejecuta en un worktree propio**, rama `tarea/<nombre>`. No toca `main` directo.
   Commitea en su rama y, al terminar, completa la sección **"Qué hice"** de la consigna
   (qué archivos tocó, cómo lo probó, qué dudas le quedaron) y cambia `Estado:` a `para revisar`.
4. **Claude revisa el diff** (`git diff main..tarea/<nombre>`), anota en **"Revisión"** y, con el OK
   de Thomas, se mergea a `main`. Si hay que corregir, `Estado:` vuelve a `en curso` con las notas.

## Reglas para el ejecutor

- Leer `AGENTS.md` → `CLAUDE.md` antes de arrancar. Si la tarea es de NAVAR, también `clientes/navar/LEEME.md`.
- **Solo tocar lo que la consigna dice.** Si hace falta tocar otra cosa, se anota en "Qué hice" y se pregunta; no se hace.
- Comentarios en criollo explicando qué hace y por qué (Thomas no programa).
- Sin nombres propios de gente de NAVAR en nada que vea el cliente (Instrucciones, PDF, mails).
- **No usar `clientes/*/privado/`** ni datos reales: los worktrees no los tienen y no deben tenerlos.
  Si una prueba necesita datos, se arma un ejemplo chico e inventado dentro de la tarea.
- No instalar dependencias nuevas sin anotarlo en "Qué hice".

## Plantilla de consigna

```
# Tarea <nn> — <nombre corto>
Estado: pendiente | en curso | para revisar | mergeada
Rama: tarea/<nombre>

## Qué hay que hacer
(en criollo: el resultado que se espera, no el cómo)

## Por qué
(para qué sirve; qué problema resuelve)

## Archivos que toca
(lista; lo que no está acá no se toca)

## Cómo se prueba
(comando o pasos que tienen que salir bien)

## Listo cuando
(criterios concretos, verificables)

## Qué hice          ← lo completa Codex
## Revisión          ← lo completa Claude
```
