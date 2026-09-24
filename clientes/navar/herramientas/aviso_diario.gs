/**
 * Aviso diario del cash. Pegar en el mismo proyecto que importar_cashflow.gs.
 * Primero correr avisoDiarioPrueba; instalar recién después de revisar el texto.
 * Agregar al menú finauto existente estas tres líneas (acá no hay otro onOpen):
 * .addItem("Ver el aviso de hoy (sin mandar)", "avisoDiarioPrueba")
 * .addItem("Instalar aviso diario 09:00", "instalarAvisoDiario")
 * .addItem("Quitar aviso diario", "quitarAvisoDiario")
 * Google ejecuta cerca de las 09:00 (nearMinute tiene un margen de 15 minutos).
 * Para probar sin Google, _armarAviso_(ahora, datos) acepta una foto inventada:
 * { entradas: [], publicados: [], retenidos: [], registro: [], log: [],
 *   ultimaPasada: Date o null, extracto: Date o null, saldos: [{banco, empresa, origen, fecha}], errores: {} }. Archivos: {nombre, ruta, tipo, fecha}.
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
  ScriptApp.newTrigger("avisoDiario").timeBased().atHour(9).nearMinute(0)
    .everyDays(1).inTimezone(AVISO_ZONA).create();
  _registrar_("sistema", "", "ok", "aviso diario instalado: cerca de las 09:00 de Buenos Aires");
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

// Origen trae «Extracto BANCO». El formato viejo sin banco sigue siendo válido.
function _esExtractoAviso_(origen) {
  return /^extracto/i.test(_textoAviso_(origen));
}

// El banco viene del extracto; sólo usamos Banco si el origen viejo no lo decía.
function _bancoExtractoAviso_(fila) {
  return _textoAviso_(fila.origen).replace(/^extracto/i, "").trim() || _textoAviso_(fila.banco);
}

// Mantiene cada sección corta, pero dice cuántos renglones quedaron afuera.
function _seccionAviso_(titulo, lineas) {
  var visibles = lineas.slice(0, 5);
  if (lineas.length > 5) visibles.push("... y " + (lineas.length - 5) + " más");
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
  var datos = {entradas: [], publicados: [], retenidos: [], registro: [], log: [], ultimaPasada: null, extracto: null, saldos: [], errores: {}};
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
  leer("Latido", function () {
    if (!salida) throw new Error("No pude abrir _para la Sheet");
    var archivos = salida.getFilesByName("vigilante_ultima_pasada.txt");
    if (!archivos.hasNext()) throw new Error("Falta la marca de vida");
    var texto = archivos.next().getBlob().getDataAsString("UTF-8").trim();
    if (archivos.hasNext()) throw new Error("Hay más de una marca de vida; revisar duplicados en Drive");
    // Se lee la fecha escrita por la notebook, no la hora en que Drive sincronizó.
    var fecha = new Date(texto);
    if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$/.test(texto) ||
        isNaN(fecha) || fecha.toISOString().slice(0, 19) !== texto.slice(0, 19))
      throw new Error("La marca de vida no tiene una fecha UTC válida");
    datos.ultimaPasada = fecha;
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
      .map(function (r) { return {fecha: r[0], tipo: _textoAviso_(r[1]).toLowerCase(), estado: _textoAviso_(r[3]), detalle: r[4]}; });
  });
  leer("Extracto", function () {
    var h = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Saldos Bancarios");
    if (!h) throw new Error("Falta Saldos Bancarios");
    var filas = h.getDataRange().getValues(), enc = filas.shift().map(function (v) { return String(v).trim(); });
    var fecha = enc.indexOf("Fecha"), origen = enc.indexOf("Origen");
    var banco = enc.indexOf("Banco"), empresa = enc.indexOf("Empresa");
    if ([fecha, origen, banco, empresa].some(function (i) { return i < 0; }))
      throw new Error("Faltan columnas Fecha, Origen, Banco o Empresa");
    filas.forEach(function (r) {
      datos.saldos.push({banco: r[banco], empresa: r[empresa], origen: r[origen], fecha: r[fecha]});
      if (_esExtractoAviso_(r[origen]) && _diaAviso_(r[fecha]) &&
          (!datos.extracto || r[fecha] > datos.extracto)) datos.extracto = r[fecha];
    });
  });
  return datos;
}

// Cuenta cierres locales, sin depender de la zona de la Sheet ni de la hora de envío.
function _diaAviso_(fecha) {
  return fecha instanceof Date && !isNaN(fecha) ? _fechaAviso_(fecha, "yyyy-MM-dd") : "";
}

// Lunes mira el viernes cerrado. No hay calendario de feriados: hábil = lunes a viernes.
function _habilAnteriorAviso_(dia) {
  var fecha = new Date(dia + "T12:00:00Z");
  do { fecha.setUTCDate(fecha.getUTCDate() - 1); } while ([0, 6].indexOf(fecha.getUTCDay()) >= 0);
  return fecha.toISOString().slice(0, 10);
}

// Una copia subida hoy de un export viejo no lo convierte en una foto de hoy.
function _fechaNombreAviso_(nombre) {
  var marca = nombre.match(/(?:^|[^0-9])(\d{4}-\d{2}-\d{2})(?=[^0-9]|$)/);
  if (!marca) return "";
  var fecha = new Date(marca[1] + "T12:00:00Z");
  return !isNaN(fecha) && fecha.toISOString().slice(0, 10) === marca[1] ? marca[1] : "";
}

// Una línea por fuente: no deja que un banco o la empresa A tapen lo que falta de otro.
function _faltantesAviso_(ahora, datos) {
  var hoy = _diaAviso_(ahora), cierre = _habilAnteriorAviso_(hoy), lineas = [];
  function mostrar(dia) { return dia.split("-").reverse().join("/"); }
  function pedir(nombre, ultima, requerida) {
    if (!ultima || ultima < requerida) lineas.push("- " + nombre + ": falta actualizar al " + mostrar(requerida) +
      (ultima ? "; última fecha disponible: " + mostrar(ultima) + "." : "; sin fecha disponible (no se puede determinar desde cuándo falta)."));
  }
  if (datos.errores.Extracto || !datos.saldos || !datos.saldos.length) {
    lineas.push("- Bancos y arqueo de caja AA: no se pudo verificar Saldos Bancarios; revisar la carga y el acceso.");
  } else {
    var bancos = {}, arqueo = "";
    datos.saldos.forEach(function (r) {
      var extracto = _esExtractoAviso_(r.origen);
      var banco = extracto ? _bancoExtractoAviso_(r) : _textoAviso_(r.banco), empresa = _textoAviso_(r.empresa).toUpperCase();
      var origen = _textoAviso_(r.origen).toLowerCase(), dia = _diaAviso_(r.fecha);
      var caja = /^(\(varios\)|varios|caja)$/i.test(banco);
      if (empresa === "AA" && caja && origen === "manual" && dia <= hoy && dia > arqueo) arqueo = dia;
      if (!banco || caja) return;
      var clave = banco.toLowerCase();
      if (!bancos[clave]) bancos[clave] = {nombre: banco, fecha: ""};
      if (extracto && dia <= hoy && dia > bancos[clave].fecha) bancos[clave].fecha = dia;
    });
    Object.keys(bancos).sort().forEach(function (clave) {
      var banco = bancos[clave], ultima = banco.fecha;
      if (ultima && ultima < cierre) {
        // La edad son días corridos; para pedir actualización manda el cierre hábil.
        var edad = Math.round((Date.parse(hoy) - Date.parse(ultima)) / AVISO_DIA);
        lineas.push("- Extracto de " + banco.nombre + ": el último extracto es del " + mostrar(ultima) +
          ", hace " + edad + (edad === 1 ? " día" : " días") + "; falta actualizar al " + mostrar(cierre) + ".");
      } else if (!ultima) pedir("Extracto de " + banco.nombre, ultima, cierre);
    });
    if (!Object.keys(bancos).length) lineas.push("- Extractos de banco: no hay bancos identificables en Saldos Bancarios; revisar la lista.");
    pedir("Arqueo de caja AA (carga manual)", arqueo, cierre);
  }
  if (datos.errores.Drive) {
    lineas.push("- Exports de Tango y tesorería AA: no se pudo verificar Drive; revisar el acceso.");
  } else {
    var fotos = {}, tesoreria = "";
    datos.entradas.forEach(function (f) {
      if (!(f.fecha instanceof Date) || f.fecha > ahora) return;
      var dia = _fechaNombreAviso_(f.nombre);
      if (!dia || dia > hoy) return;
      var nombre = f.nombre.toLowerCase().replace(/_/g, " ");
      var marca = nombre.match(/^(aa|a)\s+(cobranzas?|pagos?|cheques?)\b/);
      if (f.tipo === "tango" && marca) {
        var lista = /^cobranza/.test(marca[2]) ? "cobranzas" : /^pago/.test(marca[2]) ? "pagos" : "cheques";
        var clave = marca[1].toUpperCase() + " " + lista;
        if (!fotos[clave] || dia > fotos[clave]) fotos[clave] = dia;
      }
      if (f.tipo === "tesoreria_aa" && /^aa\s/.test(nombre) && dia > tesoreria) tesoreria = dia;
    });
    ["A", "AA"].forEach(function (empresa) {
      ["cobranzas", "pagos", "cheques"].forEach(function (lista) {
        pedir("Tango " + empresa + " — " + lista, fotos[empresa + " " + lista], hoy);
      });
    });
    pedir("Tesorería AA (subida manual)", tesoreria, hoy);
  }
  return lineas;
}

// Arma el mismo resultado para prueba y envío. Una foto opcional permite probar sin Google.
function _armarAviso_(ahora, datos) {
  datos = datos || _leerDatosAviso_();
  var errores = datos.errores, alertas = [], encabezado = ["NAVAR cash · " + _fechaAviso_(ahora, "dd/MM/yyyy")];
  // La señal de vida va antes de cualquier otra alerta; no certifica que los lectores salieron bien.
  var pasada = datos.ultimaPasada, alertaVida = "";
  if (errores.Latido || !(pasada instanceof Date) || isNaN(pasada)) {
    alertaVida = "No se pudo verificar si la notebook está procesando: " +
      (errores.Latido || "sin marca de vida") + ". Revisar el vigilante y la sincronización de Drive.";
  } else if (pasada > ahora) {
    alertaVida = "La marca de vida está en el futuro. Revisar el reloj de la notebook; no se puede confirmar la última pasada.";
  } else {
    var diaPasada = _diaAviso_(pasada), hoyVida = _diaAviso_(ahora);
    var ayerVida = new Date(hoyVida + "T12:00:00Z");
    ayerVida.setUTCDate(ayerVida.getUTCDate() - 1);
    var cuando = diaPasada === hoyVida ? "de hoy" :
      diaPasada === ayerVida.toISOString().slice(0, 10) ? "de ayer" : "del " + _fechaAviso_(pasada, "dd/MM/yyyy");
    var ultima = "última pasada a las " + _fechaAviso_(pasada, "HH:mm") + " " + cuando;
    if (ahora - pasada > 60 * 60 * 1000) {
      alertaVida = "La notebook no está procesando: " + ultima +
        ". Revisar que esté prendida y que la tarea programada corra. Revisar también la sincronización de Drive.";
    } else encabezado.push("Vigilante: " + ultima + ". Es señal de vida, no de procesamiento correcto.");
  }
  if (alertaVida) alertas.push(alertaVida);
  // Desde el cierre anterior (medianoche posterior), no desde las 9 de ayer.
  // Un lunes arranca el sábado a las 00:00: el último día hábil cerrado fue el viernes.
  // Bancos/arqueo deben cubrir ese cierre; los exports deben ser fotos de hoy.
  var cierre = _habilAnteriorAviso_(_diaAviso_(ahora));
  var desde = new Date(cierre + "T00:00:00-03:00").getTime() + AVISO_DIA;
  var faltantes = _faltantesAviso_(ahora, datos);
  // La ventana incluye el comienzo y excluye fechas del futuro.
  function reciente(f) { return f.fecha.getTime() >= desde && f.fecha <= ahora; }
  // Ordena una copia para no cambiar la foto usada en las pruebas.
  function nuevos(lista) { return lista.slice().sort(function (a, b) { return b.fecha - a.fecha; }); }
  // Hace visible una lectura fallida también dentro de su propia sección.
  function problema(clave) { return "(no pude leer esto: " + errores[clave] + ")"; }
  Object.keys(errores).forEach(function (clave) {
    if (clave === "Latido") return; // Ya quedó primero, sin repetir el mismo problema.
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
      return r.tipo === f.tipo && _textoAviso_(r.estado).toLowerCase() === "ok" && r.fecha > f.fecha && r.fecha <= ahora;
    })) alertas.push("La Sheet no importó " + _textoAviso_(f.nombre) + ". Abrir la Sheet → finauto → Importar lo nuevo ahora.");
  });
  var registros = nuevos(datos.registro.filter(reciente));
  registros.forEach(function (r) {
    if (String(r.detalle).indexOf("VERIFICACION_NO_CUADRA") !== -1) alertas.push(
      "La escritura de " + _textoAviso_(r.tipo) + " terminó pero NO CUADRÓ al releerla. No usar el cash hasta revisar Registro y reimportar con finauto.");
    if (_textoAviso_(r.estado).toUpperCase() === "ERROR") alertas.push("Falló la importación de " + _textoAviso_(r.tipo) + ": " +
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
    asunto: "NAVAR cash · " + _fechaAviso_(ahora, "dd/MM") + " · " + ((alertas.length + faltantes.length) ? "ATENCIÓN (" + (alertas.length + faltantes.length) + ")" : "al día"),
    cuerpo: (alertaVida ? ["Estado del vigilante\n" + alertaVida] : []).concat(["Qué falta subir hoy\n" + (faltantes.length ? faltantes.join("\n") : "Está todo subido al día de hoy."), encabezado.join("\n"), alertas.length ? _seccionAviso_("Alertas", alertas.map(function (a) { return "- " + a; })) :
      "Sin alertas del circuito.", _seccionAviso_("Llegó a Drive (desde el cierre anterior)", entradas),
      _seccionAviso_("El vigilante procesó", procesados), _seccionAviso_("La Sheet importó", importados)]).join("\n\n"),
    alertas: alertas, faltantes: faltantes
  };
}
