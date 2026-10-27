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
const h={getRowGroup:()=>({collapse(){}}),setConditionalFormatRules(v){reglas=v;},getRange:range,getMaxRows:()=>1000,getMaxColumns:()=>40,showRows(){},getDataRange:()=>({getValues:()=>Array.from({length:180},(_,i)=>Array.from({length:15},(_,j)=>cells.get(at(i+1,j+1))??''))}),setColumnWidth(){},hideRows(){},setFrozenRows(){},setFrozenColumns(){}};
let existente=false;
const ss={getSheetByName:n=>n==='Cash Mensual'?{}:existente?h:null,toast(){}};
const ctx=vm.createContext({SpreadsheetApp:{getActiveSpreadsheet:()=>ss,BorderStyle:{SOLID_MEDIUM:'medio'},newConditionalFormatRule:()=>{let valores={},p; p=new Proxy(valores,{get:(o,k)=>k==='build'?()=>valores:v=>{o[k]=v;return p;}});return p;},newDataValidation:()=>{let opciones;return {requireNumberBetween(a,b){opciones=[a,b];return this;},requireValueInRange(v){opciones=v;return this;},requireValueInList(v){opciones=v;return this;},requireFormulaSatisfied(v){opciones=v;return this;},setAllowInvalid(v){assert.equal(v,false);return this;},build(){return opciones;}};}}});
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
for(const s of ctx.CC_SUPUESTOS){assert.equal(cells.get(at(row(s[1]),2)),({tramo1:0,tramo2:0,plazo1:'contado',plazo2:'contado',plazoResto:'contado',blend:.6})[s[0]]);assert(formula('Faltan cargar').includes('ISBLANK($B$'+row(s[1])+')'));}
assert.deepEqual(JSON.parse(JSON.stringify(validaciones.find(v=>Array.isArray(v[2])&&v[2][0]==='contado')[2])),['contado','30 días']);
const costFormula=formula('Costo de envase por kg');
assert.equal(costFormula,'='+sup('mezcla')+'*SUM('+cost.filter(s=>s[0].endsWith('1')).map(s=>sup(s[0])).join(',')+')+(1-'+sup('mezcla')+')*SUM('+cost.filter(s=>s[0].endsWith('Medio')).map(s=>sup(s[0])).join(',')+')*2');
assert(formula('Intereses y gastos bancarios de la base').includes('MATCH("Intereses y gastos bancarios",\'Cash Mensual\'!$A:$A,0)'));
assert(formula('Intereses y gastos bancarios de la base').endsWith(',0,1,1,3))'));
const tn=row('TN vendidas'),env='Gastos de envase';
for(const c of [2,3,4]){const letra=String.fromCharCode(64+c),anterior=String.fromCharCode(64+Math.max(2,c-1));assert.equal(formula(env,c),'=IF('+sup('pagoEnvases')+'="30 días",'+anterior+tn+','+letra+tn+')*1000*$B$'+row('Costo de envase por kg'));assert.equal(formula('Comisiones',c),'='+letra+tn+'*1000*'+sup('comision'));}
const total='Total egresos de la operación';
assert.equal(formula(total),'='+['Gastos operativos sin secadero',env,'Comisiones','Compra de canchada (lo que se paga en el mes)','Flete de la canchada'].map(t=>'B'+row(t)).join('+'));
assert.equal(formula('Gastos operativos sin secadero'),'=SUM(B'+row('Base de gastos × inflación (antes de las restas)')+':B'+row('Menos: secadero y hoja verde (no corren)')+')');
assert(formula('Menos: comisiones de la base × inflación').startsWith('=-'+sup('comision')+'*'+sup('kilosBase')+'*'));
assert(formula('Menos: estampillas de la base × inflación').startsWith('=-'+sup('estampillasBase')+'*'));
assert(formula('Menos: intereses y gastos bancarios de la base × inflación').startsWith('=-$B$'+row('Intereses y gastos bancarios de la base')+'*'));
assert(formula('Menos: secadero y hoja verde (no corren)').startsWith('=-'+sup('secadero')+'*(1+'), 'el secadero se actualiza por inflación, igual que la base');
assert.equal(formula('Total bancos y deuda'),'='+['Intereses y gastos bancarios','Deuda que sale sí o sí (débito automático)','Deuda que se paga por decisión'].map(t=>'B'+row(t)).join('+'));
assert.equal(formula('Saldo del mes pagando la deuda que vence'),'=B'+row('Resultado de la operación (antes de la deuda)')+'-B'+row('Total bancos y deuda'));
assert(formula('Compra de canchada (lo que se paga en el mes)').includes('MATCH('+sup('plazoResto')));
assert(grupos.some(g=>g[2]===1));assert(grupos.some(g=>g[2]===-8));
// Hay fórmulas completas en los catorce meses, incluso después del tramo del Cash Mensual.
for(const txt of ['Gastos operativos sin secadero','Gastos de envase','Comisiones','Intereses y gastos bancarios','Total bancos y deuda','Saldo acumulado'])for(let c=2;c<=15;c++)assert(formula(txt,c));
for(let c=2;c<=15;c++)assert.equal(formula('Menos: intereses y gastos bancarios de la base × inflación',c),'=-'+formula('Intereses y gastos bancarios',c).slice(1));
// Rearmar conserva también los ceros y las opciones de pago, además de los valores anteriores.
ctx.CC_SUPUESTOS.forEach((s,i)=>cells.set(at(row(s[1]),2),s[0]==='pagoEnvases'?'30 días':s[0].startsWith("plazo")?"contado":i));
const saved=new Map(ctx.CC_SUPUESTOS.map((s,i)=>[s[0],s[0]==='pagoEnvases'?'30 días':s[0].startsWith("plazo")?"contado":i]));
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
 assert(!f.includes('B'+row('Stock total a fin de mes (TN)')));
}
// Evaluador mínimo para las fórmulas de stock de esta prueba. Los rangos se leen solo cuando
// SUM o INDEX los necesitan; detectamos recursión para que una referencia circular falle.
function escenario({stock=500,blend=.6,N=4,espera=0,modo='automáticas',ventas=Array(14).fill(100),manual=Array(14).fill(37)}={}){
 for(const [k,v]of Object.entries({stock,blend,cobertura:N,lista:espera,compras:modo,pCanch:1000}))cells.set(at(row(label(k)),2),v);
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
 let stockReal=stock,propio=stock,comprado=0,ordenes=[],listos=[],usos=[];
 for(let m=0;m<14;m++){
  // Simulación aparte: recorremos las llegadas y el consumo de la mezcla hasta que esté
  // listo el pedido de hoy. No reutiliza la suma acumulada de la fórmula de la hoja.
  let compradaProyectada=comprado,propiaProyectada=propio;
  for(let t=m;t<=m+espera;t++){
   if(t-espera>=0 && t-espera<m)compradaProyectada+=ordenes[t-espera];
   const uso=Math.min(propiaProyectada,blend*venta(t));propiaProyectada-=uso;
   compradaProyectada-=venta(t)-uso;
  }
  const automatica=Math.max(0,objetivo(m)+venta(m)-stockReal,-compradaProyectada);
  ordenes.push(modo==='a mano'?manual[m]:automatica);
  const llegan=m-espera>=0?ordenes[m-espera]:0,uso=Math.min(propio,blend*venta(m));
  propio-=uso;usos.push(uso);comprado+=llegan-(venta(m)-uso);stockReal+=ordenes[m]-venta(m);listos.push(stockReal);
  assert(Math.abs(valor(m+2,row('TN compradas (automáticas)'))-automatica)<1e-8);
  assert.equal(valor(m+2,row('TN compradas (lo que se usa)')),ordenes[m]);
  assert.equal(valor(m+2,row('Llegan listas para moler (TN)')),llegan);
  assert.equal(valor(m+2,row('Stock total a fin de mes (TN)')),stockReal);
  assert.equal(valor(m+2,row('Stock propio a fin de mes (TN)')),propio);
  assert.equal(valor(m+2,row('Canchada propia usada (TN)')),uso);
  assert.equal(valor(m+2,row('Stock comprado a fin de mes (TN)')),comprado);
  assert.equal(valor(m+2,row('Objetivo de stock total (TN)')),objetivo(m));
  assert.equal(valor(m+2,row('Meses que cubre')),objetivo(m)===0?'':stockReal/(objetivo(m)/N));
  assert.equal(valor(m+2,row('Falta canchada comprada para la mezcla (TN)')),Math.max(0,-comprado));
  assert.equal(valor(m+2,row('Compra de canchada del mes (valor sin flete)')),ordenes[m]*1000000);
  if(espera===0&&modo==='automáticas')assert(comprado>=-1e-8);
 }
 return {ordenes,listos,usos};
}
assert.deepEqual(escenario().ordenes.slice(0,3),[40,60,100]);
assert.deepEqual(escenario({ventas:Array(14).fill(200)}).usos.slice(0,6),[120,120,120,120,20,0]);
for(const blend of [0,.6,1])for(const espera of [0,2,8])for(const N of [1,4,12]){
 escenario({blend,espera,N});escenario({blend,stock:50,espera,N});
 escenario({blend,espera,N,ventas:Array.from({length:14},(_,i)=>50+10*i)});
 escenario({blend,espera,N,ventas:[100,200,50,0,100,200,0,0,100,20,30,50,0,90]});
 escenario({blend,modo:'a mano',espera,N,manual:Array.from({length:14},(_,i)=>i*10)});
 escenario({blend,espera,N,ventas:Array(14).fill(0)});
}
console.log('Stock: casos L=0/L=2/L=8, cobertura 1/4/12, faltantes, ventas variables/cero y modo manual OK; sin ciclos');

// Equilibrio: referencias por mes y casos límite, sin depender del calendario de pagos.
const variable='Costo variable por kg (canchada + flete + envase + comisión)',margen='Margen por kg',precioEq='Precio de equilibrio de la operación ($/kg)',tnEq='TN de equilibrio por mes';
assert(row('Resultado de la operación (antes de la deuda)')<row(variable));
assert(row(tnEq)<row('3 · Bancos y deuda'));
for(let c=2;c<=15;c++){
 const l=String.fromCharCode(64+c),ref=t=>l+row(t);
 assert.equal(formula(variable,c),'='+[sup('pCanch'),sup('flete'),'$B$'+row('Costo de envase por kg'),sup('comision')].join('+'));
 assert.equal(formula(margen,c),'='+ref('Precio ($/kg, sin IVA)')+'-'+ref(variable));
 assert.equal(formula(precioEq,c),'=IF('+ref('TN vendidas')+'=0,"",'+ref(variable)+'+'+ref('Gastos operativos sin secadero')+'/('+ref('TN vendidas')+'*1000))');
 assert.equal(formula(tnEq,c),'=IF('+ref(margen)+'<=0,"no hay volumen que alcance",'+ref('Gastos operativos sin secadero')+'/'+ref(margen)+'/1000)');
}
function equilibrio(precio,ventas){
 const valores={[sup('pCanch')]:1200,[sup('flete')]:30,['$B$'+row('Costo de envase por kg')]:200,[sup('comision')]:50,['B'+row('Precio ($/kg, sin IVA)')]:precio,['B'+row('TN vendidas')]:ventas,['B'+row('Gastos operativos sin secadero')]:100000000};
 for(const nombre of [variable,margen,precioEq,tnEq]){
  const f=formula(nombre).slice(1).replace(/\$?[A-O]\$?\d+/g,r=>JSON.stringify(valores[r])).replace(/(?<![<>=!])=(?!=)/g,'===');
  valores['B'+row(nombre)]=Function('IF','return '+f)((c,a,b)=>c?a:b);
 }
 return [variable,margen,precioEq,tnEq].map(n=>valores['B'+row(n)]);
}
const eq=equilibrio(2000,200);assert.deepEqual(eq.slice(0,3),[1480,520,1980]);assert(Math.abs(eq[3]-192.3076923077)<1e-8);
assert.equal(equilibrio(2000,0)[2],'');assert.equal(equilibrio(1480,200)[3],'no hay volumen que alcance');assert.equal(equilibrio(1400,200)[3],'no hay volumen que alcance');
console.log('Equilibrio: 14 meses, ejemplo inventado, cero ventas y margen cero/negativo OK');

// Tramos y migración: evaluamos las fórmulas emitidas, con una búsqueda de plazos real.
function pagos(compra,tramo1,tramo2,p1,p2,resto){
 const resultados=[],tn1=[],tn2=[],tnR=[];
 const inicio=row('Plazos de canchada')+1;
 const plazos=Array.from({length:10},(_,i)=>Array.from({length:6},(_,j)=>cells.get(at(inicio+i,j+1))));
 const valores={[sup('tramo1')]:tramo1,[sup('tramo2')]:tramo2,[sup('plazo1')]:p1,[sup('plazo2')]:p2,[sup('plazoResto')]:resto,[sup('pCanch')]:1000};
 for(let c=2;c<=15;c++){
  const l=String.fromCharCode(c+64);valores[l+row('TN compradas (lo que se usa)')]=compra;
  for(const [t,dest]of [['TN del tramo 1',tn1],['TN del tramo 2',tn2],['TN del resto',tnR]]){
   let f=formula(t,c).slice(1).replace(/\$?[A-O]\$?\d+/g,r=>JSON.stringify(valores[r]));
   const v=Function('MIN','MAX','return '+f)(Math.min,Math.max);valores[l+row(t)]=v;dest.push(v);
  }
  let f=formula('Compra de canchada (lo que se paga en el mes)',c).slice(1)
   .replace(/\$B\$\d+:\$F\$\d+/g,'TABLA').replace(/\$A\$\d+:\$A\$\d+/g,'NOMBRES')
   .replace(/\$?[A-O]\$?\d+/g,r=>JSON.stringify(valores[r]));
  resultados.push(Function('TABLA','NOMBRES','INDEX','MATCH','return '+f)(plazos.map(r=>r.slice(1)),plazos.map(r=>r[0]),(t,r,c)=>t[r-1][c-1],(v,a)=>a.indexOf(v)+1));
 }
 return {resultados,tn1,tn2,tnR};
}
assert.deepEqual(pagos(300,100,0,'contado','contado','0/30/60/90').resultados.slice(0,5),[150e6,200e6,250e6,300e6,300e6]);
const repartido=pagos(50,100,80,'contado','30 días','90 días');assert.equal(repartido.tn1[0],50);assert.equal(repartido.tn2[0],0);assert.equal(repartido.tnR[0],0);
assert.equal(pagos(300,100,80,'contado','30 días','90 días').tnR[0],120);
for(let n=1;n<=5;n++){
 if([2,3,5].includes(n)){const r=row("Plazos de canchada")+8;range(r,1,1,6).setValues([[Array.from({length:n},(_,i)=>i*30).join("/"),...Array.from({length:5},(_,i)=>i<n?1/n:0)]]);}
 const plazo=n===1?'contado':Array.from({length:n},(_,i)=>i*30).join('/');
 pagos(300,0,0,'contado','contado',plazo).resultados.forEach((v,i)=>assert(Math.abs(v-300e6*Math.min(n,i+1)/n)<1e-6));
 cells.set(at(179,1),'Canchada: en cuántas partes se paga');cells.set(at(179,2),n);
 const foto=ctx._ccLeerEditable_(h);assert.equal(foto.sup.plazoResto,plazo);assert.equal(foto.sup.tramo1,0);
}
cells.delete(at(179,1));cells.delete(at(179,2));
const ctrl=formulas.get(at(row('Plazos de canchada')+1,7));assert(ctrl.includes('No suma 100 %'));
// En la planilla en español no puede haber decimales con punto ni "0,-" en una fórmula.
assert(!/\d\.\d/.test(ctrl) && !/0,-/.test(formulas.get(at(row('Falta canchada comprada para la mezcla (TN)'),2))));
const evaluarControl=suma=>Function('IF','ABS','SUM','ROUND','return '+ctrl.slice(1).replace(/A\d+/g,'"contado"').replace(/B\d+:F\d+/g,String(suma)).replace(/(?<![<>=!])=(?!=)/g,'==='))((c,a,b)=>c?a:b,Math.abs,x=>x,(x,d)=>Math.round(x*10**d)/10**d);
assert.equal(evaluarControl(.9),'No suma 100 %');assert.equal(evaluarControl(1),'OK');
for(let c=2;c<=15;c++)assert.equal(formula('Resultado de la operación acumulado (sin deuda)',c),'=SUM($B$'+row('Resultado de la operación (antes de la deuda)')+':'+String.fromCharCode(64+c)+row('Resultado de la operación (antes de la deuda)')+')');
console.log('Tramos: reparto, pagos, migración 1–5, control del 100 % y acumulado sin bancos OK');

// Rearmado real de una hoja anterior: agrega el plazo faltante y conserva todos los amarillos.
for(const n of [1,2,3,4,5]){
 const tabla=row('Plazos de canchada');cells.set(at(tabla,1),'tabla vieja sin conservar');
 cells.set(at(179,1),'Canchada: en cuántas partes se paga');cells.set(at(179,2),n);
 ctx.armarCompraCanchada();const plazo=n===1?'contado':Array.from({length:n},(_,i)=>i*30).join('/');
 assert.equal(cells.get(at(row(label('plazoResto')),2)),plazo);
 assert.equal(cells.get(at(row(label('tramo1')),2)),0);assert.equal(cells.get(at(row(label('tramo2')),2)),0);
 assert([...cells.values()].includes(plazo));
}
const sinBorrar=cells;cells.set(at(179,1),'Canchada: en cuántas partes se paga');cells.set(at(179,2),6);
assert.throws(()=>ctx.armarCompraCanchada(),/No se borró/);assert.equal(cells,sinBorrar);
cells.delete(at(179,1));cells.delete(at(179,2));
// Las reglas nuevas respetan también una planilla con separador español.
validaciones=[];ctx._separadorDeEstaPlanilla_=()=>';';ctx.armarCompraCanchada();
for(const [r,c,v]of validaciones)if(typeof v==='string')assert(!v.includes(','),v);
