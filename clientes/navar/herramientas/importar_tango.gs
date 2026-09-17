/**
 * importar_tango.gs — carga en la Sheet las listas que salen de Tango, pisando lo anterior.
 *
 * QUÉ HACE
 * --------
 * Busca en Drive el archivo `para_pegar_en_la_sheet_<fecha>.xlsx` más nuevo
 * (lo deja `lector/tango.py` en "NAVAR - Datos / Tango / <fecha>") y vuelca sus
 * tres solapas en las solapas de esta Sheet:
 *
 *     Cuentas a Cobrar · Cuentas a Pagar · Cartera de Cheques
 *
 * Antes de escribir, BORRA las filas que vinieron de Tango la vez anterior y las
 * "(agregado cash viejo)": las reconoce por la columna Observaciones (empiezan
 * con "Tango Live", "REVISAR:" o dicen "AGREGADO"). Lo que cargó una persona a
 * mano queda como está. Así se puede correr todas las veces que haga falta sin
 * duplicar nada.
 *
 * Las columnas con fórmula (Saldo Pendiente, Estado, Dias de Atraso) NO se
 * tocan: la Sheet las calcula sola. Solo se escriben las de datos.
 *
 * CÓMO SE INSTALA (una vez)
 * -------------------------
 *  1. Abrir la Sheet "NAVAR - Cash Flow" → Extensiones → Apps Script.
 *  2. Archivo nuevo → Script → nombre "importar_tango" → pegar esto entero → Guardar.
 *  3. En Servicios (el "+" del panel izquierdo) agregar "Drive API" (para leer el xlsx).
 *  4. Elegir la función `importarTango` arriba y darle ▶ Ejecutar. La primera vez
 *     pide autorizar (leer Drive, editar esta Sheet). Aceptar.
 *  5. Mirar el registro (Ver → Registros): dice cuántas filas borró y cuántas cargó.
 *
 * CÓMO SE USA DESPUÉS
 * -------------------
 * Cada vez que haya exports nuevos: correr `lector/tango.py`, subir el
 * `para_pegar...` a la carpeta de esa fecha en Drive, y en la Sheet:
 * menú "finauto" → "Importar Tango" (el menú lo crea este script al abrir).
 * Cuando la notebook de NAVAR deje los archivos sola, un disparador horario
 * (Activadores → importarTango, cada día 7:30) hace lo mismo sin que nadie toque.
 */

var CARPETA_RAIZ = "NAVAR - Datos";
var CARPETA_TANGO = "Tango";
var PREFIJO_ARCHIVO = "para_pegar_en_la_sheet_";

// Qué solapa del xlsx va a qué solapa de la Sheet, y qué columnas de la Sheet
// tienen fórmula (no se escriben).
var SOLAPAS = [
  { xlsx: "Cuentas a Cobrar",   sheet: "Cuentas a Cobrar",   formulas: ["Saldo Pendiente", "Estado", "Dias de Atraso"] },
  { xlsx: "Cuentas a Pagar",    sheet: "Cuentas a Pagar",    formulas: ["Saldo Pendiente", "Estado", "Dias de Atraso"] },
  { xlsx: "Cartera de Cheques", sheet: "Cartera de Cheques", formulas: [] },
];

// Una fila se considera "de Tango / agregado" (y se borra antes de importar) si
// su columna Observaciones empieza o contiene alguno de estos textos.
var MARCAS_A_PISAR = ["Tango Live", "REVISAR:", "AGREGADO"];


function onOpen() {
  SpreadsheetApp.getUi().createMenu("finauto")
    .addItem("Importar Tango (último para_pegar)", "importarTango")
    .addToUi();
}


function importarTango() {
  var archivo = _ultimoParaPegar_();
  if (!archivo) throw new Error("No encontré ningún " + PREFIJO_ARCHIVO + "*.xlsx en " + CARPETA_RAIZ + "/" + CARPETA_TANGO);
  Logger.log("Importando " + archivo.getName() + " (" + archivo.getLastUpdated() + ")");

  // El xlsx se convierte a una Sheet temporal para poder leerlo; se borra al final.
  var temp = Drive.Files.copy({ title: "tmp_importar_tango", mimeType: MimeType.GOOGLE_SHEETS }, archivo.getId());
  var origen = SpreadsheetApp.openById(temp.id);
  var destino = SpreadsheetApp.getActiveSpreadsheet();
  var resumen = [];
  try {
    SOLAPAS.forEach(function (s) {
      var hOrigen = origen.getSheetByName(s.xlsx);
      var hDestino = destino.getSheetByName(s.sheet);
      if (!hOrigen || !hDestino) { resumen.push(s.sheet + ": falta la solapa (origen " + !!hOrigen + ", destino " + !!hDestino + ")"); return; }
      var r = _volcar_(hOrigen, hDestino, s.formulas);
      resumen.push(s.sheet + ": borradas " + r.borradas + " filas viejas, cargadas " + r.cargadas);
    });
  } finally {
    Drive.Files.remove(temp.id);
  }
  var msg = "Importado " + archivo.getName() + "\n" + resumen.join("\n");
  Logger.log(msg);
  // Un aviso que NO bloquea. (El 17/09 se uso alert(): espera que alguien apriete
  // "Aceptar" en la ventana del Cashflow; corriendo desde el editor nadie lo ve y a
  // los 6 minutos Google corta con "Exceeded maximum execution time", aunque el
  // trabajo ya estaba hecho.)
  try { destino.toast(resumen.join(" · "), "Importar Tango: listo", 20); } catch (e) { /* sin UI por disparador */ }
}


// ---- el archivo más nuevo que empiece con PREFIJO_ARCHIVO, buscando en las subcarpetas de Tango
function _ultimoParaPegar_() {
  var raiz = DriveApp.getFoldersByName(CARPETA_RAIZ);
  if (!raiz.hasNext()) return null;
  var tango = raiz.next().getFoldersByName(CARPETA_TANGO);
  if (!tango.hasNext()) return null;
  var mejor = null;
  var pila = [tango.next()];
  while (pila.length) {
    var carpeta = pila.pop();
    var archivos = carpeta.getFiles();
    while (archivos.hasNext()) {
      var f = archivos.next();
      if (f.getName().indexOf(PREFIJO_ARCHIVO) === 0 && (!mejor || f.getLastUpdated() > mejor.getLastUpdated())) mejor = f;
    }
    var sub = carpeta.getFolders();
    while (sub.hasNext()) pila.push(sub.next());
  }
  return mejor;
}


// ---- borra lo marcado, pega lo nuevo, respetando el orden de columnas de la Sheet.
// Todo se escribe por bloques (setValues por columna), no celda por celda: con 900
// filas, celda por celda tarda minutos y Apps Script corta a los 6.
function _volcar_(hOrigen, hDestino, formulas) {
  var encO = hOrigen.getRange(1, 1, 1, hOrigen.getLastColumn()).getValues()[0].map(String);
  var encD = hDestino.getRange(1, 1, 1, hDestino.getLastColumn()).getValues()[0].map(String);
  var colObs = encD.map(_n_).indexOf(_n_("Observaciones"));
  var colNombre = 1;   // columna B: Cliente / Proveedor / Tipo. Vacía = fila sin datos.

  // 1. Lo que hay hoy: se separa lo que se pisa de lo que cargó una persona.
  var viejas = hDestino.getLastRow() > 1
    ? hDestino.getRange(2, 1, hDestino.getLastRow() - 1, encD.length).getValues() : [];
  var vivas = [], borradas = 0;
  viejas.forEach(function (r) {
    if (String(r[colNombre] || "") === "") return;
    var obs = colObs >= 0 ? String(r[colObs] || "") : "";
    if (MARCAS_A_PISAR.some(function (m) { return obs.indexOf(m) !== -1; })) borradas++;
    else vivas.push(r);
  });

  // 2. Lo nuevo, reordenado a las columnas de la Sheet.
  var mapa = {}; encO.forEach(function (e, i) { mapa[_n_(e)] = i; });
  var nuevas = hOrigen.getLastRow() > 1
    ? hOrigen.getRange(2, 1, hOrigen.getLastRow() - 1, encO.length).getValues() : [];
  var cargadas = 0;
  var finales = vivas.slice();
  nuevas.forEach(function (r) {
    if (String(r[mapa[_n_(encD[colNombre])]] || "") === "") return;
    finales.push(encD.map(function (nombre) {
      var idx = mapa[_n_(nombre)];
      return idx === undefined ? "" : (r[idx] === null ? "" : r[idx]);
    }));
    cargadas++;
  });
  finales.forEach(function (r, i) { r[0] = i + 1; });   // ID de corrido

  // 3. Escribir columna por columna, salteando las de fórmula, y limpiar lo que sobra abajo.
  var total = finales.length, antes = viejas.length;
  for (var c = 0; c < encD.length; c++) {
    if (!encD[c] || formulas.indexOf(encD[c]) !== -1) continue;
    if (total > 0) hDestino.getRange(2, c + 1, total, 1).setValues(finales.map(function (r) { return [r[c]]; }));
    if (antes > total) hDestino.getRange(2 + total, c + 1, antes - total, 1).clearContent();
  }
  return { borradas: borradas, cargadas: cargadas };
}


function _n_(s) {
  return String(s || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/\s+/g, " ").trim();
}
