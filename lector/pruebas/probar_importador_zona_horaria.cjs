// Prueba con datos inventados el salto que ocurría entre una temporal UTC-7
// y la Sheet destino UTC-3. No llama a Google ni toca la planilla real.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');

const ZONAS = {
  'America/Los_Angeles': -7,
  'America/Argentina/Buenos_Aires': -3,
};
const dos = n => String(n).padStart(2, '0');
const Utilities = {
  formatDate(fecha, zona, formato) {
    const local = new Date(fecha.getTime() + ZONAS[zona] * 60 * 60 * 1000);
    const dia = `${local.getUTCFullYear()}-${dos(local.getUTCMonth() + 1)}-${dos(local.getUTCDate())}`;
    if (formato === 'yyyy-MM-dd') return dia;
    if (formato === 'yyyy-MM-dd HH:mm') return `${dia} ${dos(local.getUTCHours())}:${dos(local.getUTCMinutes())}`;
    throw new Error(`Formato no simulado: ${formato}`);
  },
  parseDate(texto, zona, formato) {
    assert.equal(formato, 'yyyy-MM-dd');
    const [anio, mes, dia] = texto.split('-').map(Number);
    return new Date(Date.UTC(anio, mes - 1, dia) - ZONAS[zona] * 60 * 60 * 1000);
  },
};

const contexto = vm.createContext({Date, Utilities, SpreadsheetApp: {flush() {}}});
vm.runInContext(fs.readFileSync(path.join(__dirname,
  '../../clientes/navar/herramientas/importar_cashflow.gs'), 'utf8'), contexto);

// La temporal debe tomar la zona destino antes de que se consulte una solapa.
const eventos = [];
const origenTemporal = {
  setSpreadsheetTimeZone(zona) { eventos.push(['zona', zona]); },
  getSheetByName(nombre) { eventos.push(['leer', nombre]); return {}; },
};
const hojaDestino = {getMaxRows: () => 100};
const destinoTemporal = {
  getSpreadsheetTimeZone: () => 'America/Argentina/Buenos_Aires',
  getSheetByName: () => hojaDestino,
  toast() {},
};
contexto.IMPORTS.pruebaZona = {prefijo: 'inventado_', solapas: [{xlsx: 'Datos', sheet: 'Destino'}]};
contexto.Drive = {Files: {
  copy: () => ({id: 'temporal'}),
  remove: () => eventos.push(['borrar']),
}};
contexto.MimeType = {GOOGLE_SHEETS: 'sheet'};
contexto.Logger = {log() {}};
contexto.SpreadsheetApp.openById = () => origenTemporal;
contexto.SpreadsheetApp.getActiveSpreadsheet = () => destinoTemporal;
contexto._comprobarVistas_ = () => {};
contexto._quitarFiltros_ = () => {};
const volcarReal = contexto._volcar_;
contexto._volcar_ = (origen, destino, inicio, fin, cfg, zona) => {
  assert.equal(zona, 'America/Argentina/Buenos_Aires');
  return {borradas: 0, cargadas: 1};
};
contexto._importarConLock_('pruebaZona', {
  getName: () => 'inventado.xlsx', getLastUpdated: () => new Date(0), getId: () => 'archivo',
});
assert.deepEqual(eventos.slice(0, 2), [
  ['zona', 'America/Argentina/Buenos_Aires'], ['leer', 'Datos'],
]);
contexto._volcar_ = volcarReal;

assert.deepEqual(Array.from(contexto.IMPORTS.tango.solapas[0].fechas), ['Fecha Emision', 'Fecha Vencimiento']);
assert.deepEqual(Array.from(contexto.IMPORTS.tango.solapas[1].fechas), ['Fecha Emision', 'Fecha Vencimiento']);
assert.deepEqual(Array.from(contexto.IMPORTS.tango.solapas[2].fechas), ['Fecha Emision', 'Fecha Pago / Cobro']);
assert.deepEqual(Array.from(contexto.IMPORTS.bancos.solapas[0].fechas), ['Fecha']);
assert.deepEqual(Array.from(contexto.IMPORTS.bancos.solapas[1].fechas), ['Fecha']);
assert.deepEqual(Array.from(contexto.IMPORTS.tesoreria_aa.solapas[0].fechas), ['Fecha']);
assert.deepEqual(Array.from(contexto.IMPORTS.impuestos.solapas[0].fechas), ['Fecha Vencimiento']);
assert.deepEqual(Array.from(contexto.IMPORTS.deuda.bloques[0].fechas), ['Fecha Otorgamiento', 'Fecha Vto. Final']);
assert.deepEqual(Array.from(contexto.IMPORTS.deuda.bloques[1].fechas), ['Fecha Vencimiento']);

// Hoja mínima en memoria para probar el volcado y su lectura posterior.
class Hoja {
  constructor(nombre, filas) { this.nombre = nombre; this.filas = filas.map(r => r.map(v => v ?? '')); }
  getFilter() { return null; }
  showRows() {}
  getMaxRows() { return 100; }
  getName() { return this.nombre; }
  getLastColumn() { return Math.max(...this.filas.map(r => r.length)); }
  getLastRow() { return this.filas.length; }
  getRange(fila, columna, alto = 1, ancho = 1) {
    const hoja = this;
    return {
      getValues() {
        return Array.from({length: alto}, (_, i) => Array.from({length: ancho}, (_, j) =>
          hoja.filas[fila - 1 + i]?.[columna - 1 + j] ?? ''));
      },
      setValues(valores) {
        valores.forEach((r, i) => r.forEach((v, j) => {
          hoja.filas[fila - 1 + i] ??= [];
          hoja.filas[fila - 1 + i][columna - 1 + j] = v;
        }));
        return this;
      },
      setNumberFormat() { return this; },
      clearContent() {
        return this.setValues(Array.from({length: alto}, () => Array(ancho).fill('')));
      },
    };
  }
}

const zonaDestino = 'America/Argentina/Buenos_Aires';
const encabezado = ['Fecha', 'Banco', 'Empresa', 'Cuenta / Nro', 'Saldo (caja real, sin cheques)', 'Origen', 'Observaciones'];
const medianochePacifico = new Date('2026-09-25T07:00:00.000Z');
const origen = new Hoja('Saldos Bancarios', [encabezado,
  [medianochePacifico, 'Banco inventado', 'A', '001', 100, 'Extracto', '']]);
const destino = new Hoja('Saldos Bancarios', [encabezado]);
const cfg = contexto.IMPORTS.bancos.solapas[0];

contexto._volcar_(origen, destino, 1, 100, cfg, zonaDestino);
assert.equal(Utilities.formatDate(destino.filas[1][0], zonaDestino, 'yyyy-MM-dd HH:mm'), '2026-09-25 00:00');
assert.equal(destino.filas[1][0].toISOString(), '2026-09-25T03:00:00.000Z');

// Sin normalizar, la misma fecha se vería 04:00 y la verificación tiene que frenarla.
const corrida = new Hoja('Saldos Bancarios', [encabezado,
  [medianochePacifico, 'Banco inventado', 'A', '001', 100, 'Extracto', '']]);
assert.equal(Utilities.formatDate(corrida.filas[1][0], zonaDestino, 'yyyy-MM-dd HH:mm'), '2026-09-25 04:00');
assert.throws(() => contexto._verificarVolcado_(corrida, 1, 100, encabezado, cfg,
  [corrida.filas[1].slice()], 1, zonaDestino), /fechas corridas por zona horaria/);

console.log('OK: UTC-7 → UTC-3 conserva el 25/09 a las 00:00 y detecta una fecha corrida.');
