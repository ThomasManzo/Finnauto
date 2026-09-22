# tareas/ — cómo trabajan juntos Claude Code (cerebro) y Codex (ejecutor)

Decisión de Thomas (22/09/2026): las ideas y las decisiones se toman con Claude Code; el código de
las tareas aisladas lo escribe Codex. Los dos se hablan **por archivos en este repo**, no por chats.

## El circuito

1. **Claude escribe la consigna** en `tareas/<nn>-<nombre>.md` (plantilla abajo) y la commitea en `main`.
2. **Thomas le dice a Codex**: "hacé la tarea `tareas/<nn>-<nombre>.md`".
3. **Codex la ejecuta en un worktree propio**, rama `tarea/<nombre>`. No toca `main` directo.
   Commitea en su rama (si el sandbox no lo deja —pasó en la tarea 01: el índice de git del worktree vive en
   `Finnauto/.git/worktrees/` y Codex no llega—, lo anota en "Qué hice" y Claude commitea por él) y, al terminar, completa la sección **"Qué hice"** de la consigna
   (qué archivos tocó, cómo lo probó, qué dudas le quedaron) y cambia `Estado:` a `lista para revisión`.
4. **Claude revisa el diff** (`git diff main..tarea/<nombre>`), anota en **"Revisión"** y, con el OK
   de Thomas, se mergea a `main`. Si hay que corregir, `Estado:` vuelve a `en curso` con las notas; al mergear pasa a `aprobada`.

## Reglas para el ejecutor

- Leer `AGENTS.md` → `CLAUDE.md` antes de arrancar. Si la tarea es de NAVAR, también `clientes/navar/LEEME.md`.
- **Solo tocar lo que la consigna dice.** Si hace falta tocar otra cosa, se anota en "Qué hice" y se pregunta; no se hace.
- Comentarios en criollo explicando qué hace y por qué (Thomas no programa).
- Sin nombres propios de gente de NAVAR en nada que vea el cliente (Instrucciones, PDF, mails).
- **No usar `clientes/*/privado/`** ni datos reales: los worktrees no los tienen y no deben tenerlos.
  Si una prueba necesita datos, se arma un ejemplo chico e inventado dentro de la tarea.
- No instalar dependencias nuevas sin anotarlo en "Qué hice".

## Plantilla de consigna (secciones fijas; Codex sigue exactamente esta estructura)

```
# Tarea <nn> — <nombre corto>
Estado: pendiente | en curso | lista para revisión | aprobada
Rama: tarea/<nombre>

## Objetivo
(en criollo: el resultado que se espera, no el cómo)

## Contexto
(qué existe hoy, por qué hace falta, qué decisiones ya están tomadas)

## Archivos permitidos
(lista exacta; lo que no está acá no se toca. Si hace falta tocar otro, se anota en "Qué hice" y se pregunta)

## Resultado esperado
(qué tiene que existir al terminar: archivos, funciones, textos)

## Comprobaciones
(comandos o pasos que tienen que salir bien; qué se pudo probar y qué no)

## Qué hice          ← lo completa Codex (archivos tocados, cómo lo probó, dudas)
## Revisión          ← lo completa Claude (qué verificó, qué corregir)
```

Los estados: **pendiente** (consigna escrita) → **en curso** (Codex trabajando) → **lista para revisión**
(Codex terminó y completó "Qué hice") → **aprobada** (Claude revisó, Thomas dio el OK, mergeada a main).
