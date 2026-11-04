"""Excel y saldos inventados para comprobar la bajada local, sin red."""
import datetime as dt
import json
from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from openpyxl import Workbook
from ingestas import galicia_datos as gd, mercado_datos as md


class Pruebas(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.descargas = self.base / 'descargas'
        self.descargas.mkdir()
        self.salida = self.base / 'salida'
        self.cfg = dict(activo=True, cuenta='0001234-5 999-1', prefijo_archivo='Movimientos Galicia',
                        carpeta_drive_destino=str(self.descargas))
        self.perfil = self.base / 'clientes/ejemplo/privado/perfil.json'
        self.perfil.parent.mkdir(parents=True)
        self.perfil.write_text(json.dumps({'bancos': {'galicia': self.cfg}}))

    def excel(self, fecha, cantidad=4, saldo=True):
        ruta = self.descargas / ('Movimientos Galicia ' + fecha + '.xlsx')
        libro = Workbook()
        hoja = libro.active
        hoja.append(['Fecha', 'Descripción', 'Débitos', 'Créditos', 'Saldo', 'Número de Comprobante'])
        filas = [('2026-10-29', 'TRANSFERENCIA RECIBIDA', 0, 100000, 500000),
                 ('2026-10-29', 'IMP. LEY 25413', 600, 0, 499400),
                 ('2026-10-30', 'COMISION MANTENIMIENTO', 5000, 0, 494400),
                 ('2026-10-31', 'TRANSFERENCIA TIENDANUBE', 0, 80000, 574400)]
        for n, (f, concepto, debito, credito, monto) in enumerate(filas[:cantidad]):
            hoja.append([dt.date.fromisoformat(f), concepto, debito, credito, monto if saldo else None, str(n)])
        libro.save(ruta)
        libro.close()
        return ruta

    def saldo(self, nombre, generado, saldo, fecha='2026-10-31'):
        (self.descargas / nombre).write_text(json.dumps(dict(fecha=fecha, generado=generado,
                                                           empresas=[dict(saldo_actual=saldo)])))

    def correr(self):
        # Reloj fijo: las descargas de prueba tienen fecha fija y a los 3 días la fuente queda en rojo.
        class Reloj(dt.datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 11, 1, 12, 0, tzinfo=tz)
        with patch.object(md.meli_oauth, 'BASE_REPO', self.base), patch.object(md.dt, 'datetime', Reloj):
            return md.main(['--cliente', 'ejemplo', '--salida', str(self.salida), '--solo', 'galicia'])

    def test_q_r_historial_y_atomico(self):
        self.excel('2026-10-30', 3)
        self.excel('2026-10-31')
        self.saldo('_SALDOS_Galicia_31-10.json', '2026-10-31T12:00:00', 574400)
        self.saldo('_SALDOS_Galicia_31-10_copia.json', '2026-10-31T10:00:00', 500000)
        filas, saldos, control = gd.leer(self.cfg, self.salida, dt.date(2026, 11, 1))
        self.assertTrue(control['ok'])
        self.assertEqual([f['tipo'] for f in filas], ['transferencia', 'impuesto', 'comisión', 'Tiendanube'])
        self.assertEqual([f['importe'] for f in filas], ['100000.00', '-600.00', '-5000.00', '80000.00'])
        self.assertEqual(saldos, [dict(fecha='2026-10-31', saldo='574400.00')])
        reemplazar = os.replace
        destinos = []
        def comprobar(origen, destino):
            self.assertEqual(Path(origen).parent, Path(destino).parent)
            self.assertNotEqual(Path(origen), Path(destino))
            self.assertTrue(Path(origen).exists())
            destinos.append(Path(destino).name)
            reemplazar(origen, destino)
        with patch('os.replace', side_effect=comprobar):
            self.correr()
        self.assertEqual(destinos, ['galicia_movimientos.csv', 'galicia_saldo.csv', 'mercado_datos_estado.json', 'control.json'])
        self.assertEqual(md.leer_csv(self.salida / 'galicia_movimientos.csv'), filas)
        for p in self.descargas.iterdir(): p.unlink()
        self.assertEqual(self.correr(), 1)
        self.assertEqual(md.leer_csv(self.salida / 'galicia_movimientos.csv'), filas)
        self.assertEqual(md.leer_csv(self.salida / 'galicia_saldo.csv'), saldos)
        control = json.loads((self.salida / 'control.json').read_text())['fuentes']['galicia']
        self.assertEqual(control['motivo'], 'todavía no hay descargas de Galicia')

    def test_segunda_corrida_agrega_y_actualiza_saldo_del_dia(self):
        viejo = self.excel("2026-10-30", 3)
        self.saldo("_SALDOS_Galicia_31-10.json", "2026-10-31T10:00:00", 500000)
        self.correr()
        viejo.unlink()
        self.excel("2026-10-31")
        self.saldo("_SALDOS_Galicia_31-10.json", "2026-10-31T12:00:00", 574400)
        self.correr()
        filas = md.leer_csv(self.salida / "galicia_movimientos.csv")
        self.assertEqual(len(filas), 4)
        self.assertEqual([f["referencia"] for f in filas], ["0", "1", "2", "3"])
        self.assertEqual(md.leer_csv(self.salida / "galicia_saldo.csv"),
                         [dict(fecha="2026-10-31", saldo="574400.00")])

    def test_s_sin_perfil_bloque_inactivo_y_viejo(self):
        self.excel('2026-10-27')
        _, _, control = gd.leer(self.cfg, self.salida, dt.date(2026, 11, 1))
        self.assertFalse(control['ok'])
        self.assertEqual(control['ultima_descarga'], '2026-10-27')
        self.assertEqual(control['motivo'], 'el bot de Galicia no bajó nada desde 2026-10-27')
        for perfil in ({}, {'bancos': {'galicia': dict(self.cfg, activo=False)}}, {'bancos': {'galicia': dict(self.cfg, carpeta_drive_destino='')}}):
            self.perfil.write_text(json.dumps(perfil))
            self.assertEqual(self.correr(), 0)
            self.assertNotIn('galicia', json.loads((self.salida / 'control.json').read_text())['fuentes'])
        self.perfil.unlink()
        self.assertEqual(self.correr(), 0)
        self.assertFalse((self.salida / 'galicia_movimientos.csv').exists())

    def test_error_lectura_y_replace_conservan_csv(self):
        ruta = self.excel('2026-10-31')
        self.correr()
        anterior = (self.salida / 'galicia_movimientos.csv').read_bytes()
        ruta.write_bytes(b'Excel incompleto')
        self.assertEqual(self.correr(), 1)
        self.assertEqual((self.salida / 'galicia_movimientos.csv').read_bytes(), anterior)
        self.excel('2026-10-31', 3)
        with patch('os.replace', side_effect=OSError('ocupado')):
            self.assertEqual(self.correr(), 1)
        self.assertEqual((self.salida / 'galicia_movimientos.csv').read_bytes(), anterior)
        self.assertEqual({p.name for p in self.salida.iterdir()}, {'galicia_movimientos.csv', 'galicia_saldo.csv', 'control.json'})

    def test_saldo_vacio_tipos_y_fuentes_ajenas(self):
        self.excel('2026-10-31', saldo=False)
        filas, _, _ = gd.leer(self.cfg, self.salida)
        self.assertEqual(filas[0]['saldo'], '')
        for concepto, esperado in [('Comisión', 'comisión'), ('RETEN TIENDANUBE', 'impuesto'), ('pago nube', 'Tiendanube'), ('ECHEQ', 'transferencia'), ('venta', 'otro')]:
            self.assertEqual(gd.tipo(concepto), esperado)
        self.salida.mkdir()
        (self.salida / 'control.json').write_text('{"fuentes": {"ajena": {"ok": true}}}')
        self.correr()
        self.assertEqual(json.loads((self.salida / 'control.json').read_text())['fuentes']['ajena'], {'ok': True})


if __name__ == '__main__':
    unittest.main()
