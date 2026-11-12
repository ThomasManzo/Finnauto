# Plan — ventas, stock y caja hacia adelante

Planilla de Google para un cliente que importa (compra contenedores) y vende por Mercado Libre y Tiendanube.
Mira hacia adelante y contesta tres preguntas:

1. Con las ventas que se proyectan, **¿cuándo se queda sin stock cada producto?** y ¿hasta cuándo hay que pedir?
2. **¿Cuánta plata hay en caja cada semana?** Tiene en cuenta cobros, pagos de contenedores, gastos fijos, deudas, publicidad y Flex.
3. Si la caja baja del mínimo, **¿cuánto tiene que poner cada socio y en qué semana?**

Además muestra, mes a mes, lo real contra lo proyectado.

## De dónde sale cada cosa

- **Planilla Datos (el Plan solo la lee):**
  - ventas y saldos del banco y de Mercado Pago;
  - lo que Mercado Pago tiene por liberar;
  - publicidad, dólar y productos;
  - contenedores con sus productos y sus pagos;
  - conteos de stock, mermas, gastos fijos, deudas, Flex y capital (de ahí salen los socios).

  Los contenedores se cargan **solo en Datos**, también los planeados (estado `planeado`). Los pagos que todavía no se hicieron van en `Contenedor_pagos` con estado `previsto`.
- **Planilla Plan: lo que carga el cliente (solapas naranjas).**
  - **Config**: caja mínima, meses a proyectar y supuestos. Lo que queda vacío usa el valor de "si queda vacío", que casi siempre sale de lo que pasó en los últimos 3 meses.
  - **Ventas proyectadas**: una fila por producto y mes. El Plan completa `producto` y `sugerido`; el cliente carga `unidades` (y `precio_unitario` si cambia el precio).

## Solapas que escribe el Plan (azules)

- **Caja semanal**: arranca con el último saldo del banco más el disponible de Mercado Pago. Cada semana se suma y se resta lo siguiente:
  - **suma** lo que Mercado Pago va a liberar y los cobros de las ventas proyectadas (al % que se cobra, con los días de demora);
  - **resta** los pagos previstos de contenedores que paga la empresa, los gastos fijos (el día de pago), las deudas sin pagar (por vencimiento), y la publicidad y la Flex del mes anterior.

  Si la caja queda debajo del mínimo, calcula el aporte necesario y lo reparte entre los socios.
- **Stock proyectado**: parte del stock al cierre del día anterior al inicio y sigue día por día. Muestra el stock a fin de cada mes, el día en que se queda sin stock y "pedir antes de", que es ese día menos el plazo de reposición.
- **Contenedores**: los que no están nacionalizados, con FOB, pagado, previsto y lo que queda **sin programar**, que es plata que todavía no está en la caja.
- **Real vs proyectado**: unidades y pesos de cada producto en los meses que ya empezaron.
- **Controles**: lo que falta cargar o no cierra.

Se recalcula solo cada hora (disparador). Las cuentas están en `plan_calculo.gs`, y la lectura y escritura en `plan_planilla.gs`.

## Instalación

Está en la cabecera de `plan_planilla.gs`:

1. Crear un proyecto de Apps Script independiente.
2. Pegar los dos `.gs`.
3. Poner los ids de Datos y del Plan.
4. Correr `armarPlan`, después `recalcularPlan` y después `instalarDisparador`.

## Prueba

```
/Applications/ChatGPT.app/Contents/Resources/cua_node/bin/node planillas/plan/probar_plan.cjs
```

Usa datos inventados y números calculados a mano. Prueba las cuentas, no la escritura en Google.
