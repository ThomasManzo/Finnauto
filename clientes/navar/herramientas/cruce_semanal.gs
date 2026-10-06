/**
 * cruce_semanal.gs — el mail de los miércoles con el cruce banco ↔ Tango, para la administración.
 * Va en el mismo proyecto de Apps Script que importar_cashflow.gs (usa CARPETA_RAIZ y _registrar_).
 *
 * PARA QUÉ
 *   La administración no tiene acceso a los bancos y carga los débitos cuando llegan los resúmenes.
 *   Los miércoles a las 08:30 la notebook corre lector/cruce_semanal.py, que deja en
 *   "NAVAR - Datos/Cruce" un Excel ("Cruce banco-Tango <fecha>.xlsx") y un cruce_semanal_<fecha>.json.
 *   Este script lee ese .json, arma el mail y lo manda con el Excel adjunto.
 *
 * A QUIÉN
 *   Propiedades del script (Configuración del proyecto → Propiedades de la secuencia de comandos):
 *     DESTINATARIOS_CRUCE  los mails que reciben el cruce, separados por coma.
 *     DESTINATARIOS_FALLA  a quién avisar si el cruce no corrió o no cerró (Thomas). Si falta, se usa
 *                          DESTINATARIOS_CRUCE.
 *   Los mails NO van en el código (el repo es público).
 *
 * SI ALGO NO ANDA
 *   Si no hay .json de hoy (la notebook estaba apagada, falló el cruce) o la cuenta de control del
 *   cruce no dio, NO se manda nada a la administración: va un aviso solo a DESTINATARIOS_FALLA.
 *
 * MENÚ (en onOpen de importar_cashflow.gs)
 *   Ver el cruce semanal (sin mandar) · Instalar cruce semanal (miércoles 09:30) · Quitar cruce semanal.
 *
 * PARA PROBAR SIN GOOGLE (lector/pruebas/probar_cruce_semanal.cjs)
 *   _armarCruceSemanal_(datos) y _decidirCruceSemanal_(datos, hoy) no tocan Google.
 */

var CRUCE_ZONA = "America/Argentina/Buenos_Aires";
var CRUCE_CARPETA = "Cruce";


// ---------------------------------------------------------------- lo que corre el disparador y el menú

// Miércoles 09:30: manda el mail del cruce de hoy (o avisa la falla).
function cruceSemanal() {
  _mandarCruceSemanal_(new Date());
}

// Muestra el mail de hoy sin mandarlo (usa el último .json que haya, aunque no sea de hoy).
function cruceSemanalPrueba() {
  var leido = _leerCruceSemanal_(null);
  var texto;
  if (!leido) {
    texto = "Todavía no hay ningún cruce semanal en '" + CARPETA_RAIZ + "/" + CRUCE_CARPETA + "'.";
  } else {
    var r = _armarCruceSemanal_(leido.datos);
    var d = _decidirCruceSemanal_(leido.datos, _hoyCruce_(new Date()));
    texto = (d.mandar ? "" : "OJO: el miércoles esto NO se mandaría a la administración (" + d.motivo + ").\n\n") +
      "Para: " + _propiedadCruce_("DESTINATARIOS_CRUCE") + "\nAdjunto: " + leido.datos.archivo +
      "\n\n" + r.asunto + "\n\n" + r.cuerpo;
  }
  Logger.log(texto);
  try { SpreadsheetApp.getUi().alert(texto); } catch (e) {}
}

// Un solo disparador: los miércoles entre las 09:15 y las 09:45 de Buenos Aires (nearMinute ±15 min).
function instalarCruceSemanal() {
  if (!_propiedadCruce_("DESTINATARIOS_CRUCE")) {
    throw new Error("Falta la propiedad DESTINATARIOS_CRUCE en Configuración del proyecto; no se instaló.");
  }
  _borrarDisparadoresCruce_();
  ScriptApp.newTrigger("cruceSemanal").timeBased().onWeekDay(ScriptApp.WeekDay.WEDNESDAY)
    .atHour(9).nearMinute(30).inTimezone(CRUCE_ZONA).create();
  _registrar_("sistema", "", "ok", "cruce semanal instalado: miércoles 09:15–09:45 de Buenos Aires");
}

function quitarCruceSemanal() {
  _borrarDisparadoresCruce_();
  _registrar_("sistema", "", "ok", "cruce semanal quitado");
}

function _borrarDisparadoresCruce_() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === "cruceSemanal") ScriptApp.deleteTrigger(t);
  });
}

function _mandarCruceSemanal_(ahora) {
  var hoy = _hoyCruce_(ahora);
  var falla = _propiedadCruce_("DESTINATARIOS_FALLA") || _propiedadCruce_("DESTINATARIOS_CRUCE");
  try {
    var leido = _leerCruceSemanal_(hoy);
    var d = _decidirCruceSemanal_(leido && leido.datos, hoy);
    if (!d.mandar) {
      MailApp.sendEmail(falla, "Cruce banco-Tango: no se mandó el de hoy",
        "El cruce semanal de hoy no se mandó a la administración: " + d.motivo + ".\n\n" +
        "Revisar en la notebook el log clientes\\navar\\privado\\cruce_semanal.log.");
      _registrar_("cruce_semanal", "", "ERROR", "no se mandó: " + d.motivo);
      return null;
    }
    var destinatarios = _propiedadCruce_("DESTINATARIOS_CRUCE");
    if (!destinatarios) throw new Error("Falta la propiedad DESTINATARIOS_CRUCE en Configuración del proyecto.");
    var r = _armarCruceSemanal_(leido.datos);
    MailApp.sendEmail(destinatarios, r.asunto, r.cuerpo, leido.excel ? {attachments: [leido.excel.getBlob()]} : {});
    _registrar_("cruce_semanal", leido.datos.archivo, "ok", "mandado: " + leido.datos.falta_total.cantidad +
      " para cargar en Tango" + (leido.excel ? "" : "; SIN Excel adjunto (no se encontró)"));
    return r;
  } catch (e) {
    _registrar_("cruce_semanal", "", "ERROR", String(e && e.message || e).slice(0, 300));
    throw e;
  }
}


// ---------------------------------------------------------------- Drive

// El .json del cruce de `hoy` (aaaa-mm-dd), o el más nuevo si hoy es null. Devuelve {datos, excel}.
function _leerCruceSemanal_(hoy) {
  var raiz = DriveApp.getFoldersByName(CARPETA_RAIZ);
  if (!raiz.hasNext()) throw new Error("No encontré " + CARPETA_RAIZ);
  var carpetas = raiz.next().getFoldersByName(CRUCE_CARPETA);
  if (!carpetas.hasNext()) return null;
  var carpeta = carpetas.next(), elegido = null;
  var archivos = carpeta.getFiles();
  while (archivos.hasNext()) {
    var f = archivos.next(), m = f.getName().match(/^cruce_semanal_(\d{4}-\d{2}-\d{2})\.json$/);
    if (!m || (hoy && m[1] !== hoy)) continue;
    if (!elegido || m[1] > elegido.fecha) elegido = {fecha: m[1], archivo: f};
  }
  if (!elegido) return null;
  var datos = JSON.parse(elegido.archivo.getBlob().getDataAsString("UTF-8"));
  var excel = carpeta.getFilesByName(datos.archivo);
  return {datos: datos, excel: excel.hasNext() ? excel.next() : null};
}


// ---------------------------------------------------------------- armar el mail (sin Google)

// ¿Se manda a la administración? Solo si el cruce es de hoy y su cuenta de control dio.
function _decidirCruceSemanal_(datos, hoy) {
  if (!datos) return {mandar: false, motivo: "no hay cruce de hoy en la carpeta " + CRUCE_CARPETA + " (¿corrió la notebook a las 08:30?)"};
  if (datos.fecha !== hoy) return {mandar: false, motivo: "el último cruce es del " + _ddmmCruce_(datos.fecha) + ", no de hoy"};
  if (!datos.control_ok) return {mandar: false, motivo: "la cuenta de control del cruce no dio (el informe estaría mal)"};
  return {mandar: true, motivo: ""};
}

function _armarCruceSemanal_(datos) {
  var L = [];
  var falta = datos.falta_total || {cantidad: 0, importe: 0};
  var asunto = "Cruce banco-Tango · " + _ddmmCruce_(datos.fecha) + " · " +
    (falta.cantidad ? falta.cantidad + (falta.cantidad === 1 ? " movimiento" : " movimientos") + " para cargar en Tango"
                    : "nada pendiente de cargar");
  L.push("Hola:");
  L.push("");
  L.push("Este es el cruce semanal entre los extractos de los bancos y la tesorería de Tango (empresa A), " +
    "con " + datos.meses[0] + " y " + datos.meses[1] + ". El detalle completo, para buscar cada movimiento, " +
    "está en el Excel adjunto.");
  if (datos.aviso) { L.push(""); L.push("OJO: " + datos.aviso + "."); }

  L.push(""); L.push("1. CÓMO ESTÁ CADA BANCO"); L.push("");
  (datos.bancos || []).forEach(function (b) {
    var partes = [];
    if (b.extracto_hasta) {
      partes.push("extracto hasta el " + _ddmmCruce_(b.extracto_hasta) +
        (b.dias_sin_extracto > 7 ? " (sin extracto nuevo hace " + b.dias_sin_extracto + " días)" : ""));
    } else {
      partes.push("sin extracto");
    }
    datos.meses.forEach(function (mes, i) {
      var v = b.conciliado[i];
      if (v !== null && v !== undefined) partes.push(mes + " " + Math.round(v * 100) + " % conciliado");
    });
    L.push("  · " + b.cuenta + ": " + partes.join(" · "));
  });
  L.push("  (El mes en curso concilia poco hasta que se cargan los débitos de fin de mes: es normal.)");

  L.push(""); L.push("2. EN EL BANCO Y TODAVÍA NO ESTÁ EN TANGO (de hace más de " + datos.dias + " días)"); L.push("");
  if (!falta.cantidad) {
    L.push("  Nada pendiente.");
  } else {
    L.push("  " + falta.cantidad + " movimientos por " + _plataCruce_(falta.importe) + " en total. " +
      (falta.cantidad > datos.falta.length ? "Los " + datos.falta.length + " más grandes:" : "Son estos:"));
    datos.falta.forEach(function (f) {
      L.push("  · " + _ddmmCruce_(f.fecha) + " · " + f.banco + " · " + f.concepto + " · " + _plataCruce_(f.importe));
    });
  }
  if (datos.gastos && datos.gastos.length) {
    L.push("");
    L.push("  Además, gastos e impuestos bancarios (comisiones, impuesto al débito y crédito, percepciones) sin cargar:");
    datos.gastos.forEach(function (g) {
      L.push("  · " + g.banco + ": " + g.cantidad + " renglones, " + _plataCruce_(g.importe));
    });
  }

  L.push(""); L.push("3. POSIBLES ERRORES DE CARGA"); L.push("");
  if (!datos.errores || !datos.errores.length) L.push("  No encontramos.");
  (datos.errores || []).forEach(function (e) { L.push("  · " + e); });

  L.push("");
  L.push("Si algo de esto ya está cargado o no corresponde, respondan este mail y lo revisamos.");
  L.push("");
  L.push("(Mail automático de finauto: el cruce corre los miércoles a la mañana con los extractos disponibles.)");
  return {asunto: asunto, cuerpo: L.join("\n")};
}


// ---------------------------------------------------------------- ayudas

function _propiedadCruce_(nombre) {
  return (typeof PropertiesService !== "undefined" && PropertiesService.getScriptProperties().getProperty(nombre)) || "";
}

function _hoyCruce_(ahora) {
  return Utilities.formatDate(ahora, CRUCE_ZONA, "yyyy-MM-dd");
}

function _ddmmCruce_(iso) {
  return iso ? iso.slice(8, 10) + "/" + iso.slice(5, 7) : "";
}

// 1234567.5 → "$1.234.567,50"; negativos con "-" adelante.
function _plataCruce_(v) {
  var n = Math.abs(Number(v) || 0), entero = Math.floor(n), cent = Math.round((n - entero) * 100);
  if (cent === 100) { entero += 1; cent = 0; }
  var miles = String(entero).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return (Number(v) < 0 ? "-$" : "$") + miles + "," + (cent < 10 ? "0" : "") + cent;
}
