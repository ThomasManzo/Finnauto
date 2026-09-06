# Los contratos, guardados acá

Copias locales de los contratos exportados. **Es lo único que sobrevive si se
pierde el acceso a la planilla de origen**, y por eso existe esta carpeta.

`CONTRATO_maga_2026-09-05.json` es el bueno: el último export completo, con
egresos del cashflow, cartera de cheques, referencias del cliente y las
fórmulas resueltas. Todo lo que el motor sabe leer, sale de acá.

## Por qué está acá

Comodidad, no seguro. Las planillas son de la cuenta personal de Thomas, así que
el origen no se pierde y siempre se puede volver a exportar. Tener el JSON local
evita depender de Drive para correr el motor o generar el informe.

## Qué NO va a git

Nada con datos reales — está en el `.gitignore` de al lado. Son movimientos
bancarios, deuda y cobranzas de una empresa que no es nuestra. Un repo cambia
de privado a público con dos clicks; un contrato exportado no se puede
des-publicar.
