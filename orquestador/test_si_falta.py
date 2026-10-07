# -*- coding: utf-8 -*-
"""Tarea 51: los reintentos de un banco (--si-falta). Todo inventado: no abre ningún navegador."""
import os
import sys
import datetime
import tempfile
import unittest
from unittest import mock

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from orquestador import correr  # noqa: E402


class SiFalta(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = self.tmp.name
        self.drive = os.path.join(self.repo, "drive")
        os.makedirs(self.drive)
        self.hoy = datetime.date.today()
        perfil = {"cliente": "Cliente inventado", "bancos": {"galicia": {
            "activo": True, "carpeta_drive_destino": self.drive, "cuenta": "0000000-0 000-0",
            "solo_estas_empresas": ["EMPRESA INVENTADA"], "prefijo_archivo": "Movimientos Galicia"}}}
        self.parches = [
            mock.patch.object(correr, "BASE_REPO", self.repo),
            mock.patch.object(correr._config, "cargar_perfil", return_value=perfil),
            mock.patch.object(correr._config, "config_banco", return_value=perfil["bancos"]["galicia"]),
            mock.patch.object(correr._cred, "cargar", return_value=("usuario inventado", "clave inventada")),
            mock.patch.object(correr, "log"),
        ]
        for p in self.parches:
            p.start()

    def tearDown(self):
        for p in self.parches:
            p.stop()
        self.tmp.cleanup()

    def estado(self, texto):
        with open(os.path.join(self.drive, "_ESTADO_Galicia_%s.txt" % self.hoy.strftime("%d-%m")), "w",
                  encoding="utf-8") as f:
            f.write("Bot Galicia - %s 05:45\n\n%s\n" % (self.hoy.strftime("%d/%m/%Y"), texto))

    def leer_estado(self):
        return correr._estado_hoy(self.drive, "Galicia", self.hoy)

    def correr(self, loop):
        with mock.patch.object(correr._loop, "correr", side_effect=loop) as m:
            try:
                correr.correr_banco("navar", "galicia", "produccion", si_falta=True)
            except (SystemExit, RuntimeError):
                pass
            return m.call_count

    def login_rechazado(self, *a):
        self.estado(">>> ATENCION: 1 empresa(s) fallaron. Bajar a mano hoy:\n   - LOGIN FALLIDO - "
                    "CLAVE ENVIADA SIN CONFIRMAR: no apareció la empresa")
        sys.exit(1)

    def pagina_caida(self, *a):
        self.estado(">>> ATENCION: 1 empresa(s) fallaron. Bajar a mano hoy:\n   - LOGIN FALLIDO - Timeout al abrir")
        sys.exit(1)

    def test_si_hoy_ya_bajo_bien_no_abre_el_banco(self):
        self.estado("OK: no fallo ninguna empresa.")
        self.assertEqual(0, self.correr(lambda *a: {"ok": ["x"], "fallaron": [], "sin_novedades": []}))

    def test_si_hoy_fallo_reintenta(self):
        self.estado(">>> ATENCION: 1 empresa(s) fallaron.")
        self.assertEqual(1, self.correr(lambda *a: {"ok": ["x"], "fallaron": [], "sin_novedades": []}))

    def test_sin_estado_de_hoy_corre(self):
        self.assertEqual(1, self.correr(lambda *a: {"ok": ["x"], "fallaron": [], "sin_novedades": []}))

    def test_freno_despues_de_dos_claves_sin_confirmar(self):
        self.assertEqual(1, self.correr(self.login_rechazado))
        self.assertEqual(1, self.correr(self.login_rechazado))
        # tercera: ya no abre el banco y deja escrito por qué
        self.assertEqual(0, self.correr(self.login_rechazado))
        self.assertIn("NO SE REINTENTA", self.leer_estado())
        self.assertIn("revisar la clave", self.leer_estado())
        self.assertEqual(0, self.correr(self.login_rechazado))   # y sigue frenado

    def test_falla_antes_de_mandar_la_clave_no_cuenta(self):
        for _ in range(4):
            self.assertEqual(1, self.correr(self.pagina_caida))
        self.assertEqual(0, correr._leer_contador(correr._ruta_contador(self.repo, "navar", "galicia", self.hoy)))

    def test_el_contador_es_por_dia(self):
        ayer = self.hoy - datetime.timedelta(days=1)
        ruta = correr._ruta_contador(self.repo, "navar", "galicia", ayer)
        correr._sumar_contador(ruta)
        correr._sumar_contador(ruta)
        self.assertEqual(1, self.correr(lambda *a: {"ok": ["x"], "fallaron": [], "sin_novedades": []}))

    def test_sin_si_falta_corre_siempre(self):
        self.estado("OK: no fallo ninguna empresa.")
        with mock.patch.object(correr._loop, "correr", return_value={"ok": ["x"], "fallaron": [], "sin_novedades": []}) as m:
            correr.correr_banco("navar", "galicia", "produccion")
        self.assertEqual(1, m.call_count)


if __name__ == "__main__":
    unittest.main()
