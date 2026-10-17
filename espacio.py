#!/usr/bin/env python3
"""Baja la última copia guardada de Void, dice si tu ordenador está al día y sube tus commits, con tu código y sin
navegador. Python 3.8+."""
import argparse
import getpass
import gzip
import hashlib
import http.cookiejar
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile
import urllib.error
import urllib.request
import warnings

import turno

SERVIDOR = 'https://vaultvoid.app'
MAX_ARCHIVO = 128 * 1024 * 1024
MAX_CLARO = 200 * 1024 * 1024
MAX_ENTRADAS = 100000
RE_CODIGO = re.compile(r'vr_[0-9a-f]{64}')
RE_KIT = re.compile(r'vk_[0-9a-f]{64}')


class Fallo(ValueError):
    """Mensaje controlado, sin el cuerpo remoto ni valores privados."""


class SinRedireccion(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise Fallo('Void devolvió una redirección. No se envían credenciales a otro destino.')


def _privado(ruta):
    return os.fdopen(os.open(str(ruta), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb')


def _git(carpeta, *args):
    entorno = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    entorno.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                   GIT_CONFIG_SYSTEM=os.devnull, GIT_ATTR_NOSYSTEM='1',
                   GIT_NO_REPLACE_OBJECTS='1', GIT_NO_LAZY_FETCH='1')
    r = subprocess.run(['git', '-C', str(carpeta), '-c', 'core.hooksPath=' + os.devnull,
                        '-c', 'core.fsmonitor=false', '-c', 'submodule.recurse=false'] + list(args),
                       env=entorno, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode:
        raise Fallo('La copia no tiene una historia Git completa y legible. Se conserva el archivo descargado.')
    return r.stdout


def _ruta(miembro):
    nombre = miembro.name
    if nombre in ('.', './') and miembro.isdir():
        return None
    if nombre.startswith('./'):
        nombre = nombre[2:]
    nombre = nombre.rstrip('/') if miembro.isdir() else nombre
    partes = nombre.split('/')
    if (not nombre or re.search(r'[\\\x00-\x1f\x7f]', nombre)
            or any(p in ('', '.', '..') or ':' in p for p in partes)):
        raise Fallo('La copia contiene una ruta insegura; no se extrae.')
    if not (miembro.isfile() or miembro.isdir()) or miembro.issparse():
        raise Fallo('La copia contiene enlaces o archivos especiales; se conserva el archivo sin extraer.')
    if (nombre in ('.git/commondir', '.git/shallow', '.git/info/grafts', '.git/objects/info/alternates',
                   '.git/objects/info/http-alternates')
            or nombre == '.git/worktrees' or nombre.startswith('.git/worktrees/')
            or nombre == '.git/refs/replace' or nombre.startswith('.git/refs/replace/')):
        raise Fallo('La historia depende de otras rutas o reemplaza objetos; no se extrae automáticamente.')
    return nombre


def _git_necesario(ruta):
    """La configuración y los hooks recibidos quedan solo en el tar original, sin ejecutarse."""
    if ruta in ('.git/HEAD', '.git/index', '.git/packed-refs'):
        return True
    if ruta.startswith(('.git/refs/heads/', '.git/refs/tags/')):
        return True
    return bool(re.fullmatch(r'\.git/objects/(?:[0-9a-f]{2}/(?:[0-9a-f]{38}|[0-9a-f]{62})|'
                             r'pack/pack-[0-9a-f]{40,64}\.(?:pack|idx|rev))', ruta))


def extraer(archivo, destino):
    """Valida el tar completo antes de crear su carpeta. No usa extractall ni sigue enlaces."""
    destino = Path(destino)
    try:
        with tempfile.TemporaryFile() as claro:
            total = 0
            with gzip.open(str(archivo), 'rb') as entrada:
                while True:
                    b = entrada.read(min(1024 * 1024, MAX_CLARO - total + 1))
                    if not b:
                        break
                    total += len(b)
                    if total > MAX_CLARO:
                        raise Fallo('La copia descomprimida supera 200 MiB; no se extrae.')
                    claro.write(b)
            claro.seek(0)
            with tarfile.open(fileobj=claro, mode='r:') as tar:
                miembros = {}
                for m in tar:
                    r = _ruta(m)
                    if r is None:
                        continue
                    if r in miembros or len(miembros) >= MAX_ENTRADAS:
                        raise Fallo('La copia repite rutas o tiene demasiadas entradas; no se extrae.')
                    if m.size < 0 or m.size > MAX_CLARO:
                        raise Fallo('La copia contiene un tamaño no válido.')
                    miembros[r] = m
                for r in miembros:
                    for padre in Path(r).parents:
                        p = padre.as_posix()
                        if p in miembros and not miembros[p].isdir():
                            raise Fallo('La copia confunde un archivo con una carpeta; no se extrae.')
                if '.git/HEAD' not in miembros or not miembros['.git/HEAD'].isfile():
                    raise Fallo('La copia no trae su historia Git; se conserva el archivo sin unirlo.')
                empaquetadas = miembros.get('.git/packed-refs')
                if empaquetadas and empaquetadas.isfile():
                    with tar.extractfile(empaquetadas) as f:
                        if b'refs/replace/' in f.read():
                            raise Fallo('La copia contiene reemplazos de objetos en sus referencias empaquetadas.')
                destino.mkdir(mode=0o700)
                for r, m in miembros.items():
                    if r == '.git' or r.startswith('.git/'):
                        if m.isdir() or not _git_necesario(r):
                            continue
                    p = destino / r
                    p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                    if m.isdir():
                        p.mkdir(exist_ok=True, mode=0o700)
                    else:
                        with tar.extractfile(m) as entrada, _privado(p) as salida:
                            while True:
                                b = entrada.read(1024 * 1024)
                                if not b:
                                    break
                                salida.write(b)
                        p.chmod(0o700 if m.mode & 0o111 else 0o600)
                with _privado(destino / '.git/config') as f:
                    f.write(b'[core]\n\trepositoryformatversion = 0\n\tbare = false\n')
                for nombre in ('refs', 'objects'):
                    (destino / '.git' / nombre).mkdir(exist_ok=True, mode=0o700)
        _git(destino, 'fsck', '--full', '--no-reflogs')
        _git(destino, 'rev-parse', '--verify', 'HEAD^{commit}')
    except Fallo:
        raise
    except (OSError, EOFError, tarfile.TarError, ValueError):
        raise Fallo('No se pudo extraer una copia completa y segura. El archivo descargado se conserva.') from None
    return destino


class Cliente:
    def __init__(self, servidor):
        self.servidor = servidor
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(SinRedireccion(), urllib.request.HTTPCookieProcessor(self.cookies))

    def abrir(self, ruta, cuerpo=None):
        req = urllib.request.Request(self.servidor + '/v1/web/' + ruta,
                                     data=None if cuerpo is None else json.dumps(cuerpo).encode('utf-8'),
                                     headers={'Origin': self.servidor, 'Content-Type': 'application/json',
                                              'User-Agent': 'VoidPC/1'})
        try:
            return self.opener.open(req, timeout=180)
        except urllib.error.HTTPError as e:
            codigo = e.code
            e.close()
            raise Fallo('Void rechazó la petición (HTTP {}). No se modificó el vault del PC.'.format(codigo)) from None
        except (OSError, urllib.error.URLError):
            raise Fallo('Se interrumpió la conexión. Conserva la descarga y tu kit para reintentar.') from None

    def bytes(self, ruta, datos, cabeceras):
        """Un POST con bytes (el paquete de tus commits). Nunca sigue redirecciones."""
        req = urllib.request.Request(self.servidor + '/v1/web/' + ruta, data=datos,
                                     headers=dict({'Origin': self.servidor, 'Content-Type': 'application/octet-stream',
                                                   'User-Agent': 'VoidPC/1'}, **cabeceras))
        try:
            with self.opener.open(req, timeout=300) as r:
                return json.loads(r.read(65537))
        except urllib.error.HTTPError as e:
            try:
                motivo = json.loads(e.read(4096)).get('error')
            except (ValueError, AttributeError):
                motivo = None
            codigo = e.code
            e.close()
            raise Fallo((motivo or 'Void rechazó la subida') + ' (HTTP {}). No se subió nada.'.format(codigo)) from None
        except (OSError, urllib.error.URLError, ValueError):
            raise Fallo('Se interrumpió la conexión. No se subió nada; vuelve a probar.') from None

    def json(self, ruta, cuerpo):
        try:
            with self.abrir(ruta, cuerpo) as r:
                datos = r.read(65537)
            if len(datos) > 65536:
                raise ValueError()
            d = json.loads(datos)
            if not isinstance(d, dict):
                raise ValueError()
            return d
        except (ValueError, UnicodeError) as e:
            if isinstance(e, Fallo):
                raise
            raise Fallo('La respuesta de Void no es válida. Conserva tu kit para recuperar el acceso.') from None


def descargar(alias, destino, secreto, recuperar_con_kit=False, pc=None, servidor=SERVIDOR):
    """No sube ni controla la caja. Una unión solo incorpora commits de la copia descargada."""
    if not re.fullmatch(r'[a-z0-9-]{3,24}', alias):
        raise Fallo('El nombre del espacio no es válido.')
    patron = RE_KIT if recuperar_con_kit else RE_CODIGO
    if not isinstance(secreto, str) or not patron.fullmatch(secreto):
        raise Fallo('El kit o el código no tiene el formato esperado para esta opción.')
    if servidor != SERVIDOR and not re.fullmatch(r'http://(?:localhost|127\.0\.0\.1)(?::[0-9]{1,5})?', servidor):
        raise Fallo('Solo se conecta a Void o a un servidor de prueba de este ordenador.')
    destino = Path(destino).absolute()
    try:
        destino.mkdir(mode=0o700)
        acceso = _privado(destino / 'acceso.json')
        acceso.write(b'{}\n'); acceso.flush(); os.fsync(acceso.fileno())
    except OSError:
        raise Fallo('Elige una carpeta nueva cuyo padre exista y permita guardar archivos privados.') from None
    cliente = Cliente(servidor)
    sesion = False
    aviso_salida = False
    try:
        with acceso:
            entrada = cliente.json('entrar', {'alias': alias, 'kit' if recuperar_con_kit else 'recuperacion': secreto})
            sesion = True
            guardar = {}
            for origen, campo, patron in [('codigoNuevo', 'codigo', RE_CODIGO), ('kit', 'kit', RE_KIT)]:
                valor = entrada.get(origen)
                if isinstance(valor, str) and patron.fullmatch(valor):
                    guardar[campo] = valor
            acceso.seek(0); acceso.truncate()
            acceso.write((json.dumps(guardar) + '\n').encode('utf-8'))
            acceso.flush(); os.fsync(acceso.fileno())
        if entrada.get('alias') != alias or entrada.get('listo') is not True or entrada.get('candado') != 'abierto':
            raise Fallo('No se abrió el espacio solicitado. No se descarga ni se junta nada.')
        if recuperar_con_kit and 'codigo' not in guardar:
            raise Fallo('Falta el código nuevo de recuperación. Conserva el kit y vuelve a recuperar el acceso.')
        parcial = destino / 'archivo.parcial'
        h = hashlib.sha256(); total = 0
        with cliente.abrir('archivo') as entrada, _privado(parcial) as salida:
            while True:
                b = entrada.read(min(1024 * 1024, MAX_ARCHIVO - total + 1))
                if not b:
                    break
                total += len(b)
                if total > MAX_ARCHIVO:
                    raise Fallo('La descarga supera 128 MiB; queda como parcial y no se extrae.')
                h.update(b); salida.write(b)
            salida.flush(); os.fsync(salida.fileno())
        archivo = destino / 'archivo.tgz'
        parcial.rename(archivo)
        copia = extraer(archivo, destino / 'copia')
        union = None
        if pc is not None:
            pendiente = _git(copia, 'status', '--porcelain', '--untracked-files=all', '--ignore-submodules=all')
            # Un índice recibido puede ocultar cambios con assume-unchanged o skip-worktree.
            marcas = _git(copia, 'ls-files', '-v', '-z').split(b'\0')
            pendiente = pendiente or any(m and not m.startswith(b'H ') for m in marcas)
            if pendiente:
                union = {'resultado': 'copia_sin_guardar', 'mensaje':
                         'La copia tiene archivos sin commit. Se conserva entera, pero no se junta: Git no los incorporaría.'}
            else:
                union = turno.juntar(pc, copia)
        resultado = {'archivo': str(archivo), 'copia': str(copia), 'sha256': h.hexdigest(), 'union': union}
    except Fallo:
        raise
    except (OSError, EOFError, ValueError, subprocess.SubprocessError):
        raise Fallo('No se completó la descarga o la unión. Conserva la carpeta de descarga y acceso.json, si contiene un acceso nuevo.') from None
    finally:
        if not acceso.closed:
            acceso.close()
        if sesion or list(cliente.cookies):
            try:
                cliente.json('salir', {})
            except (Fallo, OSError):
                aviso_salida = True
                print('No se pudo cerrar la sesión temporal en Void. La cookie no se guarda en el PC; caducará en el servidor.')
        cliente.cookies.clear()
    resultado['sesion_cerrada'] = not aviso_salida
    return resultado


RE_COMMIT = re.compile(r'[0-9a-f]{40}(?:[0-9a-f]{24})?')


def _entrar(alias, secreto, servidor):
    if not re.fullmatch(r'[a-z0-9-]{3,24}', alias):
        raise Fallo('El nombre del espacio no es válido.')
    if not isinstance(secreto, str) or not RE_CODIGO.fullmatch(secreto):
        raise Fallo('El código no tiene el formato esperado.')
    if servidor != SERVIDOR and not re.fullmatch(r'http://(?:localhost|127\.0\.0\.1)(?::[0-9]{1,5})?', servidor):
        raise Fallo('Solo se conecta a Void o a un servidor de prueba de este ordenador.')
    cliente = Cliente(servidor)
    entrada = cliente.json('entrar', {'alias': alias, 'recuperacion': secreto})
    if entrada.get('alias') != alias or entrada.get('listo') is not True or entrada.get('candado') != 'abierto':
        _salir(cliente)
        raise Fallo('No se abrió el espacio solicitado.')
    return cliente


def _salir(cliente):
    try:
        cliente.json('salir', {})
    except (Fallo, OSError):
        print('No se pudo cerrar la sesión temporal en Void; caducará en el servidor.')
    cliente.cookies.clear()


def _leer_estado(cliente):
    with cliente.abrir('pc') as r:
        d = json.loads(r.read(65537))
    if not isinstance(d, dict):
        raise Fallo('La respuesta de Void no es válida.')
    return d


def _comparar(pc, guardado):
    """Fase 1, parte 3 [17-oct]: tu ordenador frente al último commit guardado del espacio. Sin dato, nunca «al día»."""
    head_pc = _git(pc, 'rev-parse', '--verify', 'HEAD^{commit}').decode().strip()
    sucio = bool(_git(pc, 'status', '--porcelain', '--untracked-files=no').strip())
    g = (guardado or {}).get('head') if isinstance(guardado, dict) else None
    if not g or not RE_COMMIT.fullmatch(g):
        return 'sin_dato', 'No se pudo comprobar: tu espacio todavía no ha guardado ningún commit.', head_pc, None, sucio
    if g == head_pc:
        return 'al_dia', 'Al día: tu ordenador y tu espacio tienen los mismos commits.', head_pc, g, sucio
    conocido = subprocess.run(['git', '-C', str(pc), 'cat-file', '-e', g + '^{commit}'], stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL).returncode == 0
    if conocido and subprocess.run(['git', '-C', str(pc), 'merge-base', '--is-ancestor', g, 'HEAD'],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
        n = _git(pc, 'rev-list', '--count', g + '..HEAD').decode().strip()
        return 'pc_delante', 'Tu ordenador tiene {} commit(s) que tu espacio no tiene: súbelos con «subir».'.format(n), head_pc, g, sucio
    if conocido and subprocess.run(['git', '-C', str(pc), 'merge-base', '--is-ancestor', 'HEAD', g],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
        return 'espacio_delante', 'Tu espacio tiene commits que tu ordenador no tiene: bájalos con «bajar --juntar».', head_pc, g, sucio
    if not conocido:
        return 'espacio_delante', 'Tu espacio tiene cambios que tu ordenador no conoce: bájalos con «bajar --juntar».', head_pc, g, sucio
    return 'distintos', 'Los dos tienen cambios: baja, junta en tu ordenador y luego sube.', head_pc, g, sucio


def estado(alias, secreto, pc, servidor=SERVIDOR):
    cliente = _entrar(alias, secreto, servidor)
    try:
        d = _leer_estado(cliente)
    finally:
        _salir(cliente)
    clave, mensaje, head_pc, head_espacio, sucio = _comparar(Path(pc), d.get('guardado'))
    return {'estado': clave, 'mensaje': mensaje, 'sucio': sucio, 'head_pc': head_pc, 'head_espacio': head_espacio,
            'pendiente': d.get('pendiente'), 'ultimo': d.get('ultimo'), 'despierta': d.get('despierta') is True}


def subir(alias, secreto, pc, servidor=SERVIDOR):
    """Sube solo tus commits nuevos, como un paquete de git, y solo con el espacio dormido. Se aplican al despertar."""
    pc = Path(pc)
    if _git(pc, 'status', '--porcelain', '--untracked-files=no').strip():
        raise Fallo('Tienes cambios sin commit en tu ordenador: guárdalos en un commit y vuelve a subir. No se subió nada.')
    cliente = _entrar(alias, secreto, servidor)
    try:
        d = _leer_estado(cliente)
        clave, mensaje, head_pc, g, _ = _comparar(pc, d.get('guardado'))
        if clave == 'al_dia':
            return {'resultado': 'al_dia', 'mensaje': mensaje}
        if clave != 'pc_delante':
            raise Fallo(mensaje + ' No se subió nada.')
        if d.get('despierta') is True:
            raise Fallo('Tu espacio está despierto: duérmelo en Mi espacio y vuelve a subir. Así nada se pisa.')
        with tempfile.TemporaryDirectory(prefix='void-subir-') as t:
            paquete = Path(t) / 'pc.bundle'
            _git(pc, 'bundle', 'create', str(paquete), g + '..HEAD', 'HEAD')
            datos = paquete.read_bytes()
        if len(datos) > 50 * 1024 * 1024:
            raise Fallo('Tus commits nuevos pesan más de 50 MiB. No se subió nada.')
        cliente.bytes('pc', datos, {'x-void-base': g})
        return {'resultado': 'pendiente', 'mensaje': 'Subido: tus commits se aplicarán la próxima vez que despierte tu espacio. '
                'Las conversaciones y los archivos ignorados del espacio no se tocan.'}
    finally:
        _salir(cliente)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('accion', choices=['bajar', 'estado', 'subir'])
    p.add_argument('--alias', required=True)
    p.add_argument('--destino', help='bajar: carpeta nueva para la descarga privada; su padre debe existir.')
    p.add_argument('--vault', default='.', help='estado y subir: tu vault del ordenador.')
    p.add_argument('--juntar', metavar='VAULT_PC', help='Junta los commits de la copia con este vault mediante turno.py.')
    p.add_argument('--recuperar-con-kit', action='store_true', help='Recupera con kit: cambia el código y cierra sesiones previas.')
    a = p.parse_args(argv)
    if a.accion in ('estado', 'subir'):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', getpass.GetPassWarning)
                secreto = getpass.getpass('Código privado: ').strip()
            if a.accion == 'estado':
                r = estado(a.alias, secreto, a.vault)
                print(r['mensaje'])
                if r['sucio']:
                    print('Ojo: tienes cambios sin commit en tu ordenador; no cuentan hasta que los guardes.')
                if r['pendiente']:
                    print('Hay una subida tuya esperando a que despierte tu espacio.')
                if isinstance(r['ultimo'], dict) and r['ultimo'].get('resultado') == 'choque':
                    print('La última subida chocó en: {}. Baja, junta en tu ordenador y vuelve a subir.'.format(', '.join(r['ultimo'].get('ficheros') or []) or 'algún fichero'))
                return 0 if r['estado'] == 'al_dia' else 1
            r = subir(a.alias, secreto, a.vault)
            print(r['mensaje'])
            return 0
        except getpass.GetPassWarning:
            print('Abre una terminal con entrada oculta para introducir tu código. No lo pegues en el chat ni en los argumentos.')
            return 1
        except (Fallo, EOFError, KeyboardInterrupt) as e:
            print('No se completó: ' + (str(e) if isinstance(e, Fallo) else 'entrada cancelada.'))
            return 1
    if not a.destino:
        p.error('bajar necesita --destino')
    if a.recuperar_con_kit:
        print('Recuperar con el kit cambia tu código y cierra sesiones anteriores. El código nuevo se guardará en acceso.json, dentro del destino privado. Conserva el kit si se interrumpe.')
    print('Se descargará la última copia guardada. Puede no incluir cambios activos del espacio. No sincroniza conversaciones ni archivos ignorados con el PC.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', getpass.GetPassWarning)
            secreto = getpass.getpass('Kit privado: ' if a.recuperar_con_kit else 'Código privado: ').strip()
        r = descargar(a.alias, a.destino, secreto, a.recuperar_con_kit, a.juntar)
        print('Descarga conservada en: ' + r['archivo'])
        print('Si Void devolvió un código o kit nuevo, está en acceso.json dentro de esa carpeta. Guárdalo en un lugar privado.')
        print('SHA-256 de los bytes recibidos: ' + r['sha256'])
        if r['union']:
            print('Unión de commits de la última copia guardada: ' + r['union']['mensaje'])
            return 0 if r['union']['resultado'] in ('al_dia', 'avanza', 'unido', 'void_detras') else 1
        return 0
    except getpass.GetPassWarning:
        print('Abre una terminal con entrada oculta para introducir tu código o kit. No lo pegues en el chat ni en los argumentos.')
        return 1
    except (Fallo, EOFError, KeyboardInterrupt) as e:
        print('No se completó: ' + (str(e) if isinstance(e, Fallo) else 'entrada cancelada.'))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
