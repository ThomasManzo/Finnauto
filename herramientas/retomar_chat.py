"""Muestra lo necesario para retomar un chat, sin volcar sus herramientas."""

import argparse
from collections import deque
from datetime import datetime
import json
from pathlib import Path


def proyecto_default():
    # La carpeta de Claude usa la ruta del repo con guiones, incluso desde un worktree.
    repo = Path.home() / 'Documents' / 'Finnauto'
    return Path.home() / '.claude' / 'projects' / str(repo).replace('/', '-')


def recortar(texto, limite):
    return texto if len(texto) <= limite else texto[:limite - 1] + '…'


def texto_mensaje(registro):
    mensaje = registro.get('message', {})
    if not isinstance(mensaje, dict):
        return ''
    contenido = mensaje.get('content', '')
    if isinstance(contenido, str):
        return contenido.strip()
    if not isinstance(contenido, list):
        return ''
    # Solo texto: las imágenes, el razonamiento y las herramientas quedan afuera.
    return '\n'.join(b['text'] for b in contenido
                     if isinstance(b, dict) and b.get('type') == 'text'
                     and isinstance(b.get('text'), str)).strip()


def leer_chat(ruta, ultimos=30):
    mensajes = deque(maxlen=ultimos)
    titulo = primero = resumen = ''
    # Nunca cargamos el historial entero: conservamos solo la cola que se pidió.
    with ruta.open(encoding='utf-8') as archivo:
        for renglon in archivo:
            try:
                dato = json.loads(renglon)
            except (ValueError, UnicodeError):
                # Un chat abierto puede tener su último renglón todavía sin terminar.
                continue
            if not isinstance(dato, dict):
                continue
            tipo = dato.get('type')
            for clave in ('customTitle', 'title'):
                if isinstance(dato.get(clave), str) and dato[clave].strip():
                    titulo = dato[clave].strip()
            if tipo == 'summary' and isinstance(dato.get('summary'), str):
                resumen = recortar(dato['summary'], 4000)
            if tipo not in ('user', 'assistant'):
                continue
            texto = texto_mensaje(dato)
            if not texto:
                continue
            if dato.get('isCompactSummary'):
                resumen = recortar(texto, 4000)
                continue
            if tipo == 'user' and not primero:
                primero = recortar(' '.join(texto.split()), 100)
            mensajes.append((str(dato.get('timestamp') or 'Sin fecha'),
                             'Thomas' if tipo == 'user' else 'Claude',
                             recortar(texto, 1500)))
    return titulo or primero or '(sin título)', resumen, mensajes


def positivo(valor):
    numero = int(valor)
    if numero < 1:
        raise argparse.ArgumentTypeError('La cantidad tiene que ser mayor que cero.')
    return numero


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modo = parser.add_mutually_exclusive_group(required=True)
    modo.add_argument('--lista', action='store_true')
    modo.add_argument('--chat', help='Id corto o parte del título')
    parser.add_argument('--ultimos', type=positivo, default=30)
    parser.add_argument('--proyecto', type=Path, default=proyecto_default(),
                        help='Carpeta de Claude que contiene los archivos .jsonl')
    args = parser.parse_args(argv)
    carpeta = args.proyecto.expanduser()
    if not carpeta.is_dir():
        parser.error(f'No encuentro la carpeta de chats: {carpeta}')
    try:
        archivos = sorted(carpeta.glob('*.jsonl'), key=lambda p: p.stat().st_mtime,
                          reverse=True)
        if args.lista:
            for ruta in archivos[:20]:
                titulo, _, _ = leer_chat(ruta, 0)
                estado = ruta.stat()
                fecha = datetime.fromtimestamp(estado.st_mtime).strftime('%Y-%m-%d %H:%M')
                print(f'{ruta.stem[:8]} | {fecha} | {estado.st_size / 1024:.1f} KB | '
                      f'{" ".join(titulo.split())}')
            if not archivos:
                print('Todavía no hay chats en esa carpeta.')
            return 0
        consulta = args.chat.strip().casefold()
        if not consulta:
            parser.error('Escribí un id o una parte del título.')
        # El id tiene prioridad; no hace falta recorrer otros chats si ya identifica uno.
        candidatos = [p for p in archivos if p.stem.casefold().startswith(consulta)]
        if not candidatos:
            candidatos = [p for p in archivos if consulta in leer_chat(p, 0)[0].casefold()]
        if not candidatos:
            parser.error('No encontré un chat con ese id o título.')
        if len(candidatos) > 1:
            parser.error('Hay varios chats que coinciden. Usá un id más completo: ' +
                         ', '.join(p.stem for p in candidatos))
        _, resumen, mensajes = leer_chat(candidatos[0], args.ultimos)
        if resumen:
            print(f'Resumen de compactación:\n{resumen}\n')
        for fecha, autor, texto in mensajes:
            print(f'{fecha} — {autor}:\n{texto}\n')
        return 0
    except OSError as error:
        parser.error(f'No pude leer los chats: {error}')


if __name__ == '__main__':
    raise SystemExit(main())
