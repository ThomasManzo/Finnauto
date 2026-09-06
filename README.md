# finauto

**Sistema de automatización financiera para farmacias y comercios PYME.**
De la descarga automática de extractos bancarios a la decisión de dirección, en
un solo producto. Nombre de trabajo: `finauto` (comercial a definir).

> Este es el **producto nuevo y unificado**. El sistema productivo actual de MAGA+
> vive aparte, en el repo `MAGA` (respaldo del código que hoy corre).

## Qué hace (visión — 6 piezas)

1. **Descarga de extractos** — bots que entran al banco y bajan los extractos. ← *lo que está armado acá hoy*
2. **Clasificación al Cash** — ordena y carga cada movimiento.
3. **Cobranzas** — concilia las cobranzas.
4. **Disponibilidad** — cuánto se puede retirar (con simulador).
5. **Dashboard en vivo** — la foto financiera.
6. **Análisis EERR** — lectura de gestión.

## Lo que ya está en este repo (Fase 1 — el núcleo + los bots)

```
finauto/
├─ nucleo/            EL MOTOR compartido (no depende de ningún banco)
│   ├─ loop.py        el recorrido genérico (login → por empresa → descarga → Drive)
│   ├─ contexto.py    junta rutas + settings de una corrida
│   ├─ config.py      lee el perfil del cliente
│   ├─ credenciales.py  DPAPI (encriptadas por cliente/banco)
│   ├─ estado.py      anti-duplicado (hasta qué día bajó cada empresa)
│   ├─ fechas.py      la regla ayer+hoy / backfill
│   ├─ navegador.py   abre Chromium (Playwright)
│   ├─ salidas.py     _ESTADO_/_SALDOS_ a Drive
│   ├─ log.py         log + capturas
│   └─ utilidades.py  helpers (_norm, _parse_monto, ...)
├─ bots/             ADAPTADORES por banco (solo login + selectores)
│   ├─ base.py        el contrato (BotBanco)
│   ├─ galicia/       ✅ portado 1:1 del bot que funciona
│   ├─ comafi/        🟡 andamiaje (TODO COMAFI en los selectores)
│   └─ santander/     ⬜ esqueleto (no empezado)
├─ clientes/
│   └─ maga/perfil.json   todo lo específico de MAGA (Drive, filtros, prefijos)
├─ orquestador/correr.py  punto de entrada (CLI)
├─ setup_credenciales.py  carga credenciales encriptadas
└─ docs/            arquitectura + dudas + notas
```

**La idea central:** el motor de los bots, que hoy estaba **copiado** en cada bot,
ahora vive **una sola vez** en `nucleo/`. Cada banco es un adaptador chico que solo
implementa login + selectores. Y todo lo de MAGA (carpetas, empresas, prefijos) salió
a `clientes/maga/perfil.json` → sumar otra farmacia es agregar otro perfil, no tocar código.

## Cómo se corre

```
pip install -r requirements.txt
python -m playwright install chromium
python setup_credenciales.py --cliente maga --banco galicia
python orquestador/correr.py --cliente maga --banco galicia --modo prueba
```

- `--modo prueba` = navegador visible (para depurar) · `--modo produccion` = invisible.
- `--todos` corre todos los bancos activos del perfil.

## Estado

⚠️ **El refactor de Galicia se portó 1:1 del bot probado, pero todavía NO se corrió
contra el banco desde esta estructura nueva.** Antes de reemplazar producción hay
que hacer una corrida de prueba. Ver `docs/MANANA_THOMAS.md`.

## Cómo se corre

Un solo comando arma todo el material de una visita:

```bash
python finauto.py --contrato datos/CONTRATO_maga_2026-09-05.json
```

Controla el dato, lo contrasta contra los números del propio cliente, arma el
tablero y el informe, y guarda la foto de hoy en la memoria.

**Lo último no es un extra.** Es lo único que hace que la segunda visita valga
más que la primera — y la foto de hoy solo se puede sacar hoy.

### Las herramientas por separado

```bash
python dashboard/app.py       --contrato c.json    # el tablero
python dashboard/generar.py   --contrato c.json    # el informe de una página
python simulador/proveedores.py   --contrato c.json --cliente maga
python simulador/disponibilidad.py --contrato c.json --retiro 150000000
python simulador/posicion.py  --contrato c.json
python simulador/proyeccion.py --contrato c.json
python auditoria/contraste.py --contrato c.json
python auditoria/revisar.py   --contrato c.json
```
