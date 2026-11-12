// Todo inventado: fechas y una planilla de juguete, sin servicios ni datos reales.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const fuente = fs.readFileSync(path.join(__dirname, '../../clientes/navar/herramientas/crear_cash.gs'), 'utf8');
const ctx = vm.createContext({});
vm.runInContext(fuente, ctx);
const dia = n => (Date.UTC(2026, 10, n) - Date.UTC(1899, 11, 30)) / 86400000;
assert.equal(ctx._cuantasColumnasHistorico_(dia(1), dia(11), 7), 3);
assert.equal(ctx._cuantasColumnasHistorico_(dia(4), dia(11), 7), 0);
assert.equal(ctx._cuantasColumnasHistorico_(dia(4), dia(8), 7), 0);
assert.equal(ctx._cuantasColumnasHistorico_(0, dia(11), 7), 0);
assert.equal(ctx._cuantasColumnasHistorico_(NaN, dia(11), 7), 0);

let fechas, corte, copias, inserciones, ocultas, ancho;
const datos = [['Fecha', 'Origen'], [dia(1), 'Extracto BANCO FICTICIO'], [dia(-10), 'Tango caja A'], [dia(2), 'extracto OTRO FICTICIO']];
const h = {
  getLastColumn: () => fechas.length + 2, // al final está la auxiliar sin fecha
  getLastRow: () => 160,
  getColumnWidth: () => 92,
  setColumnWidths: (...args) => { ancho = args; },
  showColumns: () => {}, hideColumns: c => ocultas.push(c),
  insertColumnsAfter: (c, n) => { inserciones.push([c, n]); },
  getRange(r, c, nr = 1, nc = 1) {
    return {
      getValue: () => r === 3 ? corte : fechas[c - 2],
      getValues: () => [[...fechas, '']],
      setValue(v) { fechas[c - 2] = v; return this; },
      setNumberFormat() { return this; },
      copyTo(destino) { copias.push({origen: [r, c, nr, nc], destino: destino.coords}); },
      setFormulasR1C1(f) {
        assert.equal(f.length, 1); assert.equal(f[0].length, nc);
        f[0].forEach((formula, i) => {
          assert.equal(formula, '=RC[-1]+1');
          fechas[c - 2 + i] = fechas[c - 3 + i] + 1;
        });
      }, coords: [r, c, nr, nc]
    };
  }
};
let existe = true;
const ss = {
  getSpreadsheetTimeZone: () => 'America/Argentina/Buenos_Aires',
  getSheetByName: nombre => nombre === 'Cash histórico' ? (existe ? h : null) : {getDataRange: () => ({getValues: () => datos.map(f => [...f])})}
};
ctx.SpreadsheetApp = {getActiveSpreadsheet: () => ss, flush() {}};
function preparar(semilla, ultimo = dia(11)) {
  fechas = semilla; corte = ultimo; copias = []; inserciones = []; ocultas = [];
}
preparar([dia(1)]);
ctx._extenderHistorico_();
assert.deepEqual(inserciones, [[2, 3]]);
assert.deepEqual(copias, [{origen: [6, 2, 155, 1], destino: [6, 3, 155, 3]}]);
assert.deepEqual(fechas, [dia(1), dia(2), dia(3), dia(4)]);
assert.deepEqual(ancho, [3, 3, 92]);
copias = []; inserciones = [];
ctx._extenderHistorico_();
assert.equal(copias.length, 0); assert.equal(inserciones.length, 0);
corte = dia(8); ctx._extenderHistorico_(); assert.equal(copias.length, 0);
preparar(['']); ctx._extenderHistorico_();
assert.equal(fechas[0], dia(1)); assert.equal(copias.length, 1);
preparar([''], dia(5)); ctx._extenderHistorico_();
assert.deepEqual(ocultas, [2]); assert.equal(fechas[0], ''); assert.equal(copias.length, 0);
existe = false; ctx._extenderHistorico_(); assert.equal(copias.length, 0);
// Las referencias relativas al acuerdo se fijan sin duplicar los $ existentes.
const letra = 'AK';
const fijar = f => f.replace(new RegExp('(\\$?)\\b' + letra + '(\\$?[0-9]+)', 'g'), '$' + letra + '$2');
assert.equal(fijar('=SUM(AK10:AK12)+N($AK10)'), '=SUM($AK10:$AK12)+N($AK10)');

// Una falla histórica no interrumpe la exportación ni cambia el resultado de importar.
const importador = fs.readFileSync(path.join(__dirname, '../../clientes/navar/herramientas/importar_cashflow.gs'), 'utf8');
const llamadas = [];
const imp = vm.createContext({Logger: {log: s => llamadas.push(s)}, PropertiesService: {getDocumentProperties: () => ({getProperty: () => '', setProperty() {}})}});
vm.runInContext(importador, imp);
Object.assign(imp, {
  ORDEN_AUTO: ['inventado'], IMPORTS: {inventado: {prefijo: 'inventado'}},
  _conUnReintento_: f => f(), _ultimoConPrefijo_: () => ({getId: () => 'ficcion', getLastUpdated: () => new Date(0), getName: () => 'inventado'}),
  _importar_: () => 'ok', _registrar_: () => {},
  _extenderHistorico_: () => { llamadas.push('historico'); throw Error('falla inventada'); },
  exportarParaTablero: () => llamadas.push('exportar')
});
assert.equal(imp.importarLoNuevo(), 1);
assert.equal(llamadas[0], 'historico');
assert.match(llamadas[1], /Cash histórico: falla inventada/);
assert.equal(llamadas[2], 'exportar');
console.log('OK: fechas, copia única, auxiliar, ausencia de historia, repetición e importación aislada.');
