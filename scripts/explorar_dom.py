# -*- coding: utf-8 -*-
"""
scripts/explorar_dom.py — la pasada de DOM en vivo, sin dar credenciales.

Para terminar un bot de un banco nuevo hace falta saber cómo se llaman los
botones, los campos y las filas de ESE banco. Eso no se puede adivinar: hay que
mirarlo con la web abierta.

Este script hace justamente eso y nada más:

  1. abre el navegador (perfil persistente: si ya validaste el dispositivo, se
     acuerda);
  2. VOS entrás y navegás a mano — el script NO escribe usuario ni clave, no los
     pide y no los guarda;
  3. en cada paso apretás ENTER en la terminal y toma una FOTO del DOM:
     botones, links, inputs, selects, tablas e iframes, con selectores listos
     para pegar en el bot;
  4. escribe todo en un .md y un .json en salidas/dom/.

Después ese archivo alcanza para completar los `# >>> TODO COMAFI` sin que nadie
tenga que compartir un acceso.

NO captura: valores tipeados en inputs (`value`), contenido de campos password,
ni el HTML completo de la página. Solo la estructura y los textos visibles de
los controles, que es lo único que se necesita para escribir selectores.

Uso:
    python scripts/explorar_dom.py --banco comafi
    python scripts/explorar_dom.py --banco comafi --url https://...
"""

import os
import io
import sys
import json
import argparse
import datetime

BASE_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)

from nucleo.navegador import abrir_navegador


# Se lee la estructura de los controles, nunca lo que hay escrito adentro.
JS_FOTO = r"""
() => {
  const vis = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
  };
  const txt = (el) => (el.innerText || el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 80);
  const attrs = (el) => {
    const o = {};
    for (const a of el.attributes) {
      // 'value' queda afuera a proposito: puede tener datos tipeados.
      if (a.name === 'value' || a.name === 'style') continue;
      if (a.value && a.value.length < 120) o[a.name] = a.value;
    }
    return o;
  };
  const grab = (sel, limite) => {
    const out = [];
    for (const el of document.querySelectorAll(sel)) {
      if (!vis(el)) continue;
      if (el.type === 'password') { out.push({tag: 'input', tipo: 'password', nota: 'omitido'}); continue; }
      out.push({tag: el.tagName.toLowerCase(), tipo: el.type || '', texto: txt(el), attrs: attrs(el)});
      if (out.length >= limite) break;
    }
    return out;
  };
  const tablas = [];
  for (const t of document.querySelectorAll('table')) {
    if (!vis(t)) continue;
    // Si hay thead se usa ese. El fallback a la primera fila solo aplica cuando
    // NO hay thead: si no, se cuelan datos del cuerpo como si fueran titulos.
    let celdas = [...t.querySelectorAll('thead th, thead td')];
    if (!celdas.length) celdas = [...t.querySelectorAll('tr:first-child th, tr:first-child td')];
    const enc = celdas.map(x => txt(x)).slice(0, 15);
    tablas.push({encabezados: enc, filas: t.querySelectorAll('tbody tr').length, attrs: attrs(t)});
    if (tablas.length >= 10) break;
  }
  return {
    url: location.href,
    titulo: document.title,
    botones: grab('button, [role=button], input[type=submit], input[type=button]', 60),
    links: grab('a[href]', 60),
    inputs: grab('input, textarea', 40),
    selects: grab('select', 20),
    tablas: tablas,
    iframes: [...document.querySelectorAll('iframe')].map(f => ({src: (f.src || '').slice(0, 120), name: f.name || ''})),
    datatest: [...document.querySelectorAll('[data-testid],[data-test],[data-tour],[data-cy]')]
                .filter(vis).slice(0, 60)
                .map(e => ({tag: e.tagName.toLowerCase(), texto: txt(e), attrs: attrs(e)})),
  };
}
"""


def _sel(a):
    """Sugiere el selector más estable que se pueda armar con los atributos."""
    for k in ("data-testid", "data-test", "data-tour", "data-cy"):
        if a.get(k):
            return "[%s='%s']" % (k, a[k])
    if a.get("id"):
        return "#%s" % a["id"]
    if a.get("name"):
        return "[name='%s']" % a["name"]
    if a.get("aria-label"):
        return "[aria-label='%s']" % a["aria-label"]
    if a.get("class"):
        return "." + ".".join(a["class"].split()[:2])
    return ""


def _bloque(f, titulo, items, campos=("texto",)):
    if not items:
        return
    f.write("\n### %s (%d)\n\n" % (titulo, len(items)))
    for it in items:
        a = it.get("attrs", {}) or {}
        sel = _sel(a)
        txt = it.get("texto", "")
        linea = "- "
        if txt:
            linea += "**%s**" % txt
        if sel:
            linea += "  ->  `%s`" % sel
        if it.get("tipo"):
            linea += "  _(%s)_" % it["tipo"]
        f.write(linea + "\n")


def escribir(paso, nombre, foto, f):
    f.write("\n\n---\n\n## Paso %d — %s\n\n" % (paso, nombre))
    f.write("- URL: `%s`\n- Titulo: %s\n" % (foto["url"], foto["titulo"]))
    if foto["iframes"]:
        f.write("\n> [!] La pagina tiene %d iframe(s). Si un control no aparece aca, "
                "esta adentro de uno y el bot va a tener que hacer `page.frame_locator(...)`.\n"
                % len(foto["iframes"]))
        for i in foto["iframes"]:
            f.write("  - `%s` %s\n" % (i["src"], i["name"]))
    _bloque(f, "Atributos de test (los MAS estables: usar estos primero)", foto["datatest"])
    _bloque(f, "Botones", foto["botones"])
    _bloque(f, "Links", foto["links"])
    _bloque(f, "Inputs", foto["inputs"])
    _bloque(f, "Selects", foto["selects"])
    if foto["tablas"]:
        f.write("\n### Tablas (%d)\n\n" % len(foto["tablas"]))
        for t in foto["tablas"]:
            f.write("- %d filas | encabezados: %s\n" % (t["filas"], " | ".join(t["encabezados"])))
    f.flush()


PASOS_SUGERIDOS = [
    "Pantalla de login (antes de entrar)",
    "Ya adentro: pantalla principal / home",
    "Selector de EMPRESAS abierto",
    "Listado de cuentas",
    "Cuenta abierta: saldos a la vista",
    "Filtro de FECHAS abierto",
    "Pantalla de movimientos con el boton de DESCARGA a la vista",
    "Listado de CHEQUES EMITIDOS",
]


def main():
    ap = argparse.ArgumentParser(description="Pasada de DOM en vivo para armar un bot")
    ap.add_argument("--banco", required=True)
    ap.add_argument("--url", default="")
    ap.add_argument("--salida", default="")
    args = ap.parse_args()

    perfil = os.path.join(BASE_REPO, "salidas", "perfiles", args.banco)
    desc = os.path.join(BASE_REPO, "salidas", "descargas")
    dom = os.path.join(BASE_REPO, "salidas", "dom")
    for d in (perfil, desc, dom):
        if not os.path.isdir(d):
            os.makedirs(d)

    sello = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
    ruta_md = args.salida or os.path.join(dom, "%s_%s.md" % (args.banco, sello))
    ruta_json = ruta_md[:-3] + ".json" if ruta_md.endswith(".md") else ruta_md + ".json"

    print("=" * 70)
    print("  PASADA DE DOM  ·  %s" % args.banco.upper())
    print("=" * 70)
    print("  Entra y navega VOS. El script no escribe ni guarda usuario/clave.")
    print("  En cada pantalla importante: volve a esta terminal y apreta ENTER.")
    print("  Para terminar: escribi  fin  + ENTER.")
    print("  Salida: %s" % ruta_md)
    print("=" * 70)

    fotos = []
    with abrir_navegador(perfil, desc, headless=False) as page:
        if args.url:
            page.goto(args.url)
        with io.open(ruta_md, "w", encoding="utf-8") as f:
            f.write("# Pasada de DOM — %s\n\n_%s_\n\n" % (args.banco, sello))
            f.write("Generado por `scripts/explorar_dom.py`. Solo estructura de "
                    "controles: no incluye valores tipeados ni campos de clave.\n")
            paso = 0
            while True:
                sug = PASOS_SUGERIDOS[paso] if paso < len(PASOS_SUGERIDOS) else "otra pantalla"
                try:
                    r = input("\n  [%d] %s  ->  ENTER para capturar (o 'fin'): " % (paso + 1, sug))
                except (EOFError, KeyboardInterrupt):
                    break
                if r.strip().lower() in ("fin", "f", "salir", "q"):
                    break
                nombre = r.strip() or sug
                try:
                    foto = page.evaluate(JS_FOTO)
                except Exception as ex:
                    print("      No pude leer la pagina: %s" % ex)
                    continue
                paso += 1
                foto["paso"] = paso
                foto["nombre"] = nombre
                fotos.append(foto)
                escribir(paso, nombre, foto, f)
                print("      OK: %d botones, %d links, %d inputs, %d tablas%s" % (
                    len(foto["botones"]), len(foto["links"]), len(foto["inputs"]),
                    len(foto["tablas"]),
                    "  [ojo: hay iframes]" if foto["iframes"] else ""))

    with io.open(ruta_json, "w", encoding="utf-8") as f:
        f.write(json.dumps(fotos, ensure_ascii=False, indent=2))

    print("\n" + "=" * 70)
    print("  %d pantalla(s) capturadas." % len(fotos))
    print("  %s" % ruta_md)
    print("  %s" % ruta_json)
    print("=" * 70)


if __name__ == "__main__":
    main()
