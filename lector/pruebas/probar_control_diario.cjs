// Datos inventados. Evaluamos las fórmulas que se escriben, sin abrir una Sheet.
const fs = require('node:fs'), vm = require('node:vm'), path = require('node:path');
const assert = require('node:assert/strict');
const c = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../../clientes/navar/herramientas/crear_cash.gs'), 'utf8'), c);
c.R = Object.fromEntries(['movImp','movFecha','movEstado','movOrigen','movBanco','movTipo','movCat'].map(k => [k,k]));
function evaluar(f, vars = {}, filas = []) {
  const cols = Object.fromEntries(Object.keys(c.R).map(k => [k, filas.map(r => r[k])]));
  function cumple(v, criterio) {
    const s = String(criterio), m = s.match(/^(>=|<=|<>|>|<)(.*)$/);
    if (m) return ({'>=':v >= +m[2], '<=':v <= +m[2], '>':v > +m[2], '<':v < +m[2], '<>':v !== m[2]})[m[1]];
    const patron = s.replace(/~([~*?])|([*?])|([.*+?^${}()|[\]\\])/g, (_, literal, comodin, especial) => literal ? '\\' + literal : comodin === '*' ? '.*' : comodin === '?' ? '.' : '\\' + especial);
    return new RegExp('^' + patron + '$').test(String(v));
  }
  const funcs = {IF:(b,x,y)=>b?x:y, AND:(...x)=>x.every(Boolean), OR:(...x)=>x.some(Boolean), N:x=>typeof x==='number'?x:0, ABS:Math.abs, MAX:Math.max, ROUND:(x,n)=>Math.round(x*10**n)/10**n,
    SUMIFS:(s,...args)=>s.reduce((t,v,i)=>args.every((a,k)=>k%2 || cumple(a[i],args[k+1]))?t+v:t,0)};
  const args = {...funcs,...cols,...vars};
  // En estas fórmulas & concatena el operador de criterio con un número de fecha.
  const js = f.replace(/&/g,'+').replace(/(?<![<>=!])=(?!=)/g,'===');
  return Function(...Object.keys(args), 'return '+js)(...Object.values(args));
}
function estado({fecha=10, ultimo=10, ing=0, egr=0, pases=0, dif=0, banco=0, caja=0}={}) {
  return evaluar(c._estadoDia_('fecha','ultimo','ing','egr','pases','dif',['banco'],['banco','caja']),{fecha,ultimo,ing,egr,pases,dif,banco,caja});
}
assert.equal(estado({banco:25,dif:25}),'REVISAR');
assert.equal(estado({banco:-25,dif:-25}),'REVISAR'); // se cancela al otro día, pero ambos fallan
assert.equal(estado({caja:80,dif:80}),'OK');
assert.equal(estado({banco:.4,dif:.4}),'OK');
assert.equal(estado({banco:1,dif:1}),'REVISAR');
assert.equal(estado({pases:-12}),'REVISAR');
assert.equal(estado({dif:-15}),'REVISAR'); // cuenta sin saldo
assert.equal(estado({caja:1,dif:2}),'OK'); // un peso por sumar cuentas ya redondeadas no es una cuenta sin saldo
assert.equal(estado({fecha:11,banco:99}),'sin extracto');
assert.equal(estado(),'sin mov.');
assert.equal(estado({ing:10}),'OK');
assert.equal(evaluar(c._estadoDia_('10','10','0','0','0','0',['v'],['v']),{v:''}),'sin mov.');
const fila = (fecha, origen, banco, imp, estado='Real', tipo='Ingreso', cat='Otros') => ({movFecha:fecha,movOrigen:origen,movBanco:banco,movImp:imp,movEstado:estado,movTipo:tipo,movCat:cat});
const datos = [fila(10,'Extracto BANCO UNO','BANCO UNO',10),fila(10.8,'Extracto BANCO UNO','BANCO UNO',2),
  fila(9.9,'Extracto BANCO UNO','BANCO UNO',999),fila(11,'Extracto BANCO UNO','BANCO UNO',999),
  fila(10,'Extracto BANCO DOS','BANCO DOS',7),fila(10,'Extracto BANCO UNO','BANCO UNO',999,'Proyectado'),
  fila(10,'Manual','BANCO UNO',999),fila(10,'Tango caja A ejemplo','Caja A',3),fila(10,'Tango AA ejemplo','Caja AA',5)];
assert.equal(evaluar(c._movCuentaDelDia_({nombre:'BANCO UNO'},'10'),{},datos),12);
assert.equal(evaluar(c._movCuentaDelDia_({nombre:'Caja A',caja:'Caja A'},'10'),{},datos),3);
assert.equal(evaluar(c._movCuentaDelDia_({nombre:'BANCO *'},'10'),{},[fila(10,'Extracto BANCO UNO','',999),fila(10,'Extracto BANCO *','',4)]),4);
const movimientos = [fila(10,'Extracto BANCO UNO','',20),fila(10,'Extracto BANCO UNO','',-8,'Real','Egreso'),fila(10,'Extracto BANCO UNO','',-4,'Real','Egreso','Transferencia Interna')];
assert.equal(evaluar(c._movTotalDelDia_('10','Ingreso'),{},movimientos),20);
assert.equal(evaluar('-'+c._movTotalDelDia_('10','Egreso'),{},movimientos),8);
assert.equal(evaluar(c._movTotalDelDia_('10'),{},movimientos),-4);
assert.equal(evaluar(c._diferenciaCuentaDia_('10','10','0','11','10')),'');
assert.equal(evaluar(c._diferenciaCuentaDia_('12','10','0','11','10')),2);
assert.equal(evaluar(c._diferenciaCuentaDia_('10.4','10','0','10','10')),0);
assert.equal(evaluar(c._estadoControl_('0','999999','0')),'OK');
assert.equal(evaluar(c._estadoControl_('0','1000000','0')),'REVISAR');
assert.equal(evaluar(c._estadoControl_('0','1','0',1)),'REVISAR');
console.log('probar_control_diario: OK');

// Hoja de juguete: comprueba bloques, límites, avisos y que rearmar no acumule reglas.
function hoja() {
  const celdas = new Map(), ocultas = [], bloques = [];
  let reglas = [], filas = 100, columnas = 40;
  const h = {
    celdas, ocultas, bloques,
    getRange(r,col,nr=1,nc=1) {
      const rango = new Proxy({}, {get(_,metodo) {
        if (metodo === 'setFormulas' || metodo === 'setValues') return valores => {
          assert.equal(valores.length,nr); valores.forEach((fila,i)=>{assert.equal(fila.length,nc);fila.forEach((v,j)=>celdas.set(`${r+i}:${col+j}`,v));});
          bloques.push([r,col,nr,nc]); return rango;
        };
        if (metodo === 'setFormula' || metodo === 'setValue') return v=>{celdas.set(`${r}:${col}`,v);return rango;};
        return ()=>rango;
      }}); return rango;
    },
    getMaxRows:()=>filas, getMaxColumns:()=>columnas,
    insertRowsAfter:(f,n)=>{filas+=n;}, insertColumnsAfter:(f,n)=>{columnas+=n;},
    getConditionalFormatRules:()=>reglas.slice(), setConditionalFormatRules:r=>{reglas=r;},
    hideRows:(...r)=>ocultas.push(['filas',...r]), hideColumns:(...r)=>ocultas.push(['columnas',...r]),
    showRows:()=>{},showColumns:()=>{},setColumnWidths:()=>{},setColumnWidth:()=>{},setFrozenRows:()=>{},setFrozenColumns:()=>{},clear:()=>celdas.clear(),clearFormats:()=>{}
  }; return h;
}
c.SpreadsheetApp = {newConditionalFormatRule:()=>{
  const rule = new Proxy({}, {get:(_,k)=>k==='build'?()=>({}):()=>rule}); return rule;
}};
c._bancos_ = ()=>[{nombre:'Caja A',caja:'Caja A',etiqueta:'Caja A'}, {nombre:'BANCO UNO',etiqueta:'BANCO UNO'}];
c.R.salFecha='salFecha';c.R.salBanco='salBanco';c.R.salImp='salImp';
const h = hoja(), ss = {getSheetByName:()=>h, setActiveSheet:()=>{},getName:()=> 'Ejemplo - Cash Flow'};
c._armarControlDiario_(ss);
assert.ok(h.bloques.some(b=>String(b)==='10,1,120,11'));
assert.ok(h.bloques.some(b=>String(b)==='10,12,121,2'));
assert.equal(h.celdas.get('130:1'),'=$B$2-120');
assert.equal(h.celdas.get('9:10'),'BANCO UNO');
assert.equal(h.celdas.get('9:11'),'Caja A');
assert.ok(h.celdas.get('8:10').includes('ATRASADO'));
assert.equal(h.celdas.get('8:11'),'=""');
assert.ok(h.celdas.get('129:3').includes('L130:M130'));
assert.ok(h.celdas.get('2:3').includes('A10:A129'));
assert.ok(h.celdas.get('2:3').includes('TODAY()-30'));
assert.ok(c._avisoDiario_('COUNTIF(B40:H40,"REVISAR")').includes('sección 7'));
assert.equal(h.getConditionalFormatRules().length,6);
c._armarControlDiario_(ss);
assert.equal(h.getConditionalFormatRules().length,6);
assert.ok(h.ocultas.some(r=>String(r)==='filas,130'));
assert.ok(h.ocultas.some(r=>String(r)==='columnas,12,2'));
console.log('Control diario: armado y rearmado por bloques OK');
