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
  'PAGO':               { categoria: 'proveedores', intocable: false, reprogramable: true  },

  // INTERNOS: la plata no sale del grupo, solo cambia de lugar.
  // NO se cuentan como egreso (si se contaran, el simulador mostraría de menos).
  'TRANSFERENCIA':      { categoria: 'interno', intocable: false, reprogramable: true, interno: true },
  'DEPOSITO':           { categoria: 'interno', intocable: false, reprogramable: true, interno: true }
};

/**
 * INGRESOS: cómo se interpreta cada línea del bloque INGRESOS de los cashflow.
 * 'naturaleza' es lo que usa el simulador: el escenario CONSERVADOR solo cuenta
 * los FIJOS (lo que entra sí o sí). Los VARIABLES pueden no entrar ese día.
 * 'interno' = no es plata nueva, solo se mueve de lugar.
 */
var EXP_INGRESOS = {
  // --- Speedmed (droguería) ---
  'CARTERA DE CH':          { naturaleza: 'FIJO',     unidad: 'SPEEDMED' },
  'CUENTAS A COBRAR FCIAS': { naturaleza: 'VARIABLE', unidad: 'SPEEDMED' },
  'FINANCIACION':           { naturaleza: 'VARIABLE', unidad: 'SPEEDMED' },
  'DEPOSITO EFECTIVO':      { naturaleza: 'FIJO',     unidad: 'SPEEDMED', interno: true },
  'TRANSF MAGA+':           { naturaleza: 'FIJO',     unidad: 'SPEEDMED', interno: true },
  'TRANSF MAGA':            { naturaleza: 'FIJO',     unidad: 'SPEEDMED', interno: true },
  // --- MAGA+ (farmacias) ---
  'TARJETA Y MP':           { naturaleza: 'FIJO',     unidad: 'MAGA' },
  'EFECTIVO':               { naturaleza: 'FIJO',     unidad: 'MAGA' },
  'COBRO O.SOCIALES':       { naturaleza: 'VARIABLE', unidad: 'MAGA' },
  'COBRO O SOCIALES':       { naturaleza: 'VARIABLE', unidad: 'MAGA' },
  'COBRO O .SOCIALES':      { naturaleza: 'VARIABLE', unidad: 'MAGA' },  // así viene escrito en la planilla
  'PAMI':                   { naturaleza: 'VARIABLE', unidad: 'MAGA' }
};

// Palabras que marcan el fin del bloque de ingresos en el cashflow.
var EXP_FIN_INGRESOS = ['EGRESOS', 'GASTOS BANCARIOS', 'SALDO CIERRE', 'SALDO DE CIERRE'];

/**
 * FILAS DERIVADAS (regla general, confirmada con Thomas).
 *
 * En el cashflow hay filas que NO son movimientos sino SALDOS calculados: por
 * ejemplo "Con pago a droguerías" = cuánto quedaría de saldo si se les pagara.
 * Esas filas repiten un saldo en cada columna-fecha, así que NO SE SUMAN:
 * "se toman como una sola". Si se suman a lo largo de 200 columnas, dan cifras
 * absurdas (nos pasó: $249 mil millones).
 *
 * Se saltean por completo. Cualquier planilla de cliente va a tener filas así,
 * por eso está como lista configurable y no hardcodeado en la lógica.
 */
var EXP_FILAS_DERIVADAS = ['SALDO', 'SALDO INICIO', 'SALDO CIERRE', 'POSICION BANCARIA', 'TOTAL'];
// Además: cualquier fila que empiece con estos prefijos se considera derivada.
var EXP_PREFIJOS_DERIVADOS = ['CON PAGO', 'SALDO ', 'TOTAL ', 'SUBTOTAL'];

/**
 * FILAS DE SALDO: no son eventos, es UN saldo que se repite en cada columna-fecha
 * (ej. la deuda intercompany con MAGA+, que arrastra el mismo número día tras día).
 * NO se suman: se toma solamente el ÚLTIMO valor, que es el saldo vigente.
 */
var EXP_FILAS_SALDO = ['MAGA+', 'MAGA', 'SPEEDMED'];

/**
 * FILAS DE CRÉDITO: restan en vez de sumar. Las notas de crédito bajan la deuda,
 * pero en la planilla están cargadas en POSITIVO -> hay que invertirlas.
 */
var EXP_PREFIJOS_CREDITO = ['NCR', 'NOTA DE CREDITO'];

function _esFilaSaldo_(etq) { return EXP_FILAS_SALDO.indexOf(etq) > -1; }

function _esCredito_(etq) {
  for (var i = 0; i < EXP_PREFIJOS_CREDITO.length; i++) {
    if (etq.indexOf(EXP_PREFIJOS_CREDITO[i]) === 0) return true;
  }
  return false;
}

function _esFilaDerivada_(etiquetaNorm) {
  if (EXP_FILAS_DERIVADAS.indexOf(etiquetaNorm) > -1) return true;
  for (var i = 0; i < EXP_PREFIJOS_DERIVADOS.length; i++) {
    if (etiquetaNorm.indexOf(EXP_PREFIJOS_DERIVADOS[i]) === 0) return true;
  }
  return false;
}

/* ================================================================ */
/*  MENÚ                                                            */
/* ================================================================ */
/**
 * OJO: NO se llama onOpen() a propósito.
 * El proyecto del Cash YA tiene un onOpen() (el de Calculadora/Cobranzas) y si
 * hubiera dos, uno pisaría al otro y se rompería el menú existente.
 *
 * Si algún día querés el menú de finauto en la planilla, agregá esta línea
 * DENTRO del onOpen() que ya existe en Calculadora.gs:
 *      agregarMenuFinauto();
 * Mientras tanto, las funciones se corren desde el editor de Apps Script.
 */
function agregarMenuFinauto() {
  SpreadsheetApp.getUi().createMenu('finauto')
    .addItem('Exportar contrato (JSON)', 'exportarContrato')
    .addItem('Ver resumen (sin escribir)', 'previsualizarContrato')
    .addToUi();
}

/**
 * PREVISUALIZAR EN EL LOG — la forma más segura de probar.
 * No escribe NADA en ningún lado: solo lee y deja el resultado en
 * "Registro de ejecución" del editor de Apps Script.
 *
 * Cómo correrla: en el editor, elegí 'previsualizarEnLog' en el desplegable
 * de funciones y apretá ▶ Ejecutar. Después mirá "Registro de ejecución".
 */
function previsualizarEnLog() {
  var p = _construirPayload_();

  Logger.log('===== CONTRATO finauto — PREVISUALIZACIÓN (no se escribió nada) =====');
  Logger.log('Cliente: %s', p.cliente);
  Logger.log('Caja hoy: %s', p.caja_hoy);
  Logger.log('Movimientos leídos: %s', p.movimientos.length);
  Logger.log('Saldos leídos: %s', p.saldos.length);

  // Cuántos movimientos por tipo (para ver si el catálogo cubre todo)
  var porTipo = {}, porEstado = {}, sinCat = 0;
  p.movimientos.forEach(function (m) {
    porTipo[m.tipo || '(vacío)'] = (porTipo[m.tipo || '(vacío)'] || 0) + 1;
    porEstado[m.estado || '(vacío)'] = (porEstado[m.estado || '(vacío)'] || 0) + 1;
    if (m.categoria === 'sin_categoria') sinCat++;
  });
  Logger.log('--- Por TIPO ---');
  Object.keys(porTipo).sort().forEach(function (t) { Logger.log('   %s: %s', t, porTipo[t]); });
  Logger.log('--- Por ESTADO ---');
  Object.keys(porEstado).sort().forEach(function (e) { Logger.log('   %s: %s', e, porEstado[e]); });
  Logger.log('Movimientos sin categoría en el catálogo: %s', sinCat);

  // Primeras 3 filas, para confirmar que se leyeron bien las columnas
  Logger.log('--- Muestra (3 primeras filas) ---');
  p.movimientos.slice(0, 3).forEach(function (m) {
    Logger.log('   %s | %s | %s | %s | %s', m.fecha, m.unidad, m.banco, m.tipo, m.importe);
  });

  // Bancos encontrados en la grilla SALDOS
  var bancos = {};
  p.saldos.forEach(function (s) { bancos[s.banco] = (bancos[s.banco] || 0) + 1; });
  Logger.log('--- SALDOS por banco ---');
  Object.keys(bancos).forEach(function (b) { Logger.log('   %s: %s farmacias', b, bancos[b]); });

  // INGRESOS previstos (bloque INGRESOS de los cashflow)
  var cob = p.cobros_previstos || [];
  Logger.log('--- COBROS PREVISTOS: %s registros ---', cob.length);
  var porConcepto = {};
  cob.forEach(function (x) {
    var k = x.unidad + ' · ' + x.concepto + ' (' + x.naturaleza + ')';
    porConcepto[k] = (porConcepto[k] || 0) + x.importe;
  });
  Object.keys(porConcepto).sort().forEach(function (k) {
    Logger.log('   %s: %s', k, Math.round(porConcepto[k]));
  });
  if (cob.length) {
    var fechas = cob.map(function (x) { return x.fecha; }).sort();
    Logger.log('   rango de fechas: %s a %s', fechas[0], fechas[fechas.length - 1]);
  }

  // Droguerías: lo que nos deben y lo que debemos (NO es caja, son derechos/obligaciones)
  _logDrog_('CUENTAS A COBRAR A DROGUERIAS (nos deben)', p.cuentas_a_cobrar_droguerias);
  _logDrog_('DEUDA CON DROGUERIAS (les debemos)', p.deuda_droguerias);

  Logger.log('--- AVISOS ---');
  if (p.avisos.length) { p.avisos.forEach(function (a) { Logger.log('   ⚠ %s', a); }); }
  else { Logger.log('   (ninguno)'); }
  Logger.log('===== FIN =====');
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

  // OJO: el alert() solo funciona si la planilla está abierta y alguien lo acepta.
  // Corriendo desde el editor puede quedar ESPERANDO para siempre -> por eso va
  // dentro de try/catch y el resultado importante se escribe SIEMPRE en el log.
  Logger.log('✅ Contrato exportado');
  Logger.log('Archivo: %s', nombre);
  Logger.log('URL: %s', archivo.getUrl());
  Logger.log('Movimientos: %s | Saldos: %s | Caja hoy: %s',
             payload.movimientos.length, payload.saldos.length, payload.caja_hoy);
  try {
    SpreadsheetApp.getUi().alert('✅ Contrato exportado\n\nArchivo: ' + nombre);
  } catch (e) {
    // Sin interfaz (corriendo desde el editor): no pasa nada, ya está en el log.
  }
  return archivo.getUrl();
}

/**
 * EXPORTAR SIN NINGÚN CARTEL — la versión recomendada para correr desde el editor.
 * Hace exactamente lo mismo pero no intenta mostrar ningún popup, así no se puede
 * quedar esperando. El resultado queda en "Registro de ejecución".
 */
function exportarContratoEnLog() {
  var payload = _construirPayload_();
  var nombre = EXP_CONFIG.NOMBRE_SALIDA + '_' +
    Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd_HHmm') + '.json';
  var blob = Utilities.newBlob(JSON.stringify(payload, null, 2), 'application/json', nombre);
  var carpeta = EXP_CONFIG.CARPETA_SALIDA_ID
    ? DriveApp.getFolderById(EXP_CONFIG.CARPETA_SALIDA_ID)
    : DriveApp.getRootFolder();
  var archivo = carpeta.createFile(blob);

  Logger.log('===== CONTRATO EXPORTADO =====');
  Logger.log('Archivo : %s', nombre);
  Logger.log('Tamaño  : %s KB', Math.round(blob.getBytes().length / 1024));
  Logger.log('URL     : %s', archivo.getUrl());
  Logger.log('Movimientos: %s | Saldos: %s | Caja hoy: %s',
             payload.movimientos.length, payload.saldos.length, payload.caja_hoy);
  Logger.log('Cobros previstos: %s | Deuda drog.: %s | A cobrar drog.: %s',
             (payload.cobros_previstos || []).length,
             (payload.deuda_droguerias || []).length,
             (payload.cuentas_a_cobrar_droguerias || []).length);

  // LOS AVISOS SE IMPRIMEN SIEMPRE.
  //
  // Sin esto el log decia "1104 movimientos, exportado OK" y uno se iba
  // tranquilo, cuando adentro faltaba la mitad de la deuda. El resumen lindo
  // sin el detalle de que se leyo es exactamente como no darse cuenta.
  var av = payload.avisos || [];
  Logger.log('===== QUE LEYO (%s aviso/s) =====', av.length);
  for (var i = 0; i < av.length; i++) Logger.log('  . %s', av[i]);
  if (!av.length) Logger.log('  (ninguno: revisar, porque siempre deberia informar las hojas)');

  Logger.log('Está en tu Drive, en "Mi unidad".');
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
  var caja = _leerCajaPorUnidad_(ss, avisos);
  var cajaHoy = caja.total;
  var cobros = _leerIngresosCashflow_(ss, avisos);
  var drog = _leerBloquesDroguerias_(ss, avisos);

  return {
    contrato_version: '1.2',
    cliente: EXP_CONFIG.CLIENTE,
    generado: new Date().toISOString(),
    caja_hoy: cajaHoy,
    caja_por_unidad: caja.por_unidad,
    caja_efectivo: caja.efectivo,
    catalogo_tipos: EXP_TIPOS,
    catalogo_ingresos: EXP_INGRESOS,
    saldos: saldos,
    movimientos: movimientos,       // egresos (de la solapa MOVIMIENTOS)
    cobros_previstos: cobros,       // ingresos a futuro (bloque INGRESOS del cashflow) -> SÍ es caja
    // Lo de abajo NO es caja: son derechos/obligaciones. No sumar a los cobros.
    cuentas_a_cobrar_droguerias: drog.cuentas_a_cobrar_droguerias,
    deuda_droguerias: drog.deuda_droguerias,
    avisos: avisos
  };
}

/** Lee la solapa MOVIMIENTOS buscando el encabezado (no por posición). */
function _leerMovimientos_(ss, avisos) {
  var hojas = ss.getSheets();

  // Se listan TODAS las hojas. Cuando algo no se lee, lo primero que hace falta
  // saber es que habia para leer.
  var _nom = [];
  for (var z = 0; z < hojas.length; z++) _nom.push(hojas[z].getName());
  avisos.push('Hojas del archivo (' + hojas.length + '): ' + _nom.join(' | '));
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
        interno: meta ? !!meta.interno : false,   // true = no es gasto real, solo mueve plata de lugar
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

/**
 * Lee el bloque INGRESOS de las solapas de cashflow (una por unidad de negocio).
 *
 * Estas solapas son una MATRIZ: cada columna es una FECHA y cada fila un concepto.
 * Acá están los cobros PREVISTOS a futuro (lo que MOVIMIENTOS no tiene, porque
 * esa solapa es solo de egresos).
 *
 * No usa números de fila fijos: busca la fila que tiene fechas y la fila que dice
 * "INGRESOS", y lee el bloque que sigue hasta EGRESOS. Así aguanta que muevan filas.
 * Las columnas de TOTAL mensual quedan afuera solas (no parsean como fecha).
 */
function _leerIngresosCashflow_(ss, avisos) {
  var out = [], encontradas = 0;
  var hojas = ss.getSheets();

  for (var i = 0; i < hojas.length; i++) {
    var sh = hojas[i];
    var nom = _norm_(sh.getName());
    if (nom.indexOf('CASH') < 0 || nom.indexOf('FLOW') < 0) continue;
    var unidad = (nom.indexOf('SPEED') > -1) ? 'SPEEDMED'
               : (nom.indexOf('MAGA') > -1) ? 'MAGA' : '';
    // MISMO PROBLEMA QUE EN LA DEUDA, y aca afecta a los INGRESOS: una hoja de
    // cashflow cuyo nombre no diga SPEED ni MAGA se descartaba en silencio. Si
    // esa hoja existe, se pierde toda la plata que entra por ella y el contrato
    // sale igual de prolijo.
    if (!unidad) {
      unidad = sh.getName().trim();
      avisos.push('Ingresos: la hoja "' + sh.getName() + '" parece un cashflow '+
                  'pero su nombre no dice SPEED ni MAGA. La lei igual con la '+
                  'unidad "' + unidad + '".');
    }
    encontradas++;

    var maxR = sh.getLastRow(), maxC = sh.getLastColumn();
    if (maxR < 2 || maxC < 2) continue;
    var grid = sh.getRange(1, 1, maxR, maxC).getValues();

    // 1) La fila de fechas = la que más celdas-fecha tiene arriba de todo.
    var filaFechas = -1, mejor = 0;
    for (var r = 0; r < Math.min(grid.length, 15); r++) {
      var n = 0;
      for (var c = 1; c < grid[r].length; c++) if (_fechaCol_(grid[r][c])) n++;
      if (n > mejor) { mejor = n; filaFechas = r; }
    }
    if (filaFechas < 0 || mejor < 3) {
      avisos.push('En "' + sh.getName() + '" no encontré la fila de fechas.');
      continue;
    }

    var cols = [];
    for (var c2 = 1; c2 < grid[filaFechas].length; c2++) {
      var f = _fechaCol_(grid[filaFechas][c2]);
      if (f) cols.push({ c: c2, fecha: f });
    }

    // 2) La fila "INGRESOS" y el bloque que le sigue.
    var filaIng = -1;
    for (var r2 = 0; r2 < grid.length; r2++) {
      if (_norm_(grid[r2][0]) === 'INGRESOS') { filaIng = r2; break; }
    }
    if (filaIng < 0) {
      avisos.push('En "' + sh.getName() + '" no encontré la fila INGRESOS.');
      continue;
    }

    for (var rr = filaIng + 1; rr < grid.length; rr++) {
      var etiqueta = _norm_(grid[rr][0]);
      if (EXP_FIN_INGRESOS.indexOf(etiqueta) > -1) break;   // fin del bloque
      if (!etiqueta) continue;                              // fila separadora
      var meta = EXP_INGRESOS[etiqueta];
      if (!meta) avisos.push('Concepto de ingreso sin mapear en "' + sh.getName() + '": "' + grid[rr][0] + '"');
      for (var k = 0; k < cols.length; k++) {
        var v = _num_(grid[rr][cols[k].c]);
        if (!v) continue;
        out.push({
          fecha: cols[k].fecha,
          unidad: (meta && meta.unidad) || unidad,
          concepto: String(grid[rr][0]).trim(),
          importe: v,
          naturaleza: meta ? meta.naturaleza : 'VARIABLE',
          interno: meta ? !!meta.interno : false,
          efecto: 'caja',
          origen: sh.getName()
        });
      }
    }
  }
  if (!encontradas) avisos.push('No encontré solapas de cashflow (busco nombres con "cash" y "flow").');
  return out;
}

/**
 * Lee los bloques que están DEBAJO del "Saldo cierre" en los cashflow:
 *
 *   · Cobranza Droguería  -> lo que las droguerías NOS deben (DDS, SUIZO, COFALOZA...)
 *   · Deuda Droguería     -> lo que NOSOTROS les debemos (+ refinanciación, NCR)
 *
 * OJO — REGLA IMPORTANTE (confirmada con Thomas):
 * "Cobranza Droguería" NO es caja: es un derecho de cobro. Cuando la droguería
 * paga, el monto DESAPARECE de ahí y aparece en Cartera de CH (o baja deuda si el
 * cheque se endosó a otra droguería). Son estados mutuamente excluyentes, así que
 * NO hay que sumarlo a los cobros previstos: se contaría dos veces.
 *
 * Un monto con fecha PASADA que sigue ahí = esa droguería todavía no pagó (vencido).
 */
/** La fecha mas lejana de un conjunto de filas: sirve para ver hasta donde
 *  llega cargado un bloque, que es justo lo que no se estaba mirando. */
function _ultimaFecha_(filas) {
  var m = '';
  for (var i = 0; i < filas.length; i++) if (filas[i].fecha > m) m = filas[i].fecha;
  return m || '(sin fecha)';
}

/**
 * COMO ESTA DELIMITADO EL BLOQUE DE DROGUERIAS EN CADA HOJA.
 *
 * No todas las planillas arman el bloque igual, y eso no es un error de nadie:
 * son planillas que crecieron aparte. En este Cash conviven dos formas:
 *
 *   Cash Flow Diario-Speed  -> tiene encabezados propios
 *        Cobranza Drogueria / DDS, SUIZO, COFALOZA
 *        Deuda Drogueria    / SUIZO ARGENTINA, REFINANCIACION, DROG.DEL SUD
 *
 *   Cash Flow Diario -MAGA  -> NO tiene encabezado. Las droguerias cuelgan
 *        directo entre "Saldo cierre" y "Saldo con pago a droguerias".
 *
 * Por eso ninguna busqueda por rotulo iba a encontrar el de MAGA: no es que
 * este escrito distinto, es que no existe. Se declara donde empieza y donde
 * termina, y listo.
 *
 * Para un cliente nuevo se agrega una entrada aca y no se toca una linea de
 * codigo. La clave es el nombre de la hoja normalizado (mayusculas, sin
 * acentos); si no figura, se usa _default.
 */
var EXP_BLOQUES = {
  _default: {
    cobranza: { desde: 'COBRANZA DROGUERIA', hasta: ['DEUDA DROGUERIA'] },
    deuda:    { desde: 'DEUDA DROGUERIA',    hasta: ['COBRANZA DROGUERIA'] }
  },

  // OJO - SUPUESTO A VERIFICAR (05/09/2026):
  // en la hoja de MAGA se toman como DEUDA las filas entre "Saldo cierre" y
  // "Saldo con pago a droguerias" (COFALOZA, SUIZO y las NCR). Se asume que es
  // lo que MAGA LES DEBE, porque la linea siguiente es "saldo CON PAGO a
  // droguerias" -- o sea, el saldo si les pagara. Las NCR restan, como en el
  // resto del exportador.
  // Thomas dijo que la deuda de MAGA es ~$1.513M: si el numero que sale se
  // parece, el supuesto esta bien. Si no, revisar aca.
  'CASH FLOW DIARIO -MAGA': {
    deuda: { desde: 'SALDO CIERRE', hasta: ['SALDO CON PAGO A DROGUERIAS'] }
  }
};

function _leerBloquesDroguerias_(ss, avisos) {
  var cobrar = [], deuda = [], hojasCashflow = 0;
  var hoy = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd');
  var hojas = ss.getSheets();

  for (var i = 0; i < hojas.length; i++) {
    var sh = hojas[i];
    var nom = _norm_(sh.getName());
    if (nom.indexOf('CASH') < 0 || nom.indexOf('FLOW') < 0) continue;
    hojasCashflow++;
    // ERROR REAL (05/09/2026): esto decia
    //     if (!unidad) continue;
    // o sea que una hoja llamada "Cash Flow Diario" -- la de MAGA, sin la
    // palabra MAGA en el nombre -- se salteaba EN SILENCIO. El export se
    // llevaba solo la deuda de Speedmed, $2.690M, cuando la real entre las dos
    // unidades era $5.466M. Faltaba el 51% de la deuda y no habia un solo aviso.
    //
    // Ahora, si no se puede deducir la unidad, se usa el nombre de la hoja y se
    // AVISA. Una hoja de cashflow que existe y no se lee es lo peor que puede
    // pasar: el numero final sale prolijo y esta a la mitad.
    var unidad = (nom.indexOf('SPEED') > -1) ? 'SPEEDMED'
               : (nom.indexOf('MAGA') > -1) ? 'MAGA' : '';
    if (!unidad) {
      unidad = sh.getName().trim();
      avisos.push('La hoja "' + sh.getName() + '" parece un cashflow pero su ' +
                  'nombre no dice SPEED ni MAGA. La lei igual y le puse la ' +
                  'unidad "' + unidad + '". Verificar que sea correcto.');
    }

    var maxR = sh.getLastRow(), maxC = sh.getLastColumn();
    if (maxR < 2 || maxC < 2) continue;
    var grid = sh.getRange(1, 1, maxR, maxC).getValues();

    // fila de fechas + columnas-fecha (igual que en ingresos)
    var filaFechas = -1, mejor = 0;
    for (var r = 0; r < Math.min(grid.length, 15); r++) {
      var n = 0;
      for (var c = 1; c < grid[r].length; c++) if (_fechaCol_(grid[r][c])) n++;
      if (n > mejor) { mejor = n; filaFechas = r; }
    }
    if (filaFechas < 0 || mejor < 3) continue;
    var cols = [];
    for (var c2 = 1; c2 < grid[filaFechas].length; c2++) {
      var f = _fechaCol_(grid[filaFechas][c2]);
      if (f) cols.push({ c: c2, fecha: f });
    }

    // NOS DEBEN: si la fecha ya pasó y el monto sigue ahí, es que NO cobramos -> VENCIDO.
    // Que bloques tiene ESTA hoja y como estan delimitados.
    var def = EXP_BLOQUES[_norm_(sh.getName())] || EXP_BLOQUES._default;
    var defCobranza = def.cobranza || null;
    var defDeuda = def.deuda || null;

    var cobrarHoja = [];
    if (defCobranza) {
      cobrarHoja = _filasDeBloque_(grid, cols, defCobranza.desde,
        defCobranza.hasta, unidad, sh.getName(), hoy,
        { pasado: 'VENCIDO', futuro: 'A_VENCER' });
    }
    cobrar = cobrar.concat(cobrarHoja);

    // LES DEBEMOS: si la fecha ya pasó, ese pago YA SE HIZO -> PAGADO (no es deuda viva).
    var deudaHoja = [];
    if (defDeuda) {
      deudaHoja = _filasDeBloque_(grid, cols, defDeuda.desde,
        defDeuda.hasta, unidad, sh.getName(), hoy,
        { pasado: 'PAGADO', futuro: 'PENDIENTE' });
    }
    deuda = deuda.concat(deudaHoja);

    // SE INFORMA SIEMPRE, aunque haya salido todo bien.
    //
    // El export anterior solo avisaba si no encontraba NADA. Como la hoja de
    // Speed si daba resultados, el aviso nunca se disparaba y la ausencia
    // completa de MAGA paso desapercibida. Un resumen de lo leido por hoja
    // habria hecho evidente el agujero en el primer vistazo.
    avisos.push('Cashflow "' + sh.getName() + '" (' + unidad + '): ' +
                cobrarHoja.length + ' fila(s) de cobranza y ' +
                deudaHoja.length + ' de deuda' +
                (deudaHoja.length ? ', hasta ' + _ultimaFecha_(deudaHoja) : '') +
                '. Columnas con fecha: ' + cols.length +
                '. Bloques: ' + (EXP_BLOQUES[_norm_(sh.getName())] ?
                   'definicion propia' : 'definicion por defecto') + '.');

    // Una hoja de cashflow con columnas de fecha pero SIN filas es la senal de
    // que el rotulo del bloque se llama distinto. En vez de dejar que alguien lo
    // adivine mirando la planilla, se listan los rotulos que si tiene.
    if (!cobrarHoja.length && !deudaHoja.length && cols.length > 3) {
      avisos.push('  OJO: "' + sh.getName() + '" tiene ' + cols.length +
                  ' columnas de fecha pero no encontre los bloques. Los rotulos ' +
                  'que SI tiene son: ' + _rotulosDe_(grid).join(' | '));
    }
  }
  if (!cobrar.length && !deuda.length) {
    avisos.push('No encontré los bloques "Cobranza Droguería" / "Deuda Droguería" en los cashflow.');
  }
  if (hojasCashflow === 0) {
    avisos.push('No encontré NINGUNA hoja de cashflow (nombre con "cash" y "flow").');
  }
  return { cuentas_a_cobrar_droguerias: cobrar, deuda_droguerias: deuda };
}

/** Lee las filas de un bloque etiquetado, hasta otra etiqueta o 3 filas vacías.
 *  etiquetasEstado = {pasado: '...', futuro: '...'} porque el significado de una
 *  fecha pasada cambia según el bloque (ver comentario más abajo). */
/**
 * Ubica un bloque por su rotulo, con tolerancia.
 *
 * POR QUE NO ALCANZA LA IGUALDAD EXACTA EN LA COLUMNA A:
 * el export encontro la hoja "Cash Flow Diario -MAGA" con sus 217 columnas de
 * fecha y devolvio CERO filas de cobranza y CERO de deuda, cuando esa hoja
 * tiene deuda. El bloque esta; lo que no coincidia era como se busca el rotulo.
 *
 * Un rotulo se escribe distinto en cada planilla: "Deuda Drogueria", "Deuda
 * Droguerias", con la etiqueta corrida una columna, con un espacio de mas. Nada
 * de eso deberia costar una jornada de diagnostico.
 *
 * Devuelve {fila, col} o null.
 */
function _buscarBloque_(grid, etiqueta) {
  var COLS = 4;   // el rotulo puede estar corrido a la derecha
  // 1) igual, que es lo mas seguro
  for (var r = 0; r < grid.length; r++) {
    for (var c = 0; c < Math.min(COLS, grid[r].length); c++) {
      if (_norm_(grid[r][c]) === etiqueta) return { fila: r, col: c };
    }
  }
  // 2) empieza con el rotulo: cubre plurales y sufijos ("Deuda Drogueria (Speed)")
  for (var r2 = 0; r2 < grid.length; r2++) {
    for (var c2 = 0; c2 < Math.min(COLS, grid[r2].length); c2++) {
      var v = _norm_(grid[r2][c2]);
      if (v && v.indexOf(etiqueta) === 0) return { fila: r2, col: c2 };
    }
  }
  return null;
}

/** Los rotulos de texto que hay en una hoja: para poder decir que SI habia
 *  cuando no se encuentra el que se buscaba. */
function _rotulosDe_(grid) {
  var out = [], vistos = {};
  for (var r = 0; r < grid.length; r++) {
    for (var c = 0; c < Math.min(3, grid[r].length); c++) {
      var v = String(grid[r][c] == null ? '' : grid[r][c]).trim();
      if (v.length < 4 || v.length > 40) continue;
      if (!isNaN(Number(v.replace(/[.,$]/g, '')))) continue;   // no numeros
      if (vistos[v]) continue;
      vistos[v] = 1;
      out.push(v);
      if (out.length >= 40) return out;
    }
  }
  return out;
}

function _filasDeBloque_(grid, cols, etiquetaInicio, etiquetasFin, unidad, hoja, hoy, etiquetasEstado) {
  var out = [];
  var pos = _buscarBloque_(grid, etiquetaInicio);
  if (!pos) return out;
  var inicio = pos.fila, colEtq = pos.col;

  var vacios = 0;
  for (var rr = inicio + 1; rr < grid.length; rr++) {
    var etiqueta = String(grid[rr][colEtq] == null ? '' : grid[rr][colEtq]).trim();
    if (!etiqueta) {
      vacios++;
      if (vacios >= 3) break;   // se terminó el bloque
      continue;
    }
    var etqNorm = _norm_(etiqueta);
    if (etiquetasFin.indexOf(etqNorm) > -1) break;
    vacios = 0;

    // Filas de SALDO calculado (ej "Con pago a droguerías"): no son movimientos,
    // repiten un saldo en cada columna. Sumarlas da cifras absurdas -> se saltean.
    if (_esFilaDerivada_(etqNorm)) continue;

    var esIntercompany = (etqNorm === 'MAGA+' || etqNorm === 'MAGA' || etqNorm === 'SPEEDMED');
    var esSaldo = _esFilaSaldo_(etqNorm);   // arrastra el mismo saldo día a día
    // Las NCR SIEMPRE restan, se hayan cargado como se hayan cargado.
    //
    // ERROR REAL (05/09/2026): esto hacia "v * -1" para las filas de credito.
    // Pero en esta planilla algunas NCR ya estan cargadas en NEGATIVO y otras en
    // positivo -- depende de quien las cargo. Multiplicar por -1 las que ya
    // venian negativas las volvia POSITIVAS, o sea que SUMABAN a la deuda en vez
    // de restarla. Eran $435.000.000 de mas solo en MAGA.
    //
    // Por eso no se invierte el signo: se FUERZA. Una nota de credito baja la
    // deuda, y como este cargada en la planilla no cambia eso.
    var esCred = _esCredito_(etqNorm);

    var deLaFila = [];
    for (var k = 0; k < cols.length; k++) {
      var v = _num_(grid[rr][cols[k].c]);
      if (!v) continue;
      deLaFila.push({
        fecha: cols[k].fecha,
        contraparte: etiqueta,
        importe: esCred ? -Math.abs(v) : v,
        unidad: unidad,
        intercompany: esIntercompany,
        es_saldo: esSaldo,
        es_credito: esCred,
        // OJO: el significado de la fecha CAMBIA según el bloque.
        //  · Nos deben (cobranza): fecha pasada = todavía no cobramos -> VENCIDO
        //  · Les debemos (deuda) : fecha pasada = ya se pagó         -> PAGADO
        estado: (cols[k].fecha < hoy) ? etiquetasEstado.pasado : etiquetasEstado.futuro,
        origen: hoja
      });
    }

    // Si es una fila de saldo, no se suma: vale solo el último valor.
    if (esSaldo && deLaFila.length) {
      deLaFila.sort(function (a, b) { return a.fecha < b.fecha ? -1 : 1; });
      out.push(deLaFila[deLaFila.length - 1]);
    } else {
      out = out.concat(deLaFila);
    }
  }
  return out;
}

/**
 * Encabezado de columna -> 'AAAA-MM-DD', o null si no es una fecha.
 * En el cashflow las columnas vienen como '4-9' (sin año) -> se asume el año en curso,
 * igual que hace la Calculadora.
 */
function _fechaCol_(v) {
  if (v instanceof Date) return Utilities.formatDate(v, Session.getScriptTimeZone(), 'yyyy-MM-dd');
  var s = String(v == null ? '' : v).trim();
  var m = s.match(/^(\d{1,2})[\/\-.](\d{1,2})(?:[\/\-.](\d{2,4}))?$/);
  if (!m) return null;
  var d = parseInt(m[1], 10), mes = parseInt(m[2], 10);
  var y = m[3] ? parseInt(m[3], 10) : (new Date()).getFullYear();
  if (y < 100) y += 2000;
  if (mes < 1 || mes > 12 || d < 1 || d > 31) return null;
  return Utilities.formatDate(new Date(y, mes - 1, d), Session.getScriptTimeZone(), 'yyyy-MM-dd');
}

/**
 * La caja de hoy, buscada POR ETIQUETA y no por celda fija.
 *
 * Antes esto leia SALDOS!C26 a secas. Dos problemas:
 *
 *   1. Una celda fija se rompe sola. Alcanza con que alguien inserte una fila
 *      arriba para que el export empiece a traer otro numero, sin error y sin
 *      aviso. (Ya habia pasado lo mismo en el clasificador con getRange(3,2).)
 *
 *   2. Traia solo el TOTAL. Debajo, en la misma columna, estan los subtotales
 *      por unidad -- SPEEDMED y MAGA -- y el informe los necesita: son dos
 *      empresas con cajas distintas, no una sola bolsa.
 *
 * Ahora se recorre la solapa buscando las etiquetas en las primeras columnas y
 * se toma el primer numero que haya a la derecha. Si no aparece la etiqueta del
 * total, recien ahi se cae a la celda fija, y se avisa.
 */
function _leerCajaPorUnidad_(ss, avisos) {
  var out = { total: 0, efectivo: 0, por_unidad: {} };
  var sh = ss.getSheetByName(EXP_CONFIG.TAB_SALDOS);
  if (!sh) { avisos.push('No existe la solapa "' + EXP_CONFIG.TAB_SALDOS + '".'); return out; }

  var maxR = sh.getLastRow(), maxC = Math.min(sh.getLastColumn(), 12);
  if (maxR < 1 || maxC < 1) return out;
  var grid = sh.getRange(1, 1, maxR, maxC).getValues();

  for (var r = 0; r < grid.length; r++) {
    for (var c = 0; c < Math.min(grid[r].length, 4); c++) {
      var et = _norm_(grid[r][c]);
      if (!et) continue;
      if (et !== 'TOTAL' && et !== 'EFECTIVO' &&
          et !== 'SPEEDMED' && et !== 'MAGA') continue;
      // el primer numero a la derecha de la etiqueta
      for (var k = c + 1; k < grid[r].length; k++) {
        var v = _num_(grid[r][k]);
        if (v) {
          if (et === 'TOTAL') out.total = v;
          else if (et === 'EFECTIVO') out.efectivo = v;
          else out.por_unidad[et] = v;
          break;
        }
      }
    }
  }

  if (!out.total) {
    try {
      var partes = EXP_CONFIG.CAJA_HOY_REF.split('!');
      var sh2 = ss.getSheetByName(partes[0]);
      if (sh2) out.total = _num_(sh2.getRange(partes[1]).getValue());
      avisos.push('No encontre la fila "TOTAL" en ' + EXP_CONFIG.TAB_SALDOS +
                  '. Use la celda fija ' + EXP_CONFIG.CAJA_HOY_REF +
                  ': verificar que siga siendo la correcta.');
    } catch (e2) {
      avisos.push('No pude leer la caja de hoy: ' + e2);
    }
  }

  // La suma de las unidades MAS el efectivo tiene que dar el total. Si no, hay
  // una unidad que no estamos leyendo -- que es exactamente lo que paso con la
  // deuda de MAGA: el numero salia prolijo y le faltaba la mitad.
  //
  // El efectivo va aparte a proposito: en esta grilla los subtotales por unidad
  // cubren solo los bancos, y el efectivo esta en su propia fila. Sin esa
  // distincion el chequeo ladraba por los $20.000.000 de efectivo, que estan
  // perfectamente bien.
  var suma = 0, n = 0;
  for (var u in out.por_unidad) { suma += out.por_unidad[u]; n++; }
  var dif = out.total - (suma + out.efectivo);
  if (n && out.total && Math.abs(dif) > 1) {
    avisos.push('Los subtotales por unidad (' + Math.round(suma) + ') mas el ' +
                'efectivo (' + Math.round(out.efectivo) + ') dan ' +
                Math.round(suma + out.efectivo) + ', pero el TOTAL dice ' +
                Math.round(out.total) + '. Diferencia: ' + Math.round(dif) +
                '. Falta alguna unidad o hay una fila de mas.');
  }
  avisos.push('Caja: total ' + Math.round(out.total) + ' = bancos por unidad (' +
              Object.keys(out.por_unidad).join(', ') + ') + efectivo ' +
              Math.round(out.efectivo) + '.');
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
/** Resumen de un bloque de droguerías: total vencido vs a vencer, por contraparte. */
function _logDrog_(titulo, filas) {
  filas = filas || [];
  Logger.log('--- %s: %s registros ---', titulo, filas.length);
  if (!filas.length) return;
  // OJO: el Logger de Apps Script NO soporta formatos tipo '%-10s' (los imprime
  // literales). Solo %s / %d. Por eso acá se arma el texto con concatenación.
  var porEstado = {}, inter = 0, porC = {};
  filas.forEach(function (x) {
    if (x.intercompany) { inter += x.importe; return; }   // aparte: no es con terceros
    porEstado[x.estado] = (porEstado[x.estado] || 0) + x.importe;
    var k = x.estado + ' | ' + x.contraparte;
    porC[k] = (porC[k] || 0) + x.importe;
  });
  Object.keys(porEstado).sort().forEach(function (e) {
    Logger.log('   TOTAL ' + e + ' (terceros): ' + Math.round(porEstado[e]));
  });
  if (inter) Logger.log('   INTERCOMPANY (saldo, no se suma): ' + Math.round(inter));
  Object.keys(porC).sort().forEach(function (k) {
    Logger.log('   · ' + k + ': ' + Math.round(porC[k]));
  });
}

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
