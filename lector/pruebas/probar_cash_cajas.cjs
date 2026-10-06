// Tarea 48. Datos inventados: prueba las fórmulas de las cajas del cash sin abrir la Sheet.
// Las fórmulas que arma crear_cash.gs se evalúan con un SUMIFS de juguete sobre listas chicas.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');

const contexto = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname,
  '../../clientes/navar/herramientas/crear_cash.gs'), 'utf8'), contexto);
// Los rangos de las listas, con nombres cortos para poder evaluar la fórmula.
vm.runInContext('R = {movImp:"movImp", movBanco:"movBanco", movOrigen:"movOrigen", movEstado:"movEstado", movFecha:"movFecha", movTipo:"movTipo", movCat:"movCat"};', contexto);

// ---- SUMIFS de juguete: comodines * y ? (con ~ para el literal), y comparaciones con números.
function cumple(valor, criterio) {
  criterio = String(criterio);
  const m = criterio.match(/^(<=|>=|<>|<|>|=)?(.*)$/s);
  const op = m[1] || '', resto = m[2];
  if (op && op !== '=' && op !== '<>' && resto !== '' && !isNaN(Number(resto))) {
    const v = Number(valor), c = Number(resto);
    return {'<': v < c, '>': v > c, '<=': v <= c, '>=': v >= c}[op];
  }
  let re = '';
  for (let i = 0; i < resto.length; i++) {
    const ch = resto[i];
    if (ch === '~' && i + 1 < resto.length) re += resto[++i].replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    else if (ch === '*') re += '.*';
    else if (ch === '?') re += '.';
    else re += ch.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }
  const igual = new RegExp('^' + re + '$', 'is').test(String(valor));
  return op === '<>' ? !igual : igual;
}
function evaluar(formula, lista, celdas) {
  const cols = {};
  for (const clave of ['movImp', 'movBanco', 'movOrigen', 'movEstado', 'movFecha', 'movTipo', 'movCat'])
    cols[clave] = lista.map(r => r[clave]);
  const SUMIFS = (suma, ...pares) => suma.reduce((t, v, i) => {
    for (let k = 0; k < pares.length; k += 2) if (!cumple(pares[k][i], pares[k + 1])) return t;
    return t + v;
  }, 0);
  const MIN = Math.min, MAX = Math.max;
  let js = formula.replace(/\$B\$(\d)/g, (_, n) => String(celdas['B' + n])).replace(/&/g, '+');
  for (const [k, v] of Object.entries(celdas)) js = js.split('{' + k + '}').join(String(v));
  return Function('SUMIFS', 'MIN', 'MAX', ...Object.keys(cols), 'return ' + js)(SUMIFS, MIN, MAX, ...Object.values(cols));
}

// ---- 1. Saldos Bancarios: cada caja se reconoce con su nombre; el viejo "(varios)" es la de AA.
const saldos = [
  ['A', 'Caja A', 0, 0, 0, 'Manual', ''],
  ['AA', 'Caja AA', 0, 0, 0, 'Manual', ''],
  ['AA', '(varios)', 0, 0, 0, 'Manual', ''],
  ['A', 'BANCO INVENTADO', 0, 0, 0, 'Extracto BANCO INVENTADO', ''],
  ['A', 'BANCO A MANO', 0, 0, 0, 'Manual', ''],
];
const ss = {getSheetByName: () => ({getLastRow: () => saldos.length + 1, getRange: () => ({getValues: () => saldos})})};
const bancos = JSON.parse(JSON.stringify(contexto._bancos_(ss)));
assert.deepEqual(bancos.map(b => [b.nombre, b.caja, b.etiqueta]), [
  ['Caja A', 'Caja A', 'Caja A (efectivo)'],
  ['Caja AA', 'Caja AA', 'Caja AA (efectivo)'],
  ['(varios)', 'Caja AA', 'Caja AA (efectivo)'],
  ['BANCO INVENTADO', '', 'BANCO INVENTADO'],
  ['BANCO A MANO', '', 'BANCO A MANO'],     // un banco cargado a mano no suma movimientos de caja
]);

// ---- 2. El saldo de cada caja suma SOLO los movimientos de esa caja, después de su arqueo.
// Fechas como números de día (10 = arqueo, 15 = hoy).
const mov = [
  {movFecha: 11, movBanco: 'Caja A', movOrigen: 'Tango caja A · cajas · inventado.xlsx', movEstado: 'Real', movImp: -100, movTipo: 'Egreso', movCat: 'Otros'},
  {movFecha: 12, movBanco: 'Caja A', movOrigen: 'Tango caja A · cajas · inventado.xlsx', movEstado: 'Real', movImp: 300, movTipo: 'Ingreso', movCat: 'Cobranza Facturas'},
  {movFecha: 12, movBanco: 'Caja A', movOrigen: 'Tango caja A · cajas · inventado.xlsx', movEstado: 'Real', movImp: -200, movTipo: 'Ingreso', movCat: 'Cobranza Facturas'}, // depósito al banco
  {movFecha: 9, movBanco: 'Caja A', movOrigen: 'Tango caja A · cajas · inventado.xlsx', movEstado: 'Real', movImp: -999, movTipo: 'Egreso', movCat: 'Otros'},  // antes del arqueo
  {movFecha: 16, movBanco: 'Caja A', movOrigen: 'Tango caja A · cajas · inventado.xlsx', movEstado: 'Real', movImp: -999, movTipo: 'Egreso', movCat: 'Otros'}, // después del corte
  {movFecha: 11, movBanco: 'Caja A', movOrigen: 'Manual', movEstado: 'Real', movImp: -999, movTipo: 'Egreso', movCat: 'Otros'},                                 // no es de Tango
  {movFecha: 11, movBanco: 'Caja AA', movOrigen: 'Tango AA · cajas · inventado.xlsx', movEstado: 'Real', movImp: -40, movTipo: 'Egreso', movCat: 'Proveedores AA'},
  {movFecha: 13, movBanco: 'Caja AA', movOrigen: 'Tango AA · cajas · inventado.xlsx', movEstado: 'Real', movImp: 7, movTipo: 'Ingreso', movCat: 'Cobranza AA'},
  {movFecha: 12, movBanco: 'BANCO INVENTADO', movOrigen: 'Extracto BANCO INVENTADO', movEstado: 'Real', movImp: 200, movTipo: 'Ingreso', movCat: 'Cobranza Facturas'}, // el mismo depósito, en el banco
  {movFecha: 14, movBanco: 'BANCO INVENTADO', movOrigen: 'Extracto BANCO INVENTADO', movEstado: 'Real', movImp: 50, movTipo: 'Ingreso', movCat: 'Cobranza Facturas'}, // después del último extracto
];
assert.equal(evaluar(contexto._movCaja_('Caja A', 10, 15), mov, {}), 0);      // -100 + 300 - 200
assert.equal(evaluar(contexto._movCaja_('Caja AA', 10, 15), mov, {}), -33);
assert.equal(evaluar(contexto._movCaja_('Caja AA', 12, 15), mov, {}), 7);     // arqueo más nuevo: solo lo posterior

// ---- 3. Lo real de los renglones: cada origen hasta su corte. Último extracto (B3) = 12,
// último día con caja (B5) = 13. Columna del 10 al 20 (F exclusivo = 21).
const celdas = {B3: 12, B5: 13, D: 10, F: 21};
// Cobranza: caja A 300 − 200 (depósito) + banco 200 = 300; el banco del 14 no cuenta (pasa el último extracto).
assert.equal(evaluar(contexto._real_('Ingreso', 'Cobranza Facturas'), mov, celdas), 300);
assert.equal(evaluar(contexto._real_('Ingreso', 'Cobranza AA'), mov, celdas), 7);
assert.equal(evaluar(contexto._real_('Egreso', 'Otros'), mov, celdas), -100);
// Si las cajas no hubieran llegado más allá del extracto, la cobranza AA del 13 todavía no es real.
assert.equal(evaluar(contexto._real_('Ingreso', 'Cobranza AA'), mov, {B3: 12, B5: 12, D: 10, F: 21}), 0);

// ---- 4. Los patrones de Origen no se pisan entre empresas.
assert.deepEqual(Array.from(contexto.ORIGENES_REALES), ['Extracto*', 'Tango AA*', 'Tango caja A*']);
assert.ok(!cumple('Tango AA · cajas · x', 'Tango caja A*'));
assert.ok(!cumple('Tango caja A · cajas · x', 'Tango AA*'));
assert.equal(contexto._hastaReal_('Tango caja A*'), 'MIN({F},$B$5+1)');
assert.equal(contexto._hastaReal_('Extracto*'), 'MIN({F},$B$3+1)');
console.log('OK: saldo de Caja A y Caja AA por separado desde su arqueo; lo real de cada origen hasta su corte; el depósito cuenta una vez.');
