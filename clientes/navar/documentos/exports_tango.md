# Exports de Tango Live: qué bajar, cómo se llama, dónde va

Cuatro consultas, dos empresas (A = NAVAR SA, AA = NAVAR SA Otros). Cada archivo es la foto
completa del día. Se bajan como Excel (Exportar → Excel), se nombran así y se dejan en su carpeta
de `NAVAR - Datos`. Las columnas son las que trae la consulta por defecto: no hay que agregar ni
sacar ninguna; el lector las busca por nombre (mayúsculas y acentos no importan).

| # | Consulta | Ruta en Tango Live | Filtro | Columnas que tiene que traer | Nombre del archivo | Carpeta |
|---|---|---|---|---|---|---|
| 1 | Composición de saldos de clientes | Ventas → Cuentas corrientes → Composición de saldos | pendientes (saldo ≠ 0) | Cód. cliente · Razón social · Tipo comprobante · Nro. comprobante · Fecha de emisión · **Fecha de vencimiento** · Importe al Vencimiento · **Importe Pendiente** · Descripción condición de venta | `A cobranzas AAAA-MM-DD.xlsx` · `AA cobranzas AAAA-MM-DD.xlsx` | `Cuentas a cobrar` |
| 2 | Composición de saldos de proveedores | Compras → Cuentas corrientes → Composición de saldos | pendientes (saldo ≠ 0) | Cód. proveedor · Razón social · Tipo de comprobante · Nro. comprobante · Fecha de emisión · **Fecha de vencimiento** · Total al vencimiento · **Total pendiente** | `A pagos AAAA-MM-DD.xlsx` · `AA pagos AAAA-MM-DD.xlsx` | `Cuentas a pagar` |
| 3 | Cheques de terceros | Tesorería → Cheques → Cheques de terceros (cartera) | todos los estados (el lector se queda con "En cartera") | Nro. de cheque · Nombre de banco · Cód. cliente · CUIT del cheque · Razón social · Fecha de emisión · **Fecha del cheque** (cobro) · Fecha de origen · **Estado** · Desc. subestado · **Importe** · Cuenta cartera · Tipo de cheque | `A cheques terceros AAAA-MM-DD.xlsx` · `AA cheques terceros AAAA-MM-DD.xlsx` | `Cheques` |
| 4 | Cheques propios | Tesorería → Cheques → Cheques propios | emitidos, no pagados (si se puede filtrar; si no, todos) | Nro. de cheque · Nombre de banco · Cód. proveedor · Razón social · Fecha de emisión · **Fecha del cheque** (pago) · **Importe mon. cta.** · **Estado** · Nro. comp. emisión · Tipo de cheque | `A cheques propios AAAA-MM-DD.xlsx` | `Cheques` |

Las columnas en negrita son las que el cash usa para proyectar (cuándo y cuánto). Si una consulta
no trae alguna, el lector avisa en `resumen_tango_<fecha>.md` y la fila queda marcada REVISAR.

Reglas:
- **El nombre importa**: primera palabra = empresa (A / AA), después qué es (cobranzas / pagos /
  cheques terceros / cheques propios), después la fecha AAAA-MM-DD.
- Un archivo por día y por empresa. Los viejos no se borran: son la historia.
- No hace falta avisar ni apretar nada: a los 15 min corre el lector, a la hora la Sheet importa,
  y en la solapa **Registro** queda anotado qué entró.
- Si un día falta un archivo (ej. AA pagos), la Sheet sigue con el último que hubo de esa lista.
