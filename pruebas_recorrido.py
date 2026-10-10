"""Recorrido local del cliente contra el Worker real, sin cuentas ni mensajes reales."""
import contextlib
import io
import json
import os
from pathlib import Path
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))
import void as V


class Recorrido(unittest.TestCase):
    def test_dos_vaults_con_worker_real(self):
        with tempfile.TemporaryDirectory(prefix='void-recorrido-') as tmp:
            raiz = Path(tmp)
            red = RAIZ / 'red'
            wrangler = red / 'node_modules/.bin/wrangler'
            persist = raiz / 'd1'
            env = dict(os.environ, WRANGLER_SEND_METRICS='false', CI='true')
            env.update(GIT_CONFIG_GLOBAL=str(raiz / 'gitconfig'), GIT_CONFIG_NOSYSTEM='1')
            (raiz / 'gitconfig').write_text('', encoding='utf-8')
            migracion = subprocess.run([str(wrangler), 'd1', 'migrations', 'apply', 'DB', '--local',
                                        '--persist-to', str(persist)], cwd=red, env=env,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
            self.assertEqual(migracion.returncode, 0, 'No se pudo preparar la D1 local')
            with socket.socket() as libre:
                libre.bind(('127.0.0.1', 0))
                puerto = libre.getsockname()[1]
            url = 'http://127.0.0.1:{}'.format(puerto)
            with (raiz / 'worker.log').open('w') as log:
                worker = subprocess.Popen([str(wrangler), 'dev', '--port', str(puerto), '--ip', '127.0.0.1',
                                           '--persist-to', str(persist)], cwd=red, env=env,
                                          stdout=log, stderr=log, start_new_session=True)
                anterior = os.environ.get('VOID_RED')
                os.environ['VOID_RED'] = url
                try:
                    limite = time.monotonic() + 60
                    while True:
                        try:
                            with urllib.request.urlopen(url + '/', timeout=1):
                                break
                        except Exception:
                            if worker.poll() is not None or time.monotonic() > limite:
                                self.fail('El Worker local no arrancó')
                            time.sleep(0.25)
                    vaults = []
                    for alias in ('pruebaana', 'pruebabea'):
                        vault = raiz / alias
                        vault.mkdir()
                        subprocess.run(['git', 'init', '-q', str(vault)], env=env, check=True)
                        (vault / '.gitignore').write_text('.void/\n', encoding='utf-8')
                        (vault / 'void.json').write_text('{}', encoding='utf-8')
                        with contextlib.redirect_stdout(io.StringIO()):
                            self.assertEqual(V.orden_registrar(vault, alias, 'Prueba'), 0)
                        self.assertEqual(len(V.pedir_red('GET', '/v1/clave/' + alias)[1]['clave']), 44)
                        vaults.append(vault)
                    ana, bea = vaults
                    cuerpo = 'Contenido privado de prueba: piñón y brújula.'
                    with contextlib.redirect_stdout(io.StringIO()):
                        V.orden_escribir(ana, 'pruebabea', 'PETICION', 'Revisión', 'Una respuesta', cuerpo, autoriza='Prueba · persona')
                    bandeja = V.pedir_red('GET', '/v1/mensajes', V.la_llave(bea))[1]['mensajes']
                    self.assertEqual(len(bandeja), 1)
                    self.assertNotIn(cuerpo, json.dumps(bandeja, ensure_ascii=False))
                    bases = list(persist.rglob('*.sqlite'))
                    self.assertTrue(bases)
                    filas = []
                    for base in bases:
                        with contextlib.closing(sqlite3.connect(base)) as db:
                            if db.execute("SELECT name FROM sqlite_master WHERE name='mensajes'").fetchone():
                                filas.extend(db.execute('SELECT * FROM mensajes').fetchall())
                    self.assertEqual(len(filas), 1)
                    self.assertNotIn(cuerpo, repr(filas))
                    with contextlib.redirect_stdout(io.StringIO()):
                        V.orden_mensajes(bea)
                    primero = V._guardados(bea)[0]
                    self.assertEqual(primero['cuerpo'], cuerpo)
                    self.assertEqual(V.pedir_red('GET', '/v1/mensajes', V.la_llave(bea))[1]['mensajes'], [])
                    codigo, _ = V.git(bea, 'check-ignore', '-q', '--', '.void/mensajes', comprobar=False)
                    self.assertEqual(codigo, 0)
                    with contextlib.redirect_stdout(io.StringIO()):
                        V.orden_responder(bea, str(primero['id']), 'Respuesta de prueba', autoriza='Prueba · persona')
                        V.orden_mensajes(ana)
                    respuesta = V._guardados(ana)[0]
                    self.assertEqual(respuesta['responde_a'], primero['id'])
                    self.assertEqual(respuesta['cuerpo'], 'Respuesta de prueba')
                    with contextlib.redirect_stdout(io.StringIO()):
                        V.orden_escribir(ana, 'pruebabea', 'AVISO', 'Segundo', 'No hace falta respuesta', 'Otro mensaje', autoriza='Prueba · persona')
                        V.orden_mensajes(bea)
                    self.assertEqual(len(V._guardados(bea)), 2)
                    self.assertGreater(max(m['id'] for m in V._guardados(bea)), respuesta['id'])
                    with contextlib.redirect_stdout(io.StringIO()):
                        V.orden_bloquear(bea, 'pruebaana', True)
                        V.orden_escribir(ana, 'pruebabea', 'AVISO', 'Bloqueado', 'No hace falta respuesta', 'No debe llegar', autoriza='Prueba · persona')
                    self.assertEqual(V.pedir_red('GET', '/v1/mensajes', V.la_llave(bea))[1]['mensajes'], [])
                finally:
                    if anterior is None:
                        os.environ.pop('VOID_RED', None)
                    else:
                        os.environ['VOID_RED'] = anterior
                    try:
                        os.killpg(worker.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    try:
                        worker.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(worker.pid, signal.SIGKILL)
                        worker.wait(timeout=5)


if __name__ == '__main__':
    unittest.main(verbosity=2)
