# Tarea 61 — El importador busca los archivos rápido y no se corta por un tropiezo de Drive
Estado: aprobada (falta pegarla en Apps Script)
Rama: tarea/61-importador-rapido

## Objetivo
Que la revisión de cada hora de la Sheet ("importarLoNuevo") tarde segundos y no minutos, y que un
tropiezo momentáneo de Drive no frene toda la vuelta.

## Contexto
- Cada hora, para cada tipo de archivo (deuda, impuestos, bancos, cajas, Tango, últimos pagos),
  `_ultimoConPrefijo_` recorría **todo** el árbol de carpetas de datos del cliente, archivo por archivo.
  Con cientos de archivos eso son miles de consultas a Drive por hora.
- Consecuencias:
  - cada revisión tardaba de 1 a 6 minutos aunque no hubiera nada nuevo;
  - a veces Google la cortaba a los 6 minutos ("En tiempo de espera");
  - de vez en cuando Drive devolvía "Error de servicio: Drive", y como la búsqueda estaba fuera del
    `try`, se cortaba la vuelta entera.
- El riesgo: un corte por tiempo justo mientras se carga una lista la deja a medio cargar hasta la
  hora siguiente.

## Qué hay que hacer
1. Buscar el archivo con el buscador de Drive por nombre (una consulta), en vez de recorrer carpetas.
   Quedarse con el más nuevo que empiece con el prefijo y esté adentro de la carpeta raíz del cliente.
   Si el buscador no trae nada que sirva, recorrer el árbol como antes, de respaldo.
2. En `importarLoNuevo`: si buscar un tipo falla, reintentar una vez y, si sigue fallando, seguir
   con los demás tipos. Al final avisar con un error claro, así la ejecución queda "Fallida" y se ve.
3. Prueba con un Drive inventado.

## Qué hice
**La escribió Claude** (Thomas: "hacé la 61 y todo vos").

- `clientes/navar/herramientas/importar_cashflow.gs`:
  - `_ultimoConPrefijo_` usa `DriveApp.searchFiles("title contains '<prefijo>' and trashed = false")`.
    Filtra los nombres que empiezan con el prefijo, porque el buscador es laxo. Ordena del más nuevo
    al más viejo y devuelve el primero que está dentro de la raíz.
  - Para saber si un archivo está dentro de la raíz, `_dentroDeLaRaiz_` sube por las carpetas padre
    y recuerda las ya vistas.
  - Si no hay candidatos válidos, usa `_ultimoConPrefijoRecorriendo_`, que es el código viejo, intacto.
  - `importarLoNuevo`:
    - cada búsqueda va dentro de un `try`, con un reintento a los 3 segundos (`_conUnReintento_`);
    - los tipos que no se pudieron revisar se juntan, y el error se tira al final, después de
      importar los demás y de la copia para el tablero;
    - no se escribe en el Registro, para que un tropiezo que se arregla solo en una hora no lo ensucie.
  - `probarBusquedaRapida()`: para correr a mano desde el editor. Compara, para cada tipo, la búsqueda
    nueva contra el recorrido viejo (archivo elegido y milisegundos). No importa nada.
- `lector/pruebas/probar_importador_busqueda.cjs`, prueba nueva con un Drive de juguete. Comprueba que:
  - elige el más nuevo de adentro y descarta uno más nuevo de afuera y una "copia de ...";
  - encuentra en subcarpetas profundas sin recorrer carpetas;
  - si el buscador no trae nada, recorre como antes;
  - un tropiezo de un momento se salva con el reintento;
  - un tropiezo que sigue deja sin revisar solo ese tipo, los demás entran y el aviso sale al final.

  Contra el código viejo, la prueba falla; con el nuevo, pasa. Las 11 pruebas `.cjs` pasan.
- No se tocó: `aviso_diario.gs`. También recorre el árbol, pero una vez por día y tarda menos de un
  minuto.

## Revisión
- Pendiente:
  - pegar en Apps Script (Importar_cashflow.gs) y verificar la huella contra `main`;
  - correr `probarBusquedaRapida` y confirmar "IGUAL" en todos los tipos;
  - mirar que las revisiones siguientes duren segundos.
