// probar_plan.cjs — prueba las cuentas del Plan (plan_calculo.gs) con datos INVENTADOS, sin Google.
// Uso: node planillas/plan/probar_plan.cjs   (en la Mac: /Applications/ChatGPT.app/Contents/Resources/cua_node/bin/node)
// Cada número esperado está calculado a mano en el comentario de al lado.
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ctx = {};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(__dirname, "plan_calculo.gs"), "utf8"), ctx);
// plan_planilla.gs también tiene que cargar sin errores (sus funciones usan Google, acá solo se revisa que compile)
vm.runInContext(fs.readFileSync(path.join(__dirname, "plan_planilla.gs"), "utf8"), vm.createContext({}));

let fallas = 0, ok = 0;
function igual(nombre, real, esperado, tol) {
  const bien = typeof esperado === "number" ? Math.abs(real - esperado) <= (tol == null ? 0.01 : tol) : JSON.stringify(real) === JSON.stringify(esperado);
  if (bien) ok++; else { fallas++; console.log("FALLA " + nombre + ": dio " + JSON.stringify(real) + ", esperaba " + JSON.stringify(esperado)); }
}
function hay(nombre, controles, texto) {
  igual(nombre, controles.some(c => (c.tipo + " " + c.detalle).indexOf(texto) >= 0), true);
}
const T = (cols, filas) => ({ cols, filas });

// ---------------------------------------------------------------- datos inventados
function datos() {
  return {
    Ventas: T(["fecha", "estado", "sku", "unidades", "canal", "sku_conocido", "ingresos_productos", "total_neto", "otra"], [
      ["2026-09-15 10:00", "entregada", "AB1001", 30, "Mercado Libre", "sí", 300000, 240000, ""],
      ["2026-10-05 12:00", "entregada", "ab-1001", 30, "Mercado Libre", "sí", 300000, 240000, ""],
      ["2026-10-20 18:00", "entregada", "AB1001", 30, "Tiendanube", "sí", 300000, 270000, ""],
      ["2026-11-02 09:00", "cancelada", "AB1001", 5, "Mercado Libre", "sí", 50000, 40000, ""],   // no cuenta
      ["2026-11-05 09:00", "entregada", "AB1002", 6, "Mercado Libre", "sí", 60000, 48000, ""],
      ["2026-07-01 09:00", "entregada", "AB1003", 9, "Mercado Libre", "sí", 90000, 72000, ""],    // fuera de los 90 días
      ["2026-11-06 09:00", "entregada", "XX9", 1, "Mercado Libre", "no", 5000, 4000, ""],         // código desconocido
      ["", "", "", "", "", "", "", "", ""]                                                       // fila vacía
    ]),
    galicia_saldo: T(["fecha", "saldo"], [["2026-11-10", 1000000], ["2026-11-12", 9999999]]),
    mp_saldo: T(["fecha", "disponible", "a_liberar"], [["2026-11-10", 500000, ""]]),
    mp_movimientos: T(["fecha_liberacion", "monto_neto"], [
      ["2026-11-10", 100],        // ya está en el disponible del 10/11
      ["2026-11-13", 200000],     // semana 0
      ["2026-11-17", 50000],      // semana 1
      ["2027-02-01", 1]           // después del plan
    ]),
    ml_publicidad: T(["fecha", "costo"], [["2026-09-10", 30000], ["2026-10-10", 30000], ["2026-11-01", 99999]]),
    dolar: T(["fecha", "compra", "venta"], [["2026-11-10", 1500, 1550], ["2026-11-12", 1600, 1650]]),
    Productos: T(["sku", "producto", "categoria", "activo"], [
      ["AB1001", "Bici", "", "sí"], ["AB1002", "Balde", "", "sí"], ["AB1003", "Vaso", "", ""], ["AB1004", "Viejo", "", "no"]]),
    Contenedores: T(["contenedor", "proveedor", "fecha_pedido", "llegada_estimada", "llegada_real", "estado", "fob_usd", "notas"], [
      ["C0 viejo", "Prov 0", "2026-08-01", "2026-11-01", "2026-11-03", "nacionalizado", 4000, ""],
      ["C1 bicis", "Prov 1", "2026-10-01", "2026-12-15", "", "en camino", 10000, ""],
      ["C2 vasos", "Prov 2", "", "", "", "planeado", 5000, ""]]),
    Contenedor_productos: T(["contenedor", "sku", "unidades", "fob_unitario_usd"], [
      ["C0 viejo", "AB1002", 20, 200], ["C1 bicis", "AB1001", 50, 200], ["C2 vasos", "AB1003", 10, 500]]),
    Contenedor_pagos: T(["fecha", "contenedor", "concepto", "moneda", "importe", "dolar", "pagado_por", "notas", "estado"], [
      ["2026-10-01", "C1 bicis", "anticipo", "USD", 3000, "", "empresa", "", "pagado"],
      ["2026-10-02", "C1 bicis", "otros", "ARS", 300000, 1500, "socios", "", ""],        // vacío = pagado; no va contra el FOB
      ["2026-11-18", "C1 bicis", "saldo", "USD", 5000, "", "empresa", "", "previsto"],   // semana 1: 5.000 × 1.500
      ["2026-11-25", "C1 bicis", "flete", "ARS", 1500000, "", "empresa", "", "previsto"] // semana 2
    ]),
    Stock_conteo: T(["fecha", "sku", "unidades", "quien"], [
      ["2026-09-30", "AB1001", 999, ""], ["2026-10-31", "AB1001", 100, ""], ["2026-10-31", "AB1002", 10, ""]]),
    Mermas: T(["fecha", "sku", "unidades", "motivo", "Recuperado"], [["2026-11-04", "AB1002", 1, "rota", ""]]),
    Gastos_fijos: T(["concepto", "proveedor", "categoria", "moneda", "importe_mensual", "desde", "hasta"], [
      ["alquiler", "", "alquiler", "ARS", 200000, "2026-10-01", ""],
      ["sistema", "", "sistemas", "USD", 100, "2026-11-01", "2026-11-30"]]),
    Deudas: T(["fecha", "acreedor", "concepto", "moneda", "importe", "vencimiento", "pagada", "fecha_pago"], [
      ["2026-10-31", "Proveedor X", "factura", "ARS", 300000, "2026-11-19", "no", ""],   // semana 1
      ["2026-10-31", "Proveedor Y", "factura", "USD", 200, "", "no", ""],                // sin vencimiento → semana 0
      ["2026-10-31", "Proveedor Z", "factura", "ARS", 999, "2026-11-20", "sí", "2026-11-01"]]),
    Logistica_flex: T(["periodo", "proveedor", "envios", "importe"], [["2026-10", "Flex SA", 10, 18000]]),
    Capital: T(["fecha", "socio", "tipo", "usd", "pesos"], [
      ["2025-01-01", "Socio A", "aporte", 100, ""], ["2025-01-02", "Socio B", "aporte", 100, ""], ["2025-02-01", "Socio A", "aporte", 5, ""]])
  };
}
function proyeccion() {
  return T(["mes", "sku", "producto", "sugerido", "unidades", "precio_unitario", "notas"], [
    ["2026-11", "AB1001", "", "", 150, "", ""],   // el cliente cargó 150: gana sobre el sugerido (30)
    ["2026-12", "AB1001", "", "", "", "", ""],    // vacío: usa el sugerido
    ["2026-11", "ZZ1", "", "", 1, 500, "la agregó el cliente"],
    ["", "", "", "", "", "", ""]
  ]);
}
const config = { "meses a proyectar": 2, "caja mínima ($)": 1000000, "día de pago de gastos fijos": 20 };
const correr = (cambios) => ctx.calcularPlan(Object.assign({ hoy: "2026-11-11", tablas: datos(), config: config, proyeccion: proyeccion() }, cambios || {}));

const r = correr();

// ---------------------------------------------------------------- 6. Históricos (ago-oct)
// cobro: neto 240.000+240.000+270.000 = 750.000 / ingresos 900.000
igual("% que se cobra", r.porDefecto.pctCobro, 750000 / 900000, 1e-9);
// publicidad: 60.000 / ventas ML 600.000
igual("% publicidad", r.porDefecto.pctPub, 0.10, 1e-9);
// Flex: 18.000 / ventas ML de octubre 300.000
igual("% Flex", r.porDefecto.pctFlex, 0.06, 1e-9);
igual("dólar del plan", r.dolar, 1500);
igual("socios", r.socios, ["Socio A", "Socio B"]);

// ---------------------------------------------------------------- 5. Proyección
igual("filas nuevas", r.proyeccion.nuevas.map(n => n.mes + " " + n.sku), ["2026-11 AB1002", "2026-11 AB1003", "2026-12 AB1002", "2026-12 AB1003"]);
igual("sugerido AB1001 (90 u / 3)", r.proyeccion.actualizar.find(a => a.fila === 0).sugerido, 30);
igual("sugerido AB1002 (6 u / 3)", r.proyeccion.nuevas[0].sugerido, 2);
igual("la fila del cliente se actualiza, no se duplica", r.proyeccion.actualizar.map(a => a.fila), [0, 1, 2]);
hay("ZZ1 no está en Productos", r.controles, "ZZ1");
hay("venta con código desconocido", r.controles, "1 ventas de los últimos 90 días");

// ---------------------------------------------------------------- 1. Stock al empezar (cierre del 10/11)
const st = sku => r.stock.filas.find(f => f.sku === sku);
igual("stock AB1001 (conteo 100; la cancelada no resta)", st("AB1001").alEmpezar, 100);
igual("stock AB1002 (10 + 20 llegaron − 6 vendidas − 1 merma)", st("AB1002").alEmpezar, 23);
igual("AB1003 sin conteo: 0 − 9 vendidas", st("AB1003").alEmpezar, -9);
igual("AB1003 marcado sin conteo", st("AB1003").sinConteo, true);
igual("AB1004 inactivo no aparece", !!st("AB1004"), false);
hay("stock negativo", r.controles, "AB1003: da -9");

// ---------------------------------------------------------------- 2. Sin stock y pedir antes de
// AB1001: noviembre 150 u = 5 por día; del 11 al 30 son 20 días → 100 − 100 = 0 el 30/11. El 1/12 vende 30/31 → negativo.
igual("AB1001 fin de noviembre", st("AB1001").alFinal[0], 0, 1e-6);
igual("AB1001 fin de diciembre (0 + 50 que llegan el 15/12 − 30)", st("AB1001").alFinal[1], 20, 1e-6);
igual("AB1001 se queda sin stock", st("AB1001").sinStock, "2026-12-01");
igual("AB1001 pedir antes de (1/12 − 120 días)", st("AB1001").pedirAntes, "2026-08-03");
igual("AB1001 urgente", st("AB1001").urgente, true);
igual("AB1002 no se queda sin stock", st("AB1002").sinStock, "");
// Si el contenedor llega el 25/11, el 30/11 hay 50 y no se agota.
const d2 = datos();
d2.Contenedores.filas[1][3] = "2026-11-25";
const r2 = correr({ tablas: d2 });
igual("con la llegada antes, no se agota", r2.stock.filas.find(f => f.sku === "AB1001").sinStock, "");
igual("con la llegada antes, fin de noviembre", r2.stock.filas.find(f => f.sku === "AB1001").alFinal[0], 50, 1e-6);

// ---------------------------------------------------------------- 3. Contenedores
const c1 = r.contenedores.find(c => c.contenedor === "C1 bicis"), c2 = r.contenedores.find(c => c.contenedor === "C2 vasos");
igual("solo los no nacionalizados", r.contenedores.map(c => c.contenedor), ["C1 bicis", "C2 vasos"]);
igual("C1 pagado (anticipo; 'otros' no cuenta)", c1.pagado, 3000);
igual("C1 previsto (saldo)", c1.previsto, 5000);
igual("C1 otros previstos (flete 1.500.000 / 1.500)", c1.otrosPrevistos, 1000);
igual("C1 próximo pago", c1.proximo, "2026-11-18");
igual("C1 sin programar (10.000 − 3.000 − 5.000)", c1.sinProgramar, 2000);
igual("C2 sin programar", c2.sinProgramar, 5000);
hay("C1 con pagos sin programar", r.controles, "C1 bicis: faltan USD 2000");
hay("C2 sin llegada estimada", r.controles, "C2 vasos: no tiene llegada estimada");

// ---------------------------------------------------------------- 4. Caja semanal
const s = r.caja.semanas;
igual("semanas (9/11 al 3/1)", s.length, 8);
igual("primera semana", s[0].desde + " " + s[0].hasta, "2026-11-09 2026-11-15");
igual("caja al empezar (banco 1.000.000 + MP 500.000)", r.caja.apertura, 1500000);
igual("sem 0: MP a liberar", s[0].mp, 200000);
igual("sem 0: sin cobros proyectados (se cobran a 7 días)", s[0].cobros, 0);
igual("sem 0: deuda sin vencimiento (USD 200 × 1.500)", s[0].deudas, 300000);
igual("sem 0: caja al final", s[0].final, 1400000);
igual("sem 0: sin aporte", s[0].aporte, 0);
// Semana 1: cobros de lo vendido del 11 al 15/11 = 5 días × (150×10.000 + 2×10.000 + 1×500) / 30 × 750.000/900.000
const cobros1 = 5 * (1500000 + 20000 + 500) / 30 * (750000 / 900000);
igual("sem 1: cobros proyectados", s[1].cobros, cobros1, 1e-4);
igual("sem 1: MP", s[1].mp, 50000);
igual("sem 1: pago previsto de contenedor (USD 5.000 × 1.500)", s[1].contenedores, 7500000);
igual("sem 1: fijos el 20/11 (200.000 + USD 100 × 1.500)", s[1].fijos, 350000);
igual("sem 1: deuda que vence el 19/11", s[1].deudas, 300000);
const final1 = 1400000 + 50000 + cobros1 - 7500000 - 350000 - 300000;
igual("sem 1: aporte para volver a la caja mínima", s[1].aporte, 1000000 - final1, 1e-4);
igual("sem 1: caja al final = mínimo", s[1].final, 1000000, 1e-6);
igual("sem 1: mitad socio A", s[1].socios[0], (1000000 - final1) / 2, 1e-4);
igual("sem 1: mitad socio B", s[1].socios[1], (1000000 - final1) / 2, 1e-4);
igual("sem 2 arranca en el mínimo", s[2].inicio, 1000000, 1e-6);
igual("sem 2: flete previsto en pesos", s[2].contenedores, 1500000);
// Publicidad y Flex de noviembre: ventas ML = 150×10.000×(60/90) + 2×10.000×1 + 1×500×1 = 1.020.500; se pagan el 12 y el 10/12 (semana 4)
igual("sem 4: publicidad de noviembre", s[4].pub, 102050, 1e-6);
igual("sem 4: Flex de noviembre", s[4].flex, 61230, 1e-6);
igual("sem 5: fijos del 20/12 (solo alquiler)", s[5].fijos, 200000);
// Sin aportes, la semana 2 baja más (se paga el flete de 1.500.000 y solo entran cobros proyectados).
igual("caja más baja sin aportes: semana 2", r.caja.peor.desde, "2026-11-23");
igual("caja más baja sin aportes: monto", r.caja.peor.caja, final1 + s[2].cobros - 1500000, 1e-4);
igual("sem 2: cobros de 7 días de noviembre", s[2].cobros, 7 * (1500000 + 20000 + 500) / 30 * (750000 / 900000), 1e-4);
// 70/30
const r7 = correr({ config: Object.assign({}, config, { "aporte de Socio A (%)": "70%", "aporte de Socio B (%)": 30 }) });
igual("70/30 socio A", r7.caja.semanas[1].socios[0], (1000000 - final1) * 0.7, 1e-4);
igual("70/30 socio B", r7.caja.semanas[1].socios[1], (1000000 - final1) * 0.3, 1e-4);
const r9 = correr({ config: Object.assign({}, config, { "aporte de Socio A (%)": 70, "aporte de Socio B (%)": 20 }) });
hay("reparto que no da 100", r9.controles, "suman 90 %");
igual("reparto que no da 100 → partes iguales", r9.reparto, [0.5, 0.5]);
// Sin caja mínima: sin aportes y aviso
const r0 = correr({ config: { "meses a proyectar": 2, "día de pago de gastos fijos": 20 } });
igual("sin caja mínima no hay aportes", r0.caja.totalAportes, 0);
hay("aviso de caja mínima", r0.controles, "Falta la caja mínima");

// ---------------------------------------------------------------- Real contra proyectado (noviembre ya empezó)
const rr = (sku) => r.real.find(f => f.mes === "2026-11" && f.sku === sku);
igual("AB1002 real 6 contra 2 proyectadas", [rr("AB1002").uR, rr("AB1002").uP, rr("AB1002").dif], [6, 2, 4]);
igual("AB1002 $ real", rr("AB1002").pR, 60000);
igual("AB1001 la cancelada no es venta real", rr("AB1001").uR, 0);
igual("XX9 desconocido no entra", !!rr("XX9"), false);

// ---------------------------------------------------------------- 7. Columna faltante
const d7 = datos();
d7.Contenedores.cols[3] = "llegada_estimada_mal";
const r7b = correr({ tablas: d7 });
igual("sin la columna, no hay stock", r7b.stock, null);
igual("sin la columna, no hay contenedores", r7b.contenedores, null);
igual("la caja se calcula igual", r7b.caja.semanas.length, 8);
hay("aviso de columna faltante", r7b.controles, "Contenedores: falta llegada_estimada");

// ---------------------------------------------------------------- 8. Fechas en el borde
igual("domingo 22:30 en Buenos Aires sigue siendo domingo", ctx.planDia(new Date("2026-11-16T01:30:00Z")), "2026-11-15");
igual("lunes de un domingo", ctx.planLunes("2026-11-15"), "2026-11-09");
igual("lunes de un lunes", ctx.planLunes("2026-11-16"), "2026-11-16");
igual("mes siguiente a diciembre", ctx.planMesMas("2026-12", 1), "2027-01");
igual("febrero bisiesto", ctx.planDiasMes("2028-02"), 29);
igual("día 31 en noviembre → 30", ctx.planDiaDelMes("2026-11", 31), "2026-11-30");
igual("mes cargado como fecha de la planilla", ctx.planMes(new Date("2026-11-01T03:00:00Z")), "2026-11");
igual("mes 11/2026", ctx.planMes("11/2026"), "2026-11");
igual("número argentino", ctx.planNum("1.234.567,89"), 1234567.89);
igual("porcentaje", ctx.planPct("25%"), 0.25);
igual("SKU normalizado", ctx.planSku(" ab-10.01 "), "AB1001");
// Una venta del 31/10 a las 23 h (02:00 UTC del 1/11) es de octubre: entra en el histórico.
const d8 = datos();
d8.Ventas.filas.push([new Date("2026-11-01T02:00:00Z"), "entregada", "AB1002", 1, "Tiendanube", "sí", 100000, 0, ""]);
igual("venta de las 23 h del 31/10 cuenta en octubre", correr({ tablas: d8 }).porDefecto.pctCobro, 750000 / 1000000, 1e-9);

console.log((fallas ? "HAY " + fallas + " FALLAS" : "TODO BIEN") + " (" + ok + " comprobaciones bien)");
process.exit(fallas ? 1 : 0);
