"""El buscador mantiene los indicadores y la lista sale de la empresa elegida."""
from dashboard.app import render, JS


def test_buscador_render():
    html = render({'cliente': 'Ejemplo', 'fecha': '2027-01-01', 'unidades': [], 'datos': {}})
    assert 'Buscar cliente…' in html
    assert 'No hay clientes con ese nombre' in html
    assert 'coinciden.slice(0,10)' in html
    assert '<script src=' not in html


def test_lista_de_la_empresa_elegida():
    # Antes la lista salía siempre del consolidado y A y AA mostraban lo mismo.
    assert "var filas=(c.filas||[]).slice();" in JS
    assert "grupo.a_cobrar" not in JS


def test_normalizacion_js():
    # La comprobación de ejecución en navegador se documenta también en la consigna.
    assert ".normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase()" in JS
