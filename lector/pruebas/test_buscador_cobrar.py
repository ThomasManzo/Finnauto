"""El buscador mantiene los indicadores y reúne las empresas sin duplicar GRUPO."""
from dashboard.app import render, JS


def test_buscador_render():
    html = render({'cliente': 'Ejemplo', 'fecha': '2027-01-01', 'unidades': [], 'datos': {}})
    assert 'Buscar cliente…' in html
    assert 'No hay clientes con ese nombre' in html
    assert 'coinciden.slice(0,10)' in html
    assert 'grupo.a_cobrar.filas.slice()' in html
    assert '<script src=' not in html


def test_normalizacion_js():
    # La comprobación de ejecución en navegador se documenta también en la consigna.
    assert ".normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase()" in JS
