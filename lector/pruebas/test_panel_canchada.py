"""El apartado se habilita por perfil y funciona sin dependencias externas de JS."""
from dashboard.app import render
from dashboard.datos import opciones_tablero


def paquete(marca):
    return {"cliente": "Ejemplo", "fecha": "2027-01-01", "unidades": [], "datos": {},
            "tablero": {"escenario_canchada": marca}}


def test_panel_se_habilita_por_marca():
    html = render(paquete(True))
    assert 'data-capa="canchada"' in html
    assert "Compra de canchada" in html
    assert "function verCanchada()" in html
    assert "este apartado funciona desde el link del tablero" in html
    assert '<script src=' not in html
    assert html.index('data-capa="hallazgos"') < html.index('data-capa="canchada"')


def test_sin_marca_no_hay_apartado():
    html = render(paquete(False))
    assert 'data-capa="canchada"' not in html
    assert 'function verCanchada()' not in html
    assert '<script src=' not in html


def test_la_marca_se_lee_del_perfil(monkeypatch):
    from nucleo import config
    monkeypatch.setattr(config, "cargar_perfil", lambda *args: {"tablero": {"escenario_canchada": True}})
    assert opciones_tablero("ejemplo")["escenario_canchada"] is True
    monkeypatch.setattr(config, "cargar_perfil", lambda *args: {})
    assert opciones_tablero("otro") == {}
