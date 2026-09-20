/**
 * crear_cash.gs — arma las pantallas del cash sobre las listas de la Sheet.
 *
 *   "Cash"          DÍA POR DÍA: los 7 días de extracto más recientes (real) y 28 días
 *                   hacia adelante (estimado).
 *   "Cash Semanal"  SEMANA POR SEMANA, de lunes a domingo, como el cash viejo de NAVAR:
 *                   4 semanas cerradas (real), la semana en curso (real hasta el último
 *                   extracto + estimado el resto) y 12 semanas hacia adelante.
 *   "Cash Mensual"  MES POR MES: 3 meses cerrados (real, la base), el mes en curso y 6
 *                   meses hacia adelante, con la inflación mensual en una celda editable.
 *   "Plan"          qué se hace con cada deuda: pagar como está, refinanciar o posponer.
 *                   Cash Mensual toma las cuotas de acá.
 *   "Instrucciones" qué es cada solapa, cómo se actualiza, dónde va cada dato.
 *
 * LA LÓGICA, en cuatro reglas
 * ---------------------------
 *  1. Un renglón por concepto. En las columnas pasadas muestra lo REAL (extracto); en
 *     las futuras, lo ESTIMADO (listas con fecha: Tango, cronograma, impuestos). La
 *     columna que contiene el último día con extracto tiene las dos cosas: real hasta ese
 *     día, estimado desde el siguiente. La fila "real / estimado" abajo de la fecha lo dice.
 *  2. Lo real es SOLO lo que vino del extracto (Origen "Extracto ..."). Las filas migradas
 *     del cash viejo (Origen "Manual") no cuentan: son agregados, no movimientos.
 *  3. El saldo de bancos es real hasta el último extracto (por banco, arrastrando el
 *     último saldo conocido). Después: cierre anterior + ingresos − egresos.
 *  4. Lo atrasado (vencido) es un stock: no está en ninguna columna. Se paga por decisión
 *     (solapa Plan → "Regularización de atrasado").
 *
 * Todo es fórmula. Nadie tipea acá: si un número está mal, está mal en la lista. Las
 * celdas sin nada quedan vacías (los ceros se muestran en blanco por formato).
 *
 * La planilla está en español: los argumentos van con ";". Las fórmulas se escriben con
 * "," y al final se reescriben si la planilla no las acepta (_separadorLocal_).
 *
 * Se instala en el mismo proyecto que importar_cashflow.gs y se corre desde el menú
 * "finauto → Armar solapa Cash". Se puede correr las veces que haga falta: rearma Cash,
 * Cash Semanal, Cash Mensual e Instrucciones. La solapa Plan solo se crea si no existe
 * (guarda decisiones cargadas a mano); "Armar solapa Plan" la rearma desde cero.
 */

var DIAS_ATRAS = 7, DIAS_ADELANTE = 28;
var SEM_ATRAS = 4, SEM_ADELANTE = 12;
var MESES_BASE = 3, MESES_ADELANTE = 6;
var INFLACION_MENSUAL = 0.017;
var FORMATO_NUM = "#,##0;[Red]-#,##0;\"\"";

// Rangos de las listas. Se arman leyendo los ENCABEZADOS de cada solapa al momento de
// correr (fila 1; en Deuda Bancaria, las dos filas "Banco"): si alguien agrega o mueve
// una columna (el 19/09 apareció una columna "Año" en Cuentas a Cobrar y corrió todo),
// las fórmulas siguen apuntando a la columna correcta. R se llena en armarCash / armarPlan.
var R = { planTipo: "Plan!$A:$A" };

var CAMPOS = [
  ["Movimientos",        1, { movFecha: "Fecha", movTipo: "Tipo", movCat: "Categoria", movImp: "Importe", movOrigen: "Origen", movEstado: "Estado" }],
  ["Cuentas a Cobrar",   1, { cobPend: "Saldo Pendiente", cobEmp: "Empresa", cobVto: "Fecha Vencimiento", cobEstado: "Estado", cobObs: "Observaciones" }],
  ["Cuentas a Pagar",    1, { pagPend: "Saldo Pendiente", pagEmp: "Empresa", pagVto: "Fecha Vencimiento", pagEstado: "Estado", pagObs: "Observaciones" }],
  ["Cartera de Cheques", 1, { chqTipo: "Tipo", chqFecha: "Fecha Pago / Cobro", chqImp: "Importe", chqEstado: "Estado", chqObs: "Observaciones" }],
  ["Saldos Bancarios",   1, { salFecha: "Fecha", salBanco: "Banco", salImp: "Saldo" }],
  ["Deuda Impositiva",   1, { diNombre: "Impuesto", diVto: "Fecha Vencimiento", diImp: "Importe", diEstado: "Estado" }],
];

function _rangos_(ss) {
  var out = { planTipo: "Plan!$A:$A" };
  CAMPOS.forEach(function (def) {
    var h = ss.getSheetByName(def[0]);
    if (!h) throw new Error("Falta la solapa " + def[0]);
    var enc = h.getRange(def[1], 1, 1, h.getLastColumn()).getValues()[0];
    Object.keys(def[2]).forEach(function (clave) {
      var c = _colPorNombre_(enc, def[2][clave]);
      if (c < 0) throw new Error("En " + def[0] + " no encuentro la columna '" + def[2][clave] + "'");
      out[clave] = "'" + def[0] + "'!$" + _colLetra_(c + 1) + ":$" + _colLetra_(c + 1);
    });
  });
  // Deuda Bancaria: dos bloques en la misma solapa, cada uno con su fila "Banco"
  var db = ss.getSheetByName("Deuda Bancaria");
  var colA = db.getRange(1, 1, db.getLastRow(), 1).getValues().map(function (r) { return _n_(r[0]); });
  var encs = [];
  colA.forEach(function (v, i) { if (v === "banco") encs.push(i + 1); });
  if (encs.length !== 2) throw new Error("Deuda Bancaria: esperaba 2 filas 'Banco' (líneas y cronograma), hay " + encs.length);
  var encA = db.getRange(encs[0], 1, 1, db.getLastColumn()).getValues()[0];
  var encB = db.getRange(encs[1], 1, 1, db.getLastColumn()).getValues()[0];
  function rangoDB(enc, nombre, desde, hasta) {
    var c = _colPorNombre_(enc, nombre);
    if (c < 0) throw new Error("En Deuda Bancaria no encuentro la columna '" + nombre + "'");
    var L = _colLetra_(c + 1);
    return "'Deuda Bancaria'!$" + L + "$" + desde + ":$" + L + "$" + hasta;
  }
  var finA = encs[1] - 3, iniB = encs[1] + 1, finB = Math.max(db.getMaxRows(), 3000);
  out.dbBanco = rangoDB(encA, "Banco", encs[0] + 1, finA);
  out.dbLinea = rangoDB(encA, "Linea / Producto", encs[0] + 1, finA);
  out.dbOrig = rangoDB(encA, "Capital Original", encs[0] + 1, finA);
  out.dbVig = rangoDB(encA, "Capital Vigente", encs[0] + 1, finA);
  out.cuBanco = rangoDB(encB, "Banco", iniB, finB);
  out.cuLinea = rangoDB(encB, "Linea / Producto", iniB, finB);
  out.cuVto = rangoDB(encB, "Fecha Vencimiento", iniB, finB);
  out.cuTot = rangoDB(encB, "Importe Total Cuota", iniB, finB);
  out.cuEstado = rangoDB(encB, "Estado", iniB, finB);
  return out;
}

// columna cuyo encabezado es el nombre (exacto primero, después "empieza con")
function _colPorNombre_(enc, nombre) {
  var n = _n_(nombre), i;
  for (i = 0; i < enc.length; i++) if (_n_(enc[i]) === n) return i;
  for (i = 0; i < enc.length; i++) if (_n_(enc[i]).indexOf(n) === 0) return i;
  return -1;
}

function _n_(s) {
  return String(s || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/\s+/g, " ").trim();
}

var PLAN_PRIMERA_COL_MES = 15;          // columna O de Plan = mes en curso; P..U los 6 siguientes


function armarCash() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  R = _rangos_(ss);
  if (!ss.getSheetByName("Plan")) armarPlan();
  _armarPeriodica_(ss, "Cash", "dia");
  _armarPeriodica_(ss, "Cash Semanal", "semana");
  _armarPeriodica_(ss, "Cash Mensual", "mes");
  armarInstrucciones();
  ["Cash", "Cash Semanal", "Cash Mensual"].forEach(function (n) { _separadorLocal_(ss, ss.getSheetByName(n)); });
  try { ss.toast("Cash, Cash Semanal, Cash Mensual e Instrucciones armados", "finauto", 8); } catch (e) {}
}


// ================================================================== fórmulas base
// {D} = celda con la fecha de inicio de la columna; {F} = fin (exclusivo).
// Lo real corre hasta el último extracto ($B$3); lo estimado arranca el día siguiente.
// Así una misma fórmula sirve para cualquier columna: en las pasadas la parte
// estimada da 0, en las futuras la parte real da 0, y en la columna que tiene al
// último extracto adentro suman las dos.
var HASTA_REAL = "MIN({F},$B$3+1)", DESDE_EST = "MAX({D},$B$3+1)";

function _real_(tipo, cat) {
  return "SUMIFS(" + R.movImp + "," + R.movFecha + ",\">=\"&{D}," + R.movFecha + ",\"<\"&" + HASTA_REAL + "," + R.movTipo + ",\"" + tipo + "\"," +
    R.movEstado + ",\"Real\"," + R.movOrigen + ",\"Extracto*\"" + (cat ? "," + R.movCat + ",\"" + cat + "\"" : "") + ")";
}
function _lista_(imp, fecha, extra) {
  return "SUMIFS(" + imp + "," + fecha + ",\">=\"&" + DESDE_EST + "," + fecha + ",\"<\"&{F}" + extra + ")";
}
function _proy_(cat, distinto) {
  return "SUMIFS(" + R.movImp + "," + R.movFecha + ",\">=\"&" + DESDE_EST + "," + R.movFecha + ",\"<\"&{F}," + R.movTipo + ",\"Egreso\"," +
    R.movEstado + ",\"Proyectado\"," + R.movCat + ",\"" + (distinto ? "<>" : "") + cat + "\")";
}
function _planMes_(tipo) {
  // se resuelve por columna: {P} = letra de la columna del Plan para ese mes
  return "SUMIFS(Plan!${P}:${P}," + R.planTipo + ",\"" + tipo + "\")";
}

// Un renglón: nombre · real (extracto) · est (listas) · cómo se estima en el mensual ·
// fuente. En el mensual, "prom" = promedio de los 3 meses base × (1+inflación)^n.
function _renglones_(periodo) {
  var mensual = periodo === "mes";
  var cobA = _lista_(R.cobPend, R.cobVto, "," + R.cobEmp + ",\"A\"," + R.cobEstado + ",\"<>Cobrado\"," + R.cobObs + ",\"<>REVISAR*\"");
  var cobAA = _lista_(R.cobPend, R.cobVto, "," + R.cobEmp + ",\"AA\"," + R.cobEstado + ",\"<>Cobrado\"," + R.cobObs + ",\"<>REVISAR*\"");
  var chqT = _lista_(R.chqImp, R.chqFecha, "," + R.chqTipo + ",\"Terceros*\"," + R.chqEstado + ",\"En Cartera\"," + R.chqObs + ",\"<>REVISAR*\"");
  var pagA = _lista_(R.pagPend, R.pagVto, "," + R.pagEmp + ",\"A\"," + R.pagEstado + ",\"<>Pagado\"," + R.pagObs + ",\"<>REVISAR*\"");
  var pagAA = _lista_(R.pagPend, R.pagVto, "," + R.pagEmp + ",\"AA\"," + R.pagEstado + ",\"<>Pagado\"," + R.pagObs + ",\"<>REVISAR*\"");
  var cuotas = _lista_(R.cuTot, R.cuVto, "," + R.cuEstado + ",\"Pendiente\"");
  var impDeuda = _lista_(R.diImp, R.diVto, "," + R.diEstado + ",\"<>Pagado\"");
  var chqP = _lista_(R.chqImp, R.chqFecha, "," + R.chqTipo + ",\"Propio*\"," + R.chqEstado + ",\"En Cartera\"," + R.chqObs + ",\"<>REVISAR*\"");
  var interes90 = "SUMIFS(" + R.movImp + "," + R.movTipo + ",\"Egreso\"," + R.movCat + ",\"Gastos Bancarios\"," + R.movOrigen + ",\"Extracto*\"," + R.movFecha + ",\">=\"&($B$3-90))/90*MAX(0,{F}-" + DESDE_EST + ")";

  var ingresos = [
    { n: "Cobranza acreditada", real: _real_("Ingreso", "Cobranza Facturas"), est: mensual ? "" : cobA, como: "prom",
      f: "real: transferencias y depósitos de clientes (extracto) · estimado: " + (mensual ? "promedio × inflación" : "facturas A que vencen en Tango") },
    { n: "Cobranza AA (efectivo)", real: "", est: mensual ? "" : cobAA, como: "cero",
      f: "AA cobra en efectivo, no hay extracto · estimado: facturas AA que vencen en Tango" },
    { n: "Cheques de clientes (depositados y descontados)", real: _real_("Ingreso", "Cheques") + "+" + _real_("Ingreso", "Descuento de Cheques"), est: mensual ? "" : chqT, como: "prom",
      f: "real: cheques depositados + venta de valores / descuento (extracto) · estimado: " + (mensual ? "promedio × inflación" : "cheques en cartera por fecha de cobro") },
    { n: "Préstamos nuevos", real: _real_("Ingreso", "Prestamo"), est: "", como: "cero", f: "real: préstamos acreditados · no se proyecta: es una decisión" },
    { n: "Sin identificar (tiene que ser 0)", real: _real_("Ingreso", "Otros"), est: "", como: "cero", f: "lo que el banco acreditó sin decir qué es" },
  ];
  var egresos = [
    { n: "Proveedores A", real: _real_("Egreso", "Proveedores MP y Logist."), est: mensual ? "" : pagA, como: "max", lista: pagA,
      f: "real: pagos a proveedores (extracto) · estimado: " + (mensual ? "el mayor entre lo que vence en Tango y el promedio × inflación" : "facturas A que vencen en Tango") },
    { n: "Proveedores AA", real: "", est: pagAA, como: "lista", lista: pagAA, f: "AA paga en efectivo · estimado: facturas AA que vencen en Tango" },
    { n: "Sueldos y cargas", real: _real_("Egreso", "Sueldos y Jornales"), est: mensual ? "" : "-" + _proy_("Sueldos y Jornales"), como: "prom",
      f: "real: extracto (Macro) · estimado: " + (mensual ? "promedio × inflación" : "lo proyectado con fecha en Movimientos") },
    { n: "Impuestos corrientes", real: _real_("Egreso", "Impuestos"), est: "", como: "prom",
      f: "real: extracto · estimado: " + (mensual ? "promedio × inflación" : "no se estima día a día; ver Cash Mensual") },
    { n: "Cheques propios", real: _real_("Egreso", "Cheques"), est: chqP, como: "lista", lista: chqP, f: "real: debitados (extracto) · estimado: en cartera por fecha de pago" },
    { n: "Intereses y gastos bancarios", real: _real_("Egreso", "Gastos Bancarios"), est: mensual ? "" : interes90, como: "prom",
      f: "real: extracto · estimado: " + (mensual ? "promedio × inflación" : "promedio de los últimos 90 días") },
    { n: "Otros (tarjeta, honorarios, cosecha)", real: _real_("Egreso", "Otros") + "+" + _real_("Egreso", "Honorarios y Dividendos"), est: "-" + _proy_("Sueldos y Jornales", true), como: "lista", lista: "-" + _proy_("Sueldos y Jornales", true),
      f: "real: extracto · estimado: lo proyectado con fecha en Movimientos (salvo sueldos)" },
  ];
  var deuda = mensual ? [
    { n: "Cuotas bancarias y tarjeta", real: _real_("Egreso", "Prestamo"), est: "", como: "plan", plan: "Banco", f: "real: cuotas debitadas (extracto) · estimado: solapa Plan (cronograma o refinanciación, según la decisión)" },
    { n: "Impuestos: deuda y planes", real: "", est: "", como: "plan", plan: "Impuesto", f: "solapa Plan: vencimientos de la deuda impositiva o plan de pagos, según la decisión" },
    { n: "Regularización de atrasado", real: "", est: "", como: "plan", plan: "Atrasado", f: "solapa Plan: lo vencido con proveedores y cheques que se decide pagar en cuotas" },
  ] : [
    { n: "Cuotas bancarias y tarjeta", real: _real_("Egreso", "Prestamo"), est: cuotas, como: "lista", f: "real: cuotas debitadas (extracto) · estimado: cronograma de Deuda Bancaria" },
    { n: "Impuestos: deuda y planes", real: "", est: impDeuda, como: "lista", f: "estimado: Deuda Impositiva (planilla de Celia / contador) por fecha de vencimiento" },
  ];
  var atrasado = [
    { n: "Proveedores A vencidos", est: "SUMIFS(" + R.pagPend + "," + R.pagEmp + ",\"A\"," + R.pagVto + ",\"<\"&$B$2," + R.pagEstado + ",\"<>Pagado\"," + R.pagObs + ",\"<>REVISAR*\")", f: "Cuentas a Pagar · vencimiento < hoy · sin la deuda vieja (REVISAR)" },
    { n: "Proveedores AA vencidos", est: "SUMIFS(" + R.pagPend + "," + R.pagEmp + ",\"AA\"," + R.pagVto + ",\"<\"&$B$2," + R.pagEstado + ",\"<>Pagado\"," + R.pagObs + ",\"<>REVISAR*\")", f: "ídem" },
    { n: "Cuotas bancarias impagas", est: "SUMIFS(" + R.cuTot + "," + R.cuVto + ",\"<\"&$B$2," + R.cuEstado + ",\"Pendiente\")", f: "Deuda Bancaria · cronograma" },
    { n: "Impuestos vencidos", est: "SUMIFS(" + R.diImp + "," + R.diVto + ",\"<\"&$B$2," + R.diEstado + ",\"<>Pagado\")", f: "Deuda Impositiva" },
    { n: "Cheques propios vencidos sin debitar", est: "SUMIFS(" + R.chqImp + "," + R.chqTipo + ",\"Propio*\"," + R.chqEstado + ",\"En Cartera\"," + R.chqFecha + ",\"<\"&$B$2)", f: "Cartera de Cheques · confirmar con el extracto" },
    { n: "Vencido a cobrar (informativo, no suma)", est: "SUMIFS(" + R.cobPend + "," + R.cobVto + ",\"<\"&$B$2," + R.cobEstado + ",\"<>Cobrado\"," + R.cobObs + ",\"<>REVISAR*\")", f: "Cuentas a Cobrar", info: true },
  ];
  return { ingresos: ingresos, egresos: egresos, deuda: deuda, atrasado: atrasado };
}


// ================================================================== la solapa (diaria, semanal o mensual)
function _armarPeriodica_(ss, nombre, periodo) {
  var atras, adelante, fmt, ancho, cabecera;
  if (periodo === "dia") { atras = DIAS_ATRAS; adelante = DIAS_ADELANTE; fmt = "ddd dd/mm"; ancho = 92; cabecera = "día por día"; }
  else if (periodo === "semana") { atras = SEM_ATRAS; adelante = SEM_ADELANTE + 1; fmt = "\"lun\" dd/mm"; ancho = 104; cabecera = "semana por semana (de lunes a domingo)"; }
  else { atras = MESES_BASE; adelante = MESES_ADELANTE + 1; fmt = "mmm yy"; ancho = 104; cabecera = "mes por mes, 6 meses"; }
  var mensual = periodo === "mes";
  var nCols = atras + adelante;
  var colProm = mensual ? 2 + nCols : 0, colComo = mensual ? colProm + 1 : 0, colFuente = mensual ? colProm + 2 : 2 + nCols;
  var h = _hojaLimpia_(ss, nombre, colFuente);

  _titulo_(h, "CASH · " + _cliente_(ss) + " · " + cabecera, colFuente);
  h.getRange(2, 1).setValue("Hoy"); h.getRange(2, 2).setFormula("=TODAY()").setNumberFormat("dd/mm/yyyy");
  h.getRange(3, 1).setValue("Último día con extracto (real hasta acá)"); h.getRange(3, 2).setFormula("=MAXIFS(" + R.movFecha + "," + R.movOrigen + ",\"Extracto*\")").setNumberFormat("dd/mm/yyyy");
  h.getRange(3, 3).setValue("en $ · verde = real (extracto) · amarillo = estimado (listas con fecha) · qué es cada renglón y de dónde sale: solapa Instrucciones").setFontStyle("italic").setFontColor("#5f6368");
  if (mensual) {
    h.getRange(4, 1).setValue("Inflación mensual (editable)"); h.getRange(4, 2).setValue(INFLACION_MENSUAL).setNumberFormat("0.0%").setBackground("#fff8e1");
    h.getRange(4, 3).setValue("← cambiá este número y se recalcula lo estimado. Base: promedio de los 3 meses cerrados × (1 + inflación)^n; lo que tiene fecha va por su fecha; las cuotas y planes salen de la solapa Plan.").setFontStyle("italic").setFontColor("#5f6368");
  }

  // ---- fechas de inicio de cada columna
  var filaFechas = 6, fechas = [];
  for (var i = 0; i < nCols; i++) {
    var k = i - atras;
    if (periodo === "dia") fechas.push("=$B$3-" + (atras - 1) + "+" + i);                                  // 7 días de extracto, después hacia adelante
    else if (periodo === "semana") fechas.push("=$B$2-WEEKDAY($B$2,2)+1" + (k === 0 ? "" : (k > 0 ? "+" : "-") + Math.abs(k) * 7));   // lunes
    else fechas.push("=EOMONTH($B$2," + (k - 1) + ")+1");
  }
  h.getRange(filaFechas, 1).setValue("Fecha").setFontWeight("bold");
  fechas.forEach(function (f, i) {
    var c = h.getRange(filaFechas, 2 + i);
    c.setFormula(f).setNumberFormat(fmt).setFontWeight("bold").setHorizontalAlignment("right");
    var D = _colLetra_(2 + i) + "$" + filaFechas, F = _fin_(periodo, D);
    // real / estimado / real + est., según dónde cae el último extracto
    h.getRange(filaFechas + 1, 2 + i).setFormula("=IF(" + F + "-1<=$B$3,\"real\",IF(" + D + ">$B$3,\"estimado\",\"real + est.\"))").setFontSize(9).setHorizontalAlignment("right").setFontColor("#5f6368");
  });
  if (mensual) {
    h.getRange(filaFechas, colProm).setValue("Prom. base").setFontWeight("bold").setHorizontalAlignment("right");
    h.getRange(filaFechas, colComo).setValue("Cómo se estima").setFontWeight("bold");
  }
  h.getRange(filaFechas, 1, 1, colFuente).setBorder(false, false, true, false, false, false, "#3c4043", SpreadsheetApp.BorderStyle.SOLID_MEDIUM);
  var D = function (c) { return _colLetra_(2 + c) + "$" + filaFechas; };
  var F = function (c) { return _fin_(periodo, D(c)); };
  var L = function (c) { return _colLetra_(2 + c); };
  var fx = function (s, c) {
    var out = s.replace(/\{D\}/g, D(c)).replace(/\{F\}/g, F(c));
    if (mensual) out = out.replace(/\{P\}/g, _colLetra_(PLAN_PRIMERA_COL_MES + Math.max(0, c - atras)));
    return out;
  };
  var reng = _renglones_(periodo);
  var fila = filaFechas + 2;

  // ---- 1. saldos de bancos (real, arrastrando el último conocido; vacío hacia adelante)
  _seccion_(h, fila++, "1 · Bancos (saldo real al cierre)", "#e8f0fe", "#174ea6", colFuente);
  var bancos = _bancos_(ss), primeraBanco = fila;
  bancos.forEach(function (b) {
    h.getRange(fila, 1).setValue(b.etiqueta);
    for (var c = 0; c < nCols; c++) {
      var corte = "MIN(" + F(c) + "-1,$B$3)";
      var cond = R.salBanco + ",\"" + b.nombre + "\"";
      var ult = "MAXIFS(" + R.salFecha + "," + cond + "," + R.salFecha + ",\"<=\"&" + corte + ")";
      var primero = "MINIFS(" + R.salFecha + "," + cond + ")";
      // si no hay saldo anterior al corte (la caja AA se cargó el 31/08), se toma el primero conocido
      h.getRange(fila, 2 + c).setFormula("=IF(" + D(c) + ">$B$3,\"\",SUMIFS(" + R.salImp + "," + cond + "," + R.salFecha + ",IF(" + ult + "=0," + primero + "," + ult + ")))");
    }
    fila++;
  });
  var filaSaldoReal = fila;
  h.getRange(fila, 1).setValue("Total saldo real de bancos").setFontWeight("bold");
  for (var c1 = 0; c1 < nCols; c1++) h.getRange(fila, 2 + c1).setFormula("=IF(" + D(c1) + ">$B$3,\"\",SUM(" + L(c1) + primeraBanco + ":" + L(c1) + (fila - 1) + "))").setFontWeight("bold");
  _lineaTotal_(h, fila, colFuente);
  fila += 2;

  // ---- 2. ingresos · 3. egresos de la operación · 4. deuda
  function bloque(titulo, lista) {
    _seccion_(h, fila++, titulo, "#e8f0fe", "#174ea6", colFuente);
    var primera = fila;
    lista.forEach(function (r) {
      h.getRange(fila, 1).setValue(r.n);
      var promRef = mensual ? "$" + _colLetra_(colProm) + fila : "";
      for (var c = 0; c < nCols; c++) {
        var partes = [];
        if (r.real) partes.push("(" + (r.n.indexOf("Cobranza") === 0 || r.n.indexOf("Cheques de clientes") === 0 || r.n.indexOf("Préstamos") === 0 || r.n.indexOf("Sin identificar") === 0 ? "" : "-") + fx(r.real, c) + ")");
        var est = "";
        if (mensual && c >= atras) {
          var n = "((YEAR(" + D(c) + ")-YEAR($" + _colLetra_(1 + atras) + "$" + filaFechas + "))*12+MONTH(" + D(c) + ")-MONTH($" + _colLetra_(1 + atras) + "$" + filaFechas + "))";
          var parte = "MAX(0,(" + F(c) + "-" + fx(DESDE_EST, c) + ")/DAY(EOMONTH(" + D(c) + ",0)))";   // fracción del mes que falta
          var prom = promRef + "*(1+$B$4)^" + n + "*" + parte;
          if (r.como === "prom") est = prom;
          else if (r.como === "max") est = "MAX(" + fx(r.lista, c) + "," + prom + ")";
          else if (r.como === "lista") est = fx(r.lista || r.est, c);
          else if (r.como === "plan") est = fx(_planMes_(r.plan), c);
        } else if (!mensual && r.est) est = fx(r.est, c);
        if (est) partes.push(est);
        if (partes.length) h.getRange(fila, 2 + c).setFormula("=" + partes.join("+"));
      }
      if (mensual) {
        if (r.como === "prom" || r.como === "max") h.getRange(fila, colProm).setFormula("=AVERAGE(B" + fila + ":" + _colLetra_(1 + atras) + fila + ")").setFontColor("#5f6368");
        h.getRange(fila, colComo).setValue({ prom: "promedio × inflación", lista: "por fecha (lista)", max: "mayor entre Tango y promedio", cero: "no se proyecta", plan: "según solapa Plan" }[r.como]).setFontColor("#5f6368").setFontSize(10);
      }
      fila++;
    });
    var filaTotal = fila;
    h.getRange(fila, 1).setValue("Total " + titulo.replace(/^\d · /, "").toLowerCase()).setFontWeight("bold");
    for (var c2 = 0; c2 < nCols; c2++) h.getRange(fila, 2 + c2).setFormula("=SUM(" + L(c2) + primera + ":" + L(c2) + (fila - 1) + ")").setFontWeight("bold");
    _lineaTotal_(h, fila, colFuente);
    fila += 2;
    return filaTotal;
  }
  var totIng = bloque("2 · Ingresos", reng.ingresos);
  var totOpe = bloque("3 · Egresos de la operación", reng.egresos);
  var totDeu = bloque("4 · Deuda", reng.deuda);

  // ---- resultado: acá se ven los ~$150 M que deja la operación y cuánto se lleva la deuda
  h.getRange(fila, 1).setValue("Resultado de la operación (antes de la deuda)").setFontWeight("bold");
  for (var c3 = 0; c3 < nCols; c3++) h.getRange(fila, 2 + c3).setFormula("=" + L(c3) + totIng + "-" + L(c3) + totOpe).setFontWeight("bold");
  h.getRange(fila, 1, 1, colFuente).setBackground("#e6f4ea");
  var filaResOpe = fila++;
  h.getRange(fila, 1).setValue("Resultado después de la deuda").setFontWeight("bold");
  for (var c4 = 0; c4 < nCols; c4++) h.getRange(fila, 2 + c4).setFormula("=" + L(c4) + filaResOpe + "-" + L(c4) + totDeu).setFontWeight("bold");
  var filaRes = fila++;
  fila++;

  // ---- lo real del período que tiene al último extracto adentro (para no contarlo dos veces en el saldo)
  var filaRealIng = fila, filaRealEgr = fila + 1;
  h.getRange(fila, 1).setValue("de lo cual ya pasó (real): ingresos").setFontSize(10).setFontColor("#9aa0a6");
  h.getRange(fila + 1, 1).setValue("de lo cual ya pasó (real): egresos").setFontSize(10).setFontColor("#9aa0a6");
  for (var c5 = 0; c5 < nCols; c5++) {
    var base5 = R.movFecha + ",\">=\"&" + D(c5) + "," + R.movFecha + ",\"<\"&" + fx(HASTA_REAL, c5) + "," + R.movEstado + ",\"Real\"," + R.movOrigen + ",\"Extracto*\"," + R.movCat + ",\"<>Transferencia Interna\"";
    h.getRange(fila, 2 + c5).setFormula("=SUMIFS(" + R.movImp + "," + base5 + "," + R.movTipo + ",\"Ingreso\")").setFontSize(10).setFontColor("#9aa0a6");
    h.getRange(fila + 1, 2 + c5).setFormula("=-SUMIFS(" + R.movImp + "," + base5 + "," + R.movTipo + ",\"Egreso\")").setFontSize(10).setFontColor("#9aa0a6");
  }
  h.hideRows(filaRealIng, 2);         // auxiliares: las usa el saldo al cierre, no hace falta verlas
  fila += 3;

  // ---- saldo al cierre · descubiertos · disponible
  var cierreTxt = periodo === "dia" ? "al cierre del día" : (periodo === "semana" ? "al cierre de la semana" : "al cierre del mes");
  h.getRange(fila, 1).setValue("Saldo de bancos " + cierreTxt).setFontWeight("bold");
  for (var c6 = 0; c6 < nCols; c6++) {
    var ing = L(c6) + totIng, egr = "(" + L(c6) + totOpe + "+" + L(c6) + totDeu + ")";
    var mixto = L(c6) + filaSaldoReal + "+(" + ing + "-" + L(c6) + filaRealIng + ")-(" + egr + "-" + L(c6) + filaRealEgr + ")";
    var futuro = c6 === 0 ? mixto : L(c6 - 1) + fila + "+" + ing + "-" + egr;
    h.getRange(fila, 2 + c6).setFormula("=IF(" + F(c6) + "-1<=$B$3," + L(c6) + filaSaldoReal + ",IF(" + D(c6) + "<=$B$3," + mixto + "," + futuro + "))").setFontWeight("bold");
  }
  h.getRange(fila, 1, 1, colFuente).setBackground("#fff8e1");
  var filaCierre = fila++;
  h.getRange(fila, 1).setValue("Descubiertos acordados con los bancos").setFontWeight("bold");
  for (var c7 = 0; c7 < nCols; c7++) h.getRange(fila, 2 + c7).setFormula("=SUMIFS(" + R.dbOrig + "," + R.dbLinea + ",\"*escubierto*\")");
  var filaAcuerdos = fila++;
  h.getRange(fila, 1).setValue("Saldo disponible (cierre + descubiertos)").setFontWeight("bold");
  for (var c8 = 0; c8 < nCols; c8++) h.getRange(fila, 2 + c8).setFormula("=" + L(c8) + filaCierre + "+" + L(c8) + filaAcuerdos).setFontWeight("bold");
  h.getRange(fila, 1, 1, colFuente).setBackground("#fce8e6");
  fila += 2;

  // ---- 5. atrasado (stock)
  _seccion_(h, fila++, "5 · Atrasado hoy (no está en la curva: se paga por decisión, en Plan)", "#fce8e6", "#a50e0e", colFuente);
  var primeraAtr = fila;
  reng.atrasado.forEach(function (r) {
    h.getRange(fila, 1).setValue(r.n).setFontStyle(r.info ? "italic" : "normal");
    h.getRange(fila, 2).setFormula("=" + r.est);
    fila++;
  });
  h.getRange(fila, 1).setValue("Total atrasado a pagar").setFontWeight("bold");
  h.getRange(fila, 2).setFormula("=SUM(B" + primeraAtr + ":B" + (fila - 2) + ")").setFontWeight("bold");
  _lineaTotal_(h, fila, colFuente);

  // ---- formato y colores de columnas (verde real, amarillo estimado; se recalcula al rearmar)
  h.getRange(filaFechas + 2, 2, fila - filaFechas - 1, colFuente - 2).setNumberFormat(FORMATO_NUM);
  h.getRange(2, 2, 2, 1).setNumberFormat("dd/mm/yyyy");
  for (var i2 = 0; i2 < nCols; i2++) {
    h.getRange(filaFechas, 2 + i2).setNumberFormat(fmt);
    h.getRange(filaFechas, 2 + i2, 2, 1).setBackground(i2 < atras ? "#e6f4ea" : "#fef7e0");
  }
  h.setColumnWidth(1, 380);
  for (var w = 0; w < nCols; w++) h.setColumnWidth(2 + w, ancho);
  if (mensual) { h.setColumnWidth(colProm, 104); h.setColumnWidth(colComo, 200); }
  h.setColumnWidth(colFuente, 20);
  h.setFrozenRows(filaFechas + 1);
  h.setFrozenColumns(1);
}

function _fin_(periodo, D) {
  if (periodo === "dia") return "(" + D + "+1)";
  if (periodo === "semana") return "(" + D + "+7)";
  return "(EOMONTH(" + D + ",0)+1)";
}


// ================================================================== Plan
// Una fila por línea de deuda (banco), por impuesto y por grupo de atrasado, con la
// DECISIÓN al lado. Las decisiones iniciales son la propuesta del PDF del 19/09
// (pagar por consecuencia, refinanciar a la capacidad de pago): se cambian a mano.
var DECISIONES_BANCO = ["Pagar como está", "Refinanciar", "Posponer"];
var DECISIONES_ATRASADO = ["Regularizar en cuotas", "Posponer"];

// Propuesta inicial por acreedor: [prioridad, decisión, gracia, cuotas, tasa mensual, por qué]
function _propuesta_(tipo, acreedor, concepto) {
  var a = (acreedor + " " + concepto).toLowerCase();
  if (tipo === "Banco") {
    if (/tarjeta/.test(a)) return [4, "Pagar como está", 0, 0, 0, "resumen de tarjeta: no se refinancia, se paga o se corta la tarjeta"];
    if (/desc\.|descuento|venta valores/.test(a)) return [2, "Pagar como está", 0, 0, 0, "descuento de cheques: el banco cobra el cheque al vencimiento; no es cuota"];
    if (/corrientes/.test(a)) return [5, "Refinanciar", 3, 60, 0.03, "situación 3, 3 cuotas impagas por préstamo, refinanciación en curso: pedir 60 cuotas con gracia"];
    if (/galicia/.test(a)) return [2, "Refinanciar", 3, 48, 0.03, "es el banco que descuenta los cheques: se refinancia el préstamo para no perder la línea"];
    if (/nacion/.test(a)) return [3, "Pagar como está", 0, 0, 0, "recién reprogramado y vuelto a situación 1 con $100 M de descubierto: no perderlo"];
    if (/macro/.test(a)) return [2, "Pagar como está", 0, 0, 0, "al día, situación 1, descuenta cheques y paga sueldos: no tocar"];
    if (/bbva/.test(a)) return [3, "Refinanciar", 3, 48, 0.03, "cuota de $15 M colgada; refinanciar antes de que cambie la situación"];
    return [4, "Pagar como está", 0, 0, 0, ""];
  }
  if (tipo === "Impuesto") {
    if (/sicore/.test(a)) return [1, "Refinanciar", 1, 12, 0.03, "$315 M de 2024; el contador propone 9 cuotas de $32 M: pedir el máximo de cuotas"];
    if (/aportes|seg\. social/.test(a)) return [1, "Refinanciar", 1, 8, 0.02, "plan de 8 cuotas por los conceptos 301 y 351 (contador)"];
    if (/bienes/.test(a)) return [3, "Refinanciar", 1, 18, 0.01, "contado $0,19 M + 18 cuotas de $0,26 M (contador)"];
    if (/tasa comercio|patentes|inmobiliario/.test(a)) return [8, "Posponer", 0, 0, 0, "municipal / provincial: no embarga rápido; se negocia después"];
    if (/planes de pago|iva|ganancias|ingresos brutos|agentes/.test(a)) return [1, "Pagar como está", 0, 0, 0, "vencimientos con fecha: si no se pagan, caducan los planes o entra demanda"];
    return [2, "Pagar como está", 0, 0, 0, ""];
  }
  if (/cheques/.test(a)) return [2, "Posponer", 0, 0, 0, "confirmar con Priscilla si ya se pagaron (tres parecen debitados)"];
  return [6, "Posponer", 3, 12, 0, "se regulariza cuando la refinanciación libere caja; primero los que cortan la hoja"];
}

function armarPlan() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  R = _rangos_(ss);
  var nMeses = MESES_ADELANTE + 1;
  var h = _hojaLimpia_(ss, "Plan", 14 + nMeses);
  _titulo_(h, "PLAN · " + _cliente_(ss) + " · qué se paga, qué se refinancia, qué se pospone", 14 + nMeses);
  h.getRange(2, 1).setValue("Hoy"); h.getRange(2, 2).setFormula("=TODAY()").setNumberFormat("dd/mm/yyyy");
  h.getRange(3, 1).setValue("Las filas son la deuda REAL (Deuda Bancaria, Deuda Impositiva, lo vencido). La Decisión (columna H) arranca con la propuesta del PDF del 19/09 y se cambia a mano. Si es refinanciar o regularizar: gracia, cuotas y tasa → la cuota nueva se calcula sola (sistema francés) y los meses de la derecha muestran cuánto sale cada mes. Cash Mensual suma esos meses.").setFontStyle("italic").setFontColor("#5f6368");

  var enc = ["Tipo", "Acreedor", "Concepto", "Deuda total hoy", "Vencido hoy", "Vence en 6 meses (cronograma)", "Prioridad (1 = primero)",
             "Decisión", "Meses de gracia", "Cuotas nuevas", "Tasa mensual", "Cuota nueva", "Primer vencimiento", "Por qué"];
  var filaEnc = 5;
  enc.forEach(function (t, i) { h.getRange(filaEnc, 1 + i).setValue(t).setFontWeight("bold").setWrap(true); });
  for (var m = 0; m < nMeses; m++) h.getRange(filaEnc, PLAN_PRIMERA_COL_MES + m).setFormula("=EOMONTH($B$2," + (m - 1) + ")+1").setNumberFormat("mmm yy").setFontWeight("bold").setHorizontalAlignment("right");
  h.getRange(filaEnc, 1, 1, 14 + nMeses).setBackground("#f1f3f4").setBorder(false, false, true, false, false, false, "#3c4043", SpreadsheetApp.BorderStyle.SOLID_MEDIUM);
  h.getRange(filaEnc, PLAN_PRIMERA_COL_MES, 1, nMeses).setBackground("#fef7e0");

  var filas = [];
  var db = ss.getSheetByName("Deuda Bancaria");
  var bancosCol = db.getRange(R.dbBanco.split("!")[1]).getValues(), lineasCol = db.getRange(R.dbLinea.split("!")[1]).getValues();
  bancosCol.forEach(function (r, i) {
    var banco = String(r[0] || "").trim(), linea = String(lineasCol[i][0] || "").trim();
    if (!banco || !linea || /escubierto|acuerdo en cta/i.test(linea)) return;
    filas.push({ tipo: "Banco", acreedor: banco, concepto: linea });
  });
  var di = ss.getSheetByName("Deuda Impositiva"), vistos = {};
  di.getRange(2, 1, Math.max(di.getLastRow() - 1, 1), 6).getValues().forEach(function (r) {
    var imp = String(r[0] || "").trim();
    if (!imp || vistos[imp] || String(r[5]).toLowerCase() === "pagado") return;
    vistos[imp] = true;
    filas.push({ tipo: "Impuesto", acreedor: "ARCA / DGR / Municipio", concepto: imp });
  });
  filas.push({ tipo: "Atrasado", acreedor: "Proveedores A", concepto: "Facturas vencidas (Tango, sin deuda vieja)" });
  filas.push({ tipo: "Atrasado", acreedor: "Proveedores AA", concepto: "Facturas vencidas (Tango, sin deuda vieja)" });
  filas.push({ tipo: "Atrasado", acreedor: "Cheques propios", concepto: "Vencidos sin debitar" });

  var fila = filaEnc + 1;
  filas.forEach(function (f) {
    var r = fila, B = "$B" + r, C = "$C" + r, D = "$D" + r, H = "$H" + r, I = "$I" + r, J = "$J" + r, K = "$K" + r, Lc = "$L" + r, M = "$M" + r;
    var p = _propuesta_(f.tipo, f.acreedor, f.concepto);
    h.getRange(r, 1).setValue(f.tipo); h.getRange(r, 2).setValue(f.acreedor); h.getRange(r, 3).setValue(f.concepto);
    if (f.tipo === "Banco") {
      h.getRange(r, 4).setFormula("=SUMIFS(" + R.dbVig + "," + R.dbBanco + "," + B + "," + R.dbLinea + "," + C + ")");
      h.getRange(r, 5).setFormula("=SUMIFS(" + R.cuTot + "," + R.cuBanco + "," + B + "," + R.cuLinea + "," + C + "," + R.cuVto + ",\"<\"&$B$2," + R.cuEstado + ",\"Pendiente\")");
      h.getRange(r, 6).setFormula("=SUMIFS(" + R.cuTot + "," + R.cuBanco + "," + B + "," + R.cuLinea + "," + C + "," + R.cuVto + ",\">=\"&$B$2," + R.cuVto + ",\"<\"&EDATE($B$2,6)," + R.cuEstado + ",\"Pendiente\")");
    } else if (f.tipo === "Impuesto") {
      h.getRange(r, 4).setFormula("=SUMIFS(" + R.diImp + "," + R.diNombre + "," + C + "," + R.diEstado + ",\"<>Pagado\")");
      h.getRange(r, 5).setFormula("=SUMIFS(" + R.diImp + "," + R.diNombre + "," + C + "," + R.diVto + ",\"<\"&$B$2," + R.diEstado + ",\"<>Pagado\")");
      h.getRange(r, 6).setFormula("=SUMIFS(" + R.diImp + "," + R.diNombre + "," + C + "," + R.diVto + ",\">=\"&$B$2," + R.diVto + ",\"<\"&EDATE($B$2,6)," + R.diEstado + ",\"<>Pagado\")");
    } else {
      var venc = f.acreedor === "Cheques propios"
        ? "SUMIFS(" + R.chqImp + "," + R.chqTipo + ",\"Propio*\"," + R.chqEstado + ",\"En Cartera\"," + R.chqFecha + ",\"<\"&$B$2)"
        : "SUMIFS(" + R.pagPend + "," + R.pagEmp + ",\"" + (f.acreedor === "Proveedores A" ? "A" : "AA") + "\"," + R.pagVto + ",\"<\"&$B$2," + R.pagEstado + ",\"<>Pagado\"," + R.pagObs + ",\"<>REVISAR*\")";
      h.getRange(r, 4).setFormula("=" + venc); h.getRange(r, 5).setFormula("=" + D);
    }
    h.getRange(r, 7).setValue(p[0]);
    h.getRange(r, 8).setValue(p[1]).setDataValidation(SpreadsheetApp.newDataValidation().requireValueInList(f.tipo === "Atrasado" ? DECISIONES_ATRASADO : DECISIONES_BANCO, true).build());
    h.getRange(r, 9).setValue(p[2]); h.getRange(r, 10).setValue(p[3]); h.getRange(r, 11).setValue(p[4]).setNumberFormat("0.0%");
    h.getRange(r, 12).setFormula("=IF(OR(" + H + "=\"Refinanciar\"," + H + "=\"Regularizar en cuotas\"),IF(" + J + "<=0,\"\",IF(" + K + ">0,PMT(" + K + "," + J + ",-" + D + ")," + D + "/" + J + ")),\"\")");
    h.getRange(r, 13).setFormula("=IF(" + Lc + "=\"\",\"\",EOMONTH($B$2," + I + ")+1)").setNumberFormat("dd/mm/yyyy");
    h.getRange(r, 14).setValue(p[5]);
    h.getRange(r, 7, 1, 5).setBackground("#fff8e1"); h.getRange(r, 14).setBackground("#fff8e1");
    for (var m2 = 0; m2 < nMeses; m2++) {
      var mes = _colLetra_(PLAN_PRIMERA_COL_MES + m2) + "$" + filaEnc, fin = "(EOMONTH(" + mes + ",0)+1)";
      var comoEsta = "0";
      if (f.tipo === "Banco") comoEsta = "SUMIFS(" + R.cuTot + "," + R.cuBanco + "," + B + "," + R.cuLinea + "," + C + "," + R.cuVto + ",\">=\"&MAX(" + mes + ",$B$2)," + R.cuVto + ",\"<\"&" + fin + "," + R.cuEstado + ",\"Pendiente\")";
      else if (f.tipo === "Impuesto") comoEsta = "SUMIFS(" + R.diImp + "," + R.diNombre + "," + C + "," + R.diVto + ",\">=\"&MAX(" + mes + ",$B$2)," + R.diVto + ",\"<\"&" + fin + "," + R.diEstado + ",\"<>Pagado\")";
      var refi = "IF(AND(" + Lc + "<>\"\"," + mes + ">=" + M + "," + mes + "<EDATE(" + M + "," + J + "))," + Lc + ",0)";
      h.getRange(r, PLAN_PRIMERA_COL_MES + m2).setFormula("=IF(" + H + "=\"Pagar como está\"," + comoEsta + ",IF(" + H + "=\"Posponer\",0," + refi + "))");
    }
    fila++;
  });
  h.getRange(fila, 1).setValue("Total").setFontWeight("bold");
  [4, 5, 6].forEach(function (c) { h.getRange(fila, c).setFormula("=SUM(" + _colLetra_(c) + (filaEnc + 1) + ":" + _colLetra_(c) + (fila - 1) + ")").setFontWeight("bold"); });
  for (var m3 = 0; m3 < nMeses; m3++) {
    var cl = _colLetra_(PLAN_PRIMERA_COL_MES + m3);
    h.getRange(fila, PLAN_PRIMERA_COL_MES + m3).setFormula("=SUM(" + cl + (filaEnc + 1) + ":" + cl + (fila - 1) + ")").setFontWeight("bold");
  }
  _lineaTotal_(h, fila, 14 + nMeses);
  h.getRange(filaEnc + 1, 4, fila - filaEnc, 3).setNumberFormat(FORMATO_NUM);
  h.getRange(filaEnc + 1, 12, fila - filaEnc, 1).setNumberFormat(FORMATO_NUM);
  h.getRange(filaEnc + 1, PLAN_PRIMERA_COL_MES, fila - filaEnc, nMeses).setNumberFormat(FORMATO_NUM);
  h.getRange(filaEnc + 1, 11, fila - filaEnc, 1).setNumberFormat("0.0%");
  h.setColumnWidth(1, 80); h.setColumnWidth(2, 150); h.setColumnWidth(3, 260); [4, 5, 6].forEach(function (c) { h.setColumnWidth(c, 110); });
  h.setColumnWidth(7, 80); h.setColumnWidth(8, 150); h.setColumnWidth(9, 70); h.setColumnWidth(10, 70); h.setColumnWidth(11, 70); h.setColumnWidth(12, 110); h.setColumnWidth(13, 100); h.setColumnWidth(14, 320);
  h.setFrozenRows(filaEnc); h.setFrozenColumns(3);
  _separadorLocal_(ss, h);
  try { ss.toast("Solapa Plan armada con la propuesta inicial. Las decisiones se cambian en la columna H.", "finauto", 8); } catch (e) {}
}


// ================================================================== Instrucciones
// Cuatro tablas cortas: las solapas · qué es cada renglón y de dónde sale · cómo impacta
// cada movimiento · cómo se actualiza. Es lo que hay que poder explicar en una reunión.
function armarInstrucciones() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var h = ss.getSheetByName("Instrucciones");
  if (!h) h = ss.insertSheet("Instrucciones", 0); else { h.clear(); h.clearFormats(); }
  var fila = 1;
  function titulo(t) { h.getRange(fila, 1).setValue(t).setFontSize(16).setFontWeight("bold").setFontColor("#174ea6"); fila += 1; }
  function sub(t) { h.getRange(fila, 1).setValue(t).setFontStyle("italic").setFontColor("#5f6368"); fila += 2; }
  function seccion(t) { h.getRange(fila, 1).setValue(t).setFontWeight("bold").setFontSize(12).setFontColor("#174ea6"); h.getRange(fila, 1, 1, 4).setBackground("#e8f0fe"); fila += 1; }
  function tabla(enc, filas) {
    enc.forEach(function (e, i) { h.getRange(fila, 1 + i).setValue(e).setFontWeight("bold").setBackground("#f1f3f4"); });
    fila++;
    filas.forEach(function (f) { f.forEach(function (v, i) { h.getRange(fila, 1 + i).setValue(v).setWrap(true).setVerticalAlignment("top"); }); fila++; });
    fila++;
  }
  titulo("NAVAR S.A. — Cash Flow: cómo funciona");
  sub("Actualizado el " + Utilities.formatDate(new Date(), "America/Argentina/Buenos_Aires", "dd/MM/yyyy") + ". Regla única: los datos viven en las LISTAS; las PANTALLAS son fórmula. Nadie tipea un número en una pantalla.");

  seccion("1 · Las solapas");
  tabla(["Solapa", "Qué es", "De dónde sale", "Quién la toca"], [
    ["Cash", "Día por día: 7 días de extracto (real) + 28 días adelante (estimado)", "fórmula sobre las listas", "nadie"],
    ["Cash Semanal", "Semana por semana, lunes a domingo: 4 cerradas (real) + la actual + 12 adelante", "fórmula sobre las listas", "nadie"],
    ["Cash Mensual", "Mes por mes: 3 cerrados (real) + el actual + 6 adelante, con inflación editable (B4)", "fórmula sobre las listas + solapa Plan", "solo la celda de inflación"],
    ["Plan", "Una fila por deuda: pagar como está / refinanciar / posponer. Cash Mensual toma las cuotas de acá", "Deuda Bancaria + Deuda Impositiva + lo vencido", "Thomas y Priscilla: la Decisión, gracia, cuotas, tasa, prioridad"],
    ["Movimientos", "LISTA: cada movimiento real de banco, clasificado", "extractos → lector → Importar Bancos", "el importador"],
    ["Saldos Bancarios", "LISTA: saldo al cierre de cada día, por cuenta", "extractos → Importar Bancos · la caja AA se carga a mano", "el importador · AA: a mano"],
    ["Cuentas a Cobrar", "LISTA: facturas pendientes de clientes, con vencimiento", "Tango → lector → Importar Tango", "el importador"],
    ["Cuentas a Pagar", "LISTA: facturas pendientes de proveedores, con vencimiento", "Tango → Importar Tango", "el importador"],
    ["Cartera de Cheques", "LISTA: cheques de terceros en cartera y cheques propios entregados", "Tango → Importar Tango", "el importador"],
    ["Deuda Bancaria", "LISTA: A) cada línea con su capital · B) cronograma: cada cuota pendiente", "mapa de deuda + extractos → Importar Deuda", "el importador · capital: a mano si el banco no manda tabla"],
    ["Deuda Impositiva", "LISTA: cada deuda con ARCA / DGR / municipio, con vencimiento", "planilla de Celia → Importar Impuestos", "el importador"],
  ]);

  seccion("2 · Cómo se lee una pantalla");
  tabla(["Parte", "Qué muestra"], [
    ["Hoy / Último extracto", "B2 es hoy; B3 el último día con extracto. Hasta B3 todo es REAL; desde el día siguiente, ESTIMADO. La fila bajo las fechas lo dice por columna (real · estimado · real + est.)."],
    ["1 · Bancos", "Saldo de cada banco al cierre de la columna, del extracto. Si un banco no tiene extracto hasta ahí, arrastra el último conocido. Hacia adelante queda vacío: no se sabe por banco."],
    ["2 · Ingresos · 3 · Egresos de la operación", "Un renglón por concepto: en las columnas reales, lo que pasó por el banco; en las estimadas, lo que dicen las listas con fecha (tabla 3)."],
    ["4 · Deuda", "Cuotas de bancos y tarjeta, vencimientos de impuestos y (mensual) regularización del atrasado. En el mensual salen de la solapa Plan."],
    ["Resultado de la operación", "Ingresos − egresos de la operación = lo que la operación deja ANTES de la deuda. Es la capacidad de pago (hoy, $100–150 M por mes)."],
    ["Resultado después de la deuda", "Lo anterior menos la deuda. Negativo = la deuda se come más de lo que la operación deja."],
    ["Saldo de bancos al cierre", "Real hasta el último extracto; después, cierre anterior + ingresos − egresos."],
    ["Saldo disponible", "Cierre + descubiertos acordados ($160 M). Negativo = no se cubre lo comprometido ni con todo el descubierto: hay que elegir."],
    ["5 · Atrasado hoy", "Lo vencido, por concepto. NO está en ninguna columna (no arranca la curva en rojo). Se paga por decisión, en Plan."],
  ]);

  seccion("3 · Cada renglón: qué es lo real y qué es lo estimado");
  tabla(["Renglón", "REAL (columnas pasadas) = extracto", "ESTIMADO (columnas futuras)"], [
    ["Cobranza acreditada", "transferencias y depósitos de clientes (Movimientos · Cobranza Facturas)", "diario/semanal: facturas A que vencen (Cuentas a Cobrar) · mensual: promedio × inflación"],
    ["Cobranza AA (efectivo)", "nada: AA cobra en efectivo, no pasa por banco", "facturas AA que vencen (Cuentas a Cobrar)"],
    ["Cheques de clientes", "cheques depositados + venta de valores / descuento (Movimientos · Cheques + Descuento de Cheques)", "diario/semanal: cheques en cartera por fecha de cobro · mensual: promedio × inflación"],
    ["Préstamos nuevos", "préstamos acreditados (Movimientos · Prestamo, ingreso)", "no se proyecta: es una decisión"],
    ["Sin identificar", "lo que el banco acreditó sin decir qué es (Movimientos · Otros)", "tiene que ser 0"],
    ["Proveedores A", "pagos a proveedores (Movimientos · Proveedores)", "diario/semanal: facturas A que vencen (Cuentas a Pagar) · mensual: el mayor entre eso y el promedio × inflación"],
    ["Proveedores AA", "nada: AA paga en efectivo", "facturas AA que vencen (Cuentas a Pagar)"],
    ["Sueldos y cargas", "Movimientos · Sueldos y Jornales (Macro)", "diario/semanal: lo proyectado con fecha en Movimientos · mensual: promedio × inflación"],
    ["Impuestos corrientes", "Movimientos · Impuestos (IVA, cargas, retenciones, sellos)", "mensual: promedio × inflación · diario/semanal: no se estima"],
    ["Cheques propios", "cheques debitados (Movimientos · Cheques, egreso)", "cheques propios en cartera por fecha de pago"],
    ["Intereses y gastos bancarios", "Movimientos · Gastos Bancarios", "diario/semanal: promedio de los últimos 90 días · mensual: promedio × inflación"],
    ["Otros (tarjeta, honorarios, cosecha)", "Movimientos · Otros + Honorarios", "lo proyectado con fecha en Movimientos (salvo sueldos)"],
    ["Cuotas bancarias y tarjeta", "cuotas debitadas (Movimientos · Prestamo, egreso)", "diario/semanal: cronograma de Deuda Bancaria · mensual: solapa Plan"],
    ["Impuestos: deuda y planes", "—", "diario/semanal: Deuda Impositiva por vencimiento · mensual: solapa Plan"],
    ["Regularización de atrasado", "—", "mensual: solapa Plan (lo vencido que se decide pagar en cuotas)"],
  ]);

  seccion("4 · Cómo impacta cada movimiento");
  tabla(["Pasa esto", "Dónde entra", "Qué cambia en el cash"], [
    ["Un cliente paga por transferencia", "Movimientos (Cobranza Facturas, real) · en Tango se hace el recibo y la factura sale de Cuentas a Cobrar", "sube el saldo real; baja lo estimado a cobrar; baja 'Vencido a cobrar' si estaba vencida"],
    ["Un cliente paga con cheque", "Tango: recibo + cheque en Cartera de Cheques (terceros)", "sube 'Cheques en cartera' (estimado por fecha de cobro); el saldo real NO cambia hasta que se deposita o descuenta"],
    ["Se descuenta un cheque en el banco", "Movimientos (Descuento de Cheques, real) · el cheque sale de la cartera", "sube el saldo real; baja lo estimado de cheques; el interés queda en Gastos Bancarios"],
    ["Se paga a un proveedor", "Movimientos (Proveedores, real) · Tango: orden de pago, la factura sale de Cuentas a Pagar", "baja el saldo real; baja lo estimado a pagar; baja 'Proveedores vencidos' si estaba vencida"],
    ["Se entrega un cheque propio", "Cartera de Cheques (propio, con fecha de pago)", "aparece en 'Cheques propios' estimado a la fecha de pago; cuando se debita pasa a real y sale de la cartera"],
    ["Se paga una cuota de préstamo", "Movimientos (Prestamo egreso, real) · Deuda Bancaria: la cuota pasa a 'Pagado' y el capital vigente baja", "baja el saldo real; baja 'Cuotas bancarias' estimado; baja la deuda total en Plan; si estaba vencida, baja 'Cuotas impagas'"],
    ["Entra un préstamo nuevo", "Movimientos (Prestamo ingreso, real) · Deuda Bancaria: nueva línea + su cronograma", "sube el saldo real hoy; suben las cuotas futuras; sube la deuda total en Plan"],
    ["Se paga un impuesto", "Movimientos (Impuestos, real) · Deuda Impositiva: la fila pasa a 'Pagado'", "baja el saldo real; baja lo estimado de impuestos; baja 'Impuestos vencidos'"],
    ["Se firma un plan de pagos con ARCA", "Deuda Impositiva: la deuda original pasa a 'Pagado' y se cargan las cuotas del plan · en Plan, la decisión 'Refinanciar' hace lo mismo sin tocar la lista", "el stock vencido baja; aparecen cuotas mensuales en 'Impuestos: deuda y planes'"],
    ["Se refinancia un préstamo", "Deuda Bancaria: cronograma nuevo (el banco manda la tabla) · mientras tanto, en Plan: 'Refinanciar' con gracia, cuotas y tasa", "cambian las cuotas futuras; el capital no cambia hasta que el banco lo confirme"],
    ["Se usa más descubierto", "Movimientos (lo que se pagó) · el saldo real del banco queda más negativo", "baja el saldo real; baja el disponible (saldo + acuerdo)"],
    ["Transferencia entre cuentas propias", "Movimientos, marcada INTERNO", "no cambia nada: sale de una cuenta y entra en otra"],
  ]);

  seccion("5 · Cómo se actualiza (hoy a mano, mañana solo)");
  tabla(["Paso", "Qué", "Con qué", "Resultado"], [
    ["1", "Extractos de los bancos (PDF / Excel del home banking)", "lector/extractos.py → para_pegar_bancos_<fecha>.xlsx en Drive → finauto → Importar Bancos", "Movimientos y Saldos Bancarios al día; B3 avanza; todo lo real se mueve solo"],
    ["2", "Tango: cobranzas, pagos, cheques", "lector/tango.py → para_pegar_en_la_sheet_<fecha>.xlsx → Importar Tango", "lo estimado al día: qué vence y cuándo"],
    ["3", "Deuda bancaria", "lector/deuda_bancaria.py (cruza cuotas con el extracto: la debitada pasa a Pagado) → Importar Deuda", "cuotas y capital al día"],
    ["4", "Impuestos", "planilla de Celia → lector/deuda_impositiva.py → Importar Impuestos", "vencimientos y planes al día"],
    ["5", "Si cambió la estructura", "finauto → Armar solapa Cash", "rearma las pantallas; Plan no se toca"],
    ["automático", "Bots de banco + token de Tango Live en la notebook de NAVAR", "corren cada mañana, dejan los archivos en Drive y disparan los importadores", "nadie sube nada; el cash amanece al día"],
  ]);

  seccion("6 · Reglas que no se rompen");
  tabla(["Regla", "Por qué"], [
    ["Nadie tipea números en las pantallas", "si un número está mal, está mal en la lista: se corrige ahí y las pantallas cambian solas"],
    ["Real y estimado no se mezclan en una celda", "salvo en la columna del último extracto, que lo dice"],
    ["Las filas 'REVISAR:' y las 'Manual' del cash viejo no suman", "están para no perder información, no para el cash"],
    ["Lo vencido es un stock, no un movimiento", "no arranca la curva en rojo; se paga por decisión"],
    ["Ningún número sale a NAVAR sin validar", "la caja la confirma el extracto; lo vencido, Tango; la deuda, el banco"],
  ]);
  h.setColumnWidth(1, 260); h.setColumnWidth(2, 420); h.setColumnWidth(3, 420); h.setColumnWidth(4, 300);
}


// ================================================================== ayudas
function _bancos_(ss) {
  var h = ss.getSheetByName("Saldos Bancarios");
  var vals = h.getRange(2, 1, Math.max(h.getLastRow() - 1, 1), 7).getValues();
  var vistos = {}, out = [];
  vals.forEach(function (r) {
    var banco = String(r[1] || "").trim();
    if (!banco || vistos[banco]) return;
    vistos[banco] = true;
    var manual = String(r[5] || "").toLowerCase().indexOf("manual") !== -1;
    out.push({ nombre: banco, etiqueta: banco === "(varios)" ? "AA · caja en efectivo (carga manual)" : banco,
               fuente: manual ? "Saldos Bancarios · carga manual: se arrastra hasta que se cargue otro" : "Saldos Bancarios · extracto · se arrastra el último saldo conocido" });
  });
  return out;
}

function _hojaLimpia_(ss, nombre, columnas) {
  var h = ss.getSheetByName(nombre);
  if (h) { h.clear(); h.clearFormats(); } else h = ss.insertSheet(nombre);
  var faltan = Math.max(columnas, 40) - h.getMaxColumns();
  if (faltan > 0) h.insertColumnsAfter(h.getMaxColumns(), faltan);
  ss.setActiveSheet(h);
  return h;
}

function _cliente_(ss) { return ss.getName().replace(" - Cash Flow", ""); }

function _titulo_(h, texto, ancho) {
  h.getRange(1, 1).setValue(texto).setFontWeight("bold").setFontSize(14);
  h.getRange(1, 1, 1, ancho).setBackground("#1c3f60").setFontColor("#ffffff");
}

function _seccion_(h, fila, texto, fondo, color, ancho) {
  h.getRange(fila, 1).setValue(texto).setFontWeight("bold").setFontColor(color);
  h.getRange(fila, 1, 1, ancho).setBackground(fondo);
}

function _lineaTotal_(h, fila, ancho) {
  h.getRange(fila, 1, 1, ancho).setBorder(true, false, true, false, false, false, "#3c4043", SpreadsheetApp.BorderStyle.SOLID_MEDIUM);
}

function _colLetra_(n) {
  var s = "";
  while (n > 0) { var m = (n - 1) % 26; s = String.fromCharCode(65 + m) + s; n = Math.floor((n - 1) / 26); }
  return s;
}

// ---- La Sheet está en español: la coma es el decimal y los argumentos van con ";".
function _separadorLocal_(ss, h) {
  var prueba = h.getRange(1, 40);
  prueba.setFormula("=MAX(1,2)");
  SpreadsheetApp.flush();
  var conComa = (prueba.getValue() === 2);
  prueba.clearContent();
  if (conComa) return;
  var rango = h.getDataRange();
  var formulas = rango.getFormulas();
  var nuevas = formulas.map(function (fila) {
    return fila.map(function (f) {
      if (!f) return f;
      var out = "", enComillas = false;
      for (var i = 0; i < f.length; i++) {
        var ch = f.charAt(i);
        if (ch === '"') enComillas = !enComillas;
        out += (ch === "," && !enComillas) ? ";" : ch;
      }
      return out;
    });
  });
  for (var r = 0; r < nuevas.length; r++) {
    var c = 0;
    while (c < nuevas[r].length) {
      if (!nuevas[r][c]) { c++; continue; }
      var ini = c;
      while (c < nuevas[r].length && nuevas[r][c]) c++;
      h.getRange(r + 1, ini + 1, 1, c - ini).setFormulas([nuevas[r].slice(ini, c)]);
    }
  }
}
