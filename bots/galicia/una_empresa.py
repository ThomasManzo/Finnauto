"""El recorrido de una empresa, con nombre y cuenta elegidos en el perfil."""
import re
from bots.galicia.navar import BotGaliciaNavar


def patron_nombre(nombre):
    # Los puntos y espacios cambian entre pantallas; la razón social sigue siendo la misma.
    sin_sociedad = re.sub(
        r'[\s.]+(?:S\.?\s*A\.?|SOCIEDAD\s+AN[OÓ]NIMA)\s*$', '', nombre, flags=re.I)
    base = re.sub(r'[\s.]', '', sin_sociedad).upper()
    if not base:
        raise ValueError('Falta el nombre de la empresa en solo_estas_empresas.')
    letras = r'[\s.]*'.join(re.escape(c) for c in base)
    sociedad = r'(?:S[\s.]*A\.?|SOCIEDAD\s+AN[OÓ]NIMA)'
    return re.compile(r'(?<!\w)' + letras + r'(?:[\s.]*' + sociedad + r')?(?!\w)', re.I)


class BotGaliciaUnaEmpresa(BotGaliciaNavar):
    def __init__(self, cfg):
        nombres = cfg.get('solo_estas_empresas')
        if not isinstance(nombres, list) or not nombres or any(
                not isinstance(n, str) or not n.strip() for n in nombres):
            raise ValueError('Completar solo_estas_empresas con los nombres de la empresa.')
        super().__init__(cfg)
        self.patrones = [(nombre, patron_nombre(nombre)) for nombre in nombres]
        self.patron_empresa = re.compile('|'.join(p.pattern for _, p in self.patrones), re.I)
        self.nombre_empresa = nombres[0]
        self.etiqueta_empresa = nombres[0]

    def capturar_empresa_activa(self, page):
        for nombre, patron in self.patrones:
            coincidencias = page.get_by_text(patron)
            if any(coincidencias.nth(i).is_visible() for i in range(coincidencias.count())):
                return nombre
        return None

    def leer_excel(self, ruta):
        from lector.extractos import leer_planilla_galicia
        return leer_planilla_galicia(ruta, cuenta=self.cuenta)
