"""Controles con un Excel inventado; no entra al banco ni toca el llavero."""
import unittest
import datetime as dt
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from openpyxl import Workbook
from bots.galicia.navar import BotGaliciaNavar
from bots.galicia.bot import BotGalicia

class PruebaNavar(unittest.TestCase):
    def test_controles_sin_banco(self):
        from orquestador.correr import correr_banco
        base = Path(__file__).resolve().parents[2]
        cfg=json.loads((base / 'clientes/navar/perfil.json').read_text())['bancos']['galicia']
        bot=BotGaliciaNavar(cfg)
        bot.rango=(dt.date(2026,9,22),dt.date(2026,9,23))
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'inventado.xlsx'
            def escribir(cuenta=cfg['cuenta'], fecha=dt.datetime(2026,9,23), encabezado='Créditos'):
                w=Workbook(); s=w.active; s.append([cuenta]); s.append(['Fecha','Descripción','Débitos',encabezado,'Saldo']); s.append([fecha,'Ejemplo inventado',0,100,100]); w.save(p)
            escribir(); datos=bot.validar_excel(p); assert len(datos['movimientos'])==1 and datos['movimientos'][0]['importe']==100
            for kwargs in ({'cuenta':'9999999-9 999-9'},{'fecha':dt.datetime(2026,9,24)},{'encabezado':'No es crédito'}):
                escribir(**kwargs)
                try: bot.validar_excel(p)
                except (RuntimeError, ValueError): pass
                else: raise AssertionError(kwargs)
        with patch.object(BotGalicia,'aplicar_filtro_fechas',return_value=False):
            try: bot.aplicar_filtro_fechas(None,dt.date.today(),dt.date.today(),10)
            except RuntimeError: pass
            else: raise AssertionError('Aceptó fechas sin verificar')
        assert bot.rango is None
        with patch('orquestador.correr._cred.cargar',side_effect=AssertionError('Tocó llavero')):
            try: correr_banco('navar','galicia')
            except SystemExit as e: assert 'carpeta_drive_destino' in str(e)
            else: raise AssertionError('Aceptó ruta vacía')
        with patch.object(BotGalicia,'capturar_empresa_activa',return_value='NAVAR S.A.'):
            assert bot.capturar_empresa_activa(None)=='NAVAR SA'

if __name__ == "__main__":
    unittest.main()
