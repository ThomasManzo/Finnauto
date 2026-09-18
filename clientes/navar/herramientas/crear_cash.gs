/**
 * crear_cash.gs — arma las dos pantallas del cash sobre las listas de la Sheet.
 *
 *   "Cash"          DÍA POR DÍA: 7 días para atrás (real, del extracto) y 28 para
 *                   adelante (estimado, de las listas con fecha). Arriba, los bancos:
 *                   saldo real, acuerdo de descubierto y disponible. Abajo, lo atrasado.
 *   "Cash Semanal"  SEMANA POR SEMANA, como el cash viejo de NAVAR: 4 semanas para
 *                   atrás (real) y 12 para adelante (estimado). Mismos renglones.
 *
 * Todo es fórmula sobre las solapas Movimientos, Cuentas a Cobrar, Cuentas a Pagar,
 * Cartera de Cheques, Saldos Bancarios, Deuda Bancaria y Deuda Impositiva. Nadie
 * tipea un número acá: si un número está mal, está mal en la lista, y ahí se corrige.
 *
 * Reglas (diseño del 18/09/2026, ver documentos/cash_v2_diseno.md):
 *  - Una fuente por renglón. Real (banco) y estimado (lista con fecha) en columnas
 *    distintas: las columnas con fecha anterior a hoy son reales, las demás estimadas.
 *  - Lo atrasado es un stock: no arranca la curva en rojo. Se paga por decisión.
 *  - Sin "Cobranza proyectada" tipeada: el estimado es Tango por vencimiento.
 *  - Los REVISAR: (deuda vieja, cheques con fecha pasada) no suman.
 *
 * Se instala en el mismo proyecto de Apps Script que importar_cashflow.gs (Archivo
 * nuevo → Script → pegar) y se corre desde el menú "finauto → Armar solapa Cash".
 * Se puede correr todas las veces que haga falta: borra y rearma las dos solapas.
 */

var DIAS_ATRAS = 7, DIAS_ADELANTE = 28;        // solapa Cash (diaria)
var SEM_ATRAS = 4, SEM_ADELANTE = 12;          // solapa Cash Semanal

// Rangos de las listas (columnas de cada solapa, tal cual están).
var R = {
  movFecha: "Movimientos!$B:$B", movEmp: "Movimientos!$C:$C", movTipo: "Movimientos!$D:$D",
  movCat: "Movimientos!$E:$E", movImp: "Movimientos!$G:$G", movEstado: "Movimientos!$K:$K",
  cobPend: "'Cuentas a Cobrar'!$I:$I", cobEmp: "'Cuentas a Cobrar'!$C:$C", cobVto: "'Cuentas a Cobrar'!$F:$F",
  cobEstado: "'Cuentas a Cobrar'!$J:$J", cobObs: "'Cuentas a Cobrar'!$L:$L",
  pagPend: "'Cuentas a Pagar'!$J:$J", pagEmp: "'Cuentas a Pagar'!$C:$C", pagVto: "'Cuentas a Pagar'!$G:$G",
  pagEstado: "'Cuentas a Pagar'!$K:$K", pagObs: "'Cuentas a Pagar'!$N:$N",
  chqTipo: "'Cartera de Cheques'!$B:$B", chqFecha: "'Cartera de Cheques'!$G:$G", chqImp: "'Cartera de Cheques'!$I:$I",
  chqEstado: "'Cartera de Cheques'!$J:$J", chqObs: "'Cartera de Cheques'!$L:$L",
  salFecha: "'Saldos Bancarios'!$A:$A", salBanco: "'Saldos Bancarios'!$B:$B", salCta: "'Saldos Bancarios'!$D:$D",
  salImp: "'Saldos Bancarios'!$E:$E",
  dbBanco: "'Deuda Bancaria'!$A$3:$A$60", dbLinea: "'Deuda Bancaria'!$C$3:$C$60", dbOrig: "'Deuda Bancaria'!$D$3:$D$60",
  cuVto: "'Deuda Bancaria'!$E$64:$E$3000", cuTot: "'Deuda Bancaria'!$H$64:$H$3000", cuEstado: "'Deuda Bancaria'!$I$64:$I$3000",
  diVto: "'Deuda Impositiva'!$D:$D", diImp: "'Deuda Impositiva'!$E:$E", diEstado: "'Deuda Impositiva'!$F:$F",
};

// Cada renglón: nombre, fórmula REAL (extracto, para columnas pasadas) y fórmula
// ESTIMADA (listas con fecha, para columnas futuras). {D} = celda con la fecha de la
// columna, {N} = celda con los días que cubre la columna. Vacío = no aplica.
function _renglones_() {
  var d = "{D}", fin = "({D}+{N})";
  function mov(tipo, cat, extra) {
    return "SUMIFS(" + R.movImp + "," + R.movFecha + ",\">=\"&" + d + "," + R.movFecha + ",\"<\"&" + fin +
      "," + R.movTipo + ",\"" + tipo + "\"," + R.movEstado + ",\"Real\"" + (cat ? "," + R.movCat + ",\"" + cat + "\"" : "") + (extra || "") + ")";
  }
  function proy(cat, distinto) {
    return "SUMIFS(" + R.movImp + "," + R.movFecha + ",\">=\"&" + d + "," + R.movFecha + ",\"<\"&" + fin +
      "," + R.movTipo + ",\"Egreso\"," + R.movEstado + ",\"Proyectado\"," + R.movCat + ",\"" + (distinto ? "<>" : "") + cat + "\")";
  }
  return {
    ingresos: [
      { n: "Cobranza real (acreditado en bancos)", real: "=" + mov("Ingreso", "Cobranza Facturas") + "+" + mov("Ingreso", "Cheques"),
        est: "", f: "Movimientos · Ingreso · Cobranza Facturas + Cheques · extracto" },
      { n: "Cobranza facturas A pendientes (Tango, por vencimiento)", real: "",
        est: "=SUMIFS(" + R.cobPend + "," + R.cobEmp + ",\"A\"," + R.cobVto + ",\">=\"&" + d + "," + R.cobVto + ",\"<\"&" + fin + "," + R.cobEstado + ",\"<>Cobrado\"," + R.cobObs + ",\"<>REVISAR*\")",
        f: "Cuentas a Cobrar · saldo pendiente por fecha de vencimiento · ESTIMADO" },
      { n: "Cobranza facturas AA pendientes (Tango, por vencimiento)", real: "",
        est: "=SUMIFS(" + R.cobPend + "," + R.cobEmp + ",\"AA\"," + R.cobVto + ",\">=\"&" + d + "," + R.cobVto + ",\"<\"&" + fin + "," + R.cobEstado + ",\"<>Cobrado\"," + R.cobObs + ",\"<>REVISAR*\")",
        f: "Cuentas a Cobrar · ESTIMADO" },
      { n: "Cheques en cartera (terceros, por fecha de cobro)", real: "",
        est: "=SUMIFS(" + R.chqImp + "," + R.chqTipo + ",\"Terceros*\"," + R.chqEstado + ",\"En Cartera\"," + R.chqFecha + ",\">=\"&" + d + "," + R.chqFecha + ",\"<\"&" + fin + "," + R.chqObs + ",\"<>REVISAR*\")",
        f: "Cartera de Cheques · En Cartera · sin endosados ni REVISAR" },
      { n: "Financiación (préstamo nuevo, descuento, venta de valores)", real: "=" + mov("Ingreso", "Prestamo"), est: "",
        f: "Movimientos · Ingreso · Prestamo · sube a la vez en Deuda Bancaria" },
      { n: "Sin identificar (tiene que ser 0)", real: "=" + mov("Ingreso", "Otros"), est: "",
        f: "Movimientos · Ingreso · Otros: lo que el banco acreditó sin decir qué es" },
    ],
    egresos: [
      { n: "Pagos reales (debitado en bancos)", real: "=-" + mov("Egreso", null), est: "", f: "Movimientos · Egreso · extracto (sin transferencias internas)" },
      { n: "Proveedores A pendientes (Tango, por vencimiento)", real: "",
        est: "=SUMIFS(" + R.pagPend + "," + R.pagEmp + ",\"A\"," + R.pagVto + ",\">=\"&" + d + "," + R.pagVto + ",\"<\"&" + fin + "," + R.pagEstado + ",\"<>Pagado\"," + R.pagObs + ",\"<>REVISAR*\")",
        f: "Cuentas a Pagar · saldo pendiente por vencimiento · ESTIMADO" },
      { n: "Proveedores AA pendientes (Tango, por vencimiento)", real: "",
        est: "=SUMIFS(" + R.pagPend + "," + R.pagEmp + ",\"AA\"," + R.pagVto + ",\">=\"&" + d + "," + R.pagVto + ",\"<\"&" + fin + "," + R.pagEstado + ",\"<>Pagado\"," + R.pagObs + ",\"<>REVISAR*\")",
        f: "Cuentas a Pagar · ESTIMADO" },
      { n: "Sueldos y cargas sociales", real: "", est: "=-" + proy("Sueldos y Jornales"), f: "Movimientos · proyectado con fecha (carga de NAVAR)" },
      { n: "Cuotas bancarias (cronograma)", real: "",
        est: "=SUMIFS(" + R.cuTot + "," + R.cuVto + ",\">=\"&" + d + "," + R.cuVto + ",\"<\"&" + fin + "," + R.cuEstado + ",\"Pendiente\")",
        f: "Deuda Bancaria · cronograma · dato del banco o estimado (dice en Observaciones)" },
      { n: "Impuestos (ARCA, IIBB, municipales, planes)", real: "",
        est: "=SUMIFS(" + R.diImp + "," + R.diVto + ",\">=\"&" + d + "," + R.diVto + ",\"<\"&" + fin + "," + R.diEstado + ",\"<>Pagado\")",
        f: "Deuda Impositiva · planilla de Celia revisada por el contador" },
      { n: "Cheques propios (por fecha de pago)", real: "",
        est: "=SUMIFS(" + R.chqImp + "," + R.chqTipo + ",\"Propio*\"," + R.chqEstado + ",\"En Cartera\"," + R.chqFecha + ",\">=\"&" + d + "," + R.chqFecha + ",\"<\"&" + fin + "," + R.chqObs + ",\"<>REVISAR*\")",
        f: "Cartera de Cheques · Propio Emitido · En Cartera" },
      { n: "Otros con fecha (cosecha, estampillas, honorarios)", real: "", est: "=-" + proy("Sueldos y Jornales", true),
        f: "Movimientos · proyectados con fecha, salvo sueldos" },
      { n: "Intereses y gastos bancarios (promedio real 90 días)", real: "",
        est: "=-SUMIFS(" + R.movImp + "," + R.movTipo + ",\"Egreso\"," + R.movCat + ",\"Gastos Bancarios\"," + R.movEstado + ",\"Real\"," + R.movFecha + ",\">=\"&($B$3-90))/90*{N}",
        f: "promedio de lo real de los últimos 90 días · ESTIMADO" },
    ],
    atrasado: [
      { n: "Proveedores A vencidos", est: "=SUMIFS(" + R.pagPend + "," + R.pagEmp + ",\"A\"," + R.pagVto + ",\"<\"&$B$2," + R.pagEstado + ",\"<>Pagado\"," + R.pagObs + ",\"<>REVISAR*\")",
        f: "Cuentas a Pagar · vencimiento < hoy · sin REVISAR (deuda vieja)" },
      { n: "Proveedores AA vencidos", est: "=SUMIFS(" + R.pagPend + "," + R.pagEmp + ",\"AA\"," + R.pagVto + ",\"<\"&$B$2," + R.pagEstado + ",\"<>Pagado\"," + R.pagObs + ",\"<>REVISAR*\")", f: "ídem" },
      { n: "Cuotas bancarias impagas", est: "=SUMIFS(" + R.cuTot + "," + R.cuVto + ",\"<\"&$B$2," + R.cuEstado + ",\"Pendiente\")", f: "Deuda Bancaria · cronograma" },
      { n: "Impuestos vencidos", est: "=SUMIFS(" + R.diImp + "," + R.diVto + ",\"<\"&$B$2," + R.diEstado + ",\"<>Pagado\")", f: "Deuda Impositiva" },
      { n: "Cheques propios vencidos sin debitar", est: "=SUMIFS(" + R.chqImp + "," + R.chqTipo + ",\"Propio*\"," + R.chqEstado + ",\"En Cartera\"," + R.chqFecha + ",\"<\"&$B$2)", f: "Cartera de Cheques · incluye los REVISAR: confirmar con el extracto" },
      { n: "Vencido a cobrar (informativo, no suma)", est: "=SUMIFS(" + R.cobPend + "," + R.cobVto + ",\"<\"&$B$2," + R.cobEstado + ",\"<>Cobrado\"," + R.cobObs + ",\"<>REVISAR*\")", f: "Cuentas a Cobrar", info: true },
    ]
  };
}


function armarCash() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  _armarHoja_(ss, "Cash", 1, DIAS_ATRAS, DIAS_ADELANTE, true);
  _armarHoja_(ss, "Cash Semanal", 7, SEM_ATRAS, SEM_ADELANTE, false);
  try { ss.toast("Solapas Cash y Cash Semanal armadas", "finauto", 8); } catch (e) {}
}


function _armarHoja_(ss, nombre, dias, atras, adelante, conBancos) {
  var h = ss.getSheetByName(nombre);
  if (h) h.clear(); else h = ss.insertSheet(nombre);
  ss.setActiveSheet(h);
  h.setHiddenGridlines(false);

  var fila = 1;
  h.getRange(fila, 1).setValue("CASH · " + ss.getName().replace(" - Cash Flow", "") + (dias === 1 ? " · día por día" : " · semana por semana"))
    .setFontWeight("bold").setFontSize(14);
  h.getRange(fila, 1, 1, 6).setBackground("#1c3f60").setFontColor("#ffffff");
  fila = 2;
  h.getRange(fila, 1).setValue("Hoy"); h.getRange(fila, 2).setFormula("=TODAY()").setNumberFormat("dd/mm/yyyy");
  fila = 3;
  h.getRange(fila, 1).setValue("Último día con extracto (real hasta acá)");
  h.getRange(fila, 2).setFormula("=MAXIFS(" + R.movFecha + "," + R.movEstado + ",\"Real\")").setNumberFormat("dd/mm/yyyy");
  fila = 4;
  h.getRange(fila, 1).setValue("Días por columna"); h.getRange(fila, 2).setValue(dias);
  h.getRange(fila, 4).setValue("en $ · las columnas con fecha anterior a hoy son REALES (extracto); las demás, ESTIMADAS (listas con fecha)").setFontStyle("italic").setFontColor("#5f6368");
  fila = 6;

  // ---- 1. Bancos hoy (solo en la diaria)
  var filaTotalBancos = null;
  if (conBancos) {
    _seccion_(h, fila++, "1 · Bancos hoy", "#e8f0fe", "#174ea6");
    _encabezado_(h, fila++, ["Banco", "Cuenta", "Saldo real", "Acuerdo descubierto", "Disponible", "Saldo al", "Fuente"]);
    var cuentas = _cuentas_(ss);
    var primera = fila;
    cuentas.forEach(function (c) {
      h.getRange(fila, 1).setValue(c.banco); h.getRange(fila, 2).setValue(c.cuenta);
      var cond = R.salBanco + ",$A" + fila + "," + R.salCta + ",$B" + fila;
      h.getRange(fila, 3).setFormula("=SUMIFS(" + R.salImp + "," + cond + "," + R.salFecha + ",MAXIFS(" + R.salFecha + "," + cond + "))");
      h.getRange(fila, 4).setFormula("=SUMIFS(" + R.dbOrig + "," + R.dbBanco + ",$A" + fila + "," + R.dbLinea + ",\"*escubierto*\")");
      h.getRange(fila, 5).setFormula("=IF(D" + fila + ">0,MAX(0,C" + fila + "+D" + fila + "),MAX(0,C" + fila + "))");
      h.getRange(fila, 6).setFormula("=MAXIFS(" + R.salFecha + "," + cond + ")").setNumberFormat("dd/mm/yyyy");
      h.getRange(fila, 7).setValue("Saldos Bancarios (último saldo de la cuenta) · Deuda Bancaria (acuerdo: capital original del descubierto)").setFontStyle("italic").setFontColor("#5f6368");
      fila++;
    });
    h.getRange(fila, 1).setValue("Total bancos").setFontWeight("bold");
    ["C", "D", "E"].forEach(function (col, i) { h.getRange(fila, 3 + i).setFormula("=SUM(" + col + primera + ":" + col + (fila - 1) + ")").setFontWeight("bold"); });
    h.getRange(fila, 1, 1, 7).setBorder(true, false, true, false, false, false, "#3c4043", SpreadsheetApp.BorderStyle.SOLID_MEDIUM);
    filaTotalBancos = fila;
    fila += 2;
  }

  // ---- columnas de período
  var nCols = atras + adelante;
  var filaFechas = fila;
  h.getRange(fila, 1).setValue("Concepto").setFontWeight("bold");
  for (var i = 0; i < nCols; i++) {
    var col = 2 + i;
    var f = "=$B$2" + (i - atras === 0 ? "" : (i - atras > 0 ? "+" : "-") + Math.abs(i - atras) * dias);
    h.getRange(fila, col).setFormula(f).setNumberFormat(dias === 1 ? "ddd dd/mm" : "\"sem\" dd/mm").setFontWeight("bold").setHorizontalAlignment("right");
    h.getRange(fila, col).setBackground(i < atras ? "#e6f4ea" : "#fef7e0");
  }
  h.getRange(fila, 2 + nCols).setValue("Fuente").setFontWeight("bold");
  h.getRange(fila, 1, 1, nCols + 2).setBackground(null).setBorder(false, false, true, false, false, false, "#3c4043", SpreadsheetApp.BorderStyle.SOLID_MEDIUM);
  for (var i2 = 0; i2 < nCols; i2++) h.getRange(fila, 2 + i2).setBackground(i2 < atras ? "#e6f4ea" : "#fef7e0");
  fila++;
  h.getRange(fila, 1).setValue("").setFontSize(8);
  for (var j = 0; j < nCols; j++) h.getRange(fila, 2 + j).setValue(j < atras ? "real" : "estimado").setFontSize(9).setFontColor(j < atras ? "#137333" : "#b06000").setHorizontalAlignment("right");
  fila++;

  var reng = _renglones_();
  function bloque(titulo, lista, color, colorTxt) {
    _seccion_(h, fila++, titulo, color, colorTxt);
    var primera = fila;
    lista.forEach(function (r) {
      h.getRange(fila, 1).setValue(r.n);
      for (var c = 0; c < nCols; c++) {
        var celdaFecha = _colLetra_(2 + c) + "$" + filaFechas;
        var fx = c < atras ? r.real : r.est;
        if (fx) h.getRange(fila, 2 + c).setFormula(fx.replace(/\{D\}/g, celdaFecha).replace(/\{N\}/g, "$B$4"));
        else h.getRange(fila, 2 + c).setValue("—").setHorizontalAlignment("right").setFontColor("#9aa0a6");
      }
      h.getRange(fila, 2 + nCols).setValue(r.f).setFontStyle("italic").setFontColor("#5f6368");
      fila++;
    });
    h.getRange(fila, 1).setValue("Total " + titulo.split("· ")[1].toLowerCase()).setFontWeight("bold");
    for (var c2 = 0; c2 < nCols; c2++) {
      var L = _colLetra_(2 + c2);
      h.getRange(fila, 2 + c2).setFormula("=SUM(" + L + primera + ":" + L + (fila - 1) + ")").setFontWeight("bold");
    }
    h.getRange(fila, 1, 1, nCols + 2).setBorder(true, false, true, false, false, false, "#3c4043", SpreadsheetApp.BorderStyle.SOLID_MEDIUM);
    var filaTotal = fila;
    fila += 2;
    return filaTotal;
  }
  var totIng = bloque((conBancos ? "2" : "1") + " · Ingresos", reng.ingresos, "#e8f0fe", "#174ea6");
  var totEgr = bloque((conBancos ? "3" : "2") + " · Egresos", reng.egresos, "#e8f0fe", "#174ea6");

  // ---- saldo proyectado
  h.getRange(fila, 1).setValue("Saldo bancos al cierre").setFontWeight("bold");
  var saldoInicial = conBancos ? "$C$" + filaTotalBancos : "Cash!$C$" + _filaTotalBancosDeCash_(ss);
  var acuerdos = conBancos ? "$D$" + filaTotalBancos : "Cash!$D$" + _filaTotalBancosDeCash_(ss);
  for (var k = 0; k < nCols; k++) {
    var L2 = _colLetra_(2 + k), Lprev = _colLetra_(1 + k);
    var fx;
    if (k < atras) fx = "";                                   // pasado: lo real ya está en el saldo de hoy
    else if (k === atras) fx = "=" + saldoInicial + "+" + L2 + totIng + "-" + L2 + totEgr;
    else fx = "=" + Lprev + fila + "+" + L2 + totIng + "-" + L2 + totEgr;
    if (fx) h.getRange(fila, 2 + k).setFormula(fx).setFontWeight("bold"); else h.getRange(fila, 2 + k).setValue("—").setHorizontalAlignment("right").setFontColor("#9aa0a6");
  }
  h.getRange(fila, 2 + nCols).setValue("saldo de hoy + ingresos − egresos estimados (lo atrasado NO está: es stock)").setFontStyle("italic").setFontColor("#5f6368");
  h.getRange(fila, 1, 1, nCols + 2).setBackground("#fff8e1");
  var filaSaldo = fila++;
  h.getRange(fila, 1).setValue("Disponible al cierre (saldo + acuerdos de descubierto)").setFontWeight("bold");
  for (var k2 = 0; k2 < nCols; k2++) {
    var L3 = _colLetra_(2 + k2);
    if (k2 < atras) h.getRange(fila, 2 + k2).setValue("—").setHorizontalAlignment("right").setFontColor("#9aa0a6");
    else h.getRange(fila, 2 + k2).setFormula("=" + L3 + filaSaldo + "+" + acuerdos).setFontWeight("bold");
  }
  h.getRange(fila, 2 + nCols).setValue("negativo = ese día no se cubre lo comprometido con lo que hay: hay que elegir qué no pagar").setFontStyle("italic").setFontColor("#5f6368");
  h.getRange(fila, 1, 1, nCols + 2).setBackground("#fce8e6");
  fila += 2;

  // ---- atrasado (stock)
  _seccion_(h, fila++, (conBancos ? "4" : "3") + " · Atrasado (stock: no está en la curva, se paga por decisión)", "#fce8e6", "#a50e0e");
  _encabezado_(h, fila++, ["Concepto", "Monto", "", "", "", "", "Fuente"]);
  var primeraAtr = fila;
  reng.atrasado.forEach(function (r) {
    h.getRange(fila, 1).setValue(r.n).setFontStyle(r.info ? "italic" : "normal");
    h.getRange(fila, 2).setFormula(r.est);
    h.getRange(fila, 7).setValue(r.f).setFontStyle("italic").setFontColor("#5f6368");
    fila++;
  });
  h.getRange(fila, 1).setValue("Total atrasado a pagar").setFontWeight("bold");
  h.getRange(fila, 2).setFormula("=SUM(B" + primeraAtr + ":B" + (fila - 2) + ")").setFontWeight("bold");
  h.getRange(fila, 1, 1, 7).setBorder(true, false, true, false, false, false, "#3c4043", SpreadsheetApp.BorderStyle.SOLID_MEDIUM);

  // ---- formato
  h.getRange(1, 2, fila, nCols + 1).setNumberFormat("#,##0;[Red]-#,##0;\"—\"");
  h.getRange(2, 2, 2, 1).setNumberFormat("dd/mm/yyyy");
  h.setColumnWidth(1, 330);
  for (var w = 0; w < nCols; w++) h.setColumnWidth(2 + w, dias === 1 ? 92 : 104);
  h.setColumnWidth(2 + nCols, 420);
  h.setFrozenRows(conBancos ? 0 : filaFechas);
  h.setFrozenColumns(1);
  // fórmulas de fecha se formatean de nuevo (el número general las pisó)
  for (var i3 = 0; i3 < nCols; i3++) h.getRange(filaFechas, 2 + i3).setNumberFormat(dias === 1 ? "ddd dd/mm" : "\"sem\" dd/mm");
  if (conBancos) h.getRange(6, 6, fila, 1).setNumberFormat("dd/mm/yyyy");
}


// ---- (banco, cuenta) que existen en Saldos Bancarios, en el orden en que aparecen
function _cuentas_(ss) {
  var h = ss.getSheetByName("Saldos Bancarios");
  var vals = h.getRange(2, 1, Math.max(h.getLastRow() - 1, 1), 4).getValues();
  var vistos = {}, out = [];
  vals.forEach(function (r) {
    var banco = String(r[1] || "").trim(), cta = String(r[3] || "").trim();
    if (!banco) return;
    var k = banco + "|" + cta;
    if (vistos[k]) return;
    vistos[k] = true;
    out.push({ banco: banco, cuenta: cta });
  });
  return out;
}

function _filaTotalBancosDeCash_(ss) {
  var h = ss.getSheetByName("Cash");
  if (!h) return 1;
  var col = h.getRange(1, 1, h.getLastRow(), 1).getValues();
  for (var i = 0; i < col.length; i++) if (String(col[i][0]) === "Total bancos") return i + 1;
  return 1;
}

function _seccion_(h, fila, texto, fondo, color) {
  h.getRange(fila, 1).setValue(texto).setFontWeight("bold").setFontColor(color);
  h.getRange(fila, 1, 1, 8).setBackground(fondo);
}

function _encabezado_(h, fila, textos) {
  textos.forEach(function (t, i) { h.getRange(fila, 1 + i).setValue(t).setFontWeight("bold").setFontColor("#3c4043").setHorizontalAlignment(i === 0 || i === textos.length - 1 ? "left" : "right"); });
  h.getRange(fila, 1, 1, textos.length).setBackground("#f1f3f4");
}

function _colLetra_(n) {
  var s = "";
  while (n > 0) { var m = (n - 1) % 26; s = String.fromCharCode(65 + m) + s; n = Math.floor((n - 1) / 26); }
  return s;
}
