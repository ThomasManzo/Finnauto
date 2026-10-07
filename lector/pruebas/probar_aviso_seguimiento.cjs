// Tarea 51. Datos inventados: el mail de la mañana en criollo y el seguimiento de la tarde,
// sin abrir Drive, la Sheet ni mandar mails.
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
    return formato.replace(/yyyy|MM|dd|HH|mm|ss/g, m => ({yyyy: p.year, MM: p.month, dd: p.day, HH: p.hour, mm: p.minute, ss: p.second})[m]);
  },
};
const contexto = vm.createContext({Date, Intl, Utilities});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../../clientes/navar/herramientas/aviso_diario.gs'), 'utf8'), contexto);

const hora = (h) => new Date(`2026-09-28T${h}:00-03:00`);
const fecha = (dia, h = '00:00') => new Date(`2026-09-${dia}T${h}:00-03:00`);
const FOTOS = {A: ['cobranzas', 'pagos', 'cheques terceros', 'cheques propios', 'movimientos tesoreria', 'tesoreria detalle'],
  AA: ['cobranzas', 'pagos', 'cheques terceros', 'movimientos tesoreria', 'tesoreria detalle']};

// Una mañana inventada: Tango y Galicia bajaron bien, la Sheet importó.
function foto({tango = 'ok', galicia = 'ok', registro = '06:33'} = {}) {
  const entradas = [];
  for (const e of ['A', 'AA']) for (const l of FOTOS[e])
    entradas.push({nombre: `${e} ${l} 2026-09-28.xlsx`, ruta: 'Tango/x.xlsx', tipo: 'tango', fecha: fecha('28', '05:46')});
  const tangoParte = tango === 'ok' ? {fecha: fecha('28', '05:46'), ok: 11, total: 11, fallas: []}
    : {fecha: fecha('28', '05:46'), ok: 10, total: 11, fallas: ['A pagos 2026-09-28.xlsx: <urlopen error [Errno 11001] getaddrinfo failed>']};
  const galiciaParte = galicia === 'ok' ? {fecha: fecha('28', '05:48'), ok: true, detalle: ''}
    : {fecha: fecha('28', '07:15'), ok: false, detalle: galicia};
  return {entradas, publicados: [], retenidos: [], log: [], errores: {}, ultimaPasada: fecha('28', '12:20'),
    tangoParte, galiciaParte, registro: [{tipo: 'tango', estado: 'ok', fecha: fecha('28', registro), detalle: ''}],
    saldos: [{banco: 'Galicia', origen: 'Extracto Galicia', empresa: 'A', fecha: fecha('25')},
      {banco: 'Macro', origen: 'Extracto Macro', empresa: 'A', fecha: fecha('25')}]};
}
// La notebook pasó hace 10 minutos (si no, aparecería como caída y sería otra falla).
const armar = (ahora, d) => { d.ultimaPasada = new Date(ahora.getTime() - 10 * 60000); return contexto._armarAviso_(ahora, d); };
const estado = (aviso) => JSON.parse(JSON.stringify(contexto._estadoAutomaticoAviso_(aviso)));

// ---- 1. El mail de la mañana en criollo y con "qué pasa ahora".
let m = armar(hora('07:30'), foto({tango: 'falla'}));
assert.match(m.cuerpo, /☐ Tango A: pagos: no se pudo conectar con el servidor de Tango \(¿está prendido y en la red\?\)/);
assert.match(m.cuerpo, /se reintenta solo hasta las 20:00/);
assert.ok(!/getaddrinfo|Errno/.test(m.cuerpo), 'el error técnico no va al mail');
m = armar(hora('07:30'), foto({galicia: 'LOGIN FALLIDO - CLAVE ENVIADA SIN CONFIRMAR: no apareció la empresa'}));
assert.match(m.cuerpo, /☐ Galicia: el bot falló a las 07:15 \(el banco recibió la clave y no confirmó la entrada/);
assert.match(m.cuerpo, /se reintenta solo hasta las 16:00/);
m = armar(hora('07:30'), foto({galicia: 'NO SE REINTENTA - el banco recibió la clave y no confirmó la entrada 2 veces hoy'}));
assert.match(m.cuerpo, /no se reintenta para no bloquear el usuario/);
assert.match(m.cuerpo, /revisar la clave antes de volver a probar/);
assert.ok(!/se reintenta solo hasta/.test(m.cuerpo.split('\n').find(l => l.startsWith('☐ Galicia'))));
// A la noche ya no quedan reintentos: hay que mirarlo.
m = armar(hora('20:30'), foto({tango: 'falla'}));
assert.match(m.cuerpo, /☐ Tango A: .*ya no quedan reintentos hoy: hay que revisar la notebook/);
// Lo que va al seguimiento es solo lo automático.
assert.deepEqual(estado(armar(hora('07:30'), foto({tango: 'falla'}))).faltan, ['Tango A']);

// ---- 2. El seguimiento de la tarde.
const manana = estado(armar(hora('07:30'), foto({tango: 'falla'})));
const seg = (h, d, ultimo) => {
  const r = contexto._seguimientoAviso_(hora(h), armar(hora(h), d), manana, ultimo);
  return r && JSON.parse(JSON.stringify(r));
};
// Mañana todo bien → no se manda nada en todo el día.
const todoBien = estado(armar(hora('07:30'), foto()));
assert.equal(contexto._seguimientoAviso_(hora('12:30'), armar(hora('12:30'), foto()), todoBien, null), null);
// La notebook que deja de procesar a la tarde también es automático: se avisa.
const caida = foto({tango: 'falla'});
const sCaida = contexto._seguimientoAviso_(hora('17:30'), (caida.ultimaPasada = fecha('28', '12:00'), contexto._armarAviso_(hora('17:30'), caida)), {faltan: ['Tango A']}, {faltan: ['Tango A']});
assert.match(JSON.parse(JSON.stringify(sCaida)).cuerpo, /☐ La notebook no está procesando/);
assert.equal(contexto._seguimientoAviso_(hora('12:30'), armar(hora('12:30'), foto()), null, null), null);
// Se arregló con un reintento → "se arregló solo".
let s = seg('12:30', foto());
assert.equal(s.asunto, 'NAVAR · 28/09 · seguimiento · se arregló todo');
assert.match(s.cuerpo, /✅ SE ARREGLÓ SOLO\n☑ Tango A: cobranzas, pagos/);
assert.match(s.cuerpo, /Todo lo automático quedó al día/);
// Sigue igual a las 12:30 → se manda una vez para que alguien lo mire.
s = seg('12:30', foto({tango: 'falla'}));
assert.equal(s.asunto, 'NAVAR · 28/09 · seguimiento · sigue faltando 1 cosa');
assert.match(s.cuerpo, /❌ SIGUE FALTANDO\n☐ Tango A: pagos: no se pudo conectar/);
// Sigue igual a las 17:30, ya avisado a las 12:30 → no se repite.
assert.equal(seg('17:30', foto({tango: 'falla'}), s.estado), null);
// Sigue igual a las 17:30 sin aviso de las 12:30 (no había cambiado nada y era tarde) → tampoco.
assert.equal(seg('17:30', foto({tango: 'falla'}), null), null);
// Se arregla recién a la tarde → a las 17:30 avisa que se arregló.
s = seg('17:30', foto(), estado(armar(hora('12:30'), foto({tango: 'falla'}))));
assert.equal(s.asunto, 'NAVAR · 28/09 · seguimiento · se arregló todo');
// Algo nuevo que falla a la tarde (Galicia), aunque Tango siga → avisa lo nuevo.
s = seg('17:30', foto({tango: 'falla', galicia: 'LOGIN FALLIDO - Timeout 30000ms exceeded', registro: '07:40'}), {faltan: ['Tango A']});
assert.equal(s.asunto, 'NAVAR · 28/09 · seguimiento · siguen faltando 2 cosas');
assert.match(s.cuerpo, /☐ Galicia: el bot falló a las 07:15 \(no pudo entrar al home banking\)/);
console.log('OK: mail de la mañana en criollo, freno de la clave, y seguimiento de la tarde (se arregló / sigue / no repite).');
