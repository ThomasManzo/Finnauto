// Tarea 81. Datos inventados: prueba las partes del control de cierre sin abrir la Sheet.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');

const contexto = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname,
  '../../clientes/navar/herramientas/crear_cash.gs'), 'utf8'), contexto);
vm.runInContext('R = {movImp:"movImp", movOrigen:"movOrigen", movEstado:"movEstado", movFecha:"movFecha", movCat:"movCat", movTipo:"movTipo", salBanco:"salBanco", salFecha:"salFecha", salImp:"salImp", movBanco:"movBanco"};', contexto);

// SUMIFS de juguete: comodín final * y comparaciones con números (las fechas son números de día).
function cumple(v, crit) {
  crit = String(crit);
  const m = crit.match(/^(>=|<=|<|>)(.*)$/);
  if (m) return {'>=': v >= +m[2], '<=': v <= +m[2], '<': v < +m[2], '>': v > +m[2]}[m[1]];
  return crit.endsWith('*') ? String(v).startsWith(crit.slice(0, -1)) : String(v) === crit;
}
function evaluar(formula, filas) {
  const cols = {};
  for (const k of ['movImp', 'movOrigen', 'movEstado', 'movFecha', 'movCat']) cols[k] = filas.map(f => f[k]);
  const SUMIFS = (suma, ...p) => suma.reduce((t, v, i) => {
    for (let k = 0; k < p.length; k += 2) if (!cumple(p[k][i], p[k + 1])) return t;
    return t + v;
  }, 0);
  const js = formula.replace(/\{D\}/g, '10').replace(/\{F\}/g, '20').replace(/&/g, '+');
  return Function('SUMIFS', ...Object.keys(cols), 'return ' + js)(SUMIFS, ...Object.values(cols));
}
const fila = (movFecha, movOrigen, movCat, movImp, movEstado = 'Real') => ({movFecha, movOrigen, movCat, movImp, movEstado});
const movimientos = [
  fila(11, 'Extracto BANCO UNO', 'Transferencia Interna', -500),   // pase con sus dos patas: cancela
  fila(11, 'Extracto BANCO DOS', 'Transferencia Interna', 500),
  fila(12, 'Extracto BANCO UNO', 'Transferencia Interna', -70),    // le falta la otra pata
  fila(13, 'Extracto BANCO UNO', 'Otros', -30),
  fila(14, 'Tango AA · cajas · inventado.xlsx', 'Otros', -8),
  fila(14, 'Tango caja A · cajas · inventado.xlsx', 'Otros', 3),
  fila(9, 'Extracto BANCO UNO', 'Otros', -999),                    // del mes anterior
  fila(20, 'Extracto BANCO UNO', 'Otros', -999),                   // del mes siguiente
  fila(15, 'Extracto BANCO UNO', 'Otros', -999, 'Proyectado'),     // no pasó
  fila(15, 'Manual', 'Otros', -999),                               // fila vieja migrada: no cuenta
];
const mov = (origenes, cat) => evaluar(contexto._movDelMes_(origenes, cat), movimientos);

// ---- 1. Cada parte mira solo el mes, lo real y sus orígenes.
assert.equal(mov(contexto.ORIGENES_REALES, 'Transferencia Interna'), -70);
assert.equal(mov(contexto.ORIGENES_BANCO), -100);       // -500 + 500 - 70 - 30
assert.equal(mov(contexto.ORIGENES_CAJA), -5);          // -8 + 3

// ---- 2. El estado: bancos, internas y movimientos sin renglón marcan. El efectivo no entra.
function estado(interna, bancos, sin) {
  const f = contexto._estadoControl_('a', 'b', 'c');
  const IF = (c, x, y) => (c ? x : y);
  return Function('IF', 'MAX', 'ABS', 'a', 'b', 'c', 'return ' + f)(IF, Math.max, Math.abs, interna, bancos, sin);
}
assert.equal(estado(0, 0, 0), 'OK');
assert.equal(estado(999999, -999999, 0), 'OK');            // debajo de la tolerancia
assert.equal(estado(-1000000, 0, 0), 'REVISAR');
assert.equal(estado(0, 2000000, 0), 'REVISAR');
assert.equal(estado(0, 0, -3000000), 'REVISAR');

// ---- 3. La caja se reconoce con su nombre y suma movimientos; un banco solo su saldo.
const fCaja = contexto._saldoBancoAl_({nombre: 'Caja AA', caja: 'Caja AA'}, 'X');
const fBanco = contexto._saldoBancoAl_({nombre: 'BANCO UNO', caja: ''}, 'X');
assert.ok(fCaja.includes('"Caja AA"') && fCaja.includes('movImp'));
assert.ok(!fBanco.includes('movImp'));

// ---- 4. Un renglón de egreso con dos categorías las suma las dos (el "-" del cash niega el total).
// Pasó con "Otros": restaba los honorarios en vez de sumarlos, y este control lo encontró.
const otros = contexto._renglones_('mes').egresos.find(r => r.n.startsWith('Otros')).real;
const egresos = [
  {movImp: -100, movTipo: 'Egreso', movEstado: 'Real', movOrigen: 'Extracto BANCO UNO', movCat: 'Otros', movFecha: 11},
  {movImp: -5, movTipo: 'Egreso', movEstado: 'Real', movOrigen: 'Extracto BANCO UNO', movCat: 'Honorarios y Dividendos', movFecha: 12},
];
const colsE = {};
for (const k of ['movImp', 'movOrigen', 'movEstado', 'movFecha', 'movCat', 'movTipo']) colsE[k] = egresos.map(f => f[k]);
const SUMIFS_E = (suma, ...p) => suma.reduce((t, v, i) => {
  for (let k = 0; k < p.length; k += 2) if (!cumple(p[k][i], p[k + 1])) return t;
  return t + v;
}, 0);
const jsOtros = ('-' + otros).replace(/\{D\}/g, '10').replace(/\{F\}/g, '20').replace(/\$B\$\d/g, '30').replace(/&/g, '+');
const totalOtros = Function('SUMIFS', 'MIN', ...Object.keys(colsE), 'return ' + jsOtros)(SUMIFS_E, Math.min, ...Object.values(colsE));
assert.equal(totalOtros, 105);

console.log('probar_control_cierre: OK');
