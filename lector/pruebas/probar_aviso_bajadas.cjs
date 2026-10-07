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

const ahora = new Date('2026-09-28T10:30:00Z'); // lunes 07:30
const fecha = (dia, hora='00:00') => new Date(`2026-09-${dia}T${hora}:00-03:00`);
function foto() {
  const entradas = [];
  for (const empresa of ['A','AA']) for (const lista of (empresa==='A'?['cobranzas','pagos','cheques terceros','cheques propios','movimientos tesoreria','tesoreria detalle']:['cobranzas','pagos','cheques terceros','movimientos tesoreria','tesoreria detalle']))
    entradas.push({nombre:`${empresa} ${lista} 2026-09-28.xlsx`,ruta:'Tango/inventado.xlsx',tipo:lista.includes('tesoreria')?(empresa==='A'?'tesoreria_a':'tesoreria_aa'):'tango',fecha:fecha('28','05:46')});
  entradas.push({nombre:'Movimientos Galicia 2026-09-28.xlsx',ruta:'Bancos/galicia/Movimientos Galicia 2026-09-28.xlsx',tipo:'bancos',fecha:fecha('28','05:48')});
  return {entradas, publicados:[],retenidos:[],log:[],errores:{},ultimaPasada:fecha('28','07:08'),
    tangoParte:{fecha:fecha('28','05:46'),ok:11,total:11,fallas:[]},
    galiciaParte:{fecha:fecha('28','05:48'),ok:true,detalle:''},
    registro:[{tipo:'tango',estado:'ok',fecha:fecha('28','06:33'),detalle:'listo'}],
    saldos:[{banco:'Galicia',origen:'Extracto Galicia',empresa:'A',fecha:fecha('24')},
      {banco:'Macro',origen:'Extracto Macro',empresa:'A',fecha:fecha('25')},
      {banco:'(varios)',origen:'Manual',empresa:'AA',fecha:fecha('25')},
      // Tarea 48: las cajas con arqueo a mano no son bancos (no piden extracto).
      {banco:'Caja A',origen:'Manual',empresa:'A',fecha:fecha('20')},
      {banco:'Caja AA',origen:'Manual',empresa:'AA',fecha:fecha('20')}]};
}
let casos=0;
function probar(cambio, n, presentes=[], ausentes=[]) {
  const datos=foto(); cambio(datos);
  const aviso=contexto._armarAviso_(ahora,datos);
  assert.equal(aviso.asunto, `NAVAR · 28/09 · ${n===1?'falta 1 cosa':n?'faltan '+n+' cosas':'todo al día'}`);
  presentes.forEach(t=>assert.ok(aviso.cuerpo.includes(t), t+'\n'+aviso.cuerpo));
  ausentes.forEach(t=>assert.ok(!aviso.cuerpo.includes(t),t+'\n'+aviso.cuerpo));
  const lineas=aviso.cuerpo.split('\n').filter(l=>/^[☑☐]/.test(l));
  assert.equal(lineas.length,5); // una por fuente, sin repetir ninguna (el arqueo no va: tarea 41)
  for (const fuente of ['Tango A:','Tango AA:','Galicia:','Macro:','La Sheet'])
    assert.equal(lineas.filter(l=>l.includes(fuente)).length,1);
  assert.equal(lineas.filter(l=>l.startsWith('☐')).length,n);
  casos++;return aviso;
}
probar(()=>{},0,['☑ Tango A: cobranzas, pagos, cheques terceros, cheques propios, tesorería, detalle de tesorería', '☑ Tango AA:','☑ Galicia: 05:48 · movimientos hasta 24/09','☑ Macro: al día, extracto hasta 25/09','☑ La Sheet se actualizó (06:33)'],['❌','⚠️','El vigilante procesó','Llegó a Drive']);
probar(d=>{d.tangoParte.ok=9;d.tangoParte.fallas=['A pagos 2026-09-28.xlsx: timeout','AA cobranzas 2026-09-28.xlsx: HTTP 500'];},2,['☐ Tango A: pagos: el servidor de Tango no respondió a tiempo','☐ Tango AA: cobranzas: el servidor de Tango respondió con un error','último archivo: 28/09 05:46']);
probar(d=>{d.tangoParte.fecha=fecha('27','05:46');},2,['la bajada de Tango no corrió hoy (¿está prendida la notebook?) · última: 27/09 05:46']);
probar(d=>{d.tangoParte=null;},2,['última: no disponible']);
probar(d=>{d.galiciaParte.ok=false;d.galiciaParte.detalle='se cerró el navegador al guardar';},1,['☐ Galicia: el bot falló a las 05:48 (se cortó la descarga del banco a mitad de camino) · se reintenta solo hasta las 16:00','Último extracto: 28/09 05:48']);
probar(d=>{d.galiciaParte=null;},1,['el bot no corrió hoy']);
probar(d=>{d.galiciaParte.ok=false;d.entradas.push({nombre:'Movimientos GALICIA 2026-09-28_062000.xlsx',ruta:'Bancos/galicia/viejo.xlsx',tipo:'bancos',fecha:fecha('28','06:20')});},1,['Último extracto: 28/09 06:20']);
probar(d=>{d.saldos[1].fecha=fecha('24');},1,['☐ Macro: último extracto del 24/09 (hace 4 días) · subir a mano']);
probar(d=>{d.saldos[2].fecha=fecha('21');},0,[],['Arqueo','arqueo']);
probar(d=>{d.registro[0].fecha=fecha('27','06:33');},1,['La Sheet no importó lo de hoy · última importación: 27/09 06:33']);
probar(d=>{d.registro[0].fecha=fecha('28','05:47');},1,['La Sheet no importó lo de hoy']);
probar(d=>{d.registro.push({tipo:'cajas',estado:'ERROR',fecha:fecha('26','08:32'),detalle:'rate limit'}, {tipo:'cajas',estado:'ok',fecha:fecha('26','09:33'),detalle:''});},0,[],['rate limit','⚠️']);
probar(d=>{d.registro.push({tipo:'cajas',estado:'ERROR',fecha:fecha('26','08:32'),detalle:'rate limit'});},0,['⚠️ REVISAR','La Sheet no pudo cargar cajas (Google estaba saturado un momento) · se reintenta sola cada hora']);
probar(d=>{d.ultimaPasada=fecha('28','05:00');},0,['La notebook no está procesando']);
probar(d=>{d.errores.Drive='sin acceso';},0,['No se pudo leer Drive']);
probar(d=>{d.retenidos.push({nombre:'retenido.xlsx',tipo:'bancos',fecha:fecha('28','06:08')});},0,['Archivo retenido: retenido.xlsx']);
assert.equal(contexto._parteTangoAviso_('2026-09-28T08:46:00+00:00\n8 de 8').ok,8);
assert.equal(contexto._parteGaliciaAviso_('Bot Galicia - 28/09/2026 05:48\nOK: no fallo ninguna empresa.').ok,true);
console.log(`OK: ${casos} casos de checklist y lectura de partes; sin Google ni envío de mails.`);
// Un ok de instalación no cuenta como importación; tampoco se acepta una fecha futura.
probar(d=>{d.registro[0].tipo='sistema';},1,['La Sheet no importó lo de hoy']);
probar(d=>{d.registro[0].fecha=fecha('28','08:00');},1,['La Sheet no importó lo de hoy']);
probar(d=>{d.tangoParte.ok=10;d.tangoParte.fallas=['A cheques propios 2026-09-28.xlsx: timeout'];
  const f=d.entradas.find(f=>f.nombre.startsWith('A cheques propios'));
  f.nombre='A cheques propios 2026-09-25.xlsx';f.fecha=fecha('25','05:46');
},1,['☐ Tango A: cheques propios: el servidor de Tango no respondió a tiempo · último archivo: 25/09 05:46','☑ Tango AA: las 5 fotos llegaron']);
contexto.FUENTES_AUTOMATICAS.push('macro');
probar(d=>{d.bancosPartes={macro:{fecha:fecha('28','05:49'),ok:true}};},0,['☑ Macro: 05:49 · movimientos hasta 25/09']);
contexto.FUENTES_AUTOMATICAS.pop();
console.log(`OK total: ${casos} casos de checklist.`);
// Nombres de presentación: no cambian las claves ni las rutas.
for (const [entrada, salida] of Object.entries({
  GALICIA:'Galicia', NACION:'Nación', CORRIENTES:'Corrientes', MACRO:'Macro', BBVA:'BBVA', ITAU:'Itau'
})) assert.equal(contexto._nombreBancoAviso_(entrada),salida);
probar(d=>{d.saldos[0].banco='GALICIA';d.saldos[0].origen='Extracto GALICIA';},0,['☑ Galicia:'],['☑ GALICIA:']);
for (const [entrada,salida] of [['NACION','Nación'],['ITAU','Itau']]) {
  const d=foto();d.saldos[1].banco=entrada;d.saldos[1].origen='Extracto '+entrada;
  const a=contexto._armarAviso_(ahora,d);
  assert.equal(a.asunto,'NAVAR · 28/09 · todo al día');
  assert.ok(a.cuerpo.includes('☑ '+salida+': al día'));
}
// Ejercita la lectura real con dobles de Drive: no basta inyectar errores ya armados.
function iterador(elementos) {
  let i=0;return {hasNext:()=>i<elementos.length,next:()=>elementos[i++]};
}
function leerParte(archivos) {
  const carpeta={getFilesByName: nombre=>{
    assert.equal(nombre,'_ESTADO_Galicia_28-09.txt');return iterador(archivos);
  }};
  const bancos={getFoldersByName:()=>iterador([carpeta])};
  const raiz={
    getFolders:()=>iterador([]),
    getFoldersByName:nombre=>iterador(nombre==='Bancos'?[bancos]:[])
  };
  contexto.CARPETA_RAIZ='Datos inventados';
  contexto.DriveApp={getFoldersByName:()=>iterador([raiz])};
  contexto.SpreadsheetApp={getActiveSpreadsheet:()=>{throw Error('sin Sheet de prueba');}};
  return contexto._leerDatosAviso_(ahora);
}
const ausente=leerParte([]);
assert.equal(ausente.errores.GaliciaParte,undefined);
probar(d=>{d.galiciaParte=ausente.galiciaParte;d.bancosPartes=ausente.bancosPartes;},1,
  ['☐ Galicia: el bot no corrió hoy'],['⚠️','No se pudo leer GaliciaParte']);
const duplicado=leerParte([{},{}]);
assert.match(duplicado.errores.GaliciaParte,/más de un estado/);
probar(d=>{d.galiciaParte=null;d.errores.GaliciaParte=duplicado.errores.GaliciaParte;},1,
  ['⚠️ REVISAR','No se pudo leer GaliciaParte: Hay más de un estado']);
const ilegible=leerParte([{getBlob:()=>{throw Error('acceso denegado');}}]);
assert.equal(ilegible.errores.GaliciaParte,'acceso denegado');
const ajeno=leerParte([{getBlob:()=>({getDataAsString:()=> 'Bot Otro - 28/09/2026 05:48'})}]);
assert.match(ajeno.errores.GaliciaParte,/no corresponde al banco/);
console.log('OK: nombres en checklist y lectura de partes ausentes, duplicados, ilegibles y ajenos.');

// Las nueve fotos incluyen tesorería de A; una falla suya no desmarca AA.
probar(d=>{d.tangoParte.ok=10;d.tangoParte.fallas=['A movimientos tesoreria 2026-09-28.xlsx: timeout'];},1,
  ['☐ Tango A: tesorería: el servidor de Tango no respondió a tiempo · último archivo: 28/09 05:46','☑ Tango AA: las 5 fotos llegaron']);
probar(d=>{d.tangoParte.ok=10;d.tangoParte.fallas=['AA movimientos tesoreria 2026-09-28.xlsx: timeout'];},1,
  ['☑ Tango A: las 6 fotos llegaron','☐ Tango AA: tesorería: el servidor de Tango no respondió a tiempo']);
probar(d=>{d.tangoParte.ok=9;d.tangoParte.total=9;},2,
  ['☐ Tango A:', '☐ Tango AA:', 'parte incompleto (9 de 9)'], ['☑ Tango A:', '☑ Tango AA:']);
assert.equal(contexto._parteTangoAviso_('2026-09-28T08:46:00+00:00\n9 de 9').total,9);
assert.equal(contexto.TANGO_BAJADAS,11);
// Un parte de antes de la tarea 48 (10 de 10) no alcanza: falta el detalle de AA.
probar(d=>{d.tangoParte.ok=10;d.tangoParte.total=10;},2,['parte incompleto (10 de 10)']);
probar(d=>{d.tangoParte.ok=10;d.tangoParte.fallas=['AA tesoreria detalle 2026-09-28.xlsx: timeout'];},1,
  ['☑ Tango A: las 6 fotos llegaron','☐ Tango AA: detalle de tesorería: el servidor de Tango no respondió a tiempo']);
probar(()=>{},0,['☑ Tango AA: cobranzas, pagos, cheques terceros, tesorería, detalle de tesorería'],['Caja A:','Caja AA:']);
// Si falla solo el detalle de tesorería (tarea 44), se nombra con su nombre en castellano.
probar(d=>{d.tangoParte.ok=10;d.tangoParte.fallas=['A tesoreria detalle 2026-09-28.xlsx: timeout'];},1,
  ['☐ Tango A: detalle de tesorería: el servidor de Tango no respondió a tiempo','☑ Tango AA: las 5 fotos llegaron']);

// Lee la carpeta real del mapa con un doble de Drive: A no se etiqueta como caja AA.
const exportA = {getName:()=> 'A movimientos tesoreria 2026-09-28.xlsx',
  getLastUpdated:()=>fecha('28','05:46'), getId:()=> 'inventado-a'};
const tesA = {getName:()=> 'Tesoreria A', getFiles:()=>iterador([exportA]),
  getFolders:()=>iterador([])};
const raizA = {getFolders:()=>iterador([tesA]), getFoldersByName:()=>iterador([])};
contexto.DriveApp={getFoldersByName:()=>iterador([raizA])};
const leidos=contexto._leerDatosAviso_(ahora);
assert.equal(leidos.errores.Drive,undefined);
assert.equal(leidos.entradas.length,1);
assert.equal(leidos.entradas[0].tipo,'tesoreria_a');
assert.equal(leidos.entradas[0].nombre,exportA.getName());
probar(d=>{d.entradas=d.entradas.filter(f=>f.tipo!=='tesoreria_a').concat(leidos.entradas);
  d.tangoParte.ok=10;d.tangoParte.fallas=['A movimientos tesoreria 2026-09-28.xlsx: timeout'];},1,
  ['☐ Tango A: tesorería: el servidor de Tango no respondió a tiempo · último archivo: 28/09 05:46','☑ Tango AA:']);
console.log('OK: once bajadas, partes viejos incompletos y tesorería A separada de caja AA.');

// Tarea 39: un extracto que llegó y no se pudo leer se dice con su nombre, no como "subir a mano".
assert.deepEqual(JSON.parse(JSON.stringify(contexto._ilegiblesAviso_(
  '# Extractos\nArchivos leídos: 38; salteados: 1.\n' +
  '- no pude leer corrientes/Res_130559 inventado.pdf: ValueError: no se reconocieron movimientos ni saldos\n' +
  '- `Macro 26-06.pdf` · cuenta inventada'))),
  [{banco:'corrientes',archivo:'Res_130559 inventado.pdf',motivo:'no se reconocieron movimientos ni saldos'}]);
const raro={banco:'macro',archivo:'Raro.pdf',motivo:'no se reconocieron movimientos ni saldos'};
probar(d=>{d.saldos[1].fecha=fecha('22');d.ilegibles=[raro];},1,
  ['☐ Macro: llegó «Raro.pdf» pero no se pudo leer (no se reconocieron movimientos ni saldos) · avisar a finauto · último extracto leído: 22/09'],
  ['subir a mano','⚠️']);
probar(d=>{d.ilegibles=[raro];},0,
  ['☑ Macro: al día','⚠️ REVISAR','- Macro: llegó «Raro.pdf» pero no se pudo leer']);
probar(d=>{d.ilegibles=[{banco:'galicia',archivo:'Otro.xlsx',motivo:'encabezado desconocido'}];},0,
  ['☑ Galicia: 05:48','- Galicia: llegó «Otro.xlsx» pero no se pudo leer (encabezado desconocido)']);
probar(d=>{d.ilegibles=[{banco:'itau',archivo:'Nuevo.pdf',motivo:'formato desconocido'}];},0,
  ['- Bancos/itau: llegó «Nuevo.pdf» pero no se pudo leer (formato desconocido)']);
probar(d=>{d.saldos[1].fecha=fecha('22');d.ilegibles=[raro,{banco:'macro',archivo:'Otro.pdf',motivo:'vacío'}];},1,
  ['llegó «Raro.pdf» pero no se pudo leer (no se reconocieron movimientos ni saldos) y 1 archivo(s) más']);
console.log('OK: extractos que llegaron y no se pudieron leer.');

// Tarea 42: un banco manual sin movimientos el último día hábil está al día si el extracto se subió.
const subidoMacro=(dia,nombre='Movimientos Macro inventado.xls')=>({nombre,ruta:'Bancos/macro/'+nombre,tipo:'bancos',fecha:fecha(dia,'23:59')});
probar(d=>{d.saldos[1].fecha=fecha('24');d.entradas.push(subidoMacro('26'));},0,
  ['☑ Macro: al día, extracto subido el 26/09 (último movimiento 24/09)']);
probar(d=>{d.saldos[1].fecha=fecha('24');d.entradas.push(subidoMacro('23'));},1,
  ['☐ Macro: último extracto del 24/09 (hace 4 días) · subir a mano']);
probar(d=>{d.saldos[1].fecha=fecha('22');d.entradas.push(subidoMacro('24'));},1,
  ['☐ Macro: último extracto subido el 24/09 (hace 4 días) · subir a mano']);
probar(d=>{d.saldos[1].fecha=fecha('22');d.entradas.push(subidoMacro('26','Raro.pdf'));
  d.ilegibles=[{banco:'macro',archivo:'Raro.pdf',motivo:'formato desconocido'}];},1,
  ['☐ Macro: llegó «Raro.pdf» pero no se pudo leer (formato desconocido)']);
console.log('OK: extractos subidos sin movimientos del último día hábil.');
