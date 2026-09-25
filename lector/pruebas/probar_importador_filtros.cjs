// Datos inventados: fuerza fallas que Google podría devolver sin tocar la Sheet.
// Comprueba nuestras decisiones, no reproduce el servicio de Google.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const contexto = vm.createContext({Date, SpreadsheetApp: {flush() {}}});
vm.runInContext(fs.readFileSync(path.join(__dirname,
  '../../clientes/navar/herramientas/importar_cashflow.gs'), 'utf8'), contexto);

class Hoja {
  constructor(filas) { this.filas = filas.map(r => r.map(v => v ?? '')); }
  getFilter() { return null; }
  showRows() {}
  getMaxRows() { return 1000; }
  getName() { return 'Cartera de Cheques'; }
  getLastColumn() { return Math.max(...this.filas.map(r => r.length)); }
  getLastRow() { return this.filas.length; }
  getRange(fila, columna, alto = 1, ancho = 1) {
    const hoja = this;
    return {
      getValues() {
        return Array.from({length: alto}, (_, i) => Array.from({length: ancho},
          (_, j) => hoja.filas[fila - 1 + i]?.[columna - 1 + j] ?? ''));
      },
      setValues(valores) {
        assert.equal(valores.length, alto);
        valores.forEach((r, i) => {
          assert.equal(r.length, ancho);
          hoja.filas[fila - 1 + i] ??= [];
          r.forEach((v, j) => { hoja.filas[fila - 1 + i][columna - 1 + j] = v; });
        });
      },
      clearContent() { this.setValues(Array.from({length: alto}, () => Array(ancho).fill(''))); }
    };
  }
}

const cfg = contexto.IMPORTS.tango.solapas[2];
function verificar(origen, destino, manuales = []) {
  const o = new Hoja(origen), d = new Hoja(destino);
  const resultado = contexto._volcar_(o, d, 1, 1000, cfg);
  const esperadas = manuales.concat(origen.slice(1).map(r => destino[0].map(nombre => {
    const indice = origen[0].indexOf(nombre);
    return indice < 0 ? '' : r[indice] ?? '';
  }))).map((r, i) => [i + 1, ...r.slice(1)]);
  assert.equal(resultado.cargadas, origen.length - 1);
  assert.equal(resultado.borradas, destino.length - 1 - manuales.length);
  assert.deepEqual(d.filas.slice(1, 1 + esperadas.length), esperadas);
  for (const r of d.filas.slice(1 + esperadas.length)) assert.ok(r.every(v => v === ''));
  // Una segunda pasada tiene que dar lo mismo y no duplicar lo manual.
  contexto._volcar_(o, d, 1, 1000, cfg);
  assert.deepEqual(d.filas.slice(1, 1 + esperadas.length), esperadas);
}

const enc = ['ID', 'Tipo', 'Fecha Pago / Cobro', 'Observaciones'];
const nueva = [1, 'Terceros Recibido', new Date('2026-10-10T00:00:00Z'), 'Tango Live'];
const vieja = [1, 'Terceros Recibido', new Date('2027-05-25T00:00:00Z'), 'Tango Live'];
verificar([enc, nueva], [enc, vieja, vieja]);
verificar([enc, nueva, nueva], [enc, vieja]);
const manual = [1, 'Propio Emitido', new Date('2026-11-01T00:00:00Z'), 'Manual'];
verificar([enc, nueva], [enc, manual, vieja], [manual]);
verificar([enc, nueva], [[...enc.slice(0, 2), enc[3], enc[2]],
  [1, vieja[1], vieja[3], vieja[2]]]);
console.log('OK: achicar, agrandar, conservar manuales, reordenar columnas y repetir. Datos inventados.');


// El filtro debe salir y las filas mostrarse ANTES de la primera escritura.
const hoja = new Hoja([enc, vieja]);
let removido = false, visible = false;
hoja.getFilter = () => removido ? null : {remove() { removido = true; }};
hoja.showRows = () => { visible = true; };
const rango = hoja.getRange.bind(hoja);
hoja.getRange = (...args) => {
  const r = rango(...args), escribir = r.setValues;
  r.setValues = function (valores) { assert.ok(removido && visible); escribir.call(this, valores); };
  return r;
};
contexto._volcar_(new Hoja([enc, nueva]), hoja, 1, 1000, cfg);

// Un error al sacar el filtro aborta sin modificar una sola celda.
const trabada = new Hoja([enc, vieja]);
trabada.getFilter = () => ({remove() { throw Error('sin permiso'); }});
assert.throws(() => contexto._volcar_(new Hoja([enc, nueva]), trabada, 1, 1000, cfg), /Cartera de Cheques.*sacá el filtro/);
assert.deepEqual(trabada.filas, [enc, vieja]);

// Una escritura que no falla pero cambia una fecha debe dar ERROR.
const corrupta = new Hoja([enc, vieja]);
const rangoCorrupto = corrupta.getRange.bind(corrupta);
corrupta.getRange = (...args) => {
  const r = rangoCorrupto(...args), escribir = r.setValues;
  r.setValues = function (valores) {
    escribir.call(this, valores);
    if (args[1] === 3) corrupta.filas[1][2] = new Date('2027-04-15T00:00:00Z');
  };
  return r;
};
assert.throws(() => contexto._volcar_(new Hoja([enc, nueva]), corrupta, 1, 1000, cfg), /VERIFICACION_NO_CUADRA.*fila 2.*Fecha/);
// Tarea 20: la Sheet guarda "10" como 10; eso es el mismo dato. Con ceros adelante, no.
assert.equal(contexto._mismoDato_(10, '10'), true);
assert.equal(contexto._mismoDato_(55, '0055'), false);
assert.equal(contexto._mismoDato_(3.3000953674800002e28, '033000953674800000000011381061'), false);
assert.equal(contexto._mismoDato_(new Date(0), new Date(0)), true);
assert.equal(contexto._mismoDato_(new Date(0), new Date(1)), false);

const ss = {getId: () => 'inventado'};
const destino = {getName: () => 'Movimientos', getSheetId: () => 7};
assert.throws(() => contexto._comprobarVistas_(ss, [destino]), /Movimientos.*no pude comprobar/);
contexto.Sheets = {Spreadsheets: {get: () => ({sheets: [{properties: {sheetId: 7}, filterViews: [{}]}]})}};
assert.throws(() => contexto._comprobarVistas_(ss, [destino]), /Movimientos.*vistas de filtro guardadas/);
contexto.Sheets.Spreadsheets.get = () => ({sheets: [{properties: {sheetId: 7}}]});
contexto._comprobarVistas_(ss, [destino]);
contexto.Sheets.Spreadsheets.get = () => ({sheets: []});
assert.throws(() => contexto._comprobarVistas_(ss, [destino]), /Movimientos.*no pude comprobar/);
console.log('OK: filtro, filas ocultas, bloqueo sin permisos/API, vistas y corrupción silenciosa.');

// Vaciar la lista también borra los restos; una cola sin borrar no puede dar ok.
verificar([enc], [enc, vieja]);
const cola = new Hoja([enc, vieja, vieja]);
const rangoCola = cola.getRange.bind(cola);
cola.getRange = (...args) => { const r = rangoCola(...args); r.clearContent = () => {}; return r; };
assert.throws(() => contexto._volcar_(new Hoja([enc, nueva]), cola, 1, 1000, cfg), /VERIFICACION_NO_CUADRA/);

// Los dos caminos anotan ERROR y el reloj no guarda la firma de algo fallido.
const registros = [], firmas = [];
contexto._ultimoConPrefijo_ = () => ({getName: () => 'inventado.xlsx', getId: () => '1', getLastUpdated: () => new Date(0)});
contexto._registrar_ = (...r) => registros.push(r);
contexto._importar_ = () => { throw Error('VERIFICACION_NO_CUADRA: Movimientos'); };
contexto.Logger = {log() {}};
contexto.PropertiesService = {getDocumentProperties: () => ({getProperty: () => null, setProperty: (...p) => firmas.push(p)})};
assert.throws(() => contexto._importarManual_('tango'), /VERIFICACION_NO_CUADRA/);
contexto.importarLoNuevo();
assert.equal(registros.length, 6);
assert.ok(registros.every(r => r[2] === 'ERROR' && r[3].includes('VERIFICACION_NO_CUADRA')));
assert.equal(firmas.length, 0);
console.log('OK: lista vacía, cola mal borrada, Registro manual/automático y firma sin avance.');

// El aviso destaca la falta de coincidencia sin mandar correos.
vm.runInContext(fs.readFileSync(path.join(__dirname,
  '../../clientes/navar/herramientas/aviso_diario.gs'), 'utf8'), contexto);
contexto._fechaAviso_ = () => '2026-09-22';
const ahora = new Date('2026-09-22T12:00:00Z');
const aviso = contexto._armarAviso_(ahora, {entradas: [], publicados: [], retenidos: [], log: [],
  extracto: ahora, errores: {}, registro: [{fecha: ahora, tipo: 'tango', estado: 'ERROR', detalle: 'VERIFICACION_NO_CUADRA: Cartera de Cheques'}]});
assert.ok(aviso.alertas.some(a => a.includes('NO CUADRÓ')));
console.log('OK: alerta explícita del aviso diario, sin enviar mails.');
