# -*- coding: utf-8 -*-
"""
dashboard.app — la aplicación: un HTML con capas, empresa por empresa.

QUÉ CAMBIÓ RESPECTO DEL INFORME
-------------------------------
Antes esto era un documento de una sola página. la dirección (06/09/2026):

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
import datetime

BASE_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)

from dashboard import datos as DATOS


CSS = """
/* EL ESTILO (17/09/2026).
 *
 * la dirección, 16/09: "me gustaria ver distintos estilos que se vea mas profesional,
 * mas software y no tanto un tablero hecho con Power BI". Se probaron tres
 * direcciones y eligio una mezcla: barra lateral oscura con la navegacion,
 * papel calido de fondo, serif en titulos y en los numeros grandes, monoespaciada
 * en las cifras, y LINEAS en vez de cajas con sombra. Los mockups quedaron en
 * scratchpad/estilos (A_ledger, B_producto, C_relato, D_final = el elegido).
 *
 * Sigue valiendo lo del 06/09: fondo claro, "no que parezca que vas a hackear la
 * NASA". La barra oscura es un ancla, no un tema oscuro.
 *
 * TIPOGRAFIAS. Se piden a Google Fonts; si no hay internet (una reunion, un
 * proyector) caen a Georgia / Menlo / Helvetica, que se parecen bastante. El
 * tablero se tiene que ver igual de bien sin red: por eso las medidas no
 * dependen de la fuente.
 */
:root{
  --fondo:#F7F5EF; --panel:#F7F5EF; --panel2:#EFEDE6; --linea:#E1DDD2;
  --tinta:#1B1A17; --suave:#6B685F; --tenue:#9B978C;
  --lado:#1C1B18; --lado-texto:#B8B4A8; --lado-tenue:#7E7B72; --lado-linea:#2E2C27; --lado-on:#2A2824;
  --azul:#1B1A17; --verde:#2F6B45; --rojo:#B4321F; --naranja:#B97A2A;
  --violeta:#5B5F8A; --amarillo:#8E6A12; --oro:#C9A64A;
  --verde-piso:#E8EFE6; --rojo-piso:#F6E6E2; --ambar-piso:#F3ECD9;
  --serif:"Newsreader",Georgia,"Times New Roman",serif;
  --sans:"IBM Plex Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
  --mono:"IBM Plex Mono",Menlo,Consolas,monospace;
}
*{box-sizing:border-box}
.debito{border-top:1px solid var(--linea);padding:12px 0}
.debito summary{cursor:pointer}
.debito summary:focus-visible{outline:2px solid var(--tinta);outline-offset:4px}
html,body{margin:0;background:var(--fondo);color:var(--tinta)}
body{font:14.5px/1.5 var(--sans);-webkit-font-smoothing:antialiased}

/* ---- la barra lateral + el contenido */
.app{display:grid;grid-template-columns:248px minmax(0,1fr);min-height:100vh;
  background:linear-gradient(to right,var(--lado) 248px,var(--fondo) 248px)}
.lado{background:var(--lado);color:var(--lado-texto);padding:30px 22px;display:flex;
  flex-direction:column;gap:26px;position:sticky;top:0;height:100vh}
.logo{display:flex;align-items:center;gap:9px;font:600 22px var(--serif);color:#F3F0E8;
  letter-spacing:-.01em}
.logo i{width:8px;height:8px;border-radius:99px;background:var(--rojo)}
.lado hr{border:0;border-top:1px solid var(--lado-linea);margin:0}
.cliente{font:500 11px var(--mono);letter-spacing:.12em;color:var(--lado-tenue)}
.cliente b{display:block;font:600 19px var(--serif);color:#F3F0E8;letter-spacing:0;margin-top:6px}
.pills{display:flex;font:500 11px var(--mono);letter-spacing:.08em}
.pill{flex:1;padding:7px 0;border:1px solid var(--lado-linea);color:var(--lado-texto);
  background:none;cursor:pointer;font-family:inherit;font-size:inherit;letter-spacing:inherit}
.pill+.pill{border-left:0}
.pill:hover{color:#F3F0E8}
.pill[aria-pressed="true"]{background:#F3F0E8;color:var(--lado);border-color:#F3F0E8}
.tabs{display:flex;flex-direction:column;gap:2px}
.tab{display:flex;align-items:center;gap:12px;padding:10px 12px;border:0;border-radius:7px;
  background:none;color:var(--lado-texto);font:500 14.5px var(--sans);text-align:left;
  cursor:pointer;white-space:nowrap}
.tab svg{width:17px;height:17px;flex:none;stroke:currentColor;fill:none;stroke-width:1.6;
  stroke-linecap:round;stroke-linejoin:round}
.tab:hover{color:#F3F0E8}
.tab[aria-selected="true"]{background:var(--lado-on);color:#F3F0E8}
.lado .pie{margin-top:auto;font:400 11.5px/1.9 var(--mono);color:var(--lado-tenue)}
.lado .pie b{color:var(--lado-texto);font-weight:500}

.wrap{padding:40px 48px 64px;max-width:1240px}
.cab{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap}
h1{font:600 34px/1 var(--serif);margin:0;letter-spacing:-.01em}
.sub{color:var(--suave);font-size:13.5px;margin:10px 0 0}
.cab .meta{font:400 12px/1.9 var(--mono);color:var(--suave);text-align:right}
.cab .meta b{color:var(--tinta);font-weight:500}
.cab .meta i{display:inline-block;width:7px;height:7px;border-radius:99px;background:var(--verde);
  margin-right:7px;vertical-align:1px}

/* ---- secciones: titulos serif, bloques sin caja */
h2{font:600 21px/1.2 var(--serif);color:var(--tinta);margin:44px 0 14px;letter-spacing:-.01em;
  text-transform:none}
h2:first-child{margin-top:34px}
.card{background:none;border:0;border-radius:0;padding:0;box-shadow:none}
.card+.card{margin-top:22px}
.card[style*="border-left"]{padding-left:16px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:0;
  margin-top:34px;border-top:1px solid var(--tinta);border-bottom:1px solid var(--linea)}
.kpi{padding:24px 28px 26px 0}
.kpis .card+.card{margin-top:0}
.kpi+.kpi{border-left:1px solid var(--linea);padding-left:28px}
.kpi .et{font-size:13px;color:var(--suave)}
.kpi .n{font:600 46px/1 var(--serif);letter-spacing:-.02em;margin:12px 0 8px;
  font-variant-numeric:tabular-nums}
.kpi .pie{font-size:12.5px;color:var(--tenue)}
.kpi.malo{background:none;border-color:var(--linea)}
.kpi.malo .n{color:var(--rojo)}
.kpi.bien .n{color:var(--tinta)}

/* ---- tablas: encabezado mono, lineas finas, cifras mono */
table{width:100%;border-collapse:collapse;font-size:14.5px}
th{text-align:right;font:500 11px var(--mono);letter-spacing:.1em;text-transform:uppercase;
  color:var(--tenue);padding:0 0 10px 18px;border-bottom:1px solid var(--tinta)}
th:first-child,td:first-child{text-align:left;padding-left:0}
table.texto td:nth-child(2),table.texto th:nth-child(2){text-align:left}
td{text-align:right;padding:11px 0 11px 18px;border-top:0;border-bottom:1px solid var(--linea);
  font-variant-numeric:tabular-nums}
td:last-child,th:last-child{font-family:var(--mono);font-size:14px}
tr.tot td{font-weight:600;border-top:1px solid var(--tinta);border-bottom:2px solid var(--tinta)}
.pos{color:var(--verde)} .neg{color:var(--rojo)}
.chip{display:inline-block;font:500 11px var(--mono);letter-spacing:.04em;padding:3px 8px;
  border-radius:4px}
.chip.ok{background:var(--verde-piso);color:var(--verde)}
.chip.mal{background:var(--rojo-piso);color:var(--rojo)}
.chip.medio{background:var(--ambar-piso);color:var(--amarillo)}
.barra{height:10px;border-radius:0;background:var(--tinta);min-width:3px}
.nota{font-size:12.5px;color:var(--tenue);margin:14px 0 0;max-width:72ch}
.hall{border-left:3px solid var(--oro);padding:4px 0 4px 16px}
.hall .t{font:600 18px var(--serif);margin-bottom:6px}
.hall .m{font:500 22px var(--mono);color:var(--amarillo);margin-top:10px;
  font-variant-numeric:tabular-nums}
.hall + .hall{margin-top:22px}
ul.limpia{margin:0;padding-left:19px;color:var(--suave);font-size:14px}
ul.limpia li{margin-bottom:8px}
.envuelve{overflow-x:auto}
svg{display:block;width:100%;height:auto;overflow:visible}
.leyenda{display:flex;gap:22px;flex-wrap:wrap;font-size:12.5px;color:var(--suave);margin-bottom:16px}
.leyenda i{width:9px;height:9px;display:inline-block;margin-right:7px;vertical-align:-1px}
.ejeY{fill:var(--tenue);font-size:10px;font-family:var(--mono)}
.ejeX{fill:var(--tenue);font-size:10px;font-family:var(--mono)}
.rejilla{stroke:var(--linea);stroke-width:1}
.resumen{font-size:11.5px;color:var(--tenue);margin-top:3px}
.resumen b{color:var(--rojo);font-weight:600}
select{background:#fff;border:1px solid var(--linea);color:var(--tinta);
  border-radius:4px;padding:5px 8px;font-family:inherit;font-size:12.5px}
select:focus{outline:none;border-color:var(--tinta)}
input[type=text],input[type=number]{background:#fff;border:1px solid var(--linea);border-radius:4px;
  font:14px var(--mono);color:var(--tinta)}
.endosado{background:var(--verde-piso)}
input[type=range]{accent-color:var(--tinta)}
input[type=checkbox]{accent-color:var(--tinta)}
button.mini{background:#fff;border:1px solid var(--linea);border-radius:4px;
  padding:5px 10px;font:500 11.5px var(--mono);cursor:pointer;color:var(--suave)}
button.mini:hover{color:var(--tinta);border-color:var(--tinta)}
[hidden]{display:none!important}
@media (max-width:900px){
  .app{grid-template-columns:1fr;background:var(--fondo)}
  .lado{position:static;height:auto;padding:18px 16px;gap:14px}
  .tabs{flex-direction:row;flex-wrap:wrap}
  .lado .pie{margin-top:0}
  .wrap{padding:24px 16px 48px}
  .kpis{grid-template-columns:1fr}
  .kpi+.kpi{border-left:0;border-top:1px solid var(--linea);padding-left:0}
}
@media print{.lado{position:static;height:auto}.card{break-inside:avoid}}
"""

JS = r"""
// ---------------------------------------------------------------- formato
// Acá NO se calcula plata. Todo viene resuelto de Python (dashboard/datos.py):
// esto solo elige qué mostrar y cómo escribirlo. Ver el docstring de app.py.
// UNA SOLA ESCALA POR TABLA.
//
// ERROR REAL (06/09/2026). la dirección: "queda visualmente feo, si un numero no
// supera el millon le pongamos el numero completo... pero fijate como rapido a
// simple vista salta un 300M de servicios? Es lo primero que ve el ojo humano".
//
// La lista de salidas mezclaba "$39 M" con "$425.547". El ojo compara la
// cantidad de digitos antes que la unidad, asi que $425.547 parecia el numero
// grande de la columna. Le hizo dudar de si faltaban gastos el 8 y el 9 --
// estaban todos: lo que fallaba era como estaban escritos.
//
// Regla: abreviado SOLO en las tarjetas grandes, donde hay un numero solo y
// nada con que compararlo. En cualquier tabla, pesos completos.
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

// El plan se precalcula para unas pocas ventanas; el slider se mueve de a un
// dia. Se usa la mas cercana y se dice para cual es, en vez de no mostrar nada.
function cercana(claves, v){
  var mejor = null, dif = 1e9;
  claves.forEach(function(k){
    var d = Math.abs(Number(k) - v);
    if (d < dif){ dif = d; mejor = Number(k); }
  });
  return mejor;
}


// ---------------------------------------------------------------- graficos
// SVG escrito a mano, sin ninguna libreria.
//
// No es purismo: el archivo tiene que abrirse en una reunion sin internet.
// Cualquier <script src> de un CDN es una forma de que el tablero aparezca
// vacio justo cuando importa. Un grafico de barras son cuatro rectangulos.
// Tinta, gris, oro, y despues los tonos que hagan falta. Sin azules ni verdes
// chillones: el unico color fuerte del tablero es el rojo de lo vencido.
var PALETA = ['#1B1A17', '#8E8A7E', '#C9A64A', '#5B5F8A', '#B97A2A', '#B4321F'];

function svgEl(t, attrs){
  var e = document.createElementNS('http://www.w3.org/2000/svg', t);
  for (var k in attrs) e.setAttribute(k, attrs[k]);
  return e;
}

// El tooltip del grafico de ingresos.
//
// la dirección: "lo que entra dia por dia, pasar el mouse por arriba y que te diga el
// monto de cada concepto". Es lo que convierte un grafico lindo en uno que se
// usa: la barra alta del 07 no dice nada hasta que se sabe que son $490M de
// PAMI y no treinta dias de mostrador.
function tooltip(){
  var t = document.getElementById('tip');
  if (!t){
    t = el('div'); t.id = 'tip';
    t.style.cssText = 'position:fixed;z-index:99;background:var(--panel);' +
      'border:1px solid var(--linea);border-radius:9px;padding:10px 12px;' +
      'font-size:12.5px;box-shadow:0 4px 16px rgba(16,32,24,.14);pointer-events:none;' +
      'display:none;min-width:200px;color:var(--tinta)';
    document.body.appendChild(t);
  }
  return t;
}

function mostrarTip(ev, html){
  var t = tooltip();
  t.innerHTML = html;
  t.style.display = 'block';
  var x = ev.clientX + 14, y = ev.clientY + 14;
  if (x + 250 > window.innerWidth) x = ev.clientX - 250;
  if (y + t.offsetHeight > window.innerHeight) y = ev.clientY - t.offsetHeight - 10;
  t.style.left = x + 'px'; t.style.top = y + 'px';
}

function ocultarTip(){
  var t = document.getElementById('tip');
  if (t) t.style.display = 'none';
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

    // La zona sensible cubre TODA la altura de la columna, no solo la barra.
    // Apuntarle a una barra de 3 pixeles es imposible, y un tooltip al que hay
    // que apuntar no lo usa nadie.
    var zona = svgEl('rect', {x: x, y: 0, width: w, height: alto,
                              fill: 'transparent'});
    zona.style.cursor = 'crosshair';
    zona.addEventListener('mousemove', function(ev){
      var filas = [];
      d.valores.forEach(function(v, j){
        if (!v) return;
        filas.push('<div style="display:flex;justify-content:space-between;gap:14px">' +
          '<span><i style="width:9px;height:9px;border-radius:2px;display:inline-block;' +
          'margin-right:6px;background:' + PALETA[j % PALETA.length] + '"></i>' +
          datos.fuentes[j] + '</span><b>' + pesos(v) + '</b></div>');
      });
      if (!filas.length) filas.push('<span style="color:var(--tenue)">Sin ingresos ese dia</span>');
      mostrarTip(ev, '<div style="font-weight:700;margin-bottom:6px">' + dia(d.fecha) +
        '</div>' + filas.join('') +
        '<div style="display:flex;justify-content:space-between;gap:14px;' +
        'margin-top:6px;padding-top:6px;border-top:1px solid var(--linea)">' +
        '<span>Total</span><b>' + pesos(d.total) + '</b></div>');
    });
    zona.addEventListener('mouseleave', ocultarTip);
    svg.appendChild(zona);
  });
  return svg;
}

function curvaCaja(curva, critico){
  var ancho = 900, alto = 230, izq = 72, abajo = 26, arriba = 10;
  if (!curva.length) return el('p', 'nota', 'Sin datos para proyectar.');
  var vals = curva.map(function(p){ return p.caja; });
  // El cero SIEMPRE entra en el rango: la linea de "caja en cero" es el
  // dato del grafico. (Antes decia Math.min.apply(null, vals, [0]) -- el
  // tercer argumento de apply se ignora, asi que el 0 nunca entraba. Con una
  // curva plana en -190M el rango quedaba en 1 peso y el relleno del area
  // se dibujaba a -41.000 millones de pixeles, tapando la pantalla entera.
  // Aparecio con NAVAR: datos semanales, todos el mismo dia, curva plana.)
  var max = Math.max.apply(null, vals.concat([0])), min = Math.min.apply(null, vals.concat([0]));
  var margen = Math.max((max - min) * 0.05, 1);
  max += margen; min -= margen;
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



// ---------------------------------------------------------------- desplegar
// Un bloque que se abre. Se usa en los gastos y en lo que se puede patear:
// la barra dice CUANTO, y abrirla dice DE QUE esta hecha. Sin eso, frente a
// una barra de $5.028M la unica reaccion posible es desconfiar.
var ABIERTO = {};

function desplegable(id, cabecera, contenido){
  var caja = el('div');
  var b = el('button');
  b.type = 'button';
  b.style.cssText = 'background:none;border:0;padding:0;cursor:pointer;width:100%;' +
                    'text-align:left;font-family:inherit;font-size:inherit;color:inherit';
  var flecha = el('span', null, ABIERTO[id] ? '▾ ' : '▸ ');
  flecha.style.color = 'var(--tenue)';
  var cab = el('div');
  cab.style.cssText = 'display:flex;align-items:center;gap:2px';
  cab.appendChild(flecha);
  cabecera.style.flex = '1';
  cab.appendChild(cabecera);
  b.appendChild(cab);
  b.onclick = function(){
    if (ABIERTO[id]) delete ABIERTO[id]; else ABIERTO[id] = 1;
    pintar();
  };
  caja.appendChild(b);
  if (ABIERTO[id]){
    var c = el('div');
    c.style.cssText = 'margin:8px 0 14px 20px;padding-left:12px;' +
                      'border-left:2px solid var(--linea)';
    c.appendChild(contenido);
    caja.appendChild(c);
  }
  return caja;
}

// ---------------------------------------------------------------- endosos
// El unico estado que el tablero guarda. Es una simulacion del usuario, no un
// dato del negocio: por eso vive en el navegador y no toca el contrato.
var ENDOSOS = {};
// Lo que el usuario esta simulando en la solapa de proyeccion.
var VENTANA = 45, PATEADO = {}, SUELTO = {}, CON_IC = false, PARCIAL = {};
try { ENDOSOS = JSON.parse(localStorage.getItem('finauto_endosos') || '{}'); }
catch (e) { ENDOSOS = {}; }

function guardarEndosos(){
  try { localStorage.setItem('finauto_endosos', JSON.stringify(ENDOSOS)); }
  catch (e) { }
}

function resumenEndosos(){
  var por = {}, total = 0;
  var ch = (actual().a_cobrar || {}).cheques || [];
  ch.forEach(function(x){
    var dest = ENDOSOS[x.id];
    if (!dest) return;
    por[dest] = (por[dest] || 0) + x.importe;
    total += x.importe;
  });
  return {por: por, total: total};
}

// UN ENDOSO SE IMPUTA AL RESUMEN MAS VIEJO, ASI QUE BAJA LO VENCIDO PRIMERO.
//
// la dirección: "en los cheques que te diga cuanto baja de lo vencido, no de lo a
// vencer". Es la regla del negocio: todo pago o endoso se aplica al resumen
// mas viejo. Y es lo unico que importa para decidir -- lo vencido es lo que
// puede hacer que te corten la compra; bajar deuda que todavia no vencio no
// cambia nada hoy.
function bajaVencido(nombre, monto){
  var p = (actual().proveedores || []).filter(function(q){ return q.nombre === nombre; })[0];
  if (!p) return {vencido: 0, resto: monto, queda: null};
  var aVencido = Math.min(monto, p.vencido);
  return {vencido: aVencido, resto: monto - aVencido,
          queda: Math.max(0, p.vencido - aVencido)};
}

// ---------------------------------------------------------------- estado
var UNIDAD = D.unidades[0], SOLAPA = 'posicion', VENTANA = String(D.ventanas[0]);
// Las palabras con las que el tablero le habla a ESTE cliente (catalogo.vocabulario).
var V = D.vocab || {proveedor:'proveedor', proveedores:'proveedores', Proveedor:'Proveedor',
                    nota_vencido:'con proveedores', tiene_refi:false, nota_ritmo:'', nota_a_cobrar:'', no_sabe_cobranza:'', no_sabe_extra:'', comprobante:'resumen'};
function actual(){ return D.datos[UNIDAD]; }

// ---------------------------------------------------------------- capas
function verPosicion(){
  var d = actual(), k = d.kpis, out = [];

  // LOS TRES NUMEROS QUE SE MIRAN, Y NADA MAS.
  //
  // Antes habia un cuarto, "margen a 7 dias". la dirección lo saco: "no me gusta, no
  // se entiende que toma". Tenia razon -- era caja + cobros - salidas de una
  // ventana, o sea tres cosas mezcladas en un numero sin unidad clara. Un KPI
  // que hay que explicar no es un KPI.
  var c = el('div', 'kpis');
  [['Caja de hoy', pesos(k.caja, true), k.efectivo_sin_asignar
      ? '+ ' + pesos(k.efectivo_sin_asignar, true) + ' de efectivo del grupo, sin asignar'
      : 'banco + efectivo', ''],
   ['Vencido con ' + V.proveedores, pesos(k.vencido, true),
      V.nota_vencido, k.vencido > 0 ? 'malo' : 'bien'],
   ['Vence en los proximos 7 dias', pesos(k.por_vencer, true),
      V.nota_vencido, '']
  ].forEach(function(x){
    var t = el('div', 'card kpi ' + x[3]);
    t.appendChild(el('div', 'et', x[0]));
    t.appendChild(el('div', 'n', x[1]));
    t.appendChild(el('div', 'pie', x[2]));
    c.appendChild(t);
  });
  out.push(c);

  if (d.vencidos_resumen){
    var vr = d.vencidos_resumen, cv = el('div', 'card');
    out.push(el('h2', null, 'Vencido e impago · las tres puntas'));
    var tv = el('table');
    tv.innerHTML = '<thead><tr><th>Obligación</th><th>Cuánto</th><th>Desde cuándo</th><th>Qué pasa si no se paga</th></tr></thead>';
    var bv = el('tbody');
    vr.filas.forEach(function(f){
      var tr = el('tr');
      [f.nombre, pesos(f.monto), f.desde ? dia(f.desde) : 'Sin vencido', f.riesgo].forEach(function(t){
        var td = el('td'); td.textContent = t; tr.appendChild(td);
      });
      bv.appendChild(tr);
    });
    tv.appendChild(bv); cv.appendChild(tv);
    cv.appendChild(el('p', 'nota', 'Total vencido: <b>' + pesos(vr.total) +
      '</b>. Es deuda acumulada; no se vuelve a sumar a las salidas futuras.' +
      (vr.otros ? ' Incluye otros vencidos fuera de las tres puntas: ' + pesos(vr.otros) + '.' : '')));
    out.push(cv);
  }

  // La refi va aparte: es obligacion, pero no es una drogueria y no tiene
  // tolerancia de proveedor. Mezclarla con las droguerias infla la deuda que
  // "te puede cortar la compra", que es justo la que decide.
  if (d.refi && (d.refi.vencido || d.refi.por_vencer)){
    var cr = el('div', 'card');
    cr.style.borderLeft = '3px solid var(--violeta)';
    cr.innerHTML = '<b>Refinanciacion</b> — aparte de las ' + V.proveedores + ': se puede ' +
      'patear hasta el vencimiento del mes siguiente (2 semanas), y atrasarla no ' +
      'hace que te corten la compra.<br>' +
      '<span style="color:var(--suave)">Vencida: <b>' + pesos(d.refi.vencido) +
      '</b> · por vencer: ' + pesos(d.refi.por_vencer) + '</span>';
    out.push(cr);
  }

  if (d.ingresos_dia && d.ingresos_dia.dias.length){
    out.push(el('h2', null, 'Cobranza e ingresos · próximos 30 días'));
    var ci = el('div', 'card');
    ci.appendChild(leyenda(d.ingresos_dia.fuentes));
    ci.appendChild(barrasApiladas(d.ingresos_dia));
    ci.appendChild(el('p', 'nota', dia(d.ingresos_dia.desde) + ' a ' + dia(d.ingresos_dia.hasta) +
      ' · Total: <b>' + pesos(d.ingresos_dia.total) + '</b>. Cero significa sin ingresos cargados para ese día.'));
    var detalle = el('details');
    detalle.appendChild(el('summary', null, 'Ver importes por día y cheques aparte'));
    var tdia = el('table');
    tdia.innerHTML = '<thead><tr><th>Día</th><th>Ingreso en la curva</th></tr></thead>';
    d.ingresos_dia.dias.forEach(function(f){
      tdia.appendChild(el('tr', null, '<td>' + dia(f.fecha) + '</td><td>' + pesos(f.total) + '</td>'));
    });
    detalle.appendChild(tdia);
    detalle.appendChild(el('p', 'nota', 'Cheques en cartera en el mismo período: <b>' +
      pesos(d.ingresos_dia.cheques_total) + '</b>. No suman a la curva hasta decidir depósito o endoso.'));
    d.ingresos_dia.cheques.forEach(function(f){
      detalle.appendChild(el('p', 'nota', dia(f.fecha) + ': ' + pesos(f.importe)));
    });
    ci.appendChild(detalle);
    out.push(ci);
  }

  // EN QUE SE VA LA PLATA, CON LAS DROGUERIAS ADENTRO.
  // Antes este grafico salia solo del bloque de egresos, donde la deuda con
  // droguerias NO esta: mostraba en que se va la plata sin el gasto mas grande.
  out.push(el('h2', null, 'En que se va la plata (45 dias)'));
  var cg = el('div', 'card');
  var max = Math.max.apply(null, d.gastos.map(function(g){ return g.monto; })) || 1;
  d.gastos.forEach(function(g, gi){
    var f = el('div');
    f.style.cssText = 'display:grid;grid-template-columns:minmax(240px,2fr) 3fr 150px;gap:16px;' +
                      'align-items:center;padding:6px 0';
    f.appendChild(el('div', null, '<span style="color:var(--suave);font-size:13.5px">' +
      g.nombre + '</span>'));
    var b = el('div'), bb = el('div', 'barra');
    bb.style.width = Math.max(2, 100 * g.monto / max) + '%';
    b.appendChild(bb); f.appendChild(b);
    f.appendChild(el('div', null, '<span style="font-variant-numeric:tabular-nums;font-family:var(--mono);' +
      'display:block;text-align:right">' + pesos(g.monto) + '</span>'));

    // Cada barra se abre y muestra de que esta hecha. Frente a una barra de
    // $5.028M la primera pregunta siempre es "de que", y hasta ahora habia que
    // ir a buscarlo a otro lado.
    var det = el('table');
    (g.detalle || []).forEach(function(x){
      var tr = el('tr');
      tr.appendChild(el('td', null, (x.fecha ? '<b>' + dia(x.fecha) + '</b>  ' : '') +
        '<span style="color:var(--suave)">' + x.concepto + '</span>'));
      tr.appendChild(el('td', null, pesos(x.monto)));
      det.appendChild(tr);
    });
    var env = el('div', 'envuelve'); env.appendChild(det);
    cg.appendChild(desplegable('gasto_' + gi, f, env));
  });
  cg.appendChild(el('p', 'nota', 'Incluye lo que vence con cada ' + V.proveedor + ', no solo ' +
    'los egresos del cashflow. Sin eso faltaria el gasto mas grande que hay.'));
  out.push(cg);

  out.push(el('h2', null, 'Proximas salidas'));
  var cs = el('div', 'card'), ts = el('table', 'texto');
  ts.innerHTML = '<tr><th>Fecha</th><th>Detalle</th><th>Importe</th></tr>';
  d.salidas.forEach(function(x){
    var tr = el('tr');
    tr.appendChild(el('td', null, '<b>' + dia(x.fecha) + '</b>'));
    tr.appendChild(el('td', null, '<span style="color:var(--suave)">' + x.detalle + '</span>'));
    tr.appendChild(el('td', null, pesos(x.monto)));
    ts.appendChild(tr);
  });
  var w = el('div', 'envuelve'); w.appendChild(ts); cs.appendChild(w);
  if (!d.salidas.length) cs.appendChild(el('p', 'nota', 'Sin salidas cargadas en la ventana.'));
  out.push(cs);
  return out;
}

function verPagar(){
  var d = actual(), out = [];

  // ORDENADO POR ATRASO, Y CON EL RESUMEN A LA VISTA.
  //
  // la dirección, 06/09/2026: "el atraso que marcaste esta como el orto"; "no
  // pongamos esa tolerancia, no ordenemos por tolerancia, ordenemos por
  // atraso"; "aclaremos que resumen suman esas deudas".
  //
  // Las tres cosas van juntas. La tolerancia era una estimacion NUESTRA y el
  // atraso es un hecho: ordenar por la estimacion escondia el hecho. Y un
  // atraso sin la fecha del resumen del que sale no se puede discutir -- fue
  // exactamente lo que dejo pasar el error de Cofaloza, donde un resto de
  // $1,3M del 31/07 hacia figurar 5,1 semanas en vez de 1,1.
  // LOS QUE PESAN ARRIBA; EL RESTO, PLEGADO.
  //
  // Con MAGA eran cinco droguerias y la lista entraba en una pantalla. Con
  // NAVAR (17/09/2026) son 88 proveedores, y ordenar TODO por atraso ponia
  // primero una deuda de $1.300 con 30 semanas y dejaba los $135M de COPETEGLA
  // en la mitad de una lista de doce mil pixeles. La regla sigue siendo la de
  // la dirección -- ordenar por atraso, no por nuestra tolerancia -- pero aplicada
  // adentro de dos grupos: los que juntan el 90% de la plata (o los 15 mas
  // grandes, lo que ocurra primero) y "el resto", que se abre si hace falta.
  var c = el('div', 'card');
  var baja = resumenEndosos().por;
  var hayEndoso = Object.keys(baja).length > 0;
  var porMonto = d.proveedores.slice().sort(function(a, b){ return b.total - a.total; });
  var totalTodos = porMonto.reduce(function(a, p){ return a + p.total; }, 0);
  var grandes = {}, acum = 0;
  porMonto.forEach(function(p, i){
    if (i < 15 && acum < totalTodos * 0.9){ grandes[p.nombre] = 1; acum += p.total; }
  });
  var pesan = d.proveedores.filter(function(p){ return grandes[p.nombre]; });
  var resto = d.proveedores.filter(function(p){ return !grandes[p.nombre]; });

  function tablaProveedores(lista){
  var t = el('table');
  t.innerHTML = '<tr><th>' + V.Proveedor + '</th><th>Vencido</th><th>Vence pronto</th>' +
                (hayEndoso ? '<th>Endoso</th>' : '') + '<th>Atraso</th></tr>';
  lista.forEach(function(p){
    var tr = el('tr');
    var det = '<b>' + p.nombre + '</b>';
    if (p.vence_dia) det += '<div class="resumen">vence ' + p.vence_dia + '</div>';
    tr.appendChild(el('td', null, det));

    // Cada monto vencido es un RESUMEN con su fecha.
    var venc = '<span class="' + (p.vencido ? 'neg' : '') + '">' + pesos(p.vencido) + '</span>';
    if (p.resumenes && p.resumenes.length){
      venc += '<div class="resumen">' + p.resumenes.map(function(r){
        return V.comprobante + ' del <b>' + dia(r.fecha) + '</b> ' + pesos(r.monto);
      }).join(' · ') + '</div>';
    }
    tr.appendChild(el('td', null, venc));
    tr.appendChild(el('td', null, pesos(p.por_vencer)));

    // Si en la solapa de cheques se simulo un endoso, la deuda de esa
    // drogueria baja aca tambien. Es la razon de ser del endoso: contestar
    // "y si endoso este, como quedo?" sin ir a recalcular a otro lado.
    if (hayEndoso){
      var descuento = baja[p.nombre] || 0;
      tr.appendChild(el('td', descuento ? 'pos' : '', descuento
        ? '− ' + pesos(descuento) + '<div class="resumen">endoso simulado</div>' : '—'));
    }

    var at = '<b>' + sem(p.atraso) + '</b>';
    if (p.atraso_desde) at += '<div class="resumen">desde el ' + dia(p.atraso_desde) + '</div>';
    tr.appendChild(el('td', null, at));
    t.appendChild(tr);
  });
  return t;
  }

  var w = el('div', 'envuelve'); w.appendChild(tablaProveedores(pesan)); c.appendChild(w);
  if (resto.length){
    var vencResto = resto.reduce(function(a, p){ return a + p.vencido; }, 0);
    var totResto = resto.reduce(function(a, p){ return a + p.total; }, 0);
    var cab = el('div', null, '<b>Los otros ' + resto.length + ' ' + V.proveedores + '</b> ' +
      '<span style="color:var(--suave)">— vencido ' + pesos(vencResto) + ' de ' + pesos(totResto) +
      ' en total. Ninguno pesa solo; juntos, sí.</span>');
    cab.style.padding = '14px 0';
    var w2 = el('div', 'envuelve'); w2.appendChild(tablaProveedores(resto));
    c.appendChild(desplegable('resto_proveedores', cab, w2));
  }
  if (!d.proveedores.length){
    c.appendChild(el('p', 'nota', 'Sin deuda con ' + V.proveedores + ' en esta empresa.'));
  }

  // Los restos viejos y chicos se muestran, pero no definen el atraso.
  var restos = [];
  d.proveedores.forEach(function(p){
    (p.restos_ignorados || []).forEach(function(r){
      restos.push(p.nombre + ': ' + pesos(r.importe) + ' del ' + dia(r.fecha));
    });
  });
  if (restos.length){
    var muestra = restos.slice(0, 6).join(' · ') +
      (restos.length > 6 ? ' · y ' + (restos.length - 6) + ' mas' : '');
    c.appendChild(el('p', 'nota', 'Hay ' + restos.length + ' restos viejos que <b>se siguen ' +
      'debiendo</b> pero no definen el atraso, porque son menos del 5% del vencido con ese ' +
      V.proveedor + ' y suelen ser diferencias de imputacion: ' + muestra + '.'));
  }
  c.appendChild(el('p', 'nota', 'Arriba, los que juntan el 90% de la deuda; ordenados por ' +
    '<b>atraso</b>, primero el que hace mas que espera. El atraso se mide desde el ' +
    'comprobante mas viejo sin pagar.'));
  out.push(c);
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
    'La regla: primero se cubre la deuda con ' + V.proveedores + ' que <b>ya venció</b> ' +
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
    'con fecha pasada y sin entrar', c.vencido ? 'malo' : 'bien'],
   ['Nos deben, por vencer', pesos(c.por_vencer, true), 'en los proximos 45 dias', ''],
   ['Cheques en cartera', pesos(c.cheques_total, true),
    c.cheques.length + ' cheques, cada uno una decision', '']
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
      tr.appendChild(el('td', null, '<b>' + f.nombre + '</b>' +
        '<div class="resumen">' + (f.que_es === 'drogueria' ? V.proveedor : f.que_es) + '</div>'));
      tr.appendChild(el('td', f.vencido ? 'neg' : '', pesos(f.vencido)));
      tr.appendChild(el('td', null, pesos(f.por_vencer)));
      tr.appendChild(el('td', null, '<b>' + pesos(f.total) + '</b>'));
      t.appendChild(tr);
    });
    var w = el('div', 'envuelve'); w.appendChild(t); cc.appendChild(w);
    cc.appendChild(el('p', 'nota', V.nota_a_cobrar));
    out.push(cc);
  }

  // CADA CHEQUE, CON SUS DOS DECISIONES SEPARADAS.
  //
  // la dirección: "habria que sumar una columna mas: la de estado Endosar/depositar
  // y la de Drogueria: Suizo, DDS, COFA". Van separadas porque son dos
  // decisiones distintas -- primero que hago, despues a quien.
  if (c.cheques.length){
    out.push(el('h2', null, 'Cada cheque es una decision'));
    var ch = el('div', 'card'), tc = el('table');
    tc.innerHTML = '<tr><th>Vence</th><th>Librador</th><th>Importe</th>' +
                   '<th>Que hago</th><th>A quien</th><th>Efecto</th></tr>';
    c.cheques.forEach(function(x){
      var tr = el('tr');
      var dest = ENDOSOS[x.id];
      if (dest) tr.className = 'endosado';
      tr.appendChild(el('td', null, '<b>' + dia(x.fecha) + '</b>'));
      tr.appendChild(el('td', null, '<span style="color:var(--suave)">' +
        (x.librador || '—') + '</span>'));
      tr.appendChild(el('td', null, pesos(x.importe)));

      var tdA = el('td');
      var selA = document.createElement('select');
      [['', 'depositar'], ['E', 'endosar']].forEach(function(o){
        var op = document.createElement('option');
        op.value = o[0]; op.textContent = o[1];
        if ((dest ? 'E' : '') === o[0]) op.selected = true;
        selA.appendChild(op);
      });
      selA.onchange = function(){
        if (selA.value === 'E') ENDOSOS[x.id] = (D.droguerias || [''])[0];
        else delete ENDOSOS[x.id];
        guardarEndosos(); pintar();
      };
      tdA.appendChild(selA); tr.appendChild(tdA);

      var tdB = el('td');
      if (dest){
        var selB = document.createElement('select');
        (D.droguerias || []).forEach(function(n){
          var op = document.createElement('option');
          op.value = n; op.textContent = n;
          if (dest === n) op.selected = true;
          selB.appendChild(op);
        });
        selB.onchange = function(){
          ENDOSOS[x.id] = selB.value; guardarEndosos(); pintar();
        };
        tdB.appendChild(selB);
      } else {
        tdB.innerHTML = '<span style="color:var(--tenue)">—</span>';
      }
      tr.appendChild(tdB);

      tr.appendChild(el('td', dest ? 'pos' : '', dest
        ? 'baja deuda con ' + dest
        : '<span style="color:var(--suave)">entra a la caja</span>'));
      tc.appendChild(tr);
    });
    var w2 = el('div', 'envuelve'); w2.appendChild(tc); ch.appendChild(w2);
    out.push(ch);

    // EL CONSEJO: que pasa con la caja y con la deuda segun lo elegido.
    var res = resumenEndosos();
    var deposita = c.cheques_total - res.total;
    var cj = el('div', 'card');
    cj.style.borderLeft = '3px solid var(--azul)';
    var lin = ['<b>Con lo que elegiste:</b>'];
    lin.push('entran <b>' + pesos(deposita) + '</b> a la caja' +
             (res.total ? ' y baja <b>' + pesos(res.total) + '</b> de deuda' : ''));
    if (res.total){
      // CONTRA LO VENCIDO, que es lo unico que cambia algo hoy.
      lin.push('<div style="margin-top:8px;color:var(--suave)">' +
        Object.keys(res.por).map(function(n){
          var b = bajaVencido(n, res.por[n]);
          var t = '<b>' + n + '</b>: baja ' + pesos(b.vencido) + ' de lo VENCIDO';
          if (b.queda !== null) t += ', que queda en ' + pesos(b.queda);
          if (b.resto > 0.5) t += '. Los otros ' + pesos(b.resto) +
            ' van contra lo que todavia no vencio.';
          return t;
        }).join('<br>') + '</div>');
    }
    // ESTA LINEA ESTABA MAL Y ADEMAS NO SE ENTENDIA.
    //
    // la dirección (07/09/2026) marco: "explicame que quiere decir esa linea porque
    // no entiendo". Decia "faltan $1.066.774.053" justo despues de decir que
    // el endoso bajaba $191.597.425 de deuda -- y no lo restaba.
    //
    // Lo vencido se cubre de DOS formas: depositando cheques (entra plata para
    // pagarlo) y endosando (baja la deuda directamente). Contar solo el
    // deposito hacia parecer que el endoso no servia para nada.
    var venc = d.kpis.vencido;
    if (venc > 0){
      var cubierto = deposita + res.total;
      var falta = venc - cubierto;
      var det = 'Lo vencido son <b>' + pesos(venc) + '</b>. Contra eso van los ' +
        pesos(deposita) + ' que depositas' +
        (res.total ? ' mas los ' + pesos(res.total) + ' que endosas' : '') + '.';
      lin.push('<div style="margin-top:12px;padding-top:10px;' +
        'border-top:1px solid var(--linea)">' + det + '<br>' + (falta <= 0
          ? '<span class="pos"><b>Alcanza para cubrirlo todo</b>' +
            (falta < 0 ? ', y sobran ' + pesos(-falta) : '') + '.</span>'
          : '<span class="neg"><b>Faltan ' + pesos(falta) + '</b> para cubrirlo. ' +
            'Ese resto sigue vencido y suma atraso.</span>') + '</div>');
    }
    cj.innerHTML = lin.join(' ');
    if (res.total){
      var b = el('button', 'mini', 'Volver a empezar');
      b.style.marginTop = '12px';
      b.onclick = function(){ ENDOSOS = {}; guardarEndosos(); pintar(); };
      cj.appendChild(b);
    }
    out.push(cj);
  }

  if (c.cheques_sin_unidad){
    var av = el('div', 'card');
    av.style.borderLeft = '3px solid var(--amarillo)';
    av.innerHTML = 'Este export no dice de que empresa es cada cheque, asi que solo se ' +
      'muestran en la vista del grupo.';
    out.push(av);
  }
  return out;
}

function verProyeccion(){
  var d = actual(), out = [];
  // EL ESCENARIO "Y ADEMAS LE PAGO A LA OTRA EMPRESA DEL GRUPO".
  //
  // la dirección: "acordate de sumar el boton de MAGA con pago a Speed y Speed con
  // pago a MAGA". Es el escenario 3 de su Posicion Consolidada, y mide cuanto
  // le esta financiando una empresa a la otra -- hoy MAGA solo transfiere
  // cuando Speed necesita cubrir cheques.
  //
  // Va como interruptor y no como solapa aparte porque es la MISMA proyeccion
  // con una linea mas: verlas al lado hace evidente el salto.
  var p = (CON_IC && d.proyeccion_ic) ? d.proyeccion_ic : d.proyeccion;
  if (p.error || !p.dias.length){
    out.push(el('div', 'card', 'No se pudo proyectar: ' + (p.error || 'faltan datos.')));
    return out;
  }
  var hasta = p.dias[Math.min(VENTANA, p.dias.length) - 1].fecha;

  // Un item cuenta si su grupo no esta pateado y el item no esta destildado.
  function pateado(it){
    return PATEADO[it.grupo] || SUELTO[it.id];
  }
  // Cuanto sale de verdad por este item: 0 si se patea, el parcial si se
  // cargo uno, el total si no.
  function saleDe(it){
    if (pateado(it)) return 0;
    var pa = PARCIAL[it.id];
    return pa === undefined ? it.monto : pa;
  }
  function armar(){
    var porDia = {};
    (p.items || []).forEach(function(it){
      if (it.fecha > hasta) return;
      porDia[it.fecha] = (porDia[it.fecha] || 0) + saleDe(it);
    });
    var caja = p.caja_inicial, curva = [];
    for (var i = 0; i < Math.min(VENTANA, p.dias.length); i++){
      var x = p.dias[i];
      var sale = porDia[x.fecha] || 0;
      caja += x.entra - sale;
      curva.push({fecha: x.fecha, caja: caja, entra: x.entra, sale: sale});
    }
    return curva;
  }
  var curva = armar();
  var critico = null;
  for (var i = 0; i < curva.length; i++) if (curva[i].caja < 0){ critico = curva[i]; break; }
  var minimo = Math.min.apply(null, curva.map(function(x){ return x.caja; }));

  // EL CONSEJO PRIMERO, arriba de todo.
  //
  // Un tablero contesta "el 14/09 quedas en rojo". Eso ya lo tiene cualquiera.
  // Lo que se paga es la respuesta siguiente: "y que hago". Por eso el plan va
  // arriba y los tildes abajo -- primero la propuesta, despues el detalle para
  // el que quiera discutirla.
  var plan = (d.planes || {})[String(VENTANA)] ||
             (d.planes || {})[String(cercana(Object.keys(d.planes || {}), VENTANA))];

  // MODO STOCK (NAVAR): lo vencido no esta en la curva, asi que "que pago
  // pateo para llegar" no tiene sentido. La pregunta es la inversa: con la
  // caja libre que deja lo comprometido, cuanto del vencido se puede pagar y
  // a quien primero. Ver dashboard/datos.py capacidad_de_pago().
  if (p.modo === 'stock' && d.capacidad){
    var cap = d.capacidad[String(VENTANA)] ||
              d.capacidad[String(cercana(Object.keys(d.capacidad), VENTANA))];
    var cc0 = el('div', 'card');
    cc0.style.borderLeft = '3px solid ' + (cap.libre > 0 ? 'var(--verde)' : 'var(--rojo)');
    cc0.appendChild(el('div', null,
      '<span style="font-size:11.5px;text-transform:uppercase;letter-spacing:.09em;' +
      'font-weight:700;color:var(--tenue)">Cuanto podes pagar en ' + VENTANA + ' dias</span>'));
    var frase;
    if (cap.libre > 0){
      frase = 'Cubriendo todo lo comprometido hasta el ' + dia(hasta) + ', te quedan libres <b>' +
        pesos(cap.libre) + '</b>. Eso alcanza para pagar <b>' + pesos(cap.pagado) +
        '</b> de lo vencido con ' + V.proveedores + '; quedan atrasados <b>' +
        pesos(cap.queda_vencido) + '</b>.';
    } else {
      frase = 'Con lo comprometido hasta el ' + dia(hasta) + ' la caja queda en <b>' +
        pesos(cap.minimo) + '</b> el ' + dia(cap.dia_minimo) + ': <b>no hay caja libre</b> para ' +
        'pagar vencido sin postergar algo de lo que viene. El atraso con ' + V.proveedores +
        ' (' + pesos(cap.vencido_proveedores) + ') sigue creciendo.';
      // La caja es negativa: lo unico "libre" es lo que queda de los acuerdos de
      // descubierto. Se dice con nombre, para que no parezca plata que no existe.
      if (d.deuda_bancaria && d.deuda_bancaria.descubierto_acordado > 0){
        frase += ' Lo que queda sin usar de los acuerdos de descubierto es <b>' +
          pesos(d.deuda_bancaria.margen_descubierto) + '</b>: ese es el margen real.';
      }
    }
    cc0.appendChild(el('div', null, '<div style="font-size:16px;font-weight:650;margin:8px 0 4px">' +
      frase + '</div>'));
    if (cap.paga && cap.paga.length){
      // Los primeros ocho con nombre; el resto en una linea. Pagar "por atraso"
      // con 88 proveedores da una cola larga de deudas chicas y viejas: se ven
      // las que abren la lista y cuanto suma el resto, no las 40 filas.
      var tq = el('table');
      tq.style.marginTop = '10px';
      var TOPE = 8, resto = cap.paga.slice(TOPE), restoM = 0;
      resto.forEach(function(x){ restoM += x.monto; });
      cap.paga.slice(0, TOPE).forEach(function(x, n){
        var tr = el('tr');
        tr.appendChild(el('td', null, '<b>' + (n + 1) + '.</b> ' + x.nombre +
          '<div class="resumen">' + sem(x.atraso) + ' de atraso · debe ' + pesos(x.vencido) +
          (x.completo ? '' : ' · pago parcial') + '</div>'));
        tr.appendChild(el('td', 'pos', pesos(x.monto)));
        tq.appendChild(tr);
      });
      if (resto.length){
        var trr = el('tr');
        trr.appendChild(el('td', null, '<span style="color:var(--suave)">y ' + resto.length +
          ' ' + V.proveedores + ' mas, siguiendo el orden de atraso</span>'));
        trr.appendChild(el('td', 'pos', pesos(restoM)));
        tq.appendChild(trr);
      }
      var wq = el('div', 'envuelve'); wq.appendChild(tq); cc0.appendChild(wq);
    }
    var vt = cap.vencido_por_tipo || {};
    cc0.appendChild(el('p', 'nota', 'Lo vencido <b>no esta en la curva</b>: es un stock de ' +
      pesos(cap.vencido_total) + ' (' + V.proveedores + ' ' + pesos(vt.proveedores || 0) +
      (vt.impuestos ? ' · ARCA ' + pesos(vt.impuestos) : '') +
      (vt.bancos ? ' · bancos ' + pesos(vt.bancos) : '') +
      '). Se paga con la caja libre, en orden de atraso; lo que no se paga sigue atrasado.'));
    out.push(cc0);

    // LA DEUDA CON LOS BANCOS, como stock. Es lo que pidio la dirección (17/09): para
    // atras, un numero por concepto que NO toca la caja de hoy; lo que si entra
    // en la curva son las cuotas con fecha. Aca se ve cuanto se debe, a quien,
    // que ya vencio, que vence en 30 dias y como esta la situacion BCRA.
    if (d.deuda_bancaria){
      var db = d.deuda_bancaria;
      var cdb = el('div', 'card');
      cdb.style.borderLeft = '3px solid ' + (db.vencido > 0 ? 'var(--rojo)' : 'var(--tenue)');
      cdb.appendChild(el('div', null,
        '<span style="font-size:11.5px;text-transform:uppercase;letter-spacing:.09em;' +
        'font-weight:700;color:var(--tenue)">Lo que se debe a los bancos</span>'));
      cdb.appendChild(el('div', null, '<div style="font-size:16px;font-weight:650;margin:8px 0 4px">' +
        'Prestamos, tarjetas y descuento de cheques: <b>' + pesos(db.total) + '</b>. ' +
        (db.vencido > 0 ? 'Cuotas ya vencidas e impagas: <b>' + pesos(db.vencido) + '</b>. ' : '') +
        'Vencen en los proximos 30 dias: <b>' + pesos(db.en_30) + '</b>' +
        (db.en_90 ? ' (en 90 dias, ' + pesos(db.en_90) + ')' : '') + '.' +
        (db.situacion_peor >= 2 ? ' Situacion BCRA mas alta informada: <b>' + db.situacion_peor + '</b>.' : '') +
        '</div>'));
      var tdb = el('table');
      tdb.style.marginTop = '10px';
      var hdb = el('tr');
      ['Banco', 'Deuda', 'Vencido', 'En 30 dias', 'Descubierto usado / acordado', 'Sit. BCRA'].forEach(function(h, i){
        hdb.appendChild(el('th', i > 0 ? 'num' : null, h));
      });
      tdb.appendChild(hdb);
      db.por_banco.forEach(function(b){
        var tr = el('tr');
        tr.appendChild(el('td', null, '<b>' + b.banco + '</b>' +
          (b.faltan && b.faltan.length ? '<div class="resumen">sin importe: ' + b.faltan.join(', ') + '</div>' : '') +
          (b.estimados && b.estimados.length ? '<div class="resumen">cuota estimada: ' + b.estimados.join(', ') + '</div>' : '')));
        tr.appendChild(el('td', 'num', pesos(b.deuda)));
        tr.appendChild(el('td', 'num' + (b.vencido > 0 ? ' neg' : ''), b.vencido > 0 ? pesos(b.vencido) : '—'));
        tr.appendChild(el('td', 'num', b.en_30 > 0 ? pesos(b.en_30) : '—'));
        tr.appendChild(el('td', 'num', (b.descubierto_usado > 0 ? pesos(b.descubierto_usado) : '—') +
          (b.descubierto_acordado > 0 ? ' / ' + pesos(b.descubierto_acordado) : (b.descubierto_usado > 0 ? ' / sin acuerdo informado' : ''))));
        tr.appendChild(el('td', 'num' + (b.situacion >= 3 ? ' neg' : ''), b.situacion ? String(b.situacion) : '—'));
        tdb.appendChild(tr);
      });
      var wdb = el('div', 'envuelve'); wdb.appendChild(tdb); cdb.appendChild(wdb);
      cdb.appendChild(el('p', 'nota', 'La deuda es un <b>stock</b>: no esta en la curva de caja. Lo que si esta ' +
        'son las cuotas con fecha (cada una el dia que vence). Los descubiertos no se suman: lo usado ya es ' +
        'el saldo negativo de cada cuenta, que esta en la caja de hoy. Fuente: mapa de deuda del ' +
        'cliente cruzado con los extractos.'));
      cdb.appendChild(detalleDebito("bancos"));
      out.push(cdb);
    }
    if (d.deuda_impositiva_debito && d.deuda_impositiva_debito.length){
      var cdi = el("div", "card");
      cdi.appendChild(el("h2", null, "Obligaciones impositivas"));
      cdi.appendChild(detalleDebito("impuestos"));
      out.push(cdi);
    }
    plan = null;
  }
  if (plan && plan.frase){
    var col = plan.hace_falta ? (plan.alcanza ? 'var(--verde)' : 'var(--rojo)')
                              : 'var(--verde)';
    var cc = el('div', 'card');
    cc.style.borderLeft = '3px solid ' + col;
    cc.appendChild(el('div', null,
      '<span style="font-size:11.5px;text-transform:uppercase;letter-spacing:.09em;' +
      'font-weight:700;color:var(--tenue)">Que hago para llegar</span>'));
    cc.appendChild(el('div', null, '<div style="font-size:16px;font-weight:650;' +
      'margin:8px 0 4px">' + plan.frase + '</div>'));
    if (plan.pasos && plan.pasos.length){
      var tp = el('table');
      tp.style.marginTop = '10px';
      plan.pasos.forEach(function(p, n){
        var tr = el('tr');
        tr.appendChild(el('td', null, '<b>' + (n + 1) + '.</b> correr el pago del <b>' +
          dia(p.fecha) + '</b><br><span style="color:var(--suave)">' + p.concepto +
          '</span><div class="resumen">' + (p.motivo || '') + '</div>'));
        tr.appendChild(el('td', 'pos', pesos(p.monto)));
        tp.appendChild(tr);
      });
      var we = el('div', 'envuelve'); we.appendChild(tp); cc.appendChild(we);
    }
    if (plan.costo && plan.costo.length){
      cc.appendChild(el('div', null, '<div style="margin-top:14px;font-size:13.5px">' +
        '<b>Lo que cuesta:</b> ' + plan.costo.map(function(c){
          if (c.tipo !== 'drogueria') return c.quien + ' ' + pesos(c.monto);
          var t = '<b>' + c.quien + '</b> ' + pesos(c.monto);
          if (c.tolerancia_semanas) t += ' <span style="color:var(--tenue)">(aguanta ' +
            c.tolerancia_semanas + ' semanas)</span>';
          return t;
        }).join(' · ') + '</div>'));
    }
    if (plan.intocable && plan.intocable.length){
      cc.appendChild(el('p', 'nota', 'No se propone tocar: ' +
        plan.intocable.map(function(i){ return '<b>' + i.grupo + '</b> — ' + i.por_que; })
                      .join(' · ')));
    }
    out.push(cc);
  }

  // El interruptor del pago entre empresas, arriba del timeline.
  // EL BOTON DICE EN QUE DIRECCION VA LA PLATA.
  //
  // la dirección (07/09/2026): "en el selector de Speed sale como si Speed le
  // tendria que pagar a MAGA, cuando en realidad MAGA le debe a Speed. Y ese
  // boton sumalo en MAGA tambien: en Speed 'si te paga MAGA' y en MAGA 'si le
  // pago a Speed'".
  //
  // La direccion no se puede inferir del bloque donde esta cargada la fila --
  // esta en el de deuda de Speed y sin embargo es plata que Speed RECIBE. Se
  // deduce de si el escenario le suma ingresos o egresos a esta empresa.
  var pic = d.proyeccion_ic || {};
  var masEntra = (pic.total_entra || 0) - (d.proyeccion.total_entra || 0);
  var masSale = (pic.total_sale || 0) - (d.proyeccion.total_sale || 0);
  if (Math.abs(masEntra) > 1 || Math.abs(masSale) > 1){
    var cobra = masEntra > 1;
    var otra = (pic.items || []).filter(function(i){ return i.grupo === 'intercompany'; })
                                .map(function(i){ return i.concepto.replace('Pago a ', ''); })[0]
               || (UNIDAD === 'MAGA' ? 'Speedmed' : 'MAGA');
    var cic = el('div', 'card');
    cic.style.borderLeft = '3px solid var(--violeta)';
    var lab = document.createElement('label');
    lab.style.cssText = 'display:flex;gap:9px;align-items:flex-start;cursor:pointer';
    var cbic = document.createElement('input');
    cbic.type = 'checkbox'; cbic.checked = CON_IC;
    cbic.onchange = function(){ CON_IC = cbic.checked; pintar(); };
    lab.appendChild(cbic);
    lab.appendChild(el('span', null,
      '<b>' + (cobra ? 'Contar que te paga ' + otra
                     : 'Contar que le pagas a ' + otra) + '</b> ' +
      '<span style="color:var(--tenue)">' +
      (cobra ? '+' : '−') + pesos(cobra ? masEntra : masSale) + '</span>' +
      '<div class="resumen">Hoy no se maneja como un proveedor: se transfiere ' +
      'cuando hace falta cubrir cheques. Tildarlo muestra como quedarias si ' +
      'fuera una obligacion mas. En la vista del grupo no cambia nada, porque ' +
      'la plata no sale del grupo.</div>'));
    cic.appendChild(lab);
    out.push(cic);
  }

  var ct = el('div', 'card');
  ct.appendChild(el('div', null,
    '<b>Horizonte:</b> <span id="vent">' + VENTANA + ' dias</span> ' +
    '<span style="color:var(--tenue);font-size:12.5px">— hasta el ' + dia(hasta) +
    '. A 45 dias todavia no hay nada cerrado: cuanto mas lejos, menos dato real ' +
    'y mas estimacion.</span>'));
  var sl = el('input'); sl.type = 'range'; sl.min = 1; sl.max = p.dias.length;
  sl.value = VENTANA; sl.style.width = '100%'; sl.style.marginTop = '10px';
  sl.oninput = function(){
    VENTANA = Number(sl.value);
    document.getElementById('vent').textContent = VENTANA + ' dias';
    pintar();
  };
  ct.appendChild(sl);
  out.push(ct);

  var k = el('div', 'kpis');
  var fin = curva.length ? curva[curva.length - 1].caja : p.caja_inicial;
  [['Caja al arrancar', pesos(p.caja_inicial, true), p.desde, ''],
   ['El dia mas bajo', pesos(minimo, true),
     minimo < 0 ? 'la caja se da vuelta' : 'nunca toca cero', minimo < 0 ? 'malo' : 'bien'],
   ['Caja a los ' + VENTANA + ' dias', pesos(fin, true), dia(hasta),
     fin >= 0 ? 'bien' : 'malo']
  ].forEach(function(x){
    var t = el('div', 'card kpi ' + x[3]);
    t.appendChild(el('div', 'et', x[0]));
    t.appendChild(el('div', 'n', x[1]));
    t.appendChild(el('div', 'pie', x[2]));
    k.appendChild(t);
  });
  out.push(k);

  var hayPateo = Object.keys(PATEADO).length || Object.keys(SUELTO).length ||
               Object.keys(PARCIAL).length;
  if (critico){
    var av = el('div', 'card');
    av.style.borderLeft = '3px solid var(--rojo)';
    av.innerHTML = '<b style="font-size:16px">El dia critico es el ' + dia(critico.fecha) +
      '.</b><br><span style="color:var(--suave)">Ahi la caja queda en ' +
      pesos(critico.caja) + '. Un dueno no mira el final del periodo: mira el dia que ' +
      'se queda corto, y ese dia tiene fecha.</span>';
    out.push(av);
  } else if (hayPateo){
    var ok = el('div', 'card');
    ok.style.borderLeft = '3px solid var(--verde)';
    var pat = (p.items || []).filter(function(it){ return it.fecha <= hasta; })
                             .reduce(function(a, x){ return a + (x.monto - saleDe(x)); }, 0);
    ok.innerHTML = '<b>Asi llegas.</b> Corriendo ' + pesos(pat) + ' la caja no se da ' +
      'vuelta en ' + VENTANA + ' dias. La deuda no desaparece: se patea, y el atraso ' +
      'se acumula.';
    out.push(ok);
  }

  var cg = el('div', 'card');
  cg.appendChild(curvaCaja(curva, critico));
  var sale = curva.reduce(function(a, x){ return a + x.sale; }, 0);
  var entra = curva.reduce(function(a, x){ return a + x.entra; }, 0);
  cg.appendChild(el('p', 'nota',
    '<b>Que toma:</b> el comportamiento de los ultimos meses — cada tipo de movimiento ' +
    'se repite con su propio ritmo. La deuda con ' + V.proveedores + ' NO se estima: ya tiene ' +
    'fecha y monto en la planilla, por eso sus resumenes salen sin la marca de ' +
    '“estimado”. En ' + VENTANA + ' dias entran ' + pesos(entra) + ' y salen ' +
    pesos(sale) + '.'));
  out.push(cg);

  // LA CAJA PRIMERO, LOS INTERRUPTORES DESPUES.
  //
  // la dirección (07/09/2026): "en la parte de proyeccion deberia ser al reves, el
  // tema de la caja y demas arriba de todo, para luego abajo ver que se puede
  // patear y se vaya acomodando solo".
  //
  // Tiene razon y es como se usa: primero se mira como queda, y si no cierra
  // se baja a tocar. Al reves obligaba a leer una lista de opciones antes de
  // saber si hacia falta abrirla.
  var cp = el('div', 'card');
  cp.appendChild(el('div', null, '<b>Que puedo patear para llegar</b>'));
  cp.appendChild(el('p', 'nota', 'Tildar un grupo entero, o abrirlo y elegir de a uno. ' +
    'Asi se decide de verdad: no se patea “' + V.proveedores + '”, se patea el resumen de ' +
    'una y se paga el de la otra.'));
  var lista = el('div');
  lista.style.marginTop = '12px';

  p.grupos.forEach(function(g){
    // El grupo 'droguerias' del motor se rotula con la palabra del cliente.
    if (g.id === 'droguerias') g.nombre = 'Pago a ' + V.proveedores;
    var items = (p.items || []).filter(function(it){
      return it.grupo === g.id && it.fecha <= hasta;
    });
    if (!items.length) return;
    var total = items.reduce(function(a, x){ return a + x.monto; }, 0);
    var pateados = items.reduce(function(a, x){ return a + (x.monto - saleDe(x)); }, 0);

    var cab = el('div');
    cab.style.cssText = 'display:flex;gap:10px;align-items:baseline;flex:1;padding:7px 0';
    var cb = document.createElement('input');
    cb.type = 'checkbox'; cb.checked = !!PATEADO[g.id];
    cb.style.marginRight = '2px';
    cb.onclick = function(ev){
      ev.stopPropagation();
      if (cb.checked) PATEADO[g.id] = 1; else delete PATEADO[g.id];
      pintar();
    };
    cab.appendChild(cb);
    cab.appendChild(el('span', null, '<b>' + g.nombre + '</b> ' +
      '<span style="color:var(--tenue);font-size:12.5px">' + items.length + ' ' +
      (items.length === 1 ? 'movimiento' : 'movimientos') + ' · ' + pesos(total) +
      (pateados ? ' · <span class="pos">se patea ' + pesos(pateados) + '</span>' : '') +
      '</span>' + (g.nota ? '<div class="resumen">' + g.nota + '</div>' : '')));

    var det = el('table');
    items.forEach(function(it){
      var tr = el('tr');
      var td1 = el('td');
      var c2 = document.createElement('input');
      c2.type = 'checkbox';
      c2.checked = !pateado(it);
      c2.disabled = !!PATEADO[g.id];
      c2.onchange = function(){
        if (c2.checked) delete SUELTO[it.id]; else SUELTO[it.id] = 1;
        pintar();
      };
      td1.appendChild(c2);
      td1.appendChild(el('span', null, ' ' + dia(it.fecha) + '  ' +
        '<span style="color:var(--suave)">' + it.concepto + '</span>' +
        (it.estimado ? ' <span class="chip medio">estimado</span>' : '')));
      tr.appendChild(td1);

      // PAGAR UNA PARTE, que es lo que se hace de verdad.
      //
      // la dirección: "montos parciales tambien". Tiene razon y cambia el modelo:
      // hasta aca un resumen se pagaba entero o se pateaba entero, y en la
      // realidad a Suizo le pagas 200 de los 500. Un interruptor de todo o
      // nada obliga a elegir entre dos cosas que nadie hace.
      //
      // Solo tiene sentido en lo DIVISIBLE. A una drogueria le podes transferir
      // una parte; un cheque es todo o nada -- o lo cubris o rebota -- y un
      // sueldo tampoco se paga por mitades.
      var tdM = el('td');
      if (it.grupo === 'droguerias' && !PATEADO[g.id] && !SUELTO[it.id]){
        var pagado = PARCIAL[it.id];
        var inp = document.createElement('input');
        inp.type = 'text';
        inp.value = pagado !== undefined ? Math.round(pagado).toLocaleString('es-AR')
                                         : Math.round(it.monto).toLocaleString('es-AR');
        inp.style.cssText = 'width:150px;font-size:13px;padding:5px 8px;text-align:right';
        inp.onchange = function(){
          var n = Number(String(inp.value).replace(/[^\d]/g, '')) || 0;
          n = Math.max(0, Math.min(n, it.monto));
          if (Math.abs(n - it.monto) < 1) delete PARCIAL[it.id];
          else PARCIAL[it.id] = n;
          pintar();
        };
        tdM.appendChild(inp);
        if (pagado !== undefined){
          tdM.appendChild(el('div', 'resumen', 'quedan ' + pesos(it.monto - pagado) +
                             ' sin pagar'));
        }
      } else {
        tdM.className = pateado(it) ? 'pos' : '';
        tdM.innerHTML = pesos(it.monto);
      }
      tr.appendChild(tdM);
      det.appendChild(tr);
    });
    lista.appendChild(desplegable('g_' + g.id, cab, det));
  });
  cp.appendChild(lista);
  out.push(cp);

  return out;
}

function verHallazgos(){
  var out = [];

  // LO QUE DIJIMOS LA VEZ PASADA, arriba de todo.
  //
  // Es el activo de una asesoria recurrente. La frase que la sostiene no es
  // "acertamos el 83% de los movimientos": es "el mes pasado te dije que el 14
  // quedabas corto, quedaste el 16". Sin esto, cada visita arranca de cero y lo
  // que se cobra es una foto, no una relacion.
  var mem = D.memoria_tablero || {};
  var cm = el('div', 'card');
  cm.style.borderLeft = '3px solid var(--violeta)';
  cm.appendChild(el('div', null,
    '<span style="font-size:11.5px;text-transform:uppercase;letter-spacing:.09em;' +
    'font-weight:700;color:var(--tenue)">Lo que te dijimos la vez pasada</span>'));
  if (mem.hay && (mem.frases || []).length){
    var u = el('ul', 'limpia');
    u.style.marginTop = '10px';
    mem.frases.forEach(function(f){ u.appendChild(el('li', null, f)); });
    cm.appendChild(u);
    cm.appendChild(el('p', 'nota', 'Se compara contra la proyeccion guardada el ' +
      mem.desde + '. Solo se juzga lo que ya vencio: una proyeccion a 45 dias ' +
      'mirada a los 10 no se cumplio ni se incumplio.'));
  } else {
    cm.appendChild(el('p', 'nota', (mem.por_que || 'sin memoria todavia') +
      '. Se guarda una foto cada vez que se actualiza el tablero; desde la ' +
      'segunda, aca aparece si le acertamos.'));
  }
  out.push(cm);
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
  (D.faltantes || []).forEach(function(f){ u.appendChild(el('li', null, f)); });
  if (V.no_sabe_cobranza) u.appendChild(el('li', null, V.no_sabe_cobranza));
  if (d.puente.cobranza_vencida) u.appendChild(el('li', null,
    '<b>Si entra la cobranza que ya venció</b> (' + pesos(d.puente.cobranza_vencida) +
    '). No está contada en ningún número de acá.'));
  if (d.puente.cheques) u.appendChild(el('li', null,
    '<b>Qué se hace con los cheques en cartera</b> (' + pesos(d.puente.cheques) +
    '): se decide uno por uno al llegar la fecha.'));
  // Lo que solo aplica a un cliente vive en su catalogo (vocabulario.no_sabe_extra),
  // no aca: el 17/09/2026 el tablero de NAVAR decia "cuanto le debe MAGA a Speedmed".
  if (V.no_sabe_extra) u.appendChild(el('li', null, V.no_sabe_extra));
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
             proyeccion: verProyeccion, hallazgos: verHallazgos};

// El detalle ya viene escrito en el HTML. Al cambiar de empresa copiamos el suyo.
function detalleDebito(tipo){
  var fuente = document.getElementById('debito-' + D.unidades.indexOf(UNIDAD) + '-' + tipo);
  var copia = fuente ? fuente.cloneNode(true) : el('div');
  copia.removeAttribute('id');
  return copia;
}

function pintar(){
  document.querySelectorAll('[data-unidad]').forEach(function(b){
    b.setAttribute('aria-pressed', b.dataset.unidad === UNIDAD);
  });
  document.querySelectorAll('[data-capa]').forEach(function(b){
    b.setAttribute('aria-selected', b.dataset.capa === SOLAPA);
  });
  var t = document.querySelector('[data-capa="' + SOLAPA + '"]');
  if (t) document.getElementById('titulo').textContent = t.textContent.trim();
  var cont = document.getElementById('capa');
  cont.innerHTML = '';
  CAPAS[SOLAPA]().forEach(function(n){ cont.appendChild(n); });
  document.getElementById('debitos-sin-script').hidden = true;
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

# La solapa "Retiro" se saco: la dirección, 06/09/2026, "no tiene sentido".
# La pregunta que contestaba -- cuanto puedo sacar -- se contesta mirando la
# deuda vencida y la caja, que estan en Posicion. Una solapa entera para
# repetir eso con otra aritmetica agregaba una respuesta mas para conciliar.
CAPAS = [("posicion", "Posición"), ("pagar", "A quién pagar"),
         ("cobrar", "A cobrar"), ("proyeccion", "Proyección"),
         ("hallazgos", "Hallazgos")]


# Iconos de la navegacion, dibujados a mano (un trazo, misma grosura). Sin emojis.
ICONOS = {
    "posicion": '<rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/>'
                '<rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/>',
    "pagar": '<path d="M4 7h16M4 12h11M4 17h7"/>',
    "cobrar": '<path d="M12 20V5M6 11l6-6 6 6"/>',
    "proyeccion": '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
    "hallazgos": '<path d="M12 3l9.5 17h-19z"/><path d="M12 10v4M12 17h.01"/>',
}


def _cuando(paquete):
    """'2026-09-16T06:21:57' -> '16/09/2026 06:21'. Es lo que dice la esquina del tablero."""
    g = str(paquete.get("generado") or paquete.get("fecha") or "")
    try:
        d = datetime.datetime.fromisoformat(g[:19])
        return d.strftime("%d/%m/%Y %H:%M") if "T" in g else d.strftime("%d/%m/%Y")
    except ValueError:
        return g


def _detalle_debito(grupos, impuestos=False):
    """HTML listo para leer aun sin JavaScript; Enter y Espacio abren el detalle."""
    from html import escape
    def pesos(n):
        return "$ " + format(n, ",.2f").replace(",", "X").replace(".", ",").replace("X", ".")
    def fecha(f):
        try:
            return datetime.date.fromisoformat(f).strftime("%d/%m/%Y")
        except ValueError:
            return f or "Sin fecha informada"
    partes = ['<p class="nota">' + (
        'Impuestos aparte: no integran el total bancario. Los planes con débito en CBU '
        'se incluyen en Sale sí o sí cuando está informado.' if impuestos else
        'Los tres totales reparten el capital adeudado, sin descubiertos. Las cuotas '
        'pueden incluir intereses: se muestran aparte y no se suman al capital.') +
        ' Sale sí o sí significa débito automático si hay fondos, no pago confirmado. '
        'Sin definir requiere completar el dato. En 30 días incluye hoy y excluye el día 30.</p>']
    for g in grupos:
        partes.append('<details class="debito"><summary><b>%s</b> · '
                      '<span class="num">%s</span></summary>' % (escape(g['nombre']), pesos(g['total'])))
        if not g['por_banco']:
            partes.append('<p class="resumen">Sin obligaciones cargadas en este grupo.</p>')
        for b in g['por_banco']:
            partes.append('<h3>%s</h3><p class="resumen">%s: %s · Vencido: '
                          '<span class="neg">%s</span> · En 30 días: %s</p>' % (
                escape(b['banco']), 'Deuda' if impuestos else 'Capital', pesos(b['total']),
                pesos(b['vencido']), pesos(b['en_30'])))
            partes.append('<div class="envuelve"><table><thead><tr><th>Concepto</th><th>Tipo</th>'
                          '<th>Fecha</th><th class="num">Importe</th></tr></thead><tbody>')
            for x in b['items']:
                nota = ' · importe sin informar' if x['falta_importe'] else (' · estimado' if x['estimado'] else '')
                partes.append('<tr><td>%s%s</td><td>%s</td><td>%s</td><td class="num">%s</td></tr>' % (
                    escape(x['concepto']), nota, escape(x['clase']), escape(fecha(x['fecha'])), pesos(x['importe'])))
            partes.append('</tbody></table></div>')
        partes.append('</details>')
    return ''.join(partes)


def render(paquete):
    import html as _h
    e = lambda t: _h.escape(str(t if t is not None else ""))

    H = []
    A = H.append
    A('<meta charset="utf-8">')
    A('<meta name="viewport" content="width=device-width,initial-scale=1">')
    A('<title>%s — finauto</title>' % e(paquete["cliente"]))
    A('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,500;6..72,600'
      '&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap">')
    A('<style>%s</style>' % CSS)
    A('<div class="app">')

    # ---- la barra lateral: marca, cliente, empresa, solapas, pie
    A('<aside class="lado">')
    A('<div class="logo"><i></i>finauto</div>')
    A('<hr>')
    A('<div class="cliente">CLIENTE<b>%s</b></div>' % e(paquete["cliente"]))
    A('<div class="pills">')
    for u in paquete["unidades"]:
        A('<button class="pill" data-unidad="%s">%s</button>'
          % (e(u), e("GRUPO" if u == "GRUPO" else u)))
    A('</div>')
    A('<nav class="tabs" role="tablist">')
    for cid, nom in CAPAS:
        A('<button class="tab" role="tab" data-capa="%s"><svg viewBox="0 0 24 24">%s</svg>%s</button>'
          % (cid, ICONOS.get(cid, ""), e(nom)))
    A('</nav>')
    A('<div class="pie">datos del cash al <b>%s</b><br>ventana de decisión · <b>7 días</b></div>'
      % e(paquete["fecha"]))
    A('</aside>')

    # ---- el contenido: titulo de la solapa (lo pone pintar()), estado, y la capa
    A('<main class="wrap">')
    A('<div class="cab"><div><h1 id="titulo">Posición</h1>'
      '<p class="sub">Tablero de decisión · %s</p></div>' % e(paquete["cliente"]))
    A('<div class="meta"><i></i>generado %s</div></div>' % e(_cuando(paquete)))
    A('<div id="capa"></div>')
    # Si el script no corre, quedan las empresas y sus detalles a la vista.
    A('<section id="debitos-sin-script">')
    for i, u in enumerate(paquete["unidades"]):
        d = paquete["datos"][u]
        for tipo, titulo, grupos in (
            ("bancos", "Lo que se debe a los bancos", (d.get("deuda_bancaria") or {}).get("por_debito", [])),
            ("impuestos", "Obligaciones impositivas", d.get("deuda_impositiva_debito", []))):
            if grupos:
                A('<section class="card"><h2>%s · %s</h2>' % (e(u), titulo))
                A('<div id="debito-%s-%s">%s</div></section>' %
                  (i, tipo, _detalle_debito(grupos, impuestos=tipo == "impuestos")))
    A('</section>')
    A('</main>')
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
    ap.add_argument("--sin-memoria", action="store_true",
                    help="no guardar la foto de esta corrida")
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

    # SE GUARDA LA FOTO DE LO QUE SE MOSTRO.
    #
    # Antes de escribir el HTML, para que lo que quede registrado sea
    # exactamente lo que el cliente va a ver. Si se guardara despues y algo
    # fallara en el medio, quedaria una promesa que nadie hizo.
    if not args.sin_memoria:
        try:
            from memoria import tablero as MT
            ruta, _ = MT.guardar(args.cliente, paquete)
            print("Foto guardada: %s" % os.path.basename(ruta))
        except Exception as e:
            print("OJO: no se pudo guardar la foto de la memoria (%s)" % e)
    with io.open(salida, "w", encoding="utf-8") as f:
        f.write("<!doctype html>\n<html lang=\"es\">\n")
        f.write(render(paquete))
        f.write("\n</html>")
    print("Listo: %s  (%d KB)" % (salida, os.path.getsize(salida) // 1024))


if __name__ == "__main__":
    main()
