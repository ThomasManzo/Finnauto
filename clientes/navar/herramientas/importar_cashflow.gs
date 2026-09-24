/**
 * importar_cashflow.gs — carga en la Sheet "NAVAR - Cash Flow" lo que dejan los lectores,
 * pisando lo que ellos mismos cargaron la vez anterior. Tres botones en el menú "finauto":
 *
 *   Importar Tango    para_pegar_en_la_sheet_<fecha>.xlsx  (lector/tango.py)
 *                     → Cuentas a Cobrar · Cuentas a Pagar · Cartera de Cheques
 *   Importar Bancos   para_pegar_bancos_<fecha>.xlsx       (lector/extractos.py)
 *                     → Saldos Bancarios · Movimientos
 *   Importar Deuda    para_pegar_deuda_<fecha>.xlsx        (lector/deuda_bancaria.py)
 *                     → Deuda Bancaria (los dos bloques: líneas y cronograma)
 *
 * QUÉ HACE CADA UNO
 * -----------------
 * Busca en Drive, dentro de "NAVAR - Datos" (en cualquier subcarpeta), el archivo
 * más nuevo con ese prefijo, lo abre y vuelca sus solapas en las solapas de esta
 * Sheet. Antes de escribir, BORRA las filas que vinieron de ese mismo lector la vez
 * anterior (las reconoce por una marca: "Tango Live" / "REVISAR:" / "AGREGADO" en
 * Observaciones, "Extracto" / "Captura" en Origen, "Mapa deuda" en Observaciones).
 * Lo que cargó una persona a mano queda como está. Así se puede correr todas las
 * veces que haga falta sin duplicar nada.
 *
 * Las columnas con fórmula (Saldo Pendiente, Estado, Dias de Atraso, Semana (lunes),
 * Importe Total Cuota) NO se tocan: la Sheet las calcula sola.
 *
 * CÓMO SE INSTALA (una vez)
 * -------------------------
 *  1. Abrir la Sheet "NAVAR - Cash Flow" → Extensiones → Apps Script.
 *  2. Si ya está el script "importar_tango" del 17/09: borrar todo su contenido y
 *     pegar esto entero (el nombre del archivo en Apps Script no importa). Si no,
 *     Archivo nuevo → Script → pegar → Guardar.
 *  3. En Servicios (el "+" del panel izquierdo) tienen que estar "Drive API" y "Google Sheets API".
 *     Si falta Sheets API, la importación se frena sin cargar datos.
 *  4. Elegir arriba la función que se quiera probar (importarTango, importarBancos,
 *     importarDeuda) y darle ▶ Ejecutar. La primera vez pide autorizar. Aceptar.
 *  5. Al terminar aparece un aviso chico abajo a la derecha de la Sheet (toast) con
 *     cuántas filas borró y cargó. También queda en Ver → Registros.
 *
 * CÓMO SE USA DESPUÉS
 * -------------------
 * Correr el lector en la Mac, subir el para_pegar a Drive (en cualquier subcarpeta
 * de "NAVAR - Datos"), y en la Sheet: menú "finauto" → el botón que corresponda.
 *
 * ACTUALIZACIÓN AUTOMÁTICA (desde el 20/09)
 * -----------------------------------------
 * "finauto → Instalar actualización automática" crea un disparador que corre
 * importarLoNuevo() cada hora. Esa función mira, para cada lector, cuál es el
 * para_pegar_* más nuevo en Drive; si es distinto del último que importó (se acuerda
 * por id + fecha de modificación), lo importa. Si no hay nada nuevo, no toca nada.
 * Cada importación queda anotada en la solapa "Registro" (cuándo, qué archivo, qué
 * cargó, o el error si falló). Así nadie tiene que apretar botones: el lector deja el
 * archivo en Drive y a lo sumo una hora después la Sheet está al día.
 */

var CARPETA_RAIZ = "NAVAR - Datos";

// Cada solapa: de qué solapa del xlsx viene, qué columnas tienen fórmula (no se
// escriben), en qué columna está la marca y cuáles son las marcas que se pisan,
// y si la columna A es un ID que se renumera (conId) o un dato (fecha).
var IMPORTS = {
  tango: {
    prefijo: "para_pegar_en_la_sheet_",
    solapas: [
      { xlsx: "Cuentas a Cobrar",   sheet: "Cuentas a Cobrar",   formulas: ["Saldo Pendiente", "Estado", "Dias de Atraso"],
        colMarca: "Observaciones", marcas: ["Tango Live", "REVISAR:", "AGREGADO"], conId: true },
      { xlsx: "Cuentas a Pagar",    sheet: "Cuentas a Pagar",    formulas: ["Saldo Pendiente", "Estado", "Dias de Atraso"],
        colMarca: "Observaciones", marcas: ["Tango Live", "REVISAR:", "AGREGADO"], conId: true },
      { xlsx: "Cartera de Cheques", sheet: "Cartera de Cheques", formulas: [],
        colMarca: "Observaciones", marcas: ["Tango Live", "REVISAR:", "AGREGADO"], conId: true },
    ]
  },
  bancos: {
    prefijo: "para_pegar_bancos_",
    solapas: [
      // El saldo "(varios)" cargado a mano el 31/08 para la empresa A se pisa también:
      // con extractos, el saldo de A es el de cada cuenta. El de AA queda (no hay extractos).
      { xlsx: "Saldos Bancarios", sheet: "Saldos Bancarios", formulas: [],
        colMarca: "Origen", marcas: ["Extracto", "Captura"], conId: false, pisarTambien: _saldoManualDeA_ },
      { xlsx: "Movimientos",      sheet: "Movimientos",      formulas: ["Semana (lunes)"],
        colMarca: "Origen", marcas: ["Extracto", "Captura"], conId: true },
    ]
  },
  // La operación en efectivo de AA (Tango → lector/tesoreria_aa.py): filas de Movimientos con
  // Origen "Tango AA". Pisa solo esas; las del extracto ("Extracto") las maneja "bancos".
  tesoreria_aa: {
    prefijo: "para_pegar_tesoreria_aa_",
    solapas: [
      { xlsx: "Movimientos", sheet: "Movimientos", formulas: ["Semana (lunes)"],
        colMarca: "Origen", marcas: ["Tango AA"], conId: true },
    ]
  },
  impuestos: {
    prefijo: "para_pegar_impuestos_",
    solapas: [
      { xlsx: "Deuda Impositiva", sheet: "Deuda Impositiva", formulas: [],
        colMarca: "Observaciones", marcas: ["Mapa impuestos", "AGREGADO", "(agregado"], conId: false },
    ]
  },
  deuda: {
    prefijo: "para_pegar_deuda_",
    // Deuda Bancaria tiene dos bloques en la misma solapa, cada uno con su fila "Banco".
    bloques: [
      { xlsx: "Lineas",     formulas: [],                     colMarca: "Observaciones", marcas: ["Mapa deuda", "AGREGADO", "(agregado"] },
      { xlsx: "Cronograma", formulas: ["Importe Total Cuota"], colMarca: "Observaciones", marcas: ["Mapa deuda", "AGREGADO", "(agregado"] },
    ]
  }
};


function onOpen() {
  SpreadsheetApp.getUi().createMenu("finauto")
    .addItem("Importar Tango (cobrar / pagar / cheques)", "importarTango")
    .addItem("Importar Bancos (saldos / movimientos)", "importarBancos")
    .addItem("Importar Deuda (deuda bancaria)", "importarDeuda")
    .addItem("Importar Impuestos (deuda impositiva)", "importarImpuestos")
    .addItem("Importar Tesorería AA (efectivo)", "importarTesoreriaAA")
    .addSeparator()
    .addItem("Importar lo nuevo ahora (lo que haría el disparador)", "importarLoNuevo")
    .addItem("Instalar actualización automática (cada hora)", "instalarDisparador")
    .addItem("Quitar actualización automática", "quitarDisparador")
    .addSeparator()
    .addItem("Ver el aviso de hoy (sin mandar)", "avisoDiarioPrueba")          // aviso_diario.gs
    .addItem("Instalar aviso diario 09:00", "instalarAvisoDiario")
    .addItem("Quitar aviso diario", "quitarAvisoDiario")
    .addSeparator()
    .addItem("Armar solapa Cash (Cash, Semanal, Mensual)", "armarCash")
    .addItem("Armar solapa Plan (pisa las decisiones cargadas)", "armarPlan")
    .addItem("Arreglar los desplegables (Origen, Banco, Categoria)", "arreglarValidaciones")   // crear_cash.gs
    .addToUi();
}


// ---- actualización automática ------------------------------------------------------
// Orden: deuda e impuestos antes que bancos y Tango, porque las pantallas leen todo junto
// y da igual; pero si un import falla, los demás siguen (cada uno con su try).
var ORDEN_AUTO = ["deuda", "impuestos", "bancos", "tesoreria_aa", "tango"];

function importarLoNuevo() {
  var props = PropertiesService.getDocumentProperties();
  var hubo = 0;
  ORDEN_AUTO.forEach(function (cual) {
    var cfg = IMPORTS[cual];
    var archivo = _ultimoConPrefijo_(cfg.prefijo);
    if (!archivo) return;
    var firma = archivo.getId() + "@" + archivo.getLastUpdated().getTime();
    if (props.getProperty("importado_" + cual) === firma) return;     // ya se importó ese mismo archivo
    try {
      var resumen = _importar_(cual, archivo);
      props.setProperty("importado_" + cual, firma);
      _registrar_(cual, archivo.getName(), "ok", resumen);
      hubo++;
    } catch (e) {
      _registrar_(cual, archivo.getName(), "ERROR", String(e && e.message || e));
    }
  });
  if (!hubo) Logger.log("importarLoNuevo: nada nuevo");
  return hubo;
}

function instalarDisparador() {
  quitarDisparador();
  ScriptApp.newTrigger("importarLoNuevo").timeBased().everyHours(1).create();
  _registrar_("sistema", "", "ok", "disparador instalado: importarLoNuevo cada hora");
  try { SpreadsheetApp.getActiveSpreadsheet().toast("Listo: la Sheet se actualiza sola cada hora con lo nuevo de Drive.", "finauto", 10); } catch (e) {}
}

function quitarDisparador() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === "importarLoNuevo") ScriptApp.deleteTrigger(t);
  });
}

// La solapa "Registro": una fila por importación. Se crea sola la primera vez.
function _registrar_(cual, archivo, estado, detalle) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var h = ss.getSheetByName("Registro");
  if (!h) {
    h = ss.insertSheet("Registro", ss.getNumSheets());
    h.getRange(1, 1, 1, 5).setValues([["Cuándo", "Qué", "Archivo", "Estado", "Detalle"]]).setFontWeight("bold");
    h.setFrozenRows(1);
    h.setColumnWidths(1, 5, 140); h.setColumnWidth(3, 260); h.setColumnWidth(5, 520);
  }
  _quitarFiltros_(h);
  h.insertRowAfter(1);
  h.getRange(2, 1, 1, 5).setValues([[new Date(), cual, archivo, estado, detalle]]);
  h.getRange(2, 1).setNumberFormat("dd/mm/yyyy hh:mm");
}

function importarTango()     { _importarManual_("tango"); }
function importarBancos()    { _importarManual_("bancos"); }
function importarDeuda()     { _importarManual_("deuda"); }
function importarImpuestos() { _importarManual_("impuestos"); }
function importarTesoreriaAA() { _importarManual_("tesoreria_aa"); }


// Los botones y el reloj dejan la misma evidencia; un fallo nunca se disfraza de ok.
function _importarManual_(cual) {
  var archivo;
  try {
    archivo = _ultimoConPrefijo_(IMPORTS[cual].prefijo);
    var resumen = _importar_(cual, archivo);
    _registrar_(cual, archivo.getName(), "ok", resumen);
  } catch (e) {
    _registrar_(cual, archivo ? archivo.getName() : "", "ERROR", String(e.message || e));
    throw e;
  }
}

function _importar_(cual, archivo) {
  var lock = LockService.getDocumentLock();
  if (!lock || !lock.tryLock(1000)) throw new Error("Importación en curso: esperá y volvé a correr Importar lo nuevo.");
  try { return _importarConLock_(cual, archivo); }
  finally { lock.releaseLock(); }
}

function _importarConLock_(cual, archivo) {
  var cfg = IMPORTS[cual];
  archivo = archivo || _ultimoConPrefijo_(cfg.prefijo);
  if (!archivo) throw new Error("No encontré ningún " + cfg.prefijo + "*.xlsx dentro de " + CARPETA_RAIZ);
  Logger.log("Importando " + archivo.getName() + " (" + archivo.getLastUpdated() + ")");

  // El xlsx se convierte a una Sheet temporal para poder leerlo; se borra al final.
  var temp = Drive.Files.copy({ title: "tmp_importar_" + cual, mimeType: MimeType.GOOGLE_SHEETS }, archivo.getId());
  var origen = SpreadsheetApp.openById(temp.id);
  var destino = SpreadsheetApp.getActiveSpreadsheet();
  var resumen = [];
  try {
    // Se revisan TODAS las solapas de datos antes de cargar la primera.
    var nombres = cfg.solapas ? cfg.solapas.map(function (s) { return s.sheet; }) : ["Deuda Bancaria"];
    var hojas = nombres.map(function (nombre) {
      var h = destino.getSheetByName(nombre);
      if (!h) throw new Error(nombre + ": falta la solapa destino; pedí ayuda a finauto.");
      return h;
    });
    (cfg.solapas || cfg.bloques).forEach(function (s) {
      if (!origen.getSheetByName(s.xlsx)) throw new Error((s.sheet || "Deuda Bancaria") + ": falta " + s.xlsx + " en el para_pegar; revisá el archivo.");
    });
    _comprobarVistas_(destino, hojas);
    hojas.forEach(_quitarFiltros_);

    if (cfg.solapas) {
      cfg.solapas.forEach(function (s) {
        var hOrigen = origen.getSheetByName(s.xlsx);
        var hDestino = destino.getSheetByName(s.sheet);
        if (!hOrigen || !hDestino) { resumen.push(s.sheet + ": falta la solapa (origen " + !!hOrigen + ", destino " + !!hDestino + ")"); return; }
        var r = _volcar_(hOrigen, hDestino, 1, hDestino.getMaxRows(), s);
        resumen.push(s.sheet + ": borradas " + r.borradas + " filas viejas, cargadas " + r.cargadas);
      });
    }
    if (cfg.bloques) {
      var hDestino = destino.getSheetByName("Deuda Bancaria");
      var colA = hDestino.getRange(1, 1, hDestino.getLastRow(), 1).getValues().map(function (r) { return _n_(r[0]); });
      var encs = [];
      colA.forEach(function (v, i) { if (v === "banco") encs.push(i + 1); });
      if (encs.length !== 2) throw new Error("Deuda Bancaria: esperaba 2 filas 'Banco' (líneas y cronograma), hay " + encs.length);
      // bloque A: desde su encabezado hasta 2 filas antes del título "B) Cronograma"; bloque B: hasta el final.
      var limites = [[encs[0], encs[1] - 3], [encs[1], hDestino.getMaxRows()]];
      cfg.bloques.forEach(function (b, i) {
        var hOrigen = origen.getSheetByName(b.xlsx);
        if (!hOrigen) { resumen.push("Deuda Bancaria/" + b.xlsx + ": falta la solapa en el xlsx"); return; }
        var r = _volcar_(hOrigen, hDestino, limites[i][0], limites[i][1], b);
        resumen.push("Deuda Bancaria/" + b.xlsx + ": borradas " + r.borradas + " filas viejas, cargadas " + r.cargadas);
      });
    }
  } finally {
    Drive.Files.remove(temp.id);
  }
  var msg = "Importado " + archivo.getName() + "\n" + resumen.join("\n");
  Logger.log(msg);
  // Un aviso que NO bloquea (alert() espera un click que, corriendo desde el editor,
  // nadie da, y a los 6 minutos Google corta con "Exceeded maximum execution time").
  try { destino.toast(resumen.join(" · "), "Importar " + cual + ": listo", 20); } catch (e) { /* sin UI por disparador */ }
  return resumen.join(" · ");
}


// ---- el archivo más nuevo con ese prefijo, buscando en todo el árbol de NAVAR - Datos
function _ultimoConPrefijo_(prefijo) {
  var raiz = DriveApp.getFoldersByName(CARPETA_RAIZ);
  if (!raiz.hasNext()) return null;
  var mejor = null;
  var pila = [raiz.next()];
  while (pila.length) {
    var carpeta = pila.pop();
    var archivos = carpeta.getFiles();
    while (archivos.hasNext()) {
      var f = archivos.next();
      if (f.getName().indexOf(prefijo) === 0 && (!mejor || f.getLastUpdated() > mejor.getLastUpdated())) mejor = f;
    }
    var sub = carpeta.getFolders();
    while (sub.hasNext()) pila.push(sub.next());
  }
  return mejor;
}


// ---- el saldo "(varios)" de la empresa A cargado a mano: se pisa cuando hay extractos
function _saldoManualDeA_(fila, enc) {
  var banco = _n_(fila[enc.map(_n_).indexOf("banco")]);
  var empresa = _n_(fila[enc.map(_n_).indexOf("empresa")]);
  return banco === "(varios)" && empresa === "a";
}


// ---- borra lo marcado, pega lo nuevo, respetando el orden de columnas de la Sheet.
// filaEnc: fila del encabezado en el destino; filaFin: última fila que puede usar.
// Todo se escribe por bloques (setValues por columna), no celda por celda: con 2.000
// filas, celda por celda tarda minutos y Apps Script corta a los 6.
function _volcar_(hOrigen, hDestino, filaEnc, filaFin, s) {
  try {
    _quitarFiltros_(hDestino);
    return _volcarSinFiltro_(hOrigen, hDestino, filaEnc, filaFin, s);
  } catch (e) {
    throw new Error(hDestino.getName() + "/" + (s.xlsx || "lista") + ": " + String(e.message || e) +
      " Puede haber una carga parcial; revisá Registro y el para_pegar antes de usar el cash.");
  }
}

function _volcarSinFiltro_(hOrigen, hDestino, filaEnc, filaFin, s) {
  var encO = hOrigen.getRange(1, 1, 1, hOrigen.getLastColumn()).getValues()[0].map(String);
  var encD = hDestino.getRange(filaEnc, 1, 1, hDestino.getLastColumn()).getValues()[0].map(String);
  // Si el lector trae una columna que la solapa no tiene (ej. "Debito Automatico" el 22/09),
  // se agrega al final del encabezado: así una columna nueva no requiere tocar la Sheet a mano.
  var faltan = encO.filter(function (e) { return e && encD.map(_n_).indexOf(_n_(e)) === -1; });
  if (faltan.length) {
    var ultimaCol = 0;
    encD.forEach(function (e, i) { if (e) ultimaCol = i + 1; });
    faltan.forEach(function (e, k) {
      if (ultimaCol + 1 + k > hDestino.getMaxColumns()) hDestino.insertColumnAfter(hDestino.getMaxColumns());
      hDestino.getRange(filaEnc, ultimaCol + 1 + k).setValue(e).setFontWeight("bold");
    });
    encD = hDestino.getRange(filaEnc, 1, 1, hDestino.getLastColumn()).getValues()[0].map(String);
  }
  [encO, encD].forEach(function (encabezados) {
    var usados = {};
    encabezados.forEach(function (nombre) {
      var clave = _n_(nombre);
      if (clave && usados[clave]) throw new Error("encabezado repetido: " + nombre);
      if (clave) usados[clave] = true;
    });
  });
  var colMarca = encD.map(_n_).indexOf(_n_(s.colMarca));
  if (colMarca < 0 || encO.map(_n_).indexOf(_n_(s.colMarca)) < 0)
    throw new Error("falta la columna " + s.colMarca + "; no se puede distinguir lo manual.");
  var colNombre = 1;   // columna B: Cliente / Proveedor / Tipo / Fecha / Empresa. Vacía = fila sin datos.

  // 1. Lo que hay hoy: se separa lo que se pisa de lo que cargó una persona.
  var ultima = _ultimaFilaConDatos_(hDestino, filaEnc + 1, filaFin, colNombre + 1);
  var viejas = ultima >= filaEnc + 1
    ? hDestino.getRange(filaEnc + 1, 1, ultima - filaEnc, encD.length).getValues() : [];
  var vivas = [], borradas = 0;
  viejas.forEach(function (r) {
    if (String(r[colNombre] || "") === "" && String(r[0] || "") === "") return;
    var marca = colMarca >= 0 ? String(r[colMarca] || "") : "";
    var pisar = s.marcas.some(function (m) { return marca.indexOf(m) !== -1; }) ||
                (s.pisarTambien && s.pisarTambien(r, encD));
    if (pisar) borradas++;
    else vivas.push(r);
  });

  // 2. Lo nuevo, reordenado a las columnas de la Sheet.
  var mapa = {}; encO.forEach(function (e, i) { mapa[_n_(e)] = i; });
  var nuevas = hOrigen.getLastRow() > 1
    ? hOrigen.getRange(2, 1, hOrigen.getLastRow() - 1, encO.length).getValues() : [];
  var cargadas = 0;
  var finales = vivas.slice();
  nuevas.forEach(function (r) {
    var idxNombre = mapa[_n_(encD[colNombre])];
    if (idxNombre === undefined) throw new Error("falta la columna " + encD[colNombre] + " en el para_pegar");
    if (String(r[idxNombre] || "") === "") {
      if (r.some(function (v) { return v !== "" && v !== null; })) throw new Error("fila del para_pegar sin " + encD[colNombre] + "; revisá el archivo");
      return;
    }
    finales.push(encD.map(function (nombre) {
      var idx = mapa[_n_(nombre)];
      return idx === undefined ? "" : (r[idx] === null ? "" : r[idx]);
    }));
    cargadas++;
  });
  if (s.conId) finales.forEach(function (r, i) { r[0] = i + 1; });   // ID de corrido

  // 3. Escribir columna por columna, salteando las de fórmula, y limpiar lo que sobra abajo.
  var total = finales.length, antes = viejas.length;
  if (filaEnc + total > filaFin) throw new Error(hDestino.getName() + ": no hay lugar para " + total + " filas (hay hasta la fila " + filaFin + ")");
  for (var c = 0; c < encD.length; c++) {
    if (!encD[c] || s.formulas.indexOf(encD[c]) !== -1) continue;
    if (total > 0) hDestino.getRange(filaEnc + 1, c + 1, total, 1).setValues(finales.map(function (r) { return [r[c]]; }));
    if (antes > total) hDestino.getRange(filaEnc + 1 + total, c + 1, antes - total, 1).clearContent();
  }
  // 4. Las columnas con fórmula tienen que llegar hasta la última fila cargada: si hay más
  // filas que antes, se estira la fórmula de la primera fila (el 21/09, 83 facturas de AA
  // quedaron sin Saldo Pendiente ni Estado y el vencido de AA daba 0).
  if (total > 0) s.formulas.forEach(function (nombre) {
    var c = encD.indexOf(nombre);
    if (c < 0) return;
    var primera = hDestino.getRange(filaEnc + 1, c + 1);
    if (!primera.getFormula()) return;
    primera.copyTo(hDestino.getRange(filaEnc + 1, c + 1, total, 1), SpreadsheetApp.CopyPasteType.PASTE_FORMULA, false);
    if (antes > total) hDestino.getRange(filaEnc + 1 + total, c + 1, antes - total, 1).clearContent();
  });
  SpreadsheetApp.flush();
  _verificarVolcado_(hDestino, filaEnc, filaFin, encD, s, finales, antes);
  return { borradas: borradas, cargadas: cargadas };
}


// ---- última fila con algo en la columna dada, dentro del rango [desde, hasta]
function _ultimaFilaConDatos_(h, desde, hasta, col) {
  var n = Math.min(hasta, h.getLastRow()) - desde + 1;
  if (n <= 0) return desde - 1;
  var vals = h.getRange(desde, col, n, 1).getValues();
  for (var i = vals.length - 1; i >= 0; i--) if (String(vals[i][0] || "") !== "") return desde + i;
  return desde - 1;
}


function _n_(s) {
  return String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/\s+/g, " ").trim();
}


// Sheets permite consultar las vistas guardadas, pero no saber cuál tiene abierta cada
// persona. Ante cualquiera de ellas frenamos: cerrarla no alcanza, hay que eliminarla.
function _comprobarVistas_(ss, hojas) {
  var nombres = hojas.map(function (h) { return h.getName(); }).join(", ");
  var foto;
  try {
    foto = Sheets.Spreadsheets.get(ss.getId(), {fields: "sheets(properties(sheetId),filterViews)"});
    if (!foto || !foto.sheets) throw new Error("respuesta incompleta");
  } catch (e) {
    throw new Error(nombres + ": no pude comprobar vistas de filtro. Pedí a finauto habilitar Google Sheets API y revisar permisos; no se cargaron datos. " + String(e.message || e));
  }
  hojas.forEach(function (h) {
    var datos = foto.sheets.filter(function (s) { return s.properties.sheetId === h.getSheetId(); });
    if (datos.length !== 1) throw new Error(h.getName() + ": no pude comprobar vistas de filtro; pedí ayuda a finauto.");
    if ((datos[0].filterViews || []).length) throw new Error(h.getName() +
      ": sacá las vistas de filtro guardadas (Datos → Vistas de filtro → Eliminar) y volvé a correr Importar lo nuevo. No se cargaron datos.");
  });
}

// No reocultamos números de fila: al reemplazar la lista podrían tapar otro cheque.
// Tampoco reponemos filtros viejos: su rango puede dejar afuera las filas nuevas.
function _quitarFiltros_(h) {
  try {
    var filtro = h.getFilter();
    if (filtro) filtro.remove();
    h.showRows(1, h.getMaxRows());
    SpreadsheetApp.flush();
    if (h.getFilter()) throw new Error("el filtro sigue puesto");
  } catch (e) {
    throw new Error(h.getName() + ": sacá el filtro y mostrá todas las filas; volvé a correr Importar lo nuevo. " + String(e.message || e));
  }
}

// Se vuelve a leer TODO lo escrito, incluidas las filas manuales conservadas y la cola
// borrada. No alcanza comparar totales: una fecha corrida puede sumar igual.
function _verificarVolcado_(h, enc, fin, nombres, cfg, esperado, antes) {
  var alto = Math.max(esperado.length, antes);
  var leido = alto ? h.getRange(enc + 1, 1, alto, nombres.length).getValues() : [];
  for (var f = 0; f < alto; f++) {
    for (var c = 0; c < nombres.length; c++) {
      if (!nombres[c] || cfg.formulas.indexOf(nombres[c]) !== -1) continue;
      var valor = f < esperado.length ? esperado[f][c] : "";
      if (!_mismoDato_(valor, leido[f][c])) throw new Error("VERIFICACION_NO_CUADRA: " + h.getName() +
        " fila " + (enc + 1 + f) + ", columna " + nombres[c] + ". La escritura terminó pero no coincide con lo preparado; no usar el cash hasta revisar y reimportar.");
    }
  }
  if (_ultimaFilaConDatos_(h, enc + 1, fin, 2) !== enc + esperado.length)
    throw new Error("VERIFICACION_NO_CUADRA: " + h.getName() + ": cantidad de filas distinta; revisá el para_pegar y reimportá.");
}

function _mismoDato_(a, b) {
  if (a instanceof Date || b instanceof Date) return a instanceof Date && b instanceof Date && a.getTime() === b.getTime();
  return a === b;
}
