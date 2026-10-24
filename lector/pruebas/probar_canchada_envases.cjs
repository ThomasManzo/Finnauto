// Verificamos las fórmulas armando una hoja de juguete, sin conexión a Google.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
let cells=new Map(), formulas=new Map(),validaciones=[],grupos=[],reglas=[];
const at=(r,c)=>`${r},${c}`;
function range(r,c,n=1,w=1){let proxy;const obj={
 setValue(v){cells.set(at(r,c),v);return proxy;},
 setValues(vs){vs.forEach((row,i)=>row.forEach((v,j)=>cells.set(at(r+i,c+j),v)));return proxy;},
 setFormula(v){formulas.set(at(r,c),v);return proxy;},
 setDataValidation(v){validaciones.push([r,c,v]);return proxy;},
 shiftRowGroupDepth(v){grupos.push([r,n,v]);return proxy;}
};proxy=new Proxy(obj,{get:(o,k)=>k in o?o[k]:()=>proxy});return proxy;}
const h={setConditionalFormatRules(v){reglas=v;},getRange:range,getMaxRows:()=>1000,showRows(){},getDataRange:()=>({getValues:()=>Array.from({length:180},(_,i)=>Array.from({length:15},(_,j)=>cells.get(at(i+1,j+1))??''))}),setColumnWidth(){},hideRows(){},setFrozenRows(){},setFrozenColumns(){}};
let existente=false;
const ss={getSheetByName:n=>n==='Cash Mensual'?{}:existente?h:null,toast(){}};
const ctx=vm.createContext({SpreadsheetApp:{getActiveSpreadsheet:()=>ss,BorderStyle:{SOLID_MEDIUM:'medio'},newConditionalFormatRule:()=>{let valores={},p; p=new Proxy(valores,{get:(o,k)=>k==='build'?()=>valores:v=>{o[k]=v;return p;}});return p;},newDataValidation:()=>{let opciones;return {requireValueInList(v){opciones=v;return this;},requireFormulaSatisfied(v){opciones=v;return this;},setAllowInvalid(v){assert.equal(v,false);return this;},build(){return opciones;}};}}});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../../clientes/navar/herramientas/crear_cash.gs'),'utf8'),ctx);
// La planilla de juguete acepta coma como separador (la real en español usa punto y coma).
ctx._separadorDeEstaPlanilla_=()=>',';
ctx._rangos_=()=>({cuTot:'cuTot',cuVto:'cuVto',cuEstado:'cuEstado',cuAuto:'cuAuto',diImp:'diImp',diVto:'diVto',diEstado:'diEstado',diAuto:'diAuto'});
ctx._hojaLimpia_=()=>{cells=new Map();formulas=new Map();return h;};ctx._cliente_=()=> 'Ejemplo';ctx._separadorLocal_=()=>{};
ctx.armarCompraCanchada();
const row=txt=>{for(const [k,v]of cells)if(k.endsWith(',1')&&v===txt)return Number(k.split(',')[0]);throw Error('Falta '+txt);};
const formula=(txt,c=2)=>formulas.get(at(row(txt),c));
const sup=k=>'$B$'+row(ctx.CC_SUPUESTOS.find(s=>s[0]===k)[1]);
const label=k=>ctx.CC_SUPUESTOS.find(s=>s[0]===k)[1];
const cost=ctx.CC_SUPUESTOS.filter(s=>/^(estampillas|paquetes|pallets|stretch|termo)(1|Medio)$/.test(s[0]));assert.equal(cost.length,10);
for(const s of ctx.CC_SUPUESTOS){assert.equal(cells.get(at(row(s[1]),2)),undefined);assert(formula('Faltan cargar').includes('ISBLANK($B$'+row(s[1])+')'));}
assert.deepEqual(JSON.parse(JSON.stringify(validaciones.find(v=>Array.isArray(v[2])&&v[2][0]==='contado')[2])),['contado','30 días']);
const costFormula=formula('Costo de envase por kg');
assert.equal(costFormula,'='+sup('mezcla')+'*SUM('+cost.filter(s=>s[0].endsWith('1')).map(s=>sup(s[0])).join(',')+')+(1-'+sup('mezcla')+')*SUM('+cost.filter(s=>s[0].endsWith('Medio')).map(s=>sup(s[0])).join(',')+')*2');
assert(formula('Intereses y gastos bancarios de la base').includes('MATCH("Intereses y gastos bancarios",\'Cash Mensual\'!$A:$A,0)'));
assert(formula('Intereses y gastos bancarios de la base').endsWith(',0,1,1,3))'));
const tn=row('TN vendidas'),env='Gastos de envase';
for(const c of [2,3,4]){const letra=String.fromCharCode(64+c),anterior=String.fromCharCode(64+Math.max(2,c-1));assert.equal(formula(env,c),'=IF('+sup('pagoEnvases')+'="30 días",'+anterior+tn+','+letra+tn+')*1000*$B$'+row('Costo de envase por kg'));assert.equal(formula('Comisiones',c),'='+letra+tn+'*1000*'+sup('comision'));}
const total='Total egresos de la operación';
assert.equal(formula(total),'='+['Gastos operativos sin secadero',env,'Comisiones','Compra de canchada (lo que se paga en el mes, según las partes)','Flete de la canchada'].map(t=>'B'+row(t)).join('+'));
assert.equal(formula('Gastos operativos sin secadero'),'=SUM(B'+row('Base de gastos × inflación (antes de las restas)')+':B'+row('Menos: secadero y hoja verde (no corren)')+')');
assert(formula('Menos: comisiones de la base × inflación').startsWith('=-'+sup('comision')+'*'+sup('kilosBase')+'*'));
assert(formula('Menos: estampillas de la base × inflación').startsWith('=-'+sup('estampillasBase')+'*'));
assert(formula('Menos: intereses y gastos bancarios de la base × inflación').startsWith('=-$B$'+row('Intereses y gastos bancarios de la base')+'*'));
assert(formula('Menos: secadero y hoja verde (no corren)').startsWith('=-'+sup('secadero')+'*(1+'), 'el secadero se actualiza por inflación, igual que la base');
assert.equal(formula('Total bancos y deuda'),'='+['Intereses y gastos bancarios','Deuda que sale sí o sí (débito automático)','Deuda que se paga por decisión'].map(t=>'B'+row(t)).join('+'));
assert.equal(formula('Saldo del mes pagando la deuda que vence'),'=B'+row('Resultado de la operación (antes de la deuda)')+'-B'+row('Total bancos y deuda'));
assert(formula('Compra de canchada (lo que se paga en el mes, según las partes)').includes('$B$'+row('TN compradas (lo que se usa)')+':$O$'+row('TN compradas (lo que se usa)')));
assert(grupos.some(g=>g[2]===1));assert(grupos.some(g=>g[2]===-8));
// Hay fórmulas completas en los catorce meses, incluso después del tramo del Cash Mensual.
for(const txt of ['Gastos operativos sin secadero','Gastos de envase','Comisiones','Intereses y gastos bancarios','Total bancos y deuda','Saldo acumulado'])for(let c=2;c<=15;c++)assert(formula(txt,c));
for(let c=2;c<=15;c++)assert.equal(formula('Menos: intereses y gastos bancarios de la base × inflación',c),'=-'+formula('Intereses y gastos bancarios',c).slice(1));
// Rearmar conserva también los ceros y las opciones de pago, además de los valores anteriores.
ctx.CC_SUPUESTOS.forEach((s,i)=>cells.set(at(row(s[1]),2),s[0]==='pagoEnvases'?'30 días':i));
const saved=new Map(ctx.CC_SUPUESTOS.map((s,i)=>[s[0],s[0]==='pagoEnvases'?'30 días':i]));
range(row('TN vendidas'),2,1,14).setValues([Array(14).fill(100)]);existente=true;ctx.armarCompraCanchada();
ctx.CC_SUPUESTOS.forEach(s=>assert.equal(cells.get(at(row(s[1]),2)),saved.get(s[0])));assert.equal(cells.get(at(row('TN vendidas'),2)),100);
console.log('Canchada: fórmulas, referencias, faltantes, pago, grupos y conservación OK');

// Migración: los textos anteriores conservan stock y compras manuales al rearmar.
const stockRow=row(label('stock')),manualRow=row('TN compradas (a mano)');
cells.set(at(stockRow,1),'Stock de canchada propia al empezar (TN)');cells.set(at(stockRow,2),500);
cells.set(at(manualRow,1),'TN compradas');range(manualRow,2,1,14).setValues([Array(14).fill(73)]);
ctx.armarCompraCanchada();assert.equal(cells.get(at(row(label('stock')),2)),500);assert.equal(cells.get(at(row('TN compradas (a mano)'),2)),73);
assert.equal(cells.get(at(row('TN compradas (lo que se usa)'),2)),undefined);
assert.equal(reglas[0].whenNumberGreaterThan,0);
assert.deepEqual(JSON.parse(JSON.stringify(validaciones.find(v=>Array.isArray(v[2])&&v[2][0]==='automáticas')[2])),['automáticas','a mano']);
// Las compras calculadas solo nombran ventas, supuestos y compras anteriores; jamás stock futuro.
for(let c=2;c<=15;c++){
 const f=formula('TN compradas (automáticas)',c),refs=[...f.matchAll(/\$?([A-O])\$?(\d+)/g)];
 for(const r of refs)if(+r[2]===row('TN compradas (lo que se usa)'))assert(r[1].charCodeAt(0)-64<c,'referencia a compra actual o futura');
 assert(!f.includes('B'+row('Stock listo a fin de mes (TN)')));
}
// Evaluador mínimo para las fórmulas de stock de esta prueba. Los rangos se leen solo cuando
// SUM o INDEX los necesitan; detectamos recursión para que una referencia circular falle.
function escenario({stock=500,N=4,espera=0,modo='automáticas',ventas=Array(14).fill(100),manual=Array(14).fill(37)}={}){
 for(const [k,v]of Object.entries({stock,cobertura:N,lista:espera,compras:modo,pCanch:1000}))cells.set(at(row(label(k)),2),v);
 ventas.forEach((v,i)=>cells.set(at(row('TN vendidas'),i+2),v));manual.forEach((v,i)=>cells.set(at(row('TN compradas (a mano)'),i+2),v));
 const cache=new Map(),visitando=new Set();
 function valor(c,r){const key=at(r,c);if(cache.has(key))return cache.get(key);assert(!visitando.has(key),'Referencia circular en '+key);visitando.add(key);
  let v=cells.get(key)??0;
  if(formulas.has(key)){
   const f=formulas.get(key).slice(1).replace(/SUM\(\$B\$(\d+):INDEX\(\$B\$\1:\$O\$\1,/g,(_,r)=>'SUM(TAKE($B$'+r+':$O$'+r+',').replace(/\$?([A-O])\$?(\d+)(?::\$?([A-O])\$?(\d+))?/g,(_,c,r,d,s)=>d?`RANGE(${c.charCodeAt(0)-64},${r},${d.charCodeAt(0)-64},${s})`:`CELL(${c.charCodeAt(0)-64},${r})`).replace(/(?<![<>=!])=(?!=)/g,'===').replace(/\^/g,'**');
   const RANGE=(c,r,d,s)=>{let a=[];for(let j=r;j<=s;j++)for(let i=c;i<=d;i++)a.push([i,j]);return a;};
   const SUM=(...xs)=>xs.reduce((s,v)=>s+(Array.isArray(v)?v.reduce((a,[c,r])=>a+Number(valor(c,r)),0):Number(v)),0);
   v=Function('CELL','RANGE','SUM','INDEX','IF','MAX','MIN','TAKE','return '+f)(valor,RANGE,SUM,(a,i)=>{assert(a[i-1],'Índice fuera del rango');return valor(...a[i-1]);},(c,a,b)=>c?a:b,Math.max,Math.min,(a,n)=>a.slice(0,n));
  }
  visitando.delete(key);cache.set(key,v);return v;
 }
 // Cuenta aparte: proyecta el stock hasta antes de que llegue la compra actual, recorriendo
 // las llegadas de pedidos ya hechos. No usa las fórmulas ni sus referencias.
 const venta=m=>ventas[Math.min(13,m)],objetivo=m=>Array.from({length:N},(_,i)=>venta(m+i+1)).reduce((a,b)=>a+b,0);
 let stockReal=stock,ordenes=[],listos=[];
 for(let m=0;m<14;m++){
  let antesDeLlegar=stockReal;
  for(let t=m;t<m+espera;t++)antesDeLlegar+=(t-espera>=0?ordenes[t-espera]:0)-venta(t);
  const automatica=Math.max(0,objetivo(m+espera)+venta(m+espera)-antesDeLlegar);
  ordenes.push(modo==='a mano'?manual[m]:automatica);
  const llegan=m-espera>=0?ordenes[m-espera]:0;stockReal+=llegan-venta(m);listos.push(stockReal);
  assert.equal(valor(m+2,row('TN compradas (automáticas)')),automatica);
  assert.equal(valor(m+2,row('TN compradas (lo que se usa)')),ordenes[m]);
  assert.equal(valor(m+2,row('Llegan listas para moler (TN)')),llegan);
  assert.equal(valor(m+2,row('Stock listo a fin de mes (TN)')),stockReal);
  assert.equal(valor(m+2,row('Objetivo de stock listo (TN)')),objetivo(m));
  assert.equal(valor(m+2,row('Meses que cubre')),objetivo(m)===0?'':stockReal/(objetivo(m)/N));
  assert.equal(valor(m+2,row('Falta canchada para moler (TN)')),Math.max(0,-stockReal));
  assert.equal(valor(m+2,row('Compra de canchada del mes (valor sin flete)')),ordenes[m]*1000000);
 }
 return {ordenes,listos};
}
assert.deepEqual(escenario().ordenes.slice(0,3),[0,100,100]);
const verde=escenario({espera:2});assert.deepEqual(verde.ordenes.slice(0,4),[200,100,100,100]);assert.deepEqual(verde.listos.slice(0,4),[400,300,400,400]);
escenario({stock:50,espera:2});escenario({espera:8,N:12,ventas:Array.from({length:14},(_,i)=>50+10*i)});
escenario({espera:0,N:1,ventas:[100,200,50,0,100,200,0,0,100,20,30,50,0,90]});
escenario({modo:'a mano',espera:2,manual:Array.from({length:14},(_,i)=>i*10)});escenario({ventas:Array(14).fill(0)});
console.log('Stock: casos L=0/L=2/L=8, cobertura 1/4/12, faltantes, ventas variables/cero y modo manual OK; sin ciclos');
