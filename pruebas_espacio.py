"""Descarga por terminal con datos inventados; nunca usa servicios externos."""
import contextlib
import hashlib
import http.server
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import threading
import unittest
from unittest import mock
import espacio as E

CODIGO = 'vr_' + 'a' * 64
KIT = 'vk_' + 'b' * 64
NUEVO = 'vr_' + 'c' * 64


def git(p, *args):
    r = subprocess.run(['git', '-C', str(p), '-c', 'user.name=Prueba',
                        '-c', 'user.email=prueba@example.com'] + list(args),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode:
        raise AssertionError(r.stderr.decode('utf-8', 'replace'))
    return r.stdout.decode('utf-8', 'replace').strip()


def tar_de(p):
    b = io.BytesIO()
    with tarfile.open(fileobj=b, mode='w:gz') as t:
        t.add(str(p), arcname='.')
    return b.getvalue()


class DescargaEspacio(unittest.TestCase):
    def setUp(self):
        entorno = mock.patch.dict(os.environ, {'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1',
                                              'GIT_AUTHOR_NAME': 'Prueba', 'GIT_COMMITTER_NAME': 'Prueba',
                                              'GIT_AUTHOR_EMAIL': 'prueba@example.com', 'GIT_COMMITTER_EMAIL': 'prueba@example.com'})
        entorno.start(); self.addCleanup(entorno.stop)
        self.tmp = Path(tempfile.mkdtemp(prefix='void-descarga-prueba-'))
        self.pc = self.tmp / 'pc'; self.pc.mkdir()
        git(self.pc, 'init', '-q')
        (self.pc / 'nota.md').write_text('inicio\n')
        (self.pc / '.gitignore').write_text('.void/\n.agente/\n')
        git(self.pc, 'add', '-A'); git(self.pc, 'commit', '-qm', 'inicio')
        self.remota = self.tmp / 'remota'
        git(self.tmp, 'clone', '-q', str(self.pc), str(self.remota))
        (self.remota / 'nuevo.md').write_text('cambio remoto\n')
        git(self.remota, 'add', '-A'); git(self.remota, 'commit', '-qm', 'cambio')
        (self.remota / '.void').mkdir()
        (self.remota / '.void/privado').write_text('dato inventado ignorado')
        self.datos = tar_de(self.remota)
        self.destino = self.tmp / 'descarga'
        self.peticiones = []
        caso = self
        class Red:
            def open(self, req, timeout=180):
                caso.peticiones.append(req)
                if req.full_url.endswith('/entrar'):
                    return io.BytesIO(json.dumps(caso.entrada).encode())
                if req.full_url.endswith('/salir'):
                    return io.BytesIO(b'{}')
                if caso.falla_archivo:
                    raise OSError('error que incluye ' + CODIGO)
                return io.BytesIO(caso.datos)
        self.entrada = {'alias': 'espacio-prueba', 'listo': True, 'candado': 'abierto'}
        self.falla_archivo = False
        self.parche = mock.patch.object(E.urllib.request, 'build_opener', return_value=Red())
        self.parche.start()
        self.addCleanup(self.parche.stop)
        self.addCleanup(shutil.rmtree, str(self.tmp))

    def bajar(self, **kw):
        return E.descargar('espacio-prueba', self.destino, CODIGO, **kw)

    def test_descarga_privada_y_union_con_git_real(self):
        r = self.bajar(pc=self.pc)
        self.assertEqual(Path(r['archivo']).read_bytes(), self.datos)
        self.assertEqual(r['sha256'], hashlib.sha256(self.datos).hexdigest())
        self.assertEqual(r['union']['resultado'], 'avanza')
        self.assertTrue((self.pc / 'nuevo.md').is_file())
        self.assertFalse((self.pc / '.void/privado').exists())
        self.assertEqual(self.destino.stat().st_mode & 0o777, 0o700)
        self.assertEqual(Path(r['archivo']).stat().st_mode & 0o777, 0o600)
        self.assertEqual([q.full_url.rsplit('/', 1)[1] for q in self.peticiones], ['entrar', 'archivo', 'salir'])
        self.assertEqual(json.loads(self.peticiones[0].data)['recuperacion'], CODIGO)
        self.assertEqual(self.peticiones[0].get_header('Origin'), 'https://vaultvoid.app')

    def test_kit_guarda_codigo_rotado_antes_de_fallar_descarga(self):
        self.entrada['codigoNuevo'] = NUEVO
        self.falla_archivo = True
        with self.assertRaises(E.Fallo) as c:
            E.descargar('espacio-prueba', self.destino, KIT, recuperar_con_kit=True)
        self.assertNotIn(CODIGO, str(c.exception))
        acceso = self.destino / 'acceso.json'
        self.assertEqual(json.loads(acceso.read_text())['codigo'], NUEVO)
        self.assertEqual(acceso.stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(self.peticiones[0].data)['kit'], KIT)
        self.assertTrue(self.peticiones[-1].full_url.endswith('/salir'))

    def test_primera_entrada_conserva_kit_sin_imprimir(self):
        self.entrada['kit'] = KIT
        out = io.StringIO()
        with contextlib.redirect_stdout(out): self.bajar()
        self.assertEqual(json.loads((self.destino / 'acceso.json').read_text())['kit'], KIT)
        self.assertNotIn(KIT, out.getvalue())
        self.assertNotIn(CODIGO, out.getvalue())

    def test_destino_existente_y_credenciales_invalidas_no_usan_red(self):
        self.destino.mkdir(); (self.destino / 'conservar').write_text('original')
        with self.assertRaises(E.Fallo): self.bajar()
        self.assertEqual((self.destino / 'conservar').read_text(), 'original')
        for s, kit in [('incorrecto', False), (KIT, False), (CODIGO, True)]:
            with self.assertRaises(E.Fallo):
                E.descargar('espacio-prueba', self.tmp / 'otro', s, recuperar_con_kit=kit)
        self.assertFalse(self.peticiones)

    def test_host_ajeno_redireccion_y_error_no_filtran_secreto(self):
        for servidor in ['https://ajeno.invalid', 'https://vaultvoid.app' + '@' + 'ajeno.invalid', 'http://vaultvoid.app']:
            with self.assertRaises(E.Fallo): self.bajar(servidor=servidor)
        self.assertFalse(self.peticiones)
        with self.assertRaises(E.Fallo):
            E.SinRedireccion().redirect_request(None, None, 302, '', {}, 'https://ajeno.invalid')
        error = E.urllib.error.HTTPError('https://vaultvoid.app', 401, CODIGO, {}, io.BytesIO(CODIGO.encode()))
        with mock.patch.object(E.urllib.request, 'build_opener') as abrir:
            abrir.return_value.open.side_effect = error
            with self.assertRaises(E.Fallo) as c: self.bajar()
        self.assertNotIn(CODIGO, str(c.exception))

    def test_respuesta_cerrada_o_alias_distinto_no_descarga(self):
        for campo, valor in [('candado', 'cerrado'), ('alias', 'otro-espacio'), ('listo', False)]:
            with self.subTest(campo=campo):
                self.entrada[campo] = valor
                with self.assertRaises(E.Fallo): self.bajar()
                self.assertFalse(any(q.full_url.endswith('/archivo') for q in self.peticiones))
                shutil.rmtree(self.destino)
                self.entrada = {'alias': 'espacio-prueba', 'listo': True, 'candado': 'abierto'}

    def test_limites_comprimido_y_descomprimido(self):
        with mock.patch.object(E, 'MAX_ARCHIVO', 20), self.assertRaises(E.Fallo): self.bajar()
        self.assertFalse((self.destino / 'archivo.tgz').exists())
        shutil.rmtree(self.destino)
        with mock.patch.object(E, 'MAX_CLARO', 20), self.assertRaises(E.Fallo): self.bajar()
        self.assertEqual((self.destino / 'archivo.tgz').read_bytes(), self.datos)
        self.assertFalse((self.destino / 'copia').exists())

    def test_archivos_hostiles_no_se_extraen(self):
        for nombre, tipo in [('../fuera', tarfile.REGTYPE), ('/fuera', tarfile.REGTYPE),
                             ('a/../../fuera', tarfile.REGTYPE), ('a\\b', tarfile.REGTYPE),
                             ('enlace', tarfile.SYMTYPE), ('duro', tarfile.LNKTYPE),
                             ('fifo', tarfile.FIFOTYPE), ('.git/objects/info/alternates', tarfile.REGTYPE),
                             ('.git/info/grafts', tarfile.REGTYPE), ('.git/refs/replace/x', tarfile.REGTYPE)]:
            with self.subTest(nombre=nombre, tipo=tipo):
                b = io.BytesIO()
                with tarfile.open(fileobj=b, mode='w:gz') as t:
                    t.add(str(self.remota), arcname='.')
                    m = tarfile.TarInfo(nombre); m.type = tipo; m.linkname = '/fuera'
                    t.addfile(m)
                self.datos = b.getvalue()
                with self.assertRaises(E.Fallo): self.bajar()
                self.assertFalse((self.destino / 'copia').exists())
                shutil.rmtree(self.destino)
        self.assertFalse((self.tmp / 'fuera').exists())

    def test_ruta_repetida_y_colision_fichero_directorio(self):
        for nombres in [('a', './a'), ('a', 'a/b')]:
            b = io.BytesIO()
            with tarfile.open(fileobj=b, mode='w:gz') as t:
                t.add(str(self.remota), arcname='.')
                for n in nombres: t.addfile(tarfile.TarInfo(n))
            self.datos = b.getvalue()
            with self.assertRaises(E.Fallo): self.bajar()
            self.assertFalse((self.destino / 'copia').exists())
            shutil.rmtree(self.destino)

    def test_no_ejecuta_configuracion_ni_hooks_recibidos(self):
        marca = self.tmp / 'ejecutado'
        gancho = self.remota / '.git/hooks/post-checkout'
        gancho.write_text('#!/bin/sh\ntouch "{}"\n'.format(marca)); gancho.chmod(0o700)
        git(self.remota, 'config', 'core.fsmonitor', 'touch "{}"'.format(marca))
        git(self.remota, 'config', 'core.hooksPath', str(gancho.parent))
        self.datos = tar_de(self.remota)
        r = self.bajar(pc=self.pc)
        self.assertEqual(r['union']['resultado'], 'avanza')
        self.assertFalse(marca.exists())
        self.assertFalse((Path(r['copia']) / '.git/hooks').exists())
        self.assertNotIn('fsmonitor', (Path(r['copia']) / '.git/config').read_text())
        self.assertEqual(Path(r['archivo']).read_bytes(), self.datos)

    def test_copia_con_cambios_sin_commit_no_se_junta(self):
        (self.remota / 'nota.md').write_text('sin commit\n')
        self.datos = tar_de(self.remota)
        antes = git(self.pc, 'rev-parse', 'HEAD')
        r = self.bajar(pc=self.pc)
        self.assertEqual(r['union']['resultado'], 'copia_sin_guardar')
        self.assertEqual(git(self.pc, 'rev-parse', 'HEAD'), antes)
        self.assertEqual((Path(r['copia']) / 'nota.md').read_text(), 'sin commit\n')

    def test_falta_git_no_se_declara_copia_unible(self):
        b = io.BytesIO()
        with tarfile.open(fileobj=b, mode='w:gz') as t: t.addfile(tarfile.TarInfo('nota.md'))
        self.datos = b.getvalue()
        with self.assertRaises(E.Fallo): self.bajar(pc=self.pc)
        self.assertEqual((self.destino / 'archivo.tgz').read_bytes(), self.datos)

    def test_refs_empaquetadas_no_ocultan_reemplazos(self):
        git(self.remota, 'replace', 'HEAD', 'HEAD~1')
        git(self.remota, 'pack-refs', '--all', '--prune')
        (self.remota / '.git/refs/replace').rmdir()
        self.datos = tar_de(self.remota)
        with self.assertRaises(E.Fallo): self.bajar(pc=self.pc)
        self.assertFalse((self.destino / 'copia').exists())

    def test_indice_no_oculta_cambios_con_assume_unchanged(self):
        git(self.remota, 'update-index', '--assume-unchanged', 'nota.md')
        (self.remota / 'nota.md').write_text('cambio oculto\n')
        self.datos = tar_de(self.remota)
        r = self.bajar(pc=self.pc)
        self.assertEqual(r['union']['resultado'], 'copia_sin_guardar')
        self.assertFalse((self.pc / 'nuevo.md').exists())

    def test_objetos_empaquetados_tambien_se_juntan(self):
        git(self.remota, 'gc')
        self.datos = tar_de(self.remota)
        self.assertEqual(self.bajar(pc=self.pc)['union']['resultado'], 'avanza')

    def test_choque_conserva_pc_y_descarga(self):
        for carpeta, texto in [(self.pc, 'PC\n'), (self.remota, 'Void\n')]:
            (carpeta / 'nota.md').write_text(texto)
            git(carpeta, 'add', '-A'); git(carpeta, 'commit', '-qm', 'cambio distinto')
        self.datos = tar_de(self.remota)
        antes = git(self.pc, 'rev-parse', 'HEAD')
        r = self.bajar(pc=self.pc)
        self.assertEqual(r['union']['resultado'], 'choque')
        self.assertEqual(git(self.pc, 'rev-parse', 'HEAD'), antes)
        self.assertEqual((self.pc / 'nota.md').read_text(), 'PC\n')
        self.assertEqual(Path(r['archivo']).read_bytes(), self.datos)

    def test_historia_ajena_y_pc_sucio_no_se_juntan(self):
        otra = self.tmp / 'otra'; otra.mkdir()
        git(otra, 'init', '-q'); (otra / 'otro').write_text('otra historia')
        git(otra, 'add', '-A'); git(otra, 'commit', '-qm', 'otra')
        r = self.bajar(pc=otra)
        self.assertEqual(r['union']['resultado'], 'sin_comun')
        shutil.rmtree(self.destino)
        (self.pc / 'nota.md').write_text('local sin guardar')
        r = self.bajar(pc=self.pc)
        self.assertEqual(r['union']['resultado'], 'sin_guardar')
        self.assertEqual((self.pc / 'nota.md').read_text(), 'local sin guardar')

    def test_cli_no_admite_secreto_en_argumentos(self):
        out = io.StringIO()
        with mock.patch.object(E.getpass, 'getpass', return_value=CODIGO), contextlib.redirect_stdout(out):
            codigo = E.main(['bajar', '--alias', 'espacio-prueba', '--destino', str(self.destino)])
        self.assertEqual(codigo, 0)
        self.assertNotIn(CODIGO, out.getvalue())
        self.assertIn('última copia guardada', out.getvalue())

    def test_cli_sin_entrada_oculta_no_lee_el_secreto(self):
        out = io.StringIO()
        with mock.patch.object(E.getpass, 'getpass', side_effect=E.getpass.GetPassWarning), contextlib.redirect_stdout(out):
            codigo = E.main(['bajar', '--alias', 'espacio-prueba', '--destino', str(self.destino)])
        self.assertEqual(codigo, 1)
        self.assertFalse(self.peticiones)
        self.assertIn('entrada oculta', out.getvalue())

    def test_salida_fallida_se_informa_sin_perder_descarga(self):
        abrir = E.Cliente.json
        def pedir(cliente, ruta, cuerpo):
            if ruta == 'salir': raise E.Fallo('salida interrumpida')
            return abrir(cliente, ruta, cuerpo)
        out = io.StringIO()
        with mock.patch.object(E.Cliente, 'json', pedir), contextlib.redirect_stdout(out):
            r = self.bajar()
        self.assertFalse(r['sesion_cerrada'])
        self.assertEqual(Path(r['archivo']).read_bytes(), self.datos)
        self.assertIn('No se pudo cerrar', out.getvalue())

    def test_http_local_cookies_origin_y_salida(self):
        self.parche.stop()
        caso = self; vistos = []
        class Servidor(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_POST(self):
                cuerpo = json.loads(self.rfile.read(int(self.headers['content-length'])))
                vistos.append((self.path, self.headers.get('Cookie'), self.headers.get('Origin'), cuerpo))
                self.send_response(200)
                if self.path.endswith('/entrar'):
                    self.send_header('Set-Cookie', '__Host-void=sesion-ficticia; Path=/; HttpOnly')
                    self.send_header('Set-Cookie', '__Host-void-ap=aparato-ficticio; Path=/; HttpOnly')
                self.end_headers(); self.wfile.write(json.dumps(caso.entrada).encode())
            def do_GET(self):
                vistos.append((self.path, self.headers.get('Cookie'), None, None))
                self.send_response(200); self.end_headers(); self.wfile.write(caso.datos)
        servidor = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Servidor)
        hilo = threading.Thread(target=servidor.serve_forever, daemon=True); hilo.start()
        try:
            origen = 'http://127.0.0.1:' + str(servidor.server_port)
            self.bajar(servidor=origen)
        finally:
            servidor.shutdown(); servidor.server_close(); hilo.join()
        self.assertEqual(vistos[0][2], origen)
        self.assertIn('__Host-void=sesion-ficticia', vistos[1][1])
        self.assertIn('__Host-void-ap=aparato-ficticio', vistos[1][1])
        self.assertEqual(vistos[-1][0], '/v1/web/salir')



class SubidaEspacio(unittest.TestCase):
    """Fase 1, parte 3 [17-oct]: estado y subida contra un Void de mentira en este ordenador."""
    def setUp(self):
        entorno = mock.patch.dict(os.environ, {'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1',
                                              'GIT_AUTHOR_NAME': 'Prueba', 'GIT_COMMITTER_NAME': 'Prueba',
                                              'GIT_AUTHOR_EMAIL': 'prueba@example.com', 'GIT_COMMITTER_EMAIL': 'prueba@example.com'})
        entorno.start(); self.addCleanup(entorno.stop)
        self.tmp = Path(tempfile.mkdtemp(prefix='void-subida-prueba-')); self.addCleanup(shutil.rmtree, str(self.tmp))
        self.pc = self.tmp / 'pc'; self.pc.mkdir(); git(self.pc, 'init', '-q')
        (self.pc / 'nota.md').write_text('inicio\n'); git(self.pc, 'add', '-A'); git(self.pc, 'commit', '-qm', 'inicio')
        self.base = git(self.pc, 'rev-parse', 'HEAD')
        self.espacio = {'guardado': {'head': self.base, 'fecha': 1}, 'pendiente': None, 'ultimo': None, 'despierta': False}
        self.subidas = []
        caso = self
        class Servidor(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def responder(self, d, codigo=200):
                self.send_response(codigo); self.end_headers(); self.wfile.write(json.dumps(d).encode())
            def do_POST(self):
                cuerpo = self.rfile.read(int(self.headers['content-length']))
                if self.path.endswith('/entrar'): return self.responder({'alias': 'espacio-prueba', 'listo': True, 'candado': 'abierto'})
                if self.path.endswith('/salir'): return self.responder({})
                if self.path.endswith('/pc'):
                    caso.subidas.append((self.headers.get('x-void-base'), cuerpo, self.headers.get('Origin')))
                    return self.responder({'pendiente': True})
                self.responder({'error': 'no'}, 404)
            def do_GET(self):
                self.responder(caso.espacio)
        self.servidor = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Servidor)
        hilo = threading.Thread(target=self.servidor.serve_forever, daemon=True); hilo.start()
        self.addCleanup(lambda: (self.servidor.shutdown(), self.servidor.server_close(), hilo.join()))
        self.origen = 'http://127.0.0.1:' + str(self.servidor.server_port)

    def commit(self, nombre='desde-el-pc.md'):
        (self.pc / nombre).write_text('escrito en el ordenador\n'); git(self.pc, 'add', '-A'); git(self.pc, 'commit', '-qm', 'pc')

    def test_estado_al_dia_delante_y_sin_dato(self):
        self.assertEqual(E.estado('espacio-prueba', CODIGO, self.pc, self.origen)['estado'], 'al_dia')
        self.commit()
        r = E.estado('espacio-prueba', CODIGO, self.pc, self.origen)
        self.assertEqual(r['estado'], 'pc_delante'); self.assertIn('1 commit', r['mensaje'])
        self.espacio['guardado'] = {'head': 'f' * 40}
        self.assertEqual(E.estado('espacio-prueba', CODIGO, self.pc, self.origen)['estado'], 'espacio_delante')
        self.espacio['guardado'] = None
        self.assertEqual(E.estado('espacio-prueba', CODIGO, self.pc, self.origen)['estado'], 'sin_dato', 'sin dato dice al día')

    def test_subir_manda_solo_los_commits_nuevos_desde_la_base(self):
        self.commit()
        r = E.subir('espacio-prueba', CODIGO, self.pc, self.origen)
        self.assertEqual(r['resultado'], 'pendiente')
        base, paquete, origen = self.subidas[0]
        self.assertEqual(base, self.base); self.assertEqual(origen, self.origen)
        espacio = self.tmp / 'espacio'; git(self.tmp, 'clone', '-q', str(self.pc), str(espacio)); git(espacio, 'reset', '-q', '--hard', self.base)
        (self.tmp / 'p.bundle').write_bytes(paquete)
        git(espacio, 'bundle', 'verify', str(self.tmp / 'p.bundle'))
        git(espacio, 'fetch', '-q', str(self.tmp / 'p.bundle'), 'HEAD:refs/void/pc'); git(espacio, 'merge', '-q', '--ff-only', 'refs/void/pc')
        self.assertTrue((espacio / 'desde-el-pc.md').exists())
        self.assertEqual(git(self.pc, 'rev-list', '--count', self.base + '..HEAD'), '1')

    def test_rojo_no_sube_con_cambios_sin_commit_espacio_despierto_o_adelantado(self):
        self.commit(); (self.pc / 'nota.md').write_text('sin guardar\n')
        with self.assertRaises(E.Fallo): E.subir('espacio-prueba', CODIGO, self.pc, self.origen)
        git(self.pc, 'checkout', '-q', '--', 'nota.md')
        self.espacio['despierta'] = True
        with self.assertRaises(E.Fallo): E.subir('espacio-prueba', CODIGO, self.pc, self.origen)
        self.espacio['despierta'] = False; self.espacio['guardado'] = {'head': 'f' * 40}
        with self.assertRaises(E.Fallo): E.subir('espacio-prueba', CODIGO, self.pc, self.origen)
        self.assertEqual(self.subidas, [], 'subió algo que no debía')

    def test_al_dia_no_sube_nada(self):
        self.assertEqual(E.subir('espacio-prueba', CODIGO, self.pc, self.origen)['resultado'], 'al_dia')
        self.assertEqual(self.subidas, [])


if __name__ == '__main__': unittest.main()
