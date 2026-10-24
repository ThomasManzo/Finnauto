// Verificamos las fórmulas armando una hoja de juguete, sin conexión a Google.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
let cells=new Map(), formulas=new Map(),validaciones=[],grupos=[];
const at=(r,c)=>`${r},${c}`;
function range(r,c,n=1,w=1){let proxy;const obj={
 setValue(v){cells.set(at(r,c),v);return proxy;},
 setValues(vs){vs.forEach((row,i)=>row.forEach((v,j)=>cells.set(at(r+i,c+j),v)));return proxy;},
 setFormula(v){formulas.set(at(r,c),v);return proxy;},
 setDataValidation(v){validaciones.push([r,c,v]);return proxy;},
 shiftRowGroupDepth(v){grupos.push([r,n,v]);return proxy;}
};proxy=new Proxy(obj,{get:(o,k)=>k in o?o[k]:()=>proxy});return proxy;}
const h={getRange:range,getMaxRows:()=>1000,showRows(){},getDataRange:()=>({getValues:()=>Array.from({length:180},(_,i)=>Array.from({length:15},(_,j)=>cells.get(at(i+1,j+1))??''))}),setColumnWidth(){},hideRows(){},setFrozenRows(){},setFrozenColumns(){}};
let existente=false;
const ss={getSheetByName:n=>n==='Cash Mensual'?{}:existente?h:null,toast(){}};
const ctx=vm.createContext({SpreadsheetApp:{getActiveSpreadsheet:()=>ss,BorderStyle:{SOLID_MEDIUM:'medio'},newDataValidation:()=>{let opciones;return {requireValueInList(v){opciones=v;return this;},setAllowInvalid(v){assert.equal(v,false);return this;},build(){return opciones;}};}}});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../../clientes/navar/herramientas/crear_cash.gs'),'utf8'),ctx);
ctx._rangos_=()=>({cuTot:'cuTot',cuVto:'cuVto',cuEstado:'cuEstado',cuAuto:'cuAuto',diImp:'diImp',diVto:'diVto',diEstado:'diEstado',diAuto:'diAuto'});
ctx._hojaLimpia_=()=>{cells=new Map();formulas=new Map();return h;};ctx._cliente_=()=> 'Ejemplo';ctx._separadorLocal_=()=>{};
ctx.armarCompraCanchada();
const row=txt=>{for(const [k,v]of cells)if(k.endsWith(',1')&&v===txt)return Number(k.split(',')[0]);throw Error('Falta '+txt);};
const formula=(txt,c=2)=>formulas.get(at(row(txt),c));
const sup=k=>'$B$'+row(ctx.CC_SUPUESTOS.find(s=>s[0]===k)[1]);
const label=k=>ctx.CC_SUPUESTOS.find(s=>s[0]===k)[1];
const cost=ctx.CC_SUPUESTOS.filter(s=>/^(estampillas|paquetes|pallets|stretch|termo)(1|Medio)$/.test(s[0]));assert.equal(cost.length,10);
for(const s of ctx.CC_SUPUESTOS){assert.equal(cells.get(at(row(s[1]),2)),undefined);assert(formula('Faltan cargar').includes('ISBLANK($B$'+row(s[1])+')'));}
assert.deepEqual(JSON.parse(JSON.stringify(validaciones[0][2])),['contado','30 días']);
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
assert(formula('Compra de canchada (lo que se paga en el mes, según las partes)').includes('$B$'+row('TN compradas')+':$O$'+row('TN compradas')));
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
