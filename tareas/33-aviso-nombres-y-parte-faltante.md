# Tarea 33 — Aviso: nombres de banco prolijos y sin avisar dos veces el mismo faltante
Estado: lista para revisión
Rama: tarea/aviso-detalles

## Objetivo

Dos detalles que se vieron al probar la tarea 32 con datos reales (29/09/2026, ver su Revisión):

1. Los bancos salen como vienen en Saldos Bancarios: `GALICIA`, `NACION`, `CORRIENTES`, `MACRO`,
   `BBVA`. Tienen que decir **Galicia, Nación, Corrientes, Macro, BBVA**.
2. Si el bot de un banco automático no corre, no existe su `_ESTADO_<Banco>_dd-mm.txt` y el mail lo dice
   **dos veces**: en ❌ ("el bot no corrió hoy · revisar la notebook") y en ⚠️ ("No se pudo leer
   GaliciaParte: Falta _ESTADO_…"). Tiene que salir **solo en ❌**.

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `tareas/32-aviso-checklist.md` (con la Revisión),
`clientes/navar/herramientas/aviso_diario.gs` (`_leerDatosAviso_`, `_armarAviso_`) y
`lector/pruebas/probar_aviso_bajadas.cjs`.

La clave del banco para comparar con `FUENTES_AUTOMATICAS` y armar rutas es la minúscula sin tilde
(`galicia`, `nacion`); eso **no cambia**. Solo cambia cómo se **muestra**.

## Archivos permitidos

- `clientes/navar/herramientas/aviso_diario.gs`
- `lector/pruebas/probar_aviso_bajadas.cjs`
- `tareas/33-aviso-nombres-y-parte-faltante.md`

## Resultado esperado

1. Una función chica que da el nombre a mostrar: un mapa conocido (`galicia` → Galicia, `nacion` →
   Nación, `corrientes` → Corrientes, `macro` → Macro, `bbva` → BBVA) y, para uno desconocido, la
   primera letra en mayúscula y el resto en minúscula. Se usa en las líneas de bancos del mail.
2. Cuando el `_ESTADO_` de hoy de un banco automático **no existe**, eso no es un error de lectura: no
   se agrega a `errores` (o se excluye de ⚠️) y el mail muestra solo el ❌ que ya existe. Si en cambio
   el archivo existe pero no se puede leer, o hay dos, o la cabecera no corresponde al banco, **sí** va
   a ⚠️, como hoy.
3. No tocar horarios, instaladores ni `DESTINATARIOS`.
4. Tests nuevos:
   - nombres: `GALICIA` → "Galicia", `NACION` → "Nación", uno desconocido `ITAU` → "Itau";
   - parte faltante: aparece una sola vez (en ❌) y el asunto cuenta 1 faltante por eso;
   - parte duplicado: sigue yendo a ⚠️.

## Comprobaciones

1. `node lector/pruebas/probar_aviso_bajadas.cjs` OK (en la Mac de Thomas no hay Node: dejar el
   resultado en "Qué hice").
2. `grep` de nombres propios de personas vacío en lo agregado. Commit en la rama.
3. Claude lo pega en Apps Script y lo prueba con "Ver el aviso de hoy (sin mandar)".

## Qué hice

- Agregué _nombreBancoAviso_: mapa para los cinco bancos conocidos y primera letra mayúscula
  para desconocidos. Lo usan las líneas automáticas y manuales; claves y rutas no cambiaron.
- Si no existe el estado del día, la lectura termina sin agregar error y la checklist conserva
  su único faltante. Duplicados, falta de acceso y cabecera incorrecta siguen siendo errores.
- Pruebas OK con Node del runtime local: los 20 casos anteriores, nombres conocidos y desconocidos,
  nombres en el cuerpo y lectura con dobles de Drive para parte ausente, duplicado, ilegible y ajeno.
  El caso ausente verifica asunto con un faltante y ausencia de REVISAR.
- git diff --check y búsqueda de nombres propios en lo agregado: limpios. Confirmé que los
  destinatarios y las funciones de horarios están intactos.
- No accedí a Google ni envié correos. Pendiente: pegar en Apps Script y probar con
  «Ver el aviso de hoy (sin mandar)».

## Revisión
