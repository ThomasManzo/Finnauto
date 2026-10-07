/**
 * tablero_web.gs — el tablero de finauto como página web privada de Google.
 *
 * QUÉ HACE
 * --------
 * Sirve en una URL el último `finauto.html` que haya en la carpeta de Drive
 * "NAVAR - Datos / Tablero". El tablero lo calcula finauto (Python) y lo deja
 * ahí; este script NO calcula nada, solo lo muestra. Así hay un solo motor.
 *
 * QUIÉN LO VE
 * -----------
 * Solo las cuentas de Google de la lista PERMITIDOS. Cualquier otra ve "sin
 * acceso". Google se encarga de que la persona esté logueada; la lista se
 * encarga de que sea la correcta.
 *
 * CÓMO SE INSTALA (una vez, 5 minutos)
 * -------------------------------------
 *  1. Abrir la Sheet "NAVAR - Cash Flow" → Extensiones → Apps Script.
 *  2. Borrar lo que haya en Código.gs y pegar este archivo entero.
 *  3. Completar PERMITIDOS con los mails de NAVAR y el tuyo. Guardar (disquete).
 *  4. Implementar → Nueva implementación → tipo "Aplicación web":
 *       Ejecutar como: "Yo"  ·  Quién tiene acceso: "Cualquier usuario con cuenta de Google"
 *     → Implementar. Autorizar los permisos que pide (leer Drive).
 *  5. Copiar la URL que termina en /exec. Ese es el link del tablero. No cambia.
 *
 * CÓMO SE ACTUALIZA EL TABLERO
 * ----------------------------
 * Dejando un `finauto.html` nuevo en la carpeta. Nada más: la próxima vez que
 * alguien abra el link, ve el nuevo. (Al principio lo sube Thomas o Claude;
 * después lo sube sola la notebook de NAVAR con Drive para escritorio.)
 *
 * SI SE CAMBIA ESTE CÓDIGO
 * ------------------------
 * Implementar → Administrar implementaciones → lápiz → Versión: "Nueva versión"
 * → Implementar. Así la URL sigue siendo la misma.
 */

// ---- Quién puede ver el tablero. Minúsculas, sin espacios.
var PERMITIDOS = [
  "thomasezequielmanzo@gmail.com",
  // "persona@ejemplo.com",
  // "administracion@ejemplo.com",
];

// ---- Dónde está el tablero. Carpeta "Tablero" adentro de "NAVAR - Datos".
var CARPETA_RAIZ = "NAVAR - Datos";
var CARPETA_TABLERO = "Tablero";
var ARCHIVO = "finauto.html";

// ---- A partir de cuántas horas el tablero se considera viejo y se avisa.
var HORAS_VIEJO = 48;


function doGet() {
  var mail = (Session.getActiveUser().getEmail() || "").toLowerCase().trim();
  if (PERMITIDOS.indexOf(mail) === -1) {
    return HtmlService.createHtmlOutput(_pagina_(
      "Sin acceso",
      "Esta página es privada. Si tendrías que poder verla, avisale a Thomas con la cuenta con la que entraste" +
      (mail ? " (" + mail + ")" : "") + "."
    )).setTitle("NAVAR — sin acceso");
  }

  var archivo = _ultimoTablero_();
  if (!archivo) {
    return HtmlService.createHtmlOutput(_pagina_(
      "Todavía no hay tablero",
      "No encontré " + ARCHIVO + " en " + CARPETA_RAIZ + " / " + CARPETA_TABLERO + "."
    )).setTitle("NAVAR — tablero");
  }

  var html = archivo.getBlob().getDataAsString("UTF-8");
  var horas = (new Date() - archivo.getLastUpdated()) / 36e5;
  if (horas > HORAS_VIEJO) {
    // Una banda arriba: servir un tablero viejo sin decirlo es el peor modo de falla.
    var banda = '<div style="position:sticky;top:0;z-index:9999;background:#B3261E;color:#fff;' +
      'font:600 14px/1.4 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;padding:10px 16px;text-align:center">' +
      'Este tablero es del ' + Utilities.formatDate(archivo.getLastUpdated(), Session.getScriptTimeZone(), "dd/MM HH:mm") +
      ' (hace ' + Math.round(horas / 24) + ' días). Puede no reflejar la caja de hoy.</div>';
    html = html.replace(/<body([^>]*)>/i, "<body$1>" + banda);
  }

  return HtmlService.createHtmlOutput(html)
    .setTitle("NAVAR — tablero")
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL)
    .addMetaTag("viewport", "width=device-width, initial-scale=1");
}


/** El finauto.html más nuevo de la carpeta, o null. */
function _ultimoTablero_() {
  var raices = DriveApp.getFoldersByName(CARPETA_RAIZ);
  while (raices.hasNext()) {
    var sub = raices.next().getFoldersByName(CARPETA_TABLERO);
    while (sub.hasNext()) {
      var archivos = sub.next().getFilesByName(ARCHIVO);
      var mejor = null;
      while (archivos.hasNext()) {
        var f = archivos.next();
        if (!mejor || f.getLastUpdated() > mejor.getLastUpdated()) mejor = f;
      }
      if (mejor) return mejor;
    }
  }
  return null;
}


function _pagina_(titulo, texto) {
  return '<!doctype html><html lang="es"><head><meta charset="utf-8">' +
    '<meta name="viewport" content="width=device-width,initial-scale=1"></head>' +
    '<body style="margin:0;background:#F3F5F3;color:#16211C;font:16px/1.5 -apple-system,Segoe UI,Helvetica,Arial,sans-serif">' +
    '<div style="max-width:520px;margin:15vh auto;padding:0 20px"><h1 style="font-size:22px;margin:0 0 8px">' + titulo +
    '</h1><p style="color:#5E6C66;margin:0">' + texto + '</p></div></body></html>';
}


// ==================================================================================
// EL TABLERO SE REARMA SOLO (tarea 52, 07/10/2026)
// ----------------------------------------------------------------------------------
// El tablero lo arma la notebook con el programa de siempre (armar_tablero.py), a partir de una copia
// en Excel de la Sheet. Esta parte deja esa copia en "NAVAR - Datos / Tablero / fuente": la llama la
// importación horaria (importar_cashflow.gs) cada vez que entra algo nuevo, y también se puede correr
// desde el menú finauto. El vigilante de la notebook ve la copia y rearma finauto.html.
// Se guardan las últimas 3 copias (con fecha y hora en el nombre); las más viejas van a la papelera.
// La primera vez Google pide permiso para "conectarse a un servicio externo": es para bajar la copia
// de la propia Sheet.
var CARPETA_FUENTE = "fuente";
var COPIAS_FUENTE = 3;

function exportarParaTablero() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var url = "https://docs.google.com/spreadsheets/d/" + ss.getId() + "/export?format=xlsx";
  var resp = UrlFetchApp.fetch(url, {headers: {Authorization: "Bearer " + ScriptApp.getOAuthToken()}, muteHttpExceptions: true});
  if (resp.getResponseCode() !== 200) throw new Error("Google no devolvió la copia de la Sheet (código " + resp.getResponseCode() + ")");
  var carpeta = _carpetaFuente_();
  var nombre = "NAVAR - Cash Flow " + Utilities.formatDate(new Date(), "America/Argentina/Buenos_Aires", "yyyy-MM-dd HHmm") + ".xlsx";
  var nuevo = carpeta.createFile(resp.getBlob().setName(nombre));
  // Las más viejas a la papelera (no se borran del todo: se pueden recuperar).
  var copias = [], archivos = carpeta.getFiles();
  while (archivos.hasNext()) { var f = archivos.next(); if (/\.xlsx$/i.test(f.getName())) copias.push(f); }
  copias.sort(function (a, b) { return b.getDateCreated() - a.getDateCreated(); });
  copias.slice(COPIAS_FUENTE).forEach(function (f) { f.setTrashed(true); });
  return nuevo.getName();
}

// Desde el menú: deja la copia y avisa. La notebook rearma el tablero en su próxima pasada (≤ 15 min).
function rearmarTableroAhora() {
  var nombre = exportarParaTablero();
  try {
    SpreadsheetApp.getActiveSpreadsheet().toast("Copia lista (" + nombre + "). La notebook rearma el tablero en los próximos 15 minutos.", "finauto", 10);
  } catch (e) {}
}

function _carpetaFuente_() {
  var raices = DriveApp.getFoldersByName(CARPETA_RAIZ);
  if (!raices.hasNext()) throw new Error("No encontré la carpeta " + CARPETA_RAIZ);
  var raiz = raices.next();
  var tableros = raiz.getFoldersByName(CARPETA_TABLERO);
  var tablero = tableros.hasNext() ? tableros.next() : raiz.createFolder(CARPETA_TABLERO);
  var fuentes = tablero.getFoldersByName(CARPETA_FUENTE);
  return fuentes.hasNext() ? fuentes.next() : tablero.createFolder(CARPETA_FUENTE);
}
