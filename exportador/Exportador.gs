/**
 * ================================================================
 *  EXPORTADOR DE LA CAPA 2  —  finauto
 * ----------------------------------------------------------------
 *  Este es el ÚNICO archivo que sabe de solapas, filas y columnas.
 *  Lee lo que ya existe en el Cash (MOVIMIENTOS + SALDOS) y emite el
 *  CONTRATO: un JSON estable con los datos como CAMPOS (fecha, tipo,
 *  intocable...), no como posiciones.
 *
 *  A partir de acá, el dashboard y el simulador leen SOLO este JSON.
 *  Si mañana el origen cambia (base de datos en vez de planilla), se
 *  reemplaza este archivo y las herramientas visuales NO se enteran.
 *
 *  QUÉ NO HACE: no escribe nada en el Cash. Es de solo lectura.
 *
 *  USO:
 *    1. Pegar en el Apps Script del Cash.
 *    2. Menú "finauto" > "Exportar contrato" -> deja el JSON en Drive.
 *    3. (Opcional) Implementar como Web App para servirlo por URL.
 * ================================================================
 */

var EXP_CONFIG = {
  CLIENTE: 'MAGA+',

  // Solapa de MOVIMIENTOS: se busca por los encabezados, NO por nombre ni
  // por número de fila (así aguanta que se renombre o se muevan cosas).
  MOV_ENCABEZADOS: ['FECHA', 'EMPRESA', 'BANCO', 'TIPO', 'CONCEPTO', 'IMPORTE', 'ESTADO'],
  MOV_FILAS_BUSCAR_ENCABEZADO: 10,   // en cuántas filas de arriba buscar el encabezado

  TAB_SALDOS: 'SALDOS',
  CAJA_HOY_REF: 'SALDOS!C26',        // caja de hoy (banco + efectivo)

  CARPETA_SALIDA_ID: '',             // vacío = deja el JSON en la raíz de Mi unidad
  NOMBRE_SALIDA: '_CONTRATO_finauto'
};

/**
 * Catálogo: qué significa cada TIPO. Tiene que ser espejo de
 * clientes/<cliente>/catalogo.json en el repo de finauto.
 * 'intocable' = no se puede atrasar (sueldos y cheques).
 */
var EXP_TIPOS = {
  'SUELDO':             { categoria: 'personal',    intocable: true,  reprogramable: false },
  'SUELDO_QUINTANA':    { categoria: 'personal',    intocable: true,  reprogramable: false },
  'COMISION':           { categoria: 'bancario',    intocable: false, reprogramable: false },
  'RETIRO_SOCIO':       { categoria: 'socios',      intocable: false, reprogramable: true  },
  'ALQUILER':           { categoria: 'fijo',        intocable: false, reprogramable: true  },
  'HONORARIO':          { categoria: 'fijo',        intocable: false, reprogramable: true  },
  'IMPUESTO':           { categoria: 'impuestos',   intocable: false, reprogramable: true  },
  'SERVICIO':           { categoria: 'fijo',        intocable: false, reprogramable: true  },
  'VEP_AFIP':           { categoria: 'impuestos',   intocable: false, reprogramable: true  },
  'EFECTIVO_VARIOS':    { categoria: 'varios',      intocable: false, reprogramable: true  },
  'PAGO_DROGUE_TRANSF': { categoria: 'proveedores', intocable: false, reprogramable: true  },
  'PAGO':               { categoria: 'proveedores', intocable: false, reprogramable: true  }
};

/* ================================================================ */
/*  MENÚ                                                            */
/* ================================================================ */
function onOpen() {
  SpreadsheetApp.getUi().createMenu('finauto')
    .addItem('Exportar contrato (JSON)', 'exportarContrato')
    .addItem('Ver resumen (sin escribir)', 'previsualizarContrato')
    .addToUi();
}

/* ================================================================ */
/*  ENTRADAS                                                        */
/* ================================================================ */
function exportarContrato() {
  var payload = _construirPayload_();
  var nombre = EXP_CONFIG.NOMBRE_SALIDA + '_' +
    Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd_HHmm') + '.json';
  var blob = Utilities.newBlob(JSON.stringify(payload, null, 2), 'application/json', nombre);

  var carpeta = EXP_CONFIG.CARPETA_SALIDA_ID
    ? DriveApp.getFolderById(EXP_CONFIG.CARPETA_SALIDA_ID)
    : DriveApp.getRootFolder();
  var archivo = carpeta.createFile(blob);

  SpreadsheetApp.getUi().alert(
    '✅ Contrato exportado\n\n' +
    'Archivo: ' + nombre + '\n' +
    'Movimientos: ' + payload.movimientos.length + '\n' +
    'Saldos: ' + payload.saldos.length + '\n' +
    'Caja hoy: ' + payload.caja_hoy + '\n\n' +
    (payload.avisos.length ? ('⚠ Avisos:\n- ' + payload.avisos.join('\n- ')) : 'Sin avisos.')
  );
  return archivo.getUrl();
}

function previsualizarContrato() {
  var p = _construirPayload_();
  var porTipo = {};
  p.movimientos.forEach(function (m) { porTipo[m.tipo] = (porTipo[m.tipo] || 0) + 1; });
  var lineas = Object.keys(porTipo).sort().map(function (t) { return '  ' + t + ': ' + porTipo[t]; });
  SpreadsheetApp.getUi().alert(
    'Resumen del contrato (nada se escribió)\n\n' +
    'Movimientos: ' + p.movimientos.length + '\n' +
    'Intocables: ' + p.movimientos.filter(function (m) { return m.intocable; }).length + '\n' +
    'Saldos: ' + p.saldos.length + '  ·  Caja hoy: ' + p.caja_hoy + '\n\n' +
    'Por tipo:\n' + lineas.join('\n') + '\n\n' +
    (p.avisos.length ? ('⚠ Avisos:\n- ' + p.avisos.join('\n- ')) : 'Sin avisos.')
  );
}

/** Web App (opcional): devuelve el contrato por URL para las herramientas visuales. */
function doGet() {
  return ContentService
    .createTextOutput(JSON.stringify(_construirPayload_()))
    .setMimeType(ContentService.MimeType.JSON);
}

/* ================================================================ */
/*  CONSTRUCCIÓN DEL CONTRATO                                       */
/* ================================================================ */
function _construirPayload_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var avisos = [];

  var movimientos = _leerMovimientos_(ss, avisos);
  var saldos = _leerSaldos_(ss, avisos);
  var cajaHoy = _leerCajaHoy_(ss, avisos);

  return {
    contrato_version: '1.0',
    cliente: EXP_CONFIG.CLIENTE,
    generado: new Date().toISOString(),
    caja_hoy: cajaHoy,
    catalogo_tipos: EXP_TIPOS,
    saldos: saldos,
    movimientos: movimientos,
    avisos: avisos
  };
}

/** Lee la solapa MOVIMIENTOS buscando el encabezado (no por posición). */
function _leerMovimientos_(ss, avisos) {
  var hojas = ss.getSheets();
  for (var i = 0; i < hojas.length; i++) {
    var sh = hojas[i];
    var ubic = _ubicarEncabezado_(sh);
    if (!ubic) continue;

    var lastRow = sh.getLastRow();
    if (lastRow <= ubic.fila) return [];
    var ancho = Math.max(ubic.col.OBSERVACION || 0, ubic.col.ESTADO) + 1;
    var datos = sh.getRange(ubic.fila + 1, 1, lastRow - ubic.fila, ancho).getValues();

    var out = [];
    for (var r = 0; r < datos.length; r++) {
      var row = datos[r];
      var fecha = _fechaIso_(row[ubic.col.FECHA]);
      var importe = _num_(row[ubic.col.IMPORTE]);
      if (!fecha && !importe) continue;              // fila vacía
      var tipo = _txt_(row[ubic.col.TIPO]).toUpperCase();
      var meta = EXP_TIPOS[tipo] || null;
      if (tipo && !meta) avisos.push('Tipo desconocido en el catálogo: "' + tipo + '"');

      out.push({
        fecha: fecha,
        unidad: _txt_(row[ubic.col.EMPRESA]).toUpperCase(),
        banco: _txt_(row[ubic.col.BANCO]).toUpperCase(),
        tipo: tipo,
        categoria: meta ? meta.categoria : 'sin_categoria',
        intocable: meta ? !!meta.intocable : false,
        reprogramable: meta ? !!meta.reprogramable : true,
        concepto: _txt_(row[ubic.col.CONCEPTO]),
        importe: importe,
        signo: 'egreso',                              // esta solapa son egresos
        estado: _txt_(row[ubic.col.ESTADO]).toUpperCase(),
        observacion: ubic.col.OBSERVACION != null ? _txt_(row[ubic.col.OBSERVACION]) : ''
      });
    }
    return out;
  }
  avisos.push('No encontré la solapa de MOVIMIENTOS (busco los encabezados ' +
              EXP_CONFIG.MOV_ENCABEZADOS.join(', ') + ').');
  return [];
}

/** Busca la fila de encabezado y devuelve el índice de cada columna. */
function _ubicarEncabezado_(sh) {
  var maxR = Math.min(sh.getLastRow(), EXP_CONFIG.MOV_FILAS_BUSCAR_ENCABEZADO);
  var maxC = sh.getLastColumn();
  if (maxR < 1 || maxC < 1) return null;
  var grid = sh.getRange(1, 1, maxR, maxC).getValues();

  for (var r = 0; r < grid.length; r++) {
    var col = {}, encontrados = 0;
    for (var c = 0; c < grid[r].length; c++) {
      var v = _norm_(grid[r][c]);
      if (!v) continue;
      if (EXP_CONFIG.MOV_ENCABEZADOS.indexOf(v) > -1 && col[v] == null) { col[v] = c; encontrados++; }
      if (v === 'OBSERVACION' && col.OBSERVACION == null) col.OBSERVACION = c;
    }
    if (encontrados === EXP_CONFIG.MOV_ENCABEZADOS.length) return { fila: r + 1, col: col };
  }
  return null;
}

/** Lee la grilla SALDOS: fila = farmacia, columna = banco. */
function _leerSaldos_(ss, avisos) {
  var sh = ss.getSheetByName(EXP_CONFIG.TAB_SALDOS);
  if (!sh) { avisos.push('No existe la solapa "' + EXP_CONFIG.TAB_SALDOS + '".'); return []; }
  var maxR = sh.getLastRow(), maxC = sh.getLastColumn();
  if (maxR < 1) return [];
  var grid = sh.getRange(1, 1, maxR, maxC).getValues();

  // fila de encabezado: la que tiene "FARMACIA" en la col A
  var filaEnc = -1;
  for (var r = 0; r < grid.length; r++) { if (_norm_(grid[r][0]) === 'FARMACIA') { filaEnc = r; break; } }
  if (filaEnc < 0) { avisos.push('No encontré la fila "Farmacia" en SALDOS.'); return []; }

  // columnas de banco: las que tienen texto en la fila de encabezado (salvo la A)
  var bancos = [];
  for (var c = 1; c < grid[filaEnc].length; c++) {
    var n = _norm_(grid[filaEnc][c]);
    if (n) bancos.push({ col: c, nombre: n });
  }

  var out = [], empezo = false;
  for (var rr = filaEnc + 1; rr < grid.length; rr++) {
    var fcia = _txt_(grid[rr][0]);
    if (!fcia) { if (empezo) break; else continue; }   // corta al final del bloque
    empezo = true;
    bancos.forEach(function (b) {
      var v = _num_(grid[rr][b.col]);
      if (v !== 0) out.push({ farmacia: fcia, banco: b.nombre, saldo_actual: v });
    });
  }
  return out;
}

function _leerCajaHoy_(ss, avisos) {
  try {
    var partes = EXP_CONFIG.CAJA_HOY_REF.split('!');
    var sh = ss.getSheetByName(partes[0]);
    if (!sh) { avisos.push('No pude leer la caja de hoy (' + EXP_CONFIG.CAJA_HOY_REF + ').'); return 0; }
    return _num_(sh.getRange(partes[1]).getValue());
  } catch (e) {
    avisos.push('Error leyendo la caja de hoy: ' + e);
    return 0;
  }
}

/* ================================================================ */
/*  HELPERS                                                         */
/* ================================================================ */
function _norm_(v) {
  return String(v == null ? '' : v).toUpperCase()
    .normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/\s+/g, ' ').trim();
}
function _txt_(v) { return String(v == null ? '' : v).trim(); }

function _num_(v) {
  if (typeof v === 'number') return isNaN(v) ? 0 : v;
  if (v == null) return 0;
  var s = String(v).trim();
  if (!s) return 0;
  var neg = /^\(.*\)$/.test(s);
  s = s.replace(/[()$\s]/g, '');
  if (s.indexOf(',') > -1 && s.indexOf('.') > -1) s = s.replace(/\./g, '').replace(',', '.');
  else if (s.indexOf(',') > -1) s = s.replace(',', '.');
  var n = parseFloat(s);
  if (isNaN(n)) return 0;
  return neg ? -n : n;
}

/** Fecha -> 'AAAA-MM-DD' (acepta Date o texto dd/mm/aaaa). */
function _fechaIso_(v) {
  if (v instanceof Date) {
    return Utilities.formatDate(v, Session.getScriptTimeZone(), 'yyyy-MM-dd');
  }
  var s = String(v == null ? '' : v).trim();
  var m = s.match(/^(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{2,4})/);
  if (!m) return null;
  var y = parseInt(m[3], 10); if (y < 100) y += 2000;
  var d = new Date(y, parseInt(m[2], 10) - 1, parseInt(m[1], 10));
  return Utilities.formatDate(d, Session.getScriptTimeZone(), 'yyyy-MM-dd');
}
