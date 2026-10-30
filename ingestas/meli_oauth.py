# -*- coding: utf-8 -*-
"""Permiso por link para Mercado Libre y Mercado Pago.

Uso: python -m ingestas.meli_oauth --cliente ejemplo --fuente mercadolibre link
Luego usar canjear, estado o probar. Cada fuente tiene su propia aplicación,
cargada con setup_credenciales.py. El código dura diez minutos y se usa una vez.
No usamos PKCE; la dirección de vuelta debe coincidir con la de la aplicación.
Los tokens viven solamente en el llavero. Las bajadas llaman access_token():
renueva cerca del vencimiento y guarda el refresh nuevo antes de devolver nada.
El candado evita que dos bajadas gasten el mismo refresh. No reintentamos un
canje automáticamente: si la respuesta se pierde, puede haberse usado ya.
"""

import argparse
import contextlib
import datetime
import io
import json
import math
import os
from pathlib import Path
import re
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from nucleo import credenciales

BASE_REPO = Path(__file__).resolve().parents[1]
REDIRECT_POR_DEFECTO = "https://thomasmanzo.github.io/Finnauto/autorizado/"
FUENTES = {
    "mercadolibre": {
        "autorizacion": "https://auth.mercadolibre.com.ar/authorization",
        "token": "https://api.mercadolibre.com/oauth/token",
        "usuario": "https://api.mercadolibre.com/users/me",
        "formato": "form", "platform_id": None, "prefijo": "ml",
    },
    "mercadopago": {
        "autorizacion": "https://auth.mercadopago.com/authorization",
        "token": "https://api.mercadopago.com/oauth/token",
        "usuario": "https://api.mercadopago.com/users/me",
        "formato": "json", "platform_id": "mp", "prefijo": "mp",
    },
}
FALTAN_CREDENCIALES = "faltan las credenciales de la aplicación: correr setup_credenciales.py"
SIN_TOKEN = "todavía no autorizó: mandar el link"
MOTIVOS = {
    "invalid_grant": "el permiso venció o lo revocaron: hay que mandar el link de nuevo",
    "invalid_operator_user_id": "autorizó con la cuenta de un colaborador: tiene que entrar con la cuenta principal",
}
# UTC-3 no necesita instalar tzdata en Windows para mostrar la hora argentina.
HORA_BA = datetime.timezone(datetime.timedelta(hours=-3), "Buenos Aires")


class ErrorAutorizacion(Exception):
    def __init__(self, motivo):
        self.motivo = motivo
        super().__init__(motivo)


def _validar(cliente, fuente):
    if fuente not in FUENTES:
        raise ErrorAutorizacion("fuente desconocida: usar mercadolibre o mercadopago")
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", cliente):
        raise ErrorAutorizacion("cliente inválido: usar letras, números, guiones o guion bajo")
    return FUENTES[fuente]


def _aplicacion(cliente, fuente):
    _validar(cliente, fuente)
    # El lector compartido imprime errores del backend. Los tapamos acá para
    # que una excepción del llavero nunca termine mostrando una clave.
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            usuario, clave = credenciales.cargar(BASE_REPO, cliente, fuente)
        if not usuario or not clave:
            raise ValueError()
        return str(usuario), str(clave)
    except (Exception, SystemExit):
        raise ErrorAutorizacion(FALTAN_CREDENCIALES) from None


def _llavero():
    import keyring
    return keyring


def _leer(cliente, fuente):
    _validar(cliente, fuente)
    try:
        crudo = _llavero().get_password(f"finauto:{cliente}:{fuente}-token", "token")
        if crudo is None:
            return None
        dato = json.loads(crudo)
        if not (isinstance(dato["access_token"], str) and dato["access_token"]
                and isinstance(dato["refresh_token"], str) and dato["refresh_token"]
                and isinstance(dato["scope"], str)
                and isinstance(dato["vence"], (int, float))
                and math.isfinite(dato["vence"])):
            raise ValueError()
        return dato
    except Exception:
        raise ErrorAutorizacion("no se pudo leer el permiso del llavero: revisar el llavero o volver a autorizar") from None


def _guardar(cliente, fuente, respuesta):
    try:
        obtenido = time.time()
        duracion = float(respuesta["expires_in"])
        if not math.isfinite(duracion) or duracion <= 0:
            raise ValueError()
        for campo in ("access_token", "refresh_token"):
            if not isinstance(respuesta[campo], str) or not respuesta[campo]:
                raise ValueError()
        if not isinstance(respuesta["scope"], str):
            raise ValueError()
        datetime.datetime.fromtimestamp(obtenido + duracion - 60, HORA_BA)
        dato = {k: respuesta[k] for k in ("access_token", "refresh_token", "user_id", "scope")}
        dato.update(vence=obtenido + duracion - 60, obtenido=obtenido)
        serializado = json.dumps(dato)
    except (KeyError, TypeError, ValueError, OverflowError, OSError):
        raise ErrorAutorizacion("respuesta de autorización incompleta: hay que mandar el link de nuevo") from None
    try:
        _llavero().set_password(f"finauto:{cliente}:{fuente}-token", "token", serializado)
    except Exception:
        raise ErrorAutorizacion("no se pudo guardar el permiso nuevo en el llavero: hay que mandar el link de nuevo") from None
    return dato


def link_autorizacion(cliente, fuente, redirect=REDIRECT_POR_DEFECTO):
    usuario, _ = _aplicacion(cliente, fuente)
    config = FUENTES[fuente]
    parametros = dict(response_type="code", client_id=usuario, redirect_uri=redirect,
                      state=config["prefijo"] + "-" + secrets.token_hex(4))
    if config["platform_id"]:
        parametros["platform_id"] = config["platform_id"]
    return config["autorizacion"] + "?" + urllib.parse.urlencode(parametros, quote_via=urllib.parse.quote, safe="")


def limpiar_codigo(texto, fuente=None):
    """La fuente opcional permite comprobar la marca antes de gastar el código."""
    codigo = re.sub(r"\s+", "", texto)
    marca = re.match(r"^(ML|MP):", codigo, re.I)
    if fuente is not None and fuente not in FUENTES:
        raise ErrorAutorizacion("fuente desconocida: usar mercadolibre o mercadopago")
    if marca:
        if fuente and marca[1].lower() != FUENTES[fuente]["prefijo"]:
            raise ErrorAutorizacion("el prefijo del código no corresponde a la fuente elegida")
        codigo = codigo[marca.end():]
    if not codigo:
        raise ErrorAutorizacion("falta el código de autorización")
    return codigo


class _SinRedireccion(urllib.request.HTTPRedirectHandler):
    # No reenviar claves ni el encabezado Bearer a otra dirección.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _http(pedido):
    with urllib.request.build_opener(_SinRedireccion()).open(pedido, timeout=20) as respuesta:
        return json.load(respuesta)


def _pedir(pedido, secretos=()):
    try:
        resultado = _http(pedido)
        if not isinstance(resultado, dict):
            raise ValueError()
        return resultado
    except urllib.error.HTTPError as exc:
        try:
            datos = json.loads(exc.read())
            error = str(datos.get("error", ""))
            mensaje = str(datos.get("message", ""))
        except (ValueError, AttributeError, OSError):
            error, mensaje = "", ""
        if error in MOTIVOS:
            raise ErrorAutorizacion(MOTIVOS[error]) from None
        detalle = f"HTTP {exc.code}: {error} {mensaje}".strip()
        # Algunos servidores repiten valores recibidos en sus errores.
        for secreto in sorted((s for s in secretos if s), key=len, reverse=True):
            for variante in (secreto, urllib.parse.quote(secreto, safe=""), urllib.parse.quote_plus(secreto)):
                detalle = detalle.replace(variante, "[oculto]")
        detalle = re.sub(r"(?:APP_USR-|TG-)[\w-]+", "[oculto]", detalle)
        raise ErrorAutorizacion(detalle) from None
    except (OSError, ValueError):
        raise ErrorAutorizacion("no se pudo consultar la autorización: revisar la conexión y el servicio") from None


def _token(cliente, fuente, parametros):
    usuario, clave = _aplicacion(cliente, fuente)
    parametros = dict(parametros, client_id=usuario, client_secret=clave)
    config = FUENTES[fuente]
    if config["formato"] == "json":
        cuerpo = json.dumps(parametros).encode("utf-8")
        tipo = "application/json"
    else:
        cuerpo = urllib.parse.urlencode(parametros).encode("utf-8")
        tipo = "application/x-www-form-urlencoded"
    pedido = urllib.request.Request(config["token"], data=cuerpo,
                                    headers={"Content-Type": tipo, "Accept": "application/json"})
    respuesta = _pedir(pedido, [clave, parametros.get("code"), parametros.get("refresh_token")])
    return _guardar(cliente, fuente, respuesta)


@contextlib.contextmanager
def _candado(cliente, fuente):
    _validar(cliente, fuente)
    ruta = BASE_REPO / "clientes" / cliente / ".run" / fuente / "token.lock"
    limite = time.monotonic() + 30
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        while True:
            try:
                fd = os.open(ruta, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                identidad = os.fstat(fd)
                os.close(fd)
                break
            except FileExistsError:
                try:
                    if time.time() - ruta.stat().st_mtime > 120:
                        ruta.unlink()
                        continue
                except FileNotFoundError:
                    continue
                if time.monotonic() >= limite:
                    raise ErrorAutorizacion("otro programa está renovando el permiso: volver a intentar")
                time.sleep(0.1)
    except OSError:
        raise ErrorAutorizacion("no se pudo crear el candado del permiso: revisar la carpeta del cliente") from None
    try:
        yield
    finally:
        # Si alguien recuperó un candado abandonado, no borrar el suyo al salir.
        try:
            actual = ruta.stat()
            if (actual.st_ino, actual.st_mtime_ns) == (identidad.st_ino, identidad.st_mtime_ns):
                ruta.unlink()
        except FileNotFoundError:
            pass


def _resumen(dato):
    if dato is None:
        return dict(hay_token=False, user_id=None, scope=None, vence=None, offline_access=False)
    return dict(hay_token=True, user_id=dato["user_id"], scope=dato["scope"],
                vence=datetime.datetime.fromtimestamp(dato["vence"], HORA_BA).isoformat(),
                offline_access="offline_access" in dato["scope"].split())


def canjear_codigo(cliente, fuente, codigo, redirect=REDIRECT_POR_DEFECTO):
    _validar(cliente, fuente)
    codigo = limpiar_codigo(codigo, fuente)
    with _candado(cliente, fuente):
        dato = _token(cliente, fuente, dict(grant_type="authorization_code", code=codigo, redirect_uri=redirect))
    return _resumen(dato)


def access_token(cliente, fuente):
    dato = _leer(cliente, fuente)
    if dato is None:
        raise ErrorAutorizacion(SIN_TOKEN)
    if dato["vence"] - time.time() >= 600:
        return dato["access_token"]
    with _candado(cliente, fuente):
        # Mientras esperábamos, otra bajada puede haber dejado un permiso nuevo.
        dato = _leer(cliente, fuente)
        if dato is None:
            raise ErrorAutorizacion(SIN_TOKEN)
        if dato["vence"] - time.time() < 600:
            dato = _token(cliente, fuente, dict(grant_type="refresh_token", refresh_token=dato["refresh_token"]))
        return dato["access_token"]


def estado(cliente, fuente):
    return _resumen(_leer(cliente, fuente))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Autorización de Mercado Libre y Mercado Pago")
    parser.add_argument("--cliente", required=True)
    parser.add_argument("--fuente", required=True, choices=FUENTES)
    parser.add_argument("--redirect", default=REDIRECT_POR_DEFECTO)
    sub = parser.add_subparsers(dest="comando", required=True)
    for nombre in ("link", "canjear", "estado", "probar"):
        comando = sub.add_parser(nombre)
        comando.add_argument("--redirect", default=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        if args.comando == "link":
            print(link_autorizacion(args.cliente, args.fuente, args.redirect))
        elif args.comando == "canjear":
            print("El código vence a los 10 minutos y se usa una sola vez.")
            dato = canjear_codigo(args.cliente, args.fuente, input("Código: "), args.redirect)
            print(f"Listo: autorizado el usuario {dato['user_id']}. Vence {dato['vence']}.")
        elif args.comando == "estado":
            print(json.dumps(estado(args.cliente, args.fuente), ensure_ascii=False))
        else:
            token = access_token(args.cliente, args.fuente)
            pedido = urllib.request.Request(FUENTES[args.fuente]["usuario"],
                                            headers={"Authorization": "Bearer " + token, "Accept": "application/json"})
            dato = _pedir(pedido, [token])
            print(json.dumps({k: dato.get(k) for k in ("id", "nickname")}, ensure_ascii=False))
        return 0
    except ErrorAutorizacion as exc:
        print(exc.motivo, file=sys.stderr)
        return 1
    except (EOFError, KeyboardInterrupt):
        print("Autorización cancelada.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    for salida in (sys.stdout, sys.stderr):
        if hasattr(salida, "reconfigure"):
            salida.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
