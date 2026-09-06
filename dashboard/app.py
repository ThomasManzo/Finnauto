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
/* TEMA CLARO.
 *
 * Thomas, 06/09/2026: "el color tiene que ser claro de fondo, algo mucho mas
 * limpio, no que parezca que vas a hackear la NASA".
 *
 * Tenia razon y el error era de encuadre: yo lo habia hecho oscuro copiando su
 * tablero interno, que es una herramienta suya. Esto es otra cosa -- se le
 * muestra al dueno de una cadena, se proyecta, se imprime. Ahi lo oscuro se ve
 * a la defensiva y, en un proyector, directamente no se lee.
 */
:root{
  --fondo:#F6F8F7; --panel:#FFFFFF; --panel2:#F1F4F3; --linea:#E2E8E5;
  --tinta:#152119; --suave:#5C6B63; --tenue:#8B978F;
  --azul:#1B6FD6; --verde:#0F8A57; --rojo:#C0392B; --naranja:#D97A1F;
  --violeta:#7A5AF0; --amarillo:#B07D08;
  --verde-piso:#E6F5EE; --rojo-piso:#FBECEA; --ambar-piso:#FCF3DF;
}
*{box-sizing:border-box}
html,body{margin:0;background:var(--fondo);color:var(--tinta)}
body{font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  -webkit-font-smoothing:antialiased}
.wrap{max-width:1120px;margin:0 auto;padding:26px 20px 90px}
.cab{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap}
h1{font-size:25px;margin:0;letter-spacing:-.02em}
.cab .meta{font-size:12.5px;color:var(--tenue);text-align:right;line-height:1.7}
.sub{color:var(--suave);font-size:13.5px;margin:4px 0 0}
.pills{display:flex;gap:8px;flex-wrap:wrap;margin:20px 0 4px}
.pill{background:var(--panel);border:1px solid var(--linea);color:var(--suave);
  padding:8px 16px;border-radius:9px;cursor:pointer;font-size:14px;font-weight:600;
  font-family:inherit}
.pill:hover{color:var(--tinta);border-color:#C8D3CD}
.pill[aria-pressed="true"]{background:var(--azul);border-color:var(--azul);color:#fff}
.tabs{display:flex;gap:2px;margin:22px 0 18px;border-bottom:1px solid var(--linea);
  overflow-x:auto}
.tab{background:none;border:0;border-bottom:2px solid transparent;color:var(--tenue);
  padding:11px 16px;cursor:pointer;font-size:14px;font-weight:600;white-space:nowrap;
  font-family:inherit}
.tab:hover{color:var(--tinta)}
.tab[aria-selected="true"]{color:var(--azul);border-bottom-color:var(--azul)}
h2{font-size:12px;text-transform:uppercase;letter-spacing:.09em;color:var(--tenue);
  margin:30px 0 12px;font-weight:700}
h2:first-child{margin-top:6px}
.card{background:var(--panel);border:1px solid var(--linea);border-radius:12px;padding:20px;
  box-shadow:0 1px 2px rgba(16,32,24,.04)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}
.kpi .et{font-size:12.5px;color:var(--suave)}
.kpi .n{font-size:27px;font-weight:750;letter-spacing:-.02em;margin:7px 0 3px;
  font-variant-numeric:tabular-nums}
.kpi .pie{font-size:11.5px;color:var(--tenue)}
.kpi.malo{background:var(--rojo-piso);border-color:#EFC9C3}
.kpi.malo .n{color:var(--rojo)}
.kpi.bien .n{color:var(--verde)}
table{width:100%;border-collapse:collapse;font-size:14px}
th{text-align:right;font-size:11px;text-transform:uppercase;letter-spacing:.05em;
  color:var(--tenue);font-weight:700;padding:0 0 10px}
th:first-child,td:first-child{text-align:left}
td{text-align:right;padding:11px 0;border-top:1px solid var(--linea);
  font-variant-numeric:tabular-nums}
tr.tot td{font-weight:700;border-top:2px solid var(--tinta)}
.pos{color:var(--verde)} .neg{color:var(--rojo)}
.chip{display:inline-block;font-size:11px;font-weight:700;padding:3px 9px;border-radius:99px}
.chip.ok{background:var(--verde-piso);color:var(--verde)}
.chip.mal{background:var(--rojo-piso);color:var(--rojo)}
.chip.medio{background:var(--ambar-piso);color:var(--amarillo)}
.barra{height:10px;border-radius:99px;background:var(--azul);min-width:3px}
.nota{font-size:12.5px;color:var(--tenue);margin:12px 0 0}
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
.resumen{font-size:11.5px;color:var(--tenue);margin-top:3px}
.resumen b{color:var(--rojo);font-weight:600}
select{background:var(--panel);border:1px solid var(--linea);color:var(--tinta);
  border-radius:7px;padding:5px 8px;font-family:inherit;font-size:12.5px}
select:focus{outline:none;border-color:var(--azul)}
.endosado{background:var(--verde-piso)}
button.mini{background:var(--panel2);border:1px solid var(--linea);border-radius:7px;
  padding:5px 10px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;
  color:var(--suave)}
button.mini:hover{color:var(--tinta)}
[hidden]{display:none!important}
@media (max-width:760px){.kpis{grid-template-columns:1fr}}
@media print{body{background:#fff}.card{break-inside:avoid;box-shadow:none}}
"""

JS = r"""
// ---------------------------------------------------------------- formato
// Acá NO se calcula plata. Todo viene resuelto de Python (dashboard/datos.py):
// esto solo elige qué mostrar y cómo escribirlo. Ver el docstring de app.py.
// UNA SOLA ESCALA POR TABLA.
//
// ERROR REAL (06/09/2026). Thomas: "queda visualmente feo, si un numero no
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


// ---------------------------------------------------------------- endosos
// El unico estado que el tablero guarda. Es una simulacion del usuario, no un
// dato del negocio: por eso vive en el navegador y no toca el contrato.
var ENDOSOS = {};
// Lo que el usuario esta simulando en la solapa de proyeccion.
var VENTANA = 45, PATEADO = {};
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

// ---------------------------------------------------------------- estado
var UNIDAD = D.unidades[0], SOLAPA = 'posicion', VENTANA = String(D.ventanas[0]);
function actual(){ return D.datos[UNIDAD]; }

// ---------------------------------------------------------------- capas
function verPosicion(){
  var d = actual(), k = d.kpis, out = [];

  // LOS TRES NUMEROS QUE SE MIRAN, Y NADA MAS.
  //
  // Antes habia un cuarto, "margen a 7 dias". Thomas lo saco: "no me gusta, no
  // se entiende que toma". Tenia razon -- era caja + cobros - salidas de una
  // ventana, o sea tres cosas mezcladas en un numero sin unidad clara. Un KPI
  // que hay que explicar no es un KPI.
  var c = el('div', 'kpis');
  [['Caja de hoy', pesos(k.caja, true), k.efectivo_sin_asignar
      ? '+ ' + pesos(k.efectivo_sin_asignar, true) + ' de efectivo del grupo, sin asignar'
      : 'banco + efectivo', ''],
   ['Deuda ya vencida', pesos(k.vencido, true),
      'con droguerias, sin la refi', k.vencido > 0 ? 'malo' : 'bien'],
   ['Vence en los proximos 7 dias', pesos(k.por_vencer, true),
      'todavia no aprieta', '']
  ].forEach(function(x){
    var t = el('div', 'card kpi ' + x[3]);
    t.appendChild(el('div', 'et', x[0]));
    t.appendChild(el('div', 'n', x[1]));
    t.appendChild(el('div', 'pie', x[2]));
    c.appendChild(t);
  });
  out.push(c);

  // La refi va aparte: es obligacion, pero no es una drogueria y no tiene
  // tolerancia de proveedor. Mezclarla con las droguerias infla la deuda que
  // "te puede cortar la compra", que es justo la que decide.
  if (d.refi && (d.refi.vencido || d.refi.por_vencer)){
    var cr = el('div', 'card');
    cr.style.borderLeft = '3px solid var(--violeta)';
    cr.innerHTML = '<b>Refinanciacion</b> — aparte de las droguerias: se puede ' +
      'patear hasta el vencimiento del mes siguiente (2 semanas), y atrasarla no ' +
      'hace que te corten la compra.<br>' +
      '<span style="color:var(--suave)">Vencida: <b>' + pesos(d.refi.vencido) +
      '</b> · por vencer: ' + pesos(d.refi.por_vencer) + '</span>';
    out.push(cr);
  }

  if (d.ingresos_dia && d.ingresos_dia.dias.length){
    out.push(el('h2', null, 'Lo que entra, dia por dia'));
    var ci = el('div', 'card');
    ci.appendChild(leyenda(d.ingresos_dia.fuentes));
    ci.appendChild(barrasApiladas(d.ingresos_dia));
    ci.appendChild(el('p', 'nota', 'El total del mes no dice nada: lo que importa es ' +
      'el RITMO. Un pico de PAMI y treinta dias de mostrador no es lo mismo que un ' +
      'ingreso parejo, aunque sumen igual.'));
    out.push(ci);
  }

  // EN QUE SE VA LA PLATA, CON LAS DROGUERIAS ADENTRO.
  // Antes este grafico salia solo del bloque de egresos, donde la deuda con
  // droguerias NO esta: mostraba en que se va la plata sin el gasto mas grande.
  out.push(el('h2', null, 'En que se va la plata (45 dias)'));
  var cg = el('div', 'card');
  var max = Math.max.apply(null, d.gastos.map(function(g){ return g.monto; })) || 1;
  d.gastos.forEach(function(g){
    var f = el('div');
    f.style.cssText = 'display:grid;grid-template-columns:210px 1fr 120px;gap:12px;' +
                      'align-items:center;margin-bottom:10px';
    f.appendChild(el('div', null, '<span style="color:var(--suave);font-size:13.5px">' +
      g.nombre + '</span>'));
    var b = el('div'), bb = el('div', 'barra');
    bb.style.width = Math.max(2, 100 * g.monto / max) + '%';
    b.appendChild(bb); f.appendChild(b);
    f.appendChild(el('div', null, '<span style="font-variant-numeric:tabular-nums">' +
      pesos(g.monto) + '</span>'));
    cg.appendChild(f);
  });
  cg.appendChild(el('p', 'nota', 'Incluye lo que vence con cada drogueria, no solo ' +
    'los egresos del cashflow. Sin eso faltaria el gasto mas grande que hay.'));
  out.push(cg);

  out.push(el('h2', null, 'Proximas salidas'));
  var cs = el('div', 'card'), ts = el('table');
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
  // Thomas, 06/09/2026: "el atraso que marcaste esta como el orto"; "no
  // pongamos esa tolerancia, no ordenemos por tolerancia, ordenemos por
  // atraso"; "aclaremos que resumen suman esas deudas".
  //
  // Las tres cosas van juntas. La tolerancia era una estimacion NUESTRA y el
  // atraso es un hecho: ordenar por la estimacion escondia el hecho. Y un
  // atraso sin la fecha del resumen del que sale no se puede discutir -- fue
  // exactamente lo que dejo pasar el error de Cofaloza, donde un resto de
  // $1,3M del 31/07 hacia figurar 5,1 semanas en vez de 1,1.
  var c = el('div', 'card'), t = el('table');
  var baja = resumenEndosos().por;
  var hayEndoso = Object.keys(baja).length > 0;
  t.innerHTML = '<tr><th>Drogueria</th><th>Vencido</th><th>Vence pronto</th>' +
                (hayEndoso ? '<th>Endoso</th>' : '') + '<th>Atraso</th></tr>';
  d.proveedores.forEach(function(p){
    var tr = el('tr');
    var det = '<b>' + p.nombre + '</b>';
    if (p.vence_dia) det += '<div class="resumen">vence ' + p.vence_dia + '</div>';
    tr.appendChild(el('td', null, det));

    // Cada monto vencido es un RESUMEN con su fecha.
    var venc = '<span class="' + (p.vencido ? 'neg' : '') + '">' + pesos(p.vencido) + '</span>';
    if (p.resumenes && p.resumenes.length){
      venc += '<div class="resumen">' + p.resumenes.map(function(r){
        return 'resumen del <b>' + dia(r.fecha) + '</b> ' + pesos(r.monto);
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
  var w = el('div', 'envuelve'); w.appendChild(t); c.appendChild(w);
  if (!d.proveedores.length){
    c.appendChild(el('p', 'nota', 'Sin deuda con droguerias en esta empresa.'));
  }

  // Los restos viejos y chicos se muestran, pero no definen el atraso.
  var restos = [];
  d.proveedores.forEach(function(p){
    (p.restos_ignorados || []).forEach(function(r){
      restos.push(p.nombre + ': ' + pesos(r.importe) + ' del ' + dia(r.fecha));
    });
  });
  if (restos.length){
    c.appendChild(el('p', 'nota', 'Hay restos viejos que <b>se siguen debiendo</b> pero ' +
      'no definen el atraso, porque son menos del 5% del vencido con ese proveedor y ' +
      'suelen ser diferencias de imputacion: ' + restos.join(' · ') + '.'));
  }
  c.appendChild(el('p', 'nota', 'Ordenado por <b>atraso</b>: primero el que hace mas ' +
    'que espera. El atraso se mide desde el resumen mas viejo sin pagar.'));
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
        '<div class="resumen">' + f.que_es + '</div>'));
      tr.appendChild(el('td', f.vencido ? 'neg' : '', pesos(f.vencido)));
      tr.appendChild(el('td', null, pesos(f.por_vencer)));
      tr.appendChild(el('td', null, '<b>' + pesos(f.total) + '</b>'));
      t.appendChild(tr);
    });
    var w = el('div', 'envuelve'); w.appendChild(t); cc.appendChild(w);
    cc.appendChild(el('p', 'nota', 'Las obras sociales y PAMI son cuentas a cobrar ' +
      'aunque esten cargadas en el bloque de ingresos: es plata vendida y no cobrada. ' +
      'De esa fuente solo cuenta el futuro, porque ahi la planilla no limpia la celda ' +
      'al cobrar y una fecha pasada ya entro.'));
    out.push(cc);
  }

  // CADA CHEQUE, CON SUS DOS DECISIONES SEPARADAS.
  //
  // Thomas: "habria que sumar una columna mas: la de estado Endosar/depositar
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
      lin.push('<div style="margin-top:8px;color:var(--suave)">' +
        Object.keys(res.por).map(function(n){
          var p0 = (d.proveedores || []).filter(function(q){ return q.nombre === n; })[0];
          var queda = p0 ? Math.max(0, p0.vencido + p0.por_vencer - res.por[n]) : null;
          return '<b>' + n + '</b>: baja ' + pesos(res.por[n]) +
                 (queda !== null ? ', queda en ' + pesos(queda) : '');
        }).join('<br>') + '</div>');
    }
    var venc = d.kpis.vencido;
    if (deposita >= venc && venc > 0){
      lin.push('<div style="margin-top:10px" class="pos">Con eso cubris toda la deuda ' +
               'vencida (' + pesos(venc) + ').</div>');
    } else if (venc > 0){
      lin.push('<div style="margin-top:10px" class="neg">Depositando eso NO alcanza para ' +
               'cubrir lo vencido: faltan ' + pesos(venc - deposita) + '.</div>');
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
  var d = actual(), p = d.proyeccion, out = [];
  if (p.error || !p.dias.length){
    out.push(el('div', 'card', 'No se pudo proyectar: ' + (p.error || 'faltan datos.')));
    return out;
  }

  // LA CURVA SE ARMA ACA, SUMANDO LAS PARTES QUE ESTAN TILDADAS.
  //
  // Thomas: "esta solapa lo que te tiene que mostrar es que puedo hacer para
  // llegar bien, que obligaciones tengo que patear". Una curva sola no
  // contesta eso: hay que poder sacar cosas y ver el efecto.
  //
  // Sigue valiendo que la plata se calcula en Python -- lo que viaja son los
  // montos por dia y por grupo, ya resueltos. Aca solo se suman los grupos
  // elegidos, que es una suma, no un modelo.
  function armar(){
    var caja = p.caja_inicial, curva = [];
    for (var i = 0; i < Math.min(VENTANA, p.dias.length); i++){
      var x = p.dias[i], sale = 0;
      for (var g in x.sale) if (!PATEADO[g]) sale += x.sale[g];
      caja += x.entra - sale;
      curva.push({fecha: x.fecha, caja: caja, entra: x.entra, sale: sale});
    }
    return curva;
  }
  var curva = armar();
  var critico = null;
  for (var i = 0; i < curva.length; i++) if (curva[i].caja < 0){ critico = curva[i]; break; }
  var minimo = Math.min.apply(null, curva.map(function(x){ return x.caja; }));

  // --- el timeline
  var ct = el('div', 'card');
  ct.appendChild(el('div', null,
    '<b>Horizonte:</b> <span id="vent">' + VENTANA + ' dias</span> ' +
    '<span style="color:var(--tenue);font-size:12.5px">— a 45 dias todavia no hay ' +
    'nada cerrado, asi que cuanto mas lejos, menos dato real y mas proyeccion.</span>'));
  var sl = el('input'); sl.type = 'range'; sl.min = 1; sl.max = p.dias.length;
  sl.value = VENTANA; sl.style.width = '100%'; sl.style.marginTop = '10px';
  sl.oninput = function(){
    VENTANA = Number(sl.value);
    document.getElementById('vent').textContent = VENTANA + ' dias';
    pintar();
  };
  ct.appendChild(sl);
  out.push(ct);

  // --- que se puede patear
  var cp = el('div', 'card');
  cp.appendChild(el('div', null, '<b>Que pasa si pateo...</b>'));
  var cont = el('div');
  cont.style.cssText = 'display:flex;gap:16px;flex-wrap:wrap;margin-top:12px';
  p.grupos.forEach(function(g){
    var hay = p.dias.some(function(x){ return x.sale[g.id]; });
    if (!hay) return;
    var lab = document.createElement('label');
    lab.style.cssText = 'display:flex;gap:7px;align-items:flex-start;font-size:13.5px;' +
                        'max-width:250px;cursor:pointer';
    var cb = document.createElement('input');
    cb.type = 'checkbox'; cb.checked = !!PATEADO[g.id];
    cb.onchange = function(){
      if (cb.checked) PATEADO[g.id] = 1; else delete PATEADO[g.id];
      pintar();
    };
    var txt = el('span', null, '<b>' + g.nombre + '</b>' +
      (g.nota ? '<div class="resumen">' + g.nota + '</div>' : ''));
    lab.appendChild(cb); lab.appendChild(txt);
    cont.appendChild(lab);
  });
  cp.appendChild(cont);
  cp.appendChild(el('p', 'nota', 'Tildar algo lo saca de la curva: es simular que ese ' +
    'pago se corre. La deuda no desaparece — se patea, y el atraso se acumula.'));
  out.push(cp);

  // --- los numeros
  var k = el('div', 'kpis');
  var fin = curva.length ? curva[curva.length - 1].caja : p.caja_inicial;
  [['Caja al arrancar', pesos(p.caja_inicial, true), p.desde, ''],
   ['El dia mas bajo', pesos(minimo, true),
     minimo < 0 ? 'la caja se da vuelta' : 'nunca toca cero', minimo < 0 ? 'malo' : 'bien'],
   ['Caja a los ' + VENTANA + ' dias', pesos(fin, true),
     curva.length ? curva[curva.length - 1].fecha : '', fin >= 0 ? 'bien' : 'malo']
  ].forEach(function(x){
    var t = el('div', 'card kpi ' + x[3]);
    t.appendChild(el('div', 'et', x[0]));
    t.appendChild(el('div', 'n', x[1]));
    t.appendChild(el('div', 'pie', x[2]));
    k.appendChild(t);
  });
  out.push(k);

  if (critico){
    var av = el('div', 'card');
    av.style.borderLeft = '3px solid var(--rojo)';
    av.innerHTML = '<b style="font-size:16px">El dia critico es el ' + dia(critico.fecha) +
      '.</b><br><span style="color:var(--suave)">Ahi la caja queda en ' +
      pesos(critico.caja) + '. Un dueno no mira el final del periodo: mira el dia que ' +
      'se queda corto, y ese dia tiene fecha.</span>';
    out.push(av);
  } else if (Object.keys(PATEADO).length){
    var ok = el('div', 'card');
    ok.style.borderLeft = '3px solid var(--verde)';
    ok.innerHTML = '<b>Asi llegas.</b> Pateando ' +
      p.grupos.filter(function(g){ return PATEADO[g.id]; })
              .map(function(g){ return g.nombre.toLowerCase(); }).join(' y ') +
      ', la caja no se da vuelta en ' + VENTANA + ' dias.';
    out.push(ok);
  }

  var cg = el('div', 'card');
  cg.appendChild(curvaCaja(curva, critico));
  var sale = curva.reduce(function(a, x){ return a + x.sale; }, 0);
  var entra = curva.reduce(function(a, x){ return a + x.entra; }, 0);
  cg.appendChild(el('p', 'nota',
    '<b>Que toma:</b> el comportamiento de los ultimos meses, no una formula — cada ' +
    'tipo de movimiento se repite con su propio ritmo. La deuda con droguerias NO se ' +
    'proyecta: ya tiene fecha y monto en la planilla. En ' + VENTANA + ' dias entran ' +
    pesos(entra) + ' y salen ' + pesos(sale) + '.'));
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
             proyeccion: verProyeccion, hallazgos: verHallazgos};

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

# La solapa "Retiro" se saco: Thomas, 06/09/2026, "no tiene sentido".
# La pregunta que contestaba -- cuanto puedo sacar -- se contesta mirando la
# deuda vencida y la caja, que estan en Posicion. Una solapa entera para
# repetir eso con otra aritmetica agregaba una respuesta mas para conciliar.
CAPAS = [("posicion", "Posición"), ("pagar", "A quién pagar"),
         ("cobrar", "A cobrar"), ("proyeccion", "Proyección"),
         ("hallazgos", "Hallazgos")]


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
