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
from ingestas.dolar import bajar as bajar_dolar


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
    for modulo, resultado in ((C.ml, ([], 0)), (C.mp, ([], '')), (C.mp_saldo, ([], '')), (C.ads, []), (C.dolar, [])):
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

    def test_saldo_control_estado_y_falla_conserva_csv(self):
        correr, estado, control = self.corrida
        C.mp_saldo.bajar.return_value = ([dict(fecha='2026-01-14', disponible='12.00', a_liberar='', intereses_del_dia='0.00')], '')
        assert correr('--solo', 'mercadopago_saldo') == 0
        assert C.mp_saldo.bajar.call_args.args[-1] == dt.date(2026, 1, 14)
        resumen = json.loads(control.read_text())['fuentes']['mercadopago_saldo']
        assert resumen == dict(ok=True, filas=1, desde='2026-01-14', hasta='2026-01-14', motivo='', actualizado='2026-01-15 23:30')
        assert json.loads(estado.read_text())['mercadopago_saldo'] == '2026-01-15'
        C.mp_saldo.bajar.reset_mock()
        assert correr('--solo', 'mercadopago_saldo', '--solo-pendientes') == 0
        C.mp_saldo.bajar.assert_not_called()
        ruta = self.tmp_path / 'mp_saldo.csv'
        anterior = ruta.read_bytes()
        for error in (False, True):
            C.mp_saldo.bajar.return_value = ([], 'faltan saldos inventados')
            C.mp_saldo.bajar.side_effect = C.ml.ErrorDatos('saldo inválido') if error else None
            assert correr('--solo', 'mercadopago_saldo') == 1
            assert ruta.read_bytes() == anterior
            assert not json.loads(control.read_text())['fuentes']['mercadopago_saldo']['ok']

    def test_dolar_solo_sin_perfil_ni_token_y_pendientes(self):
        correr, estado, control = self.corrida
        C.dolar.bajar.return_value = [dict(fecha='2026-01-14', compra='4.00', venta='5.00', fuente='argentinadatos')]
        assert correr('--solo', 'dolar') == 0
        C.dolar.bajar.assert_called_once_with(self.tmp_path, dt.date(2025, 10, 1), dt.date(2026, 1, 14))
        assert json.loads(control.read_text())['fuentes']['dolar'] == dict(
            ok=True, filas=1, desde='2026-01-14', hasta='2026-01-14', motivo='', actualizado='2026-01-15 23:30')
        assert json.loads(estado.read_text()) == {'dolar': '2026-01-15'}
        C.dolar.bajar.reset_mock()
        assert correr('--solo', 'dolar', '--solo-pendientes') == 0
        C.dolar.bajar.assert_not_called()
        C.meli_oauth.access_token.assert_not_called()
        C.galicia.configuracion.assert_not_called()
        assert (self.tmp_path / 'dolar.csv').exists()

    def test_dolar_invalido_deja_csv_igual_y_fuente_en_rojo(self):
        correr, estado, control = self.corrida
        ruta = self.tmp_path / 'dolar.csv'
        ruta.write_bytes(b'archivo anterior\r\n')
        # Usar el lector real con una respuesta inválida, sin llamar a internet.
        C.dolar.bajar.side_effect = lambda *args: bajar_dolar(*args, http=Mock(return_value=(200, b'{}')))
        assert correr('--solo', 'dolar') == 1
        assert ruta.read_bytes() == b'archivo anterior\r\n'
        resumen = json.loads(control.read_text())['fuentes']['dolar']
        assert not resumen['ok'] and resumen['motivo']
        assert not estado.exists()

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
        fuentes = ['mercadolibre', 'mercadopago', 'mercadopago_saldo', 'mercadolibre_publicidad', 'tiendanube', 'galicia', 'dolar']
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
        C.dolar.bajar.assert_not_called()
        assert 'Nada pendiente: todo se bajó bien hoy.' in self.salida.getvalue()


    def habilitar_tn(self):
        self.setattr(C.tn, 'tiene_aplicacion', Mock(return_value=True))
        self.setattr(C.tn, 'estado', Mock(return_value={'hay_token': True}))
        self.setattr(C.tn, 'Sesion', Mock(return_value=Mock(permiso={'store_id': 123})))
        self.setattr(C.tn, 'bajar', Mock(return_value=([], 0)))

    def test_rapida_ignora_estado_y_conserva_pasada_diaria(self):
        correr, estado, control = self.corrida
        self.habilitar_tn()
        estado.parent.mkdir(parents=True)
        estado.write_text('no es json: la rápida ni lo lee')
        antes = estado.stat().st_mtime_ns
        assert correr('--rapida', '--solo-pendientes') == 0
        assert estado.read_text() == 'no es json: la rápida ni lo lee'
        assert estado.stat().st_mtime_ns == antes
        assert C.ml.bajar.call_args.kwargs == {'rapida': True}
        C.tn.bajar.assert_called_once()
        for modulo in (C.mp, C.mp_saldo, C.ads, C.dolar):
            modulo.bajar.assert_not_called()
        assert set(json.loads(control.read_text())['fuentes']) == {'mercadolibre', 'tiendanube'}
        assert (estado.parent / 'mercadopago/liquidaciones/ultima-mercadolibre.json').exists()
        assert (estado.parent / 'tiendanube/cache/ultima.json').exists()
        estado.unlink()
        assert correr('--rapida', '--solo', 'mercadolibre') == 0
        assert not estado.exists()
        assert correr('--solo-pendientes') == 0
        C.mp.bajar.assert_called_once()

    def test_fechas_y_actualizado(self):
        correr, _, control = self.corrida
        self.habilitar_tn()
        C.ml.bajar.return_value = ([dict(fecha_venta='2026-01-15 23:00')], 0)
        assert correr() == 0
        for modulo in (C.ml, C.tn):
            assert modulo.bajar.call_args.args[3] == dt.date(2026, 1, 15)
        assert C.mp.bajar.call_args.args[3] == dt.date(2026, 1, 14)
        for resumen in json.loads(control.read_text())['fuentes'].values():
            assert resumen['actualizado'] == '2026-01-15 23:30'
        assert json.loads(control.read_text())['fuentes']['mercadolibre']['hasta'] == '2026-01-15'

    @unittest.skipIf(C.fcntl is None, 'Windows no usa flock')
    def test_candado_ocupado_no_escribe_y_normal_agota_espera(self):
        correr, _, _ = self.corrida
        with C.candado('ejemplo', False):
            archivos = {p: p.read_bytes() for p in self.tmp_path.rglob('*') if p.is_file()}
            assert correr('--rapida') == 0
            assert archivos == {p: p.read_bytes() for p in self.tmp_path.rglob('*') if p.is_file()}
            with patch.object(C.time, 'monotonic', side_effect=[0, 1200]):
                assert correr() == 1
        assert 'Hay otra bajada en curso; esta se saltea.' in self.salida.getvalue()
        C.ml.bajar.assert_not_called()
        assert correr('--solo', 'mercadolibre') == 0

    def test_aviso_drive_se_guarda_y_se_borra_aun_sin_pendientes(self):
        correr, _, control = self.corrida
        with patch.object(C, 'revisar_drive_escritorio', return_value='Drive cerrado'):
            assert correr('--solo', 'dolar') == 0
        assert json.loads(control.read_text())['aviso_drive'] == 'Drive cerrado'
        with patch.object(C, 'revisar_drive_escritorio', return_value=''):
            assert correr('--solo', 'dolar', '--solo-pendientes') == 0
        assert 'aviso_drive' not in json.loads(control.read_text())

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


    def test_pendientes_rehace_mp_si_ml_se_bajo_en_la_corrida(self):
        correr, estado, control = self.corrida
        # A la mañana MP salió bien con las ventas viejas y ML falló; ahora ML baja bien.
        C.ml.guardar_json(estado, {'mercadopago': '2026-01-15', 'mercadolibre_publicidad': '2026-01-15'})
        nuevas = [dict(id_venta='789', id_pago_mp='999', fecha_venta='2026-01-14')]
        C.ml.bajar.return_value = (nuevas, 0)
        assert correr('--solo-pendientes') == 0
        C.ml.bajar.assert_called_once()
        assert C.mp.bajar.call_args.args[-1] == nuevas
        C.ads.bajar.assert_not_called()

    def test_pendientes_no_rehace_mp_si_ml_falla(self):
        correr, estado, control = self.corrida
        C.ml.guardar_json(estado, {'mercadopago': '2026-01-15', 'mercadolibre_publicidad': '2026-01-15'})
        C.ml.bajar.side_effect = C.ml.ErrorDatos('corte inventado')
        assert correr('--solo-pendientes') == 1
        C.mp.bajar.assert_not_called()


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


class DriveTests(unittest.TestCase):
    def test_revision_sin_procesos_reales(self):
        from ingestas.drive_local import revisar_drive_escritorio
        ruta = Path.home() / 'Library/CloudStorage/GoogleDrive-inventado/My Drive/datos'
        with patch('sys.platform', 'darwin'), patch('subprocess.run') as ejecutar:
            assert revisar_drive_escritorio('/tmp/datos') == ''
            ejecutar.assert_not_called()
            ejecutar.return_value.returncode = 0
            assert revisar_drive_escritorio(ruta) == ''
            assert ejecutar.call_args.args[0] == ['pgrep', '-x', 'Google Drive']
            ejecutar.side_effect = [Mock(returncode=1), Mock(returncode=0)]
            assert 'se volvió a abrir' in revisar_drive_escritorio(ruta)
            assert ejecutar.call_args.args[0] == ['open', '-a', 'Google Drive']
            ejecutar.side_effect = [Mock(returncode=1), Mock(returncode=1)]
            assert 'no se pudo abrir' in revisar_drive_escritorio(ruta)
            ejecutar.side_effect = OSError('fallo inventado')
            assert revisar_drive_escritorio(ruta)
        with patch('sys.platform', 'win32'), patch('subprocess.run') as ejecutar:
            assert revisar_drive_escritorio(ruta) == ''
            ejecutar.assert_not_called()
