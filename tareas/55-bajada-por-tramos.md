# Tarea 55 — La bajada de Tango por tramos de fechas (las páginas de Live vienen desordenadas)
Estado: escrita por Claude, falta el OK de Thomas para mergear
Rama: tarea/55-bajada-por-tramos

## Qué pasó

El 07/10/2026 el cruce semanal salió con más de cien movimientos "para cargar en Tango" que sí
estaban cargados. La causa estaba en la bajada del detalle de tesorería de A:

- La tarea 48 subió ese detalle de 120 a 180 días. Así pasó los 5000 renglones, que es una página
  de Live.
- Live no devuelve las páginas en un orden fijo. La página 2 repitió 829 renglones de la página 1 y
  se perdieron otros tantos, casi todos de septiembre.
- El total igual cerraba con totalCount, así que ningún control lo frenó.

"A movimientos tesoreria" está cerca de las 5000 (400 días), así que le iba a pasar lo mismo.

## Archivos permitidos

`ingestas/tango_live.py`, `ingestas/test_tango_live.py`, `lector/cruce.py`, esta consigna.

## Resultado esperado

- Si una consulta **con fecha desde** no entra en una página, la bajada parte el rango de fechas en
  dos, y así sucesivamente, hasta que cada tramo entre en UNA página. No pasa páginas.
  - El último tramo queda sin fecha hasta, para no perder renglones con fecha futura.
  - Al final, la suma de los tramos tiene que dar el totalCount del rango entero, o no se escribe
    el archivo.
- Las consultas **sin fechas** (las de AA, con toda la historia) y un día que solo no entra en una
  página siguen pasando páginas, pero si aparece un renglón repetido la bajada falla en lugar de
  escribir un archivo con huecos.
- `lector/cruce.py`: si el detalle trae renglones repetidos enteros, el cruce se frena ("volver a
  bajarlo") y no manda el mail con números falsos.

## Comprobaciones

- Pruebas con una Live inventada que desordena las páginas:
  - por tramos baja todo sin pedir la página 2;
  - sin fechas, se frena;
  - un solo día grande pasa páginas;
  - el cruce no corre con repetidos.
- Todas las pruebas de `lector/pruebas` e `ingestas` pasan.
- Contra el archivo real del 07/10, el cruce se frena por los 829 repetidos.

## Para instalar (lo corre Thomas en la notebook, de a uno)

1. `actualizar.ps1`.
2. Volver a bajar Tango (`ingestas/tango_live.py --cliente navar`). En el log, el detalle de A tiene
   que tener más renglones que hoy y ninguna falla.
3. Volver a correr el cruce semanal y mirar que septiembre vuelva a conciliar como antes.
