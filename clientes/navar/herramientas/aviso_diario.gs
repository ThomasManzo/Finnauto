/**
 * Aviso diario del cash. Pegar en el mismo proyecto que importar_cashflow.gs.
 * Primero correr avisoDiarioPrueba; instalar recién después de revisar el texto.
 * Agregar al menú finauto existente estas tres líneas (acá no hay otro onOpen):
 * .addItem("Ver el aviso de hoy (sin mandar)", "avisoDiarioPrueba")
 * .addItem("Instalar aviso diario 07:30", "instalarAvisoDiario")
 * .addItem("Quitar aviso diario", "quitarAvisoDiario")
 * Google ejecuta cerca de las 07:30: entre 07:15 y 07:45 (nearMinute tiene ±15 min).
 * Para probar sin Google, _armarAviso_(ahora, datos) acepta una foto inventada:
 * { entradas: [], publicados: [], retenidos: [], registro: [], log: [],
 *   ultimaPasada: Date o null, tangoParte: {...}, galiciaParte: {...}, extracto: Date o null,
 *   saldos: [{banco, empresa, origen, fecha}], errores: {} }. Archivos: {nombre, ruta, tipo, fecha}.
 * Registro: {fecha, tipo, estado, detalle}. Log: {fecha, texto}.
 * Con esa foto el armado es puro; con solo ahora, primero lee Google.
 */
var DESTINATARIOS = "finanzasnavar@gmail.com,charlesapettit@gmail.com,apriscillaharrison@gmail.com,maria.vazquez1613@gmail.com";
var AVISO_ZONA = "America/Argentina/Buenos_Aires";
var AVISO_DIA = 24 * 60 * 60 * 1000;
// Tiene que coincidir con TOTAL_BAJADAS_DIARIAS de ingestas/tango_live.py.
var TANGO_BAJADAS = 9;
// Estas fuentes ya llegan solas. Al automatizar otro banco, se lo agrega acá para
// que el aviso deje de pedir una carga manual y pase a revisar la notebook.
var FUENTES_AUTOMATICAS = ["tango", "tesoreria_aa", "galicia"];

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
  _registrar_("sistema", "", "ok", "aviso diario instalado: cerca de las 07:30 de Buenos Aires (07:15–07:45)");
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

// Saca del resumen del lector de bancos los archivos que no pudo leer. El renglón es
// "- no pude leer corrientes/<archivo>: ValueError: <motivo>"; el nombre técnico del error no va al mail.
function _ilegiblesAviso_(texto) {
  return String(texto || "").split(/\r?\n/).map(function (linea) {
    var m = linea.match(/^- no pude leer ([^\/\\]+)[\/\\](.+?): (?:[A-Za-z]+Error: )?(.*)$/);
    return m ? {banco: m[1].toLowerCase(), archivo: m[2], motivo: m[3].trim()} : null;
  }).filter(Boolean);
}

// Interpreta el parte mínimo que deja la bajada de Tango en Drive.
function _parteTangoAviso_(texto) {
  var lineas = String(texto || "").trim().split(/\r?\n/);
  if (lineas.length < 2) throw new Error("El parte de Tango está incompleto");
  var fecha = new Date(lineas[0]), conteo = lineas[1].match(/^(\d+) de (\d+)$/);
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$/.test(lineas[0]) || isNaN(fecha))
    throw new Error("El parte de Tango no tiene una fecha UTC válida");
  if (!conteo || Number(conteo[1]) > Number(conteo[2]))
    throw new Error("El parte de Tango no tiene un conteo válido");
  return {fecha: fecha, ok: Number(conteo[1]), total: Number(conteo[2]),
    fallas: lineas.slice(2).filter(Boolean).map(function (l) { return _textoAviso_(l, 220); })};
}

// El archivo de Galicia es para personas; acá tomamos sólo la hora y el bloque de atención.
function _parteGaliciaAviso_(texto) {
  var lineas = String(texto || "").split(/\r?\n/), cabecera = lineas[0] || "";
  var marca = cabecera.match(/^Bot Galicia - (\d{2}\/\d{2}\/\d{4} \d{2}:\d{2})$/i);
  if (!marca) throw new Error("El estado de Galicia no tiene fecha y hora válidas");
  var fecha = Utilities.parseDate(marca[1], AVISO_ZONA, "dd/MM/yyyy HH:mm");
  if (!(fecha instanceof Date) || isNaN(fecha))
    throw new Error("El estado de Galicia no tiene fecha y hora válidas");
  var indice = lineas.findIndex(function (l) { return />>>\s*ATENCI[OÓ]N/i.test(l); });
  var detalles = [];
  if (indice >= 0) {
    for (var i = indice; i < lineas.length && !/^Bajadas OK/i.test(lineas[i]); i++) {
      if (_textoAviso_(lineas[i])) detalles.push(_textoAviso_(lineas[i].replace(/^>>>\s*/, ""), 180));
    }
  }
  return {fecha: fecha, ok: indice < 0, detalle: detalles.join(" · ")};
}

// Origen trae «Extracto BANCO». El formato viejo sin banco sigue siendo válido.
function _esExtractoAviso_(origen) {
  return /^extracto/i.test(_textoAviso_(origen));
}

// El banco viene del extracto; sólo usamos Banco si el origen viejo no lo decía.
function _bancoExtractoAviso_(fila) {
  return _textoAviso_(fila.origen).replace(/^extracto/i, "").trim() || _textoAviso_(fila.banco);
}

// Sólo cambia la presentación: las claves internas y las rutas siguen iguales.
function _nombreBancoAviso_(nombre) {
  var clave = _textoAviso_(nombre).toLowerCase();
  var conocidos = {galicia: "Galicia", nacion: "Nación", corrientes: "Corrientes",
    macro: "Macro", bbva: "BBVA"};
  return conocidos[clave] || clave.charAt(0).toUpperCase() + clave.slice(1);
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
function _leerDatosAviso_(ahora) {
  ahora = ahora || new Date();
  var datos = {entradas: [], publicados: [], retenidos: [], registro: [], log: [], ilegibles: [],
    ultimaPasada: null, tangoParte: null, galiciaParte: null, extracto: null, saldos: [], errores: {}};
  var raiz, salida;
  // Guarda el problema junto a la sección que no se pudo leer.
  function leer(clave, trabajo) {
    try { trabajo(); } catch (e) { datos.errores[clave] = _textoAviso_(e && e.message || e, 160); }
  }
  leer("Drive", function () {
    var carpetas = DriveApp.getFoldersByName(CARPETA_RAIZ);
    if (!carpetas.hasNext()) throw new Error("No encontré " + CARPETA_RAIZ);
    raiz = carpetas.next();
    var mapa = {"Tesoreria A": "tesoreria_a", "Bancos": "bancos", "Cuentas a cobrar": "tango", "Cuentas a pagar": "tango",
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
  // Extractos que llegaron pero el lector no pudo leer (formato nuevo, PDF escaneado, archivo vacío).
  // El lector los anota en su resumen; como relee toda la carpeta de bancos cada vez, el resumen más
  // nuevo lista todos los que siguen sin leerse. Sin esto, el mail decía "subir a mano" de algo que
  // ya se había subido (Corrientes, 01/10/2026).
  leer("Ilegibles", function () {
    if (!salida) throw new Error("No pude abrir _para la Sheet");
    var mejor = null, archivos = salida.getFiles();
    while (archivos.hasNext()) {
      var f = archivos.next(), m = f.getName().match(/^resumen_bancos_(\d{4}-\d{2}-\d{2})\.md$/);
      if (m && (!mejor || m[1] > mejor.dia)) mejor = {dia: m[1], archivo: f};
    }
    datos.ilegibles = mejor ? _ilegiblesAviso_(mejor.archivo.getBlob().getDataAsString("UTF-8")) : [];
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
  leer("TangoParte", function () {
    if (!salida) throw new Error("No pude abrir _para la Sheet");
    var archivos = salida.getFilesByName("tango_ultima_bajada.txt");
    if (!archivos.hasNext()) throw new Error("Falta tango_ultima_bajada.txt");
    var archivo = archivos.next();
    if (archivos.hasNext()) throw new Error("Hay más de un parte de Tango; revisar duplicados en Drive");
    datos.tangoParte = _parteTangoAviso_(archivo.getBlob().getDataAsString("UTF-8"));
  });
  datos.bancosPartes = {};
  FUENTES_AUTOMATICAS.filter(function (banco) {
    return ["tango", "tesoreria_aa"].indexOf(banco) < 0;
  }).forEach(function (banco) {
    var etiqueta = banco.charAt(0).toUpperCase() + banco.slice(1);
    leer(banco === "galicia" ? "GaliciaParte" : banco + "Parte", function () {
      if (!raiz) throw new Error("No pude abrir la carpeta de datos");
      var bancos = raiz.getFoldersByName("Bancos");
      if (!bancos.hasNext()) throw new Error("Falta la carpeta Bancos");
      var carpetaBancos = bancos.next();
      if (bancos.hasNext()) throw new Error("Hay más de una carpeta Bancos");
      var carpetas = carpetaBancos.getFoldersByName(banco);
      if (!carpetas.hasNext()) throw new Error("Falta Bancos/" + banco);
      var carpeta = carpetas.next();
      if (carpetas.hasNext()) throw new Error("Hay más de una carpeta del banco");
      var nombre = "_ESTADO_" + etiqueta + "_" + _fechaAviso_(ahora, "dd-MM") + ".txt";
      var archivos = carpeta.getFilesByName(nombre);
      // Sin parte hoy, la checklist ya pide revisar la notebook. No es una lectura fallida.
      if (!archivos.hasNext()) return;
      var archivo = archivos.next();
      if (archivos.hasNext()) throw new Error("Hay más de un estado de hoy");
      // Los bots comparten el formato de nucleo/salidas; verificamos el banco de la cabecera.
      var texto = archivo.getBlob().getDataAsString("UTF-8");
      var prefijo = "Bot " + etiqueta + " - ";
      if (texto.slice(0, prefijo.length).toLowerCase() !== prefijo.toLowerCase())
        throw new Error("El parte no corresponde al banco");
      var parte = _parteGaliciaAviso_("Bot Galicia - " + texto.slice(prefijo.length));
      datos.bancosPartes[banco] = parte;
      if (banco === "galicia") datos.galiciaParte = parte;
    });
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

// Una sola casilla por fuente: el parte dice si bajó y el saldo hasta dónde hay movimientos.
function _armarAviso_(ahora, datos) {
  datos = datos || _leerDatosAviso_(ahora);
  var errores = datos.errores || {}, llego = [], faltantes = [], alertas = [];
  var hoy = _diaAviso_(ahora), cierre = _habilAnteriorAviso_(hoy);
  function valida(f) { return f instanceof Date && !isNaN(f) && f <= ahora; }
  function deHoy(f) { return valida(f) && _diaAviso_(f) === hoy; }
  function fecha(f) { return valida(f) ? _fechaAviso_(f, "dd/MM HH:mm") : "no disponible"; }
  function dia(d) { return d ? d.slice(8, 10) + "/" + d.slice(5, 7) : "no disponible"; }
  function poner(ok, texto) { (ok ? llego : faltantes).push((ok ? "☑ " : "☐ ") + texto); }
  function ultimo(lista) {
    return lista.filter(function (f) { return valida(f.fecha); })
      .sort(function (a, b) { return b.fecha - a.fecha; })[0];
  }
  var entradas = datos.entradas || [], parte = datos.tangoParte;
  var fotos = {A: ["cobranzas", "pagos", "cheques terceros", "cheques propios", "movimientos tesoreria"],
    AA: ["cobranzas", "pagos", "cheques terceros", "movimientos tesoreria"]};
  var fallas = parte && parte.fallas || [];
  ["A", "AA"].forEach(function (empresa) {
    if (errores.TangoParte || !parte || !deHoy(parte.fecha)) {
      poner(false, "Tango " + empresa + ": la bajada de Tango no corrió hoy · última: " +
        fecha(parte && parte.fecha) + " · revisar la notebook");
      return;
    }
    if (parte.ok === parte.total && parte.total === TANGO_BAJADAS && !fallas.length) {
      poner(true, "Tango " + empresa + ": " + fotos[empresa].join(", ").replace("movimientos tesoreria", "tesorería") +
        " (" + _fechaAviso_(parte.fecha, "HH:mm") + ")");
      return;
    }
    var faltan = [];
    fotos[empresa].forEach(function (foto) {
      var prefijo = (empresa + " " + foto + " ").toLowerCase();
      var archivo = ultimo(entradas.filter(function (f) {
        return ["tango", "tesoreria_a", "tesoreria_aa"].indexOf(f.tipo) >= 0 && f.nombre.toLowerCase().indexOf(prefijo) === 0;
      }));
      var falla = fallas.filter(function (f) { return f.toLowerCase().indexOf(prefijo) === 0; })[0];
      if (falla || errores.Drive || !archivo || _fechaNombreAviso_(archivo.nombre) !== hoy) {
        faltan.push(foto.replace("movimientos tesoreria", "tesorería") + ": " +
          (falla ? _textoAviso_(falla.replace(/^[^:]+:\s*/, ""), 100) : "no llegó la foto de hoy") +
          " · último archivo: " + fecha(archivo && archivo.fecha));
      }
    });
    // Si el conteo no cierra y el parte no identifica las fallas, no inventamos éxito.
    if (!faltan.length && (!fallas.length || fallas.some(function (f) { return !/^(A|AA)\s/i.test(f); })))
      faltan.push("parte incompleto (" + parte.ok + " de " + parte.total + "); revisar la notebook");
    poner(!faltan.length, "Tango " + empresa + ": " + (faltan.length ? faltan.join("; ") :
      "las " + fotos[empresa].length + " fotos llegaron (" + _fechaAviso_(parte.fecha, "HH:mm") + ")"));
  });
  var bancos = {}, arqueo = "";
  (datos.saldos || []).forEach(function (r) {
    var banco = _esExtractoAviso_(r.origen) ? _bancoExtractoAviso_(r) : _textoAviso_(r.banco);
    var d = valida(r.fecha) ? _diaAviso_(r.fecha) : "";
    if (/^(\(varios\)|varios|caja)$/i.test(banco)) {
      if (_textoAviso_(r.empresa).toUpperCase() === "AA" && /^manual$/i.test(_textoAviso_(r.origen)) && d > arqueo) arqueo = d;
      return;
    }
    if (!banco) return;
    var clave = banco.toLowerCase();
    if (!bancos[clave]) bancos[clave] = {nombre: banco, dia: ""};
    if (_esExtractoAviso_(r.origen) && d > bancos[clave].dia) bancos[clave].dia = d;
  });
  // Extractos que llegaron y no se pudieron leer, por banco (ver _ilegiblesAviso_).
  var ilegibles = datos.ilegibles || [], ilegiblesVistos = {};
  function ilegiblesDe(clave) {
    var lista = ilegibles.filter(function (x) { return x.banco === clave; });
    lista.forEach(function (x) { ilegiblesVistos[x.banco + "/" + x.archivo] = true; });
    return lista;
  }
  function textoIlegible(lista) {
    return "llegó «" + _textoAviso_(lista[0].archivo, 80) + "» pero no se pudo leer (" +
      _textoAviso_(lista[0].motivo, 90) + ")" +
      (lista.length > 1 ? " y " + (lista.length - 1) + " archivo(s) más" : "") + " · avisar a finauto";
  }
  function manual(nombre, d, caja, clave) {
    var raros = clave ? ilegiblesDe(clave) : [];
    // Un banco sin movimientos el último día hábil no está atrasado si el extracto se subió igual
    // (BBVA, 01/10/2026). Se toma el archivo más nuevo de Bancos/<banco>/ por su fecha en Drive,
    // salvo los que el lector no pudo leer: esos no cuentan como extracto.
    var subido = "";
    if (clave && !caja && !errores.Drive) {
      var noLeidos = raros.map(function (x) { return x.archivo; });
      var archivo = ultimo(entradas.filter(function (f) {
        var ruta = String(f.ruta || "").replace(/\\/g, "/").toLowerCase();
        return ruta.indexOf("bancos/" + clave + "/") === 0 && noLeidos.indexOf(f.nombre) < 0;
      }));
      if (archivo) subido = _diaAviso_(archivo.fecha);
    }
    var ok = !errores.Extracto && ((d && d >= cierre) || (subido && subido >= cierre));
    var masNuevo = subido > (d || "") ? subido : d;
    var edad = masNuevo ? Math.round((Date.parse(hoy) - Date.parse(masNuevo)) / AVISO_DIA) : null;
    // Al día pero con un archivo raro: la casilla sigue en ✅ y el archivo va a REVISAR.
    if (ok && raros.length) alertas.push(nombre + ": " + textoIlegible(raros));
    if (!ok && raros.length) {
      poner(false, nombre + ": " + textoIlegible(raros) + " · último extracto leído: " + dia(d));
      return;
    }
    var alDia = d && d >= cierre ? "al día, " + (caja ? "arqueo" : "extracto") + " hasta " + dia(d) :
      "al día, extracto subido el " + dia(subido) + " (último movimiento " + dia(d) + ")";
    poner(ok, nombre + ": " + (ok ? alDia :
      (errores.Extracto ? "no se pudo verificar" : masNuevo ? "último " + (caja ? "arqueo" : "extracto") +
        (subido && subido === masNuevo && subido !== d ? " subido el " : " del ") + dia(masNuevo) +
        " (hace " + edad + " días)" : "sin fecha disponible") + (caja ? " · cargar a mano" : " · subir a mano")));
  }

  var partes = datos.bancosPartes || {};
  if (datos.galiciaParte) partes = Object.assign({}, partes, {galicia: datos.galiciaParte});
  Object.keys(bancos).sort().forEach(function (clave) {
    var banco = bancos[clave];
    if (FUENTES_AUTOMATICAS.indexOf(clave) < 0) { manual(_nombreBancoAviso_(banco.nombre), banco.dia, false, clave); return; }
    var raros = ilegiblesDe(clave);
    if (raros.length) alertas.push(_nombreBancoAviso_(banco.nombre) + ": " + textoIlegible(raros));
    var p = partes[clave];
    var archivo = ultimo(entradas.filter(function (f) {
      var ruta = String(f.ruta || "").replace(/\\/g, "/").toLowerCase();
      return ruta.indexOf("bancos/" + clave + "/") === 0 &&
        f.nombre.toLowerCase().indexOf("movimientos " + clave + " ") === 0 && /\.xlsx$/i.test(f.nombre);
    }));
    var ok = p && deHoy(p.fecha) && p.ok && !errores[clave === "galicia" ? "GaliciaParte" : clave + "Parte"];
    poner(ok, _nombreBancoAviso_(banco.nombre) + ": " + (ok ? _fechaAviso_(p.fecha, "HH:mm") + " · movimientos hasta " + dia(banco.dia) :
      (p && deHoy(p.fecha) ? "el bot falló a las " + _fechaAviso_(p.fecha, "HH:mm") + " (" +
        _textoAviso_(p.detalle || "sin motivo disponible", 140) + ")" : "el bot no corrió hoy · revisar la notebook") +
      " · Último extracto: " + (errores.Drive ? "no se pudo verificar" : fecha(archivo && archivo.fecha))));
  });
  if (!Object.keys(bancos).length) alertas.push("No se pudieron identificar bancos en Saldos Bancarios.");
  // Un ilegible de un banco que todavía no está en Saldos Bancarios (banco nuevo, carpeta mal nombrada).
  ilegibles.forEach(function (x) {
    if (!ilegiblesVistos[x.banco + "/" + x.archivo]) alertas.push("Bancos/" + x.banco + ": " + textoIlegible([x]));
  });
  // El arqueo de caja AA no va al mail (pedido de Thomas, 01/10/2026): se consigue por fuera y el
  // conteo es semanal. La caja AA del cash sigue calculándose con el último arqueo cargado.
  var registros = (datos.registro || []).filter(function (r) { return valida(r.fecha); });
  function esOk(r) { return /^ok$/i.test(_textoAviso_(r.estado)) && !/VERIFICACION_NO_CUADRA/.test(r.detalle || ""); }
  var oks = registros.filter(function (r) { return esOk(r) && r.tipo !== "sistema"; });
  var ultima = ultimo(oks);
  var bajadas = [parte].concat(Object.keys(partes).map(function (k) { return partes[k]; }))
    .filter(function (p) { return p && deHoy(p.fecha); });
  var importado = !errores.Registro && ultima && deHoy(ultima.fecha) && bajadas.every(function (p) { return ultima.fecha > p.fecha; });
  poner(importado, importado ? "La Sheet se actualizó (" + _fechaAviso_(ultima.fecha, "HH:mm") + ")" :
    "La Sheet no importó lo de hoy · última importación: " + fecha(ultima && ultima.fecha));
  if (!valida(datos.ultimaPasada)) alertas.push("No se pudo verificar si la notebook está procesando.");
  else if (ahora - datos.ultimaPasada > 60 * 60 * 1000)
    alertas.push("La notebook no está procesando · última pasada: " + fecha(datos.ultimaPasada));
  registros.forEach(function (r) {
    if (!/^error$/i.test(_textoAviso_(r.estado)) && !/VERIFICACION_NO_CUADRA/.test(r.detalle || "")) return;
    if (oks.some(function (ok) { return ok.tipo === r.tipo && ok.fecha > r.fecha; })) return;
    var texto = "Falló la importación de " + r.tipo + ": " + _textoAviso_(r.detalle, 140);
    if (alertas.indexOf(texto) < 0) alertas.push(texto);
  });
  (datos.retenidos || []).forEach(function (f) {
    if (!valida(f.fecha)) return;
    if (oks.some(function (r) { return f.tipo && r.tipo === f.tipo && r.fecha > f.fecha; })) return;
    alertas.push("Archivo retenido: " + _textoAviso_(f.nombre, 120));
  });
  Object.keys(errores).forEach(function (k) { alertas.push("No se pudo leer " + k + ": " + _textoAviso_(errores[k], 120)); });
  var cuerpo = ["✅ LLEGÓ HOY\n" + (llego.join("\n") || "—")];
  if (faltantes.length) cuerpo.push("❌ FALTA\n" + faltantes.join("\n"));
  if (alertas.length) cuerpo.push("⚠️ REVISAR\n" + alertas.map(function (a) { return "- " + a; }).join("\n"));
  return {asunto: "NAVAR · " + _fechaAviso_(ahora, "dd/MM") + " · " +
    (faltantes.length === 1 ? "falta 1 cosa" : faltantes.length ? "faltan " + faltantes.length + " cosas" : "todo al día"),
    cuerpo: cuerpo.join("\n\n"), alertas: alertas, faltantes: faltantes};
}
