# Para cuando te levantes, Thomas 👋

Resumen de lo que hice de noche en finauto, las decisiones que tomé, y las dudas
que necesito que me respondas para seguir. (Lo mismo te dejé en el chat.)

## ✅ Lo que quedó hecho

1. **Monorepo `finauto` armado** en `C:\finauto` (carpeta NUEVA y aparte; no toqué
   nada de producción: ni los bots viejos ni el repo MAGA).
2. **El núcleo (motor) extraído** de los dos bots a `nucleo/` — una sola vez, ya no
   duplicado. Incluye recorrido, fechas, estado, credenciales, log, salidas a Drive.
3. **Galicia refactorizado 1:1** como adaptador (`bots/galicia/`). Misma lógica y
   selectores del bot que funciona; solo movido a la estructura nueva.
4. **Comafi** portado como andamiaje (`bots/comafi/`, con los `# >>> TODO COMAFI`).
5. **Santander** como esqueleto (`bots/santander/`) para mostrar lo poco que falta
   para sumar un banco.
6. **Config por cliente**: todo lo de MAGA salió a `clientes/maga/perfil.json`.
7. **Orquestador** (`orquestador/correr.py`) + `setup_credenciales.py`.
8. **Dashboard visual nuevo** (blanco/verde/naranja de farmacia) — te lo dejé como
   página aparte (link en el chat) y una copia en `dashboard/`.
9. Documentado todo (README, CLAUDE.md, docs/) y verificado que el código **compila
   sin errores de sintaxis**.

## ⚠️ Lo IMPORTANTE que NO hice (a propósito)

- **No corrí el bot nuevo contra el banco.** El refactor de Galicia es fiel, pero
  cambiar de estructura puede dejar algún detalle de import/ruta que solo se ve al
  correrlo. Antes de reemplazar el bot viejo hay que hacer **una corrida de prueba**.
  No la hice solo porque toca el banco real y tus credenciales. → lo hacemos juntos.
- **No pusheé finauto a GitHub**: no existe todavía el repo `finauto` (el que creaste
  es `MAGA`). Está todo committeado localmente, listo para subir.
- **No toqué el schedule de las 8:00** (sigue corriendo el bot viejo de Galicia, intacto).

## 🤔 Decisiones que tomé (decime si cambiás alguna)

- Nombre de trabajo: **finauto** (como dijiste).
- Runtime y credenciales van en `clientes/<cliente>/.run/` y `.credenciales/`
  (fuera de git). Así cada cliente/banco tiene lo suyo separado.
- El dashboard usa **datos de ejemplo** (como el que me mostraste). Es un mockup de
  diseño, todavía no conectado a datos reales.

## ❓ Dudas para vos (para arrancar mañana)

1. **¿Creo el repo `finauto` en GitHub y lo subo?** Puedo hacerlo con tu sesión ya
   guardada; solo decime si querés que lo cree yo o lo creás vos y me pasás la URL.
2. **¿Probamos el bot nuevo?** (cargar credenciales en finauto + corrida en modo
   prueba de Galicia). Es el paso que valida todo el refactor.
3. **¿Con qué pieza sigo?** Mi recomendación: **el simulador de retiro / dashboard**
   (es lo más vendible y visible), después el clasificador. Pero vos decidís.
4. **El dashboard visual**: ¿te gusta la dirección (colores, tamaño de números,
   textos)? Decime qué ajusto.
5. Una vez probado el bot nuevo, ¿**migramos la tarea de las 8:00** a finauto, o
   dejamos el viejo hasta estar 100% seguros? (yo dejaría los dos un tiempo).

## Cómo probar el bot nuevo (cuando quieras)

```
cd C:\finauto
pip install -r requirements.txt
python -m playwright install chromium
python setup_credenciales.py --cliente maga --banco galicia
python orquestador/correr.py --cliente maga --banco galicia --modo prueba
```
(en modo prueba se ve el navegador; mirá las capturas en clientes/maga/.run/galicia/capturas/)
