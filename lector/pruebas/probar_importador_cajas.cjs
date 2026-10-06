// Tarea 48. Prueba con hojas inventadas: no accede a Google ni a datos reales.
// Movimientos recibe las cajas de A y AA con dos columnas nuevas al final ("Cuenta Tango", "Leyenda");
// las filas de los bancos no las traen y no se rompen, y un import de bancos no borra las de caja.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const zona = 'America/Argentina/Buenos_Aires';
const Utilities = {
  formatDate(fecha, z, formato) { return new Date(fecha.getTime() - 3 * 3600000).toISOString().slice(0, 10); },
  parseDate(dia) { return new Date(dia + 'T03:00:00Z'); },
};
const contexto = vm.createContext({Date, Utilities, SpreadsheetApp: {flush() {}, CopyPasteType: {}}});
vm.runInContext(fs.readFileSync(path.join(__dirname,
  '../../clientes/navar/herramientas/importar_cashflow.gs'), 'utf8'), contexto);

class Hoja {
  constructor(filas) { this.filas = filas.map(r => r.slice()); this.columnas = filas[0].length; }
  getFilter() { return null; }
  showRows() {}
  getMaxRows() { return 100; }
  getMaxColumns() { return this.columnas; }
  insertColumnAfter() { this.columnas++; }
  getName() { return 'Movimientos'; }
  getLastColumn() { return Math.max(...this.filas.map(r => r.reduce((u, v, i) => v !== '' && v != null ? i + 1 : u, 0))); }
  getLastRow() { return this.filas.reduce((u, r, i) => r.some(v => v !== '' && v != null) ? i + 1 : u, 0); }
  getRange(fila, col, alto = 1, ancho = 1) {
    const h = this;
    const rango = {
      getValues() {
        return Array.from({length: alto}, (_, i) => Array.from({length: ancho}, (_, j) =>
          h.filas[fila - 1 + i]?.[col - 1 + j] ?? ''));
      },
      getFormula() { return ''; },
      setNumberFormat() { return rango; },
      setFontWeight() { return rango; },
      setValue(v) { return rango.setValues([[v]]); },
      setValues(valores) {
        assert.ok(col + ancho - 1 <= h.columnas, 'escribe fuera de la hoja');
        valores.forEach((r, i) => r.forEach((v, j) => {
          h.filas[fila - 1 + i] ??= [];
          h.filas[fila - 1 + i][col - 1 + j] = v;
        }));
        return rango;
      },
      clearContent() { return rango.setValues(Array.from({length: alto}, () => Array(ancho).fill(''))); },
    };
    return rango;
  }
}

// Configuración: entra sola cada hora y reemplaza a tesoreria_aa.
const cfg = contexto.IMPORTS.cajas;
assert.equal(cfg.prefijo, 'para_pegar_cajas_');
assert.ok(contexto.ORDEN_AUTO.includes('cajas'));
assert.ok(!contexto.ORDEN_AUTO.includes('tesoreria_aa'), 'si corren las dos, la caja de AA se cuenta doble');
const s = cfg.solapas[0];
assert.deepEqual(Array.from(s.marcas), ['Tango AA', 'Tango caja A']);
assert.ok(s.texto.includes('Leyenda') && s.texto.includes('Cuenta Tango'));
let pedido;
contexto._importarManual_ = cual => { pedido = cual; };
contexto.importarCajas();
assert.equal(pedido, 'cajas');

const ENC = ['ID', 'Fecha', 'Empresa', 'Tipo', 'Categoria', 'Concepto / Detalle', 'Importe', 'Medio de Pago',
  'Banco / Cuenta', 'Origen', 'Estado', 'Referencia', 'Semana (lunes)', 'Observaciones'];
const f = new Date('2026-10-01T03:00:00Z');
const fila = (o) => ENC.map(c => o[c] ?? '');
const manual = fila({ID: 1, Fecha: f, Empresa: 'A', Tipo: 'Egreso', Categoria: 'Otros', Importe: -10, 'Banco / Cuenta': 'Banco X', Origen: 'Manual'});
const extracto = fila({ID: 2, Fecha: f, Empresa: 'A', Tipo: 'Ingreso', Categoria: 'Otros', Importe: 500, 'Banco / Cuenta': 'Banco X', Origen: 'Extracto banco x', Referencia: '0001'});
const cajaVieja = fila({ID: 3, Fecha: f, Empresa: 'AA', Tipo: 'Egreso', Categoria: 'Otros', Importe: -7, 'Banco / Cuenta': 'Caja AA', Origen: 'Tango AA · viejo.xlsx'});
const destino = new Hoja([ENC, manual, extracto, cajaVieja]);

const ENC2 = ENC.concat(['Cuenta Tango', 'Leyenda']);
const cajaA = ['', f, 'A', 'Egreso', 'Otros', 'VIATICOS INVENTADOS', -120, 'Efectivo', 'Caja A',
  'Tango caja A · cajas · A.xlsx', 'Real', 'OPF 0000-00001', '', 'Tango', 'CAJA CHICA', 'VIATICOS INVENTADOS'];
const cajaAA = ['', f, 'AA', 'Ingreso', 'Cobranza AA', 'CLIENTE INVENTADO', 300, 'Efectivo', 'Caja AA',
  'Tango AA · cajas · AA.xlsx', 'Real', 'REC 0000-00002', '', 'Tango', 'CAJA FUERTE', ''];
const origen = new Hoja([ENC2, cajaA, cajaAA]);

for (let vez = 0; vez < 2; vez++) {
  const r = contexto._volcar_(origen, destino, 1, 100, s, zona);
  assert.equal(r.borradas, vez === 0 ? 1 : 2);     // la primera vez, solo la caja vieja de AA
  assert.equal(r.cargadas, 2);
  assert.deepEqual(destino.filas[0].slice(0, 16), ENC2, 'las dos columnas nuevas, al final');
  const col = n => ENC2.indexOf(n);
  const filas = destino.filas.slice(1).filter(x => x[col('Empresa')]);
  assert.equal(filas.length, 4);
  // Lo manual y el extracto quedan, con las columnas nuevas vacías.
  for (const origenFila of ['Manual', 'Extracto banco x']) {
    const x = filas.find(x => x[col('Origen')] === origenFila);
    assert.ok(x, origenFila);
    assert.equal(x[col('Cuenta Tango')], '');
    assert.equal(x[col('Leyenda')], '');
  }
  const a = filas.find(x => String(x[col('Origen')]).startsWith('Tango caja A'));
  assert.equal(a[col('Cuenta Tango')], 'CAJA CHICA');
  assert.equal(a[col('Leyenda')], 'VIATICOS INVENTADOS');
  assert.equal(a[col('Importe')], -120);
  assert.ok(!filas.some(x => x[col('Origen')] === 'Tango AA · viejo.xlsx'), 'la caja vieja de AA se reemplaza');
  assert.deepEqual(filas.map(x => x[0]), [1, 2, 3, 4], 'ID de corrido');
}

// Después importan los bancos (sin las columnas nuevas): las cajas quedan con su cuenta y leyenda.
const bancos = contexto.IMPORTS.bancos.solapas.find(x => x.sheet === 'Movimientos');
const extractoNuevo = fila({Fecha: f, Empresa: 'A', Tipo: 'Ingreso', Categoria: 'Otros', Importe: 800, 'Banco / Cuenta': 'Banco X', Origen: 'Extracto banco x', Referencia: '0002'});
contexto._volcar_(new Hoja([ENC, extractoNuevo]), destino, 1, 100, bancos, zona);
const col = n => ENC2.indexOf(n);
const filas = destino.filas.slice(1).filter(x => x[col('Empresa')]);
assert.equal(filas.length, 4);
assert.equal(filas.find(x => x[col('Origen')] === 'Extracto banco x')[col('Importe')], 800);
assert.equal(filas.find(x => String(x[col('Origen')]).startsWith('Tango caja A'))[col('Leyenda')], 'VIATICOS INVENTADOS');
assert.equal(filas.find(x => String(x[col('Origen')]).startsWith('Tango AA'))[col('Cuenta Tango')], 'CAJA FUERTE');
console.log('OK: cajas de A y AA en Movimientos con "Cuenta Tango" y "Leyenda"; bancos y manuales intactos; repetir no duplica.');
