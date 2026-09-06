# -*- coding: utf-8 -*-
"""
dashboard.app — la aplicación: un HTML con capas, empresa por empresa.

QUÉ CAMBIÓ RESPECTO DEL INFORME
-------------------------------
Antes esto era un documento de una sola página. Thomas (06/09/2026):

    "No tiene sentido armar ese informe si la idea es presentar un HTML o
     aplicación con varias capas: 1) el dash con información, cuentas a pagar,
     a cobrar; el otro una calculadora de retiro. Como este dash que tiene un
     botón para cada empresa."

Tiene razón, y no es una diferencia de forma. Un documento se lee de arriba a
abajo y se termina; una aplicación se **usa**: se elige la empresa, se cambia la
ventana, se prueba un monto. La asesoría se entrega con lo segundo.

LAS CUATRO CAPAS
----------------
    Posición      dónde estás parado: caja, deuda, escenarios, en qué se te va
    A quién pagar el reparto de la semana, ordenado por quién puede cortarte
    Retiro        la calculadora: cuánto podés sacar, y qué pasa si sacás X
    Hallazgos     lo que encontramos mirando, y lo que este tablero NO sabe

DOS DECISIONES QUE VALE LA PENA NO PERDER
-----------------------------------------
1. **Todo se calcula en Python** (`dashboard/datos.py`) y viaja como JSON
   adentro del archivo. El JavaScript cambia de solapa y formatea: no hace una
   sola cuenta de plata. Si la regla del retiro viviera acá, habría dos motores
   —uno con tests y otro sin— y se despegarían sin que nadie se entere.

2. **Un solo archivo, sin red.** Se abre con doble click en una reunión, sin
   servidor y sin internet, y se manda por mail. Cualquier dependencia externa
   es una forma de que falle justo cuando importa.

Uso:
    python dashboard/app.py --contrato datos/CONTRATO_maga_2026-09-05.json
"""

import io
import os
import sys
import json
import argparse

BASE_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)

from dashboard import datos as DATOS


CSS = """
:root{
  --fondo:#0B0C0E; --panel:#141619; --panel2:#1B1E22; --linea:#25292E;
  --tinta:#EDF1F4; --suave:#9AA5B1; --tenue:#6B7681;
  --azul:#4C82F7; --verde:#31C48D; --rojo:#F26B6B; --naranja:#F79552;
  --violeta:#9B7DF7; --amarillo:#E8C14A;
  --verde-piso:rgba(49,196,141,.12); --rojo-piso:rgba(242,107,107,.12);
  --ambar-piso:rgba(232,193,74,.12);
}
*{box-sizing:border-box}
html,body{margin:0;background:var(--fondo);color:var(--tinta)}
body{font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  -webkit-font-smoothing:antialiased}
.wrap{max-width:1120px;margin:0 auto;padding:26px 20px 90px}
.cab{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap}
h1{font-size:24px;margin:0;letter-spacing:-.02em}
.cab .meta{font-size:12.5px;color:var(--tenue);text-align:right;line-height:1.7}
.sub{color:var(--suave);font-size:13.5px;margin:4px 0 0}
.pills{display:flex;gap:8px;flex-wrap:wrap;margin:20px 0 4px}
.pill{background:var(--panel);border:1px solid var(--linea);color:var(--suave);
  padding:8px 16px;border-radius:9px;cursor:pointer;font-size:14px;font-weight:600;
  font-family:inherit}
.pill:hover{color:var(--tinta);border-color:#333a42}
.pill[aria-pressed="true"]{background:var(--azul);border-color:var(--azul);color:#fff}
.tabs{display:flex;gap:2px;margin:22px 0 18px;border-bottom:1px solid var(--linea);
  overflow-x:auto}
.tab{background:none;border:0;border-bottom:2px solid transparent;color:var(--tenue);
  padding:11px 16px;cursor:pointer;font-size:14px;font-weight:600;white-space:nowrap;
  font-family:inherit}
.tab:hover{color:var(--tinta)}
.tab[aria-selected="true"]{color:var(--tinta);border-bottom-color:var(--azul)}
h2{font-size:12px;text-transform:uppercase;letter-spacing:.1em;color:var(--tenue);
  margin:30px 0 12px;font-weight:700}
h2:first-child{margin-top:6px}
.card{background:var(--panel);border:1px solid var(--linea);border-radius:14px;padding:20px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}
.kpi .et{font-size:12.5px;color:var(--suave)}
.kpi .n{font-size:27px;font-weight:750;letter-spacing:-.02em;margin:7px 0 3px;
  font-variant-numeric:tabular-nums}
.kpi .pie{font-size:11.5px;color:var(--tenue)}
.kpi.malo{background:var(--rojo-piso);border-color:rgba(242,107,107,.3)}
.kpi.malo .n{color:var(--rojo)}
.kpi.bien .n{color:var(--verde)}
table{width:100%;border-collapse:collapse;font-size:14px}
th{text-align:right;font-size:11px;text-transform:uppercase;letter-spacing:.06em;
  color:var(--tenue);font-weight:700;padding:0 0 10px}
th:first-child,td:first-child{text-align:left}
td{text-align:right;padding:10px 0;border-top:1px solid var(--linea);
  font-variant-numeric:tabular-nums}
tr.tot td{font-weight:700;border-top:2px solid #39414a}
.pos{color:var(--verde)} .neg{color:var(--rojo)}
.chip{display:inline-block;font-size:11px;font-weight:700;padding:3px 9px;border-radius:99px}
.chip.ok{background:var(--verde-piso);color:var(--verde)}
.chip.mal{background:var(--rojo-piso);color:var(--rojo)}
.chip.medio{background:var(--ambar-piso);color:var(--amarillo)}
.barra{height:9px;border-radius:99px;background:var(--azul);min-width:3px}
.nota{font-size:12.5px;color:var(--tenue);margin:12px 0 0}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.veredicto{border-radius:14px;padding:24px;border:1px solid;margin-bottom:14px}
.veredicto.si{background:var(--verde-piso);border-color:rgba(49,196,141,.35)}
.veredicto.no{background:var(--rojo-piso);border-color:rgba(242,107,107,.35)}
.veredicto .n{font-size:38px;font-weight:780;letter-spacing:-.03em;margin:6px 0}
.veredicto.si .n{color:var(--verde)} .veredicto.no .n{color:var(--rojo)}
.campo{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:14px 0 0}
input[type=text]{background:var(--panel2);border:1px solid var(--linea);color:var(--tinta);
  padding:11px 14px;border-radius:9px;font-size:17px;width:240px;font-family:inherit;
  font-variant-numeric:tabular-nums}
input[type=text]:focus{outline:none;border-color:var(--azul)}
input[type=range]{width:100%;accent-color:var(--azul);margin-top:14px}
.hall{border-left:3px solid var(--amarillo)}
.hall .t{font-weight:700;font-size:16px;margin-bottom:6px}
.hall .m{font-size:22px;font-weight:750;color:var(--amarillo);margin-top:10px;
  font-variant-numeric:tabular-nums}
.hall + .hall{margin-top:12px}
ul.limpia{margin:0;padding-left:19px;color:var(--suave);font-size:14px}
ul.limpia li{margin-bottom:8px}
.envuelve{overflow-x:auto}
svg{display:block;width:100%;height:auto;overflow:visible}
.leyenda{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:var(--suave);margin-bottom:14px}
.leyenda i{width:10px;height:10px;border-radius:3px;display:inline-block;margin-right:6px;
  vertical-align:-1px}
.ejeY{fill:var(--tenue);font-size:10px}
.ejeX{fill:var(--tenue);font-size:9.5px}
.rejilla{stroke:var(--linea);stroke-width:1}
.critico{fill:var(--rojo-piso);stroke:var(--rojo);stroke-dasharray:3 3}
[hidden]{display:none!important}
@media (max-width:760px){.grid2{grid-template-columns:1fr}.veredicto .n{font-size:30px}}
"""

JS = r"""
// ---------------------------------------------------------------- formato
// Acá NO se calcula plata. Todo viene resuelto de Python (dashboard/datos.py):
// esto solo elige qué mostrar y cómo escribirlo. Ver el docstring de app.py.
function pesos(v, corto){
  var s = v < 0 ? '-' : '', n = Math.abs(v);
  if (corto && n >= 1e9) return s + '$' + (n/1e9).toFixed(2).replace('.', ',') + ' MM';
  if (corto && n >= 1e6) return s + '$' + (n/1e6).toFixed(0) + ' M';
  return s + '$' + Math.round(n).toLocaleString('es-AR');
}
function sem(v){
  if (v === null || v === undefined) return '—';
  return Math.abs(v - Math.round(v)) < 0.05
    ? Math.round(v) + ' sem'
    : v.toFixed(1).replace('.', ',') + ' sem';
}
function dia(iso){ var p = String(iso).split('-'); return p[2] + '/' + p[1]; }
function el(t, c, h){ var e = document.createElement(t);
  if (c) e.className = c; if (h !== undefined) e.innerHTML = h; return e; }
function signo(v){ return v >= 0 ? 'pos' : 'neg'; }


// ---------------------------------------------------------------- graficos
// SVG escrito a mano, sin ninguna libreria.
//
// No es purismo: el archivo tiene que abrirse en una reunion sin internet.
// Cualquier <script src> de un CDN es una forma de que el tablero aparezca
// vacio justo cuando importa. Un grafico de barras son cuatro rectangulos.
var PALETA = ['#4C82F7', '#31C48D', '#F79552', '#9B7DF7', '#E8C14A', '#F26B6B'];

function svgEl(t, attrs){
  var e = document.createElementNS('http://www.w3.org/2000/svg', t);
  for (var k in attrs) e.setAttribute(k, attrs[k]);
  return e;
}

function barrasApiladas(datos, alto){
  alto = alto || 210;
  var ancho = 900, izq = 62, abajo = 26, arriba = 8;
  var max = 0;
  datos.dias.forEach(function(d){ if (d.total > max) max = d.total; });
  if (!max) max = 1;
  var svg = svgEl('svg', {viewBox: '0 0 ' + ancho + ' ' + (alto + abajo),
                          preserveAspectRatio: 'none'});
  svg.style.height = (alto + abajo) + 'px';
  svg.removeAttribute('preserveAspectRatio');

  // rejilla y eje
  for (var i = 0; i <= 3; i++){
    var y = arriba + (alto - arriba) * i / 3;
    svg.appendChild(svgEl('line', {x1: izq, y1: y, x2: ancho, y2: y, class: 'rejilla'}));
    var t = svgEl('text', {x: izq - 8, y: y + 3, class: 'ejeY', 'text-anchor': 'end'});
    t.textContent = pesos(max * (3 - i) / 3, true);
    svg.appendChild(t);
  }
  var w = (ancho - izq) / Math.max(1, datos.dias.length);
  datos.dias.forEach(function(d, k){
    var x = izq + k * w, acum = 0;
    d.valores.forEach(function(v, j){
      if (!v) return;
      var h = (alto - arriba) * v / max;
      var y = alto - acum - h;
      svg.appendChild(svgEl('rect', {x: x + w * 0.15, y: y, width: w * 0.7, height: h,
        fill: PALETA[j % PALETA.length], rx: 1.5}));
      acum += h;
    });
    if (datos.dias.length <= 40 && k % 2 === 0){
      var tx = svgEl('text', {x: x + w / 2, y: alto + 15, class: 'ejeX', 'text-anchor': 'middle'});
      tx.textContent = d.fecha.slice(8);
      svg.appendChild(tx);
    }
  });
  return svg;
}

function curvaCaja(curva, critico){
  var ancho = 900, alto = 230, izq = 72, abajo = 26, arriba = 10;
  if (!curva.length) return el('p', 'nota', 'Sin datos para proyectar.');
  var vals = curva.map(function(p){ return p.caja; });
  var max = Math.max.apply(null, vals), min = Math.min.apply(null, vals, [0]);
  if (max === min) max = min + 1;
  var svg = svgEl('svg', {viewBox: '0 0 ' + ancho + ' ' + (alto + abajo)});
  svg.style.height = (alto + abajo) + 'px';
  function Y(v){ return arriba + (alto - arriba) * (max - v) / (max - min); }

  for (var i = 0; i <= 3; i++){
    var v = max - (max - min) * i / 3, y = Y(v);
    svg.appendChild(svgEl('line', {x1: izq, y1: y, x2: ancho, y2: y, class: 'rejilla'}));
    var t = svgEl('text', {x: izq - 8, y: y + 3, class: 'ejeY', 'text-anchor': 'end'});
    t.textContent = pesos(v, true);
    svg.appendChild(t);
  }
  // La linea del cero es la que importa: cruzarla es quedarse sin caja.
  if (min < 0){
    var y0 = Y(0);
    svg.appendChild(svgEl('line', {x1: izq, y1: y0, x2: ancho, y2: y0,
      stroke: 'var(--rojo)', 'stroke-width': 1, 'stroke-dasharray': '4 3'}));
  }
  var w = (ancho - izq) / Math.max(1, curva.length - 1);
  var d = '', da = '';
  curva.forEach(function(p, k){
    var x = izq + k * w, y = Y(p.caja);
    d += (k ? 'L' : 'M') + x.toFixed(1) + ' ' + y.toFixed(1) + ' ';
  });
  da = d + 'L' + (izq + (curva.length - 1) * w).toFixed(1) + ' ' + Y(Math.max(0, min)) +
       ' L' + izq + ' ' + Y(Math.max(0, min)) + ' Z';
  svg.appendChild(svgEl('path', {d: da, fill: 'rgba(76,130,247,.12)'}));
  svg.appendChild(svgEl('path', {d: d, fill: 'none', stroke: 'var(--azul)', 'stroke-width': 2}));

  if (critico){
    var k = curva.findIndex(function(p){ return p.fecha === critico.fecha; });
    if (k >= 0){
      var x = izq + k * w;
      svg.appendChild(svgEl('line', {x1: x, y1: arriba, x2: x, y2: alto,
        stroke: 'var(--rojo)', 'stroke-width': 1.5}));
      svg.appendChild(svgEl('circle', {cx: x, cy: Y(critico.caja), r: 4, fill: 'var(--rojo)'}));
    }
  }
  curva.forEach(function(p, k){
    if (k % Math.ceil(curva.length / 10) !== 0) return;
    var t = svgEl('text', {x: izq + k * w, y: alto + 16, class: 'ejeX', 'text-anchor': 'middle'});
    t.textContent = dia(p.fecha);
    svg.appendChild(t);
  });
  return svg;
}

function leyenda(nombres){
  var l = el('div', 'leyenda');
  nombres.forEach(function(n, i){
    l.appendChild(el('span', null, '<i style="background:' + PALETA[i % PALETA.length] +
      '"></i>' + n));
  });
  return l;
}

// ---------------------------------------------------------------- estado
var UNIDAD = D.unidades[0], SOLAPA = 'posicion', VENTANA = String(D.ventanas[0]);
function actual(){ return D.datos[UNIDAD]; }

// ---------------------------------------------------------------- capas
function verPosicion(){
  var d = actual(), k = d.kpis, out = [];
  var c = el('div', 'kpis');
  [['Caja de hoy', pesos(k.caja, true), k.efectivo_sin_asignar
      ? '+ ' + pesos(k.efectivo_sin_asignar, true) + ' de efectivo del grupo, sin asignar'
      : 'banco + efectivo', ''],
   ['Deuda ya vencida', pesos(k.vencido, true), 'es la que puede cortarte la compra',
      k.vencido > 0 ? 'malo' : ''],
   ['Vence en 7 días', pesos(k.por_vencer, true), 'todavía no aprieta', ''],
   ['Margen a 7 días', pesos(k.margen, true),
      k.se_puede ? 'después de cubrir lo vencido' : 'falta ' + pesos(k.falta, true),
      k.se_puede ? 'bien' : 'malo']
  ].forEach(function(x){
    var t = el('div', 'card kpi ' + x[3]);
    t.appendChild(el('div', 'et', x[0]));
    t.appendChild(el('div', 'n', x[1]));
    t.appendChild(el('div', 'pie', x[2]));
    c.appendChild(t);
  });
  out.push(c);

  out.push(el('h2', null, 'Cómo quedás a 45 días, según a quién le pagues'));
  var ce = el('div', 'card'), t = el('table'), tb = el('tbody');
  d.escenarios.forEach(function(e){
    var nom = e.nombre.replace('  <<', '').replace(/^\d+\.\s*/, '');
    var tr = el('tr');
    tr.appendChild(el('td', null, '<b>' + nom + '</b>' +
      (e.usa ? ' <span class="chip ok">lo que se hace</span>' : '')));
    tr.appendChild(el('td', signo(e.monto), pesos(e.monto)));
    tb.appendChild(tr);
  });
  t.appendChild(tb); ce.appendChild(el('div', 'envuelve')).appendChild(t);
  if (d.escenarios.length >= 2) {
    var dif = d.escenarios[0].monto - d.escenarios[d.escenarios.length-1].monto;
    ce.appendChild(el('p', 'nota', 'La distancia entre el primero y el último —<b>' +
      pesos(dif) + '</b>— es lo que te financian tus proveedores. Es tu línea de ' +
      'crédito real: las bancarias están agotadas.'));
  }
  out.push(ce);

  out.push(el('h2', null, 'En qué se te va la plata (45 días)'));
  var cg = el('div', 'card');
  var max = Math.max.apply(null, d.gastos.map(function(g){ return g.monto; })) || 1;
  d.gastos.forEach(function(g){
    var f = el('div');
    f.style.cssText = 'display:grid;grid-template-columns:190px 1fr 110px;gap:12px;align-items:center;margin-bottom:9px';
    f.appendChild(el('div', null, '<span style="color:var(--suave);font-size:13.5px">' +
      g.nombre + '</span>'));
    var b = el('div'), bb = el('div', 'barra');
    bb.style.width = Math.max(2, 100 * g.monto / max) + '%';
    b.appendChild(bb); f.appendChild(b);
    f.appendChild(el('div', null, '<span style="font-variant-numeric:tabular-nums">' +
      pesos(g.monto, true) + '</span>'));
    cg.appendChild(f);
  });
  out.push(cg);

  if (d.ingresos_dia && d.ingresos_dia.dias.length){
    out.push(el('h2', null, 'Lo que entra, dia por dia'));
    var ci = el('div', 'card');
    ci.appendChild(leyenda(d.ingresos_dia.fuentes));
    ci.appendChild(barrasApiladas(d.ingresos_dia));
    ci.appendChild(el('p', 'nota', 'El total del mes no dice nada: lo que importa es el ' +
      'RITMO. Un pico de PAMI y treinta dias de mostrador no es lo mismo que un ingreso ' +
      'parejo, aunque sumen igual.'));
    out.push(ci);
  }

  out.push(el('h2', null, 'Próximas salidas'));
  var cs = el('div', 'card'), ts = el('table');
  ts.innerHTML = '<tr><th>Fecha</th><th>Detalle</th><th>Importe</th></tr>';
  d.salidas.forEach(function(s){
    var tr = el('tr');
    tr.appendChild(el('td', null, '<b>' + dia(s.fecha) + '</b>'));
    tr.appendChild(el('td', null, '<span style="color:var(--suave)">' + s.detalle + '</span>'));
    tr.appendChild(el('td', null, pesos(s.monto, true)));
    ts.appendChild(tr);
  });
  var w = el('div', 'envuelve'); w.appendChild(ts); cs.appendChild(w);
  if (!d.salidas.length) cs.appendChild(el('p', 'nota', 'No hay salidas cargadas en la ventana.'));
  out.push(cs);
  return out;
}

function verPagar(){
  var d = actual(), out = [];
  var c = el('div', 'card'), t = el('table');
  t.innerHTML = '<tr><th>Proveedor</th><th>Ya vencido</th><th>Vence pronto</th>' +
                '<th>Atraso</th><th>Le queda</th></tr>';
  d.proveedores.forEach(function(p){
    var m = p.margen, cls = 'ok', txt = sem(m);
    if (m === null) { cls = 'medio'; txt = 'sin tolerancia definida'; }
    else if (m <= 0) { cls = 'mal'; txt = 'te puede cortar'; }
    else if (m <= 1) { cls = 'medio'; }
    var tr = el('tr');
    tr.appendChild(el('td', null, '<b>' + p.nombre + '</b>' +
      (p.vence_dia ? '<div style="font-size:11.5px;color:var(--tenue)">vence ' +
        p.vence_dia + '</div>' : '')));
    tr.appendChild(el('td', p.vencido ? 'neg' : '', pesos(p.vencido)));
    tr.appendChild(el('td', null, pesos(p.por_vencer)));
    tr.appendChild(el('td', null, sem(p.atraso)));
    tr.appendChild(el('td', null, '<span class="chip ' + cls + '">' + txt + '</span>'));
    t.appendChild(tr);
  });
  var w = el('div', 'envuelve'); w.appendChild(t); c.appendChild(w);
  c.appendChild(el('p', 'nota', 'Ordenado por <b>margen</b>, no por monto: primero ' +
    'el que está más cerca de cortarte la compra, aunque le debas menos. ' +
    '“Le queda” es la tolerancia de ese proveedor menos el atraso que ya tenés.'));
  if (!d.proveedores.length) c.appendChild(el('p', 'nota', 'No hay deuda con droguerías en esta empresa.'));
  out.push(c);

  out.push(el('h2', null, 'El puente a 45 días'));
  var cp = el('div', 'card'), tp = el('table');
  tp.innerHTML = '<tr><th>Concepto</th><th>Monto</th></tr>';
  var f0 = el('tr');
  f0.appendChild(el('td', null, 'Caja de hoy'));
  f0.appendChild(el('td', null, pesos(d.puente.caja)));
  tp.appendChild(f0);
  d.puente.entra.filter(function(x){ return x.seguro; }).forEach(function(x){
    var tr = el('tr');
    tr.appendChild(el('td', null, '<span style="color:var(--suave)">+ ' + x.nombre + '</span>'));
    tr.appendChild(el('td', 'pos', pesos(x.monto)));
    tp.appendChild(tr);
  });
  d.puente.sale.forEach(function(x){
    var tr = el('tr');
    tr.appendChild(el('td', null, '<span style="color:var(--suave)">' +
      (x.monto >= 0 ? '− ' : '+ ') + x.nombre + '</span>'));
    tr.appendChild(el('td', x.monto >= 0 ? 'neg' : 'pos', pesos(Math.abs(x.monto))));
    tp.appendChild(tr);
  });
  var ft = el('tr', 'tot');
  ft.appendChild(el('td', null, 'Queda'));
  ft.appendChild(el('td', signo(d.puente.queda), pesos(d.puente.queda)));
  tp.appendChild(ft);
  var w2 = el('div', 'envuelve'); w2.appendChild(tp); cp.appendChild(w2);
  if (d.puente.cheques) cp.appendChild(el('p', 'nota',
    'No están contados <b>' + pesos(d.puente.cheques) + '</b> de cheques en cartera: ' +
    'al llegar la fecha se decide entre depositarlos (entra plata) o endosarlos ' +
    '(baja deuda y no entra).'));
  out.push(cp);
  return out;
}

function verRetiro(){
  var d = actual(), r = d.retiro[VENTANA], out = [];

  var sel = el('div', 'pills');
  D.ventanas.forEach(function(v){
    var b = el('button', 'pill', v + ' días');
    b.setAttribute('aria-pressed', String(v) === VENTANA);
    b.onclick = function(){ VENTANA = String(v); pintar(); };
    sel.appendChild(b);
  });
  out.push(sel);

  var v = el('div', 'veredicto ' + (r.margen > 0 ? 'si' : 'no'));
  v.appendChild(el('div', null,
    '<span style="font-size:12.5px;text-transform:uppercase;letter-spacing:.09em;' +
    'font-weight:700;color:var(--suave)">¿Se puede retirar plata?</span>'));
  v.appendChild(el('div', 'n', r.margen > 0 ? 'Sí, hasta ' + pesos(r.margen, true) : 'No'));
  if (r.margen <= 0) v.appendChild(el('div', null,
    '<span style="font-size:16px;font-weight:600">Faltan ' + pesos(-r.margen) +
    ' para cubrir lo que ya venció</span>'));
  v.appendChild(el('p', 'nota',
    'La regla: primero se cubre la deuda con droguerías que <b>ya venció</b> ' +
    '—la que puede hacer que te corten la compra— y recién lo que sobra se saca.'));
  out.push(v);

  var c = el('div', 'card'), t = el('table');
  [['Caja de hoy', r.caja, ''],
   ['+ lo que entra seguro en ' + VENTANA + ' días', r.entra, 'pos'],
   ['− lo que sale en ' + VENTANA + ' días (incluye lo vencido)', -r.sale, 'neg']
  ].forEach(function(x){
    var tr = el('tr');
    tr.appendChild(el('td', null, '<span style="color:var(--suave)">' + x[0] + '</span>'));
    tr.appendChild(el('td', x[2], pesos(Math.abs(x[1]))));
    t.appendChild(tr);
  });
  var tt = el('tr', 'tot');
  tt.appendChild(el('td', null, 'Margen'));
  tt.appendChild(el('td', signo(r.margen), pesos(r.margen)));
  t.appendChild(tt);
  var w = el('div', 'envuelve'); w.appendChild(t); c.appendChild(w);
  out.push(c);

  if (r.tapa_una_pared) {
    var p = el('div', 'card');
    p.style.borderLeft = '3px solid var(--amarillo)';
    p.innerHTML = '<b>Ojo con lo que viene detrás.</b> En estos mismos ' + VENTANA +
      ' días vencen <b>' + pesos(r.por_vencer) + '</b> más. Pagando todo en fecha ' +
      'el margen sería ' + pesos(r.margen_pagando_todo) + '. El retiro entra hoy, ' +
      'pero se paga con atraso después. Puede estar bien: que sea a sabiendas.';
    out.push(p);
  }

  out.push(el('h2', null, 'Probá un monto'));
  var cc = el('div', 'card');
  var campo = el('div', 'campo');
  var inp = el('input'); inp.type = 'text'; inp.placeholder = '150.000.000';
  inp.setAttribute('inputmode', 'numeric');
  var res = el('div'); res.style.cssText = 'font-size:15px;font-weight:600';
  var rango = el('input'); rango.type = 'range'; rango.min = 0;
  rango.max = Math.max(1, Math.round(Math.abs(r.margen) * 2)); rango.value = 0;

  function evaluar(monto){
    if (!monto) { res.innerHTML = ''; return; }
    var queda = r.margen - monto;
    res.innerHTML = queda >= 0
      ? '<span class="pos">Entran.</span> Quedarían ' + pesos(queda) + ' de margen.'
      : '<span class="neg">No entran.</span> Faltan ' + pesos(-queda) + '.';
  }
  function deTexto(){
    var n = Number(String(inp.value).replace(/[^\d]/g, '')) || 0;
    rango.value = Math.min(n, rango.max);
    inp.value = n ? n.toLocaleString('es-AR') : '';
    evaluar(n);
  }
  inp.addEventListener('input', deTexto);
  rango.addEventListener('input', function(){
    var n = Number(rango.value);
    inp.value = n ? n.toLocaleString('es-AR') : '';
    evaluar(n);
  });
  campo.appendChild(inp); campo.appendChild(res);
  cc.appendChild(campo); cc.appendChild(rango);
  cc.appendChild(el('p', 'nota', 'Se compara contra el margen de la ventana elegida. ' +
    'No cambia nada en ninguna planilla: es una prueba.'));
  out.push(cc);
  return out;
}


function verCobrar(){
  var d = actual(), c = d.a_cobrar, out = [];
  var k = el('div', 'kpis');
  [['Nos deben, ya vencido', pesos(c.vencido, true),
    'con fecha pasada y sin entrar', c.vencido ? 'malo' : ''],
   ['Nos deben, por vencer', pesos(c.por_vencer, true), 'en los proximos 45 dias', ''],
   ['Cheques en cartera', pesos(c.cheques_total, true),
    'no son caja hasta que se decide', '']
  ].forEach(function(x){
    var t = el('div', 'card kpi ' + x[3]);
    t.appendChild(el('div', 'et', x[0]));
    t.appendChild(el('div', 'n', x[1]));
    t.appendChild(el('div', 'pie', x[2]));
    k.appendChild(t);
  });
  out.push(k);

  if (c.filas.length){
    out.push(el('h2', null, 'Quien nos debe'));
    var cc = el('div', 'card'), t = el('table');
    t.innerHTML = '<tr><th>Contraparte</th><th>Vencido</th><th>Por vencer</th><th>Total</th></tr>';
    c.filas.forEach(function(f){
      var tr = el('tr');
      tr.appendChild(el('td', null, '<b>' + f.nombre + '</b>'));
      tr.appendChild(el('td', f.vencido ? 'neg' : '', pesos(f.vencido)));
      tr.appendChild(el('td', null, pesos(f.por_vencer)));
      tr.appendChild(el('td', null, '<b>' + pesos(f.total) + '</b>'));
      t.appendChild(tr);
    });
    var w = el('div', 'envuelve'); w.appendChild(t); cc.appendChild(w);
    cc.appendChild(el('p', 'nota', 'OJO con el sentido: aca se ve lo que <b>nos deben</b>. ' +
      'MAGA le COMPRA a las droguerias; esta vista es de Speedmed, que les compra y les vende.'));
    out.push(cc);
  } else {
    out.push(el('div', 'card', 'Esta empresa no tiene cuentas a cobrar a droguerias. ' +
      'Es lo esperable en una farmacia: le compra a la drogueria, no le vende.'));
  }

  if (c.cheques.length){
    out.push(el('h2', null, 'Cheques que vencen: cada uno es una decision'));
    var ch = el('div', 'card'), tc = el('table');
    tc.innerHTML = '<tr><th>Fecha</th><th>Librador</th><th>Estado</th><th>Importe</th></tr>';
    c.cheques.forEach(function(x){
      var tr = el('tr');
      tr.appendChild(el('td', null, '<b>' + dia(x.fecha) + '</b>'));
      tr.appendChild(el('td', null, '<span style="color:var(--suave)">' +
        (x.librador || '-') + '</span>'));
      tr.appendChild(el('td', null, '<span class="chip ' +
        (x.estado.indexOf('ENDOS') >= 0 ? 'medio' : 'ok') + '">' + x.estado + '</span>'));
      tr.appendChild(el('td', null, pesos(x.importe)));
      tc.appendChild(tr);
    });
    var w2 = el('div', 'envuelve'); w2.appendChild(tc); ch.appendChild(w2);
    ch.appendChild(el('p', 'nota', 'Al llegar la fecha se elige: <b>depositar</b> (entra plata) ' +
      'o <b>endosar</b> (no entra un peso, baja deuda con una drogueria). El estado que ' +
      'trae la planilla es lo esperado, no lo decidido.'));
    out.push(ch);
  }
  return out;
}

function verProyeccion(){
  var d = actual(), p = d.proyeccion, out = [];
  if (p.error || !p.curva.length){
    out.push(el('div', 'card', 'No se pudo proyectar: ' + (p.error || 'faltan datos.')));
    return out;
  }
  var k = el('div', 'kpis');
  [['Caja al arrancar', pesos(p.caja_inicial, true), p.desde, ''],
   ['El dia mas bajo', pesos(p.minimo, true),
     p.minimo < 0 ? 'la caja se da vuelta' : 'nunca toca cero', p.minimo < 0 ? 'malo' : 'bien'],
   ['Caja al cierre', pesos(p.final, true), p.hasta, p.final >= 0 ? 'bien' : 'malo']
  ].forEach(function(x){
    var t = el('div', 'card kpi ' + x[3]);
    t.appendChild(el('div', 'et', x[0]));
    t.appendChild(el('div', 'n', x[1]));
    t.appendChild(el('div', 'pie', x[2]));
    k.appendChild(t);
  });
  out.push(k);

  if (p.critico){
    var av = el('div', 'card');
    av.style.borderLeft = '3px solid var(--rojo)';
    av.innerHTML = '<b style="font-size:16px">El dia critico es el ' + dia(p.critico.fecha) +
      '.</b><br><span style="color:var(--suave)">Ahi la caja proyectada queda en ' +
      pesos(p.critico.caja) + '. Un dueno no mira el final del periodo: mira el dia que ' +
      'se queda corto, y ese dia tiene fecha.</span>';
    out.push(av);
  }

  out.push(el('h2', null, 'La caja, dia por dia'));
  var cg = el('div', 'card');
  cg.appendChild(curvaCaja(p.curva, p.critico));
  cg.appendChild(el('p', 'nota', 'Proyectado a partir del comportamiento de los ultimos ' +
    'meses, no de una formula: cada tipo de movimiento se repite con su propio ritmo. ' +
    'Lo que entra: ' + pesos(p.total_ingresos, true) + ' - lo que sale: ' +
    pesos(p.total_egresos, true) + '.'));
  out.push(cg);
  return out;
}

function verHallazgos(){
  var out = [];
  if (!D.hallazgos.length) {
    out.push(el('div', 'card', 'No se encontró nada raro en los datos de este export.'));
  }
  D.hallazgos.forEach(function(h){
    var c = el('div', 'card hall');
    c.appendChild(el('div', 't', h.titulo));
    c.appendChild(el('div', null, '<span style="color:var(--suave);font-size:14px">' +
      h.cuerpo + '</span>'));
    if (h.monto) c.appendChild(el('div', 'm', pesos(h.monto)));
    out.push(c);
  });

  out.push(el('h2', null, 'Lo que este tablero NO sabe'));
  var d = actual(), c = el('div', 'card'), u = el('ul', 'limpia');
  u.appendChild(el('li', null, '<b>Cuándo paga PAMI.</b> Se esperan dos pagos por ' +
    'mes, a mitad y a fin, pero las fechas se corren. Es el ingreso grande e ' +
    'impredecible del negocio.'));
  if (d.puente.cobranza_vencida) u.appendChild(el('li', null,
    '<b>Si entra la cobranza que ya venció</b> (' + pesos(d.puente.cobranza_vencida) +
    '). No está contada en ningún número de acá.'));
  if (d.puente.cheques) u.appendChild(el('li', null,
    '<b>Qué se hace con los cheques en cartera</b> (' + pesos(d.puente.cheques) +
    '): se decide uno por uno al llegar la fecha.'));
  u.appendChild(el('li', null, '<b>Cuánto le debe MAGA a Speedmed.</b> No está ' +
    'cargado en la planilla de MAGA, así que el escenario “Speed como proveedor ' +
    'rígido” no se puede calcular.'));
  c.appendChild(u); out.push(c);

  // LA MEMORIA: que se prometio antes y si se cumplio.
  // Es el activo de una asesoria recurrente. Sin esto cada visita arranca de
  // cero, y el motor es una promesa que nunca mostro un acierto.
  out.push(el('h2', null, 'La memoria: que proyectamos antes'));
  var cm = el('div', 'card');
  if (!D.memoria || !D.memoria.snapshots.length){
    cm.innerHTML = 'Todavia no hay ninguna proyeccion guardada para comparar.';
  } else {
    var tm = el('table');
    tm.innerHTML = '<tr><th>Corte</th><th>Proyecta hasta</th><th>Movimientos</th>' +
                   '<th>Conciliada</th></tr>';
    D.memoria.snapshots.forEach(function(s){
      var tr = el('tr');
      tr.appendChild(el('td', null, '<b>' + s.corte + '</b>' +
        (s.etiqueta ? '<div style="font-size:11.5px;color:var(--tenue)">' + s.etiqueta +
         '</div>' : '')));
      tr.appendChild(el('td', null, s.hasta));
      tr.appendChild(el('td', null, String(s.movimientos)));
      tr.appendChild(el('td', null, '<span class="chip medio">falta el dato real</span>'));
      tm.appendChild(tr);
    });
    var wm = el('div', 'envuelve'); wm.appendChild(tm); cm.appendChild(wm);
    cm.appendChild(el('p', 'nota', 'Para conciliar una proyeccion hace falta el cash del ' +
      'periodo que proyecta. Mientras no se concilie, el motor es una promesa: ' +
      '<b>lo que se vende es "te lo dije y paso", no "el motor calcula bien".</b>'));
  }
  out.push(cm);
  return out;
}

// ---------------------------------------------------------------- pintar
var CAPAS = {posicion: verPosicion, pagar: verPagar, cobrar: verCobrar,
             proyeccion: verProyeccion, retiro: verRetiro,
             hallazgos: verHallazgos};

function pintar(){
  document.querySelectorAll('[data-unidad]').forEach(function(b){
    b.setAttribute('aria-pressed', b.dataset.unidad === UNIDAD);
  });
  document.querySelectorAll('[data-capa]').forEach(function(b){
    b.setAttribute('aria-selected', b.dataset.capa === SOLAPA);
  });
  var cont = document.getElementById('capa');
  cont.innerHTML = '';
  CAPAS[SOLAPA]().forEach(function(n){ cont.appendChild(n); });
}

document.addEventListener('click', function(e){
  var b = e.target.closest('[data-unidad],[data-capa]');
  if (!b) return;
  if (b.dataset.unidad) UNIDAD = b.dataset.unidad;
  if (b.dataset.capa) SOLAPA = b.dataset.capa;
  pintar();
});
pintar();
"""

CAPAS = [("posicion", "Posición"), ("pagar", "A quién pagar"),
         ("cobrar", "A cobrar"), ("proyeccion", "Proyección"),
         ("retiro", "Retiro"), ("hallazgos", "Hallazgos")]


def render(paquete):
    import html as _h
    e = lambda t: _h.escape(str(t if t is not None else ""))

    H = []
    A = H.append
    A('<meta charset="utf-8">')
    A('<meta name="viewport" content="width=device-width,initial-scale=1">')
    A('<title>%s — finauto</title>' % e(paquete["cliente"]))
    A('<style>%s</style>' % CSS)
    A('<div class="wrap">')
    A('<div class="cab"><div>')
    A('<h1>%s</h1>' % e(paquete["cliente"]))
    A('<p class="sub">Tablero de decisión · finauto</p>')
    A('</div><div class="meta">datos del cash al <b>%s</b><br>'
      'ventana de decisión: 7 días</div></div>' % e(paquete["fecha"]))

    A('<div class="pills">')
    for u in paquete["unidades"]:
        A('<button class="pill" data-unidad="%s">%s</button>'
          % (e(u), e("Grupo" if u == "GRUPO" else u)))
    A('</div>')

    A('<div class="tabs" role="tablist">')
    for cid, nom in CAPAS:
        A('<button class="tab" role="tab" data-capa="%s">%s</button>' % (cid, e(nom)))
    A('</div>')
    A('<div id="capa"></div>')
    A('</div>')
    A('<script>var D = %s;</script>'
      % json.dumps(paquete, ensure_ascii=False).replace("</", "<\\/"))
    A('<script>%s</script>' % JS)
    return "\n".join(H)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="La app de finauto, en un solo HTML")
    ap.add_argument("--contrato", required=True)
    ap.add_argument("--cliente", default="maga")
    ap.add_argument("--salida", default="salidas/finauto.html")
    args = ap.parse_args()

    with io.open(args.contrato, encoding="utf-8") as f:
        contrato = json.load(f)

    salida = args.salida
    if not os.path.isabs(salida):
        salida = os.path.join(BASE_REPO, salida)
    d = os.path.dirname(salida)
    if d and not os.path.isdir(d):
        os.makedirs(d)

    paquete = DATOS.armar(contrato, args.cliente)
    with io.open(salida, "w", encoding="utf-8") as f:
        f.write("<!doctype html>\n<html lang=\"es\">\n")
        f.write(render(paquete))
        f.write("\n</html>")
    print("Listo: %s  (%d KB)" % (salida, os.path.getsize(salida) // 1024))


if __name__ == "__main__":
    main()
