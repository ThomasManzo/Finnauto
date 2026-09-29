/**
 * resumen_semanal.gs — la foto de los lunes de los principales clientes y proveedores, y el mail que
 * la compara con la semana anterior. Va en el mismo proyecto de Apps Script que importar_cashflow.gs
 * y aviso_diario.gs (usa DESTINATARIOS del aviso y _registrar_ del importador).
 *
 * PARA QUÉ
 *   La solapa "Principales 20" se recalcula todos los días y pisa lo anterior: no deja ver si lo
 *   vencido bajó. Cada lunes este script guarda una foto de los 80 (20 clientes y 20 proveedores de
 *   A y de AA) en la lista "Principales 20 · historial" y manda un mail que compara con la foto
 *   anterior: totales, quién mejoró, quién empeoró, quién entró o salió y quién sigue sin pagos.
 *
 * DE DÓNDE SALEN LOS NÚMEROS
 *   De las listas (Cuentas a Cobrar, Cuentas a Pagar, Ultimos Pagos), buscando las columnas por su
 *   encabezado. NO lee la solapa Principales 20: su diseño puede cambiar (ya le insertaron una fila).
 *   Las reglas son las mismas que las fórmulas de esa solapa, así los números coinciden:
 *     saldo      = suma de Saldo Pendiente por razón social y empresa (neto, con negativos);
 *     los 20     = los de mayor saldo;
 *     vencido    = lo que tiene Fecha Vencimiento anterior al día de la foto; a vencer = saldo − vencido;
 *     vto. impago más viejo = el vencimiento más antiguo con saldo > 0 ya vencido;
 *     último pago = Fecha Ultimo Pago de la lista Ultimos Pagos (vacío si no hay).
 *
 * MENÚ (en onOpen de importar_cashflow.gs)
 *   Ver el resumen semanal (sin mandar) · Guardar foto semanal ahora · Instalar resumen semanal.
 *   La primera vez, "Guardar foto semanal ahora" deja la foto inicial para que el lunes compare.
 *
 * PARA PROBAR SIN GOOGLE (lector/pruebas/probar_resumen_semanal.cjs)
 *   _calcularFotoSemanal_(listas, dia) y _armarResumenSemanal_(dia, actual, anterior, notaPdf) no
 *   tocan Google: reciben tablas (arrays con la fila 1 de encabezado) y devuelven datos o texto.
 */

var SEMANAL_ZONA = "America/Argentina/Buenos_Aires";
var SEMANAL_HISTORIAL = "Principales 20 · historial";
var SEMANAL_ENCABEZADO = ["Fecha foto", "Empresa", "Tipo", "Puesto", "Razon Social", "Saldo", "Vencido",
  "A vencer", "Vto Impago Mas Viejo", "Ultimo Pago"];
var SEMANAL_CUANTOS = 20;
// Los cuatro bloques, en el orden en que salen en el mail.
var SEMANAL_BLOQUES = [
  {empresa: "A", tipo: "Cliente", hoja: "Cuentas a Cobrar", columnaNombre: "Cliente", titulo: "CLIENTES A (lo que nos deben)"},
  {empresa: "AA", tipo: "Cliente", hoja: "Cuentas a Cobrar", columnaNombre: "Cliente", titulo: "CLIENTES AA (lo que nos deben)"},
  {empresa: "A", tipo: "Proveedor", hoja: "Cuentas a Pagar", columnaNombre: "Proveedor", titulo: "PROVEEDORES A (lo que debemos)"},
  {empresa: "AA", tipo: "Proveedor", hoja: "Cuentas a Pagar", columnaNombre: "Proveedor", titulo: "PROVEEDORES AA (lo que debemos)"}
];


// ---------------------------------------------------------------- lo que corre el disparador y el menú

// Lunes: guarda la foto de hoy, la compara con la anterior y manda el mail con la solapa en PDF.
function resumenSemanal() {
  _mandarResumenSemanal_(SpreadsheetApp.getActiveSpreadsheet(), new Date());
}

// Muestra el mail de hoy sin mandarlo y sin guardar foto (compara contra la última foto guardada).
function resumenSemanalPrueba() {
  var r = _verResumenSemanal_(SpreadsheetApp.getActiveSpreadsheet(), new Date());
  Logger.log(r.asunto + "\n\n" + r.cuerpo);
  try { SpreadsheetApp.getUi().alert(r.asunto + "\n\n" + r.cuerpo); } catch (e) {}
}

// Guarda (o rehace) la foto de hoy. Sirve para la foto inicial el día que se instala.
function guardarFotoSemanal() {
  var n = _guardarFotoDeHoySemanal_(SpreadsheetApp.getActiveSpreadsheet(), new Date());
  try { SpreadsheetApp.getUi().alert("Foto guardada en '" + SEMANAL_HISTORIAL + "': " + n + " filas."); } catch (e) {}
}

// Lo que hacen las tres de arriba, con la Sheet y el "ahora" como parámetros (así se prueban sin Google).
function _mandarResumenSemanal_(ss, ahora) {
  var dia = _diaSemanal_(ahora);
  try {
    var actual = _calcularFotoSemanal_(_leerListasSemanal_(ss), dia);
    _guardarFotoSemanal_(ss, dia, actual);
    var anterior = _fotoAnteriorSemanal_(ss, dia);
    // El PDF es un extra: si falla, el mail sale igual y lo dice.
    var pdf = null, notaPdf = "";
    try { pdf = _pdfPrincipalesSemanal_(ss, dia); }
    catch (e) { notaPdf = "No se pudo adjuntar el PDF de la solapa: " + _textoSemanal_(e && e.message || e, 120); }
    var r = _armarResumenSemanal_(dia, actual, anterior, notaPdf);
    MailApp.sendEmail(DESTINATARIOS, r.asunto, r.cuerpo, pdf ? {attachments: [pdf]} : {});
    _registrar_("resumen_semanal", "", "ok", "mandado; foto del " + _ddmmSemanal_(dia) +
      (anterior ? " comparada con la del " + _ddmmSemanal_(anterior.dia) : " (primera foto)") + (pdf ? "" : "; sin PDF"));
    return r;
  } catch (e) {
    _registrar_("resumen_semanal", "", "ERROR", _textoSemanal_(e && e.message || e, 300));
    throw e;
  }
}

function _verResumenSemanal_(ss, ahora) {
  var dia = _diaSemanal_(ahora);
  var actual = _calcularFotoSemanal_(_leerListasSemanal_(ss), dia);
  return _armarResumenSemanal_(dia, actual, _fotoAnteriorSemanal_(ss, dia),
    "(En el mail real va adjunta la solapa Principales 20 en PDF.)");
}

function _guardarFotoDeHoySemanal_(ss, ahora) {
  var dia = _diaSemanal_(ahora);
  var actual = _calcularFotoSemanal_(_leerListasSemanal_(ss), dia);
  _guardarFotoSemanal_(ss, dia, actual);
  _registrar_("resumen_semanal", "", "ok", "foto semanal guardada a mano: " + actual.filas.length + " filas del " + _ddmmSemanal_(dia));
  return actual.filas.length;
}

// Un solo disparador: los lunes entre las 08:00 y las 08:30 de Buenos Aires (nearMinute tiene ±15 min),
// después del mail diario de las 07:30.
function instalarResumenSemanal() {
  _borrarDisparadoresSemanal_();
  ScriptApp.newTrigger("resumenSemanal").timeBased().onWeekDay(ScriptApp.WeekDay.MONDAY)
    .atHour(8).nearMinute(15).inTimezone(SEMANAL_ZONA).create();
  _registrar_("sistema", "", "ok", "resumen semanal instalado: lunes 08:00–08:30 de Buenos Aires");
}

function quitarResumenSemanal() {
  _borrarDisparadoresSemanal_();
  _registrar_("sistema", "", "ok", "resumen semanal quitado");
}

// Evita mails duplicados al reinstalar, sin tocar los disparadores del importador ni del aviso.
function _borrarDisparadoresSemanal_() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === "resumenSemanal") ScriptApp.deleteTrigger(t);
  });
}


// ---------------------------------------------------------------- leer y escribir la Sheet

// Trae las tres listas como tablas (fila 1 = encabezado). Si falta una, error claro y no se escribe nada.
function _leerListasSemanal_(ss) {
  var listas = {};
  ["Cuentas a Cobrar", "Cuentas a Pagar", "Ultimos Pagos"].forEach(function (nombre) {
    var h = ss.getSheetByName(nombre);
    if (!h) throw new Error("Falta la solapa '" + nombre + "'; no se guardó ninguna foto.");
    listas[nombre] = h.getDataRange().getValues();
  });
  return listas;
}

// Agrega la foto al historial. Si ya había una del mismo día, la reemplaza (correr dos veces no duplica).
// Las fotos de otros días no se tocan.
function _guardarFotoSemanal_(ss, dia, foto) {
  var h = ss.getSheetByName(SEMANAL_HISTORIAL);
  if (!h) {
    h = ss.insertSheet(SEMANAL_HISTORIAL, ss.getNumSheets());
    h.getRange(1, 1, 1, SEMANAL_ENCABEZADO.length).setValues([SEMANAL_ENCABEZADO]).setFontWeight("bold");
    h.setFrozenRows(1);
  }
  var valores = h.getDataRange().getValues();
  // Se borra de abajo hacia arriba para que los números de fila no se corran mientras se borra.
  for (var i = valores.length - 1; i >= 1; i--) {
    if (_diaSemanal_(valores[i][0]) === dia) h.deleteRows(i + 1, 1);
  }
  var filas = foto.filas.map(function (f) {
    return [_fechaCeldaSemanal_(dia), f.empresa, f.tipo, f.puesto, f.nombre, f.saldo, f.vencido, f.aVencer,
      f.viejo ? _fechaCeldaSemanal_(f.viejo) : "", f.ultimo ? _fechaCeldaSemanal_(f.ultimo) : ""];
  });
  if (!filas.length) return;
  var desde = h.getLastRow() + 1;
  var faltan = desde + filas.length - 1 - h.getMaxRows();
  if (faltan > 0) h.insertRowsAfter(h.getMaxRows(), faltan);
  h.getRange(desde, 1, filas.length, SEMANAL_ENCABEZADO.length).setValues(filas);
  h.getRange(desde, 1, filas.length, 1).setNumberFormat("dd/mm/yyyy");
  h.getRange(desde, 6, filas.length, 3).setNumberFormat("#,##0");
  h.getRange(desde, 9, filas.length, 2).setNumberFormat("dd/mm/yyyy");
}

// La foto guardada más reciente ANTERIOR a hoy (no necesariamente de hace 7 días). null si no hay.
function _fotoAnteriorSemanal_(ss, dia) {
  var h = ss.getSheetByName(SEMANAL_HISTORIAL);
  if (!h) return null;
  return _fotoAnteriorDeTablaSemanal_(h.getDataRange().getValues(), dia);
}

function _fotoAnteriorDeTablaSemanal_(tabla, dia) {
  if (!tabla || tabla.length < 2) return null;
  var c = _columnasSemanal_(tabla[0], ["Fecha foto", "Empresa", "Tipo", "Puesto", "Razon Social", "Saldo", "Vencido",
    "A vencer", "Vto Impago Mas Viejo", "Ultimo Pago"], SEMANAL_HISTORIAL);
  var elegido = "";
  tabla.slice(1).forEach(function (r) {
    var d = _diaSemanal_(r[c["Fecha foto"]]);
    if (d && d < dia && d > elegido) elegido = d;
  });
  if (!elegido) return null;
  var filas = tabla.slice(1).filter(function (r) { return _diaSemanal_(r[c["Fecha foto"]]) === elegido; })
    .map(function (r) {
      return {empresa: String(r[c.Empresa]), tipo: String(r[c.Tipo]), puesto: Number(r[c.Puesto]),
        nombre: String(r[c["Razon Social"]]), saldo: _numeroSemanal_(r[c.Saldo]),
        vencido: _numeroSemanal_(r[c.Vencido]), aVencer: _numeroSemanal_(r[c["A vencer"]]),
        viejo: _diaSemanal_(r[c["Vto Impago Mas Viejo"]]), ultimo: _diaSemanal_(r[c["Ultimo Pago"]])};
    });
  return {dia: elegido, filas: filas};
}

// La solapa Principales 20 como PDF apaisado (solo esa solapa). Lanza error si Google no la entrega.
function _pdfPrincipalesSemanal_(ss, dia) {
  var h = ss.getSheetByName("Principales 20");
  if (!h) throw new Error("no existe la solapa Principales 20");
  var url = "https://docs.google.com/spreadsheets/d/" + ss.getId() + "/export?format=pdf&gid=" + h.getSheetId() +
    "&portrait=false&size=A4&fitw=true&gridlines=false&sheetnames=false&printtitle=false&pagenumbers=false";
  var resp = UrlFetchApp.fetch(url, {headers: {Authorization: "Bearer " + ScriptApp.getOAuthToken()}, muteHttpExceptions: true});
  if (resp.getResponseCode() !== 200) throw new Error("Google devolvió HTTP " + resp.getResponseCode() + " al exportar");
  return resp.getBlob().setName("NAVAR - Principales clientes y proveedores " + dia + ".pdf");
}


// ---------------------------------------------------------------- el cálculo (sin Google)

// Calcula los 4 bloques con las mismas reglas que la solapa. listas = {"Cuentas a Cobrar": tabla, ...}.
function _calcularFotoSemanal_(listas, dia) {
  var ultimos = _ultimosPagosSemanal_(listas["Ultimos Pagos"]);
  var filas = [];
  SEMANAL_BLOQUES.forEach(function (b) {
    var tabla = listas[b.hoja];
    if (!tabla || !tabla.length) throw new Error("Falta la solapa '" + b.hoja + "'; no se guardó ninguna foto.");
    var c = _columnasSemanal_(tabla[0], [b.columnaNombre, "Empresa", "Fecha Vencimiento", "Saldo Pendiente"], b.hoja);
    var por = {}, orden = [];
    tabla.slice(1).forEach(function (r) {
      var nombre = r[c[b.columnaNombre]];
      if (nombre === "" || nombre == null || String(r[c.Empresa]).trim() !== b.empresa) return;
      nombre = String(nombre);
      if (!por[nombre]) { por[nombre] = {saldo: 0, vencido: 0, viejo: ""}; orden.push(nombre); }
      var x = por[nombre], s = _numeroSemanal_(r[c["Saldo Pendiente"]]), v = _diaSemanal_(r[c["Fecha Vencimiento"]]);
      x.saldo += s;
      if (v && v < dia) {
        x.vencido += s;
        if (s > 0 && (!x.viejo || v < x.viejo)) x.viejo = v;
      }
    });
    // Orden estable: a igual saldo queda primero el que apareció antes en la lista (como SORTN).
    var top = orden.map(function (n, i) { return {n: n, i: i}; })
      .sort(function (a, b2) { return por[b2.n].saldo - por[a.n].saldo || a.i - b2.i; })
      .slice(0, SEMANAL_CUANTOS);
    top.forEach(function (t, k) {
      var x = por[t.n];
      filas.push({empresa: b.empresa, tipo: b.tipo, puesto: k + 1, nombre: t.n, saldo: _redondoSemanal_(x.saldo),
        vencido: _redondoSemanal_(x.vencido), aVencer: _redondoSemanal_(x.saldo - x.vencido), viejo: x.viejo,
        ultimo: ultimos[b.empresa + "|" + b.tipo + "|" + t.n] || ""});
    });
  });
  return {dia: dia, filas: filas};
}

// empresa|tipo|razón social → la fecha de último pago más nueva (AAAA-MM-DD).
function _ultimosPagosSemanal_(tabla) {
  if (!tabla || !tabla.length) throw new Error("Falta la solapa 'Ultimos Pagos'; no se guardó ninguna foto.");
  var c = _columnasSemanal_(tabla[0], ["Empresa", "Tipo", "Razon Social", "Fecha Ultimo Pago"], "Ultimos Pagos");
  var mapa = {};
  tabla.slice(1).forEach(function (r) {
    var d = _diaSemanal_(r[c["Fecha Ultimo Pago"]]);
    if (!d || !r[c["Razon Social"]]) return;
    var k = String(r[c.Empresa]).trim() + "|" + String(r[c.Tipo]).trim() + "|" + String(r[c["Razon Social"]]);
    if (!mapa[k] || d > mapa[k]) mapa[k] = d;
  });
  return mapa;
}


// ---------------------------------------------------------------- el texto del mail (sin Google)

function _armarResumenSemanal_(dia, actual, anterior, notaPdf) {
  var L = [];
  L.push(anterior ? "Comparado con la foto del " + _ddmmSemanal_(anterior.dia) + "." :
    "Es la primera foto: todavía no hay una semana anterior para comparar. Desde el próximo lunes van las diferencias.");
  L.push("");
  SEMANAL_BLOQUES.forEach(function (b) {
    var ahora = _delBloqueSemanal_(actual, b), antes = anterior ? _delBloqueSemanal_(anterior, b) : null;
    L.push(b.titulo);
    if (!ahora.length) { L.push("- sin datos en la lista"); L.push(""); return; }
    var suma = _sumaSemanal_(ahora, "saldo"), venc = _sumaSemanal_(ahora, "vencido");
    L.push("- Los " + ahora.length + " principales suman " + _plataSemanal_(suma) +
      (antes ? " (" + _difSemanal_(suma - _sumaSemanal_(antes, "saldo")) + ")" : "") +
      " · vencido " + _plataSemanal_(venc) + (antes ? " (" + _difSemanal_(venc - _sumaSemanal_(antes, "vencido")) + ")" : ""));
    if (antes) {
      var previo = {};
      antes.forEach(function (f) { previo[f.nombre] = f; });
      var cambios = ahora.filter(function (f) { return previo[f.nombre]; }).map(function (f) {
        return {f: f, d: _redondoSemanal_(f.vencido - previo[f.nombre].vencido)};
      });
      var bajaron = cambios.filter(function (x) { return x.d <= -1; }).sort(function (a, b2) { return a.d - b2.d; }).slice(0, 3);
      var subieron = cambios.filter(function (x) { return x.d >= 1; }).sort(function (a, b2) { return b2.d - a.d; }).slice(0, 3);
      L.push("- Bajaron su vencido: " + (bajaron.length ? bajaron.map(_cambioSemanal_).join("; ") : "ninguno"));
      L.push("- Subieron su vencido: " + (subieron.length ? subieron.map(_cambioSemanal_).join("; ") : "ninguno"));
      var hoyN = {}; ahora.forEach(function (f) { hoyN[f.nombre] = true; });
      var entraron = ahora.filter(function (f) { return !previo[f.nombre]; }).map(function (f) { return _textoSemanal_(f.nombre, 40); });
      var salieron = antes.filter(function (f) { return !hoyN[f.nombre]; }).map(function (f) { return _textoSemanal_(f.nombre, 40); });
      if (entraron.length || salieron.length)
        L.push("- Entraron: " + (entraron.join(", ") || "ninguno") + " · Salieron: " + (salieron.join(", ") || "ninguno"));
      else L.push("- Los mismos 20 que la foto anterior");
    }
    L.push("");
  });
  L.push("SIN PAGOS REGISTRADOS EN TANGO (de los principales de hoy)");
  var alguno = false;
  SEMANAL_BLOQUES.forEach(function (b) {
    var sin = _delBloqueSemanal_(actual, b).filter(function (f) { return !f.ultimo; });
    if (!sin.length) return;
    alguno = true;
    L.push("- " + (b.tipo === "Cliente" ? "Clientes " : "Proveedores ") + b.empresa + ": " + sin.map(function (f) {
      return _textoSemanal_(f.nombre, 40) + " (" + _plataSemanal_(f.saldo) + ")";
    }).join("; "));
  });
  if (!alguno) L.push("- ninguno: todos tienen al menos un pago registrado");
  L.push("");
  if (notaPdf) { L.push(notaPdf); L.push(""); }
  L.push("Datos según Tango. Detalle en la solapa Principales 20 de la planilla.");
  return {asunto: "NAVAR · Principales clientes y proveedores · semana del " + _ddmmSemanal_(dia), cuerpo: L.join("\n")};
}

function _delBloqueSemanal_(foto, b) {
  return foto.filas.filter(function (f) { return f.empresa === b.empresa && f.tipo === b.tipo; })
    .sort(function (x, y) { return x.puesto - y.puesto; });
}

function _sumaSemanal_(filas, campo) {
  return filas.reduce(function (s, f) { return s + (f[campo] || 0); }, 0);
}

function _cambioSemanal_(x) {
  return _textoSemanal_(x.f.nombre, 40) + " " + _plataSemanal_(x.f.vencido) + " (" + _difSemanal_(x.d) + ")";
}


// ---------------------------------------------------------------- formatos y ayudas

// $123,4 M con coma decimal, como se lee en Argentina.
function _plataSemanal_(v) {
  var m = Math.abs(v) / 1e6;
  return (v < 0 ? "−" : "") + "$" + m.toFixed(1).replace(".", ",") + " M";
}

// Diferencia con signo: +$1,2 M / −$3,4 M / sin cambios.
function _difSemanal_(d) {
  if (Math.abs(d) < 50000) return "sin cambios";
  return (d > 0 ? "+" : "−") + "$" + (Math.abs(d) / 1e6).toFixed(1).replace(".", ",") + " M";
}

function _redondoSemanal_(v) { return Math.round(v * 100) / 100; }

function _numeroSemanal_(v) {
  if (typeof v === "number") return isFinite(v) ? v : 0;
  var s = String(v == null ? "" : v).replace(/[$\s]/g, "");
  if (!s) return 0;
  if (s.indexOf(",") >= 0) s = s.replace(/\./g, "").replace(",", ".");
  var n = Number(s);
  return isFinite(n) ? n : 0;
}

// Cualquier fecha (Date de la Sheet o texto AAAA-MM-DD / dd/mm/aaaa) → "AAAA-MM-DD" en hora de Buenos Aires.
function _diaSemanal_(v) {
  if (v instanceof Date) return isNaN(v) ? "" : Utilities.formatDate(v, SEMANAL_ZONA, "yyyy-MM-dd");
  var s = String(v == null ? "" : v).trim(), m;
  if ((m = s.match(/^(\d{4})-(\d{2})-(\d{2})/))) return m[1] + "-" + m[2] + "-" + m[3];
  if ((m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/))) return m[3] + "-" + ("0" + m[2]).slice(-2) + "-" + ("0" + m[1]).slice(-2);
  return "";
}

// "AAAA-MM-DD" → Date a las 00:00 de Buenos Aires, para que la Sheet lo muestre como ese día.
function _fechaCeldaSemanal_(dia) {
  return Utilities.parseDate(dia + " 00:00", SEMANAL_ZONA, "yyyy-MM-dd HH:mm");
}

function _ddmmSemanal_(dia) { return dia.slice(8, 10) + "/" + dia.slice(5, 7); }

function _textoSemanal_(texto, limite) {
  var limpio = String(texto == null ? "" : texto).replace(/\s+/g, " ").trim();
  return limite && limpio.length > limite ? limpio.slice(0, limite - 3) + "..." : limpio;
}

// Ubica columnas por encabezado (sin importar tildes, mayúsculas ni el orden). Si falta una, error claro.
function _columnasSemanal_(encabezado, requeridas, hoja) {
  function norm(s) {
    return String(s == null ? "" : s).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/\s+/g, " ").trim();
  }
  var pos = {};
  encabezado.forEach(function (e, i) { var k = norm(e); if (k && !(k in pos)) pos[k] = i; });
  var c = {}, faltan = [];
  requeridas.forEach(function (r) { if (norm(r) in pos) c[r] = pos[norm(r)]; else faltan.push(r); });
  if (faltan.length) throw new Error("A la solapa '" + hoja + "' le falta la columna " + faltan.join(", ") +
    " en la fila 1; no se guardó ninguna foto.");
  return c;
}
