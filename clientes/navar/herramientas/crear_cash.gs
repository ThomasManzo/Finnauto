/**
 * crear_cash.gs — arma las tres pantallas del cash sobre las listas de la Sheet.
 *
 *   "Cash"          DÍA POR DÍA: 7 días para atrás (real) y 28 para adelante (estimado).
 *   "Cash Semanal"  SEMANA POR SEMANA: 4 para atrás (real) y 12 para adelante.
 *   "Cash Mensual"  MES POR MES: 3 meses cerrados (real, la base) y 6 para adelante,
 *                   con la inflación mensual en una celda editable.
 *
 * Las tres tienen la misma estructura, de arriba a abajo (pedido de Thomas, 18/09):
 *
 *   FECHAS                 una columna por día / semana / mes
 *   SALDOS DE BANCOS       un renglón por banco: el saldo real al cierre de ese período
 *                          (del extracto; si el extracto de un banco llega hasta antes,
 *                          se arrastra el último saldo conocido). Solo en las columnas
 *                          reales: hacia adelante no se sabe por banco.
 *   INGRESOS               real (extracto) en las columnas pasadas; estimado (listas
 *                          con fecha) en las futuras. Nunca se mezclan.
 *   EGRESOS                ídem
 *   SALDO BANCOS AL CIERRE real en las pasadas; en las futuras = cierre anterior
 *                          + ingresos − egresos
 *   DESCUBIERTOS           lo acordado con los bancos (Deuda Bancaria)
 *   SALDO DISPONIBLE       cierre + descubiertos: lo que de verdad se puede usar
 *   ATRASADO (stock)       lo vencido, por concepto: no está en ninguna columna
 *
 * Todo es fórmula sobre Movimientos, Cuentas a Cobrar, Cuentas a Pagar, Cartera de
 * Cheques, Saldos Bancarios, Deuda Bancaria y Deuda Impositiva. Nadie tipea acá:
 * si un número está mal, está mal en la lista, y ahí se corrige. Las celdas que no
 * aplican quedan vacías (ni "—" ni 0): el formato muestra los ceros en blanco.
 *
 * La planilla está en español: los argumentos van con ";". Las fórmulas se escriben
 * con "," y al final se reescriben si la planilla no las acepta (_separadorLocal_).
 *
 * Se instala en el mismo proyecto de Apps Script que importar_cashflow.gs y se corre
 * desde el menú "finauto → Armar solapa Cash". Se puede correr las veces que haga
 * falta: borra y rearma las tres solapas.
 */

var DIAS_ATRAS = 7, DIAS_ADELANTE = 28;
var SEM_ATRAS = 4, SEM_ADELANTE = 12;
var MESES_BASE = 3, MESES_ADELANTE = 6;
var INFLACION_MENSUAL = 0.017;

var FORMATO_NUM = "#,##0;[Red]-#,##0;\"\"";     // ceros en blanco

// Rangos de las listas (columnas de cada solapa, tal cual están).
var R = {
  movFecha: "Movimientos!$B:$B", movTipo: "Movimientos!$D:$D", movCat: "Movimientos!$E:$E",
  movImp: "Movimientos!$G:$G", movEstado: "Movimientos!$K:$K",
  cobPend: "'Cuentas a Cobrar'!$I:$I", cobEmp: "'Cuentas a Cobrar'!$C:$C", cobVto: "'Cuentas a Cobrar'!$F:$F",
  cobEstado: "'Cuentas a Cobrar'!$J:$J", cobObs: "'Cuentas a Cobrar'!$L:$L",
  pagPend: "'Cuentas a Pagar'!$J:$J", pagEmp: "'Cuentas a Pagar'!$C:$C", pagVto: "'Cuentas a Pagar'!$G:$G",
  pagEstado: "'Cuentas a Pagar'!$K:$K", pagObs: "'Cuentas a Pagar'!$N:$N",
  chqTipo: "'Cartera de Cheques'!$B:$B", chqFecha: "'Cartera de Cheques'!$G:$G", chqImp: "'Cartera de Cheques'!$I:$I",
  chqEstado: "'Cartera de Cheques'!$J:$J", chqObs: "'Cartera de Cheques'!$L:$L",
  salFecha: "'Saldos Bancarios'!$A:$A", salBanco: "'Saldos Bancarios'!$B:$B", salImp: "'Saldos Bancarios'!$E:$E",
  dbBanco: "'Deuda Bancaria'!$A$3:$A$60", dbLinea: "'Deuda Bancaria'!$C$3:$C$60", dbOrig: "'Deuda Bancaria'!$D$3:$D$60", dbVig: "'Deuda Bancaria'!$E$3:$E$60",
  cuBanco: "'Deuda Bancaria'!$A$64:$A$3000", cuLinea: "'Deuda Bancaria'!$C$64:$C$3000",
  cuVto: "'Deuda Bancaria'!$E$64:$E$3000", cuTot: "'Deuda Bancaria'!$H$64:$H$3000", cuEstado: "'Deuda Bancaria'!$I$64:$I$3000",
  diNombre: "'Deuda Impositiva'!$A:$A", diVto: "'Deuda Impositiva'!$D:$D", diImp: "'Deuda Impositiva'!$E:$E", diEstado: "'Deuda Impositiva'!$F:$F",
  planTipo: "Plan!$A:$A",
};
var PLAN_PRIMERA_COL_MES = 15;          // columna O de la solapa Plan: el mes en curso; P..U los 6 siguientes


function armarCash() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  if (!ss.getSheetByName("Plan")) armarPlan();          // el Plan guarda decisiones: solo se crea si no está
  _armarPeriodica_(ss, "Cash", 1, DIAS_ATRAS, DIAS_ADELANTE);
  _armarPeriodica_(ss, "Cash Semanal", 7, SEM_ATRAS, SEM_ADELANTE);
  _armarMensual_(ss, "Cash Mensual");
  ["Cash", "Cash Semanal", "Cash Mensual"].forEach(function (n) { _separadorLocal_(ss, ss.getSheetByName(n)); });
  try { ss.toast("Solapas Cash, Cash Semanal y Cash Mensual armadas", "finauto", 8); } catch (e) {}
}


// ================================================================== renglones
// {D} = celda con la fecha de inicio de la columna; {F} = fin (exclusivo).
function _movReal_(tipo, cat) {
  return "SUMIFS(" + R.movImp + "," + R.movFecha + ",\">=\"&{D}," + R.movFecha + ",\"<\"&{F}," + R.movTipo + ",\"" + tipo + "\"," +
    R.movEstado + ",\"Real\"" + (cat ? "," + R.movCat + ",\"" + cat + "\"" : "") + ")";
}
function _proy_(cat, distinto) {
  return "SUMIFS(" + R.movImp + "," + R.movFecha + ",\">=\"&{D}," + R.movFecha + ",\"<\"&{F}," + R.movTipo + ",\"Egreso\"," +
    R.movEstado + ",\"Proyectado\"," + R.movCat + ",\"" + (distinto ? "<>" : "") + cat + "\")";
}
function _lista_(imp, fecha, extra) {
  return "SUMIFS(" + imp + "," + fecha + ",\">=\"&{D}," + fecha + ",\"<\"&{F}" + extra + ")";
}

// Diario y semanal. real: extracto (columnas pasadas). est: listas con fecha (futuras).
function _renglones_() {
  return {
    ingresos: [
      { n: "Cobranza acreditada (transferencias y depósitos)", real: _movReal_("Ingreso", "Cobranza Facturas"), f: "Movimientos · Cobranza Facturas" },
      { n: "Cheques de clientes depositados", real: _movReal_("Ingreso", "Cheques"), f: "Movimientos · Cheques" },
      { n: "Descuento de cheques (venta de valores)", real: _movReal_("Ingreso", "Descuento de Cheques"), f: "Movimientos · Descuento de Cheques: cobranza en cheque adelantada por el banco" },
      { n: "Préstamos nuevos", real: _movReal_("Ingreso", "Prestamo"), f: "Movimientos · Prestamo" },
      { n: "Sin identificar (tiene que ser 0)", real: _movReal_("Ingreso", "Otros"), f: "Movimientos · Otros: lo que el banco acreditó sin decir qué es" },
      { n: "Facturas A que vencen (Tango)", est: _lista_(R.cobPend, R.cobVto, "," + R.cobEmp + ",\"A\"," + R.cobEstado + ",\"<>Cobrado\"," + R.cobObs + ",\"<>REVISAR*\""), f: "Cuentas a Cobrar · por vencimiento · ESTIMADO" },
      { n: "Facturas AA que vencen (Tango)", est: _lista_(R.cobPend, R.cobVto, "," + R.cobEmp + ",\"AA\"," + R.cobEstado + ",\"<>Cobrado\"," + R.cobObs + ",\"<>REVISAR*\""), f: "Cuentas a Cobrar · ESTIMADO" },
      { n: "Cheques en cartera (por fecha de cobro)", est: _lista_(R.chqImp, R.chqFecha, "," + R.chqTipo + ",\"Terceros*\"," + R.chqEstado + ",\"En Cartera\"," + R.chqObs + ",\"<>REVISAR*\""), f: "Cartera de Cheques · En Cartera · ESTIMADO" },
    ],
    egresos: [
      { n: "Proveedores pagados", real: _movReal_("Egreso", "Proveedores MP y Logist."), neg: true, f: "Movimientos · Proveedores" },
      { n: "Sueldos y cargas pagados", real: _movReal_("Egreso", "Sueldos y Jornales"), neg: true, f: "Movimientos · Sueldos y Jornales" },
      { n: "Cuotas de préstamos pagadas", real: _movReal_("Egreso", "Prestamo"), neg: true, f: "Movimientos · Prestamo" },
      { n: "Impuestos pagados", real: _movReal_("Egreso", "Impuestos"), neg: true, f: "Movimientos · Impuestos" },
      { n: "Cheques propios debitados", real: _movReal_("Egreso", "Cheques"), neg: true, f: "Movimientos · Cheques" },
      { n: "Intereses y gastos bancarios pagados", real: _movReal_("Egreso", "Gastos Bancarios"), neg: true, f: "Movimientos · Gastos Bancarios" },
      { n: "Tarjeta, honorarios y otros pagados", real: _movReal_("Egreso", "Otros") + "+" + _movReal_("Egreso", "Honorarios y Dividendos"), neg: true, f: "Movimientos · Otros + Honorarios" },
      { n: "Proveedores A que vencen (Tango)", est: _lista_(R.pagPend, R.pagVto, "," + R.pagEmp + ",\"A\"," + R.pagEstado + ",\"<>Pagado\"," + R.pagObs + ",\"<>REVISAR*\""), f: "Cuentas a Pagar · por vencimiento · ESTIMADO" },
      { n: "Proveedores AA que vencen (Tango)", est: _lista_(R.pagPend, R.pagVto, "," + R.pagEmp + ",\"AA\"," + R.pagEstado + ",\"<>Pagado\"," + R.pagObs + ",\"<>REVISAR*\""), f: "Cuentas a Pagar · ESTIMADO" },
      { n: "Sueldos y cargas (proyectado)", est: "-" + _proy_("Sueldos y Jornales"), f: "Movimientos · proyectado con fecha (carga de NAVAR)" },
      { n: "Cuotas bancarias y tarjeta (cronograma)", est: _lista_(R.cuTot, R.cuVto, "," + R.cuEstado + ",\"Pendiente\""), f: "Deuda Bancaria · cronograma" },
      { n: "Impuestos con vencimiento (deuda y planes)", est: _lista_(R.diImp, R.diVto, "," + R.diEstado + ",\"<>Pagado\""), f: "Deuda Impositiva · planilla de Celia / contador" },
      { n: "Cheques propios (por fecha de pago)", est: _lista_(R.chqImp, R.chqFecha, "," + R.chqTipo + ",\"Propio*\"," + R.chqEstado + ",\"En Cartera\"," + R.chqObs + ",\"<>REVISAR*\""), f: "Cartera de Cheques · Propio Emitido" },
      { n: "Otros con fecha (cosecha, estampillas, honorarios)", est: "-" + _proy_("Sueldos y Jornales", true), f: "Movimientos · proyectados con fecha, salvo sueldos" },
      { n: "Intereses y gastos bancarios (promedio real 90 días)",
        est: "-SUMIFS(" + R.movImp + "," + R.movTipo + ",\"Egreso\"," + R.movCat + ",\"Gastos Bancarios\"," + R.movEstado + ",\"Real\"," + R.movFecha + ",\">=\"&($B$3-90))/90*({F}-{D})",
        f: "promedio de lo real de los últimos 90 días · ESTIMADO" },
    ],
    atrasado: [
      { n: "Proveedores A vencidos", est: "SUMIFS(" + R.pagPend + "," + R.pagEmp + ",\"A\"," + R.pagVto + ",\"<\"&$B$2," + R.pagEstado + ",\"<>Pagado\"," + R.pagObs + ",\"<>REVISAR*\")", f: "Cuentas a Pagar · vencimiento < hoy · sin REVISAR (deuda vieja)" },
      { n: "Proveedores AA vencidos", est: "SUMIFS(" + R.pagPend + "," + R.pagEmp + ",\"AA\"," + R.pagVto + ",\"<\"&$B$2," + R.pagEstado + ",\"<>Pagado\"," + R.pagObs + ",\"<>REVISAR*\")", f: "ídem" },
      { n: "Cuotas bancarias impagas", est: "SUMIFS(" + R.cuTot + "," + R.cuVto + ",\"<\"&$B$2," + R.cuEstado + ",\"Pendiente\")", f: "Deuda Bancaria · cronograma" },
      { n: "Impuestos vencidos", est: "SUMIFS(" + R.diImp + "," + R.diVto + ",\"<\"&$B$2," + R.diEstado + ",\"<>Pagado\")", f: "Deuda Impositiva" },
      { n: "Cheques propios vencidos sin debitar", est: "SUMIFS(" + R.chqImp + "," + R.chqTipo + ",\"Propio*\"," + R.chqEstado + ",\"En Cartera\"," + R.chqFecha + ",\"<\"&$B$2)", f: "Cartera de Cheques · incluye los REVISAR: confirmar con el extracto" },
      { n: "Vencido a cobrar (informativo, no suma)", est: "SUMIFS(" + R.cobPend + "," + R.cobVto + ",\"<\"&$B$2," + R.cobEstado + ",\"<>Cobrado\"," + R.cobObs + ",\"<>REVISAR*\")", f: "Cuentas a Cobrar", info: true },
    ]
  };
}

// Mensual. real: extracto. mensual: "prom" (promedio base × inflación), "lista"
// (por fecha, desde hoy), "max" (el mayor entre lista y promedio), "cero".
function _renglonesMensual_() {
  var desde = "\">=\"&MAX({D},$B$2)", hasta = "\"<\"&{F}";
  function lista(imp, fecha, extra) { return "SUMIFS(" + imp + "," + fecha + "," + desde + "," + fecha + "," + hasta + extra + ")"; }
  return {
    ingresos: [
      { n: "Cobranza acreditada (transferencias y depósitos)", real: _movReal_("Ingreso", "Cobranza Facturas"), mensual: "prom", f: "Movimientos · Cobranza Facturas" },
      { n: "Cheques de clientes depositados", real: _movReal_("Ingreso", "Cheques"), mensual: "prom", f: "Movimientos · Cheques" },
      { n: "Descuento de cheques (venta de valores)", real: _movReal_("Ingreso", "Descuento de Cheques"), mensual: "prom", f: "Movimientos · Descuento de Cheques" },
      { n: "Préstamos nuevos", real: _movReal_("Ingreso", "Prestamo"), mensual: "cero", f: "no se proyecta: es una decisión" },
      { n: "Sin identificar", real: _movReal_("Ingreso", "Otros"), mensual: "cero", f: "tiene que ser 0" },
    ],
    egresos: [
      { n: "Proveedores", real: _movReal_("Egreso", "Proveedores MP y Logist."), neg: true, mensual: "max",
        lista: lista(R.pagPend, R.pagVto, "," + R.pagEstado + ",\"<>Pagado\"," + R.pagObs + ",\"<>REVISAR*\""), f: "el mayor entre lo que vence en Tango ese mes y el promedio × inflación" },
      { n: "Sueldos y cargas (del 1 al 10)", real: _movReal_("Egreso", "Sueldos y Jornales"), neg: true, mensual: "prom", f: "Movimientos · Sueldos · horas extras en AA" },
      { n: "Cuotas bancarias y tarjeta (según Plan)", real: _movReal_("Egreso", "Prestamo"), neg: true, mensual: "plan", plan: "Banco",
        f: "solapa Plan · cronograma o refinanciación, según la decisión de cada línea" },
      { n: "Impuestos corrientes (IVA, cargas, retenciones)", real: _movReal_("Egreso", "Impuestos"), neg: true, mensual: "prom", f: "Movimientos · Impuestos · promedio de lo pagado" },
      { n: "Impuestos: deuda y planes (según Plan)", mensual: "plan", plan: "Impuesto",
        f: "solapa Plan · vencimientos o plan de pagos, según la decisión de cada impuesto" },
      { n: "Regularización de atrasado (según Plan)", mensual: "plan", plan: "Atrasado",
        f: "solapa Plan · lo vencido con proveedores y cheques que se decide pagar, en cuotas" },
      { n: "Cheques propios (por fecha de pago)", real: _movReal_("Egreso", "Cheques"), neg: true, mensual: "lista",
        lista: lista(R.chqImp, R.chqFecha, "," + R.chqTipo + ",\"Propio*\"," + R.chqEstado + ",\"En Cartera\""), f: "Cartera de Cheques · Propio Emitido" },
      { n: "Tarjeta, honorarios y otros", real: _movReal_("Egreso", "Otros") + "+" + _movReal_("Egreso", "Honorarios y Dividendos"), neg: true, mensual: "prom", f: "Movimientos · Otros + Honorarios" },
      { n: "Intereses y gastos bancarios", real: _movReal_("Egreso", "Gastos Bancarios"), neg: true, mensual: "prom", f: "Movimientos · Gastos Bancarios" },
      { n: "Otros con fecha (cosecha, estampillas; carga de NAVAR)", mensual: "lista",
        lista: "-SUMIFS(" + R.movImp + "," + R.movFecha + "," + desde + "," + R.movFecha + "," + hasta + "," + R.movTipo + ",\"Egreso\"," + R.movEstado + ",\"Proyectado\"," + R.movCat + ",\"<>Sueldos y Jornales\")",
        f: "Movimientos · proyectados con fecha, salvo sueldos" },
    ]
  };
}


// ================================================================== Cash diario y semanal
function _armarPeriodica_(ss, nombre, dias, atras, adelante) {
  var nCols = atras + adelante, colFuente = 2 + nCols;
  var h = _hojaLimpia_(ss, nombre, colFuente);
  var fmtFecha = dias === 1 ? "ddd dd/mm" : "\"sem\" dd/mm";

  _titulo_(h, "CASH · " + _cliente_(ss) + (dias === 1 ? " · día por día" : " · semana por semana"), colFuente);
  _cabecera_(h);
  var filaFechas = 6, fechas = [];
  for (var i = 0; i < nCols; i++) {
    var k = i - atras;
    fechas.push("=$B$2" + (k === 0 ? "" : (k > 0 ? "+" : "-") + Math.abs(k) * dias));
  }
  _filaFechas_(h, filaFechas, fechas, atras, fmtFecha, colFuente);
  var D = function (c) { return _colLetra_(2 + c) + "$" + filaFechas; };
  var F = function (c) { return "(" + D(c) + "+" + dias + ")"; };
  var ultima = _cuerpo_(ss, h, filaFechas + 2, nCols, atras, D, F, colFuente, dias === 1 ? "al cierre del día" : "al cierre de la semana", null);
  _formato_(h, filaFechas, ultima, nCols, colFuente, dias === 1 ? 92 : 104, fmtFecha);
}


// ================================================================== Cash mensual
function _armarMensual_(ss, nombre) {
  var atras = MESES_BASE, adelante = MESES_ADELANTE + 1;     // + el mes en curso
  var nCols = atras + adelante, colProm = 2 + nCols, colComo = colProm + 1, colFuente = colProm + 2;
  var h = _hojaLimpia_(ss, nombre, colFuente);

  _titulo_(h, "CASH · " + _cliente_(ss) + " · mes por mes, 6 meses", colFuente);
  _cabecera_(h);
  h.getRange(4, 1).setValue("Inflación mensual (editable)"); h.getRange(4, 2).setValue(INFLACION_MENSUAL).setNumberFormat("0.0%").setBackground("#fff8e1");
  h.getRange(4, 3).setValue("← cambiá este número y se recalcula lo estimado. Base: promedio de los 3 meses cerrados × (1 + inflación)^n. Lo que tiene fecha va por su fecha; proveedores toma el mayor entre Tango y el promedio.").setFontStyle("italic").setFontColor("#5f6368");

  var filaFechas = 6, fechas = [];
  for (var i = 0; i < nCols; i++) fechas.push("=EOMONTH($B$2," + (i - atras - 1) + ")+1");
  _filaFechas_(h, filaFechas, fechas, atras, "mmm yy", colFuente);
  h.getRange(filaFechas, colProm).setValue("Prom. base").setFontWeight("bold").setHorizontalAlignment("right");
  h.getRange(filaFechas, colComo).setValue("Cómo se estima").setFontWeight("bold");
  var D = function (c) { return _colLetra_(2 + c) + "$" + filaFechas; };
  var F = function (c) { return "(EOMONTH(" + D(c) + ",0)+1)"; };
  var mensual = { colProm: colProm, colComo: colComo, ultBase: "$" + _colLetra_(1 + atras) + "$" + filaFechas };
  var ultima = _cuerpo_(ss, h, filaFechas + 2, nCols, atras, D, F, colFuente, "al cierre del mes", mensual);
  _formato_(h, filaFechas, ultima, nCols, colFuente, 104, "mmm yy");
  h.setColumnWidth(colProm, 104); h.setColumnWidth(colComo, 210);
}


// ================================================================== el cuerpo común
// Saldos por banco · ingresos · egresos · saldo al cierre · descubiertos · disponible · atrasado.
// En el mensual, la columna del mes en curso es real hasta hoy + estimado por lo que falta.
function _cuerpo_(ss, h, fila, nCols, atras, D, F, colFuente, cierreTxt, mensual) {
  var reng = _renglones_();
  var bancos = _bancos_(ss);
  var L = function (c) { return _colLetra_(2 + c); };
  var ultReal = mensual ? atras : atras - 1;        // última columna con algo real

  // ---- 1. saldos de bancos: el saldo real al cierre de cada período, por banco.
  // Corte = último día del período, y nunca después del último extracto. Si el
  // extracto de un banco llega hasta antes, se arrastra su último saldo conocido.
  _seccion_(h, fila++, "1 · Saldos de bancos al cierre (real, del extracto)", "#e8f0fe", "#174ea6", colFuente);
  var primeraBanco = fila;
  bancos.forEach(function (b) {
    h.getRange(fila, 1).setValue(b.nombre);
    for (var c = 0; c <= ultReal; c++) {
      var corte = "MIN(" + F(c) + "-1,$B$3)";
      var ultFecha = "MAXIFS(" + R.salFecha + "," + R.salBanco + ",$A" + fila + "," + R.salFecha + ",\"<=\"&" + corte + ")";
      h.getRange(fila, 2 + c).setFormula("=IF(" + ultFecha + "=0,\"\",SUMIFS(" + R.salImp + "," + R.salBanco + ",$A" + fila + "," + R.salFecha + "," + ultFecha + "))");
    }
    h.getRange(fila, colFuente).setValue(b.fuente).setFontStyle("italic").setFontColor("#5f6368");
    fila++;
  });
  var filaSaldoReal = fila;
  h.getRange(fila, 1).setValue("Total saldo real de bancos").setFontWeight("bold");
  for (var c1 = 0; c1 <= ultReal; c1++) h.getRange(fila, 2 + c1).setFormula("=SUM(" + L(c1) + primeraBanco + ":" + L(c1) + (fila - 1) + ")").setFontWeight("bold");
  h.getRange(fila, colFuente).setValue("suma de los saldos de arriba · negativo = descubierto usado").setFontStyle("italic").setFontColor("#5f6368");
  _lineaTotal_(h, fila, colFuente);
  fila += 2;

  // ---- 2. ingresos · 3. egresos
  var lineas = mensual ? _renglonesMensual_() : reng;
  var filaRealIng = 0, filaRealEgr = 0;
  function bloque(num, titulo, lista) {
    _seccion_(h, fila++, num + " · " + titulo, "#e8f0fe", "#174ea6", colFuente);
    var primera = fila;
    lista.forEach(function (r) {
      h.getRange(fila, 1).setValue(r.n);
      for (var c = 0; c < nCols; c++) {
        var fx = "";
        if (mensual) fx = _formulaMensual_(r, c, atras, D, F, mensual, fila);
        else if (c < atras && r.real) fx = "=" + (r.neg ? "-" : "") + r.real.replace(/\{D\}/g, D(c)).replace(/\{F\}/g, F(c));
        else if (c >= atras && r.est) fx = "=" + r.est.replace(/\{D\}/g, D(c)).replace(/\{F\}/g, F(c));
        if (fx) h.getRange(fila, 2 + c).setFormula(fx);
      }
      if (mensual) {
        if (r.mensual === "prom" || r.mensual === "max") h.getRange(fila, mensual.colProm).setFormula("=AVERAGE(B" + fila + ":" + _colLetra_(1 + atras) + fila + ")").setFontColor("#5f6368");
        h.getRange(fila, mensual.colComo).setValue({ prom: "promedio × inflación", lista: "por fecha (lista)", max: "mayor entre Tango y promedio", cero: "no se proyecta", plan: "según solapa Plan" }[r.mensual]).setFontColor("#5f6368").setFontSize(10);
      }
      h.getRange(fila, colFuente).setValue(r.f).setFontStyle("italic").setFontColor("#5f6368");
      fila++;
    });
    h.getRange(fila, 1).setValue("Total " + titulo.toLowerCase()).setFontWeight("bold");
    for (var c2 = 0; c2 < nCols; c2++) h.getRange(fila, 2 + c2).setFormula("=SUM(" + L(c2) + primera + ":" + L(c2) + (fila - 1) + ")").setFontWeight("bold");
    _lineaTotal_(h, fila, colFuente);
    var filaTotal = fila;
    fila++;
    if (mensual) {
      // lo real del mes en curso, para no contarlo dos veces en el saldo (ya está en el saldo de hoy)
      h.getRange(fila, 1).setValue("de lo cual ya pasó (real hasta el último extracto)").setFontSize(10).setFontColor("#5f6368");
      var tipo = titulo === "Ingresos" ? "Ingreso" : "Egreso";
      for (var c3 = 0; c3 < nCols; c3++) {
        var f3 = (tipo === "Egreso" ? "=-" : "=") + "SUMIFS(" + R.movImp + "," + R.movFecha + ",\">=\"&" + D(c3) + "," + R.movFecha + ",\"<\"&MIN(" + F(c3) + ",$B$2)," + R.movTipo + ",\"" + tipo + "\"," + R.movEstado + ",\"Real\")";
        h.getRange(fila, 2 + c3).setFormula(f3).setFontSize(10).setFontColor("#5f6368");
      }
      if (tipo === "Ingreso") filaRealIng = fila; else filaRealEgr = fila;
      fila++;
    }
    fila++;
    return filaTotal;
  }
  var totIng = bloque(2, "Ingresos", lineas.ingresos);
  var totEgr = bloque(3, "Egresos", lineas.egresos);

  // ---- saldo al cierre · descubiertos · disponible
  h.getRange(fila, 1).setValue("Saldo de bancos " + cierreTxt).setFontWeight("bold");
  for (var c4 = 0; c4 < nCols; c4++) {
    var fx4;
    if (c4 < ultReal) fx4 = "=" + L(c4) + filaSaldoReal;
    else if (c4 === ultReal && !mensual) fx4 = "=" + L(c4) + filaSaldoReal;
    else if (c4 === ultReal && mensual) fx4 = "=" + L(c4) + filaSaldoReal + "+(" + L(c4) + totIng + "-" + L(c4) + filaRealIng + ")-(" + L(c4) + totEgr + "-" + L(c4) + filaRealEgr + ")";
    else fx4 = "=" + L(c4 - 1) + fila + "+" + L(c4) + totIng + "-" + L(c4) + totEgr;
    h.getRange(fila, 2 + c4).setFormula(fx4).setFontWeight("bold");
  }
  h.getRange(fila, colFuente).setValue("real en las columnas pasadas; después: cierre anterior + ingresos − egresos. Lo atrasado NO está: es stock").setFontStyle("italic").setFontColor("#5f6368");
  h.getRange(fila, 1, 1, colFuente).setBackground("#fff8e1");
  var filaCierre = fila++;

  h.getRange(fila, 1).setValue("Descubiertos acordados con los bancos").setFontWeight("bold");
  for (var c5 = 0; c5 < nCols; c5++) h.getRange(fila, 2 + c5).setFormula("=SUMIFS(" + R.dbOrig + "," + R.dbLinea + ",\"*escubierto*\")");
  h.getRange(fila, colFuente).setValue("Deuda Bancaria · capital original de las líneas 'Descubierto' (Galicia 10 M, Macro 50 M, Nación 100 M; Corrientes sin informar)").setFontStyle("italic").setFontColor("#5f6368");
  var filaAcuerdos = fila++;

  h.getRange(fila, 1).setValue("Saldo disponible (cierre + descubiertos)").setFontWeight("bold");
  for (var c6 = 0; c6 < nCols; c6++) h.getRange(fila, 2 + c6).setFormula("=" + L(c6) + filaCierre + "+" + L(c6) + filaAcuerdos).setFontWeight("bold");
  h.getRange(fila, colFuente).setValue("lo que de verdad se puede usar · negativo = no se cubre lo comprometido ni con todo el descubierto").setFontStyle("italic").setFontColor("#5f6368");
  h.getRange(fila, 1, 1, colFuente).setBackground("#fce8e6");
  fila += 2;

  // ---- 4. atrasado (stock)
  _seccion_(h, fila++, "4 · Atrasado hoy (stock: no está en ninguna columna, se paga por decisión)", "#fce8e6", "#a50e0e", colFuente);
  var primeraAtr = fila;
  reng.atrasado.forEach(function (r) {
    h.getRange(fila, 1).setValue(r.n).setFontStyle(r.info ? "italic" : "normal");
    h.getRange(fila, 2).setFormula("=" + r.est);
    h.getRange(fila, colFuente).setValue(r.f).setFontStyle("italic").setFontColor("#5f6368");
    fila++;
  });
  h.getRange(fila, 1).setValue("Total atrasado a pagar").setFontWeight("bold");
  h.getRange(fila, 2).setFormula("=SUM(B" + primeraAtr + ":B" + (fila - 2) + ")").setFontWeight("bold");
  _lineaTotal_(h, fila, colFuente);
  return fila;
}


// Fórmula de una celda del mensual. Meses base: solo real. Mes en curso: real hasta el
// último extracto + estimado por lo que falta del mes. Meses futuros: estimado.
function _formulaMensual_(r, c, atras, D, F, m, fila) {
  var M = D(c), Fin = F(c);
  var real = r.real ? "(" + (r.neg ? "-" : "") + r.real.replace(/\{D\}/g, M).replace(/\{F\}/g, "MIN(" + Fin + ",$B$2)") + ")" : "";
  if (c < atras) return real ? "=" + real : "";
  var n = "((YEAR(" + M + ")-YEAR(" + m.ultBase + "))*12+MONTH(" + M + ")-MONTH(" + m.ultBase + "))";
  var parte = "MAX(0,(EOMONTH(" + M + ",0)-MAX(" + M + ",$B$2)+1)/DAY(EOMONTH(" + M + ",0)))";   // fracción del mes que falta
  var prom = "$" + _colLetra_(m.colProm) + fila + "*(1+$B$4)^" + n + "*" + parte;
  var lista = r.lista ? r.lista.replace(/\{D\}/g, M).replace(/\{F\}/g, Fin) : "0";
  var est = "";
  if (r.mensual === "prom") est = prom;
  else if (r.mensual === "lista") est = lista;
  else if (r.mensual === "max") est = "MAX(" + lista + "," + prom + ")";
  else if (r.mensual === "plan") {
    // la columna del Plan para este mes: O = mes en curso, P.. los siguientes
    var colPlan = _colLetra_(PLAN_PRIMERA_COL_MES + (c - atras));
    est = "SUMIFS(Plan!$" + colPlan + ":$" + colPlan + "," + R.planTipo + ",\"" + r.plan + "\")";
  }
  if (!real && !est) return "";
  return "=" + [real, est].filter(function (x) { return x; }).join("+");
}


// ================================================================== Plan
// Una fila por línea de deuda (banco), por impuesto y por grupo de atrasado, con la
// DECISIÓN al lado: pagar como está, refinanciar (cuotas nuevas, gracia, tasa) o
// posponer. Los 7 meses de la derecha calculan cuánto se paga cada mes según esa
// decisión, y Cash Mensual los suma. Las decisiones son de la persona: este script
// solo las arma la primera vez (o cuando se corre "Armar solapa Plan", que las pisa).
var DECISIONES_BANCO = ["Pagar como está", "Refinanciar", "Posponer"];
var DECISIONES_ATRASADO = ["Regularizar en cuotas", "Posponer"];

function armarPlan() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var h = _hojaLimpia_(ss, "Plan", 22);
  var nMeses = MESES_ADELANTE + 1;
  _titulo_(h, "PLAN · " + _cliente_(ss) + " · qué se paga, qué se refinancia, qué se pospone", 14 + nMeses);
  h.getRange(2, 1).setValue("Hoy"); h.getRange(2, 2).setFormula("=TODAY()").setNumberFormat("dd/mm/yyyy");
  h.getRange(3, 1).setValue("Cómo se usa: en cada fila elegí la Decisión (columna H). Si es refinanciar o regularizar, poné meses de gracia, cantidad de cuotas y tasa mensual: la cuota nueva se calcula sola (sistema francés) y los meses de la derecha muestran cuánto sale cada mes. Cash Mensual toma esos meses. Prioridad y Por qué son de ustedes.").setFontStyle("italic").setFontColor("#5f6368");

  var enc = ["Tipo", "Acreedor", "Concepto", "Deuda total hoy", "Vencido hoy", "Vence en 6 meses (cronograma)", "Prioridad (1 = primero)",
             "Decisión", "Meses de gracia", "Cuotas nuevas", "Tasa mensual", "Cuota nueva", "Primer vencimiento", "Por qué"];
  var filaEnc = 5;
  enc.forEach(function (t, i) { h.getRange(filaEnc, 1 + i).setValue(t).setFontWeight("bold").setWrap(true); });
  for (var m = 0; m < nMeses; m++) {
    h.getRange(filaEnc, PLAN_PRIMERA_COL_MES + m).setFormula("=EOMONTH($B$2," + (m - 1) + ")+1").setNumberFormat("mmm yy").setFontWeight("bold").setHorizontalAlignment("right").setBackground("#fef7e0");
  }
  h.getRange(filaEnc, 1, 1, 14 + nMeses).setBackground("#f1f3f4").setBorder(false, false, true, false, false, false, "#3c4043", SpreadsheetApp.BorderStyle.SOLID_MEDIUM);
  h.getRange(filaEnc, PLAN_PRIMERA_COL_MES, 1, nMeses).setBackground("#fef7e0");

  var filas = [];
  // ---- bancos: una fila por línea con capital vigente o cuotas, sin descubiertos (ya están en la caja)
  var db = ss.getSheetByName("Deuda Bancaria");
  var lineas = db.getRange(3, 1, 58, 10).getValues();
  lineas.forEach(function (l) {
    var banco = String(l[0] || "").trim(), linea = String(l[2] || "").trim();
    if (!banco || !linea) return;
    if (/escubierto|acuerdo en cta/i.test(linea)) return;
    filas.push({ tipo: "Banco", acreedor: banco, concepto: linea, prioridad: _prioridadBanco_(banco, linea), decision: "Pagar como está" });
  });
  // ---- impuestos: una fila por impuesto
  var di = ss.getSheetByName("Deuda Impositiva");
  var vistos = {};
  di.getRange(2, 1, Math.max(di.getLastRow() - 1, 1), 6).getValues().forEach(function (r) {
    var imp = String(r[0] || "").trim();
    if (!imp || vistos[imp] || String(r[5]).toLowerCase() === "pagado") return;
    vistos[imp] = true;
    filas.push({ tipo: "Impuesto", acreedor: "ARCA / DGR / Municipio", concepto: imp, prioridad: /sicore|iva|aportes|planes/i.test(imp) ? 1 : 4, decision: "Pagar como está" });
  });
  // ---- atrasado: lo vencido con proveedores y cheques propios
  filas.push({ tipo: "Atrasado", acreedor: "Proveedores A", concepto: "Facturas vencidas (Tango, sin deuda vieja)", prioridad: 3, decision: "Posponer" });
  filas.push({ tipo: "Atrasado", acreedor: "Proveedores AA", concepto: "Facturas vencidas (Tango, sin deuda vieja)", prioridad: 3, decision: "Posponer" });
  filas.push({ tipo: "Atrasado", acreedor: "Cheques propios", concepto: "Vencidos sin debitar", prioridad: 2, decision: "Posponer" });

  var fila = filaEnc + 1;
  filas.forEach(function (f) {
    var r = fila, A = "$A" + r, B = "$B" + r, C = "$C" + r, D = "$D" + r, H = "$H" + r, I = "$I" + r, J = "$J" + r, K = "$K" + r, L = "$L" + r, M = "$M" + r;
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
    h.getRange(r, 7).setValue(f.prioridad);
    h.getRange(r, 8).setValue(f.decision).setDataValidation(SpreadsheetApp.newDataValidation().requireValueInList(f.tipo === "Atrasado" ? DECISIONES_ATRASADO : DECISIONES_BANCO, true).build());
    h.getRange(r, 9).setValue(0); h.getRange(r, 10).setValue(f.tipo === "Banco" ? 60 : (f.tipo === "Impuesto" ? 12 : 6)); h.getRange(r, 11).setValue(f.tipo === "Banco" ? 0.03 : (f.tipo === "Impuesto" ? 0.04 : 0)).setNumberFormat("0.0%");
    h.getRange(r, 12).setFormula("=IF(OR(" + H + "=\"Refinanciar\"," + H + "=\"Regularizar en cuotas\"),IF(" + K + ">0,PMT(" + K + "," + J + ",-" + D + ")," + D + "/" + J + "),\"\")");
    h.getRange(r, 13).setFormula("=IF(" + L + "=\"\",\"\",EOMONTH($B$2," + I + ")+1)").setNumberFormat("dd/mm/yyyy");
    h.getRange(r, 8, 1, 4).setBackground("#fff8e1"); h.getRange(r, 7).setBackground("#fff8e1"); h.getRange(r, 14).setBackground("#fff8e1");
    for (var m2 = 0; m2 < nMeses; m2++) {
      var mes = _colLetra_(PLAN_PRIMERA_COL_MES + m2) + "$" + filaEnc, fin = "(EOMONTH(" + mes + ",0)+1)";
      var comoEsta;
      if (f.tipo === "Banco") comoEsta = "SUMIFS(" + R.cuTot + "," + R.cuBanco + "," + B + "," + R.cuLinea + "," + C + "," + R.cuVto + ",\">=\"&MAX(" + mes + ",$B$2)," + R.cuVto + ",\"<\"&" + fin + "," + R.cuEstado + ",\"Pendiente\")";
      else if (f.tipo === "Impuesto") comoEsta = "SUMIFS(" + R.diImp + "," + R.diNombre + "," + C + "," + R.diVto + ",\">=\"&MAX(" + mes + ",$B$2)," + R.diVto + ",\"<\"&" + fin + "," + R.diEstado + ",\"<>Pagado\")";
      else comoEsta = "0";
      var refi = "IF(AND(" + L + "<>\"\"," + mes + ">=" + M + "," + mes + "<EDATE(" + M + "," + J + "))," + L + ",0)";
      h.getRange(r, PLAN_PRIMERA_COL_MES + m2).setFormula("=IF(" + H + "=\"Pagar como está\"," + comoEsta + ",IF(" + H + "=\"Posponer\",0," + refi + "))");
    }
    fila++;
  });
  // totales
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
  h.setColumnWidth(7, 80); h.setColumnWidth(8, 150); h.setColumnWidth(9, 70); h.setColumnWidth(10, 70); h.setColumnWidth(11, 70); h.setColumnWidth(12, 110); h.setColumnWidth(13, 100); h.setColumnWidth(14, 260);
  h.setFrozenRows(filaEnc); h.setFrozenColumns(3);
  h.getRange(filaEnc, 1, 1, 14).setBackground("#f1f3f4");
  _separadorLocal_(ss, h);
  try { ss.toast("Solapa Plan armada. Las decisiones se cargan a mano en la columna H.", "finauto", 8); } catch (e) {}
}

// Prioridad propuesta (1 = primero), por consecuencia de no pagar. Se puede cambiar a mano.
function _prioridadBanco_(banco, linea) {
  if (/tarjeta/i.test(linea)) return 4;
  if (/galicia|macro/i.test(banco)) return 2;      // son los que descuentan los cheques: si cierran, se para el motor
  if (/nacion/i.test(banco)) return 3;
  if (/corrientes/i.test(banco)) return 5;         // situación 3, en refinanciación
  return 4;
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
    out.push({ nombre: banco, fuente: manual ? "Saldos Bancarios · carga manual (caja AA, efectivo): se arrastra hasta que se cargue otro" : "Saldos Bancarios · extracto · se arrastra el último saldo conocido" });
  });
  return out;
}

function _hojaLimpia_(ss, nombre, columnas) {
  var h = ss.getSheetByName(nombre);
  if (h) { h.clear(); h.clearFormats(); } else h = ss.insertSheet(nombre);
  // la solapa nueva viene con 26 columnas; la diaria necesita 37 (y la celda de prueba, 40)
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

function _cabecera_(h) {
  h.getRange(2, 1).setValue("Hoy"); h.getRange(2, 2).setFormula("=TODAY()").setNumberFormat("dd/mm/yyyy");
  h.getRange(3, 1).setValue("Último día con extracto"); h.getRange(3, 2).setFormula("=MAXIFS(" + R.movFecha + "," + R.movEstado + ",\"Real\")").setNumberFormat("dd/mm/yyyy");
  h.getRange(3, 3).setValue("en $ · columnas verdes = real (extracto) · amarillas = estimado (listas con fecha) · nunca se mezclan").setFontStyle("italic").setFontColor("#5f6368");
}

function _filaFechas_(h, fila, formulas, atras, fmt, colFuente) {
  h.getRange(fila, 1).setValue("Fecha").setFontWeight("bold");
  formulas.forEach(function (f, i) {
    h.getRange(fila, 2 + i).setFormula(f).setNumberFormat(fmt).setFontWeight("bold").setHorizontalAlignment("right").setBackground(i < atras ? "#e6f4ea" : "#fef7e0");
    h.getRange(fila + 1, 2 + i).setValue(i < atras ? "real" : "estimado").setFontSize(9).setFontColor(i < atras ? "#137333" : "#b06000").setHorizontalAlignment("right");
  });
  h.getRange(fila, colFuente).setValue("Fuente").setFontWeight("bold");
  h.getRange(fila, 1, 1, colFuente).setBorder(false, false, true, false, false, false, "#3c4043", SpreadsheetApp.BorderStyle.SOLID_MEDIUM);
}

function _seccion_(h, fila, texto, fondo, color, ancho) {
  h.getRange(fila, 1).setValue(texto).setFontWeight("bold").setFontColor(color);
  h.getRange(fila, 1, 1, ancho).setBackground(fondo);
}

function _lineaTotal_(h, fila, ancho) {
  h.getRange(fila, 1, 1, ancho).setBorder(true, false, true, false, false, false, "#3c4043", SpreadsheetApp.BorderStyle.SOLID_MEDIUM);
}

function _formato_(h, filaFechas, ultima, nCols, colFuente, anchoCol, fmtFecha) {
  h.getRange(filaFechas + 2, 2, ultima - filaFechas - 1, colFuente - 2).setNumberFormat(FORMATO_NUM);
  for (var i = 0; i < nCols; i++) h.getRange(filaFechas, 2 + i).setNumberFormat(fmtFecha);
  h.getRange(2, 2, 2, 1).setNumberFormat("dd/mm/yyyy");
  h.setColumnWidth(1, 340);
  for (var w = 0; w < nCols; w++) h.setColumnWidth(2 + w, anchoCol);
  h.setColumnWidth(colFuente, 440);
  h.setFrozenRows(filaFechas + 1);
  h.setFrozenColumns(1);
}

function _colLetra_(n) {
  var s = "";
  while (n > 0) { var m = (n - 1) % 26; s = String.fromCharCode(65 + m) + s; n = Math.floor((n - 1) / 26); }
  return s;
}


// ---- La Sheet está en español: la coma es el decimal y los argumentos van con ";".
// Las fórmulas se escriben con "," (inglés); si la planilla no las entiende, se
// reescriben. Se prueba primero en una celda para no romper nada si sí las acepta.
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
