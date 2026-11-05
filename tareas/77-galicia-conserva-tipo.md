# Tarea 77 — Galicia: las filas guardadas conservan su tipo
Estado: lista para revisión
Rama: tarea/77-galicia-conserva-tipo
Hecha por Claude, por ser un cambio de pocas líneas con urgencia antes de la corrida programada.

## Objetivo
Al rearmar `galicia_movimientos.csv`, las filas ya guardadas se recalculaban con la regla por palabras y perdían un tipo
revisado a mano. Ahora la regla clasifica solo lo nuevo del Excel. Además, "Ing. Brutos" abreviado cuenta como impuesto.

## Comprobaciones
- Prueba nueva: una fila más vieja que la ventana del banco sigue igual después de dos corridas, con su tipo y su saldo.
- Prueba nueva: "Ing. Brutos" abreviado da impuesto.
- `unittest discover -s tests` completo.
