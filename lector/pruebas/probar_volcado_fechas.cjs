// Prueba el código real de _volcar_ con una planilla en memoria.
// No imita la conversión de Drive, los filtros ni las escrituras de Google:
// sirve para comprobar si el armado de filas mezcla fechas por su cuenta.
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

if (!process.stdin.isTTY) {
  const texto = fs.readFileSync(0, 'utf8').trim();
  if (texto) {
    const datos = JSON.parse(texto, (_, v) => v && typeof v === 'object' && v.fecha
      ? new Date(v.fecha + (v.fecha.endsWith('Z') ? '' : 'Z')) : v);
    verificar(datos.origen, datos.destino);
    console.log(`OK: _volcar_ conserva todas las columnas de las ${datos.origen.length - 1} filas de origen, también al repetir.`);
  }
}
