# Tarea 26 — Galicia NAVAR: que corra solo todas las mañanas
Estado: pendiente
Rama: tarea/galicia-tarea-diaria

## Objetivo

Un instalador de la tarea programada de Galicia en la notebook, **igual al de Tango**, para que el bot
baje el extracto solo cada mañana a las 07:00 y deje su salida en un log.

## Contexto

Leer antes: `AGENTS.md`, `tareas/LEEME.md`, `clientes/navar/herramientas/instalar_tango.ps1` (el
modelo a copiar), `clientes/navar/documentos/instalar_notebook.md` §6 y `nucleo/contexto.py`
(cómo se decide si el navegador se ve).

**Galicia anduvo de punta a punta el 28/09/2026 a las 00:27** con `--modo prueba` (navegador
visible): login, empresa, cuenta, saldos, descarga Excel, validación y publicación en
`Bancos/galicia`. El Excel publicado coincide movimiento por movimiento con un export a mano.

**Todavía no se probó con el navegador invisible** (`--modo produccion`). Los bancos a veces
detectan el navegador invisible y se comportan distinto. Como la tarea corre con la sesión de
Windows iniciada (hace falta para el llavero y para Drive), se decidió que **arranque con navegador
visible**. En `nucleo/contexto.py`, `modo_visible` sale del perfil
(`bancos.<banco>.modo_visible`) cuando no se pasa `--modo`, así que no hace falta tocar código.

## Archivos permitidos

- `clientes/navar/herramientas/instalar_galicia.ps1` (nuevo)
- `clientes/navar/perfil.json` — **solo** `bancos.galicia` (agregar `modo_visible`)
- `clientes/navar/documentos/instalar_notebook.md` — **solo** el punto 5 de la §6 y la tabla
  "Qué queda corriendo, en orden, cada mañana"
- `tareas/26-galicia-tarea-diaria.md`

## Resultado esperado

1. `instalar_galicia.ps1`, copiado de `instalar_tango.ps1` con estas diferencias:
   - Tarea **`finauto NAVAR Galicia`**, diaria a las **07:00**.
   - Corre `orquestador\correr.py --cliente navar --banco galicia` **sin `--modo`** (manda el perfil).
   - Log: `clientes\navar\privado\galicia.log`, con stdout y stderr agregados al final, igual que Tango.
   - Mismo `-StartWhenAvailable`, `-MultipleInstances IgnoreNew` y límite de 1 hora.
   - Mismo parámetro `quitar`. Comentarios de cabecera en criollo: qué hace, cómo se instala y quita,
     y que las claves se leen del llavero y nunca van ni a la tarea ni al log.
2. Perfil: `bancos.galicia.modo_visible: true`, con un `_nota` breve: se deja visible hasta probar
   el modo invisible; para pasarlo a invisible alcanza con ponerlo en `false`.
3. §6 punto 5: reemplazar los pasos a mano del Programador de tareas por el comando del instalador
   (`powershell -ExecutionPolicy Bypass -File clientes\navar\herramientas\instalar_galicia.ps1`, desde
   `C:\finauto`), cómo probarlo con "Ejecutar" en el Programador y dónde mirar el log. Aclarar que la
   notebook tiene que estar prendida con la sesión iniciada y que el navegador se va a abrir solo a
   las 07:00. Tabla de la mañana: 07:00 Galicia → `Bancos\galicia\`, log `privado\galicia.log`.

## Comprobaciones

1. JSON válido de `perfil.json`.
2. Revisar el `.ps1` contra `instalar_tango.ps1`: diferencias solo en nombre, hora, comando, log y
   descripción. No se puede correr PowerShell acá; decirlo en "Qué hice".
3. Commit en la rama.

## Qué hice

## Revisión
