// Datos inventados: prueba el texto del aviso sin abrir Drive, la Sheet ni mandar mails.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');

function partes(fecha, zona) {
  const salida = {};
  new Intl.DateTimeFormat('en-CA', {
    timeZone: zona, year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23'
  }).formatToParts(fecha).forEach(p => { if (p.type !== 'literal') salida[p.type] = p.value; });
  return salida;
}

const Utilities = {
  formatDate(fecha, zona, formato) {
    const p = partes(fecha, zona);
    return formato.replace(/yyyy|MM|dd|HH|mm|ss/g, marca => ({
      yyyy: p.year, MM: p.month, dd: p.day, HH: p.hour, mm: p.minute, ss: p.second
    })[marca]);
  },
  parseDate(texto, zona, formato) {
    assert.equal(zona, 'America/Argentina/Buenos_Aires');
    assert.equal(formato, 'dd/MM/yyyy HH:mm');
    const m = texto.match(/^(\d{2})\/(\d{2})\/(\d{4}) (\d{2}):(\d{2})$/);
    if (!m) return new Date(NaN);
    // Buenos Aires es UTC-3: se suman tres horas para obtener el instante UTC.
    return new Date(Date.UTC(+m[3], +m[2] - 1, +m[1], +m[4] + 3, +m[5]));
  }
};

const contexto = vm.createContext({Date, Intl, Utilities});
vm.runInContext(fs.readFileSync(path.join(__dirname,
  '../../clientes/navar/herramientas/aviso_diario.gs'), 'utf8'), contexto);

const ahora = new Date('2026-09-28T12:00:00Z'); // lunes, 09:00 de Buenos Aires
function foto() {
  const llegada = new Date('2026-09-28T11:35:00Z');
  const entradas = [];
  for (const empresa of ['A', 'AA']) for (const lista of ['cobranzas', 'pagos', 'cheques']) {
    entradas.push({
      nombre: `${empresa} ${lista} 2026-09-28.xlsx`, ruta: `${lista}/inventado.xlsx`,
      tipo: 'tango', fecha: llegada
    });
  }
  entradas.push({nombre: 'AA movimientos tesoreria 2026-09-28.xlsx',
    ruta: 'Tesoreria AA/inventado.xlsx', tipo: 'tesoreria_aa', fecha: llegada});
  return {
    entradas,
    publicados: [{nombre: 'para_pegar_en_la_sheet_2026-09-28.xlsx', ruta: '_para la Sheet',
      tipo: 'tango', fecha: new Date('2026-09-28T11:40:00Z')}],
    retenidos: [], registro: [], log: [], ultimaPasada: new Date('2026-09-28T11:45:00Z'),
    tangoParte: {fecha: new Date('2026-09-28T10:31:00Z'), ok: 8, total: 8, fallas: []},
    galiciaParte: {fecha: new Date('2026-09-28T10:00:00Z'), ok: true, detalle: ''},
    extracto: new Date('2026-09-28T03:00:00Z'),
    saldos: [
      {banco: 'Galicia', empresa: 'A', origen: 'Extracto Galicia', fecha: new Date('2026-09-28T03:00:00Z')},
      {banco: 'Macro', empresa: 'A', origen: 'Extracto Macro', fecha: new Date('2026-09-25T03:00:00Z')},
      {banco: '(varios)', empresa: 'AA', origen: 'Manual', fecha: new Date('2026-09-25T03:00:00Z')}
    ],
    errores: {}
  };
}

let datos = foto(), aviso = contexto._armarAviso_(ahora, datos);
assert.ok(aviso.cuerpo.includes('Bajada de Tango: hoy 07:31 · 8 de 8'));
assert.ok(!aviso.alertas.some(a => a.includes('La bajada de Tango terminó')));

datos = foto();
datos.tangoParte = {fecha: new Date('2026-09-28T10:31:00Z'), ok: 6, total: 8,
  fallas: ['A pagos 2026-09-28.xlsx: timeout', 'AA cobranzas 2026-09-28.xlsx: HTTP 500']};
aviso = contexto._armarAviso_(ahora, datos);
assert.ok(aviso.cuerpo.includes('Bajada de Tango: hoy 07:31 · 6 de 8'));
assert.ok(aviso.alertas.some(a => a.includes('A pagos 2026-09-28.xlsx: timeout')));

datos = foto();
datos.tangoParte.fecha = new Date('2026-09-27T10:31:00Z');
aviso = contexto._armarAviso_(ahora, datos);
assert.ok(aviso.alertas.some(a => a.includes(
  'La bajada de Tango de hoy no corrió (último parte: 27/09 07:31)')));

datos = foto();
aviso = contexto._armarAviso_(ahora, datos);
assert.ok(aviso.cuerpo.includes('Bot de Galicia: hoy 07:00 · OK'));

datos = foto();
datos.galiciaParte = {fecha: new Date('2026-09-28T10:02:00Z'), ok: false,
  detalle: 'falló la descarga inventada'};
aviso = contexto._armarAviso_(ahora, datos);
assert.ok(aviso.cuerpo.includes('Bot de Galicia: hoy 07:02 · ATENCIÓN'));
assert.ok(aviso.alertas.some(a => a.includes('falló la descarga inventada')));

datos = foto();
datos.galiciaParte = null;
datos.errores.GaliciaParte = 'Falta el estado de hoy';
aviso = contexto._armarAviso_(ahora, datos);
assert.ok(aviso.alertas.includes(
  'El bot de Galicia no corrió hoy. Revisar la tarea "finauto NAVAR Galicia"'));

// Un lunes, lo manual puede estar al viernes; lo automático debe haber llegado hoy.
datos = foto();
datos.saldos[0].fecha = new Date('2026-09-27T03:00:00Z');
datos.entradas = datos.entradas.filter(f =>
  !f.nombre.startsWith('A pagos') && f.tipo !== 'tesoreria_aa');
const faltantesLunes = contexto._faltantesAviso_(ahora, datos);
assert.ok(faltantesLunes.some(l => l.includes('Extracto de Galicia: no llegó la bajada automática de hoy')));
assert.ok(faltantesLunes.some(l => l.includes('Tango A — pagos: no llegó la bajada automática de hoy')));
assert.ok(faltantesLunes.some(l => l.includes('Tesorería AA: no llegó la bajada automática de hoy')));
assert.ok(!faltantesLunes.some(l => l.includes('Extracto de Macro')));
assert.ok(!faltantesLunes.some(l => l.includes('subida manual')));

const tangoParseado = contexto._parteTangoAviso_(
  '2026-09-28T10:31:00+00:00\n6 de 8\nA pagos 2026-09-28.xlsx: timeout\n');
assert.equal(tangoParseado.ok, 6);
assert.deepEqual(Array.from(tangoParseado.fallas), ['A pagos 2026-09-28.xlsx: timeout']);
const galiciaParseada = contexto._parteGaliciaAviso_(
  'Bot Galicia - 28/09/2026 07:02\n\n>>> ATENCION: 1 descarga falló\n   - error inventado\n\nBajadas OK (0): -');
assert.equal(galiciaParseada.ok, false);
assert.ok(galiciaParseada.detalle.includes('error inventado'));

console.log('OK: Tango y Galicia hoy, fallas, partes viejos o ausentes y cierre de lunes. Datos inventados.');
