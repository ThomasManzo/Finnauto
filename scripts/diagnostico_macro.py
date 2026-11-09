# -*- coding: utf-8 -*-
"""
scripts/diagnostico_macro.py — mira la banca empresas de Macro paso a paso y anota lo que ve.

PARA QUÉ
    Antes de programar el bot de Macro hace falta saber cómo se llaman los campos y botones de
    cada pantalla (login en tres datos, inicio, "CUENTA CORRIENTE BANCARIA", el pie con
    "Descargar listado completo"). Este script lo releva mientras Thomas entra A MANO.

REGLAS DE SEGURIDAD (el 28/09/2026 se filtraron las claves de Macro con un diagnóstico)
    · Esta ventana SOLO pide Enter. Lo que se tipee acá no se muestra, no se guarda y no se usa:
      se descarta. Así no hay ningún lugar equivocado donde escribir una clave.
    · El usuario, la clave y la clave empresa se escriben en la PÁGINA DEL BANCO, como siempre.
      El script no los lee, no los pide y no toca el llavero.
    · No saca capturas de pantalla. No lee lo escrito en ningún campo (ni el "value" ni atributos
      que lo puedan copiar): de cada control guarda solo una lista cerrada de atributos.
    · Los números que aparezcan en textos (cuentas, montos, fechas, CUIT) se tapan con 9: queda el
      formato (ej. "999-999999/9") pero no el dato.
    · No aprieta nada ni descarga nada: solo mira. Los clics los hace Thomas.
    · Si la página habla de captcha, token, segundo factor o bloqueo, lo avisa en grande: ahí se frena.

QUÉ DEJA
    Un archivo numerado por el script, en dos lugares:
      clientes/navar/.run/macro_diagnostico/macro_diagnostico_AAAA-MM-DD_N.md   (no va a GitHub)
      NAVAR - Datos/Diagnosticos/macro_diagnostico_AAAA-MM-DD_N.md          (Drive, para leerlo desde la Mac)

USO (en la notebook, desde C:\\finauto)
    .venv\\Scripts\\python.exe scripts\\diagnostico_macro.py
    Para cortar en cualquier momento: Ctrl+C (guarda lo que haya juntado).
"""

import argparse
import datetime
import getpass
import io
import os
import re
import shutil
import sys

BASE_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_REPO not in sys.path:
    sys.path.insert(0, BASE_REPO)


URL_INICIO = "https://www.macro.com.ar/biempresas"

# Cada paso: (título, qué hacer en la página ANTES de apretar Enter, ¿se saca foto?).
# Las fotos de los pasos de login se sacan ANTES de tipear el dato de ese paso.
PASOS = [
    ("Página de ingreso, tal cual abre",
     "No tipees nada. Si para llegar al campo del USUARIO hay que apretar un botón tipo "
     "'Ingresar' o 'Banca empresas', apretalo. Con el campo del usuario a la vista (vacío): Enter.",
     True),
    ("Pedido de la CLAVE (antes de tipearla)",
     "En la PÁGINA escribí el USUARIO y avanzá. Cuando aparezca el campo de la CLAVE, sin "
     "tipearla todavía: Enter. (Si la clave estaba en la misma pantalla que el usuario, Enter igual.)",
     True),
    ("Pedido de la CLAVE EMPRESA (antes de tipearla)",
     "En la PÁGINA escribí la CLAVE y avanzá. Cuando aparezca el campo de la CLAVE EMPRESA, sin "
     "tipearla todavía: Enter. Si en vez de eso aparece un captcha, un token o un código por SMS: "
     "NO sigas, cerrá con Ctrl+C y avisame.",
     True),
    ("Inicio, ya adentro",
     "En la PÁGINA escribí la CLAVE EMPRESA y entrá. Si el banco dice que algún dato está mal, "
     "NO reintentes: Ctrl+C y avisame. Con el inicio a la vista: Enter.",
     True),
    ("CUENTA CORRIENTE BANCARIA, arriba (saldos)",
     "Entrá a 'CUENTA CORRIENTE BANCARIA'. Con la parte de arriba a la vista (donde están los "
     "saldos): Enter.",
     True),
    ("CUENTA CORRIENTE BANCARIA, al pie (descarga)",
     "Bajá hasta el pie, que se vea 'Descargar listado completo'. NO lo aprietes. Enter.",
     True),
    ("Salir del banco",
     "Apretá 'Salir' o 'Cerrar sesión' en la PÁGINA, para no dejar la sesión abierta. Enter y "
     "el script cierra el navegador.",
     False),
]

# Lo que se lee de la página. NUNCA el contenido de los campos: ni .value ni el atributo value,
# ni atributos de frameworks que copian lo tipeado (ej. ng-reflect-model). Solo esta lista cerrada.
JS_FOTO = r"""
() => {
  const PERMITIDOS = ['id', 'name', 'type', 'role', 'class', 'aria-label', 'title', 'placeholder',
    'for', 'maxlength', 'autocomplete', 'readonly', 'disabled', 'target', 'download', 'href',
    'onclick', 'data-testid', 'data-test', 'data-cy', 'formcontrolname', 'tabindex'];
  const vis = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
  };
  const limpio = (t) => (t || '').trim().replace(/\s+/g, ' ');
  const txt = (el) => limpio(el.innerText || el.textContent).slice(0, 80);
  const propio = (el) => limpio([...el.childNodes].filter(n => n.nodeType === 3)
                                   .map(n => n.textContent).join(' ')).slice(0, 80);
  const attrs = (el) => {
    const o = {};
    for (const k of PERMITIDOS) {
      if (!el.hasAttribute(k)) continue;
      let v = el.getAttribute(k) || '';
      // Del link solo la ruta: lo que va después de ? o # puede traer la sesión.
      if (k === 'href') v = v.split('?')[0].split('#')[0];
      o[k] = v.slice(0, 120);
    }
    return o;
  };
  const ruta = (el) => {
    const partes = [];
    let e = el;
    for (let i = 0; i < 4 && e && e.tagName; i++) {
      let p = e.tagName.toLowerCase();
      if (e.id) p += '#' + e.id;
      else if (e.classList && e.classList.length) p += '.' + [...e.classList].slice(0, 2).join('.');
      partes.unshift(p);
      e = e.parentElement;
    }
    return partes.join(' > ');
  };
  const juntar = (sel, limite, conTexto) => {
    const out = [];
    for (const el of document.querySelectorAll(sel)) {
      if (!vis(el)) continue;
      out.push({tag: el.tagName.toLowerCase(), texto: conTexto ? txt(el) : '', attrs: attrs(el), ruta: ruta(el)});
      if (out.length >= limite) break;
    }
    return out;
  };
  // Palabras que interesan para el recorrido: se anota el elemento que las tiene como texto propio.
  const CLAVE = /descargar|listado completo|xls|excel|saldo|cuenta corriente|salir|cerrar sesi|ingres|continuar|siguiente|aceptar|usuario|clave|empresa|movimientos|cuentas/i;
  const claves = [];
  for (const el of document.querySelectorAll('body *')) {
    if (claves.length >= 120) break;
    const t = propio(el);
    if (!t || !CLAVE.test(t) || !vis(el)) continue;
    const enlace = el.closest('a');
    claves.push({tag: el.tagName.toLowerCase(), texto: t, attrs: attrs(el), ruta: ruta(el),
                 en_link: enlace ? attrs(enlace) : null});
  }
  const cuerpo = (document.body && document.body.innerText) || '';
  const alertas = [];
  const buscar = (re, nombre) => { const m = cuerpo.match(re); if (m) alertas.push(nombre + ': "' + m[0] + '"'); };
  buscar(/no soy un robot|captcha/i, 'CAPTCHA');
  buscar(/token|segundo factor|c[oó]digo de (seguridad|verificaci[oó]n)|\bsms\b|clave din[aá]mica|coordenadas|validar (tu|su) identidad/i, 'SEGUNDO FACTOR');
  buscar(/bloquead|suspendid|intentos? (fallidos|restantes)/i, 'BLOQUEO');
  buscar(/incorrect|inv[aá]lid|no coincide/i, 'DATO RECHAZADO');
  for (const f of document.querySelectorAll('iframe')) {
    const src = f.getAttribute('src') || '';
    const r = f.getBoundingClientRect();
    if (/recaptcha|hcaptcha|turnstile|challenges\.cloudflare/i.test(src) && !/size=invisible/.test(src) && r.height > 40)
      alertas.push('CAPTCHA: recuadro visible');
  }
  // Teclado virtual en pantalla: muchos botones con un solo dígito.
  const digitos = [...document.querySelectorAll('button, [role=button], a, td, span, div, input[type=button]')]
    .filter(el => vis(el) && /^\d$/.test(propio(el) || (el.getAttribute('aria-label') || ''))).length;
  return {
    url: location.href.split('?')[0].split('#')[0],
    titulo: document.title,
    titulos: [...document.querySelectorAll('h1, h2, h3, legend')].filter(vis).slice(0, 20).map(txt),
    alertas: alertas,
    teclado_virtual: digitos >= 8,
    botones: juntar('button, [role=button], input[type=submit], input[type=button], input[type=image]', 60, true),
    links: juntar('a[href], a[onclick]', 80, true),
    campos: juntar('input:not([type=hidden]), textarea, select', 40, false),
    textos_clave: claves,
    tablas: [...document.querySelectorAll('table')].filter(vis).slice(0, 10).map(t => ({
      encabezados: [...t.querySelectorAll('thead th, thead td, tr:first-child th')].map(txt).slice(0, 15),
      filas: t.querySelectorAll('tbody tr').length, attrs: attrs(t)})),
    iframes: [...document.querySelectorAll('iframe, frame')].map(f => ({
      src: (f.getAttribute('src') || '').split('?')[0].slice(0, 120), name: f.getAttribute('name') || '',
      id: f.id || ''})),
  };
}
"""


def tapar_numeros(texto):
    """Cambia por 9 los dígitos de cualquier número de 3 cifras o más (cuentas, montos, fechas).
    '$ -1.234.567,89' -> '$ -9.999.999,99'. Los números cortos ('Paso 2') quedan."""
    def tapar(m):
        trozo = m.group(0)
        if sum(c.isdigit() for c in trozo) < 3:
            return trozo
        return re.sub(r"\d", "9", trozo)
    return re.sub(r"\d[\d.,/\-]*\d|\d", tapar, texto or "")


def tapar_todo(dato):
    """Aplica tapar_numeros a todos los textos de la foto (también a los atributos)."""
    if isinstance(dato, str):
        return tapar_numeros(dato)
    if isinstance(dato, list):
        return [tapar_todo(x) for x in dato]
    if isinstance(dato, dict):
        return {k: tapar_todo(v) for k, v in dato.items()}
    return dato


def foto_de_pagina(page):
    """Lee la página y TODOS sus marcos (los bancos viejos suelen usar frames). Devuelve una lista,
    un elemento por marco, ya con los números tapados."""
    fotos = []
    for i, marco in enumerate(page.frames):
        try:
            foto = marco.evaluate(JS_FOTO)
        except Exception as e:
            fotos.append({"marco": i, "error": tapar_numeros(str(e))[:160]})
            continue
        foto["marco"] = i
        fotos.append(tapar_todo(foto))
    return fotos


def _linea(item, con_texto=True):
    a = item.get("attrs") or {}
    partes = []
    if con_texto and item.get("texto"):
        partes.append("**%s**" % item["texto"])
    partes.append("`<%s>`" % item.get("tag", "?"))
    if a:
        partes.append(" ".join("%s=\"%s\"" % (k, v) for k, v in a.items()))
    if item.get("ruta"):
        partes.append("· ruta `%s`" % item["ruta"])
    if item.get("en_link"):
        partes.append("· dentro de un link %s" % " ".join(
            "%s=\"%s\"" % (k, v) for k, v in item["en_link"].items()))
    return "- " + " ".join(partes)


def escribir_paso(f, numero, titulo, fotos):
    f.write("\n\n---\n\n## Paso %d — %s\n" % (numero, titulo))
    for foto in fotos:
        if "error" in foto:
            f.write("\n### Marco %d: no se pudo leer (%s)\n" % (foto["marco"], foto["error"]))
            continue
        vacio = not (foto["botones"] or foto["links"] or foto["campos"] or foto["textos_clave"])
        if foto["marco"] > 0 and vacio:
            continue
        f.write("\n### Marco %d · %s\n\n- URL: `%s`\n" % (foto["marco"], foto["titulo"], foto["url"]))
        if foto["alertas"]:
            f.write("- **ALERTAS:** %s\n" % " · ".join(foto["alertas"]))
        if foto["teclado_virtual"]:
            f.write("- **Hay un teclado virtual en pantalla** (8 o más botones de un dígito).\n")
        if foto["titulos"]:
            f.write("- Títulos: %s\n" % " | ".join(t for t in foto["titulos"] if t))
        if foto["iframes"]:
            f.write("- Marcos internos: %s\n" % "; ".join(
                "%s %s %s" % (x["src"], x["name"], x["id"]) for x in foto["iframes"]))
        for nombre, clave, con_texto in (("Campos", "campos", False), ("Botones", "botones", True),
                                         ("Textos clave", "textos_clave", True), ("Links", "links", True)):
            if foto[clave]:
                f.write("\n#### %s (%d)\n\n" % (nombre, len(foto[clave])))
                for item in foto[clave]:
                    f.write(_linea(item, con_texto) + "\n")
        if foto["tablas"]:
            f.write("\n#### Tablas (%d)\n\n" % len(foto["tablas"]))
            for t in foto["tablas"]:
                f.write("- %d filas · encabezados: %s\n" % (t["filas"], " | ".join(t["encabezados"])))
    f.flush()


def resumen(fotos):
    """Una línea corta para la consola (lo que Thomas pega en el chat)."""
    campos = sum(len(x.get("campos", [])) for x in fotos)
    botones = sum(len(x.get("botones", [])) for x in fotos)
    links = sum(len(x.get("links", [])) for x in fotos)
    marcos = sum(1 for x in fotos if "error" not in x)
    descarga = any(re.search(r"listado completo", i.get("texto", ""), re.I)
                   for x in fotos for i in x.get("textos_clave", []))
    claves = sum(1 for x in fotos for c in x.get("campos", [])
                 if (c.get("attrs") or {}).get("type") == "password")
    partes = ["%d marco(s)" % marcos, "%d campos (%d de clave)" % (campos, claves),
              "%d botones" % botones, "%d links" % links]
    if descarga:
        partes.append("se ve 'Descargar listado completo'")
    if any(x.get("teclado_virtual") for x in fotos):
        partes.append("TECLADO VIRTUAL")
    return " · ".join(partes)


def pedir_enter(texto):
    """Espera Enter. Usa getpass: lo que se tipee NO aparece en pantalla, y se descarta."""
    while True:
        tipeado = getpass.getpass(texto)
        if not tipeado:
            return
        del tipeado
        print("      Acá va SOLO Enter. Lo que escribiste no se mostró ni se guardó.")
        print("      Si era una clave, avisame en el chat (sin decírmela) y la cambiamos.")


def archivo_numerado(carpeta, hoy):
    n = 1
    while os.path.exists(os.path.join(carpeta, "macro_diagnostico_%s_%d.md" % (hoy, n))):
        n += 1
    return os.path.join(carpeta, "macro_diagnostico_%s_%d.md" % (hoy, n))


def main():
    ap = argparse.ArgumentParser(description="Diagnóstico de Macro banca empresas (solo mira).")
    ap.add_argument("--canal", choices=("chromium", "msedge", "chrome"), default="chromium",
                    help="navegador a usar (por defecto, el Chromium de Playwright, como los bots)")
    args = ap.parse_args()

    from nucleo.navegador import abrir_navegador
    from ingestas.drive_local import carpeta_datos

    base = os.path.join(BASE_REPO, "clientes", "navar", ".run", "macro_diagnostico")
    perfil = os.path.join(base, "perfil_" + args.canal)
    descargas = os.path.join(base, "descargas")
    for d in (base, perfil, descargas):
        os.makedirs(d, exist_ok=True)
    hoy = datetime.date.today().isoformat()
    ruta = archivo_numerado(base, hoy)

    print("=" * 72)
    print("  DIAGNÓSTICO DE MACRO · solo mira, no descarga nada")
    print("  Los datos de entrada se escriben en la PÁGINA DEL BANCO, nunca acá.")
    print("  Esta ventana solo espera Enter (lo que se tipee acá no se ve ni se guarda).")
    print("  Para cortar: Ctrl+C.")
    print("=" * 72)

    hechos = 0
    alertas_vistas = []
    with abrir_navegador(perfil, descargas, headless=False,
                         canal=None if args.canal == "chromium" else args.canal) as page:
        with io.open(ruta, "w", encoding="utf-8") as f:
            f.write("# Diagnóstico de Macro — %s\n\n" % datetime.datetime.now().strftime("%d/%m/%Y %H:%M"))
            f.write("Generado por `scripts/diagnostico_macro.py`. Sin valores de campos, sin capturas; "
                    "los números de 3 cifras o más están tapados con 9. Navegador: %s.\n" % args.canal)
            try:
                page.goto(URL_INICIO, timeout=60000)
            except Exception as e:
                print("  Aviso: la página tardó en abrir (%s). Seguí igual." % str(e)[:80])
            try:
                for numero, (titulo, hacer, con_foto) in enumerate(PASOS, start=1):
                    print("")
                    print("  [%d/%d] %s" % (numero, len(PASOS), titulo))
                    print("        %s" % hacer)
                    pedir_enter("        Enter: ")
                    if not con_foto:
                        continue
                    fotos = foto_de_pagina(page)
                    escribir_paso(f, numero, titulo, fotos)
                    hechos += 1
                    print("        OK · %s" % resumen(fotos))
                    for foto in fotos:
                        for alerta in foto.get("alertas", []):
                            alertas_vistas.append("paso %d: %s" % (numero, alerta))
                            print("")
                            print("        !!! %s" % alerta)
                            print("        !!! Si es un captcha, un token, un código o un bloqueo: NO sigas.")
                            print("        !!! Ctrl+C y avisame. (Si es solo publicidad del banco, seguí.)")
            except KeyboardInterrupt:
                print("\n  Cortado con Ctrl+C. Guardo lo que hay.")
                f.write("\n\n_Cortado con Ctrl+C después de %d foto(s)._\n" % hechos)

    print("")
    print("=" * 72)
    print("  %d foto(s) guardadas en:" % hechos)
    print("  %s" % ruta)
    drive = carpeta_datos()
    if drive:
        try:
            destino = os.path.join(drive, "Diagnosticos")
            os.makedirs(destino, exist_ok=True)
            shutil.copy2(ruta, os.path.join(destino, os.path.basename(ruta)))
            print("  Copia en Drive: NAVAR - Datos/Diagnosticos/%s" % os.path.basename(ruta))
        except OSError as e:
            print("  No pude copiarlo a Drive (%s): pegame la ruta de arriba." % e)
    else:
        print("  No encontré Drive: pegame la ruta de arriba.")
    if alertas_vistas:
        print("  Alertas: %s" % " | ".join(alertas_vistas))
    print("=" * 72)


if __name__ == "__main__":
    main()
