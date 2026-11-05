# Tarea 79 — Galicia programado: no leer Descargas, límite de tiempo y fuente en rojo si el bot falla
Estado: lista para revisión
Rama: tarea/79-galicia-sin-descargas-usuario
Hecha por Claude, por urgencia: la corrida programada falló y hay otra a la vista.

## Qué pasó (cliente de ejemplo)
La corrida programada entró al banco y quedó una hora trabada al leer `~/Downloads`, hasta un error del sistema
(`Interrupted system call`). `control.json` igual decía OK, porque el rearmado usaba lo bajado antes.

## Qué cambia
- `BotGaliciaUnaEmpresa` no mira la carpeta Descargas del usuario. `BotGaliciaNavar` sigue igual.
- `limite_segundos` en el bloque del banco del perfil: si la corrida lo pasa, deja el fallo en el estado del día y termina.
  Sin esa clave no cambia nada, así que NAVAR no se entera.
- `galicia_datos.leer`: si el estado de hoy del bot no dice OK, la fuente queda en rojo. El CSV se sigue rearmando.
- `mp_saldo`: un pedido que Mercado Pago aceptó y no generó se puede repetir a las 2 horas, no recién al día siguiente.

## Comprobaciones
`unittest discover -s tests` y `bots/galicia/test_navar.py`. Corrida real en condiciones de launchd: la hace Claude.
