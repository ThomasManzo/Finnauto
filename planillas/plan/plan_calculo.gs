/**
 * plan_calculo.gs — LAS CUENTAS de la planilla "Plan" (ventas proyectadas, stock, contenedores y caja por semana).
 *
 * QUÉ HACE ESTE ARCHIVO
 * ---------------------
 * Solo cuentas. No toca ninguna planilla: recibe las tablas ya leídas (encabezados + filas) y devuelve los resultados
 * listos para escribir. Lo que lee y escribe en Google Sheets está en plan_planilla.gs. Se separó así para poder
 * probar todas las cuentas en la computadora, con datos inventados (probar_plan.cjs), sin abrir Google.
 *
 * DE DÓNDE SALE CADA COSA
 * -----------------------
 *  - De la planilla Datos (solo lectura): ventas, saldos de banco y Mercado Pago, cobros por liberar, publicidad, dólar,
 *    productos, contenedores y sus pagos, conteos de stock, mermas, gastos fijos, deudas, Flex y capital.
 *  - De la planilla Plan: la Config (caja mínima, horizonte, supuestos) y la proyección de ventas que carga el cliente.
 *
 * FECHAS: todo se maneja como texto "AAAA-MM-DD" en hora de Buenos Aires (UTC-3; Argentina no tiene horario de
 * verano desde 2009). Así una venta de un domingo a las 23 h no se pasa al lunes.
 *
 * Archivo hermano: plan_planilla.gs (los dos se pegan en el mismo proyecto de Apps Script).
 */

var PLAN_HORAS_ZONA = -3;  // Buenos Aires = UTC-3

// Las columnas que el Plan necesita de cada solapa de Datos. Se buscan por nombre (el lugar no importa).
// Si falta una, la parte que la usa no se calcula y se avisa en Controles.
var PLAN_REQUERIDAS = {
  Ventas: ["fecha", "estado", "sku", "unidades", "canal", "sku_conocido", "ingresos_productos", "total_neto"],
  galicia_saldo: ["fecha", "saldo"],
  mp_saldo: ["fecha", "disponible"],
  mp_movimientos: ["fecha_liberacion", "monto_neto"],
  ml_publicidad: ["fecha", "costo"],
  dolar: ["fecha", "compra"],
  Productos: ["sku", "producto", "activo"],
  Contenedores: ["contenedor", "proveedor", "llegada_estimada", "llegada_real", "estado", "fob_usd"],
  Contenedor_productos: ["contenedor", "sku", "unidades"],
  // "pagado_por" y "estado" no son obligatorias: si no están, todo cuenta como pagado por la empresa.
  Contenedor_pagos: ["fecha", "contenedor", "concepto", "moneda", "importe", "dolar"],
  Stock_conteo: ["fecha", "sku", "unidades"],
  Mermas: ["fecha", "sku", "unidades"],
  Gastos_fijos: ["concepto", "moneda", "importe_mensual", "desde", "hasta"],
  Deudas: ["fecha", "acreedor", "concepto", "moneda", "importe", "vencimiento", "pagada", "fecha_pago"],
  Logistica_flex: ["periodo", "importe"],
  Capital: ["socio"]
};

// Qué solapas de Datos necesita cada parte del Plan. Si falta una, esa parte queda sin calcular.
// Las que no están en ninguna lista (publicidad, dólar, Flex, capital) son opcionales: si faltan se usa un valor
// por defecto y se avisa.
var PLAN_PARTES = {
  proyeccion: ["Productos", "Ventas"],
  stock: ["Productos", "Ventas", "Stock_conteo", "Mermas", "Contenedores", "Contenedor_productos"],
  contenedores: ["Contenedores", "Contenedor_pagos"],
  caja: ["Productos", "Ventas", "galicia_saldo", "mp_saldo", "mp_movimientos", "Contenedor_pagos", "Gastos_fijos", "Deudas"],
  real: ["Ventas"]
};

// Los parámetros de la solapa Config: [clave interna, texto que se ve en la planilla, explicación].
var PLAN_PARAMETROS = [
  ["inicio", "inicio del plan", "Desde qué día se proyecta. Vacío = hoy."],
  ["meses", "meses a proyectar", "Cuántos meses mirar hacia adelante, contando el del inicio. Vacío = 6."],
  ["cajaMinima", "caja mínima ($)", "La plata que siempre tiene que haber en caja. Si la caja baja de esto, el Plan calcula cuánto tienen que poner los socios. Vacío = no se calculan aportes."],
  ["dolar", "dólar del plan", "Dólar para pasar a pesos lo que está en USD (pagos de contenedores, gastos, deudas). Vacío = el último oficial comprador."],
  ["diaFijos", "día de pago de gastos fijos", "Qué día del mes se pagan los gastos fijos. Vacío = 5."],
  ["diaPub", "día de pago de la publicidad de ML", "La factura de publicidad de un mes se paga este día del mes siguiente. Vacío = 12."],
  ["diaFlex", "día de pago de la Flex", "La factura de envíos Flex de un mes se paga este día del mes siguiente. Vacío = 10."],
  ["diasCobro", "días hasta cobrar una venta", "Cuántos días pasan desde que se vende hasta que la plata está disponible. Vacío = 7."],
  ["pctCobro", "% que se cobra de cada venta", "Qué parte del precio queda después de comisiones y envíos. Vacío = lo que pasó en los últimos 3 meses."],
  ["pctPub", "% de publicidad sobre ventas de ML", "Gasto de publicidad de Mercado Libre sobre lo vendido en Mercado Libre. Vacío = los últimos 3 meses."],
  ["pctFlex", "% de Flex sobre ventas de ML", "Facturas de envíos Flex sobre lo vendido en Mercado Libre. Vacío = los últimos 3 meses."],
  ["plazo", "plazo de reposición (días)", "Días desde que se le pide al proveedor hasta que la mercadería está en el depósito. Vacío = 120."]
];
var PLAN_PREFIJO_SOCIO = "aporte de ";   // fila de Config: "aporte de <socio> (%)"

// ---------------------------------------------------------------------------------------------------------------
// Ayudas chicas: textos, números, SKU y fechas.
// ---------------------------------------------------------------------------------------------------------------

function planTexto(v) { return String(v == null ? "" : v).trim(); }
function planMin(v) { return planTexto(v).toLowerCase(); }
function plan2(n) { n = Number(n); return (n < 10 ? "0" : "") + n; }
function planEsFecha(v) { return Object.prototype.toString.call(v) === "[object Date]"; }

// El SKU siempre igual en todos lados: mayúsculas, sin espacios, guiones ni puntos ("ab-1001 " → "AB1001").
function planSku(v) { return planTexto(v).toUpperCase().replace(/[\s\-\.]/g, ""); }

// Lee un número venga como venga: 1234.5, "1.234,50", "25%", "$ 1.000". Vacío o texto → null.
function planNum(v) {
  if (typeof v === "number") return isFinite(v) ? v : null;
  var s = planTexto(v).replace(/\$|usd|\s/gi, "");
  if (!s) return null;
  var pct = /%$/.test(s);
  if (pct) s = s.slice(0, -1);
  if (s.indexOf(",") >= 0) s = s.replace(/\./g, "").replace(",", ".");   // formato argentino: 1.234,56
  else if (/^-?\d{1,3}(\.\d{3})+$/.test(s)) s = s.replace(/\./g, "");    // 1.234.567 sin decimales
  var n = Number(s);
  if (!isFinite(n)) return null;
  return pct ? n / 100 : n;
}
function planN(v) { var n = planNum(v); return n == null ? 0 : n; }

// Un porcentaje cargado como 0,25, 25 % o 25 → 0,25.
function planPct(v) { var n = planNum(v); if (n == null) return null; return n > 1 ? n / 100 : n; }

// Cualquier fecha → "AAAA-MM-DD" en hora de Buenos Aires. Acepta fechas de la planilla, "2026-11-10 14:30" y "10/11/2026".
function planDia(v) {
  if (planEsFecha(v)) {
    if (isNaN(v.getTime())) return "";
    var t = new Date(v.getTime() + PLAN_HORAS_ZONA * 3600000);
    return t.getUTCFullYear() + "-" + plan2(t.getUTCMonth() + 1) + "-" + plan2(t.getUTCDate());
  }
  var s = planTexto(v), m;
  if ((m = s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/))) return m[1] + "-" + plan2(m[2]) + "-" + plan2(m[3]);
  if ((m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/))) return m[3] + "-" + plan2(m[2]) + "-" + plan2(m[1]);
  return "";
}

// Un mes → "AAAA-MM". Acepta "2026-11", "11/2026", una fecha completa o una fecha de la planilla.
function planMes(v) {
  if (planEsFecha(v)) return planDia(v).slice(0, 7);
  var s = planTexto(v), m;
  if ((m = s.match(/^(\d{4})-(\d{1,2})$/))) return m[1] + "-" + plan2(m[2]);
  if ((m = s.match(/^(\d{1,2})\/(\d{4})$/))) return m[2] + "-" + plan2(m[1]);
  return planDia(s).slice(0, 7);
}

// Días como número (para sumar y restar días sin líos de horario).
function planDiaNum(d) { var p = d.split("-"); return Math.round(Date.UTC(+p[0], +p[1] - 1, +p[2]) / 86400000); }
function planNumDia(n) {
  var t = new Date(n * 86400000);
  return t.getUTCFullYear() + "-" + plan2(t.getUTCMonth() + 1) + "-" + plan2(t.getUTCDate());
}
function planMas(d, dias) { return planNumDia(planDiaNum(d) + dias); }
// El lunes de la semana de ese día (las semanas van de lunes a domingo).
function planLunes(d) { var n = planDiaNum(d); var dow = new Date(n * 86400000).getUTCDay(); return planNumDia(n - (dow + 6) % 7); }
function planMesMas(mes, k) { var p = mes.split("-"); var t = (+p[0]) * 12 + (+p[1] - 1) + k; return Math.floor(t / 12) + "-" + plan2(t % 12 + 1); }
function planDiasMes(mes) { var p = mes.split("-"); return new Date(Date.UTC(+p[0], +p[1], 0)).getUTCDate(); }
// Un día dentro de un mes; si el mes es más corto (día 31 en noviembre), el último día del mes.
function planDiaDelMes(mes, dia) { return mes + "-" + plan2(Math.min(Math.max(1, dia), planDiasMes(mes))); }

// ---------------------------------------------------------------------------------------------------------------
// Tablas: de {cols, filas} (lo que se leyó de la planilla) a una lista de objetos { columna: valor }.
// ---------------------------------------------------------------------------------------------------------------

function planObjetos(t) {
  if (!t || !t.cols) return [];
  var cols = t.cols.map(planMin);
  return (t.filas || []).filter(function (f) {
    return f.some(function (v) { return planTexto(v) !== ""; });   // las filas vacías no cuentan
  }).map(function (f) {
    var o = {};
    cols.forEach(function (c, i) { if (c && !(c in o)) o[c] = f[i]; });
    return o;
  });
}

// Revisa que estén las solapas y columnas de Datos. Devuelve { nombre: filas } y, en "faltan", las solapas incompletas.
function planTablas(tablas, aviso) {
  var res = {}, faltan = {};
  Object.keys(PLAN_REQUERIDAS).forEach(function (nombre) {
    var t = tablas[nombre];
    if (!t || !t.cols) {
      faltan[nombre] = true;
      aviso("Falta una solapa en Datos", "No está la solapa " + nombre + ".");
      return;
    }
    var cols = t.cols.map(planMin);
    var sin = PLAN_REQUERIDAS[nombre].filter(function (c) { return cols.indexOf(c) < 0; });
    if (sin.length) {
      faltan[nombre] = true;
      aviso("Falta una columna en Datos", nombre + ": falta " + sin.join(", ") + ".");
      return;
    }
    res[nombre] = planObjetos(t);
  });
  return { filas: res, faltan: faltan };
}

// ---------------------------------------------------------------------------------------------------------------
// LA CUENTA PRINCIPAL
// entrada = { hoy: "AAAA-MM-DD", tablas: { Ventas: {cols, filas}, ... }, config: { "texto del parámetro": valor },
//             proyeccion: {cols, filas} }  (proyeccion = la solapa Ventas proyectadas, desde la fila de encabezados)
// ---------------------------------------------------------------------------------------------------------------

function calcularPlan(entrada) {
  var controles = [];
  var vistos = {};
  var aviso = function (tipo, detalle) {   // el mismo aviso no se repite
    if (vistos[tipo + "|" + detalle]) return;
    vistos[tipo + "|" + detalle] = true;
    controles.push({ tipo: tipo, detalle: detalle });
  };
  var leidas = planTablas(entrada.tablas || {}, aviso);
  var T = leidas.filas;
  var falta = function (nombre) { return !!leidas.faltan[nombre]; };
  var parteOk = function (parte) {
    var sin = PLAN_PARTES[parte].filter(falta);
    return sin.length === 0;
  };
  var lista = function (nombre) { return T[nombre] || []; };

  // ---- Config: lo cargado, o el valor por defecto.
  var cfg = {};
  Object.keys(entrada.config || {}).forEach(function (k) { cfg[planMin(k)] = entrada.config[k]; });
  var valor = function (clave) {
    var p = PLAN_PARAMETROS.filter(function (x) { return x[0] === clave; })[0];
    var v = cfg[planMin(p[1])];
    return planTexto(v) === "" ? null : v;
  };
  var entero = function (clave, def, min, max) {
    var n = planNum(valor(clave));
    if (n == null) return def;
    return Math.min(max, Math.max(min, Math.round(n)));
  };
  var hoy = entrada.hoy;
  var inicio = planDia(valor("inicio")) || hoy;
  var meses = entero("meses", 6, 1, 24);
  var mesIni = inicio.slice(0, 7);
  var listaMeses = [];
  for (var k = 0; k < meses; k++) listaMeses.push(planMesMas(mesIni, k));
  var fin = planDiaDelMes(listaMeses[listaMeses.length - 1], 31);
  var diaFijos = entero("diaFijos", 5, 1, 31), diaPub = entero("diaPub", 12, 1, 31), diaFlex = entero("diaFlex", 10, 1, 31);
  var diasCobro = entero("diasCobro", 7, 0, 120), plazo = entero("plazo", 120, 0, 1000);
  var cajaMinima = planNum(valor("cajaMinima"));
  if (cajaMinima == null) aviso("Falta la caja mínima", "Config: sin caja mínima no se calcula cuánto tienen que poner los socios.");

  // Dólar del plan: el cargado, o el último oficial comprador hasta el inicio.
  var dolarDatos = null, diaDolar = "";
  lista("dolar").forEach(function (r) {
    var d = planDia(r.fecha), c = planNum(r.compra);
    if (d && c && d <= inicio && d >= diaDolar) { diaDolar = d; dolarDatos = c; }
  });
  var dolar = planNum(valor("dolar")) || dolarDatos || 0;
  if (!dolar) aviso("Falta el dólar", "No hay dólar en Datos ni en Config: lo que está en USD queda en $ 0.");
  var aPesos = function (moneda, importe) { return planMin(moneda) === "usd" ? importe * dolar : importe; };

  // ---- Ventas: solo las que cuentan (sin canceladas ni devueltas).
  var ventas = lista("Ventas").map(function (r) {
    return {
      dia: planDia(r.fecha), sku: planSku(r.sku), u: planN(r.unidades), ing: planN(r.ingresos_productos), neto: planN(r.total_neto),
      ml: /mercado|^ml$/.test(planMin(r.canal)), conocido: planMin(r.sku_conocido) !== "no",
      cuenta: !/cancelad|devuelt/.test(planMin(r.estado))
    };
  }).filter(function (v) { return v.dia && v.cuenta; });

  // Últimos 90 días antes del inicio: base del sugerido, del precio y del reparto entre canales.
  var desde90 = planMas(inicio, -90);
  var por90 = {}, desconocidas = 0;
  ventas.forEach(function (v) {
    if (v.dia < desde90 || v.dia >= inicio) return;
    if (!v.conocido || !v.sku) { desconocidas++; return; }
    var s = por90[v.sku] || (por90[v.sku] = { u: 0, ing: 0, uMl: 0 });
    s.u += v.u; s.ing += v.ing; if (v.ml) s.uMl += v.u;
  });
  if (desconocidas) aviso("Ventas sin código conocido", desconocidas + " ventas de los últimos 90 días tienen un código que no está en Productos: no cuentan en el sugerido.");
  var sugerido = function (sku) { var s = por90[sku]; return s ? Math.round(s.u / 3) : 0; };
  var precioProm = function (sku) { var s = por90[sku]; return s && s.u > 0 ? s.ing / s.u : 0; };
  var parteMl = function (sku) { var s = por90[sku]; return s && s.u > 0 ? s.uMl / s.u : 1; };

  // ---- Históricos de los últimos 3 meses cerrados.
  var mesesHist = [planMesMas(mesIni, -3), planMesMas(mesIni, -2), planMesMas(mesIni, -1)];
  var enHist = function (mes) { return mesesHist.indexOf(mes) >= 0; };
  var ingH = 0, netoH = 0, ingMlH = 0, ingMlPorMes = {};
  ventas.forEach(function (v) {
    var mes = v.dia.slice(0, 7);
    if (!enHist(mes)) return;
    ingH += v.ing; netoH += v.neto;
    if (v.ml) { ingMlH += v.ing; ingMlPorMes[mes] = (ingMlPorMes[mes] || 0) + v.ing; }
  });
  var pubH = 0;
  lista("ml_publicidad").forEach(function (r) { var d = planDia(r.fecha); if (d && enHist(d.slice(0, 7))) pubH += planN(r.costo); });
  var flexH = 0, ingMlConFlex = 0, mesesFlex = {};
  lista("Logistica_flex").forEach(function (r) {
    var mes = planMes(r.periodo);
    if (enHist(mes)) { flexH += planN(r.importe); mesesFlex[mes] = true; }
  });
  Object.keys(mesesFlex).forEach(function (m) { ingMlConFlex += ingMlPorMes[m] || 0; });
  var hist = {
    pctCobro: ingH > 0 ? netoH / ingH : null,
    pctPub: falta("ml_publicidad") ? null : (ingMlH > 0 ? pubH / ingMlH : 0),
    pctFlex: ingMlConFlex > 0 ? flexH / ingMlConFlex : 0
  };
  if (hist.pctCobro == null) aviso("Sin histórico de cobro", "No hay ventas en los últimos 3 meses: el % que se cobra queda en 0 si no se carga en Config.");
  if (falta("ml_publicidad")) aviso("Sin publicidad", "No se pudo leer la publicidad de Mercado Libre: queda en 0 % si no se carga en Config.");
  if (!Object.keys(mesesFlex).length) aviso("Sin facturas de Flex", "No hay facturas de Flex en los últimos 3 meses: la Flex queda en 0 % si no se carga en Config.");
  var pct = function (clave) { var c = planPct(valor(clave)); return c != null ? c : (hist[clave] || 0); };
  var pctCobro = pct("pctCobro"), pctPub = pct("pctPub"), pctFlex = pct("pctFlex");

  // ---- Productos.
  var productos = {}, activos = [];
  lista("Productos").forEach(function (r) {
    var s = planSku(r.sku);
    if (!s || productos[s]) return;
    productos[s] = planTexto(r.producto);
    if (planMin(r.activo) !== "no") activos.push(s);
  });

  // ---- Socios y reparto de los aportes.
  var socios = [];
  lista("Capital").forEach(function (r) { var s = planTexto(r.socio); if (s && socios.indexOf(s) < 0) socios.push(s); });
  Object.keys(entrada.config || {}).forEach(function (k) {
    var m = planTexto(k).match(/^aporte de (.+?)\s*\(%\)$/i);
    if (m && socios.map(planMin).indexOf(planMin(m[1])) < 0) socios.push(m[1]);
  });
  var etiquetaSocio = function (s) { return PLAN_PREFIJO_SOCIO + s + " (%)"; };
  var reparto = socios.map(function (s) { return planPct(cfg[planMin(etiquetaSocio(s))]); });
  var cargados = reparto.filter(function (x) { return x != null; });
  var suma = cargados.reduce(function (a, b) { return a + b; }, 0);
  if (!cargados.length || cargados.length < socios.length || Math.abs(suma - 1) > 0.001) {
    if (cargados.length) aviso("El reparto no da 100 %", "Config: los aportes de los socios suman " + Math.round(suma * 1000) / 10 + " %: se reparte en partes iguales.");
    reparto = socios.map(function () { return 1 / socios.length; });
  }

  // ---- Proyección de ventas: completar filas que faltan y decidir las unidades y el precio de cada mes.
  // (no se usa planObjetos acá: hace falta saber en qué fila de la planilla está cada una)
  var filasProy = [];
  (entrada.proyeccion && entrada.proyeccion.filas || []).forEach(function (f, i) {
    var cols = (entrada.proyeccion.cols || []).map(planMin), o = {};
    cols.forEach(function (c, j) { if (c && !(c in o)) o[c] = f[j]; });
    o._fila = i;
    filasProy.push(o);
  });
  var plan = {};            // "mes|sku" → { u, precio }
  var actualizar = [], nuevas = [], yaEsta = {};
  if (parteOk("proyeccion")) {
    filasProy.forEach(function (r) {
      var mes = planMes(r.mes), sku = planSku(r.sku);
      if (!mes || !sku) return;
      var clave = mes + "|" + sku;
      if (yaEsta[clave]) { aviso("Fila repetida en Ventas proyectadas", mes + " " + sku + ": se usa solo la primera."); return; }
      yaEsta[clave] = true;
      if (!(sku in productos)) aviso("Código que no está en Productos", "Ventas proyectadas: " + sku + " (" + mes + ").");
      var sug = mes >= mesIni ? sugerido(sku) : planN(r.sugerido);   // los meses pasados conservan su sugerido
      if (mes >= mesIni) actualizar.push({ fila: r._fila, producto: productos[sku] || "", sugerido: sug });
      var u = planNum(r.unidades);
      var precio = planNum(r.precio_unitario);
      plan[clave] = { mes: mes, sku: sku, u: u != null ? u : sug, precio: precio > 0 ? precio : precioProm(sku) };
    });
    listaMeses.forEach(function (mes) {
      activos.forEach(function (sku) {
        var clave = mes + "|" + sku;
        if (yaEsta[clave]) return;
        yaEsta[clave] = true;
        nuevas.push({ mes: mes, sku: sku, producto: productos[sku], sugerido: sugerido(sku) });
        plan[clave] = { mes: mes, sku: sku, u: sugerido(sku), precio: precioProm(sku) };
      });
    });
    Object.keys(plan).forEach(function (c) {
      var p = plan[c];
      if (p.u > 0 && !(p.precio > 0) && p.mes >= mesIni) aviso("Sin precio", "Ventas proyectadas: " + p.sku + " (" + p.mes + ") no tiene precio cargado ni ventas en los últimos 90 días.");
    });
  }
  var porDiaMes = function (mes, sku) {   // unidades proyectadas por día de ese mes
    var p = plan[mes + "|" + sku];
    return p ? p.u / planDiasMes(mes) : 0;
  };

  // ---- Contenedores y pagos (los usan stock, contenedores y caja).
  var conts = {}, ordenConts = [];
  lista("Contenedores").forEach(function (r) {
    var k = planMin(r.contenedor);
    if (!k || conts[k]) return;
    conts[k] = {
      nombre: planTexto(r.contenedor), proveedor: planTexto(r.proveedor), estado: planMin(r.estado),
      estimada: planDia(r.llegada_estimada), real: planDia(r.llegada_real), fob: planNum(r.fob_usd)
    };
    ordenConts.push(k);
  });
  var pagos = lista("Contenedor_pagos").map(function (r) {
    var imp = planN(r.importe), usd = planMin(r.moneda) === "usd";
    var dolFila = planNum(r.dolar);
    return {
      dia: planDia(r.fecha), cont: planMin(r.contenedor), concepto: planMin(r.concepto),
      usd: usd ? imp : (dolFila > 0 ? imp / dolFila : (dolar ? imp / dolar : 0)),
      pesos: usd ? imp * dolar : imp,
      previsto: planMin(r.estado) === "previsto", empresa: planMin(r.pagado_por) !== "socios"
    };
  }).filter(function (p) { return p.dia || p.usd; });
  pagos.forEach(function (p) {
    if (p.cont && !conts[p.cont] && !falta("Contenedores")) aviso("Pago de un contenedor que no existe", "Contenedor_pagos: " + p.cont + " no está en Contenedores.");
  });

  // ---- STOCK
  var stock = null;
  if (parteOk("stock")) {
    stock = calcularStock_();
  }
  function calcularStock_() {
    var antes = planMas(inicio, -1);   // stock al cierre del día anterior al inicio
    var conteo = {};                   // sku → { dia, u } (el último hasta "antes")
    lista("Stock_conteo").forEach(function (r) {
      var d = planDia(r.fecha), s = planSku(r.sku);
      if (!d || !s || d > antes) return;
      if (!conteo[s] || d >= conteo[s].dia) conteo[s] = { dia: d, u: planN(r.unidades) };
    });
    var llegadasReales = [], llegadasEst = {};   // estimadas: sku → { dia: unidades }
    var avisados = {};
    lista("Contenedor_productos").forEach(function (r) {
      var c = conts[planMin(r.contenedor)], s = planSku(r.sku), u = planN(r.unidades);
      if (!c || !s) return;
      if (c.real) { llegadasReales.push({ sku: s, dia: c.real, u: u }); return; }
      if (c.estado === "nacionalizado") return;
      if (!c.estimada) {
        aviso("Contenedor sin llegada estimada", c.nombre + ": no tiene llegada estimada (no suma al stock proyectado).");
        return;
      }
      var d = c.estimada;
      if (d < inicio) {
        if (!avisados[c.nombre]) aviso("Llegada estimada vencida", c.nombre + ": la llegada estimada (" + d + ") ya pasó y no tiene llegada real. Se toma como que llega al inicio.");
        avisados[c.nombre] = true;
        d = inicio;
      }
      var m = llegadasEst[s] || (llegadasEst[s] = {});
      m[d] = (m[d] || 0) + u;
    });
    var mermas = lista("Mermas").map(function (r) { return { dia: planDia(r.fecha), sku: planSku(r.sku), u: planN(r.unidades) }; });
    var skus = activos.slice();
    Object.keys(plan).forEach(function (c) {
      var p = plan[c];
      if (p.u > 0 && p.mes >= mesIni && skus.indexOf(p.sku) < 0) skus.push(p.sku);
    });
    var finMes = listaMeses.map(function (m) { return planDiaDelMes(m, 31); });
    var filas = skus.map(function (s) {
      var base = conteo[s], desde = base ? base.dia : "0000-00-00", st = base ? base.u : 0;
      llegadasReales.forEach(function (x) { if (x.sku === s && x.dia > desde && x.dia <= antes) st += x.u; });
      ventas.forEach(function (v) { if (v.conocido && v.sku === s && v.dia > desde && v.dia <= antes) st -= v.u; });
      mermas.forEach(function (x) { if (x.sku === s && x.dia > desde && x.dia <= antes) st -= x.u; });
      var alEmpezar = st, alFinal = [], sinStock = st < 0 ? inicio : "";
      // Día por día: entra lo que llega ese día y sale lo proyectado.
      for (var n = planDiaNum(inicio), nFin = planDiaNum(fin); n <= nFin; n++) {
        var d = planNumDia(n);
        st += (llegadasEst[s] && llegadasEst[s][d]) || 0;
        st -= porDiaMes(d.slice(0, 7), s);
        if (!sinStock && st < -1e-9) sinStock = d;
        var i = finMes.indexOf(d);
        if (i >= 0) alFinal[i] = st;
      }
      var pedir = sinStock ? planMas(sinStock, -plazo) : "";
      if (alEmpezar < 0) aviso("Stock negativo", s + ": da " + Math.round(alEmpezar) + " unidades al empezar el plan.");
      return {
        sku: s, producto: productos[s] || "", sinConteo: !base, alEmpezar: alEmpezar, alFinal: alFinal,
        sinStock: sinStock, pedirAntes: pedir, urgente: !!pedir && pedir <= planDiaDelMes(mesIni, 31)
      };
    });
    return { meses: listaMeses, filas: filas };
  }

  // ---- CONTENEDORES (los que no están nacionalizados)
  var contenedores = null;
  if (parteOk("contenedores")) {
    contenedores = ordenConts.filter(function (k) { return conts[k].estado !== "nacionalizado"; }).map(function (k) {
      var c = conts[k], pagado = 0, previsto = 0, otros = 0, proximo = "";
      pagos.forEach(function (p) {
        if (p.cont !== k) return;
        var contraFob = p.concepto === "anticipo" || p.concepto === "saldo";
        if (p.previsto) {
          if (contraFob) previsto += p.usd; else otros += p.usd;
          if (p.dia && (!proximo || p.dia < proximo)) proximo = p.dia;
        } else if (contraFob) pagado += p.usd;
      });
      var sinProgramar = c.fob != null ? c.fob - pagado - previsto : null;
      if (sinProgramar != null && sinProgramar > 0.5) aviso("Contenedor con pagos sin programar", c.nombre + ": faltan USD " + Math.round(sinProgramar) + " sin fecha de pago (no están en la caja).");
      if (!c.real && !c.estimada) aviso("Contenedor sin llegada estimada", c.nombre + ": no tiene llegada estimada (no suma al stock proyectado).");
      return {
        contenedor: c.nombre, proveedor: c.proveedor, estado: c.estado, estimada: c.estimada, fob: c.fob,
        pagado: pagado, previsto: previsto, proximo: proximo, otrosPrevistos: otros, sinProgramar: sinProgramar
      };
    });
  }

  // ---- CAJA SEMANAL
  var caja = null;
  if (parteOk("caja")) caja = calcularCaja_();
  function calcularCaja_() {
    var lunes0 = planLunes(inicio), finSemana = planMas(planLunes(fin), 6);
    var nSem = (planDiaNum(finSemana) - planDiaNum(lunes0) + 1) / 7;
    var sem = [];
    for (var i = 0; i < nSem; i++) {
      sem.push({ desde: planMas(lunes0, i * 7), hasta: planMas(lunes0, i * 7 + 6), mp: 0, cobros: 0, contenedores: 0, fijos: 0, deudas: 0, pub: 0, flex: 0 });
    }
    // En qué semana cae un día (antes de la primera → la primera; después de la última → afuera).
    var semana = function (d) {
      if (d > finSemana) return null;
      if (d < lunes0) return sem[0];
      return sem[Math.floor((planDiaNum(d) - planDiaNum(lunes0)) / 7)];
    };
    // Caja al empezar: último saldo del banco + último disponible de Mercado Pago, hasta el inicio.
    var ultimo = function (filas, col) {
      var r = { dia: "", v: 0 };
      filas.forEach(function (x) { var d = planDia(x.fecha), v = planNum(x[col]); if (d && v != null && d <= inicio && d >= r.dia) { r.dia = d; r.v = v; } });
      return r;
    };
    var banco = ultimo(lista("galicia_saldo"), "saldo"), mp = ultimo(lista("mp_saldo"), "disponible");
    if (!banco.dia) aviso("Falta el saldo del banco", "No hay saldo del banco hasta el inicio: la caja arranca sin el banco.");
    if (!mp.dia) aviso("Falta el saldo de Mercado Pago", "No hay saldo de Mercado Pago hasta el inicio: la caja arranca sin Mercado Pago.");
    [["banco", banco], ["Mercado Pago", mp]].forEach(function (x) {
      if (x[1].dia && planDiaNum(inicio) - planDiaNum(x[1].dia) > 7) aviso("Saldo viejo", "El último saldo de " + x[0] + " es del " + x[1].dia + ".");
    });
    var apertura = banco.v + mp.v;
    // Lo vendido que Mercado Pago todavía no liberó.
    var desdeMp = mp.dia || planMas(inicio, -1);
    lista("mp_movimientos").forEach(function (r) {
      var d = planDia(r.fecha_liberacion);
      if (!d || d <= desdeMp) return;
      var s = semana(d); if (s) s.mp += planN(r.monto_neto);
    });
    // Ventas proyectadas: se cobran "días hasta cobrar" después, parejo día por día.
    var plataMes = {}, plataMesMl = {};
    Object.keys(plan).forEach(function (c) {
      var p = plan[c], v = p.u * p.precio;
      plataMes[p.mes] = (plataMes[p.mes] || 0) + v;
      plataMesMl[p.mes] = (plataMesMl[p.mes] || 0) + v * parteMl(p.sku);
    });
    for (var n = planDiaNum(inicio), nFin = planDiaNum(fin); n <= nFin; n++) {
      var d = planNumDia(n), mes = d.slice(0, 7);
      var s = semana(planMas(d, diasCobro));
      if (s) s.cobros += (plataMes[mes] || 0) / planDiasMes(mes) * pctCobro;
    }
    // Pagos previstos de contenedores que paga la empresa.
    var vencidos = 0;
    pagos.forEach(function (p) {
      if (!p.previsto || !p.empresa || !p.dia) return;
      if (p.dia < inicio) vencidos++;
      var s = semana(p.dia); if (s) s.contenedores += p.pesos;
    });
    if (vencidos) aviso("Pago previsto vencido", vencidos + " pagos de contenedores marcados como previstos tienen fecha anterior al inicio: se ponen en la primera semana.");
    // Gastos fijos vigentes, el día de pago de cada mes (si ese día ya pasó en el mes del inicio, se da por pagado).
    listaMeses.forEach(function (mes) {
      var d = planDiaDelMes(mes, diaFijos);
      if (d < inicio) return;
      var s = semana(d);
      if (!s) return;
      lista("Gastos_fijos").forEach(function (r) {
        var desde = planMes(r.desde) || "0000-00", hasta = planMes(r.hasta) || "9999-99";
        if (desde <= mes && mes <= hasta) s.fijos += aPesos(r.moneda, planN(r.importe_mensual));
      });
    });
    // Publicidad y Flex de cada mes: la factura se paga el mes siguiente (las de meses anteriores al inicio ya están en Deudas).
    listaMeses.forEach(function (mes) {
      var sigue = planMesMas(mes, 1);
      var sp = semana(planDiaDelMes(sigue, diaPub)); if (sp) sp.pub += (plataMesMl[mes] || 0) * pctPub;
      var sf = semana(planDiaDelMes(sigue, diaFlex)); if (sf) sf.flex += (plataMesMl[mes] || 0) * pctFlex;
    });
    // Deudas sin pagar, por vencimiento (sin vencimiento o vencidas → la primera semana).
    var deudasViejas = 0;
    lista("Deudas").forEach(function (r) {
      var pagada = /^s[ií]$/.test(planMin(r.pagada)) || planDia(r.fecha_pago);
      if (pagada) return;
      var d = planDia(r.vencimiento);
      if (!d || d < inicio) { deudasViejas++; d = inicio; }
      var s = semana(d); if (s) s.deudas += aPesos(r.moneda, planN(r.importe));
    });
    if (deudasViejas) aviso("Deudas vencidas o sin vencimiento", deudasViejas + " deudas sin pagar no tienen vencimiento o ya vencieron: se ponen en la primera semana.");
    // Semana por semana: caja al final, y si baja del mínimo, cuánto tienen que poner los socios.
    var caja = apertura, sinAportes = apertura, peor = null, totalSocios = socios.map(function () { return 0; });
    sem.forEach(function (s) {
      s.inicio = caja;
      var mov = s.mp + s.cobros - s.contenedores - s.fijos - s.deudas - s.pub - s.flex;
      s.final = caja + mov;
      sinAportes += mov;
      if (!peor || sinAportes < peor.caja) peor = { caja: sinAportes, desde: s.desde };
      s.aporte = cajaMinima != null && s.final < cajaMinima ? cajaMinima - s.final : 0;
      s.final += s.aporte;
      s.socios = reparto.map(function (r, j) { totalSocios[j] += s.aporte * r; return s.aporte * r; });
      caja = s.final;
    });
    return {
      semanas: sem, socios: socios, apertura: apertura, diaBanco: banco.dia, diaMp: mp.dia,
      peor: peor, totalSocios: totalSocios, totalAportes: totalSocios.reduce(function (a, b) { return a + b; }, 0)
    };
  }

  // ---- REAL CONTRA PROYECTADO (meses de la proyección que ya empezaron)
  var real = null;
  if (parteOk("real") && parteOk("proyeccion")) {
    var mesesP = {};
    Object.keys(plan).forEach(function (c) { if (plan[c].mes <= mesIni) mesesP[plan[c].mes] = true; });
    var filasR = {};
    var fila = function (mes, sku) { return filasR[mes + "|" + sku] || (filasR[mes + "|" + sku] = { mes: mes, sku: sku, uP: 0, uR: 0, pP: 0, pR: 0 }); };
    Object.keys(plan).forEach(function (c) {
      var p = plan[c];
      if (!mesesP[p.mes]) return;
      var f = fila(p.mes, p.sku); f.uP += p.u; f.pP += p.u * p.precio;
    });
    ventas.forEach(function (v) {
      var mes = v.dia.slice(0, 7);
      if (!mesesP[mes] || !v.conocido || !v.sku) return;
      var f = fila(mes, v.sku); f.uR += v.u; f.pR += v.ing;
    });
    real = Object.keys(filasR).map(function (k) { return filasR[k]; })
      .filter(function (f) { return f.uP || f.uR; })
      .map(function (f) { f.producto = productos[f.sku] || ""; f.dif = f.uR - f.uP; f.difPesos = f.pR - f.pP; return f; })
      .sort(function (a, b) { return a.mes < b.mes ? -1 : a.mes > b.mes ? 1 : Math.abs(b.difPesos) - Math.abs(a.difPesos); });
  }

  // Lo que se muestra en Config, columna "si queda vacío".
  var porDefecto = {
    inicio: hoy, meses: 6, cajaMinima: "sin mínimo: no se calculan aportes", dolar: dolarDatos || "no hay dólar en Datos",
    diaFijos: 5, diaPub: 12, diaFlex: 10, diasCobro: 7,
    pctCobro: hist.pctCobro != null ? hist.pctCobro : "sin ventas en los últimos 3 meses",
    pctPub: hist.pctPub != null ? hist.pctPub : "sin datos de publicidad", pctFlex: hist.pctFlex, plazo: 120
  };

  var faltanPartes = Object.keys(PLAN_PARTES).filter(function (p) { return !parteOk(p); }).map(function (p) {
    return { parte: p, solapas: PLAN_PARTES[p].filter(falta) };
  });

  return {
    hoy: hoy, inicio: inicio, fin: fin, meses: listaMeses, dolar: dolar,
    supuestos: { pctCobro: pctCobro, pctPub: pctPub, pctFlex: pctFlex, diasCobro: diasCobro, plazo: plazo, cajaMinima: cajaMinima },
    porDefecto: porDefecto, socios: socios, etiquetasSocios: socios.map(etiquetaSocio), reparto: reparto,
    proyeccion: { actualizar: actualizar, nuevas: nuevas },
    stock: stock, contenedores: contenedores, caja: caja, real: real,
    faltanPartes: faltanPartes, controles: controles
  };
}
