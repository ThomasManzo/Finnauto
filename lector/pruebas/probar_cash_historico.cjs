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

// Planilla de juguete: fechas de la fila 6 desde la columna B; la primera vacía es el modelo.
let fechas, corte, ops;
const h = {
  getLastColumn: () => fechas.length + 1,
  getLastRow: () => 160,
  getColumnWidth: () => 92,
  setColumnWidths: () => {}, showColumns: () => {}, hideColumns: () => {},
  insertColumnsBefore: (c, n) => { ops.push(['insertar', c, n]); fechas.splice(c - 2, 0, ...Array(n).fill('')); },
  getRange(r, c, nr = 1, nc = 1) {
    return {
      coords: [r, c, nr, nc],
      getValue: () => r === 3 ? corte : fechas[c - 2],
      getValues: () => [[...fechas]],
      setValues(v) { v[0].forEach((x, i) => { fechas[c - 2 + i] = x; }); return this; },
      setNumberFormat() { return this; },
      copyTo(destino, tipo) { ops.push([tipo ? 'valores' : 'copia', [r, c, nr, nc], destino.coords]); }
    };
  }
};
let existe = true;
const ss = {
  getSpreadsheetTimeZone: () => 'America/Argentina/Buenos_Aires',
  getSheetByName: nombre => nombre === 'Cash histórico' ? (existe ? h : null) : null
};
ctx.SpreadsheetApp = {getActiveSpreadsheet: () => ss, flush() {}, CopyPasteType: {PASTE_VALUES: 'VALORES'}};
function preparar(dias, ultimo) { fechas = [...dias, '', '']; corte = ultimo; ops = []; }  // días · modelo · auxiliar

// Último día 01/11 y extracto al 11/11: faltan 02, 03 y 04/11, antes del modelo (columna E).
preparar([dia(1)], dia(11));
ctx._extenderHistorico_();
assert.deepEqual(ops[0], ['insertar', 3, 3]);
assert.deepEqual(ops[1], ['copia', [6, 6, 155, 1], [6, 3, 155, 3]]);      // una sola copia del modelo
assert.deepEqual(ops[2], ['valores', [6, 3, 155, 3], [6, 3, 155, 3]]);    // y quedan como valores
assert.deepEqual(fechas.slice(0, 4), [dia(1), dia(2), dia(3), dia(4)]);
assert.equal(fechas[4], '');                                             // el modelo sigue vacío
// Al día: no hace nada. Extracto que retrocede: tampoco.
ops = []; ctx._extenderHistorico_(); assert.equal(ops.length, 0);
corte = dia(8); ctx._extenderHistorico_(); assert.equal(ops.length, 0);
// Sin la solapa no hace nada.
existe = false; ctx._extenderHistorico_(); assert.equal(ops.length, 0); existe = true;
// Sin columna modelo (rota): avisa en vez de inventar.
fechas = [dia(1), dia(2)]; corte = dia(20); ops = [];
assert.throws(() => ctx._extenderHistorico_(), /modelo/);

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
