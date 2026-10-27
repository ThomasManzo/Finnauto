"""El apartado se habilita por perfil y funciona sin dependencias externas de JS."""
from dashboard.app import render
from dashboard.datos import opciones_tablero


def paquete(marca):
    return {"cliente": "Ejemplo", "fecha": "2027-01-01", "unidades": [], "datos": {},
            "tablero": {"escenario_canchada": marca}}


def test_panel_se_habilita_por_marca():
    html = render(paquete(True))
    assert 'data-capa="canchada"' in html
    assert "Compra de canchada" in html
    assert "function verCanchada()" in html
    assert "este apartado funciona desde el link del tablero" in html
    assert '<script src=' not in html
    assert html.index('data-capa="hallazgos"') < html.index('data-capa="canchada"')


def test_sin_marca_no_hay_apartado():
    html = render(paquete(False))
    assert 'data-capa="canchada"' not in html
    assert 'function verCanchada()' not in html
    assert '<script src=' not in html


def test_la_marca_se_lee_del_perfil(monkeypatch):
    from nucleo import config
    monkeypatch.setattr(config, "cargar_perfil", lambda *args: {"tablero": {"escenario_canchada": True}})
    assert opciones_tablero("ejemplo")["escenario_canchada"] is True
    monkeypatch.setattr(config, "cargar_perfil", lambda *args: {})
    assert opciones_tablero("otro") == {}


def test_entrada_numerica_y_leyenda():
    html = render(paquete(True))
    assert "numero.onblur=confirmar" in html
    assert "ccCambio(k,tn?Array(14).fill(n):n)" in html
    assert "fuera de la escala" in html
    assert "Number.isInteger(n)" in html
    assert "!/^nada/i.test" in html
    assert "cc-leyenda" in html
    assert "por debajo falta plata" in html


def test_envases_comisiones_y_base_en_el_panel():
    html = render(paquete(True))
    assert 'Gastos de envase' in html
    assert 'Comisión de los vendedores ($/kg)' in html
    assert "['termo','Termocontraíble']" in html
    assert "ccCampo('mezcla','Mezcla: % de kilos en paquetes de 1 kg',100,100)" in html
    assert "['contado','30 días']" in html
    assert "ccCambio('pagoEnvases',p)" in html
    assert 'ver cómo se arma la base' in html
    assert "ccCampo('estampillasBase'" in html
    assert "ccCampo('kilosBase'" in html
    assert "fila('Gastos operativos sin secadero')" in html
    assert "fila('Gastos de envase')" in html
    assert "fila('Comisiones')" in html
    assert "fila('Total bancos y deuda')" in html
    assert "fila('Total deuda del mes')" not in html
    assert '<script src=' not in html



def test_stock_cobertura_y_compras_en_panel():
    html = render(paquete(True))
    assert "['stock','Stock hoy (TN)',0,3000" in html
    assert "['cobertura','Meses de cobertura',1,12" in html
    assert "['lista','Meses hasta estar lista',0,8" in html
    assert "['automáticas','a mano']" in html
    assert "barra.disabled=numero.disabled=automatica" in html
    assert "x.disabled=automatica" in html
    assert "TN compradas (lo que se usa)" in html
    assert "TN compradas (a mano)" in html
    assert 'Compra del primer mes' in html
    assert 'Cobertura mínima:' in html
    assert 'Canchada (TN)' in html
    assert 'Llegan listas para moler (TN)' in html
    assert 'Sin ventas previstas para medir cobertura' in html
    assert '<script src=' not in html


def test_equilibrio_render_y_puente_simulado(tmp_path):
    """DOM chico y puente falso: se ejecuta el JS real sin Google ni navegador."""
    import os
    import shutil
    import subprocess
    from dashboard.app import JS_CANCHADA

    html = render(paquete(True))
    assert 'Equilibrio (por kg)' in html
    assert 'Precio de equilibrio' in html
    assert 'TN de equilibrio' in html
    prueba = tmp_path / 'panel.cjs'
    codigo = tmp_path / 'panel.js'
    codigo.write_text(JS_CANCHADA)
    prueba.write_text(r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Elemento {
 querySelectorAll(s){let out=[];for(const x of this.children){if(x.className&&x.className.split(' ').includes(s.slice(1)))out.push(x);if(x.querySelectorAll)out.push(...x.querySelectorAll(s));}return out;}
 constructor(tag,cls=''){this.tag=tag;this.className=cls;this.children=[];this.style={};this.textContent='';}
 append(...xs){this.children.push(...xs);} prepend(...xs){this.children.unshift(...xs);}
 replaceChildren(...xs){this.children=xs;} setAttribute(k,v){this[k]=v;}
 querySelector(s){return this.querySelectorAll(s)[0];}
 cloneNode(){return this;} get texto(){return this.textContent+this.children.map(x=>x.texto||'').join(' ');}
}
const fixture={supuestos:{precio:1800,plazoResto:'0/30/60/90',cobertura:4},plazos:[['0/30/60/90',.25,.25,.25,.25,0]],filas:{},meses:Array.from({length:14},(_,i)=>new Date(Date.UTC(2027,i,1)).toISOString().slice(0,10)),hora:new Date().toISOString(),falta:'nada',notas:[]};
for(const t of ['Saldo acumulado','Saldo del mes pagando la deuda que vence','Saldo disponible (acumulado + descubierto): si da negativo, eso es lo que falta financiar','Descubierto acordado con los bancos','TN compradas (lo que se usa)','Compra de canchada del mes (valor sin flete)','Meses que cubre','Gastos operativos sin secadero','Compra de canchada (lo que se paga en el mes)','Flete de la canchada','Cobranza de las ventas (según los días de cobro)','Gastos de envase','Comisiones','Total bancos y deuda','Llegan listas para moler (TN)','TN del tramo 1','TN del tramo 2','TN del resto','Stock total a fin de mes (TN)','Stock propio a fin de mes (TN)','Stock comprado a fin de mes (TN)','Canchada propia usada (TN)','Canchada comprada usada (TN)','Falta canchada comprada para la mezcla (TN)','Resultado de la operación (antes de la deuda)','Resultado de la operación acumulado (sin deuda)'])fixture.filas[t]=Array(14).fill(100);
let lecturas=0,escenarios=[],confirmaciones=[],respuestaConfirmacion=true,nombrePedido='Ensayo',memoria={};
const ctx=vm.createContext({console,Date,setInterval(){},setTimeout,clearTimeout,
 prompt:()=>nombrePedido,confirm:txt=>{confirmaciones.push(txt);return respuestaConfirmacion;},localStorage:{getItem:k=>memoria[k],setItem:(k,v)=>memoria[k]=v},
 el:(t,c)=>new Elemento(t,c),pesos:v=>'$'+v,
 document:{createElementNS:(ns,t)=>new Elemento(t),createTextNode:t=>({texto:t})},
 google:{script:{get run(){let ok,mal;return {withSuccessHandler(f){ok=f;return this;},withFailureHandler(f){mal=f;return this;},listarEscenariosCanchada(){ok(structuredClone(escenarios));},
 guardarEscenarioConNombreCanchada(p){let i=escenarios.findIndex(e=>e.nombre===p.nombre);if(i>=0&&!p.reemplazar){ok({confirmar:true,nombre:p.nombre});return;}if(i<0&&escenarios.length>=20){mal(new Error('Ya hay 20 escenarios'));return;}
 const e={nombre:p.nombre,fecha:new Date().toISOString(),entrada:{supuestos:structuredClone(fixture.supuestos),plazos:fixture.plazos},resultados:structuredClone(fixture)};if(i<0)escenarios.push(e);else escenarios[i]=e;ok(structuredClone(escenarios));},
 abrirEscenarioCanchada(nombre){fixture.supuestos=structuredClone(escenarios.find(e=>e.nombre===nombre).entrada.supuestos);ok(structuredClone(fixture));},
 borrarEscenarioCanchada(nombre){escenarios=escenarios.filter(e=>e.nombre!==nombre);ok(structuredClone(escenarios));},leerEscenarioCanchada(){lecturas++;ok(structuredClone(fixture));}};}}}
});
vm.runInContext(fs.readFileSync(process.argv[2],'utf8'),ctx);
// Estos controles no forman parte del cambio; se ejercita completa la pintura de resultados.
ctx.ccControles=()=>{};ctx.ccEstado=()=>{};ctx.ccBaseControles=()=>{};
function pintar(precio,tn,eq,vol,margin=520){
 fixture.supuestos.precio=precio;fixture.filas['TN vendidas']=Array(14).fill(tn);
 fixture.filas['Costo variable por kg (canchada + flete + envase + comisión)']=Array(14).fill(1480);
 fixture.filas['Margen por kg']=Array(14).fill(margin);
 fixture.filas['Precio de equilibrio de la operación ($/kg)']=[99999,99999,99999,...Array(11).fill(eq)];
 fixture.filas['TN de equilibrio por mes']=[99999,99999,99999,...Array(11).fill(vol)];
 ctx.CC.bueno=null;const root=ctx.verCanchada()[0],area=root.querySelector('.cc-resultados');
 assert(!area.children.some(e=>e.className==='cc-aviso'),area.texto);
 const cards=area.querySelector('.kpis');assert.equal(cards.children.length,7);
 return {area,card:t=>cards.children.find(e=>e.children[0].textContent===t)};
}
let p=pintar(1800,150,1980,192.3);
assert.match(p.card('Precio de equilibrio').texto,/1.980.*\/kg/s);
assert.match(p.card('Precio de equilibrio').texto,/falta \+10 %/);
assert.match(p.card('TN de equilibrio').texto,/faltan 42,3 TN/);
for(const t of ['Precio de equilibrio','TN de equilibrio'])assert.match(p.card(t).className,/malo/);
p=pintar(2000,200,1980,192.3);
for(const t of ['Precio de equilibrio','TN de equilibrio']){assert.match(p.card(t).texto,/ya alcanza/);assert(!/malo/.test(p.card(t).className));}
p=pintar(1980,192.3,1980,192.3);assert.match(p.card('Precio de equilibrio').texto,/ya alcanza/);
// Como el servidor real: texto convertido a null, recuperado por el margen calculado.
for(const margen of [0,-20]){p=pintar(1480,200,1980,null,margen);assert.match(p.card('TN de equilibrio').texto,/no hay volumen que alcance/);assert.match(p.card('TN de equilibrio').className,/malo/);}
p=pintar(1480,200,1980,'no hay volumen que alcance',0);assert.match(p.card('TN de equilibrio').texto,/no hay volumen que alcance/);
p=pintar(0,0,null,null,-1480);assert.match(p.card('Precio de equilibrio').texto,/sin ventas/);assert(!/NaN|Infinity/.test(p.area.texto));
p=pintar(0,200,1980,192.3);assert.match(p.card('Precio de equilibrio').texto,/hoy es cero/);
assert.match(p.area.texto,/Equilibrio \(por kg\)/);assert.equal(lecturas,8);
// El panel completo: acciones por sus botones, confirmaciones, comparación y cambio de vista.
const box=ctx.CC.raiz.querySelector('.cc-cab').querySelector('.cc-escenarios');
function boton(texto){return box.children.find(e=>e.tag==='button'&&e.textContent===texto);}
function selector(texto){return box.children.find(e=>e.tag==='label'&&e.textContent===texto).children[0];}
boton('Guardar como…').onclick();assert.equal(escenarios.length,1);assert.equal(ctx.CC.abierto,'Ensayo');
respuestaConfirmacion=false;boton('Guardar como…').onclick();assert.equal(confirmaciones.length,1);assert.equal(escenarios.length,1);
respuestaConfirmacion=true;boton('Guardar como…').onclick();assert.equal(confirmaciones.length,2);
fixture.supuestos.precio=2345;ctx.CC.bueno=structuredClone(fixture);
let sel=selector('Escenario');sel.value='Ensayo';sel.onchange();assert.equal(ctx.CC.bueno.supuestos.precio,0);
sel=selector('Comparar con…');sel.value='Ensayo';sel.onchange();
let area=ctx.CC.raiz.querySelector('.cc-resultados');assert.match(area.texto,/Diferencia contra «Ensayo»/);assert.match(area.texto,/vs «Ensayo»/);
function recorrer(n){return [n,...(n.children||[]).flatMap(recorrer)];}
assert(recorrer(area).some(e=>e['stroke-dasharray']==='6 4'));
assert(!recorrer(area).some(e=>e['stroke-dasharray']==='5 4'));
assert(!area.texto.includes('Límite del descubierto acordado'));
let vista=recorrer(area).find(e=>e['aria-label']==='Vista del gráfico');vista.value='deuda';vista.onchange();
assert.equal(memoria['cc-vista'],'deuda');assert(recorrer(area).some(e=>e['stroke-dasharray']==='5 4'));assert.match(area.texto,/Bancos y deuda/);
vista=recorrer(area).find(e=>e['aria-label']==='Vista del gráfico');vista.value='operacion';vista.onchange();assert.equal(memoria['cc-vista'],'operacion');
respuestaConfirmacion=false;boton('Borrar').onclick();assert.equal(escenarios.length,1);
respuestaConfirmacion=true;boton('Borrar').onclick();assert.equal(escenarios.length,0);assert.equal(ctx.CC.comparar,'');
for(let i=0;i<20;i++){nombrePedido='Prueba '+i;boton('Guardar como…').onclick();}assert.equal(escenarios.length,20);
nombrePedido='Excede';boton('Guardar como…').onclick();assert.match(ctx.CC.mensaje,/20 escenarios/);

""")
    node = os.environ.get('NODE') or shutil.which('node') or '/Applications/ChatGPT.app/Contents/Resources/cua_node/bin/node'
    resultado = subprocess.run([node, str(prueba), str(codigo)], capture_output=True, text=True)
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
