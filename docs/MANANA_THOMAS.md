# Lo que quedó listo, y lo que solo podés hacer vos

**Escrito el 06/09/2026**, mientras no estabas. Lo de arriba es lo urgente.
*(El anterior quedó en `MANANA_THOMAS_viejo.md`.)*

---

## 1 · Lo único con reloj: la conciliación

El premortem lo marcó como **el único fallo irreversible**, y tiene razón. Pero
**la fecha estaba mal planteada**, y eso cambia qué hay que pedir.

Verifiqué el archivo: `clientes/maga/memoria/proyeccion_2026-09-04.json` proyecta
**del 04/09 al 04/10**, 226 movimientos.

> El plan decía *"antes del 04/10 pedile el cash actualizado"*. **Un cash pedido
> hoy no sirve para eso**: solo llega hasta hoy, y te dejaría conciliar dos días.
>
> Para conciliar la proyección entera necesitás un export **fechado después del
> 04/10**.

O sea que **la fecha límite no es el 04/10: es el día que pierdas el contacto.**
Y conciliar **no es todo o nada** — verifiqué el código: `backtest_horizonte`
compara la curva acumulada de cualquier ventana. Un export del 20/09 te concilia
16 días. Uno del 05/10, los 30.

**Lo que yo haría, en este orden:**

1. **Pedir ahora, mientras la relación está tibia**, un compromiso: *"¿me
   mandarías el export del cash una vez en la primera semana de octubre?"*.
   Es un archivo, no un trabajo.
2. **Ofrecer a cambio, sin cargo, el informe del día crítico.** Ya está generado:
   `salidas/informe.html`. No es un favor que pedís: es un intercambio.
3. Si te dicen que sí, pedir **también uno ahora**, para tener una conciliación
   parcial por si el de octubre no llega.

Es lo único de toda esta lista que caduca.

## 2 · Lo que solo podés escribir vos

| | Por qué no lo puedo hacer yo |
|---|---|
| **El precio** | No sé cuánto vale tu hora ni cuánto necesitás facturar. Pero el premortem tiene razón: sin un número escrito se cotiza a ciegas, y a ciegas siempre se cotiza bajo. |
| **Cuántos meses aguantás sin cobrar** | Solo vos lo sabés, y define si esto se hace en dos semanas o en seis meses. Debería estar arriba de todo en `ESTADO.md`. |
| **Las 5 llamadas de descubrimiento** | La pregunta es una sola: *"¿tenés línea bancaria disponible hoy?"* Si la mayoría dice que sí, el nicho está mal definido — y conviene saberlo en octubre, no en marzo. |

## 3 · Lo que dejé hecho

### Un solo comando

```bash
python finauto.py --contrato datos/CONTRATO_maga_2026-09-05.json
```

Controla el dato, lo contrasta contra tus propios números, arma el tablero y el
informe, guarda la foto de hoy, y termina con el resumen para leer antes de
salir. Existe porque **antes de una reunión nadie corre siete comandos en el
orden correcto**, y el que se olvida es siempre el que hacía falta.

### El tablero, ahora con seis capas

| | |
|---|---|
| **Posición** | KPIs, escenarios, en qué se va la plata, próximas salidas y **el gráfico de ingresos día por día** — el que tenías en tu dash de Apps Script |
| **A quién pagar** | El reparto ordenado por quién puede cortarte primero |
| **A cobrar** | *Nueva.* Quién nos debe, y **cada cheque que vence con su decisión pendiente** |
| **Proyección** | *Nueva.* La curva de caja día por día y **el día crítico** |
| **Retiro** | La calculadora, con selector de ventana y prueba de monto |
| **Hallazgos** | Lo que encontramos, lo que el tablero no sabe, y **la memoria** |

Un archivo, sin internet, botón por empresa. Verificado en el navegador: las 18
combinaciones (6 capas × 3 empresas) renderizan sin un error de consola.

### La config salió del código

Era el ítem que el premortem marca como **el cuello de botella del negocio**.
Ahora vive en la solapa **`finauto CONFIG`** de cada planilla, y el menú tiene
**"Crear solapa de configuración"**, que la escribe con una columna explicando
cada campo.

Probado con un cliente hipotético (otra celda de caja, bloque llamado
*"Deuda Proveedores"*): anda sin tocar una línea de código. **Ya cumplís la regla
dura del premortem.**

### El papel que te iban a pedir

`docs/COMO_TRABAJAMOS.md` — una carilla: qué toco, dónde quedan los datos, quién
responde, qué pasa al terminar. Y **la propuesta en dos fases**: fase 1 solo una
planilla exportada, fase 2 las credenciales. Así la primera reunión no pide
acceso a ningún banco.

### El bug que encontraste vos

El clasificador automático marcaba el día como hecho apenas procesaba **algo**.
Si a las 8 llegaba Galicia y Comafi tardaba, Comafi **no se cargaba ese día** y
nadie se enteraba. Ahora las cuatro horas corren siempre, y al cerrar la ventana
compara contra `AUTO_BANCOS_ESPERADOS` y avisa por mail si faltó alguno.

---

## 4 · Lo que NO pude verificar

**El export end-to-end después del refactor de config.** Cambié el Exportador
para que lea la config de la planilla, y el navegador no me dejó correr el menú
en Sheets (se congela el renderer). Lo verifiqué de forma estática:

- las 7 claves de `EXP_CONFIG` que se usan están todas definidas;
- los defaults dan **exactamente** los mismos valores que las constantes viejas;
- `_bloques_()` devuelve la misma definición que el `EXP_BLOQUES` anterior, tanto
  para la hoja genérica como para la de MAGA.

Es sólido, pero no es lo mismo que haberlo corrido. **Antes de mostrarle esto a
alguien, corré una vez el export desde el menú** y compará contra
`datos/CONTRATO_maga_2026-09-05.json`. Si algo cambió, el contraste lo grita.

## 5 · Lo que sigue

1. **Conciliar en octubre** y poner el resultado en el tablero. Es lo que
   convierte *"el motor calcula bien"* en *"te lo dije y pasó"* — y eso último es
   lo que se vende.
2. **Probar el pipeline con una planilla que no sea de MAGA.** Cualquiera. Es la
   única forma de saber si la config alcanza o falta algo.
3. **El informe en PDF.** Hoy es HTML; se imprime bien, pero un PDF fechado con
   tu nombre es lo que se manda por mail.

---

*241 tests, todo verde. Los dos repos pusheados.*
