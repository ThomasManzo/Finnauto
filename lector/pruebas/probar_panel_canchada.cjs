// Planilla de juguete: sin conexión ni datos del cliente.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
let mail='panel@ejemplo.invalid',rows=[],props={},writes=0,opens=0,locked=false,flush=0;
const h={getDataRange:()=>({getValues:()=>rows.map(r=>r.slice())}),getRange:(r,c,n,w)=>({setValues:values=>{assert(locked);writes++;values[0].forEach((v,i)=>rows[r-1][c-1+i]=v);}})};
const ctx=vm.createContext({Date,Session:{getActiveUser:()=>({getEmail:()=>mail})},Utilities:{formatDate:d=>d.toISOString().slice(0,10),parseDate:s=>new Date(s+'T03:00:00Z')},SpreadsheetApp:{openById:()=>{opens++;return {getSheetByName:()=>h};},flush:()=>{flush++;}},PropertiesService:{getScriptProperties:()=>({getProperty:k=>props[k]||null,setProperty:(k,v)=>{assert(locked);props[k]=v;}})},LockService:{getScriptLock:()=>({waitLock:()=>{assert(!locked);locked=true;},releaseLock:()=>{locked=false;}})}});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../../clientes/navar/herramientas/tablero_web.gs'),'utf8'),ctx);
ctx.PERMITIDOS=[mail];ctx.CANCHADA_PLANILLA_ID='planilla-de-juguete';
// Los textos salen de la definición original: si cambia, la prueba avisa.
const original=vm.createContext({});vm.runInContext(fs.readFileSync(path.join(__dirname,'../../clientes/navar/herramientas/crear_cash.gs'),'utf8'),original);
assert.equal(JSON.stringify(ctx.PANEL_CC_SUPUESTOS),JSON.stringify(original.CC_SUPUESTOS));
const vals={cobertura:4,lista:0,compras:'a mano',mezcla:.5,pagoEnvases:'contado',comision:5,estampillasBase:100,kilosBase:200,precio:1500,suba:.01,mesesSuba:2,dias:30,pCanch:1000,flete:10,partes:4,stock:0,secadero:1000000,inicio:new Date('2027-01-01T03:00:00Z')};
for(const k of ['estampillas','paquetes','pallets','stretch','termo']){vals[k+'1']=10;vals[k+'Medio']=6;}
rows=Array.from(ctx.PANEL_CC_SUPUESTOS,s=>[s[1],vals[s[0]],...Array(13).fill('')]);
rows.push(['Mes',...Array.from({length:14},(_,i)=>new Date(Date.UTC(2027,i,1,3)))],['TN vendidas',...Array(14).fill(20)],['TN compradas (a mano)',...Array(14).fill(30)],['Faltan cargar','ejemplo pendiente'],['TN compradas (lo que se usa)',...Array(14).fill(600)],['Saldo acumulado',...Array(14).fill(42)],['Qué no está: ejemplo de nota']);
const plain=x=>JSON.parse(JSON.stringify(x));
assert.equal(ctx.leerEscenarioCanchada().supuestos.inicio,'2027-01-01');assert.equal(ctx.leerEscenarioCanchada().meses[0],'2027-01-01');assert.equal(ctx.leerEscenarioCanchada().falta,'ejemplo pendiente');
assert.throws(()=>ctx.volverAlPlanOriginalCanchada(),/no hay un plan/);assert(!locked);
const before=plain(ctx._ccFoto_(h));rows.reverse();
const out=ctx.guardarEscenarioCanchada({supuestos:{pCanch:1200},tnVendidas:Array(14).fill(40)});
assert.equal(out.supuestos.pCanch,1200);assert.equal(out.filas['TN vendidas'][0],40);assert.equal(flush,1);assert.deepEqual(JSON.parse(props.canchada_plan_original),before);
for(const c of [{supuestos:{partes:0}},{supuestos:{partes:1.5}},{supuestos:{partes:7}},{supuestos:{mesesSuba:15}},{supuestos:{suba:.51}},{supuestos:{precio:NaN}},{supuestos:{precio:'1000'}},{tnCompradas:Array(14).fill(5001)},{tnCompradas:Array(14).fill(-1)},{tnVendidas:Array(13).fill(1)},{supuestos:{inicio:'2027-13-01'}},{supuestos:{otra:2}},{otro:1}]){
 const n=writes;assert.throws(()=>ctx.guardarEscenarioCanchada(c));assert.equal(writes,n);assert(!locked);
}
// Las claves nuevas se guardan por texto y vuelven también con el plan original.
const nuevos={cobertura:12,lista:8,compras:'automáticas',mezcla:1,pagoEnvases:'30 días',comision:0,estampillasBase:0,kilosBase:0};
for(const k of ['estampillas','paquetes','pallets','stretch','termo']){nuevos[k+'1']=20;nuevos[k+'Medio']=12;}
const guardado=ctx.guardarEscenarioCanchada({supuestos:nuevos,tnCompradas:Array(14).fill(45)});
assert.equal(guardado.filas['TN compradas (a mano)'][0],45);assert.equal(guardado.filas['TN compradas (lo que se usa)'][0],600);
for(const [k,v]of Object.entries(nuevos))assert.equal(guardado.supuestos[k],v);
for(const k of Object.keys(nuevos)){
 const invalidos=k==='compras'?['manual','automaticas',0,null]:k==='cobertura'?[0,13,1.5,'4',NaN]:k==='lista'?[-1,9,1.5,'0',Infinity]:k==='pagoEnvases'?['60 días',0,null]:k==='mezcla'?[-.1,1.01,'0.5',NaN,Infinity]:[-1,'2',NaN,Infinity,null];
 for(const v of invalidos){const n=writes;assert.throws(()=>ctx.guardarEscenarioCanchada({supuestos:{[k]:v}}));assert.equal(writes,n);}
}
ctx.volverAlPlanOriginalCanchada();assert.deepEqual(plain(ctx._ccFoto_(h)),before);
ctx.guardarEscenarioCanchada({supuestos:{precio:1700}});ctx.guardarPlanOriginalCanchada();ctx.guardarEscenarioCanchada({supuestos:{precio:1800}});assert.equal(ctx.volverAlPlanOriginalCanchada().supuestos.precio,1700);
// También se puede volver a un original que tenía celdas sin cargar.
rows.find(r=>r[0]==='TN vendidas')[1]='';rows.find(r=>r[0]===ctx.PANEL_CC_SUPUESTOS[0][1])[1]='';ctx.guardarPlanOriginalCanchada();ctx.guardarEscenarioCanchada({supuestos:{precio:1900},tnVendidas:Array(14).fill(50)});ctx.volverAlPlanOriginalCanchada();assert.equal(rows.find(r=>r[0]==='TN vendidas')[1],'');
// Un original nuevo también puede tener envases sin cargar: volver debe reponer esos vacíos.
for(const k of ['mezcla','pagoEnvases','paquetesMedio'])rows.find(r=>r[0]===ctx.PANEL_CC_SUPUESTOS.find(s=>s[0]===k)[1])[1]='';
ctx.guardarPlanOriginalCanchada();ctx.guardarEscenarioCanchada({supuestos:{mezcla:0,pagoEnvases:'contado',paquetesMedio:0}});
const vacios=ctx.volverAlPlanOriginalCanchada().supuestos;
for(const k of ['mezcla','pagoEnvases','paquetesMedio'])assert.equal(vacios[k],'');
mail='sin-acceso@ejemplo.invalid';const n=writes,o=opens;
for(const f of [()=>ctx.leerEscenarioCanchada(),()=>ctx.guardarEscenarioCanchada({supuestos:{precio:2}}),()=>ctx.guardarPlanOriginalCanchada(),()=>ctx.volverAlPlanOriginalCanchada()])assert.throws(f,/Sin acceso/);
assert.equal(writes,n);assert.equal(opens,o);assert(!locked);
console.log('Panel canchada: lectura, permisos, rangos, filas movidas y plan original OK');
