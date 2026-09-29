// Prueba con hojas inventadas: no accede a Google ni a datos reales.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const zona = 'America/Argentina/Buenos_Aires';
const Utilities = {
  formatDate(fecha, z, formato) {
    assert.equal(z, zona);
    assert.equal(formato, 'yyyy-MM-dd');
    return new Date(fecha.getTime() - 3 * 3600000).toISOString().slice(0, 10);
  },
  parseDate(dia, z, formato) {
    assert.equal(z, zona);
    assert.equal(formato, 'yyyy-MM-dd');
    return new Date(dia + 'T03:00:00Z');
  },
};
const contexto = vm.createContext({Date, Utilities, SpreadsheetApp: {flush() {}}});
vm.runInContext(fs.readFileSync(path.join(__dirname,
  '../../clientes/navar/herramientas/importar_cashflow.gs'), 'utf8'), contexto);

class Hoja {
  constructor(filas) { this.filas = filas.map(r => r.slice()); this.formatos = {}; }
  getFilter() { return null; }
  showRows() {}
  getMaxRows() { return 100; }
  getName() { return 'Ultimos Pagos'; }
  getLastColumn() { return this.filas[0].length; }
  getLastRow() { return this.filas.length; }
  getRange(fila, col, alto = 1, ancho = 1) {
    const h = this;
    return {
      getValues() {
        return Array.from({length: alto}, (_, i) => Array.from({length: ancho}, (_, j) =>
          h.filas[fila - 1 + i]?.[col - 1 + j] ?? ''));
      },
      setNumberFormat(formato) {
        for (let i = 0; i < alto; i++) h.formatos[`${fila + i},${col}`] = formato;
        return this;
      },
      setValues(valores) {
        valores.forEach((r, i) => r.forEach((v, j) => {
          // La identificación debe escribirse con formato texto ya aplicado.
          if ([3, 6].includes(col + j) && v !== '')
            assert.equal(h.formatos[`${fila + i},${col + j}`], '@');
          h.filas[fila - 1 + i] ??= [];
          h.filas[fila - 1 + i][col - 1 + j] = v;
        }));
        return this;
      },
      clearContent() { return this.setValues(Array.from({length: alto}, () => Array(ancho).fill(''))); },
    };
  }
}

const config = contexto.IMPORTS.ultimos_pagos;
assert.equal(config.prefijo, 'para_pegar_ultimos_pagos_');
assert.ok(contexto.ORDEN_AUTO.includes('ultimos_pagos'));
assert.equal(config.solapas.length, 1);
const cfg = config.solapas[0];
assert.equal(cfg.sheet, 'Ultimos Pagos');
assert.equal(cfg.xlsx, 'Ultimos Pagos');
assert.equal(cfg.conId, false);
assert.equal(cfg.formulas.length, 0);
assert.deepEqual(Array.from(cfg.texto), ['Codigo', 'Comprobante']);
assert.deepEqual(Array.from(cfg.fechas), ['Fecha Ultimo Pago']);
let pedido;
contexto._importarManual_ = cual => { pedido = cual; };
contexto.importarUltimosPagos();
assert.equal(pedido, 'ultimos_pagos');
const menu = [];
const ui = {addItem(texto, funcion) { menu.push([texto, funcion]); return this; },
  addSeparator() { return this; }, addToUi() {}};
contexto.SpreadsheetApp.getUi = () => ({createMenu: () => ui});
contexto.onOpen();
assert.ok(menu.some(([texto, funcion]) => texto === 'Importar Últimos pagos (Tango)' && funcion === 'importarUltimosPagos'));

const enc = ['Empresa', 'Tipo', 'Codigo', 'Razon Social', 'Fecha Ultimo Pago', 'Comprobante', 'Origen'];
const fecha = new Date('2026-09-29T07:00:00Z');
const manual = ['AA', 'Proveedor', '009', 'Manual ficticio', new Date('2026-09-01T03:00:00Z'), 'OPF 009', 'Manual'];
const otra = ['A', 'Cliente', '007', 'Otro origen', new Date('2026-09-01T03:00:00Z'), 'REC 007', 'Otro lector'];
const vieja = ['A', 'Cliente', '001', 'Anterior', fecha, 'REC 1', 'Tango tesorería · anterior.xlsx'];
const nueva = ['A', 'Cliente', '001 / 002', 'Cliente  Ejemplo', fecha, 'REC 00000000000000000123', 'Tango tesorería · A.xlsx'];
const origen = new Hoja([enc, nueva]);
const destino = new Hoja([enc, manual, vieja, vieja, otra]);
for (let vez = 0; vez < 2; vez++) {
  const r = contexto._volcar_(origen, destino, 1, 100, cfg, zona);
  assert.equal(r.borradas, vez === 0 ? 2 : 1);
  assert.equal(r.cargadas, 1);
  assert.deepEqual(destino.filas[1], manual);
  assert.deepEqual(destino.filas[2], otra);
  assert.equal(destino.filas[3][0], 'A');
  assert.equal(destino.filas[3][2], '001 / 002');
  assert.equal(destino.filas[3][5], 'REC 00000000000000000123');
  assert.ok(destino.filas[3][4] instanceof Date);
  assert.equal(destino.filas[3][4].toISOString(), '2026-09-29T03:00:00.000Z');
  assert.ok(destino.filas.slice(4).every(r => r.every(v => v === '')));
}
console.log('OK: Ultimos Pagos conserva filas manuales y otros orígenes, reemplaza su marca, mantiene texto y fechas y no duplica.');
