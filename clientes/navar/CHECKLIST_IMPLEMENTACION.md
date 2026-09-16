# NAVAR — checklist de implementación (semana del 16 al 22/09/2026)

> Para no perderse. Cada paso dice **qué**, **cómo**, **para qué** y **cuándo está listo**.
> Marcá con `[x]` a medida que avanzás, y **anotá cuánto tardó cada paso** en la
> columna de tiempo: con el cliente 2 esto se convierte en el checklist estándar.
>
> Quién hace qué: **T** = Thomas · **C** = Claude · **N** = alguien de NAVAR.

---

## Día 1 · Martes 16 — papeles y acceso

### [ ] 1.1 Mail de confirmación del alcance — T — ⏱ ___
- **Qué:** un mail a Priscilla con: alcance (planilla nueva + tablero + lectura semanal durante 6 semanas), precio ($1.400.000 implementación + USD 400/mes desde el mes 2, revisable a los 3 meses), forma de pago (50% ahora, 50% a la cuarta lectura), criterio de éxito a las 6 semanas, y la línea *"acceso de consulta a Tango: no registro ni modifico nada en el sistema de gestión"*.
- **Cómo:** pedirle que responda "de acuerdo". Un mail aceptado vale como firma.
- **Para qué:** que no haya dos versiones de lo acordado.
- **Listo cuando:** llega el "de acuerdo".

### [ ] 1.2 Factura del 50% — T — ⏱ ___
- **Qué:** factura C por $700.000 desde "Comprobantes en línea" de ARCA, a NAVAR S.A. (pedir CUIT y condición de IVA).
- **Cómo:** ARCA → Comprobantes en línea → punto de venta → Factura C. Concepto: "Implementación sistema de flujo de fondos — 50%".
- **Para qué:** el pago adelantado es el filtro de compromiso: quien no adelanta, tampoco manda los datos a tiempo.
- **Listo cuando:** factura enviada por mail junto con el 1.1.

### [ ] 1.3 Acceso a la notebook — N → T — ⏱ ___
- **Qué:** ID y clave de acceso desatendido de AnyDesk (o el link de Chrome Remote Desktop), usuario de Windows propio, usuario de Tango de solo consulta.
- **Cómo:** que te lo manden por WhatsApp a vos, no al mail general. Guardar la clave en el llavero de la Mac (Contraseñas), no en una nota.
- **Para qué:** entrar sin que nadie tenga que aceptar del otro lado.
- **Listo cuando:** entrás y ves el escritorio del Windows.

### [ ] 1.4 Instalar AnyDesk en la Mac — T — ⏱ ___
- **Cómo:** anydesk.com → Descargar para macOS → abrir el .dmg → arrastrar a Aplicaciones. La primera vez macOS pide permisos de "Grabación de pantalla" y "Accesibilidad" en Ajustes → Privacidad y seguridad: darlos, si no se ve la pantalla remota en negro.
- **Para qué:** es la ventana a la notebook de ellos.
- **Ojo:** dentro de la sesión remota, el Windows espera Ctrl donde vos usás Cmd (Ctrl+C / Ctrl+V).

### [ ] 1.5 Carpeta de Drive — C ✅ hecha
- `NAVAR - Datos / Tango`. Crear adentro una subcarpeta por fecha (`2026-09-17`) cada vez que se suban archivos.

### [ ] 1.6 Pedidos por WhatsApp — T — ⏱ ___
- **Al contador:** deuda ARCA por impuesto y período, planes vigentes, intimaciones; Ingresos Brutos Corrientes. (Texto ya escrito en la charla del 15/09.)
- **A Priscilla:** los dos CUIT, stock de yerba en kilos y valuación, margen bruto aproximado de la molida. Y la pregunta: *"¿María Rosa está al tanto de los números o le paso solo el avance?"*.
- **Para qué:** los CUIT alcanzan para consultar el BCRA hoy mismo; stock y margen contestan si el plan de deuda es de reestructuración o de supervivencia.

---

## Día 2 · Miércoles 17 — la primera conexión (avisar a C antes de entrar)

### [ ] 2.1 Reconocimiento de Tango — T — ⏱ ___
- **Qué mirar y anotar:** versión de Tango (Ayuda → Acerca de), empresas disponibles al entrar (A y AA: cómo se llaman de verdad), módulos que aparecen (Ventas, Compras, Tesorería, Contabilidad, Sueldos, Stock), si existe **Tango Live** (ícono aparte o dentro de cada módulo), y el nombre del usuario con el que entraste.
- **Cómo:** capturas de pantalla (Windows: tecla `Impr Pant` o `Win+Shift+S`) guardadas en el escritorio y subidas a Drive después.
- **Para qué:** el script de carga se escribe contra la versión y los reportes reales, no contra un supuesto.

### [ ] 2.2 Los exports (por empresa: A y AA) — T — ⏱ ___
Desde Tango Live (o el informe equivalente del módulo). En cada consulta: botón **Exportar → Excel**. Nombrar cada archivo `<empresa>_<listado>_<fecha>.xlsx`.

| # | Listado | Dónde suele estar | Campos que tiene que traer |
|---|---|---|---|
| a | Cuentas corrientes de **clientes** — composición de saldos | Ventas → Cuentas corrientes | cliente, comprobante, fecha emisión, **vencimiento**, importe, **saldo pendiente** |
| b | Cuentas corrientes de **proveedores** — composición de saldos | Compras → Cuentas corrientes | proveedor, comprobante, fecha emisión, **vencimiento**, importe, **saldo pendiente** |
| c | **Cartera de cheques** de terceros (en cartera, depositados, endosados) | Tesorería → Cheques | número, banco, librador, **fecha de cobro**, importe, estado |
| d | **Cheques propios emitidos** pendientes | Tesorería → Cheques | número, banco, beneficiario, **fecha de pago**, importe, estado |
| e | **Movimientos de caja y bancos**, últimos 3 meses (jun–ago) | Tesorería → Movimientos | fecha, cuenta, concepto, importe, comprobante |
| f | **Ventas por mes** (y si se puede, por cliente y en kilos), últimos 12 meses | Ventas → Informes | mes, cliente, kilos, importe |

- **Si no hay Tango Live:** cada módulo tiene el informe con otro nombre; buscar "Composición de saldos", "Cartera de valores", "Movimientos de tesorería". Si solo deja imprimir: "Imprimir → Guardar como PDF" también sirve para empezar.
- **Si un campo no está** (típico: falta el vencimiento): anotarlo y seguir. Se resuelve con otro informe, no hay que frenar.
- **Para qué:** a y b arman "A quién pagar" y "A cobrar" con nombre; c y d la cartera real; e el histórico de caja; f la estacionalidad y la base de kilos de la cobranza proyectada.
- **Listo cuando:** 12 archivos (6 × 2 empresas), o los que existan, con nota de los que faltan.

### [ ] 2.3 Subir a Drive — T — ⏱ ___
- **Cómo:** en el navegador de la notebook, drive.google.com con tu cuenta → `NAVAR - Datos / Tango / 2026-09-17` → arrastrar los archivos y las capturas. Cerrar sesión de Google en esa notebook al terminar (es una máquina de ellos).
- **Para qué:** es el puente entre las dos máquinas; C los baja por el conector.
- **Listo cuando:** C confirma que los ve y que no falta ningún campo. Si falta algo, se vuelve a exportar en la misma sesión.

### [ ] 2.4 Cerrar la sesión remota — T
- Cerrar Tango, cerrar el navegador, cerrar AnyDesk. No dejar nada abierto en una máquina que no es tuya.

---

## Día 3 · Jueves 18 — datos reales adentro

### [ ] 3.1 `lector/tango.py` — C
- **Qué:** un lector que convierte cada export de Tango en filas para las listas de la Sheet (Cuentas a Cobrar, Cuentas a Pagar, Cartera de Cheques, Movimientos). Y una carga en la Sheet que **reemplaza** las filas "agregado cash viejo".
- **Listo cuando:** la Sheet tiene proveedores y clientes con nombre y "Posición de Deuda" da un número que sale de facturas, no de totales.

### [ ] 3.2 Reunión con quien carga los números (1 hora, video) — T — ⏱ ___
- **Qué:** los cuatro bloques de la guía del 15/09: la rutina de los lunes (**anotar cuántas horas tarda hoy**), lo que Tango no sabe (tolerancia por proveedor, cómo se calcula la cobranza por kg, cosecha, estampillas, honorarios, "otros"), cheques y bancos (qué se hace con los de terceros, qué banco para qué), y la planilla nueva compartiendo pantalla.
- **Cómo:** de cada respuesta anotar tres cosas: el dato, quién lo dijo, si es regla o excepción.
- **Para qué:** completar el catálogo de una sola sentada. Y la última pregunta: *"¿qué de esto te resulta más incómodo de cargar?"*.
- **Listo cuando:** C tiene las notas y puede cerrar el catálogo.

### [ ] 3.3 Central de Deudores del BCRA — C (con los CUIT)
- **Qué:** situación por banco, montos, cheques rechazados, últimos 24 meses. Público y gratis.
- **Para qué:** el paso 0 del camino de la deuda sin pedirle nada a los bancos.

### [ ] 3.4 Contacto con la chica de los tableros — T (vía Priscilla)
- **Qué preguntar:** de qué reportes de Tango salen sus tableros, con qué frecuencia, y si tiene margen bruto por producto. Presentarse como complemento (ella resultado, vos caja).
- **Para qué:** su margen es el "paso 1: capacidad de pago".

---

## Día 4 · Viernes 19 — la primera lectura real

### [ ] 4.1 Catálogo cerrado — C
- Tolerancias por proveedor, A/AA confirmados, cómo se calcula la cobranza por kg, cosecha, estampillas, honorarios. Todo lo que estaba en `null` deja de estarlo.

### [ ] 4.2 Corrida completa — C
- Sheet → `lector/cash_limpio.py` → contrato → `finauto.py` → tablero + hoja de lectura + primera foto de la bitácora.

### [ ] 4.3 Revisión de números, juntos — T + C — ⏱ ___
- **Qué:** caja, vencido, día crítico, a quién pagar. Comparar contra lo que la persona de oficina tiene en la cabeza.
- **Por qué:** empresa muy endeudada: antes de mostrar un número dudoso, parar y consultar. Ningún número sale sin que T lo valide.
- **Listo cuando:** T dice "cierra".

### [ ] 4.4 La Sheet pasa a NAVAR — T — ⏱ ___
- **Cómo:** pedir un mail de la empresa (no de una persona). Drive → Compartir → agregar ese mail como Editor → en el menú de ese usuario "Transferir la propiedad". Después: oficina *Editor*, Priscilla *Lector*, vos quedás *Editor*. Sacar el bloqueo de descarga (engranaje ⚙ de Compartir). Proteger las solapas `Cash Flow Consolidado` y `Posicion de Deuda` (click derecho en la solapa → Proteger hoja → "Mostrar advertencia al editar").
- **Para qué:** los datos son de ellos; vos sos editor, no dueño.
- **Ojo:** el link no cambia al transferir. Lo que se comparte antes sigue valiendo.

### [ ] 4.5 Mandar la lectura 1 — T
- Tablero (HTML) + hoja de lectura (PDF) a Priscilla y a quien carga. Avance (sin números) a María Rosa, si Priscilla dijo que sí.

---

## Día 5 · Lunes 22 — arranca la rutina (semana 1 de 6)

### [ ] 5.1 Ellos cargan la semana — N
- Movimientos reales de la semana, saldos por banco al lunes, cheques nuevos. Lo pendiente de Tango: export y subir (15 min), hasta que sea automático.

### [ ] 5.2 Corrida + lectura — C + T — ⏱ ___
- C corre; T lee 45 minutos y manda. Se guarda la foto de la bitácora: es lo que a la sexta semana permite decir "te lo dije".

### [ ] 5.3 Registro de tiempos — T
- Sumar los ⏱ de toda la semana. Ese número es el costo real del onboarding y define cuántos clientes entran en una semana tuya.

---

## Si algo se traba

| Problema | Qué hacer |
|---|---|
| AnyDesk pide aceptar del otro lado | Falta el acceso desatendido: pedir que en la notebook, en AnyDesk → Configuración → Seguridad, activen "Acceso desatendido" y pongan clave. |
| Tango pide una clave que no tenés | Usuario de consulta no creado. Pedirlo; mientras, exportar con el usuario que te dieron y anotar que es temporal. |
| Un listado no exporta a Excel | Exportar a CSV o "Imprimir → PDF". C lo lee igual; solo tarda más. |
| Un export no trae vencimiento o saldo pendiente | Anotar y seguir. Hay otro informe con ese campo; se pide en la segunda conexión. |
| La reunión con quien carga se posterga | No frena nada: 3.1 y 4.2 salen igual con lo que ya se sabe; el catálogo queda con los `null` y se cierra después. |
| Priscilla no da el mail de la empresa | La Sheet sigue en tu cuenta una semana más. No es un problema; es un pendiente. |

---

## Lo que NO va esta semana

- Bots de bancos, lectura automática de Tango, alertas: **fase 2**, recién cuando la rutina esté andando y sepamos qué archivos hacen falta cada lunes.
- Renegociación de deuda: esta semana solo el **mapa** (paso 0). La capacidad de pago y las propuestas van después, con margen y stock en la mano.
