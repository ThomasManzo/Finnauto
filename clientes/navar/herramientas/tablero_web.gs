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
  // La API de Drive es la puerta para programas (la de "Descargar" de Sheets rechaza este acceso: 403).
  var url = "https://www.googleapis.com/drive/v3/files/" + ss.getId() +
    "/export?mimeType=" + encodeURIComponent("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
  var resp = UrlFetchApp.fetch(url, {headers: {Authorization: "Bearer " + ScriptApp.getOAuthToken()}, muteHttpExceptions: true});
  if (resp.getResponseCode() !== 200)
    throw new Error("Google no devolvió la copia de la Sheet (código " + resp.getResponseCode() + "): " +
      String(resp.getContentText()).replace(/\s+/g, " ").slice(0, 300));
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

// Compra de canchada: completar con el ID de la URL de la Sheet al instalar.
// No es una contraseña. Se abre por ID porque la aplicación web no tiene hoja activa.
var CANCHADA_PLANILLA_ID = "";
var PANEL_CC_SUPUESTOS = [
  // [clave, texto, formato, nota]
  ["precio",   "Precio de venta hoy ($/kg, sin IVA)",              "#,##0", "precio promedio reciente de la yerba vendida"],
  ["suba",     "Suba del precio de venta por mes",                 "0%",    "se aplica desde el primer mes"],
  ["mesesSuba","Durante cuántos meses sube el precio",             "0",     "1 = una sola suba; igual a la cantidad de meses = sube todos los meses"],
  ["dias",     "Días promedio de cobro",                           "0",     "ponderado por importe; corre la cobranza respecto de la venta"],
  ["pCanch",   "Canchada: precio ($/kg, sin IVA)",                 "#,##0", "precio promedio de compra"],
  ["flete",    "Canchada: flete ($/kg)",                           "#,##0", "se paga el mes de la compra"],
  ["tramo1", "Tramo 1: TN por mes", "#,##0.0", "primero se llena este tramo"],
  ["plazo1", "Tramo 1: plazo", "@", "elegir un nombre de la tabla de plazos"],
  ["tramo2", "Tramo 2: TN por mes", "#,##0.0", "se llena después del tramo 1"],
  ["plazo2", "Tramo 2: plazo", "@", "elegir un nombre de la tabla de plazos"],
  ["plazoResto", "El resto de la compra: plazo", "@", "lo que excede ambos tramos"],
  ["stock", "Stock de canchada propia hoy (TN)", "#,##0", "no se repone: no hay secadero"],
  ["blend", "Máximo de canchada propia en la mezcla (%)", "0%", "el resto necesita canchada comprada"],
  ["cobertura", "Meses de cobertura", "0", "meses de ventas que debe cubrir el stock total (1 a 12)"],
  ["lista", "Meses hasta que la canchada comprada está lista", "0", "0 = estacionada, lista para moler; máximo 8 meses"],
  ["compras", "Compras", "@", "automáticas o a mano"],
  ["secadero", "Gasto por mes del secadero y la hoja verde que deja de estar ($)", "#,##0", "se resta del promedio de gastos: el secadero no corre"],
  ["estampillas1", "Estampillas por paquete de 1 kg ($ sin IVA)", "#,##0.00", "gasto por paquete; se convierte a kilos según la mezcla"],
  ["estampillasMedio", "Estampillas por paquete de ½ kg ($ sin IVA)", "#,##0.00", "gasto por paquete; se convierte a kilos según la mezcla"],
  ["paquetes1", "Paquetes por paquete de 1 kg ($ sin IVA)", "#,##0.00", "gasto por paquete; se convierte a kilos según la mezcla"],
  ["paquetesMedio", "Paquetes por paquete de ½ kg ($ sin IVA)", "#,##0.00", "gasto por paquete; se convierte a kilos según la mezcla"],
  ["pallets1", "Pallets por paquete de 1 kg ($ sin IVA)", "#,##0.00", "gasto por paquete; se convierte a kilos según la mezcla"],
  ["palletsMedio", "Pallets por paquete de ½ kg ($ sin IVA)", "#,##0.00", "gasto por paquete; se convierte a kilos según la mezcla"],
  ["stretch1", "Stretch por paquete de 1 kg ($ sin IVA)", "#,##0.00", "gasto por paquete; se convierte a kilos según la mezcla"],
  ["stretchMedio", "Stretch por paquete de ½ kg ($ sin IVA)", "#,##0.00", "gasto por paquete; se convierte a kilos según la mezcla"],
  ["termo1", "Termocontraíble por paquete de 1 kg ($ sin IVA)", "#,##0.00", "gasto por paquete; se convierte a kilos según la mezcla"],
  ["termoMedio", "Termocontraíble por paquete de ½ kg ($ sin IVA)", "#,##0.00", "gasto por paquete; se convierte a kilos según la mezcla"],
  ["mezcla", "Mezcla de venta: % de kilos en paquetes de 1 kg", "0%", "el resto se vende en paquetes de ½ kg"],
  ["pagoEnvases", "Pago de los envases", "@", "contado o 30 días"],
  ["comision", "Comisión de los vendedores ($ por kg vendido)", "#,##0.00", "se paga en el mes de la venta"],
  ["estampillasBase", "Estampillas pagadas por mes en la base ($)", "#,##0", "se restan de la base para no contarlas dos veces"],
  ["kilosBase", "Kilos vendidos por mes en la base", "#,##0", "la base resta estos kilos por la comisión por kilo"],
  ["inicio",   "Primer mes del plan",                              "mmm yyyy", "primer día del mes"],
];

function _ccPermiso_() {
  var mail = (Session.getActiveUser().getEmail() || "").toLowerCase().trim();
  if (PERMITIDOS.indexOf(mail) < 0) throw new Error("Sin acceso al escenario");
}
function _ccHoja_() {
  if (!CANCHADA_PLANILLA_ID) throw new Error("Falta configurar CANCHADA_PLANILLA_ID al instalar el tablero");
  var h = SpreadsheetApp.openById(CANCHADA_PLANILLA_ID).getSheetByName("Cash compra canchada");
  if (!h) throw new Error("Primero armar la solapa Cash compra canchada");
  return h;
}
function _ccMapa_(h) {
  var valores = h.getDataRange().getValues(), mapa = Object.create(null);
  var tabla=valores.findIndex(function(r){return r[0]==="Plazos de canchada";});
  valores.forEach(function(r, i) { if(tabla>=0 && i>tabla && i<=tabla+10)return; if (r[0]) mapa[String(r[0])] = i + 1; });
  return {valores: valores, mapa: mapa};
}
function _ccFila_(m, texto) {
  if (!m.mapa[texto]) throw new Error("Falta el renglón: " + texto);
  return m.mapa[texto];
}
function _ccFecha_(v) {
  return v instanceof Date ? Utilities.formatDate(v, "America/Argentina/Buenos_Aires", "yyyy-MM-dd") : v;
}
function leerEscenarioCanchada() {
  _ccPermiso_();
  var m = _ccMapa_(_ccHoja_()), sup = {}, filas = {};
  PANEL_CC_SUPUESTOS.forEach(function(s) { sup[s[0]] = _ccFecha_(m.valores[_ccFila_(m, s[1])-1][1]); });
  m.valores.forEach(function(r,i) {
    var tabla=_ccFila_(m,"Plazos de canchada");if(i>=tabla && i<tabla+10)return;
    if (r[0]) filas[String(r[0])] = Array.from({length:14}, function(_,i) {
      return typeof r[i+1] === "number" && isFinite(r[i+1]) ? r[i+1] : null;
    });
  });
  var meses = m.valores[_ccFila_(m, "Mes")-1].slice(1,15).map(_ccFecha_);
  return {supuestos:sup, plazos:_ccPlazos_(m), avisosPlazos:m.valores.slice(_ccFila_(m,"Plazos de canchada"),_ccFila_(m,"Plazos de canchada")+10)
      .filter(function(r){return r[0]&&r[6]&&r[6]!=="OK";}).map(function(r){return r[0]+": "+r[6];}), meses:meses, filas:filas, hora:new Date().toISOString(),
    falta:String(m.valores[_ccFila_(m,"Faltan cargar")-1][1] || ""),
    notas:m.valores.filter(function(r){return /^(Qué no está:|La base de gastos|La deuda es)/.test(r[0]);}).map(function(r){return String(r[0]);})};
}
function _ccValidar_(c, restaurar) {
  if (!c || typeof c !== "object" || Array.isArray(c)) throw new Error("Cambios inválidos");
  var limites = {precio:[0,100000],suba:[0,.5],mesesSuba:[0,14],dias:[0,365],
    pCanch:[0,100000],flete:[0,10000],tramo1:[0,5000],tramo2:[0,5000],blend:[0,1],stock:[0,1000000],secadero:[0,100000000000],cobertura:[1,12],lista:[0,8]};
  var nuevos = ["estampillas1", "estampillasMedio", "paquetes1", "paquetesMedio", "pallets1", "palletsMedio", "stretch1", "stretchMedio", "termo1", "termoMedio", "comision", "estampillasBase", "kilosBase"];
  nuevos.forEach(function(k){limites[k]=[0,Number.MAX_VALUE];});limites.mezcla=[0,1];
  function numero(v, lim, entero) {
    if (restaurar && v === "") return;
    if (typeof v !== "number" || !isFinite(v) || v < lim[0] || v > lim[1] || (entero && Math.floor(v)!==v))
      throw new Error("Valor fuera de rango");
  }
  Object.keys(c).forEach(function(k) { if (["supuestos","tnVendidas","tnCompradas","plazos"].indexOf(k)<0) throw new Error("Cambio desconocido: " + k); });
  if(c.plazos!==undefined) {
    if(!Array.isArray(c.plazos)||c.plazos.length!==10) throw new Error("Se necesitan diez lugares de plazos");
    var nombres=[];
    c.plazos.forEach(function(r){
      if(!Array.isArray(r)||r.length!==6||typeof r[0]!=="string"||r[0].length>80) throw new Error("Tabla de plazos inválida");
      if(r[0] && (r[0]!==r[0].trim() || /^[=+@]/.test(r[0]) || nombres.indexOf(r[0])>=0)) throw new Error("Los plazos deben tener nombres únicos");
      if(r[0])nombres.push(r[0]);
      r.slice(1).forEach(function(v){if(v!=="")numero(v,[0,1],false);});
    });
  }
  if (c.supuestos !== undefined) {
    if (!c.supuestos || typeof c.supuestos!=="object" || Array.isArray(c.supuestos)) throw new Error("Supuestos inválidos");
    Object.keys(c.supuestos).forEach(function(k) {
      var v=c.supuestos[k];
      if(["plazo1","plazo2","plazoResto"].indexOf(k)>=0) {
        if(restaurar && v === "") return;
        if(typeof v!=="string" || !v.trim() || v.length>80) throw new Error("Plazo inválido");
      } else if(k === "compras") {
        if(restaurar && v === "") return;
        if(v!=="automáticas" && v!=="a mano") throw new Error("Compras inválidas: automáticas o a mano");
      } else if(k === "pagoEnvases") {
        if(restaurar && v === "") return;
        if(v!=="contado" && v!=="30 días") throw new Error("Pago de envases inválido: contado o 30 días");
      } else if(k === "inicio") {
        if(restaurar && v === "") return;
        if(typeof v !== "string" || !/^\d{4}-\d{2}-01$/.test(v) || !isFinite(new Date(v).getTime()) || new Date(v).toISOString().slice(0,10)!==v) throw new Error("Primer mes inválido");
      } else {
        if(!Object.prototype.hasOwnProperty.call(limites,k)) throw new Error("Supuesto desconocido");
        numero(v,limites[k],k==="mesesSuba" || k==="cobertura" || k==="lista");
      }
    });
  }
  ["tnVendidas","tnCompradas"].forEach(function(k){if(c[k]!==undefined){
    if(!Array.isArray(c[k]) || c[k].length!==14) throw new Error("Se necesitan 14 meses");
    for(var i=0;i<14;i++) numero(c[k][i],[0,5000],false);
  }});
}
function _ccFoto_(h) {
  var m=_ccMapa_(h), sup={};
  PANEL_CC_SUPUESTOS.forEach(function(s){sup[s[0]]=_ccFecha_(m.valores[_ccFila_(m,s[1])-1][1]);});
  return {supuestos:sup,plazos:_ccPlazos_(m),tnVendidas:m.valores[_ccFila_(m,"TN vendidas")-1].slice(1,15),
    tnCompradas:m.valores[_ccFila_(m,"TN compradas (a mano)")-1].slice(1,15)};
}
function _ccPlazos_(m) {
  var fila=_ccFila_(m,"Plazos de canchada");
  return m.valores.slice(fila,fila+10).map(function(r){return r.slice(0,6);});
}
function _ccEscribir_(h,c) {
  var m=_ccMapa_(h), escrituras=[];
  // Se comprueban todos los renglones antes de escribir: un texto faltante no deja media tanda guardada.
  PANEL_CC_SUPUESTOS.forEach(function(s){if(c.supuestos && Object.prototype.hasOwnProperty.call(c.supuestos,s[0])) {
    var v=c.supuestos[s[0]];
    if(s[0]==="inicio" && v!=="") v=Utilities.parseDate(v,"America/Argentina/Buenos_Aires","yyyy-MM-dd");
    escrituras.push([_ccFila_(m,s[1]),[v]]);
  }});
  [["tnVendidas","TN vendidas"],["tnCompradas","TN compradas (a mano)"]].forEach(function(p){if(c[p[0]]!==undefined) escrituras.push([_ccFila_(m,p[1]),c[p[0]]]);});
  var plazos=c.plazos||_ccPlazos_(m), disponibles=plazos.map(function(r){return r[0];});
  ["plazo1","plazo2","plazoResto"].forEach(function(k){
    var valor=c.supuestos&&Object.prototype.hasOwnProperty.call(c.supuestos,k)?c.supuestos[k]:m.valores[_ccFila_(m,PANEL_CC_SUPUESTOS.find(function(s){return s[0]===k;})[1])-1][1];
    if(valor!=="" && disponibles.indexOf(valor)<0)throw new Error("El plazo no está en la tabla: "+valor);
  });
  if(c.plazos)h.getRange(_ccFila_(m,"Plazos de canchada")+1,1,10,6).setValues(c.plazos);
  escrituras.forEach(function(p){h.getRange(p[0],2,1,p[1].length).setValues([p[1]]);});
}
// Cada foto ocupa una propiedad. Guardamos solo las filas necesarias para comparar, no toda
// la hoja: las propiedades de Google tienen un límite de tamaño por valor.
var PANEL_CC_PREFIJO="canchada_escenario_";
function _ccClaveEscenario_(nombre) {
  if(typeof nombre!=="string" || !nombre.trim() || nombre.trim().length>80)throw new Error("Escribí un nombre de hasta 80 caracteres");
  return PANEL_CC_PREFIJO+encodeURIComponent(nombre.trim());
}
function _ccResultadosFoto_(d) {
  var textos=["Resultado de la operación (antes de la deuda)","Resultado de la operación acumulado (sin deuda)",
    "Saldo del mes pagando la deuda que vence","Saldo acumulado",
    "Saldo disponible (acumulado + descubierto): si da negativo, eso es lo que falta financiar",
    "TN compradas (lo que se usa)","Compra de canchada del mes (valor sin flete)","Meses que cubre",
    "Precio de equilibrio de la operación ($/kg)","TN de equilibrio por mes","Margen por kg"];
  var filas={};textos.forEach(function(t){filas[t]=d.filas[t];});
  return {meses:d.meses,filas:filas};
}
// Las tarjetas resumen las filas ya calculadas: no se vuelven a calcular costos ni pagos.
function _ccTarjetasFoto_(entrada,resultados) {
  var f=resultados.filas,desde=0;
  (entrada.plazos||[]).forEach(function(r){if([entrada.supuestos.plazo1,entrada.supuestos.plazo2,entrada.supuestos.plazoResto].indexOf(r[0])>=0)r.slice(1).forEach(function(v,i){if(v>0)desde=Math.max(desde,i);});});
  function numeros(t){return (f[t]||[]).filter(function(v){return typeof v==="number"&&isFinite(v);});}
  function promedio(t){var ns=(f[t]||[]).slice(desde).filter(function(v){return typeof v==="number"&&isFinite(v);});return ns.length?ns.reduce(function(a,b){return a+b;},0)/ns.length:null;}
  function minimo(t){var ns=numeros(t);return ns.length?Math.min.apply(null,ns):null;}
  var disp=minimo("Saldo disponible (acumulado + descubierto): si da negativo, eso es lo que falta financiar");
  var primero=(f["Saldo disponible (acumulado + descubierto): si da negativo, eso es lo que falta financiar"]||[]).findIndex(function(v){return typeof v==="number"&&v<0;});
  return {"Se pasa del descubierto en":primero<0?null:resultados.meses[primero],"Resultado de un mes típico":promedio("Resultado de la operación (antes de la deuda)"),
    "Resultado típico con deuda":promedio("Saldo del mes pagando la deuda que vence"),
    "Acumulado de la operación":(f["Resultado de la operación acumulado (sin deuda)"]||[])[13]||0,
    "Peor mes":minimo("Resultado de la operación (antes de la deuda)"),
    "Meses en pérdida":numeros("Resultado de la operación (antes de la deuda)").filter(function(v){return v<0;}).length,
    "Peor saldo acumulado":minimo("Saldo acumulado"),"Plata que hay que conseguir":disp===null?null:Math.max(0,-disp),
    "Compra del primer mes":(f["Compra de canchada del mes (valor sin flete)"]||[])[0],
    "Cobertura mínima":minimo("Meses que cubre"),
    "Precio de equilibrio":promedio("Precio de equilibrio de la operación ($/kg)"),
    "TN de equilibrio":(f["Margen por kg"]||[]).slice(desde).some(function(v){return typeof v==="number"&&v<=0;})?null:promedio("TN de equilibrio por mes")};
}
function _ccListaEscenarios_(props) {
  var todas=props.getProperties();
  return Object.keys(todas).filter(function(k){return k.indexOf(PANEL_CC_PREFIJO)===0;}).map(function(k){return JSON.parse(todas[k]);});
}
function _ccGuardarFoto_(props,nombre,entrada,resultados) {
  var foto={nombre:nombre.trim(),fecha:new Date().toISOString(),entrada:entrada,resultados:resultados,tarjetas:_ccTarjetasFoto_(entrada,resultados)};
  var texto=JSON.stringify(foto);
  if(unescape(encodeURIComponent(texto)).length>9000)throw new Error("El escenario es demasiado grande para guardarlo; acortá los nombres de los plazos");
  props.setProperty(_ccClaveEscenario_(nombre),texto);
  return foto;
}
function _ccMigrarOriginal_(props,h) {
  var clave=_ccClaveEscenario_("Plan original"),viejo=props.getProperty("canchada_plan_original");
  if(!viejo)return;
  if(!props.getProperty(clave)) {
    if(_ccListaEscenarios_(props).length>=20)throw new Error("Hay 20 escenarios: liberar un lugar para migrar el Plan original");
    var entrada=JSON.parse(viejo),actual=_ccFoto_(h);
    if(entrada.supuestos && entrada.supuestos.partes!==undefined) {
      var n=Number(entrada.supuestos.partes)||1;
      if(n>5)throw new Error("El plan original tiene seis partes: revisar su migración antes de continuar");
      entrada.supuestos.plazoResto=n===1?"contado":Array.from({length:n},function(_,i){return i*30;}).join("/");
      entrada.supuestos.tramo1=entrada.supuestos.tramo2=0;delete entrada.supuestos.partes;
    }
    // Una foto vieja no tenía todos los campos: se completa con los actuales. Nunca se le
    // atribuyen los resultados del plan abierto: se recalcula la foto y luego se repone la hoja.
    entrada={supuestos:Object.assign({},actual.supuestos,entrada.supuestos),tnVendidas:entrada.tnVendidas,
      tnCompradas:entrada.tnCompradas,plazos:entrada.plazos||JSON.parse(JSON.stringify(actual.plazos))};
    var resto=entrada.supuestos.plazoResto;
    if(resto && !entrada.plazos.some(function(r){return r[0]===resto;})) {
      var cuotas=resto.split("/"),libre=entrada.plazos.findIndex(function(r){return !r[0];});
      if(libre>=0&&cuotas.length>=2&&cuotas.length<=5&&cuotas.every(function(v,i){return Number(v)===i*30;}))
        entrada.plazos[libre]=[resto].concat(Array.from({length:5},function(_,i){return i<cuotas.length?1/cuotas.length:0;}));
    }
    _ccValidar_(entrada,true);
    try {_ccEscribir_(h,entrada);SpreadsheetApp.flush();_ccGuardarFoto_(props,"Plan original",entrada,_ccResultadosFoto_(leerEscenarioCanchada()));}
    finally {_ccEscribir_(h,actual);SpreadsheetApp.flush();}
  }
  props.deleteProperty("canchada_plan_original");
}
function _ccConLock_(accion,c) {
  _ccPermiso_();
  if(accion==="guardar")_ccValidar_(c,false);
  var lock=LockService.getScriptLock();lock.waitLock(30000);
  try {
    var h=_ccHoja_(),props=PropertiesService.getScriptProperties();
    _ccMigrarOriginal_(props,h);
    if(accion==="listar")return _ccListaEscenarios_(props);
    if(accion==="guardar") {_ccEscribir_(h,c);SpreadsheetApp.flush();return leerEscenarioCanchada();}
    var nombre=c&&c.nombre,clave=_ccClaveEscenario_(nombre),existe=props.getProperty(clave);
    if(accion==="nombrar") {
      if(existe&&c.reemplazar!==true)return {confirmar:true,nombre:nombre.trim()};
      if(!existe&&_ccListaEscenarios_(props).length>=20)throw new Error("Ya hay 20 escenarios. Borrá uno antes de guardar otro.");
      SpreadsheetApp.flush();
      _ccGuardarFoto_(props,nombre,_ccFoto_(h),_ccResultadosFoto_(leerEscenarioCanchada()));
      return _ccListaEscenarios_(props);
    }
    if(!existe)throw new Error("Ese escenario ya no existe");
    if(accion==="borrar") {props.deleteProperty(clave);return _ccListaEscenarios_(props);}
    if(accion==="abrir") {
      var entrada=JSON.parse(existe).entrada;_ccValidar_(entrada,true);_ccEscribir_(h,entrada);SpreadsheetApp.flush();return leerEscenarioCanchada();
    }
    throw new Error("Acción desconocida");
  } finally {lock.releaseLock();}
}
function guardarEscenarioCanchada(cambios) {return _ccConLock_("guardar",cambios);}
function listarEscenariosCanchada() {return _ccConLock_("listar");}
function guardarEscenarioConNombreCanchada(pedido) {return _ccConLock_("nombrar",pedido);}
function abrirEscenarioCanchada(nombre) {return _ccConLock_("abrir",{nombre:nombre});}
function borrarEscenarioCanchada(nombre) {return _ccConLock_("borrar",{nombre:nombre});}
