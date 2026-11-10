"""Macro: pide movimientos, controla el Excel y recién entonces lo publica."""
import datetime as dt
from decimal import Decimal
from pathlib import Path
import re
import time
import uuid

from bots.base import BotBanco
from bots.bbva.navar import BotBbvaNavar, PATRON_CUIT, PATRON_NAVAR, _esperar_unico, _hay_visible, _visibles
from bots.galicia.navar import CLAVE_ENVIADA_SIN_CONFIRMAR
from lector.extractos import _filas_planilla
from nucleo.log import log, captura
from nucleo.utilidades import _parse_monto


# Pedido de captcha o de código. Ojo: el login de Macro tiene SIEMPRE un cartel antiestafas que dice
# "NO INGRESES TOKEN"; eso no es un pedido. Por eso se busca "ingresá/introducí/escribí (el/tu) código
# o token" (con la "á" del pedido, no la "es" de "ingreses") o "te enviamos ... código".
PATRON_DESAFIO = re.compile(r'\b(ingres[aá]|introduc[ií]|escrib[ií])\s+(el|tu|un|la)?\s*(c[oó]digo|token)'
                            r'|\benviamos\b.{0,40}c[oó]digo|no soy un robot', re.I)


class MotivoMacro(RuntimeError):
    """Error escrito por este bot (no por Playwright): solo describe qué pasó, nunca trae lo tipeado,
    así que se puede mostrar en el log y en el _ESTADO_."""


def digitos(valor):
    return re.sub(r'\D', '', str(valor or ''))


def monto(texto):
    return _parse_monto(str(texto).replace('$', '').replace(' ', ''))


def numero_excel(filas):
    valores = [digitos(r[2]) for r in filas if len(r) > 2 and str(r[0]).strip() == 'Número']
    if len(valores) != 1 or not valores[0]:
        raise ValueError('Falta un único Número de cuenta en el Excel.')
    return valores[0]


def validar_excel(ruta, cuenta, pedido, hoy=None, dias_atras_tolerados=45):
    """No escribe nada: devuelve filas aprobadas y avisos para preparar la copia limpia."""
    hoy = hoy or dt.date.today()
    filas = _filas_planilla(ruta)
    textos = [' '.join(str(c) for c in r if c is not None) for r in filas]
    for titulo in ('Últimos Movimientos', 'CUENTA CORRIENTE BANCARIA'):
        if not any(titulo in t for t in textos):
            raise ValueError('El Excel no es de movimientos de cuenta corriente.')
    if numero_excel(filas) != digitos(cuenta):
        raise ValueError('El Número de cuenta no coincide con el inicio.')
    if not any(str(r[0]).strip() == 'Moneda' and 'PESOS' in t for r, t in zip(filas, textos)):
        raise ValueError('La moneda no es PESOS.')
    empresas = [t for t in textos if t.startswith('Empresa:')]
    cuit = re.match(r'Empresa:\s*([\d-]+)\s*-', empresas[0]) if len(empresas) == 1 else None
    if not cuit or not PATRON_CUIT.fullmatch(cuit[1]):
        raise ValueError('El CUIT del Excel no corresponde a la empresa.')
    pies = [t for t in textos if t.startswith('Fecha de descarga:')]
    if len(pies) != 1:
        raise ValueError('Falta una única Fecha de descarga.')
    fecha = re.search(r'\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}', pies[0])
    if not fecha or dt.datetime.strptime(fecha[0], '%d/%m/%Y %H:%M:%S') < pedido - dt.timedelta(minutes=2):
        raise ValueError('Fecha de descarga anterior al pedido.')
    cabeceras = [i for i, r in enumerate(filas) if 'Fecha' in r and 'Importe' in r and 'Saldo' in r]
    if len(cabeceras) != 1:
        raise ValueError('Falta una única tabla de movimientos.')
    n = cabeceras[0]
    ix = {k: filas[n].index(k) for k in ('Fecha', 'Importe', 'Saldo')}
    movimientos = []
    for i in range(n + 1, len(filas)):
        r = filas[i]
        if textos[i].startswith('Fecha de descarga:'):
            break
        if not any(c not in (None, '') for c in r):
            continue
        f = r[ix['Fecha']]
        if isinstance(f, dt.datetime):
            f = f.date()
        elif not isinstance(f, dt.date):
            f = dt.datetime.strptime(str(f).strip(), '%d/%m/%Y').date()
        importe, saldo = (Decimal(str(r[ix[k]])) for k in ('Importe', 'Saldo'))
        if not importe.is_finite() or not saldo.is_finite():
            raise ValueError('Importe o saldo inválido.')
        if f < hoy - dt.timedelta(days=dias_atras_tolerados):
            raise ValueError('Movimiento demasiado viejo.')
        movimientos.append((i, f, importe, saldo))
    for nuevo, viejo in zip(movimientos, movimientos[1:]):
        if nuevo[1] < viejo[1]:
            raise ValueError('Los movimientos no están del más nuevo al más viejo.')
        if nuevo[3].quantize(Decimal('.01')) != (viejo[3] + nuevo[2]).quantize(Decimal('.01')):
            raise ValueError('La cadena de saldos no cierra al centavo.')
    futuros = [m for m in movimientos if m[1] > hoy]
    quedan = [m for m in movimientos if m[1] <= hoy]
    quitar = {m[0] for m in futuros}
    avisos = []
    if futuros:
        avisos.append('Se apartaron %d movimientos futuros; fechas: %s; suma de importes: %.2f.' % (
            len(futuros), ', '.join(sorted({m[1].isoformat() for m in futuros})), sum(m[2] for m in futuros)))
    return dict(filas=[r for i, r in enumerate(filas) if i not in quitar], movimientos=quedan,
                futuros=len(futuros), avisos=avisos, cuenta=numero_excel(filas))


def elegir_fila(filas, pedido):
    """Cada fila contiene las seis celdas de la bandeja. Empates se rechazan por seguridad."""
    candidatas = []
    for i, c in enumerate(filas):
        if len(c) < 6 or c[0].strip() != 'Últimos Movimientos' or c[2].strip().lower() != 'xls':
            continue
        try:
            fecha = dt.datetime.strptime(c[3].strip(), '%d/%m/%Y %H:%M')
        except ValueError:
            continue
        if fecha >= pedido.replace(second=0, microsecond=0) - dt.timedelta(minutes=2):
            candidatas.append((fecha, i))
    if not candidatas:
        return None
    ultima = max(f for f, _ in candidatas)
    indices = [i for f, i in candidatas if f == ultima]
    if len(indices) != 1:
        raise ValueError('Bandeja ambigua: más de una fila del mismo pedido.')
    i = indices[0]
    return i if filas[i][5].strip() == 'Finalizado' else None


def ajustar_saldo(saldos, datos, avisos):
    """El núcleo conserva este mismo diccionario: corregimos antes de que escriba _SALDOS_."""
    ultimo = datos['movimientos'][0][3] if datos['movimientos'] else None
    actual = saldos.get('actual')
    if ultimo is None or actual is None or Decimal(str(actual)).quantize(Decimal('.01')) != ultimo.quantize(Decimal('.01')):
        saldos['actual'] = None
        avisos.append('Saldo de pantalla sin confirmar contra los movimientos publicados; saldo_actual queda vacío.')


class BotMacroNavar(BotBanco):
    nombre = 'Macro'
    url = 'https://www.macro.com.ar/biempresas/'

    def __init__(self, cfg):
        self.clave_empresa = None
        self.cuenta = None
        self.prefijo = cfg.get('prefijo_archivo', 'Movimientos Macro')
        self.dias = cfg.get('dias_atras_tolerados', 45)
        self.avisos = []
        self.saldos = {}
        self.saldo_inicio = None
        self.intento_login = False

    @staticmethod
    def unico(page, selector, timeout):
        # La descripción lleva el selector (es nuestro, no trae datos): así el log dice QUÉ no encontró.
        return _esperar_unico(page, [lambda m: m.locator(selector)], 'el elemento %s' % selector[:70], timeout)

    @staticmethod
    def frenar_desafio(page):
        # El cartel NO INGRESES TOKEN no es un desafío. Buscamos campos o pedidos explícitos.
        if _hay_visible(page, lambda m: m.locator('input')):
            for marco in page.frames:
                for campo in _visibles(marco.locator('input')):
                    descripcion = ' '.join(campo.get_attribute(a) or '' for a in ('id', 'name', 'placeholder', 'aria-label'))
                    if re.search(r'token|captcha|otp|sms|c[oó]digo.*seguridad', descripcion, re.I):
                        raise MotivoMacro('Macro pide captcha o segundo factor; continuar manualmente.')
        if _hay_visible(page, lambda m: m.get_by_text(PATRON_DESAFIO)):
            raise MotivoMacro('Macro pide captcha o segundo factor; continuar manualmente.')
        if _hay_visible(page, lambda m: m.locator('iframe[src*="captcha"]')):
            raise MotivoMacro('Macro muestra captcha; continuar manualmente.')

    def hacer_login(self, page, usuario, clave, timeout):
        enviado = False
        accion = 'empezando'
        paso = 'usuario'
        try:
            if self.intento_login:
                raise MotivoMacro('Ya se intentó entrar en esta corrida.')
            self.intento_login = True
            if not self.clave_empresa:
                raise MotivoMacro('Falta clave empresa; ejecutar setup_credenciales.py --cliente navar --banco macro')
            accion = 'abriendo la página'
            page.goto(self.url, timeout=timeout)
            self.frenar_desafio(page)
            accion = 'buscando el campo Usuario y su botón'
            # Relevado el 10/11/2026: el usuario se tipea OCULTO (campo de tipo clave, como en BBVA):
            # input#textField1, placeholder "Usuario Banca Empresas", etiqueta "Ingresá tu usuario",
            # y el botón es "CONTINUAR" (button#processCustomerLogin). Al lado del campo hay un botón
            # de ojito sin texto ("show-pass") que NO hay que tocar.
            campo = _esperar_unico(page, [lambda m: m.locator('input#textField1'),
                lambda m: m.locator('input[placeholder="Usuario Banca Empresas"]')], 'campo Usuario', timeout)
            boton = _esperar_unico(page, [lambda m: m.locator('button#processCustomerLogin'),
                lambda m: m.get_by_role('button', name=re.compile(r'^\s*Continuar\s*$', re.I))], 'botón Continuar', timeout)
            accion = 'cargando el usuario'
            campo.fill(usuario, timeout=timeout)
            boton.click(timeout=timeout)
            paso = 'contraseña'
            accion = 'esperando el campo de la contraseña'
            campo = self.unico(page, 'input#login_textField2[type=password]', timeout)
            boton = self.unico(page, 'button#processSystem_UserLogin', timeout)
            self.frenar_desafio(page)
            accion = 'cargando la contraseña'
            campo.fill(clave, timeout=timeout)
            enviado = True
            boton.click(timeout=timeout)
            paso = 'clave empresa'
            accion = 'esperando el campo de la clave empresa'
            campo = self.unico(page, 'input#login_textField1[type=password]', timeout)
            boton = self.unico(page, 'button#actionButtonInit2', timeout)
            self.frenar_desafio(page)
            if not self.capturar_empresa_activa(page):
                raise MotivoMacro('No se confirmó la empresa NAVAR SA en la pantalla de la clave empresa.')
            accion = 'cargando la clave empresa'
            campo.fill(self.clave_empresa, timeout=timeout)
            boton.click(timeout=timeout)
            paso = 'inicio'
            accion = 'esperando la tabla de cuentas del inicio'
            self.unico(page, 'table#collectionTableCuentas', timeout)
            self.frenar_desafio(page)
            if not self.capturar_empresa_activa(page) or _hay_visible(page, lambda m: m.locator('input[type=password]')):
                raise MotivoMacro('Inicio no confirmado.')
        except Exception as e:
            # Del error solo se muestra el texto si lo escribió este bot (MotivoMacro). De cualquier otro
            # (Playwright puede incluir lo tipeado) se muestra únicamente qué se estaba haciendo.
            detalle = str(e)[:150] if isinstance(e, MotivoMacro) else accion
            # Playwright puede incluir valores tipeados en sus errores. No propagamos ese texto.
            # El núcleo saca una foto al fallar: cerrar la pestaña impide fotografiar secretos.
            try:
                page.close()
            except Exception:
                # Si la pestaña no responde, cerrar su navegador también impide la captura.
                page.context.close()
            marca = CLAVE_ENVIADA_SIN_CONFIRMAR + ': ' if enviado else ''
            raise RuntimeError(marca + 'Macro no confirmó el paso ' + paso + ' (' + detalle + '); revisar '
                               'formulario o segundo factor. No se reintentó.') from None

    def capturar_empresa_activa(self, page):
        return 'NAVAR SA' if _hay_visible(page, lambda m: m.get_by_text(PATRON_NAVAR)) else None

    def descubrir_empresas(self, page, timeout, excluir, solo=None):
        return []

    def cambiar_a_empresa(self, page, nombre, timeout):
        raise RuntimeError('Macro trabaja con una sola empresa.')

    def ir_a_cuenta(self, page, timeout):
        if not self.capturar_empresa_activa(page):
            raise RuntimeError('Empresa no confirmada.')
        # Solo cerramos carteles por su cruz o botón de cierre, nunca sus propuestas.
        cierres = _visibles(page.locator('[role=dialog] button[aria-label*="Cerrar"], .modal:visible .close, .ui-dialog-titlebar-close:visible'))
        if len(cierres) > 1:
            raise RuntimeError('Hay más de un cierre de cartel.')
        if cierres:
            cierres[0].click(timeout=timeout)
        # 10/11/2026: buscar la FILA por su texto encontró 3 (la tabla tiene filas adentro de filas).
        # Se busca la celda de la cuenta, que es una sola, y de ahí su propia fila (el tr que la contiene).
        celda = self.unico(page, 'td#collectionTableCuentas_ON-REGISTER', timeout)
        self.cuenta, self.saldo_inicio = None, None
        try:
            textos = celda.locator('xpath=ancestor::tr[1]/td').all_inner_texts()
            numeros = [digitos(t) for t in textos if re.fullmatch(r'[\d\s-]{8,}', t.strip())]
            montos = [t.strip() for t in textos if '$' in t]
            if len(numeros) == 1:
                self.cuenta = numeros[0]
            if len(montos) == 1:
                self.saldo_inicio = montos[0]
        except Exception as e:
            log('   Aviso: no pude leer la fila de la cuenta en el inicio (%s); sigo con el detalle.' % type(e).__name__)
        celda.click(timeout=timeout)
        self.confirmar_cuenta(page, timeout)

    def confirmar_cuenta(self, page, timeout):
        """Confirma que se está adentro de la cuenta corriente. El Número del detalle es el que vale
        (se compara después con el del Excel); si también se leyó en el inicio, tienen que coincidir."""
        self.unico(page, 'p[role=heading]:text-is("CUENTA CORRIENTE BANCARIA")', timeout)
        self.unico(page, 'button#logMov', timeout)
        self.unico(page, 'table#collectionTableMovimientos', timeout)
        numero = digitos(self.unico(page, 'xpath=//*[normalize-space(text())="Número"]/following-sibling::*[1]', timeout).inner_text())
        if len(numero) < 8:
            raise MotivoMacro('No pude leer el Número de la cuenta en el detalle.')
        if self.cuenta is None:
            self.cuenta = numero
        elif numero != self.cuenta:
            raise MotivoMacro('La cuenta abierta no coincide con la del inicio.')

    def capturar_saldos(self, page):
        self.saldos = dict(actual=None, actual_texto=self.saldo_inicio, disponible=None, disponible_texto=None)
        for clave, etiqueta in (('actual', 'Saldo disponible'), ('disponible', 'SALDO A GIRAR'), ('acuerdo', 'ACUERDO')):
            try:
                texto = self.unico(page, 'xpath=//*[normalize-space(text())="%s"]/following-sibling::*[1]' % etiqueta, 1500).inner_text()
                if clave == 'acuerdo':
                    log('   Acuerdo: %s' % texto)
                else:
                    self.saldos[clave + '_texto'] = texto
            except Exception:
                log('   No pude leer %s.' % etiqueta)
        for clave in ('actual', 'disponible'):
            self.saldos[clave] = monto(self.saldos[clave + '_texto'])
        return self.saldos

    def aplicar_filtro_fechas(self, page, desde, hasta, timeout):
        return True

    def _bandeja(self, page, pedido, timeout):
        boton = _esperar_unico(page, [lambda m: m.get_by_text('IR A BANDEJA DE DESCARGAS', exact=True)], 'ir a bandeja', min(timeout, 5000)) if _hay_visible(page, lambda m: m.get_by_text('IR A BANDEJA DE DESCARGAS', exact=True)) else None
        if boton:
            boton.click(timeout=timeout)
        else:
            for texto in ('Más', 'Consultas y solicitudes', 'Bandeja de descargas'):
                _esperar_unico(page, [lambda m, t=texto: m.get_by_text(t, exact=True)], texto, timeout).click(timeout=timeout)
        _esperar_unico(page, [lambda m: m.get_by_text('Bandeja de Descargas', exact=True)], 'título bandeja', timeout)
        limite = time.monotonic() + 180
        while True:
            tabla = self.unico(page, 'table:has-text("Fecha de inicio"):has-text("Estado")', timeout)
            filas = tabla.locator('tr').all()
            textos = [f.locator('td').all_inner_texts() for f in filas]
            try:
                indice = elegir_fila(textos, pedido)
                if indice is not None:
                    botones = _visibles(filas[indice].locator('td').nth(5).locator('a, button, input[type=image], [role=button]'))
                    if len(botones) != 1:
                        raise ValueError('No hay una única flecha de descarga en Estado.')
                    return botones[0]
            except ValueError:
                captura(page, 'ERROR_bandeja_ambigua')
                raise
            if time.monotonic() >= limite:
                captura(page, 'ERROR_bandeja_demora')
                raise RuntimeError('Macro no finalizó el pedido en 180 segundos.')
            page.wait_for_timeout(10000)
            _esperar_unico(page, [lambda m: m.get_by_role('button', name=re.compile('recargar|actualizar', re.I)),
                lambda m: m.locator('[title*="Recargar"], [title*="Actualizar"]')], 'recargar bandeja', timeout).click(timeout=timeout)

    def descargar_csv(self, page, carpeta_destino, nombre_empresa, timeout, ctx):
        try:
            if nombre_empresa != 'NAVAR SA':
                raise RuntimeError('Empresa no confirmada.')
            for viejo in Path(ctx.descargas_dir).glob('macro_por_validar_*'):
                if viejo.is_file() and viejo.stat().st_mtime < time.time() - 7 * 86400:
                    viejo.unlink()
            self.confirmar_cuenta(page, timeout)
            pedido = dt.datetime.now()
            self.unico(page, '#actionButtonDescargaXlsCuentas', timeout).click(timeout=timeout)
            flecha = self._bandeja(page, pedido, timeout)
            with page.expect_download(timeout=timeout) as info:
                flecha.click(timeout=timeout)
            descarga = info.value
            if Path(descarga.suggested_filename).suffix.lower() != '.xls':
                raise ValueError('Macro no entregó el XLS esperado.')
            temporal = Path(ctx.descargas_dir) / ('macro_por_validar_' + uuid.uuid4().hex + '.xls')
            descarga.save_as(str(temporal))
            datos = validar_excel(temporal, self.cuenta, pedido, dias_atras_tolerados=self.dias)
            self.avisos.extend(datos['avisos'])
            ajustar_saldo(self.saldos, datos, self.avisos)
            if not datos['movimientos']:
                self.avisos.append('Sin novedades: no quedaron movimientos para publicar.')
                return None
            original = temporal
            if datos['futuros']:
                from openpyxl import Workbook
                temporal = temporal.with_suffix('.xlsx')
                wb = Workbook()
                for fila in datos['filas']:
                    wb.active.append(list(fila))
                wb.save(temporal)
                wb.close()
            destino = BotBbvaNavar.publicar(str(temporal), carpeta_destino, '%s %s%s' % (self.prefijo, dt.date.today(), temporal.suffix))
            temporal.unlink()
            if original != temporal:
                original.unlink()
            return destino
        finally:
            self.salir(page)

    def salir(self, page):
        """Aprieta "Salir" una sola vez. La llama la descarga al terminar y también el núcleo al final
        de la corrida, aunque haya fallado antes (10/11/2026): si la sesión queda abierta, Macro no
        deja volver a entrar por unos 10 minutos."""
        if getattr(self, 'salio', False) or not self.intento_login or page.is_closed():
            return
        self.salio = True
        try:
            self.unico(page, 'a#widgetLogoutBtn', 3000).click(timeout=3000)
            page.wait_for_timeout(1500)
            log('   Salí de Macro.')
        except Exception:
            log('   Aviso: no pude confirmar la salida de Macro.')

    def extraer_cuenta_id(self, archivo_csv):
        return numero_excel(_filas_planilla(archivo_csv)) if archivo_csv else self.cuenta
