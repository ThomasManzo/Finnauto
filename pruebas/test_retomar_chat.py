"""Conversaciones inventadas: no hace falta abrir ningún chat real."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest

from herramientas.retomar_chat import leer_chat, main


class RetomarChatTest(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.carpeta = Path(self.temporal.name)
        self.ruta = self.carpeta / 'abcdef12-3456.jsonl'
        self.escribir(self.ruta, [
            {'type': 'user', 'timestamp': '2026-01-01', 'message': {'content': 'Hola inventado'}},
            {'type': 'summary', 'summary': 'Resumen viejo'},
            {'type': 'custom-title', 'customTitle': 'Plan de ejemplo'},
            {'type': 'user', 'isCompactSummary': True, 'message': {'content': 'Resumen nuevo'}},
            {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'content': 'SECRETO'}]}},
            {'type': 'assistant', 'timestamp': '2026-01-02', 'message': {'content': [
                {'type': 'thinking', 'thinking': 'SECRETO'},
                {'type': 'image', 'source': 'SECRETO'},
                {'type': 'tool_use', 'input': 'SECRETO'},
                {'type': 'text', 'text': 'Respuesta inventada'}]}},
            {'type': 'user', 'timestamp': '2026-01-03', 'message': {'content': 'Seguir'}}])

    def escribir(self, ruta, datos):
        ruta.write_text(''.join(json.dumps(d) + '\n' for d in datos), encoding='utf-8')

    def ejecutar(self, *args):
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            self.assertEqual(main(['--proyecto', str(self.carpeta), *args]), 0)
        return salida.getvalue()

    def test_lista(self):
        salida = self.ejecutar('--lista')
        for texto in ('abcdef12', 'Plan de ejemplo', 'KB'):
            self.assertIn(texto, salida)

    def test_busqueda_y_ultimos(self):
        for consulta in ('abcdef12', 'PLAN DE'):
            salida = self.ejecutar('--chat', consulta, '--ultimos', '2')
            self.assertTrue(salida.startswith('Resumen de compactación:\nResumen nuevo'))
            for texto in ('2026-01-02 — Claude:', 'Thomas:', 'Respuesta inventada', 'Seguir'):
                self.assertIn(texto, salida)
            for texto in ('SECRETO', 'Hola inventado', 'Resumen viejo'):
                self.assertNotIn(texto, salida)

    def test_recortes_y_renglon_incompleto(self):
        self.escribir(self.ruta, [{'type': 'summary', 'summary': 'r' * 5000},
                                 {'type': 'user', 'message': {'content': 'x' * 2000}}])
        with self.ruta.open('a') as archivo:
            archivo.write('{incompleto')
        titulo, resumen, mensajes = leer_chat(self.ruta)
        self.assertEqual(len(titulo), 100)
        self.assertEqual(len(resumen), 4000)
        self.assertEqual(len(mensajes[0][2]), 1500)

    def test_lista_solo_20_recientes(self):
        for i in range(21):
            ruta = self.carpeta / f'{i:08d}.jsonl'
            self.escribir(ruta, [{'type': 'user', 'message': {'content': f'Ejemplo {i}'}}])
            os.utime(ruta, (100 + i, 100 + i))
        salida = self.ejecutar('--lista')
        self.assertEqual(len(salida.splitlines()), 20)
        self.assertNotIn('00000000 |', salida)
        self.assertIn('Ejemplo 20', salida)

    def test_errores_claros(self):
        self.escribir(self.carpeta / 'abcdef99.jsonl', [])
        for args in (('--chat', 'abcdef'), ('--chat', 'inexistente'),
                     ('--chat', 'abcdef12', '--ultimos', '0')):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                main(['--proyecto', str(self.carpeta), *args])
            self.assertEqual(error.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
