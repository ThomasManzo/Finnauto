// Datos inventados: prueba el mail del cruce semanal sin Google y sin mandar nada.
// Uso: node lector/pruebas/probar_cruce_semanal.cjs
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');

const ZONA = 'America/Argentina/Buenos_Aires';
const Utilities = {
  formatDate(fecha, zona, formato) {
    assert.equal(zona, ZONA);
    const p = {};
    new Intl.DateTimeFormat('en-CA', {timeZone: ZONA, year: 'numeric', month: '2-digit', day: '2-digit'})
      .formatToParts(fecha).forEach(x => { if (x.type !== 'literal') p[x.type] = x.value; });
    assert.equal(formato, 'yyyy-MM-dd');
    return p.year + '-' + p.month + '-' + p.day;
  }
};

// ---- Drive, mail y propiedades de mentira
function contexto({archivos = {}, propiedades = {}} = {}) {
  const mandados = [], registro = [];
  const archivo = (nombre, texto) => ({getName: () => nombre, getBlob: () => ({getDataAsString: () => texto, nombre})});
  const iter = lista => { let i = 0; return {hasNext: () => i < lista.length, next: () => lista[i++]}; };
  const carpetaCruce = {
    getFiles: () => iter(Object.entries(archivos).map(([n, t]) => archivo(n, t))),
    getFilesByName: n => iter(n in archivos ? [archivo(n, archivos[n])] : [])
  };
  const ctx = {
    Utilities, JSON, String, Number, Math, Logger: {log() {}},
    CARPETA_RAIZ: 'NAVAR - Datos',
    _registrar_: (...a) => registro.push(a),
    MailApp: {sendEmail: (para, asunto, cuerpo, opciones) => mandados.push({para, asunto, cuerpo, opciones})},
    PropertiesService: {getScriptProperties: () => ({getProperty: n => propiedades[n] || null})},
    DriveApp: {getFoldersByName: n => iter(n === 'NAVAR - Datos' ? [{getFoldersByName: m => iter(m === 'Cruce' ? [carpetaCruce] : [])}] : [])},
    SpreadsheetApp: {getUi: () => ({alert() {}})},
    ScriptApp: {getProjectTriggers: () => []}
  };
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(path.join(__dirname, '..', '..', 'clientes', 'navar', 'herramientas', 'cruce_semanal.gs'), 'utf8'), ctx);
  return {ctx, mandados, registro};
}

const datos = (cambios = {}) => Object.assign({
  fecha: '2026-10-07', meses: ['septiembre', 'octubre'], dias: 7,
  bancos: [
    {cuenta: 'Galicia 111', extracto_hasta: '2026-10-06', dias_sin_extracto: 1, conciliado: [0.95, 0.4]},
    {cuenta: 'Nación 222', extracto_hasta: '2026-09-24', dias_sin_extracto: 13, conciliado: [0.1, null]}
  ],
  falta_total: {cantidad: 3, importe: 1500.5},
  falta: [{fecha: '2026-09-30', banco: 'Galicia 111', concepto: 'CUOTA DE PRESTAMO', importe: -1000.25},
          {fecha: '2026-09-14', banco: 'Nación 222', concepto: 'TARJETA', importe: -500.25}],
  gastos: [{banco: 'Galicia 111', cantidad: 40, importe: -123.4}],
  errores: ['En Tango, BDM 1 por $10,00: fecha imposible 12/08/2036'],
  archivo: 'Cruce banco-Tango 2026-10-07.xlsx', control_ok: true, aviso: ''
}, cambios);

// ---- el texto del mail
{
  const {ctx} = contexto();
  const r = ctx._armarCruceSemanal_(datos());
  assert.equal(r.asunto, 'Cruce banco-Tango · 07/10 · 3 movimientos para cargar en Tango');
  for (const t of ['1. CÓMO ESTÁ CADA BANCO', 'Galicia 111: extracto hasta el 06/10 · septiembre 95 % conciliado · octubre 40 % conciliado',
                   'Nación 222: extracto hasta el 24/09 (sin extracto nuevo hace 13 días) · septiembre 10 % conciliado',
                   '3 movimientos por $1.500,50 en total. Los 2 más grandes:',
                   '30/09 · Galicia 111 · CUOTA DE PRESTAMO · -$1.000,25',
                   'Galicia 111: 40 renglones, -$123,40', 'fecha imposible 12/08/2036', 'Excel adjunto']) {
    assert.ok(r.cuerpo.includes(t), 'falta en el mail: ' + t + '\n\n' + r.cuerpo);
  }
  assert.ok(!r.cuerpo.includes('octubre undefined'));
  const vacio = ctx._armarCruceSemanal_(datos({falta_total: {cantidad: 0, importe: 0}, falta: [], gastos: [], errores: []}));
  assert.equal(vacio.asunto, 'Cruce banco-Tango · 07/10 · nada pendiente de cargar');
  assert.ok(vacio.cuerpo.includes('Nada pendiente.') && vacio.cuerpo.includes('No encontramos.'));
  assert.equal(ctx._plataCruce_(-1234567.5), '-$1.234.567,50');
  assert.equal(ctx._plataCruce_(0.999), '$1,00');
}

// ---- cuándo se manda y cuándo no
{
  const {ctx} = contexto();
  assert.equal(ctx._decidirCruceSemanal_(datos(), '2026-10-07').mandar, true);
  assert.match(ctx._decidirCruceSemanal_(null, '2026-10-07').motivo, /no hay cruce de hoy/);
  assert.match(ctx._decidirCruceSemanal_(datos({fecha: '2026-09-30'}), '2026-10-07').motivo, /es del 30\/09/);
  assert.match(ctx._decidirCruceSemanal_(datos({control_ok: false}), '2026-10-07').motivo, /control/);
}

// ---- el miércoles: con el cruce de hoy va a la administración con el Excel adjunto
const miercoles = new Date('2026-10-07T12:30:00Z');   // 09:30 de Buenos Aires
{
  const {ctx, mandados} = contexto({
    archivos: {'cruce_semanal_2026-10-07.json': JSON.stringify(datos()), 'Cruce banco-Tango 2026-10-07.xlsx': 'excel'},
    propiedades: {DESTINATARIOS_CRUCE: 'admin@ejemplo.test', DESTINATARIOS_FALLA: 'yo@ejemplo.test'}});
  ctx._mandarCruceSemanal_(miercoles);
  assert.equal(mandados.length, 1);
  assert.equal(mandados[0].para, 'admin@ejemplo.test');
  assert.equal(mandados[0].opciones.attachments.length, 1);
}
// ---- sin cruce de hoy (solo uno viejo): NO va a la administración, avisa a quien corresponde
{
  const {ctx, mandados} = contexto({
    archivos: {'cruce_semanal_2026-09-30.json': JSON.stringify(datos({fecha: '2026-09-30'}))},
    propiedades: {DESTINATARIOS_CRUCE: 'admin@ejemplo.test', DESTINATARIOS_FALLA: 'yo@ejemplo.test'}});
  ctx._mandarCruceSemanal_(miercoles);
  assert.equal(mandados.length, 1);
  assert.equal(mandados[0].para, 'yo@ejemplo.test');
  assert.match(mandados[0].asunto, /no se mandó/);
}
// ---- la cuenta de control no dio: tampoco va a la administración
{
  const {ctx, mandados} = contexto({
    archivos: {'cruce_semanal_2026-10-07.json': JSON.stringify(datos({control_ok: false}))},
    propiedades: {DESTINATARIOS_CRUCE: 'admin@ejemplo.test', DESTINATARIOS_FALLA: 'yo@ejemplo.test'}});
  ctx._mandarCruceSemanal_(miercoles);
  assert.deepEqual(mandados.map(m => m.para), ['yo@ejemplo.test']);
}
// ---- sin la propiedad de destinatarios no se instala el disparador
{
  const {ctx} = contexto();
  assert.throws(() => ctx.instalarCruceSemanal(), /DESTINATARIOS_CRUCE/);
}

console.log('OK: mail del cruce semanal, cuándo se manda y cuándo avisa la falla. Datos inventados.');
