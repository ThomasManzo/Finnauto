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
 *   "Supuestos" / "Modelo Nuevo": proyección a 12 períodos desde datos explícitos;
 *                   se arman aparte ejecutando armarModeloNuevo(), sin pisar el cash.
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
 *  4. Lo atrasado (vencido) es un stock: se muestra por vencimiento, fuera de la curva. Se paga por decisión
 *     (solapa Plan → "Regularización de atrasado").
 *
 * Todo es fórmula. Nadie tipea acá: si un número está mal, está mal en la lista. Las
 * celdas sin nada quedan vacías (los ceros se muestran en blanco por formato).
 * Excepción: Modelo Nuevo muestra — si falta información y muestra los ceros confirmados.
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
var R = { planTipo: "Plan!$A:$A", planAuto: "Plan!$N:$N" };

var CAMPOS = [
  ["Movimientos",        1, { movFecha: "Fecha", movBanco: "Banco", movTipo: "Tipo", movCat: "Categoria", movImp: "Importe", movOrigen: "Origen", movEstado: "Estado" }],
  ["Cuentas a Cobrar",   1, { cobPend: "Saldo Pendiente", cobEmp: "Empresa", cobVto: "Fecha Vencimiento", cobEstado: "Estado", cobObs: "Observaciones" }],
  ["Cuentas a Pagar",    1, { pagPend: "Saldo Pendiente", pagEmp: "Empresa", pagVto: "Fecha Vencimiento", pagEstado: "Estado", pagObs: "Observaciones" }],
  ["Cartera de Cheques", 1, { chqTipo: "Tipo", chqFecha: "Fecha Pago / Cobro", chqImp: "Importe", chqEstado: "Estado", chqObs: "Observaciones" }],
  ["Saldos Bancarios",   1, { salFecha: "Fecha", salBanco: "Banco", salImp: "Saldo" }],
  ["Deuda Impositiva",   1, { diNombre: "Impuesto", diVto: "Fecha Vencimiento", diImp: "Importe", diEstado: "Estado", diAuto: "Debito Automatico" }],
];

function _rangos_(ss) {
  var out = { planTipo: "Plan!$A:$A", planAuto: "Plan!$N:$N" };
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
  out.dbAuto = rangoDB(encA, "Debito Automatico", encs[0] + 1, finA);
  out.cuBanco = rangoDB(encB, "Banco", iniB, finB);
  out.cuLinea = rangoDB(encB, "Linea / Producto", iniB, finB);
  out.cuVto = rangoDB(encB, "Fecha Vencimiento", iniB, finB);
  out.cuTot = rangoDB(encB, "Importe Total Cuota", iniB, finB);
  out.cuEstado = rangoDB(encB, "Estado", iniB, finB);
  out.cuAuto = rangoDB(encB, "Debito Automatico", iniB, finB);
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

var PLAN_PRIMERA_COL_MES = 16;          // columna P de Plan = mes en curso; Q..V los 6 siguientes (N = débito automático, O = por qué)


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
// Los datos no llegan todos juntos: el extracto de un banco puede ser del 22 y la caja de AA
// del 23. Si hubiera un solo corte para todo (el del banco), lo real de AA cargado después se
// perdería. Por eso cada origen tiene su propia fecha de corte, y su propio arranque de lo
// estimado: $B$3 = último extracto bancario · $B$5 = último día con caja de AA.
var CORTE_REAL = { "Extracto*": "$B$3", "Tango AA*": "$B$5" };
var DESDE_EST_AA = "MAX({D},$B$5+1)";

// Lo real viene de dos lados: el extracto de los bancos (Origen "Extracto…") y, para AA, la
// tesorería de Tango en efectivo (Origen "Tango AA…"). Las filas migradas ("Manual") no cuentan.
var ORIGENES_REALES = ["Extracto*", "Tango AA*"];
// El nombre puede traer comillas o comodines: se busca el banco literal, no un patrón.
function _criterioBanco_(banco) {
  return '"' + banco.replace(/~/g, "~~").replace(/\*/g, "~*").replace(/\?/g, "~?").replace(/"/g, '\"\"') + '"';
}
function _real_(tipo, cat, banco) {
  // entre paréntesis: los renglones de egreso le anteponen "-" y tiene que negar la suma entera
  return "(" + ORIGENES_REALES.map(function (origen) {
    var hasta = "MIN({F}," + (CORTE_REAL[origen] || "$B$3") + "+1)";
    return "SUMIFS(" + R.movImp + "," + R.movFecha + ",\">=\"&{D}," + R.movFecha + ",\"<\"&" + hasta + "," + R.movTipo + ",\"" + tipo + "\"," +
      R.movEstado + ",\"Real\"," + R.movOrigen + ",\"" + origen + "\"" + (cat ? "," + R.movCat + ",\"" + cat + "\"" : "") + (banco !== undefined ? "," + R.movBanco + "," + _criterioBanco_(banco) : "") + ")";
  }).join("+") + ")";
}
function _lista_(imp, fecha, extra, desde) {
  // "desde" sólo se pasa para los renglones de AA: lo estimado de AA no puede pisar días que
  // ya tienen movimiento real de caja cargado.
  return "SUMIFS(" + imp + "," + fecha + ",\">=\"&" + (desde || DESDE_EST) + "," + fecha + ",\"<\"&{F}" + extra + ")";
}
function _proy_(cat, distinto) {
  return "SUMIFS(" + R.movImp + "," + R.movFecha + ",\">=\"&" + DESDE_EST + "," + R.movFecha + ",\"<\"&{F}," + R.movTipo + ",\"Egreso\"," +
    R.movEstado + ",\"Proyectado\"," + R.movCat + ",\"" + (distinto ? "<>" : "") + cat + "\")";
}
function _planMes_(tipo, auto, banco) {
  // se resuelve por columna: {P} = letra de la columna del Plan para ese mes.
  // auto: "Si" = lo que el banco / ARCA debita solo · "No" = lo que se paga por decisión
  return "SUMIFS(Plan!${P}:${P}," + R.planTipo + ",\"" + tipo + "\"" + (auto ? "," + R.planAuto + ",\"" + auto + "\"" : "") + (banco !== undefined ? ",Plan!$B:$B," + _criterioBanco_(banco) : "") + ")";
}

// Un renglón: nombre · real (extracto) · est (listas) · cómo se estima en el mensual ·
// fuente. En el mensual, "prom" = promedio de los 3 meses base × (1+inflación)^n.
function _renglones_(periodo) {
  var mensual = periodo === "mes";
  var cobA = _lista_(R.cobPend, R.cobVto, "," + R.cobEmp + ",\"A\"," + R.cobEstado + ",\"<>Cobrado\"," + R.cobObs + ",\"<>REVISAR*\"");
  var cobAA = _lista_(R.cobPend, R.cobVto, "," + R.cobEmp + ",\"AA\"," + R.cobEstado + ",\"<>Cobrado\"," + R.cobObs + ",\"<>REVISAR*\"", DESDE_EST_AA);
  var chqT = _lista_(R.chqImp, R.chqFecha, "," + R.chqTipo + ",\"Terceros*\"," + R.chqEstado + ",\"En Cartera\"," + R.chqObs + ",\"<>REVISAR*\"");
  var pagA = _lista_(R.pagPend, R.pagVto, "," + R.pagEmp + ",\"A\"," + R.pagEstado + ",\"<>Pagado\"," + R.pagObs + ",\"<>REVISAR*\"");
  var pagAA = _lista_(R.pagPend, R.pagVto, "," + R.pagEmp + ",\"AA\"," + R.pagEstado + ",\"<>Pagado\"," + R.pagObs + ",\"<>REVISAR*\"", DESDE_EST_AA);
  var cuotasAuto = _lista_(R.cuTot, R.cuVto, "," + R.cuEstado + ",\"Pendiente\"," + R.cuAuto + ",\"Si\"");
  var cuotasDec = _lista_(R.cuTot, R.cuVto, "," + R.cuEstado + ",\"Pendiente\"," + R.cuAuto + ",\"<>Si\"");
  var impAuto = _lista_(R.diImp, R.diVto, "," + R.diEstado + ",\"<>Pagado\"," + R.diAuto + ",\"Si\"");
  var impDec = _lista_(R.diImp, R.diVto, "," + R.diEstado + ",\"<>Pagado\"," + R.diAuto + ",\"<>Si\"");
  var chqP = _lista_(R.chqImp, R.chqFecha, "," + R.chqTipo + ",\"Propio*\"," + R.chqEstado + ",\"En Cartera\"," + R.chqObs + ",\"<>REVISAR*\"");
  var interes90 = "-SUMIFS(" + R.movImp + "," + R.movTipo + ",\"Egreso\"," + R.movCat + ",\"Gastos Bancarios\"," + R.movOrigen + ",\"Extracto*\"," + R.movFecha + ",\">=\"&($B$3-90))/90*MAX(0,{F}-" + DESDE_EST + ")";

  var ingresos = [
    { n: "Cobranza acreditada", real: _real_("Ingreso", "Cobranza Facturas"), est: mensual ? "" : cobA, como: "prom",
      f: "real: transferencias y depósitos de clientes (extracto) · estimado: " + (mensual ? "promedio × inflación" : "facturas A que vencen en Tango") },
    { n: "Cobranza AA (efectivo)", real: _real_("Ingreso", "Cobranza AA"), est: cobAA, como: "lista", lista: cobAA,
      f: "real: recibos de AA en la tesorería de Tango (efectivo) · estimado: facturas AA que vencen en Tango" },
    { n: "Cheques de clientes (depositados y descontados)", real: _real_("Ingreso", "Cheques") + "+" + _real_("Ingreso", "Descuento de Cheques"), est: mensual ? "" : chqT, como: "prom",
      f: "real: cheques depositados + venta de valores / descuento (extracto) · estimado: " + (mensual ? "promedio × inflación" : "cheques en cartera por fecha de cobro") },
    { n: "Sin identificar (tiene que ser 0)", real: _real_("Ingreso", "Otros"), est: "", como: "cero", f: "lo que el banco acreditó sin decir qué es" },
  ];
  var egresos = [
    { n: "Proveedores A", real: _real_("Egreso", "Proveedores MP y Logist."), est: mensual ? "" : pagA, como: "max", lista: pagA,
      f: "real: pagos a proveedores (extracto) · estimado: " + (mensual ? "el mayor entre lo que vence en Tango y el promedio × inflación" : "facturas A que vencen en Tango") },
    { n: "Proveedores AA", real: _real_("Egreso", "Proveedores AA"), est: pagAA, como: "lista", lista: pagAA, f: "real: órdenes de pago de AA en la tesorería de Tango (efectivo) · estimado: facturas AA que vencen en Tango" },
    { n: "Sueldos y cargas", real: _real_("Egreso", "Sueldos y Jornales"), est: mensual ? "" : "-" + _proy_("Sueldos y Jornales"), como: "prom",
      f: "real: extracto (Macro) · estimado: " + (mensual ? "promedio × inflación" : "lo proyectado con fecha en Movimientos") },
    { n: "Impuestos corrientes", real: _real_("Egreso", "Impuestos"), est: "", como: "prom",
      f: "real: extracto · estimado: " + (mensual ? "promedio × inflación" : "no se estima día a día; ver Cash Mensual") },
    { n: "Cheques propios", real: _real_("Egreso", "Cheques"), est: chqP, como: "lista", lista: chqP, f: "real: debitados (extracto) · estimado: en cartera por fecha de pago" },
    { n: "Intereses y gastos bancarios", real: _real_("Egreso", "Gastos Bancarios"), est: mensual ? "" : interes90, como: "prom",
      f: "real: extracto · estimado: " + (mensual ? "promedio × inflación" : "promedio de los últimos 90 días") },
    { n: "Otros (tarjeta, honorarios)", real: _real_("Egreso", "Otros") + "+" + _real_("Egreso", "Honorarios y Dividendos"), est: "-" + _proy_("Sueldos y Jornales", true), como: "lista", lista: "-" + _proy_("Sueldos y Jornales", true),
      f: "real: extracto · estimado: lo proyectado con fecha en Movimientos (salvo sueldos)" },
  ];
  // Deuda en dos bloques. "Sale sí o sí": el banco o ARCA la debita solo cuando hay fondos
  // (cuotas y tarjetas con débito automático, planes vigentes con CBU). "Por decisión": alguien
  // tiene que transferir o generar el VEP. La columna "Debito Automatico" de las listas dice cuál es cuál.
  var deudaAuto = mensual ? [
    { n: "Cuotas y tarjetas con débito automático", real: _real_("Egreso", "Prestamo"), est: "", como: "plan", plan: "Banco", auto: "Si", f: "real: cuotas debitadas (extracto) · estimado: solapa Plan, líneas con débito automático" },
    { n: "Planes de ARCA con débito automático", real: "", est: "", como: "plan", plan: "Impuesto", auto: "Si", f: "solapa Plan, impuestos con débito automático" },
    { n: "Préstamos tomados (entra plata: resta)", real: _real_("Ingreso", "Prestamo"), est: "", como: "cero", f: "real: préstamos acreditados (extracto), con signo negativo porque entran · no se proyecta: es una decisión" },
  ] : [
    { n: "Cuotas y tarjetas con débito automático", real: _real_("Egreso", "Prestamo"), est: cuotasAuto, como: "lista", f: "real: cuotas debitadas (extracto) · estimado: cronograma, líneas con débito automático" },
    { n: "Planes de ARCA con débito automático", real: "", est: impAuto, como: "lista", f: "estimado: Deuda Impositiva con débito automático, por fecha de vencimiento" },
    { n: "Préstamos tomados (entra plata: resta)", real: _real_("Ingreso", "Prestamo"), est: "", como: "cero", f: "real: préstamos acreditados, con signo negativo porque entran · no se proyecta" },
  ];
  var deudaDec = mensual ? [
    { n: "Cuotas que se pagan por decisión", real: "", est: "", como: "plan", plan: "Banco", auto: "No", f: "solapa Plan, líneas sin débito automático (transferencia)" },
    { n: "Impuestos por VEP y planes nuevos", real: "", est: "", como: "plan", plan: "Impuesto", auto: "No", f: "solapa Plan, impuestos sin débito automático" },
    { n: "Regularización de atrasado", real: "", est: "", como: "plan", plan: "Atrasado", f: "solapa Plan: lo vencido con proveedores y cheques que se decide pagar en cuotas" },
  ] : [
    { n: "Cuotas que se pagan por decisión", real: "", est: cuotasDec, como: "lista", f: "estimado: cronograma, líneas sin débito automático" },
    { n: "Impuestos por VEP y planes nuevos", real: "", est: impDec, como: "lista", f: "estimado: Deuda Impositiva sin débito automático, por fecha de vencimiento" },
  ];
  var atrasado = [
    { n: "Proveedores A vencidos", fecha: R.pagVto, est: "SUMIFS(" + R.pagPend + "," + R.pagEmp + ",\"A\"," + R.pagVto + ",\"<\"&$B$2," + R.pagEstado + ",\"<>Pagado\"," + R.pagObs + ",\"<>REVISAR*\")", f: "Cuentas a Pagar · vencimiento < hoy · sin la deuda vieja (REVISAR)" },
    { n: "Proveedores AA vencidos", fecha: R.pagVto, est: "SUMIFS(" + R.pagPend + "," + R.pagEmp + ",\"AA\"," + R.pagVto + ",\"<\"&$B$2," + R.pagEstado + ",\"<>Pagado\"," + R.pagObs + ",\"<>REVISAR*\")", f: "ídem" },
    { n: "Cuotas bancarias impagas", fecha: R.cuVto, est: "SUMIFS(" + R.cuTot + "," + R.cuVto + ",\"<\"&$B$2," + R.cuEstado + ",\"Pendiente\")", f: "Deuda Bancaria · cronograma" },
    { n: "Impuestos vencidos", fecha: R.diVto, est: "SUMIFS(" + R.diImp + "," + R.diVto + ",\"<\"&$B$2," + R.diEstado + ",\"<>Pagado\")", f: "Deuda Impositiva" },
    { n: "Cheques propios vencidos sin debitar", fecha: R.chqFecha, est: "SUMIFS(" + R.chqImp + "," + R.chqTipo + ",\"Propio*\"," + R.chqEstado + ",\"En Cartera\"," + R.chqFecha + ",\"<\"&$B$2)", f: "Cartera de Cheques · confirmar con el extracto" },
    { n: "Vencido a cobrar (informativo, no suma)", est: "SUMIFS(" + R.cobPend + "," + R.cobVto + ",\"<\"&$B$2," + R.cobEstado + ",\"<>Cobrado\"," + R.cobObs + ",\"<>REVISAR*\")", f: "Cuentas a Cobrar", info: true },
  ];
  return { ingresos: ingresos, egresos: egresos, deudaAuto: deudaAuto, deudaDec: deudaDec, atrasado: atrasado };
}


// Parte el mismo stock por vencimiento: conserva los estados, importes y exclusiones
// del total. No usa el corte del extracto: una obligación vence aunque falte el banco.
function _atrasadoEntre_(lista, desde, hasta) {
  return lista.filter(function (r) { return !r.info; }).map(function (r) {
    // Una fecha vacía o cero no es un vencimiento: queda en el control para revisar.
    var condiciones = "," + r.fecha + ',">0"';
    if (desde) condiciones += "," + r.fecha + ',">="&' + desde;
    if (hasta) condiciones += "," + r.fecha + ',"<"&' + hasta;
    return r.est.slice(0, -1) + condiciones + ")";
  }).join("+");
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
  var cuentasVista = _cuentasVistaBancos_(ss);
  var h = _hojaLimpia_(ss, nombre, colFuente);

  _titulo_(h, "CASH · " + _cliente_(ss) + " · " + cabecera, colFuente);
  h.getRange(2, 1).setValue("Hoy"); h.getRange(2, 2).setFormula("=TODAY()").setNumberFormat("dd/mm/yyyy");
  h.getRange(3, 1).setValue("Último día con extracto (real hasta acá)"); h.getRange(3, 2).setFormula("=MAXIFS(" + R.movFecha + "," + R.movOrigen + ",\"Extracto*\")").setNumberFormat("dd/mm/yyyy");
  h.getRange(3, 3).setValue("en $ · verde = real (extracto) · amarillo = estimado (listas con fecha) · qué es cada renglón y de dónde sale: solapa Instrucciones").setFontStyle("italic").setFontColor("#5f6368");
  // La caja de AA no depende del banco: puede estar más al día que el extracto. Cada origen
  // corre hasta su propia fecha, así lo real de hoy suma aunque el banco venga atrasado.
  h.getRange(5, 1).setValue("Último día con caja de AA (efectivo)");
  h.getRange(5, 2).setFormula("=MAXIFS(" + R.movFecha + "," + R.movOrigen + ",\"Tango AA*\")").setNumberFormat("dd/mm/yyyy");
  h.getRange(5, 3).setValue("la caja de AA sale de la tesorería de Tango; lo real de cada origen suma por su fecha, no por la del banco").setFontStyle("italic").setFontColor("#5f6368");
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
  var bancosCuotas = _bancosDeuda_(ss);
  // El alto se calcula al rearmar; ningún banco tiene un renglón reservado a mano.
  var filasNecesarias = 162 + bancosCuotas.length + 2 * _bancos_(ss).length + 3 * cuentasVista.length;
  if (h.getMaxRows() < filasNecesarias) h.insertRowsAfter(h.getMaxRows(), filasNecesarias - h.getMaxRows());
  // clear() no quita grupos: desarmarlos evita acumular niveles en cada corrida.
  h.getRange(2, 1, h.getMaxRows() - 1, 1).shiftRowGroupDepth(-8);
  h.setRowGroupControlPosition(SpreadsheetApp.GroupControlTogglePosition.BEFORE);
  var fila = filaFechas + 2;

  // ---- 1. margen por banco. El saldo real queda aparte: el acuerdo no es plata ingresada.
  _seccion_(h, fila++, "1 · Bancos (saldo real + descubierto acordado)", "#e8f0fe", "#174ea6", colFuente);
  var primeraCuentaVista = fila;
  fila += 2 * cuentasVista.length;
  var bancos = _bancos_(ss), primeraMargen = fila;
  fila += bancos.length;
  var primeraFechaVista = fila;
  fila += cuentasVista.length;
  var primeraBanco = fila;
  // Al rearmar, las filas antes ocultas pueden haber cambiado de lugar.
  h.showRows(1, h.getMaxRows());
  h.clearConditionalFormatRules();
  var colAcuerdo = colFuente + 1;            // auxiliar oculta: acuerdo de descubierto de cada banco
  bancos.forEach(function (b, indice) {
    var filaMargen = primeraMargen + indice;
    h.getRange(filaMargen, 1).setValue(b.etiqueta + " · margen con acuerdo");
    h.getRange(filaMargen, 1).setNote("Saldo real + descubierto acordado. Gris e itálica: alguna cuenta arrastra un saldo anterior; ver la fecha debajo de cada saldo. Con fotos al corte: verde si queda margen, ámbar si está agotado y rojo si está excedido. Sin acuerdo informado se suma cero. No modifica los cierres.");
    h.getRange(fila, 1).setValue(b.etiqueta + " · saldo real (auxiliar)");
    h.getRange(fila, colAcuerdo).setFormula("=SUMIFS(" + R.dbOrig + "," + R.dbBanco + ",\"" + b.nombre + "\"," + R.dbLinea + ",\"*escubierto*\")");
    for (var c = 0; c < nCols; c++) {
      // la caja AA se carga a mano y puede ser más nueva que el último extracto: llega hasta hoy
      // hasta HOY: si el banco no mandó extracto, el saldo es el último conocido, no un vacío
      var corte = "MIN(" + F(c) + "-1,$B$2)";
      var cond = R.salBanco + ",\"" + b.nombre + "\"";
      var ult = "MAXIFS(" + R.salFecha + "," + cond + "," + R.salFecha + ",\"<=\"&" + corte + ")";
      var primero = "MINIFS(" + R.salFecha + "," + cond + ")";
      // si no hay saldo anterior al corte (la caja AA se cargó el 31/08), se toma el primero conocido
      // La caja de AA se calcula sola: último arqueo cargado + los movimientos de caja
      // posteriores (la tesorería de AA ya está en Movimientos con su fecha y su signo).
      var base = "SUMIFS(" + R.salImp + "," + cond + "," + R.salFecha + ",IF(" + ult + "=0," + primero + "," + ult + "))";
      var desdeArqueo = "IF(" + ult + "=0," + primero + "," + ult + ")";
      var movCaja = "SUMIFS(" + R.movImp + "," + R.movOrigen + ",\"Tango AA*\"," + R.movEstado + ",\"Real\"," +
                    R.movFecha + ",\">\"&" + desdeArqueo + "," + R.movFecha + ",\"<=\"&" + corte + ")";
      h.getRange(fila, 2 + c).setFormula("=IF(" + D(c) + ">$B$2,\"\"," + base + (b.manual ? "+" + movCaja : "") + ")");
    }
    fila++;
  });
  // Estas filas siguen alimentando los cierres y el descubierto usado/disponible, sin neteo.
  if (bancos.length) h.hideRows(primeraBanco, bancos.length);
  var filaSaldoReal = fila, ultimoBanco = fila - 1;
  h.getRange(fila, 1).setValue("Total saldo real de bancos").setFontWeight("bold");
  for (var c1 = 0; c1 < nCols; c1++) h.getRange(fila, 2 + c1).setFormula("=IF(" + D(c1) + ">$B$2,\"\",SUM(" + L(c1) + primeraBanco + ":" + L(c1) + (fila - 1) + "))").setFontWeight("bold");
  _lineaTotal_(h, fila, colFuente);
  fila++;
  var filaAvisoArrastre = fila++;
  // Saldo inicial del período = cierre del anterior (como el "Saldo inicio" de un cash a mano).
  // Se llena después, cuando se sepa en qué fila queda el cierre.
  var filaInicial = fila;
  h.getRange(fila, 1).setValue("Saldo inicial (cierre del período anterior)").setFontWeight("bold");
  h.getRange(fila, 1, 1, colFuente).setBackground("#fff8e1");
  fila += 2;

  // ---- 2. ingresos · 3. egresos de la operación · 4. deuda
  function bloque(titulo, lista) {
    _seccion_(h, fila++, titulo, "#e8f0fe", "#174ea6", colFuente);
    var principales = [], grupos = [], ampliada = [];
    lista.forEach(function (r) {
      ampliada.push(r);
      if (r.n !== "Cuotas y tarjetas con débito automático") return;
      bancosCuotas.forEach(function (banco) {
        ampliada.push({ n: "    " + banco, detalle: true, banco: banco,
          real: _real_("Egreso", "Prestamo", banco),
          est: _lista_(R.cuTot, R.cuVto, "," + R.cuEstado + ",\"Pendiente\"," + R.cuAuto + ",\"Si\"," + R.cuBanco + "," + _criterioBanco_(banco)),
          como: r.como, plan: r.plan, auto: r.auto });
      });
    });
    ampliada.forEach(function (r) {
      if (!r.detalle) principales.push(fila);
      if (r.n === "Cuotas y tarjetas con débito automático" && bancosCuotas.length) grupos.push(fila + 1);
      h.getRange(fila, 1).setValue(r.n);
      var promRef = mensual ? "$" + _colLetra_(colProm) + fila : "";
      for (var c = 0; c < nCols; c++) {
        var partes = [];
        // ingresos van en positivo; egresos y deuda en negativo. "Préstamos tomados" está en
        // Deuda y son ingresos del extracto: con el "-" quedan negativos (restan de la deuda).
        if (r.real) partes.push("(" + (r.n.indexOf("Cobranza") === 0 || r.n.indexOf("Cheques de clientes") === 0 || r.n.indexOf("Sin identificar") === 0 ? "" : "-") + fx(r.real, c) + ")");
        var est = "";
        if (mensual && c >= atras) {
          var n = "((YEAR(" + D(c) + ")-YEAR($" + _colLetra_(1 + atras) + "$" + filaFechas + "))*12+MONTH(" + D(c) + ")-MONTH($" + _colLetra_(1 + atras) + "$" + filaFechas + "))";
          var parte = "MAX(0,(" + F(c) + "-" + fx(DESDE_EST, c) + ")/DAY(EOMONTH(" + D(c) + ",0)))";   // fracción del mes que falta
          var prom = promRef + "*(1+$B$4)^" + n + "*" + parte;
          if (r.como === "prom") est = prom;
          else if (r.como === "max") est = "MAX(" + fx(r.lista, c) + "," + prom + ")";
          else if (r.como === "lista") est = fx(r.lista || r.est, c);
          else if (r.como === "plan") est = fx(_planMes_(r.plan, r.auto, r.banco), c);
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
    grupos.forEach(function (inicio) {
      h.getRange(inicio, 1, bancosCuotas.length, colFuente).shiftRowGroupDepth(1);
      h.getRowGroup(inicio, 1).collapse();
    });
    // El detalle ya está dentro de su total: sumarlo otra vez inflaría la deuda.
    var filaTotal = fila;
    h.getRange(fila, 1).setValue("Total " + titulo.replace(/^\d · /, "").toLowerCase()).setFontWeight("bold");
    for (var c2 = 0; c2 < nCols; c2++) h.getRange(fila, 2 + c2).setFormula("=SUM(" + principales.map(function (r) { return L(c2) + r; }).join(",") + ")").setFontWeight("bold");
    _lineaTotal_(h, fila, colFuente);
    fila += 2;
    return filaTotal;
  }
  var totIng = bloque("2 · Ingresos", reng.ingresos);
  var totOpe = bloque("3 · Egresos de la operación", reng.egresos);

  // ---- resultado de la operación: lo que la operación deja antes de cualquier deuda
  h.getRange(fila, 1).setValue("Resultado de la operación (antes de la deuda)").setFontWeight("bold");
  for (var c3 = 0; c3 < nCols; c3++) h.getRange(fila, 2 + c3).setFormula("=" + L(c3) + totIng + "-" + L(c3) + totOpe).setFontWeight("bold");
  h.getRange(fila, 1, 1, colFuente).setBackground("#e6f4ea");
  var filaResOpe = fila++;
  fila++;

  var totAuto = bloque("4 · Deuda que sale sí o sí (débito automático)", reng.deudaAuto);
  // ---- cierre 1: pagando solo lo automático (como "sin pago a droguerías" en un cash a mano)
  h.getRange(fila, 1).setValue("SALDO AL CIERRE pagando solo lo que sale sí o sí").setFontWeight("bold");
  var filaCierre1 = fila++;
  fila++;

  var totDec = bloque("5 · Deuda que se paga por decisión", reng.deudaDec);
  // ---- cierre 2: pagando también lo que es por decisión (es el que arrastra al período siguiente)
  h.getRange(fila, 1).setValue("SALDO AL CIERRE pagando toda la deuda").setFontWeight("bold");
  var filaCierre = fila++;
  h.getRange(fila, 1).setValue("Deuda pospuesta acumulada (si solo se paga lo automático)").setFontColor("#a50e0e");
  var filaPospuesta = fila++;
  h.getRange(fila, 1).setValue("Resultado después de la deuda").setFontWeight("bold");
  for (var c4 = 0; c4 < nCols; c4++) h.getRange(fila, 2 + c4).setFormula("=" + L(c4) + filaResOpe + "-" + L(c4) + totAuto + "-" + L(c4) + totDec).setFontWeight("bold");
  var filaRes = fila++;
  // ---- lo que venció en el período y NO se pagó (solo en lo real): es lo que hace que la
  // operación "dé positiva" por banco. Facturas a pagar con vencimiento en el período que siguen
  // pendientes + impuestos ídem. Hacia adelante queda vacío: lo estimado ya cuenta lo que vence.
  h.getRange(fila, 1).setValue("Venció en el período y no se pagó (proveedores + impuestos)").setFontColor("#b3261e");
  for (var c6 = 0; c6 < nCols; c6++) {
    var hasta6 = "MIN(" + F(c6) + ",$B$3+1)";
    var prov6 = "SUMIFS(" + R.pagPend + "," + R.pagVto + ",\">=\"&" + D(c6) + "," + R.pagVto + ",\"<\"&" + hasta6 + "," + R.pagEstado + ",\"<>Pagado\"," + R.pagObs + ",\"<>REVISAR*\")";
    var imp6 = "SUMIFS(" + R.diImp + "," + R.diVto + ",\">=\"&" + D(c6) + "," + R.diVto + ",\"<\"&" + hasta6 + "," + R.diEstado + ",\"<>Pagado\")";
    h.getRange(fila, 2 + c6).setFormula("=IF(" + D(c6) + ">$B$3,\"\"," + prov6 + "+" + imp6 + ")").setFontColor("#b3261e");
  }
  var filaNoPag = fila++;
  h.getRange(fila, 1).setValue("Resultado de la operación pagando lo que vencía").setFontWeight("bold");
  for (var c7 = 0; c7 < nCols; c7++) h.getRange(fila, 2 + c7).setFormula("=IF(" + D(c7) + ">$B$3,\"\"," + L(c7) + filaResOpe + "-" + L(c7) + filaNoPag + ")").setFontWeight("bold");
  h.getRange(fila, 1, 1, colFuente).setBackground("#fce8e6");
  fila++;
  fila++;

  // ---- lo real del período que tiene al último extracto adentro (para no contarlo dos veces en el saldo)
  var filaRealIng = fila, filaRealEgr = fila + 1;
  h.getRange(fila, 1).setValue("de lo cual ya pasó (real): ingresos").setFontSize(10).setFontColor("#9aa0a6");
  h.getRange(fila + 1, 1).setValue("de lo cual ya pasó (real): egresos").setFontSize(10).setFontColor("#9aa0a6");
  for (var c5 = 0; c5 < nCols; c5++) {
    var base5 = function (origen) { return R.movFecha + ",\">=\"&" + D(c5) + "," + R.movFecha + ",\"<\"&" + fx(HASTA_REAL, c5) + "," + R.movEstado + ",\"Real\"," + R.movOrigen + ",\"" + origen + "\"," + R.movCat + ",\"<>Transferencia Interna\""; };
    h.getRange(fila, 2 + c5).setFormula("=" + ORIGENES_REALES.map(function (o) { return "SUMIFS(" + R.movImp + "," + base5(o) + "," + R.movTipo + ",\"Ingreso\")"; }).join("+")).setFontSize(10).setFontColor("#9aa0a6");
    h.getRange(fila + 1, 2 + c5).setFormula("=-(" + ORIGENES_REALES.map(function (o) { return "SUMIFS(" + R.movImp + "," + base5(o) + "," + R.movTipo + ",\"Egreso\")"; }).join("+") + ")").setFontSize(10).setFontColor("#9aa0a6");
  }
  h.hideRows(filaRealIng, 2);         // auxiliares: las usa el saldo al cierre, no hace falta verlas
  fila += 3;

  // ---- saldo al cierre (pagando toda la deuda): real hasta el último extracto; después,
  //      inicial + ingresos − egresos − deuda. Es el que arrastra al período siguiente.
  var cierreTxt = periodo === "dia" ? "del día" : (periodo === "semana" ? "de la semana" : "del mes");
  h.getRange(filaCierre, 1).setValue("SALDO AL CIERRE " + cierreTxt + " pagando toda la deuda");
  for (var c6 = 0; c6 < nCols; c6++) {
    var ing = L(c6) + totIng, egr = "(" + L(c6) + totOpe + "+" + L(c6) + totAuto + "+" + L(c6) + totDec + ")";
    var mixto = L(c6) + filaSaldoReal + "+(" + ing + "-" + L(c6) + filaRealIng + ")-(" + egr + "-" + L(c6) + filaRealEgr + ")";
    var futuro = c6 === 0 ? mixto : L(c6) + filaInicial + "+" + ing + "-" + egr;
    h.getRange(filaCierre, 2 + c6).setFormula("=IF(" + F(c6) + "-1<=$B$3," + L(c6) + filaSaldoReal + ",IF(" + D(c6) + "<=$B$3," + mixto + "," + futuro + "))").setFontWeight("bold");
    // saldo inicial: el cierre de la columna anterior; en la primera, el cierre real menos lo que pasó en ella
    h.getRange(filaInicial, 2 + c6).setFormula(c6 === 0
      ? "=" + L(0) + filaSaldoReal + "-" + L(0) + filaRealIng + "+" + L(0) + filaRealEgr
      : "=" + L(c6 - 1) + filaCierre).setFontWeight("bold");
    // deuda pospuesta acumulada: solo hacia adelante, suma lo que se pagaría por decisión y no se paga
    h.getRange(filaPospuesta, 2 + c6).setFormula("=IF(" + F(c6) + "-1<=$B$3,\"\"," + (c6 === 0 ? "0" : "N(" + L(c6 - 1) + filaPospuesta + ")") + "+" + L(c6) + totDec + ")").setFontColor("#a50e0e");
    // cierre 1 = cierre pagando todo + lo que se dejó de pagar
    h.getRange(filaCierre1, 2 + c6).setFormula("=" + L(c6) + filaCierre + "+N(" + L(c6) + filaPospuesta + ")").setFontWeight("bold");
  }
  h.getRange(filaCierre, 1, 1, colFuente).setBackground("#fff8e1");
  h.getRange(filaCierre1, 1, 1, colFuente).setBackground("#fff8e1");
  fila++;

  // ---- descubierto: acordado · usado · disponible. Con extracto, banco por banco (un banco
  //      excedido no se compensa con otro en positivo); hacia adelante, sobre el total.
  var rB = function (c) { return L(c) + primeraBanco + ":" + L(c) + ultimoBanco; };
  var rA = _colLetra_(colAcuerdo) + primeraBanco + ":" + _colLetra_(colAcuerdo) + ultimoBanco;
  h.getRange(fila, 1).setValue("Descubierto acordado con los bancos");
  for (var c7 = 0; c7 < nCols; c7++) h.getRange(fila, 2 + c7).setFormula("=SUM(" + rA + ")");
  var filaAcordado = fila++;
  h.getRange(fila, 1).setValue("Descubierto usado (saldos en negativo)");
  // "real" acá = la columna termina antes del último extracto (banco por banco); si no, sobre el cierre estimado
  var esReal = function (c) { return F(c) + "-1<=$B$3"; };
  for (var c8 = 0; c8 < nCols; c8++) h.getRange(fila, 2 + c8).setFormula("=IF(" + esReal(c8) + ",SUMPRODUCT((" + rB(c8) + "<0)*(-" + rB(c8) + ")),MAX(0,-" + L(c8) + filaCierre + "))");
  var filaUsado = fila++;
  h.getRange(fila, 1).setValue("Descubierto disponible (acordado − usado, banco por banco)").setFontWeight("bold");
  for (var c9 = 0; c9 < nCols; c9++) {
    var porBanco = "(" + rA + "+(" + rB(c9) + "<0)*" + rB(c9) + ")";
    h.getRange(fila, 2 + c9).setFormula("=IF(" + esReal(c9) + ",SUMPRODUCT((" + porBanco + ">0)*" + porBanco + "),MAX(0," + L(c9) + filaAcordado + "-" + L(c9) + filaUsado + "))").setFontWeight("bold");
  }
  var filaDispDesc = fila++;
  // con extracto: saldos en positivo + descubierto disponible banco por banco. Estimado: cierre + acordado
  // (puede dar negativo: es lo que falta aun usando todo el descubierto).
  h.getRange(fila, 1).setValue("Saldo disponible pagando toda la deuda (positivos + descubierto disponible)").setFontWeight("bold");
  for (var c10 = 0; c10 < nCols; c10++) h.getRange(fila, 2 + c10).setFormula("=IF(" + esReal(c10) + ",SUMPRODUCT((" + rB(c10) + ">0)*" + rB(c10) + ")+" + L(c10) + filaDispDesc + "," + L(c10) + filaCierre + "+" + L(c10) + filaAcordado + ")").setFontWeight("bold");
  h.getRange(fila, 1, 1, colFuente).setBackground("#fce8e6");
  fila++;
  h.getRange(fila, 1).setValue("Saldo disponible pagando solo lo que sale sí o sí").setFontWeight("bold");
  for (var c11 = 0; c11 < nCols; c11++) h.getRange(fila, 2 + c11).setFormula("=" + L(c11) + (fila - 1) + "+N(" + L(c11) + filaPospuesta + ")").setFontWeight("bold");
  h.getRange(fila, 1, 1, colFuente).setBackground("#fce8e6");
  fila += 2;

  // ---- 6. atrasado (stock)
  _seccion_(h, fila++, "6 · Atrasado hoy (stock: no está en la curva; se paga por decisión, en Plan)", "#fce8e6", "#a50e0e", colFuente);
  var primeraAtr = fila;
  reng.atrasado.forEach(function (r) {
    h.getRange(fila, 1).setValue(r.n).setFontStyle(r.info ? "italic" : "normal");
    h.getRange(fila, 2).setFormula("=" + r.est);
    fila++;
  });
  h.getRange(fila, 1).setValue("Total atrasado a pagar").setFontWeight("bold");
  h.getRange(fila, 2).setFormula("=SUM(B" + primeraAtr + ":B" + (fila - 2) + ")").setFontWeight("bold");
  _lineaTotal_(h, fila, colFuente);
  var filaTotalAtr = fila;
  fila += 2;
  h.getRange(fila++, 1).setValue("Detalle del stock por vencimiento original · no mueve la caja").setFontWeight("bold");
  // Repetimos las fechas acá: los totales de arriba están en B, pero no son del primer día.
  for (var ca = 0; ca < nCols; ca++) {
    h.getRange(fila, 2 + ca).setFormula("=" + D(ca)).setNumberFormat(fmt);
  }
  var filaFechasAtr = fila++;
  var filaDetalleAtr = fila;
  h.getRange(fila, 1).setValue("Venció en ese período y sigue impago hoy");
  for (var cd = 0; cd < nCols; cd++) {
    h.getRange(fila, 2 + cd).setFormula("=" + _atrasadoEntre_(reng.atrasado, D(cd), F(cd)));
  }
  fila++;
  var filaAntesAtr = fila;
  h.getRange(fila, 1).setValue("Venció antes del primer período visible");
  h.getRange(fila++, 2).setFormula("=" + _atrasadoEntre_(reng.atrasado, null, D(0)));
  // Si el extracto quedó muy atrás, puede haber vencido deuda después de la última
  // columna diaria. No la escondemos ni la metemos a la fuerza en otra fecha.
  var filaDespuesAtr = fila;
  h.getRange(fila, 1).setValue("Venció después del último período visible");
  h.getRange(fila++, 2).setFormula("=" + _atrasadoEntre_(reng.atrasado, F(nCols - 1), null));
  var filaRepartidoAtr = fila;
  h.getRange(fila, 1).setValue("Total repartido por vencimiento").setFontWeight("bold");
  h.getRange(fila++, 2).setFormula("=SUM(B" + filaDetalleAtr + ":" + L(nCols - 1) + filaDetalleAtr + ",B" + filaAntesAtr + ",B" + filaDespuesAtr + ")");
  h.getRange(fila, 1).setValue("Control: total atrasado menos repartido (debe dar 0)")
    .setNote("Si no da cero, revisar fechas vacías, cero o inválidas en las listas. No se inventa una fecha para hacer cuadrar el detalle. El vencido a cobrar no suma. Los proveedores REVISAR siguen excluidos como en el total.");
  h.getRange(fila, 2).setFormula("=ROUND(B" + filaTotalAtr + "-B" + filaRepartidoAtr + ",2)");

  // ---- formato y colores de columnas (verde real, amarillo estimado; se recalcula al rearmar)
  h.getRange(filaFechas + 2, 2, fila - filaFechas - 1, colFuente - 2).setNumberFormat(FORMATO_NUM);
  h.getRange(primeraAtr, 2, filaTotalAtr - primeraAtr + 1, 1).setNumberFormat('#,##0.00;[Red]-#,##0.00;""');
  h.getRange(filaTotalAtr + 2, 1, fila - filaTotalAtr - 1, 1).setWrap(true);
  h.getRange(filaFechasAtr, 2, 1, nCols).setNumberFormat(fmt).setFontWeight("bold");
  h.getRange(filaDetalleAtr, 2, fila - filaDetalleAtr + 1, nCols).setNumberFormat('#,##0.00;[Red]-#,##0.00;""');
  h.getRange(fila, 2).setNumberFormat('#,##0.00;[Red]-#,##0.00;0.00');
  h.getRange(2, 2, 2, 1).setNumberFormat("dd/mm/yyyy");
  for (var i2 = 0; i2 < nCols; i2++) {
    h.getRange(filaFechas, 2 + i2).setNumberFormat(fmt);
    h.getRange(filaFechas, 2 + i2, 2, 1).setBackground(i2 < atras ? "#e6f4ea" : "#fef7e0");
  }
  h.setColumnWidth(1, 380);
  for (var w = 0; w < nCols; w++) h.setColumnWidth(2 + w, ancho);
  if (mensual) { h.setColumnWidth(colProm, 104); h.setColumnWidth(colComo, 200); }
  h.setColumnWidth(colFuente, 20);
  h.getRange(primeraBanco, colAcuerdo, ultimoBanco - primeraBanco + 1, 1).setNumberFormat(FORMATO_NUM);
  h.hideColumns(colAcuerdo);          // auxiliar: acuerdo de descubierto por banco
  // El detalle nuevo sólo muestra datos: ninguna fórmula de cierre lo toma como base.
  _mostrarArrastreBancos_(h, cuentasVista, bancos, primeraCuentaVista, primeraFechaVista,
    primeraMargen, primeraBanco, filaAvisoArrastre, colAcuerdo, nCols, D, F, L);
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
  if (/cheques/.test(a)) return [2, "Posponer", 0, 0, 0, "confirmar con la empresa si ya se pagaron (según el extracto, varios parecen debitados)"];
  return [6, "Posponer", 3, 12, 0, "se regulariza cuando la refinanciación libere caja; primero los que cortan la hoja"];
}

function armarPlan() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  R = _rangos_(ss);
  var nMeses = MESES_ADELANTE + 1;
  var h = _hojaLimpia_(ss, "Plan", 15 + nMeses);
  _titulo_(h, "PLAN · " + _cliente_(ss) + " · qué se paga, qué se refinancia, qué se pospone", 15 + nMeses);
  h.getRange(2, 1).setValue("Hoy"); h.getRange(2, 2).setFormula("=TODAY()").setNumberFormat("dd/mm/yyyy");
  h.getRange(3, 1).setValue("Las filas son la deuda REAL (Deuda Bancaria, Deuda Impositiva, lo vencido). La Decisión (columna H) arranca con la propuesta inicial y se cambia a mano. Si es refinanciar o regularizar: gracia, cuotas y tasa → la cuota nueva se calcula sola (sistema francés) y los meses de la derecha muestran cuánto sale cada mes. 'Débito automático' (N) dice si el banco / ARCA lo debita solo (Sí) o si se paga por decisión (No): el cash separa la deuda en esos dos bloques. Cash Mensual suma esos meses.").setFontStyle("italic").setFontColor("#5f6368");

  var enc = ["Tipo", "Acreedor", "Concepto", "Deuda total hoy", "Vencido hoy", "Vence en 6 meses (cronograma)", "Prioridad (1 = primero)",
             "Decisión", "Meses de gracia", "Cuotas nuevas", "Tasa mensual", "Cuota nueva", "Primer vencimiento", "Débito automático", "Por qué"];
  var filaEnc = 5;
  enc.forEach(function (t, i) { h.getRange(filaEnc, 1 + i).setValue(t).setFontWeight("bold").setWrap(true); });
  for (var m = 0; m < nMeses; m++) h.getRange(filaEnc, PLAN_PRIMERA_COL_MES + m).setFormula("=EOMONTH($B$2," + (m - 1) + ")+1").setNumberFormat("mmm yy").setFontWeight("bold").setHorizontalAlignment("right");
  h.getRange(filaEnc, 1, 1, 15 + nMeses).setBackground("#f1f3f4").setBorder(false, false, true, false, false, false, "#3c4043", SpreadsheetApp.BorderStyle.SOLID_MEDIUM);
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
    // débito automático: viene de la lista (Deuda Bancaria / Deuda Impositiva); el atrasado siempre es por decisión
    if (f.tipo === "Banco") h.getRange(r, 14).setFormula("=IFERROR(INDEX(FILTER(" + R.dbAuto + "," + R.dbBanco + "=" + B + "," + R.dbLinea + "=" + C + "),1),\"No\")");
    else if (f.tipo === "Impuesto") h.getRange(r, 14).setFormula("=IFERROR(INDEX(FILTER(" + R.diAuto + "," + R.diNombre + "=" + C + "),1),\"No\")");
    else h.getRange(r, 14).setValue("No");
    h.getRange(r, 15).setValue(p[5]);
    h.getRange(r, 7, 1, 5).setBackground("#fff8e1"); h.getRange(r, 15).setBackground("#fff8e1");
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
  _lineaTotal_(h, fila, 15 + nMeses);
  h.getRange(filaEnc + 1, 4, fila - filaEnc, 3).setNumberFormat(FORMATO_NUM);
  h.getRange(filaEnc + 1, 12, fila - filaEnc, 1).setNumberFormat(FORMATO_NUM);
  h.getRange(filaEnc + 1, PLAN_PRIMERA_COL_MES, fila - filaEnc, nMeses).setNumberFormat(FORMATO_NUM);
  h.getRange(filaEnc + 1, 11, fila - filaEnc, 1).setNumberFormat("0.0%");
  h.setColumnWidth(1, 80); h.setColumnWidth(2, 150); h.setColumnWidth(3, 260); [4, 5, 6].forEach(function (c) { h.setColumnWidth(c, 110); });
  h.setColumnWidth(7, 80); h.setColumnWidth(8, 150); h.setColumnWidth(9, 70); h.setColumnWidth(10, 70); h.setColumnWidth(11, 70); h.setColumnWidth(12, 110); h.setColumnWidth(13, 100); h.setColumnWidth(14, 90); h.setColumnWidth(15, 320);
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
  function parrafo(t) { h.getRange(fila, 1, 1, 4).merge().setValue(t).setWrap(true).setFontColor("#5f6368"); fila += 2; }
  function tabla(enc, filas) {
    enc.forEach(function (e, i) { h.getRange(fila, 1 + i).setValue(e).setFontWeight("bold").setBackground("#f1f3f4"); });
    fila++;
    filas.forEach(function (f) { f.forEach(function (v, i) { h.getRange(fila, 1 + i).setValue(v).setWrap(true).setVerticalAlignment("top"); }); fila++; });
    fila++;
  }
  titulo(_cliente_(ss) + " — Cash Flow: cómo funciona");
  sub("Actualizado el " + Utilities.formatDate(new Date(), "America/Argentina/Buenos_Aires", "dd/MM/yyyy") + ". Regla única: los datos viven en las LISTAS; las PANTALLAS son fórmula. Nadie tipea un número en una pantalla. La carga es automática: los archivos se dejan en Drive y el sistema hace el resto.");

  seccion("1 · Las solapas");
  tabla(["Solapa", "Qué es", "De dónde sale", "Quién la toca"], [
    ["Cash", "Día por día: 7 días de extracto (real) + 28 días adelante (estimado)", "fórmula sobre las listas", "nadie"],
    ["Cash Semanal", "Semana por semana, lunes a domingo: 4 cerradas (real) + la actual + 12 adelante", "fórmula sobre las listas", "nadie"],
    ["Cash Mensual", "Mes por mes: 3 cerrados (real) + el actual + 6 adelante, con inflación editable (B4)", "fórmula sobre las listas + solapa Plan", "solo la celda de inflación"],
    ["Plan", "Una fila por deuda: pagar como está / refinanciar / posponer. Cash Mensual toma las cuotas de acá", "Deuda Bancaria + Deuda Impositiva + lo vencido", "la dirección: Decisión, gracia, cuotas, tasa, prioridad"],
    ["Movimientos", "LISTA: cada movimiento real, clasificado: los de banco (Origen Extracto) y los de la caja de AA (Origen Tango AA)", "extractos + tesorería de AA → lectores → importación automática", "el sistema"],
    ["Saldos Bancarios", "LISTA: saldo al cierre de cada día, por cuenta. La caja en efectivo de AA se carga a mano (una fila por arqueo)", "extractos → lector → importación automática · caja AA: a mano", "el sistema · la caja AA: quien hace el arqueo"],
    ["Cuentas a Cobrar", "LISTA: facturas pendientes de clientes, con vencimiento", "Tango → lector → importación automática", "el sistema"],
    ["Cuentas a Pagar", "LISTA: facturas pendientes de proveedores, con vencimiento", "Tango → lector → importación automática", "el sistema"],
    ["Cartera de Cheques", "LISTA: cheques de terceros en cartera y cheques propios entregados", "Tango → lector → importación automática", "el sistema"],
    ["Deuda Bancaria", "LISTA: A) cada línea con su capital · B) cronograma: cada cuota pendiente. 'Debito Automatico' dice si el banco la debita solo", "mapa de deuda + extractos → lector → importación automática", "el sistema · el capital, a mano si el banco no manda tabla"],
    ["Deuda Impositiva", "LISTA: cada deuda con ARCA / DGR / municipio, con vencimiento. 'Debito Automatico' = planes con débito en CBU", "planilla de impuestos → lector → importación automática", "el sistema"],
    ["Registro", "Una fila por cada importación automática: cuándo, qué archivo, cuántas filas, o el error", "lo escribe el disparador", "nadie"],
  ]);

  seccion("2 · Cómo se lee una pantalla (las tres tienen la misma estructura)");
  tabla(["Parte", "Qué muestra"], [
    ["Hoy / Último extracto", "B2 es hoy; B3 el último día con extracto. Hasta B3 todo es REAL; desde el día siguiente, ESTIMADO. La fila bajo las fechas lo dice por columna (real · estimado · real + est.)."],
    ["1 · Bancos", "Saldo real + descubierto acordado: verde si queda margen, ámbar si da cero, rojo si está excedido. Sin acuerdo se suma cero. El total real y los cierres no incluyen el acuerdo. El detalle por cuenta muestra saldo sin acuerdo y debajo su fecha: ARRASTRADO en gris e itálica si es anterior al corte (hoy o fin del período pasado); Confirmado si coincide. El margen con acuerdo también queda gris si arrastra alguna cuenta. Sin foto previa se avisa. El aviso junto al total cuenta las cuentas arrastradas y su fecha más vieja; el total conserva su corte de extracto. Vacío en períodos futuros: no se inventa saldo por banco."],
    ["Saldo inicial", "El cierre del período anterior. Es el 'saldo inicio' de un cash hecho a mano: de acá se parte cada día / semana / mes."],
    ["2 · Ingresos", "Un renglón por concepto. Real atrás (extracto), estimado adelante (listas). Sin préstamos: los préstamos no son operación."],
    ["3 · Egresos de la operación", "Ídem: proveedores, sueldos, impuestos corrientes, cheques propios, banco, otros."],
    ["Resultado de la operación", "Ingresos − egresos de la operación. Lo que la operación deja ANTES de cualquier deuda."],
    ["4 · Deuda que sale sí o sí", "Lo que el banco o ARCA debita solo cuando hay fondos: cuotas y tarjetas con débito automático, planes vigentes. Acá también entran (restando) los préstamos tomados."],
    ["SALDO AL CIERRE pagando solo lo que sale sí o sí", "Escenario 1: si no se paga nada por decisión. Es el saldo 'de mínima'."],
    ["5 · Deuda que se paga por decisión", "Cuotas por transferencia, impuestos por VEP, planes nuevos, regularización de atrasado. Alguien tiene que decidir pagarlo."],
    ["SALDO AL CIERRE pagando toda la deuda", "Escenario 2: pagando todo lo que vence. Es el que arrastra al período siguiente como saldo inicial."],
    ["Deuda pospuesta acumulada", "Si se elige el escenario 1: cuánto se fue dejando de pagar, sumado período a período. Es lo que se acumula como atrasado nuevo."],
    ["Resultado después de la deuda", "Resultado de la operación menos toda la deuda. Negativo = la deuda se come más de lo que la operación deja."],
    ["Venció en el período y no se pagó", "Facturas de proveedores e impuestos con vencimiento en ese período que siguen impagos (solo en lo real). Es la parte de la operación que se financió NO pagando."],
    ["Resultado de la operación pagando lo que vencía", "Lo que hubiera quedado pagando todo lo que venció. Es el número honesto de la operación."],
    ["Descubierto acordado · usado · disponible", "Acordado: lo que cada banco autorizó. Usado: los saldos en negativo. Disponible: acordado − usado, banco por banco (un banco excedido no se compensa con otro en positivo). Hacia adelante, sobre el total."],
    ["Saldo disponible", "Saldos en positivo + descubierto disponible, en los dos escenarios. Negativo = no se cubre lo comprometido ni usando todo el descubierto: hay que elegir."],
    ["6 · Atrasado hoy", "Stock por concepto y detalle por vencimiento original: cada importe va al día, semana o mes en que venció. Fuera de la curva; no cambia cierres. Antes/después de las fechas visibles se muestra aparte. Total menos repartido debe dar 0; si no, revisar fechas. Excluye vencido a cobrar y conserva los filtros del stock. Baja cuando la lista actualizada registra el pago; no basta el extracto. Se paga por decisión, en Plan."],
  ]);

  seccion("3 · Cada renglón: qué es lo real y qué es lo estimado");
  tabla(["Renglón", "REAL (columnas pasadas)", "ESTIMADO (columnas futuras)"], [
    ["Cobranza acreditada", "transferencias y depósitos de clientes (Movimientos · Cobranza Facturas)", "diario/semanal: facturas A que vencen (Cuentas a Cobrar) · mensual: promedio × inflación"],
    ["Cobranza AA (efectivo)", "recibos de AA en la tesorería de Tango (Movimientos · Cobranza AA, Origen Tango AA)", "facturas AA que vencen (Cuentas a Cobrar)"],
    ["Cheques de clientes", "cheques depositados + venta de valores / descuento (Movimientos · Cheques + Descuento de Cheques)", "diario/semanal: cheques en cartera por fecha de cobro · mensual: promedio × inflación"],
    ["Sin identificar", "lo que el banco acreditó sin decir qué es (Movimientos · Otros)", "tiene que ser 0"],
    ["Proveedores A", "pagos a proveedores (Movimientos · Proveedores)", "diario/semanal: facturas A que vencen (Cuentas a Pagar) · mensual: el mayor entre eso y el promedio × inflación"],
    ["Proveedores AA", "órdenes de pago de AA en la tesorería de Tango (Movimientos · Proveedores AA, Origen Tango AA)", "facturas AA que vencen (Cuentas a Pagar)"],
    ["Sueldos y cargas", "Movimientos · Sueldos y Jornales", "diario/semanal: lo proyectado con fecha en Movimientos · mensual: promedio × inflación"],
    ["Impuestos corrientes", "Movimientos · Impuestos (IVA, cargas, retenciones pagadas)", "mensual: promedio × inflación · diario/semanal: no se estima"],
    ["Cheques propios", "cheques debitados (Movimientos · Cheques, egreso)", "en cartera por fecha de pago (Cartera de Cheques)"],
    ["Intereses y gastos bancarios", "Movimientos · Gastos Bancarios", "diario/semanal: promedio de los últimos 90 días · mensual: promedio × inflación"],
    ["Otros (tarjeta, honorarios)", "Movimientos · Otros + Honorarios", "lo proyectado con fecha en Movimientos (salvo sueldos)"],
    ["Cuotas y tarjetas con débito automático", "cuotas debitadas (Movimientos · Prestamo, egreso)", "diario/semanal: cronograma de Deuda Bancaria (Debito Automatico = Si) · mensual: solapa Plan. Abrir + para ver por banco; al sumar un banco nuevo, Armar solapa Cash actualiza el detalle sin editar código."],
    ["Planes de ARCA con débito automático", "—", "Deuda Impositiva (Debito Automatico = Si) · mensual: solapa Plan"],
    ["Préstamos tomados", "préstamos acreditados (Movimientos · Prestamo, ingreso), restando", "no se proyecta: es una decisión"],
    ["Cuotas que se pagan por decisión", "—", "cronograma (Debito Automatico = No) · mensual: solapa Plan"],
    ["Impuestos por VEP y planes nuevos", "—", "Deuda Impositiva (Debito Automatico = No) · mensual: solapa Plan"],
    ["Regularización de atrasado", "—", "mensual: solapa Plan (lo vencido que se decide pagar en cuotas)"],
  ]);

  seccion("4 · Cómo impacta cada movimiento (qué se mueve cuando pasa algo)");
  tabla(["Pasa esto", "Dónde entra", "Qué cambia en las pantallas"], [
    ["Un cliente paga por transferencia", "Movimientos (real, extracto) · en Tango: recibo → la factura sale de Cuentas a Cobrar", "sube 'Cobranza acreditada' real y el saldo del banco; baja lo estimado a cobrar y el vencido a cobrar"],
    ["Un cliente paga con cheque", "Tango: recibo + Cartera de Cheques (terceros, fecha de cobro)", "sube 'Cheques de clientes' estimado en la fecha de cobro; el saldo real no cambia hasta que se deposita o descuenta"],
    ["Se descuenta un cheque (venta de valores)", "Movimientos (Descuento de Cheques) · el cheque sale de la cartera", "sube el saldo real hoy; el interés va a 'Intereses y gastos bancarios'"],
    ["Se paga a un proveedor", "Movimientos (Proveedores) · en Tango: orden de pago → la factura sale de Cuentas a Pagar", "sube 'Proveedores A' real, baja el saldo; baja lo estimado y el vencido a pagar"],
    ["Se entrega un cheque propio", "Cartera de Cheques (propio, fecha de pago)", "aparece en 'Cheques propios' estimado en esa fecha; cuando se debita pasa a real"],
    ["Se paga una cuota", "Movimientos (Prestamo egreso) · Deuda Bancaria: la cuota pasa a Pagado, baja el capital", "baja el saldo; baja 'cuotas' estimado; baja la deuda total en Plan; baja 'cuotas impagas' si estaba vencida"],
    ["Entra un préstamo", "Movimientos (Prestamo ingreso) · Deuda Bancaria: línea nueva + cronograma", "sube el saldo hoy (en el bloque Deuda, restando); suben las cuotas futuras y la deuda total"],
    ["Se paga un impuesto", "Movimientos (Impuestos) · Deuda Impositiva: la fila pasa a Pagado", "baja el saldo; baja lo estimado y lo vencido de impuestos"],
    ["Se firma un plan de pagos con ARCA", "Deuda Impositiva: la deuda pasa a Pagado y se cargan las cuotas (o en Plan: 'Refinanciar')", "baja el stock vencido; aparecen cuotas mensuales en el bloque que corresponda (débito automático o VEP)"],
    ["Se refinancia un préstamo", "Deuda Bancaria: cronograma nuevo (o en Plan: 'Refinanciar' con gracia, cuotas y tasa)", "cambian las cuotas futuras; el mensual toma el Plan"],
    ["No se paga algo que vencía", "nada: la factura sigue en la lista con vencimiento pasado", "al día siguiente sube 'Atrasado hoy' y 'Venció y no se pagó'; no se corre solo a mañana: se paga por decisión (Plan)"],
    ["Se usa más descubierto", "el saldo real del banco queda más negativo", "sube 'Descubierto usado', baja el disponible"],
    ["Transferencia entre cuentas propias", "Movimientos, marcada INTERNO", "no cambia nada: sale de una cuenta y entra en otra"],
  ]);

  seccion("5 · Cómo se actualiza (sola)");
  tabla(["Paso", "Quién", "Qué hace", "Dónde"], [
    ["1", "la empresa o el bot", "deja el archivo nuevo en SU carpeta de Drive (una carpeta por export, ver tabla de abajo)", "Drive · carpeta de datos"],
    ["2", "el vigilante (cada 15 min)", "ve el archivo nuevo y corre el lector que corresponde; el lector deja el para_pegar_*.xlsx en '_para la Sheet'. Si una lista se achica de golpe (un export con filtro cambiado), lo retiene y no publica", "log del vigilante"],
    ["3", "el disparador de esta Sheet (cada hora)", "ve el para_pegar nuevo y lo importa: pisa lo que ese lector cargó antes, no toca fórmulas ni lo cargado a mano; si el lector trae una columna nueva, la agrega", "solapa Registro"],
    ["4", "las pantallas", "recalculan solas: B3 avanza, lo real reemplaza lo estimado, la cobranza que entró sale del 'a cobrar'", "Cash · Cash Semanal · Cash Mensual"],
    ["a mano", "quien hace el arqueo", "una fila por arqueo en Saldos Bancarios: fecha, Varios, AA, saldo, Manual", "Saldos Bancarios"],
    ["a mano", "la dirección", "las decisiones: pagar / refinanciar / posponer, gracia, cuotas, tasa", "Plan"],
    ["si hace falta", "finauto → Importar lo nuevo ahora", "lo mismo que el disparador, sin esperar la hora", "menú finauto"],
    ["si cambió la estructura", "finauto → Armar solapa Cash", "rearma las pantallas; Plan no se toca", "menú finauto"],
    ["después", "bots de banco + bajada de Tango por API", "hacen el paso 1 solos cada mañana", "nadie sube nada: el cash amanece al día"],
  ]);

  seccion("5b · Las carpetas de Drive: una por export");
  tabla(["Carpeta", "Qué se deja", "Nombre del archivo", "A qué solapa va"], [
    ["Bancos/<banco>", "el extracto (PDF) o el Excel de movimientos del home banking. Se acumulan: cada mes se agrega el nuevo, nada se borra", "como venga del banco", "Saldos Bancarios · Movimientos"],
    ["Cuentas a cobrar", "Tango Live: composición de saldos de clientes, de cada empresa, un archivo por día", "A cobranzas AAAA-MM-DD.xlsx · AA cobranzas AAAA-MM-DD.xlsx", "Cuentas a Cobrar"],
    ["Cuentas a pagar", "Tango Live: composición de saldos de proveedores", "A pagos AAAA-MM-DD.xlsx · AA pagos AAAA-MM-DD.xlsx", "Cuentas a Pagar"],
    ["Cheques", "Tango Live: cheques de terceros en cartera y cheques propios emitidos", "A cheques terceros AAAA-MM-DD.xlsx · A cheques propios AAAA-MM-DD.xlsx · AA cheques terceros ...", "Cartera de Cheques"],
    ["Deuda bancaria", "el mapa de deuda cuando cambie", "Bancos_Navar.xlsx", "Deuda Bancaria"],
    ["Impuestos", "la planilla de vencimientos impositivos cuando cambie", "Control Vencimiento Impuestos.xlsx", "Deuda Impositiva"],
    ["Tesorería AA", "Tango Live: movimientos de tesorería de NAVAR SA Otros (recibos, órdenes de pago, otros), un archivo por día", "AA movimientos tesoreria AAAA-MM-DD.xlsx", "Movimientos (Origen Tango AA)"],
    ["_para la Sheet", "NO TOCAR: lo que generan los lectores; de acá lo levanta el disparador", "para_pegar_*.xlsx", "—"],
  ]);
  parrafo("Cada export de Tango es la FOTO completa de ese día (no lo nuevo desde ayer): se carga el más nuevo de cada lista; los anteriores quedan como historia. El nombre importa: primera palabra = empresa (A / AA), después qué es (cobranzas / pagos / cheques terceros / cheques propios), después la fecha. Los filtros de cada consulta tienen que ser los mismos cada vez (vencimiento sin límite, pendientes): si cambian, el vigilante retiene el archivo y no se publica.");

  seccion("6 · Reglas que no se rompen");
  tabla(["Regla", "Por qué"], [
    ["Nadie tipea números en las pantallas", "si un número está mal, está mal en la lista: se corrige ahí y las pantallas cambian solas"],
    ["Real y estimado no se mezclan en una celda", "salvo en la columna del último extracto, que lo dice"],
    ["Las filas 'REVISAR:' no suman", "están para no perder información, no para el cash"],
    ["Lo vencido es un stock, no un movimiento", "no arranca la curva en rojo; se paga por decisión"],
    ["Los préstamos no son operación", "entran en el bloque Deuda, restando; el resultado de la operación se lee sin ellos"],
    ["Ningún número se muestra sin validar", "la caja la confirma el extracto; lo vencido, Tango; la deuda, el banco"],
  ]);
  h.setColumnWidth(1, 260); h.setColumnWidth(2, 420); h.setColumnWidth(3, 420); h.setColumnWidth(4, 300);
}


// ================================================================== ayudas
// Se toma la lista real de deuda (líneas y cronograma) al rearmar las pantallas.
// Un banco nuevo entra sin editar el código; no se agregan filas mientras alguien mira el cash.
function _bancosDeuda_(ss) {
  var h = ss.getSheetByName("Deuda Bancaria"), vistos = {}, bancos = [];
  [R.dbBanco, R.cuBanco].forEach(function (rango) {
    h.getRange(rango.split("!")[1]).getValues().forEach(function (r) {
      var banco = String(r[0] || "").trim(), clave = _n_(banco);
      if (!banco || vistos[clave]) return;
      vistos[clave] = true;
      bancos.push(banco);
    });
  });
  return bancos.sort();
}

// Una cuenta se reconoce por banco, empresa y número: dos cuentas no comparten su fecha.
function _cuentasVistaBancos_(ss) {
  var h = ss.getSheetByName("Saldos Bancarios");
  var datos = h.getDataRange().getValues(), enc = datos[0];
  var campos = ["Banco", "Empresa", "Cuenta / Nro"], cols = campos.map(function (nombre) {
    var c = _colPorNombre_(enc, nombre);
    if (c < 0) throw new Error("Saldos Bancarios: falta " + nombre + " para distinguir cada cuenta");
    return c;
  });
  var vistos = {}, cuentas = [];
  datos.slice(1).forEach(function (r) {
    if (!r[cols[0]]) return;
    var valores = cols.map(function (c) { return r[c]; }), clave = JSON.stringify(valores);
    if (vistos[clave]) return;
    vistos[clave] = true;
    // Escapamos los comodines para que un número o nombre se busque tal cual está escrito.
    var cond = cols.map(function (c, i) {
      var literal = String(valores[i]).replace(/~/g, "~~").replace(/\*/g, "~*").replace(/\?/g, "~?").replace(/"/g, '""');
      return "'Saldos Bancarios'!$" + _colLetra_(c + 1) + ":$" + _colLetra_(c + 1) + ',"=' + literal + '"';
    }).join(",");
    cuentas.push({ banco: String(valores[0]).trim(), etiqueta: valores.join(" · "), cond: cond });
  });
  return cuentas;
}

function _mostrarArrastreBancos_(h, cuentas, bancos, primera, fechas, margen, auxiliares, aviso, colAcuerdo, nCols, D, F, L) {
  var reglas = [];
  cuentas.forEach(function (cuenta, i) {
    var r = primera + 2 * i, rf = fechas + i;
    h.getRange(r, 1).setValue(cuenta.etiqueta + " · saldo sin acuerdo");
    h.getRange(r + 1, 1).setValue("↳ Fecha y estado del saldo de arriba");
    h.getRange(r, 2, 2, nCols).setWrap(true).setNumberFormat("#,##0;-#,##0;0");
    h.setRowHeight(r + 1, 64);
    for (var c = 0; c < nCols; c++) {
      var fecha = L(c) + rf, saldo = L(c) + r, corte = "MIN(" + F(c) + "-1,$B$2)";
      // Nunca buscamos después de hoy ni traemos la primera foto hacia días anteriores.
      h.getRange(rf, 2 + c).setFormula('=IF(' + D(c) + '>$B$2,0,MAXIFS(' + R.salFecha + ',' + cuenta.cond + ',' + R.salFecha + ',"<="&' + corte + ',' + R.salFecha + ',">0"))');
      var condFecha = cuenta.cond + ',' + R.salFecha + ',' + fecha;
      // Una foto duplicada o sin importe no se convierte en cero ni en un saldo confirmado.
      var valor = 'SUMIFS(' + R.salImp + ',' + condFecha + ')';
      var vacios = 'COUNTIFS(' + condFecha + ',' + R.salImp + ',"=")';
      var textos = 'COUNTIFS(' + condFecha + ',' + R.salImp + ',"*")';
      h.getRange(r, 2 + c).setFormula('=IF(' + D(c) + '>$B$2,"",IF(' + fecha + '=0,"Sin saldo previo",IF(OR(COUNTIFS(' + condFecha + ')<>1,' + vacios + '>0,' + textos + '>0),"Revisar saldo",' + valor + ')))');
      h.getRange(r + 1, 2 + c).setFormula('=IF(' + D(c) + '>$B$2,"",IF(' + fecha + '=0,"Sin saldo previo",IF(ISNUMBER(' + saldo + '),IF(' + fecha + '<' + corte + ',"ARRASTRADO · al ","Confirmado · al "),"REVISAR · al ")&TEXT(' + fecha + ',"dd/mm/yyyy")))');
    }
    var rango = h.getRange(r, 2, 2, nCols), f = 'B$' + rf;
    reglas.push(SpreadsheetApp.newConditionalFormatRule().whenFormulaSatisfied('=AND(' + f + '>0,' + f + '<MIN(' + F(0) + '-1,$B$2))').setBackground("#f1f3f4").setFontColor("#5f6368").setItalic(true).setRanges([rango]).build());
  });
  if (cuentas.length) h.hideRows(fechas, cuentas.length);
  // El acuerdo sigue siendo uno por banco, aunque haya varias cuentas en ese banco.
  bancos.forEach(function (b, i) {
    var indices = [];
    cuentas.forEach(function (cuenta, j) { if (cuenta.banco === b.nombre) indices.push(j); });
    var r = margen + i;
    for (var c = 0; c < nCols; c++) {
      var saldos = indices.map(function (j) { return L(c) + (primera + 2 * j); }).join(",");
      if (!indices.length) continue;
      h.getRange(r, 2 + c).setFormula('=IF(' + D(c) + '>$B$2,"",IF(COUNT(' + saldos + ')<>' + indices.length + ',"Revisar cuentas",SUM(' + saldos + ')+N($' + _colLetra_(colAcuerdo) + (auxiliares + i) + ')))');
    }
    var celda = "B" + r, rango = h.getRange(r, 2, 1, nCols);
    var ff = indices.map(function (j) { return "B" + (fechas + j); }).join(",");
    if (indices.length) {
      // Gris gana a los colores del margen: un saldo viejo nunca parece recién confirmado.
      reglas.push(SpreadsheetApp.newConditionalFormatRule().whenFormulaSatisfied('=AND(ISNUMBER(' + celda + '),MIN(' + ff + ')<MIN(' + F(0) + '-1,$B$2))').setBackground("#f1f3f4").setFontColor("#5f6368").setItalic(true).setRanges([rango]).build());
      [[">0", "#e6f4ea", "#137333"], ["=0", "#fef7e0", "#8a5700"], ["<0", "#fce8e6", "#b3261e"]].forEach(function (color) {
        reglas.push(SpreadsheetApp.newConditionalFormatRule().whenFormulaSatisfied('=AND(ISNUMBER(' + celda + '),' + celda + color[0] + ')').setBackground(color[1]).setFontColor(color[2]).setRanges([rango]).build());
      });
    }
    h.getRange(r, 2, 1, nCols).setNumberFormat("#,##0;-#,##0;0").setWrap(true);
  });
  h.getRange(aviso, 1).setValue("Antigüedad del detalle de cuentas · total y cierres conservan su corte de extracto");
  h.getRange(aviso, 1, 1, nCols + 1).setWrap(true).setFontSize(9);
  h.setRowHeight(aviso, 150);
  for (var c = 0; c < nCols; c++) {
    if (!cuentas.length) { h.getRange(aviso, 2 + c).setValue("Sin cuentas"); continue; }
    var rangoFechas = L(c) + fechas + ':' + L(c) + (fechas + cuentas.length - 1);
    var corte = 'MIN(' + F(c) + '-1,$B$2)';
    var cantidad = 'COUNTIFS(' + rangoFechas + ',">0",' + rangoFechas + ',"<"&' + corte + ')';
    h.getRange(aviso, 2 + c).setFormula('=IF(' + D(c) + '>$B$2,"",' + cantidad + '&" cuentas con saldo arrastrado"&IF(' + cantidad + '>0," · más viejo al "&TEXT(MINIFS(' + rangoFechas + ',' + rangoFechas + ',">0"),"dd/mm/yyyy"),"")&IF(COUNTIF(' + rangoFechas + ',0)>0," · "&COUNTIF(' + rangoFechas + ',0)&" sin saldo previo",""))');
  }
  h.setConditionalFormatRules(reglas);
}

function _bancos_(ss) {
  var h = ss.getSheetByName("Saldos Bancarios");
  var vals = h.getRange(2, 1, Math.max(h.getLastRow() - 1, 1), 7).getValues();
  var vistos = {}, out = [];
  vals.forEach(function (r) {
    var banco = String(r[1] || "").trim();
    if (!banco || vistos[banco]) return;
    vistos[banco] = true;
    var manual = String(r[5] || "").toLowerCase().indexOf("manual") !== -1;
    out.push({ nombre: banco, manual: manual, etiqueta: banco.toLowerCase().indexOf("vario") !== -1 ? "AA · caja en efectivo (carga manual)" : banco,
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

// ================================================================== Modelo Nuevo
// Se corre aparte: no rearma el cash actual, no cambia Plan ni la inflación ya cargada.
// Los números de este bloque son plazos del calendario, filas y reglas de cálculo;
// no son supuestos del negocio. Todos los casilleros para cargar datos nacen vacíos.
function armarModeloNuevo() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var s = _mnSupuestos_(ss);
  var fuentes = _mnFuentes_(ss);
  _mnPantalla_(ss, s, fuentes);
  _separadorLocal_(ss, ss.getSheetByName("Supuestos"));
  _separadorLocal_(ss, ss.getSheetByName("Modelo Nuevo"));
  ss.toast("Modelo Nuevo armado. Cargá Supuestos; los faltantes se ven arriba y por renglón.", "finauto", 8);
}

function _mnDefiniciones_() {
  var d = [
    ["precio", "Ventas · precio por kilo", "$/kg", "comercial", "Precio del primer período; después acompaña la inflación."],
    ["cobro", "Ventas · condición de cobro", "días", "administración", "Días corridos desde la venta; ventas parejas dentro de cada período."],
    ["canchada", "Canchada · precio por kilo", "$/kg", "compras", "Precio del primer período."],
    ["rendimiento", "Canchada · kilos por kilo vendido", "kg/kg", "producción", "Consumo necesario para cada kilo vendido."],
    ["pago", "Canchada · condición de pago", "días", "compras", "Plazo de la parte que no se anticipa, desde la compra."],
    ["anticipo", "Canchada · anticipo", "%", "compras", "Parte pagada al inicio del período de compra. Cargar 0 si no hay. No modela anticipos anteriores a la compra."],
    ["pack", "Packaging · costo por kilo vendido", "$/kg", "compras", "Se paga en el período de venta."],
    ["nomina", "Personal · nómina completa confirmada", "Sí", "administración", "Completar la tabla de puestos al pie y luego elegir Sí. Sin puestos y con Sí declara que no hay personal ni honorarios."],
    ["cargas", "Personal · cargas sobre sueldos brutos", "%", "el estudio", "No aplica a honorarios. Cargar 0 sólo si está confirmado."],
    ["indem", "Indemnizaciones · importe total", "$", "administración", "Importe nominal total; no lleva inflación. 0 declara que no hay."],
    ["mesIndem", "Indemnizaciones · primer mes de pago", "mes 1 a 12", "administración", "Se pide sólo si el importe es mayor que 0."],
    ["cuotas", "Indemnizaciones · cantidad de cuotas", "cuotas", "administración", "Cuotas mensuales iguales; 1 si se paga todo junto. El remanente fuera del horizonte se informa."],
    ["comision", "Comercial · comisión", "%", "comercial", "Se paga en el mismo período que su base."],
    ["base", "Comercial · base de comisión", "Facturada / Cobrada", "comercial", "Cobrada incluye el cobro de ventas anteriores cargado abajo."],
    ["tipoFlete", "Fletes · forma de cálculo", "$/kg / % venta", "logística", "Elegir una sola base."],
    ["flete", "Fletes · tarifa elegida", "$/kg o proporción", "logística", "Si elegiste % venta, ingresar como porcentaje (por ejemplo con el signo %)."],
    ["seguros", "Seguros · importe mensual", "$/mes", "administración", "Importe de un mes completo; primer período parcial se prorratea."],
    ["energia", "Energía · importe mensual", "$/mes", "administración", "Importe de un mes completo."],
    ["gas", "Gas · importe mensual", "$/mes", "administración", "Importe de un mes completo."],
    ["impuestos", "Impuestos corrientes · importe mensual", "$/mes", "el estudio", "Sólo operación nueva; excluir cargas sociales e impuestos ya incluidos en Deuda Impositiva."],
    ["imprevistos", "Imprevistos · proporción del total operativo", "%", "la dirección", "Menor que 100%. Provisión = otros egresos × porcentaje / (1 − porcentaje). No incluye indemnizaciones ni deuda."],
    ["stock", "Stock · días de canchada (opcional)", "días", "producción", "Vacío: capital de trabajo SIN stock, indicado en pantalla. No programa compras para formar stock."],
    ["deuda", "Deuda · cronogramas completos confirmados", "Sí", "administración", "Confirmar capital e intereses para los 12 períodos, incluso meses sin deuda. No supone que una lista vacía signifique ausencia de deuda."],
    ["saldo", "Caja · saldos al día confirmados", "Sí", "administración", "Confirmar que las últimas fotos por banco, empresa y cuenta representan la caja real de hoy, incluida la caja física. No incluye acuerdos de descubierto."]
  ];
  for (var m = 1; m <= 12; m++) {
    d.push(["kg" + m, "Ventas · kilos del período " + m, "kg", "comercial", m === 1 ? "Sólo desde mañana hasta fin de mes; no el mes completo." : "Volumen del mes, sin inflación."]);
    d.push(["cobAnterior" + m, "Arranque · cobros de ventas anteriores · período " + m, "$", "administración", "Importe nominal pendiente de cobrar por ventas hasta hoy. 0 sólo si se confirmó que no hay."]);
    d.push(["pagAnterior" + m, "Arranque · pagos operativos anteriores · período " + m, "$", "administración", "Obligaciones operativas hasta hoy que se pagarán en este período, sin deuda financiera ni impositiva del cronograma. 0 sólo si se confirmó que no hay."]);
  }
  return d;
}

function _mnSupuestos_(ss) {
  var h = ss.getSheetByName("Supuestos");
  if (!h) h = ss.insertSheet("Supuestos");
  if (h.getMaxColumns() < 40) h.insertColumnsAfter(h.getMaxColumns(), 40 - h.getMaxColumns());
  if (h.getMaxRows() < 1000) h.insertRowsAfter(h.getMaxRows(), 1000 - h.getMaxRows());
  // Nunca se limpia esta hoja: volver a armar conserva valores y puestos ya cargados.
  _titulo_(h, "SUPUESTOS · modelo nuevo", 7);
  h.getRange(2, 1, 1, 7).merge().setValue("Amarillo = completar. Vacío = falta. 0 = ausencia confirmada. Período 1: mañana a fin de mes; después, 11 meses completos. Las fechas avanzan con el día de hoy.").setWrap(true);
  h.setRowHeight(2, 48);
  h.getRange(4, 1, 1, 5).setValues([["Qué es", "Unidad", "Valor", "Quién lo provee", "Nota"]]);
  var refs = {}, defs = _mnDefiniciones_();
  defs.forEach(function (d, i) {
    var fila = 5 + i;
    refs[d[0]] = "Supuestos!$C$" + fila;
    h.getRange(fila, 1, 1, 2).setValues([[d[1], d[2]]]);
    h.getRange(fila, 4, 1, 2).setValues([[d[3], d[4]]]);
    var celda = h.getRange(fila, 3).setBackground("#fff8e1").setFontColor("#174ea6");
    var opciones = { nomina: ["Sí"], deuda: ["Sí"], saldo: ["Sí"], base: ["Facturada", "Cobrada"], tipoFlete: ["$/kg", "% venta"] };
    var regla = SpreadsheetApp.newDataValidation().setAllowInvalid(false);
    if (opciones[d[0]]) regla.requireValueInList(opciones[d[0]], true);
    else if (d[2] === "%") regla.requireNumberBetween(0, d[0] === "imprevistos" ? 0.999999 : 1);
    else regla.requireNumberGreaterThanOrEqualTo(0);
    celda.setDataValidation(regla.build()).setNumberFormat(d[2] === "%" ? "0.0%" : "#,##0.00;[Red]-#,##0.00;0.00");
  });
  h.getRange(67, 1).setValue("Inflación mensual · única fuente");
  h.getRange(67, 2).setValue("%");
  // No se crea un supuesto duplicado ni se escribe el valor histórico por defecto.
  h.getRange(67, 3).setFormula('=IFERROR(IF(ISNUMBER(\'Cash Mensual\'!B4),\'Cash Mensual\'!B4,"—"),"—")').setNumberFormat("0.0%");
  h.getRange(67, 5).setValue("Se edita sólo en Cash Mensual!B4. Si falta esa hoja o el dato, el modelo queda incompleto.");
  refs.inflacion = "Supuestos!$C$67";
  h.getRange(69, 1, 1, 7).merge().setValue("PUESTOS · una fila por puesto o incorporación, sólo roles. Completar A, C, F y G; honorarios también van acá. Hay lugar hasta la fila 1000. No insertar filas dentro del bloque superior.").setWrap(true);
  h.setRowHeight(69, 45);
  h.getRange(70, 1, 1, 7).setValues([["Puesto / rol", "Unidad", "Bruto / honorario mensual", "Quién lo provee", "Nota", "Sueldo / Honorario", "Mes de entrada (1 a 12)"]]);
  h.getRange(71, 1, 930, 7).setBackground("#fff8e1");
  h.getRange(71, 3, 930, 1).setDataValidation(SpreadsheetApp.newDataValidation().requireNumberGreaterThanOrEqualTo(0).setAllowInvalid(false).build()).setNumberFormat("#,##0.00;[Red]-#,##0.00;0.00");
  h.getRange(71, 6, 930, 1).setDataValidation(SpreadsheetApp.newDataValidation().requireValueInList(["Sueldo", "Honorario"], true).setAllowInvalid(false).build());
  h.getRange(71, 7, 930, 1).setDataValidation(SpreadsheetApp.newDataValidation().requireNumberBetween(1, 12).setAllowInvalid(false).build());
  h.getRange(4, 1, 64, 5).setWrap(true);
  h.getRange(70, 1, 1, 7).setWrap(true).setFontWeight("bold").setBackground("#e8f0fe");
  h.setRowHeight(70, 48);
  h.setColumnWidth(1, 340); h.setColumnWidth(2, 140); h.setColumnWidth(3, 150);
  h.setColumnWidth(4, 140); h.setColumnWidth(5, 510); h.setColumnWidth(6, 130); h.setColumnWidth(7, 130);
  h.setFrozenRows(4); h.setFrozenColumns(1);
  return refs;
}

// Sólo se leen encabezados; ninguna copia de datos privados queda en el código.
// Si una fuente falta, se puede armar igual: la pantalla dice cuál falta.
function _mnFuentes_(ss) {
  var out = { errores: [] };
  function leer(nombre, bloque, campos) {
    var h = ss.getSheetByName(nombre);
    if (!h) { out.errores.push("Falta solapa " + nombre); return null; }
    var fila = 1;
    if (bloque) {
      var bancos = h.getRange(1, 1, Math.max(1, h.getLastRow()), 1).getValues();
      var encs = [];
      bancos.forEach(function (r, i) { if (_n_(r[0]) === "banco") encs.push(i + 1); });
      if (encs.length !== 2) { out.errores.push("Revisar encabezados de " + nombre); return null; }
      fila = encs[1];
    }
    var enc = h.getRange(fila, 1, 1, h.getLastColumn()).getValues()[0], r = {}, falta = false;
    Object.keys(campos).forEach(function (k) {
      var c = _colPorNombre_(enc, campos[k]);
      if (c < 0) { out.errores.push(nombre + ": falta " + campos[k]); falta = true; }
      else { var l = _colLetra_(c + 1); r[k] = "'" + nombre + "'!$" + l + "$" + (fila + 1) + ":$" + l; }
    });
    return falta ? null : r;
  }
  out.banco = leer("Deuda Bancaria", true, { id: "Banco", fecha: "Fecha Vencimiento", capital: "Importe Capital", interes: "Importe Interes", total: "Importe Total Cuota", estado: "Estado", auto: "Debito Automatico" });
  out.impuesto = leer("Deuda Impositiva", false, { id: "Impuesto", fecha: "Fecha Vencimiento", total: "Importe", estado: "Estado", auto: "Debito Automatico" });
  out.saldo = leer("Saldos Bancarios", false, { fecha: "Fecha", banco: "Banco", empresa: "Empresa", cuenta: "Cuenta / Nro", importe: "Saldo" });
  return out;
}

function _mnTexto_(texto) { return '"' + texto.replace(/"/g, '""') + '"'; }
function _mnNumero_(ref, min, max, entero) {
  return 'IFERROR(AND(ISNUMBER(' + ref + '),' + ref + '>=' + min +
    (max === undefined ? '' : ',' + ref + '<=' + max) + (entero ? ',MOD(' + ref + ',1)=0' : '') + '),FALSE)';
}
function _mnFalta_(condicion, texto) { return 'IF(' + condicion + ',"",' + _mnTexto_(texto) + ')'; }
function _mnUnir_(faltas) { return faltas.length ? 'TEXTJOIN(" | ",TRUE,' + faltas.join(',') + ')' : '""'; }

// Cobra / paga lo de cada mes según cuántos días de ese mes caen en el destino.
// Así 15, 30 o 75 días cruzan los meses de verdad, incluso febrero. Las ventas y
// compras se reparten parejo: es una convención visible, no una fecha inventada.
function _mnDesplazar_(fila, destino, dias) {
  var partes = [], faltas = [], d = _colLetra_(destino + 2) + '$4', f = _colLetra_(destino + 2) + '$5';
  for (var origen = 0; origen <= destino; origen++) {
    var l = _colLetra_(origen + 2), inicio = l + '$4', fin = l + '$5';
    var peso = 'MAX(0,MIN(' + f + ',' + fin + '+' + dias + ')-MAX(' + d + ',' + inicio + '+' + dias + '))/(' + fin + '-' + inicio + ')';
    partes.push('IF(' + peso + '>0,' + l + fila + '*' + peso + ',0)');
    faltas.push(_mnFalta_('OR(' + peso + '=0,ISNUMBER(' + l + fila + '))', 'Falta base del período ' + (origen + 1)));
  }
  return { valor: partes.join('+'), faltas: faltas };
}

function _mnDeuda_(r, inicio, fin, automatico, campo, bancaria) {
  if (!r) return { valor: '0', faltas: [_mnTexto_('Falta fuente de deuda; revisar aviso de fuentes')] };
  var auto = 'UPPER(TRIM(' + r.auto + '))', estado = 'UPPER(TRIM(' + r.estado + '))';
  var pendiente = bancaria ? '(' + estado + '="PENDIENTE")' : '(' + estado + '<>"PAGADO")';
  var tiene = '(' + r.id + '<>"")';
  var fechas = 'ISNUMBER(' + r.fecha + ')*(' + r.fecha + '>0)';
  var importes = bancaria ? 'ISNUMBER(' + r.capital + ')*ISNUMBER(' + r.interes + ')*ISNUMBER(' + r.total + ')' : 'ISNUMBER(' + r.total + ')';
  importes += '*(' + r.total + '>=0)';
  if (bancaria) importes += '*(' + r.capital + '>=0)*(' + r.interes + '>=0)';
  var clasificado = '((' + auto + '="SI")+(' + auto + '="SÍ")+(' + auto + '="NO"))';
  var valida = fechas + '*' + importes + '*' + clasificado;
  if (bancaria) valida += '*IFERROR(ABS(' + r.total + '-' + r.capital + '-' + r.interes + ')<0.01,FALSE)';
  var faltas = [
    _mnFalta_('SUMPRODUCT((' + r.id + '="")*(((' + r.fecha + '<>"")+(' + r.total + '<>""))>0))=0', 'Deuda sin identificación'),
    _mnFalta_('SUMPRODUCT(' + tiene + '*' + pendiente + '*(1-IFERROR(' + valida + ',0)))=0', 'Revisar fechas, importes o débito de ' + (bancaria ? 'Deuda Bancaria' : 'Deuda Impositiva')),
    _mnFalta_('SUMPRODUCT(' + tiene + '*(' + estado + '<>"PAGADO")*(' + estado + '<>"PENDIENTE"))=0', 'Revisar estados de ' + (bancaria ? 'Deuda Bancaria' : 'Deuda Impositiva'))
  ];
  var filtroAuto = automatico ? '((' + auto + '="SI")+(' + auto + '="SÍ"))' : '(' + auto + '="NO")';
  return { valor: 'SUMPRODUCT(IFERROR(' + tiene + '*' + pendiente + '*(' + r.fecha + '>=' + inicio + ')*(' + r.fecha + '<' + fin + ')*' + filtroAuto + '*' + r[campo] + ',0))', faltas: faltas };
}

function _mnPantalla_(ss, s, fuentes) {
  var h = _hojaLimpia_(ss, 'Modelo Nuevo', 13);
  if (h.getMaxRows() < 130) h.insertRowsAfter(h.getMaxRows(), 130 - h.getMaxRows());
  h.getRange(1, 1, h.getMaxRows(), 13).breakApart();
  _titulo_(h, 'MODELO NUEVO · operación primero, deuda debajo de la línea', 13);
  h.getRange(2, 1).setValue('Faltan datos').setFontWeight('bold');
  h.getRange(3, 1, 1, 13).merge().setValue('Proyección desde mañana. Cargá Supuestos. — = falta o dato inválido; 0 = ausencia confirmada. Los egresos se muestran positivos y se restan. Ver detalle de faltantes desde la fila 66.').setWrap(true);
  h.setRowHeight(3, 40);
  var nombres = {
    4: 'Desde (incluido)', 5: 'Hasta (sin incluir)', 6: 'Ventas · kilos', 7: 'Precio por kilo', 8: 'Ventas facturadas ($)',
    9: '1 · Ingresos', 10: 'Cobranza del modelo nuevo', 11: 'Cobros de ventas anteriores', 12: 'Total ingresos',
    13: '2 · Egresos de la operación', 14: 'Canchada · consumo / compra del período ($)', 15: 'Canchada · pago según plazo y anticipo',
    16: 'Packaging', 17: 'Sueldos brutos', 18: 'Cargas sociales', 19: 'Honorarios', 20: 'Comisiones', 21: 'Fletes',
    22: 'Seguros', 23: 'Energía', 24: 'Gas', 25: 'Impuestos corrientes', 26: 'Pagos operativos anteriores', 27: 'Imprevistos',
    28: 'Total egresos de la operación', 29: 'Resultado de la operación (antes de la deuda)', 30: '3 · Indemnizaciones',
    31: '4 · Deuda que sale sí o sí', 32: 'Capital bancario automático', 33: 'Intereses bancarios automáticos', 34: 'Deuda impositiva automática',
    35: 'Total deuda automática', 36: 'SALDO DEL PERÍODO pagando solo lo automático', 37: '5 · Deuda que se paga por decisión',
    38: 'Capital bancario por decisión', 39: 'Intereses bancarios por decisión', 40: 'Deuda impositiva por decisión', 41: 'Total deuda por decisión',
    42: 'SALDO DEL PERÍODO pagando toda la deuda', 43: 'Saldo inicial · caja real / cierre anterior',
    44: 'Saldo acumulado pagando toda la deuda', 45: 'Saldo acumulado pagando sólo lo automático',
    46: 'Capital de trabajo · necesidad según plazos', 47: 'Plata en la calle · días de cobro', 48: 'Stock de canchada · opcional',
    49: 'Financiación de proveedores · días de pago', 50: 'Capital de trabajo neto', 51: 'Alcance del capital de trabajo',
    52: 'Fuentes / actualización', 53: 'Base de caja: fecha más antigua usada',
    54: 'Indemnizaciones pendientes después del horizonte', 55: 'Ventas del modelo pendientes al cierre',
    56: 'Canchada del modelo pendiente de pagar al cierre'
  };
  Object.keys(nombres).forEach(function (r) { h.getRange(Number(r), 1).setValue(nombres[r]); });
  var filasEstado = [];
  function estado(fila) { return fila + 60; }
  // Cada cálculo tiene al pie su motivo de falta. Los totales exigen todos sus
  // componentes numéricos: SUM solo nunca decide si un bloque está completo.
  function escribir(fila, mes, valor, faltas) {
    var col = mes + 2, l = _colLetra_(col), motivo = l + estado(fila);
    if (mes === 0) {
      filasEstado.push(fila);
      h.getRange(estado(fila), 1).setValue('Falta / revisar · ' + nombres[fila]);
    }
    h.getRange(estado(fila), col).setFormula('=IFERROR(' + _mnUnir_(faltas) + ',"Revisar fuente o supuesto de este renglón")');
    h.getRange(fila, col).setFormula('=IFERROR(IF(' + motivo + '="",' + valor + ',"—"),"—")');
  }
  for (var m = 0; m < 12; m++) {
    var l = _colLetra_(m + 2), anterior = _colLetra_(m + 1), d = l + '$4', f = l + '$5';
    h.getRange(4, m + 2).setFormula(m === 0 ? '=TODAY()+1' : '=' + anterior + '$5');
    h.getRange(5, m + 2).setFormula('=EOMONTH(' + d + ',0)+1');
    var factor = '(1+' + s.inflacion + ')^' + m;
    var parteMes = '(' + f + '-' + d + ')/DAY(EOMONTH(' + d + ',0))';
    var inf = _mnFalta_(_mnNumero_(s.inflacion, -0.999999), 'Inflación mensual (Cash Mensual!B4)');
    function dato(clave, texto, max, entero) { return _mnFalta_(_mnNumero_(s[clave], 0, max, entero), texto); }
    function dep(fila) { return _mnFalta_('ISNUMBER(' + l + fila + ')', nombres[fila]); }
    function sumar(fila, componentes) {
      escribir(fila, m, componentes.map(function (r) { return l + r; }).join('+'), componentes.map(dep));
    }
    escribir(6, m, s['kg' + (m + 1)], [dato('kg' + (m + 1), 'Kilos período ' + (m + 1))]);
    escribir(7, m, s.precio + '*' + factor, [dato('precio', 'Precio de venta'), inf]);
    escribir(8, m, l + '6*' + l + '7', [dep(6), dep(7)]);
    var cobro = _mnDesplazar_(8, m, s.cobro);
    escribir(10, m, cobro.valor, [dato('cobro', 'Días de cobro', undefined, true)].concat(cobro.faltas));
    escribir(11, m, s['cobAnterior' + (m + 1)], [dato('cobAnterior' + (m + 1), 'Cobros anteriores período ' + (m + 1))]);
    sumar(12, [10, 11]);
    escribir(14, m, l + '6*' + s.rendimiento + '*' + s.canchada + '*' + factor,
      [dep(6), dato('rendimiento', 'Rendimiento canchada'), dato('canchada', 'Precio canchada'), inf]);
    var pago = _mnDesplazar_(14, m, s.pago);
    escribir(15, m, s.anticipo + '*' + l + '14+(1-' + s.anticipo + ')*(' + pago.valor + ')',
      [dep(14), dato('pago', 'Días de pago canchada', undefined, true), dato('anticipo', 'Anticipo canchada', 1)].concat(pago.faltas));
    escribir(16, m, l + '6*' + s.pack + '*' + factor, [dep(6), dato('pack', 'Packaging por kilo'), inf]);
    // Una fila parcialmente cargada nunca se pierde dentro de un SUMIFS.
    var roles = 'Supuestos!$A$71:$A$1000', brutos = 'Supuestos!$C$71:$C$1000', tipos = 'Supuestos!$F$71:$F$1000', entradas = 'Supuestos!$G$71:$G$1000';
    var usada = '((' + roles + '<>"")+(' + brutos + '<>"")+(' + tipos + '<>"")+(' + entradas + '<>""))>0';
    var valida = '(' + roles + '<>"")*ISNUMBER(' + brutos + ')*(' + brutos + '>=0)*((' + tipos + '="Sueldo")+(' + tipos + '="Honorario"))*ISNUMBER(' + entradas + ')*(' + entradas + '>=1)*(' + entradas + '<=12)*(MOD(' + entradas + ',1)=0)';
    var personalFalta = [_mnFalta_(s.nomina + '="Sí"', 'Confirmar nómina completa'), _mnFalta_('SUMPRODUCT((' + usada + ')*(1-IFERROR(' + valida + ',0)))=0', 'Completar rol, importe, tipo y mes entero de cada puesto'), inf];
    escribir(17, m, 'SUMIFS(' + brutos + ',' + tipos + ',"Sueldo",' + entradas + ',"<=' + (m + 1) + '")*' + factor + '*' + parteMes, personalFalta);
    escribir(18, m, l + '17*' + s.cargas, [dep(17), dato('cargas', 'Cargas sociales', 1)]);
    escribir(19, m, 'SUMIFS(' + brutos + ',' + tipos + ',"Honorario",' + entradas + ',"<=' + (m + 1) + '")*' + factor + '*' + parteMes, personalFalta);
    escribir(20, m, s.comision + '*IF(' + s.base + '="Facturada",' + l + '8,' + l + '12)', [dato('comision', 'Comisión', 1),
      _mnFalta_('OR(' + s.base + '="Facturada",' + s.base + '="Cobrada")', 'Base de comisión'),
      _mnFalta_('ISNUMBER(IF(' + s.base + '="Facturada",' + l + '8,' + l + '12))', 'Importe de la base de comisión')]);
    escribir(21, m, 'IF(' + s.tipoFlete + '="$/kg",' + l + '6*' + s.flete + '*' + factor + ',' + l + '8*' + s.flete + ')',
      [dato('flete', 'Tarifa de flete'), inf, _mnFalta_('OR(' + s.tipoFlete + '="$/kg",' + s.tipoFlete + '="% venta")', 'Tipo de flete'),
        _mnFalta_('OR(' + s.tipoFlete + '<>"% venta",' + s.flete + '<=1)', 'Flete porcentual mayor a 100%'),
        _mnFalta_('ISNUMBER(IF(' + s.tipoFlete + '="$/kg",' + l + '6,' + l + '8))', 'Base del flete')]);
    ['seguros', 'energia', 'gas', 'impuestos'].forEach(function (k, i) {
      escribir(22 + i, m, s[k] + '*' + factor + '*' + parteMes, [dato(k, nombres[22 + i]), inf]);
    });
    escribir(26, m, s['pagAnterior' + (m + 1)], [dato('pagAnterior' + (m + 1), 'Pagos operativos anteriores período ' + (m + 1))]);
    var gastos = [15,16,17,18,19,20,21,22,23,24,25,26];
    escribir(27, m, 'SUM(' + l + '15:' + l + '26)*' + s.imprevistos + '/(1-' + s.imprevistos + ')',
      gastos.map(dep).concat([dato('imprevistos', 'Imprevistos (menor a 100%)', 0.999999)]));
    sumar(28, gastos.concat([27]));
    escribir(29, m, l + '12-' + l + '28', [dep(12), dep(28)]);
    var indemFalta = [dato('indem', 'Importe de indemnizaciones'),
      _mnFalta_('OR(' + s.indem + '=0,AND(' + _mnNumero_(s.mesIndem, 1, 12, true) + ',' + _mnNumero_(s.cuotas, 1, undefined, true) + '))', 'Mes y cuotas de indemnizaciones')];
    escribir(30, m, 'IF(' + s.indem + '=0,0,IF(AND(' + (m + 1) + '>=' + s.mesIndem + ',' + (m + 1) + '<' + s.mesIndem + '+' + s.cuotas + '),' + s.indem + '/' + s.cuotas + ',0))', indemFalta);
    [true, false].forEach(function (automatico) {
      var primera = automatico ? 32 : 38;
      ['capital', 'interes', 'total'].forEach(function (campo, i) {
        var deuda = _mnDeuda_(i === 2 ? fuentes.impuesto : fuentes.banco, d, f, automatico, campo, i !== 2);
        escribir(primera + i, m, deuda.valor, deuda.faltas.concat([_mnFalta_(s.deuda + '="Sí"', 'Confirmar cronogramas completos')]));
      });
      sumar(primera + 3, [primera, primera + 1, primera + 2]);
    });
    escribir(36, m, l + '29-' + l + '30-' + l + '35', [dep(29), dep(30), dep(35)]);
    escribir(42, m, l + '36-' + l + '41', [dep(36), dep(41)]);
    escribir(43, m, m === 0 ? '$B$58' : anterior + '44', [_mnFalta_('ISNUMBER(' + (m === 0 ? '$B$58' : anterior + '44') + ')', m === 0 ? 'Caja real de hoy (fuentes / confirmación)' : 'Saldo acumulado del período anterior')]);
    escribir(44, m, l + '43+' + l + '42', [dep(43), dep(42)]);
    var baseAuto = m === 0 ? '$B$58' : anterior + '45';
    escribir(45, m, baseAuto + '+' + l + '36', [dep(36), _mnFalta_('ISNUMBER(' + baseAuto + ')', 'Caja inicial / saldo automático anterior')]);
    escribir(47, m, l + '8/(' + f + '-' + d + ')*' + s.cobro, [dep(8), dato('cobro', 'Días de cobro', undefined, true)]);
    // Stock es opcional, pero nunca se disfraza de un cero informado.
    escribir(48, m, 'IF(' + s.stock + '="","—",' + l + '14/(' + f + '-' + d + ')*' + s.stock + ')',
      [dep(14), _mnFalta_('OR(' + s.stock + '="",' + _mnNumero_(s.stock, 0, undefined, true) + ')', 'Días de stock inválidos')]);
    escribir(49, m, l + '14/(' + f + '-' + d + ')*(1-' + s.anticipo + ')*' + s.pago,
      [dep(14), dato('anticipo', 'Anticipo canchada', 1), dato('pago', 'Días de pago canchada', undefined, true)]);
    escribir(50, m, l + '47+IF(' + s.stock + '="",0,' + l + '48)-' + l + '49', [dep(47), dep(49), _mnFalta_('OR(' + s.stock + '="",ISNUMBER(' + l + '48))', 'Stock')]);
    h.getRange(51, m + 2).setFormula('=IF(' + s.stock + '="","Sin stock: falta informar días","Incluye stock de canchada")');
    h.getRange(52, m + 2).setValue(fuentes.errores.length ? fuentes.errores.join(' · ') : 'Listas vinculadas. Confirmar cobertura y saldos en Supuestos.');
    h.getRange(53, m + 2).setFormula('=$B$59').setNumberFormat('dd/mm/yyyy');
    escribir(54, m, 'IF(' + s.indem + '=0,0,' + s.indem + '*MAX(0,' + s.mesIndem + '+' + s.cuotas + '-13)/' + s.cuotas + ')', indemFalta);
    var ventasHasta = [], cobrosHasta = [], comprasHasta = [], pagosHasta = [], faltasVenta = [], faltasCompra = [];
    for (var previo = 0; previo <= m; previo++) {
      var p = _colLetra_(previo + 2);
      ventasHasta.push(p + '8'); cobrosHasta.push(p + '10'); comprasHasta.push(p + '14'); pagosHasta.push(p + '15');
      faltasVenta.push(_mnFalta_('AND(ISNUMBER(' + p + '8),ISNUMBER(' + p + '10))', 'Ventas / cobros período ' + (previo + 1)));
      faltasCompra.push(_mnFalta_('AND(ISNUMBER(' + p + '14),ISNUMBER(' + p + '15))', 'Canchada / pagos período ' + (previo + 1)));
    }
    escribir(55, m, 'SUM(' + ventasHasta.join(',') + ')-SUM(' + cobrosHasta.join(',') + ')', faltasVenta);
    escribir(56, m, 'SUM(' + comprasHasta.join(',') + ')-SUM(' + pagosHasta.join(',') + ')', faltasCompra);
    // Arriba se ven los supuestos concretos, sin repetir el mismo faltante.
    // El detalle por renglón queda al pie por si la lista de arriba no entra a simple vista.
    var listaFaltas = filasEstado.map(function (r) {
      return 'IF(AND(' + l + estado(r) + '="",' + l + r + '="—"' + (r === 48 ? ',' + s.stock + '<>""' : '') + '),"Revisar cálculo fila ' + r + '",' + l + estado(r) + ')';
    });
    listaFaltas.push('$B$60');
    h.getRange(2, m + 2).setFormula('=LET(faltantes,' + _mnUnir_(listaFaltas) + ',IF(faltantes="","Completo",TEXTJOIN(" | ",TRUE,UNIQUE(TRANSPOSE(SPLIT(faltantes," | ",FALSE,TRUE))))))');
  }
  _mnCaja_(h, s, fuentes.saldo);
  h.getRange(57, 1, 1, 13).merge().setValue('Capital de trabajo = venta diaria × días de cobro + costo diario de canchada × días de stock − costo diario de canchada × parte no anticipada × días de pago. Es una necesidad orientativa a ese ritmo: no se resta otra vez de la caja. Stock no programa compras.').setWrap(true);
  h.setRowHeight(57, 48);
  h.getRange(61, 1, 1, 13).merge().setValue('La caja toma la última foto por banco + empresa + cuenta hasta hoy. El saldo requiere confirmación de cobertura. Deuda vencida antes de mañana queda fuera de estos flujos: acordar un cronograma real para incorporarla. El modelo no lee propuestas de Plan.').setWrap(true);
  h.setRowHeight(61, 48);
  h.getRange(63, 1, 1, 13).merge().setValue('PRUEBA: correr armarModeloNuevo. Vacíos → — y faltantes. Cargar un dato → sólo se habilitan sus dependientes completos. Vaciarlo → vuelven a —. Repetir armado → conserva Supuestos y no toca Cash / Semanal / Mensual / Plan. Ver manual §8 para ejemplo y prueba completa.').setWrap(true);
  h.setRowHeight(63, 48);
  h.getRange(65, 1).setValue('DETALLE · qué falta para cada renglón').setFontWeight('bold');
  h.getRange(4, 2, 2, 12).setNumberFormat('dd/mm/yyyy');
  h.getRange(6, 2, 45, 12).setNumberFormat('#,##0.00;[Red]-#,##0.00;0.00');
  h.getRange(54, 2, 3, 12).setNumberFormat('#,##0.00;[Red]-#,##0.00;0.00');
  h.getRange(2, 2, 1, 12).setWrap(true).setVerticalAlignment('top').setBackground('#fff8e1');
  h.setRowHeight(2, 180);
  h.getRange(51, 2, 2, 12).setWrap(true); h.setRowHeights(51, 2, 65);
  h.getRange(66, 2, 51, 12).setWrap(true).setVerticalAlignment('top'); h.setRowHeights(66, 51, 76);
  [9,13,31,37,46].forEach(function (r) { _seccion_(h, r, nombres[r], '#e8f0fe', '#174ea6', 13); });
  [12,28,29,30,35,36,41,42,44,45,50].forEach(function (r) { _lineaTotal_(h, r, 13); h.getRange(r, 1, 1, 13).setFontWeight('bold'); });
  h.getRange(14, 1).setNote('Base de compra, informativa. El total de egresos incluye el pago de la fila 15, nunca las dos filas.');
  h.setColumnWidth(1, 425); h.setColumnWidths(2, 12, 180); h.setFrozenRows(5); h.setFrozenColumns(1);
}

function _mnCaja_(h, s, r) {
  h.getRange(58, 1).setValue('Caja real de hoy · sin acuerdos de descubierto');
  h.getRange(59, 1).setValue('Fecha más antigua de las fotos de caja usadas');
  h.getRange(60, 1).setValue('Falta / revisar · caja inicial');
  if (!r) {
    h.getRange(58, 2, 2, 1).setValues([['—'], ['—']]);
    h.getRange(60, 2).setValue('Falta Saldos Bancarios o sus encabezados');
    return;
  }
  // La clave incluye la cuenta y la empresa: dos cuentas del mismo banco no se pisan.
  // MAP vuelve a leer las claves por fórmula; una cuenta nueva entra sin rearmar.
  var claves = r.banco + '&"|"&' + r.empresa + '&"|"&' + r.cuenta;
  var fechaValida = 'ISNUMBER(' + r.fecha + ')*(' + r.fecha + '>0)*(' + r.fecha + '<=TODAY())';
  var lista = 'UNIQUE(FILTER(' + claves + ',' + r.banco + '<>""))';
  var fecha = 'MAX(FILTER(' + r.fecha + ',(' + claves + ')=clave,' + fechaValida + '))';
  var cuerpo = 'LET(fecha,' + fecha + ',coincide,((' + claves + ')=clave)*(' + r.fecha + '=fecha),IF(AND(SUMPRODUCT(coincide)=1,SUMPRODUCT(coincide*ISNUMBER(' + r.importe + '))=1),SUM(FILTER(' + r.importe + ',coincide)),NA()))';
  var calculo = 'SUM(MAP(' + lista + ',LAMBDA(clave,' + cuerpo + ')))';
  h.getRange(60, 2).setFormula('=IFERROR(IF(' + s.saldo + '<>"Sí","Confirmar saldos al día en Supuestos",IF(ISNUMBER(' + calculo + '),"","Revisar caja")),"Revisar saldos: faltan fechas/importes o hay fotos duplicadas por cuenta")');
  h.getRange(58, 2).setFormula('=IFERROR(IF(B60="",' + calculo + ',"—"),"—")').setNumberFormat('#,##0.00;[Red]-#,##0.00;0.00');
  h.getRange(59, 2).setFormula('=IFERROR(MIN(MAP(' + lista + ',LAMBDA(clave,' + fecha + '))),"—")').setNumberFormat('dd/mm/yyyy');
  h.getRange(60, 2, 1, 12).merge().setWrap(true); h.setRowHeight(60, 42);
}


// ==================================================================================
// arreglarValidaciones — las listas desplegables de Movimientos quedaron viejas y hoy
// marcan en rojo casi todo lo que carga el importador. Medido el 23/09/2026:
//
//   Origen (J)        3.153 de 3.252 filas rechazadas  ("Extracto MACRO", "Tango AA · …")
//   Medio de Pago (H) 1.617 rechazadas                 ("Débito automático" vs "Debito Automatico")
//   Categoria (E)       721 rechazadas                 (Gastos Bancarios, Transferencia Interna,
//                                                       Cobranza AA, Descuento de Cheques)
//
// Una validación que rechaza el 97 % de las filas no protege nada: sólo ensucia la pantalla
// y enseña a ignorar el triangulito rojo. Entonces:
//   · Origen: se saca la lista. El valor lo escribe el lector y lleva el banco o el archivo
//     adentro ("Extracto MACRO"), así que no hay lista posible. Las fórmulas lo leen por
//     prefijo ("Extracto*", "Tango AA*").
//   · Categoria y Medio de Pago: se completan con los valores que realmente se usan, para que
//     el desplegable siga sirviendo a quien carga una fila a mano.
// Se corre desde el menú finauto cuando hace falta; no lo llama el armado del cash.
// ==================================================================================
function arreglarValidaciones() {
  var h = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Movimientos");
  if (!h) throw new Error("No encontré la solapa Movimientos");
  var n = Math.max(h.getMaxRows() - 1, 1);
  h.getRange(2, 10, n, 1).clearDataValidations();               // J · Origen: sin lista
  _lista_validacion_(h, 5, n, ["Cobranza Facturas", "Cobranza Canchada", "Cobranza AA",
    "Descuento de Cheques", "Cheques", "Prestamo", "Proveedores MP y Logist.", "Proveedores AA",
    "Hoja Verde", "Insumos", "Cosecha", "Sueldos y Jornales", "Impuestos", "Honorarios y Dividendos",
    "Gastos Bancarios", "Estampillas", "Transferencia Interna", "Otros"]);
  _lista_validacion_(h, 8, n, ["Efectivo", "Transferencia", "Cheque Propio", "Cheque de Terceros",
    "Débito automático", "Debito Automatico"]);
  SpreadsheetApp.getActiveSpreadsheet().toast(
    "Validaciones al día: Origen sin lista (lo escribe el lector), Categoria y Medio de Pago completos.", "finauto", 8);
}

function _lista_validacion_(h, col, n, valores) {
  var regla = SpreadsheetApp.newDataValidation().requireValueInList(valores, true)
    .setAllowInvalid(true).build();          // avisa, pero no bloquea una carga a mano
  h.getRange(2, col, n, 1).setDataValidation(regla);
}
