// Tarea 61. Prueba con un Drive inventado: no accede a Google ni a datos reales.
// 1) La búsqueda por nombre elige el archivo más nuevo que esté adentro de "NAVAR - Datos".
// 2) Si el buscador no trae nada, se recorre el árbol como antes.
// 3) Si Drive tropieza con un tipo de archivo, importarLoNuevo sigue con los demás y avisa al final.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');

// ---- un Drive de juguete -------------------------------------------------------------------------
let proximoId = 1;
class Iter {
  constructor(lista) { this.lista = lista.slice(); }
  hasNext() { return this.lista.length > 0; }
  next() { return this.lista.shift(); }
}
class Carpeta {
  constructor(nombre, padre) {
    this.id = 'c' + proximoId++; this.nombre = nombre; this.padre = padre || null;
    this.archivos = []; this.subcarpetas = [];
    if (padre) padre.subcarpetas.push(this);
  }
  getId() { return this.id; }
  getName() { return this.nombre; }
  getParents() { return new Iter(this.padre ? [this.padre] : []); }
  getFiles() { drive.recorridas++; return new Iter(this.archivos); }
  getFolders() { return new Iter(this.subcarpetas); }
}
class Archivo {
  constructor(nombre, carpeta, dia) {
    this.id = 'a' + proximoId++; this.nombre = nombre; this.carpeta = carpeta;
    this.fecha = new Date('2026-10-' + String(dia).padStart(2, '0') + 'T09:00:00Z');
    carpeta.archivos.push(this); drive.todos.push(this);
  }
  getId() { return this.id; }
  getName() { return this.nombre; }
  getLastUpdated() { return this.fecha; }
  getParents() { return new Iter([this.carpeta]); }
}
const drive = {
  todos: [], recorridas: 0, buscadorApagado: false, fallas: {},
  searchFiles(consulta) {
    const m = consulta.match(/title contains '(.*)' and trashed = false/);
    assert.ok(m, 'consulta inesperada: ' + consulta);
    const prefijo = m[1];
    if (drive.fallas[prefijo]) { drive.fallas[prefijo]--; throw new Error('Error de servicio: Drive'); }
    if (drive.buscadorApagado) return new Iter([]);
    // El buscador real es laxo ("contains"): también trae nombres que tienen el texto en el medio.
    return new Iter(drive.todos.filter(a => a.getName().includes(prefijo)));
  },
};

const otraCarpeta = new Carpeta('Descargas viejas');
const raiz = new Carpeta('NAVAR - Datos');
const paraLaSheet = new Carpeta('_para la Sheet', raiz);
const historico = new Carpeta('2026', new Carpeta('Bancos', raiz));
drive.getFoldersByName = nombre => new Iter(nombre === 'NAVAR - Datos' ? [raiz] : []);

new Archivo('para_pegar_bancos_2026-10-12.xlsx', paraLaSheet, 12);
const bancosBueno = new Archivo('para_pegar_bancos_2026-10-14.xlsx', paraLaSheet, 14);
new Archivo('para_pegar_bancos_2026-10-20.xlsx', otraCarpeta, 20);           // más nuevo, pero afuera
new Archivo('copia de para_pegar_bancos_2026-10-21.xlsx', historico, 21);     // no empieza con el prefijo
const cajasBueno = new Archivo('para_pegar_cajas_2026-10-14.xlsx', historico, 14);  // subcarpeta profunda

const registrados = [];
const contexto = vm.createContext({
  Date, Object,
  DriveApp: drive,
  Logger: { log() {} },
  Utilities: { sleep() {} },
  PropertiesService: { getDocumentProperties: () => ({ getProperty() { return null; }, setProperty() {} }) },
});
vm.runInContext(fs.readFileSync(path.join(__dirname,
  '../../clientes/navar/herramientas/importar_cashflow.gs'), 'utf8'), contexto);

// ---- 1) búsqueda rápida ------------------------------------------------------------------------
drive.recorridas = 0;
assert.equal(contexto._ultimoConPrefijo_('para_pegar_bancos_'), bancosBueno,
  'tiene que elegir el más nuevo de adentro de NAVAR - Datos, no el de afuera ni la "copia de"');
assert.equal(contexto._ultimoConPrefijo_('para_pegar_cajas_'), cajasBueno, 'encuentra en subcarpetas profundas');
assert.equal(drive.recorridas, 0, 'con el buscador andando no se recorren carpetas');

// ---- 2) respaldo: el buscador no trae nada -> se recorre el árbol ---------------------------------
drive.buscadorApagado = true;
assert.equal(contexto._ultimoConPrefijo_('para_pegar_bancos_'), bancosBueno);
assert.ok(drive.recorridas > 0, 'sin resultados del buscador, recorre las carpetas como antes');
assert.equal(contexto._ultimoConPrefijo_('para_pegar_deuda_'), null, 'si no existe, devuelve null');
drive.buscadorApagado = false;

// ---- 3) importarLoNuevo con Drive que tropieza ---------------------------------------------------
const importados = [];
contexto._importar_ = (cual, archivo) => { importados.push(cual); return 'cargadas 1'; };
contexto._registrar_ = (cual, nombre, estado) => registrados.push([cual, nombre, estado]);
contexto.exportarParaTablero = () => {};
new Archivo('para_pegar_deuda_2026-10-14.xlsx', paraLaSheet, 14);
new Archivo('para_pegar_impuestos_2026-10-14.xlsx', paraLaSheet, 14);
new Archivo('para_pegar_en_la_sheet_2026-10-14.xlsx', paraLaSheet, 14);
new Archivo('para_pegar_ultimos_pagos_2026-10-14.xlsx', paraLaSheet, 14);

// Un tropiezo de un momento: el reintento lo salva y no se avisa nada.
drive.fallas = { 'para_pegar_deuda_': 1 };
assert.equal(contexto.importarLoNuevo(), 6);
assert.deepEqual(importados, ['deuda', 'impuestos', 'bancos', 'cajas', 'tango', 'ultimos_pagos']);

// Un tropiezo que sigue: bancos queda sin revisar, los demás entran igual y el aviso sale al final.
importados.length = 0;
drive.fallas = { 'para_pegar_bancos_': 2 };
assert.throws(() => contexto.importarLoNuevo(), /No se pudo revisar Drive para: bancos/);
assert.deepEqual(importados, ['deuda', 'impuestos', 'cajas', 'tango', 'ultimos_pagos'],
  'los demás tipos se importan aunque bancos haya fallado');
assert.ok(!registrados.some(r => r[0] === 'bancos' && r[2] === 'ERROR'),
  'un tropiezo de Drive no ensucia el Registro: queda en la ejecución y se reintenta en una hora');

console.log('probar_importador_busqueda: OK');
