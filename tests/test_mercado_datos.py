"""Corridas con datos inventados y carpetas temporales, sin red ni llavero."""
import datetime as dt
import json
from unittest.mock import Mock, patch
import unittest
import tempfile
import contextlib
import io
from pathlib import Path


from ingestas import mercado_datos as C


class Reloj(dt.datetime):
    @classmethod
    def now(cls, tz=None):
        # En UTC ya es mañana; el estado debe usar el día de Buenos Aires.
        return cls(2026, 1, 15, 23, 30, tzinfo=C.ml.HORA_BA)


def preparar(tmp_path, parches):
    parches.setattr(C.dt, 'datetime', Reloj)
    parches.setattr(C.meli_oauth, 'BASE_REPO', tmp_path)
    parches.setattr(C.meli_oauth, 'access_token', Mock(side_effect=AssertionError('No pedir tokens')))
    parches.setattr(C.tn, 'tiene_aplicacion', Mock(return_value=False))
    parches.setattr(C.galicia, 'configuracion', Mock(return_value=None))
    for modulo, resultado in ((C.ml, ([], 0)), (C.mp, ([], '')), (C.ads, [])):
        parches.setattr(modulo, 'bajar', Mock(return_value=resultado))
    estado = tmp_path / 'clientes/ejemplo/.run/mercado_datos_estado.json'
    control = tmp_path / 'control.json'

    def correr(*args):
        return C.main(['--cliente', 'ejemplo', '--salida', str(tmp_path), *args])
    return correr, estado, control


class CorridaTests(unittest.TestCase):
    def setattr(self, objeto, nombre, valor):
        parche = patch.object(objeto, nombre, valor)
        parche.start()
        self.addCleanup(parche.stop)

    def setUp(self):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.tmp_path = Path(temporal.name)
        self.salida = io.StringIO()
        redireccion = contextlib.redirect_stdout(self.salida)
        redireccion.__enter__()
        self.addCleanup(redireccion.__exit__, None, None, None)
        self.corrida = preparar(self.tmp_path, self)

    def test_fallo_de_bajada(self):
        self.comprobar_fallo(False)

    def test_fallo_de_csv(self):
        self.comprobar_fallo(True)

    def test_pendientes_conserva_resumen_y_usa_ventas_guardadas(self):
        correr, estado, control = self.corrida
        C.ml.guardar_json(estado, {'mercadolibre': '2026-01-15', 'mercadolibre_publicidad': '2026-01-15'})
        resumen = dict(ok=True, filas=12, desde='2025-12-01', hasta='2026-01-14', motivo='', descuadradas=2)
        C.ml.guardar_json(control, {'fuentes': {'mercadolibre': resumen, 'ajena': {'ok': False}}})
        ventas = [dict(id_venta='123', id_pago_mp='456')]
        C.escribir_csv(self.tmp_path / 'ml_ventas.csv', ['id_venta', 'id_pago_mp'], ventas)
        assert correr('--solo-pendientes') == 0
        C.ml.bajar.assert_not_called()
        C.ads.bajar.assert_not_called()
        assert C.mp.bajar.call_args.args[-1] == ventas
        assert json.loads(control.read_text())['fuentes']['mercadolibre'] == resumen
        assert json.loads(estado.read_text())['mercadopago'] == '2026-01-15'


    def test_todo_listo_no_toca_control_ni_permisos(self):
        correr, estado, control = self.corrida
        fuentes = ['mercadolibre', 'mercadopago', 'mercadolibre_publicidad', 'tiendanube', 'galicia']
        C.ml.guardar_json(estado, dict.fromkeys(fuentes, '2026-01-15'))
        control.write_text('{"corrida": "anterior", "fuentes": {}}')
        antes = control.stat().st_mtime_ns
        self.setattr(C.tn, 'estado', Mock(side_effect=AssertionError('No pedir permiso')))
        assert correr('--solo-pendientes') == 0
        assert control.stat().st_mtime_ns == antes
        assert control.read_text() == '{"corrida": "anterior", "fuentes": {}}'
        C.tn.tiene_aplicacion.assert_not_called()
        C.meli_oauth.access_token.assert_not_called()
        C.ml.bajar.assert_not_called()
        C.mp.bajar.assert_not_called()
        C.ads.bajar.assert_not_called()
        assert 'Nada pendiente: todo se bajó bien hoy.' in self.salida.getvalue()


    def comprobar_fallo(self, falla_csv):
        correr, estado, control = self.corrida
        C.ml.guardar_json(estado, {'mercadolibre': '2026-01-14'})
        csv = self.tmp_path / 'ml_ventas.csv'
        csv.write_text('anterior')
        if falla_csv:
            self.setattr(C, 'escribir_csv', Mock(side_effect=OSError('ocupado')))
        else:
            C.ml.bajar.side_effect = C.ml.ErrorDatos('corte inventado')
        assert correr('--solo', 'mercadolibre', '--solo-pendientes') == 1
        assert json.loads(estado.read_text()) == {'mercadolibre': '2026-01-14'}
        assert csv.read_text() == 'anterior'
        assert not json.loads(control.read_text())['fuentes']['mercadolibre']['ok']


    def test_corrida_normal_guarda_estado_y_solo_filtra(self):
        correr, estado, control = self.corrida
        assert correr('--solo', 'mercadolibre') == 0
        assert json.loads(estado.read_text()) == {'mercadolibre': '2026-01-15'}
        C.ml.bajar.reset_mock()
        assert correr('--solo', 'mercadolibre', '--solo-pendientes') == 0
        C.ml.bajar.assert_not_called()
        C.mp.bajar.assert_not_called()
        # Sin la opción se vuelve a bajar aunque ya haya salido bien hoy.
        assert correr('--solo', 'mercadolibre') == 0
        C.ml.bajar.assert_called_once()


    def test_tiendanube_sin_permiso_se_quita_sin_falla(self):
        correr, estado, control = self.corrida
        self.setattr(C.tn, 'tiene_aplicacion', Mock(return_value=True))
        self.setattr(C.tn, 'estado', Mock(return_value={'hay_token': False}))
        self.setattr(C.tn, 'Sesion', Mock(side_effect=AssertionError('No iniciar sesión')))
        C.ml.guardar_json(control, {'corrida': 'anterior', 'fuentes': {'tiendanube': {'ok': False}}})
        assert correr('--solo', 'tiendanube') == 0
        assert json.loads(control.read_text()) == {'corrida': 'anterior', 'fuentes': {}}
        assert not estado.exists()


if __name__ == '__main__':
    unittest.main()
