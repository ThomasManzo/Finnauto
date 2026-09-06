# Transcripción del premortem — finauto

**Fecha:** 06/09/2026, 00:42
**Objeto:** finauto / Finnauto
**Criterio de éxito sometido a premortem:** que una cadena ajena pague
**Horizonte:** 6 meses (→ marzo 2027)
**Método:** premortem de Gary Klein. 10 razones de fallo en bruto, 10 agentes de análisis profundo en paralelo, síntesis posterior.

---

## 1. Contexto recopilado

**Fuentes leídas antes de arrancar:** memorias del proyecto (`project_maga_monorepo`, `project_maga_repo_backup`, `project_comafi_next`, `reference_cashflow_appsscript`), `C:\finauto\docs\ESTADO.md` y `C:\finauto\docs\NEGOCIO.md`.

### Qué es
Motor de decisión financiera para PyMEs argentinas que se financian con sus proveedores, no con el banco. Nicho: farmacias y droguerías. La tesis: la caja real de una PyME argentina no está en el banco sino en cuánto aguantan sus proveedores antes de cortarle la compra. El motor contesta "¿a quién le pago esta semana y cuánto atraso acumulo?", no "¿me alcanza?".

### Para quién
Cadenas de farmacias y droguerías. Cliente #1: MAGA+ / Speedmed — 14 farmacias (14 razones sociales, porque en Buenos Aires no se pueden tener más de 3 por titular) + 1 droguería.

**Modelo de negocio:** asesoría recurrente, no venta de software. Thomas corre las herramientas; el entregable es un documento por visita; el éxito es que la próxima visita valga más que la anterior. La memoria (qué se predijo vs. qué pasó) es el activo declarado.

### Cómo es el éxito
**Que una cadena ajena pague.** Textual: *"Que se vende sin que vos seas parte de la empresa. Es el test que de verdad informa."*

### Estado al 06/09/2026
- **Motor:** terminado y probado. 195 tests.
- **Exportador** (planilla → contrato JSON): completo, corre sobre copia de prueba. Config por cliente hardcodeada adentro.
- **Bots:** el bot genérico está probado punta a punta y Galicia funciona end-to-end. Falta la ficha de selectores de Comafi y Santander.
- **Clasificador automático:** código listo, trigger sin instalar.
- **Dashboard:** dos maquetas HTML sin datos.
- **Documento por visita** (el entregable que se cobra): pendiente, no existe.

### Cambio de encuadre del 06/09/2026 (detectado durante la sesión)
Thomas **ya no trabaja en MAGA+**. El cliente #1 pasó de empleador a prospecto. Posición: *"no voy a trabajar sobre el cash original de MAGA y Speedmed sin que antes me pague"*. Consecuencias: no hay cash de producción, los bots quedan sin acceso, el trigger no se instala, y **el dato es una foto del 05/09/2026 que no se puede refrescar**.

### Validación conseguida
La caja del motor coincide al peso con la del cliente. Las diferencias en deuda cierran al peso con motivos nombrados (la refinanciación y las notas de crédito).

### Hallazgos que ya justifican la asesoría
- La "Posición Consolidada" que el cliente usa como faro apunta a la columna B del cashflow = el 1 de abril de 2026. Cinco meses vieja.
- La Calculadora infla la deuda en $915M por no netear las notas de crédito.
- El "horizonte 45 días" es solo un texto: no filtra nada, suma 56 días.
- Los números de la Calculadora no son fórmulas vivas: el mismo valor pasó de $1.456M a $2.526M entre dos exports del mismo día.
- Día crítico detectado: 25/09/2026, la caja cae a $135M bajo el mínimo de $200M.
- Solo el 9% de los egresos es flexible ($114M vs $1.158M rígido).

---

## 2. El encuadre

> Es marzo de 2027. Pasaron seis meses. Ninguna cadena ajena a MAGA+ paga por finauto. El intento está muerto. Miramos para atrás para entender qué lo mató.

---

## 3. Premortem en bruto — las 10 razones de fallo

1. El documento por visita nunca se construyó → no hay nada que facturar.
2. El primer onboarding ajeno se come el trimestre.
3. El motor de bots anda; la ficha del banco del prospecto, no.
4. El "sí" de la reunión no se convierte en un acceso cargado.
5. El valor solo se demuestra adentro → no hay demo vendible en la primera reunión.
6. El precio nunca se fijó, ni siquiera con MAGA+.
7. Las horas del cliente #2 salen de las mismas 24.
8. La cadena ajena no tenía el problema con esa forma.
9. No hubo fracaso: hubo estancamiento.
10. El dato se congeló y se pudrió *(agregada tras detectar el cambio de encuadre)*.

---

## 4. Correcciones de Thomas sobre la primera pasada

Thomas corrigió cinco premisas que yo había metido en las razones de fallo. Las correcciones son suyas; los errores eran míos al redactar los prompts, no de los agentes.

| Corrección | Efecto |
|---|---|
| "El proyecto no está terminado todavía, por eso hay cosas que no están armadas, como el documento por visita." | El fallo 01 se reescribe: no es abandono, es una pieza pendiente. El riesgo se mantiene: es la única que se cobra. |
| "Nunca dije que sea proyecto de un día el onboarding." | El fallo 02 se reescribe alrededor de lo que sí está escrito: *"onboarding = una reunión que las herramientas preparan"*, y esas herramientas no existen. |
| "Los bots funcionan ya probado contra Galicia, falta la configuración de los demás bancos." | El fallo 03 se reescribe: el motor anda, lo que falta es la ficha, y la ficha necesita una sesión real del banco. |
| "No necesito que me abran la caja, necesito que se carguen credenciales en texto no leíble. No pertenezco a la competencia." | El fallo 04 se reescribe entero: se elimina el ángulo de competencia y el de "entregar claves". Queda el cuello contractual. |
| "El cliente 2 no duplica costo si estoy yo solo." | **Punto en disputa.** Se acepta la mitad (no hay estructura duplicada) y se mantiene la otra (las horas operativas se suman enteras). |

---

## 5. Análisis profundos — un agente por razón de fallo

### Fallo 01 — El entregable que se cobra nunca se construyó

**Historia.** Decisión de ingeniero: primero las tuberías de datos —bots, clasificador, dashboard— y después la interfaz. El problema es que el documento no es interfaz, es el producto. Cuando los bancos cambian contraseñas, todo se frena; pero el motor ya tiene datos reales validados y no hacía falta Comafi ni Santander funcionando para escribir el primer documento con Galicia sola, o a mano con los CSVs que ya bajaban. Los hallazgos fuertes —el faro apuntando a abril, los $915M, el "45 días" que suma 56— se quedaron en conversaciones sueltas y nunca bajaron a un artefacto fechado y guardable. Se volvieron anécdotas de asesoría informal, no informes. El cliente sigue conforme porque Thomas está ahí corrigiendo en vivo — que es exactamente lo que impide el test de la cadena ajena: no hay nada que un tercero pueda mirar sin que Thomas esté parado al lado explicando.

**Supuesto subyacente.** Que un motor técnicamente correcto se traduce solo, después, en un entregable vendible.

**Señales tempranas.**
- Pasan más de 30 días desde la validación al peso sin que exista un documento fechado y versionado que se pueda mostrar sin estar presente.
- Los hallazgos se mencionan en conversación pero no aparecen citados en ningún archivo entregado con fecha.

---

### Fallo 02 — El primer onboarding ajeno se come el trimestre

**Historia.** Semana 1: llega la planilla del prospecto y no se parece a la de MAGA+. Otras columnas, otro orden de fechas, y la convención clave no aplica — esta cadena borra la celda cuando paga en vez de dejarla en cero, así que "monto con fecha vieja = vencido" no significa nada ahí. El Exportador, cableado contra el layout de MAGA+, tira error en la primera corrida y en la segunda. Semana 2 mapeando tipos a mano: no hay Suizo ni DDS, hay dos droguerías regionales con plazos y compensación propios, y no hay endoso de cheques sino pagarés, un instrumento que el motor ni contempla. Cada campo nuevo implica tocar código porque el reconocedor de planillas —identificado como el cuello de botella del negocio— sigue en el backlog. Semana 3: corrida parcial, faltan las notas de crédito de obra social y el número de caja no cierra. El dueño, que accedió a "una visita", lleva tres semanas sin ver un informe y responde cada vez más lento. Semana 4: sin cobrar un peso, se cae por desgaste, no por rechazo explícito.

**Supuesto subyacente.** Que el trabajo de generalizar se podía dejar para cuando apareciera el segundo cliente — cuando es justamente lo que determina si hay un segundo cliente.

**Señales tempranas.**
- Si a la primera planilla ajena no se le puede apuntar un archivo de config nuevo sin tocar código, la señal ya está prendida.
- Días entre "recibí la planilla del prospecto" y "le mostré el primer número propio". Si no baja a menos de tres, el patrón se repite.

---

### Fallo 03 — El motor de bots anda; la ficha del banco del prospecto, no

**Historia.** El bot genérico funciona: ficha JSON, 20 tests contra un home banking falso, y Galicia probado punta a punta corriendo a las 8:00. Pero Comafi y Santander necesitan una pasada de DOM, y una ficha no se llena de memoria: se llena navegando una sesión real de ese banco. Las credenciales de MAGA se cambiaron; las del prospecto no existen todavía. Ahí se cierra el círculo: no hay ficha sin acceso, no hay acceso sin cliente, no hay cliente sin demo. Aparece un prospecto con cuentas en dos bancos sin ficha. Llenarlas exige entrar a sus cuentas antes de tener contrato. Para no trabar la reunión sale el atajo: "mandame los extractos por mail". El clasificador los parsea igual, así que el motor sigue funcionando — pero la cadena tiene que exportar, nombrar y mandar archivos a mano, exactamente lo que hacía con el contador. A los dos meses deja de mandarlos con regularidad porque no ve para qué sirve el intermediario.

**Supuesto subyacente.** Que llenar una ficha es trabajo que se agenda para "cuando haya cliente" — cuando la ficha vacía es parte de lo que impide cerrarlo.

**Señales tempranas.**
- Pasan más de 4 semanas desde el primer contacto con un prospecto sin un solo selector mapeado de su banco.
- El verbo cambia: de "yo bajo los extractos" a "mandame los extractos". Ese cambio es el fallo ocurriendo en tiempo real.

---

### Fallo 04 — El "sí" de la reunión no se convierte en un acceso cargado

> *Reescrito tras las correcciones: no hay ángulo de competencia, y el diseño no pide ver las claves de nadie — se cargan cifradas con DPAPI y Thomas no las lee.*

**Historia.** La reunión sale bien: el dolor es real y el diagnóstico suena a magia. El dueño dice "dale, arrancamos". Después hay que hacer dos cosas concretas que un "sí" verbal no hace: que alguien de su equipo se siente a cargar las credenciales en el setup —lo que implica aceptar que un bot en la máquina de Thomas entre a sus cuentas, cosa que los bancos formalmente desalientan— y que le pasen la deuda real con cada droguería y los retiros de los socios, material que nadie manda sin un papel firmado. El dueño pide "primero mandame cómo protegés los datos". No hay entidad legal, ni contrato, ni cláusula de confidencialidad para contestar en el momento. El mail queda sin responder tres semanas. Alguno manda un Excel viejo "para probar" y ahí se estanca: sin datos reales, sin bots, sin cobrar.

**Supuesto subyacente.** Que el cuello del acceso es técnico —cómo se guardan las credenciales— cuando en realidad es contractual: quién responde si algo sale mal, y con qué papel.

**Señales tempranas.**
- Reuniones positivas contra accesos efectivamente cargados. Si a los 60 días hay 3 "sí" verbales y 0 credenciales cargadas, el patrón está activo.
- La primera vez que un prospecto pide un contrato o una política de datos y no hay un documento para contestarle en el momento.

---

### Fallo 05 — El valor solo se demuestra adentro

**Historia.** La reunión llega por la red del rubro. Cuarenta y cinco minutos. El pitch abre fuerte: la Posición Consolidada mirando una columna de hace cinco meses, la Calculadora inflando la deuda en $915M, el 91% de los egresos rígido. El prospecto escucha y pregunta lo obvio: *"¿y eso lo viste en mis números o en los de otro?"*. Mostrar los hallazgos reales es exhibir la intimidad financiera de una empresa del mismo mercado. Entonces se cae al modo genérico —"el motor puede hacer esto con tus datos"— que es exactamente lo que dice cualquier consultor de Excel, cualquier implementador de Power BI, cualquiera con ChatGPT. La diferenciación real vive adentro de datos que no se pueden mostrar. La segunda reunión, si la hay, es peor: el prospecto pide "algo por escrito" antes de dar acceso — exactamente el documento por visita que no existe. Un caso anonimizado con números cambiados suena a consultora genérica, sin el filo de lo real. El dashboard en maqueta tampoco ayuda: es una demo vacía. Huevo y gallina: hace falta acceso total para producir la prueba, y la prueba para conseguir acceso total.

**Supuesto subyacente.** Que la potencia técnica del motor hablaría por sí sola en una primera reunión, sin necesitar una prueba empírica sobre los datos del prospecto.

**Señales tempranas.**
- Tres o más primeras reuniones y ninguna avanzó a "te doy acceso" sin haber entregado antes algo escrito y específico.
- El documento por visita sigue sin existir a los 60-90 días de arrancar la prospección: sin artefacto transferible, cada reunión arranca de cero.

---

### Fallo 06 — El precio nunca se fijó

**Historia.** Todo pasó como estaba escrito: motor con 195 tests, un faro desactualizado encontrado, $915M de deuda inflada destapada, un horizonte de 45 días que en realidad era 56. Datos durísimos. Y sin embargo, cuando en enero un conocido de un conocido —dueño de una cadena— pregunta *"che, ¿y esto cuánto sale?"*, hay un segundo de más de silencio. No hay un número. Sale un "depende del volumen, lo vemos sobre la marcha" y un "el primer mes para que lo veas funcionar". El tipo acepta: es gratis. Ese mes se convierte en marzo y después en abril. La razón raíz es anterior: en MAGA+, donde se destapó una deuda inflada en $915M, nunca se puso ese hallazgo en una factura. "Pendiente" quedó pendiente. Entonces al cotizarle a un extraño falta el ancla más poderosa que existe: *"esto ya se lo cobré a alguien y lo pagó"*. Sin ese precedente se cotiza a ciegas, y a ciegas siempre se cotiza bajo, o gratis, o "después vemos".

**Supuesto subyacente.** Que el valor entregado se iba a traducir solo en un precio, sin que hiciera falta cobrárselo primero a alguien real.

**Señales tempranas.**
- Pasan 30 días desde un hallazgo grande sin que exista una nota de honorarios o acuerdo escrito que le ponga precio.
- Aparece la frase "el primer mes sin cargo" en una conversación comercial real, sin fecha de corte ni número que se active después.

---

### Fallo 07 — Las horas del cliente #2 salen de las mismas 24

> *Punto en disputa. Thomas: "el cliente 2 no duplica costo si estoy yo solo". Acuerdo parcial: no hay estructura duplicada ni coordinación. Desacuerdo: estando solo es cuando las horas operativas se suman enteras, porque no hay a quién delegar.*

**Historia.** El cliente #1 ya tiene su rutina semanal: correr los bots, revisar la descarga, clasificar, exportar, tres auditorías, motor, interpretar, escribir el documento, visita. Una tarde entera, más los imprevistos del bot que se cae. Aparece el cliente #2 y hay que exportar: la config de MAGA está hardcodeada adentro del Exportador. Se copia el módulo y se parchea a mano. Ya estaba anotado que había que sacarla "antes de vender el segundo", pero no había segundo; ahora que hay, no hay tiempo de refactorizar porque hay que entregar. Semana 1 con dos clientes: dos corridas de bots (bancos distintos, un bot se cuelga y hay que debuggear en vivo), dos clasificaciones, dos exportaciones sobre dos copias que ya no son iguales, dos auditorías, dos documentos escritos a mano. En la semana 3 se olvida de replicar un cambio en la otra copia y el documento del cliente #2 sale con un número mal. Nadie decide abandonar: simplemente la próxima gestión comercial se pospone una semana, y otra.

**Supuesto subyacente.** Que "estar solo" mantiene el costo bajo, cuando es lo que hace que el techo lo ponga tu semana y no tu estructura.

**Señales tempranas.**
- Cronometrar una corrida completa de MAGA+ de punta a punta, una sola vez. Sin ese número no se puede saber cuántos clientes entran en una semana.
- Aparece más de una copia de config por cliente en el repo, o un `if cliente ==`, antes de que exista config externa.

---

### Fallo 08 — La cadena ajena no tenía el problema con esa forma

**Historia.** Thomas sale a vender con lo único que tiene: un caso. Lleva el pitch a cuatro o cinco cadenas de zonas cercanas. La primera reunión buena es con una cadena de 8 locales: tienen un ERP contable de agencia y un administrativo full-time que ya concilia proveedores todos los lunes. Escuchan diez minutos y dicen "esto ya lo hacemos, solo que en Excel más feo". No hay droguería propia, no hay compensación intercompany, no hay 14 razones sociales: hay un balance prolijo y una persona cuyo trabajo es exactamente lo que el motor automatiza. Segunda reunión, cadena de 3 locales en el interior: el dueño lleva la cuenta de memoria y dice que el día que necesite una planilla para saber a quién pagarle, cierra. No hay dolor suficiente para pagar por un análisis. Thomas ajusta el pitch buscando el punto medio —ni tan chica que se decide de memoria, ni tan grande que ya tiene ERP y gerente— y descubre que ese punto medio casi no tiene representantes a su alcance: o están bancarizadas con líneas activas y no viven al límite del proveedor, o son tan chicas que el dueño la lleva en la cabeza. Siete reuniones, cero contratos.

**Supuesto subyacente.** Que la configuración financiera de MAGA+ era representativa del nicho, cuando era una anomalía de un solo grupo: droguería propia, 14 razones sociales, líneas bancarias agotadas por elección.

**Señales tempranas.**
- Preguntar en las primeras tres reuniones: *"¿tenés línea bancaria disponible hoy?"*. Si la mayoría dice que sí, el nicho no existe como está definido.
- Contar cuántos prospectos ya usan un ERP con módulo de tesorería antes de la primera llamada. Si son mayoría, se compite contra software instalado, no contra una planilla.

---

### Fallo 09 — No hubo fracaso: hubo estancamiento

**Historia.** Siempre hay una buena razón. "Primero cierro el bot de Comafi, así el exportador tiene datos de dos bancos." Después Comafi cambia la contraseña y hay que rehacer el login. Después aparece un edge case en el reparto semanal que rompe tres tests, y arreglarlo es más gratificante que escribir un documento que todavía nadie va a leer. En diciembre: antes de mostrarle nada a un prospecto hace falta el dashboard con datos reales, porque dos maquetas vacías "no venden nada". En enero el motor tiene proyección a 60 días y una cuarta capa de auditoría. Nadie afuera de MAGA+ sabe que finauto existe. En febrero sigue sin haber propuesta escrita, precio, ni una sola llamada. En marzo los 195 tests son 340, la documentación pesa el doble, y el documento por visita sigue donde estaba en septiembre. El estancamiento nunca se sintió como fracaso porque cada semana hubo commits, demos internas y cosas que funcionaban. El día que dejó de ser "todavía no" fue el día en que la fecha del primer contacto comercial dejó de estar anotada en ningún lado, ni siquiera como pendiente.

**Supuesto subyacente.** Que si el motor es suficientemente bueno, la parte comercial va a resultar fácil o casi automática cuando llegue el momento — y por eso nunca hay apuro en empezarla.

**Señales tempranas.**
- Pasan más de 2 semanas sin una fecha concreta agendada con una persona ajena a MAGA+. No "voy a buscar prospectos": una fecha real en un calendario.
- El repo acumula commits nuevos en motor, tests y docs mientras el archivo del documento por visita no cambia de fecha de modificación en más de 30 días.

---

### Fallo 10 — El dato se congeló y se pudrió *(irreversible)*

**Historia.** El módulo de memoria estaba bien diseñado —proyectar, conciliar, aprender— pero necesitaba una segunda foto para probar que servía, y esa foto dependía de un acceso que se perdió el 06/09/2026. `proyeccion_2026-09-04.json` quedó como un fósil: 226 movimientos, un día crítico marcado para el 25/09, y nadie pudo volver a mirar la cuenta real de MAGA+ para ver si la caja efectivamente cayó a $135M. El 25 de septiembre pasó como un martes cualquiera, sin que nadie lo registrara. Para noviembre la misma foto seguía usándose en cada reunión, con el discurso retocado ("esto fue una demostración de capacidad, no un backtest") pero sin poder cambiar los números. En febrero de 2027, en la reunión con la cadena que parecía interesada, alguien hizo la pregunta obvia: *"¿y le acertaste?"*. No había respuesta, había una promesa de hace cinco meses sin verificar. Peor: cuando el prospecto preguntó *"¿y a MAGA+ le seguís laburando?"*, la respuesta era no — lo cual convirtió el caso de éxito en el caso de un cliente que se fue. Un motor de predicción que nunca mostró un acierto no es un producto, es una hipótesis.

**Supuesto subyacente.** Que iba a poder demostrar valor con datos prestados de un cliente que ya no era cliente, sin necesitar nunca una segunda medición.

**Señales tempranas.**
- El contador de proyecciones conciliadas sigue en 1 después de 30 días.
- La fecha del hallazgo estrella no cambia entre reuniones. Si en octubre y en enero se sigue citando el mismo 25/09/2026, el caso está muerto y nadie lo dijo en voz alta.

---

## 6. Síntesis

### El fallo más probable — El documento que se cobra nunca se escribió

El proyecto no está terminado y el documento es una de las piezas que faltan: eso es legítimo. El fallo no es que hoy no exista, es que dentro de seis meses siga sin existir mientras el motor sumó tests. Es el único artefacto que convierte todo lo construido en algo facturable, y la única pieza importante que no depende de ningún acceso que ya no está.

El mecanismo no es falta de tiempo: construir motor da satisfacción inmediata, sale rápido con asistencia de IA y no expone a un "no". El propio `ESTADO.md` ya dice *"lo único que mueve la aguja ahora es lo que sirva para vender"*. La pregunta del premortem no es si se sabe: es qué hace que dentro de seis meses siga escrito ahí.

### El fallo más peligroso — El dato se congela y la prueba caduca

Es el único fallo irreversible de la lista. `proyeccion_2026-09-04.json` llega al 04/10/2026; conciliarla exige el cash real de MAGA+ de ese período. Sin acceso, esa conciliación no se posterga: se pierde. Y lo que se pierde es justo el activo declarado como corazón del negocio — la memoria, *"el mes pasado te dije que el 25 quedabas corto"*. Cuando un prospecto pregunte "¿y le acertaste?", la respuesta será una promesa sin verificar sobre un cliente que ya no es cliente.

### El supuesto oculto — Que el caso MAGA+ es un activo que te espera quieto

Falta la demo y falta el precio: eso está identificado. Lo que no está cuestionado es el estado del material con el que se van a hacer las dos cosas. La foto del 05/09/2026 se trata como una base estable, guardada, lista para cuando le llegue el turno en la secuencia. No lo es: se deprecia, y una parte tiene fecha de vencimiento exacta.

El supuesto oculto no es que falte software. Es que **los pendientes son secuenciales e independientes** —primero la demo, después el precio, después el acceso— cuando uno de ellos tiene un reloj propio corriendo que no espera a los otros.

### El plan revisado

1. **Antes del 04/10/2026 — 28 días — pedirle a MAGA+ el cash actualizado para conciliar la proyección.** No como trabajo ni favor abierto: como pedido puntual de un archivo exportado. Ofrecer a cambio el informe del día crítico del 25/09 sin cargo. Única chance de tener un backtest real. *(Fallo 10)*
2. **Esta semana: escribir el documento por visita con la foto del 05/09.** PDF fechado y versionado. Contenido ya disponible: los cuatro hallazgos, el día crítico del 25/09, el 9% flexible, el reparto semanal sugerido. Cero bots, cero dashboard, cero acceso nuevo. *(Fallos 1 y 5)*
3. **Antes del 30/09: mandarle a MAGA+ un número por escrito.** Precio mensual, qué incluye, qué no, qué pasa si no hay acceso a los bancos. MAGA+ hoy califica para el propio test: ya no sos parte de la empresa. *(Fallo 6)*
4. **Escribir el papel de una carilla que hoy no existe.** Que las credenciales se carguen cifradas resuelve el problema técnico; lo que un dueño pide antes de dar acceso es un contrato: qué datos tocás, dónde quedan, quién responde si un consejo sale mal, qué pasa al terminar. Y ordenar la propuesta en dos fases: fase 1 la planilla exportada, fase 2 las credenciales. *(Fallos 3 y 4)*
5. **Sacar la config de MAGA de adentro del Exportador antes de tocar la planilla del segundo prospecto.** Es la diferencia entre tres días y tres semanas de onboarding. Regla dura: si a una planilla ajena no se le puede apuntar un archivo de config sin tocar código, no salir a vender todavía. *(Fallos 2 y 7)*
6. **Cinco llamadas de descubrimiento con una sola pregunta antes de armar el pitch: "¿tenés línea bancaria disponible hoy?"** Si la mayoría dice que sí, el nicho está mal definido. Mejor enterarse en octubre que en marzo. *(Fallo 8)*
7. **Escribir cuántos meses se puede sostener esto sin cobrar, y qué pasa el día que se acaba.** Sin sueldo de MAGA+, el reloj del proyecto lo marca la plata, no el backlog. Ese número debería estar arriba de todo en `ESTADO.md`. *(Fallo 9)*

### Lista de verificación pre-lanzamiento

1. ¿Existe un PDF fechado que un tercero pueda leer sin vos al lado? Si la respuesta es "está casi", la respuesta es no.
2. ¿Se pidió el cash de octubre antes del 04/10? Es la única fecha de la lista que no se puede correr.
3. ¿Hay un número de precio mensual escrito en algún lado? No "depende del volumen": un número.
4. ¿Hay una fecha concreta en el calendario con una persona ajena a MAGA+? No "voy a buscar prospectos": una fecha.
5. ¿La fase 1 de la propuesta pide credenciales de home banking? Si sí, moverlas a la fase 2.
