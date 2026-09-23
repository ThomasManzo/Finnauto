/**
 * Aviso diario del cash. Pegar en el mismo proyecto que importar_cashflow.gs.
 * Primero correr avisoDiarioPrueba; instalar recién después de revisar el texto.
 * Agregar al menú finauto existente estas tres líneas (acá no hay otro onOpen):
 * .addItem("Ver el aviso de hoy (sin mandar)", "avisoDiarioPrueba")
 * .addItem("Instalar aviso diario 07:30", "instalarAvisoDiario")
 * .addItem("Quitar aviso diario", "quitarAvisoDiario")
 * Google ejecuta cerca de las 07:30 (nearMinute tiene un margen de 15 minutos).
 * Para probar sin Google, _armarAviso_(ahora, datos) acepta una foto inventada:
 * { entradas: [], publicados: [], retenidos: [], registro: [], log: [],
 *   extracto: Date o null, errores: {} }. Archivos: {nombre, ruta, tipo, fecha}.
 * Registro: {fecha, tipo, estado, detalle}. Log: {fecha, texto}.
 * Con esa foto el armado es puro; con solo ahora, primero lee Google.
 */
var DESTINATARIOS = "finanzasnavar@gmail.com";
var AVISO_ZONA = "America/Argentina/Buenos_Aires";
var AVISO_DIA = 24 * 60 * 60 * 1000;

// Manda exactamente el texto que también permite revisar el botón de prueba.
function avisoDiario() {
  var aviso = _armarAviso_(new Date());
  MailApp.sendEmail(DESTINATARIOS, aviso.asunto, aviso.cuerpo);
}

// Muestra el aviso completo sin mandar ningún mail ni escribir en Registro.
function avisoDiarioPrueba() {
  var aviso = _armarAviso_(new Date());
  Logger.log(aviso.asunto + "\n\n" + aviso.cuerpo);
  // Desde el editor de Apps Script no hay ventana de la Sheet: ahí alcanza con el Logger.
  try { SpreadsheetApp.getUi().alert(aviso.asunto + "\n\n" + aviso.cuerpo); } catch (e) {}
}

// Deja un solo aviso diario para esta cuenta, con horario de Buenos Aires.
function instalarAvisoDiario() {
  _borrarDisparadoresAviso_();
  ScriptApp.newTrigger("avisoDiario").timeBased().atHour(7).nearMinute(30)
    .everyDays(1).inTimezone(AVISO_ZONA).create();
  _registrar_("sistema", "", "ok", "aviso diario instalado: cerca de las 07:30 de Buenos Aires");
}

// Quita solamente el aviso; la actualización horaria sigue funcionando.
function quitarAvisoDiario() {
  _borrarDisparadoresAviso_();
  _registrar_("sistema", "", "ok", "aviso diario quitado");
}

// Evita duplicar mails al instalar de nuevo, sin borrar otros disparadores.
function _borrarDisparadoresAviso_() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === "avisoDiario") ScriptApp.deleteTrigger(t);
  });
}

// Todas las fechas visibles usan Buenos Aires aunque la Sheet esté en otra zona.
function _fechaAviso_(fecha, formato) {
  return Utilities.formatDate(fecha, AVISO_ZONA, formato);
}

// Saca saltos de línea de nombres y errores para que no desarmen el mail.
function _textoAviso_(texto, limite) {
  var limpio = String(texto == null ? "" : texto).replace(/\s+/g, " ").trim();
  return limite && limpio.length > limite ? limpio.slice(0, limite - 3) + "..." : limpio;
}

// Mantiene cada sección corta, pero dice cuántos renglones quedaron afuera.
function _seccionAviso_(titulo, lineas) {
  var visibles = lineas.slice(0, 25);
  if (lineas.length > 25) visibles.push("... y " + (lineas.length - 25) + " más");
  return titulo + "\n" + (visibles.length ? visibles.join("\n") : "- nada nuevo");
}

// Reconoce los mismos prefijos que importa la Sheet, sin duplicar esa configuración.
function _tipoAviso_(nombre) {
  var tipos = Object.keys(IMPORTS);
  for (var i = 0; i < tipos.length; i++) {
    if (nombre.indexOf(IMPORTS[tipos[i]].prefijo) === 0) return tipos[i];
  }
  return "";
}

// Ignora carpetas viejas, ocultos y archivos auxiliares que no son datos de entrada.
function _ignorarAviso_(nombre) {
  return /^(\.|~\$)/.test(nombre) ||
    ["_para la Sheet", "Scripts", "Tablero", "_viejo", "Tango", "desktop.ini", "Thumbs.db"].indexOf(nombre) >= 0;
}

// Recorre con una pila, como el importador; conserva la ruta para ubicar cada archivo.
function _archivosAviso_(carpeta, ruta, tipo, recursivo) {
  var salida = [], pila = [{carpeta: carpeta, ruta: ruta}];
  while (pila.length) {
    var actual = pila.pop(), archivos = actual.carpeta.getFiles();
    while (archivos.hasNext()) {
      var f = archivos.next(), nombre = f.getName();
      if (_ignorarAviso_(nombre)) continue;
      salida.push({nombre: nombre, ruta: actual.ruta + "/" + nombre,
        tipo: tipo || _tipoAviso_(nombre), fecha: f.getLastUpdated()});
    }
    if (!recursivo) continue;
    var sub = actual.carpeta.getFolders();
    while (sub.hasNext()) {
      var c = sub.next();
      if (!_ignorarAviso_(c.getName())) pila.push({carpeta: c, ruta: actual.ruta + "/" + c.getName()});
    }
  }
  return salida;
}

// Lee cada parte por separado: si una falla, las demás igual llegan al mail.
function _leerDatosAviso_() {
  var datos = {entradas: [], publicados: [], retenidos: [], registro: [], log: [], extracto: null, errores: {}};
  var raiz, salida;
  // Guarda el problema junto a la sección que no se pudo leer.
  function leer(clave, trabajo) {
    try { trabajo(); } catch (e) { datos.errores[clave] = _textoAviso_(e && e.message || e, 160); }
  }
  leer("Drive", function () {
    var carpetas = DriveApp.getFoldersByName(CARPETA_RAIZ);
    if (!carpetas.hasNext()) throw new Error("No encontré " + CARPETA_RAIZ);
    raiz = carpetas.next();
    var mapa = {"Bancos": "bancos", "Cuentas a cobrar": "tango", "Cuentas a pagar": "tango",
      "Cheques": "tango", "Deuda bancaria": "deuda", "Impuestos": "impuestos",
      "Tesorería AA": "tesoreria_aa", "Tesoreria AA": "tesoreria_aa"};
    var sub = raiz.getFolders();
    while (sub.hasNext()) {
      var c = sub.next(), nombre = c.getName();
      if (mapa[nombre]) datos.entradas = datos.entradas.concat(_archivosAviso_(c, nombre, mapa[nombre], true)
        .filter(function (f) { return /\.(pdf|xlsx?|csv)$/i.test(f.nombre) && !/^(para_pegar|resumen_)/i.test(f.nombre); }));
    }
  });
  leer("Procesados", function () {
    if (!raiz) throw new Error("No pude abrir la carpeta de datos");
    var carpetas = raiz.getFoldersByName("_para la Sheet");
    if (!carpetas.hasNext()) throw new Error("Falta _para la Sheet");
    salida = carpetas.next();
    datos.publicados = _archivosAviso_(salida, "_para la Sheet", "", false)
      .filter(function (f) { return /^para_pegar_.*\.xlsx$/i.test(f.nombre); });
  });
  leer("Retenidos", function () {
    if (!salida) throw new Error("No pude abrir _para la Sheet");
    var carpetas = salida.getFoldersByName("_retenido");
    while (carpetas.hasNext()) datos.retenidos = datos.retenidos.concat(_archivosAviso_(carpetas.next(), "_retenido", "", true));
  });
  leer("Log", function () {
    if (!salida) throw new Error("No pude abrir _para la Sheet");
    var archivos = salida.getFilesByName("vigilante.log");
    if (!archivos.hasNext()) return; // La copia aparece recién cuando trabaja el vigilante.
    archivos.next().getBlob().getDataAsString("UTF-8").split(/\r?\n/).forEach(function (linea) {
      var marca = linea.match(/^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})/);
      if (marca && /FALLÓ|RETENIDO/.test(linea)) datos.log.push({
        fecha: Utilities.parseDate(marca[1], AVISO_ZONA, "yyyy-MM-dd HH:mm:ss"), texto: linea.slice(19).trim()});
    });
  });
  leer("Registro", function () {
    var h = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Registro");
    if (!h) throw new Error("Falta la solapa Registro");
    datos.registro = h.getDataRange().getValues().slice(1).filter(function (r) { return r[0] instanceof Date; })
      .map(function (r) { return {fecha: r[0], tipo: String(r[1]), estado: String(r[3]), detalle: r[4]}; });
  });
  leer("Extracto", function () {
    var h = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Saldos Bancarios");
    if (!h) throw new Error("Falta Saldos Bancarios");
    var filas = h.getDataRange().getValues(), enc = filas.shift().map(function (v) { return String(v).trim(); });
    var fecha = enc.indexOf("Fecha"), origen = enc.indexOf("Origen");
    if (fecha < 0 || origen < 0) throw new Error("Faltan las columnas Fecha u Origen");
    filas.forEach(function (r) {
      if (String(r[origen]).trim() === "Extracto" && r[fecha] instanceof Date &&
          (!datos.extracto || r[fecha] > datos.extracto)) datos.extracto = r[fecha];
    });
  });
  return datos;
}

// Arma el mismo resultado para prueba y envío. Una foto opcional permite probar sin Google.
function _armarAviso_(ahora, datos) {
  datos = datos || _leerDatosAviso_();
  var errores = datos.errores, alertas = [], encabezado = ["NAVAR cash · " + _fechaAviso_(ahora, "dd/MM/yyyy")];
  var desde = ahora.getTime() - AVISO_DIA;
  // La ventana incluye el comienzo y excluye fechas del futuro.
  function reciente(f) { return f.fecha.getTime() >= desde && f.fecha <= ahora; }
  // Ordena una copia para no cambiar la foto usada en las pruebas.
  function nuevos(lista) { return lista.slice().sort(function (a, b) { return b.fecha - a.fecha; }); }
  // Hace visible una lectura fallida también dentro de su propia sección.
  function problema(clave) { return "(no pude leer esto: " + errores[clave] + ")"; }
  Object.keys(errores).forEach(function (clave) {
    alertas.push(clave + ": " + problema(clave) + ". Pedir a finauto que revise el acceso y vuelva a probar el aviso.");
  });
  encabezado.push("Último extracto cargado: " + (errores.Extracto ? problema("Extracto") :
    datos.extracto ? _fechaAviso_(datos.extracto, "dd/MM/yyyy") : "sin datos"));
  var tango = nuevos(datos.publicados.filter(function (f) { return f.tipo === "tango" && f.fecha <= ahora; }))[0];
  var fechaTango = null;
  if (tango) {
    var marca = tango.nombre.match(/^para_pegar_en_la_sheet_(\d{4}-\d{2}-\d{2})/);
    if (marca) fechaTango = new Date(marca[1] + "T00:00:00-03:00");
  }
  encabezado.push("Último export de Tango: " + (errores.Procesados ? problema("Procesados") :
    fechaTango && !isNaN(fechaTango) ? _fechaAviso_(fechaTango, "dd/MM/yyyy") : "sin fecha disponible"));
  // La antigüedad se cuenta por días de calendario de Buenos Aires, no por la zona de la Sheet.
  function dias(fecha) {
    return Math.floor((Date.parse(_fechaAviso_(ahora, "yyyy-MM-dd")) - Date.parse(_fechaAviso_(fecha, "yyyy-MM-dd"))) / AVISO_DIA);
  }
  if (!errores.Extracto) {
    if (!datos.extracto) alertas.push("No hay extractos cargados. Pedir un extracto de banco y revisar la importación.");
    else if (dias(datos.extracto) > 7) alertas.push("Hace " + dias(datos.extracto) + " días que no llega un extracto de banco. Pedirlo.");
  }
  if (!errores.Procesados) {
    if (!fechaTango || isNaN(fechaTango)) alertas.push("No hay un export de Tango con fecha reconocible. Revisar el export y su nombre.");
    else if (dias(fechaTango) > 3) alertas.push("Hace " + dias(fechaTango) + " días que no llega un export de Tango. Pedir un export actualizado.");
  }
  // Mira también pendientes viejos: cumplir 24 horas no debe hacer desaparecer una traba.
  if (!errores.Drive && !errores.Procesados) datos.entradas.forEach(function (f) {
    if (ahora - f.fecha > 2 * 60 * 60 * 1000 && !datos.publicados.some(function (p) {
      return p.tipo === f.tipo && p.fecha > f.fecha && p.fecha <= ahora;
    })) alertas.push("El vigilante no procesó " + _textoAviso_(f.ruta) + ". Revisar que la notebook esté prendida y vigilante.log.");
  });
  if (!errores.Procesados && !errores.Registro) datos.publicados.forEach(function (f) {
    if (ahora - f.fecha > 2 * 60 * 60 * 1000 && !datos.registro.some(function (r) {
      return r.tipo === f.tipo && r.estado.toLowerCase() === "ok" && r.fecha > f.fecha && r.fecha <= ahora;
    })) alertas.push("La Sheet no importó " + _textoAviso_(f.nombre) + ". Abrir la Sheet → finauto → Importar lo nuevo ahora.");
  });
  var registros = nuevos(datos.registro.filter(reciente));
  registros.forEach(function (r) {
    if (r.estado.toUpperCase() === "ERROR") alertas.push("Falló la importación de " + _textoAviso_(r.tipo) + ": " +
      _textoAviso_(r.detalle, 120) + ". Revisar Registro y pedir a finauto que corrija el error antes de reintentar.");
  });
  var retenidos = nuevos(datos.retenidos.filter(reciente));
  retenidos.forEach(function (f) {
    alertas.push("El vigilante retuvo " + _textoAviso_(f.nombre) + " (una lista se achicó más de la mitad). Revisar el export antes de publicarlo.");
  });
  var lineasLog = nuevos(datos.log.filter(reciente)).slice(0, 5).map(function (r) {
    return _textoAviso_("- " + _fechaAviso_(r.fecha, "dd/MM HH:mm") + " " + r.texto, 160);
  });
  // Un fallo del lector también pide atención aunque todavía no hayan pasado dos horas.
  if (lineasLog.length) alertas.push("El log del vigilante registra fallos o retenciones. Revisar las líneas de abajo y el export antes de reintentar.");
  var entradas = nuevos(datos.entradas.filter(reciente)).map(function (f) {
    return "- " + _textoAviso_(f.ruta) + " (" + _fechaAviso_(f.fecha, "HH:mm") + ")";
  });
  if (errores.Drive) entradas.unshift(problema("Drive"));
  var procesados = nuevos(datos.publicados.filter(reciente)).map(function (f) {
    return "- " + (f.tipo || "tipo desconocido") + ": " + _textoAviso_(f.nombre) + " (" + _fechaAviso_(f.fecha, "HH:mm") + ")";
  });
  retenidos.forEach(function (f) { procesados.push("- RETENIDO: " + _textoAviso_(f.nombre) + " (" + _fechaAviso_(f.fecha, "HH:mm") + ")"); });
  ["Procesados", "Retenidos", "Log"].forEach(function (clave) { if (errores[clave]) procesados.unshift(problema(clave)); });
  // Las fallas van primero dentro de la sección, para que el tope no esconda el log.
  procesados = lineasLog.concat(procesados);
  var importados = registros.map(function (r) {
    return _textoAviso_("- " + _fechaAviso_(r.fecha, "HH:mm") + " " + r.tipo + " " + r.estado + " — " + r.detalle, 120);
  });
  if (errores.Registro) importados.unshift(problema("Registro"));
  return {
    asunto: "NAVAR cash · " + _fechaAviso_(ahora, "dd/MM") + " · " + (alertas.length ? "ATENCIÓN (" + alertas.length + ")" : "al día"),
    cuerpo: [encabezado.join("\n"), alertas.length ? _seccionAviso_("Alertas", alertas.map(function (a) { return "- " + a; })) :
      "Sin alertas: el cash está al día.", _seccionAviso_("Llegó a Drive (últimas 24 h)", entradas),
      _seccionAviso_("El vigilante procesó", procesados), _seccionAviso_("La Sheet importó", importados)].join("\n\n"),
    alertas: alertas
  };
}
