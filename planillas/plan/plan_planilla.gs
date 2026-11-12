/**
 * plan_planilla.gs — arma la planilla "Plan", lee Datos, recalcula y escribe los resultados.
 *
 * QUÉ ES EL PLAN
 * --------------
 * Una planilla de Google que mira hacia adelante: con las ventas que se proyectan, cuándo se queda sin stock cada
 * producto, cuánta plata hay en caja cada semana y cuánto tienen que poner los socios si la caja baja del mínimo.
 * Las cuentas están en plan_calculo.gs; este archivo solo lee, escribe y da formato.
 *
 *  - El cliente carga en el Plan SOLO dos cosas: la solapa Config y la solapa Ventas proyectadas (naranjas).
 *  - Todo lo demás sale de la planilla Datos, que el Plan solo LEE: contenedores (los que vienen y los planeados) y sus
 *    pagos (los hechos y los previstos), saldos, ventas, gastos fijos, deudas. Los contenedores no se cargan en el Plan.
 *  - Las pantallas (azules) las escribe el script. Se recalculan solas cada hora.
 *
 * POR QUÉ ES UN PROYECTO INDEPENDIENTE
 * ------------------------------------
 * Igual que el importador de Datos: un script atado a la planilla lo podría ver o cambiar cualquier editor, y el
 * disparador corre con la cuenta de quien lo instaló. Por eso vive aparte, sin compartir, y abre las planillas por id.
 *
 * CÓMO SE INSTALA (una vez)
 * -------------------------
 *  1. Crear una planilla vacía (será el Plan) y copiar su id (lo que está entre /d/ y /edit en la dirección).
 *  2. En script.google.com → Nuevo proyecto. Pegar plan_calculo.gs y plan_planilla.gs (dos archivos) y guardar.
 *  3. Acá abajo, poner el id de Datos en ID_DATOS y el del Plan en ID_PLAN.
 *  4. Ejecutar armarPlan (la primera vez pide autorizar: aceptar), después recalcularPlan y después instalarDisparador.
 *
 * SI SE COPIA A OTRA CUENTA: repetir los pasos 2 a 4 con los ids nuevos (el disparador no viaja con la copia).
 *
 * Lo que pasó en cada corrida queda en la solapa Registro y en Ejecuciones del proyecto.
 */

var ID_DATOS = "PONER_ID_DATOS";
var ID_PLAN = "PONER_ID_PLAN";

var ZONA = "America/Argentina/Buenos_Aires";
var NARANJA = "#fce5cd", AZUL = "#cfe2f3", GRIS = "#eeeeee", ROJO = "#f4cccc", AMARILLO = "#fff2cc";
var F_PESOS = "#,##0", F_USD = "#,##0", F_FECHA = "dd/mm/yyyy", F_PCT = "0.0%", F_UNID = "#,##0";

// En Datos, las LISTAS (las llena el importador) tienen el encabezado en la fila 1; las CARGAS, en la fila 2.
var LISTAS_DATOS = ["Ventas", "galicia_saldo", "mp_saldo", "mp_movimientos", "ml_publicidad", "dolar"];

var SOLAPAS = ["Leeme", "Config", "Ventas proyectadas", "Caja semanal", "Stock proyectado", "Contenedores",
  "Real vs proyectado", "Controles", "Registro"];
var CARGAS_PLAN = ["Config", "Ventas proyectadas"];

// Ventas proyectadas: fila 1 = ayuda, fila 2 = encabezados, datos desde la fila 3 (igual que las cargas de Datos).
var COLS_PROY = [
  ["mes", "Mes de la venta, como 2026-12."],
  ["sku", "Código del producto."],
  ["producto", "Lo completa el Plan."],
  ["sugerido", "Lo completa el Plan: unidades vendidas en los últimos 90 días dividido 3. Si 'unidades' queda vacío, se usa este."],
  ["unidades", "Las unidades que piensan vender ese mes. Vacío = se usa el sugerido."],
  ["precio_unitario", "Precio de venta por unidad, en pesos. Vacío = el promedio de los últimos 90 días."],
  ["notas", ""]
];
var AYUDA_PROY = "Una fila por producto y mes. El Plan agrega solo las filas que faltan y completa 'producto' y 'sugerido'. " +
  "Ustedes cargan 'unidades' (y 'precio_unitario' si cambia el precio). Lo que cargan nunca se borra.";

// ---------------------------------------------------------------------------------------------------------------
// Lo que se corre desde el editor
// ---------------------------------------------------------------------------------------------------------------

// Crea o completa las solapas. Se puede correr las veces que haga falta: nunca borra lo que cargó el cliente.
function armarPlan() {
  var ss = SpreadsheetApp.openById(ID_PLAN);
  ss.setSpreadsheetTimeZone(ZONA);
  ss.setSpreadsheetLocale("es_AR");
  SOLAPAS.forEach(function (n) { if (!ss.getSheetByName(n)) ss.insertSheet(n, ss.getNumSheets()); });
  _armarConfig_(ss, null);
  _armarProyeccion_(ss);
  _armarLeeme_(ss);
  var reg = ss.getSheetByName("Registro");
  if (!reg.getLastRow()) { reg.getRange(1, 1, 1, 4).setValues([["cuándo", "qué", "resultado", "detalle"]]).setFontWeight("bold"); reg.setFrozenRows(1); }
  SOLAPAS.forEach(function (n, i) {
    var h = ss.getSheetByName(n);
    try { ss.setActiveSheet(h); ss.moveActiveSheet(i + 1); } catch (e) { /* si Google no deja moverla, no importa */ }
    h.setTabColor(CARGAS_PLAN.indexOf(n) >= 0 ? NARANJA : AZUL);
    if (CARGAS_PLAN.indexOf(n) < 0 && !h.getProtections(SpreadsheetApp.ProtectionType.SHEET).length) {
      h.protect().setDescription("Pantalla: la escribe el Plan").setWarningOnly(true);
    }
  });
  ["Hoja 1", "Hoja1", "Sheet1"].forEach(function (n) { var h = ss.getSheetByName(n); if (h && ss.getSheets().length > 1) ss.deleteSheet(h); });
  _registrar_(ss, "armarPlan", "OK", "solapas listas");
}

// Lee Datos y el Plan, calcula y escribe las pantallas. Es lo que corre el disparador cada hora.
function recalcularPlan() {
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(1000)) return;   // ya hay una corrida en marcha
  var ss = SpreadsheetApp.openById(ID_PLAN), t0 = Date.now();
  try {
    // 1) Leer todo.
    var datos = SpreadsheetApp.openById(ID_DATOS);
    var tablas = {};
    Object.keys(PLAN_REQUERIDAS).forEach(function (nombre) {
      var h = datos.getSheetByName(nombre);
      if (!h || !h.getLastRow()) return;
      var filaEnc = LISTAS_DATOS.indexOf(nombre) >= 0 ? 1 : 2;
      var v = h.getDataRange().getValues();
      if (v.length < filaEnc) return;
      tablas[nombre] = { cols: v[filaEnc - 1], filas: v.slice(filaEnc) };
    });
    var config = _leerConfig_(ss);
    var hp = ss.getSheetByName("Ventas proyectadas");
    var vp = hp.getLastRow() >= 2 ? hp.getRange(2, 1, hp.getLastRow() - 1, Math.max(hp.getLastColumn(), 1)).getValues() : [[]];
    var proyeccion = { cols: vp[0], filas: vp.slice(1) };

    // 2) Calcular todo antes de escribir (si algo falla, las pantallas quedan como estaban).
    var res = calcularPlan({ hoy: planDia(new Date()), tablas: tablas, config: config, proyeccion: proyeccion });

    // 3) Escribir.
    _armarConfig_(ss, res);
    _escribirProyeccion_(hp, proyeccion, res);
    _escribirCaja_(ss, res);
    _escribirStock_(ss, res);
    _escribirContenedores_(ss, res);
    _escribirReal_(ss, res);
    _escribirControles_(ss, res);
    _registrar_(ss, "recalcularPlan", "OK", res.controles.length + " avisos; " + Math.round((Date.now() - t0) / 1000) + " s");
  } catch (e) {
    _registrar_(ss, "recalcularPlan", "ERROR", String(e && e.stack || e));
    throw e;
  } finally {
    lock.releaseLock();
  }
}

// El recálculo automático: cada hora, cerca de los 10 minutos (después del importador de Datos). Sin duplicados.
function instalarDisparador() {
  quitarDisparador();
  ScriptApp.newTrigger("recalcularPlan").timeBased().everyHours(1).nearMinute(10).create();
  _registrar_(SpreadsheetApp.openById(ID_PLAN), "instalarDisparador", "OK", "recalcularPlan cada hora");
}
function quitarDisparador() {
  ScriptApp.getProjectTriggers().forEach(function (t) { if (t.getHandlerFunction() === "recalcularPlan") ScriptApp.deleteTrigger(t); });
}

// ---------------------------------------------------------------------------------------------------------------
// Config y Ventas proyectadas (las cargas del cliente)
// ---------------------------------------------------------------------------------------------------------------

// Config: parámetro | valor | si queda vacío | qué es. Busca cada parámetro por su texto; agrega los que faltan
// (también una fila por socio) y solo escribe las columnas C y D. La columna B (lo que carga el cliente) no se toca.
function _armarConfig_(ss, res) {
  var h = ss.getSheetByName("Config");
  if (!h.getLastRow()) {
    h.getRange(1, 1, 1, 4).setValues([["parámetro", "valor", "si queda vacío", "qué es"]]).setFontWeight("bold").setBackground(NARANJA);
    h.setFrozenRows(1);
    h.setColumnWidth(1, 260); h.setColumnWidth(2, 140); h.setColumnWidth(3, 200); h.setColumnWidth(4, 520);
  }
  var etiquetas = h.getLastRow() > 1 ? h.getRange(2, 1, h.getLastRow() - 1, 1).getValues().map(function (f) { return planMin(f[0]); }) : [];
  var filaDe = function (texto) {
    var i = etiquetas.indexOf(planMin(texto));
    if (i >= 0) return i + 2;
    h.appendRow([texto]);
    etiquetas.push(planMin(texto));
    return etiquetas.length + 1;
  };
  var formatos = { inicio: F_FECHA, cajaMinima: F_PESOS, dolar: "#,##0.00", pctCobro: F_PCT, pctPub: F_PCT, pctFlex: F_PCT };
  PLAN_PARAMETROS.forEach(function (p) {
    var f = filaDe(p[1]);
    h.getRange(f, 4).setValue(p[2]).setWrap(true);
    var fmt = formatos[p[0]] || "0";
    h.getRange(f, 2, 1, 2).setNumberFormat(fmt);
    if (res) {
      var d = res.porDefecto[p[0]];
      h.getRange(f, 3).setValue(p[0] === "inicio" ? _fecha_(d) : d);
    }
  });
  if (res) {
    res.etiquetasSocios.forEach(function (et, i) {
      var f = filaDe(et);
      h.getRange(f, 2, 1, 2).setNumberFormat(F_PCT);
      h.getRange(f, 3).setValue(1 / res.socios.length);
      h.getRange(f, 4).setValue("Qué parte de cada aporte pone este socio. Entre todos tienen que sumar 100 %. Vacío = partes iguales.");
    });
  }
  h.getRange(2, 3, Math.max(h.getLastRow() - 1, 1), 2).setBackground(GRIS).setFontColor("#555555");
}

function _leerConfig_(ss) {
  var h = ss.getSheetByName("Config"), cfg = {};
  if (!h || h.getLastRow() < 2) return cfg;
  h.getRange(2, 1, h.getLastRow() - 1, 2).getValues().forEach(function (f) { if (planTexto(f[0])) cfg[planTexto(f[0])] = f[1]; });
  return cfg;
}

function _armarProyeccion_(ss) {
  var h = ss.getSheetByName("Ventas proyectadas");
  var nombres = COLS_PROY.map(function (c) { return c[0]; });
  var actuales = h.getLastRow() >= 2 ? h.getRange(2, 1, 1, Math.max(h.getLastColumn(), 1)).getValues()[0].map(planMin) : [];
  if (actuales.join("") === "") {
    h.getRange(2, 1, 1, nombres.length).setValues([nombres]);
    actuales = nombres.slice();
  } else {
    var faltan = nombres.filter(function (n) { return actuales.indexOf(n) < 0; });
    if (faltan.length) { _registrar_(ss, "armarPlan", "AVISO", "Ventas proyectadas: faltan las columnas " + faltan.join(", ") + "; no se tocó"); return; }
  }
  COLS_PROY.forEach(function (c) {
    var col = actuales.indexOf(c[0]) + 1;
    var celda = h.getRange(2, col);
    if (c[1]) celda.setNote(c[1]);
    celda.setFontWeight("bold").setBackground(c[0] === "producto" || c[0] === "sugerido" ? GRIS : NARANJA);
    var cuerpo = h.getRange(3, col, h.getMaxRows() - 2, 1);
    if (c[0] === "mes" || c[0] === "sku") cuerpo.setNumberFormat("@");   // que "2026-12" no se convierta en fecha
    if (c[0] === "producto" || c[0] === "sugerido") cuerpo.setBackground("#f6f6f6");
    if (c[0] === "precio_unitario") cuerpo.setNumberFormat(F_PESOS);
  });
  var ayuda = h.getRange(1, 1, 1, nombres.length);
  ayuda.breakApart().merge();
  ayuda.setValue(AYUDA_PROY).setWrap(true).setFontStyle("italic").setBackground("#fff8ee").setVerticalAlignment("middle");
  h.setRowHeight(1, 48);
  h.setFrozenRows(2);
}

// Escribe "producto" y "sugerido" de las filas del mes del inicio en adelante (las de meses pasados quedan como
// estaban, para poder comparar), y agrega abajo las filas que faltan. Las columnas del cliente no se escriben nunca.
function _escribirProyeccion_(h, proyeccion, res) {
  var cols = (proyeccion.cols || []).map(planMin);
  var cProd = cols.indexOf("producto"), cSug = cols.indexOf("sugerido");
  if (cProd < 0 || cSug < 0 || !res.proyeccion) return;
  var n = proyeccion.filas.length;
  if (n && res.proyeccion.actualizar.length) {
    var prod = proyeccion.filas.map(function (f) { return [f[cProd]]; });
    var sug = proyeccion.filas.map(function (f) { return [f[cSug]]; });
    res.proyeccion.actualizar.forEach(function (a) { prod[a.fila] = [a.producto]; sug[a.fila] = [a.sugerido]; });
    h.getRange(3, cProd + 1, n, 1).setValues(prod);
    h.getRange(3, cSug + 1, n, 1).setValues(sug);
  }
  if (res.proyeccion.nuevas.length) {
    var filas = res.proyeccion.nuevas.map(function (x) {
      var f = cols.map(function () { return ""; });
      f[cols.indexOf("mes")] = x.mes; f[cols.indexOf("sku")] = x.sku; f[cProd] = x.producto; f[cSug] = x.sugerido;
      return f;
    });
    // La primera fila libre después de la última con algo escrito.
    var desde = 3;
    for (var i = n - 1; i >= 0; i--) { if (proyeccion.filas[i].some(function (v) { return planTexto(v) !== ""; })) { desde = i + 4; break; } }
    h.getRange(desde, 1, filas.length, cols.length).setValues(filas);
  }
}

// ---------------------------------------------------------------------------------------------------------------
// Pantallas
// ---------------------------------------------------------------------------------------------------------------

// Borra la pantalla y escribe: título (fila 1), aclaraciones (filas 2-3), encabezados (fila 5) y filas (desde la 6).
// formatos: { número de columna (desde 0): formato }. pintar(fila, i) → [[columna, color], ...] para resaltar celdas.
function _pantalla_(ss, nombre, titulo, notas, enc, filas, formatos, pintar) {
  var h = ss.getSheetByName(nombre);
  h.clear();
  h.getRange(1, 1).setValue(titulo).setFontWeight("bold").setFontSize(14);
  var lineas = ["Recalculado el " + Utilities.formatDate(new Date(), ZONA, "dd/MM/yyyy HH:mm") + "."].concat(notas || []);
  lineas.forEach(function (t, i) { h.getRange(2 + i, 1).setValue(t).setFontColor("#555555"); });
  var filaEnc = 3 + lineas.length;
  if (!enc) return h;
  h.getRange(filaEnc, 1, 1, enc.length).setValues([enc]).setFontWeight("bold").setBackground(AZUL).setWrap(true);
  h.setFrozenRows(filaEnc);
  if (filas.length) {
    h.getRange(filaEnc + 1, 1, filas.length, enc.length).setValues(filas);
    Object.keys(formatos || {}).forEach(function (c) { h.getRange(filaEnc + 1, +c + 1, filas.length, 1).setNumberFormat(formatos[c]); });
    if (pintar) {
      filas.forEach(function (f, i) {
        (pintar(f, i) || []).forEach(function (p) { h.getRange(filaEnc + 1 + i, p[0] + 1).setBackground(p[1]); });
      });
    }
  }
  return h;
}

function _sinCalcular_(res, parte) {
  var f = res.faltanPartes.filter(function (x) { return x.parte === parte; })[0];
  return "No se calculó: en Datos falta o está incompleta la solapa " + (f ? f.solapas.join(", ") : "?") + " (ver Controles).";
}

function _escribirCaja_(ss, res) {
  var c = res.caja, sup = res.supuestos;
  if (!c) { _pantalla_(ss, "Caja semanal", "Caja semana a semana", [_sinCalcular_(res, "caja")], null); return; }
  var pesos = function (n) {   // 1234567,8 → "$ 1.234.568"
    var r = Math.round(n || 0), t = String(Math.abs(r)).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    return (r < 0 ? "-$ " : "$ ") + t;
  };
  var notas = [
    "Caja al empezar: " + pesos(c.apertura) + " (banco al " + (_txt_(c.diaBanco) || "—") + " + Mercado Pago al " + (_txt_(c.diaMp) || "—") + ").",
    "Caja más baja sin aportes: " + pesos(c.peor ? c.peor.caja : 0) + ", semana del " + _txt_(c.peor && c.peor.desde) + ". " +
      "Aportes que hacen falta en total: " + pesos(c.totalAportes) +
      (c.socios.length ? " (" + c.socios.map(function (s, i) { return s + " " + pesos(c.totalSocios[i]); }).join(", ") + ")." : "."),
    "Supuestos (Config): cobro " + _pct_(sup.pctCobro) + " de cada venta a " + sup.diasCobro + " días · publicidad " + _pct_(sup.pctPub) +
      " · Flex " + _pct_(sup.pctFlex) + " de las ventas de ML · dólar " + res.dolar + " · caja mínima " + (sup.cajaMinima == null ? "sin cargar" : pesos(sup.cajaMinima)) + "."
  ];
  var enc = ["semana (lunes)", "hasta (domingo)", "caja al inicio", "cobros de Mercado Pago a liberar", "cobros de ventas proyectadas",
    "pagos de contenedores", "gastos fijos", "deudas", "publicidad ML", "Flex", "caja al final", "aporte necesario"]
    .concat(c.socios.map(function (s) { return "aporte " + s; }));
  var filas = c.semanas.map(function (s) {
    return [_fecha_(s.desde), _fecha_(s.hasta), s.inicio, s.mp, s.cobros, -s.contenedores, -s.fijos, -s.deudas, -s.pub, -s.flex, s.final, s.aporte]
      .concat(s.socios);
  });
  var suma = function (k) { return c.semanas.reduce(function (a, s) { return a + s[k]; }, 0); };
  filas.push(["Total", "", "", suma("mp"), suma("cobros"), -suma("contenedores"), -suma("fijos"), -suma("deudas"), -suma("pub"), -suma("flex"), "", c.totalAportes]
    .concat(c.totalSocios));
  var fmt = { 0: F_FECHA, 1: F_FECHA };
  for (var i = 2; i < enc.length; i++) fmt[i] = F_PESOS;
  var h = _pantalla_(ss, "Caja semanal", "Caja semana a semana", notas, enc, filas, fmt, function (f, i) {
    if (i === filas.length - 1) return null;
    return f[11] > 0 ? [[11, ROJO], [10, AMARILLO]] : null;
  });
  h.getRange(h.getFrozenRows() + filas.length, 1, 1, enc.length).setFontWeight("bold").setBackground(GRIS);
}

function _escribirStock_(ss, res) {
  var st = res.stock;
  if (!st) { _pantalla_(ss, "Stock proyectado", "Stock proyectado", [_sinCalcular_(res, "stock")], null); return; }
  var notas = ["Stock al empezar = cierre del " + _txt_(planMas(res.inicio, -1)) + " (último conteo + llegadas − ventas − mermas). " +
    "Después: + lo que llega en la fecha estimada de cada contenedor de Datos − las ventas proyectadas.",
    "'Pedir antes de' = el día que se queda sin stock menos el plazo de reposición (" + res.supuestos.plazo + " días). En rojo: hay que pedir ya."];
  var enc = ["sku", "producto", "stock al empezar"].concat(st.meses.map(function (m) { return "fin " + m; }))
    .concat(["se queda sin stock", "pedir antes de", "nota"]);
  var n = st.meses.length;
  var filas = st.filas.map(function (f) {
    var nota = [f.sinConteo ? "sin conteo" : "", f.urgente ? "pedir ya" : ""].filter(String).join(" · ");
    return [f.sku, f.producto, f.alEmpezar].concat(f.alFinal.map(function (x) { return Math.round(x); }))
      .concat([_fecha_(f.sinStock), _fecha_(f.pedirAntes), nota]);
  });
  var fmt = { 2: F_UNID };
  for (var i = 0; i < n; i++) fmt[3 + i] = F_UNID;
  fmt[3 + n] = F_FECHA; fmt[4 + n] = F_FECHA;
  _pantalla_(ss, "Stock proyectado", "Stock proyectado", notas, enc, filas, fmt, function (f, i) {
    var p = [], x = st.filas[i];
    if (x.alEmpezar < 0) p.push([2, ROJO]);
    x.alFinal.forEach(function (v, j) { if (v < 0) p.push([3 + j, ROJO]); });
    if (x.urgente) p.push([4 + n, ROJO]);
    return p;
  });
}

function _escribirContenedores_(ss, res) {
  var c = res.contenedores;
  if (!c) { _pantalla_(ss, "Contenedores", "Contenedores", [_sinCalcular_(res, "contenedores")], null); return; }
  var notas = ["Los de Datos que no están nacionalizados. Se cargan en Datos (Contenedores y Contenedor_pagos), no acá.",
    "Contra el FOB cuentan solo anticipo y saldo. 'Sin programar' = FOB − pagado − previsto: esa plata no está en la caja (en amarillo)."];
  var enc = ["contenedor", "proveedor", "estado", "llegada estimada", "FOB USD", "pagado USD", "previsto USD", "próximo pago previsto",
    "otros gastos previstos USD", "sin programar USD"];
  var filas = c.map(function (x) {
    return [x.contenedor, x.proveedor, x.estado, _fecha_(x.estimada), x.fob == null ? "" : x.fob, x.pagado, x.previsto, _fecha_(x.proximo),
      x.otrosPrevistos, x.sinProgramar == null ? "" : x.sinProgramar];
  });
  _pantalla_(ss, "Contenedores", "Contenedores", notas, enc, filas, { 3: F_FECHA, 4: F_USD, 5: F_USD, 6: F_USD, 7: F_FECHA, 8: F_USD, 9: F_USD },
    function (f, i) { return c[i].sinProgramar > 0.5 ? [[9, AMARILLO]] : null; });
}

function _escribirReal_(ss, res) {
  if (!res.real) { _pantalla_(ss, "Real vs proyectado", "Real contra proyectado", [_sinCalcular_(res, "real")], null); return; }
  var notas = ["Los meses de Ventas proyectadas que ya empezaron. El mes en curso está incompleto. $ real = lo que pagó el comprador por los productos."];
  var enc = ["mes", "sku", "producto", "unidades proyectadas", "unidades reales", "diferencia", "$ proyectado", "$ real", "diferencia $"];
  var filas = res.real.map(function (f) { return [f.mes, f.sku, f.producto, f.uP, f.uR, f.dif, f.pP, f.pR, f.difPesos]; });
  _pantalla_(ss, "Real vs proyectado", "Real contra proyectado", notas, enc, filas, { 3: F_UNID, 4: F_UNID, 5: F_UNID, 6: F_PESOS, 7: F_PESOS, 8: F_PESOS });
}

function _escribirControles_(ss, res) {
  var filas = res.controles.map(function (c) { return [c.tipo, c.detalle]; });
  if (!filas.length) filas = [["Todo en orden", ""]];
  var h = _pantalla_(ss, "Controles", "Controles", ["Lo que falta cargar o no cierra. Cada aviso dice dónde mirar."], ["qué pasa", "detalle"], filas, {});
  h.setColumnWidth(1, 260); h.setColumnWidth(2, 700);
}

function _armarLeeme_(ss) {
  var h = ss.getSheetByName("Leeme");
  var t = [
    ["Plan: ventas, stock y caja hacia adelante"],
    [""],
    ["Qué cargan ustedes (solapas naranjas):"],
    ["  · Config: caja mínima, meses a proyectar y los supuestos. Lo que queda vacío usa el valor de la columna 'si queda vacío'."],
    ["  · Ventas proyectadas: las unidades que piensan vender de cada producto, mes por mes. Si no cargan nada, se usa el sugerido."],
    [""],
    ["Qué sale de la planilla Datos (no se carga acá):"],
    ["  · Contenedores y sus pagos: los que vienen, los planeados (estado 'planeado') y los pagos previstos (estado 'previsto' en Contenedor_pagos)."],
    ["  · Saldos del banco y de Mercado Pago, lo que Mercado Pago tiene por liberar, ventas, gastos fijos, deudas, Flex y publicidad."],
    [""],
    ["Pantallas (azules): Caja semanal, Stock proyectado, Contenedores, Real vs proyectado y Controles."],
    ["Se recalculan solas cada hora. La publicidad y la Flex de meses anteriores al inicio tienen que estar en Datos → Deudas."]
  ];
  h.clear();
  h.getRange(1, 1, t.length, 1).setValues(t);
  h.getRange(1, 1).setFontWeight("bold").setFontSize(14);
  h.setColumnWidth(1, 900);
}

// ---------------------------------------------------------------------------------------------------------------
// Ayudas
// ---------------------------------------------------------------------------------------------------------------

// "AAAA-MM-DD" → fecha de la planilla (medianoche de Buenos Aires). Vacío → vacío.
function _fecha_(d) {
  if (!d || typeof d !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(d)) return d || "";
  var p = d.split("-");
  return new Date(Date.UTC(+p[0], +p[1] - 1, +p[2], -PLAN_HORAS_ZONA, 0, 0));
}
function _txt_(d) { if (!d) return ""; var p = d.split("-"); return p[2] + "/" + p[1] + "/" + p[0]; }
function _pct_(x) { return (Math.round((x || 0) * 1000) / 10).toString().replace(".", ",") + " %"; }

function _registrar_(ss, que, resultado, detalle) {
  var h = ss.getSheetByName("Registro");
  if (!h) return;
  h.appendRow([Utilities.formatDate(new Date(), ZONA, "dd/MM/yyyy HH:mm:ss"), que, resultado, String(detalle).slice(0, 2000)]);
  if (h.getLastRow() > 2000) h.deleteRows(2, h.getLastRow() - 2000);
}
