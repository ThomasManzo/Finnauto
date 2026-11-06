# Tarea 84 — "A cobrar": la lista de cada empresa
Estado: aprobada
Rama: tarea/tablero-cobrar-empresa

## Objetivo
En "A cobrar", la lista "Quién nos debe" salía siempre del consolidado. Ahora cada vista muestra lo suyo: A, AA y el consolidado con las dos juntas.

## Qué hice
Hecha por Claude por ser un arreglo de una línea en `dashboard/app.py`: la lista usa los datos de la vista elegida, los mismos de los indicadores de arriba. Se
sacó la rama "separadas", que ya no se usa. `lector/pruebas/test_buscador_cobrar.py` actualizada.

## Revisión
Con el tablero publicado: en las tres vistas la lista suma lo mismo que sus indicadores, y consolidado = A + AA por cliente (números fuera del repo).
