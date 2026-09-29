// Datos inventados: prueba la foto semanal y el mail de los lunes sin abrir la Sheet ni mandar mails.
// Uso: node lector/pruebas/probar_resumen_semanal.cjs
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
// Lo que sale del script vive en otro "mundo" de JavaScript (vm): se compara por contenido.
const eq = (a, b) => assert.deepEqual(JSON.parse(JSON.stringify(a)), JSON.parse(JSON.stringify(b)));

const ZONA = 'America/Argentina/Buenos_Aires';
function partes(fecha) {
  const salida = {};
  new Intl.DateTimeFormat('en-CA', {timeZone: ZONA, year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23'}).formatToParts(fecha)
    .forEach(p => { if (p.type !== 'literal') salida[p.type] = p.value; });
  return salida;
}
const Utilities = {
  formatDate(fecha, zona, formato) {
    assert.equal(zona, ZONA);
    const p = partes(fecha);
    return formato.replace(/yyyy|MM|dd|HH|mm/g, m => ({yyyy: p.year, MM: p.month, dd: p.day, HH: p.hour, mm: p.minute})[m]);
  },
  parseDate(texto, zona, formato) {
    assert.equal(zona, ZONA);
    assert.equal(formato, 'yyyy-MM-dd HH:mm');
    const m = texto.match(/^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})$/);
    // Buenos Aires es UTC-3: medianoche de allá son las 03:00 UTC.
    return new Date(Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4] + 3, +m[5]));
  }
};
// Un día a las 12:00 de Buenos Aires (15:00 UTC), como Date de la Sheet.
const d = s => new Date(s + 'T15:00:00Z');

// ---- una Sheet de mentira, suficiente para lo que usa el script
class Hoja {
  constructor(nombre, valores, id) { this.nombre = nombre; this.valores = valores.map(r => r.slice()); this.maxRows = Math.max(this.valores.length, 1); this.id = id; this.formatos = []; }
  getName() { return this.nombre; }
  getSheetId() { return this.id; }
  getDataRange() { const v = this.valores; return {getValues: () => v.map(r => r.slice())}; }
  getLastRow() { return this.valores.length; }
  getMaxRows() { return this.maxRows; }
  insertRowsAfter(_despues, n) { this.maxRows += n; }
  deleteRows(fila, n) { this.valores.splice(fila - 1, n); this.maxRows -= n; }
  setFrozenRows() {}
  getRange(fila, col, nf, nc) {
    const hoja = this;
    const rango = {
      setValues(v) {
        assert.equal(v.length, nf); v.forEach(r => assert.equal(r.length, nc));
        assert.ok(fila + nf - 1 <= hoja.maxRows, 'se escribió fuera de las filas de la hoja');
        v.forEach((r, i) => { while (hoja.valores.length < fila + i) hoja.valores.push([]); hoja.valores[fila - 1 + i] = r.slice(); });
        return rango;
      },
      setNumberFormat(f) { hoja.formatos.push([fila, col, nf, nc, f]); return rango; },
      setFontWeight() { return rango; }
    };
    return rango;
  }
}
class Planilla {
  constructor(hojas) { this.hojas = hojas; }
  getSheetByName(n) { return this.hojas.find(h => h.getName() === n) || null; }
  insertSheet(n) { const h = new Hoja(n, [], 900 + this.hojas.length); this.hojas.push(h); return h; }
  getNumSheets() { return this.hojas.length; }
  getId() { return 'planilla-inventada'; }
}

// ---- contexto de Apps Script
const mails = [], registro = [], disparadores = [];
let pdfFalla = false;
const contexto = vm.createContext({
  Date, Intl, Utilities, Math, String, Number, isFinite, isNaN, Logger: {log() {}},
  MailApp: {sendEmail: (a, asunto, cuerpo, op) => mails.push({a, asunto, cuerpo, op})},
  UrlFetchApp: {fetch: (url, op) => {
    assert.match(url, /\/export\?format=pdf&gid=77&portrait=false/);
    assert.equal(op.headers.Authorization, 'Bearer token-inventado');
    return {getResponseCode: () => (pdfFalla ? 500 : 200),
      getBlob: () => ({nombre: '', setName(n) { this.nombre = n; return this; }})};
  }},
  ScriptApp: {
    getOAuthToken: () => 'token-inventado',
    WeekDay: {MONDAY: 'MONDAY'},
    getProjectTriggers: () => disparadores.slice(),
    deleteTrigger: t => disparadores.splice(disparadores.indexOf(t), 1),
    newTrigger: funcion => {
      const t = {funcion, getHandlerFunction: () => funcion};
      const b = {timeBased: () => b, onWeekDay: x => { t.dia = x; return b; }, atHour: x => { t.hora = x; return b; },
        nearMinute: x => { t.minuto = x; return b; }, inTimezone: x => { t.zona = x; return b; },
        create: () => { disparadores.push(t); return t; }};
      return b;
    }
  },
  _registrar_: (...r) => registro.push(r)
});
for (const archivo of ['aviso_diario.gs', 'resumen_semanal.gs'])
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../../clientes/navar/herramientas', archivo), 'utf8'), contexto);
const C = contexto;

// ---- 1. El cálculo, a mano, con columnas en otro orden que la Sheet real
{
  const cobrar = [['Saldo Pendiente', 'Fecha Vencimiento', 'ID', 'Empresa', 'Cliente'],
    [100, d('2026-09-01'), 1, 'A', 'EQUIS S.A.'],          // vencido
    [50, d('2026-10-15'), 2, 'A', 'EQUIS S.A.'],           // a vencer
    [-20, d('2026-08-01'), 3, 'A', 'YE SRL'],              // nota de crédito: resta, no cuenta para el más viejo
    [80, d('2026-08-20'), 4, 'A', 'YE SRL'],
    [30, d('2026-09-10'), 5, 'AA', 'EQUIS S.A.'],           // misma razón social, otra empresa
    ['', '', 6, '', '']];                                  // fila vacía
  const pagar = [['Proveedor', 'Empresa', 'Saldo Pendiente', 'Fecha Vencimiento'],
    ['PROVE UNO', 'A', 500, '2026-09-28'],                 // vence el mismo día de la foto: todavía no vencido
    ['PROVE DOS', 'AA', 70, '15/09/2026']];                // fecha como texto dd/mm/aaaa
  const ultimos = [['Origen', 'Razon Social', 'Tipo', 'Empresa', 'Codigo', 'Fecha Ultimo Pago'],
    ['x', 'EQUIS S.A.', 'Cliente', 'A', '1', d('2026-09-20')],
    ['x', 'EQUIS S.A.', 'Cliente', 'A', '2', d('2026-09-25')],   // dos códigos: gana la más nueva
    ['x', 'PROVE UNO', 'Proveedor', 'A', 'P1', d('2026-05-15')]];
  const f = C._calcularFotoSemanal_({'Cuentas a Cobrar': cobrar, 'Cuentas a Pagar': pagar, 'Ultimos Pagos': ultimos}, '2026-09-28');
  const busca = (e, t, n) => f.filas.find(x => x.empresa === e && x.tipo === t && x.nombre === n);
  eq(JSON.parse(JSON.stringify(busca('A', 'Cliente', 'EQUIS S.A.'))),
    {empresa: 'A', tipo: 'Cliente', puesto: 1, nombre: 'EQUIS S.A.', saldo: 150, vencido: 100, aVencer: 50, viejo: '2026-09-01', ultimo: '2026-09-25'});
  eq(JSON.parse(JSON.stringify(busca('A', 'Cliente', 'YE SRL'))),
    {empresa: 'A', tipo: 'Cliente', puesto: 2, nombre: 'YE SRL', saldo: 60, vencido: 60, aVencer: 0, viejo: '2026-08-20', ultimo: ''});
  assert.equal(busca('AA', 'Cliente', 'EQUIS S.A.').saldo, 30);
  assert.equal(busca('AA', 'Cliente', 'EQUIS S.A.').ultimo, '');            // el pago de A no se cruza con AA
  assert.equal(busca('A', 'Proveedor', 'PROVE UNO').vencido, 0);
  assert.equal(busca('A', 'Proveedor', 'PROVE UNO').ultimo, '2026-05-15');
  assert.equal(busca('AA', 'Proveedor', 'PROVE DOS').vencido, 70);
  assert.equal(f.filas.length, 5);
  console.log('OK: cálculo de saldo, vencido, a vencer, vto. más viejo y último pago, con columnas en otro orden.');
}

// ---- 2. Solo los 20 de mayor saldo; empate: el que aparece primero en la lista
{
  const cobrar = [['Cliente', 'Empresa', 'Fecha Vencimiento', 'Saldo Pendiente']];
  for (let i = 1; i <= 25; i++) cobrar.push(['C' + i, 'A', d('2026-10-30'), i === 7 || i === 3 ? 999 : i]);
  const f = C._calcularFotoSemanal_({'Cuentas a Cobrar': cobrar, 'Cuentas a Pagar': [['Proveedor', 'Empresa', 'Fecha Vencimiento', 'Saldo Pendiente']],
    'Ultimos Pagos': [['Empresa', 'Tipo', 'Razon Social', 'Fecha Ultimo Pago']]}, '2026-09-28');
  assert.equal(f.filas.length, 20);
  eq(f.filas.slice(0, 3).map(x => x.nombre), ['C3', 'C7', 'C25']);
  assert.ok(!f.filas.some(x => ['C1', 'C2', 'C4', 'C5', 'C6'].includes(x.nombre)));
  console.log('OK: tope de 20 y empates en el orden de la lista.');
}

// ---- datos para las fotos: la Sheet de la semana 1 y la de la semana 2
function planillaCon(cobrarA, pagarA) {
  const cobrar = [['ID', 'Cliente', 'Empresa', 'Nro Factura', 'Fecha Emision', 'Fecha Vencimiento', 'Año', 'Importe Total', 'Cobrado', 'Saldo Pendiente']];
  cobrarA.forEach(([n, s, v], i) => cobrar.push([i + 1, n, 'A', 'F' + i, '', d(v), '', s, 0, s]));
  const pagar = [['ID', 'Proveedor', 'Empresa', 'Categoria', 'Nro Factura / OC', 'Fecha Emision', 'Fecha Vencimiento', 'Año', 'Importe Total', 'Pagado', 'Saldo Pendiente']];
  pagarA.forEach(([n, s, v], i) => pagar.push([i + 1, n, 'A', 'x', 'O' + i, '', d(v), '', s, 0, s]));
  const ultimos = [['Empresa', 'Tipo', 'Codigo', 'Razon Social', 'Fecha Ultimo Pago', 'Comprobante', 'Origen'],
    ['A', 'Cliente', '1', 'ALFA SA', d('2026-09-18'), 'REC 1', 'Tango tesorería'],
    ['A', 'Proveedor', 'P', 'COPE', d('2026-05-15'), 'O/P 9', 'Tango tesorería']];
  return new Planilla([new Hoja('Cuentas a Cobrar', cobrar, 1), new Hoja('Cuentas a Pagar', pagar, 2),
    new Hoja('Ultimos Pagos', ultimos, 3), new Hoja('Principales 20', [['x']], 77)]);
}
const lunes1 = new Date('2026-09-28T11:00:00Z'), lunes2 = new Date('2026-10-05T11:00:00Z');
let ss = planillaCon(
  [['ALFA SA', 10e6, '2026-09-01'], ['BETA SRL', 8e6, '2026-09-10'], ['GAMA', 5e6, '2026-10-30'], ['VIEJO SA', 1e6, '2024-01-10']],
  [['COPE', 134.9e6, '2026-07-17'], ['ENVA', 96.2e6, '2026-08-28']]);

// ---- 3. Primer lunes: sin foto anterior; crea el historial y el mail lo aclara
{
  const r = C._mandarResumenSemanal_(ss, lunes1);
  const h = ss.getSheetByName('Principales 20 · historial');
  assert.ok(h, 'crea el historial');
  eq(h.valores[0], [...C.SEMANAL_ENCABEZADO]);
  assert.equal(h.valores.length, 1 + 6);
  assert.equal(C._diaSemanal_(h.valores[1][0]), '2026-09-28');
  assert.equal(mails.length, 1);
  assert.equal(mails[0].a, C.DESTINATARIOS);
  assert.equal(mails[0].asunto, 'NAVAR · Principales clientes y proveedores · semana del 28/09');
  assert.match(mails[0].cuerpo, /Es la primera foto/);
  assert.match(mails[0].cuerpo, /CLIENTES A \(lo que nos deben\)\n- Los 4 principales suman \$24,0 M · vencido \$19,0 M/);
  assert.match(mails[0].cuerpo, /CLIENTES AA \(lo que nos deben\)\n- sin datos en la lista/);
  assert.match(mails[0].cuerpo, /- Clientes A: BETA SRL \(\$8,0 M\); GAMA \(\$5,0 M\); VIEJO SA \(\$1,0 M\)/);
  assert.match(mails[0].cuerpo, /- Proveedores A: ENVA \(\$96,2 M\)/);
  assert.ok(!/No se pudo adjuntar/.test(mails[0].cuerpo));
  assert.equal(mails[0].op.attachments[0].nombre, 'NAVAR - Principales clientes y proveedores 2026-09-28.pdf');
  assert.equal(r.asunto, mails[0].asunto);
  eq(registro.at(-1).slice(0, 3), ['resumen_semanal', '', 'ok']);
  console.log('OK: primer lunes, sin comparación, con PDF adjunto.');
}

// ---- 4. Guardar dos veces el mismo día no duplica ni toca otras fotos
{
  const h = ss.getSheetByName('Principales 20 · historial');
  h.valores.splice(1, 0, ...[[d('2026-09-21'), 'A', 'Cliente', 1, 'ANTIGUO', 1, 1, 0, '', '']]);  // una foto vieja arriba
  const antes = h.valores.length;
  assert.equal(C._guardarFotoDeHoySemanal_(ss, lunes1), 6);
  assert.equal(C._guardarFotoDeHoySemanal_(ss, lunes1), 6);
  assert.equal(h.valores.length, antes);
  assert.equal(h.valores[1][4], 'ANTIGUO');
  console.log('OK: la foto del mismo día se reemplaza y las anteriores quedan intactas.');
}

// ---- 5. Segundo lunes: diferencias, bajaron/subieron, entraron/salieron, sin pagos; PDF que falla
{
  ss.hojas[0] = planillaCon(
    [['ALFA SA', 4e6, '2026-09-01'], ['BETA SRL', 12e6, '2026-09-10'], ['GAMA', 5e6, '2026-10-30'], ['DELTA', 3e6, '2026-09-20']],
    []).hojas[0];
  ss.hojas[1] = planillaCon([], [['COPE', 134.9e6, '2026-07-17'], ['ENVA', 90e6, '2026-08-28']]).hojas[1];
  pdfFalla = true;
  C._mandarResumenSemanal_(ss, lunes2);
  const m = mails.at(-1).cuerpo;
  assert.match(m, /Comparado con la foto del 28\/09\./);
  assert.match(m, /- Los 4 principales suman \$24,0 M \(sin cambios\) · vencido \$19,0 M \(sin cambios\)/);
  assert.match(m, /- Bajaron su vencido: ALFA SA \$4,0 M \(−\$6,0 M\)/);
  assert.match(m, /- Subieron su vencido: BETA SRL \$12,0 M \(\+\$4,0 M\)/);
  assert.match(m, /- Entraron: DELTA · Salieron: VIEJO SA/);
  assert.match(m, /PROVEEDORES A \(lo que debemos\)\n- Los 2 principales suman \$224,9 M \(−\$6,2 M\) · vencido \$224,9 M \(−\$6,2 M\)\n- Bajaron su vencido: ENVA \$90,0 M \(−\$6,2 M\)\n- Subieron su vencido: ninguno\n- Los mismos 20 que la foto anterior/);
  assert.match(m, /No se pudo adjuntar el PDF de la solapa: Google devolvió HTTP 500 al exportar/);
  eq(mails.at(-1).op, {});
  assert.match(registro.at(-1)[3], /comparada con la del 28\/09; sin PDF/);
  const fechas = new Set(ss.getSheetByName('Principales 20 · historial').valores.slice(1).map(r => C._diaSemanal_(r[0])));
  eq([...fechas].sort(), ['2026-09-21', '2026-09-28', '2026-10-05']);
  pdfFalla = false;
  console.log('OK: segundo lunes con diferencias, movimientos del top y mail sin PDF cuando la exportación falla.');
}

// ---- 6. "Ver sin mandar": no manda, no guarda, compara contra la última foto anterior a hoy
{
  const nMails = mails.length, nFilas = ss.getSheetByName('Principales 20 · historial').valores.length;
  const r = C._verResumenSemanal_(ss, new Date('2026-10-06T12:00:00Z'));
  assert.equal(mails.length, nMails);
  assert.equal(ss.getSheetByName('Principales 20 · historial').valores.length, nFilas);
  assert.match(r.cuerpo, /Comparado con la foto del 05\/10\./);
  console.log('OK: la vista previa no manda ni guarda.');
}

// ---- 7. Falta una lista o un encabezado: error claro y no se escribe nada
{
  for (const [romper, mensaje] of [
    [p => p.hojas.splice(2, 1), /Falta la solapa 'Ultimos Pagos'/],
    [p => { p.hojas[0].valores[0][5] = 'Vencimiento'; }, /le falta la columna Fecha Vencimiento/]]) {
    const p = planillaCon([['ALFA SA', 1, '2026-09-01']], []);
    romper(p);
    const nMails = mails.length;
    assert.throws(() => C._mandarResumenSemanal_(p, lunes1), mensaje);
    assert.equal(p.getSheetByName('Principales 20 · historial'), null);
    assert.equal(mails.length, nMails);
    assert.equal(registro.at(-1)[2], 'ERROR');
  }
  console.log('OK: sin lista o sin encabezado, error claro y nada escrito.');
}

// ---- 8. Instalar deja un solo disparador, los lunes a las 08, sin tocar los demás
{
  disparadores.push({getHandlerFunction: () => 'importarLoNuevo'}, {getHandlerFunction: () => 'resumenSemanal'});
  C.instalarResumenSemanal();
  C.instalarResumenSemanal();
  const nuestros = disparadores.filter(t => t.getHandlerFunction() === 'resumenSemanal');
  assert.equal(nuestros.length, 1);
  eq([nuestros[0].dia, nuestros[0].hora, nuestros[0].minuto, nuestros[0].zona], ['MONDAY', 8, 15, ZONA]);
  assert.ok(disparadores.some(t => t.getHandlerFunction() === 'importarLoNuevo'));
  C.quitarResumenSemanal();
  assert.equal(disparadores.filter(t => t.getHandlerFunction() === 'resumenSemanal').length, 0);
  console.log('OK: un solo disparador semanal, lunes 08:00–08:30.');
}

// ---- 9. El menú lista las tres funciones nuevas y todas existen
{
  const menu = fs.readFileSync(path.join(__dirname, '../../clientes/navar/herramientas/importar_cashflow.gs'), 'utf8');
  for (const f of ['resumenSemanalPrueba', 'guardarFotoSemanal', 'instalarResumenSemanal']) {
    assert.ok(menu.includes('"' + f + '"'), 'falta en el menú: ' + f);
    assert.equal(typeof C[f], 'function');
  }
  console.log('OK: menú.');
}
